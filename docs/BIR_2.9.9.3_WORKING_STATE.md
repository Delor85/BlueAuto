# B.I.R. 2.9.9.3 — état de travail

- Base exacte : B.I.R. 2.9.9.2 `abde508132568ef1c9eefb6ee058db21af5577a2`.
- Branche : `fix/bir-v2-9-9-3-android11-child-warroom-tchoronko`.
- Cible : `2.9.9.3`, versionCode `67`.
- Constat terrain déterminant : Android 11 est stable sur B.I.R. 2.9.7 et versions antérieures ; la régression apparaît après la rupture d'architecture UI de la lignée 2.9.8/2.9.9.

## Architecture Android 6+ unifiée

- Il n'existe plus de chemin visuel ou fonctionnel spécial Android 11. Android 6, 7, 8, 9, 10, 11, 12, 13, 14, 15 et 16 doivent charger le même cockpit moderne et les mêmes fonctionnalités B.I.R.
- Le moteur Intelligence/Cockpit exact de la 2.9.7 terrain (`intelligence-v297.js` historique, blob `514aa337d1ff4afabb416a726aeb819479cf4be9`) est conservé dans `intelligence-v297-core.js` et redevient la fondation UI commune.
- `intelligence-v297.js` est désormais uniquement un chargeur commun : noyau 2.9.7, puis `field-runtime-v2993`. Il ne détecte pas Android 11 et ne charge plus `transaction-first-v298`, `reference-stability-v299`, `field-runtime-v2991` ou `field-runtime-v2992`.
- Motif technique : la 2.9.8 a remplacé le cockpit additif par une couche qui créait un second Home après affichage, déplaçait/reparentait plusieurs blocs DOM existants, installait un MutationObserver supplémentaire, enveloppait plusieurs callbacks et relançait Dashboard/file. La 2.9.9 y ajoutait encore des réveils sur install, focus, pageshow et visibilité. Cette reconstruction n'existait pas dans la lignée stable.
- `BirApplication.java` et `AndroidManifest.xml` ont retrouvé le comportement structurel 2.9.7 : pas de `ActivityLifecycleCallbacks` ajouté pour forcer une synchro à chaque reprise, pas de sélection de renderer par version Android. Les anciennes ressources `bir_rendering` Android-spécifiques ont été retirées.
- Le rythme de contrôle historique, l'Accessibilité, RobotService, la file et les mécanismes natifs restent indépendants de l'interface et ne sont pas réécrits par cette correction.

## Fonctions actuelles conservées/ajoutées dans la couche commune 2.9.9.3

- Achat de crédit visuellement distinct en vert sur le même écran statique, pour toutes les versions Android.
- Inscription Tchoronko avec résultat succès/erreur/timeout explicite.
- DAE : liste de ses DSM directs, y compris DSM2G/Tchoronko.
- DSM : liste de ses PoS directs, y compris PoS2G/Tchoronko.
- War Room cliquable de chaque enfant direct : identité, SIM, terminal, zone, solde/fraîcheur, activité, alertes, état Robot/Accessibilité lorsque disponible.
- Commission parent→enfant : taux persistant/défaut/personnalisé et taux ponctuel/écart récent lorsque le registre serveur en apporte la preuve.
- Navigation sûre de la War Room vers Approvisionner ou Consulter solde : préremplissage seulement, aucune exécution financière automatique.
- Le noyau 2.9.7 restitue également son cockpit adaptatif, sa recherche, son Assistant/IA local, sa barre de vérité et le rapprochement financier. Les ajouts 2.9.9.3 viennent compléter ce cockpit au lieu de le remplacer.

## Anti-régression et qualification

- Aucun changement `cloudflare/`, aucune migration D1, aucune fusion ni production.
- Invariants à préserver : finance/preflight/double confirmation/FIFO/idempotence/UNKNOWN/PIN/Accessibilité/dual-SIM/Robot unique/certificat permanent.
- Qualification dédiée : un APK exact est construit une seule fois puis installé sur la matrice Android 6→16.
- Le smoke injecte uniquement dans l'émulateur un profil DAE local/non-production afin d'ouvrir le vrai WebView. Il exige le cockpit moderne `COCKPIT ADAPTATIF` puis la `WAR ROOM DES ENFANTS` avant tout stress.
- Le stress ne clique aucune opération financière : navigation Accueil/Réseau, défilement et cycles arrière-plan/reprise uniquement. Android 11 reçoit un stress renforcé.
- L'ancien rouge de matrice du run 32834988156 était un défaut de harnais : `android-emulator-runner` exécutait chaque ligne du bloc shell séparément et coupait la boucle `for` avant `done`. Ce résultat n'est pas une preuve de plantage applicatif.
- Le workflow historique `v299-reference-stability.yml` est désormais limité à sa propre ligne 2.9.9 ; il ne juge plus la 2.9.9.3 avec des contrats de l'architecture abandonnée.
- Le cahier des charges maître ne sera déclaré définitivement mis à jour qu'après qualification de l'APK exact et validation terrain, notamment Android 11 réel.
