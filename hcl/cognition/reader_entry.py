"""Cost-bounded ordinary reader selection over existing B01/C01/C03 mechanisms.

The local path is tried first, without provider extraction. A single optional
translation can increase coverage, but remains an unverified representation.
This is a reader's authorized source view, never a character access projection.
"""
from dataclasses import dataclass
import json
import re
from .core import ClaimKind, Scope, identity
from .workspace import OperationResult
from .retained import (prepare_retained_reader, original_sources_from_messages,
                       audit_supplied_source_citations)


@dataclass(frozen=True)
class ReaderEntry:
    prepared: object
    receipt_json: str

    @property
    def messages(self):
        return self.prepared.messages

    @property
    def receipt(self):
        return json.loads(self.receipt_json)

    def current_messages(self, workspace):
        return self.prepared.current_messages(workspace)


class _OneTranslation:
    def __init__(self, backend):
        self.backend = backend
        self.requests = []
        self.responses = []

    def complete_json(self, messages, **kwargs):
        if self.requests:
            raise ValueError('one optional translation only; no retry')
        self.requests.append(dict(messages=messages, parameters=kwargs))
        raw = self.backend.complete_json(messages, **kwargs)
        self.responses.append(raw)
        return raw


def _local(workspace, query, source_id, max_chars):
    from hcl.v1.long_source_question import prepare_reader_cognition
    source = workspace._documents[source_id][0]
    version = workspace._versions[source_id]
    key = identity('ordinary-local-reader', query, source_id, max_chars)
    versions = ((source_id, version),)
    old = workspace._cache.get(key)
    if old and old.source_versions == versions:
        old.current_messages(workspace)
        return old
    raw = prepare_reader_cognition(query, source, source_id=source_id,
                                   max_context_chars=max_chars,workspace=workspace)
    messages = list(raw.messages)
    payload = json.loads(messages[-1]['content'])
    from .ordinary_access import prepare_ordinary_access
    access=prepare_ordinary_access(source,source_id=source_id,version=version)
    preparation=dict(raw.preparation_receipt)
    preparation['communication_treatment']=dict(mechanism='B02_EXISTING_REPORTED_ACCESS_CHECKER',
        checked_operations=access['checked_operations'],coverage_failure=access['reason'],
        knowledge_established=False,comprehension_established=False,private_state_established=False)
    if access['state'] is not None:
        payload['checked_reported_communication']=access['state']
        preparation['specialized_cognition_treatment']=True
        preparation['method']+='_reported_access_integration'
        messages[0]=dict(role='system',content=messages[0]['content']+' Communication views use a source-local syntactic representation, not quotable original text. Reported receipt is not comprehension, acceptance, knowledge or private belief; availability/addressing and missing routes are not receipt or ignorance. Actor aliases are reversible local labels, not cross-source identities. Later source receipt cannot rewrite earlier non-receipt; source order is not calendar time.')
    if not preparation.get('specialized_cognition_treatment'):
        # No checked cognition was executed. Keep the complete original and the
        # source/mental-truth guard, omit unexecuted candidate/audit wire payload.
        payload=dict(query=query,sources=payload['sources'])
        preparation['context_selection']='COMPLETE_SOURCE_NO_CHECKED_STATE_MINIMAL_WIRE'
        preparation['unused_candidates_not_sent']=True
    else:
        preparation['context_selection']='ACTUAL_CHECKED_COGNITION_AND_COMPLETE_SOURCE'
    # The nested local checker uses statement order; the primary wire version
    # is the actual shared source revision, not a reset checker-local version.
    payload['sources'][0]['version'] = version
    messages[-1] = dict(role='user', content=json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if len(json.dumps(messages,ensure_ascii=False))>max_chars:
        raise ValueError('complete reader and access state exceed context budget; no truncation')
    original_sources_from_messages(messages)
    scope = Scope(source_ids=(source_id,))
    root = workspace.core.claim(scope, ClaimKind.SOURCE_REPORT,
        dict(source_id=source_id, version=version, authority='CALLER_AUTHORIZED_TEXT'))
    workspace.core.support(root, workspace._spans[source_id])
    claim = workspace.core.claim(scope, ClaimKind.SYSTEM_INTERPRETATION,
        dict(state=payload, source_versions=versions,
             semantic_boundary='SOURCE_REPORT_NOT_PRIVATE_OR_WORLD_TRUTH'))
    workspace.core.support(claim, root, *preparation.get('shared_support_claim_ids',()))
    workspace.core.interpret(claim, required_premises=(root,),
        unknown_conditions=('calendar_and_receipt_time_not_established',))
    result = OperationResult(key, query, scope, versions, (claim,),
        json.dumps(messages, ensure_ascii=False, sort_keys=True),
        json.dumps(preparation, ensure_ascii=False, sort_keys=True))
    workspace.executions += 1
    workspace._cache[key] = result
    return result


def prepare_reader_entry(workspace, query, *, source_ids, backend=None,
                         max_chars=64000, compact_context=True, allow_translation=False):
    """Local first; optional extraction requires allow_translation=True, no answer call.

    Invalid/stale support, unknown transport failure and budget errors in the
    local whole-source path propagate. An unusable optional representation is
    recorded and leaves the original complete local context available.
    """
    if (not isinstance(query, str) or not query.strip() or len(query) > 8000
            or not isinstance(source_ids, tuple) or len(source_ids) != 1
            or source_ids[0] not in workspace._documents
            or type(max_chars) is not int or not 512 <= max_chars <= 64000
            or type(compact_context) is not bool or type(allow_translation) is not bool):
        raise ValueError('one registered analyst source and bounded reader context required')
    if re.search(r'\b(?:At statement|before statement|after statement)\s+\d+', query, re.I):
        raise ValueError('project source explicitly before adaptive reader statement snapshot')
    local = _local(workspace, query, source_ids[0], max_chars)
    prep = json.loads(local.preparation_json)
    receipt = dict(schema='hcl-adaptive-reader-entry-v1',
        source_versions=list(local.source_versions), selection='LOCAL_COMPLETE_SOURCE',
        checked_treatment_present=bool(prep.get('specialized_cognition_treatment')),
        local_preparation=prep, extraction_calls=0, extraction_requests=[],
        extraction_responses=[], extraction_failure=None,
        semantic_certification=False, private_state_established=False,
        world_truth_established=False, answer_gain_established=False,
        source_shortened=False, retry_count=0, allow_translation=allow_translation,
        translation_scope='EXPLICIT_OPT_IN_CONDITIONAL_REPRESENTATION' if allow_translation else 'DEFERRED_BY_DEFAULT_UNSUPPORTED_EXTRACTION_SIMPLIFICATION')
    selected = local
    if not receipt['checked_treatment_present'] and backend is not None and allow_translation:
        relay = _OneTranslation(backend)
        try:
            conditional = prepare_retained_reader(workspace, query, source_ids=source_ids,
                backend=relay, max_chars=max_chars, compact_context=compact_context)
        except ValueError as exc:
            # Never turn a concurrent source update/challenge into an accepted
            # fallback. Only known representation coverage failures are handled.
            local.current_messages(workspace)
            if not str(exc).startswith(('no supported translation;',
                    'unparsed source may qualify', 'ambiguous or oversized translation branch',
                    'shared support and original-source context exceeds budget',
                    'retained adapter did not ground requested task:')):
                raise
            receipt['selection'] = 'COMPLETE_SOURCE_AFTER_UNUSABLE_TRANSLATION'
            receipt['extraction_failure'] = dict(type=type(exc).__name__, message=str(exc))
        else:
            conditional.current_messages(workspace)
            original_sources_from_messages(conditional.messages)
            if conditional.receipt['checked_treatment_present']:
                selected = conditional
                receipt['selection'] = 'CONDITIONAL_TRANSLATION'
                receipt['checked_treatment_present'] = True
                receipt['conditional_preparation'] = conditional.receipt
            else:
                receipt['selection'] = 'COMPLETE_SOURCE_AFTER_NO_CHECKED_TREATMENT'
                receipt['unused_conditional_preparation'] = conditional.receipt
        receipt.update(extraction_calls=len(relay.requests),
            extraction_requests=relay.requests, extraction_responses=relay.responses)
    selected.current_messages(workspace)
    receipt['actual_final_messages'] = selected.messages
    return ReaderEntry(selected, json.dumps(receipt, ensure_ascii=False, sort_keys=True))


def answer_reader_entry(workspace, query, answer_backend, **kwargs):
    """One final call; source audit never rewrites raw output or retries."""
    entry = prepare_reader_entry(workspace, query, **kwargs)
    messages = entry.current_messages(workspace)
    original_sources_from_messages(messages)
    messages = [*messages, dict(role='system', content='Return exactly answer, source_citations, uncertainty and assumptions in one JSON object. Quote only supplied original sources. Source provenance does not certify semantics, private state or world truth.')]
    raw = (answer_backend.complete(messages) if hasattr(answer_backend, 'complete')
           else answer_backend(messages))
    audit = audit_supplied_source_citations(messages, raw)
    try:
        entry.current_messages(workspace)
    except ValueError:
        audit.update(status='STALE_OR_CHALLENGED_SUPPORT', deliverable=False)
    answer = raw if audit['deliverable'] else json.dumps(dict(
        answer='I cannot support this answer from the supplied text.', source_citations=[],
        uncertainty='The returned answer did not preserve reliable current source references.',
        assumptions='No private state, world fact or moral judgment is established.'))
    return dict(answer=answer, answer_raw=raw, source_citation_audit=audit,
        prepared=entry, actual_final_messages=messages, answer_adapter_calls=1,
        preparation_provider_calls=entry.receipt['extraction_calls'])
