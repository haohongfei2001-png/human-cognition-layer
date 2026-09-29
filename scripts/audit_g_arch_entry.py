"""Provider-free source-first audit of the single G-ARCH operational artifact."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_g_arch_entry_once import digest

ROOT = Path('reports/HCL_G_ARCH_ENTRY_36551001816')
PACKAGE = Path('reports/HCL_G_ARCH_ENTRY_PACKAGE.json')
RUN = ROOT / 'raw-run.json'
PREFLIGHT = ROOT / 'provider-free-preflight.json'
ARTIFACT_ID = 11024906326
ARTIFACT_DIGEST = 'sha256:6e241b96f9466aeb0cd0d9b00f1d394ceaee44c09ff45b61fe9aac682855cc42'
SHA = '5f14b829ee6247389bc326eb14736342723de2d0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    package = json.loads(PACKAGE.read_text())
    run = json.loads(RUN.read_text())
    preflight = json.loads(PREFLIGHT.read_text())
    assert run['sha'] == SHA and run['run_id'] == '36551001816' and run['run_attempt'] == '1'
    assert run['package_sha256'] == digest(package) == preflight['package_sha256']
    assert run['runtime_sha256'] == package['runtime_sha256'] == preflight['runtime_sha256']
    assert preflight['status'] == 'PASS_PROVIDER_FREE' and preflight['provider_calls'] == 0
    assert run['status'] == 'PIPELINE_COMPLETED_REQUIRES_SOURCE_FIRST_REVIEW'
    assert run['provider_calls'] == len(run['attempts']) == 2 and run['retries'] == 0
    assert run['budget_state'] == 'CLOSED_NO_TRANSFER_NO_RERUN'
    assert run['authorization_remaining_usd'] == 0
    assert run['conservative_guard_spend_usd'] <= run['budget_cap_usd'] == package['budget_cap_usd'] == 0.04
    assert [a['phase'] for a in run['attempts']] == ['extraction', 'final']
    assert all(a['actual_model_id'] == 'deepseek-flash' for a in run['attempts'])
    assert all(a['response_raw']['choices'][0]['finish_reason'] == 'stop' for a in run['attempts'])
    assert all(a['usage']['completion_tokens'] <= a['request_raw']['max_tokens'] for a in run['attempts'])
    source = package['source']
    raw = json.loads(run['attempts'][0]['response_raw']['choices'][0]['message']['content'])
    candidates = raw['candidates']
    assert len(candidates) == 6
    anchors = []
    for proposal, diagnostic in zip(candidates, run['preparation']['semantic_diagnostics']):
        quote = proposal['quote']
        assert proposal['source_id'] == package['source_id']
        assert source.count(quote) == 1 and diagnostic['quotation'] == 'EXACT'
        assert diagnostic['semantic_support'] == 'BOUNDED_LITERAL_FORM'
        derived = source.index(quote)
        repair = diagnostic['source_derived_anchor']
        if proposal['start'] != derived:
            assert repair == dict(submitted_start=proposal['start'], derived_start=derived,
                rule='UNIQUE_EXACT_SOURCE_QUOTE_OVERRIDES_SUPPLIED_OFFSET')
        else:
            assert repair is None
        anchors.append(dict(source_id=proposal['source_id'], original_quote=quote,
            submitted_start=proposal['start'], derived_start=derived,
            exact_unique=True, semantic_support=diagnostic['semantic_support']))
    final_messages = run['preparation']['actual_final_messages']
    assert run['attempts'][1]['request_raw']['messages'] == final_messages
    assert len(final_messages) == 3
    final_state = run['preparation']['cognition_state']
    assert final_state['role_status'] == 'REPORTED_OCCUPANT' and final_state['local_tension']
    assert [r['label'] for r in final_state['current_self_descriptions']] == ['careful']
    assert [r['label'] for r in final_state['other_identity_attributions']] == ['careless']
    assert [r['endorsement'] for r in final_state['requirement_endorsements']] == ['REJECTS']
    assert 'REPORTED_OCCUPANT' in final_messages[1]['content']
    actual_final = json.loads(run['attempts'][1]['response_raw']['choices'][0]['message']['content'])
    assert actual_final == run['final_answer'] and set(actual_final) == set(package['final_fields'])
    usage = [a['usage'] for a in run['attempts']]
    assert sum(a['rated_peak_cost_usd'] for a in run['attempts']) == run['rated_peak_spend_usd']
    assert sum(a['conservative_guard_cost_usd'] for a in run['attempts']) == run['conservative_guard_spend_usd']
    return dict(schema='hcl-g-arch-entry-source-first-audit-v1',
        run_id=run['run_id'], sha=SHA, artifact_id=ARTIFACT_ID,
        artifact_digest=ARTIFACT_DIGEST,
        package_sha256=run['package_sha256'], runtime_sha256=run['runtime_sha256'],
        raw_receipt_sha256=sha(RUN), provider_free_preflight_sha256=sha(PREFLIGHT),
        frozen_package_file_sha256=sha(PACKAGE),
        raw_extraction_anchors=anchors, source_derived_offset_repairs=sum(
            a['submitted_start'] != a['derived_start'] for a in anchors),
        final_model_input_equals_prepared_state=True,
        grounded_role_status=final_state['role_status'],
        final_output_fields=sorted(actual_final),
        model_ids=[a['actual_model_id'] for a in run['attempts']],
        usages=usage, provider_calls=2, retries=0,
        rated_peak_cost_usd=run['rated_peak_spend_usd'],
        estimated_provider_cost_usd=run['estimated_provider_spend_usd'],
        conservative_guard_cost_usd=run['conservative_guard_spend_usd'],
        actual_invoice_cost_usd=None, cap_usd=run['budget_cap_usd'],
        authorization_remaining_usd=0, budget_state=run['budget_state'],
        operational_input='PASS_BOUNDED_AUTHORED_FUNCTIONAL_SMOKE',
        independent_efficacy='UNTESTED',
        historical_e03='FAILED_CLOSED_UNCHANGED',
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'source-first-audit.json')
    target.write_text(json.dumps(audit(), ensure_ascii=False, indent=2) + '\n')
