"""Shared source revision drives real retained cognition, with bounded legacy entry.

A01 deliberately reuses the v1 ordinary grammar. A02 supplies the extensible
semantic entry. This adapter must not claim broad language understanding.
"""
from dataclasses import dataclass
import json

from hcl.v1 import HCLCognitionLayer, prepare_person_context
from .core import ClaimKind, EvidenceCore, Scope, identity


@dataclass(frozen=True)
class OperationResult:
    id: str
    query: str
    scope: Scope
    source_versions: tuple[tuple[str, int], ...]
    claim_ids: tuple[str, ...]
    messages_json: str
    preparation_json: str

    @property
    def messages(self):
        return json.loads(self.messages_json)

    def current_messages(self, workspace):
        """Answer only from the current, unchallenged source dependencies."""
        if (any(s not in workspace._documents or workspace._versions[s] != v
                for s, v in self.source_versions)
                or any(workspace.core.support_statuses().get(k) != 'SUPPORT_AVAILABLE'
                       for k in self.claim_ids)):
            raise ValueError('prepared support changed; recompute before answering')
        return self.messages


class CognitionWorkspace:
    def __init__(self):
        self.core = EvidenceCore()
        self._documents = {}
        self._versions = {}
        self._spans = {}
        self._version_spans = {}
        self._cache = {}
        self.executions = 0

    def put_source(self, source_id, text, *, permitted_observers=()):
        """Authorized analyst source, not evidence that any character received it."""
        if source_id in self._documents and self._documents[source_id] == (text, permitted_observers):
            return frozenset()
        version = self._versions.get(source_id, 0) + 1
        # Validate before withdrawing any previous version.
        span = self.core.add_span(text, source_id=source_id, version=version,
            permitted_observers=permitted_observers, order=max(1, len(text.splitlines())))
        invalidated = frozenset().union(*(self.core.withdraw(k)
            for k in self._version_spans.get(source_id, ())))
        self._version_spans[source_id] = {span}
        self._documents[source_id] = (text, permitted_observers)
        self._versions[source_id] = version
        self._spans[source_id] = span
        return invalidated

    def remove_source(self, source_id):
        invalidated = frozenset().union(*(self.core.withdraw(k)
            for k in self._version_spans.pop(source_id)))
        self._spans.pop(source_id)
        del self._documents[source_id]
        return invalidated

    def prepare(self, query, *, source_ids, through_order=None):
        """Reader analysis only: exact v1 actor/access semantics stay in the adapter.

        Whole selected documents are read dependencies, including absent evidence.
        Adding text to one of them must invalidate the result even when it had no
        positive support before. Unselected source changes do not rerun it.
        """
        if not isinstance(source_ids, tuple) or not 1 <= len(source_ids) <= 4 or len(set(source_ids)) != len(source_ids):
            raise ValueError('one to four distinct ordered authorized sources required')
        if any(s not in self._documents for s in source_ids):
            raise ValueError('missing source cannot reuse a stale result')
        if through_order is not None and (len(source_ids) != 1 or type(through_order) is not int or through_order < 1):
            raise ValueError('statement snapshot requires one source and positive order')
        if through_order is not None:
            lines = self._documents[source_ids[0]][0].splitlines(keepends=True)
            if through_order > len(lines) or any(not line.strip() for line in lines):
                raise ValueError('snapshot requires unambiguous nonempty source lines')
        key = identity('operation', query, source_ids, through_order)
        versions = tuple((s, self._versions[s]) for s in source_ids)
        prior = self._cache.get(key)
        if prior and prior.source_versions == versions:
            return prior
        narrative = '\n'.join(self._documents[s][0] for s in source_ids)
        # No provider is created: prepare_person_context only prepares inputs.
        prepared = prepare_person_context(HCLCognitionLayer(lambda _: None), query,
            narrative, as_of_statement=through_order)
        prep = prepared.preparation_receipt
        selected = prep.get('question_entrypoint', {}).get('scope', {})
        scope = Scope(actor=selected.get('actor'), context=selected.get('context'),
            source_ids=source_ids, through_order=through_order)
        # Generic complete-source paths have no legacy context object. Preserve
        # the actual wire state as preparation, never a private-state verdict.
        stages = getattr(prepared, 'stages', (prepared,))
        states = []
        for stage in stages:
            if stage.context is not None:
                states.append((stage.context.as_dict(),
                    'RETAINED_V1_SOURCE_SCOPED_NOT_PRIVATE_OR_WORLD_TRUTH'))
            else:
                if len(source_ids) != 1:
                    raise ValueError('generic cognition across documents requires explicit identity binding')
                payload = json.loads(stage.messages[-1]['content'])
                if not isinstance(payload, dict) or not isinstance(payload.get('sources'), list):
                    raise ValueError('complete reader prepared payload required')
                states.append((payload,
                    'PREPARED_READER_SOURCE_STATE_NOT_PRIVATE_OR_WORLD_TRUTH'))
        # The legacy entry uses artificial timestamps solely for source order.
        # No calendar/knowledge time is inferred into the shared scope.
        roots = []
        for source in source_ids:
            roots.append(self.core.claim(scope, ClaimKind.SOURCE_REPORT,
                dict(source_id=source, version=self._versions[source], authority='CALLER_AUTHORIZED_TEXT')))
            span = self._spans[source]
            if through_order is not None:
                text = self._documents[source][0]
                lines = text.splitlines(keepends=True)
                end = sum(len(line) for line in lines[:through_order])
                span = self.core.add_span(text, source_id=source, version=self._versions[source],
                    end=end, order=through_order, permitted_observers=self._documents[source][1])
                self._version_spans[source].add(span)
            self.core.support(roots[-1], span)
        claims = []
        for index, (state, boundary) in enumerate(states):
            result = self.core.claim(scope, ClaimKind.SYSTEM_INTERPRETATION,
                dict(operation_index=index, state=state, source_versions=versions,
                     semantic_boundary=boundary))
            self.core.support(result, *roots)
            self.core.interpret(result, required_premises=tuple(roots),
                unknown_conditions=('calendar_and_receipt_time_not_established',))
            claims.append(result)
        self.executions += 1
        result = OperationResult(key, query, scope, versions, tuple(claims),
            json.dumps(prepared.messages, ensure_ascii=False, sort_keys=True),
            json.dumps(prep, ensure_ascii=False, sort_keys=True))
        self._cache[key] = result
        return result

    def answer(self, query, answer_backend, *, source_ids, through_order=None):
        """One final answer call from current ordinary source preparation."""
        result = self.prepare(query, source_ids=source_ids, through_order=through_order)
        messages = result.current_messages(self)
        answer = (answer_backend.complete(messages) if hasattr(answer_backend, 'complete')
                  else answer_backend(messages))
        return dict(answer=answer, prepared=result, answer_adapter_calls=1,
                    actual_final_messages=messages, preparation_provider_calls=0)

    def answer_source_guarded(self, query, answer_backend, *, source_ids, through_order=None):
        """Zero-extraction whole-reader answer with actual source IDs/raw preserved."""
        from .retained import original_sources_from_messages, audit_supplied_source_citations
        result=self.prepare(query,source_ids=source_ids,through_order=through_order)
        messages=result.current_messages(self)
        # Unsupported source-frame layouts fail before a final transport call.
        original_sources_from_messages(messages)
        messages=[*messages,dict(role='system',content='Return exactly answer, source_citations, uncertainty and assumptions in one JSON object. Quote only supplied original sources; no private, world or moral truth is established by a source citation.')]
        raw=(answer_backend.complete(messages) if hasattr(answer_backend,'complete') else answer_backend(messages))
        audit=audit_supplied_source_citations(messages,raw)
        try: result.current_messages(self)
        except ValueError: audit.update(status='STALE_OR_CHALLENGED_SUPPORT',deliverable=False)
        answer=raw if audit['deliverable'] else json.dumps(dict(
            answer='I cannot support this answer from the supplied text.',source_citations=[],
            uncertainty='The returned answer did not preserve reliable current source references.',
            assumptions='No private state, world fact or moral judgment is established.'))
        return dict(answer=answer,answer_raw=raw,source_citation_audit=audit,prepared=result,
            answer_adapter_calls=1,actual_final_messages=messages,preparation_provider_calls=0)

    def prepare_semantic(self, query, *, source_ids, observer=None, backend=None):
        """Unified source preparation; access filtering precedes any backend call."""
        from .semantic import AuthorizedText, prepare_semantics
        if (not isinstance(source_ids, tuple)
                or len(set(source_ids)) != len(source_ids)
                or any(s not in self._documents for s in source_ids)):
            raise ValueError('distinct registered sources required')
        sources = tuple(AuthorizedText(s, self._documents[s][0], self._versions[s],
            self._documents[s][1], index) for index, s in enumerate(source_ids, 1))
        result = prepare_semantics(query, sources, core=self.core,
            scope=Scope(observer=observer, source_ids=source_ids), backend=backend)
        if any(s.source_id not in self._documents or self._versions[s.source_id] != s.version for s in sources):
            # A callback/concurrent revision must not relabel old candidates with
            # the new source version or leave their support active.
            for root_id in result.root_ids:
                for supports in self.core.dependencies[root_id]:
                    for span in supports:
                        self.core.withdraw(span)
            raise ValueError('source changed during semantic preparation')
        for root_id in result.root_ids:
            for supports in self.core.dependencies[root_id]:
                for span in supports:
                    source_id = self.core.spans[span].source_id
                    self._version_spans[source_id].add(span)
        return result

    def prepare_reader_semantic(self, query, *, source_ids, observer=None,
                                backend=None, max_chars=64000, compact_context=False):
        """Ordinary source analysis with explicitly conditional translations."""
        from .retained import prepare_retained_reader
        return prepare_retained_reader(self, query, source_ids=source_ids,
            observer=observer, backend=backend, max_chars=max_chars, compact_context=compact_context)

    def answer_reader_semantic(self, query, answer_backend, *, source_ids,
                               observer=None, backend=None, max_chars=64000, compact_context=False):
        """Bounded opt-in extraction, then one current final answer; no retries."""
        from .retained import answer_retained_reader
        return answer_retained_reader(self, query, answer_backend, source_ids=source_ids,
            observer=observer, backend=backend, max_chars=max_chars, compact_context=compact_context)

    def receipt(self, result):
        return dict(schema='hcl-shared-operation-v1', operation_id=result.id,
            source_versions=list(result.source_versions), claim_ids=list(result.claim_ids),
            current=(all(self._versions.get(s) == v and s in self._documents for s, v in result.source_versions)
                and all(self.core.support_statuses().get(k) == 'SUPPORT_AVAILABLE' for k in result.claim_ids)),
            actual_final_messages=result.messages, core=self.core.receipt(result.scope),
            provider_calls=0, evidence_level='CORRECTNESS_ONLY',
            ordinary_input=json.loads(result.preparation_json).get('method', 'SOURCE_SCOPED_PROVIDER_FREE'),
            calendar_time='NOT_ESTABLISHED')

    def prepare_reader_entry(self, query, *, source_ids, backend=None,
                             max_chars=64000, compact_context=True, allow_translation=False):
        """Adaptive ordinary analyst entry; local checks before optional extraction."""
        from .reader_entry import prepare_reader_entry
        return prepare_reader_entry(self, query, source_ids=source_ids, backend=backend,
            max_chars=max_chars, compact_context=compact_context, allow_translation=allow_translation)

    def answer_reader_entry(self, query, answer_backend, **kwargs):
        """One final answer from the selected, current source-bearing reader state."""
        from .reader_entry import answer_reader_entry
        return answer_reader_entry(self, query, answer_backend, **kwargs)
