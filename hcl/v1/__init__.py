"""HCL v1 minimal on-demand cognition integration foundation."""
from .capabilities import CAPABILITIES, Capability, CapabilityType, CostClass
from .context import CognitionContext, ConditionalToolResult, EvidenceLevel
from .router import CognitionPlan, CognitionRequest, CognitionRouter, ToolRequest
from .layer import HCLCognitionLayer, PreparedAnswer, AnswerReceipt
