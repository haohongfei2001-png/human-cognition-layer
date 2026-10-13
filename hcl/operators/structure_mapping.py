"""Bounded consistent relational mappings and hypothetical transfer checks.

Inspired by structure-mapping (Gentner; Falkenhainer/Forbus/Gentner), not a
reimplementation or validation of SME. Predicate compatibilities are explicit
semantic hypotheses. Labels, embeddings and observed answers never rank pairs.
"""

from hashlib import sha256
from hcl.memory import codec
from hcl.kernel.types import freeze, thaw

VERSION = "hcl-structural-mapping-1"
MAX_ENTITIES = 16
MAX_FACTS = 32
MAX_PREDICATES = 16
MAX_DEPTH = 16
MAX_SEARCH_STATES = 8192


def _node_id(node):
    """Content identity of one flat node, never an expanded relation tree."""
    return sha256(codec.dumps(freeze(node))).hexdigest()


def _text(value):
    if type(value) is not str or not value or len(value) > 128:
        raise ValueError("bounded explicit structural identity required")
    value.encode()
    return value


def _domain(value):
    if type(value) is not dict or set(value) != {"entities", "predicates", "facts"}:
        raise ValueError("typed structural domain required")
    for key, limit in (
        ("entities", MAX_ENTITIES),
        ("predicates", MAX_PREDICATES),
        ("facts", MAX_FACTS),
    ):
        if type(value[key]) is not list or len(value[key]) > limit:
            raise ValueError("structural domain bound exceeded")
    entities, predicates, facts = {}, {}, {}
    for row in value["entities"]:
        if set(row) != {"id", "type"} or _text(row["id"]) in entities:
            raise ValueError("unique typed entities required")
        entities[row["id"]] = _text(row["type"])
    for row in value["predicates"]:
        if (
            set(row) != {"id", "kind", "arguments"}
            or _text(row["id"]) in predicates
            or row["kind"] not in ("RELATION", "ATTRIBUTE")
            or type(row["arguments"]) is not list
            or not 1 <= len(row["arguments"]) <= 4
        ):
            raise ValueError("unique typed predicates required")
        for kind in row["arguments"]:
            if kind != "FACT":
                if type(kind) is not str or not kind.startswith("ENTITY:"):
                    raise ValueError("explicit argument sort required")
                _text(kind[7:])
        if row["kind"] == "ATTRIBUTE" and (
            len(row["arguments"]) != 1 or row["arguments"][0] == "FACT"
        ):
            raise ValueError("attributes apply only to a single entity")
        predicates[row["id"]] = row
    for row in value["facts"]:
        if (
            set(row) != {"id", "predicate", "arguments", "negated"}
            or _text(row["id"]) in facts
            or row["predicate"] not in predicates
            or type(row["arguments"]) is not list
            or type(row["negated"]) is not bool
        ):
            raise ValueError("unique grounded relation instances required")
        if len(row["arguments"]) != len(predicates[row["predicate"]]["arguments"]):
            raise ValueError("predicate arity mismatch")
        facts[row["id"]] = row
    for row in facts.values():
        for arg, kind in zip(
            row["arguments"], predicates[row["predicate"]]["arguments"]
        ):
            if type(arg) is not dict or set(arg) != {"kind", "id"}:
                raise ValueError("explicit structural reference required")
            _text(arg["id"])
            if kind == "FACT":
                if arg["kind"] != "FACT" or arg["id"] not in facts:
                    raise ValueError("unknown higher-order argument")
            elif arg["kind"] != "ENTITY" or entities.get(arg["id"]) != kind[7:]:
                raise ValueError("entity argument sort mismatch")
    terms, heights, identities = {}, {}, {}

    def term(key, stack=()):
        if key in stack:
            raise ValueError("finite acyclic relation expressions required")
        if key not in terms:
            row = facts[key]
            args, height = [], 1
            for arg in row["arguments"]:
                if arg["kind"] == "ENTITY":
                    args.append(("ENTITY", arg["id"]))
                else:
                    term(arg["id"], (*stack, key))
                    height = max(height, 1 + heights[arg["id"]])
                    args.append(("FACT", identities[arg["id"]]))
            if height > MAX_DEPTH:
                raise ValueError("finite acyclic relation expressions required")
            heights[key] = height
            terms[key] = (row["predicate"], row["negated"], tuple(args))
            identities[key] = _node_id(terms[key])
        return terms[key]

    for key in facts:
        term(key)
    if len(set(terms.values())) != len(terms):
        raise ValueError(
            "duplicate structural assertions must share one evidence identity"
        )
    return entities, predicates, facts, terms


