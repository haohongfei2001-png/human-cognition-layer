"""Competing source-conditioned communication explanations, not deception labels."""
from dataclasses import dataclass
import json
import re

from .agency_chain import SemanticWorkspace
from .communication import CommunicationScene
from .core import ClaimKind
from .epistemic import Attitude, MentalProposition, parse_mental_proposition
from .plan_feasibility import prepare_plan_feasibility, _literal

_NAME = r'[A-Z][\w-]*'
_QUERY = re.compile(rf"How might (?P<speaker>{_NAME})'s statement to (?P<recipient>{_NAME}) that (?P<content>[^?]+) be explained\?")
_TRUTH = re.compile(rf"(?P<speaker>{_NAME})'s statement that (?P<content>.+) is (?P<value>true|false)")
_OMITTED = re.compile(rf"(?P<speaker>{_NAME})'s statement that (?P<statement>.+?) omitted that (?P<content>.+)")
_POLICY = ('These are competing conditional communication explanations, not actual motives '
    'or deception verdicts. False content alone establishes neither speaker knowledge '
    'nor intent. Belief, knowledge claim, goal, literal truth, omission and recipient '
    'information need are separate premises. Source claims and sincerity are unverified. '
    'A literally true utterance can coexist with conditional concealment concerns. '
    'No moral verdict, global trust score or unique strategy is inferred. Later speaker '
    'knowledge or goals do not backfill the source-order action prefix.')


def _condition(values, expected=True):
    return 'CONFLICT' if len(values) > 1 else 'SUPPORTED' if values == {expected} else 'CONTRADICTED' if values == {not expected} else 'UNKNOWN'


