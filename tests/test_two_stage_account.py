"""Read-only account preflight; synthetic transport never reveals financial data."""
from datetime import datetime,timedelta,timezone
from io import BytesIO
import json,unittest
from scripts import two_stage_account as a
NOW=datetime(2026,10,6,18,tzinfo=timezone.utc)
IDENTITY={'run_id':'42','head_sha':'a'*40}
class Response(BytesIO):
    status=200
    def geturl(self):return a.URL
class Opener:
    def __init__(self,value):self.value=value;self.calls=[]
    def open(self,request,timeout):
        self.calls.append((request,timeout))
        return Response(json.dumps(self.value).encode())
class AccountTests(unittest.TestCase):
    def test_one_get_same_destination_returns_only_currency_and_available(self):
        value={'is_available':True,'balance_infos':[{'currency':'CNY','total_balance':'PRIVATE_FINANCIAL_CANARY','granted_balance':'SECRET_BALANCE','topped_up_balance':'HIDDEN'}],'debug':'PROVIDER_PRIVATE'}
        opener=Opener(value);result=a.read_existing('SYNTHETIC_KEY',IDENTITY,NOW,opener)
        self.assertEqual(len(opener.calls),1);request,timeout=opener.calls[0]
        self.assertEqual(request.full_url,a.URL);self.assertEqual(request.method,'GET');self.assertIsNone(request.data)
        self.assertEqual(timeout,30);self.assertTrue(a.validate(result,IDENTITY,NOW))
        wire=json.dumps(result)
        for secret in('SYNTHETIC_KEY','PRIVATE_FINANCIAL_CANARY','SECRET_BALANCE','HIDDEN','PROVIDER_PRIVATE'):self.assertNotIn(secret,wire)
        self.assertEqual(result['model_calls'],0)
    def test_usd_mixed_unavailable_or_unknown_never_pass_cny_gate(self):
        for currencies,available in ((['USD'],True),(['CNY','USD'],True),(['CNY'],False)):
            result=a.read_existing('KEY',IDENTITY,NOW,Opener({'is_available':available,'balance_infos':[{'currency':c}for c in currencies]}))
            with self.assertRaises(ValueError):a.validate(result,IDENTITY,NOW)
        for value in ({},{'is_available':True,'balance_infos':[]},{'is_available':1,'balance_infos':[{'currency':'CNY'}]},{'is_available':True,'balance_infos':[{'currency':'OTHER'}]}):
            with self.assertRaisesRegex(ValueError,'ACCOUNT_READINESS_UNAVAILABLE'):a.read_existing('KEY',IDENTITY,NOW,Opener(value))
    def test_failure_is_single_read_and_error_has_no_sensitive_text(self):
        class Broken(Opener):
            def open(self,request,timeout):self.calls.append(request);raise RuntimeError('PRIVATE_TOKEN_AND_BALANCE')
        opener=Broken(None)
        with self.assertRaisesRegex(ValueError,'^ACCOUNT_READINESS_UNAVAILABLE_NO_MODEL_CALL$'):a.read_existing('KEY',IDENTITY,NOW,opener)
        self.assertEqual(len(opener.calls),1)
        self.assertIsNone(a.NoRedirect().redirect_request(None,None,None,None,None,None))
    def test_readiness_identity_bounds_and_freshness(self):
        result=a.read_existing('KEY',IDENTITY,NOW,Opener({'is_available':True,'balance_infos':[{'currency':'CNY'}]}))
        for field,value in (('run_id','41'),('head_sha','b'*40),('currency','USD'),('available',False),('model_calls',1),('account_read_queries',2),('checked_at',(NOW-timedelta(minutes=11)).isoformat()),('checked_at',(NOW+timedelta(seconds=1)).isoformat())):
            changed=dict(result,**{field:value})
            with self.subTest(field=field),self.assertRaises(ValueError):a.validate(changed,IDENTITY,NOW)
        with self.assertRaises(ValueError):a.read_existing('',IDENTITY,NOW,Opener(None))
if __name__=='__main__':unittest.main()
