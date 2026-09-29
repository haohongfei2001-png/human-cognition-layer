"""Versioned ACL development exposure beside immutable consumed v2 lineage."""

import hashlib
import json
from pathlib import Path

from scripts.i02_source_lineage import require_confirmation_disjoint
from scripts.i02_source_qualification_v4 import require_qualified_confirmation_source_v4


OVERLAY = Path('reports/HCL_I02_ACL_ETHICS_EXPOSURE_OVERLAY.json')


def load_overlay():
    row = json.loads(OVERLAY.read_text())
    expected = {
        'schema': 'hcl-i02-acl-ethics-exposure-overlay-v1',
        'scope': 'ADDITIONAL_DEVELOPMENT_ONLY_SOURCE_WITH_IMMUTABLE_V2_LINEAGE',
        'id': 'acl-eacl-2023-ethics-tutorial-abstracts-development',
        'source_file': 'reports/HCL_I02_ACL_ETHICS_DEVELOPMENT_SOURCE.json',
        'source_file_sha256': '09a501f1ecf50f31e96659b6fa22637d14ce2ce3e7cf12b400820c9574e45a50',
        'source_text_sha256': '127cf23ee554c575b5c35c94c4d5468f5f1abae14d7cb15195f31ca22e602bc1',
        'writing_system_id': 'acl-eacl-2023-ethics-tutorial-synthetic-abstracts',
        'author_id': 'acl-eacl-2023-ethics-tutorial-organizers',
        'template_id': 'acl-eacl-2023-synthetic-problematic-abstracts',
        'related_author_ids': ['luciana-benotti', 'karen-fort',
                               'min-yen-kan', 'yulia-tsvetkov'],
        'publisher_commit': '582bcc6c68f9f53d23912ea19892a9b2e74264c7',
        'publisher_blob': '3328c30f0bf41956ce61dad617785bc2e4936ec6',
        'content_rows_seen_at_least': 6,
        'native_labels_opened': 0,
        'calibration_model_input_only': True,
        'confirmation_qualified': False,
        'provider_calls': 0,
        'longmemeval': 'SEALED_NOT_ACCESSED',
    }
    if row != expected:
        raise ValueError('ACL exposure overlay changed')
    raw = Path(row['source_file']).read_bytes()
    source = json.loads(raw)
    if (hashlib.sha256(raw).hexdigest() != row['source_file_sha256'] or
            hashlib.sha256(source['source_text'].encode()).hexdigest() !=
                row['source_text_sha256'] or
            source['source_system'] != row['writing_system_id']):
        raise ValueError('ACL exposed source changed')
    return row


def require_acl_development_input(candidate):
    row = load_overlay()
    if (not isinstance(candidate, dict) or
            candidate.get('split') != 'CALIBRATION' or
            any(candidate.get(field) != row[field] for field in
                ('writing_system_id', 'author_id', 'template_id')) or
            not isinstance(candidate.get('source_text'), str) or
            hashlib.sha256(candidate['source_text'].encode()).hexdigest() !=
                row['source_text_sha256'] or
            candidate.get('source_group_id') != row['source_text_sha256'] or
            candidate.get('source_license_status') !=
                'VERIFIED_FOR_THIS_EVALUATION' or
            candidate.get('source_access_status') !=
                'AUTHORIZED_FOR_EVERY_ARM'):
        raise ValueError('ACL development input not approved')
    return True


def require_confirmation_disjoint_acl_overlay(candidate, lineage=None):
    row = load_overlay()
    if not isinstance(candidate, dict):
        raise ValueError('candidate must be an object')
    for field in ('writing_system_id', 'author_id', 'template_id'):
        if candidate.get(field) == row[field]:
            raise ValueError(f'{field} reuses ACL development system')
    if candidate.get('author_id') in row['related_author_ids']:
        raise ValueError('author_id reuses ACL development author')
    if (isinstance(candidate.get('source_text'), str) and
            hashlib.sha256(candidate['source_text'].encode()).hexdigest() ==
                row['source_text_sha256']):
        raise ValueError('source_text reuses ACL development content')
    return require_confirmation_disjoint(candidate, lineage)


def require_qualified_confirmation_source_v5(freeze, candidate, audit,
                                             lineage=None):
    """Compose ACL exclusion with the unchanged v4 source qualification gate."""
    require_confirmation_disjoint_acl_overlay(candidate, lineage)
    return require_qualified_confirmation_source_v4(freeze, candidate, audit,
                                                    lineage)
