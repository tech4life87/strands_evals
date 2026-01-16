"""Pydantic models for the Web API."""

from typing import Any

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    """Model for creating a new case."""

    name: str | None = None
    input: Any
    expected_output: Any | None = None
    expected_trajectory: list[Any] | None = None
    expected_interactions: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class CaseUpdate(BaseModel):
    """Model for updating a case."""

    name: str | None = None
    input: Any | None = None
    expected_output: Any | None = None
    expected_trajectory: list[Any] | None = None
    expected_interactions: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class CaseResponse(BaseModel):
    """Model for case response."""

    id: str
    name: str | None = None
    session_id: str
    input: Any
    expected_output: Any | None = None
    expected_trajectory: list[Any] | None = None
    expected_interactions: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class EvaluatorConfig(BaseModel):
    """Model for evaluator configuration."""

    evaluator_type: str
    rubric: str | None = None
    model_id: str | None = None
    system_prompt: str | None = None
    include_inputs: bool = True
    trajectory_description: dict[str, Any] | None = None


class ExperimentCreate(BaseModel):
    """Model for creating a new experiment."""

    name: str
    description: str | None = None
    cases: list[CaseCreate] = Field(default_factory=list)
    evaluators: list[EvaluatorConfig] = Field(default_factory=list)


class ExperimentUpdate(BaseModel):
    """Model for updating an experiment."""

    name: str | None = None
    description: str | None = None


class ExperimentResponse(BaseModel):
    """Model for experiment response."""

    id: str
    name: str
    description: str | None = None
    cases: list[CaseResponse] = Field(default_factory=list)
    evaluators: list[EvaluatorConfig] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ExperimentListResponse(BaseModel):
    """Model for listing experiments."""

    id: str
    name: str
    description: str | None = None
    case_count: int
    evaluator_count: int
    created_at: str
    updated_at: str


class EvaluatorTypeInfo(BaseModel):
    """Model for evaluator type information."""

    name: str
    description: str
    parameters: list[dict[str, Any]]


class RunEvaluationRequest(BaseModel):
    """Model for running an evaluation."""

    max_workers: int = 10
    task_code: str | None = None


class EvaluationStatus(BaseModel):
    """Model for evaluation status."""

    id: str
    experiment_id: str
    status: str
    progress: float = 0.0
    current_case: int = 0
    total_cases: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class EvaluationReportResponse(BaseModel):
    """Model for evaluation report response."""

    id: str
    experiment_id: str
    overall_score: float
    scores: list[float]
    test_passes: list[bool]
    cases: list[dict[str, Any]]
    reasons: list[str]
    detailed_results: list[list[dict[str, Any]]] = Field(default_factory=list)
    created_at: str


class ImportExperimentRequest(BaseModel):
    """Model for importing an experiment."""

    data: dict[str, Any]
    name: str | None = None


class BulkCaseCreate(BaseModel):
    """Model for bulk creating cases."""

    cases: list[CaseCreate]
