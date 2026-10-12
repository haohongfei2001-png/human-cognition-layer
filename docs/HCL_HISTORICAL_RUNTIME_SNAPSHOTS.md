# Historical runtime source snapshots

These frozen evidence branches make previously local predecessor Python runtimes
readable by ordinary repository checkout in CI. They are historical test inputs,
not shipped releases, new capability evidence, an active implementation branch,
or another execution plan. The original local commits, test assertions and exact
runtime pins remain unchanged. No fixture, user content, evaluation package,
credential, or workflow is included in a snapshot tree.

Only `hcl/**/*.py` regular files (mode `100644`) are present. The complete ordered
path/blob inventory is equal to the original commit's Python-only projection;
this is not a claim that the original full repository tree equals the snapshot.
Runtime hashes use the existing canonical relative-path-to-SHA256 inventory.

| Files | Original local commit | Remote source snapshot | Exact Python projection tree | Original runtime hash |
| --- | --- | --- | --- | --- |
| 194 | `09ff3935bc87ca44cc95271dc507be630ec702c6` | `c80d48eca23147e31802614f249dbbf7ac25e9d7` | `13cd5cbc6f365e39f421813212eeb1e887a15f8a` | `0cff907d511fc684251b4bcce902e5800b372885ed4b27bd8989f99c22fc436f` |
| 202 | `769c07459c784c55c8292c82c75ab130db924eee` | `5f797274a12d29295b90f1ecb9c3b61372463445` | `4700d9d2b0522bc6ac6328b785327d5ffef57289` | `856f2077af271a5a69e2d4261bf61cc22a414742b38b9637d428951eb97b50c0` |
| 214 | `855e440f95f43297a7c38c1d689a3ac13f03b52c` | `25a94fb7bf3fa317c2f68c96bb9f47568deeafe6` | `926267371ffd37da3b7c82841415ab3435759515` | `33bf314734f08aac7898c67bb5e2559fd5bfdea6dfe4e704269050c2a536b9ff` |

The corresponding immutable evidence refs are
`evidence/hcl-runtime-194-09ff3935`, `evidence/hcl-runtime-202-769c0745`, and
`evidence/hcl-runtime-214-855e440f`. A fresh empty Git repository fetched these
refs and verified the complete Python inventory and exact hashes. Actual CI
migration tests must additionally materialize the selected remote commit, enforce
the same file-count/hash pin, and execute the unchanged historical/current
assertions; local reachability checks alone are not a CI pass.

A snapshot may contain limitations or defects later corrected. Historical replay
does not grant its outputs current delivery eligibility. The current runtime's
qualification, source access, tombstone, and exact commit guards remain required.
Only disposable synthetic test stores are created or erased for these checks.
