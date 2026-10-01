"""Existing B01/C01/C03 ordinary mixed-narration admission; archives pinned."""
import json
from pathlib import Path
from scripts.development_runtime_amendment_v22 import validate_current as validate_v22
from scripts.development_drc006_replay import validate_archive
from scripts.serious_eval_contract import runtime_digest

def validate_current(*,current_digest=None):
 previous=json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V22.json').read_text());pin=previous['amended_hcl_runtime_sha256'];validate_v22(current_digest=pin);cert=validate_archive()
 v=json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V23.json').read_text())
 if (v.get('schema')!='hcl-development-runtime-amendment-v23'
     or v.get('previous_hcl_runtime_sha256')!=pin or cert['runtime_sha256']!=pin
     or v.get('amended_hcl_runtime_sha256')!=(current_digest or runtime_digest())
     or v.get('historical_i01_main_sha')!=previous['historical_i01_main_sha']
     or v.get('reason')!='GENERAL_MIXED_NARRATIVE_ATTRIBUTION_COVERAGE'
     or v.get('development_exposed_batches')!=['DRC001','DRC002','DRE001','DRC003','DRC004','DRC005','DRC006']
     or v.get('development_only') is not True or v.get('new_cognition_module') is not False
     or v.get('answer_gain_claimed') is not False or v.get('semantic_certification_claimed') is not False
     or v.get('provider_calls')!=0 or v.get('provider_spend_usd')!=0
     or v.get('confirmation_items_inspected')!=0 or v.get('longmemeval')!='SEALED_NOT_ACCESSED'
     or any(v.get(k) is not True for k in ('consumed_drc001_runtime_preserved','consumed_drc002_runtime_preserved','consumed_drc003_runtime_preserved','consumed_drc004_runtime_preserved','consumed_dre001_runtime_preserved','consumed_drc005_runtime_preserved','consumed_drc006_runtime_preserved'))):
  raise ValueError('invalid current development runtime v23')
 return True
if __name__=='__main__':validate_current();print('DEVELOPMENT_RUNTIME_V23_VALID_MIXED_NARRATION')
