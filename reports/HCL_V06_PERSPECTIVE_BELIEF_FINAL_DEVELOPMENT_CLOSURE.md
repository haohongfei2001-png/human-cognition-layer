# HCL v0.6 Perspective/Belief Final Development Closure

Decision: **RETAIN** the frozen v0.6.1 specialized perspective layer as a
reusable HCL capability. End the FANToM perspective development cycle here.

## Immutable fresh pilot evidence

- Main trigger commit: `135dd2cf5efa6300bb90f1fddcf7957c9cbf19d7`.
- GitHub Actions run: `36151145297`, first attempt, **SUCCESS**.
- Artifact: `hcl-v06-fantom-cpgd-fresh-v01-36151145297`, ID `10871607773`.
- Artifact ZIP SHA-256: `0bcbf93ea035ed6c7ced4e6708edc07a3fe25795517148303cdd7a9b42792d17`.
- Selection manifest SHA-256: `9d19063aa96793dfd9cfc8c5707825a75b905f34501786f147f64480f5d7f704`.
- 32/32 selected, disjoint full conversations completed; eight in each frozen
  stratum. Zero run failures, empty answers, invalid predictions, or access
  adapter repairs. All 160 responses reported model `deepseek-flash`.
- The original 80 historical conversations and eight v0.6 development
  conversations remained excluded. These 32 are now consumed fresh-pilot
  evidence and cannot be reused as a new fresh set.

The source, selection, question/gold firewall, common model and answer budget,
G control, D runtime and caps were frozen before this run in
`docs/HCL_V06_FANTOM_CPGD_FRESH_V01.md`. The adapter and G/D states were built
before release of each selected question. The artifact stores IDs, hashes,
predictions and access maps; raw FANToM questions, answers and conversations
are not committed here.

## Results

| Arm | Correct / 32 |
|---|---:|
| C — direct | 11 |
| P — thin perspective prompt | 19 |
| G — competent generic chronology/access structure | 22 |
| D — frozen v0.6.1 perspective state | 30 |

| Paired contrast | D only correct | Control only correct | Both correct | Both wrong | Two-sided exact McNemar p |
|---|---:|---:|---:|---:|---:|
| D vs C | 19 | 0 | 11 | 2 | 0.00000381 |
| D vs P | 12 | 1 | 18 | 1 | 0.003418 |
| D vs G | 8 | 0 | 22 | 2 | 0.007813 |

The p values use the exact conditional binomial test on discordant pairs. They
describe this fixed pilot; they are not a population-wide or cross-model claim.

| Frozen stratum (n=8 each) | C | P | G | D |
|---|---:|---:|---:|---:|
| First-order inaccessible belief | 3 | 4 | 5 | 7 |
| Second-order inaccessible belief | 5 | 6 | 6 | 8 |
| Inaccessible answerability | 1 | 5 | 6 | 7 |
| Inaccessible information access | 2 | 4 | 5 | 8 |

D's eight wins over G span all four strata (2, 2, 1, 3); there were no G-only
wins. This supports a specific incremental value for bounded character views
and access projection within this one-model, information-asymmetry pilot. It
does not isolate which D subcomponent caused each win. The two D misses are
preserved as outcomes, with no post-hoc runtime adjustment.

## Operational accounting and limits

- Calls: 32 access extractions plus 32 each for C, P, G and D = **160** of the
  192-call cap; no repair calls.
- Total input/output characters: **3,852,011 / 85,770**.
- Provider wall time summed over calls: **218.516 seconds**.
- Peak-rate provider-token ledger: **USD 0.42461608**, below the authorized
  USD 3.50 operational cap. Conservative character-as-token calculation:
  **USD 1.258527**. These are operational calculations, not an invoice.
- D answer contexts used 2,343,537 input characters, versus 773,859 for G,
  222,657 for P and 214,977 for C. RETAIN therefore includes a clear context
  and cost tradeoff; this pilot did not equalize input context size.
- The adapter's fixed presence-evidence floor removed 200 unsupported
  retroactive listener assignments; this was frozen before the pilot and
  applied to the shared G/D access map. The artifact preserves every access
  map for later causal audit.
- One model, one public benchmark family, 32 cases and a single run limit
  generalization. The result does not establish broad human cognition,
  other-model transfer or independent real-world utility.

## Final decision and next capability

**RETAIN.** D has a clear paired advantage over both the thin P and competent
G controls, with no G-only wins, under the frozen protocol. Keep v0.6.1 as a
reusable, evidence-bounded perspective component. Do not tune it against the
consumed FANToM cases or expand perspective-specific rules from this result.
HCL v0.6 is closed.

Continue v0.7 Evidence-Constrained Intention & Motivation. Its minimal
provider-free runtime and source audit already exist. The next external check
must separately freeze a small development protocol and budget; no v0.7
provider exposure is claimed here. LongMemEval remains sealed and untouched.
