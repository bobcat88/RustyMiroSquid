"""
Graph-related API routes
Uses project context mechanism with server-side persistent state
"""

import json
import os
import traceback
import threading
from fastapi import Request, HTTPException, Body, File, UploadFile, Form
from typing import List, Optional
from . import graph_router
from ..schemas import (
    FetchURLRequest, FetchURLResponse, 
    OntologyGenerateRequest, BuildGraphRequest,
    SuccessResponse, TaskResponse, ProjectResponse
)
from ..config import Config
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus

# Get logger
logger = get_logger('rustymirosquid.api')


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# ============== Project Management APIs ==============

@graph_router.get('/project/{project_id}', response_model=SuccessResponse)
async def get_project(project_id: str):
    """
    Get project details
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    return SuccessResponse(success=True, data=project.to_dict())



# ============== URL Fetch API ==============

@graph_router.post('/fetch-url', response_model=SuccessResponse)
async def fetch_url(payload: FetchURLRequest):
    """
    Fetch a URL and extract readable text for use as a simulation document.
    """
    try:
        url = payload.url.strip()

        if not url:
            raise HTTPException(status_code=400, detail="url is required")

        from ..utils.url_fetcher import fetch_url_text
        result = fetch_url_text(url)

        return SuccessResponse(success=True, data=result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"URL fetch error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch URL: {str(e)}")


# ============== API 1: Upload files and generate ontology ==============

@graph_router.post('/ontology/generate', response_model=SuccessResponse)
async def generate_ontology(
    request: Request,
    simulation_requirement: str = Form(...),
    project_name: str = Form('Unnamed Project'),
    additional_context: Optional[str] = Form(None),
    url_docs: Optional[str] = Form(None),
    files: List[UploadFile] = File(None)
):
    """
    API 1: Upload files and/or URL-fetched texts, then analyze to generate ontology.
    """
    try:
        logger.info("=== Starting ontology generation ===")

        if not simulation_requirement:
            raise HTTPException(status_code=400, detail="Please provide a simulation requirement description")

        # Parse URL docs
        parsed_url_docs = []
        if url_docs:
            try:
                parsed_url_docs = json.loads(url_docs)
            except Exception:
                logger.warning("Failed to parse url_docs field, ignoring")

        if not files and not parsed_url_docs:
            raise HTTPException(status_code=400, detail="Please upload at least one document file or provide URL documents")

        # Create project
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        logger.info(f"Created project: {project.project_id}")

        # Save files and extract text
        document_texts = []
        all_text = ""

        if files:
            for file in files:
                if file.filename and allowed_file(file.filename):
                    # Save file to project directory
                    file_info = ProjectManager.save_file_to_project(
                        project.project_id,
                        file,
                        file.filename
                    )
                    project.files.append({
                        "filename": file_info["original_filename"],
                        "size": file_info["size"]
                    })

                    # Extract text
                    text = FileParser.extract_text(file_info["path"])
                    text = TextProcessor.preprocess_text(text)
                    document_texts.append(text)
                    all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"

        # Incorporate URL-fetched documents
        for doc in parsed_url_docs:
            title = doc.get('title') or doc.get('url', 'URL Document')
            text = doc.get('text', '').strip()
            if not text:
                continue
            text = TextProcessor.preprocess_text(text)
            document_texts.append(text)
            all_text += f"\n\n=== {title} ===\n{text}"
            project.files.append({
                "filename": title,
                "size": len(text),
                "url": doc.get('url', '')
            })
            logger.info(f"Incorporated URL doc: {title} ({len(text)} chars)")

        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            raise HTTPException(status_code=400, detail="No documents were successfully processed")
        
        # Save extracted text
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"Text extraction complete, {len(all_text)} characters total")

        # Generate ontology
        logger.info("Calling LLM to generate ontology definition...")
        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement,
            additional_context=additional_context
        )
        
        # Save ontology to project
        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== Ontology generation complete === Project ID: {project.project_id}")
        
        return SuccessResponse(success=True, data={
            "project_id": project.project_id,
            "project_name": project.name,
            "ontology": project.ontology,
            "analysis_summary": project.analysis_summary,
            "files": project.files,
            "total_text_length": project.total_text_length
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ontology generation error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== API 2: Build graph ==============

@graph_router.post('/build', response_model=SuccessResponse)
async def build_graph(request: Request, payload: BuildGraphRequest):
    """
    API 2: Build graph based on project_id
    """
    try:
        logger.info("=== Starting graph build ===")

        # Check Neo4j storage
        storage = request.app.state.neo4j_storage
        if not storage:
            logger.error("Neo4j storage not initialized")
            raise HTTPException(status_code=503, detail="Neo4j storage is not initialized")
        
        project_id = payload.project_id
        
        # Get project
        project = ProjectManager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        # Check project status
        if project.status == ProjectStatus.CREATED:
            raise HTTPException(status_code=400, detail="Ontology not yet generated")
        
        if project.status == ProjectStatus.GRAPH_BUILDING and not payload.force:
            raise HTTPException(status_code=400, detail="Graph is currently being built")
        
        # If force rebuild, reset state
        if payload.force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
        
        # Get configuration
        graph_name = payload.graph_name or project.name or 'RustyMiroSquid Graph'
        chunk_size = payload.chunk_size or project.chunk_size or Config.DEFAULT_CHUNK_SIZE
        chunk_overlap = payload.chunk_overlap or project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP
        
        # Update project configuration
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # Get extracted text
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            raise HTTPException(status_code=400, detail="Extracted text content not found")
        
        # Get ontology
        ontology = project.ontology
        if not ontology:
            raise HTTPException(status_code=400, detail="Ontology definition not found")
        
        # Create async task
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"Build graph: {graph_name}")
        logger.info(f"Created graph build task: task_id={task_id}, project_id={project_id}")
        
        # Update project status
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        
        # Background task logic (same as before)
        def build_task():
            build_logger = get_logger('rustymirosquid.build')
            try:
                build_logger.info(f"[{task_id}] Starting graph build...")
                task_manager.update_task(task_id, status=TaskStatus.PROCESSING, message="Initializing service...")
                
                builder = GraphBuilderService(storage=storage)
                chunks = TextProcessor.split_text(text, chunk_size=chunk_size, overlap=chunk_overlap)
                total_chunks = len(chunks)
                
                graph_id = builder.create_graph(name=graph_name)
                project.graph_id = graph_id
                ProjectManager.save_project(project)
                
                builder.set_ontology(graph_id, ontology)
                
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)
                    task_manager.update_task(task_id, message=msg, progress=progress)
                
                builder.add_text_batches(graph_id, chunks, batch_size=3, progress_callback=add_progress_callback)
                
                # Retrieve graph data
                graph_data = builder.get_graph_data(graph_id)
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)
                
                task_manager.complete_task(task_id, result={
                    "project_id": project_id,
                    "graph_id": graph_id,
                    "node_count": graph_data.get("node_count", 0),
                    "edge_count": graph_data.get("edge_count", 0),
                    "chunk_count": total_chunks
                })
                
            except Exception as e:
                build_logger.error(f"[{task_id}] Graph build failed: {str(e)}")
                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)
                task_manager.fail_task(task_id, str(e))
        
        # Start background thread
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
        
        return SuccessResponse(success=True, data={
            "project_id": project_id,
            "task_id": task_id,
            "message": "Graph build task started"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Graph build error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Task Query APIs ==============

@graph_router.get('/task/{task_id}', response_model=SuccessResponse)
async def get_task(task_id: str):
    """
    Query task status
    """
    task = TaskManager().get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    return SuccessResponse(success=True, data=task.to_dict())


# ============== Graph Data APIs ==============

@graph_router.get('/data/{graph_id}', response_model=SuccessResponse)
async def get_graph_data(request: Request, graph_id: str):
    """
    Get graph data (nodes and edges)
    """
    try:
        storage = request.app.state.neo4j_storage
        if not storage:
            raise HTTPException(status_code=503, detail="Neo4j storage is not initialized")

        builder = GraphBuilderService(storage=storage)
        graph_data = builder.get_graph_data(graph_id)

        return SuccessResponse(success=True, data=graph_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get graph data error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


