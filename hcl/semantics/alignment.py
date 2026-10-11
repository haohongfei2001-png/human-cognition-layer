"""Alignment records cannot certify semantics merely because quotes/JSON match."""


def judgment(model_judgment, explanation, *, unresolved_segments=()):
    return {'model_judgment': model_judgment, 'explanation': explanation,
            'mechanical_validation': 'SOURCE_SEGMENT_IDENTITIES_AND_TYPED_AST_CHECKED',
            'semantic_certified': False,
            'semantic_validation': 'MODEL_INTERPRETATION_UNVERIFIED',
            'unresolved_segments': list(unresolved_segments),
            'coverage_claim': 'DECLARED_MAPPINGS_ONLY_NOT_SEMANTIC_COMPLETENESS'}


def render_formula(ast, entities, predicates):
    """Deterministic candidate paraphrase, never an original quotation."""
    op = ast['op']
    if op == 'atom':
        args = [entities[term['entity']]['label'] if 'entity' in term else term['var'] for term in ast['args']]
        return predicates[ast['predicate']]['label'] + '(' + ', '.join(args) + ')'
    if op == 'opaque':
        return 'Unresolved meaning: ' + ast['text']
    if op == 'not':
        return 'NOT (' + render_formula(ast['arg'], entities, predicates) + ')'
    if op in ('all', 'some'):
        return ('FOR ALL ' if op == 'all' else 'THERE EXISTS ') + ast['var'] + ': ' + render_formula(ast['body'], entities, predicates)
    words = {'and': 'AND', 'or': 'OR', 'implies': 'IMPLIES', 'iff': 'IF AND ONLY IF'}
    return '(' + render_formula(ast['left'], entities, predicates) + ') ' + words[op] + ' (' + render_formula(ast['right'], entities, predicates) + ')'
