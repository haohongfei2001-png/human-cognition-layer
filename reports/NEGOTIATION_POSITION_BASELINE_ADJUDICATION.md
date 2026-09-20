# Negotiation-Position Synthetic Baseline Adjudication

Run: `35511100930`

Frozen Decision Policy v0.1 was evaluated on 12 independently written
negotiation-position fixtures before the v0.2 prompt change.

Raw result:
- **11 / 12**
- one raw failure: `np02_initial_office_rent_counter`

The raw failure is a strategy-label boundary rather than a behavioral failure.

Expected label:
- `DIRECT_PROGRESS`

Actual label:
- `INFORMATION_PROBE`

But the actual chosen intent was to make a **specific bounded counterproposal at
the acting agent's ceiling**, ask whether that price is possible, and leave only
if the counterparty cannot move into the feasible range.

That behavior is the intended repair target.

Therefore:
- raw 11/12 is preserved;
- no post-hoc 12/12 score is claimed;
- the baseline suite does **not** establish a broad v0.1 negotiation incapacity;
- the justification for Decision Policy v0.2 comes primarily from repeated
  SOTOPIA trajectory-level evidence, where v0.1 actually chose an open-ended
  self-anchor probe in one case and immediate EXIT from an opening ask in
  another.

Scientific implication:

The v0.2 prompt revision should be interpreted as **making already latent
capability more reliable in interactive contexts**, not teaching an entirely
new concept that v0.1 lacked.
