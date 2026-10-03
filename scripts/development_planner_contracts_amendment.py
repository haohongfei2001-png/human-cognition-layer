"""Current planner contract guidance with immutable previous runtime and paid receipts."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_universal_sensitivity_amendment import validate_current as validate_previous
from scripts.development_universal_sensitivity_amendment import HISTORICAL_PINS as PRIOR_PINS

REPORT=Path('reports/HCL_PLANNER_ENTRY_CONTRACTS_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_universal_sensitivity_amendment.py': '04bb47da080af4ce0c8a41e17b617597cecfb2bb20498679d3a169d1ac19ff74', 'reports/HCL_DEVELOPMENT_UNIVERSAL_SENSITIVITY_AMENDMENT.json': '2d1a68dc8c61374a6b1be39e77fa8c088d07f273d241e2ec23f20b8c428ea608', 'scripts/bounded_diagnostic_protocol.py': 'a11712be17046f6ec02409be6118820a18fe8a5b0426b14665e1510b6ecdfa3f', 'scripts/bounded_diagnostic_port.py': '16720c930139e66484ba86dc6238ad338c2eadf4e61317560dfe7902e8090a8a', 'scripts/run_bounded_diagnostics.py': '3bd072cd550b9ee547ef245dfc128bb37f74a94b83e13b8bfd2e11310a40f638', 'tests/test_bounded_diagnostics.py': 'c560185180c42eb350b4c276605b3ae4688c75637d8abb799bb3231789a051ab', 'reports/HCL_BOUNDED_DIAGNOSTIC_PACKAGE.json': '8caeb38d84b0d529b28e0c228bed0d0b0fcbd711f7e72a772536ec68ee77060d', 'reports/HCL_BOUNDED_DIAGNOSTIC_CLOSURE.json': '6d4ce5f12a7b747d9af82f51c4f26d3c7ade316e5d59b7e81432ef97d80af51e', '.github/HCL_BOUNDED_DIAGNOSTIC_GRANT.json': '8564366fc91d920730320911c817ad67b585d181cc8e27a14a8abd7261fb2f84', '.github/frozen/hcl-bounded-diagnostics-once.yml': '4f013e622349220e7f5861b79e19fdcbee28ad0731cbed5dacbc349d5fe1b38d', 'scripts/output_limit_protocol.py': '994b2c591e4bdcef903de870ae74696d8bfc409c57f225c932276d6d82bca9d7', 'scripts/output_limit_port.py': '3bf22b5481eea36fefcad48cea6bcb4952d934b0ca529392ce7499f11f29afef', 'scripts/run_output_limit_continuation.py': '325eda1c0569bbaacb81bec20823135eb27e80f5c6fc1dca12ae15b1680681ca', 'tests/test_output_limit_continuation.py': 'a0d49c52d3f05e64852c5aae8b7b4db078668fad1d87e9dfd06cd1b1597d8b9e', 'reports/HCL_OUTPUT_LIMIT_CONTINUATION_PACKAGE.json': '8892948784f482107506f244f2fa0796ca26e4d6308c534148cc29b445ecf279', 'reports/HCL_OUTPUT_LIMIT_CONTINUATION_CLOSURE.json': '72c02989728bab402a7326ed0bf5ce1060085c34e092a9bdbfc0db0aca00ccb0', '.github/HCL_OUTPUT_LIMIT_CONTINUATION_GRANT.json': '7b9c9d4bb396e0bddd397a7d1c9db35d2590d73cd888248385739b1079129d8c', '.github/frozen/hcl-output-limit-original-planning.json': 'cd0ef97dda2f15d9316823bfbae61d4db4621e227c5d39f2b1db1c44a36c2a61', '.github/frozen/hcl-output-limit-continuation-once.yml': 'ceb7b3f6dd0f8d547fc58942d353bbb7bf81a541bf846bc322a893a1f24d2798'})
PREVIOUS_FILES={'hcl/cognition/capability_catalog.py': 'd69c627f1114f025af560a1c3007300b09c30ce767d09ff3cb9aed44669e8f38', 'hcl/cognition/universal_entry.py': 'b62c2461d9a1ddbde9bb56c489bf843f1d100394521cf93214a1858f76129ee1'}
PREVIOUS_RUNTIME='ad67e85c9bd00cb23dd61825bf7c35790f72282754574da19612435e96839cfe'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    validate_previous(current_digest=PREVIOUS_RUNTIME)
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime or membership changed')
    expected={'schema': 'hcl-planner-entry-contracts-amendment-v1', 'previous_hcl_runtime_sha256': 'ad67e85c9bd00cb23dd61825bf7c35790f72282754574da19612435e96839cfe', 'amended_hcl_runtime_sha256': '3932cdda69549f66311fdeedd7d8182b6ecb232e1b4cb1a533e589b74df1b628', 'changed_runtime_files': ['hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'EXPOSE_EXISTING_ADAPTER_INPUT_CONTRACTS_WITHOUT_DISPATCH_OR_PARSER_CHANGE', 'parser_changed': False, 'dispatch_changed': False, 'model_or_token_settings_changed': False, 'provider_calls_in_preparation': 0, 'provider_spend_usd': 0, 'model_selection_efficacy_verified': False, 'complete_capability_integration': False, 'authorized_additional_calls': 0, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('planner entry contract amendment drift')
    return True


if __name__=='__main__':validate_current();print('PLANNER_ENTRY_CONTRACTS_AND_IMMUTABLE_EVIDENCE_PASS')
