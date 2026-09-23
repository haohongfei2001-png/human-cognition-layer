# HCL v0.4 Bounded Latent-Hypothesis Slice v0.1

Status: **FROZEN FOR MINIMAL IMPLEMENTATION**

## 1. Capability objective

The explicit first-order belief slice reached ceiling against ordinary full
history memory.

The next capability target is:

> maintain several plausible latent human-state hypotheses, update them as
> behavior/evidence arrives, and use the maintained alternatives to improve
> prediction or communication decisions.

This slice is closer to the long-term HCL objective because the target state is
not directly observable.

## 2. Scope

First version supports one target agent and one latent question at a time.

Examples of latent question classes:
- current hidden goal;
- current intention;
- unobserved belief;
- reason for a behavior.

The mechanism must not claim that the leading hypothesis is psychological truth.

## 3. Candidate set

For the minimal implementation:

- 2–3 named hypotheses;
- plus mandatory `OTHER_UNKNOWN`.

Candidate labels are supplied by the controlled task/harness in v0.1 so that the
update mechanism can be tested independently of hypothesis-generation quality.

Automatic open-ended hypothesis generation is deferred to a later slice.

This is a deliberate decomposition, not a statement that real human cognition
has a closed candidate set.

## 4. Hypothesis state

Each candidate stores:

- target_id;
- subject_agent_id;
- hypothesis_label;
- description;
- support status;
- supporting raw event IDs;
- counterevidence raw event IDs;
- unresolved raw event IDs;
- short evidence-grounded rationale;
- version;
- update time.

Allowed qualitative support status:

- `SUPPORTED`
- `PLAUSIBLE`
- `WEAKENED`
- `CONTRADICTED`

`OTHER_UNKNOWN` must always exist and may be `PLAUSIBLE` when evidence does
not adequately cover the candidate space.

No pseudo-precise probability is required.

## 5. Evidence authority

Only raw events/evidence may be cited as support or counterevidence.

Forbidden:

- using a previous HCL hypothesis as new external evidence;
- counting repeated retellings of one underlying source as independent evidence
  without provenance;
- promoting a hypothesis to fact merely because it is currently leading;
- deleting `OTHER_UNKNOWN` to force a closed answer.

## 6. Update semantics

At each update:

1. provide the current candidate set;
2. provide only the newly relevant raw events plus traceable earlier evidence as
   needed;
3. LLM proposes revised support/counterevidence;
4. deterministic code validates all event references and candidate labels;
5. commit a new hypothesis-set version;
6. preserve the previous version for audit/rebuild.

The update may:
- strengthen;
- weaken;
- contradict;
- leave unchanged.

It may not silently rename or delete a frozen candidate.

## 7. Recovery

If an update cites nonexistent evidence or invalid labels:

- reject atomically;
- allow at most one bounded schema/invariant repair;
- preserve the rejected proposal and reason.

A target can be rebuilt from raw event history.

## 8. Query projection

The downstream consumer receives:

- candidate labels/descriptions;
- current qualitative support;
- support and counterevidence references;
- unresolved evidence;
- OTHER_UNKNOWN;
- relevant raw evidence excerpts.

The query layer must preserve multiple hypotheses when evidence does not justify
collapse.

## 9. Capability test

The first internal test uses controlled sequential scenarios with hidden
environment state.

The HCL module does not see the hidden state.

Visible behavior is consistent with a hidden target but may also temporarily
support alternatives.

Primary downstream outcome:
- predict a later observable behavior/choice.

Secondary diagnostic:
- whether the hidden-state candidate becomes better supported as evidence
  accumulates.

## 10. Comparison

Use three arms:

- C — reconstruct hypothesis state from full visible history at each query;
- D — dynamic persistent hypothesis state;
- E — ordinary full-history reasoning with the same candidate labels.

All use the same base model and exact-label prediction interface.

The hidden state is used only by the evaluator.

## 11. Interpretation

- D > E on independent scenarios: candidate incremental cognition signal;
- D = E: no incremental utility established;
- D worse than E: structured hypotheses currently hurt;
- C = D but D cheaper: persistence engineering value;
- hypothesis state improves while prediction does not: representation gain only,
  not full HCL utility.

## 12. Claim boundary

Internal controlled hidden state is valid for mechanism development.

It does not establish that HCL can read real human minds.

Human validity will require later external/behavioral evidence.

## 13. IP boundary

Do not add owner-originated unpublished conceptual examples.

Use generic controlled scenarios only.

## 14. Gate

**Gate: HCL_V04_LATENT_HYPOTHESIS_V01_MINIMAL_IMPLEMENTATION_READY**
