"""Pydantic data models for scenarios, results, and benchmark runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, computed_field

Category = Literal[
    "false_belief",
    "indirect_request",
    "knowledge_attr",
    "deception",
    "emotional_inference",
    "higher_order_beliefs",
]

Tier = Literal["easy", "medium", "hard", "expert"]


class Complexity(BaseModel):
    """Per-scenario metadata describing the cognitive complexity."""

    belief_depth: int = Field(ge=1, le=5, description="Order of belief reasoning required.")
    num_agents: int = Field(ge=1, description="Number of agents involved.")
    information_gap_type: str | None = Field(
        default=None,
        description="How the information asymmetry is created (e.g. absence, deception).",
    )


class Scenario(BaseModel):
    """A single ToM test case."""

    id: str
    category: Category
    name: str
    tier: Tier
    complexity: Complexity
    scenario: str
    question: str
    expected_answer: str
    answer_aliases: list[str] = Field(default_factory=list)
    rubric: str
    explanation: str


class Layer2Result(BaseModel):
    """Output from the LLM-as-Judge."""

    score: float = Field(ge=0.0, le=1.0)
    verdict: str
    rationale: str
    judge_model: str


class Layer3Result(BaseModel):
    """Structured JSON output from the model under test."""

    answer: str
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)


class TestResult(BaseModel):
    """Result of evaluating a single scenario."""

    __test__ = False  # tell pytest not to collect this Pydantic model as a test class

    scenario_id: str
    category: Category
    tier: Tier
    model: str
    response: str
    extracted_answer: str | None = None
    correct: bool | None = None  # None when ambiguous & no judge available
    ambiguous: bool = False
    latency_seconds: float = 0.0
    error: str | None = None
    layer2: Layer2Result | None = None
    layer3: Layer3Result | None = None


class BenchmarkRun(BaseModel):
    """Aggregated results for a single (model, run) pair."""

    model_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    judge_model: str | None = None
    structured: bool = False
    results: list[TestResult] = Field(default_factory=list)

    @computed_field  # type: ignore[misc]
    @property
    def total(self) -> int:
        return len(self.results)

    @computed_field  # type: ignore[misc]
    @property
    def correct_count(self) -> int:
        return sum(1 for r in self.results if r.correct is True)

    @computed_field  # type: ignore[misc]
    @property
    def error_count(self) -> int:
        """Results left unscored by an error (adapter failure, or judge failure on an ambiguous response)."""
        return sum(1 for r in self.results if r.error is not None and r.correct is None)

    @computed_field  # type: ignore[misc]
    @property
    def ambiguous_count(self) -> int:
        return sum(1 for r in self.results if r.ambiguous)

    @computed_field  # type: ignore[misc]
    @property
    def accuracy(self) -> float:
        scored = [r for r in self.results if r.correct is not None]
        if not scored:
            return 0.0
        return sum(1 for r in scored if r.correct) / len(scored)

    def accuracy_by_category(self) -> dict[str, float]:
        buckets: dict[str, list[bool]] = {}
        for r in self.results:
            if r.correct is None:
                continue
            buckets.setdefault(r.category, []).append(bool(r.correct))
        return {cat: (sum(v) / len(v) if v else 0.0) for cat, v in buckets.items()}

    def accuracy_by_tier(self) -> dict[str, float]:
        buckets: dict[str, list[bool]] = {}
        for r in self.results:
            if r.correct is None:
                continue
            buckets.setdefault(r.tier, []).append(bool(r.correct))
        return {tier: (sum(v) / len(v) if v else 0.0) for tier, v in buckets.items()}
