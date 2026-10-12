"""Actual conditional FOL calculation for source-bound candidate interpretations."""
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

from hcl import quantified_logic
from hcl.kernel.types import Delta, HCLFailure, InferenceResult, OpResult, thaw
from hcl.semantics.alignment import render_formula
from hcl.semantics.frames import SemanticProfile


class ReadingLogicOperator:
    operation_id = 'logic.compare_semantic_readings'
    version = '1'

    def __init__(self, profile=None):
        self.profile = profile or SemanticProfile()

    @staticmethod
    def _failure(code, *, budget=False):
        return HCLFailure('BUDGET_EXHAUSTED' if budget else 'FAILED', 'semantic_solver', code,
                          'semantic_readings', 'The bounded formal computation could not complete safely.')

    def _solve(self, readings):
        payload = dict(schema='hcl-fol-worker-1', readings=readings, timeout_ms=self.profile.solver_timeout_ms,
                       cpu_seconds=self.profile.worker_cpu_seconds, memory_bytes=self.profile.worker_memory_bytes)
        encoded = json.dumps(payload).encode()
        if len(encoded) > 262144:
            raise self._failure('SOLVER_INPUT_LIMIT', budget=True)
        root = str(Path(__file__).resolve().parents[2])
        env = {'PATH': os.defpath, 'PYTHONPATH': root, 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
        try:
            process = subprocess.Popen([sys.executable, '-m', 'hcl.operators.fol_worker'],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       cwd=root, env=env)
            try:
                stdout, _ = process.communicate(encoded, timeout=self.profile.worker_wall_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise self._failure('SOLVER_WALL_LIMIT', budget=True) from None
        except OSError:
            raise self._failure('SOLVER_START_FAILURE') from None
        if process.returncode != 0:
            raise self._failure('SOLVER_PROCESS_LIMIT_OR_FAILURE', budget=process.returncode < 0)
        if len(stdout) > 1024*1024:
            raise self._failure('SOLVER_RESULT_LIMIT', budget=True)
        try:
            result = json.loads(stdout)
            if 'fatal' in result:
                code = result['fatal']
                if code not in ('RESOURCE_ISOLATION_UNAVAILABLE', 'SOLVER_UNAVAILABLE', 'SOLVER_RESOURCE_EXHAUSTED', 'SOLVER_WORKER_FAILURE'):
                    raise ValueError()
                raise self._failure(code, budget=code == 'SOLVER_RESOURCE_EXHAUSTED')
            if (result['schema'] != 'hcl-fol-worker-result-1' or not result['resource_limits_applied']
                    or result['classification_batches_completed'] != len(readings)
                    or [row['id'] for row in result['readings']] != [row['id'] for row in readings]):
                raise ValueError()
            return result
        except (ValueError, KeyError, TypeError):
            raise self._failure('INVALID_SOLVER_RESULT') from None

    def _validate_classification(self, result):
        """Labels must agree with actual consistency/entailment/refutation results."""
        if type(result) is not dict or 'status' not in result or 'label' not in result:
            raise self._failure('INVALID_SOLVER_RESULT')
        status, label = result['status'], result['label']
        if status == 'INVALID_FORMAL_INPUT':
            if label is not None:
                raise self._failure('INVALID_SOLVER_LABEL')
            return
        checks = []
        for name in ('consistency_check', 'entailment_check', 'refutation_check'):
            check = result.get(name)
            if check is None:
                checks.append(None)
            elif type(check) is dict and check.get('status') in ('EQUIVALENT', 'NOT_EQUIVALENT', 'UNKNOWN'):
                checks.append(check['status'])
            else:
                raise self._failure('INVALID_SOLVER_CHECK')
        consistency, entailment, refutation = checks
        if consistency == 'EQUIVALENT':
            expected_status, expected_label = 'INCONSISTENT_PREMISES', None
        elif consistency == 'UNKNOWN':
            expected_status, expected_label = 'UNKNOWN', None
        elif consistency == 'NOT_EQUIVALENT' and entailment and refutation:
            if 'UNKNOWN' in (entailment, refutation):
                expected_status, expected_label = 'UNKNOWN', None
            else:
                labels = {('EQUIVALENT', 'NOT_EQUIVALENT'): 'True',
                          ('NOT_EQUIVALENT', 'EQUIVALENT'): 'False',
                          ('NOT_EQUIVALENT', 'NOT_EQUIVALENT'): 'Uncertain'}
                expected_label = labels.get((entailment, refutation))
                expected_status = 'CLASSIFIED' if expected_label else 'SOLVER_RESULT_CONFLICT'
        else:
            raise self._failure('INVALID_SOLVER_CHECK')
        if (status, label) != (expected_status, expected_label):
            raise self._failure('SOLVER_LABEL_CHECK_MISMATCH')

    @staticmethod
    def checked_witness(premises, query, check, target, symbols, entities, predicates):
        witness = check.get('countermodel') if type(check) is dict else None
        if not witness or witness.get('status') != 'VERIFIED_FINITE_COUNTERMODEL':
            return None
        # equivalence checks use conjunction transformations. Validate the exact
        # original premise list and the correct original/negated query again.
        conclusion = query if target == 'QUERY_FALSE' else ('not', query)
        model = witness['model']
        verified = quantified_logic.check_countermodel(premises, conclusion, model)
        if not verified['is_countermodel']:
            raise HCLFailure('FAILED', 'semantic_solver', 'COUNTERMODEL_RECHECK_FAILED', 'countermodel',
                             'The returned model does not refute the intended formal target.')
        query_value = verified['conclusion'] if target == 'QUERY_FALSE' else not verified['conclusion']
        reverse_constants = {symbol: key for key, symbol in symbols['constants'].items()}
        reverse_predicates = {symbol: key for key, symbol in symbols['predicates'].items()}
        scenario = {'kind': 'GENERATED_FORMAL_SCENARIO_NOT_SOURCE_QUOTATION',
            'domain': list(model['domain']),
            'constant_assignments': [{'entity_id': reverse_constants[symbol],
                'source_id': entities[reverse_constants[symbol]]['source_id'],
                'label': entities[reverse_constants[symbol]]['label'], 'individual': value}
                for symbol, value in sorted(model['constants'].items())],
            'predicate_extensions': [{'predicate_id': reverse_predicates[symbol],
                'label': predicates[reverse_predicates[symbol]]['label'],
                'arity': predicates[reverse_predicates[symbol]]['arity'], 'extension': extension}
                for symbol, extension in sorted(model['predicates'].items())],
            'different_constants_may_corefer': True}
        # Round-trip the generated scenario, rather than trusting its prose labels.
        rebuilt = {'domain': scenario['domain'],
            'constants': {symbols['constants'][row['entity_id']]: row['individual'] for row in scenario['constant_assignments']},
            'predicates': {symbols['predicates'][row['predicate_id']]: row['extension'] for row in scenario['predicate_extensions']}}
        if rebuilt != model:
            raise HCLFailure('FAILED', 'semantic_solver', 'COUNTERMODEL_ROUNDTRIP_FAILED', 'countermodel',
                             'The generated scenario did not preserve the computed model.')
        return {'status': 'INDEPENDENTLY_CHECKED_FINITE_COUNTERMODEL', 'check_target': target,
                'model': model, 'premise_values': verified['premises'], 'query_value': query_value,
                'target_value': verified['conclusion'], 'scenario': scenario,
                'alignment': 'FORMAL_ROUNDTRIP_ONLY_NOT_SOURCE_SEMANTIC_CERTIFICATION'}

    def run(self, snapshot, issue, allowance, forest):
        if dict(forest.source_versions) != dict(snapshot.source_versions):
            raise self._failure('PARSE_SOURCE_VERSION_MISMATCH')
        if len(forest.readings) > allowance.max_local_evaluations:
            raise self._failure('CLASSIFICATION_BATCH_LIMIT', budget=True)
        executable = [reading for reading in forest.readings
                      if not {'OPAQUE_MEANING', 'FRAME_BRIDGE_REQUIRED', 'NO_FORMAL_PREMISES'} & set(reading.unresolved)]
        work = [{'id': reading.reading_id, 'premises': [p.formula for p in reading.premises],
                 'conclusion': reading.query.formula} for reading in executable]
        try:
            solved = self._solve(work) if work else {'readings': [], 'classification_batches_completed': 0,
                                                   'solver_checks_upper_bound': 0, 'solver_version': None}
        except HCLFailure as error:
            raise HCLFailure(error.status, error.diagnostic.stage, error.diagnostic.code, error.diagnostic.field_path,
                             error.diagnostic.message, resource_usage={
                                 'local_evaluations': None, 'classification_batches_reserved': len(work),
                                 'classification_batches_completed': None, 'solver_checks_upper_bound': 15*len(work),
                                 'local_work_completion_unknown': True}) from None
        by_id = {row['id']: row['result'] for row in solved['readings']}
        rows, unresolved = [], []
        frame_kinds = {frame.frame_id: frame.kind for frame in forest.frames}
        for reading in forest.readings:
            result = by_id.get(reading.reading_id, {'status': 'UNRESOLVED_COMPILATION', 'label': None})
            if reading in executable:
                self._validate_classification(result)
            if result['status'] not in ('CLASSIFIED', 'INCONSISTENT_PREMISES', 'UNKNOWN', 'SOLVER_RESULT_CONFLICT',
                                        'INVALID_FORMAL_INPUT', 'UNRESOLVED_COMPILATION'):
                raise self._failure('INVALID_SOLVER_STATUS')
            if result['status'] == 'CLASSIFIED' and result['label'] not in ('True', 'False', 'Uncertain'):
                raise self._failure('INVALID_SOLVER_LABEL')
            witnesses = []
            if reading in executable:
                premises = [quantified_logic.parse(p.formula) for p in reading.premises]
                query = quantified_logic.parse(reading.query.formula)
                for check, target in (('entailment_check', 'QUERY_FALSE'), ('refutation_check', 'QUERY_TRUE')):
                    try:
                        witness = self.checked_witness(premises, query, result.get(check), target,
                                                       forest.symbol_map, forest.entities, forest.predicates)
                    except (quantified_logic.FormulaError, ValueError, KeyError, TypeError):
                        raise self._failure('COUNTERMODEL_RECHECK_FAILED') from None
                    if witness:
                        witnesses.append(witness)
            if result['status'] != 'CLASSIFIED' or reading.unresolved:
                unresolved.append(reading.reading_id)
            rows.append({'id': reading.reading_id, 'frame': reading.frame_id, 'frame_kind': frame_kinds[reading.frame_id],
                         'assumptions': list(reading.assumptions),
                         'formal_premises': [p.formula for p in reading.premises], 'formal_query': reading.query.formula,
                         'status': result['status'], 'label': result['label'], 'checks': result,
                         'countermodels': witnesses,
                         'premise_readings': [render_formula(thaw(p.typed_ast), forest.entities, forest.predicates) for p in reading.premises],
                         'query_reading': render_formula(thaw(reading.query.typed_ast), forest.entities, forest.predicates),
                         'alignment': thaw(reading.alignment), 'unresolved': list(reading.unresolved),
                         'unparsed_segments': list(reading.unparsed_segments),
                         'premise_refs': [list(p.segment_ids) for p in reading.premises], 'query_refs': list(reading.query.segment_ids)})
        if any(row['status'] != 'CLASSIFIED' for row in rows):
            status, label = 'UNRESOLVED_READING', None
        elif len({row['label'] for row in rows}) == 1:
            status, label = 'AGREEMENT_ACROSS_SUPPLIED_READINGS', rows[0]['label']
        else:
            status, label = 'READING_DEPENDENT', None
            unresolved.extend(row['id'] for row in rows)
        values = {'status': status, 'label': label, 'readings': rows,
                  'semantic_certified': False, 'candidate_completeness': 'NOT_ESTABLISHED',
                  'model_evidence': forest.model_evidence, 'symbol_map': thaw(forest.symbol_map),
                  'entities': thaw(forest.entities), 'predicates': thaw(forest.predicates),
                  'propositions': [{'reading_id': reading.reading_id, 'meaning_id': proposition.meaning_id,
                                    'natural_reading': proposition.natural_reading,
                                    'typed_ast': thaw(proposition.typed_ast), 'frame': proposition.frame_id,
                                    'segment_ids': list(proposition.segment_ids), 'origin': proposition.origin,
                                    'formula': proposition.formula, 'time_constraints': [],
                                    'time_status': 'UNRESOLVED_UNLESS_EXPLICIT_IN_TYPED_AST',
                                    'alignment_refs': [reading.reading_id]}
                                   for reading in forest.readings for proposition in (*reading.premises, reading.query)],
                  'source_segments': [asdict(segment) for segment in forest.segments],
                  'frames': [asdict(frame) for frame in forest.frames],
                  'solver_profile': asdict(self.profile), 'solver_version': solved['solver_version']}
        identity = sha256(json.dumps([snapshot.session_id, snapshot.revision, issue.issue_id, values],
                                    ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
        environments = tuple('candidate-reading:' + identity + ':' + row['id'] for row in rows)
        result = InferenceResult('semantic-fol:' + identity, 'CONDITIONAL_FOL', values, environments,
                                 tuple(identity + ':' + p.meaning_id for r in forest.readings for p in r.premises),
                                 tuple(identity + ':' + row['id'] + ':' + witness['check_target']
                                       for row in rows for witness in row['countermodels']), snapshot.rule_version,
                                 'SUPPLIED_INTERPRETATIONS_ONLY_NOT_NL_WORLD_OR_PRIVATE_TRUTH')
        delta = Delta(snapshot.session_id, snapshot.principal, snapshot.revision, snapshot.access_epoch,
                      snapshot.rule_version, dict(snapshot.source_versions), (result,))
        return OpResult(self.operation_id, self.version, dict(snapshot.source_versions), ('append_inference',),
                        (result.result_id,), tuple(sorted(set(unresolved))),
                        {'local_evaluations': solved['classification_batches_completed'],
                         'local_evaluation_unit': 'classification_batch_not_individual_solver_check',
                         'classification_batches_started': len(work),
                         'classification_batches_completed': solved['classification_batches_completed'],
                         'solver_checks_upper_bound': solved['solver_checks_upper_bound']}, (), delta)
