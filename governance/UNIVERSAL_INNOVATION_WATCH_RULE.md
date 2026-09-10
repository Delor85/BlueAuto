# RÈGLE UNIVERSELLE PERMANENTE — Veille Innovation Positive

Cette règle s'applique à tous les projets Delor85. Elle impose de rechercher régulièrement des innovations, fonctionnalités, modules, idées, algorithmes, parcours, méthodes opérationnelles et briques gratuites/open source susceptibles d'améliorer positivement le projet sans dégrader les acquis.

## FIT-LAPS
Tout candidat est évalué sur : Fit métier, Impact utilisateur, Terrain réel, Licence/droits, Architecture, Privacy/Protection, Sustainability.

Décisions : `ADOPT_NOW`, `REIMPLEMENT_IDEA`, `PILOT`, `WATCH`, `REJECT`.

## Copier l'idée, pas le code — clean-room
Une licence difficile, inconnue, restrictive, payante ou en négociation ne doit pas automatiquement faire jeter une bonne idée. Si seul un fragment nous intéresse, ou si le code/SDK/modèle n'est pas réutilisable, nous pouvons reproduire indépendamment la fonctionnalité utile :

- ne jamais copier code source, poids propriétaires, clés, assets, données, textes protégés, secrets, ni écrans pixel-par-pixel ;
- formaliser d'abord le besoin, le comportement observable et le résultat attendu dans une spécification indépendante ;
- concevoir ensuite notre propre architecture, nos propres algorithmes, UX/UI, textes et tests ;
- permettre la reprise d'un simple fragment : flux, logique de file, scoring, fidélité, interaction, monétisation, cache, simulation, etc. ;
- documenter la source d'inspiration avec le statut `REIMPLEMENTED_FROM_IDEA` lorsqu'aucun code tiers n'est incorporé ;
- vérifier séparément brevet, marque, secret d'affaires, réglementation ou autre droit applicable avant exploitation commerciale lorsque pertinent ;
- ne jamais utiliser cette règle pour contourner un accès, voler des secrets/données ou reproduire du contenu non public.

## Cadence
- à chaque tranche majeure : veille ciblée ;
- chaque semaine : scan court des innovations significatives ;
- chaque mois : revue approfondie des candidats ;
- à chaque incident de coût/performance : rechercher une alternative gratuite, open source ou réimplémentable ;
- lorsqu'un concurrent lance une fonction pertinente : décider rapidement si elle doit être adoptée, réimplémentée, améliorée ou rejetée.

## Sources
GitHub, GitLab, Hugging Face, arXiv/Papers with Code, Google AI Edge/MediaPipe, ONNX, Transformers.js, WebGPU, OpenCV/OpenMMLab, MapLibre/Turf/OpenStreetMap, Cloudflare, W3C/MDN/Chrome/Android, plateformes concurrentes et toute autre source crédible.

## Discipline
Préserver les acquis, documenter provenance/droits/décision, épingler les versions importantes, prévoir fallback, privilégier traitement local pour données sensibles, et passer par branche/PR/tests/CI avant de déclarer une innovation `ACQUIRED` quand le dépôt le permet.

Cette règle mutualise les méthodes et enseignements, jamais les secrets ou données privées entre projets.
