# Backlog-RustyMiroSquid-v1.md

## Évolutions Proposées

| ID | Évolution | Description | Complexité | Priorité |
|---|---|---|---|---|
| 01 | **No-GIL Refactoring** | Optimisation du simulateur avec `ThreadPoolExecutor` pour le runtime No-GIL. | 5/10 | Haute |
| 02 | **Live Broker Bridge** | Connexion réelle aux APIs de trading (Alpaca/IBKR). *Infrastructure de bridge local finalisée.* | 8/10 | Haute |
| 03 | **Dashboard Integration** | Intégration du Market Color, des SMC Signals et des PnL agents dans le dashboard React. | 6/10 | Haute |
| 04 | **Behavioral Analysis** | Outil de comparaison des trades agents vs entrées SMC "idéales" a posteriori. | 7/10 | Moyenne |
| 05 | **Unit Test Coverage** | Augmentation de la couverture de test à ≥70% (standard équipe). | 4/10 | Moyenne |

| 06 | **Audit & Refactoring** | Alignement des dépendances, correction des lints et centralisation fiscale. | 4/10 | Haute |

**Completed in v1.6.0:**
- [x] French Fiscal Integration (PFU 31.4% calculation + Tax-aware R:R).
- [x] Trading Platforms Analysis (Alpaca/IBKR for France).
- [/] Project Audit & API Strategy Plan.

**Completed in v1.5.0:**
- [x] Multi-Timeframe Context (HTF Bias + LTF Entry signals).
- [x] Real-world Persona Library (Whales, Quants, Macro).
- [x] Institutional SMC Validation logic.
