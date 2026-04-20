# 🐙 RustyMiroSquid Frontend — GEMINI.md

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

<!-- BORG_KNOWLEDGE_WORKFLOW_START -->
## Borg Knowledge Vault & AI Workflow

- Shared memory lives in `/home/_johan/Documents/Borg`. Start with `300 Entities/Projects/Portfolio - Condensed Knowledge.md`, `400 Resources/Tech/AI Knowledge Map.md`, `000 OS / Meta/AI Collaboration Protocol.md`, and `300 Entities/People/Johan - Working Profile.md`.
- For this frontend scope, also read root `GEMINI.md`, `AGENTS.md`, and the vault symlink `300 Entities/Projects/RustyMiroSquid`.
- Keep UI decisions tied to the investment-simulation workflow; mirror durable dashboard/product decisions back into the vault.
- Use Beads/kspec if present, GitNexus before symbol edits, RTK for noisy command output, and run `bun run build` or the smallest relevant frontend gate before finishing.
<!-- BORG_KNOWLEDGE_WORKFLOW_END -->
