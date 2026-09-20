# Decision Policy v0.2.1 — Verification Stopping and Observability

Status: **DESIGN FROZEN FOR INDEPENDENT SYNTHETIC VALIDATION**

This is a minimal decision/action-layer repair. It does not alter the frozen
HCL v0.3 cognition-state semantics.

## Failure class

Confirmed external failure:

> non-resolving verification deadlock under option decay

The cognition layer may correctly identify a critical uncertainty while the
decision layer repeatedly selects verification actions whose results are not
observable/resolvable inside the current interaction. Opportunity value then
decays without a bounded fallback.

The failure reproduced across different SOTOPIA env-agent combinations, so the
repair targets the abstract control problem rather than a benchmark instance.

## New structured decision state

Decision Policy now emits:

- `verification_status`:
  - `NOT_NEEDED`
  - `RESOLVABLE`
  - `UNRESOLVABLE_IN_INTERFACE`
  - `EXHAUSTED`
- `equivalent_probe_count`: number of materially equivalent prior attempts;
- `option_decay`: `low|medium|high`;
- `fallback_required`: whether further equivalent probing should stop.

The SOTOPIA adapter passes a compact structured history of prior HCL decisions
and final actions into the next Decision Policy call.

## Rules

1. **Equivalent-probe family**
   - rephrasing the same request does not reset the probe budget;
   - repeating the same external action counts as the same family unless a new
     evidence channel is actually introduced.

2. **Observable resolution**
   - before probing, ask whether the result can become visible in the current
     interface and relevant time horizon;
   - an off-interface action with no represented return path is not a high-value
     repeated probe.

3. **Finite probe budget**
   - after two or more equivalent attempts with no new decision-relevant
     evidence, normally classify the route as `EXHAUSTED`;
   - a further probe is allowed only through a genuinely new resolvable channel.

4. **Option decay**
   - waiting has a cost when an offer, reservation, deadline, attention window,
     or other useful option can disappear;
   - compare cost-of-waiting with risk-of-acting.

5. **Bounded fallback**
   - when verification is exhausted/unresolvable, preserve the uncertainty and
     choose a constraint-respecting fallback:
     conditional or reversible commitment, alternative path, defer, or exit.

6. **No fabricated resolution**
   - never invent the result of an external call/check simply to escape a
     deadlock.

7. **Hard-boundary protection**
   - probe exhaustion never authorizes crossing legal, ownership, consent,
     safety, or explicit hard constraints.

## Integration boundary

Frozen HCL state
→ Decision Policy v0.2.1 verification state
→ candidate action
→ Action Checker
→ final action

Action Checker treats `EXHAUSTED`,
`UNRESOLVABLE_IN_INTERFACE`, or `fallback_required=true` as an explicit
anti-loop signal.

## Synthetic gate

The validation suite must use independent domains and must include both positive
and negative controls:

- repeated off-interface verification + expiring option;
- repeated unanswered preference probes + reversible default;
- new resolvable channel after failed prior probes;
- cheap waiting with no option decay;
- irreversible legal/ownership uncertainty;
- hard safety/consent boundaries;
- ordinary no-verification direct progress.

No SOTOPIA dialogue text, personas, prices, or exact record-sale scenario may be
copied into the suite.

## Gate

Pass requires:
- all synthetic cases satisfy allowed strategy family;
- structured verification status matches the predeclared expectation;
- exhausted/unresolvable cases requiring fallback do not choose
  `INFORMATION_PROBE`;
- probe-count lower bounds hold where predeclared.

Only after this gate passes may another unused SOTOPIA expanded-combo holdout be
consumed.
