"""I02 historical-calibration lineage gate for unseen confirmation selection.

This supplements the I01 catalog guard. It checks known earlier exposures even
when a future catalog contains only confirmation cases, not calibration cases.
"""

import json
from pathlib import Path


LINEAGE = Path('reports/HCL_I02_EXPOSURE_LINEAGE.json')
IDENTITY_FIELDS = ('writing_system_id', 'author_id', 'template_id', 'source_group_id')
SYSTEM_FIELDS = ('writing_system_id', 'author_id', 'template_id')


def load_lineage(path=LINEAGE):
    lineage = json.loads(Path(path).read_text())
    if (lineage.get('schema') != 'hcl-i02-exposure-lineage-v2' or
            lineage.get('longmemeval') != 'SEALED_NOT_ACCESSED' or
            lineage.get('scope') !=
                'KNOWN_I02_AND_PRE_I02_EXPOSURES_NOT_EXHAUSTIVE_REPOSITORY_AUDIT'):
        raise ValueError('lineage receipt invalid')
    rows = lineage.get('exposed_systems')
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError('known exposed systems missing')
    ids = set()
    for row in rows:
        if not isinstance(row, dict) or not row.get('id') or row['id'] in ids:
            raise ValueError('exposure identity invalid')
        ids.add(row['id'])
        if any(not isinstance(row.get(k), str) or not row[k] for k in IDENTITY_FIELDS):
            raise ValueError('exposure lineage fields missing')
        if not isinstance(row.get('calibration_run_id'), int) or not row.get('closure'):
            raise ValueError('immutable run/closure receipt missing')
    historical = lineage.get('historical_exposed_systems')
    if not isinstance(historical, list) or len(historical) < 5:
        raise ValueError('known pre-I02 historical exposure systems missing')
    for row in historical:
        if not isinstance(row, dict) or not row.get('id') or row['id'] in ids:
            raise ValueError('historical exposure identity invalid')
        ids.add(row['id'])
        if any(not isinstance(row.get(key), str) or not row[key]
               for key in SYSTEM_FIELDS):
            raise ValueError('historical source-system lineage missing')
        evidence = row.get('evidence')
        if (not isinstance(evidence, str) or not evidence.startswith('docs/') or
                not Path(evidence).is_file() or not row.get('basis')):
            raise ValueError('historical exposure evidence missing')
    screened_statuses = {
        'SEARCH_SNIPPET_EXPOSED_TASK_FIT_UNAUDITED_NOT_CONFIRMATION_QUALIFIED',
        'PUBLISHER_CONTENT_AND_QUESTIONS_EXPOSED_NOT_CONFIRMATION_QUALIFIED',
        'PUBLIC_CATALOG_SUMMARY_EXPOSED_NOT_CONFIRMATION_QUALIFIED',
    }
    for row in lineage.get('screened_not_qualified', []):
        if (row.get('status') not in screened_statuses or
                row.get('content_rows_seen_at_least', 0) < 1 or
                row.get('native_labels_opened') != 0 or
                row.get('model_input_allowed') is not False or
                row.get('item_level_source_validity') != 'NOT_AUDITED'):
            raise ValueError('screened source cannot be promoted by metadata')
        if any(not row.get(key) for key in ('writing_system_id', 'author_id', 'template_id')):
            raise ValueError('screened source lineage missing')
    return lineage


def require_confirmation_disjoint(candidate, lineage=None):
    """Reject known source-system reuse; never certify rights or semantic truth.

    The independent repo-wide historical audit is a separate required receipt.
    Candidate content and native labels are intentionally unnecessary here.
    """
    if not isinstance(candidate, dict):
        raise ValueError('candidate must be an object')
    lineage = lineage or load_lineage()
    if candidate.get('split') != 'CONFIRMATION':
        raise ValueError('confirmation split required')
    if any(not isinstance(candidate.get(k), str) or not candidate[k] for k in IDENTITY_FIELDS):
        raise ValueError('complete source lineage identity required')
    for exposed in lineage['exposed_systems']:
        for key in IDENTITY_FIELDS:
            if candidate[key] == exposed[key]:
                raise ValueError(f'{key} reuses exposed calibration system {exposed["id"]}')
    for exposed in lineage['historical_exposed_systems']:
        for key in SYSTEM_FIELDS:
            if candidate[key] == exposed[key]:
                raise ValueError(f'{key} reuses historical source system {exposed["id"]}')
    for screened in lineage.get('screened_not_qualified', []):
        for key in ('writing_system_id', 'author_id', 'template_id'):
            if candidate[key] == screened[key]:
                raise ValueError(f'{key} reuses screened source system {screened["id"]}')
    if candidate.get('repository_wide_exposure_audit') != 'PASS_DISJOINT':
        raise ValueError('repository-wide historical exposure audit required')
    if candidate.get('source_license_status') != 'VERIFIED_FOR_THIS_EVALUATION':
        raise ValueError('source rights not qualified')
    if candidate.get('item_level_source_validity') != 'PASS_SOURCE_FIRST':
        raise ValueError('item-level semantics not qualified')
    if candidate.get('source_access_status') != 'AUTHORIZED_FOR_EVERY_ARM':
        raise ValueError('fair source access missing')
    if candidate.get('longmemeval') != 'NOT_USED':
        raise ValueError('LongMemEval excluded')
    return True


def validate_i02_confirmation_candidate(freeze, candidate, lineage=None):
    """Compose the frozen I01 ordinary/fairness gate with known I02 exposure.

    This still needs independently verified source rights and a real source-first
    item audit before I03; flags in a candidate are assertions, not proof.
    """
    from scripts.serious_eval_contract import validate_candidate

    validate_candidate(freeze, candidate)
    return require_confirmation_disjoint(candidate, lineage)
