# Procédure obligatoire de reprise externe — Blue Magic

Ce document permet à un autre développeur ou agent de reprendre Blue Magic sans dépendre de la conversation ChatGPT. Il commence à la demande initiale, conserve les acquis des versions historiques, consigne les régressions et les blocages rencontrés, puis décrit le trajet critique, la compilation, le déploiement, les tests et la livraison.

Il est volontairement plus complet qu'une simple note de version. En cas de contradiction avec une réponse de conversation, le code publié, les preuves GitHub Actions, l'état Cloudflare et les limites écrites ici priment.

## 0. Résumé de la reprise v2.6.4 au 13 août 2026

- Le Worker de production `blue-magic-api` exécute `2.6.4-cloudflare` avec D1 `blue-magic` en ligne.
- L'APK permanente livrée est `Blue-Magic-v2.6.4-Remote-Robot-Release.apk`.
- Le paquet est `com.profitloop.blueauto`, `versionName 2.6.4`, `versionCode 44`, `minSdk 23` et `targetSdk 34`.
- Le certificat est identique à celui des APK permanentes v2.5.3, v2.5.4, v2.6.0, v2.6.1 et v2.6.2.
- Le SHA-256 de l'APK est `76dcb157723da77aa68794c3a4f8ff9abc98c04e4f34388d17b98d0c9cc58e6b`.
- Le flux Remote distinct vers Robot distinct, `TEST_NUMBER`, Achat, Approvisionnement et Vente sont couverts par les tests Android/JavaScript et Worker/D1.
- L'ouverture sous Android 11 et le redémarrage avec un profil Robot mémorisé sont prouvés par la CI sur API 30.
- Une transaction financière Camtel réelle n'est pas simulable dans GitHub Actions : le dernier verdict reste un test physique supervisé, d'abord sans fonds puis avec le montant minimal accepté.
- La PR `#4` reste ouverte et non fusionnée jusqu'à ce verdict terrain.

## Partie I — mémoire complète depuis le début du projet

### A. Sources utilisées pour reconstruire cette mémoire

La reprise a été reconstruite à partir de quatre sources, recoupées entre elles :

1. le cahier des charges fonctionnel maître de juillet 2026 ;
2. les anciens échanges fournis par le propriétaire, notamment les versions 2.4 à 2.6.3 ;
3. l'historique Git complet de `Delor85/BlueAuto` ;
4. les sources Android, Worker, migrations, tests et workflows réellement présents sur la branche.

Il ne faut jamais se fier uniquement au numéro affiché dans une ancienne réponse. Pour toute reprise, vérifier la version dans l'APK décodée, le certificat avec `apksigner`, le commit Git, le run CI et `/api?action=health`.

### B. Demande initiale et cahier des charges à conserver

#### B.1 Problème métier

Blue Magic doit supprimer la dépendance à une personne physiquement présente devant la Master SIM. La chaîne Camtel/Blue est hiérarchique :

```text
SIM nationale/régionale → DAE → DSM → PoS → client final
```

- Le DAE alimente ses DSM.
- Le DSM alimente ses PoS.
- Le PoS vend le crédit de communication au client final.
- Chaque niveau ne doit être alimenté que par son supérieur officiel.
- La pression opérationnelle existe 24 h/24 : sommeil, réunions, déplacements ou absence de réseau du responsable ne doivent plus arrêter la distribution.

#### B.2 Solution prioritaire demandée

Deux téléphones distincts doivent coopérer par Internet :

- le téléphone **Remote/Télécommande** crée et suit l'ordre ;
- le serveur joue la boîte aux lettres et l'unique source de vérité ;
- le téléphone **Robot**, qui détient la SIM réelle, prend l'ordre et compose l'USSD ;
- le résultat Camtel remonte jusqu'au Remote.

Le projet d'origine utilisait InfinityFree, `api.php` et SQLite. La production active a ensuite été migrée vers un Worker Cloudflare et D1, sans changer le principe de boîte aux lettres.

#### B.3 Contraintes non négociables du cahier des charges

- Android 6 et versions supérieures lorsque la plateforme Android le permet.
- Remote et Robot distincts, avec un ancien profil Hybride accepté en compatibilité de migration.
- multi-comptes, multi-rôles et multi-SIM sans mélange de PIN, de nœud ou de file ;
- file FIFO, lease atomique, idempotence et anti-double-exécution ;
- confirmation avant toute opération financière ;
- contrôle fournisseur, bénéficiaire et montant avant insertion du PIN ;
- PIN Camtel chiffré uniquement sur le téléphone Robot, jamais sur Internet ni dans D1 ;
- arrêt immédiat du profil en cas de mauvais PIN, sans trois tentatives automatiques ;
- test sans fonds indépendant du PIN financier ;
- service Robot persistant et économe, avec notification et gestion de la veille ;
- interface lisible bleu/or et fonctionnement des WebView anciennes ;
- coût d'exploitation minimal ;
- procédure détaillée permettant à un tiers de reprendre sans la conversation.

