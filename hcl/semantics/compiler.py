"""General source-bound typed-tree compilation, not a text-to-answer lookup.

A model supplies candidate structure. This compiler checks references, frames,
lexical binding and coverage, then serializes safe trees for the actual solver.
It does not certify that the model understood the source, even on valid JSON.
"""
import json

from hcl.kernel.types import HCLFailure
from .alignment import judgment
from .frames import Frame, ParseForest, Proposition, Reading, SemanticProfile


class SemanticCompiler:
    def __init__(self, profile=None):
        self.profile = profile or SemanticProfile()

    @staticmethod
    def _invalid(field='candidate'):
        return HCLFailure('INVALID_REQUEST', 'semantic_compile', 'INVALID_SEMANTIC_CANDIDATE', field,
                          'The proposed interpretation does not satisfy the typed source-bound contract.')

    @staticmethod
    def _limit(field):
        return HCLFailure('BUDGET_EXHAUSTED', 'semantic_compile', 'SEMANTIC_COMPILE_LIMIT', field,
                          'The candidate compilation exceeds its declared bounded profile.')

    def _keys(self, row, required):
        if type(row) is not dict or set(row) != set(required.split()):
            raise self._invalid()

    def _text(self, value, maximum=2048):
        if type(value) is not str or not value.strip() or len(value) > maximum:
            raise self._invalid()
        try:
            value.encode('utf-8')
        except UnicodeEncodeError:
            raise self._invalid() from None
        return value

    def _strings(self, value, maximum=128, unique=True):
        if type(value) is not list or len(value) > maximum:
            raise self._invalid()
        for item in value:
            self._text(item)
        if unique and len(set(value)) != len(value):
            raise self._invalid()
        return tuple(value)

    def compile(self, snapshot, segments, raw_candidate, allowance):
        """Pure proposal compilation; only Engine can commit its downstream result."""
        try:
            return self._compile(snapshot, segments, raw_candidate, allowance)
        except (TypeError, KeyError, IndexError, ValueError, RecursionError):
            raise self._invalid() from None

    def _compile(self, snapshot, segments, raw_candidate, allowance):
        try:
            if type(raw_candidate) is not str or len(raw_candidate.encode('utf-8')) > allowance.max_output_bytes:
                raise self._limit('candidate_bytes')
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise self._invalid('duplicate_json_field')
                    result[key] = value
                return result
            data = json.loads(raw_candidate, object_pairs_hook=unique,
                              parse_constant=lambda _: (_ for _ in ()).throw(self._invalid()))
        except (ValueError, TypeError, RecursionError, UnicodeEncodeError):
            raise self._invalid('candidate_json') from None
        self._keys(data, 'schema frames entities predicates readings')
        if data['schema'] != 'hcl-semantic-candidates-1':
            raise self._invalid('schema')
        by_segment = {segment.segment_id: segment for segment in segments}
        if len(by_segment) != len(segments):
            raise self._invalid('segments')
        source_segments = {key for key, segment in by_segment.items() if segment.kind == 'SOURCE'}
        if not source_segments:
            raise HCLFailure('NEEDS_EVIDENCE', 'semantic_compile', 'NO_SEMANTIC_SOURCES', 'source_handles',
                             'This semantic computation needs an authorized original source.')

        def refs(raw, *, source_id=None):
            result = self._strings(raw)
            if any(key not in by_segment for key in result):
                raise self._invalid('segment_ids')
            if source_id is not None and any(by_segment[key].source_id != source_id for key in result):
                raise self._invalid('entity_source_binding')
            return result

        for field, limit in (('frames', self.profile.max_frames), ('entities', self.profile.max_entities),
                             ('predicates', self.profile.max_predicates), ('readings', self.profile.max_readings)):
            if type(data[field]) is not list or (field in ('frames', 'readings') and not data[field]):
                raise self._invalid(field)
            if len(data[field]) > limit:
                raise self._limit(field)
        frame_map = {}
        kinds = {'SOURCE_DISCOURSE', 'QUOTATION', 'HYPOTHETICAL', 'COUNTERFACTUAL', 'INTERPRETATION'}
        for row in data['frames']:
            self._keys(row, 'id kind parent segment_ids')
            key = self._text(row['id'], 128)
            if key in frame_map or row['kind'] not in kinds or (row['parent'] is not None and type(row['parent']) is not str):
                raise self._invalid('frame')
            evidence = refs(row['segment_ids'])
            if not evidence:
                raise self._invalid('frame.segment_ids')
            frame_map[key] = Frame(key, row['kind'], row['parent'], evidence)
        for frame in frame_map.values():
            seen = set()
            current = frame.frame_id
            while current is not None:
                if current in seen or current not in frame_map:
                    raise self._invalid('frame_parent')
                seen.add(current)
                current = frame_map[current].parent_id
        entities, predicates = {}, {}
        for row in data['entities']:
            self._keys(row, 'id label source_id segment_ids')
            key = self._text(row['id'], 128)
            self._text(row['label'], 256)
            if key in entities or type(row['source_id']) is not str or row['source_id'] not in snapshot.source_versions:
                raise self._invalid('entities')
            if not refs(row['segment_ids'], source_id=row['source_id']):
                raise self._invalid('entity.segment_ids')
            entities[key] = row
        for row in data['predicates']:
            self._keys(row, 'id label arity segment_ids')
            key = self._text(row['id'], 128)
            self._text(row['label'], 256)
            if key in predicates or type(row['arity']) is not int or row['arity'] not in (1, 2):
                raise self._invalid('predicates')
            if not refs(row['segment_ids']):
                raise self._invalid('predicate.segment_ids')
            predicates[key] = row
        constant_map = {key: 'abcdefghijklmnopqr'[index] for index, key in enumerate(sorted(entities))}
        predicate_map = {key: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[index] for index, key in enumerate(sorted(predicates))}
        readings, reading_ids, meanings = [], set(), set()
        total_formula_chars = 0
        for row in data['readings']:
            self._keys(row, 'id frame assumptions premises query unparsed_segments alignment')
            key = self._text(row['id'], 128)
            if key in reading_ids or row['frame'] not in frame_map:
                raise self._invalid('reading')
            reading_ids.add(key)
            assumptions = self._strings(row['assumptions'])
            if type(row['premises']) is not list:
                raise self._invalid('premises')
            if len(row['premises']) > min(16, allowance.max_premises):
                raise self._limit('premises')
            state = {'nodes': 0, 'opaque': False}
            unresolved = []
            used_segments = set()

            def tree(node, bound, depth=0):
                state['nodes'] += 1
                if state['nodes'] > self.profile.max_ast_nodes or depth > self.profile.max_ast_depth:
                    raise self._limit('typed_ast')
                if type(node) is not dict or type(node.get('op')) is not str:
                    raise self._invalid('typed_ast')
                op = node['op']
                if op == 'opaque':
                    self._keys(node, 'op text reason')
                    self._text(node['text'])
                    self._text(node['reason'])
                    state['opaque'] = True
                    return None
                if op == 'atom':
                    self._keys(node, 'op predicate args')
                    predicate = node['predicate']
                    if type(predicate) is not str or predicate not in predicates or type(node['args']) is not list:
                        raise self._invalid('atom')
                    if len(node['args']) != predicates[predicate]['arity']:
                        raise self._invalid('predicate_arity')
                    terms = []
                    for term in node['args']:
                        if type(term) is not dict:
                            raise self._invalid('term')
                        if set(term) == {'entity'} and type(term['entity']) is str and term['entity'] in constant_map:
                            terms.append(constant_map[term['entity']])
                        elif set(term) == {'var'} and type(term['var']) is str and term['var'] in bound:
                            terms.append(bound[term['var']])
                        else:
                            raise self._invalid('unbound_term')
                    return predicate_map[predicate] + ''.join(terms)
                if op == 'not':
                    self._keys(node, 'op arg')
                    inner = tree(node['arg'], bound, depth+1)
                    return '¬' + inner if inner is not None else None
                if op in ('all', 'some'):
                    self._keys(node, 'op var body')
                    variable = self._text(node['var'], 128)
                    if len(bound) >= 8 and variable not in bound:
                        raise self._limit('bound_variables')
                    symbol = bound.get(variable, 'stuvwxyz'[len(bound)] if len(bound) < 8 else 'z')
                    inner = tree(node['body'], dict(bound, **{variable: symbol}), depth+1)
                    return ('∀' if op == 'all' else '∃') + symbol + inner if inner is not None else None
                if op in ('and', 'or', 'implies', 'iff'):
                    self._keys(node, 'op left right')
                    left, right = tree(node['left'], bound, depth+1), tree(node['right'], bound, depth+1)
                    return '(' + left + {'and':'∧', 'or':'∨', 'implies':'→', 'iff':'↔'}[op] + right + ')' if left is not None and right is not None else None
                raise self._invalid('ast_operation')

            def proposition(item, query=False):
                self._keys(item, 'id natural_reading ast frame segment_ids origin')
                meaning = self._text(item['id'], 128)
                if meaning in meanings or item['frame'] not in frame_map:
                    raise self._invalid('meaning_identity_or_frame')
                meanings.add(meaning)
                self._text(item['natural_reading'])
                evidence = refs(item['segment_ids'])
                origin = item['origin']
                if origin not in ('DIRECT_REPORT', 'INTERPRETATION', 'BACKGROUND_PRIOR', 'ASSUMPTION'):
                    raise self._invalid('origin')
                if query:
                    if not any(by_segment[ref].kind == 'QUESTION' for ref in evidence):
                        raise self._invalid('query_anchor')
                elif origin in ('DIRECT_REPORT', 'INTERPRETATION'):
                    if not evidence or any(by_segment[ref].kind != 'SOURCE' for ref in evidence):
                        raise self._invalid('premise_source_anchor')
                elif not assumptions:
                    raise self._invalid('unlabelled_assumption')
                used_segments.update(evidence)
                if item['frame'] != row['frame']:
                    unresolved.append('FRAME_BRIDGE_REQUIRED')
                formula = tree(item['ast'], {})
                return Proposition(meaning, item['natural_reading'], item['ast'], item['frame'], evidence, origin, formula)

            premises = tuple(proposition(item) for item in row['premises'])
            query = proposition(row['query'], True)
            if not premises:
                unresolved.append('NO_FORMAL_PREMISES')
            if state['opaque']:
                unresolved.append('OPAQUE_MEANING')
            unparsed = set(refs(row['unparsed_segments']))
            if not unparsed <= source_segments:
                raise self._invalid('unparsed_segments')
            unparsed.update(source_segments - used_segments)
            if unparsed:
                unresolved.append('SOURCE_COVERAGE_UNRESOLVED')
            self._keys(row['alignment'], 'judgment explanation')
            if row['alignment']['judgment'] not in ('SUPPORTED', 'UNRESOLVED', 'CHALLENGED'):
                raise self._invalid('alignment')
            self._text(row['alignment']['explanation'])
            if row['alignment']['judgment'] != 'SUPPORTED':
                unresolved.append('SEMANTIC_ALIGNMENT_UNRESOLVED')
            formulas = tuple(p.formula for p in (*premises, query) if p.formula is not None)
            total_formula_chars += sum(map(len, formulas))
            if any(len(formula) > 4000 for formula in formulas) or total_formula_chars > allowance.max_formula_chars:
                raise self._limit('formula_chars')
            readings.append(Reading(key, row['frame'], assumptions, premises, query, tuple(sorted(unparsed)),
                                    tuple(sorted(set(unresolved))), judgment(row['alignment']['judgment'],
                                    row['alignment']['explanation'], unresolved_segments=sorted(unparsed))))
        if len(readings) > allowance.max_local_evaluations:
            raise self._limit('classification_batches')
        return ParseForest(tuple(readings), tuple(frame_map.values()), entities, predicates,
                           {'constants': constant_map, 'predicates': predicate_map}, tuple(segments), dict(snapshot.source_versions))
