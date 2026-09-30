"""Bitemporal source corrections and explicitly reported character revisions.

A stream is one declared source-local identity domain. Record versions correct
our source, never supersede a character's belief. Only explicit anchored revision
language does the latter, conditionally on accurate, sincere self-report.
"""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import re

from hcl.v06.belief import (BeliefEvidenceEvent, BeliefEvidenceKind, BeliefSignal,
    project_subject_beliefs)
from .core import ClaimKind, EvidenceCore, Scope, identity
from .semantic import AuthorizedText, prepare_semantics, _local_candidates, _PRONOUNS
from .epistemic import Attitude, MentalProposition, parse_mental_proposition

_POLICY = ('Keep source-record correction distinct from reported character revision. '
    'All belief estimates below are conditional on accurate, sincere explicit self-report, '
    'not verified private psychology or world truth. Exposure/challenge is not acceptance. '
    'Unknown event times do not establish temporal succession. Later record knowledge '
    'must not enter an earlier known-at snapshot. Exact proposition strings are local '
    'identifiers, not semantic equivalence or a global ontology.')
_REVISION = re.compile(r'I now believe (.+?) instead of (.+)\.?$')
_CHALLENGE = re.compile(r'I have received a challenge to my belief that (.+)\.?$')
_ACCEPT = re.compile(r'I accept that (.+)\.?$')
_REJECT = re.compile(r'I reject that (.+)\.?$')


