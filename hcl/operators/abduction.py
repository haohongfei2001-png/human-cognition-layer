"""Shared bounded mechanism discovery from actual predictions and residuals.

This module never treats hypothesis prose as an observation or a prediction.
Domain adapters execute the proposed mechanism. Observation targets are passed
only to the matrix comparator, never to the domain evaluator.
"""

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from itertools import combinations

from hcl.memory.codec import canonical

VERSION = "s3-residual-mechanism-discovery-1"
RELATIONS = frozenset(
    {
        "EXPLAINED",
        "CONTRADICTED",
        "COMPATIBLE_UNDERSPECIFIED",
        "UNMODELED",
        "UNCOMPUTED",
    }
)


def identity(value):
    return sha256(canonical(value).encode()).hexdigest()


def context_identity(context):
    """Display labels do not create another condition or evidence factor."""
    return identity({key: value for key, value in context.items() if key != "id"})


def domain_conditions(actual):
    return tuple(
        dict(
            result_id=r["result_id"],
            context_hash=r.get("context_hash"),
            assumption_environments=r.get("assumption_environments", ()),
        )
        for r in actual
        if "result_id" in r
    )


def edit_evaluation(column):
    if not column["actual_results"]:
        return "UNCOMPUTED"
    if any(c["relation"] in ("UNCOMPUTED", "UNMODELED") for c in column["cells"]):
        return "PARTIALLY_RECOMPUTED"
    return "RECOMPUTED"


def program_hash(program):
    return identity({key: value for key, value in program.items() if key != "id"})


def expression_size(value):
    if isinstance(value, dict):
        return 1 + sum(expression_size(v) for v in value.values())
    if isinstance(value, (tuple, list)):
        return 1 + sum(expression_size(v) for v in value)
    return 1


def evaluate_expression(expression, features, latent, depth=0):
    """A bounded data AST; observed explanation targets are not an environment."""
    if depth > 8 or type(expression) is not dict:
        raise ValueError("bounded expression required")
    if set(expression) == {"const"}:
        value = expression["const"]
        if type(value) not in (bool, int, str) or (
            type(value) is str and len(value) > 128
        ):
            raise ValueError("bounded scalar constant required")
        return value
    if set(expression) == {"feature"}:
        return features[expression["feature"]]
    if set(expression) == {"latent"}:
        return latent[expression["latent"]]
    if set(expression) != {"op", "args"} or type(expression["args"]) not in (
        list,
        tuple,
    ):
        raise ValueError("unknown expression")
    op, args = expression["op"], expression["args"]
    if not 1 <= len(args) <= 8:
        raise ValueError("bounded expression arity required")
    values = [evaluate_expression(a, features, latent, depth + 1) for a in args]
    if op in ("and", "or", "not"):
        if any(type(v) is not bool for v in values) or (
            op == "not" and len(values) != 1
        ):
            raise ValueError("Boolean operands required")
        return (
            all(values) if op == "and" else any(values) if op == "or" else not values[0]
        )
    if op == "if" and len(values) == 3 and type(values[0]) is bool:
        return values[1] if values[0] else values[2]
    if op == "eq" and len(values) == 2:
        return type(values[0]) is type(values[1]) and values[0] == values[1]
    if op in ("add", "sub", "mul") and len(values) == 2:
        if any(type(v) not in (int, str) for v in values):
            raise ValueError("rational operands required")
        a, b = map(Fraction, values)
        value = a + b if op == "add" else a - b if op == "sub" else a * b
        if abs(value) > 1000000 or value.denominator > 1000000:
            raise ValueError("rational expression bound")
        return str(value)
    raise ValueError("unknown operation or arity")


def compare_prediction(prediction, observation):
    """Set-valued uncertainty is preserved, never replaced by a forced label."""
    if prediction["status"] == "UNMODELED":
        return "UNMODELED"
    if prediction["status"] != "COMPUTED":
        return "UNCOMPUTED"
    actual = {canonical(v) for v in prediction["values"]}
    expected = {canonical(v) for v in observation["values"]}
    if not actual:
        return "UNCOMPUTED"
    if actual == expected:
        return "EXPLAINED"
    if actual.isdisjoint(expected):
        return "CONTRADICTED"
    return "COMPATIBLE_UNDERSPECIFIED"


