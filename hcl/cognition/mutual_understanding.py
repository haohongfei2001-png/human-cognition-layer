"""Finite acknowledged interpretation chains, never infinite common knowledge."""
from dataclasses import dataclass
import json
import re

from .communication import CommunicationScene
from .core import ClaimKind
from .epistemic import MentalProposition, parse_mental_proposition

_NAME = r'[A-Z][\w-]*'
_QUERY = re.compile(rf'Do (?P<speaker>{_NAME}) and (?P<recipient>{_NAME}) share an acknowledged understanding that (?P<content>[^?]+)\?')
_MEAN = re.compile(r'I mean that (?P<content>.+)')
_REVISE = re.compile(r'I revise my meaning from (?P<old>.+?) to (?P<new>.+)')
_UNDERSTAND = re.compile(rf'I (?P<verb>understand|do not understand|am unsure whether I understand) (?P<speaker>{_NAME}) to mean that (?P<content>.+)')
_CONFIRM = re.compile(rf"I confirm (?P<recipient>{_NAME})'s understanding that (?P<content>.+)")
_POLICY = ('A finite source-reported acknowledgment chain is not private comprehension '
    'or infinite common knowledge. Exposure, interpretation report, speaker confirmation '
    'and confirmation receipt remain separate. Later receipt does not backfill earlier '
    'understanding. A clarification can replace the speaker\'s meaning while old '
    'acknowledgments remain historical; it does not automatically update the recipient '
    'or restore trust. Reported higher-order beliefs remain attributed, not detached truth.')


