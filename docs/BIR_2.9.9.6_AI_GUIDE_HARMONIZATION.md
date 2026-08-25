# B.I.R. 2.9.9.6 — Harmonisation Assistant / Guide utilisateur

Date : 2026-08-25
Branche : `feat/bir-v2-9-9-6-ai-guide-harmonization`
Base : `fix/bir-v2-9-9-3-android11-child-warroom-tchoronko` @ `e27a0ead275b44be880461a9be548bb3c9c5a0c5`
Version Android candidate : `2.9.9.6` / `versionCode 70`

## Objectif

Converger les demandes UX/IA avec les acquis B.I.R. 2.9.7 → 2.9.9.5, sans réécrire le moteur financier et sans réintroduire les couches historiques ayant provoqué des instabilités Android 11.

## Changements apportés

1. Le sélecteur `EN` / `FR` est compacté à 42 px et reste visible sans monopoliser la largeur.
2. L'espace libéré devient une barre de découverte de l'Assistant B.I.R. avec exemples d'usage.
3. Un catalogue local des services est disponible par rubrique : Accueil, Réseau, Piloter/Fournir/Vendre, Activité, Gérer.
4. L'Assistant peut expliquer comment utiliser les services et comment il fonctionne lui-même.
5. Pour DAE/DSM, « Prépare 5 000 FCFA pour POS1 » peut uniquement préremplir le formulaire d'approvisionnement ; aucune transaction n'est créée, prévisualisée, confirmée ou exécutée.
6. Une couche `ai-role-guard-v2996.js` applique désormais un verrouillage explicite par rôle.

## Verrouillage IA du rôle PoS

Le PoS conserve l'aide IA liée à ses propres capacités :

- situation de son compte, solde et preuves ;
- achat de crédit auprès de son supérieur ;
- vente client ;
- file, journal et rapprochement ;
- diagnostic boutons, Robot/Remote, SIM, Accessibilité ;
- synchronisation et vérification serveur ;
- navigation vers les rubriques autorisées.

Le PoS ne reçoit pas l'aide réservée aux DAE/DSM concernant :

- préparation d'approvisionnement d'un enfant (`Prépare 5 000 FCFA pour POS1`) ;
- War Room des enfants ;
- Check Réseau hiérarchique / audit réseau enfants ;
- solde enfant ;
- gestion Tchoronko ;
- politiques ou taux de commission des enfants ;
- diagnostic/explication d'alertes portant sur un enfant du réseau ;
- listes de services DAE/DSM présentées comme disponibles pour le PoS.

Le garde s'exécute en interception avant les handlers de l'Assistant existant afin d'éviter qu'une ancienne réponse générique puisse contourner la séparation des rôles.

## Invariants préservés

- aucune modification Cloudflare / D1 / Worker ;
- aucune modification des migrations ;
- aucun changement preflight, double confirmation, FIFO, lease, idempotence ou UNKNOWN ;
- aucun changement du stockage PIN ;
- aucun changement du moteur USSD / Accessibilité ;
- aucun changement du multi-SIM / unicité Robot ;
- certificat historique attendu inchangé ;
- aucune réactivation de `transaction-first-v298.js`, `reference-stability-v299.js`, `field-runtime-v2991.js` ou `field-runtime-v2992.js`.

## Fichiers principaux

- `app/src/main/assets/ai-guide-v2996.css` ;
- `app/src/main/assets/ai-guide-v2996.js` ;
- `app/src/main/assets/ai-role-guard-v2996.js` ;
- `app/src/main/assets/intelligence-v297.js` ;
- `app/src/test/v2996-ai-guide-harmonization-contract.mjs` ;
- `app/src/test/v2996-webview-smoke.sh` ;
- `.github/workflows/v2996-ai-guide-qualification.yml` ;
- `app/build.gradle` → 2.9.9.6 / vc70.

## Validation automatisée prévue

Le workflow `BIR v2.9.9.6 AI Guide Qualification` doit :

1. vérifier que la branche n'a aucune mutation Cloudflare ;
2. valider les contrats 2.9.9.5 et 2.9.9.6 ;
3. vérifier la syntaxe JavaScript et le smoke shell ;
4. exécuter les tests unitaires Android ;
5. construire un APK Release 2.9.9.6 / vc70 avec le certificat historique ;
6. vérifier package, version, minSdk 23, targetSdk 34 et SHA-256 ;
7. lancer un smoke de rendu/lifecycle sur Android 6, Android 11 et Android 16 ;
8. ne réaliser aucun déploiement Cloudflare/D1.

## Validation terrain à conserver avant production

Même après CI verte :

- vérifier physiquement Android 6, Android 11 et un Android récent ;
- tester FR → EN → FR ;
- tester le rail IA et les questions proposées ;
- vérifier que le PoS ne voit ni ne reçoit l'aide DAE/DSM ;
- vérifier DAE/DSM : préparation = préremplissage seulement ;
- vérifier que le parcours financier réel et toutes les confirmations restent inchangés.

## Point de reprise

Ne pas déployer Cloudflare/D1 dans cette étape. La livraison 2.9.9.6 est une évolution Android/UI/Assistant. Toute production serveur reste soumise à une autorisation distincte.
