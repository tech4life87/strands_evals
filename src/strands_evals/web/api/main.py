"""FastAPI application for Strands Evals Web UI."""

import asyncio
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from strands import Agent
from strands_evals import Case
from strands_evals.types.evaluation_report import EvaluationReport

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("strands_evals.web")
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
            # Agent constructor uses 'model' parameter, not 'model_id'
            agent_kwargs["model"] = model_id
        if system_prompt:
            agent_kwargs["system_prompt"] = system_prompt

        agent = Agent(**agent_kwargs)
        result = agent(case.input)
        return str(result)

    return task_fn


async def _send_ws_message(evaluation_id: str, message: dict):
    """Send a message to all WebSocket clients for an evaluation."""
    if evaluation_id in active_websockets:
        for ws in active_websockets[evaluation_id]:
            try:
                await ws.send_json(message)
            except Exception:
                pass


async def _run_async_evaluation(evaluation_id: str, experiment_id: str, request: RunEvaluationRequest | None):
    """Background task for async evaluation.
    
    This implements a custom evaluation loop that processes cases one by one,
    sending progress updates via WebSocket as each case completes. This provides
    real-time feedback to the UI instead of waiting for all cases to complete.
    """
    logger.info(f"Starting async evaluation: evaluation_id={evaluation_id}, experiment_id={experiment_id}")
    
    experiment = storage.get_experiment(experiment_id)
    if not experiment:
        logger.error(f"Experiment not found: {experiment_id}")
        return

    storage.update_evaluation(evaluation_id, status="running")
    logger.debug(f"Evaluation status set to 'running'")

    try:
        cases_data = experiment["cases"]
        evaluators_data = experiment["evaluators"]
        num_cases = len(cases_data)
        agent_config = experiment.get("agent_config")

        logger.info(f"Evaluation config: {num_cases} cases, {len(evaluators_data)} evaluators, agent_config={bool(agent_config)}")

        if num_cases == 0:
            raise ValueError("No cases to evaluate")

        if not evaluators_data:
            raise ValueError("No evaluators configured")

        # Create Case objects
        cases = [
            Case(
                name=case.get("name"),
                input=case["input"],
                expected_output=case.get("expected_output"),
                expected_trajectory=case.get("expected_trajectory"),
                expected_interactions=case.get("expected_interactions"),
                metadata=case.get("metadata"),
            )
            for case in cases_data
        ]

        # Create Evaluator objects
        evaluators = []
        for eval_config in evaluators_data:
            evaluator = storage._create_evaluator(eval_config)
            if evaluator:
                evaluators.append(evaluator)

        if not evaluators:
            raise ValueError("Failed to create evaluators")

        logger.debug(f"Created {len(evaluators)} evaluators: {[e.get_type_name() for e in evaluators]}")

        # Use Agent if configured, otherwise use passthrough mode
        if agent_config and (agent_config.get("model_id") or agent_config.get("system_prompt")):
            logger.info(f"Using Agent task with model_id={agent_config.get('model_id')}")
            task_fn = _create_agent_task(agent_config)
        else:
            logger.info("Using passthrough task (no Agent configured)")
            task_fn = _create_passthrough_task()

        # Initialize data structures for collecting results per evaluator
        evaluator_data: dict[str, dict[str, list]] = {
            evaluator.get_type_name(): {
                "scores": [],
                "test_passes": [],
                "cases": [],
                "reasons": [],
                "detailed_results": [],
            }
            for evaluator in evaluators
        }

        # Process each case and send progress updates
        logger.info(f"Starting to process {num_cases} cases")
        for case_idx, case in enumerate(cases):
            case_name = case.name or f"Case {case_idx + 1}"
            logger.debug(f"Processing case {case_idx + 1}/{num_cases}: {case_name}")
            
            # Send progress update before processing
            progress = (case_idx / num_cases) * 100
            storage.update_evaluation(evaluation_id, progress=progress, current_case=case_idx)
            await _send_ws_message(evaluation_id, {
                "type": "progress",
                "progress": progress,
                "current_case": case_idx,
                "total_cases": num_cases,
                "case_name": case_name,
                "message": f"Processing case: {case_name}",
            })

            # Run the task function to get actual output
            try:
                loop = asyncio.get_event_loop()
                task_output = await loop.run_in_executor(None, task_fn, case)
                
                # Build evaluation context
                evaluation_context = {
                    "name": case.name,
                    "input": case.input,
                    "expected_output": case.expected_output,
                    "expected_trajectory": case.expected_trajectory,
                    "expected_interactions": case.expected_interactions,
                    "metadata": case.metadata,
                    "actual_output": None,
                    "actual_trajectory": None,
                    "actual_interactions": None,
                }
                
                if isinstance(task_output, dict):
                    evaluation_context["actual_output"] = task_output.get("output")
                    evaluation_context["actual_trajectory"] = task_output.get("trajectory")
                    evaluation_context["actual_interactions"] = task_output.get("interactions")
                else:
                    evaluation_context["actual_output"] = task_output

                # Evaluate with each evaluator
                for evaluator in evaluators:
                    eval_name = evaluator.get_type_name()
                    logger.debug(f"Running evaluator: {eval_name}")
                    try:
                        # Create EvaluationData for the evaluator
                        from strands_evals.types.evaluation import EvaluationData
                        eval_data = EvaluationData(
                            name=case.name,
                            input=case.input,
                            expected_output=case.expected_output,
                            expected_trajectory=case.expected_trajectory,
                            expected_interactions=case.expected_interactions,
                            metadata=case.metadata,
                            actual_output=evaluation_context["actual_output"],
                            actual_trajectory=evaluation_context["actual_trajectory"],
                            actual_interactions=evaluation_context["actual_interactions"],
                        )
                        
                        # Run evaluation
                        evaluation_outputs = await loop.run_in_executor(
                            None, evaluator.evaluate, eval_data
                        )
                        (aggregate_score, aggregate_pass, aggregate_reason) = evaluator.aggregator(evaluation_outputs)

                        evaluator_data[eval_name]["cases"].append(evaluation_context)
                        evaluator_data[eval_name]["scores"].append(aggregate_score)
                        evaluator_data[eval_name]["test_passes"].append(aggregate_pass)
                        evaluator_data[eval_name]["reasons"].append(aggregate_reason or "")
                        evaluator_data[eval_name]["detailed_results"].append(evaluation_outputs)
                    except Exception as eval_error:
                        logger.error(f"Evaluator {eval_name} failed: {eval_error}")
                        evaluator_data[eval_name]["cases"].append(evaluation_context)
                        evaluator_data[eval_name]["scores"].append(0)
                        evaluator_data[eval_name]["test_passes"].append(False)
                        evaluator_data[eval_name]["reasons"].append(f"Evaluator error: {str(eval_error)}")
                        evaluator_data[eval_name]["detailed_results"].append([])

            except Exception as task_error:
                # Task execution failed - record failure for all evaluators
                logger.error(f"Task execution failed for case {case_name}: {task_error}")
                for evaluator in evaluators:
                    eval_name = evaluator.get_type_name()
                    evaluator_data[eval_name]["cases"].append({
                        "name": case.name,
                        "input": case.input,
                        "expected_output": case.expected_output,
                        "actual_output": None,
                    })
                    evaluator_data[eval_name]["scores"].append(0)
                    evaluator_data[eval_name]["test_passes"].append(False)
                    evaluator_data[eval_name]["reasons"].append(f"Task error: {str(task_error)}")
                    evaluator_data[eval_name]["detailed_results"].append([])

            # Small delay to allow WebSocket messages to be sent
            await asyncio.sleep(0.05)

        # Build final reports
        logger.info(f"All cases processed, building final reports")
        reports = []
        for evaluator in evaluators:
            eval_name = evaluator.get_type_name()
            data = evaluator_data[eval_name]
            scores = data["scores"]
            report = EvaluationReport(
                overall_score=sum(scores) / len(scores) if scores else 0,
                scores=scores,
                test_passes=data["test_passes"],
                cases=data["cases"],
                reasons=data["reasons"],
                detailed_results=data["detailed_results"],
            )
            reports.append(report)

        # Update storage with completed status and reports
        storage.update_evaluation(
            evaluation_id,
            status="completed",
            progress=100.0,
            current_case=num_cases,
            reports=reports,
        )

        # Send completion message
        logger.info(f"Evaluation completed successfully: {evaluation_id}")
        await _send_ws_message(evaluation_id, {
            "type": "completed",
            "evaluation_id": evaluation_id,
        })

    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"Evaluation failed: {evaluation_id}\n{error_msg}")
        storage.update_evaluation(evaluation_id, status="failed", error=error_msg)

        await _send_ws_message(evaluation_id, {
            "type": "error",
            "error": str(e),
        })


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
