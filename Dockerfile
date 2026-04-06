FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

# Copy uv from the official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency descriptor files first
COPY package.json bun.lockb ./
COPY frontend/package.json frontend/bun.lockb ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install dependencies
RUN bun install \
    && cd frontend && bun install \
    && cd ../backend && uv sync --frozen

# Copy project source code
COPY . .

EXPOSE 3000 5001

# Start both frontend and backend simultaneously (development mode)
CMD ["bun", "run", "dev"]