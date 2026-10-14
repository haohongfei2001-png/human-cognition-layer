"""Finite, explicitly scoped concept versions and independent classification uses.

A candidate supplies examples and directional criteria, never a learned pattern,
classification, semantic version hash, host namespace or normative permission.
"""
from dataclasses import asdict
from hashlib import sha256
from itertools import product

from hcl.kernel.types import freeze, thaw
from hcl.memory import codec
from hcl.operators.concept_induction import validate_term
from hcl.semantics.compiler import SemanticCompiler
from hcl.semantics.argument_compiler import FRAMES

FIELDS = "versions cases uses choices constraints unmodeled_segments"
DIRECTIONS = ("NECESSARY", "SUFFICIENT", "BICONDITIONAL", "TYPICAL")


def digest(value):
    return sha256(codec.dumps(value)).hexdigest()


def host_context(snapshot):
    return dict(session_id=snapshot.session_id, principal=asdict(snapshot.principal))


def semantic_definition(version):
    """Exclude all span, source-version, proposal-name and coverage identities.

    Example order/ids cannot change the language learned. Assumption names and
    direction are semantic conditions. Withdrawal affects execution, not meaning.
    """
    criteria = []
    for c in version["criteria"]:
        criterion = dict(direction=c["direction"], assumptions=sorted(c["assumptions"]),
            **{kind: sorted((dict(term=r["term"], assumptions=sorted(r["assumptions"]))
                            for r in c[kind]), key=codec.canonical)
               for kind in ("positive", "negative", "boundary")})
        if version.get("definition_language") == "OR_OF_POSITIVE_PARTITION_LGGS_1":
            terms = {r["id"]: r["term"] for r in c["positive"]}
            for kind in ("positive", "negative", "boundary"):
                criterion[kind] = [value for _, value in sorted({codec.canonical(r):r for r in criterion[kind]}.items())]
            criterion["partition"] = sorted([list({codec.canonical(terms[k]):terms[k] for k in sorted(block, key=lambda x:codec.canonical(terms[x]))}.values())
                for block in c["partition"]], key=codec.canonical)
            criterion["definition_language"] = version["definition_language"]
        criteria.append(criterion)
    return dict(purpose=version["purpose"], frame_kind=version["frame_kind"],
                effective_at=version["effective_at"], assumptions=sorted(version["assumptions"]),
                criteria=sorted(criteria, key=codec.canonical))


