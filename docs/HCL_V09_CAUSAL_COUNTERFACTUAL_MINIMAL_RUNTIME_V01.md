# HCL v0.9 Bounded Causal & Counterfactual Runtime v0.1

Status: **minimal candidate; provider-free correctness; external utility untested**.

## Scope

`hcl/v09` implements published Boolean structural-model semantics. A declared
model has at most 24 variables and eight Boolean exogenous roots (256 worlds),
a complete acyclic equation per endogenous variable, exact source excerpts,
and a source-model assumption scope. Supported expressions are names, integer
0/1, NOT, AND, OR and XOR. It does not execute source programs or use Python
`eval`; arithmetic, continuous noise, probability, cycles and nested potential-
outcome expressions are outside this slice.

A structural model is an explicit conditional assumption. Unqualified causal
language and correlation do not automatically establish deterministic equations.
Quote anchoring checks provenance, not entailment. The caller/source adapter
must disclose assumptions and externally audit the equation interpretation.
No causal discovery, real-world intervention recommendation, diagnosis or
private mental-state inference is claimed.

## Operational semantics

1. Compile a source-only model before the task is released; retain all rules.
2. Filter factual exogenous worlds by the factual observations.
3. Preserve each compatible world's exogenous context; replace only intervened
   variable equations with the requested constant.
4. Evaluate each alternative world and return all possible target values.

One possible value is `DETERMINATE` under the declared model. Multiple values
are `SYSTEM_INSUFFICIENT`; no compatible factual worlds are
`INCONSISTENT_OBSERVATIONS`. No probabilities are inferred from unweighted
world counts. An alternative does not overwrite the factual source/history.
A result is explicitly conditional and not an observed or private mental fact.
This is generic exact constraint computation, not a new psychological theory.

`HCLV09Runtime` wraps v0.6 EventRecord and perspective views. Exact source
quotes, declared model scope and source existence are required at registration.
The source's valid time, record time and access path bound both model context
and computations. Hidden/unavailable models yield no traces. Models have
immutable tuples, atomic registration and collision/replay checks. Distinct
models are addressed explicitly; there is no automatic model merging,
supersession, model selection, higher-order belief inference or new persistence
layer. Existing v0.5 persistence remains separate.

## Independent correctness

Twelve v0.9 runtime regressions cover:

- factual abduction with shared context after intervention;
- observation versus intervention, joint changes and underdetermination;
- inconsistent evidence and no invented world probabilities;
- Boolean operations against an independent truth table;
- incomplete/cyclic/duplicate/undeclared models and invalid assignments;
- expression grammar/resource limits without program execution;
- quote/scope binding, atomic registration and replay/collision;
- private model and bitemporal cutoff isolation;
- query nonmutation of source/model history.

Four utility regressions additionally verify source-only construction, public
assumption release to every arm, native-gold/query firewall, full state/trace
receipt, independent full-assignment oracle and preserved contradictions.
The full selected source is pinned and checked separately in cloud preflight.
Synthetic correctness is not evidence of downstream utility or broad human
causal understanding.
