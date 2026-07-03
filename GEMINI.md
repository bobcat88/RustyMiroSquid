---
type: reference
tags:
  - project/rustymirosquid
aliases:
- GEMINI
---
# 🐙 RustyMiroSquid — GEMINI.md (Root)
Up: [[RustyMiroSquid INDEX]]

#projects #rustymirosquid

## Projet
Mutation de MiroShark (swarm intelligence engine) en **RustyMiroSquid** — moteur de simulation multi-agents haute performance pour l'analyse prédictive d'investissements.

## Architecture
```
RustyMiroSquid/
├── backend/              # Python 3.15 (No-GIL) — FastAPI API + simulation engine
│   ├── app/              # API routes, services, models, config
│   │   ├── api/          # FastAPI REST endpoints
│   │   ├── models/       # Pydantic v2 schemas (agent personas, etc.)
│   │   ├── services/     # Core logic: simulation runner, report agent, polars analytics
│   │   └── storage/      # Neo4j storage layer
│   ├── wonderwall/       # Fork OASIS (CAMEL-AI) — simulation engine
│   │   ├── simulations/  # Platform simulations (Twitter, Reddit, Polymarket)
│   │   ├── social_agent/ # Agent models, belief state, action handler
│   │   └── social_platform/ # Platform-specific logic
│   └── scripts/          # Parallel simulation runner, E2E tests
├── frontend/             # Bun + Vue 3 + Vite 7 — Dashboard
│   └── src/              # Vue components, router, D3 visualizations
├── docs/                 # Documentation & images
├── Dockerfile            # Multi-stage: uv + bun + Python 3.15
└── docker-compose.yml    # Neo4j + Redis + app (+ vLLM optionnel)
```

## Stack Technique
| Layer | Tech |
|---|---|
| Runtime Backend | Python 3.15 Free-threaded (No-GIL) |
| Package Manager Backend | UV (Astral) |
| Runtime Frontend | Bun (Oven) |
| Web Framework | FastAPI 0.115+ |
| Data Processing | Polars (Rust-core), orjson |
| Validation | Pydantic v2 (Rust-core) |
| Graph DB | Neo4j 5.x (async driver) |
| Cache | Redis (semantic caching) |
| LLM | Qwen 3.5 35B via vLLM/Ollama |
| Simulation | CAMEL-AI + Wonderwall (fork OASIS) |
| Frontend | Vue 3.5 + Vite 7 + D3.js |

## Commandes
```bash
# Setup
bun run setup:all           # Backend (uv sync) + Frontend (bun install)

# Dev
bun run dev                 # Backend FastAPI + Frontend Vite (parallel)
cd backend && uv run python run.py   # Backend seul

# Tests
cd backend && uv run pytest tests/ -v
cd backend && uv run python scripts/test_e2e_api.py

# Docker
docker compose up --build

# GitNexus
gitnexus analyze            # Index le codebase dans le knowledge graph
```

## Agents (voir backend/GEMINI.md et frontend/GEMINI.md)
| Agent | Scope |
|---|---|
| Architect | Root: Dockerfile, docker-compose, CI/CD |
| Backend-Core | `backend/app/` |
| Simulation-Engine | `backend/wonderwall/` + `backend/scripts/` |
| Frontend | `frontend/` |
| LLM-Optim | Token compression, semantic cache |
| Market-Data | WebSocket connectors, sentiment velocity |

## Fichiers Projet
| Fichier | Rôle |
|---|---|
| README-RustyMiroSquid-v1.md | Documentation complète |
| Patchnote-RustyMiroSquid-v1.md | Historique des changements |
| Backlog-RustyMiroSquid-v1.md | Évolutions planifiées |
| Tracking-RustyMiroSquid-v1.md | Suivi erreurs & régressions |

## Contexte pour Agents IA
Pour reprendre ce projet à froid :
1. Lire ce fichier `GEMINI.md`
2. Lire `README.md` pour comprendre MiroShark (le projet source)
3. Lire `backend/GEMINI.md` pour le backend
4. Lire `frontend/GEMINI.md` pour le frontend
5. Exécuter `gitnexus analyze` pour indexer le codebase

<!-- MCP_REGISTRY_RULES_START -->
## MCP Registry Rules

- Treat `/home/_johan/Documents/Borg/AI-Agents/_shared/mcp-registry.md` as the canonical MCP source of truth.
- Link it into active project roots as `MCP-REGISTRY.md` when practical.
- Core MCPs: Memory (`@modelcontextprotocol/server-memory`), Context7 (`@upstash/context7-mcp`), and GitNexus (`gitnexus mcp`) for active development repos.
- Enable Playwright MCP (`playwright-mcp`) only for UI/web/visual verification work.
- Use per-agent config templates from `/home/_johan/Documents/Borg/AI-Agents/<agent>/` instead of ad-hoc snippets.
- Use fully qualified MCP tool names in durable docs/skills when referencing connector tools.
- Keep secrets out of MCP config files; use environment variables or the agent auth flow.
- For Google-agent workflows, prefer Antigravity CLI (`agy`, installed via `https://antigravity.google/cli/install.sh`) over legacy Gemini CLI.
<!-- MCP_REGISTRY_RULES_END -->

<!-- BORG_KNOWLEDGE_WORKFLOW_START -->
## Borg Knowledge Vault & AI Workflow

- Treat `/home/_johan/Documents/Borg` as the durable cross-project memory layer. Start with `300 Entities/Projects/Portfolio - Condensed Knowledge.md`, `400 Resources/Tech/AI Knowledge Map.md`, `000 OS / Meta/AI Collaboration Protocol.md`, and `300 Entities/People/Johan - Working Profile.md`.
- Keep repo-local docs authoritative for implementation details, but mirror durable project knowledge back into the vault when it affects other projects or future agents.
- Use local symlink entry points from the vault when navigating related repos, especially `300 Entities/Projects/RustyMiroSquid`, `300 Entities/Projects/BorgInvestor`, and `300 Entities/Projects/AI-Bonanza`.
- If Beads is present, run `bd prime`, use `bd ready/show/update/close`, and do not create markdown TODOs for trackable work.
- Use GSD for planning, specs, execution, review, and verification when work needs structure beyond Beads task tracking.
- If GitNexus is present, use it before code edits: impact analysis before symbol changes, change detection before commits, and `npx gitnexus analyze --embeddings` only when embeddings already exist.
- Use RTK for noisy command output when the repo requires it or when output volume would obscure the decision.
- Before finishing, run the smallest meaningful quality gate, update docs/vault notes if knowledge changed, commit intentionally, and push when the branch scope is clear.
<!-- BORG_KNOWLEDGE_WORKFLOW_END -->
