"""Opt-in shared cognition workspace; historical v1 entry remains available."""
from .core import Claim, ClaimKind, Dependency, EvidenceCore, Interpretation, Scope, SourceSpan
from .workspace import CognitionWorkspace, OperationResult

__all__ = ['Claim', 'ClaimKind', 'Dependency', 'EvidenceCore', 'Interpretation',
           'Scope', 'SourceSpan', 'CognitionWorkspace', 'OperationResult',
           'AuthorizedText', 'SemanticResult', 'prepare_semantics', 'PositionAssessment', 'assess_positions', 'RetainedResult', 'prepare_retained', 'answer_retained', 'Attitude', 'MentalProposition', 'EpistemicBundle', 'prepare_epistemic', 'CommunicationScene', 'CommunicationView', 'RevisionTimeline', 'RevisionSnapshot', 'SourceRecord', 'ReportAssessment', 'prepare_reports', 'IntegratedScene', 'IntegratedSceneResult', 'AgencyResult', 'prepare_agency', 'ActionExplanations', 'prepare_explanations', 'PlanFeasibility', 'prepare_plan_feasibility', 'AppraisalResult', 'prepare_appraisal']

from .semantic import AuthorizedText, SemanticResult, prepare_semantics

from .positions import PositionAssessment, assess_positions

from .retained import RetainedResult, prepare_retained, answer_retained

from .epistemic import Attitude, MentalProposition, EpistemicBundle, prepare_epistemic

from .communication import CommunicationScene, CommunicationView

from .revision_time import RevisionTimeline, RevisionSnapshot, SourceRecord

from .report_provenance import ReportAssessment, prepare_reports

from .integrated_scene import IntegratedScene, IntegratedSceneResult

from .agency import AgencyResult, prepare_agency

from .action_explanations import ActionExplanations, prepare_explanations

from .plan_feasibility import PlanFeasibility, prepare_plan_feasibility

from .appraisal import AppraisalResult, prepare_appraisal

from .agency_chain import AgencyChain, SemanticWorkspace, prepare_agency_chain

from .commitments import CommitmentResult, prepare_commitment

from .mutual_understanding import MutualUnderstanding, prepare_mutual_understanding
