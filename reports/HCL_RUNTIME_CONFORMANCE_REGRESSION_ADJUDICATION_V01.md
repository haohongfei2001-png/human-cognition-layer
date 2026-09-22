# HCL Runtime Conformance Full-Regression Raw-Failure Adjudication v0.1

Status: **PREDECLARED / ADJUDICATION ONLY / NO BEHAVIOR CHANGE**

## Trigger

Canonical full synthetic regression run `35721321301` completed with:

- state-generation reliability: 24/24 PASS;
- fresh semantic-faithfulness answer suite: 12/12 PASS;
- original output-interface audit: 8/8 full-loop + 8/8 forced-revision PASS;
- production-path state fidelity: raw 11/12;
- answer-checker fresh suite: raw 11/12.

The two raw failures are:

1. `epistemic_private_message`
   - all state-fidelity checks passed except the legacy expectation that
     `missing_bridges` must be non-empty;

2. `fresh11_absence_of_evidence`
   - checker status was REVISE as expected;
   - revised answer passed final verification;
   - only the expected violation-family overlap failed because the checker used
     `PREMATURE_COLLAPSE` rather than the fixture's sole expected
     `BELIEF_LEVEL`.

No HCL behavior change is authorized before adjudication closure.

## Frozen behavior

Behavior anchor:

`da09c1fc8b82a538f6b0fdbbbe101e58b839241b`

The adjudication must not alter:
- hcl/v03/answer_loop.py;
- hcl/v03/backends.py;
- hcl/v03/state_schema.json;
- hcl/v03/FROZEN_STATE_SEMANTICS.md;
- either frozen fixture file;
- the existing state-fidelity or answer-checker runner.

## Bounded execution

Run exactly:

- `epistemic_private_message`: 4 independent production-path state builds;
- `fresh11_absence_of_evidence`: 4 independent checker/revision pipelines.

Total: 8 provider-backed adjudication repetitions.

Use:
- deepseek-flash;
- seed 42;
- frozen current behavior;
- no retries beyond the normal HCL pipeline.

## A. State-fidelity adjudication semantics

For each `epistemic_private_message` repetition persist the full normalized
repository-owned synthetic state.

Semantic pass requires all of:

1. schema-valid structured state;
2. mode = EPISTEMIC;
3. uncertainty = low or medium;
4. explicit facts preserve:
   - the project-delay information was communicated privately to the informed
     member;
   - no retransmission/public-channel communication occurred;
5. the state does not assert that the other members know the delay;
6. the state's hypotheses/summary are consistent with the no-access evidence
   path at the question's granularity.

`missing_bridges` is **not independently required to be non-empty** if the
state has already explicitly established the absence of an information path.
This is the exact evaluator condition under adjudication.

Classification:

- `EVALUATOR_FALSE_NEGATIVE` if semantic pass holds in 4/4 while the only raw
  evaluator failure would be the non-empty missing-bridge requirement;
- `RUNTIME_SEMANTIC_DEFECT` if semantic pass holds in <=2/4;
- `MIXED_OR_UNSTABLE` otherwise.

## B. Answer-checker adjudication semantics

For each `fresh11_absence_of_evidence` repetition persist:
- full state;
- first checker verdict;
- revised answer;
- final checker verdict.

Behavioral pass requires all of:

1. first checker status = REVISE;
2. first checker rejects the candidate's unsupported certainty that the agent
   definitely lacks the information;
3. revision removes that unsupported certainty and preserves the appropriate
   epistemic uncertainty;
4. final checker status = PASS.

The first-check violation family may be:
- BELIEF_LEVEL;
- PREMATURE_COLLAPSE;
- or both,

provided the behavioral semantics above hold.

Classification:

- `TAXONOMY_EVALUATOR_FALSE_NEGATIVE` if behavioral pass holds in 4/4 and the
  only mismatch is violation-family taxonomy;
- `RUNTIME_SEMANTIC_DEFECT` if behavioral pass holds in <=2/4;
- `MIXED_OR_UNSTABLE` otherwise.

## Closure rule

The full regression may receive an **adjudicated synthetic pass** only if:

- state-fidelity raw failure classifies EVALUATOR_FALSE_NEGATIVE;
- answer-checker raw failure classifies TAXONOMY_EVALUATOR_FALSE_NEGATIVE;
- all other already-passed frozen gates remain historical PASS evidence;
- no HCL behavior changed during adjudication.

The original run remains raw FAILURE and must never be rewritten as CI success.

## External-evidence boundary

No external benchmark evidence.

## Claim boundary

An adjudicated pass establishes synthetic closure of the frozen runtime behavior
despite two evaluator-taxonomy/fixture-gate false negatives. It does not
establish external benchmark efficacy, cross-base transfer, or HCL 1.0
certification.
