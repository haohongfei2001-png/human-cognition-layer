"""Local expectation repair across access, condition, meaning and role evidence."""
from dataclasses import dataclass
import json
import re

from hcl.v1.cg05 import prepare_concept_narrative, check_concepts
from .commitments import prepare_commitment
from .communication import CommunicationScene
from .core import ClaimKind

_NAME = r'[A-Z][\w-]*'
_TERM = r'[A-Za-z][A-Za-z0-9_-]{0,31}'
_QUERY = re.compile(rf"Explain (?P<recipient>{_NAME})'s expectation of (?P<speaker>{_NAME})'s promise to (?P<action>.+?) in (?P<context>{_TERM}), using (?P<term>{_TERM}) for (?P<item>{_TERM})\.")
_EXPECT = re.compile(rf'I (?P<now>now )?expect (?P<speaker>{_NAME}) to (?P<action>.+?)(?: if (?P<condition>.+))?')
_CLARIFY = re.compile(rf'I clarify to (?P<recipient>{_NAME}) that my promise to (?P<action>.+?) still requires that (?P<condition>.+)')
_ROLE = re.compile(rf'As (?P<role>{_TERM}) in (?P<context>{_TERM}), I expect (?P<speaker>{_NAME}) to (?P<action>.+)')
_POLICY = ('Localize possible expectation mismatch factors without establishing blame. '
    'Condition omission, non-receipt, differing local meanings and self-reported role '
    'expectation are separate. Different meanings do not prove a misunderstanding caused '
    'the behavior. Clarification receipt is not acceptance or repaired understanding. '
    'An explicit revised expectation does not rewrite the original promise or restore '
    'trust. Analyst explanation revision is not proof of a private psychological change.')


