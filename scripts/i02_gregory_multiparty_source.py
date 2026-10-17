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
# Historical full-RDF freeze; retained for audit, never an acceptance bypass.
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

METADATA_CONTRACT=Path('reports/HCL_I02_GREGORY_METADATA_CONTRACT_V2.json')
METADATA_CONTRACT_HASH='7be4b5480604a0fc4aa19ce29a88d04a65550b29240412a3597e162e92dd99b8'

def publisher_metadata_v2(raw):
    """Strict selected RDF shape, not a general RDF graph or whole-file equality.

    Unused metadata is deliberately outside this versioned contract. Original
    source/question/obligation pins and the embedded-lyrics transport hold stay
    independent. No historical RDF byte equivalence is inferred.
    """
    from urllib.parse import urljoin
    import re
    def require(ok):
        if not ok:raise ValueError('fixed publisher metadata v2 contract drift or ambiguity')
    frozen=METADATA_CONTRACT.read_bytes()
    require(sha(frozen)==METADATA_CONTRACT_HASH)
    contract=json.loads(frozen);expected=contract['projection']
    require(type(raw) is bytes and 0<len(raw)<=512000)
    text=raw.decode('utf-8-sig')
    require('<!DOCTYPE' not in text.upper() and '<!ENTITY' not in text.upper())
    try:root=ET.fromstring(text)
    except ET.ParseError:raise ValueError('invalid publisher metadata XML') from None
    ns={'p':'http://www.gutenberg.org/2009/pgterms/','d':'http://purl.org/dc/terms/',
        'r':'http://www.w3.org/1999/02/22-rdf-syntax-ns#','c':'http://web.resource.org/cc/',
        'a':'http://purl.org/dc/dcam/','x':'http://www.w3.org/XML/1998/namespace',
        's':'http://www.w3.org/2000/01/rdf-schema#'}
    def q(prefix,name):return '{'+ns[prefix]+'}'+name
    base='http://www.gutenberg.org/';xsd='http://www.w3.org/2001/XMLSchema#'
    require(root.tag==q('r','RDF') and root.attrib=={q('x','base'):base})
    nodes=list(root.iter());require(len(nodes)<=4096)
    tags={
        'p':('ebook','downloads','agent','name','birthdate','deathdate','alias','webpage',
            'marc508','marc520','marc901','marc908','bookshelf','file'),
        'd':('publisher','license','issued','rights','creator','title','tableOfContents','language',
            'subject','type','hasFormat','isFormatOf','extent','modified','format','description'),
        'r':('RDF','Description','value'),'c':('Work','license'),'a':('memberOf',),'s':('comment',)}
    allowed_tags={q(prefix,name) for prefix,names in tags.items() for name in names}
    require(all(n.tag in allowed_tags for n in nodes))
    allowed_attributes={q('r',n) for n in ('about','resource','nodeID','datatype')} | {q('x','base')}
    require(all(set(n.attrib)<=allowed_attributes for n in nodes))
    require(all(n.tag in {q('p','ebook'),q('c','Work'),q('r','Description')} for n in root))
    require(all(q('x','base') not in n.attrib for n in nodes[1:]))
    require(all(q('r','parseType') not in n.attrib for n in nodes))
    ids=[n.attrib[q('r','nodeID')] for n in nodes if q('r','nodeID') in n.attrib]
    require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9._-]{0,127}',v) for v in ids)
        and len(ids)==len(set(ids)))
    def blank(node):
        require(not (node.text or '').strip() and all(not (c.tail or '').strip() for c in node))
    def one(parent,tag):
        matches=parent.findall(tag);require(len(matches)==1);return matches[0]
    def scalar(parent,tag,attributes=None):
        node=one(parent,tag);require(len(node)==0 and node.attrib==(attributes or {}))
        require(type(node.text) is str);return node.text
    def uri(value):
        require(type(value) is str and all(33<=ord(c)<=126 for c in value))
        return urljoin(base,value)
    def subject(node):
        require(set(node.attrib)=={q('r','about')});return uri(node.attrib[q('r','about')])
    def resource(parent,tag):
        node=one(parent,tag);require(len(node)==0 and not (node.text or '').strip()
            and set(node.attrib)=={q('r','resource')});return uri(node.attrib[q('r','resource')])
    def container(parent,tag,datatype=None,member=None):
        wrapper=one(parent,tag);require(not wrapper.attrib and len(wrapper)==1);blank(wrapper)
        desc=one(wrapper,q('r','Description'))
        require(set(desc.attrib)=={q('r','nodeID')});blank(desc)
        require(len(desc)==(2 if member else 1))
        if member:require(resource(desc,q('a','memberOf'))==member)
        return scalar(desc,q('r','value'),{} if datatype is None else {q('r','datatype'):datatype})
    book=one(root,q('p','ebook'));ebook_uri=subject(book);blank(book)
    require(ebook_uri==expected['ebook_uri'] and len(root.findall('.//'+q('p','ebook')))==1)
    creator=one(book,q('d','creator'));require(not creator.attrib and len(creator)==1);blank(creator)
    agent=one(creator,q('p','agent'));agent_uri=subject(agent);blank(agent)
    catalog=one(root,q('c','Work'));catalog_uri=subject(catalog);blank(catalog)
    require(catalog_uri==base and len(root.findall('.//'+q('c','Work')))==1)
    def predicates(parent,allowed):require(all(node.tag in allowed for node in parent))
    # New predicates on protected subjects may add rights/access conditions.
    # They are not silently classed as unused metadata by this version.
    predicates(book,{q('d',n) for n in ('publisher','license','issued','rights','creator','title',
        'tableOfContents','language','subject','type','hasFormat')} |
        {q('p',n) for n in ('downloads','marc508','marc520','marc901','marc908','bookshelf')})
    predicates(agent,{q('p',n) for n in ('name','birthdate','deathdate','alias','webpage')})
    predicates(catalog,{q('c','license'),q('s','comment')})
    # Protected predicates cannot be moved to another subject or hidden inside
    # otherwise ignored metadata. Unknown namespaces with protected names fail.
    protected=[q('d',n) for n in ('publisher','license','issued','rights','creator','title','language','type')]
    protected += [q('p',n) for n in ('agent','name','birthdate','deathdate')]+[q('c','license')]
    names={tag.split('}')[1] for tag in protected}
    require(all(n.tag in protected for n in nodes if n.tag.split('}')[-1] in names))
    require(all(sum(n.tag==tag for n in nodes)==1 for tag in protected))
    formats=book.findall(q('d','hasFormat'));files=[]
    for wrapper in formats:
        require(not wrapper.attrib and len(wrapper)==1);blank(wrapper)
        node=one(wrapper,q('p','file'))
        if subject(node)==expected['source_file']['uri']:files.append(node)
    require(len(files)==1);source_file=files[0];blank(source_file)
    predicates(source_file,{q('d',n) for n in ('isFormatOf','extent','modified','format')})
    owners={ebook_uri:book,expected['creator']['uri']:agent,expected['source_file']['uri']:source_file,base:catalog,
        expected['ebook_license_uri']:None,expected['catalog_metadata_license_uri']:None}
    all_files=[one(wrapper,q('p','file')) for wrapper in formats]
    parents={child:parent for parent in nodes for child in parent}
    for desc in root.findall(q('r','Description')):
        subject(desc);blank(desc);require(len(desc)==1)
        scalar(desc,q('d','description'))  # Supported detached webpage label only.
    for node in nodes:
        if q('r','about') in node.attrib:
            identity=uri(node.attrib[q('r','about')])
            if identity in owners:require(node is owners[identity])
        if q('r','resource') in node.attrib:
            identity=uri(node.attrib[q('r','resource')])
            if identity in owners:
                valid=(identity==ebook_uri and node.tag==q('d','isFormatOf') and parents.get(node) in all_files)
                valid=valid or (identity==expected['ebook_license_uri'] and node is one(book,q('d','license')))
                valid=valid or (identity==expected['catalog_metadata_license_uri'] and node is one(catalog,q('c','license')))
                require(valid and len(node)==0 and not (node.text or '').strip()
                    and set(node.attrib)=={q('r','resource')})
    projection=dict(schema=expected['schema'],ebook_uri=ebook_uri,
        publisher=scalar(book,q('d','publisher')),title=scalar(book,q('d','title')),
        issued=scalar(book,q('d','issued'),{q('r','datatype'):xsd+'date'}),
        rights=scalar(book,q('d','rights')),ebook_license_uri=resource(book,q('d','license')),
        creator=dict(uri=agent_uri,name=scalar(agent,q('p','name')),
            birthdate=scalar(agent,q('p','birthdate'),{q('r','datatype'):xsd+'integer'}),
            deathdate=scalar(agent,q('p','deathdate'),{q('r','datatype'):xsd+'integer'})),
        language=container(book,q('d','language'),ns['d']+'RFC4646'),
        type=container(book,q('d','type'),member=ns['d']+'DCMIType'),
        source_file=dict(uri=subject(source_file),is_format_of=resource(source_file,q('d','isFormatOf')),
            extent=scalar(source_file,q('d','extent'),{q('r','datatype'):xsd+'integer'}),
            publisher_format_claim=container(source_file,q('d','format'),ns['d']+'IMT',ns['d']+'IMT')),
        catalog_metadata_license_uri=resource(catalog,q('c','license')))
    digest=sha(json.dumps(projection,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    require(projection==expected and digest==contract['projection_sha256'])
    return dict(publisher_metadata_contract=contract['schema'],publisher_metadata_contract_sha256=sha(frozen),
        publisher_metadata_projection_sha256=digest,observed_publisher_rdf_sha256=sha(raw),
        historical_publisher_rdf_sha256=RDF_HASH,historical_full_rdf_equivalence='NOT_ESTABLISHED',
        publisher_metadata_scope='SELECTED_V2_FIELDS_ONLY_NOT_WHOLE_RDF_EQUIVALENCE')

def preflight(raw,rdf):
    item=load_candidate();source=original_play(raw);manifest=source_first_manifest(source)
    metadata=publisher_metadata_v2(rdf)
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
    return dict(schema='hcl-i02-gregory-multiparty-preflight-v2',**metadata,status='DEFERRED_EMBEDDED_LYRIC_RIGHTS',source_valid=True,source_chars=len(source),source_sha256=SOURCE_HASH,question_sha256=item['question_sha256'],candidate_sha256=sha(CANDIDATE.read_bytes()),obligations_sha256=sha(OBLIGATIONS.read_bytes()),source_first_obligation_count=len(manifest['obligations']),source_first_review='IMPLEMENTER_ONLY_NOT_INDEPENDENT_SEMANTIC_CERTIFICATION',family_fit='DEVELOPMENT_SOURCE_REVIEW_MULTIPARTY_INFORMATION_STRATEGY',difficulty_qualified=False,source_author_external=True,question_author_external=False,model_training_novelty='UNKNOWN_PUBLIC_CLASSIC',complete_source_in_all_cpg_inputs=True,scorer_or_gold_in_model_input=False,g_map_origin='MOCK_PROVIDER_FREE_ONLY',input_sha256={p:digest(m) for p,m in messages.items()},h_input_sha256=digest(h.messages),h_runtime_sha256=runtime_digest(),h_source_complete=True,h_candidate_count=h.preparation_receipt['candidate_count'],h_checked_mental_expression_count=h.preparation_receipt['epistemic_treatment']['checked_mental_expressions'],h_specialized_treatment=treatment,h_calls_allowed=False,hnew_calls_allowed=False,provider_input_allowed=False,provider_calls_authorized=0,provider_spend_authorized_usd=0,provider_calls=0,provider_spend_usd=0,independent_review=False,confirmation_qualified=False,raw_source_published=False,longmemeval='SEALED_NOT_ACCESSED')

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
