# Backlog-RustyMiroSquid-v1.md

## Évolutions Proposées

| ID | Évolution | Description | Complexité | Priorité |
|---|---|---|---|---|
| 01 | **No-GIL Refactoring** | Optimisation du simulateur avec `ThreadPoolExecutor` pour le runtime No-GIL. | 5/10 | Haute |
| 02 | **SMC Strategy Agent** | Implémentation du moteur de décision SMC (Liquidity Sweeps, FVG, MSS) via Claude 3.5. | 8/10 | Haute |
| 03 | **Breadth Market Scanner** | Scanner multi-paires Rust pour détecter l'accumulation institutionnelle (Order Blocks). | 7/10 | Haute |
| 04 | **Auto-Pine Script Gen** | Génération dynamique de scripts TradingView V5 par l'agent pour la vérification visuelle. | 6/10 | Moyenne |
| 05 | **Unit Test Coverage** | Augmentation de la couverture de test à ≥70% (standard équipe). | 4/10 | Moyenne |
| 06 | **Live Broker Bridge** | Connexion réelle aux APIs de trading (Alpaca/IBKR) pour exécution live. | 7/10 | Haute |
| 07 | **Market Data UI** | Intégration du Market Color et des SMC Signals dans le dashboard React. | 5/10 | Moyenne |