#### B.4 Périmètre ERP plus large demandé mais non entièrement livré

Le cahier maître décrit également cinq familles d'onglets : graphes/rapports, flux de crédit et preuve, flotte/cycle de vie, configuration/robotique, puis SAV/diagnostic. Il contient aussi des idées de comptes Tchoronko, mercenaires, CRM, KYC, GPS, audit de soldes, SMS et reporting comptable.

La priorité explicite était toutefois de rétablir d'abord l'interaction avec le téléphone Robot. La v2.6.4 livre et sécurise ce trajet critique. Elle ne doit pas être présentée comme l'ERP complet à cinq onglets. Les modules étendus doivent être planifiés séparément après validation terrain des opérations.

### C. Matrice du cahier des charges et état réel

| Exigence | État v2.6.4 | Preuve ou limite |
|---|---|---|
| Remote → serveur → Robot distinct | Implémenté et testé automatiquement | Le test Worker crée avec le jeton Remote A et loue uniquement avec le jeton Robot B. Validation physique encore requise. |
| Achat DSM/PoS | Implémenté | Prévisualisation, confirmation, création D1, lease, contrôles et états testés ; Camtel réel à valider. |
| Approvisionnement DAE→DSM / DSM→PoS | Implémenté | Hiérarchie, numéros officiels et montant contrôlés ; Camtel réel à valider. |
| Vente PoS→client | Implémenté | Réservée au rôle PoS ; destinataire externe et montant contrôlés ; Camtel réel à valider. |
| Test sans fonds `*825*3*3#` | Implémenté | Ne dépend ni du PIN ni de l'Accessibilité ; à exécuter en premier sur le terrain. |
| Confirmation 1/2 | Acquis | Aucun ordre financier n'est créé avant confirmation. |
| Contrôle du pop-up Camtel 2/2 | Implémenté défensivement | L'Accessibilité exige les mêmes numéros et le même montant ; toute variation non reconnue échoue sans PIN. Dépend du dialer du fabricant. |
| PIN local uniquement | Acquis | Android Keystore/chiffrement local ; Worker et D1 ne le reçoivent pas. |
| Anti-mauvais PIN | Acquis | Un mauvais PIN bloque le profil concerné ; les autres SIM/profils continuent. |
| FIFO, lease, idempotence | Acquis | Tests D1/Miniflare, expiration, annulation avant lease et absence de rejeu après composition. |
| Liaison à la SIM physique et au slot | Acquis | Attestation avant activation, lease et composition. |
| Multi-SIM et multi-comptes | Implémenté et testé au niveau logiciel | Validation recommandée sur chaque fabricant/dialer réel. |
| Remote ne remplace pas un Robot vivant | Acquis | `ROBOT_ALREADY_ACTIVE`; transfert uniquement après arrêt explicite ou récupération prouvée par la même SIM devenue silencieuse. |
| Android 6+ | Paramétré et partiellement prouvé | `minSdk 23`; anciens appareils Android 6/8 ont ouvert l'app ; API 30 prouvée par émulateur ; chaque téléphone terrain reste à tester. |
| Robot après veille/redémarrage | Implémenté | Foreground Service, watchdog et réveil ; après redémarrage complet, Android peut exiger un premier déverrouillage. |
| Cinq onglets ERP complets | Non livré | Hors trajet critique de la v2.6.4 ; ne pas annoncer comme acquis. |
| Reporting, KYC, CRM, Tchoronko, mercenaires | Non livré ou seulement présent dans le cahier | À traiter dans des lots futurs après validation financière. |

### D. Chronologie technique et leçons des versions

#### D.1 Premiers essais et reconstruction v2

Le dépôt contient de nombreux premiers commits Android, SMS et Accessibilité, puis une suppression/reconstruction. Le commit `2e82396` a rétabli un noyau Robot v2 propre : Android/WebView, backend, distribution et pipeline CI.

Les v2.1 à v2.3 ont ajouté successivement :

- PIN automatisé, multi-SIM et multi-comptes ;
- durcissement de l'isolement des Robots et des PIN ;
- pause des profils verrouillés, sérialisation multi-SIM et file d'attente.

Acquis à conserver : un profil défaillant ne doit pas arrêter les autres, et une SIM ne doit jamais exécuter deux sessions USSD simultanées.

#### D.2 Série v2.4 — Remote, appairage, veille et verrouillage