class ConceptVersionCompiler(SemanticCompiler):
    def compile_data(self, snapshot, segments, value):
        data = thaw(value)
        self._keys(data, FIELDS)
        sources = {s.segment_id: s for s in segments if s.kind == "SOURCE"}
        used = set()

        def refs(value):
            keys = self._strings(value, 64)
            if not keys or not set(keys) <= set(sources):
                raise ValueError("concept source anchors required")
            used.update(keys)

        def rows(value, maximum, minimum=0):
            if type(value) is not list or not minimum <= len(value) <= maximum:
                raise ValueError("bounded concept rows required")
            return value

        def identity(row, seen):
            self._text(row["id"], 64)
            if row["id"] in seen:
                raise ValueError("duplicate concept row")
            seen.add(row["id"])
            refs(row["segment_ids"])

        def time(value):
            if type(value) is not int or not 0 <= value <= 1000000:
                raise ValueError("explicit local concept time required")

        versions, ids = {}, set()
        for v in rows(data["versions"], 16, 1):
            self._keys(v, "id concept_key scope purpose frame_kind effective_at assumptions active_assumptions criteria segment_ids")
            identity(v, ids)
            for name in ("concept_key", "scope"):
                self._text(v[name], 128)
            self._text(v["purpose"], 512)
            time(v["effective_at"])
            if v["frame_kind"] not in FRAMES:
                raise ValueError("concept frame required")
            assumptions = set(self._strings(v["assumptions"], 64))
            active = set(self._strings(v["active_assumptions"], 64))
            if not active <= assumptions:
                raise ValueError("undeclared concept assumptions")
            criteria, sorts, signatures = set(), set(), {}
            for c in rows(v["criteria"], 8, 1):
                self._keys(c, "id direction assumptions positive negative boundary segment_ids")
                identity(c, criteria)
                if c["direction"] not in DIRECTIONS or not set(self._strings(c["assumptions"], 64)) <= assumptions:
                    raise ValueError("explicit directional concept hypothesis required")
                example_ids = set()
                for kind, maximum, minimum in (("positive", 16, 1), ("negative", 32, 0), ("boundary", 32, 0)):
                    for r in rows(c[kind], maximum, minimum):
                        self._keys(r, "id term assumptions segment_ids")
                        identity(r, example_ids)
                        if not set(self._strings(r["assumptions"], 64)) <= assumptions:
                            raise ValueError("undeclared example assumptions")
                        for symbol, signature in validate_term(r["term"]).items():
                            if signatures.setdefault(symbol, signature) != signature:
                                raise ValueError("concept term signature changed")
                        sorts.add(r["term"]["sort"])
            if len(sorts) != 1:
                raise ValueError("common concept case sort required")
            versions[v["id"]] = v
        cases, ids = {}, set()
        for case in rows(data["cases"], 32, 1):
            self._keys(case, "id term assumptions active_assumptions segment_ids")
            identity(case, ids)
            if not set(self._strings(case["active_assumptions"], 64)) <= set(self._strings(case["assumptions"], 64)):
                raise ValueError("undeclared case assumptions")
            if case["term"] is not None:
                validate_term(case["term"])
            cases[case["id"]] = case
        choices, ids = {}, set()
        for choice in rows(data["choices"], 4):
            self._keys(choice, "id versions segment_ids")
            identity(choice, ids)
            keys = self._strings(choice["versions"], 4)
            if not keys or not set(keys) <= set(versions):
                raise ValueError("declared version alternatives required")
            if len({(versions[k]["concept_key"], versions[k]["scope"], versions[k]["frame_kind"]) for k in keys}) != 1:
                raise ValueError("choice crosses concept family or frame")
            choices[choice["id"]] = choice
        count = 1
        for choice in choices.values():
            count *= len(choice["versions"])
        if count > 64:
            raise ValueError("joint version Cartesian bound exceeded")
        for c in rows(data["constraints"], 16):
            self._keys(c, "left right allowed_pairs segment_ids")
            refs(c["segment_ids"])
            if c["left"] not in choices or c["right"] not in choices or c["left"] == c["right"]:
                raise ValueError("joint version constraint requires two choices")
            pairs = rows(c["allowed_pairs"], 16, 1)
            if any(type(p) is not list or len(p) != 2 or p[0] not in choices[c["left"]]["versions"]
                   or p[1] not in choices[c["right"]]["versions"] for p in pairs):
                raise ValueError("invalid joint version pair")
        ids = set()
        for use in rows(data["uses"], 32, 1):
            self._keys(use, "id concept_key scope frame_kind case_id at selector commitment segment_ids")
            identity(use, ids)
            time(use["at"])
            if use["case_id"] not in cases:
                raise ValueError("independent case missing")
            selector = use["selector"]
            self._keys(selector, "kind id")
            if selector["kind"] == "PINNED":
                options = [selector["id"]]
            elif selector["kind"] == "CHOICE" and selector["id"] in choices:
                options = choices[selector["id"]]["versions"]
            else:
                raise ValueError("explicit version use required")
            for key in options:
                v = versions[key]
                if (v["concept_key"], v["scope"], v["frame_kind"]) != (use["concept_key"], use["scope"], use["frame_kind"]) or v["effective_at"] > use["at"]:
                    raise ValueError("unbridged family/frame or future concept version")
                term = cases[use["case_id"]]["term"]
                if term is not None and term["sort"] != v["criteria"][0]["positive"][0]["term"]["sort"]:
                    raise ValueError("case sort differs from concept")
                if term is not None:
                    language = {}
                    for c in v["criteria"]:
                        for kind in ("positive", "negative", "boundary"):
                            for example in c[kind]:
                                language.update(validate_term(example["term"]))
                    if any(symbol in language and language[symbol] != signature for symbol, signature in validate_term(term).items()):
                        raise ValueError("case changes concept symbol signature")
            if use["commitment"] is not None:
                self._keys(use["commitment"], "id terms_version")
                for value in use["commitment"].values():
                    self._text(value, 128)
                if selector["kind"] != "PINNED":
                    raise ValueError("original commitment meaning must be pinned")
        unmodeled = set(self._strings(data["unmodeled_segments"], 1024))
        if not unmodeled <= set(sources) or used | unmodeled != set(sources):
            raise ValueError("concept source coverage incomplete")
        data["host_context"] = host_context(snapshot)
        data["namespace"] = digest(data["host_context"])
        data["source_versions"] = dict(snapshot.source_versions)
        data["source_bindings"] = {k: {n: v for n, v in asdict(s).items() if n != "text"} for k, s in sources.items()}
        return freeze(data)
