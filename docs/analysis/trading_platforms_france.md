# Plateformes de Trading API en France : Guide Simplifié (RustyMiroSquid)

## 1. Cadre Légal & Fiscal (France)
En tant qu'utilisateur particulier (domicilié en France) développant une IA pour gérer son propre capital :

- **Déclaration 3916-bis** : Obligation de déclarer les comptes à l'étranger (Alpaca, IBKR, Kraken) chaque année au fisc français.
- **Flat Tax (PFU)** : Prélèvement Forfaitaire Unique de **31,4%** (12,8% IR + 18,6% PS) sur les gains réalisés.
- **Opérations Crypto** : Exonération sur les échanges crypto-à-crypto. Taxable uniquement lors de la conversion en Euro (si > 305€/an).

## 2. Comparatif des Plateformes API

| Plateforme | Paper Trading | Points Forts |
|---|---|---|
| **Alpaca** | Natif & Gratuit | API-first, SDK Python excellent, Exécution 24/5 sur US Equities. |
| **IBKR** | 1,000,000$ Virtuels | Standard industriel, accès Euronext (France), frais dégressifs. |

## 3. Architecture Recommandée
Utiliser **Alpaca** pour la phase de prototypage et de simulation (Paper Trading) grâce à sa facilité d'intégration. Envisager **Interactive Brokers** pour l'accès aux marchés européens à terme.

## 4. Sécurité Critique
- **IP Whitelisting** : Restreindre l'accès à l'API à une adresse IP fixe.
- **Withdrawal Lock** : Désactiver l'autorisation de retrait (Withdraw) sur les clés API.

---
*Dernière mise à jour : 2026-04-05*
