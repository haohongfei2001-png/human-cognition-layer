# HCL Decision Policy v0.2 — Negotiation Position Semantics

Status: **DESIGN FROZEN FOR SYNTHETIC VALIDATION**

This revision is derived from abstract failure classes, not from copying
benchmark instances.

## Problem

Decision Policy v0.1 sometimes:
- treats an opening position as if it were a hard constraint;
- assumes information probes are observationally neutral;
- delays concrete proposals even when a proposal is both safe and informative.

This can reduce goal progress without improving epistemic quality.

## New rules

### 1. Soft position vs hard constraint

By default, these are **soft positions**:
- opening ask;
- opening offer;
- tentative plan;
- stated preference;
- current target;
- "around X", "maybe X", "I was thinking X".

Treat a position as a **hard constraint** only with evidence such as:
- explicit "final", "firm", "floor", "ceiling", "cap", "will not";
- explicit non-consent;
- legal / policy / safety prohibition;
- externally enforced resource or authority limit.

Do not infer a hard constraint merely because the current position is far from
the acting agent's target.

### 2. Probe intervention cost

An information probe can change the interaction.

Before choosing INFORMATION_PROBE, consider whether the question itself may:
- invite a low self-anchor;
- harden a tentative position into a commitment;
- consume scarce attention / time;
- reveal unnecessary private constraints.

A probe is not automatically safer or more rational than a concrete proposal.

### 3. Concrete proposal as a dual-purpose action

When:
- the acting agent has a concrete target;
- no hard counterpart constraint rules it out;
- a proposal is socially/legal/safety compatible;
- rejection is reversible;

a concrete proposal can both:
- directly advance the goal; and
- reveal the counterpart's flexibility.

Prefer DIRECT_PROGRESS over generic preference elicitation when the concrete
proposal has at least comparable information value and better expected goal
progress.

### 4. Probe-to-progress transition

Do not remain in INFORMATION_PROBE after the decision-relevant gap is small
enough to act.

Once sufficient information exists for a bounded, reversible, materially useful
proposal:
- switch to DIRECT_PROGRESS / COMMIT;
- do not keep asking generic questions about motivation, comfort, or preference.

### 5. Bounded negotiation before EXIT

If the current offer/ask misses the private target but no hard floor/cap is
known:
- normally make at least one bounded counterproposal before EXIT.

EXIT is appropriate when:
- a hard incompatible floor/cap is explicit;
- repeated bounded proposals establish infeasibility;
- further negotiation has negligible expected value;
- a hard consent/legal/safety boundary blocks the route.

### 6. Constraint protection remains unchanged

This revision does not license:
- coercion;
- pressure past explicit refusal;
- illegal action;
- evasion of a known hard cap;
- inventing flexibility unsupported by evidence.

The research target is not "more aggressive." It is more accurate distinction
between **negotiable position** and **binding constraint**.

## Expected architecture

Frozen HCL state
→ Decision Policy v0.2
→ candidate action
→ Action Checker v0.1
→ final action

No change to HCL v0.3 frozen cognition-state semantics.