def structural_mappings(
    base, target, compatibilities, *, max_work=100000, max_mappings=128
):
    """Search a finite set of one-to-one, argument-preserving partial mappings.

    Work charges each local pair, recursive constraint, search state, and bounded
    leaf/transfer evaluation. It is not a CPU-time measure. Exhaustion yields only
    actually checked mappings and an explicit unsearched frontier. ATTRIBUTEs do
    not seed correspondences. Negative assertions are explicit, not closed-world
    conclusions. Counterexamples remain attached to each particular mapping.
    """
    base, target, compatibilities = thaw(base), thaw(target), thaw(compatibilities)
    if (
        type(max_work) is not int
        or not 0 <= max_work <= 1000000
        or type(max_mappings) is not int
        or not 1 <= max_mappings <= 256
        or type(compatibilities) is not list
        or len(compatibilities) > 256
    ):
        raise ValueError("explicit finite mapping resource bounds required")
    be, bp, bf, bt = _domain(base)
    te, tp, tf, tt = _domain(target)
    compatible = set()
    for pair in compatibilities:
        if (
            type(pair) is not list
            or len(pair) != 2
            or pair[0] not in bp
            or pair[1] not in tp
            or bp[pair[0]]["kind"] != tp[pair[1]]["kind"]
            or bp[pair[0]]["arguments"] != tp[pair[1]]["arguments"]
        ):
            raise ValueError(
                "explicit sort-preserving predicate compatibility required"
            )
        compatible.add(tuple(pair))
    if len(compatible) != len(compatibilities):
        raise ValueError("duplicate predicate compatibility")
    work, frontier = 0, []
    pool, found, local_seen = [], {}, set()

    class Exhausted(Exception):
        pass

    def charge():
        nonlocal work
        if work >= max_work:
            raise Exhausted()
        work += 1

    def add(mapping, inverse, key, value):
        if (
            key in mapping
            and mapping[key] != value
            or value in inverse
            and inverse[value] != key
        ):
            return False
        mapping[key], inverse[value] = value, key
        return True

    def local(left, right):
        mapping, inverse, pending = {}, {}, [("FACT", left, right)]
        while pending:
            charge()
            kind, b, t = pending.pop()
            key, value = (kind, b), (kind, t)
            if key in mapping:
                if mapping[key] != value:
                    return None
                continue
            if not add(mapping, inverse, key, value):
                return None
            if kind == "ENTITY":
                if be[b] != te[t]:
                    return None
            else:
                br, tr = bf[b], tf[t]
                if (br["predicate"], tr["predicate"]) not in compatible or br[
                    "negated"
                ] != tr["negated"]:
                    return None
                if not add(
                    mapping,
                    inverse,
                    ("PREDICATE", br["predicate"]),
                    ("PREDICATE", tr["predicate"]),
                ):
                    return None
                pending.extend(
                    (a["kind"], a["id"], z["id"])
                    for a, z in zip(br["arguments"], tr["arguments"])
                )
        return tuple(sorted(mapping.items()))

    def merge(current, incoming):
        mapping, inverse = dict(current), {v: k for k, v in current}
        for key, value in incoming:
            if not add(mapping, inverse, key, value):
                return None
        return tuple(sorted(mapping.items()))

    target_terms = {value: key for key, value in tt.items()}

    def evaluate(mapping):
        mapping = dict(mapping)
        entities = {b: t[1] for (kind, b), t in mapping.items() if kind == "ENTITY"}
        predicates = {
            b: t[1] for (kind, b), t in mapping.items() if kind == "PREDICATE"
        }
        cache, projected_nodes = {}, {}

        def transfer(key):
            if key not in cache:
                row = bf[key]
                if row["predicate"] not in predicates:
                    cache[key] = None
                else:
                    args = []
                    for arg in row["arguments"]:
                        value = (
                            entities.get(arg["id"])
                            if arg["kind"] == "ENTITY"
                            else transfer(arg["id"])
                        )
                        if value is None:
                            cache[key] = None
                            break
                        args.append(
                            (
                                arg["kind"],
                                value if arg["kind"] == "ENTITY" else _node_id(value),
                            )
                        )
                    else:
                        cache[key] = (
                            predicates[row["predicate"]],
                            row["negated"],
                            tuple(args),
                        )
                        projected_nodes[_node_id(cache[key])] = cache[key]
            return cache[key]

        predictions, unsupported, higher, relational, disagreements = [], [], 0, 0, 0
        for key, row in sorted(bf.items()):
            charge()
            value = transfer(key)
            if value is None:
                unsupported.append(key)
                continue
            positive = target_terms.get(value)
            opposite = target_terms.get((value[0], not value[1], value[2]))
            status = (
                "CONFLICTING_TARGET_EVIDENCE"
                if positive and opposite
                else (
                    "TARGET_SUPPORTED"
                    if positive
                    else "TARGET_REFUTED" if opposite else "TARGET_UNDETERMINED"
                )
            )
            is_relation = bp[row["predicate"]]["kind"] == "RELATION"
            contribution = dict(
                supported_relations=int(is_relation and positive is not None),
                higher_order_links=(
                    sum(arg["kind"] == "FACT" for arg in row["arguments"])
                    if is_relation and positive is not None
                    else 0
                ),
                explicit_counterexamples=int(is_relation and opposite is not None),
            )
            relational += contribution["supported_relations"]
            higher += contribution["higher_order_links"]
            disagreements += contribution["explicit_counterexamples"]
            predictions.append(
                dict(
                    base_fact=key,
                    hypothesis=value,
                    hypothesis_id=_node_id(value),
                    metric_contributions=contribution,
                    status=status,
                    supporting_target_fact=positive,
                    counterexample_target_fact=opposite,
                    qualification="HYPOTHETICAL_TRANSFER_NOT_TARGET_FACT",
                )
            )
        # Attributes never seed mappings. Only explicit unique compatibilities
        # permit a secondary dissimilarity test; ambiguity stays uncomputed.
        attributes, attribute_mismatches = [], 0
        for key, row in sorted(bf.items()):
            if bp[row["predicate"]]["kind"] != "ATTRIBUTE":
                continue
            charge()
            entity = entities.get(row["arguments"][0]["id"])
            options = (
                [predicates[row["predicate"]]]
                if row["predicate"] in predicates
                else sorted(t for b, t in compatible if b == row["predicate"])
            )
            blocked = (
                row["predicate"] not in predicates
                and len(options) == 1
                and options[0] in predicates.values()
            )
            if entity is None or len(options) != 1 or blocked:
                attributes.append(
                    dict(
                        base_fact=key,
                        status="ATTRIBUTE_ALIGNMENT_UNDETERMINED",
                        target_predicate=options[0] if len(options) == 1 else None,
                        alignment_reason=(
                            "ENTITY_MAPPING_UNRESOLVED"
                            if entity is None
                            else (
                                "PREDICATE_MAPPING_CONFLICT"
                                if blocked
                                else "PREDICATE_ALIGNMENT_UNRESOLVED"
                            )
                        ),
                    )
                )
                continue
            value = (options[0], row["negated"], (("ENTITY", entity),))
            opposite = target_terms.get((value[0], not value[1], value[2]))
            support = target_terms.get(value)
            attribute_mismatches += int(opposite is not None)
            attributes.append(
                dict(
                    base_fact=key,
                    target_predicate=options[0],
                    alignment_reason=(
                        "ESTABLISHED_PREDICATE_MAPPING"
                        if row["predicate"] in predicates
                        else "UNIQUE_COMPATIBLE_PREDICATE"
                    ),
                    supporting_target_fact=support,
                    counterexample_target_fact=opposite,
                    status=(
                        "ATTRIBUTE_CONFLICT"
                        if opposite
                        else (
                            "ATTRIBUTE_SUPPORTED"
                            if support
                            else "ATTRIBUTE_UNDETERMINED"
                        )
                    ),
                )
            )
        return dict(
            entities=entities,
            predicates=predicates,
            facts={b: t[1] for (kind, b), t in mapping.items() if kind == "FACT"},
            higher_order_links=higher,
            supported_relations=relational,
            explicit_counterexamples=disagreements,
            attribute_mismatches=attribute_mismatches,
            predictions=predictions,
            projected_expression_nodes=projected_nodes,
            expression_encoding="CONTENT_ADDRESSED_FACT_DAG_1",
            unprojected_base_facts=unsupported,
            attribute_checks=attributes,
        )

    local_complete = False
    try:
        for b, br in sorted(bf.items()):
            if bp[br["predicate"]]["kind"] != "RELATION":
                continue
            for t, tr in sorted(tf.items()):
                charge()
                candidate = local(b, t)
                if candidate and candidate not in local_seen:
                    local_seen.add(candidate)
                    pool.append(candidate)
        local_complete = True
        # Larger higher-order closures first; this affects a bounded prefix,
        # never silently upgrades it to a globally optimal mapping.
        pool.sort(key=lambda row: (-len(row), row))
        stack, visited = [(0, ())], set()
        while stack:
            charge()
            index, current = stack.pop()
            state = (index, current)
            if state in visited:
                continue
            if len(visited) >= MAX_SEARCH_STATES:
                frontier.append("MAPPING_STATE_STORAGE_FRONTIER")
                break
            visited.add(state)
            if index == len(pool):
                if current and current not in found:
                    if len(found) >= 4096:
                        frontier.append("MAPPING_STORAGE_FRONTIER")
                        break
                    value = evaluate(current)
                    found[current] = value
                continue
            combined = merge(current, pool[index])
            stack.append((index + 1, current))
            if combined is not None and combined != current:
                stack.append((index + 1, combined))
    except Exhausted:
        frontier.append(
            "MAPPING_SEARCH_FRONTIER"
            if local_complete
            else "MAPPING_LOCAL_MATCH_FRONTIER"
        )
    # This bounded postprocessing does not claim unsearched maximality. The
    # number of saved states is a fixed bound, but subset comparisons are also
    # charged and an unfinished dominance pass keeps all actually checked rows.
    maximal = list(found)
    try:
        keep = []
        for key in maximal:
            subset = set(key)
            dominated = False
            for other in maximal:
                charge()
                if len(other) > len(key) and subset < set(other):
                    dominated = True
                    break
            if not dominated:
                keep.append(key)
        maximal = keep
    except Exhausted:
        frontier.append("MAPPING_MAXIMALITY_FRONTIER")
    rows = [found[key] for key in maximal]
    # A declared structural ordering, not calibrated confidence or a beauty score.
    rows.sort(
        key=lambda r: (
            -r["higher_order_links"],
            -(r["supported_relations"] - r["explicit_counterexamples"]),
            r["attribute_mismatches"],
            codec.canonical(r["entities"]),
            codec.canonical(r["predicates"]),
        )
    )
    if len(rows) > max_mappings:
        frontier.append("MAPPING_OUTPUT_FRONTIER")
        rows = rows[:max_mappings]
    for row in rows:
        row["mapping_id"] = sha256(
            codec.dumps([row["entities"], row["predicates"], row["facts"]])
        ).hexdigest()
        row["maximality"] = (
            "SEARCH_PREFIX_ONLY"
            if frontier
            else "MAXIMAL_WITHIN_DECLARED_RELATIONAL_CONTRACT"
        )
    return dict(
        schema=VERSION,
        mappings=rows,
        work=work,
        frontier=tuple(sorted(set(frontier))),
        input_identity=sha256(codec.dumps([base, target, compatibilities])).hexdigest(),
        local_match_count=len(pool),
        checked_mapping_count=len(found),
        ordering="HIGHER_ORDER_THEN_RELATIONAL_SUPPORT_MINUS_EXPLICIT_COUNTEREXAMPLES_THEN_ATTRIBUTE_MISMATCHES",
        qualifications=(
            "DECLARED_PREDICATE_COMPATIBILITIES_ARE_SEMANTIC_HYPOTHESES",
            "MAPPING_DOES_NOT_ESTABLISH_TRANSFERRED_CONCLUSIONS",
        ),
    )
