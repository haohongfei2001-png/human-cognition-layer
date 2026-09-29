"""I02 source-first, arm-blind scoring interface; never an automatic semantic judge.

The source auditor writes obligations before seeing any arm output. A separate
reviewer assigns judgments to opaque outputs. This module validates the
receipts and computes a conservative score; it cannot decide semantic truth.
"""

import hashlib
import json
from pathlib import Path


RUBRIC_PATH = Path('reports/HCL_I02_SEMANTIC_SCORER_FREEZE.json')
ANSWER_FIELDS = frozenset(('answer', 'source_citations', 'uncertainty', 'assumptions'))
EXPECTATIONS = frozenset(('STATE', 'QUALIFY', 'AVOID'))
JUDGMENTS = frozenset(('SATISFIED', 'VIOLATED', 'UNRESOLVED'))


def load_rubric(path=RUBRIC_PATH):
    rubric = json.loads(Path(path).read_text())
    if rubric.get('schema') != 'hcl-i02-semantic-scorer-v1':
        raise ValueError('unknown scorer schema')
    if rubric.get('answer_fields') != sorted(ANSWER_FIELDS):
        raise ValueError('answer contract changed')
    if rubric.get('unresolved_credit') != 0 or rubric.get('invalid_citation') != 'INELIGIBLE':
        raise ValueError('scoring safety rule changed')
    dimensions = rubric.get('dimensions')
    if not isinstance(dimensions, dict) or not dimensions:
        raise ValueError('dimensions required')
    for name, rule in dimensions.items():
        if not name or rule.get('weight') not in (1, 2, 3):
            raise ValueError('invalid dimension weight')
        if not isinstance(rule.get('description'), str) or not rule['description']:
            raise ValueError('dimension description required')
    return rubric


def rubric_sha256(path=RUBRIC_PATH):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _source_index(manifest):
    sources = manifest.get('sources')
    if not isinstance(sources, list) or not sources:
        raise ValueError('source-first authorized sources required')
    index = {}
    for source in sources:
        if not isinstance(source, dict) or set(source) != {'source_id', 'text'}:
            raise ValueError('invalid source entry')
        source_id, source_text = source['source_id'], source['text']
        if not isinstance(source_id, str) or not source_id or not isinstance(source_text, str) or not source_text:
            raise ValueError('empty source')
        if source_id in index:
            raise ValueError('duplicate source ID')
        index[source_id] = source_text
    return index


def validate_manifest(manifest, rubric):
    """Check a pre-output audit, without consulting any answer or native gold."""
    if manifest.get('schema') != 'hcl-i02-source-first-obligations-v1':
        raise ValueError('unknown source audit schema')
    if manifest.get('rubric_sha256') != rubric_sha256():
        raise ValueError('source audit bound to another rubric')
    if manifest.get('split') not in ('CALIBRATION', 'CONFIRMATION'):
        raise ValueError('split missing')
    if not manifest.get('case_id') or manifest.get('arm_output_seen') is not False:
        raise ValueError('audit must precede arm outputs')
    index = _source_index(manifest)
    obligations = manifest.get('obligations')
    if not isinstance(obligations, list) or not obligations:
        raise ValueError('source-first obligations required')
    ids = set()
    for item in obligations:
        if not isinstance(item, dict) or set(item) != {
                'id', 'dimension', 'expectation', 'source_quotes', 'audit_question'}:
            raise ValueError('invalid obligation')
        if not isinstance(item['id'], str) or not item['id'] or item['id'] in ids:
            raise ValueError('duplicate or empty obligation ID')
        ids.add(item['id'])
        if item['dimension'] not in rubric['dimensions'] or item['expectation'] not in EXPECTATIONS:
            raise ValueError('unknown dimension or expectation')
        if not isinstance(item['audit_question'], str) or not item['audit_question'].strip():
            raise ValueError('auditable semantic question required')
        if not isinstance(item['source_quotes'], list) or not item['source_quotes']:
            raise ValueError('each obligation needs source-first anchors')
        for anchor in item['source_quotes']:
            if not isinstance(anchor, dict) or set(anchor) != {'source_id', 'quote'}:
                raise ValueError('invalid source anchor')
            if (anchor['source_id'] not in index or not isinstance(anchor['quote'], str)
                    or not anchor['quote'] or anchor['quote'] not in index[anchor['source_id']]):
                raise ValueError('obligation quote is not exact authorized source')
    return index


