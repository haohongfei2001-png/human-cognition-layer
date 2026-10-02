# Six-row MindGames development smoke: offline freeze

**Preflight: checked treatment 0/6; do not spend to claim H mechanism benefit.**

Base main: `5cc6abcef4df46db7f36641614aaef5f5433a1e8`.
[Machine protocol](../reports/HCL_MINDGAMES_DEVELOPMENT_PROTOCOL.json).
The existing six reviewed native rows are retained without replacement. Their
complete native-row, premise, hypothesis and ordinary-input hashes match the
source-preparation receipt. No further sources, labels or model answers were
searched. The pinned original parquet was re-fetched and its SHA256 matches
`093d3162baad0e6cb8dac5a1775c0cfc238f9b92e55ee92e3b4e059e94a14212`.

## Executable offline preparation

`python -m scripts.development_mindgames_protocol --native-rows <private-six-native-rows.json> --output <protocol.json>`

Input is the six complete native rows in the already fixed order. The script
rejects native identity/label drift. Provider requests are constructed exclusively
from `premise` and `hypothesis`; labels, formal solver representations, predictions,
difficulty, setup and review notes never enter either arm. Only hashes/reservations
and treatment flags are emitted; original source and native metadata stay local.
There is deliberately no live transport, grant or workflow in this package.

Both arms use DeepSeek V4 Pro, enabled/high thinking, 8192 output tokens, the same
native entailment vocabulary, common task contract and complete original input.
H uses the current ordinary local-first entry and the actual final answer-boundary contract, no translation. Arm order alternates
by fixed source order. One answer per arm per item: maximum 12 calls, zero retries,
zero extraction, zero grader calls. Native exact-label correctness, format validity
and citation delivery remain separate; malformed/truncated/missing output cannot
be a correct answer. Preserve raw outputs, all errors, costs and actual treatment.
No case substitution or rerun to chase gains.

## Important preflight result

Current checked H treatment is **0/6**. All six enter the same HCL orchestration
and carry explicit capability-insufficiency records beside the full source. None
is relabelled as Base or falsely marked checked. This is an observed coverage limit, not evidence of equivalence or HCL
benefit. A paid run can check end-to-end native task behavior; it cannot establish
checked-mechanism benefit. Recommendation: retain this usable offline packet and
prioritize a general coverage/boundary improvement before spending solely on this
absent-treatment comparison. Do not add a benchmark-specific route or formal gold
to make H treatment appear. If a future runtime changes, rebuild request identities
and reservations before any execution; these frozen hashes must not be reused.

## Cost proposal, not authorization

Exact 12-request conservative reservation: **USD 0.52258536**.
Maximum complete request: 36,000 UTF-8 bytes; input reservation = twice serialized
request bytes + 2048 tokens. Output reservation = 8192 + 32 margin tokens.
Existing official peak tariff: USD 1.32 input / USD 3.96 output per million tokens.
Global byte-bound ceiling across all twelve calls: USD 1.56372480.
Proposed hard cap: **USD 1.60**, no historical budget transfer. Actual input hashes
are tighter than the global bound. All grants remain closed; authorized spend and
calls are zero. Before transport: a new explicit owner budget, exact reviewed live
runner/grant, unchanged price/model check, and per-call durable reservation gate.
Uncertain transmission counts as spent/called and stops without retry.
Pricing: https://api-docs.deepseek.com/quick_start/pricing/ (checked 2026-10-02).
Physical model snapshot behind the alias remains unverified.

## Canonical boundary-repair queue remains open

The merged hypothetical-speech, actual-narrator and embedded-scene repairs address
source-to-derived-state scope. They do not certify a final freeform explanation.
A fresh authored witness still delivers an exact-cited unsupported trait claim:
source “Mira closed the workshop door. Theo waited outside.”; stub answer claims
she did so because she is inherently spiteful, with the exact door quote. The
existing audit explicitly returns `ORIGINAL_ANCHORS_LOCATED_SEMANTICS_UNASSESSED`.
This proves the delivery boundary remains semantic-uncertified; a stub is not a
new observed model failure. The audit is honest about its scope, so do not relabel
it a broken entailment checker or silently block all useful interpretation.

Finite next engineering decision: a general source-versus-interpretation answer
contract/audit using existing provenance and responsibility factors, with authored
explicit-cause/unsupported-cause contrasts, must be reviewed independently of this
smoke. This preparation adopts no unmerged prompt mechanism and makes no claim
that those scope repairs complete the canonical queue. Final I03–I06 disposition,
sealed confirmation and LongMemEval remain separate; no final material is accessed.
