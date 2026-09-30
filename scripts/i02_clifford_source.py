"""One complete public-domain essay and pre-output development task, not a solver."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
from hcl.v1 import HCLCognitionLayer,prepare_person_context
from scripts.serious_eval_contract import runtime_digest
from scripts.serious_eval_semantic_score import validate_manifest,load_rubric
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9,prepare_generic_final_v9
SOURCE=Path('reports/HCL_I02_CLIFFORD_DEVELOPMENT_SOURCE.json')
OBLIGATIONS=Path('reports/HCL_I02_CLIFFORD_SOURCE_FIRST_OBLIGATIONS.json')
SOURCE_FILE_HASH='ba69220352cff7c2ee08ae36f1c64069f2280d352f15a727df474da1294b87ef'
OBLIGATIONS_FILE_HASH='b8a2b25ee1e669784c266b8077cb65b36d2a737050e79cc7fa766f3cacf2bb66'
RAW_HASH='3b9b1eb0455b0fe968a0f987aa279602216ae0aabe1560300177a1993e45a6e9'
RDF_HASH='df8c41fa5aded36dd94cbc058a7edf4e0a712d13947f62bf86df8f860b21f56e'
SOURCE_HASH='ff0bdcb7dfc4bdcde98b37108cd33b40583adef83c8ff6eaee5f8d4025e65eaa'
QUESTION_HASH='1fbd10ba151d92ba265cbd86c8e708e455f9fe53379a1e02efe8969e032ff41c'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def reconstruct(raw,rdf):
    if sha(raw)!=RAW_HASH or sha(rdf)!=RDF_HASH:raise ValueError('pinned publisher edition mismatch')
    if b'<pgterms:name>Clifford, William Kingdon</pgterms:name>' not in rdf or b'>1879</pgterms:deathdate>' not in rdf or b'Public domain in the USA.' not in rdf:raise ValueError('publisher attribution/term metadata mismatch')
    text=raw.decode('utf-8-sig');start=text.index('III. THE ETHICS OF BELIEF.');end=text.index('IV. THE ETHICS OF RELIGION.')
    unit=text[start:end].strip()
    if [start,end]!=[117851,174684] or sha(unit.encode())!=SOURCE_HASH:raise ValueError('complete native essay reconstruction drift')
    return unit
def download_material():
    item=json.loads(SOURCE.read_text())
    return tuple(urllib.request.urlopen(item[k],timeout=45).read() for k in ('raw_url','rdf_url'))
def audit(raw=None,rdf=None):
    b,o=SOURCE.read_bytes(),OBLIGATIONS.read_bytes()
    if sha(b)!=SOURCE_FILE_HASH or sha(o)!=OBLIGATIONS_FILE_HASH:raise ValueError('frozen source or source-first obligations drift')
    item,manifest=json.loads(b),json.loads(o);s,q=item['source_text'],item['ordinary_question']
    if sha(s.encode())!=SOURCE_HASH or sha(q.encode())!=QUESTION_HASH or item['provider_input_allowed'] is not True or item['development_exposed'] is not True or item['independent_confirmation_qualified'] is not False or item['expert_gold_used'] or item['arm_outputs_seen'] or item['private_owner_data'] or item['longmemeval']!='SEALED_NOT_ACCESSED':raise ValueError('source/rights/exposure boundary drift')
    if (raw is None)!=(rdf is None):raise ValueError('both pinned raw and metadata required')
    if raw is not None and reconstruct(raw,rdf)!=s:raise ValueError('source differs from publisher unit')
    validate_manifest(manifest,load_rubric())
    if manifest['case_id']!=item['case_id'] or len(manifest['obligations'])!=9:raise ValueError('source-first task identity mismatch')
    arms=prepare_primary_arms_v9(q,item['source_id'],s);expected=[dict(source_id=item['source_id'],text=s)]
    for phase in ('C','P','G_map'):
        p=json.loads(arms[phase][-1]['content'])
        if p['sources']!=expected or p['question']!=q:raise ValueError('unequal ordinary comparator input')
    mock=json.dumps(dict(source_index=[dict(id='e1',source_id=item['source_id'],quote=manifest['obligations'][0]['source_quotes'][0]['quote'])],relations=[],answer_plan=[],open_questions=[]))
    final=prepare_generic_final_v9(arms,mock)
    if json.loads(final[-1]['content'])['sources']!=expected:raise ValueError('G full-source loss')
    h=prepare_person_context(HCLCognitionLayer(lambda _: ''),q,s)
    hp=json.loads(h.messages[-1]['content'])
    if hp['sources']!=[dict(source_id=item['source_id'],text=s,version=1)] or hp['query']!=q or h.preparation_receipt['specialized_cognition_treatment']:raise ValueError('measured no-treatment/full-source H boundary drift')
    return dict(schema='hcl-i02-clifford-source-preflight-v1',source_file_sha256=sha(b),obligations_file_sha256=sha(o),source_sha256=SOURCE_HASH,question_sha256=QUESTION_HASH,publisher_reconstruction_verified=raw is not None,source_characters=len(s),source_valid=True,rights_scope=item['rights_scope'],source_first_obligation_count=9,independent_confirmation_qualified=False,difficulty_qualified=False,cpg_model_semantics_qualified=False,full_ordinary_input_equal_for_cpg=True,hcl_runtime_sha256=runtime_digest(),h_complete_source=True,h_specialized_treatment_present=False,h_preparation_receipt=h.preparation_receipt,h_hnew_calls_allowed=False,provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--raw',required=True);parser.add_argument('--rdf',required=True);parser.add_argument('--output',required=True);a=parser.parse_args()
    Path(a.output).write_text(json.dumps(audit(Path(a.raw).read_bytes(),Path(a.rdf).read_bytes()),indent=2)+'\n')
