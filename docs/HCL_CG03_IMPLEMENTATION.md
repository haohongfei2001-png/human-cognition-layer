# HCL-CG-03 provider-free implementation and limits

CG03-B/C/D extends the explicit CG03-A operation. A request must supply either
a `ResponsibilityCase` with source `EventRecord`s or set
`responsibility_analysis=True` with a short ordinary narrative, a focal actor,
and one to three caller-supplied `NarrativePremise`s. A generic responsibility
word in a query does not activate the capability.

## What is checked

- **Source and time:** each typed claim binds an actor, focal action, source
  event, exact quote, polarity, authority and action time. A later report needs
  an explicit retrospective action-time expression. Later learning is rejected
  as action-time knowledge. Causal contribution needs an explicit causal claim
  sourced no earlier than the outcome; action plus outcome alone stays unknown.
- **Access:** reader, character and observer views use the existing v0.6
  source visibility rules plus event and record-time cutoffs. Hidden action,
  outcome or premise sources remove the operation from that view. Hidden factor
  sources never appear in factor receipts or support a premise.
- **Five separate factors:** causal contribution, knowledge, foreseeability,
  control and stated intention each receive source support, contradiction,
  contest, attribution-only or unknown. A third-party intention report is an
  attribution. A self-attributed causal link is not treated as established
  causal support. Opposed source claims remain contested.
- **Conditional premise:** the checker evaluates only explicitly structured
  `FactorRequirement`s and only claims inside that premise's declared source
  basis. It returns met, counterexample or unresolved for each requirement and
  a premise-dependent result. A free-text rule with no structured requirements
  remains unresolved. There is no overall moral or legal verdict.
- **Ordinary text:** a deliberately small ordered prose grammar accepts two to
  twelve exact source lines, one focal action, one later outcome, explicit
  factor phrases and caller-supplied structured premises. Every accepted claim
  has an exact line span. Ambiguous or unsupported lines produce diagnostics;
  missing or ambiguous action/outcome fails closed. No model extraction is
  invoked. The debug receipt stores parser input, output IDs, diagnostics,
  checked context and actual final messages.

The source checker is a bounded claim checker. Exact phrase and authority
validation do not prove that a source claim is true, or that the caller's
normative premise is sound. `SUPPORTED_CLAIM` and
`CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS` must be read with those limits.
The one-time synthetic development comparison selects RETAIN for this bounded
mechanism, with H 28/28 versus P 21/28, G 20/28 and H-new 23/28. This is a
development signal, not independent/fresh external utility or broad moral
competence. The component remains explicit and optional, including because
H cost about 4.34 times P. See the source-first closure.

For an ablation, `responsibility_checker_enabled=False` leaves the same case
input and caller premise in context while removing only the checked factor and
premise state. This is the CG03-E H-new treatment boundary; it makes no paid
call by itself.
