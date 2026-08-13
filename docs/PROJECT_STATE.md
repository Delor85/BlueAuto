# ÉTAT DU PROJET — APK v2.6.6 LIVRÉE / WORKER v2.6.5 EN PRODUCTION

État vérifié le 13 août 2026. La reprise doit commencer ici puis continuer dans `docs/PROCEDURE_REPRISE_EXTERNE.md`, qui contient le cahier des charges synthétisé, l'historique complet, les causes de régression, la procédure et les limites terrain.

## 0A. Reprise v2.6.6 — demande, retour terrain et état réel

Retour terrain reçu après la livraison v2.6.5 :

- Android 11 a finalement accepté l’installation, mais seulement après plusieurs essais, désinstallations et réinstallations ; ce résultat prouve que l’APK peut s’ouvrir sur ce téléphone, pas encore que la mise à jour directe y est fiable ;
- les autres versions Android essayées acceptent la mise à jour ;
- le diagnostic qui explique qu’une finance échoue lorsque l’Accessibilité ou les autorisations du Robot manquent est approuvé et doit être conservé ;
- Test, Achat et Vente, le trajet Remote → Worker/D1 → Robot, la confirmation 1/2, la propriété SIM/slot et le remplacement encadré d’un Robot fantôme restent des acquis à ne pas réécrire.

Demande ciblée v2.6.6 : rendre le réglage PIN immédiatement accessible dans **Gérer**, corriger l’insertion/validation du PIN sous verrou simple sans voile de confidentialité, repositionner les cinq onglets dans une navigation ergonomique et commencer à rendre chaque module utile, sans régression financière.

État fonctionnel livré :

- version Android préparée : `2.6.6`, code `46`, `minSdk 23`, `targetSdk 34` ;
- le réglage **MODIFIER LE PIN CAMTEL** est placé avant Autorisations et ouvre un dialogue dédié ; le panneau **Gérer** affiche une barre de défilement persistante et un indice explicite ;
- le verrou simple est traité avant la composition : réveil de l’écran, retrait temporaire du keyguard sans identifiant, ouverture de l’activité normale si l’OEM l’exige, stabilisation de la fenêtre puis appel USSD ; un verrou sécurisé n’est jamais contourné ;
- aucun overlay Blue Magic ne masque le dialogue Camtel ; le PIN peut être visible physiquement pendant l’insertion, tout en restant absent des journaux, du JavaScript, du Worker et de D1 ;
- lorsque le dialer Android confirme `ACTION_SET_TEXT` mais ne réexpose pas la valeur du champ, cette confirmation devient la preuve de saisie au lieu de provoquer cinq tentatives et une boucle apparente ;
- l’écran reste réveillé jusqu’au résultat ou à la fin de la commande, puis le verrou simple est restauré ;
- les onglets deviennent un dock inférieur flottant : Flux est central, le nœud actif reste dégagé et le dock disparaît pendant l’édition d’un formulaire ;
- Rapports calcule les indicateurs locaux, Flotte ouvre Comptes/SIM, Robot ouvre Autorisations/PIN/Gérer/Démarrer, SAV contrôle le serveur et renvoie vers le test sans fonds ;
- aucun changement Worker, D1, protocole financier, élection Robot ou migration n’est nécessaire pour cette tranche ; le Worker `2.6.5-cloudflare` reste compatible ;
- test statique/local `app/src/test/finance-flow.mjs`, tests Worker/D1 et `git diff --check` : réussis ; aucun fichier Worker ou migration n’a changé ;
- commit GitHub fonctionnel `45cca8f33b871a066e049f2b08b7a16e69cab8c5`, arbre `5fa0d70b2f8e40a07864ca0858f59dccbd9981ab`, identique à l’arbre du commit local autorisé `b502bfd81168dea7e8cc0004f77ef2c67a6d332b` ;
- runs GitHub Actions `31722781395` (push/export) et `31722786172` (PR, relance API 36) : compilation et tests financiers/serveur réussis ; mise à jour avec conservation des données réussie sur API 23, 26 et 30 ; lancement réel Android 11 et scénario Robot réussis dans le run PR ;
- API 36 reste une limite du harnais : les deux exécutions et la relance ont expiré sur `am start -W` de la v2.6.5 de référence, avant l’installation v2.6.6, sans crash Blue Magic ;
- export interne unique `Blue-Magic-v2.6.6-Internal-Resign`, artefact `9190012328`, créé le 13 août 2026 à 16:52 UTC, expiration le 14 août à 16:52 UTC ; ZIP SHA-256 `671b0041d44c96d292bce5e00e4abdbfef50fc59dc78ddd3d14bec25fdbe7e1b` ;
- APK finale `Blue-Magic-v2.6.6-Ergonomie-Verrou-PIN-Release.apk`, 119 515 octets, SHA-256 `9ff5fc65925030b4ef29a07550d0010cebb1d93c06fdc7d86bf7f4c5cdf3602b` ; paquet `com.profitloop.blueauto`, code 46, minSdk 23, targetSdk 34 ; signatures v1/v2/v3 valides et certificat permanent RSA 4096 `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5` ;
- l’export temporaire a été retiré du workflow après le téléchargement unique ; le commit de nettoyage utilise `[skip ci]`, donc aucun nouveau build ni export ne doit être déclenché ;
- le test Camtel réel sous verrou simple reste obligatoire avant de déclarer ce cas terrain validé.

