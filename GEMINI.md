# GEMINI.md — RustyMiroSquid

Ce fichier sert de point d'entrée pour l'agent IA (Claude/Gemini) pour comprendre l'état actuel et la structure du projet **RustyMiroSquid**.

## Documentation Courante (Standard PROUST v3.0)

| Type | Fichier | Description |
|---|---|---|
| **Principal** | [README-RustyMiroSquid-v1.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/README-RustyMiroSquid-v1.md) | Vision, Stack, Setup, Architecture |
| **Historique** | [Patchnote-RustyMiroSquid-v1.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/Patchnote-RustyMiroSquid-v1.md) | Tous les changements ordonnés (v1.0.0+) |
| **Backlog** | [Backlog-RustyMiroSquid-v1.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/Backlog-RustyMiroSquid-v1.md) | Évolutions planifiées et priorisées |
| **Suivi** | [Tracking-RustyMiroSquid-v1.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/Tracking-RustyMiroSquid-v1.md) | Erreurs et régressions en cours |

---

## Architecture & Stack

- **Frontend** : Vue 3.5 + Vite 7 + D3.js + Vue Router (Gestion via **Bun**)
- **Backend** : Flask 3 (Migration FastAPI prévue) + Python 3.12 + **uv**
- **Graph DB** : Neo4j 5.15
- **LLM** : Ollama (Modèle : `qwen3:32b`)
- **Agents AI** : camel-ai v0.2.78 (Version verrouillée)

---

## Contraintes Techniques Critiques (NOYAU DUR)

- **Python Version** : Utiliser impérativement **Python 3.12** ou **3.14** (`uv python pin 3.14`). La compatibilité 3.14 a été validée avec `camel-ai>=0.2.90`.
- **Package Managers** : **Bun** pour Node/Frontend, **uv** pour Python/Backend.
- **Docker Usage** : Utiliser Docker uniquement pour l'infrastructure (Neo4j, Ollama). Le code applicatif (`rustymirosquid`) doit tourner en **local**.
- **GitNexus** : Analyse d'impact obligatoire (`gitnexus_impact`) avant toute modification de symbole. Détection de changements (`gitnexus_detect_changes`) avant commit.

---

## Commandes de Référence

```bash
# Setup infrastructure
docker compose up neo4j ollama -d

# Lancement Développement (Backend + Frontend)
bun run dev

# Tests Backend
cd backend && uv run pytest
```

---

## Instructions de Relancement
Pour reprendre ce projet "à froid", l'agent doit lire les fichiers ci-dessus et se référer au [AGENTS.md](file:///C:/Users/Johan/AppData/Roaming/Antigravity/User/agents/AGENT_TEAM_BLUEPRINT.md) pour les règles de collaboration.

**Dernière version majeure :** `v1`
**Branche courante :** `feat/pro-init-v1`

