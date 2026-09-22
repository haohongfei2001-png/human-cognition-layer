from __future__ import annotations
import json, unittest
from pathlib import Path
from scripts.run_hitom_external_v01 import parse_pred, sha, prompt
from scripts.aggregate_hitom_external_v01 import summ

ROOT=Path(__file__).resolve().parents[1]
SEL=ROOT/"eval/hitom/selection_v01.json"

class HiToMV01(unittest.TestCase):
    def test_selection_shape(self):
        d=json.loads(SEL.read_text()); s=d["selected"]
        self.assertEqual(len(s),60); self.assertEqual(len({x["sample_id"] for x in s}),60); self.assertEqual(len({x["story_sha256"] for x in s}),60)
        for o in range(5):
            rows=[x for x in s if x["question_order"]==o]; self.assertEqual(len(rows),12)
            for dec in (False,True):
                for l in (1,2,3):
                    self.assertEqual(sum(x["deception"] is dec and x["story_length"]==l for x in rows),2)
    def test_parser(self):
        self.assertEqual(parse_pred("[A]"),"A"); self.assertEqual(parse_pred("Answer: B."),"B"); self.assertIsNone(parse_pred("[A] or [B]"))
    def test_prompt_has_no_cot(self):
        row={"story":"STORY","question":"Q?","choices":"A. x, B. y"}
        p=prompt(row); self.assertIn("STORY",p); self.assertNotIn("Think step-by-step",p); self.assertIn("Return exactly one bracketed option letter",p)
    def test_summary(self):
        xs=[{"control":{"correct":False},"treatment":{"correct":True},"paired_outcome":"improved"},{"control":{"correct":True},"treatment":{"correct":False},"paired_outcome":"worsened"},{"control":{"correct":True},"treatment":{"correct":True},"paired_outcome":"both_correct"}]
        s=summ(xs); self.assertEqual(s["net_paired_gain"],0); self.assertEqual(s["control_correct"],2); self.assertEqual(s["treatment_correct"],2)
if __name__=="__main__": unittest.main()
