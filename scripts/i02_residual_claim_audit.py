"""Add a full-answer residual claim audit to an immutable I02 v1 score.

This is a reviewer-completeness interface, not an automatic truth judge. It
does not rewrite source-first obligations or historical frozen scores.
"""

from scripts.serious_eval_semantic_score import score_review, validate_manifest, load_rubric


RESIDUAL_JUDGMENTS = frozenset(('SUPPORTED', 'QUALIFIED', 'UNSUPPORTED', 'UNRESOLVED'))
SEVERE_KINDS = frozenset(('ACTOR_TIME_ACCESS', 'INFERENCE_BOUNDARY',
    'NORMATIVE_PREMISE', 'SOURCE_PERMISSION', 'OTHER_SEVERE'))


def audit_residual_claims(manifest, answer, obligation_review, residual_review):
    """Reconcile source-first score with all material leftover output claims.

    An independent reviewer must explicitly attest claim coverage. Exact
    excerpts and supporting source quotes make the audit inspectable, but the
    program cannot prove semantic truth or completeness of human annotation.
    """
    base = score_review(manifest, answer, obligation_review)
    sources = validate_manifest(manifest, load_rubric())
    if not isinstance(residual_review, dict) or set(residual_review) != {
            'schema', 'case_id', 'opaque_output_id', 'coverage_attestation', 'claims'}:
        raise ValueError('complete residual review required')
    if (residual_review['schema'] != 'hcl-i02-residual-claim-audit-v1' or
            residual_review['case_id'] != manifest['case_id'] or
            residual_review['opaque_output_id'] != obligation_review['opaque_output_id'] or
            residual_review['coverage_attestation'] is not True or
            not isinstance(residual_review['claims'], list)):
        raise ValueError('residual review identity or coverage mismatch')
    response_text = '\n'.join((answer['answer'], answer['uncertainty'], answer['assumptions']))
    seen = set()
    unresolved = []
    unsupported = []
    severe = []
    for row in residual_review['claims']:
        if not isinstance(row, dict) or set(row) != {
                'excerpt', 'judgment', 'kind', 'rationale', 'source_quotes'}:
            raise ValueError('invalid residual claim')
        excerpt = row['excerpt']
        if not isinstance(excerpt, str) or not excerpt.strip() or excerpt not in response_text or excerpt in seen:
            raise ValueError('residual excerpt must be unique exact output text')
        seen.add(excerpt)
        if (row['judgment'] not in RESIDUAL_JUDGMENTS or
                row['kind'] not in SEVERE_KINDS | {'OTHER'} or
                not isinstance(row['rationale'], str) or not row['rationale'].strip() or
                not isinstance(row['source_quotes'], list)):
            raise ValueError('invalid residual claim judgment')
        if row['judgment'] == 'SUPPORTED' and not row['source_quotes']:
            raise ValueError('supported claim needs source evidence')
        for anchor in row['source_quotes']:
            if not isinstance(anchor, dict) or set(anchor) != {'source_id', 'quote'}:
                raise ValueError('invalid residual source anchor')
            if (anchor['source_id'] not in sources or
                    not isinstance(anchor['quote'], str) or
                    not anchor['quote'] or anchor['quote'] not in sources[anchor['source_id']]):
                raise ValueError('residual source quote is not exact authorized source')
        if row['judgment'] == 'UNRESOLVED':
            unresolved.append(excerpt)
        if row['judgment'] == 'UNSUPPORTED':
            unsupported.append(excerpt)
            if row['kind'] in SEVERE_KINDS:
                severe.append(excerpt)
    return {'schema': 'hcl-i02-residual-reconciliation-v1',
        'case_id': manifest['case_id'], 'opaque_output_id': base['opaque_output_id'],
        'source_first_score': base, 'residual_claim_count': len(seen),
        'unsupported_excerpts': unsupported, 'unresolved_excerpts': unresolved,
        'severe_unsupported_excerpts': severe,
        'eligible': base['eligible'] and not unsupported and not unresolved,
        'full_answer_semantics_qualified': False}
