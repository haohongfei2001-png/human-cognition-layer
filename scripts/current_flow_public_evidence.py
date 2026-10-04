"""Exact owner-approved public synthetic exception. Never serialize a raw receipt."""
import argparse
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

from scripts import run_current_flow_diagnostic as runner

TERMINALS={'G05_ANSWER_ACCEPTED_READBACK_PENDING','HCL_CITATIONS_REJECTED_NO_RETRY',
           'HCL_FAILED_NO_RETRY','FAILED_OR_UNKNOWN_NO_RETRY'}
INVOCATIONS={'NOT_INVOKED','INVOKED_OR_SEND_UNKNOWN','RETURNED','RESPONSE_RETURNED_REJECTED'}


def identity(run_id,head_sha):
    if (not isinstance(run_id,str)or not run_id.isascii()or not run_id.isdecimal()or int(run_id)<=0
        or not isinstance(head_sha,str)or len(head_sha)!=40 or any(c not in '0123456789abcdef'for c in head_sha)):
        raise ValueError('EXACT_PUBLIC_RUN_HEAD_REQUIRED')
    return dict(run_id=run_id,head_sha=head_sha)


def money(value):
    if not isinstance(value,str)or len(value)>40:raise ValueError('BOUNDED_COST_REQUIRED')
    number=Decimal(value)
    if not number.is_finite()or not 0<=number<=runner.CAP:raise ValueError('BOUNDED_COST_REQUIRED')
    # Return a canonical numeric string, never an unchecked input string.
    return str(number)


def final_fields(raw):
    if not isinstance(raw,str)or len(raw.encode())>256000:return None
    try:value=json.loads(raw)
    except (ValueError,TypeError):return None
    if (not isinstance(value,dict)or set(value)!={'answer','source_citations','uncertainty','assumptions'}
        or any(not isinstance(value[k],str)for k in ('answer','uncertainty','assumptions'))
        or not isinstance(value['source_citations'],list)):
        return None
    for citation in value['source_citations']:
        if (not isinstance(citation,dict)or not {'source_id','version','quote'}<=set(citation)
            or not set(citation)<={'source_id','version','quote','start','end'}
            or not isinstance(citation['source_id'],str)or not isinstance(citation['quote'],str)
            or type(citation['version'])is not int
            or any(type(citation[k])is not int for k in ('start','end')if k in citation)):
            return None
    # Whitelisted final fields and even invalid citation offsets remain unchanged.
    # No trimming, correction, added citation, or semantic PASS transformation.
    return value


