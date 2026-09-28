# HCL-CG-02 Capability Contract

Status: **PLANNED / ACTIVE DEVELOPMENT PACKAGE**

Work package: **HCL-CG-02 — Social Commitment, Expectation and Misunderstanding**

This contract defines the capability delta, boundaries, execution order and
validation conditions for the next HCL capability-growth package.

## 1. Capability delta

CG-02 asks whether HCL can reason more reliably about a social exchange when
different people may hear, interpret or remember a proposal, request, acceptance,
refusal or conditional commitment differently.

The target capability is:

> Given source-grounded dialogue/narrative evidence, preserve what social act was
> actually expressed, which conditions were attached, who could access which parts,
> what each participant had evidence to expect, and where a later expectation
> mismatch or misunderstanding arose.

This is not a relationship graph and not a trust score.

Example:

- A says: "If I finish by Friday, I can go with you."
- B later says: "A promised to go with me Friday."

CG-02 should preserve that A's source act was conditional. It may explain that B's
later expectation is stronger than the source commitment if B dropped or never
received the condition. It must not automatically conclude that A lied, betrayed B,
broke a promise, or had bad intent.

## 2. Minimal social-act vocabulary

The first implementation may represent only:

- PROPOSAL
- REQUEST
- ACCEPTANCE
- REFUSAL
- CONDITIONAL_COMMITMENT
- WITHDRAWAL

Do not expand this into a broad speech-act ontology unless a later concrete failure
requires it.

Each grounded act minimally binds:

- speaker
- addressee or intended recipient when source-supported
- act kind
- proposition/content
- explicit condition(s), if any
- source span / provenance
- event time or relative order
- access metadata where available

## 3. Perspective and interpretation separation

CG-02 must distinguish:

1. **source-grounded act** — what the authorized source supports was actually said
   or done;
2. **participant interpretation** — what actor A or B had evidence to understand;
3. **system explanation** — why their expectations may diverge.

A participant interpretation must never overwrite the source act.

Reader knowledge must not be copied into participant knowledge.

A missing record that B heard a condition is not proof that B did not hear it.
Negative access requires explicit evidence or a justified closed-world boundary.

## 4. Commitment and expectation reasoning

The deterministic mechanism should support bounded checks such as:

- whether an acceptance refers to a prior proposal/request;
- whether a commitment is conditional or unconditional;
- whether a cited condition was source-supported;
- whether the condition was known to the relevant participant;
- whether a later withdrawal/revision occurred before or after the expected act;
- whether an expectation preserves or drops an explicit condition;
- whether two participants' expectations are compatible, stronger/weaker, or
  unresolved relative to the source.

The mechanism must not determine a unique private intention.

It must not infer:

- trust/distrust scores;
- friendship/enmity;
- deception;
- moral blame;
- promise-breaking;
- stable personality traits.

Those require separate evidence or future capability work.

## 5. First-round bounds

Engineering limits only:

- at most 4 actors;
- at most 32 source events;
- at most 6 grounded social acts;
- at most 3 active conditions per act;
- at most 2 explicit revisions/withdrawals;
- at most 2 participant interpretations of the same act.

## 6. Execution phases

### CG02-A — capability boundary and v1 integration surface

- add the smallest explicit route/operation for social commitment or
  misunderstanding analysis;
- reuse READER_ANALYSIS / CHARACTER_PERSPECTIVE / OBSERVER_ABOUT_TARGET;
- ordinary non-social tasks remain direct;
- do not trigger from generic words such as "promise", "why" or "misunderstand"
  alone without a person/social target.

### CG02-B — grounded social-act checker

Implement typed, source-scoped operations for:

- proposal/request reference;
- acceptance/refusal;
- conditional commitment;
- withdrawal/revision;
- source/time/access validity;
- unresolved evidence.

The checker must execute these constraints rather than merely store labels.

### CG02-C — expectation mismatch and misunderstanding

Implement bounded comparison between:

- the source-grounded social act;
- each participant's evidence-scoped interpretation;
- resulting expectation.

The system should identify where an expectation mismatch comes from, for example:

- condition omitted in a later retelling;
- participant did not have evidence of a condition;
- acceptance referred to only part of a proposal;
- withdrawal occurred after one participant formed an expectation;
- evidence is insufficient to decide.

### CG02-D — ordinary-text end-to-end path

Add a bounded semantic preparation path from authorized text.

Requirements:

- exact or generically normalized source anchoring;
- no hidden oracle mental state;
- actual prepared state and final model messages preserved in debug receipts;
- default path remains provider-free unless the caller explicitly supplies an
  authorized semantic adapter;
- failed preparation fails closed.

### CG02-CERT — provider-free certification

Cover:

- positive social-act grounding;
- conditional commitment;
- partial/hearsay access;
- condition omission;
- ambiguous acceptance;
- withdrawal timing;
- reader vs participant views;
- negative tests preventing deception/blame/trust inference;
- direct-path non-regression;
- historical regressions.

### CG02-E — bounded external development package

Only after A-D and provider-free certification.

Compare:

- C — strong direct model;
- P — strongest simple social-reasoning prompt/process;
- G — competent generic structured dialogue/event representation;
- H — HCL + CG-02;
- H-new — identical to H with the CG-02 expectation/commitment checker removed.

No paid call is authorized by this contract.

## 7. Treatment-presence gate learned from CG-01

A paid CG-02 package is invalid unless provider-free preflight proves, for every
selected H case:

1. semantic preparation is source-valid;
2. at least one CG-02 social act is grounded;
3. at least one CG-02 condition/expectation check actually executes;
4. H contains the resulting checked state;
5. H-new removes that state/mechanism as intended;
6. the final H and H-new model inputs are observably different because of the
   mechanism, not because of incidental formatting.

If any selected case fails this gate, replace or repair it **before** requesting
paid authorization. Do not spend money on an arm that does not exercise the
treatment.

## 8. Decision rule

After valid external development evidence:

- **RETAIN** — meaningful semantic increment beyond qualified P/G, and H-new
  ablation supports attribution;
- **SIMPLIFY** — P/G gives equivalent useful behavior more simply;
- **DEACTIVATE** — no useful increment, systematic harm, or the capability only
  works with hand-prepared oracle state;
- **INCONCLUSIVE** — measurement/source failure prevents a mechanism judgment.

Do not repeatedly change datasets to seek a positive result.

## 9. Owner gates

Work may implement, test, fix CI and freeze a provider-free validation package
without owner intervention.

Owner approval is required before:

- provider-backed spending;
- new credentials/accounts;
- private owner material;
- changed data-sharing/privacy scope;
- unresolved licensing risk;
- expansion into a large relationship/social ontology.

The paid gate, if reached, is:

**HCL_CG02_EXTERNAL_VALIDATION_OWNER_AUTHORIZATION**

LongMemEval remains sealed and is unrelated to CG-02.