Autorisation v2.6.6 exécutée dans son périmètre : publication, CI, export unique, re-signature permanente, livraison et nettoyage sans nouveau build. Aucun Worker, aucune migration D1 et aucun secret n’ont été modifiés ou publiés.

## 0. Livraison v2.6.5 autorisée et exécutée

Le propriétaire a autorisé le commit/push sur `fix/blue-magic-v2-6-recovery`/PR `#4`, un déploiement unique de `2.6.5-cloudflare` sans migration D1, un export interne unique, la re-signature permanente et la livraison. Il a ensuite autorisé explicitement la publication publique des documents et workflows du commit local `c7dbce4` dans son dépôt public `Delor85/BlueAuto`.

- Commit GitHub : `c7b9404e22e8c314f95723105b2e474e2b21194c` ; arbre `43cfc0fdb69c2ac7e504cd58d1508fb432eded47`, identique au commit local autorisé `c7dbce4`.
- Commit de nettoyage distant : `9b1d35f05630effa5e1683bfaa3da2195691ed61`, HEAD de la PR `#4`, ouverte et non fusionnée. Aucun run n'a été créé pour ce commit `[skip ci]`.
- Run build : `31710676903` ; artefact interne unique `9185102053`, expiration le 14 août 2026 à 14:32 UTC.
- Résultat final de matrice : mise à jour et conservation des données réussies sur API 23/Android 6 et API 26/Android 8. Les jobs API 30 et 36 ont été relancés une fois, mais `am start -W` a encore expiré sur la v2.6.4 de référence avant l'installation v2.6.5. Le job de lancement Android 11 a installé l'APK, puis le gestionnaire Activity a renvoyé `MainActivity does not exist` alors que cette activité est présente dans le manifeste décodé. Aucun crash Blue Magic n'est consigné, mais Android 11/36 restent à valider sur téléphone pour la v2.6.5. Une amélioration locale du harnais a été écartée de la publication parce que l'autorisation publique visait exactement les workflows de `c7dbce4`.
- Run Cloudflare : `31710676858` ; aucun fichier de migration en attente, aucune migration appliquée.
- Worker actif : `2.6.5-cloudflare`, D1 `online`, version Cloudflare `b2cc65a1-9d86-4d37-8d18-9e48b746e90e`.
- APK finale : `Blue-Magic-v2.6.5-Hall-SIM-Tabs-Release.apk`, 115 522 octets, SHA-256 `5b95a1bf61f397b3e1f4fe81328ccddda2e011704c18c13e955e7bda6b023384`.
- Paquet/version : `com.profitloop.blueauto`, `2.6.5`, code 45, minSdk 23, targetSdk 34.
- Signature : v1/v2/v3 valides ; certificat permanent RSA 4096 `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`, identique à la v2.6.4.
- Le contrôle de santé du workflow a lu `2.6.4` immédiatement après publication et a donc marqué le job en échec. Le déploiement lui-même était réussi ; un contrôle indépendant après propagation confirme `2.6.5-cloudflare` et D1 `online`.
- Le déclencheur et le workflow Cloudflare ponctuels ont été retirés après usage. Le retrait de l'étape d'export de `build.yml` est prêt localement mais sa publication a été refusée car l'autorisation publique visait le workflow exact de `c7dbce4`. L'étape distante reste conditionnée au message exact du commit de remise et ne peut pas être activée par un futur commit ordinaire ; ne pas relancer le run complet `31710676903`.
- Les ajouts postérieurs de cette procédure et de cet état ont eux aussi été refusés à la publication publique, l'autorisation visant exactement leurs versions dans `c7dbce4`. La version finale reste disponible localement et dans l'espace durable du propriétaire.

