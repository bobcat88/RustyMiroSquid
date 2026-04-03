"""
Report API routes
Provides simulation report generation, retrieval, and conversation endpoints
"""

import os
import traceback
import threading
from typing import Dict, Any, Optional, List
import uuid
import tempfile

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ..services.report_agent import ReportAgent, ReportManager, ReportStatus
from ..services.graph_tools import GraphToolsService
from ..services.simulation_manager import SimulationManager
from ..models.project import ProjectManager
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger

logger = get_logger('miroshark.api.report')

router = APIRouter(prefix="/report", tags=["report"])


class GenerateReportRequest(BaseModel):
    simulation_id: str
    force_regenerate: bool = False

class GenerateStatusRequest(BaseModel):
    task_id: Optional[str] = None
    simulation_id: Optional[str] = None

class ChatRequest(BaseModel):
    simulation_id: str
    message: str
    chat_history: List[Dict[str, Any]] = []

class ToolSearchRequest(BaseModel):
    graph_id: str
    query: str
    limit: int = 10

class ToolStatisticsRequest(BaseModel):
    graph_id: str


# ============== Report Generation Endpoints ==============

@router.post("/generate")
def generate_report(req: GenerateReportRequest, request: Request, background_tasks: BackgroundTasks):
    try:
        simulation_id = req.simulation_id
        force_regenerate = req.force_regenerate

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return JSONResponse({"success": False, "error": f"Simulation not found: {simulation_id}"}, status_code=404)

        if not force_regenerate:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return {
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "message": "Report already exists",
                        "already_generated": True
                    }
                }

        project = ProjectManager.get_project(state.project_id)
        if not project:
            return JSONResponse({"success": False, "error": f"Project not found: {state.project_id}"}, status_code=404)

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return JSONResponse({"success": False, "error": "Missing graph ID, please ensure the graph has been built"}, status_code=400)

        simulation_requirement = project.simulation_requirement
        if not simulation_requirement:
            return JSONResponse({"success": False, "error": "Missing simulation requirement description"}, status_code=400)

        report_id = f"report_{uuid.uuid4().hex[:12]}"

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="report_generate",
            metadata={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "report_id": report_id
            }
        )

        storage = getattr(request.app.state, 'neo4j_storage', None)
        if not storage:
            return JSONResponse({"success": False, "error": "Neo4j storage not initialized"}, status_code=503)
            
        graph_tools = GraphToolsService(storage=storage)

        def run_generate():
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message="Initializing Report Agent..."
                )

                agent = ReportAgent(
                    graph_id=graph_id,
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement,
                    graph_tools=graph_tools
                )

                def progress_callback(stage, progress, message):
                    task_manager.update_task(
                        task_id,
                        progress=progress,
                        message=f"[{stage}] {message}"
                    )

                report = agent.generate_report(
                    progress_callback=progress_callback,
                    report_id=report_id
                )

                ReportManager.save_report(report)

                if report.status == ReportStatus.COMPLETED:
                    task_manager.complete_task(
                        task_id,
                        result={
                            "report_id": report.report_id,
                            "simulation_id": simulation_id,
                            "status": "completed"
                        }
                    )
                else:
                    task_manager.fail_task(task_id, report.error or "Report generation failed")

            except Exception as e:
                logger.error(f"Report generation failed: {str(e)}")
                task_manager.fail_task(task_id, str(e))

        # Using BackgroundTasks instead of threading directly
        background_tasks.add_task(run_generate)

        return {
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "report_id": report_id,
                "task_id": task_id,
                "status": "generating",
                "message": "Report generation task started, query progress via /api/report/generate/status",
                "already_generated": False
            }
        }

    except Exception as e:
        logger.error(f"Failed to start report generation task: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@router.post("/generate/status")
def get_generate_status(req: GenerateStatusRequest):
    try:
        task_id = req.task_id
        simulation_id = req.simulation_id

        if simulation_id:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return {
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "progress": 100,
                        "message": "Report has been generated",
                        "already_completed": True
                    }
                }

        if not task_id:
            return JSONResponse({"success": False, "error": "Please provide task_id or simulation_id"}, status_code=400)

        task_manager = TaskManager()
        task = task_manager.get_task(task_id)

        if not task:
            return JSONResponse({"success": False, "error": f"Task not found: {task_id}"}, status_code=404)

        return {"success": True, "data": task.to_dict()}

    except Exception as e:
        logger.error(f"Failed to query task status: {str(e)}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ============== Report Retrieval Endpoints ==============

@router.get("/{report_id}")
def get_report(report_id: str):
    try:
        report = ReportManager.get_report(report_id)

        if not report:
            return JSONResponse({"success": False, "error": f"Report not found: {report_id}"}, status_code=404)

        return {"success": True, "data": report.to_dict()}

    except Exception as e:
        logger.error(f"Failed to get report: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@router.get("/by-simulation/{simulation_id}")
def get_report_by_simulation(simulation_id: str):
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)

        if not report:
            return JSONResponse({
                "success": False,
                "error": f"No report available for this simulation: {simulation_id}",
                "has_report": False
            }, status_code=404)

        return {
            "success": True,
            "data": report.to_dict(),
            "has_report": True
        }

    except Exception as e:
        logger.error(f"Failed to get report: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@router.get("/{report_id}/download")
def download_report(report_id: str):
    try:
        report = ReportManager.get_report(report_id)

        if not report:
            return JSONResponse({"success": False, "error": f"Report not found: {report_id}"}, status_code=404)

        md_path = ReportManager._get_report_markdown_path(report_id)

        if not os.path.exists(md_path):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(report.markdown_content)
                temp_path = f.name
            return FileResponse(temp_path, media_type='text/markdown', filename=f"{report_id}.md")

        return FileResponse(md_path, media_type='text/markdown', filename=f"{report_id}.md")

    except Exception as e:
        logger.error(f"Failed to download report: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@router.delete("/{report_id}")
def delete_report(report_id: str):
    try:
        success = ReportManager.delete_report(report_id)

        if not success:
            return JSONResponse({"success": False, "error": f"Report not found: {report_id}"}, status_code=404)

        return {"success": True, "message": f"Report deleted: {report_id}"}

    except Exception as e:
        logger.error(f"Failed to delete report: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


# ============== Report Agent Chat Endpoints ==============

@router.post("/chat")
def chat_with_report_agent(req: ChatRequest, request: Request):
    try:
        simulation_id = req.simulation_id
        message = req.message
        chat_history = req.chat_history

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return JSONResponse({"success": False, "error": f"Simulation not found: {simulation_id}"}, status_code=404)

        project = ProjectManager.get_project(state.project_id)
        if not project:
            return JSONResponse({"success": False, "error": f"Project not found: {state.project_id}"}, status_code=404)

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return JSONResponse({"success": False, "error": "Missing graph ID"}, status_code=400)

        simulation_requirement = project.simulation_requirement or ""

        storage = getattr(request.app.state, 'neo4j_storage', None)
        if not storage:
            return JSONResponse({"success": False, "error": "Neo4j storage not initialized"}, status_code=503)

        graph_tools = GraphToolsService(storage=storage)

        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement,
            graph_tools=graph_tools
        )

        result = agent.chat(message=message, chat_history=chat_history)

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


# ============== Report Status Check Endpoints ==============

@router.get("/check/{simulation_id}")
def check_report_status(simulation_id: str):
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)

        has_report = report is not None
        report_status = report.status.value if report else None
        report_id = report.report_id if report else None
        interview_unlocked = has_report and report.status == ReportStatus.COMPLETED

        return {
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "has_report": has_report,
                "report_status": report_status,
                "report_id": report_id,
                "interview_unlocked": interview_unlocked
            }
        }

    except Exception as e:
        logger.error(f"Failed to check report status: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


# ============== Agent Log Endpoints ==============

@router.get("/{report_id}/agent-log")
def get_agent_log(report_id: str, from_line: int = 0):
    try:
        log_data = ReportManager.get_agent_log(report_id, from_line=from_line)
        return {"success": True, "data": log_data}
    except Exception as e:
        logger.error(f"Failed to get Agent log: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@router.get("/{report_id}/agent-log/stream")
def stream_agent_log(report_id: str):
    try:
        logs = ReportManager.get_agent_log_stream(report_id)
        return {"success": True, "data": {"logs": logs, "count": len(logs)}}
    except Exception as e:
        logger.error(f"Failed to get Agent log: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


# ============== Console Log Endpoints ==============

@router.get("/{report_id}/console-log")
def get_console_log(report_id: str, from_line: int = 0):
    try:
        log_data = ReportManager.get_console_log(report_id, from_line=from_line)
        return {"success": True, "data": log_data}
    except Exception as e:
        logger.error(f"Failed to get console log: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@router.get("/{report_id}/console-log/stream")
def stream_console_log(report_id: str):
    try:
        logs = ReportManager.get_console_log_stream(report_id)
        return {"success": True, "data": {"logs": logs, "count": len(logs)}}
    except Exception as e:
        logger.error(f"Failed to get console log: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


# ============== Tool Call Endpoints (for debugging) ==============

@router.post("/tools/search")
def search_graph_tool(req: ToolSearchRequest, request: Request):
    try:
        storage = getattr(request.app.state, 'neo4j_storage', None)
        if not storage:
            return JSONResponse({"success": False, "error": "Neo4j storage is not initialized"}, status_code=503)

        tools = GraphToolsService(storage=storage)
        result = tools.search_graph(
            graph_id=req.graph_id,
            query=req.query,
            limit=req.limit
        )

        return {"success": True, "data": result.to_dict()}

    except Exception as e:
        logger.error(f"Graph search failed: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@router.post("/tools/statistics")
def get_graph_statistics_tool(req: ToolStatisticsRequest, request: Request):
    try:
        storage = getattr(request.app.state, 'neo4j_storage', None)
        if not storage:
            return JSONResponse({"success": False, "error": "Neo4j storage is not initialized"}, status_code=503)

        tools = GraphToolsService(storage=storage)
        result = tools.get_graph_statistics(req.graph_id)

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Failed to get graph statistics: {str(e)}")
        return JSONResponse({"success": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)
