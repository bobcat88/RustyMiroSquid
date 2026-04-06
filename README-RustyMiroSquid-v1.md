# README-RustyMiroSquid-v1.md

## Contexte & Finalité
**RustyMiroSquid** (basé sur RustyMiroSquid) est un moteur d'intelligence en essaim universel. Il permet de simuler des réactions sociales à partir de n'importe quel document source (communiqués de presse, rapports financiers, etc.) en générant des centaines d'agents IA aux personnalités uniques.

Le projet a été forké pour intégrer des optimisations de performance (Neo4j, No-GIL Python) et une infrastructure compatible avec le standard **PROUST**.

## Charte Graphique
- **Titres** : Barlow Condensed SemiBold
- **Corps** : Raleway
- **Couleurs** : #ED1C24 (rouge), #575756 (gris foncé)

## Stack Technique
- **Backend** : Python 3.11+ (asyncio, ThreadPoolExecutor)
- **Database** : Neo4j 5.15+
- **Frontend** : Node.js 18+, React
- **Infra** : Docker & Docker Compose
- **LLM Support** : OpenAI-compatible, Ollama, Claude Code CLI

## Getting Started
1. Configurer `.env` à partir de `.env.example`.
2. Lancer Neo4j (Docker ou local).
3. Exécuter `npm run setup:all`.
4. Lancer le développement avec `npm run dev`.
5. **Analyse GitNexus** : `gitnexus analyze` obligatoire après modification structurelle.

## Variables d'Environnement
Voir le fichier `.env.example` pour la liste complète (LLM_API_KEY, NEO4J_URI, etc.).

## Structure du Projet
- `/backend` : Moteur de simulation (Python, TriggerService, TradingPersonaFactory).
- `/frontend` : Interface utilisateur (React, Dashboard expansion).
- `/docs` : Documentation technique, analyses stratégiques et images.

## Modèle de Données Projet
- **Graph** : Entités et relations extraites via LLM.
- **Agents** : Personas avec états de croyance (stance, confidence, trust) + Archetypes Trading (Whale, Alpha, Sniper, Reactor).
- **Triggers** : Snapshot de microstructure (Market Color, SMC Signals, RSS News).

## Context for Claude
Ce projet utilise le standard **PROUST v3.0**. Pour reprendre le contexte :
1. Consulter `C:\Users\Johan\AppData\Roaming\Antigravity\User\agents\sessions\SESSION_CONTEXT.md`.
2. Lire les fichiers `README-v1`, `Patchnote-v1`, `Backlog-v1` et `Tracking-v1`.
3. Lien vers [AGENTS.md](file:///C:/Users/Johan/AppData/Roaming/Antigravity/User/agents/AGENT_TEAM_BLUEPRINT.md).

## Patch Notes
- **v1.6.0** (2026-04-05) : Intégration fiscale française (PFU 31.4%) et audit initial.
Voir [Patchnote-RustyMiroSquid-v1.md](file:///c:/WeAreTheBorgsWorkers/RustyMiroSquid/RustyMiroSquid/Patchnote-RustyMiroSquid-v1.md).
