# RustyMiroSquid Backend — Quick Start Guide

This guide explains how to set up and run the FastAPI-based backend.

## 🚀 Environment Setup

The backend uses **uv** for dependency management and Python 3.14.

1. **Install uv** (if not already installed):
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Synchronize dependencies**:
   ```bash
   cd backend
   uv sync
   ```

3. **Pin Python version**:
   ```bash
   uv python pin 3.14
   ```

## 🏃 Running the Server

Launch the FastAPI server using the `run.py` wrapper (which configures UTF-8 for Windows).

```bash
uv run run.py
```

- **Default Address**: `http://localhost:5001`
- **Interactive Docs**: `http://localhost:5001/docs` (Swagger UI)
- **Health Check**: `http://localhost:5001/health`

## 🧪 Running Tests

```bash
cd backend
uv run pytest
```

## 🛠️ Architecture Reference

- **API Routes**: [app/api/](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/backend/app/api/)
- **Core Logic**: [app/services/](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/backend/app/services/)
- **LLM Prompts**: See [docs/LLM_CALL_REFERENCE.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/backend/docs/LLM_CALL_REFERENCE.md)
