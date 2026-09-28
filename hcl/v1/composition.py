"""Compose existing source-scoped operations; never infer bridges between them."""
from dataclasses import dataclass
from datetime import datetime
import json

from .compact import compact_cognition_context, COMPACT_POLICY
from .context import ANSWER_POLICY
from .source_pool import pool_composed_sources, POOL_POLICY
from .layer import HCLCognitionLayer
from .router import CognitionRequest, PerspectiveMode

COMPOSITION_POLICY = (
    'The operations below analyze the same authorized source and focal actor. '
    'Keep each operation scope and its uncertainty distinct. Combine them to '
    'answer the question, without treating local concept criteria as preferences, '
    'preferences as intention/control, or any source claim as a moral conclusion. '
    'A responsibility explanation remains conditional on that operation caller '
    'premise. Failure or missing state in one operation is unresolved, not support '
    'from another. Never transfer evidence across operation access boundaries.'
)

COMPARISON_POLICY = (
    'belief_concept_comparison compares an explicitly expressed self-report '
    'with the same actor/context/item/term local criteria only. Consistency or '
    'difference describes source assertions, never whether a private belief is '
    'true, a shared meaning, irrationality, deception, intention or moral truth. '
    'Later definitions/properties cannot establish a mismatch at an earlier '
    'self-report. Missing, conflicting, indirect or hidden evidence stays unresolved.'
)


@dataclass(frozen=True)
class ComposedAnswer:
    plans: tuple
    stages: tuple
    messages: tuple[dict, ...]
    preparation_receipt: dict


@dataclass(frozen=True)
class ComposedAnswerReceipt:
    answer: str
    prepared: ComposedAnswer


def _operation(plan):
    active = [name for name, yes in (
        ('responsibility', plan.responsibility_structure),
        ('preferences', plan.contextual_preference),
        ('belief', plan.belief_preparation),
        ('concepts', plan.concept_interpretation)) if yes]
    if len(active) != 1:
        raise ValueError('composition requires explicit retained belief or existing CG03/04/05 operations')
    return active[0]


def _compare_belief_concepts(stages, operations):
    """Explain existing source states; never promote evidence across operations."""
    if 'belief' not in operations or 'concepts' not in operations:
        raise ValueError('explicit comparison requires retained belief and concept stages')
    belief = stages[operations.index('belief')].context
    concept = stages[operations.index('concepts')].context
    checked = concept.concepts.get('checked', {})
    scenario = checked.get('scenario', {})
    focal = concept.concepts.get('case_input', {}).get('actor_id')
    rows = []
    parse = lambda stamp: datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    for b in belief.belief:
        if (b['subject_agent_id'] != focal or
            b['proposition_key'] != '/'.join(scenario.get(k, '') for k in ('context', 'item', 'term'))):
            continue
        # Basis must be an available self-report, not a narrator/private-state
        # attribution or a later indirect report that updates last_valid_time.
        provenance = [p for p in belief.provenance if p.get('evidence_id') in b['basis_evidence_ids']]
        source_ids = [p['source_event_id'] for p in provenance if p['evidence_level'] == 'DIRECT_SELF_REPORT']
        sources = [e for e in belief.evidence if e['event_id'] in source_ids and e['actor_id'] == focal]
        for d in checked.get('readings', []):
            if (d['definition_id'] not in checked.get('focal_reading_ids', []) or
                d['actor_id'] != focal or d['authority'] != 'DIRECT_SELF_REPORT'):
                continue
            basis = [d['source_event_id']]
            basis.extend(eid for c in d['criterion_checks'] for eid in c['source_event_ids'])
            basis.extend(d['application_source_ids'])
            concept_sources = [e for e in concept.evidence if e['event_id'] in basis]
            relation = 'UNRESOLVED_SOURCE_COMPARISON'
            if b['status'] == 'AFFIRMED' and sources and len(provenance) == len(sources):
                report_time = max(parse(e['valid_time']) for e in sources)
                report_record = max(parse(e['recorded_at']) for e in sources)
                if len({e['event_id'] for e in concept_sources}) != len(set(basis)):
                    relation = 'UNRESOLVED_SOURCE_COMPARISON'
                elif any(parse(e['valid_time']) > report_time or parse(e['recorded_at']) > report_record for e in concept_sources):
                    relation = 'LATER_CONTEXT_NOT_EVIDENCE_OF_EARLIER_BELIEF'
                elif d['state'] == 'CRITERIA_MET':
                    relation = 'CONSISTENT_WITH_LOCAL_SOURCE_CRITERIA'
                elif d['state'] == 'CRITERIA_NOT_MET':
                    relation = 'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA'
                elif d['state'] == 'DECLARED_COUNTEREXAMPLE':
                    relation = 'DIFFERS_FROM_EXPLICIT_LOCAL_APPLICATION'
            rows.append(dict(actor_id=focal, context=scenario['context'], item=scenario['item'], term=scenario['term'],
                belief_status=b['status'], belief_basis_evidence_ids=list(b['basis_evidence_ids']),
                belief_source_event_ids=[e['event_id'] for e in sources],
                definition_id=d['definition_id'], concept_state=d['state'],
                concept_source_event_ids=list(dict.fromkeys(basis)), relation=relation,
                scope='SOURCE_COMPARISON_NOT_PRIVATE_WORLD_OR_MORAL_TRUTH'))
    return dict(status='SOURCE_SCOPED_COMPARISON' if rows else 'NO_COMPARABLE_VISIBLE_SELF_REPORT_AND_LOCAL_READING',
        reading_relation=checked.get('reading_relation', 'NO_SOURCE_READING'),
        rows=rows, unsupported_inferences=['belief is false', 'shared meaning', 'deception', 'irrationality',
            'private intention', 'moral truth'])


