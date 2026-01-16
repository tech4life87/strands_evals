"""In-memory storage for experiments and evaluations."""

import uuid
from datetime import datetime, timezone
from typing import Any

from strands_evals.case import Case
from strands_evals.evaluators import (
    Evaluator,
    FaithfulnessEvaluator,
    GoalSuccessRateEvaluator,
    HarmfulnessEvaluator,
    HelpfulnessEvaluator,
    InteractionsEvaluator,
    OutputEvaluator,
    ToolParameterAccuracyEvaluator,
    ToolSelectionAccuracyEvaluator,
    TrajectoryEvaluator,
)
from strands_evals.experiment import Experiment
from strands_evals.types.evaluation_report import EvaluationReport


class ExperimentStorage:
    """In-memory storage for experiments."""

    def __init__(self):
        self._experiments: dict[str, dict[str, Any]] = {}
        self._evaluations: dict[str, dict[str, Any]] = {}

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_experiment(
        self,
        name: str,
        description: str | None = None,
        cases: list[dict[str, Any]] | None = None,
        evaluators: list[dict[str, Any]] | None = None,
        agent_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new experiment."""
        experiment_id = str(uuid.uuid4())
        now = self._now_iso()

        processed_cases = []
        if cases:
            for case_data in cases:
                case_id = str(uuid.uuid4())
                case_obj = Case(**case_data)
                processed_cases.append(
                    {
                        "id": case_id,
                        "name": case_obj.name,
                        "session_id": case_obj.session_id,
                        "input": case_obj.input,
                        "expected_output": case_obj.expected_output,
                        "expected_trajectory": case_obj.expected_trajectory,
                        "expected_interactions": case_obj.expected_interactions,
                        "metadata": case_obj.metadata,
                    }
                )

        experiment = {
            "id": experiment_id,
            "name": name,
            "description": description,
            "cases": processed_cases,
            "evaluators": evaluators or [],
            "agent_config": agent_config,
            "created_at": now,
            "updated_at": now,
        }
        self._experiments[experiment_id] = experiment
        return experiment

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        """Get an experiment by ID."""
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> list[dict[str, Any]]:
        """List all experiments."""
        return [
            {
                "id": exp["id"],
                "name": exp["name"],
                "description": exp["description"],
                "case_count": len(exp["cases"]),
                "evaluator_count": len(exp["evaluators"]),
                "created_at": exp["created_at"],
                "updated_at": exp["updated_at"],
            }
            for exp in self._experiments.values()
        ]

    def update_experiment(
        self,
        experiment_id: str,
        name: str | None = None,
        description: str | None = None,
        agent_config: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Update an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None

        if name is not None:
            experiment["name"] = name
        if description is not None:
            experiment["description"] = description
        if agent_config is not None:
            experiment["agent_config"] = agent_config
        experiment["updated_at"] = self._now_iso()
        return experiment

    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete an experiment."""
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            return True
        return False

    def add_case(self, experiment_id: str, case_data: dict[str, Any]) -> dict[str, Any] | None:
        """Add a case to an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None

        case_id = str(uuid.uuid4())
        case_obj = Case(**case_data)
        case = {
            "id": case_id,
            "name": case_obj.name,
            "session_id": case_obj.session_id,
            "input": case_obj.input,
            "expected_output": case_obj.expected_output,
            "expected_trajectory": case_obj.expected_trajectory,
            "expected_interactions": case_obj.expected_interactions,
            "metadata": case_obj.metadata,
        }
        experiment["cases"].append(case)
        experiment["updated_at"] = self._now_iso()
        return case

    def update_case(self, experiment_id: str, case_id: str, case_data: dict[str, Any]) -> dict[str, Any] | None:
        """Update a case in an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None

        for case in experiment["cases"]:
            if case["id"] == case_id:
                for key, value in case_data.items():
                    if value is not None:
                        case[key] = value
                experiment["updated_at"] = self._now_iso()
                return case
        return None

    def delete_case(self, experiment_id: str, case_id: str) -> bool:
        """Delete a case from an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False

        for i, case in enumerate(experiment["cases"]):
            if case["id"] == case_id:
                experiment["cases"].pop(i)
                experiment["updated_at"] = self._now_iso()
                return True
        return False

    def add_evaluator(self, experiment_id: str, evaluator_config: dict[str, Any]) -> dict[str, Any] | None:
        """Add an evaluator to an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None

        evaluator_id = str(uuid.uuid4())
        evaluator = {"id": evaluator_id, **evaluator_config}
        experiment["evaluators"].append(evaluator)
        experiment["updated_at"] = self._now_iso()
        return evaluator

    def delete_evaluator(self, experiment_id: str, evaluator_id: str) -> bool:
        """Delete an evaluator from an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False

        for i, evaluator in enumerate(experiment["evaluators"]):
            if evaluator.get("id") == evaluator_id:
                experiment["evaluators"].pop(i)
                experiment["updated_at"] = self._now_iso()
                return True
        return False

    def to_experiment_object(self, experiment_id: str) -> Experiment | None:
        """Convert stored experiment to Experiment object."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None

        cases = [
            Case(
                name=case.get("name"),
                input=case["input"],
                expected_output=case.get("expected_output"),
                expected_trajectory=case.get("expected_trajectory"),
                expected_interactions=case.get("expected_interactions"),
                metadata=case.get("metadata"),
            )
            for case in experiment["cases"]
        ]

        evaluators = []
        for eval_config in experiment["evaluators"]:
            evaluator = self._create_evaluator(eval_config)
            if evaluator:
                evaluators.append(evaluator)

        return Experiment(cases=cases, evaluators=evaluators if evaluators else None)

    def _create_evaluator(self, config: dict[str, Any]) -> Evaluator | None:
        """Create an evaluator from config."""
        evaluator_type = config.get("evaluator_type")
        evaluator_map = {
            "Evaluator": Evaluator,
            "OutputEvaluator": OutputEvaluator,
            "TrajectoryEvaluator": TrajectoryEvaluator,
            "InteractionsEvaluator": InteractionsEvaluator,
            "HelpfulnessEvaluator": HelpfulnessEvaluator,
            "HarmfulnessEvaluator": HarmfulnessEvaluator,
            "GoalSuccessRateEvaluator": GoalSuccessRateEvaluator,
            "FaithfulnessEvaluator": FaithfulnessEvaluator,
            "ToolSelectionAccuracyEvaluator": ToolSelectionAccuracyEvaluator,
            "ToolParameterAccuracyEvaluator": ToolParameterAccuracyEvaluator,
        }

        evaluator_class = evaluator_map.get(evaluator_type)
        if not evaluator_class:
            return None

        kwargs = {}
        if "rubric" in config and config["rubric"]:
            kwargs["rubric"] = config["rubric"]
        if "model_id" in config and config["model_id"]:
            kwargs["model"] = config["model_id"]
        if "system_prompt" in config and config["system_prompt"]:
            kwargs["system_prompt"] = config["system_prompt"]
        if "include_inputs" in config:
            kwargs["include_inputs"] = config["include_inputs"]
        if "trajectory_description" in config and config["trajectory_description"]:
            kwargs["trajectory_description"] = config["trajectory_description"]

        try:
            return evaluator_class(**kwargs)
        except TypeError:
            return evaluator_class()

    def store_evaluation(
        self,
        experiment_id: str,
        status: str = "pending",
        reports: list[EvaluationReport] | None = None,
    ) -> dict[str, Any]:
        """Store an evaluation result."""
        evaluation_id = str(uuid.uuid4())
        now = self._now_iso()

        experiment = self._experiments.get(experiment_id)
        total_cases = len(experiment["cases"]) if experiment else 0

        evaluation = {
            "id": evaluation_id,
            "experiment_id": experiment_id,
            "status": status,
            "progress": 0.0,
            "current_case": 0,
            "total_cases": total_cases,
            "started_at": now if status == "running" else None,
            "completed_at": None,
            "error": None,
            "reports": [r.to_dict() for r in reports] if reports else [],
            "created_at": now,
        }
        self._evaluations[evaluation_id] = evaluation
        return evaluation

    def update_evaluation(
        self,
        evaluation_id: str,
        status: str | None = None,
        progress: float | None = None,
        current_case: int | None = None,
        error: str | None = None,
        reports: list[EvaluationReport] | None = None,
    ) -> dict[str, Any] | None:
        """Update an evaluation."""
        evaluation = self._evaluations.get(evaluation_id)
        if not evaluation:
            return None

        if status is not None:
            evaluation["status"] = status
            if status == "running" and not evaluation["started_at"]:
                evaluation["started_at"] = self._now_iso()
            elif status in ("completed", "failed"):
                evaluation["completed_at"] = self._now_iso()
        if progress is not None:
            evaluation["progress"] = progress
        if current_case is not None:
            evaluation["current_case"] = current_case
        if error is not None:
            evaluation["error"] = error
        if reports is not None:
            evaluation["reports"] = [r.to_dict() for r in reports]

        return evaluation

    def get_evaluation(self, evaluation_id: str) -> dict[str, Any] | None:
        """Get an evaluation by ID."""
        return self._evaluations.get(evaluation_id)

    def list_evaluations(self, experiment_id: str | None = None) -> list[dict[str, Any]]:
        """List evaluations, optionally filtered by experiment."""
        evaluations = list(self._evaluations.values())
        if experiment_id:
            evaluations = [e for e in evaluations if e["experiment_id"] == experiment_id]
        return evaluations


storage = ExperimentStorage()
