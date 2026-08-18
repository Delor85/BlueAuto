# B.I.R. / Blue Magic — v2.9.1 permanente — récupération terrain

Date : 2026-08-18

## Ancre applicative

- Branche : `fix/bir-v2-9-1-field-recovery`
- SHA applicatif exact : `828fddb027309df4cecfccf482c99e6aa83d22e1`
- Package : `com.profitloop.blueauto`
- versionName : `2.9.1`
- versionCode : `56`
- minSdk : `23`
- targetSdk : `34`
- modes effectifs : `REMOTE`, `ROBOT` uniquement

Les commits documentaires ultérieurs ne changent pas cette ancre applicative.

## Problèmes terrain traités

### 1. Synchronisation Robot ↔ Remote lente / bloquée

Cause réelle observée dans le code : snapshot Remote 15 s, heartbeat 60 s, backoff réseau pouvant rester longtemps actif, cache dashboard Remote, et `FORCE_SYNC` qui ne réinitialisait pas entièrement la fenêtre snapshot. Une activité sur un autre compte pouvait indirectement relancer les cycles.

Correction :

- snapshot Remote 5 s ;
- heartbeat 20 s ;
- backoff maximal réduit et remis à zéro par Auto‑Réveil ;
- cache Remote réduit ;
- `FORCE_SYNC` invalide aussi l’horodatage snapshot ;
- vidage immédiat de l’outbox offline + résultats finaux à remonter ;
- régime normal de polling dashboard conservé à 60 s pour batterie/réseau ;
- surveillance fraîcheur toutes les 5 s ; réveil ciblé seulement si donnée >12 s ou événement de commande ;
- aucune fausse transaction n’est créée.

### 2. Utilisateur Remote éloigné du Robot

Le Worker 2.9 annonçait `force_sync:true` mais aucune route API ordinaire ne permettait au Remote de réveiller son Robot. Le canal Admin existant exigeait un entitlement Owner et ne devait pas être détourné.

Correction 2.9.1 :

- route `force_sync` Remote-only ;
- migration additive `0009_remote_sync_wake.sql` ;
- table `sync_wake_requests` ;
- demande bornée au **même `node_code`** ;
- cible = Robot actif + `robot_enabled` + SIM vérifiée ;
- une demande PENDING dédupliquée ; expiration 10 minutes ;
- le Robot récupère le réveil via son `lease_command` déjà existant ; aucun nouveau polling permanent ;
- réveil = sync événements/résultats + heartbeat, jamais création de transaction/commande USSD ;
- aucun PIN/secret/token stocké ; aucun SMS fallback.

### 3. Secours ouvrait « Taux de commission »

Cause : Android interceptait tous les `window.prompt()` dans un unique `onJsPrompt()` numérique intitulé « Taux de commission ».

Correction : classification contextuelle :

- commission → champ numérique + `VALIDER LE TAUX` ;
- Secours/SAV → champ texte multiline + `ENVOYER` ;
- autres prompts → saisie B.I.R. générique.

### 4. Solde lent ou trompeur

Correction :

- rafraîchissement transport accéléré seulement quand utile ;
- le calcul prédictif d’approvisionnement intègre le débit de commission ;
- une donnée non certifiée n’est plus présentée comme un solde exact : `≈ Estimation B.I.R. à rapprocher` ;
- la preuve Blue certifiée reste prioritaire ;
- aucune supposition de solde n’autorise une finance risquée.

### 5. Recherche globale des services

Ajout `TROUVER UN SERVICE` en langage simple, indexant les services déjà présents : solde, preuves, historique, TEST_NUMBER, fourniture, demande de stock, vente, Secours/SAV, réparation sync, comptes/SIM, permissions, Robot, réseau/flotte, activité, KYC, commissions, créances, rapports/audit, preuves Blue, catalogue Camtel, Mercenaires, administration enfant et santé serveur.

## Validation complète

### Convergence

- Run GitHub Actions : `32183356624` — **SUCCESS**
- contrats hérités 2.6.8 → 2.9 : verts
- nouveaux contrats 2.9.1 : verts
- Worker 2.9.1 + migration 0009 dry-run : vert
- Java/Gradle/tests unitaires/Release : verts
- APK éphémère exact SHA‑256 : `32570e0fa815b7a87634c17cd5a8bae3d1dcb2ac2761a3c7db134460329079c3`

### Même APK exact sur Android

Run : `32183719076` — **SUCCESS**

- Android 6/API23 : SUCCESS
- Android 8/API26 : SUCCESS
- Android 11/API30 : SUCCESS
- installation, lancement, force-stop, relance, absence de crash
- aucun rebuild entre les trois plateformes

### Production

Run : `32184875374` — **SUCCESS**

- D1 migrations jusqu’à `0009`
- `sync_wake_requests` vérifiée
- aucune migration restante après activation
- Worker : `2.9.1-cloudflare`
- Cloudflare Worker Version ID : `99554d17-3acb-4103-a478-0739002fc7cb`
- le health a servi encore 2.9.0 lors de la première lecture juste après déploiement puis 2.9.1 quatre secondes plus tard ; la CI attend désormais explicitement la propagation avant verdict
- capabilities requises : `force_sync`, `offline_sync`, `bir_relay`, `free_ops_cockpit`, `dae_pro_free`, `region_national_ops_free`, `super_admin`
- modes serveur : `REMOTE`, `ROBOT`

## APK permanente

