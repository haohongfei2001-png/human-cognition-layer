"""Local exact operations. No natural-language formalization or providers."""
import hashlib
import json
from .context import ConditionalToolResult


def execute_tool(request, source, perspectives, *, viewer, event_time, knowledge_cutoff):
    cid = request.capability_id
    inputs = dict(request.inputs)
    digest = hashlib.sha256(source.raw_text.encode()).hexdigest()
    provenance = {'source_event_id': source.event_id, 'source_id': source.source_id,
                  'source_sha256': digest, 'valid_time': source.valid_time,
                  'recorded_at': source.recorded_at}
    if cid == 'causal':
        from hcl.v09 import CausalModel, HCLV09Runtime
        model = inputs['model']
        if not isinstance(model, CausalModel) or model.source_event_id != source.event_id:
            raise ValueError('source-bound typed causal model required')
        runtime = HCLV09Runtime(perspectives)
        runtime.ingest_model(model)
        result = runtime.counterfactual(model.model_id, inputs['target'],
            observations=inputs.get('observations'), interventions=inputs.get('interventions'),
            viewer_agent_id=viewer, event_time=event_time, knowledge_cutoff=knowledge_cutoff)
        assumptions = {'model': model.as_dict(), 'observations': inputs.get('observations', {}),
                       'interventions': inputs.get('interventions', {})}
    elif cid == 'argumentation':
        from hcl.v10 import ArgumentFramework, HCLV10Runtime
        graph = inputs['framework']
        if not isinstance(graph, ArgumentFramework) or graph.source_event_id != source.event_id:
            raise ValueError('source-bound typed framework required')
        runtime = HCLV10Runtime(perspectives)
        runtime.ingest_framework(graph)
        result = runtime.analyse(graph.framework_id, inputs.get('semantics', 'grounded'),
            inputs.get('target'), viewer_agent_id=viewer, event_time=event_time, knowledge_cutoff=knowledge_cutoff)
        assumptions = {'framework': graph.as_dict(), 'semantics': inputs.get('semantics', 'grounded')}
    else:
        from hcl.quantified_logic import equivalent, find_countermodel, check_countermodel, parse
        from hcl.argument_readings import compare_readings
        if source.metadata.get('formal_scope') != 'EXPLICIT_FORMAL_INPUT':
            raise ValueError('explicit formal source scope required')
        timeout = inputs.get('timeout_ms', 500)
        if type(timeout) is not int or not 1 <= timeout <= 2000:
            raise ValueError('bounded solver timeout required')
        assumptions = inputs
        # Exact anchoring is necessary, not proof of NL interpretation.
        if cid == 'formal_reading':
            readings = inputs['readings']
            if not isinstance(readings, list) or not 1 <= len(readings) <= 4:
                raise ValueError('at most four supplied readings')
            formulas = [f for row in readings for f in row['premises'] + [row['conclusion']]]
            if any(row['source_sha256'] != digest for row in readings):
                raise ValueError('reading source digest mismatch')
        elif cid == 'formal_verifier':
            formulas = [inputs['left'], inputs['right']]
        else:
            formulas = inputs['premises'] + [inputs['conclusion']]
            if not 1 <= len(inputs['premises']) <= 16:
                raise ValueError('bounded explicit premises required')
        if any(not isinstance(f, str) or f not in source.raw_text for f in formulas):
            raise ValueError('formula missing exact source anchor')
        if len(json.dumps(inputs, ensure_ascii=False)) > 16000:
            raise ValueError('formal input size cap')
        if cid == 'formal_reading':
            result = compare_readings(inputs['readings'], timeout)
        elif cid == 'formal_verifier':
            result = equivalent(parse(inputs['left']), parse(inputs['right']), timeout)
        elif cid == 'countermodel':
            if 'witness' in inputs:
                result = check_countermodel([parse(f) for f in inputs['premises']], parse(inputs['conclusion']), inputs['witness'])
            else:
                result = find_countermodel([parse(f) for f in inputs['premises']], parse(inputs['conclusion']), inputs.get('domain_size', 2), timeout)
        else:
            raise ValueError('unknown tool')
    return ConditionalToolResult(cid, result.get('status', 'COMPUTED'), assumptions, result, provenance)
