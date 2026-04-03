"""
Template API routes — serves preset simulation templates
"""

import os
import orjson
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from ..utils.logger import get_logger

router = APIRouter()
logger = get_logger('miroshark.api.templates')

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'preset_templates')

class TemplateSummary(BaseModel):
    id: str
    name: str
    category: str = ""
    description: str = ""
    icon: str = ""
    difficulty: str = "medium"
    estimated_agents: int = 0
    estimated_rounds: int = 0
    platforms: List[str] = []
    tags: List[str] = []

class TemplateListResponse(BaseModel):
    success: bool
    data: List[TemplateSummary]
    count: int

def _load_templates() -> List[Dict[str, Any]]:
    """Load all template JSON files from the templates directory."""
    templates = []
    if not os.path.isdir(TEMPLATES_DIR):
        return templates

    for filename in sorted(os.listdir(TEMPLATES_DIR)):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(TEMPLATES_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                template = orjson.loads(f.read())
            templates.append(template)
        except Exception as e:
            logger.warning(f"Failed to load template {filename}: {e}")

    return templates

@router.get("/list", response_model=TemplateListResponse)
async def list_templates():
    """
    List all available simulation templates.
    """
    try:
        templates = _load_templates()
        summaries = [
            TemplateSummary(
                id=t["id"],
                name=t["name"],
                category=t.get("category", ""),
                description=t.get("description", ""),
                icon=t.get("icon", ""),
                difficulty=t.get("difficulty", "medium"),
                estimated_agents=t.get("estimated_agents", 0),
                estimated_rounds=t.get("estimated_rounds", 0),
                platforms=t.get("platforms", []),
                tags=t.get("tags", []),
            )
            for t in templates
        ]

        return {
            "success": True,
            "data": summaries,
            "count": len(summaries)
        }
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{template_id}")
async def get_template(template_id: str = Path(..., description="The ID of the template to retrieve")):
    """
    Get a single template by ID.
    """
    try:
        # Security check: ensure path is within TEMPLATES_DIR
        filepath = os.path.realpath(os.path.join(TEMPLATES_DIR, f"{template_id}.json"))
        if not filepath.startswith(os.path.realpath(TEMPLATES_DIR)):
            raise HTTPException(status_code=400, detail="Invalid template ID")
            
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

        with open(filepath, 'r', encoding='utf-8') as f:
            template = orjson.loads(f.read())

        return {
            "success": True,
            "data": template
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