def export(receipt,package,grant,run_id,head_sha,secret_check):
    public_identity=identity(run_id,head_sha)
    if (package!=runner.build_package()or grant!=runner.expected_grant(package,
        authorization_ref=runner.AUTHORIZATION,approved_at=runner.APPROVED_AT,expires_at=runner.EXPIRES_AT)
        or receipt.get('package_sha256')!=runner.digest(package)
        or receipt.get('authorization_ref')!=runner.AUTHORIZATION
        or secret_check!=dict(public_identity,existing_provider_secret='PRESENT')):
        raise ValueError('EXACT_PUBLIC_SYNTHETIC_AUTHORITY_AND_IDENTITY_REQUIRED')
    if receipt.get('status')not in TERMINALS or receipt.get('budget_state')!='CLOSED_NO_TRANSFER_NO_RETRY':
        raise ValueError('TERMINAL_CLOSED_RECEIPT_REQUIRED')
    rows=receipt.get('calls')
    if not isinstance(rows,list)or len(rows)>runner.MAX_CALLS:raise ValueError('BOUNDED_CALLS_REQUIRED')
    calls=[];final=None;answer_sha=None
    for index,row in enumerate(rows):
        phase=('planning','answer')[index]
        if row.get('call_id')!='hcl:'+phase or row.get('phase')!=phase:raise ValueError('EXACT_TWO_PHASE_ORDER_REQUIRED')
        request_sha=row.get('request_sha256')
        if not isinstance(request_sha,str)or len(request_sha)!=64 or any(c not in '0123456789abcdef'for c in request_sha):
            raise ValueError('REQUEST_HASH_REQUIRED')
        invocation=row.get('invocation_status')
        if invocation not in INVOCATIONS:raise ValueError('KNOWN_INVOCATION_STATUS_REQUIRED')
        call=dict(phase=phase,request_sha256=request_sha,reserved_usd=money(row['reserved_usd']),
            invocation_status=invocation,provider_call=row.get('provider_call')is True,returned=row.get('status')=='RETURNED')
        counts=row.get('usage')
        if (isinstance(counts,dict)and set(counts)=={'prompt_tokens','completion_tokens'}
            and all(type(v)is int and 0<=v<=200000 for v in counts.values())):
            rated=(counts['prompt_tokens']*runner.INPUT_RATE+counts['completion_tokens']*runner.OUTPUT_RATE)/1000000
            if money(row['actual_usd'])!=str(rated)or rated>Decimal(call['reserved_usd']):
                raise ValueError('EXACT_RATED_USAGE_REQUIRED')
            call.update(usage={k:counts[k]for k in ('prompt_tokens','completion_tokens')},usage_rated_usd=str(rated))
        elif 'actual_usd'in row:raise ValueError('COST_WITHOUT_COMPLETE_USAGE_FORBIDDEN')
        calls.append(call)
        if phase=='answer'and isinstance(row.get('response_content'),str):
            raw=row['response_content'];answer_sha=hashlib.sha256(raw.encode()).hexdigest();final=final_fields(raw)
    reserved=money(receipt['reserved_usd'])
    if Decimal(reserved)!=sum(Decimal(row['reserved_usd'])for row in calls):raise ValueError('LEDGER_TOTAL_REQUIRED')
    complete=all('usage_rated_usd'in row for row in calls if row['provider_call'])
    def capabilities(key):
        values=receipt.get(key,[])
        if not isinstance(values,list)or any(v not in runner.CATALOG for v in values):raise ValueError('CATALOG_CAPABILITIES_ONLY')
        return list(values)
    source=runner.frozen_input()
    return dict(schema='hcl-public-synthetic-g05-evidence-v1',**public_identity,
        authorization_ref=runner.AUTHORIZATION,public_output_scope=runner.PUBLIC_SCOPE,
        package_sha256=runner.digest(package),runtime_commit=runner.RUNTIME_COMMIT,runtime_sha256=runner.RUNTIME_SHA,
        input_sha256=runner.INPUT_SHA,question=source['question'],
        sources=[dict(source_id=s['source_id'],version=s['version'],text_sha256=hashlib.sha256(s['text'].encode()).hexdigest())for s in source['sources']],
        existing_provider_secret='PRESENT',model=runner.MODEL,planning_tokens=16384,answer_tokens=8192,
        production_default_planning_tokens=4096,status=receipt['status'],
        selected_capabilities=capabilities('selected_capabilities'),executed_capabilities=capabilities('executed_capabilities'),
        source_and_original_request_supported=receipt.get('g05_treatment_gate')=='SOURCE_AND_ORIGINAL_REQUEST_SUPPORTED',
        citations_accepted=receipt.get('hcl_citations_accepted')is True,
        final_answer_fields=final,final_answer_sha256=answer_sha,
        final_fields_status='EXACT_FIELDS_UNCHANGED'if final is not None else 'ABSENT_OR_NONCANONICAL_NOT_PUBLISHED',
        calls=calls,provider_calls=sum(row['provider_call']for row in calls),reserved_usd=reserved,
        usage_complete=complete,usage_rated_usd=str(sum(Decimal(row.get('usage_rated_usd','0'))for row in calls))if complete else None,
        invoice_cost_usd=None,cost_basis='USAGE_RATED_PEAK_NOT_INVOICE_FULL_RESERVATION_RETAINED',
        budget_state='CLOSED_NO_TRANSFER_NO_RETRY',remaining_authorized_calls=0,remaining_authorized_usd='0',
        semantic_review='PENDING_SOURCE_FIRST_REVIEW',efficacy_verified=False,i02_certified=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    raw=Path(args.receipt).read_bytes()
    if len(raw)>16*1024*1024:raise ValueError('BOUNDED_PRIVATE_RECEIPT_REQUIRED')
    result=export(json.loads(raw),json.loads(runner.PACKAGE.read_text()),json.loads(runner.GRANT.read_text()),
        os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_SHA'],json.loads(runner.SECRET_CHECK.read_text()))
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print('SCOPED_PUBLIC_SYNTHETIC_EVIDENCE_SAVED')