@dataclass(frozen=True)
class MisunderstandingResult:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded misunderstanding context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('misunderstanding source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('misunderstanding support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('misunderstanding context budget exceeded')
        return messages


def prepare_misunderstanding(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not match or match['term'] not in match['action'].split() or len(match['action']) > 200:
        raise ValueError('bounded promise, context and explicitly relevant local term required')
    speaker, recipient, action = match['speaker'], match['recipient'], match['action']
    social = prepare_commitment(workspace, f"What is the status of {speaker}'s promise to {recipient} to {action}?", source_id=source_id, observer=observer)
    if social.payload['status'] == 'SYSTEM_INSUFFICIENT':
        return MisunderstandingResult(social.source_versions, json.dumps(dict(query=query, status='SYSTEM_INSUFFICIENT', original_source=social.payload['original_source'], policy=_POLICY), sort_keys=True), ())
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, rows = workspace.core, []
    original = social.payload['original_source']
    for candidate in semantic.candidate_ids:
        c = core.claims[candidate].content
        if c['kind'] != 'event' or c['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        row, span = c['proposal'], core.spans[c['source_span_id']]
        narrator = row['speaker_surface'] == 'Narrator' and span.quote.startswith('Narrator:')
        if row['assertion_scope'] != 'SOURCE_REPORT' or (not narrator and row['speaker_candidates'] != [row['speaker_surface']]):
            continue
        rows.append(dict(candidate=candidate, speaker=row['speaker_surface'], body=row['utterance'].rstrip('.!?'),
            quote=span.quote, line=original[:span.start].count('\n') + 1))
    rows.sort(key=lambda r: r['line'])
    expectations, clarifications, roles = [], [], []
    condition = social.payload['commitment']['original_promise']['conditions'][0]['key']
    promise_quote = social.payload['commitment']['original_promise']['quote']
    promise_line = next(r['line'] for r in rows if r['quote'] == promise_quote)
    for row in rows:
        expected, clarification, role = _EXPECT.fullmatch(row['body']), _CLARIFY.fullmatch(row['body']), _ROLE.fullmatch(row['body'])
        if row['line'] <= promise_line:
            continue
        if expected and row['speaker'] == recipient and expected['speaker'] == speaker and expected['action'] == action:
            expectations.append(dict(row, condition=expected['condition'], explicit_revision=bool(expected['now'])))
        if clarification and row['speaker'] == speaker and clarification['recipient'] == recipient and clarification['action'] == action:
            clarifications.append(dict(row, condition=clarification['condition'], preserves_original_condition=clarification['condition'] == condition))
        if role and row['speaker'] == recipient and role['speaker'] == speaker and role['action'] == action and role['context'] == match['context']:
            roles.append(dict(row, role=role['role'], authority='SELF_REPORTED_ROLE_EXPECTATION_NOT_INSTITUTIONAL_RULE'))
    if len(expectations) > 2 or len(clarifications) > 2:
        raise ValueError('bounded initial/revised expectation and two clarifications required')
    if sum(not e['explicit_revision'] for e in expectations) > 1:
        raise ValueError('multiple unlinked expectations; use explicit revision')
    initial = next((e for e in expectations if not e['explicit_revision']), None)
    revised = [e for e in expectations if e['explicit_revision'] and initial and e['line'] > initial['line']]
    scene = CommunicationScene(original, source_id=source_id)
    def receipt(line, cutoff):
        audit = next(a for a in scene.view(recipient, through_line=cutoff).access_audit if a['statement_line'] == line)
        return dict(status=audit['status'], received=audit['content_transmitted'])
    def meanings(cutoff):
        bindings = [dict(source_claim_id=r['candidate'], original_quote=r['quote'], derived_line=f"{r['speaker']}: {r['body']}.")
            for r in rows if r['line'] <= cutoff and r['body'].startswith(f"In {match['context']}, ")]
        if not bindings:
            return dict(status='NO_LOCAL_DEFINITION', readings=[], bindings=[])
        prepared = prepare_concept_narrative('\n'.join(b['derived_line'] for b in bindings), speaker, match['context'], match['term'], match['item'])
        if prepared.case is None:
            return dict(status=prepared.failure, readings=[], bindings=bindings)
        native = check_concepts(prepared.case, prepared.events)
        readings = [r for r in native['readings'] if r['actor_id'] in (speaker, recipient) and r['state'] not in ('SUPERSEDED_LOCAL', 'OTHER_SCOPE', 'ATTRIBUTED_ONLY')]
        signatures = {actor: {tuple(sorted((c['key'], c['value']) for c in r['criteria'])) for r in readings if r['actor_id'] == actor} for actor in (speaker, recipient)}
        differs = bool(signatures[speaker] and signatures[recipient] and signatures[speaker] != signatures[recipient])
        return dict(status='DIFFERING_SOURCE_LOCAL_CRITERIA' if differs else 'NO_ESTABLISHED_DIFFERENCE', readings=readings,
            bindings=bindings, causal_misunderstanding='NOT_ESTABLISHED', shared_meaning='NOT_ESTABLISHED')
    at_initial = initial['line'] if initial else promise_line
    initial_meaning = meanings(at_initial)
    exposure = receipt(promise_line, at_initial)
    factors = dict(condition_omitted=bool(initial and initial['condition'] != condition),
        original_condition_receipt=exposure, local_meaning=initial_meaning,
        role_expectations=[r for r in roles if r['line'] <= at_initial], causes='COMPETING_SOURCE_FACTORS_NOT_PROVEN_CAUSES')
    old = core.claim(semantic.scope, ClaimKind.SYSTEM_INTERPRETATION,
        dict(operation='INITIAL_EXPECTATION_MISMATCH_FACTORS', factors=factors))
    core.support(old, *(r['candidate'] for r in rows if r['line'] <= at_initial))
    core.interpret(old, unknown_conditions=('source_accuracy', 'private_understanding'))
    available = [dict(c, receipt=receipt(c['line'], len(scene.lines))) for c in clarifications if c['preserves_original_condition']]
    accepted_revisions = []
    for revision in revised:
        preceding = [c for c in clarifications if c['preserves_original_condition'] and c['line'] < revision['line']]
        received = [c for c in preceding if receipt(c['line'], revision['line'])['received']]
        aligned = revision['condition'] == condition
        state = ('REVISED_EXPECTATION_ALIGNS_CLARIFICATION_AVAILABLE' if aligned and received else
            'REVISED_EXPECTATION_ALIGNS_CAUSE_UNRESOLVED' if aligned else 'REVISED_EXPECTATION_STILL_DIFFERS')
        accepted_revisions.append(dict(revision, status=state, clarification_source_ids=[c['candidate'] for c in received], cause='NOT_PROVEN'))
    status = (accepted_revisions[-1]['status'] if accepted_revisions else
        'CLARIFICATION_RECEIVED_EXPECTATION_UNREVISED' if any(c['receipt']['received'] for c in available) else
        'CLARIFICATION_NOT_RECEIVED' if available else 'INITIAL_EXPECTATION_FACTORS_ONLY' if initial else 'NO_ANCHORED_EXPECTATION')
    current_claim, revision_receipt = old, None
    if accepted_revisions:
        reasons = tuple([accepted_revisions[-1]['candidate']] + accepted_revisions[-1]['clarification_source_ids'])
        current_claim = core.claim(semantic.scope, ClaimKind.SYSTEM_INTERPRETATION,
            dict(operation='REVISED_EXPECTATION_EXPLANATION', status=status, revision=accepted_revisions[-1]))
        core.support(current_claim, *(r['candidate'] for r in rows))
        core.interpret(current_claim, unknown_conditions=('source_accuracy', 'revision_cause_not_proven'))
        if old not in core.withdrawn:
            core.replace_interpretation(old, current_claim, reasons=reasons)
        revision_receipt = dict(old=old, new=current_claim, reasons=reasons, kind='ANALYST_EXPLANATION_REVISION_NOT_PRIVATE_STATE_ASSERTION')
    payload = dict(query=query, original_source=original, status=status, original_promise=social.payload['commitment']['original_promise'],
        initial_expectation=initial, initial_factors=factors, clarifications=available,
        changed_condition_reports=[c for c in clarifications if not c['preserves_original_condition']],
        expectation_revisions=accepted_revisions, current_local_meaning=meanings(len(scene.lines)),
        explanation_revision=revision_receipt, cg02_source_check=social.payload['cg02_source_check'],
        trust_restoration='NOT_INFERRED', promise_rewritten=False, actual_understanding='NOT_ESTABLISHED', policy=_POLICY)
    return MisunderstandingResult(social.source_versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(social.claim_ids) + (current_claim,))
