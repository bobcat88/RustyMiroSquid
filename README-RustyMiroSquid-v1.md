# 🐙 RustyMiroSquid — README

## Contexte & Finalité
Mutation de **MiroShark** (moteur de simulation d'intelligence collective LLM-powered) en **RustyMiroSquid** — moteur haute performance dédié à l'analyse prédictive d'investissements. Le projet combine :
- Un moteur de simulation multi-agents (CAMEL-AI/Wonderwall)
- Un data-path Rust-native (Polars, orjson, Pydantic v2)
- Le multi-threading réel Python 3.15 (No-GIL)
- L'optimisation de tokens LLM (LLMLingua, semantic caching)
- L'intégration de données de marché en temps réel

## Stack Technique
| Layer | Tech |
|---|---|
| Backend Runtime | Python 3.13+ (target: 3.15 Free-threaded) |
| Package Manager | UV (Astral) + Bun (Oven) |
| Web Framework | FastAPI 0.115+ |
| Data Processing | Polars, orjson, Pydantic v2 |
| Graph DB | Neo4j 5.x |
| Cache | Redis |
| LLM | Qwen 3.5 35B via vLLM/Ollama |
| Simulation | CAMEL-AI + Wonderwall |
| Frontend | Vue 3.5 + Vite 7.2 + D3.js |

## Getting Started
```bash
# Prerequisites: Python 3.13+, Bun, UV, Neo4j ou Docker
bun run setup:all
bun run dev
# Ouvrir http://localhost:3000

# GitNexus (indexation du codebase)
gitnexus analyze
```

## Variables d'environnement
→ Voir `.env.example`

## Structure du projet
→ Voir `GEMINI.md` (root)

## Modèle de données
- **Neo4j** : graphe de connaissances (entités, relations, embeddings)
- **SQLite** : logs de simulation par plateforme (Twitter, Reddit, Polymarket)
- **Redis** : cache sémantique des raisonnements agents
- **JSONL** : logs d'actions par round

## Context for Claude
Pour reprendre ce projet : lire `GEMINI.md` → `backend/GEMINI.md` → `frontend/GEMINI.md` → `AGENTS.md`
