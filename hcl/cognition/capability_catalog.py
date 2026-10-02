"""Current A–H implementation inventory, distinct from ordinary-entry readiness.

A00 is governance, not an executable capability. Entries name real retained
implementations; availability here never claims every entry adapter is finished.
"""
from dataclasses import dataclass
from importlib import import_module

@dataclass(frozen=True)
class RetainedCapability:
    capability_id: str
    family: str
    implementation: str
    entry_readiness: str = 'ADAPTER_REQUIRED'

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
CATALOG={cid:RetainedCapability(cid,family,'hcl.cognition.'+path,
    'BOUNDED_ORDINARY_ADAPTER' if cid in ('B01','B02','C01','C03','C02','G02','G01','G03') else 'ADAPTER_REQUIRED')
    for cid,family,path in _ROWS}


def validate_catalog():
    for entry in CATALOG.values():
        module, symbol=entry.implementation.split(':')
        target=import_module(module)
        for part in symbol.split('.'):target=getattr(target,part)
        if not callable(target):raise ValueError('catalog entry is not callable')
    return True
