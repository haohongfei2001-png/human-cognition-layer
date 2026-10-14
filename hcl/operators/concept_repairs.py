"""Counterexample-driven finite partitions of positive typed examples.

A single LGG cannot be specialized further while retaining every positive.
The explicit alternative language is ORs of block LGGs, with the original
criterion direction unchanged. Exhaustion certifies only this finite language.
"""
from copy import deepcopy
from hcl.memory import codec
from hcl.kernel.types import thaw
from hcl.operators.abduction import discover, identity, program_hash
from hcl.operators.concept_induction import generalize_examples, match_independent_case
from hcl.operators.judgment import JudgmentWork

VERSION = "finite-counterexample-partition-repair-1"
LANGUAGE = "OR_OF_POSITIVE_PARTITION_LGGS_1"
ADAPTER = "concept-partition-lgg-1"


def match_disjunction(patterns, term, charge):
    """OR is one criterion: failed alternatives never independently exclude."""
    if term is None:
        return dict(status="UNKNOWN", substitution={})
    traces = []
    for index, pattern in enumerate(patterns):
        charge()
        check = match_independent_case(pattern, term, charge)
        traces.append(check)
        if check["status"] == "MATCH":
            return dict(status="MATCH", alternative=index, substitution=check["substitution"])
    return dict(status="NO_MATCH", substitution={})


def partition_lgg(positive, partition, max_work):
    """Execute a specific full partition; never silently omit a positive."""
    positive = thaw(positive)
    rows = {r["id"]: r for r in positive}
    flat = [key for block in partition for key in block]
    if (len(flat) != len(set(flat)) or set(flat) != set(rows)
            or any(not block for block in partition)):
        raise ValueError("complete disjoint positive partition required")
    work, patterns, frontier = 0, [], []
    for block in partition:
        result = generalize_examples([rows[k] for k in block], [], max_work=min(1000000, max_work-work))
        work += result["work"]
        if result["frontier"]:
            frontier.extend(result["frontier"])
            break
        patterns.append(result["pattern"])
    return dict(patterns=sorted(patterns, key=codec.canonical), work=work, frontier=frontier)


def _partitions(rows, work):
    """Restricted-growth recursion: each unlabeled set partition exactly once."""
    def visit(index, blocks):
        work.spend()
        if index == len(rows):
            yield deepcopy(blocks)
            return
        for i in range(len(blocks)):
            blocks[i].append(rows[index]["id"])
            yield from visit(index + 1, blocks)
            blocks[i].pop()
        blocks.append([rows[index]["id"]])
        yield from visit(index + 1, blocks)
        blocks.pop()
    yield from visit(0, [])


