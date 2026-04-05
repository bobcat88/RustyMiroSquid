# Patchnote-RustyMiroSquid-v1.md

## 1.2.0 — 2026-04-05

### TECH
- Intégration du `TriggerService` dans la boucle de simulation parallèle (`run_parallel_simulation.py`).
- Implémentation du `TradingPersonaFactory` pour la génération d'archétypes (Whale, Alpha, Sniper, Reactor).
- Renforcement du `MarketMediaBridge` pour le partage de données inter-thread (Snapshots).
- Optimisation des prompts d'agents pour inclure le contexte de microstructure de marché.

### FUNCTION
- Les agents Polymarket possèdent désormais des traits de personnalité spécialisés influençant leurs décisions de trading.
- Injection dynamique de données réelles (yfinance, RSS) dans chaque round de simulation.
- Support du "Market Color" (Fear/Greed) pour le basculement stratégique des agents.

### QoL
- Structure de code backend améliorée pour le support des multi-thread snapshots.
- Documentation technique mise à jour avec les nouveaux services.

## 1.1.0 — 2026-04-05

### TECH
- Création du dossier `docs/analysis/` pour centraliser les analyses de stratégies IA.
- Comparaison des concepts **Smart Money Concepts (SMC)** avec les études réelles de Microstructure de Marché (Bouchaud, Vayanos, Kyle).

### FUNCTION
- Ajout de 3 analyses détaillées des vidéos stratégiques de **Kasper** (SMC + Claude 3.5 Sonnet).
- Création d'un **Resume Strategique** pour l'implémentation des agents IA dans RustyMiroSquid.
- Ajout d'un guide complet sur le **Gestion du Risque (R:R)** et la sélection d'actifs (SPY, QQQ, NVDA).
- Intégration de la méthodologie **OVTLYR Fund Manager** (Plans A, M, ETF & SICADFU).
- Définition des signaux de scan (Liquidity Sweep + MSS) pour automatiser les entrées/sorties.

### QoL
- Structure de documentation étendue aux analyses externes.

## 1.0.0 — 2026-04-04

### UI
- N/A (Initial PR)

### UX
- N/A (Initial PR)

### TECH
- Fork initialisé avec le standard **PROUST v3.0**.
- Création de la branche `feat/pro-init-v1`.
- Mise en conformité de la documentation (4 fichiers standard).

### FUNCTION
- Initialisation du moteur de simulation MiroShark.

### QoL
- Structure de repository clarifiée.

### BUGFIX
- N/A
