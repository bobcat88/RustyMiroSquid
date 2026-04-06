"""
Simulation-related API routes
Step 2: Entity reading and filtering, OASIS simulation preparation and execution (fully automated)
"""

import os
import io
import csv
import json
import traceback
import tempfile
import threading
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from fastapi import Request, HTTPException, Body, Query, Path, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from . import simulation_router
from ..schemas import SuccessResponse
from ..config import Config
from ..services.entity_reader import EntityReader
from ..services.oasis_profile_generator import OasisProfileGenerator
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_runner import SimulationRunner, RunnerStatus
from ..utils.logger import get_logger
from ..models.project import ProjectManager

logger = get_logger('rustymirosquid.api.simulation')


# Interview prompt optimization prefix
# Adding this prefix prevents Agents from calling tools and makes them reply with text directly
INTERVIEW_PROMPT_PREFIX = "Based on your persona, all past memories and actions, reply directly with text without calling any tools: "


def _ensure_env_alive(simulation_id: str) -> bool:
    """
    Check if simulation environment is alive. If not, try to restart it
    in env-only mode for interviews. Returns True if env is alive.
    """
    if SimulationRunner.check_env_alive(simulation_id):
        return True

    # Try to auto-restart the environment
    logger.info(f"Environment not alive for {simulation_id}, attempting auto-restart for interviews...")
    is_prepared, _ = _check_simulation_prepared(simulation_id)
    if not is_prepared:
        return False

    try:
        SimulationRunner.start_simulation(
            simulation_id=simulation_id,
            platform='parallel',
            start_round=0,
            env_only=True
        )
        # Wait a bit for the env to start
        import time
        for _ in range(15):
            time.sleep(2)
            if SimulationRunner.check_env_alive(simulation_id):
                logger.info(f"Environment auto-restarted for {simulation_id}")
                return True
        logger.warning(f"Environment auto-restart timed out for {simulation_id}")
        return False
    except Exception as e:
        logger.error(f"Failed to auto-restart environment: {e}")
        return False


def optimize_interview_prompt(prompt: str) -> str:
    """
    Optimize interview prompt by adding prefix to prevent Agent from calling tools

    Args:
        prompt: Original question

    Returns:
        Optimized question
    """
    if not prompt:
        return prompt
    # Avoid adding prefix repeatedly
    if prompt.startswith(INTERVIEW_PROMPT_PREFIX):
        return prompt
    return f"{INTERVIEW_PROMPT_PREFIX}{prompt}"


# ============== Entity Reading Endpoints ==============

