"""Four public PyArg author examples, not a benchmark or fresh efficacy set."""

import ast
import hashlib
import itertools
import json
from pathlib import Path

REVISION = "f907bac94cbdd663839300b3b7523d4d958ff36f"
SOURCE_REPO = "DaphneOdekerken/PyArg"
REFERENCES = [
    ("src/py_arg_tests/test_af_from_scratch.py", "test_three_argument_example", "af"),
    (
        "src/py_arg_tests/test_af_complete_semantics.py",
        "test_af_complete_semantics",
        "af",
    ),
    ("src/py_arg_tests/test_af_canonical_constructions.py", "test_construct_af", "af"),
    (
        "src/py_arg_tests/test_incomplete_argumentation_framework.py",
        "test_ac_example_4",
        "af1",
    ),
]
MANIFEST = Path(__file__).resolve().parents[1] / "eval/v10/pyarg_dev_selection_v01.json"
CONTRACT = (
    "This is an explicit complete Dung argumentation framework, not a moral verdict, world truth, or private belief. Arguments are atomic nodes; the listed directed attacks are all attacks. "
    "A set attacks a node if one of its members attacks it. A set defends a node if it attacks every attacker of that node. "
    "An admissible set is conflict-free and defends every member. A complete extension is an admissible set containing every node it defends. "
    "The grounded extension is the least complete extension. IN is the extension, OUT all nodes it attacks, UNDEC the rest. "
    "Return every requested labelling exactly; preserve cycles and multiple complete extensions without forcing a winner."
)


def sha(s):
    return hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()


def graph_from_source(text, method, assignment):
    """Interpret only static constructor declarations; never execute source/assertions."""
    tree = ast.parse(text)
    lines = text.splitlines()
    base = {}
    quotes = {}

    def value(node, env):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            return env[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            return [value(x, env) for x in node.elts]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            args = [value(x, env) for x in node.args]
            kw = {x.arg: value(x.value, env) for x in node.keywords}
            if node.func.id == "Argument" and len(args) == 1 and not kw:
                return ("argument", args[0])
            if node.func.id == "Defeat" and len(args) == 2 and not kw:
                return ("attack", args[0][1], args[1][1])
            if node.func.id == "AbstractArgumentationFramework":
                arguments = kw.get("arguments", args[1] if len(args) > 1 else None)
                attacks = kw.get("defeats", args[2] if len(args) > 2 else None)
                if arguments is None or attacks is None:
                    raise ValueError("incomplete constructor")
                if any(a[0] != "argument" for a in arguments) or any(
                    e[0] != "attack" for e in attacks
                ):
                    raise ValueError("typed static constructor required")
                return {
                    "arguments": [a[1] for a in arguments],
                    "attacks": [[e[1], e[2]] for e in attacks],
                }
        raise ValueError("unsupported static source expression")

    def declarations(body, env, q, wanted=None):
        for stmt in body:
            if (
                not isinstance(stmt, ast.Assign)
                or len(stmt.targets) != 1
                or not isinstance(stmt.targets[0], ast.Name)
            ):
                continue
            name = stmt.targets[0].id
            try:
                v = value(stmt.value, env)
            except (ValueError, KeyError, IndexError):
                # An unsupported reassignment invalidates the earlier binding.
                env.pop(name, None)
                q.pop(name, None)
                continue
            env[name] = v
            q[name] = "\n".join(lines[stmt.lineno - 1 : stmt.end_lineno])
            if name == wanted:
                if not isinstance(v, dict):
                    raise ValueError("framework assignment required")
                # Retain declarations only; no author assertion/oracle/annotation.
                source = "\n".join(q.values())
                return v, source
        return None

    declarations(tree.body, base, quotes)
    functions = [
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == method
    ]
    matches = []
    for fn in functions:
        r = declarations(fn.body, dict(base), dict(quotes), assignment)
        if r is not None:
            matches.append(r)
    if len(matches) != 1:
        raise ValueError("unique static source example required")
    return matches[0]


def family(graph):
    # This four-source utility is bounded at five nodes, making exact alias
    # deduplication affordable. This is not a runtime graph cap/heuristic.
    ids = graph["arguments"]
    edges = graph["attacks"]
    enc = []
    if len(ids) > 5:
        raise ValueError("example-source qualification cap exceeded")
    for permutation in itertools.permutations(range(len(ids))):
        rename = dict(zip(ids, permutation))
        enc.append(tuple(sorted((rename[a], rename[b]) for a, b in edges)))
    return sha(json.dumps([len(ids), min(enc)]))


def prepared(source_dir):
    candidates = []
    for path, method, assignment in REFERENCES:
        raw = (source_dir / path).read_bytes()
        g, s = graph_from_source(raw.decode(), method, assignment)
        candidates.append(
            {
                "source_path": path,
                "source_file_sha256": sha(raw),
                "method": method,
                "assignment": assignment,
                "source": s,
                "source_sha256": sha(s),
                "graph": g,
                "family_sha256": family(g),
            }
        )
    candidates.sort(key=lambda x: sha("HCL-V10-PYARG-DEV-V01|" + x["source_sha256"]))
    if len({x["family_sha256"] for x in candidates}) != 4:
        raise ValueError("renamed graph family overlap")
    return [
        x
        | {
            "case_id": f"arg-dev-{j+1:02d}",
            "semantics": "grounded" if j % 2 == 0 else "complete",
        }
        for j, x in enumerate(candidates)
    ]


def manifest(items):
    return {
        "format": "hcl-v10-pyarg-author-example-dev-v01",
        "repo": SOURCE_REPO,
        "revision": REVISION,
        "license": "MIT",
        "scope": "four source-inspected public author examples, not native benchmark/fresh or natural-language efficacy",
        "cases": [
            {k: v for k, v in x.items() if k not in ["source", "graph"]} for x in items
        ],
    }


def verified_selection(source_dir):
    items = prepared(source_dir)
    if manifest(items) != json.loads(MANIFEST.read_text()):
        raise ValueError("source/selection drift")
    return items


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--freeze", action="store_true")
    a = p.parse_args()
    items = prepared(a.source_dir)
    if a.freeze:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(
            json.dumps(manifest(items), sort_keys=True, indent=2) + "\n"
        )
    else:
        verified_selection(a.source_dir)
    print(
        json.dumps(
            {
                "cases": len(items),
                "selection_sha256": sha(MANIFEST.read_bytes()),
                "provider_calls": 0,
            }
        )
    )
