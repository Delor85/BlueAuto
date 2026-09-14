# BlueAuto / Blue Magic — registre d’adoption des innovations

Décision du 14 septembre 2026.

Ce fichier devient une référence à relire avant toute réforme importante. Les acquis Robot/Remote, Android 6+, multi-SIM, file locale, reprise et fonctionnement sans veille forcée doivent être préservés.

## 1. Sécurisation de la chaîne APK — ADOPT_NOW
Objectif : rendre chaque APK traçable jusqu’au commit et au workflow qui l’a produit.

À intégrer progressivement dans GitHub Actions :
- génération d’un hash SHA-256 pour chaque APK livré ;
- SBOM CycloneDX des dépendances ;
- conservation de la provenance du build ;
- signature et vérification des artefacts selon une méthode compatible avec la chaîne Android existante ;
- publication des métadonnées avec la Release ;
- contrôle que l’APK publié correspond exactement au commit et au workflow attendus ;
- conservation du keystore Android existant et absence de rotation implicite afin de préserver les mises à jour par-dessus les versions installées.

Ordre recommandé : hash → SBOM → provenance → signature/vérification → politique de release. Toute étape doit pouvoir être désactivée sans empêcher un build de diagnostic.

## 2. Cloudflare Queues — ADOPT_NOW par étapes
But : fiabiliser le transport serveur ↔ téléphone Robot/Remote sans remplacer la file locale Android.

Architecture cible : commande créée → stockage canonique → message Queue → appareil disponible → réservation de commande → exécution USSD → résultat → synchronisation. La Queue transporte et réessaie ; la base conserve l’état métier ; Android garde sa résilience locale.

Obligatoire : idempotence par identifiant de commande, timeout de réservation, reprise après redémarrage, résultat rejouable sans double transaction, dead-letter/quarantaine pour cas irréconciliables et métriques de latence.

## 3. OpenFeature / feature flags — ADOPT_NOW
Toute réforme sensible doit être activable séparément : nouveau moteur de queue, nouvel overlay PIN, optimisation des vérifications de solde, nouvelles stratégies Remote. Ne jamais supprimer l’ancien chemin stable avant validation terrain.

## 4. Passkeys
WATCH uniquement pour les interfaces Web éventuelles. Ne jamais relever le minimum Android ni remplacer les mécanismes d’activation/pairing de l’application Android 6+ par une technologie indisponible sur les anciens appareils.

## 5. CAMARA / Open Gateway
WATCH. Potentiel futur pour Number Verification, SIM Swap ou Device Status si un opérateur/agrégateur réellement accessible au Cameroun les propose. Aucune dépendance tant que disponibilité, coût, réglementation et consentement ne sont pas confirmés.

## 6. Règle anti-régression
Avant fusion : build Android, tests minimum Android 6/API23 et versions modernes ciblées, validation Robot et Remote, vérification multi-SIM, reprise de file, annulation, synchronisation et mise à jour APK par-dessus une version précédente.
