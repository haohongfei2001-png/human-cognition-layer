"""Current ordinary-reader entry chain, preserving I01/v1–v12 and consumed DRC001."""
import json
from pathlib import Path
from scripts.i02_runtime_amendment_v12 import validate_runtime_amendment_v12
from scripts.serious_eval_contract import runtime_digest
from scripts.development_drc001_replay import validate_archive

def validate_current(*, current_digest=None):
 names=['HCL_I01_EVALUATION_FREEZE.json','HCL_I02_RUNTIME_AMENDMENT.json']+[f'HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,13)]
 freeze,*versions=[json.loads(Path('reports',n).read_text()) for n in names]
 previous=versions[-1]['amended_hcl_runtime_sha256']
 validate_runtime_amendment_v12(freeze,*versions,current_digest=previous)
 cert=validate_archive();v=json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V13.json').read_text())
 if (v.get('schema')!='hcl-development-runtime-amendment-v13' or v.get('reason')!='GENERAL_AUTHORIZED_READER_B01_C01_C03_ENTRY' or
     v.get('previous_hcl_runtime_sha256')!=previous or cert['runtime_sha256']!=previous or
     v.get('amended_hcl_runtime_sha256')!=(runtime_digest() if current_digest is None else current_digest) or
     v.get('historical_i01_main_sha')!=freeze['architecture_main_sha'] or
     v.get('development_only') is not True or v.get('new_cognition_module') is not False or
     v.get('answer_gain_claimed') is not False or v.get('provider_calls')!=0 or
     v.get('provider_spend_usd')!=0 or v.get('confirmation_items_inspected')!=0 or
     v.get('longmemeval')!='SEALED_NOT_ACCESSED'):
  raise ValueError('invalid current development runtime v13')
 return True
if __name__=='__main__':validate_current();print('DEVELOPMENT_RUNTIME_V13_VALID_OLD_DRC001_PRESERVED')
