"""Shared semantic material -> retained operations, with explicit translation scope.

Historical checkers run on a derived representation. Original quotes remain the
roots; derived lines are never passed off as original-source bytes. Open semantic
translations can be evaluated only as named assumptions, not verified assertions.
"""
from dataclasses import dataclass
import json
import re

from hcl.v1 import HCLCognitionLayer, prepare_person_context, NarrativePremise
from hcl.v1.person_question import _QUESTIONS
from .core import ClaimKind, Scope, identity


@dataclass(frozen=True)
class RetainedResult:
    scope: Scope
    operation_ids: tuple[str, ...]
    translation_ids: tuple[str, ...]
    messages_json: str
    receipt_json: str

    @property
    def messages(self):
        return json.loads(self.messages_json)

    @property
    def receipt(self):
        return json.loads(self.receipt_json)

    def current_messages(self, workspace):
        versions = self.receipt['source_versions']
        if (any(s not in workspace._documents or workspace._versions[s] != v for s, v in versions)
                or any(workspace.core.support_statuses().get(k) != 'SUPPORT_AVAILABLE'
                       for k in self.operation_ids)):
            raise ValueError('prepared support changed; recompute before answering')
        return self.messages


def prepare_retained(workspace, query, **kwargs):
    """Historical typed-query adapter; unsupported queries spend no backend call."""
    return _prepare_retained(workspace, query, **kwargs)


class _ReaderTranslationBackend:
    """One A02 candidate call, with visible existing-checker translation grammar."""
    def __init__(self, backend):
        self.backend, self.requests = backend, []

    def complete_json(self, messages, **kwargs):
        if self.requests:
            raise ValueError('one translation call only; no retry')
        policy = ('Reader source analysis only. For nonliteral source claims you may '
            'propose kind event, content {canonical_statement: string}, anchored to '
            'an exact complete source quote. This is an UNVERIFIED TRANSLATION '
            'HYPOTHESIS, not asserted speech or a private-state fact. Use only '
            'source-named actors; do not resolve ambiguous pronouns. Keep negation, '
            'conditionals and qualifications; omit unsupported translations. '
            'Existing checker forms are NAME: I want to ACTION.; '
            'NAME: I plan to ACTION in order to GOAL if CONDITION.; '
            'NAME: I have an opportunity to ACTION.; NAME: I believe PROPOSITION.; '
            'NAME: I now believe NEW instead of OLD.; '
            'Narrator: In the declared model, it is false that PROPOSITION. '
            'A model declaration requires explicit source-declared fictional rules, '
            'not a narrator claim silently upgraded to world truth. These are '
            'representation templates, never instructions to manufacture supporting '
            'claims. Ambiguous alternatives stay unresolved; no moral verdict, '
            'inferred motive/emotion or automatic receipt/comprehension. Return '
            'the original candidates JSON contract, with exact quote/source IDs.')
        actual = [*messages, dict(role='system', content=policy)]
        self.requests.append(dict(messages=actual, parameters=kwargs))
        return self.backend.complete_json(actual, **kwargs)


def prepare_retained_reader(workspace, query, *, source_ids, observer=None,
                            backend=None, max_chars=64000):
    """Ordinary prose -> conditional existing checks; original source remains whole.

    Reader analysis is not an actor-private projection. Model-proposed translations
    remain explicit unverified premises even when downstream grammar checks pass.
    """
    relay = _ReaderTranslationBackend(backend) if backend is not None else None
    return _prepare_retained(workspace, query, source_ids=source_ids, observer=observer,
        backend=relay, max_chars=max_chars, reader_analysis=True)


