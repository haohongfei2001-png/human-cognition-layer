"""Owner-directed model routing with required native outcomes; historical evidence stays frozen."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_universal_understanding_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_LLM_ROUTING_EXECUTION_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_universal_understanding_amendment.py': '131803eb32c59af7983eae4f76ea894a988dd0ba0865370b2409603bb4a30f8c', 'reports/HCL_UNIVERSAL_UNDERSTANDING_AMENDMENT.json': 'd4578818a3447d11f97a8001063bdbc05a152b0ed21de3e97f247aaa43bf652b', 'docs/HCL_UNIVERSAL_UNDERSTANDING_ENTRY.md': 'd219de0a4ad902c6499f99e33446e214b188dc3d74fe618f5cecbf06a0340719', 'reports/HCL_UNIVERSAL_UNDERSTANDING_VALIDATION.json': '6fd781bb82186e2cb401a485765410a46b1451ae8408f48d998dbd2d867ea87d'})
PREVIOUS_FILES={'hcl/cognition/universal_entry.py': '566fa661d053cf205f3eda7d71d7bf7c055233e267b4419954c9d437d22bd460', 'hcl/cognition/capability_catalog.py': '665746500b182dbd6788441f377237e5633fcf3c7dd109588483826090105106'}
REVIEWED_FILES={'hcl/cognition/universal_entry.py': 'bda1ad2e8257087634fb910da3f802f04dea8eb82a13e3ee59f68f1d77aab3e9', 'hcl/cognition/capability_catalog.py': '0ef420e550bccb340e309460a9e328cd3ee649dbe51ec59b7d1b9cc4ad64ce3f'}
PREVIOUS_RUNTIME='071d5327b32903c96b6e397103b8715acd82a4974af4195e32f49f35ddd3b53d'


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
    expected={'schema': 'hcl-llm-routing-execution-amendment-v1', 'previous_hcl_runtime_sha256': '071d5327b32903c96b6e397103b8715acd82a4974af4195e32f49f35ddd3b53d', 'amended_hcl_runtime_sha256': 'cfcaeef7a3ecf8c878b569a2d554c15814129599febc56bcd288812c22dca097', 'changed_runtime_files': ['hcl/cognition/universal_entry.py', 'hcl/cognition/capability_catalog.py'], 'reason': 'LLM_PLANNED_SOURCE_ANCHORED_STRUCTURED_INPUT_WITH_REQUIRED_NATIVE_HCL_OUTCOME', 'initial_understanding': 'LLM_BEST_EFFORT_NOT_DETERMINISTIC_PREREQUISITE', 'planner_arguments': 'INTENT_PRESERVING_WITH_ORIGINAL_SOURCE_AND_CALLER_AUTHORITY', 'empty_or_unavailable_plan': 'NO_ANSWER_CALL_NO_FORCED_OPERATION', 'native_insufficient_evidence': 'LIMITED_ANSWER_ALLOWED_NOT_CHECKED_TREATMENT', 'execution_is_treatment_proof': False, 'selection_accuracy_verified': False, 'capability_catalog_changed': True, 'native_parser_or_grammar_changed': False, 'source_citation_or_authority_guards_changed': False, 'model_or_token_settings_changed': False, 'new_provider_subcalls': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'longmemeval': 'SEALED_NOT_ACCESSED', 'conditional_input_families': ['B01', 'C01', 'C03'], 'conditional_input_maximum_operations': 1, 'conditional_input_maximum_candidates': 24, 'semantic_input_origin': 'FIRST_METERED_PLANNING_RESPONSE', 'additional_provider_phases': 0, 'native_conditional_adapter': 'EXISTING_PREPARE_RETAINED_READER', 'derived_input_is_original_source': False, 'translation_semantics': 'UNVERIFIED_MODEL_INTERPRETATION', 'native_parsers_changed': False}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('LLM routing execution amendment drift')
    return True


if __name__=='__main__':validate_current();print('LLM_ROUTING_EXECUTION_AND_IMMUTABLE_EVIDENCE_PASS')
