"""Bounded social-act and expectation checks with source and access boundaries."""
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
import re

from hcl.v04.model import EventRecord
from hcl.v06.perspective import event_accessible_to


class SocialActKind(str, Enum):
    PROPOSAL = 'PROPOSAL'
    REQUEST = 'REQUEST'
    ACCEPTANCE = 'ACCEPTANCE'
    REFUSAL = 'REFUSAL'
    CONDITIONAL_COMMITMENT = 'CONDITIONAL_COMMITMENT'
    WITHDRAWAL = 'WITHDRAWAL'


@dataclass(frozen=True)
class SocialCondition:
    key: str
    text: str
    source_event_id: str


@dataclass(frozen=True)
class SocialAct:
    act_id: str
    kind: SocialActKind
    speaker: str
    addressee: str | None
    content: str
    quote: str
    source_event_id: str
    event_time: str
    conditions: tuple[SocialCondition, ...] = ()
    refers_to: str | None = None


@dataclass(frozen=True)
class ParticipantInterpretation:
    interpretation_id: str
    participant: str
    act_id: str
    expected_content: str
    expected_conditions: tuple[str, ...]
    quote: str
    source_event_id: str
    formed_time: str


@dataclass(frozen=True)
class AccessStatement:
    statement_id: str
    participant: str
    event_id: str
    source_event_id: str
    had_access: bool


