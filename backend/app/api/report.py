"""
Report API routes
Provides simulation report generation, retrieval, and conversation endpoints
"""

import os
import traceback
import threading
import uuid
from typing import Dict, Any, List, Optional
from fastapi import Request, HTTPException, Body, Query, Path, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse

from . import report_router
from ..config import Config
from ..services.report_agent import ReportAgent, ReportManager, ReportStatus
from ..services.graph_tools import GraphToolsService
from ..services.simulation_manager import SimulationManager
from ..models.project import ProjectManager
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger

logger = get_logger('rustymirosquid.api.report')


# ============== Report Generation Endpoints ==============

@report_router.post('/generate')
async def generate_report(request: Request, background_tasks: BackgroundTasks, payload: Dict[str, Any] = Body(...)):
    """
    Generate simulation analysis report (async task)
    """
    try:
        simulation_id = payload.get('simulation_id')
        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")

        force_regenerate = payload.get('force_regenerate', False)

        # Get simulation info
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")

        # Check if a report already exists
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

        # Get project info
        project = ProjectManager.get_project(state.project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {state.project_id}")

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            raise HTTPException(status_code=400, detail="Missing graph ID, please ensure the graph has been built")

        simulation_requirement = project.simulation_requirement
        if not simulation_requirement:
            raise HTTPException(status_code=400, detail="Missing simulation requirement description")

        # Pre-generate report_id for immediate return to frontend
        report_id = f"report_{uuid.uuid4().hex[:12]}"

        # Create async task
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="report_generate",
            metadata={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "report_id": report_id
            }
        )

        # Get storage from app state
        storage = request.app.state.neo4j_storage
        if not storage:
            raise HTTPException(status_code=503, detail="Neo4j storage not initialized")
        graph_tools = GraphToolsService(storage=storage)

        # Define background task
        def run_generate():
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message="Initializing Report Agent..."
                )

                # Create Report Agent
                agent = ReportAgent(
                    graph_id=graph_id,
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement,
                    graph_tools=graph_tools
                )

                # Progress callback
                def progress_callback(stage, progress, message):
                    task_manager.update_task(
                        task_id,
                        progress=progress,
                        message=f"[{stage}] {message}"
                    )

                # Generate report (pass pre-generated report_id)
                report = agent.generate_report(
                    progress_callback=progress_callback,
                    report_id=report_id
                )

                # Save report
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

        # Start background task
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start report generation task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@report_router.post('/generate/status')
async def get_generate_status(payload: Dict[str, Any] = Body(...)):
    """
    Query report generation task progress
    """
    try:
        task_id = payload.get('task_id')
        simulation_id = payload.get('simulation_id')

        # If simulation_id is provided, first check if a completed report exists
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
            raise HTTPException(status_code=400, detail="Please provide task_id or simulation_id")

        task_manager = TaskManager()
        task = task_manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        return {
            "success": True,
            "data": task.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Report Retrieval Endpoints ==============

@report_bp.route('/<report_id>', methods=['GET'])
def get_report(report_id: str):
    """
    Get report details

    Returns:
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                "simulation_id": "sim_xxxx",
                "status": "completed",
                "outline": {...},
                "markdown_content": "...",
                "created_at": "...",
                "completed_at": "..."
            }
        }
    """
    try:
        report = ReportManager.get_report(report_id)

        if not report:
            return jsonify({
                "success": False,
                "error": f"Report not found: {report_id}"
            }), 404

        return jsonify({
            "success": True,
            "data": report.to_dict()
        })

    except Exception as e:
        logger.error(f"Failed to get report: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_router.get('/by-simulation/{simulation_id}')
async def get_report_by_simulation(simulation_id: str):
    """
    Get report by simulation ID
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)

        if not report:
            return {
                "success": False,
                "error": f"No report available for this simulation: {simulation_id}",
                "has_report": False
            }

        return {
            "success": True,
            "data": report.to_dict(),
            "has_report": True
        }

    except Exception as e:
        logger.error(f"Failed to get report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@report_router.get('/{report_id}/download')
async def download_report(report_id: str):
    """
    Download report (Markdown format)
    """
    try:
        report = ReportManager.get_report(report_id)

        if not report:
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")

        md_path = ReportManager._get_report_markdown_path(report_id)

        if not os.path.exists(md_path):
            # If MD file does not exist, generate a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
                f.write(report.markdown_content)
                temp_path = f.name

            return FileResponse(
                path=temp_path,
                filename=f"{report_id}.md",
                media_type="text/markdown"
            )

        return FileResponse(
            path=md_path,
            filename=f"{report_id}.md",
            media_type="text/markdown"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@report_router.delete('/{report_id}')
async def delete_report(report_id: str):
    """Delete report"""
    try:
        success = ReportManager.delete_report(report_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")

        return {
            "success": True,
            "message": f"Report deleted: {report_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Report Agent Chat Endpoints ==============

@report_router.post('/chat')
async def chat_with_report_agent(request: Request, payload: Dict[str, Any] = Body(...)):
    """
    Chat with Report Agent
    """
    try:
        simulation_id = payload.get('simulation_id')
        message = payload.get('message')
        chat_history = payload.get('chat_history', [])

        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")

        if not message:
            raise HTTPException(status_code=400, detail="Please provide message")

        # Get simulation and project info
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")

        project = ProjectManager.get_project(state.project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {state.project_id}")

        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            raise HTTPException(status_code=400, detail="Missing graph ID")

        simulation_requirement = project.simulation_requirement or ""

        # Create Agent and start conversation
        storage = request.app.state.neo4j_storage
        if not storage:
            raise HTTPException(status_code=503, detail="Neo4j storage not initialized")
        graph_tools = GraphToolsService(storage=storage)

        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement,
            graph_tools=graph_tools
        )

        result = agent.chat(message=message, chat_history=chat_history)

        return {
            "success": True,
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Report Progress and Section Endpoints ==============

# ============== Report Status Check Endpoints ==============

@report_bp.route('/check/<simulation_id>', methods=['GET'])
def check_report_status(simulation_id: str):
    """
    Check if a simulation has a report and its status

    Used by frontend to determine whether to unlock Interview feature

    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "has_report": true,
                "report_status": "completed",
                "report_id": "report_xxxx",
                "interview_unlocked": true
            }
        }
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)

        has_report = report is not None
        report_status = report.status.value if report else None
        report_id = report.report_id if report else None

        # Only unlock interview after report is completed
        interview_unlocked = has_report and report.status == ReportStatus.COMPLETED

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "has_report": has_report,
                "report_status": report_status,
                "report_id": report_id,
                "interview_unlocked": interview_unlocked
            }
        })

    except Exception as e:
        logger.error(f"Failed to check report status: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Agent Log Endpoints ==============

@report_router.get('/{report_id}/agent-log')
async def get_agent_log(report_id: str, from_line: int = Query(0)):
    """
    Get Report Agent's detailed execution log
    """
    try:
        log_data = ReportManager.get_agent_log(report_id, from_line=from_line)

        return {
            "success": True,
            "data": log_data
        }

    except Exception as e:
        logger.error(f"Failed to get Agent log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@report_router.get('/{report_id}/agent-log/stream')
async def stream_agent_log(report_id: str):
    """
    Get complete Agent log (fetch all at once)
    """
    try:
        logs = ReportManager.get_agent_log_stream(report_id)

        return {
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get Agent log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Console Log Endpoints ==============

@report_router.get('/{report_id}/console-log')
async def get_console_log(report_id: str, from_line: int = Query(0)):
    """
    Get Report Agent's console output log
    """
    try:
        log_data = ReportManager.get_console_log(report_id, from_line=from_line)

        return {
            "success": True,
            "data": log_data
        }

    except Exception as e:
        logger.error(f"Failed to get console log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@report_router.get('/{report_id}/console-log/stream')
async def stream_console_log(report_id: str):
    """
    Get complete console log (fetch all at once)
    """
    try:
        logs = ReportManager.get_console_log_stream(report_id)

        return {
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get console log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Tool Call Endpoints (for debugging) ==============

@report_router.post('/tools/search')
async def search_graph_tool(request: Request, payload: Dict[str, Any] = Body(...)):
    """
    Graph search tool endpoint (for debugging)
    """
    try:
        graph_id = payload.get('graph_id')
        query = payload.get('query')
        limit = payload.get('limit', 10)

        if not graph_id or not query:
            raise HTTPException(status_code=400, detail="Please provide graph_id and query")

        storage = request.app.state.neo4j_storage
        if not storage:
            raise HTTPException(status_code=503, detail="Neo4j storage is not initialized")

        tools = GraphToolsService(storage=storage)
        result = tools.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit
        )

        return {
            "success": True,
            "data": result.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@report_router.post('/tools/statistics')
async def get_graph_statistics_tool(request: Request, payload: Dict[str, Any] = Body(...)):
    """
    Graph statistics tool endpoint (for debugging)
    """
    try:
        graph_id = payload.get('graph_id')

        if not graph_id:
            raise HTTPException(status_code=400, detail="Please provide graph_id")

        storage = request.app.state.neo4j_storage
        if not storage:
            raise HTTPException(status_code=503, detail="Neo4j storage is not initialized")

        tools = GraphToolsService(storage=storage)
        result = tools.get_graph_statistics(graph_id)

        return {
            "success": True,
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get graph statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
