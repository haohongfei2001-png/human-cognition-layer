# Coherent shared-source snapshots in ordinary HCL delivery

This is a provider-free correctness repair, not a new capability or evidence of
better model answers. It does not explain or rescore any historical experiment.

## Demonstrated defect

`UniversalHCL` stores the original source/version for planning, final composition
and citation review. Its exposed `CognitionWorkspace` also has a public
`put_source`/`remove_source` lifecycle used by real native operations. Previously,
`_current` compared only the outer version list and checked the **current** shared
root's support. A newly grounded shared root could therefore be mistaken for
confirmation that the older outer snapshot was still current.

At baseline `cd3fa7fffbbfd2caa746812061a0def2edda90fe` (the runtime of PR #376):

- A local planner callback revised “Nia believes the gate is clear” to “blocked”
  through the shared workspace. Actual B01 output used v2, final original source
  still said v1, and delivery incorrectly succeeded.
- A real C02 insufficient-evidence result had no positive support-claim IDs.
  Revising the shared source during the local answer callback also escaped the
  old post-answer checks and delivered a stale v1 answer.

These are scripted counterexamples with actual native execution and zero provider
calls. Direct workspace updates, or the intermediate state of a concurrent outer
update, expose the problem; serialized outer `UniversalHCL.put_source` revisions
were already rejected. The missing historical PAIR1 wire and PAIR3 fact omission
remain unexplained by this evidence.

## Narrow repair

Before the existing root/support checks, every registered outer source must still
exist in the shared workspace with the same version and exact text. A mismatch
or removal uses the existing `SOURCE_CHANGED_DURING_ORCHESTRATION` boundary code.
The same check already surrounds planning, each native dispatch, final composition
and returned-answer review. Raw returned answers remain retained when final review
rejects them; there is no rewrite, retry, fallback or new model phase.

This is not equality of all workspace state. Same-text puts, unrelated workspace
sources, legitimate derived claims, operation caches and same-version native
execution remain allowed. Explicitly registering the revised source through the
outer API permits a fresh coherent run. Source-root withdrawal still uses the
existing support rejection, and citation/translation/version rules are unchanged.
Checkpoint checks do not claim to make the whole shared workspace transactional.

## Regression and identity evidence

Eleven new test methods cover source changes before planning, during planning,
immediately before/after native execution, between native operations and after
the answer returns; source removal, equal-version text disagreement and the
empty-support C02 path; and the allowed controls above. The frozen tests produced
nine failing assertions on the old runtime, including five fail-open delivery
examples plus classification differences. They pass after the six-line guard.

`development_universal_source_amendment` accepts only the reviewed runtime file
hash and resulting full runtime identity. Restoring that file's prior hash must
recover the exact preceding runtime digest; other file/membership drift fails.
It preserves all 45 consumed CNY/predecessor pins plus three PR #376 amendment
artifacts. Current test/witness validator imports and provider-free workflow
commands move to this identity; consumed paid executors, grants, packages, output
records, scores and historical replay commands remain unchanged.

Run the new boundary tests, exact identity guard and full existing provider-free
suite. Hosted exact-head/main checks provide the commit-specific receipts. The
new runtime has no live model evidence or new spending authority. Both old CNY
grants remain closed at zero; any future live diagnostic needs a fresh exact
package and limited authorization. The separate ordinary-reader native-policy
omission remains a next information-preservation repair.
