"""Externally sourced formal models under an explicitly supplemented contract.

No published answers or hidden generator structures enter this adapted task.
The ordinary-language causal sentences are not equations without that contract.
"""

from __future__ import annotations
import hashlib, json, re
from itertools import product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from hcl.v09 import CausalModel, StructuralRule, SCOPE
from hcl.v04.model import EventRecord

SHA = "39f935a48fb997869c1e4488c9a2b902dc08acd876da557c675722c269391a76"
COMMIT = "c6225dfa00b7a89ccfeae67797b9a6d80e48e44c"
SALT = "HCL-V09-COUNTERBENCH-DEV-V01"
MANIFEST = ROOT / "eval/v09/counterbench_dev_selection_v01.json"
CONTRACT = """This is a supplemented, closed-world Boolean structural-model exercise, not a claim about ordinary real-world causation. Each listed positive causal clause is stipulated to be the complete equation child = parent, joint parents use AND, alternative parents use OR, and a negative child means child = NOT(parent expression). No other equation or noise term is assumed; variables without an equation are unconstrained exogenous Boolean context. Hold the same exogenous context in factual and alternative worlds, except explicitly intervened variables. Source observations constrain only the factual world. If observations contradict the model, or possible factual contexts give different target outcomes, answer UNKNOWN instead of guessing. The result is conditional on these declared assumptions, never a real or private mental fact."""
CLAUSE = re.compile(
    r"(?P<parents>\w+(?: (?:and|or) \w+)*) (?:together )?causes? (?P<neg>not )?(?P<child>\w+)\Z"
)
QUESTION = re.compile(r"Would (\w+) occur if not (\w+) instead of \2\?\Z")


def sha(value):
    return hashlib.sha256(
        value.encode() if isinstance(value, str) else value
    ).hexdigest()


def source_model(text, case_id):
    prefix = "We know that "
    if not text.startswith(prefix):
        raise ValueError("unsupported source syntax")
    causal, sep, observed = text[len(prefix) :].partition(". We observed ")
    causal = causal.rstrip(".")
    rules = []
    clauses = []
    variables = set()
    for chunk in causal.split(", "):
        chunk = chunk.removeprefix("and ")
        match = CLAUSE.fullmatch(chunk)
        if not match:
            raise ValueError("ambiguous or malformed source causal clause")
        p = match["parents"]
        parts = re.split(r" (?:and|or) ", p)
        ops = re.findall(r" (and|or) ", p)
        if len(set(ops)) > 1:
            raise ValueError("parent precedence not explicit")
        expression = f"not ({p})" if match["neg"] else p
        rules.append(StructuralRule(match["child"], expression, chunk))
        clauses.append(
            (
                match["child"],
                tuple(parts),
                ops[0] if ops else "copy",
                bool(match["neg"]),
            )
        )
        variables.update(parts)
        variables.add(match["child"])
    targets = {r.target for r in rules}
    roots = variables - targets
    model = CausalModel(
        case_id, case_id, tuple(sorted(variables)), tuple(sorted(roots)), tuple(rules)
    )
    facts = {}
    if sep:
        observed = observed.rstrip(".")
        names = observed.split(" and ")
        if any(x not in variables for x in names):
            raise ValueError("unsupported observed source")
        facts = {x: 1 for x in names}
    return model, facts, clauses


def query_task(text, model, facts):
    match = QUESTION.fullmatch(text)
    if not match or match[1] not in model.variables or match[2] not in model.variables:
        raise ValueError("unsupported query")
    target, changed = match[1], match[2]
    # The native wording's factual X is explicitly restated as an assumption
    # to every arm. It is a query constraint, never a construction input.
    factual = dict(facts)
    if changed in factual and factual[changed] != 1:
        raise ValueError("contradictory explicit query baseline")
    factual[changed] = 1
    return target, factual, {changed: 0}


