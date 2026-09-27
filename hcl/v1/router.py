"""Deterministic semantic routing; no benchmark names or model extraction."""
from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any
from hcl.v04.model import EventRecord
from .capabilities import CostClass, resolve_dependencies


@dataclass(frozen=True)
class ToolRequest:
    capability_id: str
    source_event_id: str
    inputs: dict[str, Any]


@dataclass(frozen=True)
class CognitionRequest:
    query: str
    evidence: tuple[EventRecord, ...] = ()
    history: tuple[str, ...] = ()
    target_actor: str | None = None
    observer_actor: str | None = None
    event_time: str | None = None
    knowledge_cutoff: str | None = None
    tools: tuple[ToolRequest, ...] = ()
    max_context_chars: int = 24000

    def __post_init__(self):
        if not isinstance(self.query, str) or not self.query.strip() or len(self.query) > 16000:
            raise ValueError('bounded nonempty query required')
        if type(self.max_context_chars) is not int or not 512 <= self.max_context_chars <= 64000:
            raise ValueError('context budget must be between 512 and 64000 characters')
        if not isinstance(self.evidence, tuple) or len(self.evidence) > 256 or not all(isinstance(e, EventRecord) for e in self.evidence):
            raise ValueError('bounded typed evidence tuple required')
        if not isinstance(self.history, tuple) or not all(isinstance(h, str) for h in self.history) or sum(map(len, self.history)) > 16000:
            raise ValueError('bounded conversation tuple required')
        if not isinstance(self.tools, tuple) or len(self.tools) > 4 or not all(isinstance(t, ToolRequest) for t in self.tools):
            raise ValueError('at most four typed tool requests')
        if len({t.capability_id for t in self.tools}) != len(self.tools):
            raise ValueError('one request per tool capability')
        for actor in (self.target_actor, self.observer_actor):
            if actor is not None and (not isinstance(actor, str) or not actor.strip() or len(actor) > 128):
                raise ValueError('bounded actor ID required')
        if self.observer_actor and not self.target_actor:
            raise ValueError('second-order view requires target_actor')
        seen = {}
        for e in self.evidence:
            if e.event_id in seen and seen[e.event_id] != e:
                raise ValueError('conflicting evidence ID')
            seen[e.event_id] = e
            for stamp in (e.valid_time, e.recorded_at):
                if datetime.fromisoformat(stamp.replace('Z', '+00:00')).utcoffset() is None:
                    raise ValueError('timezone-aware evidence required')
        for stamp in (self.event_time, self.knowledge_cutoff):
            if stamp is not None and datetime.fromisoformat(stamp.replace('Z', '+00:00')).utcoffset() is None:
                raise ValueError('timezone-aware scope required')


@dataclass(frozen=True)
class CognitionPlan:
    use_base_model: bool
    capabilities: tuple[str, ...]
    optional_capabilities: tuple[str, ...]
    tools: tuple[str, ...]
    uncertainty_policy: str
    reason_for_activation: dict[str, str]
    cost_class: CostClass
    extraction_provider_calls: int = 0
    answer_provider_calls: int = 1
    max_context_chars: int = 24000
    blocked_tools: tuple[str, ...] = ()

    @property
    def direct(self):
        return not self.capabilities and not self.tools and not self.blocked_tools


_PATTERNS = {
    'perspective': r'\b(knows?|knew|believes?|believed|belief|perspective|aware|unaware|heard|hear|learned|information asymmetry|access to information)\b|知道|相信|信念|视角|听到|信息不对称|得知',
    'intention': r'\b(intention|intentions|intends?|motives?|motivation|goals?|plans?|planned|planning|wants?|wanted|aims?|why did|why does|why would)\b|意图|动机|目标|计划|打算|想要|为什么',
    'affect': r'\b(emotions?|feelings?|feels?|felt|angry|anger|happy|sad|afraid|appraisal|appraisals)\b|情绪|感受|感觉|生气|高兴|难过|害怕|评价',
    'causal': r'\b(counterfactual|intervene|intervention|causal propagation|structural causal)\b|\bif\b.*\b(had|would|were|did not|do not)\b|反事实|干预|如果.*(?:没|会|不)',
    'argumentation': r'\b(attack graph|attack relation|argumentation|grounded extension|stable extension|preferred extension|argument framework)\b|攻击关系|论证图|论证框架',
    'formal_verifier': r'\b(premises?|entailment|logical equivalence|logically|quantifier|formal logic|prove)\b|前提|逻辑蕴涵|量词|形式逻辑',
    'countermodel': r'\b(countermodel|counterexample|witness)\b|反模型|反例|见证',
    'formal_reading': r'\b(alternative readings?|formal readings?|interpretations?)\b|多解读|不同解读|形式解读',
}
_TOOL_IDS = frozenset(('causal', 'argumentation', 'formal_verifier', 'countermodel', 'formal_reading'))


class CognitionRouter:
    def plan(self, request: CognitionRequest):
        query = request.query.lower()
        selected = []
        optional = []
        tools = []
        blocked = []
        reasons = {}
        for cid in ('perspective', 'intention', 'affect'):
            if re.search(_PATTERNS[cid], query):
                selected.append(cid)
                reasons[cid] = 'explicit task semantics; no inference from incidental evidence'
                if cid == 'perspective':
                    selected.append('belief')
                    reasons['belief'] = 'evidence-bounded knowledge/belief projection'
                else:
                    optional.append(cid)
        # Explicit source/time scopes must still be respected for factual tasks.
        if request.target_actor or request.event_time or request.knowledge_cutoff:
            selected.append('source_visibility')
            reasons['source_visibility'] = 'explicit actor/time scope'
        supplied = {t.capability_id for t in request.tools}
        for cid in sorted(_TOOL_IDS):
            # A typed tool request is itself an explicit ordinary operation,
            # never a benchmark label. NL hints alone cannot invent a model.
            if cid in supplied:
                tools.append(cid)
                selected.append(cid)
                reasons[cid] = 'explicit source-scoped exact operation; validate assumptions before execution'
            elif re.search(_PATTERNS[cid], query):
                blocked.append(cid)
                reasons[cid] = 'task needs an exact tool but no declared formal input supplied'
                selected.append('uncertainty')
        unknown = supplied - _TOOL_IDS
        if unknown:
            raise ValueError('unsupported tool capability: ' + ', '.join(sorted(unknown)))
        closure = resolve_dependencies(selected)
        return CognitionPlan(True, closure, tuple(optional), tuple(tools),
                             'evidence_bounded' if closure else 'base_model_default', reasons,
                             CostClass.LOW if closure else CostClass.ZERO,
                             max_context_chars=request.max_context_chars,
                             blocked_tools=tuple(blocked))
