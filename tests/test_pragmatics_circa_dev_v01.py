import csv, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from hcl.pragmatics import source_view, request_messages, THIN_METHOD
from scripts import run_pragmatics_circa_dev_v01 as r


class PragmaticsTests(unittest.TestCase):
    def fixture(self):
        return {
            "id": "test",
            "context": "X and Y are discussing a shared plan.",
            "question-X": "Would you attend?",
            "answer-Y": "Only if I can leave early.",
            "canquestion-X": "POISON_REWRITE",
            "judgements": "POISON",
            "goldstandard1": "POISON",
            "goldstandard2": "POISON",
        }

    def test_annotations_and_rewritten_hypotheses_cannot_enter_source_or_messages(self):
        x = self.fixture()
        v = source_view(x)
        for field in ("canquestion-X", "judgements", "goldstandard1", "goldstandard2"):
            x[field] = "OTHER_POISON"
        self.assertEqual(v, source_view(x))
        c = request_messages(v, r.TASK, r.COMMON)
        p = request_messages(v, r.TASK, r.COMMON, True)
        self.assertEqual(c[1], p[1])
        self.assertNotIn("POISON", json.dumps(p))
        self.assertEqual(p[0]["content"], c[0]["content"] + " " + THIN_METHOD)
        self.assertEqual(v["turns"][1]["utterance"], "Only if I can leave early.")

    def test_source_boundaries_and_detachment(self):
        x = self.fixture()
        v = source_view(x)
        x["answer-Y"] = "changed"
        self.assertNotEqual(v, source_view(x))
        for bad in ("", " " * 10, "x" * 2001, None):
            with self.assertRaises(ValueError):
                source_view(self.fixture() | {"context": bad})

    def test_strict_contract_and_native_labels_are_not_private_truth(self):
        answer = {
            "label": "Yes, subject to some conditions",
            "reason": "The reply explicitly conditions attendance.",
        }
        raw = json.dumps(answer)
        self.assertEqual(r.parse(raw), answer)
        for bad in (
            {"answer": answer},
            answer | {"extra": 1},
            answer | {"reason": ""},
            answer | {"label": "YES"},
            answer | {"reason": "x" * 501},
        ):
            with self.assertRaises(ValueError):
                r.parse(json.dumps(bad))
        self.assertIn("not the person's true mental state", r.COMMON)

    def test_selection_ignores_annotation_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "source"
            f.write_bytes(b"synthetic")
            rows = [
                self.fixture()
                | {
                    "id": str(i),
                    "context": f"situation {i}",
                    "question-X": f"Would you attend activity {i}?",
                }
                for i in range(8)
            ]
            rows = (rows * 4284)[:34268]
            with patch.object(r, "DATA_SHA", r.sha(f.read_bytes())), patch.object(
                r.csv, "DictReader", return_value=rows
            ):
                first = r.select(f)
            poison = [
                x
                | {
                    "goldstandard1": "CHANGED",
                    "judgements": "CHANGED",
                    "canquestion-X": "CHANGED",
                }
                for x in rows
            ]
            with patch.object(r, "DATA_SHA", r.sha(f.read_bytes())), patch.object(
                r.csv, "DictReader", return_value=poison
            ):
                second = r.select(f)
            self.assertEqual(first, second)
            self.assertEqual(len(first), 8)

    def test_earlier_authorizations_cannot_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = Path(tmp) / "manifest"
            m.write_text(json.dumps(r.manifest([])))
            with patch.object(r, "MANIFEST", m), patch.object(
                r, "select", return_value=[]
            ), patch(
                "sys.argv", ["runner", "--source-file", "unused", "--execute"]
            ), patch.dict(
                r.os.environ,
                {
                    "GITHUB_ACTIONS": "true",
                    "GITHUB_RUN_ATTEMPT": "1",
                    "HCL_PRAGMATICS_CIRCA_DEV_RUN_ONCE_TOKEN": r.TOKEN,
                    "HCL_V10_PYARG_DEV_V02_COST_AUTHORIZED_USD": "100",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(RuntimeError, "separate pragmatic"):
                    r.main()

    def test_partial_case_preserves_successful_first_arm_and_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "source.tsv"
            x = self.fixture() | {"goldstandard1": "Yes", "judgements": "Yes#Yes#Yes"}
            with f.open("w") as out:
                w = csv.DictWriter(out, fieldnames=list(x), delimiter="\t")
                w.writeheader()
                w.writerow(x)
            item = {"id": "test", "source": source_view(x), "source_sha256": "s"}
            m = root / "manifest"
            m.write_text(json.dumps(r.manifest([item])))
            calls = []

            class Fake:
                def __init__(self, b, *, name, caps):
                    self.name = name

                def complete_json(self, messages, **kwargs):
                    calls.append(self.name)
                    if self.name == "P":
                        raise RuntimeError("uncertain transport")
                    return json.dumps(
                        {
                            "label": "No",
                            "reason": "A deliberately wrong but valid answer.",
                        }
                    )

            metrics = {"TOTAL": {"provider_response_models": ["fake"]}}
            env = {
                "GITHUB_ACTIONS": "true",
                "GITHUB_RUN_ATTEMPT": "1",
                "HCL_PRAGMATICS_CIRCA_DEV_RUN_ONCE_TOKEN": r.TOKEN,
                "HCL_PRAGMATICS_CIRCA_DEV_COST_AUTHORIZED_USD": "0.05",
                "DEEPSEEK_API_KEY": "fake",
            }
            dest = root / "results.json"
            with patch.object(r, "MANIFEST", m), patch.object(
                r, "select", return_value=[item]
            ), patch.object(r, "CappedBackend", Fake), patch.object(
                r, "OneCallDeepSeekBackend", return_value=None
            ), patch.object(
                r, "_metrics", return_value=metrics
            ), patch(
                "sys.argv",
                ["runner", "--source-file", str(f), "--execute", "--out", str(dest)],
            ), patch.dict(
                r.os.environ, env, clear=True
            ):
                self.assertEqual(r.main(), 1)
            saved = json.loads(dest.read_text())
            self.assertEqual(calls, ["C", "P"])
            self.assertEqual(saved["status"], "PARTIAL_DEVELOPMENT_CONSUMED")
            self.assertEqual(saved["results"][0]["arms"]["C"]["answer"]["label"], "No")
            self.assertFalse(
                saved["results"][0]["arms"]["C"]["agrees_with_human_majority"]
            )


if __name__ == "__main__":
    unittest.main()
