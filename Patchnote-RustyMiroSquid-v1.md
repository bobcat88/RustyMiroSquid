# 🐙 RustyMiroSquid — Patch Notes

## v1.0.0 — 2026-04-03

### TECH
- Migration du projet MiroShark vers RustyMiroSquid
- `pyproject.toml` : ajout orjson, polars, redis, llmlingua, websockets, yfinance
- `package.json` (root) : migration npm → Bun
- Création des GEMINI.md (root, backend, wonderwall, frontend)
- Création de `AGENTS.md` avec 6 prompts d'agents spécialisés
- Installation Python 3.13 (fallback No-GIL) + UV sync réussi (166 packages)
- Installation Bun pour root + frontend (bun.lockb générés)

### FUNCTION
- Structure de projet prête pour le développement multi-agents
- Blueprint technique détaillé avec 5 phases de développement

## v1.1.0 — 2026-04-03

### TECH
- Dockerfile multi-stage 3 étapes (UV backend → Bun frontend → slim runtime)
- `PYTHON_GIL=0` activé dans le runtime container
- `docker-compose.yml` : ajout Redis, healthchecks, 3 GPU variants (NVIDIA/AMD/Mac)
- Migration orjson : 32 fichiers migrés automatiquement (json→orjson)
- Nouveau module `polars_analytics.py` (5 méthodes d'analyse Rust-native)
- Nouveau modèle `agent_personas.py` (Pydantic v2 : BeliefState, AgentPersona, SimulationConfig)

### FUNCTION
- `README.md` réécrit pour GitHub (comparaison MiroShark vs RustyMiroSquid)
- Logo RustyMiroSquid généré (`docs/images/rustymirosquid.png`)

## v1.2.0 — 2026-04-03

### TECH
- **No-GIL thread-safety** : `threading.RLock` sur `BeliefTracker`, `threading.Lock` sur `RoundMemory` et `CrossPlatformLog`
- Nouveau module `prompt_compressor.py` : middleware LLMLingua avec protection des données financières (regex montants/dates/métriques)
- Nouveau module `semantic_cache.py` : cache Redis async (SHA-256, TTL configurable, invalidation par pattern, métriques hit/miss)

### FUNCTION
- Compression de prompts > 2000 tokens avant envoi LLM (économie ~40% tokens)
- Cache sémantique des raisonnements types (namespace `squid:llm_cache`, TTL default 1h)

## v1.3.0 — 2026-04-03

### TECH
- Nouveau module `market_connector.py` : WebSocket Binance (auto-reconnect, stream combiné) + yfinance batch (throttle 30s)
- Nouveau module `sentiment_velocity.py` : calcul dS/dt par agent × topic (Polars LazyFrame), alertes de shift rapide

### FUNCTION
- Données de marché réelles injectées dans les agents (crypto : BTC/ETH/SOL + equities : SPY/AAPL/MSFT/NVDA)
- Signaux de trading par vélocité de sentiment (3 niveaux : moderate/strong/extreme)
- Thread-safe pour les deux modules (Lock)

## v1.4.0 — 2026-04-03

### TECH
- Audit structuré de la *Definition of Done* complété
- Création du répertoire `tests/` (suite manquante)
- Implémentation des 4 test suites : orjson, polars, personas, thread-safety
- Correction typographique critique dans `action_logger.py` (`ororjson`)
- Résolution f-string invalid placeholder dans `test_market_generation.py`

### FUNCTION
- Coverage et validation qualité assurés sur les composants core du framework
- Finition post-migration avec alignement sur les standards PROUST

## v1.5.0 — 2026-04-04

### TECH
- Purge complète des dépendances `flask` et `flask-cors`
- Refactoring `app/api/report.py` en 100% FastAPI (`APIRouter`, `BackgroundTasks`)
- Remplacement de `requests` par `httpx` dans `app/utils/url_fetcher.py` pour des meilleures performances
- Correction d'un bug HTTP 2x requests lors du téléchargement de chunks HTML avec requests/httpx
- Ajout de la bibliothèque `pytest-httpx` (`uv add`)

### FUNCTION
- Test coverage de l'application poussé à 100% sur le composant critique URL fetcher
- Finalisation de la phase 9 FastAPI Purge avec un code asynchrone unifié et allégé

## v1.6.0 — 2026-04-04

### TECH
- Limitation CPU stricte à 80% via `docker-compose.yml` (`cpus: 0.8`)
- Centralisation de `MAX_WORKERS` et `POLARS_MAX_THREADS` dans `app/config.py`
- Mise à jour de `run_parallel_simulation.py`, `graph_builder.py` et `simulation_config_generator.py` pour respecter les quotas de ressources
- Optimisation des threads Polars (no-GIL friendly) pour éviter la contention CPU pendant l'ingestion massive de données

### FUNCTION
- Stabilité garantie du système sous charge intensive
- Respect des contraintes de ressources partagées (PROUST 80/20 rule)

## v1.7.0 — 2026-04-04

### TECH
- Audit global de conformité *Definition of Done* (DoD) terminé.
- Synchronisation complète de la documentation architecture (`GEMINI.md`, `README.md`) avec FastAPI.
- Mise en conformité des TODO (datés) dans les fichiers modifiés.
- 18 tests unitaires validés (100% success rate).

### FUNCTION
- Nettoyage final du projet MiroShark vers RustyMiroSquid.
- Roadmap mise à jour (Backlog v2) incluant l'observabilité et les futures optimisations LLM (TurboQuant).