@dataclass(frozen=True)
class MutualUnderstanding:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded acknowledgment context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('acknowledgment source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('acknowledgment support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('acknowledgment context budget exceeded')
        return messages


def prepare_mutual_understanding(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not match or match['speaker'] == match['recipient'] or len(match['content']) > 250:
        raise ValueError('bounded distinct participants and interpretation question required')
    speaker, recipient, target = match['speaker'], match['recipient'], match['content']
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, rows = workspace.core, []
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    original = workspace._documents[source_id][0] if versions else ''
    for candidate in semantic.candidate_ids:
        c = core.claims[candidate].content
        if c['kind'] != 'event' or c['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        row, span = c['proposal'], core.spans[c['source_span_id']]
        if row['assertion_scope'] != 'SOURCE_REPORT':
            continue
        narrator = row['speaker_surface'] == 'Narrator' and span.quote.startswith('Narrator:')
        if not narrator and row['speaker_candidates'] != [row['speaker_surface']]:
            continue
        rows.append(dict(line=original[:span.start].count('\n') + 1, candidate=candidate,
            speaker=row['speaker_surface'], body=row['utterance'].rstrip('.!?'), quote=span.quote))
    rows.sort(key=lambda r: r['line'])
    if len(rows) > 20:
        raise ValueError('acknowledgment source budget exceeded')
    scene = CommunicationScene(original, source_id=source_id) if original else None
    def receipt(actor, line, cutoff):
        view = scene.view(actor, through_line=cutoff)
        audit = next(a for a in view.access_audit if a['statement_line'] == line)
        return dict(status=audit['status'], received=audit['content_transmitted'])
    current, historical, interpretations, confirmations, diagnostics, nested, doubts = None, [], [], [], [], [], []
    for row in rows:
        who, body = row['speaker'], row['body']
        if who in (speaker, recipient):
            try:
                tree = parse_mental_proposition(body, who)
                if isinstance(tree, MentalProposition) and tree.depth > 1:
                    nested.append(dict(source_claim_id=row['candidate'], public_expression=tree.as_dict(), private_state='NOT_ESTABLISHED'))
            except ValueError:
                diagnostics.append(dict(source_claim_id=row['candidate'], status='MODAL_DEPTH_EXCEEDED'))
        meaning, revision = _MEAN.fullmatch(body), _REVISE.fullmatch(body)
        understand, confirm = _UNDERSTAND.fullmatch(body), _CONFIRM.fullmatch(body)
        if who == speaker and meaning:
            if current is not None:
                raise ValueError('multiple unlinked meaning episodes; use an explicit revision or narrow source')
            current = dict(row, content=meaning['content'])
        elif who == speaker and revision:
            if current is None or current['content'] != revision['old']:
                diagnostics.append(dict(source_claim_id=row['candidate'], status='REVISION_WITHOUT_MATCHING_PRIOR_MEANING'))
                continue
            historical.append(current)
            current = dict(row, content=revision['new'], revises_claim_id=current['candidate'])
        elif who == recipient and understand and understand['speaker'] == speaker:
            if understand['verb'] != 'understand':
                doubts.append(dict(row, content=understand['content'], kind=understand['verb']))
                continue
            origin = current if current and current['content'] == understand['content'] else None
            interpretations.append(dict(row, content=understand['content'], origin=origin,
                original_receipt=receipt(recipient, origin['line'], row['line']) if origin else None))
        elif who == speaker and confirm and confirm['recipient'] == recipient:
            candidates = [i for i in interpretations if i['content'] == confirm['content'] and i['origin']
                and current and i['origin']['candidate'] == current['candidate']]
            if len(candidates) != 1:
                diagnostics.append(dict(source_claim_id=row['candidate'], status='CONFIRMATION_REFERENCE_UNRESOLVED'))
                continue
            interpretation = candidates[0]
            confirmations.append(dict(row, content=confirm['content'], interpretation=interpretation,
                interpretation_receipt=receipt(speaker, interpretation['line'], row['line'])))
    chains, claims = [], []
    for confirmation in confirmations:
        interpretation = confirmation['interpretation']
        origin = interpretation['origin']
        delivered = receipt(recipient, confirmation['line'], len(scene.lines))
        links = [interpretation['original_receipt'], confirmation['interpretation_receipt'], delivered]
        challenged = any(d['content'] == confirmation['content'] for d in doubts)
        state = ('SUPERSEDED_MEANING_HISTORICAL_ACKNOWLEDGMENT' if not current or origin['candidate'] != current['candidate'] else
            'EXPLICIT_UNCERTAINTY_OR_CONFLICT' if challenged else
            'BOUNDED_MUTUALLY_ACKNOWLEDGED' if all(link['received'] for link in links) else
            'ACKNOWLEDGMENT_DELIVERY_INCOMPLETE')
        item = dict(content=confirmation['content'], status=state, original_quote=origin['quote'],
            interpretation_quote=interpretation['quote'], confirmation_quote=confirmation['quote'],
            original_receipt_at_interpretation=links[0], interpretation_receipt_at_confirmation=links[1],
            confirmation_receipt_current=links[2], common_knowledge='NOT_ESTABLISHED', actual_understanding='NOT_ESTABLISHED')
        claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='FINITE_ACKNOWLEDGMENT_CHAIN', **item))
        core.support(claim, *(r['candidate'] for r in rows))
        claims.append(claim)
        chains.append(dict(item, claim_id=claim))
    matching = [c for c in chains if c['content'] == target]
    status = ('BOUNDED_MUTUALLY_ACKNOWLEDGED' if any(c['status'] == 'BOUNDED_MUTUALLY_ACKNOWLEDGED' for c in matching) else
        'EXPLICIT_UNCERTAINTY_OR_CONFLICT' if any(d['content'] == target for d in doubts) else
        'SUPERSEDED_MEANING' if current and current['content'] != target and any(h['content'] == target for h in historical) else
        'ACKNOWLEDGMENT_DELIVERY_INCOMPLETE' if matching else 'NO_COMPLETE_ACKNOWLEDGMENT_CHAIN')
    payload = dict(query=query, original_source=original, status=status, current_meaning=current,
        historical_meanings=historical, interpretation_reports=interpretations, doubts=doubts,
        acknowledgment_chains=chains, reported_higher_order=nested, diagnostics=diagnostics,
        actual_comprehension='NOT_ESTABLISHED', infinite_common_knowledge='NOT_INFERRED',
        trust_restoration='NOT_INFERRED', temporal_assumption='SOURCE_ORDER_NOT_VERIFIED_CHRONOLOGY', policy=_POLICY)
    if rows:
        final = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='MUTUAL_UNDERSTANDING_SUMMARY', status=status, target=target))
        core.support(final, *(r['candidate'] for r in rows), *claims)
        claims.append(final)
        payload['dependency_claim_id'] = final
    return MutualUnderstanding(versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
