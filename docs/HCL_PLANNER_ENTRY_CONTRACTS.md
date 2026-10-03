# Planner-facing bounded entry contracts

The two closed synthetic diagnostic runs exposed an interface-description gap.
The planner was given forty retained implementation names/readiness flags while
its policy specifically highlighted C02/G02. It was not given the accepted C02
operation-question form, the distinction between operation and original questions,
or G02 actor/source binding constraints. The saved plans are evidence of those
mismatches; they do not prove every selection failure has this one cause.

## Minimal general repair

Each of the ten existing ordinary-entry adapters now has a frozen structured
`entry_contract` alongside its existing catalog entry. The other thirty retain
`ADAPTER_REQUIRED` and no contract. No capability is added, preselected or forced.
Contracts state question origin, source cardinality, binding requirements,
supported question forms, input bounds and result limits.

- B01/B02/C01/C03 consume an intent-preserving operation question and one complete
  source through the shared reader. Its selected-family checked flag, not mere
  execution, indicates treatment.
- C02 requires the exact internal `Why did <Actor> <verb and object>?` form and
  bounded literal source reports. A general competing-explanations request can
  be interpreted into that form without changing actor/action or asserting motive.
- G01 consumes the original request and zero to eight selected sources. Caller
  conditions, character/institution reports and unadopted proposals remain distinct.
- G02 consumes the original caller rule. It needs one binding per distinct actor,
  one distinct source per actor episode, and at most four episodes. Repeated
  mentions do not create extra actors. Missing adopted rules mean `checked=null`;
  unsupported literal episode forms remain unresolved.
- G03/G04/G05 consume the unchanged original request and exactly one complete
  source. G05 advertises its three retained single-factor forms, exact premise /
  local-comparison prerequisites and independent variants. Planner rewrites cannot
  introduce a caller hypothesis or make a broad request fit the parser.

The policy now directs internal selection toward the supplied contracts instead
of spotlighting two IDs. It allows zero operations when useful prerequisites are
absent and preserves ordinary unsourced analysis with explicit limits. Unsupported
implementations cannot be described as executed. There is no external task gate,
Base fallback, deterministic case router or actor/source inference rule.

## Boundaries intentionally unchanged

Retained parsers, dispatch branches, plan validation, source revisions and support,
original-request authority, exact quote/offset validation, model, thinking effort
and token limits are unchanged. Descriptive guidance cannot weaken those checks.
The larger planning inventory is bounded by the existing complete-context/request
limits; no truncation is added. Provider-free reconstruction of the two prior
synthetic requests produces 19959 and 19599 serialized UTF-8 bytes at a 16384-token
diagnostic planning limit, with fresh conservative reservations USD0.12040248 and
USD0.11945208. Both fit 36000 bytes, but are roughly 10.3k bytes larger than their
historical requests. Old hashes/reservations cannot authorize these new requests.
Production's default output limit is unchanged; no provider proposal follows
from this measurement. A field or a successful preparation cannot certify
substantive treatment, semantic truth, model selection quality or answer gain.

The normal provider-free tests use fresh self-authored fixtures in other domains:
maintenance actions, literal responsibility episodes, design premise changes,
missing/caller/source rules, duplicate mentions and cross-source selections. They
compare actual adapter outcomes and actual planner/final messages, including a
positive C02 conditional explanation and G05 source-preserving variant. Eight separate reviewer-authored engineering challenges were hash-frozen before
implementation and revealed only after local candidate 56e3ce5 was frozen. All
eight contract assertions passed without changing the implementation. The C02
challenge lacked a source, so it did not establish positive C02 execution; E05
remained unavailable. Expected refusals, a real G05 preparation and non-adoption
are distinguished in the engineering report. For the IDs-only cardinality case,
IDs themselves were explicitly used as opaque source payloads, not semantic data.
Neither set is a final-confirmation corpus or efficacy evaluation.

The exact reviewer fixture is `eval/planner_contract_challenges_v1.json`, SHA-256
`430bcca39eae5c90f21b2d26bd01a1308ed6c62d2b8222bd06f05fbb35017ef5`.
The portable verifier and scalar report are `scripts/verify_planner_contract_challenges.py`
and `reports/HCL_PLANNER_ENTRY_CONTRACTS_REVIEW.json`. Run the verifier with
`--output <path>` at the recorded runtime or the commit introducing the report.
Its deliberate runtime pin prevents silently treating a later implementation as
the frozen reviewed candidate.

## Historical evidence and cost

Only catalog metadata and planner policy change in `hcl/`. A new amendment pins
all prior amendment scripts/reports and both closed diagnostic packages, grants,
runner files and scalar closures byte-for-byte, reconstructing the preceding
runtime from the two prior file hashes. Current witness imports advance only to
the new current validator; their inputs/assertions and historical reports remain.
Closed diagnostic runners are frozen historical executors and must be replayed
under their recorded runtime, not silently relabeled as current executions.

No provider call or spending is part of this repair. The owner's original campaign
still has nine calls and US$0.51528576 full reservations charged through the last
closure; any separately reviewed future sequence must import them within the
original US$1 / twelve-call / 2026-10-03 08:00 UTC ceiling. Closed sub-run grants
remain closed. No paid judge, source-specific repair, confirmation access or new
model/token configuration is introduced.
