"""Bounded nested epistemic objects; reports never collapse into other minds.

PUBLIC_EXPRESSION is the evidence channel. Private belief remains a defeasible
interpretation under an explicit sincerity assumption. Exposure, understanding,
knowledge claims and beliefs are distinct operators, not interchangeable labels.
"""
from dataclasses import asdict, dataclass
from enum import Enum
import json
import re

from .core import ClaimKind, EvidenceCore, Scope, identity
from .semantic import _PRONOUNS


class Attitude(str, Enum):
    BELIEF = 'BELIEF'
    EXPOSURE = 'EXPOSURE_CLAIM'
    UNDERSTANDING = 'UNDERSTANDING_CLAIM'
    KNOWLEDGE = 'KNOWLEDGE_CLAIM'
    REPORT = 'REPORTED_ATTRIBUTION'


@dataclass(frozen=True)
class MentalProposition:
    holder: str
    attitude: Attitude
    polarity: str
    content: object

    def __post_init__(self):
        if (not isinstance(self.holder, str) or not self.holder or len(self.holder) > 100
                or not isinstance(self.attitude, Attitude)
                or self.polarity not in ('AFFIRM', 'DENY', 'UNCERTAIN')
                or not isinstance(self.content, (str, MentalProposition))
                or (isinstance(self.content, str) and not self.content.strip())):
            raise ValueError('explicit holder, modal operator, polarity and content required')

    def as_dict(self):
        return dict(holder=self.holder, attitude=self.attitude.value, polarity=self.polarity,
            content=self.content.as_dict() if isinstance(self.content, MentalProposition) else self.content)

    @property
    def depth(self):
        return 1 + (self.content.depth if isinstance(self.content, MentalProposition) else 0)


_PREDICATE = re.compile(
    r'^(?P<subject>I|[A-Z][\w-]*(?: [A-Z][\w-]*)?)\s+'
    r'(?P<verb>do not believe|does not believe|don\x27t believe|doesn\x27t believe|'
    r'do not think|does not think|am unsure whether|is unsure whether|'
    r'am uncertain whether|is uncertain whether|do not know|does not know|'
    r'do not understand|does not understand|did not hear|did not read|'
    r'believes|believe|thinks|think|knows|know|understands|understand|heard|read)\s+'
    r'(?:that\s+)?(?P<content>.+)$', re.S)


def parse_mental_proposition(text, speaker, *, max_depth=3):
    if type(max_depth) is not int or not 1 <= max_depth <= 4:
        raise ValueError('bounded explicit modal depth required')
    def parse(fragment, remaining):
        match = _PREDICATE.fullmatch(fragment.rstrip('.!?').strip())
        if not match:
            return fragment.rstrip('.!?').strip()
        subject = speaker if match['subject'] == 'I' else match['subject']
        if subject.lower() in _PRONOUNS:
            return fragment.rstrip('.!?').strip()  # unresolved reference, not guessed
        if remaining == 0:
            raise ValueError('modal_depth_exceeded')
        verb = match['verb']
        kind = (Attitude.KNOWLEDGE if 'know' in verb else
                Attitude.UNDERSTANDING if 'understand' in verb else
                Attitude.EXPOSURE if 'hear' in verb or 'heard' in verb or 'read' in verb else Attitude.BELIEF)
        polarity = ('UNCERTAIN' if 'unsure' in verb or 'uncertain' in verb else
                    'DENY' if 'not' in verb or "n't" in verb else 'AFFIRM')
        return MentalProposition(subject, kind, polarity, parse(match['content'], remaining - 1))
    tree = parse(text, max_depth)
    if isinstance(tree, MentalProposition) and tree.holder != speaker:
        if tree.depth == max_depth:
            raise ValueError('modal_depth_exceeded_with_reporter')
        tree = MentalProposition(speaker, Attitude.REPORT, 'AFFIRM', tree)
    return tree


def _query_path(query):
    match = re.fullmatch(r'What does (.+?)[?.]?', query)
    if not match:
        return ()
    rest, names = match[1], []
    pattern = re.compile(r'(?:that )?([A-Z][\w-]*(?: [A-Z][\w-]*)?) '
        r'(?:thinks|think|believes|believe|knows|know|understands|understand|heard)\b\s*')
    while True:
        part = pattern.match(rest)
        if not part:
            break
        names.append(part[1])
        rest = rest[part.end():]
    if len(names) > 4:
        raise ValueError('query modal path exceeds budget')
    return tuple(names)


@dataclass(frozen=True)
class EpistemicRecord:
    source_id: str
    speaker: str
    expression_id: str
    tree: object
    private_interpretation_id: str | None


