"""Source-bound entry syntax, shared by planner exposure and plan admission.

These are necessary input conditions, never native results or semantic judgments.
No workspace, claim, backend, provider, or evaluation-case metadata is consulted.
"""
from dataclasses import asdict

from .agency import _PLAN, is_agency_utterance
from .capability_catalog import CATALOG, READER_BRIDGE_CAPABILITIES
from .entry_readiness import literal_entry_blockers
from .epistemic import _PREDICATE
from .semantic import AuthorizedText, _SCRIPT, _local_candidates


class EntryContractError(ValueError):
    """Code-owned admission failure; contains no source or provider content."""


def _literal_conditions(source):
    """Reuse actual candidate syntax; a positive result does not mean treatment.

    B01/C01/C03 use the ordinary reader's dialogue/narrator candidate surface.
    C02 uses the standalone explanation adapter's default candidate surface.
    Broad necessary predicates deliberately leave relevance, scope, actor, query,
    action-time joins and native bounds to the real execution and final audit.
    """
    text = source['text']
    authorized = AuthorizedText(source['source_id'], text, version=source['version'])
    reader = [row['content'] for row in _local_candidates(authorized,
        dialogue_blocks=bool(_SCRIPT.search(text)), narrator_reports=True)
        if row['kind'] == 'event']
    explanation = [row for row in _local_candidates(authorized) if row['kind'] == 'event']
    utterances = [row.get('utterance', '').rstrip('.!?').strip() for row in reader]
    return {
        'B01': any(_PREDICATE.fullmatch(body) for body in utterances),
        'C01': any(is_agency_utterance(body) for body in utterances),
        'C02': bool(explanation),
        'C03': any(match and match['condition'] for body in utterances
                   for match in [_PLAN.fullmatch(body)]),
    }


def executable_entry_contract(sources, *, require_checked=False):
    """A code-owned, version-bound contract for both ordinary and strict callers."""
    blockers = literal_entry_blockers(sources)
    entries = []
    for source_index, source in enumerate(sources):
        conditions = _literal_conditions(source)
        blocked = {row['capability']: row['reason'] for row in blockers
                   if row['source_id'] == source['source_id'] and row['version'] == source['version']}
        entries.append(dict(source_index=source_index, version=source['version'],
            literal_syntax_capabilities=[cid for cid, present in conditions.items() if present],
            source_entry_blockers=blocked))
    return dict(schema='hcl-executable-entry-contract-v1',
        caller_requirement='CHECKED_NATIVE_REQUIRED' if require_checked else 'ORDINARY_EVIDENCE_LIMITS_ALLOWED',
        condition_authority='CODE_OWNED_NECESSARY_SYNTAX_ONLY',
        positive_condition_certifies_treatment=False,
        semantic_relevance_certified=False,
        actual_native_execution_still_required=True,
        reader_modes=dict(literal='Original source only. Checked mode requires the capability in that source literal_syntax_capabilities. Ordinary mode without this syntax may return only evidence limits.',
            semantic='Model must supply faithful source-anchored candidates; syntax and anchors do not certify semantics.',
            insufficient='No faithful supported representation; no native execution or checked result.'),
        sources=entries)


def planner_inventory():
    """Keep all retained IDs, with full contracts only for callable adapters.

    Implementation import paths are not planner arguments. Unavailable IDs remain
    explicit inventory gaps; their absent adapter cannot become an action.
    """
    rows = []
    for capability in CATALOG.values():
        row = dict(capability_id=capability.capability_id, family=capability.family,
                   entry_readiness=capability.entry_readiness)
        if capability.entry_contract is not None:
            row['entry_contract'] = asdict(capability.entry_contract)
        rows.append(row)
    return rows


def validate_executable_operations(operations, contract, sources):
    """Use the exact trusted contract supplied before planning; never model fields."""
    by_source = {}
    for expected_index, row in enumerate(contract['sources']):
        index = row['source_index']
        if (type(index) is not int or index != expected_index or not 0 <= index < len(sources)
                or type(row['version']) is not int or row['version'] != sources[index]['version']):
            raise EntryContractError('TRUSTED_ENTRY_SOURCE_BINDING_CHANGED')
        source_id = sources[index]['source_id']
        if source_id in by_source:
            raise EntryContractError('TRUSTED_ENTRY_SOURCE_BINDING_CHANGED')
        by_source[source_id] = row
    if len(by_source) != len(sources):
        raise EntryContractError('TRUSTED_ENTRY_SOURCE_BINDING_CHANGED')
    strict = contract['caller_requirement'] == 'CHECKED_NATIVE_REQUIRED'
    for operation in operations:
        cid = operation['capability']
        if CATALOG[cid].entry_contract is None:
            if strict:
                raise EntryContractError('UNAVAILABLE_ENTRY_NOT_SELECTABLE')
            # Ordinary composition retains honest unavailable-operation records
            # alongside any genuinely executed useful operation.
            continue
        for source_id in operation['source_ids']:
            entry = by_source[source_id]
            if strict and cid in entry['source_entry_blockers']:
                raise EntryContractError('SOURCE_ENTRY_NECESSARY_CONDITION_FAILED_BEFORE_NATIVE')
            if strict and cid in READER_BRIDGE_CAPABILITIES:
                if operation['input_mode'] == 'literal' and cid not in entry['literal_syntax_capabilities']:
                    raise EntryContractError('LITERAL_ENTRY_NECESSARY_CONDITION_FAILED_BEFORE_NATIVE')