def prepare_composed_answer(layer, query, requests, *, max_context_chars=48000, compact_context=True, pool_sources=False,
                            compare_belief_concepts=False):
    """Prepare 2–3 existing operations, from a common source, with no model calls."""
    if not isinstance(layer, HCLCognitionLayer):
        raise ValueError('existing cognition layer required')
    if not isinstance(query, str) or not query.strip() or len(query) > 16000:
        raise ValueError('bounded composed question required')
    if (not isinstance(requests, tuple) or not 2 <= len(requests) <= 3 or
        not all(isinstance(r, CognitionRequest) for r in requests)):
        raise ValueError('two or three bounded existing operation requests required')
    if (type(max_context_chars) is not int or not 512 <= max_context_chars <= 64000 or
        any(type(flag) is not bool for flag in (compact_context, pool_sources, compare_belief_concepts))):
        raise ValueError('bounded composition context and explicit encoding required')
    first = requests[0]
    if not first.target_actor or not (first.narrative or first.evidence):
        raise ValueError('one focal actor and authorized shared source required')
    signature = lambda r: (r.target_actor, r.observer_actor, r.event_time, r.knowledge_cutoff, r.narrative, r.evidence, r.narrative_access)
    if any(signature(r) != signature(first) for r in requests):
        raise ValueError('operations must share exact actor, observer, source and time scope')
    if any(r.allow_semantic_preparation or r.tools for r in requests):
        raise ValueError('composition cannot schedule extraction or formal tools')
    plans = tuple(layer.router.plan(r) for r in requests)
    operations = tuple(_operation(p) for p in plans)
    if len(set(operations)) != len(operations) or len({p.perspective_mode for p in plans}) != 1:
        raise ValueError('distinct operations with identical perspective required')
    mode = plans[0].perspective_mode
    # Existing prose paths have different historical speaker-access assumptions.
    # Do not infer an access channel while joining them: ordinary input is reader
    # analysis; private views need shared validated typed EventRecords.
    if first.narrative and mode != PerspectiveMode.READER_ANALYSIS and not first.narrative_access:
        raise ValueError('ordinary composition requires reader analysis; private views need typed access')
    if layer.intentions is not None or layer.affects is not None:
        raise ValueError('composition requires request-local state; injected persistent views need explicit scoped integration')
    stages = tuple(layer.prepare(r) for r in requests)
    contexts = []
    for p in stages:
        row = p.context.as_dict()
        row['preparation'] = dict(row['preparation'], answer_provider_calls=0,
            answer_execution='DEFERRED_TO_SINGLE_COMPOSED_ANSWER')
        contexts.append(compact_cognition_context(row) if compact_context else row)
    state = dict(focal_actor=first.target_actor, perspective_mode=mode.value,
        observer_actor=first.observer_actor,
        temporal_scope={'event_time': first.event_time, 'knowledge_cutoff': first.knowledge_cutoff},
        operation_contexts=[dict(operation=op, cognition_context=row) for op, row in zip(operations, contexts)],
        cross_operation_inference='NO_AUTOMATIC_CONCEPT_PREFERENCE_INTENTION_OR_MORAL_PROMOTION')
    if compare_belief_concepts:
        state['belief_concept_comparison'] = _compare_belief_concepts(stages, operations)
    if pool_sources:
        state = pool_composed_sources(state)
    serialized = json.dumps(state, ensure_ascii=False, sort_keys=True)
    failure = None
    if len(serialized) > max_context_chars:
        failure = 'composition_context_budget_exceeded'
        state = dict(focal_actor=first.target_actor, perspective_mode=mode.value,
            temporal_scope=state['temporal_scope'], operation_contexts=[],
            uncertainty=[dict(status='SYSTEM_INSUFFICIENT', reason='composition context budget exceeded; narrow the shared source')])
    policies = tuple(dict.fromkeys(p.messages[0]['content'] for p in stages))
    # One policy per actual operation, avoiding multiple copies of shared policy.
    additions = [p.removeprefix(ANSWER_POLICY).strip() for p in policies]
    policy = ANSWER_POLICY + ' ' + ' '.join(a for a in additions if a) + ' ' + COMPOSITION_POLICY
    if compact_context:
        # A compact stage may already carry this policy; include it once only.
        policy = policy.replace(COMPACT_POLICY, '').strip() + ' ' + COMPACT_POLICY
    if 'source_pool_encoding' in state:
        policy += ' ' + POOL_POLICY
    if compare_belief_concepts:
        policy += ' ' + COMPARISON_POLICY
    messages = (dict(role='system', content=policy), dict(role='user', content=json.dumps(
        {'query': query, 'composed_cognition': state}, ensure_ascii=False, sort_keys=True)))
    receipt = dict(method='existing_capability_composition', operations=list(operations),
        failure=failure, extraction_provider_calls=0, answer_provider_calls=1,
        evidence_class='PROVIDER_FREE_INTEGRATION_NOT_EXTERNAL_EFFICACY',
        stage_preparation=[dict(p.preparation_receipt, answer_provider_calls=0, preparation_only=True) for p in stages],
        actual_final_messages=list(messages), longmemeval='SEALED_NOT_ACCESSED')
    return ComposedAnswer(plans, stages, messages, receipt)


def answer_composed(layer, query, requests, *, debug=False, **kwargs):
    prepared = prepare_composed_answer(layer, query, requests, **kwargs)
    answer = (layer.base_model(list(prepared.messages)) if callable(layer.base_model)
              else layer.base_model.complete(list(prepared.messages)))
    if not isinstance(answer, str):
        raise TypeError('base model adapter must return an answer string')
    return ComposedAnswerReceipt(answer, prepared) if debug else answer
