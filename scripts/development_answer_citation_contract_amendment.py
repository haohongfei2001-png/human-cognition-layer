"""Policy-only citation contract; retain original failed receipt and all prior pins."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_planner_contracts_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_ANSWER_CITATION_CONTRACT_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_planner_contracts_amendment.py': '95597b7b58d7631b59d8ff4667a376faed7c4a00847419f6a52df10464dac094', 'reports/HCL_PLANNER_ENTRY_CONTRACTS_AMENDMENT.json': 'bd1b754425739941380fe615c1a62ad57ce3926a17311bbf5141dd3e3112d78c', 'eval/planner_contract_challenges_v1.json': '430bcca39eae5c90f21b2d26bd01a1308ed6c62d2b8222bd06f05fbb35017ef5', 'scripts/verify_planner_contract_challenges.py': '715f7c02defb3e7069bdd6d27665ede215a04aab683f96fac418bd71af5522e3', 'reports/HCL_PLANNER_ENTRY_CONTRACTS_REVIEW.json': 'd413252509c901c16a7c56d560ee898f9536807a369d8a00920742b650fab332', 'scripts/run_planner_contract_smoke.py': '37d996f1e9b9287fdbfca6c53c50b285d26291962c19adc02c296f5987995373', 'tests/test_planner_contract_smoke.py': '6dc816f89b24a9a1dd02682ea952f25a0152d621e84b1aaae57ce0d4b08e336d', 'reports/HCL_PLANNER_CONTRACT_SMOKE_PACKAGE.json': '90f5a3430a219e7f23a8a3209ab6df64102767e77b3d3f152e55ba97af8f0158', 'reports/HCL_PLANNER_CONTRACT_SMOKE_CLOSURE.json': 'b6f08caba47d904ffafb88c6c1e3800967a93af807cde18b767b48845bdd836e', '.github/HCL_PLANNER_CONTRACT_SMOKE_GRANT.json': '4eb67c19ba54083436dd573b550c298ea0e43ed6d2db4d98648b86235d7f1f39', '.github/frozen/hcl-planner-contract-smoke-request.json': 'e68c73e0cc42b191528a8f3ada15635cb5d90e7dee7b8989fa77b7b781342aea', '.github/frozen/hcl-planner-contract-smoke-once.yml': '05213cbd3fb6c23d78594d66132a893ec535514de69ce10f7c51d89fbd6ef349'})
PREVIOUS_FILES={'hcl/cognition/reader_entry.py': '1546b58b1b8df4d39d688a86ade89213d5096a53cc5039135a5d02d26658922c'}
READER_NONPOLICY_SHA256='3ff9155836ae72082e083b73af1710111c5efbc8e5079d4a1fea7c2cabb9b8dc'
PREVIOUS_RUNTIME='3932cdda69549f66311fdeedd7d8182b6ecb232e1b4cb1a533e589b74df1b628'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    # Earlier live-tree validators mask dispatch/catalog, not this newly amended
    # reader policy. Preserve every transitive byte pin, validate consumed archives,
    # then restore only this policy file hash to prove the exact prior whole runtime.
    # No monkeypatch, rewritten old report, or current-runtime historical replay.
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    reader=Path('hcl/cognition/reader_entry.py').read_text();tree=ast.parse(reader)
    policies=[n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='_FINAL_ANSWER_POLICY'for t in n.targets)]
    if len(policies)!=1 or len(policies[0].targets)!=1 or not isinstance(policies[0].value,ast.Constant) or not isinstance(policies[0].value.value,str):
        raise ValueError('one literal final policy constant required')
    node=policies[0];lines=reader.splitlines(keepends=True)
    outside=''.join(lines[:node.lineno-1]+['_FINAL_ANSWER_POLICY = <POLICY>\n']+lines[node.end_lineno:])
    # Byte identity outside the one literal policy is stable across Python AST
    # dump-format versions, and stricter than the separately checked AST delta.
    if hashlib.sha256(outside.encode()).hexdigest()!=READER_NONPOLICY_SHA256:
        raise ValueError('reader change outside final policy')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime or membership changed')
    expected={'schema': 'hcl-answer-citation-contract-amendment-v1', 'previous_hcl_runtime_sha256': '3932cdda69549f66311fdeedd7d8182b6ecb232e1b4cb1a533e589b74df1b628', 'amended_hcl_runtime_sha256': '6554c136562a112333071eda9ebb5a18bd1e51686b68a10f96647d4bf0cc331d', 'changed_runtime_files': ['hcl/cognition/reader_entry.py'], 'reason': 'DISCLOSE_EXISTING_ANSWER_CITATION_ELEMENT_CONTRACT', 'validator_changed': False, 'dispatch_changed': False, 'raw_output_rewriting_added': False, 'model_or_token_settings_changed': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_failed_answer_reclassified': False, 'answer_gain_established': False, 'model_compliance_verified': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('answer citation contract amendment drift')
    return True


if __name__=='__main__':validate_current();print('ANSWER_CITATION_CONTRACT_AND_IMMUTABLE_EVIDENCE_PASS')
