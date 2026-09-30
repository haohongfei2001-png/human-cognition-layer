"""Future-only focused evidence ranges with a shared 1500-character quote budget.

The consumed v3/v4 500-character runs remain failed and unchanged. This copies
their identity/shape/enum/occurrence/order checks with only the range resource
limit changed to the pre-existing competent G quote bound. It does not rescore
old responses or certify evidence semantics, independence or model behavior.
"""
import json
from scripts.i02_source_holder_line_index_v3 import index_source,sha,KINDS,TIMES
from scripts.i02_source_holder_typed_contract_v4 import messages as messages_v4
MAX_ANCHOR_CHARACTERS=1500
MAX_RECONSTRUCTED_CHARACTERS=21000  # 8 episodes + 6 obligations, each bounded.

def resolve_review_v5(review,question,source_id,source,index):
    if index!=index_source(source_id,source):
        raise ValueError('current complete source identity/hash/index drift')
    fields={'source_id','source_sha256','question_sha256','family_judgment','answerability_judgment',
            'episodes','obligations','serious_unsupported_upgrades','unresolved_limits','judge_limits'}
    if (not isinstance(review,dict) or set(review)!=fields or
            review['source_id']!=source_id or review['source_sha256']!=sha(source) or
            not isinstance(question,str) or not question.strip() or review['question_sha256']!=sha(question) or
            any(review[k] not in {'PASS','REJECT','UNRESOLVED'} for k in ('family_judgment','answerability_judgment'))):
        raise ValueError('complete source-bound review required')
    if (not isinstance(review['episodes'],list) or len(review['episodes'])>8 or
            (review['family_judgment']=='PASS' and len(review['episodes'])<3) or
            not isinstance(review['obligations'],list) or not 3<=len(review['obligations'])<=6):
        raise ValueError('source-led episode/obligation coverage required')
    ids=set()
    def anchor(row,keys):
        if not isinstance(row,dict) or set(row)!=keys:
            raise ValueError('range-reference row shape mismatch')
        a,z=row['start_line'],row['end_line']
        if (type(a) is not int or type(z) is not int or not 1<=a<=z<=len(index['records']) or
                any(not isinstance(row[k],str) or not row[k].strip() for k in keys-{'start_line','end_line'}) or
                row['id'] in ids):
            raise ValueError('identified existing line range required')
        ids.add(row['id']);begin=index['records'][a-1]['start'];end=index['records'][z-1]['end']
        quote=source[begin:end].strip()
        if not 1<=len(quote)<=MAX_ANCHOR_CHARACTERS:
            raise ValueError('bounded nonempty exact source anchor required')
        return dict(row,quote=quote,source_start=begin,source_end=end)
    episodes=[];positions=[]
    for row in review['episodes']:
        got=anchor(row,{'id','start_line','end_line','evidence_kind','time_basis','analysis'})
        if row['evidence_kind'] not in KINDS or row['time_basis'] not in TIMES:
            raise ValueError('source/time categories required; no automatic chronology')
        episodes.append(got);positions.append(got['source_start'])
    if positions!=sorted(set(positions)):
        raise ValueError('distinct episode source order required')
    obligations=[anchor(row,{'id','expectation','start_line','end_line','audit_question'}) for row in review['obligations']]
    if {row['expectation'] for row in obligations}!={'STATE','QUALIFY','AVOID'}:
        raise ValueError('supported content, uncertainty and unsupported inference boundaries required')
    for key in ('serious_unsupported_upgrades','unresolved_limits'):
        if not isinstance(review[key],list) or any(not isinstance(x,str) or not x.strip() for x in review[key]):
            raise ValueError('reasoned limits/errors required')
    if not review['serious_unsupported_upgrades'] or not isinstance(review['judge_limits'],str) or not review['judge_limits'].strip():
        raise ValueError('critical errors and judge limits required')
    return dict(schema='hcl-i02-source-holder-resolved-ranges-v5',episodes=episodes,obligations=obligations,
        source_sha256=sha(source),question_sha256=sha(question),source_order_verified=True,story_time_verified=False,
        semantic_truth_verified=False,actor_or_motive_semantics_verified=False,
        confirmation_qualified=False,provider_calls_authorized=0,provider_spend_authorized_usd=0,
        consumed_package_migration=False,live_capacity_verified=False)

def messages(question,source_id,source):
    prepared=messages_v4(question,source_id,source)
    old='totaling at most 500 characters'
    if prepared[0]['content'].count(old)!=1:
        raise ValueError('future reference instruction dependency drift')
    prepared[0]=dict(role='system',content=prepared[0]['content'].replace(old,'totaling at most 1500 characters')+
        ' Reference ranges remain focused exact source evidence, not whole-source citations. Their reconstructed quote length is at most 1500 characters each; all references together are at most 21000 characters. No old receipt is rescored. The checker verifies source occurrence and resource bounds only, never semantic truth. ')
    payload=json.loads(prepared[-1]['content'])
    payload['reference_limits']=dict(max_anchor_characters=MAX_ANCHOR_CHARACTERS,max_reconstructed_characters=MAX_RECONSTRUCTED_CHARACTERS)
    prepared[-1]=dict(role='user',content=json.dumps(payload,ensure_ascii=False))
    return prepared
