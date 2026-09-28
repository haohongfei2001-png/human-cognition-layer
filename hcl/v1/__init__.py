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
from .cg03 import (NormativePremise, ResponsibilityCase, ResponsibilityFactor,
                   ClaimAuthority, FactorRequirement, FactorClaim,
                   NarrativePremise, ResponsibilityPreparation,
                   check_responsibility, prepare_responsibility_narrative)
from .cg04 import (PreferenceCondition, PreferenceStatement, ContextConditionClaim,
                   PreferenceCase, PreferencePreparation, project_preferences,
                   check_preferences, prepare_preference_narrative)

from .cg05 import (ConceptDefinition, ConceptProperty, ConceptUse, ConceptCase,
                   ConceptPreparation, project_concepts, check_concepts, prepare_concept_narrative)

from .compact import compact_cognition_context, expand_cognition_context

from .composition import (ComposedAnswer, ComposedAnswerReceipt, prepare_composed_answer, answer_composed)