def repair_examples(positive, negative, *, max_work=100000):
    positive, negative = thaw(positive), thaw(negative)
    # Existing validator checks identities, complete ground terms and sorts.
    generalize_examples(positive, negative, max_work=0)
    if len({codec.canonical(r["term"]) for r in positive}) > 5:
        raise ValueError("finite repair language admits at most five distinct positives")
    if type(max_work) is not int or not 0 <= max_work <= 1000000:
        raise ValueError("bounded concept repair work required")
    work = JudgmentWork(max_work)
    unique = {}
    for row in sorted(positive, key=lambda r:(codec.canonical(r["term"]),r["id"])):
        unique.setdefault(codec.canonical(row["term"]), row)
    rows = list(unique.values())
    programs, partitions, generation, frontier = [], {}, {}, []
    base = generalize_examples(positive, negative, max_work=max_work)
    work.spend(base["work"])
    frontier.extend(base["frontier"])
    # Only actual residuals trigger edits. A nonrefuted LGG needs no repair.
    triggered = bool(base["counterexample_ids"])
    exhausted = not frontier
    try:
        if not frontier:
            iterator = _partitions(rows, work) if triggered else iter([[ [r["id"] for r in rows] ]])
            for partition in iterator:
                actual = partition_lgg(rows, partition, work.limit-work.used)
                work.spend(actual["work"])
                if actual["frontier"]:
                    frontier.extend(actual["frontier"])
                    exhausted = False
                    break
                program = dict(adapter=ADAPTER, patterns=actual["patterns"])
                key = program_hash(program)
                partitions.setdefault(key, []).append(partition)
                generation[key] = generation.get(key, 0) + actual["work"]
                if key not in {program_hash(p) for p in programs}:
                    programs.append(program)
    except OverflowError:
        exhausted = False
        frontier.append("CONCEPT_REPAIR_GENERATION_FRONTIER")
    contexts = [dict(id="examples", cases=[dict(id=r["id"],term=r["term"]) for r in (*positive,*negative)])]
    observations = [dict(id=r["id"],context_id="examples",query_id=r["id"],
        factor_id=identity([i<len(positive),r["term"]]),provenance_group="declared-concept-examples",
        values=[i<len(positive)]) for i,r in enumerate((*positive,*negative))]
    from hcl.operators.discovery_model import evaluate_concept_partition
    # Shared M04 comparator/Pareto; evaluator receives no observation labels.
    discovered = discover(programs, observations, contexts, [], {}, evaluate_concept_partition,
        max_evaluations=min(100000,work.limit-work.used), max_rounds=0,
        scope=dict(language=LANGUAGE,positive_terms=[r["term"] for r in rows], comparison_identity=identity([contexts,observations])))
    work.spend(discovered["local_evaluations"])
    frontier.extend(discovered["frontier"])
    candidates = []
    for key, column in discovered["prediction_matrix"].items():
        checks = []
        for source, cell in zip(observations,column["cells"]):
            prediction = cell["prediction"]
            checks.append(dict(id=source["id"],expected="POSITIVE" if source["values"]==[True] else "NEGATIVE",
                status="UNCOMPUTED" if prediction["status"]!="COMPUTED" else "MATCH" if prediction["values"]==[True] else "NO_MATCH"))
        candidates.append(dict(id=key,partition=partitions[key][0],equivalent_partitions=partitions[key],
            patterns=discovered["programs"][key]["patterns"],examples=checks,complexity=column["complexity"],
            work=column["work"],generation_work=generation[key],profile=column["profile"],
            consistent=all(c["status"] == ("MATCH" if c["expected"]=="POSITIVE" else "NO_MATCH") for c in checks)))
    if any(c["status"] == "UNCOMPUTED" for candidate in candidates for c in candidate["examples"]):
        frontier.append("CONCEPT_REPAIR_PREDICTION_FRONTIER")
    complete = exhausted and not frontier and bool(candidates)
    consistent = [c for c in candidates if c["consistent"]]
    minimum = lambda metric: sorted(c["id"] for c in consistent if metric(c)==min(map(metric,consistent))) if consistent and complete and triggered else []
    return dict(schema=VERSION,language=LANGUAGE,base=base,triggered_by=list(base["counterexample_ids"]),
        candidates=candidates,discovery=discovered,pareto_candidate_ids=list(discovered["pareto_programs"]),
        complete=complete,frontier=sorted(set(frontier)),work=work.used,
        minimum_consistent_candidate_ids=minimum(lambda c:c["complexity"]),
        minimum_consistent_block_candidate_ids=minimum(lambda c:len(c["patterns"])),
        status="PARTIAL" if not complete else "NO_DECLARED_COUNTEREXAMPLE" if not triggered else "FINITE_LANGUAGE_REPAIR_FOUND" if consistent else "NO_REPAIR_IN_FINITE_LANGUAGE",
        candidate_completeness="PARTIAL_DECLARED_PARTITIONS" if not complete else "EXHAUSTED_DECLARED_PARTITIONS" if triggered else "NOT_SEARCHED_NO_COUNTEREXAMPLE",
        edit_history=[dict(operation="PARTITION_POSITIVE_EXAMPLES", candidate_id=c["id"], partitions=c["equivalent_partitions"],
            residual_ids=list(base["counterexample_ids"]), evaluation_status="RECOMPUTED" if all(e["status"]!="UNCOMPUTED" for e in c["examples"]) else "PARTIALLY_RECOMPUTED")
            for c in candidates if len(c["patterns"])>1 and triggered],
        scope="FINITE_DECLARED_PARTITIONS_NOT_OPEN_CONCEPT_OPTIMALITY",adopted=False)


