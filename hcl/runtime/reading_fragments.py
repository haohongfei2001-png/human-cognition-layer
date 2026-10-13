"""Compact exact-source reading partitions, not semantic composition evidence.

Only source identities/ranges are checkpointed here. Authoritative originals
remain in the shared snapshot, and model returns remain in governed call rows.
The ordinary execution adapter must still enforce current ACL and budgets.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json

from hcl.kernel.types import freeze, thaw
from hcl.memory import codec
from hcl.runtime.context import ContextChunk
from hcl.semantics.segments import SourceSegment

PROTOCOL = "source-reading-fragments-1"


@dataclass(frozen=True)
class ValidatedPartition:
    """Ephemeral immutable cache; never serialized or an authorization token."""

    snapshot: object
    question: str
    data: object


def validated_partition(snapshot, question, plan):
    return ValidatedPartition(
        snapshot, question, freeze(validate(snapshot, question, plan))
    )


def _binding(snapshot, question):
    return dict(
        session=snapshot.session_id,
        principal=[snapshot.principal.tenant_id, snapshot.principal.subject_id],
        access_epoch=snapshot.access_epoch,
        rule=snapshot.rule_version,
        source_versions=dict(snapshot.source_versions),
        question_sha256=sha256(question.encode()).hexdigest(),
    )


def partition(compiler, snapshot, question, purpose, budget, capabilities):
    chunks = compiler.chunks(snapshot, question, purpose, budget, capabilities)
    fragments = []
    for chunk in chunks:
        descriptors = []
        for segment in chunk.segments:
            descriptor = asdict(segment)
            del descriptor["text"]
            descriptors.append(descriptor)
        fragments.append(dict(ordinal=chunk.ordinal, segments=descriptors))
    result = dict(
        protocol=PROTOCOL,
        binding=_binding(snapshot, question),
        purpose=purpose,
        fragments=fragments,
    )
    result["partition_hash"] = sha256(codec.dumps(result)).hexdigest()
    validate(snapshot, question, result)
    return freeze(result)


def validate(snapshot, question, plan):
    data = thaw(plan)
    if (
        set(data) != {"protocol", "binding", "purpose", "fragments", "partition_hash"}
        or data["protocol"] != PROTOCOL
        or data["binding"] != _binding(snapshot, question)
        or not isinstance(data["fragments"], list)
        or not 1 <= len(data["fragments"]) <= 1024
    ):
        raise ValueError("reading partition binding mismatch")
    digest = data.pop("partition_hash")
    if sha256(codec.dumps(data)).hexdigest() != digest:
        raise ValueError("reading partition integrity mismatch")
    ends = {source_id: 0 for source_id in snapshot.source_versions}
    lengths = {
        source_id: len(source.text)
        for source_id, source in snapshot.immutable_views.items()
    }
    if set(lengths) != set(ends):
        raise ValueError("reading partition needs explicit original source scope")
    for ordinal, fragment in enumerate(data["fragments"]):
        if set(fragment) != {"ordinal", "segments"} or fragment["ordinal"] != ordinal:
            raise ValueError("reading fragment order mismatch")
        for row in fragment["segments"]:
            if (
                set(row)
                != {
                    "segment_id",
                    "kind",
                    "source_id",
                    "version",
                    "source_sha256",
                    "start",
                    "end",
                    "byte_start",
                    "byte_end",
                }
                or row["kind"] != "SOURCE"
                or row["source_id"] not in ends
                or row["version"] != snapshot.source_versions[row["source_id"]]
                or type(row["start"]) is not int
                or type(row["end"]) is not int
                or row["start"] != ends[row["source_id"]]
                or not row["start"] < row["end"] <= lengths[row["source_id"]]
            ):
                raise ValueError("reading source coverage mismatch")
            identity = json.dumps(
                [
                    "SOURCE",
                    row["source_id"],
                    row["version"],
                    row["source_sha256"],
                    row["start"],
                    row["end"],
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if row["segment_id"] != "segment:" + sha256(identity.encode()).hexdigest():
                raise ValueError("reading segment identity mismatch")
            ends[row["source_id"]] = row["end"]
    if ends != lengths:
        raise ValueError("reading partition silently omitted original ranges")
    return data


def materialize(compiler, snapshot, question, plan, ordinal, *, feedback=None):
    # Full partition validation is admission/recovery work; each selected packet
    # is then checked against original hash, UTF-8 offsets and bytes by serialize.
    if type(plan) is ValidatedPartition:
        if plan.snapshot is not snapshot or plan.question != question:
            raise ValueError("validated reading partition belongs to another snapshot")
        data = plan.data
    else:
        data = validate(snapshot, question, plan)
    if type(ordinal) is not int or not 0 <= ordinal < len(data["fragments"]):
        raise ValueError("known reading fragment required")
    segments = tuple(
        SourceSegment(
            **row,
            text=snapshot.immutable_views[row["source_id"]].text[
                row["start"] : row["end"]
            ]
        )
        for row in data["fragments"][ordinal]["segments"]
    )
    chunk = ContextChunk(
        data["purpose"], segments, ordinal, len(data["fragments"]), feedback
    )
    wire = compiler.serialize(snapshot, question, chunk)
    return chunk, wire


def call_identity(goal_id, plan, ordinal, attempt):
    if (
        type(goal_id) is not str
        or not goal_id
        or type(attempt) is not int
        or attempt < 0
    ):
        raise ValueError("explicit reading call identity required")
    if type(ordinal) is not int or not 0 <= ordinal < len(plan["fragments"]):
        raise ValueError("known reading fragment required")
    return (
        "reading:"
        + sha256(
            codec.dumps([PROTOCOL, goal_id, plan["partition_hash"], ordinal, attempt])
        ).hexdigest()
    )
