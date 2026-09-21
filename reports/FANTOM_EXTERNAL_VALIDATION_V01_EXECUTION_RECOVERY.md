# FANToM External Validation v0.1 — Execution Recovery

## Failed first launch

Workflow run:
- `35603596148`

Preflight:
- **SUCCESS**
- frozen HCL behavior check passed;
- frozen FANToM selection/protocol check passed;
- unit tests passed;
- official FANToM archive SHA check passed;
- deterministic 32-question reconstruction matched the frozen manifest.

Paid shard execution:
- shard 0: failed
- shard 1: failed
- shard 2: failed
- shard 3: failed

All four shards failed at Python module import with the same error:

`ModuleNotFoundError: No module named 'hcl'`

The exception occurred before the runner constructed a DeepSeek backend and
before any selected FANToM question was sent to a provider.

Therefore:
- provider/model calls in the failed first launch: **0**
- FANToM predictions observed: **0**
- paired outcomes observed: **0**
- no partial result was available for tuning;
- no benchmark prompt, answer or gold label was changed.

The aggregate job failed because no shard artifacts existed. It produced no
experimental interpretation.

## Root cause

When invoked as:

`python scripts/run_fantom_external_v01.py ...`

Python initially places the `scripts/` directory on `sys.path`.
The runner imported `hcl.*` before adding the repository root.

The zero-provider unit tests imported the runner as a module from repository
root and therefore did not expose this script-entrypoint path difference.

## Minimal repair

Commit:
- `cf6acc22bc7c00f23e8785dfb8f1c81501b76e52`

Change:
- compute repository root and prepend it to `sys.path` before importing
  `hcl.*`.

Unchanged:
- 32 frozen question IDs;
- conversation-disjoint selection;
- selection salt;
- FANToM source/archive/hash;
- belief option orientation;
- prompts;
- scoring;
- DeepSeek model/provider/seed/temperature;
- HCL behavior;
- predeclared interpretation thresholds.

Recovery CI additionally runs:
- `python scripts/run_fantom_external_v01.py --help`
- `python scripts/aggregate_fantom_external_v01.py --help`

during zero-provider preflight so script-entrypoint import failures cannot reach
paid shards again.

## Evidence status

Because the failed launch made zero model/provider calls, this recovery is a
plumbing retry of the same frozen predeclared pilot, not a new sample selection
or post-outcome protocol amendment.

The first launch remains in history and must not be erased.

No result from the recovery may be interpreted until all 32 paired questions
complete and the canonical aggregate succeeds.
