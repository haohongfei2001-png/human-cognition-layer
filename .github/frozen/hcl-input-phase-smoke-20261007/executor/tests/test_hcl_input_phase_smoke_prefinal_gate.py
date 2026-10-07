"""Source-rooted post-native/pre-final controls; no provider or account access."""
import copy
import json
from types import SimpleNamespace
import unittest

import hcl_input_phase_smoke_candidate as r
import hcl_input_phase_smoke_native_public as n
from hcl.cognition.universal_entry import _share_identical_native_reader_contexts
import test_hcl_input_phase_smoke_candidate as fixture


class BeforeFinalNativeAdmission(unittest.TestCase):
    def setUp(self):
        self.package=r.OfflinePackage.build(fixture.fixture_packet(),fixture.RUNTIME)
        self.case=self.package.cases[0]

    def prompt(self, *, empty=False, shared=False):
        case=copy.deepcopy(self.case)
        if empty:
            case['sources'][0]['text']='A complete observation without admitted typed premises.'
        session=n._session(case)
        op=dict(capability='B01',question=case['question'],source_ids=[case['sources'][0]['source_id']],bindings=[],input_mode='literal')
        ops=[copy.deepcopy(op) for _ in range(2 if shared else 1)]
        native=[session._execute(arg,case['question']) for arg in ops]
        payload=dict(question=case['question'],sources=[{key:s[key] for key in ('source_id','version','text')} for s in case['sources']],
            hcl_plan=dict(task='Unrelated synthetic control.',operations=ops,limitations=[]),hcl_operations=native,
            hcl_execution=dict(selected_operations=len(ops),dispatched_operations=len(native),native_results=len(native)))
        if shared:payload=_share_identical_native_reader_contexts(payload)
        return case,[dict(role='system',content='Trusted local control.'),dict(role='user',content=json.dumps(payload))]

    def test_real_checked_result_admitted_and_shared_pairs_expand_exactly(self):
        for shared in (False,True):
            case,prompt=self.prompt(shared=shared);before=copy.deepcopy(prompt)
            result=r.validate_pre_final_native(self.package,case,prompt)
            self.assertTrue(result['allowed_family_checked_treatment_present'])
            self.assertFalse(result['semantic_relevance_or_quality_certified'])
            self.assertEqual(prompt,before)

    def test_zero_treatment_fails_before_any_final_reservation(self):
        case,prompt=self.prompt(empty=True)
        package=SimpleNamespace(cases=[case],value=self.package.value,packet=self.package.packet)
        reservations=[];observed=[]
        def reserve(*args):reservations.append(args);raise AssertionError('NO_FINAL_RESERVATION')
        ledger=SimpleNamespace(package=package,observe_request=lambda *args:observed.append(args),reserve=reserve)
        client=SimpleNamespace(max_retries=0,base_url='https://api.deepseek.com',timeout=180)
        port=r.BoundedPort(client,ledger,case['case_id']+':HCL')
        with self.assertRaisesRegex(r.MeteredPortError,'PRE_FINAL_NATIVE_REQUIREMENTS_REJECTED_NO_CALL'):
            port.reservation_usd('answer',prompt)
        self.assertEqual(reservations,[]);self.assertEqual(len(observed),1)
        self.assertEqual(port.known_failure,'PRE_FINAL_NATIVE_REQUIREMENTS_REJECTED_NO_CALL')

    def test_changed_source_version_and_result_are_rejected_before_final(self):
        for mutation in ('source','result','forged_reference'):
            case,prompt=self.prompt();body=json.loads(prompt[-1]['content'])
            if mutation=='source':body['sources'][0]['version']+=1
            elif mutation=='result':body['hcl_operations'][0]['status']='FORGED_ACTUAL_NATIVE_STATUS'
            else:body['hcl_operations'][0]['native_reader_context_ref']=True
            prompt[-1]['content']=json.dumps(body)
            with self.assertRaises(ValueError):r.validate_pre_final_native(self.package,case,prompt)

    def test_selected_known_blocker_fails_even_with_a_valid_checked_family(self):
        case,prompt=self.prompt();body=json.loads(prompt[-1]['content']);session=n._session(case)
        op=dict(capability='B02',question=case['question'],source_ids=[case['sources'][0]['source_id']],bindings=[])
        body['hcl_plan']['operations'].append(op);body['hcl_operations'].append(session._execute(op,case['question']))
        prompt[-1]['content']=json.dumps(body)
        with self.assertRaisesRegex(ValueError,'NATIVE_ENTRY_REQUIREMENTS_NOT_SATISFIED_BEFORE_FINAL'):
            r.validate_pre_final_native(self.package,case,prompt)

if __name__=='__main__':unittest.main()