def reference_values(model, clauses, target, observations, interventions):
    """Independent full truth-table equation satisfaction (no runtime AST/order)."""
    assignments = [
        dict(zip(model.variables, bits))
        for bits in product((0, 1), repeat=len(model.variables))
    ]

    def valid(world, changes):
        if any(world[k] != v for k, v in changes.items()):
            return False
        for child, parents, operator, negative in clauses:
            if child in changes:
                continue
            inputs = [world[x] for x in parents]
            result = (
                all(inputs)
                if operator == "and"
                else any(inputs) if operator == "or" else inputs[0]
            )
            result = int(not result) if negative else int(result)
            if world[child] != result:
                return False
        return True

    factual = [
        w
        for w in assignments
        if valid(w, {}) and all(w[k] == v for k, v in observations.items())
    ]
    alternative = [w for w in assignments if valid(w, interventions)]
    values = set()
    for old in factual:
        for new in alternative:
            if all(
                new[x] == (interventions[x] if x in interventions else old[x])
                for x in model.exogenous
            ):
                values.add(new[target])
    return sorted(values)


def selection(source):
    if sha(source) != SHA:
        raise ValueError("source digest drift")
    rows = json.loads(source)
    if len(rows) != 1000:
        raise ValueError("source count drift")
    # Project away answer immediately; no answer values or generator truth read.
    public = [
        {k: r[k] for k in ("question_id", "given_info", "question", "type", "meta")}
        for r in rows
    ]
    selected = []
    families = set()
    for kind in ("basic", "conditional"):
        candidates = sorted(
            (
                r
                for r in public
                if r["type"] == kind and r["meta"]["graph_id"] != "graph5"
            ),
            key=lambda r: sha(SALT + "|" + str(r["question_id"])),
        )
        count = 0
        for row in candidates:
            try:
                model, facts, clauses = source_model(row["given_info"], "candidate")
                query_task(row["question"], model, facts)
            except ValueError:
                continue
            # Rename by first occurrence in source clauses, excluding factual
            # observations/query, to exclude structural clones across names.
            rename = {}
            for child, parents, op, negative in clauses:
                for n in parents + (child,):
                    if n not in rename:
                        rename[n] = "V" + str(len(rename))
            family = sha(
                json.dumps(
                    [
                        (rename[c], [rename[p] for p in ps], op, neg)
                        for c, ps, op, neg in clauses
                    ]
                )
            )
            if family in families:
                continue
            families.add(family)
            cid = f"cf-dev-{len(selected)+1:02d}"
            selected.append(
                {
                    "case_id": cid,
                    "question_id": str(row["question_id"]),
                    "source_sha256": sha(row["given_info"]),
                    "question_sha256": sha(row["question"]),
                    "structural_family_sha256": family,
                    "source": row["given_info"],
                    "question": row["question"],
                    "kind": kind,
                }
            )
            count += 1
            if count == 4:
                break
        if count != 4:
            raise ValueError("insufficient qualified source families")
    return selected


def manifest_rows(selected):
    return [
        {k: v for k, v in x.items() if k not in ("source", "question")}
        for x in selected
    ]


def verified_selection(source):
    selected = selection(source)
    manifest = json.loads(MANIFEST.read_text())
    if (
        manifest.get("selected") != manifest_rows(selected)
        or manifest.get("source_sha256") != SHA
        or manifest.get("contract_sha256") != sha(CONTRACT)
        or manifest.get("source_commit") != COMMIT
        or manifest.get("salt") != SALT
    ):
        raise ValueError("frozen selection drift")
    return selected


def source_event(item):
    return EventRecord(
        event_id=item["case_id"],
        source_id="CounterBench-public-causal-sentences-with-supplemented-contract",
        raw_text=CONTRACT + "\n" + item["source"],
        valid_time="2026-01-01T00:00:00+00:00",
        recorded_at="2026-01-01T00:00:00+00:00",
        metadata={
            "reader_only": True,
            "causal_model_scope": SCOPE,
            "chronology": "INGESTION_PLACEHOLDER",
        },
    )


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    args = p.parse_args()
    print(
        json.dumps(
            {
                "selected": len(verified_selection(args.source.read_bytes())),
                "provider_calls": 0,
            }
        )
    )
