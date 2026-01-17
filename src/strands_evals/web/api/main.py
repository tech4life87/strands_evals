"""FastAPI application for Strands Evals Web UI."""

import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from strands import Agent
from strands_evals import Case
from strands_evals.types.evaluation_report import EvaluationReport
from .models import (
    BulkCaseCreate,
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    EvaluationStatus,
    EvaluatorConfig,
    EvaluatorTypeInfo,
    ExperimentCreate,
    ExperimentListResponse,
    ExperimentResponse,
    ExperimentUpdate,
    ImportExperimentRequest,
    RunEvaluationRequest,
)
from .storage import storage

app = FastAPI(
    title="Strands Evals Web UI",
    description="Web interface for the Strands Evals evaluation framework",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_websockets: dict[str, list[WebSocket]] = {}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Strands Evals Web UI API", "version": "0.1.0"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/experiments", response_model=list[ExperimentListResponse])
async def list_experiments():
    """List all experiments."""
    return storage.list_experiments()


@app.post("/api/experiments", response_model=ExperimentResponse)
async def create_experiment(experiment: ExperimentCreate):
    """Create a new experiment."""
    cases = [case.model_dump() for case in experiment.cases]
    evaluators = [eval_config.model_dump() for eval_config in experiment.evaluators]
    agent_config = experiment.agent_config.model_dump() if experiment.agent_config else None

    result = storage.create_experiment(
        name=experiment.name,
        description=experiment.description,
        cases=cases,
        evaluators=evaluators,
        agent_config=agent_config,
    )
    return result


