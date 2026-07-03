---
type: reference
tags:
  - project/rustymirosquid
  - domain/dev/backend
aliases:
- GEMINI
---
# 🐙 RustyMiroSquid Backend — GEMINI.md
Up: [[RustyMiroSquid INDEX]]

#projects #rustymirosquid #backend

## Scope
Backend Python du moteur de simulation multi-agents. Inclut l'API FastAPI, les services (simulation, rapports, graphes), et le moteur Wonderwall (fork OASIS/CAMEL-AI).

## Structure
```
backend/
├── app/
│   ├── api/                        # Routes REST
│   │   ├── simulation.py           # (110KB) Routes de simulation
│   │   ├── graph.py                # Routes de graphe Neo4j
│   │   ├── report.py               # Routes de génération de rapports
│   │   └── templates.py            # Templates de preset
│   ├── config.py                   # Configuration (.env loader)
│   ├── models/
│   │   └── agent_personas.py       # [NEW] Schémas Pydantic v2
│   ├── services/
│   │   ├── simulation_runner.py    # (77KB) Orchestrateur de simulation
│   │   ├── report_agent.py         # (135KB) Agent ReACT pour rapports
│   │   ├── graph_tools.py          # (77KB) Outils de graphe Neo4j
│   │   ├── simulation_config_generator.py  # Générateur de config
│   │   ├── oasis_profile_generator.py      # Générateur de personas
│   │   ├── polars_analytics.py     # [NEW] Analyse Polars des résultats
│   │   ├── prompt_compressor.py    # [NEW] Compression LLMLingua
│   │   ├── semantic_cache.py       # [NEW] Cache sémantique Redis
│   │   ├── market_connector.py     # [NEW] WebSocket market data
│   │   └── sentiment_velocity.py   # [NEW] Vélocité de sentiment
│   ├── storage/                    # Couche de persistance Neo4j
│   └── utils/                      # Utilitaires
├── wonderwall/                     # Fork OASIS (voir wonderwall/GEMINI.md)
├── scripts/
│   ├── run_parallel_simulation.py  # (110KB) Script principal de simulation
│   ├── action_logger.py            # Logger d'actions JSONL
│   ├── belief_integration.py       # Intégration des croyances
│   ├── cross_platform_digest.py    # Contexte cross-plateforme
│   ├── market_media_bridge.py      # Bridge marché↔média
│   ├── round_memory.py             # Mémoire par round (sliding window)
│   └── test_*.py                   # Tests E2E
├── pyproject.toml                  # Dépendances UV
└── run.py                          # Entrypoint FastAPI
```

## Stack
- **Runtime :** Python 3.15 Free-threaded (No-GIL), fallback Python 3.13
- **Package Manager :** UV (Astral)
- **Web Framework :** FastAPI 0.115+
- **LLM :** OpenAI-compatible API (Ollama, OpenRouter, Claude Code)
- **Simulation :** CAMEL-AI 0.2.78 + Wonderwall
- **Data :** Polars (analytics), orjson (serialization), Pydantic v2 (validation)
- **Graph :** Neo4j 5.x (driver async v5)
- **Cache :** Redis (semantic caching)
- **Tokens :** LLMLingua (prompt compression)

## Conventions
- Coder en anglais, commenter en français
- `orjson` pour toute sérialisation JSON (pas `json` stdlib)
- `Polars` pour tout traitement de données tabulaires (pas `pandas`)
- Schémas Pydantic v2 pour toute validation de données
- `threading.Lock` sur les structures partagées (No-GIL ready)
- Tests unitaires avec `pytest` (coverage minimum 70%)
- TODO datés : `# TODO [YYYY-MM-DD] : <description>`

## Commandes
```bash
uv sync                          # Installer les dépendances
uv run python run.py             # Lancer le serveur FastAPI
uv run pytest tests/ -v          # Tests unitaires
uv run python scripts/test_e2e_api.py  # Test E2E
```

## Migration orjson — Fichiers à modifier
```
app/services/simulation_runner.py
app/services/report_agent.py
app/services/graph_tools.py
app/services/simulation_config_generator.py
app/services/oasis_profile_generator.py
app/api/simulation.py
scripts/run_parallel_simulation.py
scripts/action_logger.py
```

## Règle : `json.loads()` → `orjson.loads()`, `json.dumps()` → `orjson.dumps().decode()`

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

- Shared memory lives in `/home/_johan/Documents/Borg`. Start with `300 Entities/Projects/Portfolio - Condensed Knowledge.md`, `400 Resources/Tech/AI Knowledge Map.md`, `000 OS / Meta/AI Collaboration Protocol.md`, and `300 Entities/People/Johan - Working Profile.md`.
- For this backend scope, also read root `GEMINI.md`, `AGENTS.md`, `backend/wonderwall/GEMINI.md` when touching simulation internals, and the vault symlink `300 Entities/Projects/RustyMiroSquid`.
- Keep backend implementation details in repo docs, but mirror durable AI/simulation architecture decisions back into the vault.
- Use Beads/GSD if present, GitNexus before symbol edits, RTK for noisy command output, and run the smallest meaningful backend quality gate before finishing.
<!-- BORG_KNOWLEDGE_WORKFLOW_END -->