- **v2.4** : réparation de l'appairage et remise en attente du Robot sous Android 6.
- **v2.4.1** : protection du mode Remote et isolation des files multi-SIM.
- **v2.4.2** : conservation des preuves en attente sans bloquer les autres SIM ; meilleure synchronisation Remote/Robot et annulation.
- **v2.4.3** : service persistant et watchdog sans garder l'écran allumé.
- **v2.4.4** : renouvellement automatique d'un jeton appareil D1 invalide.
- **v2.4.5** : retrait de l'overlay applicatif et réveil de la surface USSD système pour préserver Remote, FIFO, multi-SIM et compatibilité Android 6.

Limite découverte : `TelephonyManager.sendUssdRequest()` n'est disponible qu'à partir d'Android 8 et ne résout pas universellement les dialogues interactifs Camtel. La voie retenue combine composition système, Accessibilité et échec fermé. Aucun code Android ne peut contourner légalement et universellement un verrou sécurisé du téléphone.

#### D.3 Série v2.5 — routage SIM et sûreté financière

- **v2.5.0** : durcissement du routage SIM et contrôle de l'intégrité financière.
- **v2.5.1** : repli Android 6 sur une seule SIM vérifiée et gestion du verrou simple.
- **v2.5.2 à v2.5.4** : récupération des profils migrés, lignée de signature permanente, diagnostics d'appairage et affichage explicite des erreurs.

Une régression s'est installée : la recherche d'une route `PhoneAccount` parfaite a progressivement été traitée comme condition de démarrage du Robot. Sur plusieurs dialers, cette métadonnée n'existe pas avant l'appel réel. L'interface restait vivante, mais le Robot ne louait plus les commandes.

#### D.4 Série v2.6 avant la présente reprise

- **v2.6.0** : tentative de restauration du flux Robot et de la récupération.
- **v2.6.1** : restauration de la finance Android 6 et confirmation financière signée côté Worker.
- **v2.6.2** : Worker financier correspondant déployé, boutons financiers réparés et protection du Robot actif contre le « dernier appareil arrivé ».
- **v2.6.3** : suppression du blocage de route parfaite avant démarrage/lease. Une APK a été produite, mais le problème Remote→Robot n'était pas encore éliminé et Android 11 n'était pas prouvé.

Le point positif majeur de v2.6.3 à préserver est la distinction suivante : **vérifier la SIM avant le lease, résoudre la route Téléphone seulement au moment de composer**.

### E. Journal complet de ce chat de reprise v2.6.4

#### E.1 État signalé par le propriétaire

Au début de cette reprise :

- les boutons répondaient ;
- `CONFIRMATION 1 SUR 2` apparaissait ;
- après confirmation, Achat, Vente et Test n'aboutissaient pas ;
- le Remote ne commandait pas le Robot ;
- l'application s'ouvrait sous Android 6 et 8 mais pas sous Android 11 ;
- la réflexion précédente avait été interrompue avant une livraison complète.

Cette description a été traitée comme une rupture de la chaîne après l'interface, pas comme un simple problème de bouton.

#### E.2 Audits exécutés

La reprise a :

1. relu les anciens échanges fournis et le cahier des charges maître ;
2. audité l'historique Git et comparé les acquis v2.4.5, v2.5 et v2.6 ;
3. inspecté Android, Worker, D1, tests et workflows ;
4. vérifié l'ancien état de production, alors encore en `2.6.2-cloudflare` ;
5. reproduit les flux avec deux identités appareils réellement distinctes ;
6. ajouté des tests de réparation de jeton, propriétaire fantôme et profil migré ;
7. ajouté un démarrage réel d'APK sous émulateur Android 11/API 30.

#### E.3 Deux causes racines cumulatives

**Cause Android — route exigée trop tôt :** les versions 2.5/2.6 exigeaient une « route d'appel parfaite » avant de démarrer le Robot et avant de louer une commande. Sur Android 6/8/11, plusieurs dialers ne l'exposent qu'au moment de l'appel. Le Robot paraissait actif, mais ne prenait rien.

**Cause Worker — propriétaire Robot fantôme :** lors d'une réparation de jeton, `pair_device` pouvait créer une nouvelle ligne appareil et laisser l'ancienne ligne avec `robot_enabled = 1`. D1 attribuait la file à l'ancien identifiant silencieux. Le vrai téléphone affichait Robot, mais le serveur attendait un appareil disparu.

Ces causes expliquent pourquoi une correction uniquement visuelle, une correction uniquement Android ou un test avec le même jeton des deux côtés ne suffisait pas.

#### E.4 Corrections v2.6.4

