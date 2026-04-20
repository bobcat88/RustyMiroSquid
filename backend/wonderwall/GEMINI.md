# 🐙 Wonderwall (Simulation Engine) — GEMINI.md

## Scope
Fork d'OASIS (CAMEL-AI) — moteur de simulation multi-plateforme (Twitter, Reddit, Polymarket). Gère les agents sociaux, les états de croyance, et l'orchestration des rounds.

## Structure
```
wonderwall/
├── __init__.py           # Exports principaux (ActionType, LLMAction, etc.)
├── clock/                # Gestion du temps de simulation
├── environment/          # Environnement de simulation (step loop)
├── simulations/
│   ├── base.py           # Classe de base SimulationConfig
│   ├── social_media/     # Simulations Twitter + Reddit
│   └── polymarket/       # Simulation Polymarket (AMM engine)
├── social_agent/
│   ├── agent.py          # SocialAgent — agent principal
│   ├── agent_action.py   # Actions disponibles (CREATE_POST, etc.)
│   ├── agent_environment.py  # Environnement par agent
│   ├── agent_graph.py    # Graphe de relations entre agents
│   ├── agents_generator.py # Générateur d'agents depuis config
│   ├── belief_state.py   # [MODIFIER] État de croyance (thread-safety)
│   └── round_analyzer.py # Analyseur de round
├── social_platform/      # Logique spécifique par plateforme
└── testing/              # Tests
```

## Dépendances Hard
- `camel-ai==0.2.78` — ModelFactory, ModelPlatformType
- `numpy` — calculs vectoriels
- `pandas` — ⚠️ Encore utilisé en interne par CAMEL-AI (NE PAS SUPPRIMER)
- `torch` + `sentence-transformers` — embeddings locaux
- `igraph` — graphe social
- `scikit-learn` — recommandation système

## Priorités de Modification

### Thread-Safety (P1 — No-GIL)
- `social_agent/belief_state.py` — Ajouter `threading.RLock` sur `BeliefTracker`
- `social_agent/round_analyzer.py` — Protéger les accès concurrents

### Données (P1)
- Les logs sont en JSONL → compatible Polars
- Les données internes Wonderwall utilisent `pandas` → **NE PAS MIGRER** (cassure CAMEL-AI)
- Seuls les modules RustyMiroSquid (dans `app/services/`) utilisent Polars

## Attention
> L'internals de Wonderwall (fork OASIS) est complexe et couplé à CAMEL-AI. Les modifications doivent être chirurgicales. Ne pas refactoriser l'architecture interne de Wonderwall — seulement ajouter les guards de thread-safety et les hooks nécessaires.

<!-- BORG_KNOWLEDGE_WORKFLOW_START -->
## Borg Knowledge Vault & AI Workflow

- Shared memory lives in `/home/_johan/Documents/Borg`. Start with `300 Entities/Projects/Portfolio - Condensed Knowledge.md`, `400 Resources/Tech/AI Knowledge Map.md`, `000 OS / Meta/AI Collaboration Protocol.md`, and `300 Entities/People/Johan - Working Profile.md`.
- For this Wonderwall scope, also read root `GEMINI.md`, `AGENTS.md`, `backend/GEMINI.md`, and the vault symlink `300 Entities/Projects/RustyMiroSquid`.
- Keep Wonderwall changes surgical. Mirror durable simulation/agent architecture decisions back into the vault instead of leaving them only in chat.
- Use Beads/kspec if present, GitNexus before symbol edits, RTK for noisy command output, and run focused simulation/thread-safety tests before finishing.
<!-- BORG_KNOWLEDGE_WORKFLOW_END -->
