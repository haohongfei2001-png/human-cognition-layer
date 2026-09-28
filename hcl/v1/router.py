"""Deterministic semantic routing; no benchmark names or model extraction."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from typing import Any
from hcl.v04.model import EventRecord
from .capabilities import CostClass, resolve_dependencies
from .narrative import query_actor
from .cg02 import SocialAct, ParticipantInterpretation, AccessStatement
from .cg03 import ResponsibilityCase, NarrativePremise
from .cg04 import PreferenceCase
from .cg05 import ConceptCase


@dataclass(frozen=True)
class ToolRequest:
    capability_id: str
    source_event_id: str
    inputs: dict[str, Any]


class PerspectiveMode(str, Enum):
    READER_ANALYSIS = 'READER_ANALYSIS'
    CHARACTER_PERSPECTIVE = 'CHARACTER_PERSPECTIVE'
    OBSERVER_ABOUT_TARGET = 'OBSERVER_ABOUT_TARGET'


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
    perspective_mode: PerspectiveMode | None = None
    narrative: str | None = None
    allow_semantic_preparation: bool = False
    social_analysis: bool = False
    social_acts: tuple[SocialAct, ...] = ()
    social_interpretations: tuple[ParticipantInterpretation, ...] = ()
    social_access_statements: tuple[AccessStatement, ...] = ()
    responsibility_case: ResponsibilityCase | None = None
    responsibility_analysis: bool = False
    responsibility_premises: tuple[NarrativePremise, ...] = ()
    preference_case: PreferenceCase | None = None
    preference_analysis: bool = False
    preference_role: str | None = None
    preference_context: str | None = None

    concept_case: ConceptCase | None = None
    concept_analysis: bool = False
    concept_context: str | None = None
    concept_term: str | None = None
    concept_item: str | None = None
    compact_context: bool = False
    narrative_access: bool = False

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
        if self.perspective_mode is not None and not isinstance(self.perspective_mode, PerspectiveMode):
            raise ValueError('invalid perspective mode')
        if self.perspective_mode == PerspectiveMode.CHARACTER_PERSPECTIVE and not self.target_actor:
            raise ValueError('character perspective requires target_actor')
        if self.perspective_mode == PerspectiveMode.OBSERVER_ABOUT_TARGET and not (self.target_actor and self.observer_actor):
            raise ValueError('observer perspective requires observer_actor and target_actor')
        if self.observer_actor and self.perspective_mode not in (None, PerspectiveMode.OBSERVER_ABOUT_TARGET):
            raise ValueError('observer_actor requires observer perspective')
        if self.narrative is not None and (not isinstance(self.narrative, str) or len(self.narrative) > 16000):
            raise ValueError('bounded narrative text required')
        if self.narrative is not None and (self.event_time or self.knowledge_cutoff):
            raise ValueError('narrative sentence order cannot be mixed with calendar cutoffs; supply timed EventRecords')
        if type(self.allow_semantic_preparation) is not bool:
            raise ValueError('semantic preparation flag must be boolean')
        if type(self.social_analysis) is not bool:
            raise ValueError('social analysis flag must be boolean')
        if type(self.responsibility_analysis) is not bool:
            raise ValueError('responsibility analysis flag must be boolean')
        if type(self.narrative_access) is not bool:
            raise ValueError('narrative access flag must be boolean')
        if self.narrative_access and (self.narrative is None or not (
                self.responsibility_analysis or self.preference_analysis or self.concept_analysis)):
            raise ValueError('explicit narrative access needs an existing ordinary operation')
        if type(self.compact_context) is not bool:
            raise ValueError('compact context flag must be boolean')
        if type(self.concept_analysis) is not bool:
            raise ValueError('concept analysis flag must be boolean')
        if self.concept_analysis or self.concept_case is not None:
            if (not self.target_actor or self.preference_analysis or self.preference_case is not None or
                self.responsibility_analysis or self.responsibility_case is not None or
                self.social_analysis or self.social_acts or self.social_interpretations or self.social_access_statements):
                raise ValueError('concept operation requires one explicit focal operation')
            if self.concept_analysis:
                if (self.concept_case is not None or self.narrative is None or self.evidence or
                    not all(isinstance(v, str) for v in (self.concept_context, self.concept_term, self.concept_item))):
                    raise ValueError('ordinary concept path needs narrative and explicit scenario')
            elif (not isinstance(self.concept_case, ConceptCase) or
                  self.concept_case.actor_id != self.target_actor or self.narrative is not None or len(self.evidence) > 24):
                raise ValueError('typed concept case and focal actor required')
        elif any(v is not None for v in (self.concept_context, self.concept_term, self.concept_item)):
            raise ValueError('concept scenario requires explicit operation')
        if type(self.preference_analysis) is not bool:
            raise ValueError('preference analysis flag must be boolean')
        if self.preference_analysis or self.preference_case is not None:
            if (not self.target_actor or self.responsibility_analysis or
                self.responsibility_case is not None or self.social_analysis or
                self.social_acts or self.social_interpretations or self.social_access_statements):
                raise ValueError('preference operation requires one explicit focal operation')
            if self.preference_analysis:
                if (self.preference_case is not None or self.narrative is None or self.evidence or
                    not isinstance(self.preference_role, str) or not isinstance(self.preference_context, str)):
                    raise ValueError('ordinary preference path needs narrative, role and context')
            elif (not isinstance(self.preference_case, PreferenceCase) or
                  self.preference_case.actor_id != self.target_actor or
                  self.narrative is not None or len(self.evidence) > 24):
                raise ValueError('typed source preference case required')
        elif self.preference_role is not None or self.preference_context is not None:
            raise ValueError('preference scenario requires explicit preference operation')
        if self.responsibility_analysis:
            if (self.responsibility_case is not None or not self.target_actor or
                self.narrative is None or self.evidence or
                not isinstance(self.responsibility_premises, tuple) or
                not 1 <= len(self.responsibility_premises) <= 3 or
                not all(isinstance(p, NarrativePremise) for p in self.responsibility_premises)):
                raise ValueError('ordinary responsibility path needs actor, narrative and typed caller premises')
        elif self.responsibility_premises:
            raise ValueError('narrative premises require responsibility analysis')
        if (not isinstance(self.social_acts, tuple) or len(self.social_acts) > 6 or
            not all(isinstance(act, SocialAct) for act in self.social_acts)):
            raise ValueError('bounded typed social acts required')
        if (not isinstance(self.social_interpretations, tuple) or
            len(self.social_interpretations) > 12 or
            not all(isinstance(row, ParticipantInterpretation)
                    for row in self.social_interpretations)):
            raise ValueError('bounded typed social interpretations required')
        if (not isinstance(self.social_access_statements, tuple) or
            len(self.social_access_statements) > 8 or
            not all(isinstance(row, AccessStatement)
                    for row in self.social_access_statements)):
            raise ValueError('bounded typed social access statements required')
        if (self.social_analysis or self.social_acts or self.social_interpretations or
            self.social_access_statements) and not self.target_actor:
            raise ValueError('social analysis requires explicit target_actor')
        if self.responsibility_case is not None:
            case = self.responsibility_case
            if not isinstance(case, ResponsibilityCase):
                raise ValueError('typed responsibility case required')
            if not self.target_actor or self.target_actor not in case.actor_ids:
                raise ValueError('responsibility case requires focal target_actor in actor_ids')
            if len(self.evidence) > 24:
                raise ValueError('CG-03 accepts at most 24 source events')
            event_ids = {e.event_id for e in self.evidence}
            required = {case.action_event_id, case.outcome_event_id}
            required.update(eid for premise in case.premises for eid in premise.basis_event_ids)
            required.update(claim.source_event_id for claim in case.claims)
            if not required <= event_ids:
                raise ValueError('responsibility case references missing source event')
            action = next(e for e in self.evidence if e.event_id == case.action_event_id)
            if action.actor_id != self.target_actor:
                raise ValueError('focal action source actor mismatch')
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
    perspective_mode: PerspectiveMode = PerspectiveMode.READER_ANALYSIS
    explanation: bool = False
    social_commitment: bool = False
    responsibility_structure: bool = False
    contextual_preference: bool = False
    concept_interpretation: bool = False
    target_actor: str | None = None

    @property
    def direct(self):
        return not self.capabilities and not self.tools and not self.blocked_tools


_PATTERNS = {
    'perspective': r'\b(knows?|knew|believes?|believed|belief|perspective|aware|unaware|heard|hear|learned|information asymmetry|access to information)\b|知道|相信|信念|视角|听到|信息不对称|得知',
    'intention': r'\b(intention|intentions|intends?|motives?|motivation|goals?|plans?|planned|planning|wants?|wanted|aims?)\b|意图|动机|目标|计划|打算|想要',
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
        target_actor = request.target_actor or query_actor(request.query)
        mode = request.perspective_mode or (PerspectiveMode.OBSERVER_ABOUT_TARGET if request.observer_actor else
            PerspectiveMode.CHARACTER_PERSPECTIVE if request.target_actor and (request.tools or re.search(
                r'\b(what does .+ (?:know|believe|think|want)|what did .+ (?:know|believe|think|want)|from .+ perspective)\b|知道什么|从.+视角|以.+视角', query)
            ) else PerspectiveMode.READER_ANALYSIS)
        concept = request.concept_case is not None or request.concept_analysis
        preference = request.preference_case is not None or request.preference_analysis
        responsibility = not preference and (request.responsibility_case is not None or request.responsibility_analysis)
        social = bool(not concept and not preference and not responsibility and target_actor and (request.social_analysis or request.social_acts or
            request.social_interpretations or request.social_access_statements or re.search(
            r'\b(?:promis(?:e|ed|es)|commit(?:ment|ted)?|propos(?:e|al|ed)|request(?:ed)?|accept(?:ed|ance)?|refus(?:e|ed|al)|withdraw(?:al|n)?|misunderstand(?:ing)?|expect(?:s|ed|ation|ations)?)\b|承诺|提议|请求|接受|拒绝|撤回|误解|期待',
            query)))
        explanation = bool(not concept and not preference and not responsibility and not social and target_actor and re.search(
            r'\b(?:why did|why does|why would|explain .+ action|explanation of .+ action)\b|为什么.+(?:做|去|没|不|离开|参加)|解释.+(?:行为|行动)', query))
        selected = []
        optional = []
        tools = []
        blocked = []
        reasons = {}
        for cid in ('perspective', 'intention', 'affect'):
            if not concept and not preference and not responsibility and re.search(_PATTERNS[cid], query):
                selected.append(cid)
                reasons[cid] = 'explicit task semantics; no inference from incidental evidence'
                if cid == 'perspective':
                    selected.append('belief')
                    reasons['belief'] = 'evidence-bounded knowledge/belief projection'
                else:
                    optional.append(cid)
        if explanation:
            selected.append('cg01_explanation')
            reasons['cg01_explanation'] = 'bounded character-action explanation conditions'
        if social:
            selected.append('cg02_social_commitment')
            reasons['cg02_social_commitment'] = 'explicit bounded social act and expectation analysis'
        if responsibility:
            selected.append('cg03_responsibility_structure')
            reasons['cg03_responsibility_structure'] = 'explicit bounded action, outcome and premise operation'
        if preference:
            selected.append('cg04_contextual_preference')
            optional.append('cg04_contextual_preference')
            reasons['cg04_contextual_preference'] = 'explicit actor/role/context preference operation'
        if concept:
            selected.append('cg05_local_concept')
            optional.append('cg05_local_concept')
            reasons['cg05_local_concept'] = 'explicit speaker/context concept interpretation'
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
            elif not concept and re.search(_PATTERNS[cid], query):
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
                             blocked_tools=tuple(blocked), perspective_mode=mode,
                             explanation=explanation, social_commitment=social,
                             responsibility_structure=responsibility,
                             contextual_preference=preference, concept_interpretation=concept,
                             target_actor=target_actor)
