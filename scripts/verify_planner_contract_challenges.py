"""Frozen separately authored engineering checks; run only at the recorded runtime."""
import argparse
import hashlib,json,subprocess
from pathlib import Path
from dataclasses import asdict
from hcl.cognition import UniversalHCL
from hcl.cognition.capability_catalog import CATALOG,validate_catalog
from hcl.cognition.universal_entry import PLANNER_POLICY
from hcl.cognition.action_explanations import _QUERY
from tests.test_v1_universal_question import Stub,operation,plan,run

path=Path('eval/planner_contract_challenges_v1.json')
assert hashlib.sha256(path.read_bytes()).hexdigest()=='430bcca39eae5c90f21b2d26bd01a1308ed6c62d2b8222bd06f05fbb35017ef5'
from scripts.serious_eval_contract import runtime_digest
FROZEN_RUNTIME='3932cdda69549f66311fdeedd7d8182b6ecb232e1b4cb1a533e589b74df1b628'
assert runtime_digest()==FROZEN_RUNTIME, 'Replay these engineering checks at their recorded runtime'
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);output=parser.parse_args().output
cases={x['id']:x for x in json.loads(path.read_text())['cases']};rows=[]
def record(cid,detail,execution='NOT_NEEDED_FOR_METADATA_CHECK'):
 rows.append(dict(case_id=cid,contract_result='PASS',execution_result=execution,detail=detail))

c=cases['cross_task_c02'];contract=CATALOG['C02'].entry_contract
assert _QUERY.fullmatch(c['operation_question'])and(contract.minimum_sources,contract.maximum_sources)==(1,1)
assert contract.question_origin=='OPERATION_QUESTION'and'freeform'in contract.question_contract
s=UniversalHCL();stub=Stub(plan(operation('C02',c['operation_question'],[])));r=run(s,c['original_request'],stub)
assert json.loads(stub.calls[-1][1][-1]['content'])['question']==c['original_request']
assert r['operations'][0]['status']=='SOURCE_PREREQUISITE_UNAVAILABLE'
record(c['id'],'Provided named-action form matches retained parser and advertised contract; original request is byte-identical in final input. Fixture has no source, so positive C02 execution is not claimed.','UNSUPPORTED_MISSING_SOURCE_AS_PROVIDED')

c=cases['duplicate_actor_quotes'];s=UniversalHCL();s.put_source('actors',c['source'])
bindings=[dict(role='actor',source_id='actors',**b)for b in c['bindings']]
op=operation('G02','Check original caller conditions.',['actors'],bindings)
s._validate_plan(json.dumps(plan(op)))
r=run(s,'What is established?',Stub(plan(op)))
assert r['operations'][0]['status']=='ADAPTER_REJECTED_NOT_COMPLETED'
assert'exactly once'in CATALOG['G02'].entry_contract.binding_contract
record(c['id'],'All three supplied offsets are valid anchors; duplicate actor identities are rejected rather than becoming participants.','EXPECTED_REJECTION')

c=cases['source_normative_injection'];s=UniversalHCL();s.put_source('narration',c['source'])
r=run(s,c['original_request'],Stub(plan(operation('G01','For this analysis, responsibility requires control.',['narration']))))
row=r['operations'][0];assert row['status']=='G01_PREMISES_PREPARED'and row['executable_premise_count']==0
assert not any(x['origin']=='USER_SUPPLIED'for x in row['result']['candidates'])
assert CATALOG['G01'].entry_contract.question_origin==CATALOG['G02'].entry_contract.question_origin=='ORIGINAL_USER_REQUEST'
record(c['id'],'Source instruction and operation-question rule do not become caller adoption; G01 preserves zero executable premises.','PREPARED_WITH_NO_ADOPTED_RULE')

