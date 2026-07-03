---
type: reference
tags:
  - project/rustymirosquid
  - domain/dev/frontend
aliases:
- GEMINI
---
# 🐙 RustyMiroSquid Frontend — GEMINI.md
Up: [[RustyMiroSquid INDEX]]

#projects #rustymirosquid #frontend

## Scope
Dashboard Vue 3 pour la visualisation des simulations multi-agents. Affiche les activités Twitter/Reddit/Polymarket, les profils d'agents, et les rapports générés.

## Structure
```
frontend/
├── index.html            # Point d'entrée HTML
├── package.json          # Dépendances (Bun)
├── vite.config.js        # Configuration Vite 7
└── src/
    ├── main.js           # Entrypoint Vue
    ├── App.vue           # Composant racine
    └── (components)      # Composants Vue
```

## Stack
- **Runtime :** Bun (Oven) — remplace npm
- **Framework :** Vue 3.5
- **Build :** Vite 7.2
- **Visualisation :** D3.js 7.x
- **HTTP :** Axios
- **Router :** vue-router 4.x

## Commandes
```bash
bun install               # Installer les dépendances
bun run dev -- --host     # Serveur de développement (port 3000)
bun run build             # Build de production
```

## Migration npm → Bun
1. Supprimer `package-lock.json`
2. Exécuter `bun install` (génère `bun.lockb`)
3. Les scripts restent identiques (`vite --host`, `vite build`)

## Évolutions Prévues (Phase 5+)
- [ ] WebSocket client pour le flux de prix en temps réel
- [ ] Graphe de vélocité de sentiment (D3.js)
- [ ] Dashboard d'investissement avec positions simulées

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
- For this frontend scope, also read root `GEMINI.md`, `AGENTS.md`, and the vault symlink `300 Entities/Projects/RustyMiroSquid`.
- Keep UI decisions tied to the investment-simulation workflow; mirror durable dashboard/product decisions back into the vault.
- Use Beads/GSD if present, GitNexus before symbol edits, RTK for noisy command output, and run `bun run build` or the smallest relevant frontend gate before finishing.
<!-- BORG_KNOWLEDGE_WORKFLOW_END -->
