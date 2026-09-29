"""Versioned I02 source qualification boundary, leaving frozen v2 untouched.

The publisher screens are evidence-backed denials. Positive audit fields are
necessary assertions, never automatic proof of privacy, rights or semantics.
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from scripts.i02_source_lineage import require_confirmation_disjoint
from scripts.serious_eval_contract import validate_candidate


SCREENS = Path('reports/HCL_I02_SCREENED_SYSTEMS_V3.json')
REASONS = {
    'PUBLISHER_PROHIBITS_LLM_INGESTION_WITHOUT_PERMISSION',
    'IDENTIFIABLE_SENSITIVE_FAMILY_HISTORY_NOT_CLEARED',
    'DEVELOPMENT_CALIBRATION_SOURCE_EXPOSED_NOT_CONFIRMATION',
}


def _https_url(value):
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username


def load_screens(path=SCREENS):
    data = json.loads(Path(path).read_text())
    if (data.get('schema') != 'hcl-i02-screened-systems-v3' or
            data.get('scope') !=
                'ADDITIONAL_NEGATIVE_SOURCE_SCREENS_NO_CONFIRMATION_QUALIFICATION' or
            data.get('model_provider_calls') != 0 or
            data.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('v3 source screen receipt invalid')
    rows = data.get('screened')
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError('v3 source screens incomplete')
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('id'), str) or
                not row['id'] or row['id'] in seen or
                row.get('reason') not in REASONS or
                not isinstance(row.get('writing_system_id'), str) or
                not row['writing_system_id'] or
                not _https_url(row.get('publisher_url_prefix')) or
                not _https_url(row.get('evidence_url')) or
                row.get('model_input_allowed') is not (
                    row['reason'] ==
                    'DEVELOPMENT_CALIBRATION_SOURCE_EXPOSED_NOT_CONFIRMATION') or
                row.get('calibration_model_input_only', False) is not (
                    row['reason'] ==
                    'DEVELOPMENT_CALIBRATION_SOURCE_EXPOSED_NOT_CONFIRMATION') or
                row.get('confirmation_qualified') is not False):
            raise ValueError('invalid v3 source screen')
        seen.add(row['id'])
    return data


def require_qualified_confirmation_source(freeze, candidate, audit,
                                          lineage=None):
    """Compose old exposure guard with explicit URL, rights and privacy pins.

    A passing machine gate only means a source-first reviewer *claims* the
    evidence is complete. I02 still needs independently checked audit receipts.
    """
    validate_candidate(freeze, candidate)
    screens = load_screens()
    source_url = candidate.get('source_url')
    if not _https_url(source_url):
        raise ValueError('canonical HTTPS publisher source URL required')
    for row in screens['screened']:
        if (source_url.startswith(row['publisher_url_prefix']) or
                candidate['writing_system_id'] == row['writing_system_id']):
            raise ValueError(f'screened source system blocked: {row["id"]}')
    require_confirmation_disjoint(candidate, lineage)
    if (not isinstance(audit, dict) or
            audit.get('schema') != 'hcl-i02-source-first-rights-audit-v3' or
            audit.get('source_url') != source_url or
            audit.get('source_sha256') != hashlib.sha256(
                candidate['source_text'].encode()).hexdigest() or
            audit.get('question_sha256') != hashlib.sha256(
                candidate['question'].encode()).hexdigest() or
            not _https_url(audit.get('license_evidence_url')) or
            audit.get('model_ingestion_permission') != 'VERIFIED_FOR_THIS_USE' or
            audit.get('privacy_review') != 'NO_PRIVATE_PERSON_OR_CLEARED_SCOPE' or
            audit.get('native_question_review') != 'SOURCE_FIRST_PASS' or
            audit.get('rights_reviewer_independent_of_model_outcomes') is not True or
            audit.get('confirmation_outputs_seen') != 0 or
            audit.get('longmemeval') != 'NOT_USED'):
        raise ValueError('source-first rights/privacy/question audit incomplete')
    return True
