# I02 — compact G v6 generic comparator candidate

**Status: provider-free candidate / model semantics unqualified / zero new
provider calls.** The consumed EPC v5 run failed because the G-map model used
all 1,024 frozen output tokens for 16 quoted rows and stopped mid-JSON. That
run and its grant remain closed. This separately versioned candidate addresses
only the generic comparator's map interface; it does not modify HCL runtime or
any historical v5 package, prompt, receipt or outcome.

The [v6 module](../scripts/serious_eval_generic_workspace_v6.py) keeps v3 C
and P byte-identical and gives G-map the same complete ordinary question and
source. It asks G to select up to eight short, distinct relevant source spans,
up to six provisional evidence relations, five answer steps and three open
questions. The map response must fit 3,500 UTF-8 bytes; each quote must fit
180 characters and match one unique original-source span. The checker also
rejects extra/oracle fields, duplicate keys, bad endpoints, invented quotes
and unsupported operations. Failed replacement maps erase prior accepted
state. Source revisions invalidate the map and its dependent links before a
final answer. G-final retains the complete original source and the same four
answer fields as C/P. Two G calls would be charged if this candidate were
later executed; no call was made here.

The limits are chosen to make a normal eight-span map fit the old output scale,
but provider-free tests cannot prove a model will comply or that eight spans
cover a new question. The graph's relation labels are explicitly unverified
model proposals. A future independent development calibration must use a new
source, freeze model limits and costs before output, and include C/P as fair
comparators; the EPC source cannot be rerun. This candidate does not satisfy
I02 independent source diversity or I03 model-semantic qualification.

The tests provide an ordinary-text positive witness: a noon report conflicts
with a dusk notice, the exact quotes and source versions enter G-final beside
the full text, and C/P are unchanged. Negative tests reject invented private
intent, oracle fields, oversized/invalid maps and disconnected relations.
Composition, local revision and v5/package regression tests pass.

**EVALUATION_DELTA:** an executable, bounded generic comparator can now build
and invalidate a compact source-grounded map without changing the historical
v5 run. **HCL answer CAPABILITY_DELTA:** none; H has not been evaluated on this
material. **NEXT_READY:** I02 unexposed source qualification, followed by a
separate model-semantic check if an eligible new development source is found.
LongMemEval remains sealed.