def _time(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError('timezone-aware social event time required')
    return parsed


def _contains(source, span):
    return isinstance(span, str) and bool(span.strip()) and span in source


def _validate(acts, interpretations, access_statements, events):
    if len(events) > 32 or len(acts) > 6 or len(access_statements) > 8:
        raise ValueError('CG-02 source/act/access bounds exceeded')
    if len({e.event_id for e in events}) != len(events):
        raise ValueError('duplicate social source event')
    if len({a.act_id for a in acts}) != len(acts):
        raise ValueError('duplicate social act')
    if len({i.interpretation_id for i in interpretations}) != len(interpretations):
        raise ValueError('duplicate interpretation')
    if len({s.statement_id for s in access_statements}) != len(access_statements):
        raise ValueError('duplicate access statement')
    if sum(a.kind == SocialActKind.WITHDRAWAL for a in acts) > 2:
        raise ValueError('at most two withdrawals')
    event_by_id = {e.event_id: e for e in events}
    act_by_id = {a.act_id: a for a in acts}
    actors = set()
    for act in acts:
        if not isinstance(act.kind, SocialActKind):
            raise ValueError('unsupported social act kind')
        source = event_by_id.get(act.source_event_id)
        if source is None or source.actor_id != act.speaker or _time(source.valid_time) != _time(act.event_time):
            raise ValueError('social act speaker/source/time mismatch')
        if not _contains(source.raw_text, act.quote) or not _contains(act.quote, act.content):
            raise ValueError('social act content must be an exact source span')
        if act.addressee and act.addressee.lower() not in source.raw_text.lower():
            raise ValueError('social addressee lacks source mention')
        if len(act.conditions) > 3 or len({c.key for c in act.conditions}) != len(act.conditions):
            raise ValueError('social condition bound or duplicate key')
        if act.kind == SocialActKind.CONDITIONAL_COMMITMENT and not act.conditions:
            raise ValueError('conditional commitment requires an explicit condition')
        for condition in act.conditions:
            condition_source = event_by_id.get(condition.source_event_id)
            if (condition_source is None or condition_source.actor_id != act.speaker or
                not _contains(condition_source.raw_text, condition.text) or
                condition.key != condition.text or
                _time(condition_source.valid_time) > _time(act.event_time)):
                raise ValueError('condition lacks speaker/source/time anchor')
        if act.kind in (SocialActKind.ACCEPTANCE, SocialActKind.REFUSAL, SocialActKind.WITHDRAWAL):
            if act.refers_to is not None:
                prior = act_by_id.get(act.refers_to)
                if prior is None or _time(prior.event_time) >= _time(act.event_time):
                    raise ValueError('social reference must precede response')
                if (act.kind in (SocialActKind.ACCEPTANCE, SocialActKind.REFUSAL) and
                    prior.kind not in (SocialActKind.PROPOSAL, SocialActKind.REQUEST,
                                       SocialActKind.CONDITIONAL_COMMITMENT)):
                    raise ValueError('acceptance/refusal requires a prior social offer or request')
                if act.kind == SocialActKind.WITHDRAWAL and prior.speaker != act.speaker:
                    raise ValueError('speaker may withdraw only own act')
        elif act.refers_to is not None:
            raise ValueError('only response/withdrawal can reference a prior act')
        actors.update((act.speaker, act.addressee))
    per_act = {}
    for interpretation in interpretations:
        source = event_by_id.get(interpretation.source_event_id)
        act = act_by_id.get(interpretation.act_id)
        if act is None or source is None or source.actor_id != interpretation.participant:
            raise ValueError('interpretation lacks participant/source act')
        if (_time(source.valid_time) != _time(interpretation.formed_time) or
            _time(source.valid_time) < _time(act.event_time) or
            not _contains(source.raw_text, interpretation.quote) or
            not _contains(interpretation.quote, interpretation.expected_content)):
            raise ValueError('interpretation content/time lacks source anchor')
        if len(set(interpretation.expected_conditions)) != len(interpretation.expected_conditions):
            raise ValueError('duplicate expected condition')
        if any(not _contains(interpretation.quote, condition)
               for condition in interpretation.expected_conditions):
            raise ValueError('expected condition must be explicit in participant report')
        per_act[interpretation.act_id] = per_act.get(interpretation.act_id, 0) + 1
        actors.add(interpretation.participant)
    if len(interpretations) > 12 or any(count > 2 for count in per_act.values()):
        raise ValueError('at most two interpretations per act')
    for statement in access_statements:
        source = event_by_id.get(statement.source_event_id)
        if statement.event_id not in event_by_id or source is None or type(statement.had_access) is not bool:
            raise ValueError('access statement lacks source/event')
        if _time(source.valid_time) < _time(event_by_id[statement.event_id].valid_time):
            raise ValueError('access report predates event')
        if source.actor_id is not None or statement.participant.lower() not in source.raw_text.lower():
            raise ValueError('access assertion requires explicit narrator source naming participant')
        if statement.had_access and (not re.search(
            r'\b(?:heard|received|learned|knew|was told)\b', source.raw_text, re.I,
        ) or re.search(r'\b(?:did not|never|not)\s+(?:hear|receive|learn|know|heard|received|learned|knew)\b|\bwas not told\b',
            source.raw_text, re.I)):
            raise ValueError('positive access requires explicit unnegated report')
        if not statement.had_access and not re.search(
            r'\b(?:did not|never|not)\s+(?:hear|receive|learn|know)|\bwas not told\b',
            source.raw_text, re.I,
        ):
            raise ValueError('negative access requires explicit denial')
        actors.add(statement.participant)
    if len(actors - {None}) > 4:
        raise ValueError('at most four social actors')
    return event_by_id, act_by_id


def _access(event, participant, statements, event_by_id, visible):
    if event_accessible_to(event, participant):
        return 'DIRECT_ACCESS'
    for statement in statements:
        if statement.participant != participant or statement.event_id != event.event_id:
            continue
        if not visible(event_by_id[statement.source_event_id]):
            continue
        if statement.had_access:
            return 'REPORTED_ACCESS'
        return 'EXPLICIT_NO_ACCESS'
    return 'UNKNOWN_ACCESS'


def check_social_exchange(
    acts: tuple[SocialAct, ...],
    interpretations: tuple[ParticipantInterpretation, ...],
    access_statements: tuple[AccessStatement, ...],
    events: tuple[EventRecord, ...],
    *,
    mode: str = 'READER_ANALYSIS',
    target_actor: str | None = None,
    observer_actor: str | None = None,
    event_time: str | None = None,
    knowledge_cutoff: str | None = None,
) -> dict:
    """Compare reported expectations without asserting private understanding or blame."""
    if mode not in ('READER_ANALYSIS', 'CHARACTER_PERSPECTIVE', 'OBSERVER_ABOUT_TARGET'):
        raise ValueError('invalid perspective mode')
    if mode == 'CHARACTER_PERSPECTIVE' and not target_actor:
        raise ValueError('character view requires target')
    if mode == 'OBSERVER_ABOUT_TARGET' and not (target_actor and observer_actor):
        raise ValueError('observer view requires observer and target')
    event_by_id, act_by_id = _validate(acts, interpretations, access_statements, events)
    viewer = (target_actor if mode == 'CHARACTER_PERSPECTIVE' else
              observer_actor if mode == 'OBSERVER_ABOUT_TARGET' else None)

    def visible(event):
        if event_time and _time(event.valid_time) > _time(event_time):
            return False
        if knowledge_cutoff and _time(event.recorded_at) > _time(knowledge_cutoff):
            return False
        return viewer is None or event_accessible_to(event, viewer)

    act_rows = []
    for act in acts:
        source = event_by_id[act.source_event_id]
        if not visible(source):
            continue
        visible_conditions = []
        for condition in act.conditions:
            condition_source = event_by_id[condition.source_event_id]
            if visible(condition_source):
                visible_conditions.append(asdict(condition))
        reference = act_by_id.get(act.refers_to)
        reference_status = ('NOT_APPLICABLE' if act.kind not in (
            SocialActKind.ACCEPTANCE, SocialActKind.REFUSAL, SocialActKind.WITHDRAWAL) else
            'UNRESOLVED_REFERENCE' if reference is None else
            'VISIBLE_PRIOR_ACT' if visible(event_by_id[reference.source_event_id]) else
            'UNRESOLVED_REFERENCE')
        act_rows.append({
            'act_id': act.act_id, 'kind': act.kind.value, 'speaker': act.speaker,
            'addressee': act.addressee, 'content': act.content,
            'source_event_id': act.source_event_id, 'event_time': act.event_time,
            'condition_count_known_to_reader': len(act.conditions) if viewer is None else None,
            'conditions_visible_in_view': visible_conditions,
            'condition_scope_complete': len(visible_conditions) == len(act.conditions)
                if viewer is None else None,
            'reference_status': reference_status,
            'refers_to': act.refers_to if reference_status == 'VISIBLE_PRIOR_ACT' else None,
        })

    comparisons = []
    for interpretation in interpretations:
        act = act_by_id[interpretation.act_id]
        act_source = event_by_id[act.source_event_id]
        source = event_by_id[interpretation.source_event_id]
        if not visible(source) or not visible(act_source):
            continue
        if mode != 'READER_ANALYSIS' and interpretation.participant != target_actor:
            # An observer may quote what the target reported, but cannot import
            # another participant's private expectation into the target view.
            continue
        actual = {c.key for c in act.conditions}
        expected = set(interpretation.expected_conditions)
        available_conditions = {
            c.key: _access(event_by_id[c.source_event_id], interpretation.participant,
                           access_statements, event_by_id, visible)
            for c in act.conditions
        }
        if viewer is not None:
            # Do not reveal reader-only condition identities or access facts.
            available_conditions = {key: state for key, state in available_conditions.items()
                if any(c.key == key and visible(event_by_id[c.source_event_id]) for c in act.conditions)}
            actual = set(available_conditions)
        omitted = sorted(actual - expected)
        added = sorted(expected - actual)
        relation = ('STRONGER_THAN_SOURCE' if omitted and not added else
                    'WEAKER_THAN_SOURCE' if added and not omitted else
                    'MIXED_OR_UNRESOLVED' if added and omitted else 'COMPATIBLE')
        withdrawals = [later for later in acts if
            later.kind == SocialActKind.WITHDRAWAL and later.refers_to == act.act_id and
            visible(event_by_id[later.source_event_id])]
        withdrawal_order = ('NO_VISIBLE_WITHDRAWAL' if not withdrawals else
            'BEFORE_REPORTED_EXPECTATION' if any(_time(w.event_time) <=
                _time(interpretation.formed_time) for w in withdrawals) else
            'AFTER_REPORTED_EXPECTATION')
        factors = []
        if omitted:
            factors.append('REPORTED_EXPECTATION_OMITS_SOURCE_CONDITION')
        if added:
            factors.append('REPORTED_EXPECTATION_ADDS_UNSUPPORTED_CONDITION')
        if any(state == 'EXPLICIT_NO_ACCESS' for state in available_conditions.values()):
            factors.append('EXPLICIT_SOURCE_SAYS_CONDITION_NOT_ACCESSED')
        elif any(state == 'UNKNOWN_ACCESS' for state in available_conditions.values()):
            factors.append('CONDITION_ACCESS_UNRESOLVED')
        if withdrawal_order == 'AFTER_REPORTED_EXPECTATION':
            factors.append('WITHDRAWAL_AFTER_REPORTED_EXPECTATION')
        comparisons.append({
            'interpretation_id': interpretation.interpretation_id,
            'act_id': act.act_id, 'participant': interpretation.participant,
            'source_event_id': interpretation.source_event_id,
            'relation': relation, 'omitted_condition_keys': omitted,
            'added_condition_keys': added, 'condition_access': available_conditions,
            'content_relation': ('EXACT_TEXT' if interpretation.expected_content == act.content
                else 'PARAPHRASE_NOT_VERIFIED'),
            'withdrawal_order': withdrawal_order,
            'explanation_factors': factors,
            'caution': 'reported expectation and source access do not prove private understanding, deception, betrayal, or blame',
        })
    pairwise = []
    by_act = {}
    for row in comparisons:
        by_act.setdefault(row['act_id'], []).append(row)
    for act_id, rows in by_act.items():
        for left_index, left in enumerate(rows):
            for right in rows[left_index + 1:]:
                if left['participant'] == right['participant']:
                    continue
                left_expected = next(i for i in interpretations
                    if i.interpretation_id == left['interpretation_id'])
                right_expected = next(i for i in interpretations
                    if i.interpretation_id == right['interpretation_id'])
                if (left_expected.expected_content != right_expected.expected_content):
                    relation = 'CONTENT_COMPATIBILITY_UNRESOLVED'
                elif set(left_expected.expected_conditions) == set(right_expected.expected_conditions):
                    relation = 'COMPATIBLE_REPORTED_EXPECTATIONS'
                elif set(left_expected.expected_conditions) < set(right_expected.expected_conditions):
                    relation = 'LEFT_STRONGER_THAN_RIGHT'
                elif set(right_expected.expected_conditions) < set(left_expected.expected_conditions):
                    relation = 'RIGHT_STRONGER_THAN_LEFT'
                else:
                    relation = 'MIXED_OR_UNRESOLVED'
                pairwise.append({'act_id': act_id,
                    'left_interpretation_id': left['interpretation_id'],
                    'right_interpretation_id': right['interpretation_id'],
                    'relation': relation})
    return {
        'acts': act_rows,
        'expectation_comparisons': comparisons,
        'pairwise_expectations': pairwise,
        'checked_act_count': len(act_rows),
        'checked_expectation_count': len(comparisons),
        'scope': mode,
        'unsupported_inferences': [
            'hearing implies understanding', 'omission implies deception',
            'expectation mismatch implies promise-breaking or blame',
            'social act implies trust or relationship status',
        ],
    }
