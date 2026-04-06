from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SuccessResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None

class ProjectFile(BaseModel):
    filename: str
    size: int
    url: Optional[str] = None

class ProjectOntology(BaseModel):
    entity_types: List[str]
    edge_types: List[Dict[str, Any]]

class ProjectResponse(BaseModel):
    project_id: str
    project_name: str
    status: str
    ontology: Optional[ProjectOntology] = None
    analysis_summary: Optional[str] = None
    files: List[ProjectFile] = []
    total_text_length: int = 0

class FetchURLRequest(BaseModel):
    url: str

class FetchURLResponse(BaseModel):
    title: str
    text: str
    url: str
    char_count: int

class OntologyGenerateRequest(BaseModel):
    simulation_requirement: str
    project_name: str = "Unnamed Project"
    additional_context: Optional[str] = None
    url_docs: Optional[List[Dict[str, Any]]] = None

class BuildGraphRequest(BaseModel):
    project_id: str
    graph_name: Optional[str] = None
    chunk_size: Optional[int] = 500
    chunk_overlap: Optional[int] = 50
    force: bool = False

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None
    progress: int = 0
    result: Optional[Any] = None
    error: Optional[str] = None

class CreateSimulationRequest(BaseModel):
    project_id: str
    graph_id: Optional[str] = None
    enable_twitter: bool = True
    enable_reddit: bool = True
    enable_polymarket: bool = False

class SimulationState(BaseModel):
    simulation_id: str
    project_id: str
    graph_id: str
    status: str
    enable_twitter: bool
    enable_reddit: bool
    enable_polymarket: bool
    entities_count: int = 0
    created_at: str
    updated_at: Optional[str] = None
