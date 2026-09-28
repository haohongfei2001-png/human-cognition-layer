"""Incremental actor-visible ordinary scene composition for retained cognition."""
from dataclasses import asdict, dataclass
import json

from hcl.v1.person_question import _QUESTIONS
from hcl.v1 import NarrativePremise
from .communication import CommunicationScene
from .core import identity
from .epistemic import _query_path, prepare_epistemic
from .retained import prepare_retained
from .workspace import CognitionWorkspace

_POLICY = ('This is an explicitly selected observer information view, not an omniscient '
    'scene. Source-reported receipt does not establish comprehension, acceptance or '
    'private belief. Keep each mental holder, reported concept criterion and conditional '
    'responsibility premise separate. Compare attributions with subject reports only '
    'when both are visible; do not infer hidden beliefs. Narrator records require '
    'explicit access before entering this view. Times encode visible statement order '
    'only, not calendar time. Normative premises are analyst conditions, not moral truth.')


@dataclass(frozen=True)
class IntegratedSceneResult:
    observer: str
    source_id: str
    source_version: int
    visible_fingerprint: str
    messages_json: str
    claim_ids: tuple[str, ...]
    operations: tuple[str, ...]

    def current_messages(self, scene):
        view, workspace = scene._view(self.observer)
        if (identity('visible-input', view.visible_text) != self.visible_fingerprint or
                workspace._versions.get(self.source_id, 0) != self.source_version):
            raise ValueError('observer evidence changed; recompute before answering')
        status = workspace.core.support_statuses()
        if any(status.get(key) != 'SUPPORT_AVAILABLE' for key in self.claim_ids):
            raise ValueError('integrated support is no longer available')
        return json.loads(self.messages_json)


class IntegratedScene:
    """Cache by observer-visible source, not global scene revision or hidden text."""
    def __init__(self, narrative, *, source_id='integrated-scene'):
        self._scene = CommunicationScene(narrative, source_id=source_id)
        self._workspaces, self._views, self._cache = {}, {}, {}
        self.executions = {}

    def _view(self, observer):
        if observer not in self._views:
            view = self._scene.view(observer)
            workspace = CognitionWorkspace()
            if view.events:
                workspace.put_source(view.source_id, view.visible_text, permitted_observers=(observer,))
            self._views[observer], self._workspaces[observer] = view, workspace
        return self._views[observer], self._workspaces[observer]

    def update(self, narrative):
        replacement = CommunicationScene(narrative, source_id=self._scene.source_id)
        # Validate every previously requested observer before any local mutation.
        projected = {actor: replacement.view(actor) for actor in self._views}
        changed = []
        for actor, view in projected.items():
            old = self._views[actor]
            if old.visible_text != view.visible_text:
                workspace = self._workspaces[actor]
                if view.events:
                    workspace.put_source(view.source_id, view.visible_text, permitted_observers=(actor,))
                elif old.events:
                    workspace.remove_source(old.source_id)
                changed.append(actor)
            self._views[actor] = view
        self._scene = replacement
        return tuple(sorted(changed))

    def prepare(self, observer, queries, *, responsibility_premises=(), max_chars=64000):
        if (not isinstance(queries, tuple) or not 1 <= len(queries) <= 4
                or len(set(queries)) != len(queries)
                or any(not isinstance(q, str) or not q.strip() or len(q) > 8000 for q in queries)
                or not isinstance(responsibility_premises, tuple)
                or not all(isinstance(p, NarrativePremise) for p in responsibility_premises)
                or type(max_chars) is not int or not 2000 <= max_chars <= 128000):
            raise ValueError('bounded distinct ordinary questions, explicit premises and context budget required')
        routes = []
        for query in queries:
            path = _query_path(query)
            if path:
                if len(path) > 3:
                    raise ValueError('integrated mental-depth budget exceeded')
                routes.append('epistemic')
            elif any(pattern.fullmatch(query) for _, pattern in _QUESTIONS):
                routes.append('retained')
            else:
                raise ValueError('unsupported ordinary integrated question')
        responsibility_queries = {q for q in queries if any('responsibility' in kind and pattern.fullmatch(q) for kind, pattern in _QUESTIONS)}
        if responsibility_premises and not responsibility_queries:
            raise ValueError('premises require an explicit responsibility question')
        view, workspace = self._view(observer)
        fingerprint = identity('visible-input', view.visible_text)
        version = workspace._versions.get(view.source_id, 0)
        key = identity('integrated-request', observer, fingerprint, version, queries,
            [asdict(p) for p in responsibility_premises], max_chars)
        if key in self._cache:
            result = self._cache[key]
            result.current_messages(self)
            return result
        source_ids = (view.source_id,) if view.events else ()
        operations, supports = [], []
        for route, query in zip(routes, queries):
            if route == 'epistemic':
                bundle = prepare_epistemic(workspace, query, source_ids=source_ids,
                    observer=observer, max_depth=4)
                messages = bundle.messages(workspace.core, query)
                payload = json.loads(messages[-1]['content'])
                supports.extend(r.expression_id for r in bundle.records)
                supports.extend(row['claim_id'] for row in payload['comparisons'])
                operations.append(dict(operation='SCOPED_EPISTEMIC_COMPARISON', query=query,
                    cognitive_state=payload, operation_policy=messages[0]['content']))
            elif source_ids:
                try:
                    retained = prepare_retained(workspace, query, source_ids=source_ids, observer=observer,
                        responsibility_premises=responsibility_premises if query in responsibility_queries else (), max_chars=min(max_chars, 64000))
                except ValueError as exc:
                    if not str(exc).startswith('retained adapter did not ground requested task:'):
                        raise
                    operations.append(dict(operation='RETAINED_TASK_NOT_GROUNDED', query=query,
                        cognitive_state={'status': 'SYSTEM_INSUFFICIENT', 'reason': str(exc)}))
                    continue
                messages = retained.current_messages(workspace)
                supports.extend(retained.operation_ids)
                operations.append(dict(operation='RETAINED_CONDITIONAL_CHECK', query=query,
                    cognitive_state=json.loads(messages[-1]['content']), operation_policy=messages[0]['content']))
            else:
                operations.append(dict(operation='MISSING_OBSERVER_EVIDENCE', query=query,
                    cognitive_state={'status': 'SYSTEM_INSUFFICIENT'}))
        payload = dict(observer=observer, source_id=view.source_id, visible_source=view.visible_text,
            source_version=version, operations=operations,
            receipt=[dict(event_id=e.event_id, text=e.raw_text,
                source_kind='EXPLICIT_NARRATOR_RECORD' if e.metadata['narrator'] else 'REPORTED_SPEECH',
                access_state=e.metadata['access_state'], time_semantics=e.metadata['time_semantics']) for e in view.events],
            comprehension='NOT_ESTABLISHED', acceptance='NOT_ESTABLISHED', provider_calls=0)
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(payload,
            ensure_ascii=False, sort_keys=True))]
        wire = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        if len(wire) > max_chars:
            raise ValueError('integrated context exceeds budget; narrow questions, no silent truncation')
        result = IntegratedSceneResult(observer, view.source_id, version, fingerprint, wire,
            tuple(sorted(set(supports))), tuple(routes))
        self._cache[key] = result
        self.executions[observer] = self.executions.get(observer, 0) + 1
        return result

    def answer(self, observer, queries, answer_backend, **kwargs):
        result = self.prepare(observer, queries, **kwargs)
        messages = result.current_messages(self)
        answer = answer_backend(messages)  # One configured call, no retry or provider construction.
        return dict(answer=answer, actual_final_messages=messages,
            observer=observer, operations=result.operations, answer_adapter_calls=1)
