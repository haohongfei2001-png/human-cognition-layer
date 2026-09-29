# I02 exact-commit exposure screen

**State:** provider-free negative screen. No confirmation case qualified; I02 remains `I02_UNEXPOSED_SOURCE_QUALIFICATION`.

**EVALUATION_CAPABILITY_DELTA:** A proposed source can now be checked against the UTF-8 text of every eligible tracked file in a pinned repository commit. The v5 qualification wrapper executes that check before the older rights, item, lineage and fairness gates. A source already embedded in a development source file, raw provider receipt or runner is rejected even if its URL and lineage IDs are renamed. The receipt records the commit, source digest, matching paths and counts without copying the source into the receipt.

**Real positive witness:** the already development-exposed KPU conflict source was screened against remote `main@7758180cb29b65ad1b925ecad801a4b6fc8d07f0`. It returned `REVIEW_REQUIRED`: 1,252 UTF-8 files scanned; 12-word overlap in `reports/HCL_I02_KPU_CONFLICT_DEVELOPMENT_SOURCE.json`, `reports/HCL_I02_KPU_CPG_V6_RUN_36602249307/raw_receipt.json` and `scripts/run_i02_kpu_cpg_v6_once.py`; 29 LongMemEval-named paths excluded before content access; no oversized path. This is a rejection witness, not a new source or evidence of HCL efficacy.

**Correctness and regression:** temporary Git repositories verify pinned-commit behavior, exact and embedded source overlap, gate ordering, and sealed-path exclusion. A clean older commit and a contaminated newer commit produce different results for the same source. The older v4 gate still runs after a clean snapshot result. No provider calls or spend.

**Boundary:** `TEXT_SNAPSHOT_NO_MATCH` only says the candidate did not match scanned UTF-8 text in that one exact commit under the 12-word window rule. Binary files, large files, earlier Git history, public model training, related writing systems, licensing, privacy, item semantics and blind reviewer independence are outside this screen. The older `PASS_DISJOINT` historical assertion and source-first rights/semantic review remain required. A snapshot miss cannot by itself promote any item to independent confirmation or authorize a model call. LongMemEval content is never read.

**Next:** qualify a genuinely unexposed source system with independently checked rights, privacy, native question semantics and historical disjointness. Preserve the source before comparator outputs and use the already frozen blind review interface. Do not recycle exposed KPU, ACL, MuSR or other screened systems.
