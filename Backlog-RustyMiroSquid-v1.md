# Backlog-RustyMiroSquid-v1.md

## Évolutions Proposées

| ID | Évolution | Description | Complexité | Priorité |
|---|---|---|---|---|
| 01 | **No-GIL Refactoring** | Optimisation du simulateur avec `ThreadPoolExecutor` pour le runtime No-GIL. | 5/10 | Haute |
| 02 | **FastAPI Migration** | Passage de Flask à FastAPI + Pydantic v2 (Standard PROUST). | 6/10 | P0 |
| 03 | **UI Upgrade** | Intégration intensive de Motion, Lucide et shadcn-vue / Tailwind v4. | 5/10 | P1 |
| 04 | **Polars Integration** | Évaluation / remplacement de pandas par Polars pour les pipelines data. | 7/10 | P2 |
| 05 | **Frontend Pivot** | Audit et migration potentielle de Vue 3.5 vers Next.js 15. | 9/10 | P2 |
| 06 | **Live Broker Bridge** | Connexion réelle aux APIs de trading (Alpaca/IBKR). | 8/10 | Haute |
| 07 | **Dashboard Integration** | Intégration du Market Color et des SMC Signals. | 6/10 | Haute |
| 08 | **Behavioral Analysis** | Comparaison trades agents vs entrées SMC "idéales". | 7/10 | Moyenne |
| 09 | **Unit Test Coverage** | Augmentation de la couverture de test à ≥70%. | 4/10 | Moyenne |

| 06 | **Audit & Refactoring** | Alignement des dépendances (Python 3.14), correction asynchrone et centralisation fiscale. | 4/10 | **Terminé** |

**Completed in v1.7.0:**
- [x] Python 3.14 Compatibility Audit & Zero-Warning refactor.
- [x] BaseBroker architecture with FiscalService injection.
- [x] Alpaca/IBKR API Bridges (Paper Trading support).

**Completed in v1.6.0:**
- [x] French Fiscal Integration (PFU 31.4% calculation + Tax-aware R:R).
- [x] Trading Platforms Analysis (Alpaca/IBKR for France).

**Completed in v1.5.0:**
- [x] Multi-Timeframe Context (HTF Bias + LTF Entry signals).
- [x] Real-world Persona Library (Whales, Quants, Macro).
- [x] Institutional SMC Validation logic.
