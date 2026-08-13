# ÉTAT DU PROJET — BLUE MAGIC v2.6.4

État vérifié le 13 août 2026. La reprise doit commencer ici puis continuer dans `docs/PROCEDURE_REPRISE_EXTERNE.md`, qui contient le cahier des charges synthétisé, l'historique complet, les causes de régression, la procédure et les limites terrain.

## 1. Résultat de la présente reprise

La v2.6.4 répare deux causes distinctes qui rendaient l'application vivante en apparence mais empêchaient toute prise de commande :

1. Android exigeait une route `PhoneAccount` parfaite avant le démarrage et le lease, alors que plusieurs dialers Android 6/8/11 ne publient cette information qu'au moment de l'appel.
2. La réparation d'un jeton appareil pouvait créer une nouvelle ligne D1 et laisser l'ancien appareil marqué Robot, ce qui attribuait la file à un propriétaire fantôme.

Le code Android et le Worker corrigés sont publiés. Le Worker `2.6.4-cloudflare` est en production. L'APK permanente v2.6.4 est produite, signée et vérifiée. Les tests prouvent le flux Remote distinct → Worker/D1 → Robot distinct et le lancement Android 11. Le dernier test Camtel sur deux téléphones physiques reste obligatoire.

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

### Non prouvé sans téléphone Camtel

- la présentation exacte du dialogue USSD par chaque dialer Android 6/8/11/récent ;
- la reconnaissance du texte Camtel actuel ;
- l'insertion du PIN dans le pop-up réel ;
- le résultat financier réel sur la SIM.

Il est interdit d'assimiler tests automatisés verts et validation d'argent réel.

## 10. Test terrain obligatoire

1. Ne désinstaller aucune ancienne version permanente.
2. Installer l'APK v2.6.4 par-dessus.
3. Vérifier `2.6.4` et `versionCode 44`.
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
- ne pas afficher, transmettre ou journaliser le PIN ;
- ne pas rejouer automatiquement après composition ;
- ne pas changer de certificat Android ;
- ne pas désinstaller l'app de production pour contourner un échec de mise à jour ;
- ne pas redéployer Cloudflare, modifier D1 ou fusionner la PR sans autorisation explicite.

## 14. Point de reprise suivant

1. Lire `docs/PROCEDURE_REPRISE_EXTERNE.md` en entier.
2. Vérifier le HEAD de `fix/blue-magic-v2-6-recovery` et la PR `#4`.
3. Vérifier `/api?action=health = 2.6.4-cloudflare` sans redéployer.
4. Contrôler que le déclencheur, le workflow de déploiement et l'export temporaire ont disparu.
5. Commencer par le test terrain sans fonds sur deux téléphones distincts.
6. Documenter chaque résultat par version Android, modèle, SIM/slot, identifiant de commande et état final.
7. Ne fusionner qu'après validation terrain explicite.

Prochaine action : installer l'APK v2.6.4 sans désinstaller, puis exécuter `TEST_NUMBER` depuis un Remote distinct vers le Robot détenteur de la SIM.
