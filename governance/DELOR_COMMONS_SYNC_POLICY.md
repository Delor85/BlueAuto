# DELOR_COMMONS — Politique universelle de mutualisation

Version : 1.0 — 2026-09-11

## But
Tous les projets Delor85 doivent pouvoir bénéficier des règles, innovations, patterns techniques et procédures qui ont déjà fait leurs preuves dans un autre projet, sans recopier aveuglément le métier ou les données de ce projet.

## Éléments mutualisables
- garde-fous universels ;
- Innovation Watch / FIT-LAPS / REIMPLEMENT_IDEA ;
- procédure anti-régression ;
- procédure sauvegarde / reprise / CURRENT_TRUTH ;
- patterns offline-first et faible réseau ;
- modèles de vérité paiement et idempotence ;
- consentement et privacy ;
- sécurité API, auth, secrets et permissions minimales ;
- observabilité/tests/CI ;
- accessibilité et confort UX ;
- coûts IA et fallbacks ;
- composants génériques quand leur licence et leur architecture le permettent.

## Interdictions
Ne jamais synchroniser automatiquement :
- secrets, tokens, clés, mots de passe ;
- PII et données utilisateurs ;
- données financières ou médicales ;
- tables métier incompatibles ;
- assets propriétaires ;
- code tiers sans droits compatibles.

## Pipeline d’une innovation
DISCOVERED → FIT-LAPS → ADOPT_NOW / REIMPLEMENT_IDEA / PILOT / WATCH / REJECT → qualification projet par projet.

Une fonction utile trouvée chez un concurrent ou dans un logiciel sous licence difficile peut être réimplémentée indépendamment : spécification du comportement public, architecture originale, code original, UX/textes originaux, tests originaux. Aucun code, asset, poids propriétaire, secret, donnée ou identité visuelle n’est copié.

## Registre commun cible
À terme, un registre DELOR_COMMONS devra contenir :
- UNIVERSAL_GUARDRAILS.yaml
- INNOVATION_RADAR.json
- CAPABILITY_REGISTRY.yaml
- SECURITY_BASELINE.md
- OFFLINE_FIRST_PATTERNS.md
- PAYMENT_TRUTH_MODEL.md
- CONSENT_MODEL.md
- ANTI_REGRESSION_RULES.md
- BACKUP_RECOVERY_STANDARD.md
- AI_COST_GUARDRAILS.md

## Règle d’intégration
Une règle commune n’écrase jamais CURRENT_TRUTH d’un projet. Le projet local reste autoritaire sur son métier. DELOR_COMMONS propose, le projet évalue, teste et adopte.

## Projets actuellement concernés
- Delor85/as-beauty
- Delor85/BlueAuto
- Delor85/tontine-platform / Eco-System et plateformes associées

Tout nouveau dépôt Delor85 doit évaluer cette politique lors de son bootstrap.
