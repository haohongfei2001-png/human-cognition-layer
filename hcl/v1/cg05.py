"""Source-bound local concept readings, never shared meaning or moral truth."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import re

from hcl.v04.model import EventRecord
from hcl.v06.perspective import event_accessible_to, viewer_can_establish_target_access
from .cg04 import (_TERM, _label, _time, PreferenceCondition, _requirements,
                   _CONDITION as _PREFERENCE_CONDITION, _decode as _decode_preference)

_SELF = re.compile(rf'(?P<actor>{_TERM}): In (?P<context>{_TERM}), by (?P<term>{_TERM}) I mean (?P<criteria>.+)\.')
_REVISION = re.compile(rf'(?P<actor>{_TERM}): In (?P<context>{_TERM}), I now use (?P<term>{_TERM}) to mean (?P<criteria>.+?) instead of (?P<old>.+)\.')
_REPORT = re.compile(rf'(?P<speaker>{_TERM}): In (?P<context>{_TERM}), (?P<actor>{_TERM}) uses (?P<term>{_TERM}) to mean (?P<criteria>.+)\.')
_FACT = re.compile(rf'Narrator: In (?P<context>{_TERM}), (?P<item>{_TERM}) has (?P<key>{_TERM}) (?P<value>true|false)\.')
_USE = re.compile(rf'(?P<actor>{_TERM}): In (?P<context>{_TERM}), (?P<item>{_TERM}) is (?P<negative>not )?(?P<term>{_TERM})\.')


def _criteria(text):
    rows = _requirements(' if ' + text)
    if not 1 <= len(rows) <= 4 or len({r.key for r in rows}) != len(rows):
        raise ValueError('one to four distinct explicit criteria required')
    return rows


def _decode(text):
    match = _SELF.fullmatch(text) or _REVISION.fullmatch(text)
    if match:
        row = match.groupdict()
        return row, 'DIRECT_SELF_REPORT', row['actor']
    match = _REPORT.fullmatch(text)
    if match and match['actor'] != match['speaker']:
        row = match.groupdict()
        return row, ('EXPLICIT_NARRATOR' if row['speaker'] == 'Narrator' else 'THIRD_PARTY_ATTRIBUTION'), row['speaker']
    raise ValueError('unsupported local definition expression')


@dataclass(frozen=True)
class ConceptDefinition:
    definition_id: str
    source_event_id: str
    quote: str
    actor_id: str
    context: str
    term: str
    criteria: tuple[PreferenceCondition, ...]
    authority: str = 'DIRECT_SELF_REPORT'
    supersedes_id: str | None = None

    def __post_init__(self):
        for value in (self.definition_id, self.source_event_id, self.actor_id, self.context, self.term):
            _label(value)
        if (not isinstance(self.quote, str) or not 1 <= len(self.quote) <= 2000 or
            not isinstance(self.criteria, tuple) or not 1 <= len(self.criteria) <= 4 or
            not all(isinstance(c, PreferenceCondition) for c in self.criteria) or
            len({c.key for c in self.criteria}) != len(self.criteria) or
            self.authority not in ('DIRECT_SELF_REPORT', 'EXPLICIT_NARRATOR', 'THIRD_PARTY_ATTRIBUTION')):
            raise ValueError('bounded source definition required')
        if self.supersedes_id is not None:
            _label(self.supersedes_id)


@dataclass(frozen=True)
class ConceptProperty:
    source_event_id: str
    quote: str
    context: str
    item: str
    key: str
    value: bool

    def __post_init__(self):
        for value in (self.source_event_id, self.context, self.item, self.key):
            _label(value)
        if type(self.value) is not bool or not isinstance(self.quote, str) or not 1 <= len(self.quote) <= 2000:
            raise ValueError('bounded boolean source property required')


@dataclass(frozen=True)
class ConceptUse:
    source_event_id: str
    quote: str
    actor_id: str
    context: str
    item: str
    term: str
    positive: bool

    def __post_init__(self):
        for value in (self.source_event_id, self.actor_id, self.context, self.item, self.term):
            _label(value)
        if type(self.positive) is not bool or not isinstance(self.quote, str) or not 1 <= len(self.quote) <= 2000:
            raise ValueError('bounded explicit application required')


@dataclass(frozen=True)
class ConceptCase:
    actor_id: str
    context: str
    term: str
    item: str
    definitions: tuple[ConceptDefinition, ...]
    properties: tuple[ConceptProperty, ...] = ()
    uses: tuple[ConceptUse, ...] = ()

    def __post_init__(self):
        for value in (self.actor_id, self.context, self.term, self.item):
            _label(value)
        for rows, cls, cap in ((self.definitions, ConceptDefinition, 8),
                               (self.properties, ConceptProperty, 12), (self.uses, ConceptUse, 8)):
            if not isinstance(rows, tuple) or len(rows) > cap or not all(isinstance(r, cls) for r in rows):
                raise ValueError('bounded typed concept rows required')
            if len({r.source_event_id for r in rows}) != len(rows):
                raise ValueError('duplicate concept source')
        if not self.definitions or len({d.definition_id for d in self.definitions}) != len(self.definitions):
            raise ValueError('distinct source definitions required')
        if (len({d.actor_id for d in self.definitions} | {u.actor_id for u in self.uses} | {self.actor_id}) > 4 or
            len({d.context for d in self.definitions} | {r.context for r in self.properties + self.uses} | {self.context}) > 2 or
            len({c.key for d in self.definitions for c in d.criteria} | {p.key for p in self.properties}) > 4 or
            len({d.term for d in self.definitions} | {u.term for u in self.uses} | {self.term}) > 2 or
            len({p.item for p in self.properties} | {u.item for u in self.uses} | {self.item}) > 2):
            raise ValueError('concept actor/context/feature/term/item bounds exceeded')


def _validate(case, events):
    if not isinstance(case, ConceptCase) or not isinstance(events, tuple) or not 1 <= len(events) <= 24:
        raise ValueError('bounded concept case and source records required')
    if not all(isinstance(e, EventRecord) for e in events):
        raise ValueError('typed source records required')
    sources = {e.event_id: e for e in events}
    if len(sources) != len(events) or len({e.actor_id for e in events if e.actor_id}) > 4:
        raise ValueError('duplicate source or actor bound exceeded')
    for e in events:
        _time(e.valid_time)
        _time(e.recorded_at)
    defs = {d.definition_id: d for d in case.definitions}
    for d in case.definitions:
        e = sources.get(d.source_event_id)
        if not e or d.quote != e.raw_text.strip():
            raise ValueError('definition lacks exact complete source')
        row, authority, speaker = _decode(d.quote)
        if (e.actor_id != (None if speaker == 'Narrator' else speaker) or authority != d.authority or
            row['actor'] != d.actor_id or row['context'] != d.context or row['term'] != d.term or
            _criteria(row['criteria']) != d.criteria or bool(row.get('old')) != bool(d.supersedes_id)):
            raise ValueError('definition fields contradict source')
        if d.supersedes_id:
            prior = defs.get(d.supersedes_id)
            if (prior is None or prior.authority != 'DIRECT_SELF_REPORT' or
                (prior.actor_id, prior.context, prior.term) != (d.actor_id, d.context, d.term) or
                _criteria(row['old']) != prior.criteria or
                _time(e.valid_time) <= _time(sources[prior.source_event_id].valid_time)):
                raise ValueError('revision requires earlier matching self definition')
            matches = [p for p in case.definitions if p.authority == 'DIRECT_SELF_REPORT' and
                (p.actor_id, p.context, p.term, p.criteria) == (d.actor_id, d.context, d.term, prior.criteria) and
                _time(sources[p.source_event_id].valid_time) < _time(e.valid_time)]
            if len(matches) != 1 or matches[0] != prior:
                raise ValueError('ambiguous prior definition')
    for row in case.properties + case.uses:
        e = sources.get(row.source_event_id)
        if not e or row.quote != e.raw_text.strip():
            raise ValueError('application lacks exact complete source')
        if isinstance(row, ConceptProperty):
            m = _FACT.fullmatch(row.quote)
            if (not m or e.actor_id is not None or
                (m['context'], m['item'], m['key'], m['value'] == 'true') !=
                (row.context, row.item, row.key, row.value)):
                raise ValueError('property fields contradict narrator source')
        else:
            m = _USE.fullmatch(row.quote)
            if (not m or e.actor_id != row.actor_id or
                (m['actor'], m['context'], m['item'], m['term'], not bool(m['negative'])) !=
                (row.actor_id, row.context, row.item, row.term, row.positive)):
                raise ValueError('usage fields contradict actor source')
    return sources


def project_concepts(case, events, *, mode='READER_ANALYSIS', observer_actor=None,
                     event_time=None, knowledge_cutoff=None):
    from .source_access import scope_source_access
    events = scope_source_access(events, event_time=event_time, knowledge_cutoff=knowledge_cutoff)
    sources = _validate(case, events)
    if mode not in ('READER_ANALYSIS', 'CHARACTER_PERSPECTIVE', 'OBSERVER_ABOUT_TARGET'):
        raise ValueError('invalid concept perspective')
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
        return viewer_can_establish_target_access(e, viewer_agent_id=observer_actor, target_agent_id=case.actor_id)
    available = {eid for eid, e in sources.items() if visible(e)}
    definitions = []
    for d in case.definitions:
        if d.source_event_id not in available:
            continue
        row = asdict(d)
        prior = next((p for p in case.definitions if p.definition_id == d.supersedes_id), None)
        if prior and prior.source_event_id not in available:
            row['supersedes_id'] = None
            row['quote'] = d.quote.split(' instead of ')[0] + '.'
        definitions.append(row)
    return dict(actor_id=case.actor_id, scenario=dict(context=case.context, term=case.term, item=case.item,
        authority='CALLER_SELECTED_SCENARIO'), definitions=definitions,
        properties=[asdict(p) for p in case.properties if p.source_event_id in available],
        uses=[asdict(u) for u in case.uses if u.source_event_id in available])


def check_concepts(case, events, **scope):
    view = project_concepts(case, events, **scope)
    retired = {d['supersedes_id'] for d in view['definitions'] if d['supersedes_id']}
    readings = []
    for d in view['definitions']:
        criteria = []
        for c in d['criteria']:
            facts = [p for p in view['properties'] if (p['context'], p['item'], p['key']) ==
                (d['context'], case.item, c['key'])]
            values = {p['value'] for p in facts}
            state = ('CONTESTED' if len(values) > 1 else 'UNKNOWN' if not values else
                     'MET_BY_SOURCE_CLAIM' if c['value'] in values else 'NOT_MET_BY_SOURCE_CLAIM')
            criteria.append(dict(c, state=state, source_event_ids=[p['source_event_id'] for p in facts]))
        uses = [u for u in view['uses'] if (u['actor_id'], u['context'], u['term'], u['item']) ==
            (d['actor_id'], d['context'], d['term'], case.item) and
            _time(next(e.valid_time for e in events if e.event_id == u['source_event_id'])) >=
            _time(next(e.valid_time for e in events if e.event_id == d['source_event_id']))]
        declared = {u['positive'] for u in uses}
        met = all(c['state'] == 'MET_BY_SOURCE_CLAIM' for c in criteria)
        missing = any(c['state'] in ('UNKNOWN', 'CONTESTED') for c in criteria)
        failed = any(c['state'] == 'NOT_MET_BY_SOURCE_CLAIM' for c in criteria)
        if d['definition_id'] in retired:
            state = 'SUPERSEDED_LOCAL'
        elif (d['context'], d['term']) != (case.context, case.term):
            state = 'OTHER_SCOPE'
        elif d['authority'] == 'THIRD_PARTY_ATTRIBUTION':
            state = 'ATTRIBUTED_ONLY'
        elif len(declared) > 1 or (True in declared and failed):
            state = 'CONTESTED_APPLICATION'
        elif False in declared:
            state = 'DECLARED_COUNTEREXAMPLE'
        elif failed:
            state = 'CRITERIA_NOT_MET'
        elif missing:
            state = 'CRITERIA_UNRESOLVED'
        else:
            state = 'CRITERIA_MET'
        readings.append(dict(d, state=state, criterion_checks=criteria,
            application_source_ids=[u['source_event_id'] for u in uses],
            counterexample_conflicts_with_criteria=met and False in declared,
            scope='LOCAL_SOURCE_USAGE_NOT_SHARED_OR_MORAL_TRUTH'))
    active = [d for d in readings if d['state'] not in ('SUPERSEDED_LOCAL', 'OTHER_SCOPE', 'ATTRIBUTED_ONLY')]
    signatures = {tuple(sorted((c['key'], c['value']) for c in d['criteria'])) for d in active}
    return dict(status='LOCAL_CONCEPT_READINGS_CHECKED', scenario=view['scenario'], readings=readings,
        focal_reading_ids=[d['definition_id'] for d in active if d['actor_id'] == case.actor_id],
        reading_relation='MULTIPLE_LOCAL_READINGS' if len(signatures) > 1 else
            'ONE_OBSERVED_READING' if signatures else 'NO_SOURCE_READING',
        shared_meaning='NOT_ESTABLISHED', moral_truth='NOT_INFERRED',
        misunderstanding_or_deception='NOT_INFERRED')


@dataclass(frozen=True)
class ConceptPreparation:
    events: tuple[EventRecord, ...]
    case: ConceptCase | None
    failure: str | None
    diagnostics: tuple[dict, ...]


def prepare_concept_narrative(narrative, actor_id, context, term, item):
    for value in (actor_id, context, term, item):
        _label(value)
    if not isinstance(narrative, str) or not narrative.strip() or len(narrative) > 16000:
        raise ValueError('bounded concept narrative required')
    lines = [s.strip() for s in narrative.splitlines() if s.strip()]
    if not 1 <= len(lines) <= 24 or any(len(s) > 2000 for s in lines):
        return ConceptPreparation((), None, 'narrative_line_bounds', ())
    digest = hashlib.sha256(narrative.encode()).hexdigest()[:10]
    events, definitions, properties, uses, diagnostics = [], [], [], [], []
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Preserve the full authorized source even when one semantic line fails.
    for i, line in enumerate(lines, 1):
        speaker = re.match(rf'({_TERM}): ', line)
        stamp = (base + timedelta(seconds=i)).isoformat()
        events.append(EventRecord(f'cg05-{digest}-{i}', stamp, line, 'authorized-concept-line-order', stamp,
            speaker[1] if speaker and speaker[1] != 'Narrator' else None, metadata={'reader_only': True}))
    try:
        for i, line in enumerate(lines, 1):
            eid = events[i - 1].event_id
            from .belief_preparation import decode_belief_source
            try:
                decode_belief_source(line)
            except ValueError:
                pass
            else:
                diagnostics.append(dict(line=i, status='BELIEF_NOT_CONCEPT_DEFINITION'))
                continue
            # A context condition belongs to CG04, not to an item's concept
            # properties or to a fictional speaker named Narrator.
            if _PREFERENCE_CONDITION.fullmatch(line):
                diagnostics.append(dict(line=i, status='CONTEXT_CONDITION_NOT_CONCEPT_PROPERTY'))
                continue
            try:
                preference, _, _ = _decode_preference(line)
                _requirements(preference['conditions'])
            except ValueError:
                pass
            else:
                diagnostics.append(dict(line=i, status='PREFERENCE_NOT_CONCEPT_DEFINITION'))
                continue
            fact, use = _FACT.fullmatch(line), _USE.fullmatch(line)
            if fact:
                properties.append(ConceptProperty(eid, line, fact['context'], fact['item'], fact['key'], fact['value'] == 'true'))
                continue
            if use:
                uses.append(ConceptUse(eid, line, use['actor'], use['context'], use['item'], use['term'], not bool(use['negative'])))
                continue
            try:
                row, authority, _ = _decode(line)
            except ValueError:
                if re.search(r'\b(mean|means|uses|by|instead of|has|is not)\b', line):
                    raise ValueError('unsupported or ambiguous concept expression')
                diagnostics.append(dict(line=i, status='NO_MEANING_INFERRED'))
                continue
            prior = [d for d in definitions if d.authority == 'DIRECT_SELF_REPORT' and
                (d.actor_id, d.context, d.term, d.criteria) ==
                (row['actor'], row['context'], row['term'], _criteria(row['old']))] if row.get('old') else []
            if row.get('old') and len(prior) != 1:
                raise ValueError('ambiguous or absent prior meaning')
            definitions.append(ConceptDefinition(f'def-{i}', eid, line, row['actor'], row['context'], row['term'],
                _criteria(row['criteria']), authority, prior[0].definition_id if prior else None))
        if not definitions:
            return ConceptPreparation(tuple(events), None, 'no_explicit_definition', tuple(diagnostics))
        case = ConceptCase(actor_id, context, term, item, tuple(definitions), tuple(properties), tuple(uses))
        _validate(case, tuple(events))
        return ConceptPreparation(tuple(events), case, None, tuple(diagnostics))
    except ValueError:
        return ConceptPreparation(tuple(events), None, 'invalid_or_ambiguous_concept_source', tuple(diagnostics))
