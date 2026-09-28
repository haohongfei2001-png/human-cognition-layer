"""Source-scoped responsibility factors and conditional premise checks.

The checker assesses explicit claims, never private truth or moral desert.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import re

from hcl.v04.model import EventRecord
from hcl.v06.perspective import event_accessible_to, viewer_can_establish_target_access, SYSTEM_VIEWER


def _label(value, name, limit=256):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'bounded {name} required')


def _time(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as exc:
        raise ValueError('timezone-aware factor time required') from exc
    if stamp.utcoffset() is None:
        raise ValueError('timezone-aware factor time required')
    return stamp


class ResponsibilityFactor(str, Enum):
    CAUSAL_CONTRIBUTION = 'CAUSAL_CONTRIBUTION'
    KNOWLEDGE = 'KNOWLEDGE'
    FORESEEABILITY = 'FORESEEABILITY'
    CONTROL = 'CONTROL'
    STATED_INTENTION = 'STATED_INTENTION'


class ClaimAuthority(str, Enum):
    EXPLICIT_NARRATOR = 'EXPLICIT_NARRATOR'
    DIRECT_SELF_REPORT = 'DIRECT_SELF_REPORT'
    THIRD_PARTY_ATTRIBUTION = 'THIRD_PARTY_ATTRIBUTION'


@dataclass(frozen=True)
class FactorRequirement:
    factor: ResponsibilityFactor
    value: bool

    def __post_init__(self):
        if not isinstance(self.factor, ResponsibilityFactor) or type(self.value) is not bool:
            raise ValueError('typed factor requirement required')


@dataclass(frozen=True)
class FactorClaim:
    claim_id: str
    factor: ResponsibilityFactor
    actor_id: str
    action_event_id: str
    source_event_id: str
    quote: str
    about_time: str
    value: bool
    authority: ClaimAuthority

    def __post_init__(self):
        for name in ('claim_id', 'actor_id', 'action_event_id', 'source_event_id'):
            _label(getattr(self, name), name, 128)
        _label(self.quote, 'exact factor quote', 2000)
        _time(self.about_time)
        if (not isinstance(self.factor, ResponsibilityFactor) or
            not isinstance(self.authority, ClaimAuthority) or type(self.value) is not bool):
            raise ValueError('typed factor claim required')


@dataclass(frozen=True)
class NormativePremise:
    premise_id: str
    text: str
    basis_event_ids: tuple[str, ...]
    requirements: tuple[FactorRequirement, ...] = ()

    def __post_init__(self):
        _label(self.premise_id, 'premise ID', 128)
        _label(self.text, 'premise text', 1000)
        if (not isinstance(self.basis_event_ids, tuple) or
            not 1 <= len(self.basis_event_ids) <= 24 or
            len(set(self.basis_event_ids)) != len(self.basis_event_ids)):
            raise ValueError('premise requires one to 24 distinct source IDs')
        for event_id in self.basis_event_ids:
            _label(event_id, 'premise source ID', 128)
        if (not isinstance(self.requirements, tuple) or len(self.requirements) > 5 or
            not all(isinstance(r, FactorRequirement) for r in self.requirements) or
            len({r.factor for r in self.requirements}) != len(self.requirements)):
            raise ValueError('at most five distinct typed factor requirements')


@dataclass(frozen=True)
class NarrativePremise:
    """Caller rule for a narrative; the parser binds it to exact source lines."""
    premise_id: str
    text: str
    requirements: tuple[FactorRequirement, ...]

    def __post_init__(self):
        _label(self.premise_id, 'premise ID', 128)
        _label(self.text, 'premise text', 1000)
        if (not isinstance(self.requirements, tuple) or
            not 1 <= len(self.requirements) <= 5 or
            not all(isinstance(r, FactorRequirement) for r in self.requirements) or
            len({r.factor for r in self.requirements}) != len(self.requirements)):
            raise ValueError('one to five distinct structured narrative requirements required')


@dataclass(frozen=True)
class ResponsibilityCase:
    actor_ids: tuple[str, ...]
    action_event_id: str
    outcome_event_id: str
    premises: tuple[NormativePremise, ...]
    claims: tuple[FactorClaim, ...] = ()

    def __post_init__(self):
        if (not isinstance(self.actor_ids, tuple) or
            not 1 <= len(self.actor_ids) <= 4 or
            len(set(self.actor_ids)) != len(self.actor_ids)):
            raise ValueError('one to four distinct actors required')
        for actor_id in self.actor_ids:
            _label(actor_id, 'actor ID', 128)
        _label(self.action_event_id, 'action event ID', 128)
        _label(self.outcome_event_id, 'outcome event ID', 128)
        if self.action_event_id == self.outcome_event_id:
            raise ValueError('action and outcome need distinct source events')
        if (not isinstance(self.premises, tuple) or
            not 1 <= len(self.premises) <= 3 or
            not all(isinstance(p, NormativePremise) for p in self.premises) or
            len({p.premise_id for p in self.premises}) != len(self.premises)):
            raise ValueError('one to three distinct typed normative premises required')
        if (not isinstance(self.claims, tuple) or len(self.claims) > 20 or
            not all(isinstance(c, FactorClaim) for c in self.claims) or
            len({c.claim_id for c in self.claims}) != len(self.claims)):
            raise ValueError('at most 20 distinct typed factor claims')
        if any(c.actor_id not in self.actor_ids or c.action_event_id != self.action_event_id
               for c in self.claims):
            raise ValueError('factor claim must bind declared actor and focal action')


_FACTOR_PATTERNS = {
    ResponsibilityFactor.CAUSAL_CONTRIBUTION: r'\b(caus(?:e|ed|es|ing)|led to|because of|contribut(?:e|ed|ion))\b|导致|造成|促成',
    ResponsibilityFactor.KNOWLEDGE: r'\b(knew|know|aware|learned|ignorant|unaware)\b|知道|知晓|不知',
    ResponsibilityFactor.FORESEEABILITY: r'\b(foresaw|foresee|predict(?:ed)?|expect(?:ed)?|anticipat(?:e|ed)|unforeseeable)\b|预见|预料|预计',
    ResponsibilityFactor.CONTROL: r"\b(control(?:led)?|could(?: not|n't)? (?:have )?(?:stop(?:ped)?|prevent(?:ed)?|avoid(?:ed)?)|able to (?:stop|prevent|avoid)|unable to (?:stop|prevent|avoid))\b|控制|阻止|避免",
    ResponsibilityFactor.STATED_INTENTION: r'\b(intend(?:ed)?|plan(?:ned)?|meant to|aim(?:ed)? to)\b|打算|意图|计划',
}
_RETROSPECTIVE = re.compile(r'\b(at the time|before the action|at the moment of the action)\b|当时|事前', re.I)
_NEGATIVE = re.compile(r'\b(did not|didn.t|could not|couldn.t|was not|wasn.t|unable to|unaware|unforeseeable|never|not)\b|不知道|无法|不能|没有|未能|无意', re.I)
_LATER_LEARNING = re.compile(r'\b(later learned|learned .{0,80} after(?:ward| the action)|only learned after)\b|后来才知道|事后才知道', re.I)


def _validate_claim(claim, case, events):
    source = events.get(claim.source_event_id)
    action = events[case.action_event_id]
    outcome = events[case.outcome_event_id]
    if source is None or claim.quote not in source.raw_text:
        raise ValueError('factor quote lacks exact source span')
    if _time(claim.about_time) != _time(action.valid_time):
        raise ValueError('factor claim must refer to focal action time')
    if not re.search(_FACTOR_PATTERNS[claim.factor], claim.quote, re.I):
        raise ValueError('factor quote lacks explicit factor expression')
    if sum(bool(re.search(pattern, claim.quote, re.I))
           for pattern in _FACTOR_PATTERNS.values()) != 1:
        raise ValueError('factor quote has competing factor expressions')
    if claim.value == bool(_NEGATIVE.search(claim.quote)):
        raise ValueError('factor polarity conflicts with exact quote')
    if claim.factor == ResponsibilityFactor.KNOWLEDGE and claim.value and _LATER_LEARNING.search(claim.quote):
        raise ValueError('later learning is not action-time knowledge')
    if claim.authority == ClaimAuthority.EXPLICIT_NARRATOR:
        if source.actor_id is not None or claim.actor_id.lower() not in claim.quote.lower():
            raise ValueError('narrator factor attribution invalid')
    elif claim.authority == ClaimAuthority.DIRECT_SELF_REPORT:
        if source.actor_id != claim.actor_id:
            raise ValueError('self report actor mismatch')
    elif source.actor_id in (None, claim.actor_id) or claim.actor_id.lower() not in claim.quote.lower():
        raise ValueError('third-party attribution invalid')
    if (claim.factor == ResponsibilityFactor.STATED_INTENTION and
        claim.authority != ClaimAuthority.DIRECT_SELF_REPORT and
        not re.search(r'\b(said|stated|reported|claimed|told)\b|说|表示|声称', claim.quote, re.I)):
        raise ValueError('non-self intention requires an explicit statement attribution')
    if claim.factor == ResponsibilityFactor.CAUSAL_CONTRIBUTION:
        if _time(source.valid_time) < _time(outcome.valid_time):
            raise ValueError('causal contribution cannot be sourced before outcome')
    elif _time(source.valid_time) > _time(action.valid_time) and not _RETROSPECTIVE.search(claim.quote):
        raise ValueError('later report needs explicit action-time anchor')


def _factor_row(factor, claims):
    def source_supports(c):
        return (c.authority != ClaimAuthority.THIRD_PARTY_ATTRIBUTION and
                (factor != ResponsibilityFactor.CAUSAL_CONTRIBUTION or
                 c.authority == ClaimAuthority.EXPLICIT_NARRATOR))
    support = [c for c in claims if c.value and source_supports(c)]
    contradiction = [c for c in claims if not c.value and source_supports(c)]
    attributed = [c for c in claims if not source_supports(c)]
    if (support and contradiction or
        support and any(not c.value for c in attributed) or
        contradiction and any(c.value for c in attributed)):
        state = 'CONTESTED'
    elif support:
        state = 'SUPPORTED_CLAIM'
    elif contradiction:
        state = 'CONTRADICTED_CLAIM'
    elif attributed:
        state = 'ATTRIBUTED_ONLY'
    else:
        state = 'UNKNOWN'
    def receipt(rows):
        return [{'claim_id': c.claim_id, 'source_event_id': c.source_event_id,
                 'target_actor': c.actor_id, 'about_time': c.about_time,
                 'authority': c.authority.value, 'value': c.value, 'quote': c.quote}
                for c in rows]
    return {'factor': factor.value, 'state': state,
            'support': receipt(support), 'contradiction': receipt(contradiction),
            'third_party_attributions': receipt(attributed),
            'epistemic_scope': 'EXPLICIT_SOURCE_CLAIMS_NOT_PRIVATE_OR_WORLD_TRUTH'}


def check_responsibility(case: ResponsibilityCase, events: tuple[EventRecord, ...],
                         *, target_actor: str, mode: str = 'READER_ANALYSIS',
                         observer_actor: str | None = None,
                         event_time: str | None = None,
                         knowledge_cutoff: str | None = None) -> dict:
    """Check factor claims, then evaluate only caller-declared premise requirements."""
    if not isinstance(case, ResponsibilityCase) or len(events) > 24:
        raise ValueError('bounded typed responsibility case required')
    if mode not in ('READER_ANALYSIS', 'CHARACTER_PERSPECTIVE', 'OBSERVER_ABOUT_TARGET'):
        raise ValueError('invalid responsibility perspective')
    if mode == 'OBSERVER_ABOUT_TARGET' and not observer_actor:
        raise ValueError('observer required')
    if target_actor not in case.actor_ids:
        raise ValueError('focal actor not in case')
    sources = {e.event_id: e for e in events}
    if len(sources) != len(events) or case.action_event_id not in sources or case.outcome_event_id not in sources:
        raise ValueError('missing or duplicate action/outcome source')
    for source in events:
        _time(source.valid_time)
        _time(source.recorded_at)
    action, outcome = sources[case.action_event_id], sources[case.outcome_event_id]
    if action.actor_id != target_actor or _time(outcome.valid_time) < _time(action.valid_time):
        raise ValueError('action/outcome actor or order mismatch')
    for claim in case.claims:
        _validate_claim(claim, case, sources)
    for premise in case.premises:
        if not set(premise.basis_event_ids) <= sources.keys():
            raise ValueError('premise basis lacks source')
    def visible(e):
        if event_time and _time(e.valid_time) > _time(event_time):
            return False
        if knowledge_cutoff and _time(e.recorded_at) > _time(knowledge_cutoff):
            return False
        if mode == 'READER_ANALYSIS':
            return True
        if mode == 'CHARACTER_PERSPECTIVE':
            return event_accessible_to(e, target_actor)
        return viewer_can_establish_target_access(e, viewer_agent_id=observer_actor,
                                                  target_agent_id=target_actor)
    view = {e.event_id for e in events if visible(e)}
    if {case.action_event_id, case.outcome_event_id} - view:
        return {'status': 'SOURCE_VIEW_INSUFFICIENT', 'factors': [],
                'premise_assessments': [], 'conclusion': 'UNRESOLVED'}
    visible_claims = [c for c in case.claims if c.actor_id == target_actor and
                      c.source_event_id in view]
    factor_rows = [_factor_row(f, [c for c in visible_claims if c.factor == f])
                   for f in ResponsibilityFactor]
    assessments = []
    for premise in case.premises:
        if not set(premise.basis_event_ids) <= view:
            continue
        scoped = [c for c in visible_claims if c.source_event_id in premise.basis_event_ids]
        requirements = []
        for requirement in premise.requirements:
            row = _factor_row(requirement.factor,
                              [c for c in scoped if c.factor == requirement.factor])
            state = row['state']
            if state == 'SUPPORTED_CLAIM' and requirement.value or state == 'CONTRADICTED_CLAIM' and not requirement.value:
                result = 'MET_BY_SOURCE_CLAIM'
            elif state == 'CONTRADICTED_CLAIM' and requirement.value or state == 'SUPPORTED_CLAIM' and not requirement.value:
                result = 'COUNTEREXAMPLE_IN_SOURCE'
            else:
                result = 'UNRESOLVED'
            requirements.append({'factor': requirement.factor.value,
                'required_value': requirement.value, 'result': result,
                'factor_state': state, 'source_claim_ids': [c['claim_id'] for key in
                    ('support', 'contradiction', 'third_party_attributions') for c in row[key]]})
        if not requirements:
            result = 'UNRESOLVED_NO_STRUCTURED_RULE'
        elif any(r['result'] == 'COUNTEREXAMPLE_IN_SOURCE' for r in requirements):
            result = 'CONDITIONALLY_NOT_SUPPORTED'
        elif all(r['result'] == 'MET_BY_SOURCE_CLAIM' for r in requirements):
            result = 'CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS'
        else:
            result = 'UNRESOLVED'
        assessments.append({'premise_id': premise.premise_id, 'text': premise.text,
            'basis_event_ids': list(premise.basis_event_ids),
            'authority': 'CALLER_SUPPLIED_CONDITIONAL',
            'requirements': requirements, 'result': result,
            'scope': 'PREMISE_DEPENDENT_EXPLANATION_NOT_MORAL_OR_LEGAL_VERDICT'})
    return {'status': 'SOURCE_FACTORS_CHECKED', 'focal_actor': target_actor,
        'action_event_id': case.action_event_id,
        'outcome_event_id': case.outcome_event_id,
        'factors': factor_rows, 'premise_assessments': assessments,
        'conclusion': 'PREMISE_DEPENDENT_ONLY',
        'other_relevant_facts': 'OPEN_UNKNOWN'}


@dataclass(frozen=True)
class ResponsibilityPreparation:
    events: tuple[EventRecord, ...]
    case: ResponsibilityCase | None
    failure: str | None
    source_span_diagnostics: tuple[dict, ...]


_ACTION = re.compile(r'\b(opened|closed|pressed|removed|sent|gave|took|turned|moved|released|switched)\b|打开|关闭|按下|移走|释放', re.I)
_OUTCOME = re.compile(r'\b(escaped|failed|broke|died|occurred|happened|was lost|was injured|was damaged)\b|逃走|失败|受伤|损坏', re.I)
_BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def prepare_responsibility_narrative(narrative: str, target_actor: str,
                                     premises: tuple[NarrativePremise, ...], *, premise_scope='ALL_SOURCE') -> ResponsibilityPreparation:
    """Parse a small ordered prose family; every accepted span is an exact line."""
    if premise_scope not in ('ALL_SOURCE', 'FOCAL_EPISODE'):
        raise ValueError('explicit caller premise source scope required')
    if (not isinstance(narrative, str) or not narrative.strip() or len(narrative) > 16000 or
        not isinstance(target_actor, str) or not target_actor.strip() or
        not isinstance(premises, tuple) or not 1 <= len(premises) <= 3 or
        not all(isinstance(p, NarrativePremise) for p in premises) or
        len({p.premise_id for p in premises}) != len(premises)):
        raise ValueError('bounded narrative and explicit caller premises required')
    lines = [line.strip() for line in narrative.splitlines() if line.strip()]
    if not 2 <= len(lines) <= 12 or any(len(line) > 2000 for line in lines):
        return ResponsibilityPreparation((), None, 'narrative_line_bounds', ())
    digest = hashlib.sha256(narrative.encode()).hexdigest()[:12]
    events = []
    for index, line in enumerate(lines, 1):
        speaker = None
        header = re.match(r'^([A-Z][A-Za-z-]{0,63}|Narrator):\s+', line)
        if header:
            speaker = None if header.group(1) == 'Narrator' else header.group(1)
        elif line.startswith(target_actor + ' '):
            speaker = target_actor
        elif re.match(r'^(The|A|An)\b', line):
            speaker = None
        else:
            return ResponsibilityPreparation((), None, 'unrecognized_source_line',
                ({'line': index, 'status': 'UNRECOGNIZED'},))
        time = (_BASE + timedelta(seconds=index)).isoformat()
        events.append(EventRecord(f'cg03-{digest}-{index}', time, line,
            'authorized-responsibility-narrative-order', time, speaker,
            metadata={'reader_only': speaker is None}))
    from .cg05 import _FACT as concept_fact, _USE as concept_use
    from .cg04 import _CONDITION as context_condition
    foreign = {e.event_id for e in events if (
        re.search(r'\b(?:believe|believes|believed|belief|prefer|prefers|preference|mean|means|meaning)\b', e.raw_text, re.I) or
        concept_fact.fullmatch(e.raw_text) or concept_use.fullmatch(e.raw_text) or
        context_condition.fullmatch(e.raw_text))}
    actions = [e for e in events if e.event_id not in foreign and e.actor_id == target_actor and
               _ACTION.search(e.raw_text) and
               not re.search(_FACTOR_PATTERNS[ResponsibilityFactor.STATED_INTENTION], e.raw_text, re.I)]
    outcomes = [e for e in events if e.event_id not in foreign and e.actor_id is None and _OUTCOME.search(e.raw_text)]
    if len(actions) != 1 or len(outcomes) != 1 or _time(outcomes[0].valid_time) < _time(actions[0].valid_time):
        return ResponsibilityPreparation((), None, 'action_or_outcome_ambiguous', ())
    action, outcome = actions[0], outcomes[0]
    claims = []
    diagnostics = []
    for index, source in enumerate(events, 1):
        if source in (action, outcome):
            continue
        # Local readings/properties and belief/preference assertions describe
        # another operation. Their incidental factor words do not report the
        # focal actor's action-time knowledge, control or intention. Mixed or
        # partial mental assertions are equally unsafe as factor evidence.
        if source.event_id in foreign:
            diagnostics.append({'line': index, 'status': 'OTHER_OPERATION_NOT_RESPONSIBILITY_FACTOR'})
            continue
        matched = [factor for factor, pattern in _FACTOR_PATTERNS.items()
                   if re.search(pattern, source.raw_text, re.I)]
        if not matched:
            continue
        if len(matched) != 1:
            diagnostics.append({'line': index, 'status': 'AMBIGUOUS_FACTOR'})
            continue
        authority = (ClaimAuthority.EXPLICIT_NARRATOR if source.actor_id is None else
                     ClaimAuthority.DIRECT_SELF_REPORT if source.actor_id == target_actor else
                     ClaimAuthority.THIRD_PARTY_ATTRIBUTION)
        claim = FactorClaim(f'claim-{index}', matched[0], target_actor,
            action.event_id, source.event_id, source.raw_text, action.valid_time,
            not bool(_NEGATIVE.search(source.raw_text)), authority)
        try:
            _validate_claim(claim, ResponsibilityCase((target_actor,), action.event_id,
                outcome.event_id, (NormativePremise('temporary', 'temporary',
                (action.event_id,)),)), {e.event_id: e for e in events})
        except ValueError:
            diagnostics.append({'line': index, 'status': 'FACTOR_REJECTED'})
            continue
        claims.append(claim)
        diagnostics.append({'line': index, 'status': 'EXACT_SOURCE_FACTOR',
                            'claim_id': claim.claim_id, 'source_event_id': source.event_id})
    def premise_basis(p):
        if premise_scope == 'ALL_SOURCE':
            return tuple(e.event_id for e in events)
        required = {r.factor for r in p.requirements}
        return tuple(dict.fromkeys((action.event_id, outcome.event_id,
            *(c.source_event_id for c in claims if c.factor in required))))
    actors = tuple(dict.fromkeys([target_actor] +
        [e.actor_id for e in events if e.actor_id and e.actor_id != target_actor]))
    if len(actors) > 4:
        return ResponsibilityPreparation((), None, 'actor_bound_exceeded', tuple(diagnostics))
    case = ResponsibilityCase(actors, action.event_id, outcome.event_id,
        tuple(NormativePremise(p.premise_id, p.text, premise_basis(p), p.requirements)
              for p in premises), tuple(claims))
    return ResponsibilityPreparation(tuple(events), case, None, tuple(diagnostics))