@dataclass(frozen=True)
class StrategicCommunication:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded strategy context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('strategy source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('strategy support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('strategy context budget exceeded')
        return messages


def prepare_strategic_communication(workspace, query, *, source_id, observer=None):
    question = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not question or question['speaker'] == question['recipient'] or len(question['content']) > 250:
        raise ValueError('bounded distinct speaker/recipient statement question required')
    speaker, recipient, proposition = question['speaker'], question['recipient'], question['content']
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, rows = workspace.core, []
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    original = workspace._documents[source_id][0] if versions else ''
    for candidate in semantic.candidate_ids:
        content = core.claims[candidate].content
        if content['kind'] != 'event' or content['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        row, span = content['proposal'], core.spans[content['source_span_id']]
        narrator = row['speaker_surface'] == 'Narrator' and span.quote.startswith('Narrator:')
        if row['assertion_scope'] != 'SOURCE_REPORT' or (not narrator and row['speaker_candidates'] != [row['speaker_surface']]):
            continue
        rows.append(dict(candidate=candidate, speaker=row['speaker_surface'], body=row['utterance'].rstrip('.!?'),
            start=span.start, quote=span.quote, narrator=narrator, line=original[:span.start].count('\n') + 1))
    rows.sort(key=lambda r: r['start'])
    if len(rows) > 20:
        raise ValueError('strategy source budget exceeded')
    actions = [r for r in rows if r['speaker'] == speaker and r['body'] == f'{recipient}, {proposition}']
    if len(actions) > 1:
        raise ValueError('multiple statement episodes; narrow source')
    if not actions:
        return StrategicCommunication(versions, json.dumps(dict(query=query, status='SYSTEM_INSUFFICIENT',
            reason='no_unambiguous_visible_addressed_utterance', original_source=original, explanations=[], policy=_POLICY), sort_keys=True), ())
    action = actions[0]
    prefix_rows = [r for r in rows if r['start'] < action['start']]
    prefix_text = original[:action['start']].strip()
    prefix_state = dict(reported_belief_states=[], agency=dict(goals=[]))
    if prefix_text:
        local = SemanticWorkspace()
        local.put_source(source_id, prefix_text)
        prefix_state = prepare_plan_feasibility(local, f"Could {speaker}'s plans work under their beliefs and the declared model?", source_id=source_id).payload
    beliefs = prefix_state['reported_belief_states']
    def belief_state(p, expected=True):
        relevant = [b for b in beliefs if _literal(b['proposition_key'])[0] == p]
        values = {_literal(b['proposition_key'])[1] for b in relevant if b['status'] == 'AFFIRMED'}
        if any(b['status'] in ('CONFLICT', 'CHARACTER_UNCERTAIN') or b['unresolved_challenge_evidence_ids'] for b in relevant):
            return 'CONFLICT' if len(values) > 1 else 'UNKNOWN'
        return _condition(values, expected)
    def goal_state(goal):
        relevant = [g for g in prefix_state['agency']['goals'] if g['goal'] == goal]
        statuses = {g['status'] for g in relevant}
        return 'SUPPORTED' if statuses == {'ACTIVE'} else 'CONTRADICTED' if statuses and statuses <= {'ABANDONED', 'COMPLETED'} else 'UNKNOWN'
    truth, omissions, knowledge = [], [], []
    for row in rows:
        fact, omitted = _TRUTH.fullmatch(row['body']), _OMITTED.fullmatch(row['body'])
        if row['narrator'] and fact and fact['speaker'] == speaker and fact['content'] == proposition:
            truth.append(dict(value=fact['value'] == 'true', source_claim_id=row['candidate']))
        if row['narrator'] and omitted and omitted['speaker'] == speaker and omitted['statement'] == proposition:
            omissions.append(dict(content=omitted['content'], source_claim_id=row['candidate']))
        if row not in prefix_rows or row['speaker'] != speaker:
            continue
        tree = parse_mental_proposition(row['body'], speaker)
        if isinstance(tree, MentalProposition) and tree.attitude == Attitude.KNOWLEDGE and isinstance(tree.content, str):
            knowledge.append(dict(content=tree.content, polarity=tree.polarity, source_claim_id=row['candidate'], authority='SELF_REPORTED_KNOWLEDGE_NOT_PRIVATE_TRUTH'))
    omitted_keys = {o['content'] for o in omissions}
    if len(omitted_keys) > 1:
        raise ValueError('multiple omitted propositions; narrow communication episode')
    omitted = next(iter(omitted_keys), None)
    known_values = {k['polarity'] == 'AFFIRM' for k in knowledge if k['content'] == omitted and k['polarity'] != 'UNCERTAIN'}
    conceal_goal = goal_state(f'keep {recipient} from learning that {omitted}') if omitted else 'UNKNOWN'
    scene = CommunicationScene(original, source_id=source_id)
    needs = [r for r in prefix_rows if r['speaker'] == recipient and r['body'] == f'I need to know whether {omitted}'] if omitted else []
    view = scene.view(speaker, through_line=action['line'])
    received_needs = [r for r in needs if any(a['statement_line'] == r['line'] and a['content_transmitted'] for a in view.access_audit)]
    truth_values = {r['value'] for r in truth}
    conditions = dict(literal_false=_condition(truth_values, False), literal_true=_condition(truth_values),
        reported_belief_in_content=belief_state(proposition), reported_belief_opposite=belief_state(proposition, False),
        recipient_belief_goal=goal_state(f'make {recipient} believe {proposition}'),
        explicit_omission='SUPPORTED' if omitted else 'UNKNOWN', reported_knowledge_of_omission=_condition(known_values),
        concealment_goal=conceal_goal, recipient_information_need_received='SUPPORTED' if received_needs else 'UNKNOWN')
    specifications = dict(BENIGN_ERROR=('literal_false', 'reported_belief_in_content'),
        DELIBERATE_FALSEHOOD=('literal_false', 'reported_belief_opposite', 'recipient_belief_goal'),
        CONCEALMENT=('explicit_omission', 'reported_knowledge_of_omission', 'concealment_goal', 'recipient_information_need_received'),
        LITERALLY_TRUE_POTENTIALLY_MISLEADING=('literal_true', 'explicit_omission', 'reported_knowledge_of_omission', 'concealment_goal', 'recipient_information_need_received'))
    explanations, claims = [], []
    for kind, required in specifications.items():
        checks = {key: conditions[key] for key in required}
        values = set(checks.values())
        disposition = ('CONFLICTING_PREMISES' if 'CONFLICT' in values else 'WEAKENED_BY_COUNTEREVIDENCE' if 'CONTRADICTED' in values else
            'CONDITIONALLY_SUPPORTED' if values == {'SUPPORTED'} else 'UNRESOLVED')
        result = dict(hypothesis=kind, conditions=checks, disposition=disposition,
            actual_strategy='NOT_ESTABLISHED', assumptions=['source_accuracy', 'self_report_sincerity', 'source_order_as_action_prefix'])
        claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='COMPETING_COMMUNICATION_CONDITIONS', **result))
        core.support(claim, *(r['candidate'] for r in rows))
        claims.append(claim)
        explanations.append(dict(result, claim_id=claim))
    payload = dict(query=query, original_source=original, statement=action, status='CHECKED_COMPETING_EXPLANATIONS',
        explanations=explanations, source_truth_claims=truth, omission_reports=omissions,
        prefix_beliefs=beliefs, prefix_goals=prefix_state['agency']['goals'], prefix_knowledge_claims=knowledge,
        recipient_need_evidence=received_needs, actual_deception='NOT_ESTABLISHED', moral_verdict='NOT_INFERRED',
        unique_motive='NOT_INFERRED', recipient_belief_change='NOT_ESTABLISHED', policy=_POLICY)
    return StrategicCommunication(versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
