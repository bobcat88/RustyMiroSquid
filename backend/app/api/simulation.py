"""
Simulation-related API routes — Migrated to FastAPI
Step 2: Entity reading and filtering, OASIS simulation preparation and execution
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends

from ..services.entity_reader import EntityReader
from ..services.simulation_manager import SimulationManager
from ..services.simulation_runner import SimulationRunner
from ..utils.logger import get_logger
from ..models.project import ProjectManager
from ..models.task import TaskManager

router = APIRouter()
logger = get_logger('miroshark.api.simulation')

# Interview prompt optimization prefix
INTERVIEW_PROMPT_PREFIX = "Based on your persona, all past memories and actions, reply directly with text without calling any tools: "

def get_storage():
    from app.main import app
    return getattr(app.state, 'neo4j_storage', None)

def _ensure_env_alive(simulation_id: str) -> bool:
    """Check if simulation environment is alive. Auto-restarts if needed."""
    if SimulationRunner.check_env_alive(simulation_id):
        return True

    logger.info(f"Environment not alive for {simulation_id}, attempting auto-restart...")
    # Logic for auto-restart (simplified for brevity, should match Flask version)
    return False # Placeholder

# ============== Entity Reading Endpoints ==============

@router.get("/entities/{graph_id}")
async def get_graph_entities(
    graph_id: str,
    entity_types: Optional[str] = Query(None),
    enrich: bool = Query(True),
    storage = Depends(get_storage)
):
    """Get all entities from the graph (filtered)"""
    try:
        types_list = [t.strip() for t in entity_types.split(',') if t.strip()] if entity_types else None
        reader = EntityReader(storage)
        result = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=types_list,
            enrich_with_edges=enrich
        )
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        logger.error(f"Failed to fetch entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============== Simulation Management Endpoints ==============

@router.post("/create")
async def create_simulation(payload: dict):
    """Create a new simulation"""
    try:
        project_id = payload.get('project_id')
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id is required")
        
        project = ProjectManager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        graph_id = payload.get('graph_id') or project.graph_id
        if not graph_id:
            raise HTTPException(status_code=400, detail="Graph not built yet")
        
        manager = SimulationManager()
        state = manager.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=payload.get('enable_twitter', True),
            enable_reddit=payload.get('enable_reddit', True),
            enable_polymarket=payload.get('enable_polymarket', False),
        )
        return {"success": True, "data": state.to_dict()}
    except Exception as e:
        logger.error(f"Failed to create simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/prepare")
async def prepare_simulation(payload: dict, background_tasks: BackgroundTasks, storage = Depends(get_storage)):
    """Prepare simulation environment (async)"""
    simulation_id = payload.get('simulation_id')
    if not simulation_id:
        raise HTTPException(status_code=400, detail="simulation_id is required")
    
    manager = SimulationManager()
    state = manager.get_simulation(simulation_id)
    if not state:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    # Check if already prepared
    # ... logic from Flask ...
    
    task_manager = TaskManager()
    task_id = task_manager.create_task("Simulation Prepare")
    
    def run_prepare_task():
        # Core preparation logic
        try:
            manager.prepare_simulation(
                simulation_id=simulation_id,
                storage=storage,
                # ... other params ...
            )
            task_manager.complete_task(task_id)
        except Exception as e:
            task_manager.fail_task(task_id, str(e))

    background_tasks.add_task(run_prepare_task)
    
    return {
        "success": True,
        "data": {
            "simulation_id": simulation_id,
            "task_id": task_id,
            "status": "preparing"
        }
    }

@router.get("/{simulation_id}")
async def get_simulation(simulation_id: str):
    """Get simulation status"""
    manager = SimulationManager()
    state = manager.get_simulation(simulation_id)
    if not state:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return {"success": True, "data": state.to_dict()}

@router.post("/run")
async def run_simulation(payload: dict, background_tasks: BackgroundTasks):
    """Start simulation execution"""
    simulation_id = payload.get('simulation_id')
    platform_name = payload.get('platform', 'parallel')
    start_round = payload.get('start_round', 0)
    
    if not simulation_id:
        raise HTTPException(status_code=400, detail="simulation_id is required")
        
    try:
        # Check preparation status
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if not state:
            raise HTTPException(status_code=404, detail="Simulation not found")
            
        def simulation_task():
            try:
                SimulationRunner.start_simulation(
                    simulation_id=simulation_id,
                    platform=platform_name,
                    start_round=start_round
                )
            except Exception as e:
                logger.error(f"Simulation run failed: {e}")

        background_tasks.add_task(simulation_task)
        
        return {
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "status": "running",
                "platform": platform_name
            }
        }
    except Exception as e:
        logger.error(f"Failed to start simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop/{simulation_id}")
async def stop_simulation(simulation_id: str):
    """Stop running simulation"""
    try:
        success = SimulationRunner.stop_simulation(simulation_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interact/{simulation_id}/{agent_uuid}")
async def agent_interaction(
    simulation_id: str, 
    agent_uuid: str, 
    payload: dict
):
    """Interact (interview) with an agent"""
    prompt = payload.get('prompt')
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
        
    try:
        # Optimization logic from original simulation.py
        if not prompt.startswith(INTERVIEW_PROMPT_PREFIX):
            prompt = INTERVIEW_PROMPT_PREFIX + prompt
            
        # Ensure env is alive
        if not _ensure_env_alive(simulation_id):
             raise HTTPException(status_code=503, detail="Simulation environment not ready")
             
        # Mocking OASIS response for migration demo
        # In reality, this would call OasisAgent.interview(...)
        return {
            "success": True,
            "data": {
                "agent_uuid": agent_uuid,
                "response": "Agent response placeholder (FastAPI)",
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Interaction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/{simulation_id}/{agent_uuid}")
async def get_agent_memory(simulation_id: str, agent_uuid: str):
    """Retrieve agent's memory/history"""
    try:
        # Logic to fetch from internal OASIS state
        return {
            "success": True,
            "data": {
                "agent_uuid": agent_uuid,
                "history": [] # TODO [2026-03-14] : Integrate with OASIS RoundMemory
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
