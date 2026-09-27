import csv,json,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from hcl.value_perspective import source_view,request_messages,THIN_METHOD
from scripts import run_value_clash_dev_v01 as r
class ValueTests(unittest.TestCase):
    def test_label_bearing_fields_cannot_enter_messages(self):
        row={"situation":"A team must choose between two public plans.","action":"Choose the first plan.","acceptable":"POISON","unacceptable":"POISON","native_category":"POISON"}
        view=source_view(row,"A previously prioritized speed. A now gives speed and quality equal regard.")
        c=request_messages(view,r.TASK,r.COMMON);p=request_messages(view,r.TASK,r.COMMON,True)
        self.assertNotIn("POISON",json.dumps(p));self.assertEqual(c[1],p[1]);self.assertEqual(p[0]["content"],c[0]["content"]+" "+THIN_METHOD)
        self.assertEqual(set(view),{"situation","action","character_description","scope"})
    def test_no_native_equal_value_solver_or_private_truth(self):
        self.assertIn("do not turn equal regard into a universal rule",THIN_METHOD)
        self.assertIn("not true private psychology",r.COMMON)
        self.assertIn("prior/current",r.COMMON)
        with self.assertRaises(ValueError):source_view({"situation":"","action":"act"},"profile")
    def test_strict_output_contract(self):
        valid={"label":"Ambiguous","reason":"The public description leaves alternatives unresolved."}
        self.assertEqual(r.parse(json.dumps(valid)),valid)
        for bad in [valid|{"label":"Yes/No"},valid|{"extra":True},{"answer":valid},valid|{"reason":""}]:
            with self.assertRaises(ValueError):r.parse(json.dumps(bad))
    def test_previous_budget_cannot_execute(self):
        with tempfile.TemporaryDirectory() as d:
            m=Path(d)/"manifest";m.write_text(json.dumps(r.manifest([])))
            with patch.object(r,"MANIFEST",m),patch.object(r,"select",return_value=[]),patch("sys.argv",["run","--source-file","unused","--execute"]),patch.dict(r.os.environ,{"GITHUB_ACTIONS":"true","GITHUB_RUN_ATTEMPT":"1","HCL_VALUE_CLASH_DEV_RUN_ONCE_TOKEN":r.TOKEN,"HCL_PRAGMATICS_CIRCA_DEV_COST_AUTHORIZED_USD":"100"},clear=True):
                with self.assertRaisesRegex(RuntimeError,"separate value"):r.main()

    def test_selection_ignores_rationale_labels_and_preserves_multiline_anchors(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"source.csv"
            rows=[{"id":str(i),"situation":"First paragraph.\nSecond paragraph.","action":"Choose a plan.","topic":str(i%4),"acceptable":"POISON","unacceptable":"POISON",**{k:"Earlier priority.\nCurrent unresolved alternatives." for k in set(r.PROFILE_FIELDS)}} for i in range(345)]
            def select():
                with f.open("w",newline="") as out:
                    w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
                with patch.object(r,"DATA_SHA",r.sha(f.read_bytes())):return r.select(f)
            before=select()
            for row in rows:row["acceptable"]="OTHER";row["unacceptable"]="OTHER"
            after=select();self.assertEqual(before,after);self.assertEqual(len({x["id"] for x in before}),8)
            self.assertTrue(all("\n" in x["source"]["situation"] and "\n" in x["source"]["character_description"] for x in before))
            self.assertFalse(set(x["id"] for x in before)&set(str(i) for i in range(20)))

    def test_partial_case_preserves_successful_first_arm_and_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "source.tsv"
            x = {"id":"test", "situation":"A public choice.", "action":"Choose the first plan."}
            with f.open("w") as out:
                w = csv.DictWriter(out, fieldnames=list(x), delimiter="\t")
                w.writeheader()
                w.writerow(x)
            item = {"id": "test", "source": source_view(x, "A gives both priorities equal regard."), "source_sha256": "s"}
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
                "HCL_VALUE_CLASH_DEV_RUN_ONCE_TOKEN": r.TOKEN,
                "HCL_VALUE_CLASH_DEV_COST_AUTHORIZED_USD": "0.05",
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
                saved["results"][0]["arms"]["C"]["agrees_with_intended_reference"]
            )