def _stamp(value, *, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise ValueError('explicit timezone-aware source/system time required')
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('explicit ISO source/system time required') from exc
    if stamp.tzinfo is None:
        raise ValueError('timezone required')
    return stamp.astimezone(timezone.utc).isoformat()


def _project(evidence, actor):
    # v0.6 groups by event AND record time. Here disclosure time selects the
    # source version, but cannot order two simultaneous character statements.
    return project_subject_beliefs(
        [replace(e, system_record_time=e.valid_time) for e in evidence],
        subject_agent_id=actor)


@dataclass(frozen=True)
class SourceRecord:
    record_id: str
    version: int
    text: str
    event_time: str | None
    recorded_at: str
    permitted_observers: tuple[str, ...]
    access_time: str | None


@dataclass(frozen=True)
class RevisionSnapshot:
    payload_json: str

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, query, *, max_chars=64000):
        if (not isinstance(query, str) or not query.strip() or len(query) > 8000
                or type(max_chars) is not int or not 1000 <= max_chars <= 128000):
            raise ValueError('bounded ordinary query and context budget required')
        messages = [dict(role='system', content=_POLICY), dict(role='user',
            content=json.dumps(dict(query=query, cognition=self.payload), ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('revision context budget exceeded; no silent evidence truncation')
        return messages


class RevisionTimeline:
    """Append source versions; query event time separately from analyst record time."""
    def __init__(self, source_id, *, dialogue_blocks=False):
        if not isinstance(source_id, str) or not source_id.strip() or len(source_id) > 200 or type(dialogue_blocks) is not bool:
            raise ValueError('one explicit source-local identity domain required')
        self.source_id = source_id
        self.dialogue_blocks = dialogue_blocks
        self._records = {}

    def record(self, record_id, text, *, event_time, recorded_at,
               permitted_observers=(), access_time=None):
        if (not isinstance(record_id, str) or not record_id or len(record_id) > 200
                or not isinstance(text, str) or not text.strip() or len(text) > 4000
                or not isinstance(permitted_observers, tuple)
                or len(set(permitted_observers)) != len(permitted_observers)
                or any(not isinstance(a, str) or not a or a.lower() in _PRONOUNS for a in permitted_observers)):
            raise ValueError('bounded source text and explicit distinct observer identities required')
        event_time, recorded_at, access_time = (_stamp(event_time, optional=True),
            _stamp(recorded_at), _stamp(access_time, optional=True))
        prior = self._records.get(record_id, ())
        if prior and recorded_at <= prior[-1].recorded_at:
            raise ValueError('source correction must have a later system record time')
        if sum(len(v) for v in self._records.values()) >= 128:
            raise ValueError('record-version budget exceeded')
        if record_id not in self._records and len(self._records) >= 16:
            raise ValueError('snapshot source budget exceeded')
        record = SourceRecord(record_id, len(prior) + 1, text, event_time,
            recorded_at, permitted_observers, access_time)
        self._records[record_id] = (*prior, record)
        return record

    def snapshot(self, *, event_time, known_at, observer=None):
        event_time, known_at = _stamp(event_time), _stamp(known_at)
        if observer is not None and (not isinstance(observer, str) or not observer or observer.lower() in _PRONOUNS):
            raise ValueError('explicit observer required')
        selected = []
        for versions in self._records.values():
            known = [r for r in versions if r.recorded_at <= known_at]
            if not known:
                continue
            # Select the correction BEFORE event/access filtering: never resurrect
            # an obsolete version because its replacement is outside this view.
            record = known[-1]
            if record.event_time is not None and record.event_time > event_time:
                continue
            if observer is not None and (observer not in record.permitted_observers
                    or record.access_time is None or record.access_time > event_time):
                continue
            selected.append(record)
        selected.sort(key=lambda r: (r.event_time or '9999', r.record_id))
        core = EvidenceCore()
        sources = tuple(AuthorizedText(identity('timeline-source', self.source_id, r.record_id),
            r.text, version=r.version, permitted_observers=(observer,) if observer else (), order=i, event_time=r.event_time,
            access_time=r.access_time, record_time=r.recorded_at) for i, r in enumerate(selected, 1))
        semantic = prepare_semantics('What self-reports and revisions are explicit?', sources,
            core=core, scope=Scope(observer=observer, source_ids=tuple(s.source_id for s in sources)),
            dialogue_blocks=self.dialogue_blocks)
        evidence, transitions, diagnostics, prior, evidence_claims = [], [], [], {}, {}
        for record, source in zip(selected, sources):
            rows = [r for r in _local_candidates(source,dialogue_blocks=self.dialogue_blocks) if r['kind'] == 'event']
            if (len(rows) != 1 or rows[0]['quote'].strip() != record.text.strip()
                    or rows[0]['content']['assertion_scope'] != 'SOURCE_REPORT'
                    or rows[0]['content']['speaker_surface'].lower() in _PRONOUNS):
                diagnostics.append(dict(record_id=record.record_id, status='NO_UNAMBIGUOUS_SELF_REPORT'))
                continue
            row = rows[0]['content']
            actor, body = row['speaker_surface'], row['utterance'].rstrip('.!?')
            if record.event_time is None:
                diagnostics.append(dict(record_id=record.record_id, status='UNKNOWN_EVENT_TIME_NO_TEMPORAL_PROJECTION'))
                continue
            signal, proposition, old, kind = None, None, None, BeliefEvidenceKind.SELF_REPORT
            action = 'REPORTED_EXPRESSION'
            revision, challenge = _REVISION.fullmatch(body), _CHALLENGE.fullmatch(body)
            accept, reject = _ACCEPT.fullmatch(body), _REJECT.fullmatch(body)
            if revision:
                proposition, claimed_old = (v.rstrip('.!?').strip() for v in revision.groups())
                if not proposition or not claimed_old or proposition == claimed_old:
                    raise ValueError('distinct nonempty revision propositions required')
                anchors = [e for e in prior.get((actor, claimed_old), ())
                    if e.valid_time < record.event_time and e.signal == BeliefSignal.AFFIRM]
                # A prior explicit rejection/uncertainty or supersession defeats
                # the available anchor; merely finding an old affirmation is insufficient.
                states = {s.proposition_key: s for s in _project(
                    [e for e in evidence if e.valid_time < record.event_time], actor)}
                state = states.get(claimed_old)
                if anchors and state is not None and state.status.value == 'AFFIRMED':
                    old = claimed_old
                    action = 'REPORTED_CHARACTER_REVISION'
                else:
                    action = 'REPORTED_NEW_POSITION_WITHOUT_SUPPORTED_OLD_ANCHOR'
                signal = BeliefSignal.AFFIRM
            elif challenge:
                proposition = challenge[1].rstrip('.!?').strip()
                signal, kind, action = BeliefSignal.CHALLENGE, BeliefEvidenceKind.INFORMATION_EXPOSURE, 'REPORTED_CHALLENGE_RECEIPT_NOT_ACCEPTANCE'
            elif accept or reject:
                proposition = (accept or reject)[1].rstrip('.!?').strip()
                signal = BeliefSignal.AFFIRM if accept else BeliefSignal.DENY
                action = 'REPORTED_ACCEPTANCE' if accept else 'REPORTED_REJECTION'
            else:
                tree = parse_mental_proposition(body, actor)
                if (isinstance(tree, MentalProposition) and tree.holder == actor
                        and tree.attitude == Attitude.BELIEF and isinstance(tree.content, str)):
                    proposition, signal = tree.content, BeliefSignal(tree.polarity)
            if signal is None:
                diagnostics.append(dict(record_id=record.record_id, status='NO_DIRECT_BELIEF_INFERRED'))
                continue
            source_event = identity('timeline-event', self.source_id, asdict(record))
            item = BeliefEvidenceEvent(identity('timeline-evidence', source_event, actor, proposition, signal.value),
                actor, proposition, signal, kind, record.event_time, record.recorded_at,
                source_event, actor, supersedes_proposition_key=old, evidence_text=record.text)
            bindings = [cid for cid in semantic.candidate_ids
                if core.claims[cid].content['kind'] == 'event'
                and core.spans[core.claims[cid].content['source_span_id']].source_id == source.source_id]
            if len(bindings) != 1:
                raise ValueError('unique shared source binding required')
            claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
                dict(operation=action, evidence_id=item.evidence_id, actor=actor,
                    proposition=proposition, signal=signal.value, supersedes=old,
                    assumption='ACCURATE_SINCERE_SELF_REPORT', event_time=record.event_time))
            supports = [bindings[0]]
            if old:
                supports.extend(evidence_claims[e.evidence_id] for e in evidence
                    if e.subject_agent_id == actor and e.proposition_key == old)
            core.support(claim, *supports)
            evidence_claims[item.evidence_id] = claim
            evidence.append(item)
            prior.setdefault((actor, proposition), []).append(item)
            transitions.append(dict(record_id=record.record_id, source_event_id=source_event,
                evidence_id=item.evidence_id, dependency_claim_id=claim, actor=actor, operation=action, proposition=proposition,
                supersedes=old, event_time=record.event_time,
                source_version=record.version, recorded_at=record.recorded_at,
                private_state='CONDITIONAL_ON_ACCURATE_SINCERE_SELF_REPORT'))
        actors = sorted({e.subject_agent_id for e in evidence})
        states = []
        for actor in actors:
            for estimate in _project(evidence, actor):
                result = estimate.as_dict()
                # Normalized projector clock is not an actual system record time.
                result.pop('last_system_record_time')
                related = [e for e in evidence if e.subject_agent_id == actor and
                    (e.proposition_key == estimate.proposition_key or
                     e.supersedes_proposition_key == estimate.proposition_key)]
                result['latest_source_record_time'] = max(e.system_record_time for e in related)
                claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
                    dict(operation='BITEMPORAL_BELIEF_ESTIMATE', **result,
                        assumption='ACCURATE_SINCERE_SELF_REPORT'))
                core.support(claim, *(evidence_claims[e.evidence_id] for e in related))
                states.append(dict(result, dependency_claim_id=claim))
        payload = dict(source_id=self.source_id, event_time=event_time, known_at=known_at, observer=observer,
            records=[{k: v for k, v in asdict(r).items() if k != 'permitted_observers'} for r in selected], transitions=transitions, estimates=states,
            source_corrections=[dict(record_id=r.record_id, selected_version=r.version,
                operation='ANALYST_SOURCE_CORRECTION_NOT_CHARACTER_CHANGE') for r in selected if r.version > 1],
            semantic_receipt=core.receipt(semantic.scope), diagnostics=diagnostics,
            evidence=[dict(asdict(e), signal=e.signal.value, evidence_kind=e.evidence_kind.value) for e in evidence],
            policy=_POLICY, projection_time_policy='EVENT_TIME_ONLY_RECORD_TIME_SELECTS_SOURCE_VERSION', provider_calls=0)
        return RevisionSnapshot(json.dumps(payload, ensure_ascii=False, sort_keys=True))
