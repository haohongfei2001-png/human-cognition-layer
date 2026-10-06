"""Official public price read only. No API credential, purchase or model call."""
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
import hashlib,json,os
from pathlib import Path
from urllib.request import Request,urlopen

URL='https://api-docs.deepseek.com/zh-cn/quick_start/pricing/'
RATES={'currency':'CNY','input':'9.0','output':'27.0','model':'deepseek-v4-pro','version':'DeepSeek-V4-Pro-0813'}
class Rows(HTMLParser):
    def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in ('th','td')and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th')and self.cell is not None:
            self.row.append(' '.join(' '.join(self.cell).split()));self.cell=None
        if tag=='tr'and self.row is not None:self.rows.append(self.row);self.row=None

def parse_price(raw):
    if not isinstance(raw,bytes)or not 1<=len(raw)<=512000:raise ValueError('BOUNDED_OFFICIAL_PRICE_REQUIRED')
    parser=Rows();parser.feed(raw.decode('utf-8'))
    text=' '.join(' '.join(row)for row in parser.rows)
    # Exact official model-column order and peak rows; fail rather than guess a
    # changed table, currency, alias, version, or discount schedule.
    model=next((row for row in parser.rows if row and row[0]=='模型'),None)
    if model is None or len(model)!=3 or not model[1].startswith('deepseek-flash')or model[2]!='deepseek-v4-pro':raise ValueError('OFFICIAL_MODEL_TABLE_CHANGED')
    version=next((row for row in parser.rows if row and row[0]=='模型版本'),None)
    if version is None or len(version)!=3 or version[2]!='DeepSeek-V4-Pro-0813':raise ValueError('OFFICIAL_MODEL_VERSION_CHANGED')
    peaks=[row for row in parser.rows if row and row[0]=='高峰时段']
    if peaks!=[['高峰时段','0.04元','0.30元'],['高峰时段','2元','9.0元'],['高峰时段','8元','27.0元']]:raise ValueError('OFFICIAL_PEAK_PRICE_CHANGED')
    return dict(RATES)

def validate_price_evidence(row,identity,now):
    if(set(row)!= {'run_id','head_sha','url','checked_at','sha256','rates'}or any(row[k]!=v for k,v in identity.items())or row['url']!=URL or row['rates']!=RATES):raise ValueError('SAME_RUN_PRICE_REQUIRED')
    sha=row['sha256']
    if not isinstance(sha,str)or len(sha)!=64 or any(c not in '0123456789abcdef'for c in sha):raise ValueError('PRICE_HASH_REQUIRED')
    checked=datetime.fromisoformat(row['checked_at'])
    if checked.tzinfo is None or not timedelta(0)<=now-checked<=timedelta(minutes=10):raise ValueError('FRESH_PRICE_CHECK_REQUIRED')
    return True

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with urlopen(Request(URL,headers={'User-Agent':'HCL-public-price-preflight/1.0'}),timeout=40)as response:
        if response.status!=200 or response.geturl().rstrip('/')!=URL.rstrip('/'):raise ValueError('OFFICIAL_PRICE_FETCH_FAILED')
        raw=response.read(512001)
    rates=parse_price(raw)
    evidence=dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'],url=URL,checked_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest(),rates=rates)
    Path(a.output).write_text(json.dumps(evidence,sort_keys=True))
    print('OFFICIAL_PEAK_PRICE_AND_MODEL_VERIFIED_ZERO_MODEL_CALLS')