def factor_profile(cells):
    """A repeated report never becomes an extra independent evidence factor."""
    groups = {}
    for cell in cells:
        groups.setdefault(cell["factor_id"], set()).add(cell["relation"])
    return {
        name: tuple(
            sorted(
                key
                for key, relations in groups.items()
                if (
                    relations == {"EXPLAINED"}
                    if name == "explained"
                    else (
                        "CONTRADICTED" in relations
                        if name == "contradicted"
                        else (
                            bool(relations & {"UNMODELED", "UNCOMPUTED"})
                            if name == "unmodeled"
                            else "COMPATIBLE_UNDERSPECIFIED" in relations
                        )
                    )
                )
            )
        )
        for name in ("explained", "contradicted", "unmodeled", "underspecified")
    }


def dominates(first, second):
    a, b = first["profile"], second["profile"]
    # Unknown cells cannot win by avoiding evidence or by not paying for work.
    if a["unmodeled"] or b["unmodeled"]:
        return False
    comparisons = (
        set(a["explained"]) >= set(b["explained"]),
        set(a["contradicted"]) <= set(b["contradicted"]),
        set(a["underspecified"]) <= set(b["underspecified"]),
        first["complexity"] <= second["complexity"],
        first["work"] <= second["work"],
    )
    return all(comparisons) and (
        a != b
        or first["complexity"] != second["complexity"]
        or first["work"] != second["work"]
    )


def pareto_frontier(columns):
    return tuple(
        sorted(
            key
            for key, value in columns.items()
            if not any(
                other != key and dominates(candidate, value)
                for other, candidate in columns.items()
            )
        )
    )


def prediction_classes(columns, observations, scope):
    """Equivalence is only for these actual obligations; all members survive."""
    groups = {}
    for key, column in columns.items():
        if any(
            cell["prediction"]["status"] != "COMPUTED"
            or not cell["prediction"]["values"]
            for cell in column["cells"]
        ):
            signature = "uncomputed:" + key
        else:
            signature = identity(
                [
                    scope,
                    [
                        (
                            o["id"],
                            sorted(canonical(v) for v in cell["prediction"]["values"]),
                        )
                        for o, cell in zip(observations, column["cells"])
                    ],
                ]
            )
        groups.setdefault(signature, []).append(key)
    return tuple(
        dict(
            class_id=key,
            members=tuple(sorted(members)),
            scope=scope,
            status=(
                "UNCOMPUTED_NOT_EQUIVALENT"
                if key.startswith("uncomputed:")
                else "EQUIVALENT_ON_DECLARED_OBLIGATIONS"
            ),
        )
        for key, members in sorted(groups.items())
    )


def mechanism_edits(program, grammar, residuals, contexts):
    """Generate new mechanism ASTs, not a fixed list of explanatory answers."""
    if not residuals:
        return
    trigger_ids = tuple(sorted(row["observation_id"] for row in residuals))
    features = sorted(
        {
            name
            for row in residuals
            for name, value in contexts[row["context_id"]]["features"].items()
            if type(value) is bool and name in grammar["observation_features"]
        }
    )
    for index, binding in enumerate(program["observe"]):
        old = binding["when"]
        for name in features:
            term = {"feature": name}
            if term == old:
                continue
            for operation, replacement in (
                ("replace_channel", term),
                ("extend_channel", {"op": "or", "args": [old, term]}),
                ("restrict_channel", {"op": "and", "args": [old, term]}),
            ):
                if (
                    replacement == old
                    or expression_size(replacement) > grammar["max_expression_size"]
                ):
                    continue
                new = deepcopy(program)
                new["observe"][index]["when"] = replacement
                yield new, dict(
                    operation=operation,
                    path=("observe", str(index), "when"),
                    before=old,
                    after=replacement,
                    residual_ids=trigger_ids,
                )
        replacement = {"op": "not", "args": [old]}
        if expression_size(replacement) <= grammar["max_expression_size"]:
            new = deepcopy(program)
            new["observe"][index]["when"] = replacement
            yield new, dict(
                operation="negate_channel",
                path=("observe", str(index), "when"),
                before=old,
                after=replacement,
                residual_ids=trigger_ids,
            )
    for name, choices in sorted(grammar["latent_domains"].items()):
        if name not in program["latent"]:
            continue
        for value in choices:
            if value == program["latent"][name] and type(value) is type(
                program["latent"][name]
            ):
                continue
            new = deepcopy(program)
            new["latent"][name] = value
            yield new, dict(
                operation="replace_latent",
                path=("latent", name),
                before=program["latent"][name],
                after=value,
                residual_ids=trigger_ids,
            )


