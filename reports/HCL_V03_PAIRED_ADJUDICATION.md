# HCL v0.3 Paired Boundary Fresh Run — Adjudication

Run: `35415058681`

## Raw independent result

- 24 fresh cases / 12 minimal contrast pairs
- passed: **22 / 24**
- mode accuracy: **95.8%**
- uncertainty accuracy: **91.7%**
- schema validity: **100%**

## Failure review

### p16 — behavior-inferred intention

Scene:
- picks up phone and coat;
- walks toward door;
- destination not stated.

The fixture expected CAUSAL_AMBIGUITY / high.

HCL produced:
- SIMPLE;
- low uncertainty;
- summary: preparing to leave/go out is strongly supported, destination/purpose remains unknown.

Adjudication:
**fixture granularity error.**

The question asks what the person intends to do, not the destination. The coarse-grained action "leave/go out" is strongly supported. Unknown finer detail should not inflate uncertainty at the coarser decision level.

This yields a new HCL principle:
**decision-relevant uncertainty must be evaluated at the granularity of the actual question.**

### p24 — ambiguous social gift after a quarrel

HCL correctly:
- selected CAUSAL_AMBIGUITY;
- generated multiple motives;
- recorded missing causal bridges;
- refused to collapse to one motive.

Difference:
- fixture expected high uncertainty;
- HCL used medium.

Adjudication:
**calibration-boundary issue, not structural failure.**

The immediate post-quarrel timing gives apology/reconciliation a stronger prior than an arbitrary motive, while alternatives remain credible.

This yields explicit uncertainty semantics:
- low = explicit/overwhelming at required granularity;
- medium = one interpretation materially favored, credible alternatives remain;
- high = no interpretation clearly privileged / critical bridge missing.

## Conclusion

The raw independent result remains 22/24 and must be preserved.

After adjudication, neither failure demonstrates a structural HCL state error.

However, these principles were derived after observing this suite, so they require another unseen validation suite before HCL v0.3 state semantics can be frozen.
