"""
RustyMiroSquid Backend - FastAPI application factory
"""

import os
import warnings

# Suppress multiprocessing resource_tracker warnings (from third-party libraries like transformers)
# Must be set before all other imports
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .config import Config
from .utils.logger import setup_logger, get_logger

def create_app(config_class=Config):
    """FastAPI application factory function"""
    app = FastAPI(
        title="RustyMiroSquid API",
        description="Simple and Universal Swarm Intelligence Engine",
        version="0.1.0"
    )
    
    # Set up logging
    logger = setup_logger('rustymirosquid')
    logger.info("=" * 50)
    logger.info("RustyMiroSquid Backend (FastAPI) starting...")
    logger.info("=" * 50)
    
    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Initialize Neo4jStorage singleton ---
    from .storage import Neo4jStorage
    try:
        neo4j_storage = Neo4jStorage()
        app.state.neo4j_storage = neo4j_storage
        logger.info("Neo4jStorage initialized (connected to %s)", Config.NEO4J_URI)
    except Exception as e:
        logger.error("Neo4jStorage initialization failed: %s", e)
        app.state.neo4j_storage = None

    # Register simulation process cleanup
    from .services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()
    logger.info("Simulation process cleanup function registered")
    
    # Register routers
    from .api import graph_router, simulation_router, report_router, templates_router
    app.include_router(graph_router, prefix='/api/graph', tags=['Graph'])
    app.include_router(simulation_router, prefix='/api/simulation', tags=['Simulation'])
    app.include_router(report_router, prefix='/api/report', tags=['Report'])
    app.include_router(templates_router, prefix='/api/templates', tags=['Templates'])
    
    # Health check
    @app.get('/health')
    async def health():
        return {'status': 'ok', 'service': 'RustyMiroSquid Backend'}
    
    logger.info("RustyMiroSquid Backend startup complete")
    return app

