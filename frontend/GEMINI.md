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
