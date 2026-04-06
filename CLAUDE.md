# CLAUDE.md — RustyMiroSquid (MiroShark)
*Contexte d'initialisation — Lire en premier avant toute action.*
*Version : 1.0 — 2026-04-05 | Auteur : Johan PROUST*

---

## Identité du projet

**RustyMiroSquid** — Universal Swarm Intelligence Engine.
Upload d'un document (presse, rapport, politique) → génère des centaines d'agents IA avec personnalités uniques → simule la réaction sur les réseaux sociaux (posts, arguments, opinion shifts) heure par heure.

Fork de [`github.com/aaronjmars/MiroShark`](https://github.com/aaronjmars/MiroShark) — étendu par Antigravity avec un framework de trading.

**Propriétaire :** Johan PROUST
**Dossier :** `C:\WeAreTheBorgsWorkers\RustyMiroSquid\RustyMiroSquid`

---

## Architecture

```
RustyMiroSquid/
├── frontend/          ← Vue 3 + Vite + D3.js + Vue Router (npm — voir ⚠️)
├── backend/           ← Flask + Python + uv (pyproject.toml)
│   └── app/
│       ├── api/           ← graph, simulation, report, templates
│       ├── models/        ← project, task
│       ├── services/      ← logique métier (voir liste complète)
│       ├── storage/       ← embedding_service, graph_storage, neo4j_schema
│       └── preset_templates/ ← JSON templates (campus, crypto, political...)
├── docker-compose.yml ← Neo4j + Ollama + miroshark (image ghcr.io)
├── package.json       ← root scripts (concurrently backend+frontend)
└── .env.example
```

**Stack :**
- Frontend : Vue 3.5 + Vite 7 + D3.js + Axios + Vue Router
- Backend : Flask 3 (should FastAPI) + Python 3.11+ + uv + pydantic v2
- Graph DB : Neo4j 5.15
- LLM : Ollama (local) ou OpenAI-compatible API
- AI agents : camel-ai 0.2.78 + sentence-transformers + torch
- Embeddings : nomic-embed-text (via Ollama)

---

## Historique Git — Ce qu'Antigravity a fait

```
0be442c  feat: trading agent framework — fiscal FR, SMC strategies, market-media bridge
9cf7fbd  feat: OVTLYR trading policy — multi-strategy agent simulations
980b317  chore: PROUST standard documentation v1
--- (commits upstream MiroShark en dessous)
```

**Antigravity a ajouté :**
- `fiscal_service.py` — intégration fiscale française
- `trading_persona_factory.py` — création d'agents trading
- `trigger_service.py` — déclenchement d'événements de marché
- `web_enrichment.py` — enrichissement web des données
- `graph_memory_updater.py` — mise à jour mémoire graphe
- Documentation PROUST standard (README, CLAUDE.md initial, etc.)

Ce sont des extensions **non présentes dans le MiroShark upstream** — à ne pas écraser si on resync avec l'upstream.

---

## ⚠️ Conflits et Points de Vigilance

### 1. Python 3.14 vs pyproject.toml (CRITIQUE)
Des fichiers `.pyc` compilés avec `cpython-314` sont présents dans `backend/app/services/__pycache__/` — Antigravity a lancé le projet avec **Python 3.14 localement**.

**Problème :** `pyproject.toml` déclare `requires-python = ">=3.11"` mais `torch`, `camel-ai 0.2.78`, `sentence-transformers` n'ont pas de wheels stables pour Python 3.14.

**Recommandation :** Utiliser **Python 3.12** (sweet spot — supporté par tout l'écosystème). Vérifier avec `uv python list` quelle version est active.

```bash
uv python install 3.12
uv python pin 3.12
uv sync
```

### 2. npm vs bun (frontend + root)
Le `package.json` root et `frontend/package.json` utilisent encore **npm**. Si Antigravity a déjà fait un `npm install`, il existe un `package-lock.json`.

**Migration bun :**
```bash
# Supprimer les lock files npm avant de switcher
rm package-lock.json frontend/package-lock.json
bun install
cd frontend && bun install
```
Puis adapter les scripts dans `package.json` (voir tableau npm→bun dans AI-Bonanza README).

### 3. Docker image vs code local (IMPORTANT)
`docker-compose.yml` utilise l'image upstream : `ghcr.io/aaronjmars/miroshark:latest`
Cette image **ne contient pas** les additions Antigravity (trading, fiscal, OVTLYR).

Pour développement local : **ne pas utiliser docker pour miroshark**, uniquement pour Neo4j + Ollama :
```bash
# Lancer seulement Neo4j + Ollama via docker
docker compose up neo4j ollama -d
# Lancer miroshark en local
bun run dev  # ou npm run dev
```

### 4. LLM Model — qwen2.5:32b → qwen3:32b
`docker-compose.yml` configure `LLM_MODEL_NAME=qwen2.5:32b`.
Qwen3 est supérieur à taille égale. Migration simple :
```yaml
# docker-compose.yml
- LLM_MODEL_NAME=qwen3:32b
```
Puis : `docker exec miroshark-ollama ollama pull qwen3:32b`

### 5. camel-ai version lock
`camel-ai==0.2.78` est pincé. Le framework trading d'Antigravity l'utilise — ne pas upgrader sans tester.

---

## Commandes de démarrage

```bash
# Setup complet (première fois)
uv python pin 3.12        # épingler Python 3.12
cd backend && uv sync     # installer dépendances Python
cd .. && bun install      # installer dépendances Node root
cd frontend && bun install

# Développement
docker compose up neo4j ollama -d   # services infra
bun run dev                          # backend + frontend en parallèle

# Backend seul
cd backend && uv run python run.py

# Frontend seul
cd frontend && bun run dev
```

---

## Outillage — Règles globales Johan

- **Python :** `uv` > `pip` (déjà en place ✅)
- **Node :** `bun` > `npm` (migration à faire)
- **Linting :** Biome (`bun add -D @biomejs/biome`)

---

## Fichiers clés à connaître

| Fichier | Rôle |
|---------|------|
| `backend/app/config.py` | Config centrale (LLM URL, Neo4j, clés) |
| `backend/run.py` | Entrypoint Flask |
| `backend/pyproject.toml` | Dépendances Python + uv |
| `frontend/src/main.js` | Entrypoint Vue |
| `frontend/src/router/index.js` | Routes Vue |
| `docker-compose.yml` | Infrastructure (Neo4j + Ollama) |
| `.env.example` | Variables d'environnement à copier en `.env` |

---

## Roadmap / Chantiers identifiés

| Priorité | Tâche | Impact |
|----------|-------|--------|
| P0 | Vérifier compatibilité Python 3.12 (torch/camel-ai) | Stabilité |
| P1 | Migrer npm → bun (frontend + root) | Performance |
| P1 | Docker : séparer miroshark (local) de Neo4j+Ollama | Dev workflow |
| P2 | LLM model : qwen2.5:32b → qwen3:32b | Qualité outputs |
| P3 | Frontend : évaluer shadcn-vue + Tailwind v4 | UI upgrade |
| P3 | Évaluer Polars pour remplacer pandas dans pipeline | Performance data |

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **RustyMiroSquid** (2271 symbols, 10378 relationships, 189 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/RustyMiroSquid/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/RustyMiroSquid/context` | Codebase overview, check index freshness |
| `gitnexus://repo/RustyMiroSquid/clusters` | All functional areas |
| `gitnexus://repo/RustyMiroSquid/processes` | All execution flows |
| `gitnexus://repo/RustyMiroSquid/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
