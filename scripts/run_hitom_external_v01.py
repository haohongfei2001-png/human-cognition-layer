#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from hcl.v03.answer_loop import HCLAnswerLoop
from hcl.v03.backends import OpenAICompatibleBackend

SELECTION=ROOT/"eval/hitom/selection_v01.json"
MODEL="deepseek-flash"; BASE_URL="https://api.deepseek.com"; SEED=42; TEMPERATURE=0.0; DIRECT_MAX_TOKENS=4096
CONTROL_SYSTEM="Answer the user's benchmark request directly. Follow its requested output format exactly and do not add an explanation."
NOTE="Note: You should assume the following. (1) An agent witnesses everything and every movement before exiting a location. (2) An agent A can infer another agent B's mental state only if A and B have been in the same location, or have private or public interactions. (3) Note that every agent tends to lie. What an agent A tells others doesn't affect A's actual belief. An agent tends to trust an agent that exited the room later than himself. The exit order is known to all agents. (4) Agents in private communications know that others won't hear them, but they know that anyone can hear any public claims."

def sha(s:str)->str: return hashlib.sha256(s.encode()).hexdigest()
def parse_pred(t:str)->str|None:
    b=re.findall(r"\[\s*([A-Z])\s*\]",t.upper())
    if len(set(b))==1: return b[0]
    if len(set(b))>1: return None
    m=re.match(r"^\s*(?:ANSWER\s*:\s*)?\(?\s*([A-Z])\s*\)?(?:\s|[\.,:;]|$)",t.upper())
    return m.group(1) if m else None
def response_meta(t:str)->dict[str,Any]:
    b=t.encode(); return {"response_bytes":len(b),"response_sha256":hashlib.sha256(b).hexdigest()}
def load_rows(path:Path):
    raw=json.loads(path.read_text())
    return raw["data"] if isinstance(raw,dict) else raw
def prompt(row):
    return f"Story:\n{row['story']}\n\nQuestion:\n{row['question']}\n\nChoices:\n{row['choices']}\n\n{NOTE}\n\nReturn exactly one bracketed option letter such as [A]."
def main():
    p=argparse.ArgumentParser(); p.add_argument("--dataset",type=Path,required=True); p.add_argument("--shard-index",type=int,required=True); p.add_argument("--shard-count",type=int,default=6); p.add_argument("--out",type=Path,default=ROOT/"artifacts/hitom-external-v01"); a=p.parse_args()
    key=os.getenv("DEEPSEEK_API_KEY")
    if not key: raise RuntimeError("DEEPSEEK_API_KEY is required")
    sel=json.loads(SELECTION.read_text()); selected=sel["selected"]; shard=selected[a.shard_index::a.shard_count]
    if a.shard_count!=6 or len(selected)!=60 or len(shard)!=10: raise RuntimeError("unexpected sharding")
    rows={int(x["sample_id"]):x for x in load_rows(a.dataset)}
    cb=OpenAICompatibleBackend(api_key=key,base_url=BASE_URL,model=MODEL,seed=SEED)
    hb=OpenAICompatibleBackend(api_key=key,base_url=BASE_URL,model=MODEL,seed=SEED); loop=HCLAnswerLoop(hb)
    results=[]; failures=[]
    for m in shard:
        try:
            row=rows[int(m["sample_id"])]
            assert row["prompting_type"]=="VP"
            assert int(row["question_order"])==m["question_order"] and bool(row["deception"])==m["deception"] and int(row["story_length"])==m["story_length"]
            assert sha(str(row["story"]))==m["story_sha256"]
            pr=prompt(row)
            c=cb.complete([{"role":"system","content":CONTROL_SYSTEM},{"role":"user","content":pr}],max_tokens=DIRECT_MAX_TOKENS,temperature=TEMPERATURE).strip()
            cr=parse_pred(c)
            run=loop.run(pr); t=run.final_answer.strip(); tr=parse_pred(t)
            cc=cr==m["gold_option"]; tc=tr==m["gold_option"]
            results.append({"sample_id":m["sample_id"],"story_sha256":m["story_sha256"],"question_order":m["question_order"],"deception":m["deception"],"story_length":m["story_length"],"control":{"prediction":cr,"correct":cc,**response_meta(c)},"treatment":{"prediction":tr,"correct":tc,**response_meta(t),"hcl_mode":run.state.get("mode"),"hcl_uncertainty":(run.state.get("uncertainty") or {}).get("level") if isinstance(run.state.get("uncertainty"),dict) else None,"revision_performed":run.revision_performed,"second_revision_performed":run.second_revision_performed},"paired_outcome":"improved" if (not cc and tc) else "worsened" if (cc and not tc) else "both_correct" if cc else "both_wrong"})
        except Exception as e:
            failures.append({"sample_id":m["sample_id"],"error_type":type(e).__name__})
    a.out.mkdir(parents=True,exist_ok=True)
    out={"shard_index":a.shard_index,"shard_count":a.shard_count,"requested":len(shard),"completed":len(results),"failures":failures,"results":results}
    (a.out/f"shard_{a.shard_index}.json").write_text(json.dumps(out,indent=2)+"\n")
    raise SystemExit(0 if not failures and len(results)==len(shard) else 3)
if __name__=="__main__": main()