def evaluate_partition(criterion, max_work):
    positive, negative = ([dict(id=r["id"],term=r["term"]) for r in criterion[k]] for k in ("positive","negative"))
    result = partition_lgg(positive, criterion["partition"], max_work)
    work = JudgmentWork(max_work)
    work.spend(result["work"])
    examples, counters = [], []
    try:
        if not result["frontier"]:
            for index,row in enumerate((*positive,*negative)):
                work.spend()
                actual = match_disjunction(result["patterns"],row["term"],work.spend)
                examples.append(dict(id=row["id"],expected="POSITIVE" if index<len(positive) else "NEGATIVE",**actual))
                if index>=len(positive) and actual["status"]=="MATCH":
                    counters.append(row["id"])
    except OverflowError:
        result["frontier"].append("CONCEPT_PARTITION_COVERAGE_FRONTIER")
    return dict(schema=LANGUAGE,patterns=result["patterns"],examples=examples,work=work.used,
        frontier=result["frontier"],counterexample_ids=counters)


def expand_repairs(program, max_work):
    """Generate new immutable readings, never adopt them or alter pinned uses."""
    concepts = deepcopy(program["concepts"])
    work = JudgmentWork(max_work)
    repairs, frontier = [], []
    for request in program["repairs"]:
        version = next(v for v in concepts["versions"] if v["id"]==request["version_id"])
        criterion = version["criteria"][0]
        active = set(version["active_assumptions"])
        if criterion["direction"] not in ("SUFFICIENT", "BICONDITIONAL"):
            repairs.append(dict(id=request["id"],status="NO_DIRECTIONAL_COUNTEREXAMPLE",candidates=[],complete=True,adopted=False,
                scope="NEGATIVE_MATCH_DOES_NOT_REFUTE_NECESSARY_OR_TYPICAL_CRITERION"))
            continue
        if (set(version["assumptions"]) != active or
            any(set(r["assumptions"])-active for k in ("positive","negative","boundary") for r in criterion[k])):
            repairs.append(dict(id=request["id"],status="ASSUMPTION_RETRACTED",candidates=[],complete=False,adopted=False))
            frontier.append("CONCEPT_REPAIR_ASSUMPTION_RETRACTED")
            continue
        actual = repair_examples(*([dict(id=r["id"],term=r["term"]) for r in criterion[k]] for k in ("positive","negative")),
                                 max_work=min(1000000,work.limit-work.used))
        work.spend(actual["work"])
        repairs.append(dict(id=request["id"],**actual,
            downstream_comparison_scope="ALL_CONSISTENT_FINITE_REPAIRS_PLUS_ORIGINALS",
            downstream_candidate_ids=[c["id"] for c in actual["candidates"] if c["consistent"] and actual["triggered_by"]],
            excluded_candidate_ids=[c["id"] for c in actual["candidates"] if not c["consistent"]]))
        frontier.extend(actual["frontier"])
        choice = next(c for c in concepts["choices"] if c["id"]==request["choice_id"])
        terms = {r["id"]:r["term"] for r in criterion["positive"]}
        for candidate in actual["candidates"]:
            if not actual["triggered_by"] or not candidate["consistent"]:
                continue
            new = deepcopy(version)
            new["id"] = "repair:"+candidate["id"][:56]
            new["definition_language"] = LANGUAGE
            new["criteria"][0]["partition"] = [[r["id"] for r in criterion["positive"]
                if any(r["term"]==terms[k] for k in block)] for block in candidate["partition"]]
            candidate["version_label"] = new["id"]
            if new["id"] in {v["id"] for v in concepts["versions"]}:
                raise ValueError("generated concept identity collides")
            concepts["versions"].append(new)
            choice["versions"].append(new["id"])
    return dict(concepts=concepts,repairs=repairs,frontier=frontier,work=work.used)
