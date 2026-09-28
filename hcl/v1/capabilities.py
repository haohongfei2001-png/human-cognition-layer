"""Canonical, executable inventory; historical runtimes are not all defaults."""
from dataclasses import asdict, dataclass
from enum import Enum
from types import MappingProxyType


class CapabilityType(str, Enum):
    CORE = 'CORE_RETAIN'
    OPTIONAL = 'OPTIONAL_STRUCTURED_SIMPLIFIED'
    TOOL = 'GENERIC_EXACT_TOOL'
    INACTIVE = 'INACTIVE_RESEARCH_ONLY'


class CostClass(str, Enum):
    ZERO = 'ZERO'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


@dataclass(frozen=True)
class Capability:
    capability_id: str
    kind: CapabilityType
    status: str
    implementation: str
    evidence_level: str
    activation_policy: str
    dependencies: tuple[str, ...]
    cost_class: CostClass
    failure_behavior: str = 'SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth'

    def as_dict(self):
        return asdict(self)


def _cap(cid, kind, implementation, evidence, policy, deps=(), cost=CostClass.LOW, status_override=None):
    status = status_override or {CapabilityType.CORE: 'RETAIN', CapabilityType.OPTIONAL: 'SIMPLIFY',
              CapabilityType.TOOL: 'CONDITIONAL_TOOL_ONLY', CapabilityType.INACTIVE: 'FROZEN'}[kind]
    return Capability(cid, kind, status, implementation, evidence, policy, deps, cost)


_ROWS = (
    _cap('evidence', CapabilityType.CORE, 'hcl/v04/model.py:EventRecord', 'FOUNDATION_CORRECTNESS', 'only selected HCL paths'),
    _cap('provenance', CapabilityType.CORE, 'hcl/v05/store.py', 'FOUNDATION_CORRECTNESS', 'retain source and evidence kind', ('evidence',)),
    _cap('temporal', CapabilityType.CORE, 'hcl/v05/store.py;hcl/v06/perspective.py', 'FOUNDATION_CORRECTNESS', 'event and record-time bounds', ('evidence',)),
    _cap('actor_source', CapabilityType.CORE, 'hcl/v04/model.py', 'FOUNDATION_CORRECTNESS', 'actor is not source', ('evidence',)),
    _cap('source_visibility', CapabilityType.CORE, 'hcl/v06/perspective.py', 'FOUNDATION_CORRECTNESS', 'scope every selected context', ('temporal', 'actor_source')),
    _cap('uncertainty', CapabilityType.CORE, 'hcl/v06/belief.py', 'FOUNDATION_CORRECTNESS', 'missing system evidence is not character uncertainty', ('evidence',)),
    _cap('perspective', CapabilityType.CORE, 'hcl/v06/runtime.py:HCLV06Runtime', 'FRESH_DEVELOPMENT_C11_P19_G22_D30_OF32_D_ONLY8_G_ONLY0', 'information access/asymmetry/second-order tasks only', ('source_visibility', 'provenance', 'uncertainty')),
    _cap('belief', CapabilityType.CORE, 'hcl/v06/belief.py', 'FRESH_DEVELOPMENT_C11_P19_G22_D30_OF32_D_ONLY8_G_ONLY0', 'knowledge/belief/revision tasks only', ('perspective',)),
    _cap('cg01_explanation', CapabilityType.CORE, 'hcl/v1/cg01.py', 'PROVIDER_FREE_CORRECTNESS_ONLY', 'bounded action-explanation condition checks only', ('source_visibility', 'provenance', 'uncertainty'), status_override='IMPLEMENTED_UNVALIDATED'),
    _cap('intention', CapabilityType.OPTIONAL, 'hcl/v07/runtime.py', 'SIMPLIFY_NO_SPECIALIZED_UTILITY', 'explicit goal/plan query; source-grounded optional context', ('provenance', 'source_visibility', 'uncertainty')),
    _cap('goal', CapabilityType.OPTIONAL, 'hcl/v07/runtime.py:GoalEstimate', 'SIMPLIFY_NO_SPECIALIZED_UTILITY', 'explicit goals only', ('intention',)),
    _cap('motivation_evidence', CapabilityType.OPTIONAL, 'hcl/v07/runtime.py', 'SIMPLIFY_NO_SPECIALIZED_UTILITY', 'retain attribution as evidence, never invent motive', ('intention',)),
    _cap('affect', CapabilityType.OPTIONAL, 'hcl/v08/runtime.py', 'SIMPLIFY_NO_SPECIALIZED_UTILITY', 'feeling/appraisal question only; no action-to-emotion promotion', ('provenance', 'source_visibility', 'uncertainty')),
    _cap('causal', CapabilityType.TOOL, 'hcl/v09/runtime.py', 'GENERIC_TOOL_DEVELOPMENT_SIGNAL_ONLY', 'counterfactual request plus declared source-scoped model', ('source_visibility', 'provenance')),
    _cap('argumentation', CapabilityType.TOOL, 'hcl/v10/runtime.py', 'NONFRESH_GENERIC_TOOL_DEVELOPMENT_SIGNAL_ONLY', 'formal request plus complete declared attack graph', ('source_visibility', 'provenance')),
    _cap('formal_verifier', CapabilityType.TOOL, 'hcl/quantified_logic.py', 'PROVIDER_FREE_CORRECTNESS_ONLY', 'explicit formulas only', ('source_visibility', 'provenance')),
    _cap('countermodel', CapabilityType.TOOL, 'hcl/quantified_logic.py', 'NO_EXTERNAL_SEMANTIC_INCREMENT', 'explicit formulas and witness/domain bounds', ('formal_verifier',)),
    _cap('formal_reading', CapabilityType.TOOL, 'hcl/argument_readings.py', 'PROVIDER_FREE_CORRECTNESS_ONLY', 'explicit alternative readings; never choose a winner', ('formal_verifier',)),
    _cap('pragmatics_research', CapabilityType.INACTIVE, 'hcl/pragmatics.py', 'SIMPLIFY_NO_INCREMENT', 'never router-activated'),
    _cap('value_research', CapabilityType.INACTIVE, 'hcl/value_perspective.py', 'SIMPLIFY_NO_SEMANTIC_INCREMENT', 'never router-activated'),
    _cap('narrative_research', CapabilityType.INACTIVE, 'hcl/narrative_order.py', 'NO_GENERIC_TOOL_INCREMENT', 'never router-activated'),
    _cap('historical_harnesses', CapabilityType.INACTIVE, 'eval/;scripts/;reports/', 'CONSUMED_OR_INVALID_OR_INCONCLUSIVE', 'never runtime-imported', cost=CostClass.ZERO),
    _cap('longmemeval_sealed', CapabilityType.INACTIVE, 'eval/v05/', 'SEALED_DEPRIORITIZED_32_ROWS', 'never access/trigger/consume; new owner scope required', cost=CostClass.ZERO),
)
CAPABILITIES = MappingProxyType({row.capability_id: row for row in _ROWS})


def resolve_dependencies(ids):
    """Stable minimal closure; inactive research cannot enter an execution plan."""
    selected = set()
    def add(cid):
        cap = CAPABILITIES[cid]
        if cap.kind == CapabilityType.INACTIVE:
            raise ValueError('inactive capability cannot execute: ' + cid)
        if cid in selected:
            return
        selected.add(cid)
        for dep in cap.dependencies:
            add(dep)
    for cid in ids:
        add(cid)
    return tuple(cid for cid in CAPABILITIES if cid in selected)
