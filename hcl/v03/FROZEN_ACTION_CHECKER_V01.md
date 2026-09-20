# HCL v0.3 + Decision Policy v0.1 + Action Checker v0.1 — Fresh Holdout Freeze

This freeze is established immediately after:
- Action Checker synthetic gate: run `35492634398` — **14/14 PASS**
- SOTOPIA action-checker integration smoke: run `35492711369` — **SUCCESS**

The next external validation uses previously unused SOTOPIA-Hard ordinals
`20-29`. No module tuning is permitted until that holdout is complete.

Frozen file content SHAs:
- `hcl/v03/answer_loop.py`: `f62781da3621689dbed07e3a34dd444f7fd80d37`
- `hcl/v03/decision_policy.py`: `eb0cace3b95f38a6b595cc892a5c39d5b097b693`
- `hcl/v03/action_checker.py`: `1ecd9917532aec1710a16170f89dc42eca4fcc92`
- `hcl/integrations/sotopia_agent.py`: `2e761168e5a9572ad5909ef1017b1c98d7b4b18d`

Pinned upstream SOTOPIA:
- `a0aaafb440e570e5e61b7c44a44e5e417c545383`

Claim boundary:
- synthetic and smoke gates establish implementation behavior only;
- Hard ordinals 20-29 are the next fresh generalization test;
- Hard ordinals 0-19 are no longer fresh evidence for this implementation.
