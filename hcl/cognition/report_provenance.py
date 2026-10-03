"""Bounded query-selected report families, without majority-to-belief inference."""
from dataclasses import dataclass, replace
import json
import re

from .core import ClaimKind, identity
from .epistemic import Attitude, MentalProposition, _query_path, check_epistemic_candidates

_COPY = re.compile(r"Narrator: ([A-Z][\w-]*)'s last statement (?:repeats|was copied from) ([A-Z][\w-]*)'s last statement\.")
_POLICY = ('Report families describe provenance, not independent witnesses or vote weights. '
    'Repeated/correlated reports never establish a majority, truth, sincerity or another '
    'person private belief. Unknown source relatedness remains unknown. Distinguish a '
    'character reported uncertainty from system missing evidence. Preserve outer negation '
    'and epistemic operator scope; never detach an inner attribution as actual belief.')


@dataclass(frozen=True)
class ReportAssessment:
    scope: object
    query: str
    entries_json: str
    families_json: str
    diagnostics_json: str

    def current(self, core):
        statuses = core.support_statuses()
        entries, families = json.loads(self.entries_json), json.loads(self.families_json)
        for row in entries:
            row['support_status'] = statuses[row['expression_id']]
        for family in families:
            family['support_status'] = statuses[family['claim_id']]
        live = [r for r in entries if r['support_status'] == 'SUPPORT_AVAILABLE']
        groups = {}
        for row in live:
            key = json.dumps([row['holders'], row.get('content')], sort_keys=True)
            groups.setdefault(key, []).append(row)
        conclusions = []
        for rows in groups.values():
            signals = {r['result'] for r in rows}
            direct_uncertain = any(r['result'] == 'SOURCE_REPORTED_UNCERTAIN'
                and r['channel'] == 'SUBJECT_SELF_REPORT' for r in rows)
            status = ('REPORT_CONFLICT' if {'SOURCE_REPORTED_AFFIRM', 'SOURCE_REPORTED_DENY'} <= signals
                else 'CHARACTER_REPORTED_UNCERTAINTY' if direct_uncertain
                else 'OUTER_MODAL_SCOPE_UNRESOLVED' if any(not s.startswith('SOURCE_REPORTED_') for s in signals)
                else 'INDIRECT_REPORTS_ONLY' if all(r['channel'] == 'THIRD_PARTY_REPORT' for r in rows)
                else 'REPORTED_POSITION_NOT_PRIVATE_TRUTH')
            conclusions.append(dict(holders=rows[0]['holders'], content=rows[0].get('content'), status=status,
                signals=sorted(signals), expression_ids=[r['expression_id'] for r in rows],
                private_belief='NOT_ESTABLISHED', world_truth='NOT_ESTABLISHED'))
        return dict(query=self.query, reports=entries, provenance_families=families,
            assessment=conclusions, missing_evidence='SYSTEM_INSUFFICIENT' if not live else 'SEE_REPORT_CHANNELS',
            report_occurrences=len(live), current_provenance_family_count=sum(
                f['support_status'] == 'SUPPORT_AVAILABLE' for f in families),
            independent_support_count=None, independence='NOT_ESTABLISHED',
            diagnostics=json.loads(self.diagnostics_json), provider_calls=0)

    def messages(self, core, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded context budget required')
        payload = dict(cognition=self.current(core), evidence=core.receipt(self.scope))
        messages = [dict(role='system', content=_POLICY), dict(role='user',
            content=json.dumps(payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('report context budget exceeded')
        return messages


def prepare_reports(workspace, query, *, source_id, observer=None, max_depth=3, max_reports=12):
    """One ordinary source domain, named bounded question, explicit copy cues.

    Query depth bounds queried minds; a third-party reporter is a separate channel.
    No same-name cross-document identity or default source-independence assumption.
    """
    holders = _query_path(query) if isinstance(query, str) and len(query) <= 8000 else ()
    if (not holders or type(max_depth) is not int or not 1 <= max_depth <= 3
            or len(holders) > max_depth or type(max_reports) is not int or not 1 <= max_reports <= 12):
        raise ValueError('bounded named mental-state query required')
    # Generic extraction retains reporting channels before query selection; B01
    # parser includes at most three mental operators plus a reporting wrapper.
    extraction_query = 'Extract explicit reported mental propositions.'
    semantic = workspace.prepare_semantic(extraction_query, source_ids=(source_id,), observer=observer)
    bundle = check_epistemic_candidates(workspace.core, extraction_query, semantic, max_depth=max_depth + 1)
    core = workspace.core
    diagnostics = list(bundle.diagnostics)
    records = [r for r in bundle.records if isinstance(r.tree, MentalProposition)]
    if len(records) > max_reports:
        raise ValueError('report expansion budget exceeded')
    entries, by_expression = [], {}
    for record in records:
        indirect = record.tree.attitude == Attitude.REPORT
        path = ((record.speaker,) + holders) if indirect else holders
        projected = replace(bundle, records=(record,)).project(core, path)
        for row in projected:
            leaf = record.tree
            for _ in path[:-1]:
                leaf = leaf.content
            if isinstance(leaf, MentalProposition):
                row = dict(row, content=leaf.content.as_dict() if isinstance(leaf.content, MentalProposition) else leaf.content)
            if row.get('attitude') not in (None, Attitude.BELIEF.value):
                diagnostics.append(dict(expression_id=record.expression_id, reason='NON_BELIEF_OPERATOR'))
                continue
            if isinstance(row.get('content'), dict):
                diagnostics.append(dict(expression_id=record.expression_id, reason='QUERY_ENDS_BEFORE_NESTED_LEAF'))
                continue
            entry = dict(row, holders=list(holders), reporter=record.speaker,
                channel='THIRD_PARTY_REPORT' if indirect else 'SUBJECT_SELF_REPORT' if len(holders) == 1 else 'REPORTED_NESTED_ATTRIBUTION')
            entries.append(entry)
            by_expression[record.expression_id] = entry
    # Hidden sources never reach raw parsing or cue interpretation.
    text = workspace._documents[source_id][0] if source_id in bundle.scope.source_ids else ''
    lines = text.splitlines(keepends=True)
    if len(lines) > 40:
        raise ValueError('source-line budget exceeded')
    spans = {r.expression_id: core.spans[core.claims[r.expression_id].content['source_span_id']] for r in records}
    # Resolve literal last speech before filtering its mental content. A later
    # nonmental or unsupported utterance must not revive an older parsed belief.
    by_span = {core.claims[r.expression_id].content['source_span_id']: r for r in records
        if core.claims[r.expression_id].content['channel'] == 'PUBLIC_EXPRESSION'}
    statements, cue_events = [], {}
    status = core.support_statuses()
    for key in semantic.candidate_ids:
        content = core.claims[key].content
        if content.get('kind') != 'event':
            continue
        row = content['proposal']
        span = core.spans[content['source_span_id']]
        if (status[key] == 'SUPPORT_AVAILABLE'
                and content['validation']['semantic_support'] == 'BOUNDED_LITERAL_FORM'
                and row.get('event_kind') == 'SPEECH_REPORT'
                and row.get('speaker_surface') == 'Narrator'
                and row.get('assertion_scope') == 'SOURCE_REPORT'
                and span.source_id == source_id and span.version == workspace._versions[source_id]):
            cue_events.setdefault((span.start, span.end), set()).add(key)
        if (row.get('event_kind') != 'SPEECH_REPORT' or row.get('assertion_scope') != 'SOURCE_REPORT'
                or row.get('speaker_surface') == 'Narrator'
                or row.get('speaker_candidates') != [row.get('speaker_surface')]):
            continue
        statements.append((span.start, span.end, row['speaker_surface'], span.id))
    statements.sort()

    parent = {r.expression_id: r.expression_id for r in records}
    links = []
    def root(key):
        while parent[key] != key:
            key = parent[key]
        return key
    def join(left, right):
        a, b = root(left), root(right)
        if a != b:
            parent[max(a, b)] = min(a, b)
    # Repeated same-reporter expressions are occurrences of one report position,
    # not evidence of independently acquired support. Every occurrence is kept.
    duplicates = {}
    for record in records:
        key = json.dumps([record.speaker, record.tree.as_dict()], sort_keys=True)
        if key in duplicates:
            join(record.expression_id, duplicates[key])
        else:
            duplicates[key] = record.expression_id
    offset = 0
    for line in lines:
        match = _COPY.fullmatch(line.strip())
        if match:
            # The cue is the complete prepared source-line event, including
            # original trailing spaces/CRLF carriage return, never a text-only
            # match to another occurrence or an unqualified raw-source fallback.
            source_line = line.rstrip('\n')
            candidates = [key for key in cue_events.get((offset, offset + len(source_line)), ())
                if core.spans[core.claims[key].content['source_span_id']].quote == source_line]
            if len(candidates) != 1:
                diagnostics.append(dict(source_id=source_id, start=offset, end=offset + len(source_line),
                    reason='COPY_CUE_WITHOUT_ELIGIBLE_NARRATOR_EVENT' if not candidates
                        else 'COPY_CUE_AMBIGUOUS_PREPARED_EVENTS'))
                offset += len(line)
                continue
            cue_candidate = candidates[0]
            copier, origin = match.groups()
            earlier = [r for r in statements if r[1] <= offset]
            last_left = next((r for r in reversed(earlier) if r[2] == copier), None)
            last_right = next((r for r in reversed(earlier) if r[2] == origin), None)
            left = by_span.get(last_left[3]) if last_left else None
            right = by_span.get(last_right[3]) if last_right else None
            if (left is None or right is None or left == right
                    or spans[right.expression_id].start >= spans[left.expression_id].start):
                raise ValueError('copy cue requires distinct preceding origin and later report')
            # A copy claim remains provenance even if its rendering disagrees;
            # disagreement within a family cannot create extra independent votes.
            begin = offset + line.index(line.strip())
            span = core.add_span(text, source_id=source_id, version=workspace._versions[source_id],
                start=begin, end=begin + len(line.strip()), order=1,
                permitted_observers=workspace._documents[source_id][1])
            workspace._version_spans[source_id].add(span)
            source = core.claim(bundle.scope, ClaimKind.SOURCE_REPORT,
                dict(source_id=source_id, quote=line.strip(), interpretation='EXPLICIT_REPORTED_COPY_RELATION'))
            core.support(source, span)
            link = core.claim(bundle.scope, ClaimKind.SYSTEM_INTERPRETATION,
                dict(relation='REPORTED_SHARED_ORIGIN', copier_expression=left.expression_id,
                    origin_expression=right.expression_id, cue_candidate_id=cue_candidate,
                    independence='NOT_ESTABLISHED'))
            core.support(link, source, cue_candidate, left.expression_id, right.expression_id)
            core.interpret(link, unknown_conditions=('copy_report_accuracy_not_established',))
            join(left.expression_id, right.expression_id)
            links.append((left.expression_id, right.expression_id, link))
        offset += len(line)
    families = []
    selected_roots = {root(key) for key in by_expression}
    for group in sorted(selected_roots):
        members = sorted(key for key in parent if root(key) == group)
        selected = [key for key in members if key in by_expression]
        relation_claims = [claim for left, right, claim in links if root(left) == group]
        family = dict(family_id=identity('report-family', source_id, members),
            all_expression_ids=members, selected_expression_ids=selected,
            relation_claim_ids=relation_claims, report_occurrences=len(selected),
            relatedness='REPORTED_SHARED_ORIGIN' if relation_claims else
                'REPEATED_SAME_REPORTER' if len(members) > 1 else 'UNKNOWN_RELATION_TO_OTHER_REPORTS',
            independent_support_count=None, independence='NOT_ESTABLISHED')
        claim = core.claim(bundle.scope, ClaimKind.SYSTEM_INTERPRETATION, family)
        core.support(claim, *members, *relation_claims)
        core.interpret(claim)
        families.append(dict(family, claim_id=claim))
    return ReportAssessment(bundle.scope, query, json.dumps(entries, sort_keys=True),
        json.dumps(families, sort_keys=True), json.dumps(diagnostics, sort_keys=True))
