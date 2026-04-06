"""
Template API routes — serves preset simulation templates
"""

import os
import json
from fastapi import HTTPException
from typing import List, Dict, Any

from . import templates_router
from ..utils.logger import get_logger

logger = get_logger('rustymirosquid.api.templates')

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'preset_templates')


def _load_templates():
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
                template = json.load(f)
            templates.append(template)
        except Exception as e:
            logger.warning(f"Failed to load template {filename}: {e}")

    return templates


@templates_router.get('/list')
async def list_templates():
    """
    List all available simulation templates.
    """
    try:
        templates = _load_templates()

        summaries = []
        for t in templates:
            summaries.append({
                "id": t["id"],
                "name": t["name"],
                "category": t.get("category", ""),
                "description": t.get("description", ""),
                "icon": t.get("icon", ""),
                "difficulty": t.get("difficulty", "medium"),
                "estimated_agents": t.get("estimated_agents", 0),
                "estimated_rounds": t.get("estimated_rounds", 0),
                "platforms": t.get("platforms", []),
                "tags": t.get("tags", []),
            })

        return {
            "success": True,
            "data": summaries,
            "count": len(summaries)
        }

    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@templates_router.get('/{template_id}')
async def get_template(template_id: str):
    """
    Get a single template by ID.
    """
    try:
        # Security check: ensure template_id is just a filename
        safe_id = os.path.basename(template_id)
        if safe_id != template_id:
            raise HTTPException(status_code=400, detail="Invalid template ID")
            
        filepath = os.path.join(TEMPLATES_DIR, f"{template_id}.json")
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

        with open(filepath, 'r', encoding='utf-8') as f:
            template = json.load(f)

        return {
            "success": True,
            "data": template
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
