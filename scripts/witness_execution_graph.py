"""H03 ordinary-source correction across actual conditional graph edges."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition.execution_graph import CognitiveExecutionGraph
from tests.test_v1_wave_h03 import SOURCE, CORRECTED, QUERY


def witness():
    graph = CognitiveExecutionGraph()
    graph.put_source('team-scene', SOURCE)
    before = graph.prepare_graph(QUERY, source_id='team-scene')
    before_input = before.messages(graph)
    graph.put_source('club-scene', SOURCE.replace('team', 'club'))
    club_query = QUERY.replace('team', 'club')
    club = graph.prepare_graph(club_query, source_id='club-scene')
    club_input = club.messages(graph)
    invalidated = graph.revise_source('team-scene', CORRECTED,
        kind='ANALYST_SOURCE_CORRECTION')
    after = graph.prepare_graph(QUERY, source_id='team-scene')
    final_input = after.messages(graph)
    assert set(before.claim_ids) & invalidated
    assert before.payload['nodes']['plan']['subjective_feasibility'] == 'SUPPORTED_UNDER_REPORTED_BELIEFS'
    assert after.payload['nodes']['plan']['subjective_feasibility'] == 'CONTRADICTED_UNDER_REPORTED_BELIEFS'
    assert before.payload['nodes']['relationship']['source_view']['conditional_alternatives'] == ['INFORMATION_GAP']
    assert after.payload['nodes']['relationship']['source_view']['conditional_alternatives'] == []
    assert club.messages(graph) == club_input
    assert graph.prepare_graph(club_query, source_id='club-scene') is club
    return dict(schema='hcl-h03-positive-witness-v1',
        capability_delta='One ordinary source correction revises a self-reported belief, a conditional plan check, the plan-expectation dependency and a source-linked relationship interpretation through actual evidence claims; an independent source is reused.',
        ordinary_source_before=SOURCE, ordinary_source_after=CORRECTED,
        ordinary_question=QUERY, before=before.payload, after=after.payload,
        invalidated_claim_ids=sorted(invalidated),
        actual_model_input_before=before_input, actual_final_model_input=final_input,
        unrelated_actual_model_input=club_input,
        execution_counts={'team': graph.graph_executions[(QUERY, 'team-scene', None)],
            'club': graph.graph_executions[(club_query, 'club-scene', None)]},
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0,
        provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_H03_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, separators=(',', ':')) + '\n')
