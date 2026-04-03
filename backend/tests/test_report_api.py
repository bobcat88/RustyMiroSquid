import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.api.report import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_get_report_not_found():
    response = client.get("/report/not-found-id")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "not found" in data["error"]

def test_generate_report_missing_sim_id():
    response = client.post("/report/generate", json={"force_regenerate": True})
    # FastAPI handles validation before entering the function!
    # Because simulation_id is required in the GenerateReportRequest schema.
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_generate_report_not_found(monkeypatch):
    class MockSimulationManager:
        def get_simulation(self, sim_id):
            return None
    
    monkeypatch.setattr("app.api.report.SimulationManager", MockSimulationManager)
    response = client.post("/report/generate", json={"simulation_id": "missing", "force_regenerate": True})
    assert response.status_code == 404
    assert response.json()["success"] is False

def test_check_report_status_not_found():
    response = client.get("/report/check/sim_123")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["has_report"] is False

def test_tool_search_missing_graph_id():
    response = client.post("/report/tools/search", json={"query": "test"})
    assert response.status_code == 422