## 0.1 Périmètre fonctionnel livré après validation terrain v2.6.4

Le propriétaire confirme que la v2.6.4 libère enfin Test, Achat et Vente en Remote comme en Robot, avec une durée maximale observée d'environ 30 secondes. Ce cœur ne doit plus être réécrit.

La source v2.6.5/45 prépare uniquement :

- retrait du voile PIN qui gênait l'Accessibilité sous verrou simple ; le PIN peut être visible à l'écran mais reste masqué dans les journaux et absent du serveur ;
- entrée Remote → hall Robot sans autorisations ni élection, puis séquence autorisations → slot → liaison SIM → PIN → démarrage ;
- arrêt serveur avant suppression locale du profil ;
- remplacement explicite d'un Robot fantôme uniquement après seconde preuve de la même SIM physique ;
- mauvaise SIM, SIM absente ou autre empreinte : refus et ancien Robot préservé ;
- navigation initiale Rapports, Flux, Flotte, Robot et SAV, le moteur financier restant dans Flux ;
- test de mise à jour v2.6.4 → v2.6.5 et conservation des données sur API 23, 26, 30 et 36.

État de publication : le Worker v2.6.5 est déployé et l'APK permanente est prête. Aucune migration D1 n'a été créée ni appliquée.

Retours d'installation v2.6.4 à conserver : mise à jour réussie sous Android 8 ; désinstallation nécessaire sous Android 6.0.1 ; sous Android 11, installation v2.6.2 puis v2.6.4. La v2.6.5 ajoute donc un vrai scénario CI de mise à jour avec la même clé sur ces trois API et sur API 36/Android 16.

## 1. Résultat de la présente reprise

La v2.6.4 répare deux causes distinctes qui rendaient l'application vivante en apparence mais empêchaient toute prise de commande :

1. Android exigeait une route `PhoneAccount` parfaite avant le démarrage et le lease, alors que plusieurs dialers Android 6/8/11 ne publient cette information qu'au moment de l'appel.
2. La réparation d'un jeton appareil pouvait créer une nouvelle ligne D1 et laisser l'ancien appareil marqué Robot, ce qui attribuait la file à un propriétaire fantôme.

Le code Android et le Worker corrigés sont publiés. Le Worker `2.6.4-cloudflare` est en production. L'APK permanente v2.6.4 est produite, signée et vérifiée. Les tests prouvent le flux Remote distinct → Worker/D1 → Robot distinct et le lancement Android 11. Le propriétaire a ensuite validé sur le terrain Test, Achat et Vente en Remote et Robot, en 30 secondes au maximum. Cette validation vaut pour v2.6.4 ; la v2.6.5 devra répéter ces essais après livraison.

## 2. Références Git

- Dépôt : `Delor85/BlueAuto`
- Branche : `fix/blue-magic-v2-6-recovery`
- PR : `#4`, ouverte, non fusionnée
- Commit fonctionnel v2.6.4 : `381adc2`
- Correctifs du harnais Android 11 : `8826566`, `185fe41`, `5e42a0f`
- Commit d'autorisation unique production/export : `53806cb0db407185004a3812d57012bf50555b76`
- Le commit suivant retire les déclencheurs temporaires et publie cette documentation ; utiliser le HEAD de branche comme point de reprise.

Ne pas fusionner la PR avant la validation terrain explicite.

## 3. Version Android livrée

