from dataclasses import replace
from hashlib import sha256
import unittest
from unittest.mock import patch

from hcl import ExecutionBudget
from hcl.kernel.types import HCLFailure, Principal, thaw
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.models.gateway import OfflineModelPort
from hcl.runtime.context import ContextCompiler
from hcl.runtime.reading_fragments import (
    partition,
    validate,
    materialize,
    call_identity,
    validated_partition,
)


class ReadingPartitionTests(unittest.TestCase):
    def fixture(self):
        store = StateStore()
        owner = Principal("t", "reader")
        store.create_session("s", owner)
        originals = {"A": "aaaa秘密𝄞\n" * 800, "B": "Late counterevidence.\r\n"}
        handles = tuple(
            store.put_source("s", owner, key, text) for key, text in originals.items()
        )
        snapshot = store.snapshot("s", owner, handles)
        budget = ExecutionBudget(max_request_bytes=12000, max_context_tokens=12000)
        compiler = ContextCompiler()
        plan = partition(
            compiler,
            snapshot,
            "Interpret the whole supplied text.",
            "semantic_compile",
            budget,
            OfflineModelPort().describe(),
        )
        return store, snapshot, budget, compiler, plan

    def test_compact_partition_roundtrip_materializes_all_original_bytes(self):
        _, snapshot, budget, compiler, plan = self.fixture()
        question = "Interpret the whole supplied text."
        copied = codec.loads(codec.dumps(plan))
        self.assertNotIn("text", copied["fragments"][0]["segments"][0])
        actual = {key: "" for key in snapshot.source_versions}
        for index in range(len(copied["fragments"])):
            chunk, wire = materialize(compiler, snapshot, question, copied, index)
            self.assertLessEqual(len(wire.encode()), budget.max_request_bytes)
            for segment in chunk.segments:
                actual[segment.source_id] += segment.text
        self.assertEqual(
            actual, {key: value.text for key, value in snapshot.immutable_views.items()}
        )

    def test_omission_wrong_offsets_and_foreign_snapshot_fail_closed(self):
        _, snapshot, _, compiler, plan = self.fixture()
        question = "Interpret the whole supplied text."
        for field, value in [
            ("start", 1),
            ("source_id", "FOREIGN"),
            ("byte_start", 1),
            ("source_sha256", "0" * 64),
        ]:
            altered = thaw(plan)
            altered["fragments"][0]["segments"][0][field] = value
            altered["partition_hash"] = sha256(
                codec.dumps({k: v for k, v in altered.items() if k != "partition_hash"})
            ).hexdigest()
            with self.subTest(field=field), self.assertRaises((ValueError, HCLFailure)):
                materialize(compiler, snapshot, question, altered, 0)
        altered = thaw(plan)
        altered["fragments"].pop()
        altered["partition_hash"] = sha256(
            codec.dumps({k: v for k, v in altered.items() if k != "partition_hash"})
        ).hexdigest()
        with self.assertRaises(ValueError):
            validate(snapshot, question, altered)
        with self.assertRaises(ValueError):
            validate(
                replace(snapshot, access_epoch=snapshot.access_epoch + 1),
                question,
                plan,
            )
        with self.assertRaises(ValueError):
            validate(snapshot, question + " changed", plan)

    def test_fragment_and_repair_call_ids_stay_distinct_and_restorable(self):
        _, snapshot, _, _, plan = self.fixture()
        restored = codec.loads(codec.dumps(plan))
        ids = {
            call_identity("literature", plan, index, attempt)
            for index in range(len(plan["fragments"]))
            for attempt in (0, 1)
        }
        self.assertEqual(len(ids), 2 * len(plan["fragments"]))
        self.assertEqual(
            call_identity("literature", plan, 0, 0),
            call_identity("literature", restored, 0, 0),
        )
        self.assertNotEqual(
            call_identity("other-goal", plan, 0, 0),
            call_identity("literature", plan, 0, 0),
        )

    def test_validated_immutable_partition_does_not_rescan_whole_book_per_packet(self):
        _, snapshot, _, compiler, plan = self.fixture()
        question = "Interpret the whole supplied text."
        with patch("hcl.runtime.reading_fragments.validate", wraps=validate) as checks:
            selected = validated_partition(snapshot, question, plan)
            for ordinal in range(len(plan["fragments"])):
                materialize(compiler, snapshot, question, selected, ordinal)
            self.assertEqual(checks.call_count, 1)
        with self.assertRaises(TypeError):
            selected.data["fragments"][0]["ordinal"] = 99
        with self.assertRaises(ValueError):
            materialize(
                compiler,
                replace(snapshot, revision=snapshot.revision + 1),
                question,
                selected,
                0,
            )


if __name__ == "__main__":
    unittest.main()