@simulation_router.get('/entities/{graph_id}', response_model=SuccessResponse)
async def get_graph_entities(
    request: Request,
    graph_id: str,
    entity_types: Optional[str] = Query(None),
    enrich: bool = Query(True)
):
    """
    Get all entities from the graph (filtered)
    """
    try:
        types = [t.strip() for t in entity_types.split(',') if t.strip()] if entity_types else None

        logger.info(f"Fetching graph entities: graph_id={graph_id}, entity_types={types}, enrich={enrich}")

        storage = request.app.state.neo4j_storage
        if not storage:
            raise HTTPException(status_code=503, detail="GraphStorage not initialized")
        
        reader = EntityReader(storage)
        result = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=types,
            enrich_with_edges=enrich
        )
        
        return SuccessResponse(success=True, data=result.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to fetch graph entities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/entities/{graph_id}/{entity_uuid}', response_model=SuccessResponse)
async def get_entity_detail(request: Request, graph_id: str, entity_uuid: str):
    """Get detailed information for a single entity"""
    try:
        storage = request.app.state.neo4j_storage
        if not storage:
            raise HTTPException(status_code=503, detail="GraphStorage not initialized")
        
        reader = EntityReader(storage)
        entity = reader.get_entity_with_context(graph_id, entity_uuid)
        
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entity not found: {entity_uuid}")
        
        return SuccessResponse(success=True, data=entity.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/entities/{graph_id}/by-type/{entity_type}', response_model=SuccessResponse)
async def get_entities_by_type(request: Request, graph_id: str, entity_type: str, enrich: bool = Query(True)):
    """Get all entities of a specified type"""
    try:
        storage = request.app.state.neo4j_storage
        if not storage:
            raise HTTPException(status_code=503, detail="GraphStorage not initialized")
        
        reader = EntityReader(storage)
        entities = reader.get_entities_by_type(
            graph_id=graph_id,
            entity_type=entity_type,
            enrich_with_edges=enrich
        )
        
        return SuccessResponse(success=True, data={
            "entity_type": entity_type,
            "count": len(entities),
            "entities": [e.to_dict() for e in entities]
        })
        
    except Exception as e:
        logger.error(f"Failed to get entities: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Simulation Management Endpoints ==============

@simulation_router.post('/create', response_model=SuccessResponse)
async def create_simulation(data: Dict[str, Any] = Body(...)):
    """
    Create a new simulation
    """
    try:
        project_id = data.get('project_id')
        if not project_id:
            raise HTTPException(status_code=400, detail="Please provide project_id")
        
        project = ProjectManager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        graph_id = data.get('graph_id') or project.graph_id
        if not graph_id:
            raise HTTPException(status_code=400, detail="Graph not yet built for this project, please call /api/graph/build first")
        
        manager = SimulationManager()
        state = manager.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=data.get('enable_twitter', True),
            enable_reddit=data.get('enable_reddit', True),
            enable_polymarket=data.get('enable_polymarket', False),
        )
        
        return SuccessResponse(success=True, data=state.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _check_simulation_prepared(simulation_id: str) -> tuple:
    """
    Check if the simulation has been prepared

    Conditions checked:
    1. state.json exists and status is "ready"
    2. Required files exist: reddit_profiles.json, twitter_profiles.csv, simulation_config.json

    Note: Run scripts (run_*.py) remain in backend/scripts/ directory and are no longer copied to simulation directory

    Args:
        simulation_id: Simulation ID

    Returns:
        (is_prepared: bool, info: dict)
    """
    import os
    from ..config import Config
    
    simulation_dir = os.path.join(Config.WONDERWALL_SIMULATION_DATA_DIR, simulation_id)
    
    # Check if directory exists
    if not os.path.exists(simulation_dir):
        return False, {"reason": "Simulation directory does not exist"}
    
    # Required files list (excluding scripts, which are in backend/scripts/)
    required_files = [
        "state.json",
        "simulation_config.json",
        "reddit_profiles.json",
        "twitter_profiles.csv"
    ]
    
    # Check if files exist
    existing_files = []
    missing_files = []
    for f in required_files:
        file_path = os.path.join(simulation_dir, f)
        if os.path.exists(file_path):
            existing_files.append(f)
        else:
            missing_files.append(f)
    
    if missing_files:
        return False, {
            "reason": "Missing required files",
            "missing_files": missing_files,
            "existing_files": existing_files
        }
    
    # Check status in state.json
    state_file = os.path.join(simulation_dir, "state.json")
    try:
        import json
        with open(state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        
        status = state_data.get("status", "")
        config_generated = state_data.get("config_generated", False)
        
        # Detailed logging
        logger.debug(f"Checking simulation preparation status: {simulation_id}, status={status}, config_generated={config_generated}")
        
        # If config_generated=True and files exist, consider preparation complete
        # The following statuses indicate preparation is complete:
        # - ready: preparation complete, can run
        # - preparing: if config_generated=True it means completed
        # - running: currently running, preparation was done long ago
        # - completed: run finished, preparation was done long ago
        # - stopped: stopped, preparation was done long ago
        # - failed: run failed (but preparation is complete)
        prepared_statuses = ["ready", "preparing", "running", "completed", "stopped", "failed", "paused"]
        if status in prepared_statuses and config_generated:
            # Get file statistics
            profiles_file = os.path.join(simulation_dir, "reddit_profiles.json")
            config_file = os.path.join(simulation_dir, "simulation_config.json")
            
            profiles_count = 0
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    profiles_count = len(profiles_data) if isinstance(profiles_data, list) else 0
            
            # If status is preparing but files are complete, auto-update status to ready
            if status == "preparing":
                try:
                    state_data["status"] = "ready"
                    from datetime import datetime
                    state_data["updated_at"] = datetime.now().isoformat()
                    with open(state_file, 'w', encoding='utf-8') as f:
                        json.dump(state_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Auto-updated simulation status: {simulation_id} preparing -> ready")
                    status = "ready"
                except Exception as e:
                    logger.warning(f"Failed to auto-update status: {e}")
            
            logger.info(f"Simulation {simulation_id} check result: preparation complete (status={status}, config_generated={config_generated})")
            return True, {
                "status": status,
                "entities_count": state_data.get("entities_count", 0),
                "profiles_count": profiles_count,
                "entity_types": state_data.get("entity_types", []),
                "config_generated": config_generated,
                "created_at": state_data.get("created_at"),
                "updated_at": state_data.get("updated_at"),
                "existing_files": existing_files
            }
        else:
            logger.warning(f"Simulation {simulation_id} check result: not prepared (status={status}, config_generated={config_generated})")
            return False, {
                "reason": f"Status not in prepared list or config_generated is false: status={status}, config_generated={config_generated}",
                "status": status,
                "config_generated": config_generated
            }
            
    except Exception as e:
        return False, {"reason": f"Failed to read state file: {str(e)}"}


@simulation_router.post('/prepare', response_model=SuccessResponse)
async def prepare_simulation(background_tasks: BackgroundTasks, data: Dict[str, Any] = Body(...)):
    """
    Step 2: Prepare simulation
    """
    try:
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")
        
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
        
        force_regenerate = data.get('force_regenerate', False)
        if not force_regenerate:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            if is_prepared:
                return SuccessResponse(success=True, data={
                    "simulation_id": simulation_id,
                    "status": "ready",
                    "message": "Preparation already complete",
                    "already_prepared": True,
                    "prepare_info": prepare_info
                })
        
        # Start background task
        background_tasks.add_task(_run_prepare_task, simulation_id, data)
        
        return SuccessResponse(success=True, data={
            "simulation_id": simulation_id,
            "status": "preparing",
            "message": "Preparation started in background"
        })
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to start preparation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _run_prepare_task(simulation_id: str, data: dict):
    # This replaces the internal threading logic
    # I'll need to define this function properly or adapt the existing one
    pass


@simulation_router.post('/prepare/status', response_model=SuccessResponse)
async def get_prepare_status(data: Dict[str, Any] = Body(...)):
    """
    Query preparation task progress

    Supports two query methods:
    1. Query ongoing task progress by task_id
    2. Check if preparation is already complete by simulation_id

    Request (JSON):
        {
            "task_id": "task_xxxx",          // Optional, task_id returned from prepare
            "simulation_id": "sim_xxxx"      // Optional, simulation ID (to check completed preparation)
        }

    Returns:
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|ready",
                "progress": 45,
                "message": "...",
                "already_prepared": true|false,  // Whether preparation is already complete
                "prepare_info": {...}            // Detailed info when preparation is complete
            }
        }
    """
    from ..models.task import TaskManager
    
    try:
        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')
        
        if simulation_id:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            if is_prepared:
                return SuccessResponse(success=True, data={
                    "simulation_id": simulation_id,
                    "status": "ready",
                    "progress": 100,
                    "message": "Preparation work already complete",
                    "already_prepared": True,
                    "prepare_info": prepare_info
                })
        
        # If no task_id, return error
        if not task_id:
            if simulation_id:
                return SuccessResponse(success=True, data={
                    "simulation_id": simulation_id,
                    "status": "not_started",
                    "progress": 0,
                    "message": "Preparation has not started",
                    "already_prepared": False
                })
            raise HTTPException(status_code=400, detail="Please provide task_id or simulation_id")
        
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        
        if not task:
            # Task not found, but if simulation_id is provided, check if preparation is complete
            if simulation_id:
                is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
                if is_prepared:
                    return SuccessResponse(success=True, data={
                        "simulation_id": simulation_id,
                        "task_id": task_id,
                        "status": "ready",
                        "progress": 100,
                        "message": "Task completed (preparation already exists)",
                        "already_prepared": True,
                        "prepare_info": prepare_info
                    })
            
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        
        task_dict = task.to_dict()
        task_dict["already_prepared"] = False
        
        return SuccessResponse(success=True, data=task_dict)
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to query task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}', response_model=SuccessResponse)
async def get_simulation(simulation_id: str):
    """Get simulation status"""
    try:
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")
        
        result = state.to_dict()
        
        # If simulation is ready, append run instructions
        if state.status == SimulationStatus.READY:
            result["run_instructions"] = manager.get_run_instructions(simulation_id)
        
        return SuccessResponse(success=True, data=result)
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to get simulation status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/list', response_model=SuccessResponse)
async def list_simulations(project_id: Optional[str] = Query(None)):
    """
    List all simulations
    """
    try:
        manager = SimulationManager()
        simulations = manager.list_simulations(project_id=project_id)
        
        return SuccessResponse(
            success=True, 
            data=[s.to_dict() for s in simulations],
            count=len(simulations)
        )
        
    except Exception as e:
        logger.error(f"Failed to list simulations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_report_id_for_simulation(simulation_id: str) -> str:
    """
    Get the latest report_id corresponding to a simulation

    Traverses the reports directory to find reports matching the simulation_id.
    If multiple exist, returns the most recent one (sorted by created_at).

    Args:
        simulation_id: Simulation ID

    Returns:
        report_id or None
    """
    import json
    from datetime import datetime
    
    # reports directory path: backend/uploads/reports
    # __file__ is app/api/simulation.py, need to go up two levels to backend/
    reports_dir = os.path.join(os.path.dirname(__file__), '../../uploads/reports')
    if not os.path.exists(reports_dir):
        return None
    
    matching_reports = []
    
    try:
        for report_folder in os.listdir(reports_dir):
            report_path = os.path.join(reports_dir, report_folder)
            if not os.path.isdir(report_path):
                continue
            
            meta_file = os.path.join(report_path, "meta.json")
            if not os.path.exists(meta_file):
                continue
            
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                
                if meta.get("simulation_id") == simulation_id:
                    matching_reports.append({
                        "report_id": meta.get("report_id"),
                        "created_at": meta.get("created_at", ""),
                        "status": meta.get("status", "")
                    })
            except Exception:
                continue
        
        if not matching_reports:
            return None
        
        # Sort by creation time descending, return the most recent
        matching_reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return matching_reports[0].get("report_id")
        
    except Exception as e:
        logger.warning(f"Failed to find report for simulation {simulation_id}: {e}")
        return None


@simulation_router.get('/history', response_model=SuccessResponse)
async def get_simulation_history(limit: int = Query(20)):
    """
    Get historical simulation list (with project details)
    """
    try:
        manager = SimulationManager()
        simulations = manager.list_simulations()[:limit]
        
        enriched_simulations = []
        for sim in simulations:
            sim_dict = sim.to_dict()
            
            config = manager.get_simulation_config(sim.simulation_id)
            if config:
                sim_dict["simulation_requirement"] = config.get("simulation_requirement", "")
                time_config = config.get("time_config", {})
                sim_dict["total_simulation_hours"] = time_config.get("total_simulation_hours", 0)
                recommended_rounds = int(
                    time_config.get("total_simulation_hours", 0) * 60 / 
                    max(time_config.get("minutes_per_round", 60), 1)
                )
            else:
                sim_dict["simulation_requirement"] = ""
                sim_dict["total_simulation_hours"] = 0
                recommended_rounds = 0
            
            run_state = SimulationRunner.get_run_state(sim.simulation_id)
            if run_state:
                sim_dict["current_round"] = run_state.current_round
                sim_dict["runner_status"] = run_state.runner_status.value
                sim_dict["total_rounds"] = run_state.total_rounds if run_state.total_rounds > 0 else recommended_rounds
            else:
                sim_dict["current_round"] = 0
                sim_dict["runner_status"] = "idle"
                sim_dict["total_rounds"] = recommended_rounds
            
            project = ProjectManager.get_project(sim.project_id)
            if project and hasattr(project, 'files') and project.files:
                sim_dict["files"] = [
                    {"filename": f.get("filename", "Unknown file")} 
                    for f in project.files[:3]
                ]
            else:
                sim_dict["files"] = []
            
            sim_dict["report_id"] = _get_report_id_for_simulation(sim.simulation_id)
            sim_dict["version"] = "v1.0.2"
            
            try:
                created_date = sim_dict.get("created_at", "")[:10]
                sim_dict["created_date"] = created_date
            except:
                sim_dict["created_date"] = ""
            
            enriched_simulations.append(sim_dict)
        
        return SuccessResponse(
            success=True, 
            data=enriched_simulations,
            count=len(enriched_simulations)
        )
        
    except Exception as e:
        logger.error(f"Failed to get simulation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}/profiles', response_model=SuccessResponse)
async def get_simulation_profiles(
    simulation_id: str = Path(...),
    platform: str = Query('reddit')
):
    """
    Get simulation Agent Profiles
    """
    try:
        manager = SimulationManager()
        profiles = manager.get_profiles(simulation_id, platform=platform)
        
        return SuccessResponse(success=True, data={
            "platform": platform,
            "count": len(profiles),
            "profiles": profiles
        })
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}/profiles/realtime', response_model=SuccessResponse)
async def get_simulation_profiles_realtime(
    simulation_id: str = Path(...),
    platform: str = Query('reddit')
):
    """
    Get simulation Agent Profiles in real-time
    """
    import json
    import csv
    from datetime import datetime
    
    try:
        sim_dir = os.path.join(Config.WONDERWALL_SIMULATION_DATA_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")

        if platform == "reddit":
            profiles_file = os.path.join(sim_dir, "reddit_profiles.json")
        else:
            profiles_file = os.path.join(sim_dir, "twitter_profiles.csv")

        file_exists = os.path.exists(profiles_file)
        profiles = []
        file_modified_at = None
        
        if file_exists:
            file_stat = os.stat(profiles_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            
            try:
                if platform == "reddit":
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        profiles = json.load(f)
                else:
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        profiles = list(reader)
            except Exception as e:
                logger.warning(f"Failed to read profiles file (may be in the process of writing): {e}")
                profiles = []
        
        is_generating = False
        total_expected = None

        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    total_expected = state_data.get("entities_count")
            except Exception: pass
        
        return SuccessResponse(success=True, data={
            "simulation_id": simulation_id,
            "platform": platform,
            "count": len(profiles),
            "total_expected": total_expected,
            "is_generating": is_generating,
            "file_exists": file_exists,
            "file_modified_at": file_modified_at,
            "profiles": profiles
        })
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to get profiles in real-time: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}/config/realtime', response_model=SuccessResponse)
async def get_simulation_config_realtime(simulation_id: str = Path(...)):
    """
    Get simulation configuration in real-time
    """
    import json
    from datetime import datetime
    
    try:
        sim_dir = os.path.join(Config.WONDERWALL_SIMULATION_DATA_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")

        config_file = os.path.join(sim_dir, "simulation_config.json")
        file_exists = os.path.exists(config_file)
        config = None
        file_modified_at = None
        
        if file_exists:
            file_stat = os.stat(config_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read config file (may be in the process of writing): {e}")
                config = None
        
        is_generating = False
        generation_stage = None
        config_generated = False
        
        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    config_generated = state_data.get("config_generated", False)
                    
                    if is_generating:
                        if state_data.get("profiles_generated", False):
                            generation_stage = "generating_config"
                        else:
                            generation_stage = "generating_profiles"
                    elif status == "ready":
                        generation_stage = "completed"
            except Exception: pass
        
        response_data = {
            "simulation_id": simulation_id,
            "file_exists": file_exists,
            "file_modified_at": file_modified_at,
            "is_generating": is_generating,
            "generation_stage": generation_stage,
            "config_generated": config_generated,
            "config": config
        }
        
        if config:
            response_data["summary"] = {
                "total_agents": len(config.get("agent_configs", [])),
                "simulation_hours": config.get("time_config", {}).get("total_simulation_hours"),
                "initial_posts_count": len(config.get("event_config", {}).get("initial_posts", [])),
                "hot_topics_count": len(config.get("event_config", {}).get("hot_topics", [])),
                "has_twitter_config": "twitter_config" in config,
                "has_reddit_config": "reddit_config" in config,
                "generated_at": config.get("generated_at"),
                "llm_model": config.get("llm_model")
            }
        
        return SuccessResponse(success=True, data=response_data)
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to get config in real-time: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}/config', response_model=SuccessResponse)
async def get_simulation_config(simulation_id: str = Path(...)):
    """
    Get simulation configuration
    """
    try:
        manager = SimulationManager()
        config = manager.get_simulation_config(simulation_id)
        
        if not config:
            raise HTTPException(status_code=404, detail="Simulation configuration does not exist, please call /prepare endpoint first")
        
        return SuccessResponse(success=True, data=config)
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}/config/download')
async def download_simulation_config(simulation_id: str = Path(...)):
    """Download simulation configuration file"""
    try:
        manager = SimulationManager()
        sim_dir = manager._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            raise HTTPException(status_code=404, detail="Configuration file does not exist, please call /prepare endpoint first")
        
        return FileResponse(
            config_path,
            filename="simulation_config.json"
        )
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to download configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/script/{script_name}/download')
async def download_simulation_script(script_name: str = Path(...)):
    """
    Download simulation run script file
    """
    try:
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        allowed_scripts = [
            "run_twitter_simulation.py",
            "run_reddit_simulation.py", 
            "run_parallel_simulation.py",
            "action_logger.py"
        ]
        
        if script_name not in allowed_scripts:
            raise HTTPException(status_code=400, detail=f"Unknown script: {script_name}, options: {allowed_scripts}")
        
        script_path = os.path.join(scripts_dir, script_name)
        
        if not os.path.exists(script_path):
            raise HTTPException(status_code=404, detail=f"Script file does not exist: {script_name}")
        
        return FileResponse(
            script_path,
            filename=script_name
        )
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to download script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Profile Generation Endpoint (standalone use) ==============

@simulation_router.post('/generate-profiles', response_model=SuccessResponse)
async def generate_profiles(data: dict = Body(...)):
    """
    Directly generate OASIS Agent Profile from graph
    """
    try:
        graph_id = data.get('graph_id')
        if not graph_id:
            raise HTTPException(status_code=400, detail="Please provide graph_id")
        
        entity_types = data.get('entity_types')
        use_llm = data.get('use_llm', True)
        platform = data.get('platform', 'reddit')

        # Use dependencies for neo4j_storage if possible, but here we can keep it simple
        from app.api import get_neo4j_storage
        storage = get_neo4j_storage()
        if not storage:
            raise HTTPException(status_code=500, detail="GraphStorage not initialized")
            
        reader = EntityReader(storage)
        filtered = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=True
        )
        
        if filtered.filtered_count == 0:
            raise HTTPException(status_code=400, detail="No matching entities found")
        
        generator = OasisProfileGenerator()
        profiles = generator.generate_profiles_from_entities(
            entities=filtered.entities,
            use_llm=use_llm
        )
        
        if platform == "reddit":
            profiles_data = [p.to_reddit_format() for p in profiles]
        elif platform == "twitter":
            profiles_data = [p.to_twitter_format() for p in profiles]
        else:
            profiles_data = [p.to_dict() for p in profiles]
        
        return SuccessResponse(success=True, data={
            "platform": platform,
            "entity_types": list(filtered.entity_types),
            "count": len(profiles_data),
            "profiles": profiles_data
        })
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to generate profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Simulation Run Control Endpoints ==============

@simulation_router.post('/start', response_model=SuccessResponse)
async def start_simulation(data: dict = Body(...)):
    """
    Start running simulation
    """
    try:
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")

        platform = data.get('platform', 'parallel')
        max_rounds = data.get('max_rounds')
        enable_graph_memory_update = data.get('enable_graph_memory_update', False)
        force = data.get('force', False)
        resume = data.get('resume', False)

        start_round = 0
        if resume:
            existing_state = SimulationRunner.get_run_state(simulation_id)
            if existing_state and existing_state.current_round > 0:
                start_round = existing_state.current_round
                logger.info(f"Resuming simulation {simulation_id} from round {start_round}")

        if max_rounds is not None:
            try:
                max_rounds = int(max_rounds)
                if max_rounds <= 0:
                    raise HTTPException(status_code=400, detail="max_rounds must be a positive integer")
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="max_rounds must be a valid integer")

        if platform not in ['twitter', 'reddit', 'polymarket', 'parallel']:
            raise HTTPException(status_code=400, detail=f"Invalid platform type: {platform}")

        enable_cross_platform = data.get('enable_cross_platform', True)

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")

        force_restarted = False
        
        if state.status != SimulationStatus.READY:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)

            if is_prepared:
                if state.status == SimulationStatus.RUNNING:
                    run_state = SimulationRunner.get_run_state(simulation_id)
                    if run_state and run_state.runner_status.value == "running":
                        if force:
                            logger.info(f"Force mode: stopping running simulation {simulation_id}")
                            try:
                                SimulationRunner.stop_simulation(simulation_id)
                            except Exception as e:
                                logger.warning(f"Warning while stopping simulation: {str(e)}")
                        else:
                            raise HTTPException(status_code=400, detail="Simulation is running, please call /stop endpoint to stop first, or use force=true to force restart")

                if force and not resume:
                    logger.info(f"Force mode: cleaning simulation logs {simulation_id}")
                    cleanup_result = SimulationRunner.cleanup_simulation_logs(simulation_id)
                    if not cleanup_result.get("success"):
                        logger.warning(f"Warning while cleaning logs: {cleanup_result.get('errors')}")
                    force_restarted = True

                logger.info(f"Simulation {simulation_id} preparation complete, reset status to ready")
                state.status = SimulationStatus.READY
                manager._save_simulation_state(state)
            else:
                raise HTTPException(status_code=400, detail=f"Simulation not ready, current status: {state.status.value}")
        
        graph_id = None
        if enable_graph_memory_update:
            graph_id = state.graph_id
            if not graph_id:
                project = ProjectManager.get_project(state.project_id)
                if project:
                    graph_id = project.graph_id
            
            if not graph_id:
                raise HTTPException(status_code=400, detail="Enabling graph memory update requires a valid graph_id")
            
            logger.info(f"Enable graph memory update: simulation_id={simulation_id}, graph_id={graph_id}")
        
        sim_storage = None
        if enable_graph_memory_update:
            from app.api import get_neo4j_storage
            sim_storage = get_neo4j_storage()

        run_state = SimulationRunner.start_simulation(
            simulation_id=simulation_id,
            platform=platform,
            max_rounds=max_rounds,
            enable_graph_memory_update=enable_graph_memory_update,
            graph_id=graph_id,
            storage=sim_storage,
            start_round=start_round,
            enable_cross_platform=enable_cross_platform,
        )
        
        state.status = SimulationStatus.RUNNING
        manager._save_simulation_state(state)
        
        response_data = run_state.to_dict()
        if max_rounds:
            response_data['max_rounds_applied'] = max_rounds
        response_data['graph_memory_update_enabled'] = enable_graph_memory_update
        response_data['force_restarted'] = force_restarted
        response_data['resumed'] = resume and start_round > 0
        if start_round > 0:
            response_data['resumed_from_round'] = start_round
        if enable_graph_memory_update:
            response_data['graph_id'] = graph_id
        
        return SuccessResponse(success=True, data=response_data)
        
    except HTTPException: raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.post('/stop', response_model=SuccessResponse)
async def stop_simulation(data: dict = Body(...)):
    """
    Stop simulation
    """
    try:
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")
        
        run_state = SimulationRunner.stop_simulation(simulation_id)
        
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.PAUSED
            manager._save_simulation_state(state)
        
        return SuccessResponse(success=True, data=run_state.to_dict())
        
    except HTTPException: raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to stop simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Real-time Status Monitoring Endpoints ==============

@simulation_router.get('/{simulation_id}/run-status', response_model=SuccessResponse)
async def get_run_status(simulation_id: str = Path(...)):
    """
    Get simulation real-time running status
    """
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)
        
        if not run_state:
            return SuccessResponse(success=True, data={
                "simulation_id": simulation_id,
                "runner_status": "idle",
                "current_round": 0,
                "total_rounds": 0,
                "progress_percent": 0,
                "twitter_actions_count": 0,
                "reddit_actions_count": 0,
                "total_actions_count": 0,
            })
        
        return SuccessResponse(success=True, data=run_state.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get running status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}/run-status/detail', response_model=SuccessResponse)
async def get_run_status_detail(simulation_id: str = Path(...), platform: str = Query(None)):
    """
    Get simulation detailed running status (including all actions)
    """
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)
        
        if not run_state:
            return SuccessResponse(success=True, data={
                "simulation_id": simulation_id,
                "runner_status": "idle",
                "all_actions": [],
                "twitter_actions": [],
                "reddit_actions": []
            })
        
        # Get complete action list
        all_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform=platform
        )
        
        # Get actions by platform
        twitter_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform="twitter"
        ) if not platform or platform == "twitter" else []
        
        reddit_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform="reddit"
        ) if not platform or platform == "reddit" else []
        
        # Get current round actions (recent_actions only shows latest round)
        current_round = run_state.current_round
        recent_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id,
            platform=platform,
            round_num=current_round
        ) if current_round > 0 else []
        
        # Get basic status information
        result = run_state.to_dict()
        result["all_actions"] = [a.to_dict() for a in all_actions]
        result["twitter_actions"] = [a.to_dict() for a in twitter_actions]
        result["reddit_actions"] = [a.to_dict() for a in reddit_actions]
        result["rounds_count"] = len(run_state.rounds)
        # recent_actions only shows current latest round content for both platforms
        result["recent_actions"] = [a.to_dict() for a in recent_actions]
        
        return SuccessResponse(success=True, data=result)
        
    except Exception as e:
        logger.error(f"Failed to get detailed status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}/actions', response_model=SuccessResponse)
async def get_simulation_actions(
    simulation_id: str = Path(...),
    limit: int = Query(100),
    offset: int = Query(0),
    platform: str = Query(None),
    agent_id: int = Query(None),
    round_num: int = Query(None)
):
    """
    Get agent action history during simulation
    """
    try:
        actions = SimulationRunner.get_actions(
            simulation_id=simulation_id,
            limit=limit,
            offset=offset,
            platform=platform,
            agent_id=agent_id,
            round_num=round_num
        )
        
        return SuccessResponse(success=True, data={
            "count": len(actions),
            "actions": [a.to_dict() for a in actions]
        })
        
    except Exception as e:
        logger.error(f"Failed to get action history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}/timeline', response_model=SuccessResponse)
async def get_simulation_timeline(
    simulation_id: str = Path(...),
    start_round: int = Query(0),
    end_round: int = Query(None)
):
    """
    Get simulation timeline (summarized by round)
    """
    try:
        timeline = SimulationRunner.get_timeline(
            simulation_id=simulation_id,
            start_round=start_round,
            end_round=end_round
        )
        
        return SuccessResponse(success=True, data={
            "rounds_count": len(timeline),
            "timeline": timeline
        })
        
    except Exception as e:
        logger.error(f"Failed to get timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get('/{simulation_id}/agent-stats', response_model=SuccessResponse)
async def get_agent_stats(simulation_id: str = Path(...)):
    """
    Get statistics for each agent
    """
    try:
        stats = SimulationRunner.get_agent_stats(simulation_id)
        
        return SuccessResponse(success=True, data={
            "agents_count": len(stats),
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Failed to get agent statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Influence Leaderboard ==============

@simulation_router.get('/{simulation_id}/influence', response_model=SuccessResponse)
async def get_influence_leaderboard(simulation_id: str = Path(...)):
    """
    Compute agent influence scores from simulation action JSONL logs.
    """
    try:
        sim_dir = os.path.join(Config.WONDERWALL_SIMULATION_DATA_DIR, simulation_id)

        if not os.path.exists(sim_dir):
            raise HTTPException(status_code=404, detail=f"Simulation not found: {simulation_id}")

        # Engagement action types that credit the original post author
        ENGAGEMENT_TYPES = frozenset({
            'LIKE_POST', 'REPOST', 'QUOTE_POST', 'LIKE_COMMENT',
            'CREATE_COMMENT',  # replying to a post counts as engagement
        })

        agents: Dict[str, Dict[str, Any]] = {}  # agent_name -> mutable stats dict

        def _get_or_create(name):
            if name not in agents:
                agents[name] = {
                    'agent_name': name,
                    'posts_created': 0,
                    'engagement_received': 0,
                    'follows_received': 0,
                    'platforms': set(),
                }
            return agents[name]

        for platform in ('twitter', 'reddit', 'polymarket'):
            actions_path = os.path.join(sim_dir, platform, 'actions.jsonl')
            if not os.path.exists(actions_path):
                continue

            with open(actions_path, 'r', encoding='utf-8') as fh:
                for raw_line in fh:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        event = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    # Skip bookkeeping events that have no agent
                    if event.get('event_type') in (
                        'simulation_start', 'round_start', 'round_end', 'simulation_end'
                    ):
                        continue

                    agent_name = event.get('agent_name')
                    if not agent_name:
                        continue

                    actor = _get_or_create(agent_name)
                    actor['platforms'].add(platform)

                    action_type = event.get('action_type', '')
                    args = event.get('action_args') or {}

                    if action_type == 'CREATE_POST':
                        actor['posts_created'] += 1

                    elif action_type in ENGAGEMENT_TYPES:
                        # Credit the original author, not the actor
                        author = (
                            args.get('post_author_name')
                            or args.get('original_author_name')
                        )
                        if author and author != agent_name:
                            _get_or_create(author)['engagement_received'] += 1

                    elif action_type == 'FOLLOW':
                        target = args.get('target_user_name')
                        if target:
                            _get_or_create(target)['follows_received'] += 1

        if not agents:
            return SuccessResponse(success=True, data={"agents": [], "total_agents": 0})

        ranked: List[Dict[str, Any]] = []
        for a in agents.values():
            platform_count = len(a['platforms'])
            score = (
                a['engagement_received'] * 3
                + a['follows_received'] * 2
                + platform_count * 5
                + a['posts_created']
            )
            ranked.append({
                'agent_name': a['agent_name'],
                'posts_created': a['posts_created'],
                'engagement_received': a['engagement_received'],
                'follows_received': a['follows_received'],
                'platform_count': platform_count,
                'platforms': sorted(a['platforms']),
                'influence_score': score,
            })

        ranked.sort(key=lambda x: x['influence_score'], reverse=True)

        # Attach rank (1-based)
        for i, entry in enumerate(ranked):
            entry['rank'] = i + 1

        return SuccessResponse(
            success=True,
            data={
                "agents": ranked[:20],
                "total_agents": len(ranked),
            }
        )

    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to compute influence leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Database Query Endpoints ==============

@simulation_router.get('/{simulation_id}/posts', response_model=SuccessResponse)
async def get_simulation_posts(
    simulation_id: str = Path(...),
    platform: str = Query('reddit'),
    limit: int = Query(50),
    offset: int = Query(0)
):
    """
    Get simulation posts
    """
    try:
        sim_dir = os.path.join(
            os.path.dirname(__file__),
            f'../../uploads/simulations/{simulation_id}'
        )
        
        db_file = f"{platform}_simulation.db"
        db_path = os.path.join(sim_dir, db_file)
        
        if not os.path.exists(db_path):
            return SuccessResponse(success=True, data={
                "platform": platform,
                "count": 0,
                "posts": [],
                "message": "Database does not exist, simulation may not have started"
            })
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM post 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            posts = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT COUNT(*) FROM post")
            total_count = cursor.fetchone()[0]
            
        except sqlite3.OperationalError:
            posts = []
            total_count = 0
        finally:
            conn.close()
        
        return SuccessResponse(success=True, data={
            "platform": platform,
            "total": total_count,
            "count": len(posts),
            "posts": posts
        })
        
    except Exception as e:
        logger.error(f"Failed to get posts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Interview Endpoints ==============

@simulation_router.post('/interview', response_model=SuccessResponse)
async def interview_agent(data: Dict[str, Any] = Body(...)):
    """
    Interview single agent
    """
    try:
        simulation_id = data.get('simulation_id')
        agent_id = data.get('agent_id')
        prompt = data.get('prompt')
        platform = data.get('platform')  # Optional: twitter/reddit/None
        timeout = data.get('timeout', 60)
        
        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")
        
        if agent_id is None:
            raise HTTPException(status_code=400, detail="Please provide agent_id")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Please provide prompt (interview question)")

        # Validate platform parameter
        if platform and platform not in ("twitter", "reddit"):
            raise HTTPException(status_code=400, detail="platform parameter can only be 'twitter' or 'reddit'")

        # Check environment status — auto-restart if needed
        if not _ensure_env_alive(simulation_id):
            raise HTTPException(status_code=400, detail="Simulation environment could not be started. Please try again.")

        # Optimize prompt, add prefix to prevent agent from calling tools
        optimized_prompt = optimize_interview_prompt(prompt)
        
        result = SimulationRunner.interview_agent(
            simulation_id=simulation_id,
            agent_id=agent_id,
            prompt=optimized_prompt,
            platform=platform,
            timeout=timeout
        )

        return SuccessResponse(
            success=result.get("success", False),
            data=result
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Timed out waiting for interview response: {str(e)}")
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Interview failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.post('/interview/batch', response_model=SuccessResponse)
async def interview_agents_batch(data: Dict[str, Any] = Body(...)):
    """
    Batch interview multiple agents
    """
    try:
        simulation_id = data.get('simulation_id')
        interviews = data.get('interviews')
        platform = data.get('platform')  # Optional: twitter/reddit/None
        timeout = data.get('timeout', 120)

        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")

        if not interviews or not isinstance(interviews, list):
            raise HTTPException(status_code=400, detail="Please provide interviews (interview list)")

        # Validate platform parameter
        if platform and platform not in ("twitter", "reddit"):
            raise HTTPException(status_code=400, detail="platform parameter can only be 'twitter' or 'reddit'")

        # Validate each interview item
        for i, interview in enumerate(interviews):
            if 'agent_id' not in interview:
                raise HTTPException(status_code=400, detail=f"Interview list item {i+1} is missing agent_id")
            if 'prompt' not in interview:
                raise HTTPException(status_code=400, detail=f"Interview list item {i+1} is missing prompt")
            # Validate each item's platform (if present)
            item_platform = interview.get('platform')
            if item_platform and item_platform not in ("twitter", "reddit"):
                raise HTTPException(status_code=400, detail=f"Interview list item {i+1} platform can only be 'twitter' or 'reddit'")

        # Check environment status — auto-restart if needed
        if not _ensure_env_alive(simulation_id):
            raise HTTPException(status_code=400, detail="Simulation environment could not be started. Please try again.")

        # Optimize each interview item's prompt, add prefix to prevent agent from calling tools
        optimized_interviews = []
        for interview in interviews:
            optimized_interview = interview.copy()
            optimized_interview['prompt'] = optimize_interview_prompt(interview.get('prompt', ''))
            optimized_interviews.append(optimized_interview)

        result = SimulationRunner.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=optimized_interviews,
            platform=platform,
            timeout=timeout
        )

        return SuccessResponse(
            success=result.get("success", False),
            data=result
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=f"Timed out waiting for batch interview response: {str(e)}")

    except HTTPException: raise
    except Exception as e:
        logger.error(f"Batch interview failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.post('/interview/history', response_model=SuccessResponse)
async def get_interview_history(data: Dict[str, Any] = Body(...)):
    """
    Get interview history
    """
    try:
        simulation_id = data.get('simulation_id')
        platform = data.get('platform')  # If not specified, return history for both platforms
        agent_id = data.get('agent_id')
        limit = data.get('limit', 100)
        
        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")

        history = SimulationRunner.get_interview_history(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            limit=limit
        )

        return SuccessResponse(success=True, data={
            "count": len(history),
            "history": history
        })

    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to get interview history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.post('/env-status', response_model=SuccessResponse)
async def get_env_status(data: Dict[str, Any] = Body(...)):
    """
    Get simulation environment status
    """
    try:
        simulation_id = data.get('simulation_id')
        
        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")

        env_alive = SimulationRunner.check_env_alive(simulation_id)
        
        # Get more detailed status information
        env_status = SimulationRunner.get_env_status_detail(simulation_id)

        if env_alive:
            message = "Environment is running, can receive interview commands"
        else:
            message = "Environment is not running or has been shut down"

        return SuccessResponse(success=True, data={
            "simulation_id": simulation_id,
            "env_alive": env_alive,
            "twitter_available": env_status.get("twitter_available", False),
            "reddit_available": env_status.get("reddit_available", False),
            "message": message
        })

    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to get environment status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.post('/restart-env', response_model=SuccessResponse)
async def restart_env(data: Dict[str, Any] = Body(...)):
    """
    Restart simulation environment for interviews (without running simulation).
    """
    try:
        simulation_id = data.get('simulation_id')

        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")

        # Check if env is already alive
        if SimulationRunner.check_env_alive(simulation_id):
            return SuccessResponse(success=True, data={
                "simulation_id": simulation_id,
                "message": "Environment is already running",
                "already_running": True
            })

        # Check if simulation is prepared
        is_prepared, _ = _check_simulation_prepared(simulation_id)
        if not is_prepared:
            raise HTTPException(status_code=400, detail="Simulation not prepared")

        # Start the simulation script with --env-only
        run_state = SimulationRunner.start_simulation(
            simulation_id=simulation_id,
            platform='parallel',
            start_round=0,
            env_only=True
        )

        return SuccessResponse(success=True, data={
            "simulation_id": simulation_id,
            "process_pid": run_state.process_pid,
            "message": "Environment starting for interviews",
            "already_running": False
        })

    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to restart env: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.post('/close-env', response_model=SuccessResponse)
async def close_simulation_env(data: Dict[str, Any] = Body(...)):
    """
    Shut down simulation environment
    """
    try:
        simulation_id = data.get('simulation_id')
        timeout = data.get('timeout', 30)
        
        if not simulation_id:
            raise HTTPException(status_code=400, detail="Please provide simulation_id")
        
        result = SimulationRunner.close_simulation_env(
            simulation_id=simulation_id,
            timeout=timeout
        )
        
        # Update simulation status
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.COMPLETED
            manager._save_simulation_state(state)
        
        return SuccessResponse(
            success=result.get("success", False),
            data=result
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to shut down environment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Data Export Endpoints ==============

@simulation_router.get('/{simulation_id}/export')
async def export_simulation_data(
    simulation_id: str,
    format: str = Query('json'),
    include: str = Query('actions,posts,timeline,agent_stats,metadata')
):
    """
    Export simulation data as JSON or CSV file download.
    """
    try:
        export_format = format.lower()
        include_sections = {s.strip() for s in include.split(',')}

        if export_format not in ('json', 'csv'):
            raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'csv'.")

        export_data: Dict[str, Any] = {}

        # --- Metadata ---
        if 'metadata' in include_sections:
            manager = SimulationManager()
            state = manager.get_simulation(simulation_id)
            run_state = SimulationRunner.get_run_state(simulation_id)
            export_data['metadata'] = {
                "simulation_id": simulation_id,
                "exported_at": datetime.utcnow().isoformat(),
                "status": state.status.value if state else None,
                "project_id": state.project_id if state else None,
                "run_state": run_state.to_dict() if run_state else None,
            }

        # --- Actions ---
        if 'actions' in include_sections:
            actions = SimulationRunner.get_all_actions(simulation_id)
            export_data['actions'] = [a.to_dict() for a in actions]

        # --- Timeline ---
        if 'timeline' in include_sections:
            export_data['timeline'] = SimulationRunner.get_timeline(simulation_id)

        # --- Agent Stats ---
        if 'agent_stats' in include_sections:
            export_data['agent_stats'] = SimulationRunner.get_agent_stats(simulation_id)

        # --- Posts (both platforms) ---
        if 'posts' in include_sections:
            import sqlite3
            sim_dir = os.path.join(
                os.path.dirname(__file__),
                f'../../uploads/simulations/{simulation_id}'
            )
            all_posts = []
            for platform in ('twitter', 'reddit'):
                db_path = os.path.join(sim_dir, f"{platform}_simulation.db")
                if os.path.exists(db_path):
                    try:
                        conn = sqlite3.connect(db_path)
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute("SELECT * FROM post ORDER BY created_at DESC")
                        for row in cursor.fetchall():
                            post = dict(row)
                            post['platform'] = platform
                            all_posts.append(post)
                        conn.close()
                    except sqlite3.OperationalError:
                        pass
            export_data['posts'] = all_posts

        # --- Build response ---
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename_base = f"rustymirosquid_export_{simulation_id[:12]}_{timestamp}"

        if export_format == 'json':
            content = json.dumps(export_data, indent=2, default=str, ensure_ascii=False)
            return StreamingResponse(
                io.BytesIO(content.encode('utf-8')),
                media_type='application/json',
                headers={"Content-Disposition": f"attachment; filename={filename_base}.json"}
            )

        # CSV: flatten actions into a single table (the most useful tabular view)
        rows = export_data.get('actions', [])
        if not rows:
            raise HTTPException(status_code=404, detail="No action data available to export as CSV")

        fieldnames = ['round_num', 'timestamp', 'platform', 'agent_id',
                      'agent_name', 'action_type', 'action_args', 'result', 'success']

        string_buf = io.StringIO()
        writer = csv.DictWriter(string_buf, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            row_copy = dict(row)
            # Serialize nested dicts to JSON strings for CSV
            if isinstance(row_copy.get('action_args'), dict):
                row_copy['action_args'] = json.dumps(row_copy['action_args'], ensure_ascii=False)
            writer.writerow(row_copy)

        return StreamingResponse(
            io.BytesIO(string_buf.getvalue().encode('utf-8')),
            media_type='text/csv',
            headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"}
        )

    except HTTPException: raise
    except Exception as e:
        logger.error(f"Failed to export simulation data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
