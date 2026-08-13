# Procédure obligatoire de reprise externe — Blue Magic

Ce document permet à un autre développeur ou agent de reprendre Blue Magic sans dépendre de la conversation ChatGPT. Il décrit le trajet critique, les acquis à protéger, les causes de régression déjà identifiées, la compilation, le déploiement, les tests et la livraison.

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

Utiliser uniquement `.github/workflows/deploy-cloudflare.yml` sur la branche validée.

Le workflow doit :

1. installer Node 22 ;
2. exécuter tous les tests ;
3. générer la configuration D1 de production sans afficher l’identifiant ;
4. effectuer un dry-run ;
5. lister les migrations ;
6. appliquer uniquement les migrations additives en attente ;
7. déployer `blue-magic-api` ;
8. vérifier `/health`.

Avant le déploiement, confirmer :

- `PAIRING_SECRET` reste présent ;
- le binding D1 vise uniquement `blue-magic` ;
- aucune migration destructive n’existe ;
- les autres Workers et bases ne sont pas concernés.

Cette version ne nécessite aucune nouvelle migration D1.

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
