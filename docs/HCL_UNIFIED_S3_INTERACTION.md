# S3 in progress: finite source-bound interaction composition

This increment continues M07 from main `e3a73062ebcb011b2db7b4ad4ece8136a9e655c8`
(PR #433). It is bounded offline evidence for a first actual M03 → M07 → M05
composition. Full M07, S3/S4 and T01–T32 research acceptance remain open. It
preserves the complete approved S1–S7 plan and all research exits.

## The ordinary executable path

`interaction.evaluate` is an ExecutionIssue goal in the existing authenticated
HCL run/run_sync/stream graph. The versioned `interaction-model-1` LocalModel is
compiled from a source-anchored `hcl-interaction-candidates-1` proposal. The model
port supplies interpretations, utterances, receipt/understanding hypotheses,
original commitment terms, discrete event times, candidate messages, explicit
priors and utilities. It cannot supply computed beliefs, Q values, posteriors,
strategy scores, commitment verdicts or common-knowledge labels.

The existing MentalSceneOperator supplies actual finite epistemic states and
queries. Internal event overrides preserve each recipient's proposed content;
no duplicate epistemic solver is introduced. The existing M05 action-value
solver computes each relevant state/action value. InteractionModelOperator composes
these real results, rather than filling an interface from fixture answer labels.
The controller alone commits the resulting immutable inference. Final claims
consume both the nested cognitive results and the interaction results through
exact projections of their actual committed fields.

## Recipient-specific interpretation and time

Receipt, understanding, belief acceptance, social acceptance and acknowledgment
remain different inputs and transitions. A received but untrusted message does
not automatically change belief. Distinct recipients can accept different
contents of the same utterance. Several interpretations become alternative
virtual events in the actual M03 product; they neither select the literal meaning
nor silently preserve only the prior belief. These updates leave the designated
physical state separate from recipients' beliefs.

Games share source/model/actor/time-scoped M03 variables for actual world,
speaker view, speaker's expected listener view and actual listener view. Each
game separately maps those views into its declared planning states; no later
plan can overwrite an earlier plan's mapping. Listener-private evidence can
change the actual response while leaving the speaker's forecast unchanged.
Evidence arriving after the decision time does not backfill that forecast.
Per-game and per-commitment-fact assumption environments are consumed at their
actual time. Their outer union is not a substitute for local qualifications.

## Explicit finite message games

Message meanings are finite extensions over an existing one-step listener plan.
This first family uses an explicitly normalized prior, message costs, declared
speaker/listener rationality parameters and recursion depth 0–4. It computes:

1. L0 by conditioning the declared prior on the message extension and the
   relevant listener perspective.
2. A generative fully informed cooperative speaker with utility equal to the
   listener's probability of its state minus message cost, followed by stable
   softmax. This utility family is an explicit model assumption, not a claim
   about all human pragmatic inference.
3. The next listener by conditioning on those computed message likelihoods;
   the bounded speaker/listener recursion is actually evaluated.
4. Actual one-step M05 Q values for each relevant planning state, then expected
   listener action values under the computed message posterior and a declared
   softmax action rule.
5. The actual modeled speaker's choice using its own possibly false or incomplete
   belief state and its expected listener, with either an identification goal
   or declared action-dependent utilities. It never substitutes actual-world
   truth or the actual listener's private knowledge for the speaker's view.

A missing prior stays unspecified, with possible literal sets and no numerical
probabilities; epistemic world counts never become weights. Zero likelihood
stays empty. A known single speaker state needs no arbitrary multi-state prior.
Computed Q values are consumed without reapplying the external input magnitude
bound. The ordinary mental-plan weights remain separately source-declared and
must bind their own current support; they are not the speaker's message prior.

The independent two-state oracle uses R={r}, B={b}, V={r,b}, prior 1/2, cost(R)=1,
other costs 0 and rationality 1. L1(r|V)=1/(1+exp(-0.5)); with crossing utilities
+3/-3 and waiting utility 0, the computed Q is 3(2L1(r|V)-1). An actor believing
b and wanting the listener to cross can favor literally true V, while an actor
mistakenly believing r can sincerely favor R. The output keeps literal truth,
speaker belief, conditional incentives and receiver consequences separate. It
does not certify actual deception, private intent or human calibration.

## Original terms and finite understanding evidence

A commitment retains its offer identity/version, participants, condition,
outcome, deadline, acceptance requirement and explicit effect rules. Acceptance
is either a qualified source act or effective only once received by the offeror,
as declared by the proposal. Receiving an offer later cannot retroactively
qualify an earlier acceptance; only the latest interpretation available at the
act time can match the original terms. This is a conditional source institution,
not a legal rule or system authorization.

The actual M03 queries supply time-local condition/outcome possibilities.
Conditions can be current or latched. Outcome reports are not verified model
performance. Fulfillment and breach remain in history: later state changes do
not erase earlier fulfillment, and late withdrawal does not erase breach.
Withdrawal is either ineffective or effective on matching-version receipt by
the recipient under the explicit rule. A third party or mismatched version does
not release the original terms. Late acceptance, post-acceptance refusal and
unordered contradictory simultaneous acts have unmodeled effects, retained as
frontiers rather than guessed new terms or retroactive verdicts.

Finite INTERPRET/ACK chains require each prior receipt, matching latest version and propositional-content
interpretation and the same two participants fixed by the root message and its
interpreter. A third party cannot complete that pair’s chain. All INTERPRET/ACK
utterances must preserve the exact root proposition and version in this bounded
model; paraphrase equivalence is not inferred. Related act and delivery times
are executed by M03 even when every explicit mental query is earlier. Only
actual APPLIED events with active assumptions qualify as receipt evidence.
Each chain retains and consumes the exact result/event/time receipt and latest
interpretation evidence, its conditional assumption environment and original
content. Later receipt assumptions never backfill an earlier chain. The final receiver must
also have received and interpreted the confirmation for that explicit chain to
be complete. Mere sending, joint hearing or an uncomprehended acknowledgment
cannot establish it. The result reports a finite chain and its limitations,
never infinite common knowledge or certified private understanding.

An M03 resource frontier remains an unresolved commitment, never an invalid
candidate or evidence that acceptance, fulfillment or breach did not occur.
Each condition/outcome row retains its genuine query status and frontier.
Missing frontier assumptions are explicitly NOT_FULLY_COMPUTED, not a proof
with an empty environment. The lifecycle preserves only the fully computed
historical prefix and labels the current state FRONTIER_UNEXPLORED; cached and
restarted delivery retain the same qualification and actual consumed values.

## Persistence, qualification and resource boundaries

The model has at most eight source-local mental models, eight agents per model,
thirty-two utterances/acts, eight commitments, sixteen candidate messages per
game, thirty-two planning states, recursion depth four and acknowledgment depth
eight. Existing M03 world/edge/formula limits and M05 evaluation bounds remain.
The shared execution budget reserves local work and model calls; resource
frontiers cannot acquire strategy values. Full output and cumulative output
limits apply to the actual TaskResult, including replay. Provider calls/spend
and sealed reads are zero in this increment.

Actual domain issues and time-local assumptions remain in committed records,
compact claims and text. The consumer rechecks state mappings, original terms,
M03 condition/outcome references, finite histories, acknowledgment evidence and
the recomputed strategic composition of retained M05 Q values. The full nested
cognitive proof remains in the store, with exact final-field projections.
Existing ACL/source-version gates apply before computation and final delivery;
recovery preserves accepted operations and UNKNOWN holds without resending.

Side-copy migration admits only the exact published qualified M04 predecessor:
179 Python files, code bundle
`d733606ff73ab7f923b082fb0c56ab195db235ded81667739588d6f48664cfde`.
Real schema 3/4 completed/PARTIAL, RETURNED, computed, committed and UNKNOWN
states are exercised using the actual old runtime. M04's scoped limitations,
historical evidence and current-delivery qualification remain intact. Historical
pins, closed grants and original objects are not rewritten.

## Evidence and remaining research

`test_unified_s3_interaction_math.py` supplies independent finite numerical,
event-product, version/time and lifecycle counterexamples.
`test_unified_s3_interaction.py` drives the real authenticated entry, changed
inputs, private-view separation, material-span gates, missing priors, resource
frontiers, compact consumption and durable stream/recovery.
`test_unified_s3_interaction_upgrade.py` executes the exact old runtime.
`witness_unified_interaction.py` binds seven actual composed computations and
consumed fields to the candidate SHA and runtime hashes.

These are injected source interpretations and declared local mechanisms.
Open pragmatic extraction, candidate completeness, richer strategic families,
multi-step interactive action planning, institutional authorization/group-plan
composition, full misunderstanding repair search and integration with actual
M08/M09/M14 suppliers remain required. No partial implementation changes the
formal research exits or moves missing M07 mechanisms to S6 by fiat. Full M07
and all S1–S7/T01–T32 acceptance goals remain unclosed.
