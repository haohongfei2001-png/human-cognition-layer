"""Conservative source anchored CG-02 preparation from ordinary dialogue lines."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import re

from hcl.v04.model import EventRecord
from .cg02 import (AccessStatement, ParticipantInterpretation, SocialAct,
                   SocialActKind, SocialCondition)


_NAME = r'[A-Z][A-Za-z0-9_-]{0,39}'
_DIALOGUE = re.compile(rf'^(?P<speaker>{_NAME})(?: to (?P<recipient>{_NAME}))?:\s*(?P<quote>"[^"]+")$')
_CONDITION = re.compile(r'^(?P<condition>If [^,]{1,120}),\s*(?P<content>.+)$', re.I)
_ACCESS_DENIAL = re.compile(rf'^(?P<actor>{_NAME}) did not (?:hear|receive|learn|know)\b', re.I)


@dataclass(frozen=True)
class SocialPreparation:
    events: tuple[EventRecord, ...]
    acts: tuple[SocialAct, ...]
    interpretations: tuple[ParticipantInterpretation, ...]
    access_statements: tuple[AccessStatement, ...]
    raw_output: str = ''
    model_id: str = 'bounded_deterministic_social_grammar'
    provider_calls: int = 0
    cost_usd: float | None = 0.0
    source_span_diagnostics: tuple[str, ...] = ()


def prepare_social_narrative(narrative: str) -> SocialPreparation:
    """Parse only complete quoted dialogue lines; ambiguous lines stay source only.

    Order is narrative line order, not a claimed calendar time. Recipient names in
    the source establish a direct delivery only for that dialogue line.
    """
    lines = [line.strip() for line in narrative.splitlines() if line.strip()]
    if len(lines) > 32:
        digest = hashlib.sha256(narrative.encode()).hexdigest()[:12]
        stamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
        whole = EventRecord(f'social-{digest}-whole', stamp, narrative,
            'authorized-social-narrative-order', stamp,
            metadata={'reader_only': True})
        return SocialPreparation((whole,), (), (), (),
            source_span_diagnostics=('source_event_bound_exceeded',))
    prefix = hashlib.sha256(narrative.encode()).hexdigest()[:12]
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    acts = []
    interpretations = []
    access = []
    for index, line in enumerate(lines):
        match = _DIALOGUE.fullmatch(line)
        stamp = (start + timedelta(seconds=index)).isoformat()
        event_id = f'social-{prefix}-{index+1}'
        speaker = match.group('speaker') if match else None
        recipient = match.group('recipient') if match else None
        event = EventRecord(event_id, stamp, line, 'authorized-social-narrative-order',
            stamp, speaker, recipient_ids=((recipient,) if recipient else ()),
            metadata={'reader_only': not bool(match)})
        events.append(event)
        if match:
            quote = match.group('quote')
            utterance = quote[1:-1].strip()
            condition = _CONDITION.match(utterance)
            kind = None
            content = utterance
            conditions = ()
            if condition and re.search(r'\b(?:will|can|shall|promise to)\b', condition.group('content'), re.I):
                kind = SocialActKind.CONDITIONAL_COMMITMENT
                content = condition.group('content').rstrip('.')
                condition_text = condition.group('condition')
                conditions = (SocialCondition(condition_text, condition_text, event_id),)
            elif re.match(r'(?:I (?:offer|propose)|How about|Let us)\b', utterance, re.I):
                kind = SocialActKind.PROPOSAL
            elif re.match(r'(?:Please |Could you |Would you )', utterance, re.I):
                kind = SocialActKind.REQUEST
            elif re.match(r'(?:Yes,? I accept|I accept)\b', utterance, re.I):
                kind = SocialActKind.ACCEPTANCE
            elif re.match(r'(?:No,? I refuse|I refuse|I decline)\b', utterance, re.I):
                kind = SocialActKind.REFUSAL
            elif re.match(r'I (?:withdraw|retract)\b', utterance, re.I):
                kind = SocialActKind.WITHDRAWAL
            if kind and len(acts) < 6:
                reference = None
                if kind in (SocialActKind.ACCEPTANCE, SocialActKind.REFUSAL, SocialActKind.WITHDRAWAL):
                    prior = [a for a in acts if a.addressee == speaker and a.speaker == recipient]
                    if kind == SocialActKind.WITHDRAWAL:
                        prior = [a for a in acts if a.speaker == speaker]
                    if len(prior) == 1:
                        reference = prior[0].act_id
                acts.append(SocialAct(f'act-{index+1}', kind, speaker, recipient,
                    content, quote, event_id, stamp, conditions, reference))
            # A later self-report can supply an expectation, never private state.
            if acts and not kind and re.search(r'\b(?:promised|expected|thought|understood)\b', utterance, re.I):
                named = [a for a in acts if a.speaker.lower() in utterance.lower()]
                if len(named) == 1 and sum(i.act_id == named[0].act_id for i in interpretations) < 2:
                    expected_conditions = tuple(c.key for c in named[0].conditions if c.key in quote)
                    interpretations.append(ParticipantInterpretation(f'interpretation-{index+1}',
                        speaker, named[0].act_id, utterance.rstrip('.'), expected_conditions,
                        quote, event_id, stamp))
        else:
            denial = _ACCESS_DENIAL.match(line)
            if denial and len(acts) == 1 and len(access) < 8:
                access.append(AccessStatement(f'access-{index+1}', denial.group('actor'),
                    acts[0].source_event_id, event_id, False))
    return SocialPreparation(tuple(events), tuple(acts), tuple(interpretations),
                             tuple(access))