- Le Robot démarre et loue après vérification de la SIM, sans attendre une route `PhoneAccount` prématurée.
- La route exacte est résolue juste avant la composition ; le repli dialer n'est permis que pour une seule SIM physiquement vérifiée.
- La réparation du jeton cible la même ligne par `replace_device_id`.
- Un profil migré peut retrouver son appareil par l'empreinte de la même SIM attestée.
- Un propriétaire fantôme non attesté ne bloque plus la file.
- Un Robot de la même SIM silencieux depuis 15 minutes peut être récupéré, mais un Robot vivant reste prioritaire.
- Le Remote reçoit `robot_ready`, `robot_status`, le dernier passage et un message honnête.
- L'interface n'annonce plus « transmise au Robot » si le Robot est hors ligne.
- Le test d'intégration utilise un Remote A et un Robot B distincts.
- Le service de premier plan utilise les types compatibles API 23–28, 29–33 et 34+.
- Le démarrage automatique du Robot mémorisé se fait après le premier rendu de l'activité.

#### E.5 Tests et incidents de CI

Les tests locaux `finance-flow.mjs` et `cloudflare/test/integration.mjs` ont réussi. Le premier ajout du test Android 11 a rencontré trois défauts du **script CI**, pas trois crashs de l'application : mot de passe de signature non transmis à Gradle, `pipefail` utilisé avec un shell non compatible, puis variables non persistantes entre lignes d'émulateur. Les commits `8826566`, `185fe41` et `5e42a0f` ont corrigé ce harnais.

Le run final antérieur `#167` a alors réellement : installé l'APK sur API 30, ouvert une installation propre, injecté un profil Robot mémorisé, redémarré à froid, conservé le processus vivant et confirmé l'absence de crash.

#### E.6 Autorisation et déploiement de production

Le propriétaire a explicitement autorisé le déploiement du Worker v2.6.4 et l'export temporaire de l'APK interne pour re-signature permanente.

Pour borner cette autorisation :

- un déclencheur unique lié au message exact du commit `53806cb` a été ajouté ;
- l'export APK n'était actif que pour ce commit ;
- aucune étape de migration D1 n'a été exécutée, car v2.6.4 n'en nécessite aucune ;
- le workflow a seulement listé les migrations, obtenu `No migrations to apply!`, puis déployé le Worker concerné ;
- les déclencheurs temporaires ont ensuite été retirés du dépôt.

Le workflow Cloudflare `#4`, run `31683508389`, a réussi. Version Cloudflare : `ef561d4b-d46b-4644-b339-f3c0d730463b`. Le contrôle de santé immédiat du workflow a brièvement lu l'ancienne version en raison de la propagation edge. Deux contrôles indépendants avec URL non mise en cache ont ensuite confirmé :

```json
{"ok":true,"data":{"service":"blue-magic-api","version":"2.6.4-cloudflare","database":"online"}}
```

#### E.7 Export, re-signature et vérification de l'APK

- Run d'export : `31683508357`.
- Artefact temporaire : `Blue-Magic-v2.6.4-Internal-Resign`, identifiant `9174458793`, ZIP de 99 300 octets.
- L'APK interne a été utilisée uniquement comme matériau de re-signature.
- Les anciennes entrées de signature ont été retirées avant signature.
- Signature finale v1/v2/v3 avec la clé permanente, RSA 4096.
- Certificat : `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`.
- Empreinte certificat : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`.
- Taille finale : 111 323 octets.
- SHA-256 final : `76dcb157723da77aa68794c3a4f8ff9abc98c04e4f34388d17b98d0c9cc58e6b`.
- Intégrité ZIP/APK : aucune erreur.
- Valeurs vérifiées après décodage : paquet, version 2.6.4/44, minSdk 23, targetSdk 34.
- Certificat comparé directement et identique aux APK v2.5.3, v2.5.4, v2.6.0, v2.6.1 et v2.6.2.

### F. Avancées, acquis, problèmes et blocages pour la relève

#### F.1 Acquis techniques

- Production Worker et application sont enfin au même protocole v2.6.4.
- Les deux causes du silence Remote/Robot sont corrigées dans le code et couvertes par tests.
- Android 11 n'est plus une affirmation basée sur `minSdk` : un lancement API 30 est exécuté en CI.
- Le certificat permanent et la possibilité de mise à jour directe sont prouvés pour la lignée v2.5.3+.
- La procédure de diagnostic distingue interface, création D1, lease, composition, PIN et résultat.
- Les mécanismes financiers positifs des v2.4.5 à v2.6.2 sont conservés.

#### F.2 Blocages qui ne peuvent pas être levés à distance

- GitHub Actions n'a ni SIM Camtel, ni dialer fabricant, ni réseau radio : il ne peut pas prouver une opération réelle.
- Les dialogues USSD interactifs ne sont pas standardisés entre Android 6, 8, 11 et les surcouches Samsung/Tecno/Xiaomi.
- Un écran protégé par un verrou Android sécurisé peut empêcher l'Accessibilité d'agir ; Blue Magic doit échouer sans PIN, jamais contourner ce verrou.
- Le texte Camtel peut changer. Une différence de fournisseur, bénéficiaire ou montant doit bloquer la transaction jusqu'à mise à jour contrôlée des règles.

#### F.3 Règle de communication honnête

Ne jamais écrire « toutes les opérations fonctionnent en production » avant le test physique. La formulation correcte est : le code, D1, le Worker, la liaison Remote/Robot et le lancement Android 11 sont réparés et testés automatiquement ; la dernière preuve Camtel sur téléphone réel reste obligatoire.

## Partie II — procédure technique permanente

## 1. Dépôt et état de départ

- Dépôt : `Delor85/BlueAuto`
- Branche de travail : `fix/blue-magic-v2-6-recovery`
- PR : `#4`, à conserver ouverte et non fusionnée jusqu’à validation terrain
- Application Android : `com.profitloop.blueauto`
- Version de cette reprise : `2.6.4`, `versionCode 44`
- Android minimum : API 23, Android 6.0
- Android cible de compilation : API 34
- Worker attendu après déploiement de cette version : `2.6.4-cloudflare`
- Base : D1 `blue-magic`
- Point de santé : `GET /api?action=health`

