# B.I.R. 2.9.9.6 — Harmonisation Assistant / Guide utilisateur

Date : 2026-08-25
Branche : `feat/bir-v2-9-9-6-ai-guide-harmonization`
Base : `fix/bir-v2-9-9-3-android11-child-warroom-tchoronko` @ `e27a0ead275b44be880461a9be548bb3c9c5a0c5`
PR de qualification : `#74` — brouillon, non fusionnée
Version Android candidate : `2.9.9.6` / `versionCode 70`

## Objectif

Converger les demandes UX/IA avec les acquis B.I.R. 2.9.7 → 2.9.9.5, sans réécrire le moteur financier et sans réintroduire les couches historiques ayant provoqué des instabilités Android 11.

## Changements apportés

1. Le sélecteur `EN` / `FR` est compacté à 42 px et reste visible sans monopoliser la largeur.
2. L'espace libéré devient une barre de découverte de l'Assistant B.I.R. avec exemples d'usage.
3. Un catalogue local des services est disponible par rubrique : Accueil, Réseau, Piloter/Fournir/Vendre, Activité, Gérer.
4. L'Assistant peut expliquer comment utiliser les services et comment il fonctionne lui-même.
5. La préparation en langage naturel reste un préremplissage seulement : aucune transaction n'est créée, prévisualisée, confirmée ou exécutée par l'Assistant.
6. Une couche `ai-role-guard-v2996.js` applique désormais un verrouillage explicite par rôle et par hiérarchie directe.

## Matrice stricte d'aide et de préparation

- DAE : peut recevoir l'aide de pilotage de ses enfants DSM et préparer uniquement un approvisionnement destiné à un DSM direct.
- DSM : peut recevoir l'aide de pilotage de ses enfants PoS et préparer uniquement un approvisionnement destiné à un PoS direct.
- PoS : ne possède aucun enfant de distribution ; il ne peut donc recevoir ni aide ni préparation d'approvisionnement d'enfant.
- Toute cible incompatible avec la hiérarchie est refusée avant le préremplissage.
- Cette matrice d'aide ne remplace jamais les contrôles serveur ou financiers existants ; elle ajoute une barrière UX/Assistant supplémentaire.

## Verrouillage IA du rôle PoS

Le PoS conserve l'aide IA liée à ses propres capacités :

- situation de son compte, solde et preuves ;
- achat de crédit auprès de son DSM supérieur ;
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

Le garde s'exécute en interception avant les handlers de l'Assistant existant afin d'éviter qu'une ancienne réponse générique puisse contourner la séparation des rôles. Le rail générique est masqué pour le PoS et remplacé par un rail PoS ne contenant que des exemples autorisés.

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
- `.github/workflows/v2996-ai-guide-role-scope.yml` ;
- `app/build.gradle` → 2.9.9.6 / vc70.

## Validation automatisée prévue

Les workflows 2.9.9.6 doivent :

1. vérifier qu'il n'existe aucune mutation Cloudflare ;
2. valider les contrats hérités 2.9.9.3/2.9.9.4/2.9.9.5 et le contrat 2.9.9.6 ;
3. vérifier explicitement le cloisonnement PoS et la hiérarchie DAE→DSM / DSM→PoS ;
4. vérifier la syntaxe JavaScript et le smoke shell ;
5. exécuter les tests unitaires Android ;
6. construire un APK Release 2.9.9.6 / vc70 ;
7. pour la qualification permanente, vérifier le certificat historique, package, version, minSdk 23, targetSdk 34 et SHA-256 ;
8. lancer les smokes Android 6, Android 11 et Android 16 ;
9. ne réaliser aucun déploiement Cloudflare/D1.

## Validation terrain à conserver avant production

Même après CI verte :

- vérifier physiquement Android 6, Android 11 et un Android récent ;
- tester FR → EN → FR ;
- tester le rail IA DAE, DSM et PoS ;
- vérifier que le PoS ne voit ni ne reçoit l'aide DAE/DSM ;
- vérifier qu'un PoS tapant manuellement « Prépare 5 000 FCFA pour POS1 » reçoit un refus sans préremplissage ;
- vérifier DAE→DSM et DSM→PoS ; refuser DAE→PoS et DSM→DSM dans le guide de préparation ;
- vérifier que la préparation autorisée reste un préremplissage seulement ;
- vérifier que le parcours financier réel et toutes les confirmations restent inchangés.

## État GitHub

- PR `#74` ouverte en brouillon ;
- aucune fusion effectuée ;
- aucun déploiement Cloudflare/D1 effectué ;
- le diff de la branche contre la base reste limité à Android/UI, tests, workflows et documentation.

## Point de reprise

Ne pas fusionner la PR #74 ni déployer de serveur sur la seule base de la présence du code. Conserver la qualification automatisée et le test terrain avant la livraison permanente. Toute production serveur reste soumise à une autorisation distincte.
