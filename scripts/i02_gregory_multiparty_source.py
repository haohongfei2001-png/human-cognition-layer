"""Complete development play + pre-output audit; embedded rights hold all transport."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
import xml.etree.ElementTree as ET
from hcl.v1 import HCLCognitionLayer,prepare_person_context
from scripts.serious_eval_contract import runtime_digest
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9,prepare_generic_final_v9,digest
from scripts.serious_eval_semantic_score import validate_manifest,load_rubric
CANDIDATE=Path('reports/HCL_I02_GREGORY_MULTIPARTY_DEVELOPMENT_CANDIDATE.json')
OBLIGATIONS=Path('reports/HCL_I02_GREGORY_MULTIPARTY_SOURCE_FIRST_OBLIGATIONS.json')
RAW_HASH='5a154c3d214a49e75b2003205356dc78ae25c3c3162a8851d54a57265cfeda23'
RDF_HASH='e32d60224cbf64f51d8a10e16e5c9e7ae62302db4173bda4a2e1900aa1b92901'
SOURCE_HASH='712a9a29d5b8ab974342cf7b2b3c7ad72ae8df979a2ec0bb479b914919d5ce2e'
CANDIDATE_HASH='8cd228779d744e96f372312b4c784a17a95f7a657460b9cb436b7f6223b88833'
OBLIGATION_HASH='2fa17dab35a45a37baa74d3c5a546c687ca47ca61cc1cc5e7ec9ea50955766a7'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def load_candidate():
    raw=CANDIDATE.read_bytes()
    if sha(raw)!=CANDIDATE_HASH:raise ValueError('fixed source/rights/exposure metadata drift')
    return json.loads(raw)
def original_play(raw):
    if sha(raw)!=RAW_HASH:raise ValueError('fixed complete publisher edition drift')
    text=raw.decode('utf-8-sig')
    body=text[85472:103378].strip()
    if (sha(body.encode())!=SOURCE_HASH or len(body)!=17896 or
        not body.startswith('THE RISING OF THE MOON') or not body.endswith('_Curtain._') or
        'THE JACKDAW' in body):raise ValueError('complete play boundary drift; no shortening or rewriting')
    return body

def source_first_manifest(source):
    raw=OBLIGATIONS.read_bytes()
    if sha(raw)!=OBLIGATION_HASH or sha(source.encode())!=SOURCE_HASH:raise ValueError('pre-output source obligation drift')
    seed=json.loads(raw);item=load_candidate()
    if (seed['source_sha256']!=SOURCE_HASH or seed['question_sha256']!=item['question_sha256'] or
        seed['arm_output_seen'] is not False or seed['reviewer']!='IMPLEMENTER_SOURCE_FIRST_ONLY_NOT_INDEPENDENT'):
        raise ValueError('source-first temporal/reviewer boundary drift')
    manifest=dict(schema='hcl-i02-source-first-obligations-v1',rubric_sha256=seed['rubric_sha256'],split='CALIBRATION',case_id=seed['case_id'],arm_output_seen=False,sources=[dict(source_id=item['input_source_id'],text=source)],obligations=seed['obligations'])
    validate_manifest(manifest,load_rubric());return manifest

def preflight(raw,rdf):
    item=load_candidate();source=original_play(raw);manifest=source_first_manifest(source)
    if sha(rdf)!=RDF_HASH:raise ValueError('fixed publisher metadata drift')
    root=ET.fromstring(rdf);ns={'d':'http://purl.org/dc/terms/','pg':'http://www.gutenberg.org/2009/pgterms/'}
    values={k:[e.text for e in root.findall('.//'+tag,ns)] for k,tag in [('title','d:title'),('author','pg:name'),('death','pg:deathdate'),('rights','d:rights')]}
    if values!=dict(title=['Seven Short Plays'],author=['Gregory, Lady'],death=['1932'],rights=['Public domain in the USA.']):raise ValueError('publisher original attribution or term metadata drift')
    sid,q=item['input_source_id'],item['ordinary_question']
    if sha(q.encode())!=item['question_sha256']:raise ValueError('fixed ordinary question drift')
    arms=prepare_primary_arms_v9(q,sid,source)
    fixture=json.dumps(dict(source_index=[dict(id='e1',source_id=sid,quote=manifest['obligations'][0]['source_quotes'][0]['quote'])],relations=[],answer_plan=[],open_questions=[]))
    messages={p:arms[p] for p in ('C','P','G_map')};messages['G_final']=prepare_generic_final_v9(arms,fixture)
    for p,msg in messages.items():
        payload=json.loads(msg[-1]['content'])
        if payload['sources']!=[dict(source_id=sid,text=source)] or payload['question']!=q:raise ValueError('complete source/task inequality')
        if any(row['audit_question'] in json.dumps(msg,ensure_ascii=False) for row in manifest['obligations']):raise ValueError('source-specific scoring oracle leaked to comparator')
    def prohibited(_):raise AssertionError('source qualification cannot invoke provider')
    h=prepare_person_context(HCLCognitionLayer(prohibited),q,source)
    hp=json.loads(h.messages[-1]['content'])
    if hp['sources']!=[dict(source_id=sid,version=1,text=source)] or hp['query']!=q:raise ValueError('actual H source/task loss')
    treatment=h.preparation_receipt['specialized_cognition_treatment']
    return dict(schema='hcl-i02-gregory-multiparty-preflight-v1',status='DEFERRED_EMBEDDED_LYRIC_RIGHTS',source_valid=True,source_chars=len(source),source_sha256=SOURCE_HASH,question_sha256=item['question_sha256'],candidate_sha256=sha(CANDIDATE.read_bytes()),obligations_sha256=sha(OBLIGATIONS.read_bytes()),source_first_obligation_count=len(manifest['obligations']),source_first_review='IMPLEMENTER_ONLY_NOT_INDEPENDENT_SEMANTIC_CERTIFICATION',family_fit='DEVELOPMENT_SOURCE_REVIEW_MULTIPARTY_INFORMATION_STRATEGY',difficulty_qualified=False,source_author_external=True,question_author_external=False,model_training_novelty='UNKNOWN_PUBLIC_CLASSIC',complete_source_in_all_cpg_inputs=True,scorer_or_gold_in_model_input=False,g_map_origin='MOCK_PROVIDER_FREE_ONLY',input_sha256={p:digest(m) for p,m in messages.items()},h_input_sha256=digest(h.messages),h_runtime_sha256=runtime_digest(),h_source_complete=True,h_candidate_count=h.preparation_receipt['candidate_count'],h_checked_mental_expression_count=h.preparation_receipt['epistemic_treatment']['checked_mental_expressions'],h_specialized_treatment=treatment,h_calls_allowed=False,hnew_calls_allowed=False,provider_input_allowed=False,provider_calls_authorized=0,provider_spend_authorized_usd=0,provider_calls=0,provider_spend_usd=0,independent_review=False,confirmation_qualified=False,raw_source_published=False,longmemeval='SEALED_NOT_ACCESSED')

def require_provider_input(receipt):
    # No transport/grant exists for this held source. A caller cannot toggle
    # a Boolean rights assertion and turn a mechanical preflight into permission.
    raise ValueError('embedded lyric provenance/rights unresolved; no provider input or grant')

def download_material():
    item=load_candidate()
    def get(url):
        with urllib.request.urlopen(url,timeout=30) as response:return response.read()
    return get(item['raw_url']),get(item['publisher_rdf_url'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',required=True);p.add_argument('--rdf',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    result=preflight(Path(a.raw).read_bytes(),Path(a.rdf).read_bytes())
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print('COMPLETE_MULTIPARTY_SOURCE_AUDIT_PROVIDER_INPUT_HELD')
