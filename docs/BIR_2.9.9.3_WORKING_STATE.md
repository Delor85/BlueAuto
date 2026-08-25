# B.I.R. 2.9.9.3 — état de travail

- Base exacte : B.I.R. 2.9.9.2 `abde508132568ef1c9eefb6ee058db21af5577a2`.
- Branche : `fix/bir-v2-9-9-3-android11-child-warroom-tchoronko`.
- Cible : `2.9.9.3`, versionCode `67`.
- Constat terrain déterminant : Android 11 est stable sur B.I.R. 2.9.7 et versions antérieures ; la régression apparaît dans la lignée 2.9.9.
- Stratégie API30 : ne pas exécuter les couches UI introduites après 2.9.7 (`transaction-first-v298`, `reference-stability-v299`, `field-runtime-v2991`, `field-runtime-v2992`). Garder le socle historique déjà chargé par `index.html`/`field-ops-v297`/`war-room-v294`, puis ajouter uniquement `field-runtime-v2993`.
- API30 retrouve l'accélération matérielle utilisée par le chemin pré-2.9.9 et ne reçoit plus le `forceSync` supplémentaire à chaque reprise Activity/process start. Le cycle 10 s historique du RobotService/BirApplication reste inchangé.
- Autres Android : chaîne UI moderne 2.9.8→2.9.9.2 conservée, puis couche 2.9.9.3 additive.
- 2.9.9.3 ajoute : inscription Tchoronko avec retour succès/erreur/timeout explicite, listes directes DAE→DSM2G et DSM→PoS2G, War Room cliquable de chaque enfant direct, solde/preuve/activité/terminal/alertes, taux de commission persistant et taux ponctuel/écart récent lorsqu'il existe, navigation sûre vers approvisionnement/solde sans exécution automatique.
- Aucun changement `cloudflare/`, aucune migration D1, aucune fusion ni production.
- Invariants : finance/preflight/double confirmation/FIFO/idempotence/UNKNOWN/PIN/Accessibilité/dual-SIM/Robot unique/certificat permanent préservés.
- Qualification dédiée : build exact + contrats historiques ciblés + vrai WebView avec profil local CI sur Android 6/8/11/14 ; API30 stress renforcé.
- Le cahier des charges maître doit être mis à jour uniquement après qualification et livraison permanente de cette version.
