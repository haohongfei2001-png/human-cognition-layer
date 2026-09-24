# HCL v0.5 Routed Semantic Extraction v0.2 — Closure

Verdict: **COMPLETE / CONTROLLED EXTRACTION GATE PASSED WITH ONE AMBIGUOUS MISMATCH**

This is internal evidence for the routed event-local semantic boundary. It is
not evidence that HCL improves downstream cognition, not an external benchmark,
and not a production/general-language extraction claim.

## Frozen execution

- Trigger/main commit: `8efc35408b73ea6112970cf2bdb38da14949791b`
- Candidate anchor: `a245613a798d0bf57f7aec5ba5e40d4ad2483af7`
- Workflow run: `36004792453` — SUCCESS
- Job: `107650058976`
- Artifact: `10809113887`
- Artifact ZIP digest:
  `sha256:a551ba5ec427340bb074a1f067352f85a9601c717ddcb3c4664243f9860d2b6e`
- Result JSON SHA-256:
  `9a62fc5b7e94e27ee1b3fcbdbb8772f15f381fdea79bdebe5c854d87427e7181`
- Model: `deepseek-flash`; seed: 42
- Fixture SHA-256:
  `57d06573294c107f863c85890bd92a45bbc45871202bd1569b55d0ec080d3a58`
- Gold SHA-256:
  `8dc199d75b4e187a9fe33ddaaffdf5d19ed9399303a47d57c75633a432336f62`
- Shape: 3 streams / 36 events / 19 self-stance gold / 14 revision-relation gold

All one-shot, candidate-drift, digest, provider-free preflight and artifact
completeness checks passed. The package was executed once and was not rerun.

## Frozen result

- exact event matches: **35 / 36**
- self stance:
  - TP: **19**
  - FP: **1**
  - FN: **0**
  - precision: **0.95**
  - recall: **1.00**
- revision relation:
  - TP: **14**
  - FP: **0**
  - FN: **0**
  - precision: **1.00**
  - recall: **1.00**
- extraction errors: **0**
- repair events: **0**
- provider calls: **36**
- input characters: **92,780**
- output characters: **5,453**
- provider wall time: **33.02 s**

The architectural goal of separating revision relation recognition from
exposure-subject routing is strongly supported on this controlled slice. The
consumed v0.1 package had revision misses/misattributions across most revision
risk classes; v0.2 recognized all 14 fresh revision relations exactly, while
recipient/observer routing remained deterministic.

The earlier false promotion of ordinary source information into the source
actor's belief did not recur on the three fresh source-information cases.

## Sole mismatch

The only non-exact event was `r2-e09`:

> Omar tells Pax: I saw Friday on the board; I think it may be the new
> maintenance day.

Frozen gold treated this as:
- no explicit revision relation;
- no self stance.

The model produced:
- no revision relation;
- `UNRESOLVED(maintenance_day=FRIDAY)` for Omar.

The revision decision is correct. The self-stance disagreement is semantically
ambiguous rather than a clear unsafe attribution: "I think it may be" expresses
a tentative epistemic attitude by Omar, while the current v0.5 self-stance
schema has only AFFIRM / DENY / UNRESOLVED.

Research hygiene requires keeping the frozen score at 35/36. Do not relabel the
row post hoc to create 36/36. The mismatch instead identifies a future ontology
question: whether tentative belief/hypothesis should remain outside the
current-stance core or receive a distinct representation.

## Interpretation

This result is sufficient to unblock a **new independent controlled end-to-end
capability pilot** using the routed runtime, because:

- the high-risk revision relation interface is exact on this fresh slice;
- deterministic routing removes recipient/observer identity from model choice;
- no false source-belief attribution appeared on the fresh source-info cases;
- no schema failure or repair occurred.

It does not establish:
- general extraction reliability across domains/languages;
- open-ended issue/value ontology induction;
- downstream HCL utility versus ordinary memory;
- transfer across base models.

The next capability pilot should therefore keep issue/value identity explicitly
seeded for both compared systems, so it tests persistent cognition/state
tracking rather than ontology induction.

## Consumption boundary

The 36 v0.2 extraction events are consumed.

- Do not rerun them as fresh evidence.
- Do not tune against the sole mismatch and reuse the package.
- A later extraction test requires fresh data.
- The next end-to-end capability package must also be fresh and independent.

No owner-private research example, external benchmark, training, publication or
leaderboard claim is authorized by this closure.
