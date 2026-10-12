"""Typed first-order syntactic anti-unification with explicit counterexamples.

This is finite term generalization in the tradition of Plotkin, not unrestricted
rule discovery, causal induction, semantic equivalence or calibrated prediction.
"""

from hashlib import sha256
from hcl.kernel.types import thaw
from hcl.memory import codec

VERSION = "hcl-concept-anti-unification-1"


def validate_term(term, *, variables=False):
    count = 0
    signatures = {}
    variable_sorts = {}

    def visit(value, depth):
        nonlocal count
        count += 1
        if count > 256 or depth > 16 or type(value) is not dict:
            raise ValueError("bounded typed term required")
        if type(value.get("sort")) is not str or not 0 < len(value["sort"]) <= 128:
            raise ValueError("explicit term sort required")
        value["sort"].encode()
        if value.get("kind") == "VARIABLE" and variables:
            if (
                set(value) != {"kind", "sort", "id"}
                or type(value["id"]) is not str
                or not value["id"]
            ):
                raise ValueError("explicit generated variable identity required")
            if variable_sorts.setdefault(value["id"], value["sort"]) != value["sort"]:
                raise ValueError("variable changes sort")
            return
        if (
            set(value) != {"kind", "sort", "symbol", "arguments"}
            or value["kind"] != "TERM"
            or type(value["symbol"]) is not str
            or not 0 < len(value["symbol"]) <= 128
            or type(value["arguments"]) is not list
            or len(value["arguments"]) > 4
        ):
            raise ValueError("ground typed term required")
        value["symbol"].encode()
        for arg in value["arguments"]:
            visit(arg, depth + 1)
        signature = (value["sort"], tuple(arg["sort"] for arg in value["arguments"]))
        if signatures.setdefault(value["symbol"], signature) != signature:
            raise ValueError("term symbol signature changes")

    visit(thaw(term), 0)
    return signatures


def generalize_examples(positive, negative, *, max_work=100000):
    positive, negative = thaw(positive), thaw(negative)
    if (
        type(positive) is not list
        or not 1 <= len(positive) <= 16
        or type(negative) is not list
        or len(negative) > 32
        or type(max_work) is not int
        or not 0 <= max_work <= 1000000
    ):
        raise ValueError("finite examples and work allowance required")
    ids, signatures = set(), {}
    for row in (*positive, *negative):
        if (
            type(row) is not dict
            or set(row) != {"id", "term"}
            or type(row["id"]) is not str
            or not 0 < len(row["id"]) <= 128
            or row["id"] in ids
        ):
            raise ValueError("unique explicit example identities required")
        ids.add(row["id"])
        for symbol, signature in validate_term(row["term"]).items():
            if signatures.setdefault(symbol, signature) != signature:
                raise ValueError("example language changes symbol sorts")
    if len({row["term"]["sort"] for row in (*positive, *negative)}) != 1:
        raise ValueError("examples require a common target sort")
    work, frontier = 0, []
    disagreements = {}
    pattern = None
    results = [
        dict(
            id=row["id"],
            expected="POSITIVE" if i < len(positive) else "NEGATIVE",
            status="UNCOMPUTED",
            substitution={},
        )
        for i, row in enumerate((*positive, *negative))
    ]

    class Exhausted(Exception):
        pass

    def charge():
        nonlocal work
        if work >= max_work:
            raise Exhausted()
        work += 1

    def lgg(terms):
        charge()
        if all(term == terms[0] for term in terms):
            return terms[0]
        if len({term["sort"] for term in terms}) != 1:
            raise ValueError("term disagreement crosses declared sorts")
        if all(
            (term["symbol"], len(term["arguments"]))
            == (terms[0]["symbol"], len(terms[0]["arguments"]))
            for term in terms
        ):
            return dict(
                kind="TERM",
                sort=terms[0]["sort"],
                symbol=terms[0]["symbol"],
                arguments=[
                    lgg([term["arguments"][i] for term in terms])
                    for i in range(len(terms[0]["arguments"]))
                ],
            )
        key = codec.canonical(terms)
        if key not in disagreements:
            disagreements[key] = dict(
                kind="VARIABLE", sort=terms[0]["sort"], id="v" + str(len(disagreements))
            )
        return disagreements[key]

    def match(pattern, term, bindings):
        charge()
        if pattern["sort"] != term["sort"]:
            return False
        if pattern["kind"] == "VARIABLE":
            if pattern["id"] in bindings:
                return bindings[pattern["id"]] == term
            bindings[pattern["id"]] = term
            return True
        return (
            pattern["symbol"] == term["symbol"]
            and len(pattern["arguments"]) == len(term["arguments"])
            and all(
                match(a, b, bindings)
                for a, b in zip(pattern["arguments"], term["arguments"])
            )
        )

    try:
        pattern = lgg([row["term"] for row in positive])
    except Exhausted:
        frontier.append("ANTI_UNIFICATION_FRONTIER")
    if pattern is not None:
        for result, row in zip(results, (*positive, *negative)):
            try:
                bindings = {}
                matched = match(pattern, row["term"], bindings)
                result["status"] = "MATCH" if matched else "NO_MATCH"
                result["substitution"] = bindings if matched else {}
            except Exhausted:
                frontier.append("GENERALIZATION_COVERAGE_FRONTIER")
                break
    counterexamples = tuple(
        row["id"]
        for row in results
        if row["expected"] == "NEGATIVE" and row["status"] == "MATCH"
    )
    return dict(
        schema=VERSION,
        pattern=pattern,
        examples=results,
        work=work,
        frontier=tuple(sorted(set(frontier))),
        counterexample_ids=counterexamples,
        status=(
            "PARTIAL"
            if frontier
            else (
                "REFUTED_BY_DECLARED_COUNTEREXAMPLE"
                if counterexamples
                else "CONSISTENT_WITH_DECLARED_EXAMPLES"
            )
        ),
        input_identity=sha256(codec.dumps([positive, negative])).hexdigest(),
        qualifications=(
            "TYPED_SYNTACTIC_GENERALIZATION_NOT_SEMANTIC_LAW",
            "UNSEEN_AND_OPEN_WORLD_CASES_NOT_CERTIFIED",
        ),
    )
