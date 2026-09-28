"""HCL v1 minimal on-demand cognition integration foundation."""
from .capabilities import CAPABILITIES, Capability, CapabilityType, CostClass
from .context import CognitionContext, ConditionalToolResult, EvidenceLevel
from .router import CognitionPlan, CognitionRequest, CognitionRouter, PerspectiveMode, ToolRequest
from .layer import HCLCognitionLayer, PreparedAnswer, AnswerReceipt
from .cg01 import (ConditionFact, ConditionKind, ExplanationCandidate,
                   FactAuthority, RequiredCondition, check_explanations,
                   revise_explanations)
from .narrative import SemanticPreparation
from .cg02 import (SocialActKind, SocialCondition, SocialAct,
                   ParticipantInterpretation, AccessStatement, check_social_exchange)
from .social_narrative import SocialPreparation, prepare_social_narrative