- `BIR-Blue-Infinity-Retail-v2.9.1-vc56-Permanent.apk`
- taille : `227497` octets
- SHA‑256 : `0599337933327f1b64074d9fd6a66a9b863d348707f80961d2e5db66a7454b36`
- certificat SHA‑256 : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- DN : `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`
- RSA : 4096 bits
- v1/v2/v3 : true
- 1 signataire
- non debuggable
- zipalign 4 : OK

### Continuité de mise à jour

- v2.9.0 : package identique, code55, même certificat
- v2.9.1 : package identique, code56, même certificat

Mise à jour en place préservée ; ne pas désinstaller la 2.9.0 permanente pour le test normal de mise à jour.

### Preuve identité du code testé

Comparaison entre APK exacte de la matrice et APK permanente :

- entrées applicatives hors signature : `28`
- ajoutées : `0`
- supprimées : `0`
- modifiées : `0`

La signature n’a donc pas remplacé le code testé.

## Cahier des charges — complétude restante

La matrice détaillée est : `docs/BIR_V291_CAHIER_GAP_MATRIX.md`.

Principales vraies lacunes encore identifiées :

- KYC documentaire complet (CNI recto/verso/caméra/galerie + stockage chiffré et audit) ;
- paquet diagnostic JSON/ZIP nettoyé + FAQ SAV ;
- assistant explicite de rapprochement d’écart de solde ;
- reporting homogène avec graphes/filtres et exports CSV/PDF ;
- sauvegarde/export utilisateur/audit plus complet ;
- Mercenaires à finaliser selon règles métier gelées ;
- Tchoronko reste normativement `[À DÉFINIR]` dans le cahier maître et ne doit pas être déclaré complet artificiellement.

Academy Offline et API Business restent exclus pour l’instant. Aucun redimensionnement national n’est lancé.

## Tests terrain obligatoires

1. Installer 2.9.1 directement par-dessus 2.9.0 permanente.
2. Vérifier deux comptes Robot sur même téléphone puis un seul compte.
3. Remote éloigné : attendre une situation stale et vérifier Auto‑Réveil Remote→Robot.
4. Vérifier que le compte bloqué repart sans transaction sur un autre compte.
5. TEST_NUMBER.
6. Solde puis contrôle fraîcheur/qualification.
7. 5 dernières transactions et détail.
8. Secours/SAV : vérifier le champ texte, jamais le taux de commission.
9. Recherche globale : `solde`, `secours`, `SIM`, `KYC`, `commission`.
10. Reboot Robot + reprise de file.
11. Coupure Internet puis retour Internet sans double finance.
12. Multi-SIM et files indépendantes.
13. Une transaction financière de faible montant uniquement après les tests non financiers.

## ÉTAT DU PROJET APRÈS CETTE ÉTAPE

- Version : `2.9.1`
- Branche : `fix/bir-v2-9-1-field-recovery`
- SHA applicatif : `828fddb027309df4cecfccf482c99e6aa83d22e1`
- GitHub : convergence et matrice exactes vertes ; triggers temporaires à fermer sans fusion ; PR #4 à ne pas fusionner
- Cloudflare : `2.9.1-cloudflare`, Version ID `99554d17-3acb-4103-a478-0739002fc7cb`
- D1 : jusqu’à `0009`
- APK : code56/name2.9.1/SHA `0599337933327f1b64074d9fd6a66a9b863d348707f80961d2e5db66a7454b36`
- Problèmes traités : synchronisation lente/bloquée, réveil Remote distant, Secours/commission, solde trompeur, recherche services
- Cause : cadence/cache/backoff incomplets, `force_sync` annoncé mais route absente, prompt Android générique, calcul prédictif commission incomplet
- Correction : Auto‑Réveil local+distant non financier, same-node wake, prompt contextuel, fraîcheur solde, recherche globale
- Tests : contrats hérités+2.9.1, Worker/D1 dry-run, Java/Gradle, exact API23/26/30, production health, signature permanente
- Résultats : gates automatisés verts ; recette USSD/SIM physique encore requise
- Acquis : aucun faux réveil financier, aucun SMS fallback, modes REMOTE/ROBOT uniquement, PIN local, PR #4 intacte
- Reste à faire : recette physique puis lots cahier additifs de `BIR_V291_CAHIER_GAP_MATRIX.md`
- Régression possible : aucune détectée automatiquement ; spécificités USSD/opérateur/constructeur à tester physiquement
- Autorisation prochaine : diagnostic/recette autorisés ; nouvelle expansion/redimensionnement reste hors périmètre

## Procédure de reprise

Dans un nouveau chat :

`BLUE MAGIC / B.I.R. — REPRISE v2.9.1. Lis d'abord docs/BIR_V291_RELEASE_PERMANENTE_2026-08-18.md puis docs/BIR_V291_CAHIER_GAP_MATRIX.md. Ancre applicative 828fddb027309df4cecfccf482c99e6aa83d22e1. Production Worker 2.9.1-cloudflare / Version ID 99554d17-3acb-4103-a478-0739002fc7cb ; D1 jusqu'à 0009. APK permanente code56/name2.9.1 SHA256 0599337933327f1b64074d9fd6a66a9b863d348707f80961d2e5db66a7454b36 ; certificat f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5. Runs : convergence 32183356624 ; exact Android 32183719076 ; production 32184875374. Deux modes REMOTE/ROBOT ; pas SMS fallback ; PIN jamais serveur/Remote/Admin ; Auto‑Réveil same-node non financier ; PoS→DSM→DAE→ADMIN ; PR #4 interdite de fusion sans autorisation distincte. Vérifie toujours GitHub→Actions→Cloudflare/D1→APK avant toute mutation.`
