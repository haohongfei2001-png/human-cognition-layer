#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SEL=ROOT/"eval/hitom/selection_v01.json"

def summ(items):
    n=len(items); cc=sum(x["control"]["correct"] for x in items); tc=sum(x["treatment"]["correct"] for x in items); imp=sum(x["paired_outcome"]=="improved" for x in items); wor=sum(x["paired_outcome"]=="worsened" for x in items)
    return {"n":n,"control_correct":cc,"treatment_correct":tc,"control_accuracy":cc/n,"treatment_accuracy":tc/n,"improved":imp,"worsened":wor,"both_correct":sum(x["paired_outcome"]=="both_correct" for x in items),"both_wrong":sum(x["paired_outcome"]=="both_wrong" for x in items),"net_paired_gain":imp-wor}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,required=True); p.add_argument("--out",type=Path,default=ROOT/"artifacts/hitom-external-v01-summary"); a=p.parse_args()
    sel=json.loads(SEL.read_text()); expected={x["sample_id"] for x in sel["selected"]}
    files=sorted(a.root.rglob("shard_*.json"))
    if len(files)!=6: raise RuntimeError(f"expected 6 shards, got {len(files)}")
    rows=[]; fails=[]; shards=set()
    for f in files:
        d=json.loads(f.read_text()); shards.add(d["shard_index"]); rows+=d["results"]; fails+=d["failures"]
    if shards!=set(range(6)) or fails or len(rows)!=60 or {x["sample_id"] for x in rows}!=expected: raise RuntimeError("Hi-ToM aggregate integrity failure")
    primary=[x for x in rows if x["question_order"]>=2]; controls=[x for x in rows if x["question_order"]<=1]
    by_order={str(o):summ([x for x in rows if x["question_order"]==o]) for o in range(5)}
    by_deception={str(v).lower():summ([x for x in primary if x["deception"] is v]) for v in (False,True)}
    by_length={str(l):summ([x for x in primary if x["story_length"]==l]) for l in (1,2,3)}
    ps=summ(primary); cs=summ(controls)
    positive=ps["net_paired_gain"]>=4 and all(by_order[str(o)]["net_paired_gain"]>-2 for o in (2,3,4)) and cs["net_paired_gain"]>=-2
    negative=ps["net_paired_gain"]<0 or cs["net_paired_gain"]<=-3
    interpretation="positive" if positive else "negative" if negative else "mixed"
    out={"sample":{"questions":60,"distinct_stories":60},"primary":ps,"lower_order_control":cs,"by_order":by_order,"primary_by_deception":by_deception,"primary_by_story_length":by_length,"predeclared_interpretation":interpretation,"question_level":[{"sample_id":x["sample_id"],"story_sha256":x["story_sha256"],"question_order":x["question_order"],"deception":x["deception"],"story_length":x["story_length"],"paired_outcome":x["paired_outcome"],"control_correct":x["control"]["correct"],"treatment_correct":x["treatment"]["correct"],"control_prediction":x["control"]["prediction"],"treatment_prediction":x["treatment"]["prediction"],"hcl_mode":x["treatment"]["hcl_mode"],"hcl_uncertainty":x["treatment"]["hcl_uncertainty"],"revision_performed":x["treatment"]["revision_performed"],"second_revision_performed":x["treatment"]["second_revision_performed"]} for x in sorted(rows,key=lambda z:z["sample_id"])]}
    a.out.mkdir(parents=True,exist_ok=True); (a.out/"summary.json").write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps({k:out[k] for k in ["primary","lower_order_control","by_order","predeclared_interpretation"]},indent=2))
if __name__=="__main__": main()
