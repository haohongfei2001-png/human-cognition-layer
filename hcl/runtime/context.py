"""Two channels: immutable complete evidence vs bounded model argument packets.

No relevance heuristic silently drops a late counterexample. All mechanical
source slices are scheduled; cross-chunk semantic composition stays unresolved.
The UTF-8 byte count is a conservative fixture token bound, not observed usage.
"""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json

from hcl.kernel.types import HCLFailure
from hcl.semantics.segments import SourceSegment, segment_snapshot


@dataclass(frozen=True)
class ContextChunk:
    purpose: str
    segments: tuple[SourceSegment, ...]
    ordinal: int
    total: int
    feedback: object = None


def tokens_upper_bound(text):
    return len(text.encode("utf-8"))


class ContextCompiler:
    version = "bounded-source-packets-1"

    def __init__(self, semantic_profile=None):
        self.semantic_profile = semantic_profile

    def serialize(self, snapshot, question, chunk):
        if type(chunk) is not ContextChunk:
            raise ValueError("typed context chunk required")
        checked = []
        for segment in chunk.segments:
            if type(segment) is not SourceSegment or segment.kind != "SOURCE":
                raise ValueError("original source segment required")
            source = snapshot.immutable_views.get(segment.source_id)
            if source is None:
                raise HCLFailure(
                    "DENIED",
                    "context",
                    "CONTEXT_SOURCE_DENIED",
                    "segments",
                    "A selected source is outside the authorized snapshot.",
                )
            digest = sha256(source.text.encode()).hexdigest()
            if (
                segment.version != source.handle.version
                or segment.source_sha256 != digest
                or not 0 <= segment.start < segment.end <= len(source.text)
                or source.text[segment.start : segment.end] != segment.text
                or segment.byte_start != len(source.text[: segment.start].encode())
                or segment.byte_end != len(source.text[: segment.end].encode())
            ):
                raise HCLFailure(
                    "DENIED",
                    "context",
                    "CONTEXT_SLICE_MISMATCH",
                    "segments",
                    "The selected bytes do not match an original authorized source.",
                )
            checked.append(segment)
        if chunk.purpose == "semantic_compile":
            from hcl.semantics.segments import semantic_context

            context = semantic_context(snapshot, question, self.semantic_profile)
        elif chunk.purpose == "revision_compile":
            from hcl.semantics.revision import revision_context

            context = revision_context(snapshot, question)
        elif chunk.purpose == "answer":
            context = dict(schema="hcl-bounded-answer-context-1", purpose="OFFLINE_EXPRESSION_ONLY")
        else:
            raise ValueError("unsupported context purpose")
        question_segments = tuple(s for s in segment_snapshot(snapshot, question) if s.kind == "QUESTION")
        context["segments"] = [asdict(s) for s in (*checked, *question_segments)]
        context["coverage"] = dict(
            ordinal=chunk.ordinal,
            total=chunk.total,
            composition="CHUNK_LOCAL_NOT_GLOBAL" if chunk.total > 1 else "SELECTED_SOURCE_SCOPE",
        )
        if chunk.feedback is not None:
            # Feedback is data, cannot modify the requested operation or schema.
            feedback = dict(chunk.feedback)
            if (
                not set(feedback) <= {"kind", "code", "field", "segments", "remaining_count"}
                or len(json.dumps(feedback)) > 8192
            ):
                raise ValueError("bounded diagnostic feedback required")
            context["repair_obligation"] = feedback
        return json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def limit(budget, capabilities):
        limits = [budget.max_request_bytes, budget.max_context_tokens]
        if capabilities.context_tokens is not None:
            limits.append(capabilities.context_tokens)
        return min(limits)

    def chunks(self, snapshot, question, purpose, budget, capabilities):
        limit = self.limit(budget, capabilities)
        # Reserve ordinal/total and a bounded field-specific repair diagnosis.
        overhead = (
            len(self.serialize(snapshot, question, ContextChunk(purpose, (), 1024, 1024)).encode()) + 1024
        )
        room = limit - overhead
        if room < 256:
            raise HCLFailure(
                "BUDGET_EXHAUSTED",
                "context",
                "CONTEXT_CONTRACT_CAPACITY",
                "budget",
                "The question and necessary operator contract exceed context capacity.",
            )
        segments = [s for s in segment_snapshot(snapshot, question) if s.kind == "SOURCE"]
        pieces = []
        for segment in segments:
            # Long paragraphs are partitioned at Unicode character boundaries.
            start = segment.start
            while start < segment.end:
                low, high = start + 1, segment.end
                end = start
                while low <= high:
                    middle = (low + high) // 2
                    part = self._piece(snapshot, segment, start, middle)
                    size = len(json.dumps(asdict(part), ensure_ascii=False).encode())
                    if size <= room:
                        end, low = middle, middle + 1
                    else:
                        high = middle - 1
                if end == start:
                    raise HCLFailure(
                        "BUDGET_EXHAUSTED",
                        "context",
                        "CONTEXT_SEGMENT_CAPACITY",
                        "segments",
                        "An exact source fragment cannot fit the available context.",
                    )
                pieces.append(self._piece(snapshot, segment, start, end))
                start = end
        groups, group = [], []
        for piece in pieces:
            candidate = ContextChunk(purpose, tuple((*group, piece)), 1024, 1024)
            if group and len(self.serialize(snapshot, question, candidate).encode()) + 1024 > limit:
                groups.append(tuple(group))
                group = []
            group.append(piece)
        if group or not groups:
            groups.append(tuple(group))
        if len(groups) > 1024:
            raise HCLFailure(
                "BUDGET_EXHAUSTED",
                "context",
                "CONTEXT_CHUNK_BOUND",
                "segments",
                "The bounded context partition has too many fragments.",
            )
        return tuple(ContextChunk(purpose, group, i, len(groups)) for i, group in enumerate(groups))

    @staticmethod
    def _piece(snapshot, segment, start, end):
        if start == segment.start and end == segment.end:
            return segment
        text = snapshot.immutable_views[segment.source_id].text
        identity = json.dumps(
            [segment.kind, segment.source_id, segment.version, segment.source_sha256, start, end],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return SourceSegment(
            "segment:" + sha256(identity.encode()).hexdigest(),
            segment.kind,
            segment.source_id,
            segment.version,
            segment.source_sha256,
            start,
            end,
            len(text[:start].encode()),
            len(text[:end].encode()),
            text[start:end],
        )
