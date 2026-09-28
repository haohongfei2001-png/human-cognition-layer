"""Bounded caller-supplied input for responsibility-structure analysis.

CG03-A validates and projects an operation surface. Factor and premise checks
belong to CG03-B/C; this module does not decide responsibility.
"""
from dataclasses import dataclass


def _label(value, name, limit=256):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'bounded {name} required')


@dataclass(frozen=True)
class NormativePremise:
    premise_id: str
    text: str
    basis_event_ids: tuple[str, ...]

    def __post_init__(self):
        _label(self.premise_id, 'premise ID', 128)
        _label(self.text, 'premise text', 1000)
        if (not isinstance(self.basis_event_ids, tuple) or
            not 1 <= len(self.basis_event_ids) <= 24 or
            len(set(self.basis_event_ids)) != len(self.basis_event_ids)):
            raise ValueError('premise requires one to 24 distinct source IDs')
        for event_id in self.basis_event_ids:
            _label(event_id, 'premise source ID', 128)


@dataclass(frozen=True)
class ResponsibilityCase:
    actor_ids: tuple[str, ...]
    action_event_id: str
    outcome_event_id: str
    premises: tuple[NormativePremise, ...]

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