@dataclass(frozen=True)
class EpistemicBundle:
    scope: Scope
    records: tuple[EpistemicRecord, ...]
    diagnostics: tuple[dict, ...]
    query_path: tuple[str, ...] = ()

    def project(self, core, holders, *, attitude=None):
        if not isinstance(holders, tuple) or not holders or len(holders) > 4:
            raise ValueError('bounded holder path required')
        status = core.support_statuses()
        rows = []
        for record in self.records:
            if status[record.expression_id] != 'SUPPORT_AVAILABLE':
                continue
            node, nodes = record.tree, []
            for holder in holders:
                if not isinstance(node, MentalProposition) or node.holder != holder:
                    break
                nodes.append(node)
                node = node.content
            if len(nodes) != len(holders):
                continue
            leaf = nodes[-1]
            if attitude is not None and leaf.attitude != attitude:
                continue
            chain = [dict(holder=n.holder, attitude=n.attitude.value, polarity=n.polarity) for n in nodes]
            blocker = next((n for n in nodes[:-1] if n.polarity != 'AFFIRM'), None)
            base = dict(source_id=record.source_id, expression_id=record.expression_id,
                holders=list(holders), chain=chain, private_state='NOT_ESTABLISHED', world_truth='NOT_ESTABLISHED')
            if blocker:
                rows.append(dict(base, result='OUTER_ATTRIBUTION_' +
                    ('DENIED' if blocker.polarity == 'DENY' else 'UNCERTAIN'),
                    unprojected_inner_state='NO_INNER_POLARITY_INFERENCE'))
            else:
                nonbelief = any(n.attitude not in (Attitude.BELIEF, Attitude.REPORT) for n in nodes[:-1])
                rows.append(dict(base, result=('NESTED_CONTENT_NOT_BELIEF_ATTRIBUTION' if nonbelief
                    else 'SOURCE_REPORTED_' + leaf.polarity), attitude=leaf.attitude.value,
                    content=leaf.content.as_dict() if isinstance(leaf.content, MentalProposition) else leaf.content))
        return rows

    def compare_attribution(self, core, reporter, subject):
        """A real join of nested attribution and the subject's own expression.

        Matching names only join inside one source identity domain. This compares
        evidence channels, not omniscient private minds or objective world facts.
        """
        attributed = self.project(core, (reporter, subject), attitude=Attitude.BELIEF)
        direct = self.project(core, (subject,), attitude=Attitude.BELIEF)
        results = []
        for left in attributed:
            for right in direct:
                if (left['source_id'] != right['source_id'] or left.get('content') != right.get('content')
                        or not isinstance(left.get('content'), str)
                        or not left['result'].startswith('SOURCE_REPORTED_')):
                    continue
                relation = ('UNRESOLVED_EXPLICIT_UNCERTAINTY' if 'UNCERTAIN' in (left['chain'][-1]['polarity'], right['chain'][-1]['polarity'])
                    else 'CONSISTENT_WITH_SUBJECT_REPORT' if left['result'] == right['result']
                    else 'DIFFERS_FROM_SUBJECT_REPORT')
                result = dict(reporter=reporter, subject=subject, content=left['content'], relation=relation,
                    source_id=left['source_id'], private_belief_truth='NOT_ESTABLISHED')
                claim = core.claim(self.scope, ClaimKind.SYSTEM_INTERPRETATION, result)
                core.support(claim, left['expression_id'], right['expression_id'])
                core.interpret(claim)
                results.append(dict(claim_id=claim, **result))
        return results

    def messages(self, core, query, *, comparisons=None, max_chars=64000):
        status = core.support_statuses()
        if comparisons is None:
            comparisons = (self.compare_attribution(core, *self.query_path)
                           if len(self.query_path) == 2 else ())
            status = core.support_statuses()
        verified_comparisons = []
        for row in comparisons:
            key = row['claim_id']
            if key not in core.claims or core.claims[key].scope != self.scope:
                raise ValueError('comparison outside epistemic scope')
            if status.get(key) == 'SUPPORT_AVAILABLE':
                verified_comparisons.append(dict(claim_id=key, **core.claims[key].content))
        rows = []
        for r in self.records:
            rows.append(dict(source_id=r.source_id, speaker=r.speaker,
                public_expression=core.claims[r.expression_id].content,
                support_status=status[r.expression_id], expression_id=r.expression_id,
                private_interpretation=(dict(claim_id=r.private_interpretation_id,
                    hypothesis=core.claims[r.private_interpretation_id].content,
                    assumptions=list(core.claims[r.private_interpretation_id].scope.assumptions),
                    support_status=status[r.private_interpretation_id]) if r.private_interpretation_id else None)))
        payload = json.dumps(dict(query=query, epistemic_objects=rows, comparisons=verified_comparisons,
            selected_holder_path=list(self.query_path),
            query_projection=self.project(core, self.query_path) if self.query_path else [],
            diagnostics=list(self.diagnostics)), ensure_ascii=False, sort_keys=True)
        if len(payload) > max_chars:
            raise ValueError('epistemic context budget exceeded')
        return [dict(role='system', content='Distinguish public expression, conditional private-belief '
            'interpretation, exposure claims, understanding claims and knowledge claims. A claim of '
            'knowing p is not proof of p. A says p does not establish A privately believes p. '
            'Nested attribution cannot be detached into the inner person actual state. Outer denial '
            'is not inner denial. Sincerity assumptions are not established facts. Preserve source-local '
            'identity, unknowns and challenges; unsupported rows are history, not current support.'),
            dict(role='user', content=payload)]


