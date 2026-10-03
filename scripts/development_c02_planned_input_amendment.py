"""Bounded planned C02 structured input; fixed native tools and prior evidence stay frozen."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_llm_routing_execution_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_C02_PLANNED_INPUT_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_llm_routing_execution_amendment.py': 'c95e1492250309b3f22ecde1aae5030830424105770e2ae9f6c34ad3a78a49e4', 'reports/HCL_LLM_ROUTING_EXECUTION_AMENDMENT.json': '60f14dbb08507eaed35be0716e95d2c9d169ef8f5f19e346821195400d6c556c', 'docs/HCL_LLM_ROUTING_EXECUTION.md': '5d82993f289133a7f81a68dc21d2c24105fbc8949e0a9d31785346211f927ed1', 'reports/HCL_LLM_ROUTING_EXECUTION_VALIDATION.json': 'f97e0a4cea8efad6bfedc3414ab668faf37cfd88295927dae96649844a580acf', 'reports/HCL_LLM_ROUTING_EXECUTION_WITNESS.json': '2a61517ffc95a4c6cebaadd869250103cc11581a6e64d77dcefa3eda833758b7'})
PREVIOUS_FILES={'hcl/cognition/retained.py': '2213db2447405fb59355d42ab9538fc58852311b0ad7d854713fdd2f2b08ccc6', 'hcl/cognition/universal_entry.py': 'bda1ad2e8257087634fb910da3f802f04dea8eb82a13e3ee59f68f1d77aab3e9', 'hcl/cognition/capability_catalog.py': '0ef420e550bccb340e309460a9e328cd3ee649dbe51ec59b7d1b9cc4ad64ce3f'}
REVIEWED_FILES={'hcl/cognition/retained.py': 'f83240579ca0e8063d87903f273679a932be2360bc66c764986c0cce5560527e', 'hcl/cognition/universal_entry.py': '86220045affc5dcd961fb20f8c2f09fdee42f9d9af872e1ed561f0db40c29ca2', 'hcl/cognition/capability_catalog.py': '27823a49c18d84d0851bf7f828a94857cc5c9c74caf73cf9ca2c2ba7e8fdea54'}
PREVIOUS_RUNTIME='cfcaeef7a3ecf8c878b569a2d554c15814129599febc56bcd288812c22dca097'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    for path,expected in REVIEWED_FILES.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('unrelated runtime outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected={'schema': 'hcl-c02-planned-input-amendment-v1', 'previous_hcl_runtime_sha256': 'cfcaeef7a3ecf8c878b569a2d554c15814129599febc56bcd288812c22dca097', 'amended_hcl_runtime_sha256': '38ee8c979847ccf68f32747d5485d0494274fdb65165d1bde7fe7a08fc4dc9a4', 'changed_runtime_files': ['hcl/cognition/retained.py', 'hcl/cognition/universal_entry.py', 'hcl/cognition/capability_catalog.py'], 'reason': 'EXISTING_C02_EXECUTION_UNDER_FIRST_PLANNER_SOURCE_INTERPRETATIONS', 'native_action_explanations_sha256': '39fd7d6ce18959f726795b8e3b558fd05452dfa7d193b02ec7129d273511d305', 'native_parsers_changed': False, 'conditional_input_families': ['B01', 'C01', 'C02', 'C03'], 'maximum_translated_operations': 1, 'maximum_sources_per_translated_operation': 1, 'maximum_candidates': 24, 'native_c02_row_limit_preserved': 20, 'provider_phases': ['planning', 'answer'], 'additional_provider_phases': 0, 'semantic_input_origin': 'METERED_PLANNING_RESPONSE', 'translation_authority': 'UNVERIFIED_TRANSLATION_HYPOTHESIS', 'original_sources_only_quotable': True, 'source_and_translation_withdrawal_preserved': True, 'source_order_is_calendar_time': False, 'later_knowledge_or_goals_backfill_action_time': False, 'winning_motive': 'NOT_INFERRED', 'empty_result_is_checked_treatment': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'model_interpretation_quality_verified': False, 'maximum_request_bytes': 36000, 'token_defaults_changed': False, 'capability_count_changed': False, 'longmemeval': 'SEALED_NOT_ACCESSED', 'existing_actor_label_contract_disclosed': 'EXACT_SOURCE_NAMED_ASCII_AT_MOST_32_NO_INVENTED_ALIAS', 'existing_negated_action_choice_contract_disclosed': True}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('C02 planned input amendment drift')
    return True


if __name__=='__main__':validate_current();print('C02_PLANNED_INPUT_AND_IMMUTABLE_EVIDENCE_PASS')
