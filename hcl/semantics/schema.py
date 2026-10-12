"""Candidate JSON Schema supplied on the real gateway wire, never answer labels."""


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def ref(name):
    return {'$ref': '#/$defs/' + name}


TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 2048}
LABEL = {'type': 'string', 'minLength': 1, 'maxLength': 256}
ID = {'type': 'string', 'minLength': 1, 'maxLength': 128}
REFS = {'type': 'array', 'items': ID, 'maxItems': 128, 'uniqueItems': True}
AST = {'oneOf': [
    obj({'op': {'const': 'atom'}, 'predicate': ID, 'args': {'type': 'array', 'minItems': 1, 'maxItems': 2,
         'items': {'oneOf': [obj({'entity': ID}), obj({'var': ID})]}}}),
    obj({'op': {'const': 'not'}, 'arg': ref('ast')}),
    obj({'op': {'enum': ['and', 'or', 'implies', 'iff']}, 'left': ref('ast'), 'right': ref('ast')}),
    obj({'op': {'enum': ['all', 'some']}, 'var': ID, 'body': ref('ast')}),
    obj({'op': {'const': 'opaque'}, 'text': TEXT, 'reason': TEXT}),
]}
PROPOSITION = obj({'id': ID, 'natural_reading': TEXT, 'ast': ref('ast'), 'frame': ID,
                   'segment_ids': REFS, 'origin': {'enum': ['DIRECT_REPORT', 'INTERPRETATION', 'BACKGROUND_PRIOR', 'ASSUMPTION']}})
CANDIDATE_SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    **obj({'schema': {'const': 'hcl-semantic-candidates-1'},
        'frames': {'type': 'array', 'minItems': 1, 'maxItems': 128, 'items': obj({
            'id': ID, 'kind': {'enum': ['SOURCE_DISCOURSE', 'QUOTATION', 'HYPOTHETICAL', 'COUNTERFACTUAL', 'INTERPRETATION']},
            'parent': {'anyOf': [ID, {'type': 'null'}]}, 'segment_ids': REFS})},
        'entities': {'type': 'array', 'maxItems': 18, 'items': obj({
            'id': ID, 'label': LABEL, 'source_id': ID, 'segment_ids': REFS})},
        'predicates': {'type': 'array', 'maxItems': 26, 'items': obj({
            'id': ID, 'label': LABEL, 'arity': {'type': 'integer', 'enum': [1, 2]}, 'segment_ids': REFS})},
        'readings': {'type': 'array', 'minItems': 1, 'maxItems': 64, 'items': obj({
            'id': ID, 'frame': ID, 'assumptions': {'type': 'array', 'items': TEXT, 'maxItems': 128, 'uniqueItems': True},
            'premises': {'type': 'array', 'maxItems': 16, 'items': ref('proposition')},
            'query': ref('proposition'), 'unparsed_segments': REFS,
            'alignment': obj({'judgment': {'enum': ['SUPPORTED', 'UNRESOLVED', 'CHALLENGED']}, 'explanation': TEXT})})}}),
    '$defs': {'ast': AST, 'proposition': PROPOSITION},
}