def discover(
    programs,
    observations,
    contexts,
    probes,
    grammar,
    evaluate,
    *,
    max_evaluations,
    max_rounds=2,
    beam=12,
    new_per_round=4,
    max_candidates=64,
    scope=None
):
    """Actual callback contract: evaluate(program, context, remaining) -> result.

    The callback receives no Observation/expected values. It returns computed
    predictions by query id, actual solver records, diagnostics and work units.
    Source-bound production adapters implement it using the common operators.
    """
    if not (
        0 <= max_evaluations <= 100000
        and 0 <= max_rounds <= 8
        and 1 <= beam <= 12
        and 1 <= new_per_round <= 4
        and 1 <= max_candidates <= 64
    ):
        raise ValueError("bounded discovery budget required")
    contexts = {row["id"]: deepcopy(row) for row in contexts}
    context_hashes = {key: context_identity(value) for key, value in contexts.items()}
    originals = identity([programs, observations, contexts, probes, grammar])
    columns, archive, edits, frontier = {}, {}, [], []
    used = 0

    def column(program):
        nonlocal used
        key = program_hash(program)
        if key in archive:
            return key
        if len(archive) >= max_candidates:
            frontier.append("CANDIDATE_STORAGE_BOUND")
            return None
        archive[key] = deepcopy(program)
        by_context, cells, actual = {}, [], []
        for observation in observations:
            context_id = observation["context_id"]
            context_key = context_hashes[context_id]
            if context_key not in by_context:
                if used >= max_evaluations:
                    by_context[context_key] = dict(
                        predictions={}, status="UNCOMPUTED", work=0, actual_results=()
                    )
                    frontier.append("PREDICTION_BUDGET_FRONTIER")
                else:
                    value = evaluate(
                        deepcopy(program),
                        deepcopy(contexts[context_id]),
                        max_evaluations - used,
                    )
                    if (
                        type(value["work"]) is not int
                        or not 0 <= value["work"] <= max_evaluations - used
                    ):
                        raise ValueError("adapter resource accounting mismatch")
                    used += value["work"]
                    by_context[context_key] = value
                    actual.extend(value["actual_results"])
            computed = by_context[context_key]
            prediction = computed["predictions"].get(
                observation["query_id"],
                dict(
                    status=(
                        "UNMODELED"
                        if computed["status"] == "UNMODELED"
                        else "UNCOMPUTED"
                    ),
                    values=(),
                    result_refs=(),
                ),
            )
            cells.append(
                dict(
                    observation_id=observation["id"],
                    context_id=context_id,
                    factor_id=observation["factor_id"],
                    provenance_group=observation["provenance_group"],
                    prediction=prediction,
                    relation=compare_prediction(prediction, observation),
                )
            )
        columns[key] = dict(
            program_hash=key,
            cells=cells,
            profile=factor_profile(cells),
            complexity=expression_size({k: v for k, v in program.items() if k != "id"}),
            work=sum(v["work"] for v in by_context.values()),
            actual_results=actual,
            domain_conditions=domain_conditions(actual),
        )
        return key

    for program in programs:
        column(program)
    for round_id in range(max_rounds):
        if used >= max_evaluations:
            frontier.append("DISCOVERY_BUDGET_FRONTIER")
            break
        active = pareto_frontier(columns)
        if len(active) > beam:
            frontier.append("PARETO_EXPANSION_BEAM_BOUND")
        proposals = []
        proposal_hashes = set(archive)
        for parent in active[:beam]:
            residuals = [
                cell
                for cell in columns[parent]["cells"]
                if cell["relation"] != "EXPLAINED"
            ]
            for new, edit in mechanism_edits(
                archive[parent], grammar, residuals, contexts
            ):
                key = program_hash(new)
                if key not in proposal_hashes:
                    proposal_hashes.add(key)
                    proposals.append(
                        (
                            new,
                            dict(
                                edit,
                                parent_hash=parent,
                                child_hash=key,
                                round=round_id + 1,
                            ),
                        )
                    )
                    # Retain one extra candidate solely to prove the beam bound;
                    # never materialize the entire grammar before truncating.
                    if len(proposals) > new_per_round:
                        break
            if len(proposals) > new_per_round:
                break
        if not proposals:
            break
        if len(proposals) > new_per_round:
            frontier.append("NEW_PROGRAM_BEAM_BOUND")
        for program, edit in proposals[:new_per_round]:
            child = column(program)
            if child is not None:
                edits.append(
                    dict(edit, evaluation_status=edit_evaluation(columns[child]))
                )
    retained = pareto_frontier(columns)
    classes = prediction_classes(columns, observations, scope)
    distinguishing = []
    # Test every member, not only a representative of current equivalence.
    probe_members = tuple(
        sorted(
            {
                member
                for group in classes
                if set(group["members"]) & set(retained)
                for member in group["members"]
            }
        )
    )
    for probe in probes:
        predictions, groups, incomplete, evaluations = {}, {}, [], {}
        for key in probe_members:
            if used >= max_evaluations:
                incomplete.append(key)
                evaluations[key] = dict(
                    status="UNCOMPUTED",
                    work=0,
                    actual_results=(),
                    diagnostic="PROBE_BUDGET_FRONTIER",
                )
                continue
            value = evaluate(
                deepcopy(archive[key]),
                deepcopy(probe["context"]),
                max_evaluations - used,
            )
            if (
                type(value["work"]) is not int
                or not 0 <= value["work"] <= max_evaluations - used
            ):
                raise ValueError("adapter resource accounting mismatch")
            used += value["work"]
            evaluations[key] = {
                name: value[name] for name in ("status", "work", "actual_results")
            }
            if "diagnostic" in value:
                evaluations[key]["diagnostic"] = value["diagnostic"]
            prediction = value["predictions"].get(probe["query_id"])
            if (
                prediction is None
                or prediction["status"] != "COMPUTED"
                or not prediction["values"]
            ):
                incomplete.append(key)
                continue
            predictions[key] = dict(
                prediction=prediction,
                actual_results=value["actual_results"],
                domain_conditions=domain_conditions(value["actual_results"]),
            )
            groups.setdefault(
                canonical(sorted(canonical(v) for v in prediction["values"])), []
            ).append(key)
        separation = tuple(
            tuple(sorted(members)) for _, members in sorted(groups.items())
        )
        pairs = sum(len(a) * len(b) for a, b in combinations(separation, 2))
        distinguishing.append(
            dict(
                probe_id=probe["id"],
                query_id=probe["query_id"],
                tested_members=probe_members,
                hypothetical=True,
                partitions=separation,
                separated_pairs=pairs,
                incomplete=tuple(incomplete),
                predictions=predictions,
                evaluations=evaluations,
                information_gain="NOT_CALIBRATED",
            )
        )
        if incomplete:
            frontier.append("PROBE_FRONTIER")
    assert originals == identity([programs, observations, contexts, probes, grammar])
    return dict(
        operator_version=VERSION,
        programs=archive,
        initial_program_hashes=tuple(
            sorted({program_hash(p) for p in programs} & set(archive))
        ),
        prediction_matrix=columns,
        pareto_programs=retained,
        prediction_classes=classes,
        edit_history=edits,
        distinguishing_observations=distinguishing,
        local_evaluations=used,
        frontier=tuple(sorted(set(frontier))),
        candidate_completeness="NOT_ESTABLISHED",
        evidence_factor_ids=tuple(sorted({o["factor_id"] for o in observations})),
        semantic_certified=False,
        posterior="NOT_CALIBRATED",
        equivalence_scope=scope,
    )