| Propriété | Valeur vérifiée dans l'APK |
|---|---|
| Fichier | `Blue-Magic-v2.6.4-Remote-Robot-Release.apk` |
| Taille | 111 323 octets |
| Paquet | `com.profitloop.blueauto` |
| `versionName` | `2.6.4` |
| `versionCode` | `44` |
| `minSdk` | `23` — Android 6.0 |
| `targetSdk` | `34` |
| Signatures | v1, v2 et v3 valides |
| Certificat | `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`, RSA 4096 |
| SHA-256 certificat | `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5` |
| SHA-256 APK | `76dcb157723da77aa68794c3a4f8ff9abc98c04e4f34388d17b98d0c9cc58e6b` |

Le certificat a été comparé directement avec les APK permanentes v2.5.3, v2.5.4, v2.6.0, v2.6.1 et v2.6.2 : il est identique. Installer par-dessus sans désinstaller. La v2.4.5 historique peut appartenir à une autre lignée : en cas de refus Android, ne pas désinstaller et relever la version exacte.

## 4. Production Cloudflare

- Worker : `blue-magic-api`
- URL : `https://blue-magic-api.mbolodelorpro.workers.dev`
- Version active : `2.6.4-cloudflare`
- Version Cloudflare : `ef561d4b-d46b-4644-b339-f3c0d730463b`
- Base D1 : `blue-magic`
- Santé vérifiée : `{"ok":true,"data":{"service":"blue-magic-api","version":"2.6.4-cloudflare","database":"online"}}`
- Workflow : déploiement Cloudflare `#4`, run `31683508389`, succès
- Migration : aucune ; `No migrations to apply!`

Le contrôle de santé situé immédiatement après le déploiement a brièvement obtenu l'ancienne version 2.6.2 pendant la propagation edge. Deux requêtes indépendantes non mises en cache ont ensuite confirmé 2.6.4 et D1 en ligne.

Seul le Worker Blue Magic a été déployé. Aucun autre Worker, aucune autre base et aucun secret n'ont été modifiés.

## 5. Export et signature

- Run d'export unique : `31683508357`
- Artefact temporaire : `Blue-Magic-v2.6.4-Internal-Resign`
- Identifiant artefact : `9174458793`
- ZIP : 99 300 octets
- Expiration GitHub : 14 août 2026
- Empreinte artefact : `sha256:fcefb80af9ff779930a7e06951e9f905ecee2370bb71ec137292cf394862552c`

L'APK interne n'est pas un livrable et ne doit pas être installée. Elle a été exportée une seule fois, débarrassée de son ancienne signature, puis re-signée avec le keystore permanent existant. Le mot de passe et le keystore ne figurent pas dans Git, la documentation ou les journaux.

Le déclencheur et le workflow de déploiement Cloudflare ont été supprimés après usage afin qu'aucune capacité de production persistante ne reste dans la branche. L'étape d'export interne a également été supprimée. Le workflow normal de build ne publie aucune APK permanente si les secrets permanents GitHub sont absents.

## 6. Corrections fonctionnelles v2.6.4

### 6.1 Côté Android

- La présence et l'identité de la SIM restent obligatoires avant lease.
- La route du dialer est résolue seulement avant composition.
- Un téléphone à une seule SIM active et attestée peut utiliser le dialer système même si le `PhoneAccount` n'est pas exposé tôt.
- Un téléphone multi-SIM ambigu échoue sans choisir arbitrairement une SIM.
- `TEST_NUMBER` reste disponible sans PIN ni Accessibilité.
- Les profils Robot mémorisés démarrent après le premier rendu de l'activité.
- Foreground Service : API 23–28 standard, API 29–33 `dataSync`, API 34+ `specialUse` avec repli.
- L'écran Remote affiche `ONLINE`, `OFFLINE` ou `STALE` et n'affirme plus une transmission si aucun Robot n'est prêt.

### 6.2 Côté Worker/D1

- `pair_device` accepte `replace_device_id` pour renouveler la même ligne appareil.
- Un profil migré peut récupérer la ligne correspondant à la même empreinte SIM vérifiée.
- Une ancienne ligne sans attestation SIM ne garde plus la propriété de la file.
- La même SIM peut récupérer un propriétaire silencieux depuis 15 minutes.
- Un Robot vivant reste prioritaire et ne peut pas être éjecté par un Remote.
- `preview_command` et `create_command` renvoient l'état réel du Robot.
- Les tests utilisent un jeton Remote et un jeton Robot différents.