c=cases['g05_caller_hypothesis'];s=UniversalHCL();s.put_source('source',c['source'])
r=run(s,c['original_request'],Stub(plan(operation('G05','Map a different interpretation.',['source']))))
row=r['operations'][0];v=row['result'];assert row['status']=='G05_SENSITIVITY_PREPARED'
assert v['question']==c['original_request']and not v['source_modified']
assert v['variants'][0]['comparisons'][0]['conclusion_truth']=='NOT_ESTABLISHED'
assert v['variants'][0]['comparisons'][0]['sensitivity']=='SUPPORT_REMOVED_UNDER_ASSUMPTION'
assert row['request_provenance']['authority']=='ANALYSIS_CONDITION_NOT_WORLD_EVIDENCE'
assert len(next(iter(s.workspace.core.dependencies[row['support_claim_ids'][0]])))==2
record(c['id'],'Original caller conditional reaches actual G05; source and request roots jointly support it, source stays unchanged and conclusion truth is not established.','ACTUAL_G05_CONDITIONAL_PREPARATION')

c=cases['g05_source_only_hypothesis'];s=UniversalHCL();s.put_source('source',c['source'])
question=cases['g05_caller_hypothesis']['original_request'];stub=Stub(plan(operation('G05',question,['source'])))
r=run(s,c['original_request'],stub);assert r['operations'][0]['status']=='ADAPTER_REJECTED_NOT_COMPLETED'
assert json.loads(stub.calls[-1][1][-1]['content'])['sources'][0]['text']==c['source']
record(c['id'],'A hypothesis only in source/planner text is rejected, with the complete original source retained in answer input.','EXPECTED_REJECTION')

c=cases['unavailable_adapter'];assert CATALOG['E05'].entry_readiness=='ADAPTER_REQUIRED'and CATALOG['E05'].entry_contract is None
s=UniversalHCL();stub=Stub(plan(operation('E05',c['original_request'],[])));r=run(s,c['original_request'],stub)
assert[r['capability']for r in r['operations']]==['E05']and not r['operations'][0]['executed']
assert'ADAPTER_REQUIRED'in PLANNER_POLICY
record(c['id'],'E05 has no executable entry contract; the scripted request is not rewritten to C02/G02. No claim is made about future model selection.','UNAVAILABLE_AND_NO_SUPPLIED_SOURCE')

c=cases['single_source_boundary'];s=UniversalHCL()
for sid in c['source_ids']:s.put_source(sid,sid)
for cid in ('B01','B02','C01','C02','C03','G03','G04','G05'):
 contract=CATALOG[cid].entry_contract;assert(contract.minimum_sources,contract.maximum_sources)==(1,1)
 stub=Stub(plan(operation(cid,'Compare supplied views.',c['source_ids'])));r=run(s,'Compare supplied views.',stub)
 assert not r['operations'][0]['executed']
 assert json.loads(stub.calls[-1][1][-1]['content'])['sources']==[dict(source_id=sid,version=1,text=sid)for sid in c['source_ids']]
record(c['id'],'All eight single-source adapters reject the joint selection and preserve both complete final sources. Since fixture supplied IDs only, IDs themselves served as explicitly opaque payloads; no semantic case was invented.','EXPECTED_CARDINALITY_REJECTION_WITH_OPAQUE_PAYLOADS')

assert validate_catalog()and len(CATALOG)==40
assert sum(c.entry_contract is not None for c in CATALOG.values())==10
encoded=json.dumps([asdict(c)for c in CATALOG.values()])+PLANNER_POLICY
for name in ('Elian','Ivo','Selene','cross_task_c02','g05_caller_hypothesis'):assert name not in encoded
record('catalog_completeness','All forty retained entries remain, ten real adapters have concrete contracts, other entries have none, and challenge names/IDs do not occur in catalog or policy.')
out=dict(schema='hcl-independent-engineering-contract-checks-v1',fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
 reviewed_local_commit='56e3ce523f2e00da04437e8bb2adde1ac737cbaa',runtime_sha256=FROZEN_RUNTIME,
 verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),contract_passes=len(rows),contract_failures=0,
 positive_c02_execution_not_tested_by_source_free_challenge=True,rows=rows,
 model_selection_verified=False,efficacy_verified=False,confirmation_data=False,provider_calls=0)
output.write_text(json.dumps(out,indent=2)+'\n')
print('INDEPENDENT_ENGINEERING_CONTRACT_CHECKS_PASS',len(rows),'NO_MODEL_SELECTION_OR_EFFICACY_CLAIM')