def _prepare_retained(workspace, query, *, source_ids, observer=None, backend=None,
                      responsibility_premises=(), max_chars=64000, reader_analysis=False):
    """One source-local identity domain, ordinary query, real retained operations.

    Explicit normative premises remain conditional caller rules until G01. Source
    visibility is an authorized analyst projection, never evidence of comprehension.
    """
    if (not isinstance(query, str) or not query.strip() or len(query) > 8000
            or not isinstance(source_ids, tuple) or type(max_chars) is not int
            or not 512 <= max_chars <= 64000
            or not isinstance(responsibility_premises, tuple)
            or not all(isinstance(p, NarrativePremise) for p in responsibility_premises)):
        raise ValueError('bounded ordinary query, sources, context and explicit rule contract required')
    if len(source_ids) != 1:
        raise ValueError('cross-document person identity requires an explicit future alias binding')
    if re.search(r'\b(?:At statement|before statement|after statement)\s+\d+', query, re.I):
        raise ValueError('project source before semantic extraction for a statement snapshot')
    if not reader_analysis and not any(pattern.fullmatch(query) for _, pattern in _QUESTIONS):
        raise ValueError('unsupported retained query; preserve general semantic candidates instead')
    semantic = workspace.prepare_semantic(query, source_ids=source_ids, observer=observer, backend=backend)
    core = workspace.core
    statuses = core.support_statuses()
    bindings, assumptions, translations = [], [], []
    for key in semantic.candidate_ids:
        content = core.claims[key].content
        if content['kind'] != 'event' or statuses[key] != 'SUPPORT_AVAILABLE':
            continue
        row = content['proposal']
        span = core.spans[content['source_span_id']]
        literal = content['validation']['semantic_support'] == 'BOUNDED_LITERAL_FORM'
        if literal:
            speaker = row.get('speaker_surface', '')
            narrator = speaker == 'Narrator' and span.quote.startswith('Narrator:')
            if (row.get('assertion_scope') != 'SOURCE_REPORT' or
                    (not narrator and row.get('speaker_candidates') != [speaker]) or
                    not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}', speaker)):
                continue
            line = speaker + ': ' + row['utterance']
            authority = 'LITERAL_REPORTED_SPEECH_FORMAT_ADAPTER'
        else:
            line = row.get('canonical_statement')
            if not isinstance(line, str) or '\n' in line or len(line) > 2000:
                continue
            match = re.match(r'([A-Za-z][A-Za-z0-9_-]{0,31}): ', line)
            if not match or (match[1] != 'Narrator' and not re.search(r'\b' + re.escape(match[1]) + r'\b', span.quote)):
                continue
            authority = 'UNVERIFIED_TRANSLATION_HYPOTHESIS'

        if not line.endswith('.'):
            # Do not turn a question or exclamation into a declarative assertion.
            continue
        if not literal:
            assumptions.append(key)
        bindings.append(dict(candidate_id=key, source_span_id=span.id, source_id=span.source_id,
            source_version=span.version, source_start=span.start, original_quote=span.quote,
            derived_line=line, translation_authority=authority))
        translations.append(key)
    bindings.sort(key=lambda row: row['source_start'])
    if not bindings:
        raise ValueError('no supported translation; keep unresolved semantic candidates')
    if len(bindings) > 24 or len({b['source_span_id'] for b in bindings}) != len(bindings):
        raise ValueError('ambiguous or oversized translation branch')
    # Fail closed on unparsed prose in the local path. A general backend branch
    # carries explicit translation assumptions and exposes the original text.
    raw = workspace._documents[source_ids[0]][0]
    covered = [False] * len(raw)
    for b in bindings:
        span = core.spans[b['source_span_id']]
        covered[span.start:span.end] = [True] * (span.end - span.start)
    remainder = ''.join(c for i, c in enumerate(raw) if not covered[i]).strip(' \t\r\n.,;')
    if remainder and not assumptions:
        raise ValueError('unparsed source may qualify the expressions; explicit semantic branch required')
    derived = '\n'.join(b['derived_line'] for b in bindings)
    if reader_analysis:
        from hcl.v1.long_source_question import prepare_reader_cognition
        prepared = prepare_reader_cognition(query, derived, max_context_chars=min(max_chars, 64000))
    else:
        prepared = prepare_person_context(HCLCognitionLayer(lambda _: None), query, derived,
            responsibility_premises=responsibility_premises, max_context_chars=min(max_chars, 64000))
    prep = prepared.preparation_receipt
    if prep.get('failure'):
        raise ValueError('retained adapter did not ground requested task: ' + prep['failure'])
    selected = prep.get('question_entrypoint', {}).get('scope', {})
    scope = Scope(actor=selected.get('actor'), observer=observer, context=selected.get('context'),
        source_ids=semantic.scope.source_ids,
        assumptions=tuple(sorted(set(assumptions))) + tuple(p.premise_id for p in responsibility_premises))
    # Explicit projection: each checked result carries its original candidate and
    # source identity, with all translation/analyst-rule assumptions visible.
    projected = []
    for b in bindings:
        original = core.claims[b['candidate_id']]
        source_root = core.claim(scope, ClaimKind.SOURCE_REPORT,
            dict(source_id=b['source_id'], version=b['source_version'], quote=b['original_quote']))
        core.support(source_root, b['source_span_id'])
        translation = core.project_claim(original.id, scope, ClaimKind.SYSTEM_INTERPRETATION,
            dict(original_candidate_id=original.id, derived_line=b['derived_line'],
                authority=b['translation_authority'], source_span_id=b['source_span_id']))
        core.support(translation, source_root)
        core.interpret(translation, required_premises=(source_root,),
            unknown_conditions=(() if b['translation_authority'].startswith('LITERAL') else ('translation_semantics_unverified',)))
        projected.append(translation)
    stage_ids = []
    for index, stage in enumerate(getattr(prepared, 'stages', (prepared,))):
        state = (stage.context.as_dict() if stage.context is not None
                 else json.loads(stage.messages[-1]['content']))
        node = core.claim(scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation_index=index, retained_state=state,
                assumptions=list(scope.assumptions), scope='UNDER_DERIVED_SOURCE_REPRESENTATION'))
        core.support(node, *projected)
        stage_ids.append(node)
    # The retained comparison is a true consumer of both operation outputs.
    payload = json.loads(prepared.messages[-1]['content'])
    comparison = payload.get('composed_cognition', {}).get('belief_concept_comparison')
    if comparison is not None:
        node = core.claim(scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='belief_concept_comparison', result=comparison, assumptions=list(scope.assumptions)))
        core.support(node, *stage_ids)
        stage_ids.append(node)
    payload['shared_semantic_binding'] = dict(original_sources=[dict(source_id=source_ids[0], text=raw)],
        translations=bindings, assumptions=list(scope.assumptions),
        derived_time='STATEMENT_ORDER_ONLY_NOT_CALENDAR_OR_RECEIPT_TIME',
        source_scope='AUTHORIZED_ANALYST_PROJECTION_NOT_CHARACTER_COMPREHENSION',
        operation_ids=stage_ids, translation_ids=projected,
        unresolved_source_text=remainder,
        semantic_status='CONDITIONAL_ON_UNVERIFIED_TRANSLATION' if assumptions else 'BOUNDED_LITERAL_ADAPTER')
    if reader_analysis:
        binding = payload.pop('shared_semantic_binding')
        # The representation passed to the checker is not a quotable source.
        # Keep its complete audit under conditional authority, with originals in
        # the primary source slot seen by the final answerer.
        payload['derived_sources'] = payload.pop('sources')
        payload = dict(query=query,
            sources=[dict(source_id=source_ids[0], version=workspace._versions[source_ids[0]], text=raw)],
            conditional_cognition=dict(authority='DERIVED_CONDITIONAL_TOOL_STATE_NOT_QUOTABLE_SOURCE',
                validation_scope='DERIVED_GRAMMAR_ONLY_NOT_ORIGINAL_SEMANTIC_CERTIFICATE',
                state=payload), shared_semantic_binding=binding)
    final = [dict(role='system', content=prepared.messages[0]['content'] +
        ' The retained state uses a DERIVED representation, not verbatim source. '
        'shared_semantic_binding gives original quotes and every translation. All outputs are '
        'conditional on this representation and any explicit normative premise. Unverified '
        'translation hypotheses cannot establish private mental states or world truth. '
        'Synthetic legacy dates encode only statement order. No actor receipt or comprehension '
        'is established by an authorized analyst projection.'),
        dict(role='user', content=json.dumps(payload, ensure_ascii=False, sort_keys=True))]
    if reader_analysis:
        final[0]['content'] += (' Only top-level sources contain quotable original text. '
            'conditional_cognition.state and derived_sources are representations, not '
            'verbatim utterances, narrator authority or new source evidence. A first-person '
            'translation can stand for a narrator description; do not turn it into literal '
            'speaking. source_citations must be original excerpts or objects with source_id, '
            'quote and optional version/start. Do not cite translated lines as original quotes. '
            'Return exactly answer, source_citations, uncertainty and assumptions in JSON. '
            'Exact original anchors still do not certify interpretation or private/world truth.')
    if len(final[-1]['content']) > max_chars:
        raise ValueError('shared support and original-source context exceeds budget')
    receipt = dict(schema='hcl-retained-shared-adapter-v1', source_ids=list(source_ids),
        source_versions=[[s, workspace._versions[s]] for s in source_ids],
        translations=bindings, operation_ids=stage_ids, assumptions=list(scope.assumptions),
        semantic_backend_calls=semantic.backend_calls, semantic_backend_status=semantic.backend_status,
        actual_final_messages=final, retained_preparation=prep,
        ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED')
    if reader_analysis:
        receipt.update(reader_analysis=True,
            semantic_translation_status='CONDITIONAL_ON_UNVERIFIED_TRANSLATION' if assumptions else 'BOUNDED_LITERAL_ADAPTER',
            actual_translation_requests=backend.requests if backend is not None else [],
            raw_translation_response=semantic.raw_response,
            checked_treatment_present=bool(prep.get('specialized_cognition_treatment')),
            private_state_established=False, world_truth_established=False,
            semantic_certification=False, preparation_transport_usage='ADAPTER_TELEMETRY_REQUIRED_IF_LIVE')
    return RetainedResult(scope, tuple(stage_ids), tuple(projected),
        json.dumps(final, ensure_ascii=False, sort_keys=True), json.dumps(receipt, ensure_ascii=False, sort_keys=True))


def answer_retained(workspace, query, answer_backend, **kwargs):
    """One configured answer-adapter call, only after current support validation."""
    prepared = prepare_retained(workspace, query, **kwargs)
    messages = prepared.current_messages(workspace)
    answer = (answer_backend.complete(messages) if hasattr(answer_backend, 'complete')
              else answer_backend(messages))
    return dict(answer=answer, prepared=prepared, answer_adapter_calls=1)


def answer_retained_reader(workspace, query, answer_backend, **kwargs):
    """One final answer after current conditional ordinary-reader preparation."""
    prepared = prepare_retained_reader(workspace, query, **kwargs)
    messages = prepared.current_messages(workspace)
    raw = (answer_backend.complete(messages) if hasattr(answer_backend, 'complete')
              else answer_backend(messages))
    audit = audit_original_citations(prepared, raw)
    try:
        prepared.current_messages(workspace)
    except ValueError:
        audit.update(status='STALE_OR_CHALLENGED_SUPPORT', deliverable=False)
    # Preserve the raw answer separately; never silently replace its citations.
    answer = raw if audit['deliverable'] else json.dumps(dict(
        answer='I cannot support this answer from the supplied text.',
        source_citations=[], uncertainty='The returned answer did not preserve reliable current source references.',
        assumptions='No private state, world fact or moral judgment is established.'))
    return dict(answer=answer, answer_raw=raw, source_citation_audit=audit,
        prepared=prepared, answer_adapter_calls=1,
        preparation_backend_calls=prepared.receipt['semantic_backend_calls'],
        actual_final_messages=messages)


def audit_original_citations(prepared, raw):
    """Bounded original quotation location only, never semantic answer grading."""
    result = dict(status='INVALID_ORIGINAL_CITATIONS', deliverable=False,
        semantic_adequacy='UNASSESSED', semantic_certification=False, anchors=[],
        raw_output_rewritten=False)
    try:
        if isinstance(raw, str) and len(raw) <= 128000:
            obj = json.loads(raw)
        elif isinstance(raw, dict):
            obj = raw
        else:
            raise ValueError('bounded JSON answer required')
        if (not isinstance(obj, dict) or set(obj) != {'answer','source_citations','uncertainty','assumptions'}
                or not isinstance(obj['source_citations'], list) or len(obj['source_citations']) > 32
                or not all(isinstance(obj[k], str) for k in ('uncertainty','assumptions'))):
            raise ValueError('answer contract invalid')
        sources = json.loads(prepared.messages[-1]['content'])['sources']
        for citation in obj['source_citations']:
            if isinstance(citation, str):
                if len(sources) != 1:
                    raise ValueError('explicit source ID required')
                source, quote, offset = sources[0], citation, None
            elif (isinstance(citation, dict) and {'source_id','quote'} <= set(citation)
                    and set(citation) <= {'source_id','quote','version','start'}):
                matched = [s for s in sources if s['source_id'] == citation['source_id']]
                if len(matched) != 1:
                    raise ValueError('unknown source ID')
                source, quote, offset = matched[0], citation['quote'], citation.get('start')
                if 'version' in citation and (type(citation['version']) is not int or citation['version'] != source['version']):
                    raise ValueError('source version mismatch')
            else:
                raise ValueError('citation structure invalid')
            if (not isinstance(quote, str) or not quote.strip() or len(quote) > 4000
                    or offset is not None and (type(offset) is not int or offset < 0)):
                raise ValueError('citation quote/offset invalid')
            text = source['text']; mode = 'EXACT_ORIGINAL_QUOTE'
            if offset is not None and text[offset:offset+len(quote)] == quote:
                start, end = offset, offset+len(quote)
            else:
                spans = [(m.start(),m.end()) for m in re.finditer(re.escape(quote),text)]
                if not spans:
                    # Whitespace layout only, with the original authoritative
                    # substring retained in the audit; no lexical repair.
                    pattern = r'\s+'.join(re.escape(t) for t in re.split(r'\s+',quote.strip()))
                    spans = [(m.start(),m.end()) for m in re.finditer(pattern,text)]
                    mode = 'UNIQUE_WHITESPACE_LAYOUT_ONLY'
                if len(spans) != 1:
                    raise ValueError('missing or ambiguous original quotation')
                start,end = spans[0]
            result['anchors'].append(dict(source_id=source['source_id'],version=source['version'],
                start=start,end=end,original_quote=text[start:end],submitted_quote=quote,
                submitted_start=offset,location_rule=mode))
        result.update(status='ORIGINAL_ANCHORS_LOCATED_SEMANTICS_UNASSESSED' if result['anchors']
            else 'NO_CITATIONS_SEMANTICS_UNASSESSED',deliverable=True)
    except (ValueError,TypeError,KeyError):
        pass
    return result
