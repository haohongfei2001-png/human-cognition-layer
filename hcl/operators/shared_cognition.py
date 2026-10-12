"""An ephemeral view of one actual M03 operation, never a second state store."""

from dataclasses import dataclass, replace
from types import MappingProxyType
from hcl.kernel.types import thaw, freeze
from hcl.memory import codec
from hcl.operators.mental_scene import MentalSceneOperator


def canonical(value):
    return codec.canonical(thaw(value))


@dataclass(frozen=True)
class SharedCognitiveExecution:
    """Internal composition value. Candidate JSON cannot construct this object.

    The caller owns the single M03 work charge; each consumer charges only its
    additional computation. Immutable source and rule bindings remain those of
    the original authenticated snapshot and operation.
    """

    original: object
    augmented: object
    operation: object
    trace: object
    issue_id: str
    max_local_evaluations: int
    trace_times: tuple

    def __post_init__(self):
        object.__setattr__(self, "original", freeze(self.original))
        object.__setattr__(self, "augmented", freeze(self.augmented))
        object.__setattr__(
            self,
            "trace",
            MappingProxyType(
                {
                    key: (
                        MappingProxyType(dict(timeline)),
                        MappingProxyType(dict(environments)),
                    )
                    for key, (timeline, environments) in self.trace.items()
                }
            ),
        )

    def bind(self, snapshot, original):
        if canonical(original) != canonical(self.original):
            raise ValueError("shared cognition input differs from domain source model")
        delta = self.operation.candidate_delta
        if (
            delta.session_id != snapshot.session_id
            or delta.principal != snapshot.principal
            or delta.base_revision != snapshot.revision
            or delta.access_epoch != snapshot.access_epoch
            or delta.rule_version != snapshot.rule_version
            or canonical(self.operation.read_set) != canonical(snapshot.source_versions)
        ):
            raise ValueError("shared cognition belongs to a different snapshot")
        return self.operation, self.trace


def compute_shared_cognition(snapshot, issue, allowance, interaction, extra_times):
    # M07 owns the interpretation semantics, including recipient-specific readings.
    from hcl.operators.interaction_model import prepare_interaction_cognition

    original = interaction["mental"]
    augmented, overrides, times = prepare_interaction_cognition(
        interaction, extra_times
    )
    trace = {}
    operation = MentalSceneOperator()._run(
        snapshot,
        issue,
        allowance,
        dict(models=[augmented]),
        event_overrides=overrides,
        trace=trace,
        trace_times={original["id"]: times},
    )
    return SharedCognitiveExecution(
        original,
        augmented,
        operation,
        trace,
        issue.issue_id,
        allowance.max_local_evaluations,
        times,
    )


def cognitive_record(bundle):
    operation = bundle.operation
    actual = operation.candidate_delta.new_inferences[0]
    return dict(
        issue_id=bundle.issue_id,
        max_local_evaluations=bundle.max_local_evaluations,
        trace_times=bundle.trace_times,
        actual=dict(
            result_id=actual.result_id,
            kind=actual.kind,
            values=thaw(actual.values),
            assumption_environments=actual.assumption_environments,
            source_versions=dict(operation.read_set),
            issues=operation.issues,
        ),
        local_evaluations=operation.resource_usage["local_evaluations"],
    )


def verify_cognitive_record(record, interaction, source_versions, rule_version):
    """Recompute a pure certificate; this context cannot read or commit any source.

    Authorization is exclusively the surrounding engine's current read-set/ACL
    gate. Recomputed Delta metadata are discarded, not usable as access evidence.
    """
    from types import SimpleNamespace
    from hcl.kernel.types import Principal, Issue
    from hcl.kernel.execution import ExecutionBudget

    allowance = record["max_local_evaluations"]
    if type(allowance) is not int or allowance < 0:
        raise ValueError("invalid shared cognitive allowance")
    snapshot = SimpleNamespace(
        session_id="pure-certificate",
        principal=Principal("pure", "certificate"),
        revision=0,
        access_epoch=0,
        rule_version=rule_version,
        source_versions=source_versions,
    )
    bundle = compute_shared_cognition(
        snapshot,
        Issue(record["issue_id"], "mental.simulate"),
        replace(ExecutionBudget(), max_local_evaluations=allowance),
        interaction,
        record["trace_times"],
    )
    if canonical(cognitive_record(bundle)) != canonical(record):
        raise ValueError("shared cognition certificate differs from actual computation")
    return bundle
