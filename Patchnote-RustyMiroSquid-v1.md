## [v1.7.0] — 2026-04-06

### TECH
- Migration vers **Python 3.14** validée (compatible avec `uv python pin 3.14`).
- Audit complet de compatibilité : zéro warning en mode strict (`-W error::DeprecationWarning`).
- Mise à jour de **camel-ai** (0.2.90), **neo4j** (6.1.0), **pytest** (9.0.2), **pytest-asyncio** (1.3.0).
- Intégration des bridges **Alpaca** (Paper Trading) et **IBKR** (TWS/Gateway) via `alpaca-py` et `ib-insync`.
- Migration complète de **npm** vers **bun** (racine + frontend) avec génération de `bun.lockb`.
- Refactorisation du code asynchrone pour suivre les standards Python 3.14+ (`inspect` & `get_running_loop`).
- Nouvelle architecture **BaseBroker** avec injection native du **FiscalService** (Tax-Aware Equity).
- Suppression des overrides `tool.uv` dans `pyproject.toml`.

## [v1.6.0] — 2026-04-05

### TECH
- Intégration de `FiscalService` pour le calcul du PFU 31.4% (Flat Tax).
- Ajustement de `TradingPolicy` pour compenser la pression fiscale (Min R:R 4.0).
- Audit complet des dépendances et de l'architecture (voir `audit_report.md`).
- Définition de la stratégie d'intégration API Alpaca (Paper Trading) et IBKR (Production).

### FUNCTION
- Les agents sont désormais "Tax-Aware" et affichent leur Equity Nette Estimée.

## 1.5.0 — 2026-04-05

### TECH
- Bibliothèque de Personas réelles (`personas_v1.json`) basée sur des profils emblématiques (Whale, Innovateur, Macro, Retail).
- Support du chargement dynamique des Personas dans `TradingAgent` via `archetype`.
- Amélioration de l'injection de prompts MTF dans `MarketMediaBridge` avec formatage [TREND] vs [ENTRIES].
- Mise à jour de `TradingAction` avec le renommage des directions (BULLISH/BEARISH) pour la clarté opérationnelle.

### FUNCTION
- Validation SMC stricte via `TradingPolicy` (HTF Bias + LTF Sweep + LTF MSS).
- Intégration des personas dans le comportement social et décisionnel de l'agent (Risk adjustment & Persona specific context).
- Support du scale-out automatique à 2.0 R:R pour les agents institutionnels.

### QoL
- Prompts d'agents enrichis avec des rappels de stratégie institutionnelle (3-Step Confluence).

## 1.4.0 — 2026-04-05

## 1.3.0 — 2026-04-05

### TECH
- Intégration complète du toolkit `TradingAction` avec héritage de `PolymarketAction`.
- Injection automatique de l'agent (`LocalBroker` & `TradingPolicy`) dans la couche d'action au runtime.
- Mise à jour de la boucle de simulation (`run_parallel_simulation.py`) pour l'injection temps-réel du portfolio.
- Support hybride des outils : Trading d'actions + Marchés de prédiction (Polymarket).

### FUNCTION
- Les agents peuvent désormais soumettre des ordres (`submit_market_order`), consulter leur portfolio et valider leurs risques via des outils LLM.
- Les décisions de trading sont désormais contraintes par la `TradingPolicy` (gestion du risque dynamique).

### BUGFIX
- Correction de l'identification des agents dans les logs de simulation inter-plateformes (`Twitter`/`Reddit`/`Polymarket`).

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
- Initialisation du moteur de simulation RustyMiroSquid.

### QoL
- Structure de repository clarifiée.

### BUGFIX
- N/A
