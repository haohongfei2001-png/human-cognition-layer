"""Two channels: immutable complete evidence vs bounded model argument packets.

No relevance heuristic silently drops a late counterexample. All mechanical
source slices are scheduled; cross-chunk semantic composition stays unresolved.
The UTF-8 byte count is a conservative fixture token bound, not observed usage.
"""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from array import array
import json

from hcl.kernel.types import HCLFailure
from hcl.semantics.segments import SourceSegment, iter_segments, question_segments


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
        self._metadata_cache = None
        self._template_cache = None

    def _metadata(self, snapshot):
        cached = self._metadata_cache
        if cached is not None and cached[0] is snapshot:
            return cached[1]
        values = {}
        for key, source in snapshot.immutable_views.items():
            offsets = array("I", (0,))
            count = 0
            for char in source.text:
                count += len(char.encode("utf-8"))
                offsets.append(count)
            values[key] = (sha256(source.text.encode()).hexdigest(), offsets)
        self._metadata_cache = (snapshot, values)
        return values

    def _template(self, snapshot, question, purpose):
        cached = self._template_cache
        if cached is not None and cached[0] is snapshot and cached[1:3] == (question, purpose):
            return dict(cached[3]), cached[4]
        # Keep source version/query bindings, but never construct discarded full
        # source segments merely to obtain the typed contract and query anchors.
        empty = replace(snapshot, immutable_views={})
        if purpose == "semantic_compile":
            from hcl.semantics.segments import semantic_context

            context = semantic_context(empty, question, self.semantic_profile)
        elif purpose == "revision_compile":
            from hcl.semantics.revision import revision_context

            context = revision_context(empty, question)
        elif purpose == "interaction_compile":
            from hcl.semantics.interaction_compiler import interaction_context
            context = interaction_context(empty, question)
        elif purpose == "discovery_compile":
            from hcl.semantics.discovery_compiler import discovery_context
            context = discovery_context(empty, question)
        elif purpose == "argument_compile":
            from hcl.semantics.argument_compiler import argument_context
            context = argument_context(empty, question)
        elif purpose == "mental_compile":
            from hcl.semantics.model_compiler import model_context

            context = model_context(empty, question)
        elif purpose == "answer":
            context = dict(schema="hcl-bounded-answer-context-1", purpose="OFFLINE_EXPRESSION_ONLY")
        else:
            raise ValueError("unsupported context purpose")
        questions = tuple(question_segments(question))
        self._template_cache = (snapshot, question, purpose, context, questions)
        return dict(context), questions

    def serialize(self, snapshot, question, chunk):
        if type(chunk) is not ContextChunk:
            raise ValueError("typed context chunk required")
        checked = []
        metadata = self._metadata(snapshot)
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
            digest, offsets = metadata[segment.source_id]
            if (
                segment.version != source.handle.version
                or segment.source_sha256 != digest
                or not 0 <= segment.start < segment.end <= len(source.text)
                or source.text[segment.start : segment.end] != segment.text
                or segment.byte_start != offsets[segment.start]
                or segment.byte_end != offsets[segment.end]
            ):
                raise HCLFailure(
                    "DENIED",
                    "context",
                    "CONTEXT_SLICE_MISMATCH",
                    "segments",
                    "The selected bytes do not match an original authorized source.",
                )
            checked.append(segment)
        context, questions = self._template(snapshot, question, chunk.purpose)
        context["segments"] = [asdict(s) for s in (*checked, *questions)]
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
        groups, group, group_size = [], [], overhead
        # Stream mechanical slices once. Packet size is additive in serialized
        # segment records, so packing never reserializes the growing source.
        for source in snapshot.immutable_views.values():
            segments = iter_segments(source.text, source.handle.source_id, source.handle.version, "SOURCE")
            for segment in segments:
                start = segment.start
                while start < segment.end:
                    low, high, end = start + 1, segment.end, start
                    while low <= high:
                        middle = (low + high) // 2
                        part = self._piece(snapshot, segment, start, middle)
                        size = len(
                            json.dumps(asdict(part), ensure_ascii=False, separators=(",", ":")).encode()
                        )
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
                    piece = self._piece(snapshot, segment, start, end)
                    size = (
                        len(json.dumps(asdict(piece), ensure_ascii=False, separators=(",", ":")).encode())
                        + 1
                    )
                    if group and group_size + size > limit:
                        groups.append(tuple(group))
                        group, group_size = [], overhead
                        if len(groups) >= 1024:
                            raise HCLFailure(
                                "BUDGET_EXHAUSTED",
                                "context",
                                "CONTEXT_CHUNK_BOUND",
                                "segments",
                                "The bounded context partition has too many fragments.",
                            )
                    group.append(piece)
                    group_size += size
                    start = end
        if group or not groups:
            groups.append(tuple(group))
        return tuple(ContextChunk(purpose, group, i, len(groups)) for i, group in enumerate(groups))

    def _piece(self, snapshot, segment, start, end):
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
            self._metadata(snapshot)[segment.source_id][1][start],
            self._metadata(snapshot)[segment.source_id][1][end],
            text[start:end],
        )