Toujours commencer par :

```bash
git status --short --branch
git log --oneline -10
git diff --check
```

Ne jamais travailler directement sur `main`, ne jamais fusionner la PR avant les tests terrain et ne jamais désinstaller l’application d’un téléphone de production pour effectuer une mise à jour.

## 2. Objectif fonctionnel non négociable

Le système doit exécuter cette chaîne, sans raccourci :

1. Un utilisateur ouvre Blue Magic sur un téléphone Remote ou Robot.
2. Il demande Achat, Approvisionnement, Vente ou Test.
3. Pour une finance, le Worker calcule les numéros officiels et le montant.
4. L’application affiche `CONFIRMATION 1 SUR 2`.
5. Après confirmation seulement, le Worker insère une commande `PENDING` dans D1.
6. Le téléphone Robot élu pour le nœud fournisseur interroge le Worker.
7. Le Worker loue la commande uniquement à ce Robot.
8. Le Robot vérifie encore la SIM physique, le slot, le nœud, les numéros, le montant et l’intégrité.
9. Le Robot compose l’USSD.
10. Pour une finance, le service d’accessibilité vérifie le pop-up Camtel avant d’insérer le PIN local.
11. Le résultat opérateur est renvoyé au Worker et visible sur le Remote.

Une confirmation qui apparaît sans création D1, ou une création D1 sans location par le Robot, est une panne. Un bouton actif ou un test unitaire vert ne suffit jamais à déclarer cette chaîne opérationnelle.

## 3. Architecture

### Android

- `MainActivity.java` : appairage, profils, écran de gestion, WebView embarquée et pont JavaScript.
- `app/src/main/assets/app.js` : boutons, prévisualisation, confirmation 1/2, création et affichage des commandes.
- `ApiClient.java` : HTTPS, jeton appareil, réparation d’authentification et appels API.
- `RobotService.java` : heartbeat, polling FIFO, lease, composition et synchronisation.
- `SimIdentityManager.java` : attestation de la SIM physique liée au profil.
- `SimCallManager.java` : résolution du compte Téléphone et composition USSD.
- `UssdCommandFactory.java` : reconstruction et contrôle de l’ordre loué.
- `BlueAccessibilityService.java` : contrôle du dialogue Camtel, insertion PIN et clic de validation.
- `PendingCommandStore.java` : état local par profil/SIM.

### Cloudflare

- `cloudflare/src/index.js` : API unique.
- `cloudflare/migrations/0001_initial.sql` : nœuds, appareils, commandes et événements.
- `cloudflare/migrations/0002_robot_sim_attestation.sql` : attestation et slot SIM.
- `cloudflare/test/integration.mjs` : test D1/Miniflare du flux complet.
- `cloudflare/wrangler.jsonc` et fichier de production généré : Worker, assets et binding D1.

### États d’une commande

```text
PENDING
  → LEASED
  → DIALING
  → AWAITING_PIN        (finance)
  → PIN_SUBMITTED       (finance)
  → AWAITING_RESULT
  → SUCCEEDED | FAILED | UNKNOWN | BLOCKED
```

`CANCELLED` est permis uniquement avant la location. Un ordre composé mais sans preuve finale devient `UNKNOWN`, jamais automatiquement rejoué.

## 4. Causes déjà identifiées