def prepare_epistemic(workspace, query, *, source_ids, observer=None, max_depth=3):
    semantic = workspace.prepare_semantic(query, source_ids=source_ids, observer=observer)
    return check_epistemic_candidates(workspace.core, query, semantic, max_depth=max_depth)


def check_epistemic_candidates(core, query, semantic, *, max_depth=3):
    """Reuse B01 checks on already grounded candidates, without re-extraction.

    Source access filtering belongs to the original semantic preparation. A
    candidate from another core/scope cannot enter this checked projection.
    """
    from .semantic import SemanticResult
    if (not isinstance(core, EvidenceCore) or not isinstance(query, str) or not query.strip() or len(query)>8000
            or not isinstance(semantic, SemanticResult)
            or type(max_depth) is not int or not 1<=max_depth<=4):
        raise ValueError('bounded grounded epistemic input required')
    if any(key not in core.claims or core.claims[key].scope != semantic.scope
            for key in semantic.candidate_ids + semantic.root_ids):
        raise ValueError('epistemic candidates outside their grounded core or scope')
    path = _query_path(query)
    records, diagnostics = [], []
    status = core.support_statuses()
    for key in semantic.candidate_ids:
        content = core.claims[key].content
        if content.get('kind') != 'event' or status[key] != 'SUPPORT_AVAILABLE':
            continue
        row = content['proposal']
        if (content['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM'
                or row.get('assertion_scope') != 'SOURCE_REPORT'
                or row.get('speaker_candidates') != [row.get('speaker_surface')]):
            diagnostics.append(dict(candidate_id=key, reason='unresolved_speaker_or_semantics'))
            continue
        speaker = row['speaker_surface']
        narrator_report = row.get('event_kind') == 'NARRATOR_MENTAL_REPORT'
        if path and speaker not in (path[0], path[-1]) and not narrator_report:
            continue
        try:
            tree = parse_mental_proposition(row['utterance'], speaker, max_depth=max_depth)
        except ValueError as exc:
            diagnostics.append(dict(candidate_id=key, reason=str(exc)))
            continue
        span = core.spans[content['source_span_id']]
        expression = core.claim(semantic.scope, ClaimKind.SYSTEM_INTERPRETATION,
            dict(channel='SOURCE_NARRATOR_ATTRIBUTION' if narrator_report else 'PUBLIC_EXPRESSION', speaker=speaker, source_id=span.source_id,
                original_quote=span.quote, source_span_id=span.id,
                expressed_content=tree.as_dict() if isinstance(tree, MentalProposition) else tree,
                semantics='SOURCE_REPORTED_ATTRIBUTION_NOT_SUBJECT_EXPRESSION_OR_PRIVATE_TRUTH' if narrator_report else 'REPORTED_EXPRESSION_NOT_ACTUAL_PRIVATE_STATE'))
        core.support(expression, key)
        core.interpret(expression)
        private = None
        if not narrator_report and isinstance(tree, MentalProposition) and tree.attitude == Attitude.BELIEF and tree.holder == speaker:
            assumption = identity('unverified-sincerity', expression)
            scope = Scope(**dict(asdict(semantic.scope), actor=speaker,
                assumptions=semantic.scope.assumptions + (assumption,)))
            private = core.project_claim(expression, scope, ClaimKind.SYSTEM_INTERPRETATION,
                dict(channel='PRIVATE_BELIEF_HYPOTHESIS', content=tree.as_dict(),
                    condition='IF_THIS_EXPRESSION_SINCERELY_REPORTS_THE_SPEAKER_BELIEF',
                    epistemic_status='DEFEASIBLE_NOT_CONFIRMED'))
            core.support(private, span.id)
            core.interpret(private, unknown_conditions=('speaker_sincerity_not_established',))
        records.append(EpistemicRecord(span.source_id, speaker, expression, tree, private))
    return EpistemicBundle(semantic.scope, tuple(records), tuple(diagnostics), path)
