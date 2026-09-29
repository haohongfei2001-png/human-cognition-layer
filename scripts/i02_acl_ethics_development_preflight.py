"""Provider-free source-first ACL tutorial development calibration gate."""

import hashlib
import json
from pathlib import Path

from hcl.v1 import CognitionRequest, HCLCognitionLayer
from scripts.i02_acl_ethics_exposure_overlay import require_acl_development_input
from scripts.serious_eval_arms_v8 import (
    prepare_generic_final_v8, prepare_primary_arms_v8)
from scripts.serious_eval_semantic_score import load_rubric, validate_manifest
from scripts.serious_eval_contract import runtime_digest


SOURCE = Path('reports/HCL_I02_ACL_ETHICS_DEVELOPMENT_SOURCE.json')
OBLIGATIONS = Path('reports/HCL_I02_ACL_ETHICS_SOURCE_FIRST_OBLIGATIONS.json')
SOURCE_SHA256 = '127cf23ee554c575b5c35c94c4d5468f5f1abae14d7cb15195f31ca22e602bc1'
QUESTION_SHA256 = '653992830b23fef2fea55039e493885aa1059b95b707e5e84946612e8477ce51'
REPO_COMMIT = '582bcc6c68f9f53d23912ea19892a9b2e74264c7'
REPO_BLOB = '3328c30f0bf41956ce61dad617785bc2e4936ec6'


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def git_blob_sha(value):
    raw = value.encode()
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def audit():
    source_file = SOURCE.read_bytes()
    source = json.loads(source_file)
    text, question, source_id = (source['source_text'],
        source['ordinary_question'], source['source_id'])
    if (source['schema'] != 'hcl-i02-acl-ethics-development-source-v1' or
            source['repository_commit'] != REPO_COMMIT or
            source['repository_blob_sha'] != REPO_BLOB or
            git_blob_sha(text) != REPO_BLOB or
            source['native_activity_document_blob'] !=
                'a5a2fef8a28a45db792bb4f9233420c761485ba5' or
            source['native_activity_instruction'] !=
                'Use this document to co-construct your thoughts on these abstracts.' or
            source['license'] != 'CC BY 4.0' or
            source['question_origin'] !=
                'ADAPTED_FROM_NATIVE_GROUP_CRITIQUE_ACTIVITY_NOT_VERBATIM_NATIVE_QUESTION' or
            source['development_exposed'] is not True or
            source['confirmation_qualified'] is not False or
            sha(text) != SOURCE_SHA256 or sha(question) != QUESTION_SHA256 or
            source['provider_calls'] != 0 or
            source['longmemeval'] != 'SEALED_NOT_ACCESSED'):
        raise ValueError('pinned ACL development source drift')
    manifest_file = OBLIGATIONS.read_bytes()
    manifest = json.loads(manifest_file)
    validate_manifest(manifest, load_rubric())
    if (manifest['case_id'] != 'acl-ethics-abstract-3-development' or
            manifest['sources'] != [dict(source_id=source_id, text=text)] or
            manifest['arm_output_seen'] is not False):
        raise ValueError('source-first ACL obligations drift')
    candidate = dict(split='CALIBRATION', source_text=text,
        writing_system_id=source['source_system'],
        author_id='acl-eacl-2023-ethics-tutorial-organizers',
        template_id='acl-eacl-2023-synthetic-problematic-abstracts',
        source_group_id=SOURCE_SHA256,
        source_license_status='VERIFIED_FOR_THIS_EVALUATION',
        source_access_status='AUTHORIZED_FOR_EVERY_ARM')
    require_acl_development_input(candidate)
    arms = prepare_primary_arms_v8(question, source_id, text)
    for phase in ('C', 'P', 'G_map'):
        payload = json.loads(arms[phase][-1]['content'])
        if payload['question'] != question or payload['sources'] != [
                dict(source_id=source_id, text=text)]:
            raise ValueError('unequal ordinary comparator input')
    quote = 'publicly-accessible EPub versions of all the books of the commercial Amazonia bookshop web storefront'
    map_response = json.dumps(dict(source_index=[dict(id='e1', source_id=source_id,
        quote=quote)], relations=[], answer_plan=[], open_questions=[]))
    g_final = prepare_generic_final_v8(arms, map_response)
    final_payload = json.loads(g_final[-1]['content'])
    if final_payload['question'] != question or final_payload['sources'] != [
            dict(source_id=source_id, text=text)]:
        raise ValueError('G final lost ordinary source')
    h = HCLCognitionLayer(lambda _: '').prepare(
        CognitionRequest(question, narrative=text))
    h_payload = json.loads(h.messages[-1]['content'])
    if (h_payload['query'] != question or h_payload['narrative'] != text or
            not h.plan.direct or h.plan.capabilities or h.context is not None):
        raise ValueError('H ordinary source or fixed direct-treatment boundary drift')
    # A direct H path remains a measured fact. It is never relabeled as
    # specialized treatment to justify H/H-new provider calls.
    return dict(schema='hcl-i02-acl-ethics-development-preflight-v1',
        source_file_sha256=hashlib.sha256(source_file).hexdigest(),
        obligations_file_sha256=hashlib.sha256(manifest_file).hexdigest(),
        source_sha256=SOURCE_SHA256, question_sha256=QUESTION_SHA256,
        source_first_obligation_count=len(manifest['obligations']),
        source_valid=True, rights_verified_for_development=True,
        full_ordinary_input_equal_for_cpg=True,
        g_final_original_source_present=True,
        h_runtime_sha256=runtime_digest(),
        h_direct=h.plan.direct, h_selected_capabilities=list(h.plan.capabilities),
        h_specialized_treatment_present=False,
        h_hnew_calls_allowed=False,
        cpg_model_semantics_qualified=False,
        independent_confirmation_qualified=False,
        provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, sort_keys=True))