### 4.1 Route d’appel exigée trop tôt

Les versions 2.5/2.6.2 pouvaient exiger une correspondance parfaite entre slot SIM et `PhoneAccount` avant même de démarrer le Robot ou de louer une commande. Plusieurs dialers Android 6, 8 et 11 ne publient ces informations qu’au moment de l’appel. Le Robot paraissait actif mais ne prenait aucune commande.

Correction à préserver :

- vérifier la présence et l’identité de la SIM avant le lease ;
- résoudre la route Téléphone seulement juste avant la composition ;
- utiliser le compte exact lorsqu’il est disponible ;
- sur une seule SIM active et physiquement vérifiée, permettre le dialer système par défaut ;
- ne jamais choisir arbitrairement une SIM sur un téléphone réellement ambigu.

### 4.2 Propriétaire Robot fantôme

L’ancienne réparation d’un jeton appelait `pair_device`, qui créait une nouvelle ligne `devices`. L’ancienne ligne pouvait conserver `robot_enabled = 1`. Le nouveau téléphone affichait localement Robot actif, mais le Worker réservait la file à un appareil qui n’existait plus.

Correction v2.6.4 à préserver :

- l’application transmet `replace_device_id` lors d’une réparation ;
- le Worker renouvelle le jeton de la même ligne appareil ;
- si un ancien profil Android ne connaît plus cet identifiant, le Worker retrouve cette ligne
  grâce à l’empreinte de la SIM vérifiée, au lieu de créer un second propriétaire ;
- un propriétaire historique sans attestation SIM valide ne bloque plus la file ;
- un propriétaire de la même SIM devenu silencieux depuis 15 minutes peut être libéré par le téléphone qui prouve cette même SIM ;
- un Robot vivant reste prioritaire ;
- un Remote sans la SIM physique ne peut pas devenir Robot ni évincer l’existant.

### 4.3 Tests trop superficiels

Un ancien test utilisait souvent le même appareil logique pour créer puis louer. Cela ne prouvait pas la communication Remote/Robot.

Le test obligatoire doit utiliser :

- jeton A : appareil `REMOTE` ;
- jeton B : appareil `ROBOT` du même nœud, avec SIM attestée ;
- création avec A ;
- lease avec B ;
- impossibilité de lease avec A ;
- états de commande visibles depuis A.

### 4.4 Démarrage Android 11

Un profil Robot mémorisé redémarre le service lorsque l’activité reprend. Les types de service de premier plan introduits sur Android 14 ne doivent pas fermer le processus sur Android 10/11.

Correction à préserver :

- API 23–28 : `startForeground(id, notification)` ;
- API 29–33 : type `dataSync` ;
- API 34+ : type `specialUse`, avec repli `dataSync` ;
- démarrage automatique après rendu initial de l’activité ;
- test émulateur API 30 avec un premier démarrage propre puis un profil Robot mémorisé.

## 5. Invariants de sécurité et d’usage

Ne pas modifier sans une preuve et un test dédiés :

- le PIN reste chiffré localement et n’est jamais envoyé au Worker, à D1 ou au JavaScript ;
- la confirmation 1/2 reste obligatoire pour toute finance ;
- `TEST_NUMBER` reste indépendant du PIN et de l’Accessibilité ;
- la SIM physique est contrôlée avant lease et avant composition ;
- le numéro fournisseur, le numéro bénéficiaire et le montant sont contrôlés avant PIN ;
- un Remote ne peut pas éjecter un Robot vivant ;
- une SIM/nœud bloqué ne bloque pas les autres profils du téléphone ;
- une seule session USSD est ouverte à la fois par téléphone ;
- aucune répétition automatique après `DIALING` en cas de résultat inconnu ;
- la signature Android permanente ne change pas ;
- le design bleu/or et la compatibilité WebView Android 6 restent présents.

## 6. API utile

Les actions sont envoyées sur `/api?action=<action>` en JSON.

- `health` : version Worker et état D1.
- `pair_device` : nouvel appareil ou renouvellement ciblé avec `replace_device_id`.
- `heartbeat` : présence, mode et attestation SIM.
- `activate_robot` : tentative explicite de devenir Robot.
- `update_device_mode` : Remote ou Robot.
- `preview_command` : résolution officielle et empreinte de confirmation.
- `create_command` : création D1 idempotente.
- `lease_command` : location par le Robot élu.
- `release_command` : retour en file avant composition.
- `cancel_command` : annulation d’une commande encore `PENDING`.
- `command_event` : progression ou résultat.
- `command_status` : suivi depuis Remote ou Robot autorisé.

`preview_command` et `create_command` renvoient aussi :

