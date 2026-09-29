"""Exact-content exposure overlay without modifying consumed v3 package files."""
import hashlib
import json
from pathlib import Path

from scripts.i02_source_qualification_v3 import require_qualified_confirmation_source


FINGERPRINTS = Path('reports/HCL_I02_SOURCE_FINGERPRINTS_V4.json')


def load_fingerprints(path=FINGERPRINTS):
    data = json.loads(Path(path).read_text())
    if (data.get('schema') != 'hcl-i02-exposed-source-fingerprints-v4' or
            data.get('scope') !=
                'ADDITIONAL_EXACT_CONTENT_EXPOSURE_DENIAL_NOT_EXHAUSTIVE_AUDIT' or
            data.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('v4 exposed source fingerprints invalid')
    rows = data.get('exposed')
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError('v4 known source exposure missing')
    row = rows[0]
    if (not isinstance(row, dict) or
            row.get('id') != 'kpu-conflict-management-development-calibration' or
            row.get('source_file') !=
                'reports/HCL_I02_KPU_CONFLICT_DEVELOPMENT_SOURCE.json' or
            row.get('source_file_sha256') !=
                '4d415a7e6ea50cb217e72f8a57c36b5841e38209e9fb37934f7e1d659a547cef' or
            row.get('source_text_sha256') !=
                '9e029c7fa4abd6b48607bebb8147b48edf3e093f18b3cd78bd8be6cd8d25347b' or
            row.get('publisher_url') !=
                'https://kpu.pressbooks.pub/businesscomms/chapter/case-conflict-management/' or
            row.get('writing_system_id') !=
                'kpu-business-communication-case-scenarios' or
            row.get('calibration_run_id') != 36602249307 or
            row.get('closure') != 'reports/HCL_I02_KPU_CPG_V6_CLOSURE.md' or
            row.get('confirmation_qualified') is not False):
        raise ValueError('v4 KPU exposure identity drift')
    source_file = Path(row['source_file'])
    raw = source_file.read_bytes()
    if hashlib.sha256(raw).hexdigest() != row['source_file_sha256']:
        raise ValueError('v4 source receipt byte drift')
    source = json.loads(raw)
    if (source.get('source_url') != row['publisher_url'] or
            hashlib.sha256(source.get('source_text', '').encode()).hexdigest() !=
                row['source_text_sha256'] or
            not Path(row['closure']).is_file()):
        raise ValueError('v4 source content or closure drift')
    return data


def require_qualified_confirmation_source_v4(freeze, candidate, audit,
                                             lineage=None):
    """Reject an exact exposed source even under a mirror and renamed IDs."""
    fingerprints = load_fingerprints()
    if not isinstance(candidate, dict) or not isinstance(candidate.get('source_text'), str):
        raise ValueError('ordinary source text required for exposure check')
    source_hash = hashlib.sha256(candidate['source_text'].encode()).hexdigest()
    for row in fingerprints['exposed']:
        if source_hash == row['source_text_sha256']:
            raise ValueError(f'exact exposed source content: {row["id"]}')
    return require_qualified_confirmation_source(freeze, candidate, audit,
                                                 lineage)