@app.get("/api/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str):
    """Get an experiment by ID."""
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@app.put("/api/experiments/{experiment_id}", response_model=ExperimentResponse)
async def update_experiment(experiment_id: str, update: ExperimentUpdate):
    """Update an experiment."""
    agent_config = update.agent_config.model_dump() if update.agent_config else None
    result = storage.update_experiment(
        experiment_id,
        name=update.name,
        description=update.description,
        agent_config=agent_config,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return result


@app.delete("/api/experiments/{experiment_id}")
async def delete_experiment(experiment_id: str):
    """Delete an experiment."""
    if not storage.delete_experiment(experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"message": "Experiment deleted"}


@app.post("/api/experiments/import", response_model=ExperimentResponse)
async def import_experiment(request: ImportExperimentRequest):
    """Import an experiment from JSON data."""
    try:
        data = request.data
        name = request.name or data.get("name", "Imported Experiment")

        cases = data.get("cases", [])
        evaluators = data.get("evaluators", [])

        result = storage.create_experiment(
            name=name,
            description="Imported experiment",
            cases=cases,
            evaluators=evaluators,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to import experiment: {str(e)}") from e


@app.get("/api/experiments/{experiment_id}/export")
async def export_experiment(experiment_id: str):
    """Export an experiment to JSON."""
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    exp_obj = storage.to_experiment_object(experiment_id)
    if not exp_obj:
        raise HTTPException(status_code=404, detail="Failed to convert experiment")

    return exp_obj.to_dict()


@app.get("/api/experiments/{experiment_id}/cases", response_model=list[CaseResponse])
async def list_cases(experiment_id: str):
    """List all cases in an experiment."""
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment["cases"]


@app.post("/api/experiments/{experiment_id}/cases", response_model=CaseResponse)
async def add_case(experiment_id: str, case: CaseCreate):
    """Add a case to an experiment."""
    result = storage.add_case(experiment_id, case.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return result


@app.put("/api/experiments/{experiment_id}/cases/{case_id}", response_model=CaseResponse)
async def update_case(experiment_id: str, case_id: str, case: CaseUpdate):
    """Update a case in an experiment."""
    update_data = {k: v for k, v in case.model_dump().items() if v is not None}
    result = storage.update_case(experiment_id, case_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Case not found")
    return result


@app.delete("/api/experiments/{experiment_id}/cases/{case_id}")
async def delete_case(experiment_id: str, case_id: str):
    """Delete a case from an experiment."""
    if not storage.delete_case(experiment_id, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return {"message": "Case deleted"}


@app.post("/api/experiments/{experiment_id}/cases/bulk", response_model=list[CaseResponse])
async def bulk_create_cases(experiment_id: str, bulk: BulkCaseCreate):
    """Bulk create cases in an experiment."""
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    results = []
    for case in bulk.cases:
        result = storage.add_case(experiment_id, case.model_dump())
        if result:
            results.append(result)
    return results


@app.get("/api/evaluators", response_model=list[EvaluatorTypeInfo])
async def list_evaluator_types():
    """List available evaluator types."""
    evaluators = [
        EvaluatorTypeInfo(
            name="OutputEvaluator",
            description="LLM-based evaluator that assesses the output quality based on a rubric",
            parameters=[
                {"name": "rubric", "type": "string", "required": True, "description": "Evaluation criteria"},
                {"name": "model_id", "type": "string", "required": False, "description": "Model ID"},
                {"name": "include_inputs", "type": "boolean", "required": False, "description": "Include inputs"},
            ],
        ),
        EvaluatorTypeInfo(
            name="TrajectoryEvaluator",
            description="Evaluator that assesses the trajectory/sequence of actions taken",
            parameters=[
                {"name": "rubric", "type": "string", "required": True, "description": "Evaluation criteria"},
                {"name": "trajectory_description", "type": "object", "required": False, "description": "Trajectories"},
                {"name": "model_id", "type": "string", "required": False, "description": "Model ID"},
                {"name": "include_inputs", "type": "boolean", "required": False, "description": "Include inputs"},
            ],
        ),
        EvaluatorTypeInfo(
            name="InteractionsEvaluator",
            description="Evaluator for multi-agent interaction sequences",
            parameters=[
                {"name": "rubric", "type": "string", "required": True, "description": "Evaluation criteria"},
            ],
        ),
        EvaluatorTypeInfo(
            name="HelpfulnessEvaluator",
            description="Evaluates how helpful the response is",
            parameters=[],
        ),
        EvaluatorTypeInfo(
            name="HarmfulnessEvaluator",
            description="Evaluates potential harmfulness of the response",
            parameters=[],
        ),
        EvaluatorTypeInfo(
            name="FaithfulnessEvaluator",
            description="Evaluates faithfulness to source material",
            parameters=[],
        ),
        EvaluatorTypeInfo(
            name="GoalSuccessRateEvaluator",
            description="Evaluates goal completion success rate",
            parameters=[],
        ),
        EvaluatorTypeInfo(
            name="ToolSelectionAccuracyEvaluator",
            description="Evaluates accuracy of tool selection",
            parameters=[],
        ),
        EvaluatorTypeInfo(
            name="ToolParameterAccuracyEvaluator",
            description="Evaluates accuracy of tool parameters",
            parameters=[],
        ),
    ]
    return evaluators


@app.post("/api/experiments/{experiment_id}/evaluators", response_model=EvaluatorConfig)
async def add_evaluator(experiment_id: str, evaluator: EvaluatorConfig):
    """Add an evaluator to an experiment."""
    result = storage.add_evaluator(experiment_id, evaluator.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return result


@app.delete("/api/experiments/{experiment_id}/evaluators/{evaluator_id}")
async def delete_evaluator(experiment_id: str, evaluator_id: str):
    """Delete an evaluator from an experiment."""
    if not storage.delete_evaluator(experiment_id, evaluator_id):
        raise HTTPException(status_code=404, detail="Evaluator not found")
    return {"message": "Evaluator deleted"}


@app.post("/api/experiments/{experiment_id}/run", response_model=EvaluationStatus)
async def run_evaluation(experiment_id: str, request: RunEvaluationRequest | None = None):
    """Run an evaluation synchronously (demo mode with mock results)."""
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if not experiment["cases"]:
        raise HTTPException(status_code=400, detail="Experiment has no cases")

    if not experiment["evaluators"]:
        raise HTTPException(status_code=400, detail="Experiment has no evaluators")

    evaluation = storage.store_evaluation(experiment_id, status="running")

    try:
        num_cases = len(experiment["cases"])
        mock_reports = []

        for _eval_config in experiment["evaluators"]:
            mock_report = EvaluationReport(
                overall_score=0.85,
                scores=[0.8 + (i * 0.05) % 0.2 for i in range(num_cases)],
                test_passes=[True if i % 3 != 0 else False for i in range(num_cases)],
                cases=[
                    {
                        "name": case.get("name", f"Case {i+1}"),
                        "input": case["input"],
                        "expected_output": case.get("expected_output"),
                        "actual_output": f"Mock output for case {i+1}",
                    }
                    for i, case in enumerate(experiment["cases"])
                ],
                reasons=[f"Mock evaluation reason for case {i+1}" for i in range(num_cases)],
                detailed_results=[],
            )
            mock_reports.append(mock_report)

        storage.update_evaluation(
            evaluation["id"],
            status="completed",
            progress=100.0,
            current_case=num_cases,
            reports=mock_reports,
        )

        return storage.get_evaluation(evaluation["id"])

    except Exception as e:
        storage.update_evaluation(evaluation["id"], status="failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}") from e


@app.post("/api/experiments/{experiment_id}/run-async", response_model=EvaluationStatus)
async def run_evaluation_async(experiment_id: str, request: RunEvaluationRequest | None = None):
    """Start an async evaluation (returns immediately, use WebSocket for progress)."""
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if not experiment["cases"]:
        raise HTTPException(status_code=400, detail="Experiment has no cases")

    if not experiment["evaluators"]:
        raise HTTPException(status_code=400, detail="Experiment has no evaluators")

    evaluation = storage.store_evaluation(experiment_id, status="pending")

    asyncio.create_task(_run_async_evaluation(evaluation["id"], experiment_id, request))

    return evaluation


def _create_passthrough_task():
    """Create a task function that returns expected_output as actual_output (for testing evaluators)."""
    def task_fn(case: Case) -> str:
        """Passthrough task that returns expected_output as actual_output."""
        if case.expected_output is not None:
            return str(case.expected_output)
        return str(case.input)

    return task_fn


def _create_agent_task(agent_config: dict | None):
    """Create a task function that uses the configured Agent."""
    model_id = agent_config.get("model_id") if agent_config else None
    system_prompt = agent_config.get("system_prompt") if agent_config else None

    def task_fn(case: Case) -> str:
        """Task function that uses the Agent to process a case."""
        agent_kwargs = {"callback_handler": None}
        if model_id:
            agent_kwargs["model_id"] = model_id
        if system_prompt:
            agent_kwargs["system_prompt"] = system_prompt

        agent = Agent(**agent_kwargs)
        result = agent(case.input)
        return str(result)

    return task_fn


async def _run_async_evaluation(evaluation_id: str, experiment_id: str, request: RunEvaluationRequest | None):
    """Background task for async evaluation."""
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        return

    storage.update_evaluation(evaluation_id, status="running")

    try:
        num_cases = len(experiment["cases"])
        agent_config = experiment.get("agent_config")

        experiment_obj = storage.to_experiment_object(experiment_id)
        if not experiment_obj:
            raise ValueError("Failed to create Experiment object")

        # Use Agent if configured, otherwise use passthrough mode
        if agent_config and (agent_config.get("model_id") or agent_config.get("system_prompt")):
            task_fn = _create_agent_task(agent_config)
        else:
            # Passthrough mode: use expected_output as actual_output
            # This allows testing evaluators without needing an Agent
            task_fn = _create_passthrough_task()

        async def send_progress(current: int, total: int):
            """Send progress update via WebSocket."""
            progress = (current / total) * 100
            storage.update_evaluation(
                evaluation_id,
                progress=progress,
                current_case=current,
            )

            if evaluation_id in active_websockets:
                for ws in active_websockets[evaluation_id]:
                    try:
                        await ws.send_json({
                            "type": "progress",
                            "progress": progress,
                            "current_case": current,
                            "total_cases": total,
                        })
                    except Exception:
                        pass

        max_workers = request.max_workers if request else 10
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            reports = await loop.run_in_executor(
                executor,
                lambda: experiment_obj.run_evaluations(task_fn)
            )

        for i in range(num_cases):
            await send_progress(i + 1, num_cases)
            await asyncio.sleep(0.1)

        storage.update_evaluation(
            evaluation_id,
            status="completed",
            progress=100.0,
            current_case=num_cases,
            reports=reports,
        )

        if evaluation_id in active_websockets:
            for ws in active_websockets[evaluation_id]:
                try:
                    await ws.send_json({
                        "type": "completed",
                        "evaluation_id": evaluation_id,
                    })
                except Exception:
                    pass

    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        storage.update_evaluation(evaluation_id, status="failed", error=error_msg)

        if evaluation_id in active_websockets:
            for ws in active_websockets[evaluation_id]:
                try:
                    await ws.send_json({
                        "type": "error",
                        "error": str(e),
                    })
                except Exception:
                    pass


@app.get("/api/evaluations/{evaluation_id}/status", response_model=EvaluationStatus)
async def get_evaluation_status(evaluation_id: str):
    """Get the status of an evaluation."""
    evaluation = storage.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


@app.get("/api/evaluations/{evaluation_id}/report")
async def get_evaluation_report(evaluation_id: str):
    """Get the evaluation report."""
    evaluation = storage.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    if evaluation["status"] != "completed":
        raise HTTPException(status_code=400, detail="Evaluation not completed")

    reports = evaluation.get("reports", [])
    if not reports:
        raise HTTPException(status_code=404, detail="No reports available")

    return {
        "id": evaluation_id,
        "experiment_id": evaluation["experiment_id"],
        "reports": reports,
        "created_at": evaluation["created_at"],
    }


@app.get("/api/evaluations/{evaluation_id}/export")
async def export_evaluation_report(evaluation_id: str):
    """Export evaluation report to JSON."""
    evaluation = storage.get_evaluation(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return {
        "evaluation_id": evaluation_id,
        "experiment_id": evaluation["experiment_id"],
        "status": evaluation["status"],
        "reports": evaluation.get("reports", []),
        "created_at": evaluation["created_at"],
        "completed_at": evaluation.get("completed_at"),
    }


@app.get("/api/experiments/{experiment_id}/evaluations", response_model=list[EvaluationStatus])
async def list_experiment_evaluations(experiment_id: str):
    """List all evaluations for an experiment."""
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return storage.list_evaluations(experiment_id)


@app.websocket("/ws/evaluations/{evaluation_id}")
async def websocket_evaluation_progress(websocket: WebSocket, evaluation_id: str):
    """WebSocket endpoint for real-time evaluation progress."""
    await websocket.accept()

    if evaluation_id not in active_websockets:
        active_websockets[evaluation_id] = []
    active_websockets[evaluation_id].append(websocket)

    try:
        evaluation = storage.get_evaluation(evaluation_id)
        if evaluation:
            await websocket.send_json({
                "type": "status",
                "status": evaluation["status"],
                "progress": evaluation["progress"],
                "current_case": evaluation["current_case"],
                "total_cases": evaluation["total_cases"],
            })

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_text("ping")
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    finally:
        if evaluation_id in active_websockets:
            active_websockets[evaluation_id].remove(websocket)
            if not active_websockets[evaluation_id]:
                del active_websockets[evaluation_id]