- `robot_ready` ;
- `robot_status` : `ONLINE`, `OFFLINE` ou `STALE` ;
- `robot_last_seen_at` ;
- `robot_message`.

L’interface ne doit jamais afficher « transmise au Robot » lorsque `robot_ready` vaut `false`.

## 7. Tests locaux

Depuis la racine :

```bash
git diff --check
node app/src/test/finance-flow.mjs
npm --prefix cloudflare ci
npm --prefix cloudflare run check
```

Le test Cloudflare doit prouver au minimum :

- appairage hiérarchique DAE/DSM/PoS ;
- Remote distinct vers Robot distinct ;
- `TEST_NUMBER` ;
- prévisualisation et confirmation financière ;
- FIFO et isolation de deux nœuds ;
- expiration sans double exécution ;
- refus d’un second Robot vivant ;
- transfert après arrêt explicite ;
- renouvellement du même appareil sans propriétaire fantôme ;
- ancien jeton refusé et nouveau jeton opérationnel.

## 8. Compilation Android

La CI utilise Java 17 et Gradle 8.2.

Le keystore permanent n’est pas dans le dépôt. Pour une compilation locale autorisée :

1. placer le keystore hors du dépôt ;
2. fournir son mot de passe par variable de processus protégée ;
3. ne jamais afficher le mot de passe ;
4. compiler `:app:testDebugUnitTest :app:assembleDebug` ;
5. vérifier le certificat avant livraison.

Une APK temporaire signée par une clé CI ne doit jamais être installée ni livrée.

## 9. Test Android 11 obligatoire

Le workflow `Build Blue Magic APK` contient le job `android-11-launch` :

1. il compile une APK éphémère ;
2. démarre un émulateur API 30 ;
3. installe et ouvre l’application sans profil ;
4. vérifie que l’activité reste vivante ;
5. injecte un profil Robot mémorisé de test ;
6. redémarre l’activité ;
7. vérifie que le processus reste vivant et qu’aucun crash du paquet n’apparaît.

Ce job ne prouve pas un USSD Camtel réel. Il prouve le démarrage Android 11 et le chemin du service. Le terrain doit encore valider les dialers des fabricants.

## 10. Déploiement Cloudflare

Le workflow ponctuel ayant servi à la remise v2.6.4 a été supprimé après usage. Le dépôt final ne conserve donc aucune capacité dormante de redéploiement en production. Pour un futur déploiement, obtenir d'abord une nouvelle autorisation explicite, puis recréer un workflow strictement borné sur une branche validée.

Ce workflow ponctuel doit :

1. installer Node 22 ;
2. exécuter tous les tests ;
3. générer la configuration D1 de production sans afficher l’identifiant ;
4. effectuer un dry-run ;
5. lister les migrations ;
6. arrêter le déploiement si une migration apparaît ; son application exige une autorisation séparée et une procédure dédiée ;
7. déployer `blue-magic-api` uniquement lorsqu'aucune migration n'est en attente ;
8. vérifier `/health`.

Avant le déploiement, confirmer :

- `PAIRING_SECRET` reste présent ;
- le binding D1 vise uniquement `blue-magic` ;
- aucune migration destructive n’existe ;
- les autres Workers et bases ne sont pas concernés.

Cette version ne nécessite aucune nouvelle migration D1.

### Déploiement v2.6.4 effectivement réalisé

- Autorisation explicite reçue le 13 août 2026.
- Commit borné : `53806cb0db407185004a3812d57012bf50555b76`.
- Run Cloudflare : `31683508389`, conclusion `success`.
- Tests, dry-run, liste des migrations, déploiement et santé exécutés.
- Réponse migrations : `No migrations to apply!` ; aucune migration n'a été appliquée.
- Seul le Worker `blue-magic-api` a été déployé.
- Version Cloudflare : `ef561d4b-d46b-4644-b339-f3c0d730463b`.
- Santé indépendante après propagation : `2.6.4-cloudflare`, base `online`.
- Le déclencheur, le workflow de déploiement et l'étape d'export APK temporaires ont été retirés immédiatement après la livraison.

## 11. Vérification et signature APK

Pour chaque APK livrée, relever :

- nom de fichier ;
- taille ;
- paquet ;
- `versionName` ;
- `versionCode` ;
- `minSdk` et `targetSdk` ;
- schémas de signature v1/v2/v3 ;
- empreinte SHA-256 du certificat ;
- SHA-256 du fichier.

Empreinte attendue du certificat permanent Blue Magic :

```text
f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5
```

L’installation doit se faire par-dessus la version permanente précédente, sans désinstallation. Une v2.4.5 historique peut appartenir à une autre lignée de signature : si Android refuse, arrêter et relever la version ; ne pas supprimer les données.

### APK v2.6.4 effectivement vérifiée

