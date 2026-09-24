# HCL v0.5 Strong-Baseline Replication v0.1

Status: **DESIGN FROZEN / FRESH PACKAGE NOT YET GENERATED**

## Purpose

Run one final internal controlled replication before external benchmark /
cross-model transfer.

The prior fresh seeded-state pilot produced:
- D routed HCL: 24/24;
- E strong free-form memory: 23/24;
- C full history: 22/24.

That is promising but did not meet the pre-registered +2/24 incremental-utility
threshold. The next experiment must therefore strengthen the baseline rather
than merely enlarge the same D-vs-free-form comparison.

The primary question is:

> Does the routed deterministic HCL add value beyond a strong generic
> LLM-managed structured state representation?

## Arms

Use the same base model, seed, decoding settings, frozen ontology, raw event
stream and query labels.

### D — routed deterministic HCL

- canonical HCL v0.5 runtime;
- same frozen issue/value ontology as every compared arm;
- event-local routed semantic extraction;
- deterministic recipient/observer exposure routing;
- deterministic issue-centered stance state machine;
- deterministic query projection to one ontology value or UNCERTAIN;
- no query-time answer-model call.

### G — generic structured state baseline — PRIMARY COMPARATOR

G is deliberately strong.

The model maintains one bounded JSON state record incrementally after every raw
event. The schema is generic and not copied from HCL internals:

```json
{
  "agents": {
    "<agent>": {
      "<issue>": {
        "current_label": "<ontology value|UNCERTAIN>",
        "rejected_values": [],
        "history": [
          {
            "valid_time": "...",
            "label": "<ontology value|UNCERTAIN>",
            "note": "short provenance/why"
          }
        ]
      }
    }
  }
}
```

Rules:
- G receives the same frozen ontology;
- G may freely rewrite/compress its JSON under the fixed state-size limit;
- G is instructed to preserve enough dated history for historical queries;
- G is told ordinary epistemic hygiene such as not inventing access or
  acceptance, but is **not** given HCL semantic types, deterministic routing
  rules, suspended-value machinery, or HCL transition algorithms;
- G chooses its own state updates with the model;
- query output is read deterministically from G's stored
  `current_label/history`, so D does not receive an unfair advantage merely
  from avoiding a second answer-model call.

### E — strong free-form persistent memory — SECONDARY BASELINE

- same style as the prior strong ordinary-memory baseline;
- same frozen ontology;
- bounded free-form memory + observable-content retrieval;
- query answer by the same base model.

E remains useful for continuity but is not the primary comparator.

### C — full-history diagnostic

- same base model;
- complete raw history through the query point when within provider context;
- same frozen ontology;
- diagnostic only.

## Fresh capability package

Freeze before any provider use:

- **4 independent streams**;
- **96 events per stream**;
- **12 scored queries per stream**;
- **384 events / 48 scored queries total**;
- at least 5 named agents per stream;
- exactly 4 seeded issues per stream;
- at least 2 different queried target agents per stream;
- at least 2 different queried issues per stream;
- query-time budget for E/G: 8000 characters;
- persistent E/G state limit: 6000 characters.

The package must be text/ID disjoint from:
- consumed v0.4 long-horizon v0.2;
- consumed v0.5 seeded-state v0.1;
- consumed semantic extraction v0.1/v0.2 packages.

No owner-private conceptual example may be used.

## Capability coverage

The 48 queries must be balanced across streams and include at least:

- current stance after explicit acceptance;
- revision delivered only to another agent;
- relay revision accepted;
- relay revision rejected;
- direct revision pending without stance;
- explicit rejection restoring prior stance;
- repeated confirmation of an already accepted revision;
- unseen authoritative world update;
- historical replay after multiple later revisions;
- two agents holding different stances on the same issue;
- one agent holding independent stances on two queried issues;
- interleaved revisions across several seeded issues;
- irrelevant agents/issues as distractors.

Ambiguous tentative-language rows such as "I think it may be..." should not be
used as scored gold until a tentative-belief ontology is explicitly designed.

## Primary comparison and interpretation

The primary comparison is **D vs G**, paired by query.

Let:
- `D_correct` = number of correct D queries;
- `G_correct` = number of correct G queries;
- `D_only` = queries D gets right and G gets wrong;
- `G_only` = queries G gets right and D gets wrong.

### Route A — capability advantage

A positive specialized-HCL capability signal requires all of:

1. `D_correct - G_correct >= 4` out of 48;
2. D's net advantage appears in at least 2 of the 4 independent streams;
3. no concentrated severe semantic-extraction/recovery failure explains the
   apparent gain;
4. G is not weakened by truncation/schema errors that an ordinary competent
   implementation could avoid.

### Route B — practical efficiency advantage with correctness non-inferiority

HCL may establish practical module utility without a larger correctness score if
all of:

1. `D_correct >= G_correct - 1`;
2. no severe HCL perspective/stance failure appears;
3. total D provider character volume
   `(input_chars + output_chars)` is at most **60%** of G's;
4. D provider wall time is at most **60%** of G's;
5. D query/state representation remains mechanically valid and auditable.

This route supports a practical-efficiency claim, not a claim that HCL has
strictly greater reasoning capability.

### No established unique utility

If:
- `abs(D_correct - G_correct) <= 2`, and
- Route B does not pass,

then no unique HCL utility is established by the internal replication.

### Evidence against current HCL

If:
- `G_correct - D_correct >= 4`,

that is evidence against the current specialized HCL design on this slice.

A 3-query gap without either stronger condition is **inconclusive**.

## Secondary evidence

Record but do not use to override semantic correctness:

- D vs E accuracy;
- C diagnostic accuracy;
- per-stream results;
- per-risk-class failures;
- D semantic repair/error count;
- G/E update repair/error count;
- provider calls;
- provider input/output characters;
- provider wall time;
- total arm wall time;
- persistent state size;
- query context size.

## Stop rule after this replication

This is the **last planned internal synthetic capability replication** for the
current v0.5 architecture.

If Route A or Route B passes:
- stop internal synthetic tuning;
- proceed to external benchmark selection and cross-base-model transfer.

If neither passes:
- do not start another near-identical synthetic round;
- reassess whether HCL should be simplified toward a generic structured-memory
  architecture, narrowed to a specific capability, or falsified as a distinct
  module.

## Evidence hygiene

- fixture/gold are frozen separately before provider use;
- gold/risk never enter prompts;
- every provider package is one-shot and consumed after first exposure;
- no patch against observed rows may turn that package fresh again;
- preserve full D/G/E query-visible state for diagnosis;
- preserve exact SHA/digests/cost evidence;
- no owner-private research examples;
- no external/public claim from internal results alone.

**Gate: HCL_V05_STRONG_BASELINE_REPLICATION_V01_DESIGN_FROZEN_PACKAGE_NOT_GENERATED**
