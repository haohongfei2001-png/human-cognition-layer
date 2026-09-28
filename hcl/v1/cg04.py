"""Explicit contextual preferences; no global weights or inferred values."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import re

from hcl.v04.model import EventRecord
from hcl.v06.perspective import event_accessible_to, viewer_can_establish_target_access


_TERM = r'[A-Za-z][A-Za-z0-9_-]{0,31}'
_SELF = re.compile(rf'(?P<actor>{_TERM}): As (?P<role>{_TERM}) in (?P<context>{_TERM}), '
    rf'I (?P<now>now )?prefer (?P<preferred>{_TERM}) over (?P<over>{_TERM})'
    rf'(?P<conditions> if .+?)?(?: instead of (?P<old_preferred>{_TERM}) over (?P<old_over>{_TERM}))?\.')
_REPORT = re.compile(rf'(?P<speaker>{_TERM}): In (?P<context>{_TERM}), '
    rf'(?P<actor>{_TERM}) as (?P<role>{_TERM}) prefers '
    rf'(?P<preferred>{_TERM}) over (?P<over>{_TERM})(?P<conditions> if .+?)?\.')
_CONDITION = re.compile(rf'Narrator: In (?P<context>{_TERM}), (?P<key>{_TERM}) is (?P<value>true|false)\.')


def _label(value):
    if not isinstance(value, str) or re.fullmatch(_TERM, value) is None:
        raise ValueError('bounded source-named label required')


def _time(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.utcoffset() is None:
        raise ValueError('timezone-aware source scope required')
    return stamp


@dataclass(frozen=True)
class PreferenceCondition:
    key: str
    value: bool

    def __post_init__(self):
        _label(self.key)
        if type(self.value) is not bool:
            raise ValueError('boolean preference condition required')


@dataclass(frozen=True)
class PreferenceStatement:
    statement_id: str
    source_event_id: str
    quote: str
    actor_id: str
    role: str
    context: str
    preferred: str
    over: str
    authority: str = 'DIRECT_SELF_REPORT'
    conditions: tuple[PreferenceCondition, ...] = ()
    supersedes_id: str | None = None

    def __post_init__(self):
        for name in ('statement_id', 'source_event_id', 'actor_id', 'role',
                     'context', 'preferred', 'over'):
            _label(getattr(self, name))
        if (not isinstance(self.quote, str) or not self.quote or len(self.quote) > 2000 or
            self.preferred == self.over or self.authority not in (
                'DIRECT_SELF_REPORT', 'EXPLICIT_NARRATOR', 'THIRD_PARTY_ATTRIBUTION')):
            raise ValueError('bounded distinct preference and authority required')
        if (not isinstance(self.conditions, tuple) or len(self.conditions) > 4 or
            not all(isinstance(c, PreferenceCondition) for c in self.conditions) or
            len({c.key for c in self.conditions}) != len(self.conditions)):
            raise ValueError('at most four distinct typed conditions required')
        if self.supersedes_id is not None:
            _label(self.supersedes_id)


@dataclass(frozen=True)
class ContextConditionClaim:
    source_event_id: str
    quote: str
    context: str
    key: str
    value: bool

    def __post_init__(self):
        for value in (self.source_event_id, self.context, self.key):
            _label(value)
        if not isinstance(self.quote, str) or not self.quote or len(self.quote) > 2000 or type(self.value) is not bool:
            raise ValueError('bounded condition source claim required')


@dataclass(frozen=True)
class PreferenceCase:
    actor_id: str
    role: str
    context: str
    statements: tuple[PreferenceStatement, ...]
    conditions: tuple[ContextConditionClaim, ...] = ()

    def __post_init__(self):
        for value in (self.actor_id, self.role, self.context):
            _label(value)
        if (not isinstance(self.statements, tuple) or not 1 <= len(self.statements) <= 8 or
            not all(isinstance(s, PreferenceStatement) for s in self.statements) or
            len({s.statement_id for s in self.statements}) != len(self.statements) or
            len({s.source_event_id for s in self.statements}) != len(self.statements) or
            any(s.actor_id != self.actor_id for s in self.statements)):
            raise ValueError('one to eight distinct focal-actor preference statements required')
        if (not isinstance(self.conditions, tuple) or len(self.conditions) > 8 or
            not all(isinstance(c, ContextConditionClaim) for c in self.conditions) or
            len({c.source_event_id for c in self.conditions}) != len(self.conditions)):
            raise ValueError('at most eight distinct source condition claims required')
        if (len({s.role for s in self.statements}) > 2 or
            len({s.context for s in self.statements} | {c.context for c in self.conditions}) > 2 or
            len({v for s in self.statements for v in (s.preferred, s.over)}) > 6 or
            len({c.key for s in self.statements for c in s.conditions} |
                {c.key for c in self.conditions}) > 4):
            raise ValueError('role/context/value/condition bounds exceeded')


def _requirements(text):
    if not text:
        return ()
    rows = []
    for part in text.removeprefix(' if ').split(' and '):
        match = re.fullmatch(rf'({_TERM}) is (true|false)', part)
        if not match:
            raise ValueError('unsupported explicit condition grammar')
        rows.append(PreferenceCondition(match[1], match[2] == 'true'))
    return tuple(rows)


def _decode(quote):
    match = _SELF.fullmatch(quote)
    if match:
        row = match.groupdict()
        if bool(row['now']) != bool(row['old_preferred']):
            raise ValueError('revision requires now and an explicit prior pair')
        return row, 'DIRECT_SELF_REPORT', row['actor']
    match = _REPORT.fullmatch(quote)
    if match:
        row = match.groupdict()
        if row['speaker'] == row['actor']:
            raise ValueError('self statement needs explicit first-person grammar')
        return row, ('EXPLICIT_NARRATOR' if row['speaker'] == 'Narrator'
                     else 'THIRD_PARTY_ATTRIBUTION'), row['speaker']
    raise ValueError('unanchored explicit preference grammar')


def _validate(case, events):
    if not isinstance(case, PreferenceCase) or not isinstance(events, tuple) or not 1 <= len(events) <= 24:
        raise ValueError('bounded typed preference case and source tuple required')
    if not all(isinstance(e, EventRecord) for e in events):
        raise ValueError('typed source records required')
    sources = {e.event_id: e for e in events}
    if len(sources) != len(events) or len({e.actor_id for e in events if e.actor_id}) > 4:
        raise ValueError('duplicate source or actor bound exceeded')
    for e in events:
        _time(e.valid_time)
        _time(e.recorded_at)
    statements = {s.statement_id: s for s in case.statements}
    if {s.source_event_id for s in case.statements} - sources.keys():
        raise ValueError('missing preference source')
    for s in case.statements:
        e = sources.get(s.source_event_id)
        if e is None or s.quote != e.raw_text.strip():
            raise ValueError('preference lacks exact source span')
        row, authority, speaker = _decode(s.quote)
        if (authority != s.authority or e.actor_id != (None if speaker == 'Narrator' else speaker) or
            any(row[k] != getattr(s, k) for k in ('role', 'context', 'preferred', 'over')) or
            row['actor'] != s.actor_id or _requirements(row['conditions']) != s.conditions):
            raise ValueError('preference fields contradict source expression')
        prior_pair = (row.get('old_preferred'), row.get('old_over'))
        if bool(s.supersedes_id) != bool(prior_pair[0]):
            raise ValueError('revision pointer contradicts explicit source')
        if s.supersedes_id:
            prior = statements.get(s.supersedes_id)
            if (prior is None or prior.authority != 'DIRECT_SELF_REPORT' or
                (s.actor_id, s.role, s.context) != (prior.actor_id, prior.role, prior.context) or
                s.conditions != prior.conditions or
                prior_pair != (prior.preferred, prior.over) or
                _time(e.valid_time) <= _time(sources[prior.source_event_id].valid_time)):
                raise ValueError('revision requires an earlier self statement with the same scope and conditions')
            candidates = [p for p in case.statements if p.authority == 'DIRECT_SELF_REPORT' and
                (p.actor_id, p.role, p.context, p.preferred, p.over) ==
                (s.actor_id, s.role, s.context, *prior_pair) and
                _time(sources[p.source_event_id].valid_time) < _time(e.valid_time)]
            # Avoid resolving multiple indistinguishable earlier statements by
            # a hand-entered pointer that the prose itself does not disambiguate.
            if len(candidates) != 1 or candidates[0] != prior:
                raise ValueError('ambiguous prior preference reference')
    for c in case.conditions:
        e = sources.get(c.source_event_id)
        match = _CONDITION.fullmatch(c.quote)
        if (e is None or c.quote != e.raw_text.strip() or e.actor_id is not None or
            not match or (match['context'], match['key'], match['value'] == 'true') !=
            (c.context, c.key, c.value)):
            raise ValueError('condition fields lack matching exact narrator source')
    return sources


def project_preferences(case, events, *, mode='READER_ANALYSIS', observer_actor=None,
                        event_time=None, knowledge_cutoff=None):
    """A: validate input then project source before any statement is serialized."""
    sources = _validate(case, events)
    if mode not in ('READER_ANALYSIS', 'CHARACTER_PERSPECTIVE', 'OBSERVER_ABOUT_TARGET'):
        raise ValueError('invalid preference perspective')
    if mode == 'OBSERVER_ABOUT_TARGET' and not observer_actor:
        raise ValueError('observer required')
    def visible(e):
        if event_time and _time(e.valid_time) > _time(event_time):
            return False
        if knowledge_cutoff and _time(e.recorded_at) > _time(knowledge_cutoff):
            return False
        if mode == 'READER_ANALYSIS':
            return True
        if mode == 'CHARACTER_PERSPECTIVE':
            return event_accessible_to(e, case.actor_id)
        return viewer_can_establish_target_access(e, viewer_agent_id=observer_actor,
            target_agent_id=case.actor_id)
    view = {eid for eid, e in sources.items() if visible(e)}
    rows = []
    for s in case.statements:
        if s.source_event_id not in view:
            continue
        row = asdict(s)
        prior = next((p for p in case.statements if p.statement_id == s.supersedes_id), None)
        if prior and prior.source_event_id not in view:
            row['supersedes_id'] = None
            row['revision_reference_available'] = False
            # The prior pair may itself reveal hidden source content. Retain
            # only the standalone new expression in the projected statement.
            row['quote'] = s.quote.split(' instead of ')[0] + '.'
        else:
            row['revision_reference_available'] = True
        rows.append(row)
    return {'actor_id': case.actor_id, 'scenario': {'role': case.role, 'context': case.context,
            'authority': 'CALLER_SELECTED_SCENARIO_NOT_OBSERVED_ROLE'},
        'statements': rows,
        'conditions': [asdict(c) for c in case.conditions if c.source_event_id in view]}


def check_preferences(case, events, **scope):
    """B/C: conditional applicability, explicit local revision and pair conflicts."""
    projected = project_preferences(case, events, **scope)
    rows = projected['statements']
    superseded = {r['supersedes_id'] for r in rows if r['supersedes_id']}
    checked = []
    for s in rows:
        conditions = []
        for requirement in s['conditions']:
            evidence = [c for c in projected['conditions'] if c['context'] == s['context']
                        and c['key'] == requirement['key']]
            values = {c['value'] for c in evidence}
            state = ('CONTESTED' if len(values) > 1 else 'UNKNOWN' if not values else
                     'MET_BY_SOURCE_CLAIM' if requirement['value'] in values else 'NOT_MET_BY_SOURCE_CLAIM')
            conditions.append(dict(requirement, state=state,
                source_event_ids=[c['source_event_id'] for c in evidence]))
        if s['statement_id'] in superseded:
            state = 'SUPERSEDED_LOCAL'
        elif (s['role'], s['context']) != (case.role, case.context):
            state = 'OTHER_SCOPE'
        elif s['authority'] == 'THIRD_PARTY_ATTRIBUTION':
            state = 'ATTRIBUTED_ONLY'
        elif any(c['state'] == 'NOT_MET_BY_SOURCE_CLAIM' for c in conditions):
            state = 'CONDITION_NOT_MET'
        elif any(c['state'] in ('UNKNOWN', 'CONTESTED') for c in conditions):
            state = 'CONDITION_UNRESOLVED'
        else:
            state = 'APPLICABLE_SOURCE_CLAIM'
        checked.append(dict(s, state=state, condition_checks=conditions,
            scope='EXPRESSED_LOCAL_PREFERENCE_NOT_PRIVATE_OR_MORAL_TRUTH'))
    active = [r for r in checked if r['state'] == 'APPLICABLE_SOURCE_CLAIM']
    conflicts = [{'statement_ids': [a['statement_id'], b['statement_id']],
                  'values': [a['preferred'], a['over']], 'state': 'UNRESOLVED_CONFLICT'}
                 for i, a in enumerate(active) for b in active[i + 1:]
                 if (a['preferred'], a['over']) == (b['over'], b['preferred'])]
    # Preserve longer directed conflicts too, without producing transitive
    # preferences or choosing a winner. Six bounded values permit finite DFS.
    edges = {r['preferred']: set() for r in active}
    for r in active:
        edges[r['preferred']].add(r['over'])
    def cycle(node, path):
        return any(n in path or cycle(n, path | {n}) for n in edges.get(node, ()))
    cyclic = any(cycle(n, {n}) for n in edges)
    return {'status': 'CONTEXTUAL_PREFERENCES_CHECKED', 'scenario': projected['scenario'],
        'statements': checked, 'conflicts': conflicts,
        'conflict_state': 'UNRESOLVED_CONFLICT' if cyclic else 'NO_OBSERVED_CONFLICT',
        'uncompared_values': 'UNRESOLVED_NO_TRANSITIVE_RANKING',
        'global_value_ranking': 'NOT_INFERRED', 'moral_winner': 'NOT_INFERRED'}


@dataclass(frozen=True)
class PreferencePreparation:
    events: tuple[EventRecord, ...]
    case: PreferenceCase | None
    failure: str | None
    diagnostics: tuple[dict, ...]


def prepare_preference_narrative(narrative, actor_id, role, context):
    """D: small ordinary-English prose grammar, zero model extraction."""
    for value in (actor_id, role, context):
        _label(value)
    if not isinstance(narrative, str) or not narrative.strip() or len(narrative) > 16000:
        raise ValueError('bounded preference narrative required')
    lines = [line.strip() for line in narrative.splitlines() if line.strip()]
    if not 1 <= len(lines) <= 24 or any(len(line) > 2000 for line in lines):
        return PreferencePreparation((), None, 'narrative_line_bounds', ())
    digest = hashlib.sha256(narrative.encode()).hexdigest()[:10]
    events, statements, conditions, diagnostics = [], [], [], []
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    try:
        for i, line in enumerate(lines, 1):
            speaker = re.match(rf'({_TERM}): ', line)
            stamp = (base + timedelta(seconds=i)).isoformat()
            eid = f'cg04-{digest}-{i}'
            # Prose does not supply reliable access metadata. It remains
            # reader-only rather than being copied to the named speaker view.
            e = EventRecord(eid, stamp, line, 'authorized-preference-line-order', stamp,
                speaker[1] if speaker and speaker[1] != 'Narrator' else None,
                metadata={'reader_only': True})
            events.append(e)
            cond = _CONDITION.fullmatch(line)
            if cond:
                conditions.append(ContextConditionClaim(eid, line, cond['context'], cond['key'], cond['value'] == 'true'))
                continue
            try:
                row, authority, _ = _decode(line)
            except ValueError:
                # Complete concept definitions are another operation's source,
                # even when their explicit revision contains 'instead of'.
                from .cg05 import _decode as decode_concept, _criteria as concept_criteria
                try:
                    concept, _, _ = decode_concept(line)
                    concept_criteria(concept['criteria'])
                    if concept.get('old'):
                        concept_criteria(concept['old'])
                except ValueError:
                    pass
                else:
                    diagnostics.append({'line': i, 'source_event_id': eid, 'status': 'CONCEPT_NOT_PREFERENCE'})
                    continue
                # Partial preference/revision syntax cannot silently disappear.
                if re.search(r'\b(prefer|prefers|preference|instead of)\b', line):
                    raise ValueError('unsupported or ambiguous preference line')
                diagnostics.append({'line': i, 'source_event_id': eid, 'status': 'NO_PREFERENCE_INFERRED'})
                continue
            if row['actor'] != actor_id:
                diagnostics.append({'line': i, 'source_event_id': eid, 'status': 'OTHER_ACTOR_NOT_PROJECTED'})
                continue
            prior_id = None
            if row.get('old_preferred'):
                prior = [s for s in statements if s.authority == 'DIRECT_SELF_REPORT' and
                    (s.role, s.context, s.preferred, s.over) ==
                    (row['role'], row['context'], row['old_preferred'], row['old_over'])]
                if len(prior) != 1:
                    raise ValueError('ambiguous or absent prior preference')
                prior_id = prior[0].statement_id
            statements.append(PreferenceStatement(f'pref-{i}', eid, line, actor_id,
                row['role'], row['context'], row['preferred'], row['over'], authority,
                _requirements(row['conditions']), prior_id))
        if not statements:
            return PreferencePreparation(tuple(events), None, 'no_explicit_preference', tuple(diagnostics))
        case = PreferenceCase(actor_id, role, context, tuple(statements), tuple(conditions))
        _validate(case, tuple(events))
        return PreferencePreparation(tuple(events), case, None, tuple(diagnostics))
    except ValueError:
        return PreferencePreparation(tuple(events), None, 'invalid_or_ambiguous_preference_source',
            tuple(diagnostics))
