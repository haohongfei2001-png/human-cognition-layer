"""Additive v5 source/host-bound normalized rational weight-domain proposals.

The fixed v1 cognitive model is computed unchanged. Target frameworks must
explicitly leave weights unknown; a separate domain declaration supplies only
conditional linear constraints, never membership, winners or user adoption.
"""
from dataclasses import replace
from hashlib import sha256
import json

from hcl.kernel.types import freeze, thaw
from hcl.memory import codec
from hcl.operators.agency import encoded, rational
from hcl.semantics.concept_version_compiler import digest, host_context
from hcl.semantics.joint_change_compiler import node_count
from hcl.semantics.judgment_compiler import JudgmentCompiler, ORIGINS

SCHEMA = 'hcl-judgment-candidates-5'


class WeightRegionCompiler(JudgmentCompiler):
    def compile(self, snapshot, segments, raw, allowance):
        try:
            return self._compile_weights(snapshot, segments, raw, allowance)
        except (ValueError, TypeError, KeyError, IndexError, StopIteration, RecursionError, OverflowError, ZeroDivisionError):
            raise self._invalid('weight_domains') from None

    def _compile_weights(self, snapshot, segments, raw, allowance):
        if type(raw) is not str or len(raw.encode()) > min(allowance.max_output_bytes, 1048576):
            raise self._limit('candidate_bytes')
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result: raise ValueError('duplicate field')
                result[key] = value
            return result
        data = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite value')))
        self._keys(data, 'schema models weight_domains')
        if data['schema'] != SCHEMA: raise ValueError('explicit v5 required')
        base = thaw(JudgmentCompiler().compile(snapshot, segments,
            json.dumps(dict(schema='hcl-judgment-candidates-1', models=data['models']), ensure_ascii=False), allowance))
        domains = data['weight_domains']
        if type(domains) is not list or not 1 <= len(domains) <= 4: raise ValueError('bounded weight domains required')
        models = {(m['mental']['source_id'], m['mental']['id']): m for m in base['models']}
        identities, targets = set(), set()
        compiled = []
        for domain in domains:
            self._keys(domain, 'id source_id model_id decision_id framework_id decision_rule constraints origin segment_ids')
            for key in ('id', 'source_id', 'model_id', 'decision_id', 'framework_id'): self._text(domain[key], 128)
            target = tuple(domain[k] for k in ('source_id', 'model_id', 'decision_id', 'framework_id'))
            if domain['id'] in identities or target in targets: raise ValueError('duplicate domain identity or framework target')
            identities.add(domain['id']); targets.add(target)
            model = models[target[:2]]
            decision = next(d for d in model['decisions'] if d['id'] == domain['decision_id'])
            framework = next(f for f in decision['frameworks'] if f['id'] == domain['framework_id'])
            if framework['weights'] is not None or framework['decision_rule'] != 'PARETO':
                raise ValueError('domain analysis must explicitly preserve unknown fixed weights')
            if domain['decision_rule'] not in ('EXPECTED', 'MAXIMIN'): raise ValueError('explicit scalar rule required')
            if domain['decision_rule'] == 'EXPECTED' and len(decision['scenarios']) > 1: raise ValueError('expected rule requires one scenario')
            ids = [d['id'] for d in decision['dimensions']]
            if len(ids) > 4: raise ValueError('at most four declared dimensions')
            allowed = set(framework['segment_ids']) | set(framework['origin']['segment_ids'])
            def refs(value):
                keys = self._strings(value, 64)
                if not keys or not set(keys) <= allowed: raise ValueError('weight declaration must cite its actual framework sources')
            refs(domain['segment_ids'])
            origin = domain['origin']
            self._keys(origin, 'kind declarer at frame_kind segment_ids')
            refs(origin['segment_ids']); self._text(origin['declarer'], 256)
            plan = next(p for p in model['mental']['plans'] if p['id'] == decision['plan_id'])
            if (origin['kind'] not in ORIGINS or type(origin['at']) is not int or not 0 <= origin['at'] <= plan['at']
                    or origin['frame_kind'] != model['mental']['frame_kind']): raise ValueError('invalid conditional domain provenance')
            constraints = domain['constraints']
            if type(constraints) is not list or len(constraints) > 16: raise ValueError('bounded linear constraints required')
            rows, seen = [], set()
            for row in constraints:
                self._keys(row, 'id coefficients relation rhs segment_ids')
                self._text(row['id'], 128); refs(row['segment_ids'])
                if row['id'] in seen: raise ValueError('duplicate constraint identity')
                seen.add(row['id'])
                if row['relation'] not in ('LE', 'LT', 'EQ') or type(row['coefficients']) is not dict or set(row['coefficients']) != set(ids):
                    raise ValueError('rational linear inequality required')
                rows.append(dict(row, coefficients={k: encoded(rational(row['coefficients'][k])) for k in ids}, rhs=encoded(rational(row['rhs']))))
            binding = dict(host=host_context(snapshot), source_versions=dict(snapshot.source_versions),
                target=list(target), at=plan['at'], actor=plan['actor'], frame_kind=model['mental']['frame_kind'],
                framework_origin=framework['origin'], source_bindings={k: base['source_bindings'][k] for k in sorted(allowed)})
            compiled.append(dict(domain, constraints=rows, dimensions=ids, normalization='NONNEGATIVE_SUM_ONE',
                binding=binding, domain_identity='weight-domain:'+digest([domain, binding]), adoption_authorized=False))
        return freeze(dict(schema=SCHEMA, base_program=base, weight_domains=compiled,
            source_versions=dict(snapshot.source_versions), host_context=host_context(snapshot),
            candidate=raw, candidate_identity=sha256(raw.encode()).hexdigest(), validation_units=node_count(data)))


def verify_weight_program(program, snapshot, allowance):
    from hcl.semantics.segments import SourceSegment
    from hcl.semantics.judgment_compiler import verify_program_bindings
    data = thaw(program)
    if data['host_context'] != host_context(snapshot) or data['source_versions'] != dict(snapshot.source_versions):
        raise ValueError('weight host/source scope differs')
    verify_program_bindings(data['base_program'], snapshot, allowance)
    segments = tuple(SourceSegment(**row) for row in data['base_program']['segments'])
    expected = WeightRegionCompiler().compile(snapshot, segments, data['candidate'], replace(allowance, max_output_bytes=1048576))
    if codec.canonical(thaw(expected)) != codec.canonical(data): raise ValueError('weight proposal or provenance changed')
