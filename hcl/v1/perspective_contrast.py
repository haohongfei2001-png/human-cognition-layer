"""Two source-bounded participant views; access is never pooled between them."""
import json
import re

from hcl.v04.model import EventRecord
from .belief_preparation import belief_narrative_events
from .cg04 import _TERM, _label
from .compact import compact_cognition_context, COMPACT_POLICY
from .composition import ComposedAnswer, ComposedAnswerReceipt
from .layer import HCLCognitionLayer
from .person_question import _refusal
from .router import CognitionRequest, PerspectiveMode
from .source_access import prepare_source_access, scope_source_access

_QUESTIONS = (
    re.compile(rf"Contrast (?P<a>{_TERM}) and (?P<b>{_TERM})'s views of (?P<item>{_TERM}) as (?P<term>{_TERM}) in (?P<context>{_TERM})[.?]?"),
    re.compile(rf'比较 (?P<a>{_TERM}) 与 (?P<b>{_TERM}) 在 (?P<context>{_TERM}) 中对 (?P<item>{_TERM}) 是否 (?P<term>{_TERM}) 的视角[。？]?'),
)
CONTRAST_POLICY = (
    'These participant views are independently projected from the same authorized '
    'source. Keep each actor evidence, public source declarations, nonpublic '
    'exposure, belief, uncertainty and unknown state separate. shared_available '
    'source IDs mean only a source/access basis in both views, not shared belief '
    'or understanding. direct_self_report is an expressed source stance, not '
    'verified private psychology or world truth. A narrator or third-party report '
    'does not become that participant direct self-report. Missing access does '
    'not prove ignorance or uncertainty. Describe supported differences without '
    'deception, irrationality, relationship change or moral blame. An observer '
    'contrast includes only what that observer can establish for each target. '
    'Never import reader-only material or evidence from one participant into another.'
)


