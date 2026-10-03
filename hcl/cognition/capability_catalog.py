"""Current A–H implementation inventory, distinct from ordinary-entry readiness.

A00 is governance, not an executable capability. Entries name real retained
implementations; availability here never claims every entry adapter is finished.
"""
from dataclasses import dataclass
from importlib import import_module

@dataclass(frozen=True)
class AdapterContract:
    question_origin: str
    minimum_sources: int
    maximum_sources: int
    binding_contract: str
    question_forms: tuple[str, ...]
    question_contract: str
    input_limits: str
    result_limits: str


@dataclass(frozen=True)
class RetainedCapability:
    capability_id: str
    family: str
    implementation: str
    entry_readiness: str = 'ADAPTER_REQUIRED'
    entry_contract: AdapterContract | None = None

_ROWS = (
 ('A01','shared evidence','core:EvidenceCore'),
 ('A02','semantic preparation','semantic:prepare_semantics'),
 ('A03','support and revision','core:EvidenceCore.support_statuses'),
 ('A04','retained adapters','retained:prepare_retained'),
 ('A05','shared workspace','workspace:CognitionWorkspace'),
 ('B01','reported mental expressions','epistemic:prepare_epistemic'),
 ('B02','communication access','communication:CommunicationScene'),
 ('B03','belief revision','revision_time:RevisionTimeline'),
 ('B04','report provenance','report_provenance:prepare_reports'),
 ('B05','integrated perspectives','integrated_scene:IntegratedScene'),
 ('C01','goals and plans','agency:prepare_agency'),
 ('C02','competing action explanations','action_explanations:prepare_explanations'),
 ('C03','plan feasibility','plan_feasibility:prepare_plan_feasibility'),
 ('C04','appraisal','appraisal:prepare_appraisal'),
 ('C05','agency composition','agency_chain:prepare_agency_chain'),
 ('D01','commitments','commitments:prepare_commitment'),
 ('D02','mutual understanding','mutual_understanding:prepare_mutual_understanding'),
 ('D03','strategic communication','strategic_communication:prepare_strategic_communication'),
 ('D04','misunderstanding','misunderstanding:prepare_misunderstanding'),
 ('D05','joint plans','joint_plan:prepare_joint_plan'),
 ('E01','relationships','relationships:prepare_relationship'),
 ('E02','relational conflict','relational_conflict:prepare_relational_conflict'),
 ('E03','identity and roles','identity_roles:prepare_identity_roles'),
 ('E04','contextual values','contextual_values:prepare_contextual_values'),
 ('E05','relationship dynamics','relationship_dynamics:prepare_relationship_dynamics'),
 ('F01','episodic retrieval','episodic:EpisodicIndex'),
 ('F02','narrative time','narrative_time:NarrativeTimeline'),
 ('F03','evidence closure','evidence_closure:EvidenceClosureIndex'),
 ('F04','character development','character_development:compare_character_development'),
 ('F05','long narrative','long_narrative:NarrativeCorpus'),
 ('G01','normative premises','normative_premises:NormativePremiseWorkspace'),
 ('G02','responsibility composition','responsibility_composition:ResponsibilityCompositionWorkspace'),
 ('G03','concept criteria','concept_criteria:ConceptCriteriaWorkspace'),
 ('G04','argument analysis','argument_analysis:ArgumentWorkspace'),
 ('G05','argument sensitivity','argument_sensitivity:ArgumentSensitivityWorkspace'),
 ('H01','query planning','query_planner:QueryDirectedWorkspace'),
 ('H02','discriminating evidence','discriminating_evidence:DiscriminatingEvidenceWorkspace'),
 ('H03','execution graph','execution_graph:CognitiveExecutionGraph'),
 ('H04','answer audit','answer_audit:AnswerAuditWorkspace'),
 ('H05','hard cognition','hard_cognition:HardCognitionSession'),
)
# Descriptions of existing dispatch contracts, not new routing or parser rules.
# An absent contract means the retained implementation has no ordinary-entry adapter.
_UNUSED_BINDINGS='Not consumed by this adapter; use an empty bindings array.'
_READER_LIMITS='One complete source; bounded literal-report reader with no semantic translation or invented source facts.'
_CONCEPT_LIMITS='Source at most 16000 characters and 64 lines; original question at most 4000 characters.'
_CONTRACTS = {
    cid:AdapterContract('OPERATION_QUESTION',1,1,_UNUSED_BINDINGS,(),question,_READER_LIMITS,
        'The shared reader may prepare multiple families. Only the selected family checked_treatment_present flag indicates its treatment; execution alone is not substantive support.')
    for cid,question in (
        ('B01','Ask about source-reported mental expressions or beliefs; reports do not establish private belief or world truth.'),
        ('B02','Ask about explicitly reported communication access; availability, hearing, agreement and knowledge remain distinct.'),
        ('C01','Ask about reported goals and plans; do not infer a unique actual motive.'),
        ('C03','Ask about source-conditioned plan feasibility; a reported plan does not establish world feasibility.'),
    )
}
_CONTRACTS.update({
    'C02':AdapterContract('OPERATION_QUESTION',1,1,_UNUSED_BINDINGS,
        ('Why did <Actor> <verb and object>?',),
        'The internal question must exactly use the Why did form with one capitalized single-token actor and an explicit action plus object. A freeform request for competing explanations is not accepted. Interpret the user task into this form without changing its actor/action or asserting a true motive.',
        'Operation question at most 8000 characters; action at most 300 characters; at most 20 accepted literal source rows and two supported goals.',
        'Conditional, non-exhaustive explanations only; supported goals do not establish a unique actual motive. Unknown action/premises remain explicit.'),
    'G01':AdapterContract('ORIGINAL_USER_REQUEST',0,8,_UNUSED_BINDINGS,
        ('For this analysis, responsibility requires <conjunctive factors>.',
         'For this analysis, a person is responsible only if <conjunctive factors>.'),
        'Prepare normative-premise candidates from the original request and selected sources. Only a supported explicit original caller rule is adopted; unsupported rule logic/terms remain unresolved and planner interpretations cannot adopt a framework. Source rules and analyst proposals remain reports or unadopted.',
        'Original question at most 8000 characters; each selected source at most 64000 characters; complete preparation must fit its existing budget.',
        'No responsibility verdict or moral truth. Zero executable candidates is possible; execution alone is not an adopted rule.'),
    'G02':AdapterContract('ORIGINAL_USER_REQUEST',1,8,
        'Required: one to four distinct actor surface quotes, each bound exactly once to a distinct selected source ID. Repeated mentions are not additional actors. Do not bind the same actor twice or use one source as two actor episodes.',(),
        'Compose responsibility factors under the ORIGINAL caller rule, not an operation-question rule. A supported rule starts For this analysis, responsibility requires ... or For this analysis, a person is responsible only if ... and conjunctively names knowledge, control, foreseeability, intention or causal contribution (joined with and). Without an adopted caller rule, the result is NO_ADOPTED_INDIVIDUAL_RULE, not a factor check. Do not substitute responsibility for motive or argument sensitivity.',
        'One to four bound actor episodes using existing literal action/outcome forms; unsupported episodes remain SOURCE_EPISODE_UNRESOLVED. Each episode at most 16000 characters; original question at most 8000 characters. Source/actor bindings must use exact supplied quotes and offsets.',
        'Conditional responsibility only, never moral/legal truth. Source-reported factors, alternatives and group rules remain limited; no adopted rule means checked=null.'),
    'G03':AdapterContract('ORIGINAL_USER_REQUEST',1,1,_UNUSED_BINDINGS,(),
        'Prepare source-local concept criteria/readings and explicit revisions. The original question is consumed unchanged; an operation rewrite cannot supply criteria or meanings.',
        _CONCEPT_LIMITS,
        'Criteria and readings are conditional source reports. Unknown forms stay unresolved; a revision does not rewrite historical views. Empty preparation is possible.'),
    'G04':AdapterContract('ORIGINAL_USER_REQUEST',1,1,_UNUSED_BINDINGS,(),
        'Map source-reported arguments, premises, challenges, concept/value disagreements, counterexamples and analogies. The original question is consumed unchanged; an operation rewrite cannot supply an argument.',
        _CONCEPT_LIMITS,
        'No winner, world truth or formal proof is established. Exact bounded source forms are required for substantive mapping; empty or unresolved results remain explicit.'),
    'G05':AdapterContract('ORIGINAL_USER_REQUEST',1,1,_UNUSED_BINDINGS,
        ('If <exact argument premise> were false, what changes?',
         "If <Actor> used <Other>'s reading of <term>, what changes?",
         'If <Actor> valued <higher> over <lower> instead, what changes?'),
        'Use for one to three distinct single-factor sensitivity questions already present in the ORIGINAL user request in these exact forms. Fact hypotheses require an exact argument premise in one context; reading switches require one source-backed local comparison; value reversals require one explicit opposite source ranking. Never invent, combine or rewrite caller hypotheses to fit.',
        _CONCEPT_LIMITS+' At most three distinct question lines; no broad speculative counterfactual parser.',
        'Variants independently preserve the base source. Changed support/reading/value does not prove a conclusion flips; unaffected paths do not prove truth. Source and original-request roots are both required.'),
})
CATALOG={cid:RetainedCapability(cid,family,'hcl.cognition.'+path,
    'BOUNDED_ORDINARY_ADAPTER' if cid in _CONTRACTS else 'ADAPTER_REQUIRED',_CONTRACTS.get(cid))
    for cid,family,path in _ROWS}


def validate_catalog():
    for entry in CATALOG.values():
        if (entry.entry_readiness=='BOUNDED_ORDINARY_ADAPTER')!=(entry.entry_contract is not None):
            raise ValueError('ordinary adapter readiness and contract disagree')
        if entry.entry_contract is not None:
            contract=entry.entry_contract
            if contract.question_origin not in ('ORIGINAL_USER_REQUEST','OPERATION_QUESTION') or not 0<=contract.minimum_sources<=contract.maximum_sources<=8:
                raise ValueError('bounded adapter input contract required')
        module, symbol=entry.implementation.split(':')
        target=import_module(module)
        for part in symbol.split('.'):target=getattr(target,part)
        if not callable(target):raise ValueError('catalog entry is not callable')
    return True
