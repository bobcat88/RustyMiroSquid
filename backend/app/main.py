import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
from app.api import simulation, graph, report, templates, market
import uvicorn

class Settings(BaseSettings):
    PROJECT_NAME: str = "RustyMiroSquid"
    API_V1_STR: str = "/api"
    DEBUG: bool = True

    class Config:
        env_file = ".env"

settings = Settings()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        debug=settings.DEBUG
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include Routers
    app.include_router(simulation.router, prefix=f"{settings.API_V1_STR}/simulation", tags=["simulation"])
    app.include_router(graph.router, prefix=f"{settings.API_V1_STR}/graph", tags=["graph"])
    app.include_router(report.router, prefix=f"{settings.API_V1_STR}/report", tags=["report"])
    app.include_router(templates.router, prefix=f"{settings.API_V1_STR}/templates", tags=["templates"])
    app.include_router(market.router, prefix=f"{settings.API_V1_STR}/market", tags=["market"])

    @app.get("/")
    def root():
        return {"message": "Welcome to RustyMiroSquid API", "status": "running"}

    return app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("FASTAPI_HOST", "0.0.0.0")
    port = int(os.environ.get("FASTAPI_PORT", 5001))
    uvicorn.run("app.main:app", host=host, port=port, reload=settings.DEBUG)
