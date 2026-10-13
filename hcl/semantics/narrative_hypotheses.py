"""Explicitly shared M04 comparisons over locally compiled source passages.

A comparison name requests a common candidate mechanism, not entity identity.
Every context retains its actual original packet scope. The common discoverer
recomputes every prediction; this compiler never supplies a fit or answer.
"""

from copy import deepcopy
from hashlib import sha256
import json

from hcl.kernel.types import HCLFailure, thaw
from hcl.memory import codec
from hcl.operators.abduction import program_hash
from hcl.semantics.discovery_compiler import DiscoveryCompiler


def scoped(fragment, kind, name):
    return "narrative-" + kind + ":" + sha256(codec.dumps([fragment, name])).hexdigest()


def compose_comparisons(snapshot, fragments, candidates, allowance):
    groups = {}
    chunks = {chunk.ordinal: chunk for chunk, raw in candidates}
    all_segments = tuple(s for chunk, raw in candidates for s in chunk.segments)
    for fragment in fragments:
        for comparison in fragment["comparisons"]:
            groups.setdefault(comparison["id"], []).append(
                (fragment["fragment"], comparison["task"])
            )
    if len(groups) > 4:
        raise HCLFailure(
            "BUDGET_EXHAUSTED",
            "literature_composition",
            "LITERATURE_COMPARISON_BOUND",
            "comparisons",
            "The composition has too many simultaneous hypothesis searches.",
        )
    result = []
    for group, items in sorted(groups.items()):
        first = items[0][1]
        if any(
            (item["grammar"], item["search"]) != (first["grammar"], first["search"])
            for _, item in items
        ):
            raise HCLFailure(
                "INVALID_REQUEST",
                "literature_composition",
                "COMPARISON_CONTRACT_MISMATCH",
                "comparisons",
                "Cross-passage comparisons require one explicitly shared mechanism grammar and search contract.",
            )
        data = dict(
            schema=first["schema"],
            contexts=[],
            observations=[],
            probes=[],
            programs=[],
            grammar=deepcopy(first["grammar"]),
            search=deepcopy(first["search"]),
            unmodeled_segments=[],
        )
        scopes = {}
        programs = {}
        participating = set()
        omissions = set()
        declared = []
        for ordinal, task in items:
            selected = chunks[ordinal].segments
            participating.update(s.segment_id for s in selected)
            omissions.update(task["unmodeled_segments"])
            context_names = {
                row["id"]: scoped(ordinal, "context", row["id"])
                for row in task["contexts"]
            }
            observation_names = {
                row["id"]: scoped(ordinal, "observation", row["id"])
                for row in task["observations"]
            }
            for row in task["contexts"]:
                row = deepcopy(row)
                row["id"] = context_names[row["id"]]
                data["contexts"].append(row)
                scopes[row["id"]] = selected
            for row in task["observations"]:
                row = deepcopy(row)
                row["id"] = observation_names[row["id"]]
                row["context_id"] = context_names[row["context_id"]]
                row["derived_from"] = [
                    observation_names[key] for key in row["derived_from"]
                ]
                data["observations"].append(row)
            for row in task["probes"]:
                row = deepcopy(row)
                row["id"] = scoped(ordinal, "probe", row["id"])
                row["context"]["id"] = scoped(ordinal, "probe-context", row["id"])
                data["probes"].append(row)
                scopes[row["context"]["id"]] = selected
            for program in task["programs"]:
                digest = program_hash(program)
                declared.append(
                    dict(fragment=ordinal, id=program["id"], program_hash=digest)
                )
                programs.setdefault(
                    digest, dict(deepcopy(program), id="program:" + digest)
                )
        data["programs"] = [programs[key] for key in sorted(programs)]
        data["unmodeled_segments"] = sorted(
            omissions | ({s.segment_id for s in all_segments} - participating)
        )
        # Existing M04 validation checks all programs against all actual context
        # templates. No last-fragment proposal can become a whole-work answer.
        program = DiscoveryCompiler().compile(
            snapshot,
            all_segments,
            json.dumps(data, ensure_ascii=False),
            allowance,
            context_scopes=scopes,
        )
        result.append(
            dict(
                id=group,
                program=thaw(program),
                declared_programs=declared,
                context_scope_ids={
                    key: [s.segment_id for s in value] for key, value in scopes.items()
                },
            )
        )
    return result
