# ===================================================================
# RustyMiroSquid — Multi-stage Dockerfile
# UV (Astral) + Bun (Oven) + Python 3.13 (PYTHON_GIL=0)
# ===================================================================
# Fallback: Python 3.13 avec PYTHON_GIL=0 (No-GIL expérimental)
# Quand Python 3.15 stable → basculer sur python:3.15-slim
# ===================================================================

# ===== Stage 1: Backend dependencies =====
FROM python:3.13-slim AS backend-deps

# Copier UV depuis l'image officielle
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app/backend

# Copier uniquement les fichiers de dépendances (cache Docker)
COPY backend/pyproject.toml backend/uv.lock ./

# Installer les dépendances Python (sans le code source)
RUN uv sync --frozen --no-dev --no-install-project

# ===== Stage 2: Frontend build =====
FROM oven/bun:latest AS frontend-build

WORKDIR /app/frontend

# Copier les fichiers de dépendances frontend
COPY frontend/package.json frontend/bun.lockb ./

# Installer les dépendances frontend
RUN bun install --frozen-lockfile

# Copier le code source frontend et build
COPY frontend/ ./
RUN bun run build

# ===== Stage 3: Runtime =====
FROM python:3.13-slim AS runtime

# Copier UV pour le runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Installer les dépendances système minimales
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier le venv Python depuis le stage backend-deps
COPY --from=backend-deps /app/backend/.venv /app/backend/.venv
COPY --from=backend-deps /app/backend/pyproject.toml /app/backend/uv.lock /app/backend/

# Copier le build frontend depuis le stage frontend-build
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Copier le code source backend
COPY backend/ /app/backend/

# Activer le No-GIL expérimental (Python 3.13+)
ENV PYTHON_GIL=0
ENV PYTHONUNBUFFERED=1

EXPOSE 3000 5001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD curl -f http://localhost:5001/api/health || exit 1

# Lancer le backend Flask
CMD ["uv", "run", "--directory", "/app/backend", "python", "run.py"]