def validate_answer(answer, sources):
    if not isinstance(answer, dict) or set(answer) != ANSWER_FIELDS:
        raise ValueError('final answer contract mismatch')
    for field in ('answer', 'uncertainty', 'assumptions'):
        if not isinstance(answer[field], str):
            raise ValueError('text field must be a string')
    citations = answer['source_citations']
    if not isinstance(citations, list):
        raise ValueError('source citations must be a list')
    for citation in citations:
        if not isinstance(citation, dict) or 'source_id' not in citation:
            raise ValueError('invalid citation')
        quote = citation.get('quote')
        quotation = citation.get('quotation')
        if (quote is None) == (quotation is None):
            raise ValueError('citation needs exactly one quote key')
        text = quote if quote is not None else quotation
        if citation['source_id'] not in sources or not isinstance(text, str) or not text or text not in sources[citation['source_id']]:
            raise ValueError('citation is not exact authorized source')
    return True


def score_review(manifest, answer, review, rubric=None):
    """Score a complete blinded human audit; unresolved receives zero credit."""
    rubric = rubric or load_rubric()
    sources = validate_manifest(manifest, rubric)
    validate_answer(answer, sources)
    if (not isinstance(review, dict) or review.get('schema') != 'hcl-i02-blind-review-v1'
            or review.get('case_id') != manifest['case_id'] or not review.get('opaque_output_id')
            or 'arm' in review or 'winner' in review):
        raise ValueError('review must be complete and arm-blind')
    rows = review.get('judgments')
    if not isinstance(rows, list) or len(rows) != len(manifest['obligations']):
        raise ValueError('one judgment per obligation required')
    by_id = {item['id']: item for item in manifest['obligations']}
    response_text = '\n'.join((answer['answer'], answer['uncertainty'], answer['assumptions']))
    seen = set()
    earned = total = 0
    critical_failures = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'id', 'judgment', 'rationale', 'output_excerpt'}:
            raise ValueError('invalid review row')
        item_id = row['id']
        if item_id not in by_id or item_id in seen or row['judgment'] not in JUDGMENTS:
            raise ValueError('unknown, duplicate or invalid judgment')
        seen.add(item_id)
        if not isinstance(row['rationale'], str) or not row['rationale'].strip():
            raise ValueError('reasoned review required')
        excerpt = row['output_excerpt']
        if not isinstance(excerpt, str) or (excerpt and excerpt not in response_text):
            raise ValueError('review excerpt must be exact output text')
        if (by_id[item_id]['expectation'] == 'AVOID' and row['judgment'] == 'VIOLATED'
                and not excerpt):
            raise ValueError('unsupported upgrade must cite output')
        if (by_id[item_id]['expectation'] == 'STATE' and row['judgment'] == 'SATISFIED'
                and not excerpt):
            raise ValueError('positive finding must cite output')
        weight = rubric['dimensions'][by_id[item_id]['dimension']]['weight']
        total += weight
        if row['judgment'] == 'SATISFIED':
            earned += weight
        elif row['judgment'] == 'VIOLATED' and weight == 3:
            critical_failures.append(item_id)
    if seen != set(by_id):
        raise ValueError('incomplete review')
    return {'case_id': manifest['case_id'], 'opaque_output_id': review['opaque_output_id'],
        'rubric_sha256': rubric_sha256(), 'earned': earned, 'possible': total,
        'semantic_fraction': earned / total, 'critical_failures': critical_failures,
        'eligible': not critical_failures, 'unresolved_credit': 0}
