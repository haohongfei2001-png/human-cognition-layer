"""Optional source-entry blockers with immutable consumed smoke evidence."""
import hashlib
import json
from pathlib import Path
from scripts import development_semantic_bridge_contract_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = 'f5f48ad552fae28d6d3141cb1c73771df57a1b16'
PREVIOUS_RUNTIME = 'a3ace7e929e46a1aebd6cc5706c549abf930189fd032c54ab31298e3742b3672'
CURRENT_RUNTIME = '7bbbb74b9877f108bf8052cc252d588302a820f0b8d5d17a9177c76019def12b'
CONSUMED_CNY_RUNTIME = previous.CONSUMED_CNY_RUNTIME
PREVIOUS_FILES = {'hcl/cognition/deepseek_metered.py': 'd2d60d5c2456f91857deae88a361d9468d3acae429f53428b6f35c1f8b919fec', 'hcl/cognition/universal_entry.py': 'bde140aefa5d97798d95cb99ff3f84c5d1ef56c504cd08457dac510000310d0e'}
ADDED_RUNTIME_FILES = ('hcl/cognition/entry_readiness.py',)
REVIEWED_FILES = {'hcl/cognition/deepseek_metered.py': 'c0ffb14f24e3c703cc8703e2d0f0c1b5502a1b6cd8cb81ce80f2639a73e69e69', 'hcl/cognition/universal_entry.py': 'e72033bbb9df4539982f04a58c4ed11dccc6404f66e90fe9cfdf04b4dc88d7a3', 'hcl/cognition/entry_readiness.py': 'd41ddf97f4d6d94a53dfd999b940c6d28dc525f39ae077610b2becdb2592605a'}
PINS = Path('reports/HCL_ENTRY_READINESS_HISTORY_PINS.json')
PINS_SHA256 = '680fbaacd9b03b44bd8b3667e9f568995030c4d23e93244dbb10363a556ce253'
REPORT = Path('reports/HCL_ENTRY_READINESS_AMENDMENT.json')
apply_reviewed_planner_contract = previous.apply_reviewed_planner_contract


def digest(raw): return hashlib.sha256(raw).hexdigest()


def validate_preserved_history():
    previous.validate_preserved_history()
    raw=PINS.read_bytes()
    if digest(raw)!=PINS_SHA256: raise ValueError('historical pin manifest drift')
    manifest=json.loads(raw)
    if manifest['baseline_commit']!=BASELINE: raise ValueError('historical amendment baseline drift')
    for name,expected in manifest['files_sha256'].items():
        if digest(Path(name).read_bytes())!=expected: raise ValueError('historical amendment or consumed evidence changed')
    return True


def expected_report():
    return dict(schema='hcl-entry-readiness-amendment-v1', baseline_commit=BASELINE,
        previous_hcl_runtime_sha256=PREVIOUS_RUNTIME, amended_hcl_runtime_sha256=CURRENT_RUNTIME,
        changed_runtime_files=sorted(REVIEWED_FILES), added_runtime_files=list(ADDED_RUNTIME_FILES),
        reason='OPTIONAL_SOURCE_VERSION_BOUND_NECESSARY_LITERAL_ENTRY_BLOCKERS',
        blocker_capabilities=['B02','D02'], same_parser_regex_objects_reused=True,
        native_views_prerun=False, native_receipts_created_by_hints=False,
        no_blocker_certifies_readiness=False, automatic_rerouting=False,
        source_version_bound=True, source_text_changed=False, native_parser_or_results_changed=False,
        optional_metadata_all_or_none=True, original_messages_preserved_on_capacity_omission=True,
        pure_request_serializer_shared_with_existing_port=True, serialization_touches_ledger=False,
        original_no_hint_request_hash_preserved=True, planning_tokens=16384, answer_tokens=8192,
        maximum_request_bytes=36000, provider_phases_changed=False, automatic_retry=False,
        mandatory_native_result_preserved=True, source_snapshot_guard_preserved=True,
        historical_executors_unchanged=True, historical_grants_reopened=False,
        historical_answers_rescored=False, provider_calls=0, provider_spend_cny=0,
        authorized_additional_calls=0, model_selection_improvement_verified=False,
        answer_quality_improvement_claimed=False, longmemeval='SEALED_NOT_ACCESSED')


def validate_current(*, current_digest=None):
    validate_preserved_history()
    files={str(path):digest(path.read_bytes()) for path in Path('hcl').rglob('*.py')}
    if any(files.get(name)!=expected for name,expected in REVIEWED_FILES.items()):
        raise ValueError('unrelated runtime outside reviewed scope changed')
    restored=dict(files,**PREVIOUS_FILES)
    for name in ADDED_RUNTIME_FILES: restored.pop(name,None)
    if digest(json.dumps(restored,sort_keys=True,separators=(',',':')).encode())!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    if runtime_digest()!=CURRENT_RUNTIME or current_digest is not None and current_digest!=CURRENT_RUNTIME:
        raise ValueError('entry readiness amendment drift')
    if json.loads(REPORT.read_text())!=expected_report(): raise ValueError('entry readiness amendment drift')
    return True


if __name__=='__main__':
    validate_current()
    print('ENTRY_READINESS_AND_CLOSED_HISTORY_PASS')
