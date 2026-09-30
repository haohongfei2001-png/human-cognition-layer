"""Development exposures are ineligible for later final sealed confirmation."""
import hashlib,json
from pathlib import Path
from urllib.parse import urlsplit
REGISTER=Path('reports/HCL_DEVELOPMENT_BENCHMARK_EXPOSURE_REGISTER.json')

def require_final_development_disjoint(candidate):
    if not isinstance(candidate,dict):raise ValueError('candidate object required')
    data=json.loads(REGISTER.read_text())
    if data['schema']!='hcl-development-benchmark-exposure-register-v1' or data['longmemeval']!='SEALED_NOT_ACCESSED':raise ValueError('development exposure register invalid')
    for row in data['entries']:
        if (candidate.get('dataset_id')==row['dataset_id'] or candidate.get('writing_system_id')==row['writing_system_id']):
            raise ValueError('development benchmark consumed for final confirmation')
        for field in ('source_url','canonical_url','publisher_url'):
            value=candidate.get(field)
            if isinstance(value,str):
                got=urlsplit(value);known=urlsplit(row['publisher_url'])
                if got.hostname==known.hostname and (got.path.rstrip('/')==known.path.rstrip('/') or got.path.startswith(known.path.rstrip('/')+'/')):
                    raise ValueError('development publisher lineage cannot enter final confirmation')
    text=candidate.get('source_text');hashes=set(data['selected_source_sha256'])|set(data['raw_distribution_sha256'])
    if candidate.get('source_sha256') in hashes or isinstance(text,str) and hashlib.sha256(text.encode()).hexdigest() in hashes:
        raise ValueError('exact development source consumed despite renamed identities')
    return True

def require_final_confirmation_source(freeze,candidate,audit,repository,revision,lineage=None):
    from scripts.i02_source_qualification_v14 import require_qualified_confirmation_source_v14
    require_final_development_disjoint(candidate)
    return require_qualified_confirmation_source_v14(freeze,candidate,audit,repository,revision,lineage)
