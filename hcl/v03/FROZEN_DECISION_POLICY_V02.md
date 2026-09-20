# HCL v0.3 + Decision Policy v0.2 + Action Checker v0.1 — Holdout Freeze

Established after:
- negotiation-position synthetic baseline on v0.1: run `35511100930`, raw **11/12**;
- baseline adjudication: sole miss was a strategy-label boundary, not a semantic
  behavior failure;
- Decision Policy v0.2 negotiation-position synthetic: run
  `35511183476`, **12/12 PASS**.

The v0.2 change is interpreted as making a latent capability more reliable in
interactive contexts, not as learning a completely new concept.

Frozen file content SHAs:
- `hcl/v03/answer_loop.py`: `f62781da3621689dbed07e3a34dd444f7fd80d37`
- `hcl/v03/decision_policy.py`: `dd1457048b121357498a625ca29edbd8acc43ad5`
- `hcl/v03/action_checker.py`: `1ecd9917532aec1710a16170f89dc42eca4fcc92`
- `hcl/integrations/sotopia_agent.py`: `2e761168e5a9572ad5909ef1017b1c98d7b4b18d`

Pinned upstream SOTOPIA:
- `a0aaafb440e570e5e61b7c44a44e5e417c545383`

No HCL cognition, Decision Policy, Action Checker, or SOTOPIA agent-policy
changes are permitted until the next predeclared external holdout completes.