| Contrôle | Valeur |
|---|---|
| Fichier | `Blue-Magic-v2.6.4-Remote-Robot-Release.apk` |
| Taille | 111 323 octets |
| Paquet | `com.profitloop.blueauto` |
| Version | `2.6.4` / `versionCode 44` |
| Android | `minSdk 23` / `targetSdk 34` |
| Signatures | v1, v2 et v3 valides |
| Certificat | `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`, RSA 4096 |
| SHA-256 certificat | `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5` |
| SHA-256 APK | `76dcb157723da77aa68794c3a4f8ff9abc98c04e4f34388d17b98d0c9cc58e6b` |

Le certificat a été comparé directement avec v2.5.3, v2.5.4, v2.6.0, v2.6.1 et v2.6.2 : correspondance exacte. L'installation par-dessus ces versions est donc la voie prévue. Pour v2.4.5 ou une APK inconnue, ne jamais désinstaller en cas de refus : relever d'abord la version et la signature.

## 12. Test terrain sans fonds

Ordre obligatoire :

1. installer l’APK sans désinstaller ;
2. confirmer `2.6.4 • versionCode 44` ;
3. ouvrir le téléphone Robot et vérifier la SIM/slot ;
4. démarrer le Robot ;
5. depuis un autre téléphone Remote, lancer seulement `TEST_NUMBER` ;
6. vérifier `ONLINE` côté Remote ;
7. vérifier la prise en moins de 10 secondes ;
8. vérifier uniquement `*825*3*3#` sur le Robot ;
9. recommencer sur Android 6, 8, 11 et un Android récent disponible ;
10. pour une finance, aller jusqu’à la confirmation 1/2 puis choisir `ANNULER` ;
11. aucune commande ne doit être créée après l’annulation ;
12. une transaction minimale supervisée n’est permise qu’après ces réussites.

## 13. Diagnostic de terrain

Si la confirmation apparaît mais rien ne suit :

1. noter le texte affiché après confirmation ;
2. vérifier si un identifiant de commande apparaît ;
3. relever `ONLINE`, `OFFLINE` ou `STALE` ;
4. regarder la notification du Robot ;
5. ne pas appuyer plusieurs fois ;
6. si l’ordre est `PENDING`, ne pas le recréer ;
7. vérifier le téléphone propriétaire de la SIM et redémarrer son Robot ;
8. relever le statut après 10 secondes.

Si Android 11 ne s’ouvre pas :

```bash
adb shell am force-stop com.profitloop.blueauto
adb logcat -c
adb shell am start -W -n com.profitloop.blueauto/.MainActivity
adb logcat -d -b crash
adb logcat -d | grep -iE 'blueauto|blue magic|FATAL EXCEPTION|ForegroundService'
```

Fournir la trace depuis `FATAL EXCEPTION` jusqu’au dernier `Caused by`, sans secret ni PIN.

## 14. Retour arrière

Le retour arrière serveur doit se faire par commit Git identifié, jamais par modification manuelle non tracée. Avant tout rollback :

- arrêter les tests financiers ;
- vérifier les commandes `PENDING`, `LEASED`, `DIALING` et `UNKNOWN` ;
- ne jamais rejouer automatiquement un ordre déjà composé ;
- conserver D1 ;
- déployer le dernier Worker validé ;
- vérifier `/health`.

Un rollback APK n’est possible que vers une version de même signature et de `versionCode` compatible. Android refuse normalement une baisse de `versionCode` sans désinstallation ; ne pas forcer sur un téléphone contenant des profils utiles.

## 15. Critère de livraison

La livraison n’est terminée que si :

- le code est commité et publié sur la branche ;
- la PR reste dans l’état demandé ;
- les tests Android, Worker et Android 11 sont verts ;
- le Worker correspondant est déployé et `/health` donne la bonne version ;
- l’APK permanente est signée et vérifiée ;
- le SHA-256 est communiqué ;
- `docs/PROJECT_STATE.md` est actualisé ;
- le test terrain est distingué honnêtement des tests automatisés.

Le système ne doit être déclaré opérationnel avec argent réel qu’après validation Camtel sur les téléphones du terrain.

### État de ces critères pour v2.6.4

- code v2.6.4 publié sur la branche : oui ;
- PR ouverte et non fusionnée : oui ;
- tests Android/Worker et preuve Android 11 : oui ;
- Worker v2.6.4 en production et D1 en ligne : oui ;
- APK permanente signée, décodée et vérifiée : oui ;
- procédure et état du projet actualisés : oui ;
- test sans fonds sur deux téléphones physiques : à faire par le propriétaire ;
- opération Camtel minimale supervisée : à faire uniquement après réussite du test sans fonds.