def prepare_perspective_contrast(layer, query, source, *, observer_actor=None, as_of_statement=None,
                                 event_time=None, knowledge_cutoff=None, max_context_chars=64000):
    """Ordinary bilingual question -> two existing retained belief projections.

    Text needs exact narrated exposure. Typed raw EventRecords can retain explicit
    upstream public/access/time declarations; neither path supplies mental gold.
    """
    if (not isinstance(layer, HCLCognitionLayer) or layer.intentions is not None or layer.affects is not None or
        not isinstance(query, str) or not query.strip() or len(query) > 16000 or
        type(max_context_chars) is not int or not 512 <= max_context_chars <= 64000):
        raise ValueError('request-local layer, ordinary question and bounded context required')
    if observer_actor is not None:
        _label(observer_actor)
        if observer_actor == 'Narrator':
            raise ValueError('named character observer required')
    mode = PerspectiveMode.OBSERVER_ABOUT_TARGET if observer_actor else PerspectiveMode.CHARACTER_PERSPECTIVE
    def refuse(reason):
        return _refusal(query, '', mode, reason, max_context_chars=max_context_chars, preserve_reader_source=False)
    original_query = query
    prefix = (re.fullmatch(r'At statement ([1-9][0-9]?), (.+)', query.strip()) or
              re.fullmatch(r'截至第 ([1-9][0-9]?) 条陈述，(.+)', query.strip()))
    if prefix:
        if as_of_statement is not None and as_of_statement != int(prefix[1]):
            return refuse('conflicting_source_order_scope')
        as_of_statement, query = int(prefix[1]), prefix[2]
    elif query.strip().startswith(('At statement', '截至第')):
        return refuse('unsupported_source_order_scope')
    matches = [m.groupdict() for p in _QUESTIONS if (m := p.fullmatch(query.strip()))]
    if (len(matches) != 1 or matches[0]['a'] == matches[0]['b'] or
        'Narrator' in (matches[0]['a'], matches[0]['b'])):
        return refuse('unsupported_or_ambiguous_participant_contrast')
    task = matches[0]
    scope = None
    if isinstance(source, str):
        lines = [line.strip() for line in source.splitlines() if line.strip()]
        if (not 1 <= len(lines) <= 24 or len(source) > 16000 or any(len(line) > 2000 for line in lines) or
            event_time is not None or knowledge_cutoff is not None):
            return refuse('bounded_ordered_ordinary_contrast_source_required')
        if as_of_statement is not None:
            if type(as_of_statement) is not int or not 1 <= as_of_statement <= len(lines):
                return refuse('source_order_scope_out_of_bounds')
            lines = lines[:as_of_statement]
            scope = dict(kind='SOURCE_STATEMENT_ORDER_ONLY', through_statement=as_of_statement,
                         calendar_time='NOT_ESTABLISHED')
        source = '\n'.join(lines)
        events, access = prepare_source_access(belief_narrative_events(source))
        common = dict(narrative=source, narrative_access=True)
    elif (isinstance(source, tuple) and 1 <= len(source) <= 24 and
          all(isinstance(e, EventRecord) and isinstance(e.raw_text, str) for e in source) and
          sum(len(e.raw_text) for e in source) <= 16000):
        if as_of_statement is not None:
            return refuse('typed_time_and_statement_scope_must_not_mix')
        for event in source:
            if (not isinstance(event.raw_text, str) or not 1 <= len(event.raw_text) <= 2000 or
                any(k in event.metadata and type(event.metadata[k]) is not bool for k in ('public', 'reader_only'))):
                return refuse('invalid_explicit_source_access_metadata')
        events = scope_source_access(source, event_time=event_time, knowledge_cutoff=knowledge_cutoff)
        access = dict(status='EXPLICIT_UPSTREAM_SOURCE_ACCESS_DECLARATIONS_NOT_VERIFIED_RECEIPTS')
        common = dict(evidence=source, event_time=event_time, knowledge_cutoff=knowledge_cutoff)
    else:
        return refuse('bounded_explicit_contrast_source_required')
    stages = tuple(layer.prepare(CognitionRequest(original_query, target_actor=actor,
        observer_actor=observer_actor, perspective_mode=mode, belief_analysis=True,
        compact_context=True, max_context_chars=max_context_chars, **common))
        for actor in (task['a'], task['b']))
    sources = {e.event_id: e for e in events}
    claim = '/'.join(task[k] for k in ('context', 'item', 'term'))
    participants, direct_status = [], []
    available = []
    for actor, stage in zip((task['a'], task['b']), stages):
        context = stage.context.as_dict()
        visible = {e['event_id'] for e in context['evidence']}
        public = {eid for eid in visible if bool(sources[eid].metadata.get('public'))}
        available.append(visible)
        estimates = [b for b in context['belief'] if b['subject_agent_id'] == actor and b['proposition_key'] == claim]
        basis = {eid for b in estimates for eid in b['basis_evidence_ids']}
        provenance = [p for p in context['provenance'] if p.get('evidence_id') in basis]
        direct = bool(estimates and provenance and len(provenance) == len(basis) and all(p['evidence_level'] == 'DIRECT_SELF_REPORT' for p in provenance))
        status = estimates[0]['status'] if estimates else 'SYSTEM_INSUFFICIENT'
        direct_status.append(status if direct and status in ('AFFIRMED', 'DENIED', 'CHARACTER_UNCERTAIN') else None)
        context['preparation'] = dict(context['preparation'], answer_provider_calls=0,
            answer_execution='DEFERRED_TO_SINGLE_CONTRAST_ANSWER')
        participants.append(dict(actor_id=actor, cognition_context=compact_cognition_context(context),
            claim_estimate=estimates, direct_self_report=direct,
            evidence_boundary=dict(available_source_event_ids=sorted(visible),
                public_source_event_ids=sorted(public), nonpublic_available_source_event_ids=sorted(visible - public),
                unmentioned_access='UNKNOWN', exposure_implies_belief=False)))
    relation = ('SAME_EXPLICIT_SELF_REPORT_STANCE' if direct_status[0] == direct_status[1]
                else 'DIFFERENT_EXPLICIT_SELF_REPORT_STANCES') if all(direct_status) else 'UNRESOLVED_PARTICIPANT_COMPARISON'
    state = dict(task_scope=task, observer_actor=observer_actor, perspective_mode=mode.value,
        participants=participants, relation=relation,
        shared_available_source_event_ids=sorted(available[0] & available[1]),
        access_basis=access['status'], source_order_scope=scope,
        calendar_time='UPSTREAM_DECLARED_ONLY' if isinstance(source, tuple) else 'NOT_ESTABLISHED',
        world_truth='NOT_ESTABLISHED', moral_blame='NOT_INFERRED')
    failure = None
    if len(json.dumps(state, ensure_ascii=False, sort_keys=True)) > max_context_chars:
        failure = 'participant_contrast_context_budget_exceeded'
        state = dict(participants=[], uncertainty=[dict(status='SYSTEM_INSUFFICIENT', reason=failure)])
    policies = tuple(dict.fromkeys(s.messages[0]['content'] for s in stages))
    policy = ' '.join(policies).replace(COMPACT_POLICY, '').strip() + ' ' + COMPACT_POLICY + ' ' + CONTRAST_POLICY
    messages = (dict(role='system', content=policy), dict(role='user', content=json.dumps(
        dict(query=original_query, perspective_contrast=state), ensure_ascii=False, sort_keys=True)))
    receipt = dict(method='retained_source_bounded_participant_contrast', task_scope=task, failure=failure,
        extraction_provider_calls=0, answer_provider_calls=1, provider_calls_executed=0,
        evidence_class='PROVIDER_FREE_INTEGRATION_NOT_EXTERNAL_EFFICACY',
        stage_preparation=[dict(s.preparation_receipt, answer_provider_calls=0, preparation_only=True) for s in stages],
        actual_final_messages=list(messages), longmemeval='SEALED_NOT_ACCESSED')
    return ComposedAnswer(tuple(s.plan for s in stages), stages, messages, receipt)


def answer_perspective_contrast(layer, query, source, *, debug=False, **kwargs):
    prepared = prepare_perspective_contrast(layer, query, source, **kwargs)
    answer = (layer.base_model(list(prepared.messages)) if callable(layer.base_model)
              else layer.base_model.complete(list(prepared.messages)))
    if not isinstance(answer, str):
        raise TypeError('base model adapter must return an answer string')
    return ComposedAnswerReceipt(answer, prepared) if debug else answer
