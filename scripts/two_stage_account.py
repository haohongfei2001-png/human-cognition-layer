"""One official read-only account query; never expose balance amounts or credentials."""
from datetime import datetime,timezone,timedelta
import json,os
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler

URL='https://api.deepseek.com/user/balance'
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def summarize(value):
    if not isinstance(value,dict)or type(value.get('is_available'))is not bool or not isinstance(value.get('balance_infos'),list):raise ValueError('ACCOUNT_METADATA_UNAVAILABLE')
    rows=value['balance_infos']
    if not rows or len(rows)>10 or any(not isinstance(row,dict)or row.get('currency')not in('USD','CNY')for row in rows):raise ValueError('ACCOUNT_CURRENCY_UNAVAILABLE')
    currencies={row['currency']for row in rows}
    return dict(currency=next(iter(currencies))if len(currencies)==1 else'MULTIPLE_OR_UNKNOWN',available=value['is_available'])

def validate(row,identity,now):
    if(set(row)!={'schema','run_id','head_sha','checked_at','currency','available','model_calls','account_read_queries'}or row['schema']!='hcl-two-stage-account-readiness-v1'or any(row[k]!=v for k,v in identity.items())or row['currency']!='CNY'or row['available']is not True or type(row['model_calls'])is not int or row['model_calls']!=0 or row['account_read_queries']!=1):raise ValueError('CNY_ACCOUNT_READY_REQUIRED')
    checked=datetime.fromisoformat(row['checked_at'])
    if checked.tzinfo is None or not timedelta(0)<=now-checked<=timedelta(minutes=10):raise ValueError('FRESH_ACCOUNT_CHECK_REQUIRED')
    return True

def read_existing(key,identity,now,opener=None):
    if not isinstance(key,str)or not key:raise ValueError('EXISTING_SECRET_UNAVAILABLE')
    opener=opener or build_opener(NoRedirect())
    request=Request(URL,headers={'Authorization':'Bearer '+key,'Accept':'application/json'},method='GET')
    try:
        with opener.open(request,timeout=30)as response:
            if response.status!=200 or response.geturl()!=URL:raise ValueError('ACCOUNT_QUERY_FAILED')
            raw=response.read(64001)
            if len(raw)>64000:raise ValueError('ACCOUNT_RESPONSE_BOUND')
        summary=summarize(json.loads(raw))
    except Exception:
        # No provider body, exception text, balance, or Authorization header.
        raise ValueError('ACCOUNT_READINESS_UNAVAILABLE_NO_MODEL_CALL')from None
    return dict(schema='hcl-two-stage-account-readiness-v1',**identity,checked_at=now.isoformat(),**summary,model_calls=0,account_read_queries=1)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--require-cny',action='store_true');args=parser.parse_args()
    if os.environ.get('GITHUB_REF')!='refs/heads/main':raise SystemExit('TRUSTED_MAIN_ACCOUNT_READ_REQUIRED')
    identity=dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'])
    try:result=read_existing(os.environ.get('DEEPSEEK_API_KEY'),identity,datetime.now(timezone.utc))
    except ValueError:raise SystemExit('ACCOUNT_READINESS_UNAVAILABLE_NO_MODEL_CALL')from None
    Path(args.output).write_text(json.dumps(result,sort_keys=True))
    print(json.dumps(result,sort_keys=True))
    if args.require_cny:
        try:validate(result,identity,datetime.now(timezone.utc))
        except ValueError:raise SystemExit('CNY_ACCOUNT_READY_REQUIRED_NO_MODEL_CALL')from None