## 7. Invariants préservés

- confirmation 1/2 avant toute création financière ;
- contrôle fournisseur, bénéficiaire et montant avant PIN ;
- PIN chiffré localement et jamais transmis au Worker/D1/JavaScript ;
- mauvais PIN : blocage du profil concerné, pas de nouvelle tentative automatique ;
- liaison nœud/SIM/slot contrôlée avant lease et composition ;
- FIFO, idempotence, lease atomique et annulation seulement avant location ;
- une opération composée sans preuve finale devient `UNKNOWN`, jamais rejouée automatiquement ;
- Remote distinct, Robot distinct et résultat suivi depuis les deux côtés ;
- multi-profils/multi-SIM : une SIM bloquée ne bloque pas les autres ;
- design bleu/or et WebView compatible Android 6 ;
- aucun « dernier appareil arrivé gagne ».

## 8. Tests et preuves

### Tests locaux

- `node app/src/test/finance-flow.mjs` : succès ;
- `node cloudflare/test/integration.mjs` via le script de contrôle : succès ;
- `git diff --check` : succès ;
- intégrité ZIP de l'APK : succès ;
- décodage APK : paquet/version/SDK confirmés ;
- `apksigner verify --verbose --print-certs` : v1/v2/v3 et certificat confirmés ;
- comparaison directe de la signature v2.5.3 à v2.6.4 : identique.

### GitHub Actions

- Run de référence `#167` : tous les jobs verts, y compris `android-11-launch`.
- Le test API 30 installe et ouvre l'APK proprement, injecte un profil Robot mémorisé, redémarre à froid, maintient le processus vivant et ne détecte aucun crash.
- Run d'autorisation/export `31683508357` : build Android et paquets serveur réussis ; export interne unique réussi.
- Run PR correspondant `31683512418` : aucun export interne sur l'événement PR.
- Run Cloudflare `31683508389` : tests, dry-run, migrations list, déploiement et santé réussis.

Les premiers essais du job Android 11 ont échoué dans le script CI, pas dans l'app : variable de mot de passe Gradle, shell `pipefail`, puis portée des variables entre commandes. Ces trois défauts du harnais ont été corrigés avant le run vert.

## 9. Ce que les tests prouvent et ne prouvent pas

### Prouvé

- Remote A crée et Robot B loue ; Remote A ne peut pas louer à sa place.
- Le Worker et l'APK parlent le même protocole 2.6.4.
- Réparation du jeton sans propriétaire fantôme.
- Récupération d'un profil migré par la même SIM attestée.
- FIFO, isolation des nœuds, expiration, annulation et états.
- Android 11/API 30 ouvre l'application et redémarre le Robot mémorisé sans crash.
- L'APK finale a la bonne version et la bonne signature permanente.

### Validé sur les téléphones Camtel du propriétaire pour v2.6.4

- Test, Achat et Vente en Remote comme en Robot ;
- communication entre téléphone Remote et téléphone Robot ;
- prise, composition et résultat en 30 secondes au maximum ;
- présentation réelle du dialogue USSD et insertion du PIN lorsque l'écran est déjà ouvert.

Ce retour ne prouve ni tous les dialers Android, ni la correction v2.6.5 sous verrou simple, ni la mise à jour directe sur Android 6/11. Il est interdit d'étendre une validation terrain à un modèle ou une version non essayé.

## 10. Test terrain obligatoire

1. Ne désinstaller aucune ancienne version permanente.
2. Après déploiement du Worker 2.6.5, installer l'APK permanente v2.6.5 par-dessus la v2.6.4.
3. Vérifier `2.6.5` et `versionCode 45` ; si la mise à jour échoue, ne pas désinstaller et relever le message exact.
4. Sur le Robot, vérifier le profil, la SIM physique et le slot, puis démarrer le Robot.
5. Sur un autre téléphone en Remote, vérifier `ONLINE`.
6. Lancer uniquement `TEST_NUMBER`.
7. Vérifier que le Remote obtient un identifiant et que le Robot prend la commande sous environ 10 secondes.
8. Vérifier que le Robot compose seulement `*825*3*3#` et que l'état remonte.
9. Répéter sur Android 6, 8, 11 et une version récente disponible.
10. Tester une finance jusqu'à `CONFIRMATION 1 SUR 2`, vérifier les deux numéros et le montant, puis choisir `ANNULER`.
11. Vérifier qu'aucune commande n'est créée après l'annulation.
12. Seulement après ces réussites, effectuer une transaction minimale supervisée.

Ne jamais appuyer plusieurs fois si une commande est `PENDING`, `LEASED`, `DIALING` ou `UNKNOWN`.

## 11. Diagnostic si rien ne se passe après confirmation

Relever dans cet ordre :

1. le texte exact affiché après confirmation ;
2. l'identifiant de commande, s'il existe ;
3. `ONLINE`, `OFFLINE` ou `STALE` ;
4. la notification du Robot ;
5. l'état D1 visible : `PENDING`, `LEASED`, `DIALING`, etc. ;
6. le profil et la SIM réellement sélectionnés sur le Robot ;
7. l'heure du dernier heartbeat ;
8. le dialogue ou SMS Camtel expurgé de tout PIN.

Interprétation :

- pas d'identifiant : échec avant `create_command` ;
- `PENDING` durable avec Robot `ONLINE` : propriété/lease à auditer ;
- `LEASED` sans composition : route dialer ou état verrouillé ;
- `DIALING`/`AWAITING_PIN` : ne jamais recréer la commande ;
- `UNKNOWN` : contrôler le solde ou les SMS Camtel avant toute nouvelle opération.

## 12. Périmètre du cahier des charges

Le trajet critique Robotique/transactions est la priorité livrée. Les cinq grands onglets ERP décrits dans le cahier maître ne sont pas tous achevés. Graphes avancés, CRM, KYC/GPS, Tchoronko, mercenaires, reporting comptable exhaustif et administration complète de la flotte restent des lots futurs.

Ne pas dégrader le trajet Remote→Robot pour ajouter ces modules. Chaque nouveau lot doit préserver les invariants financiers et ajouter ses propres tests.

## 13. Ce qui ne doit pas être modifié sans nouvelle preuve

- ne pas rétablir le prérequis de route `PhoneAccount` avant lease ;
- ne pas créer une nouvelle ligne appareil lors d'un simple renouvellement de jeton ;
- ne pas laisser un appareil sans SIM attestée posséder la file ;
- ne pas permettre à un Remote d'éjecter un Robot vivant ;
- ne pas créer une finance avant pression et confirmation ;
- ne pas rendre PIN/Accessibilité obligatoires pour `TEST_NUMBER` ;
- ne pas afficher le PIN dans l'interface Blue Magic, le transmettre ou le journaliser ; le champ système Camtel peut toutefois le montrer brièvement pendant l'insertion demandée ;
- ne pas rejouer automatiquement après composition ;
- ne pas changer de certificat Android ;
- ne pas désinstaller l'app de production pour contourner un échec de mise à jour ;
- ne pas redéployer Cloudflare, modifier D1 ou fusionner la PR sans autorisation explicite.

## 14. Point de reprise suivant

1. Lire `docs/PROCEDURE_REPRISE_EXTERNE.md` en entier.
2. Vérifier le HEAD de `fix/blue-magic-v2-6-recovery` et la PR `#4`.
3. Tant que la v2.6.5 n'est pas autorisée et publiée, vérifier `/api?action=health = 2.6.4-cloudflare` sans redéployer.
4. Contrôler que le déclencheur, le workflow de déploiement et l'export temporaire ont disparu.
5. Après livraison v2.6.5, commencer par la mise à jour sans désinstallation puis le test sans fonds sur deux téléphones distincts.
6. Documenter chaque résultat par version Android, modèle, SIM/slot, identifiant de commande et état final.
7. Ne fusionner qu'après validation terrain explicite.

Prochaine action autorisée : publier le code v2.6.5, exécuter la CI de mise à jour API 23/26/30, déployer le Worker 2.6.5 sans migration, puis produire l'APK permanente. Ensuite seulement, installer cette APK par-dessus la v2.6.4 et répéter `TEST_NUMBER`, Achat et Vente depuis un Remote distinct vers le Robot détenteur de la SIM.
