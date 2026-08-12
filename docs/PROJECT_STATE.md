# ÉTAT DU PROJET APRÈS CETTE ÉTAPE

État vérifié le 12 août 2026. Ce document est la source de reprise obligatoire avec `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`.

**Version :**
2.6.1 — restauration du flux financier Android 6, validation terrain encore obligatoire.

**Branche :**
`fix/blue-magic-v2-6-recovery`

**Commit :**
`3577a530e8f768535e444e71f4d1cec381d56c8b` pour le dernier état code/tests publié. Le commit contenant le présent document constitue le HEAD documentaire suivant.

**État GitHub :**
Branche publiée. PR non brouillon, ouverte, fusionnable sans conflit et non fusionnée. La PR #3 historique reste distincte.

**PR :**
PR #4 : https://github.com/Delor85/BlueAuto/pull/4 — titre mis à jour pour la v2.6.1.

**GitHub Actions :**
- push #129 et PR #130 : succès sur le premier commit v2.6.1 ;
- push #131 et PR #132 : succès du circuit temporaire contrôlé ayant fourni l’APK intermédiaire, ensuite re-signée hors GitHub ;
- push #133 et PR #134 : succès après retrait immédiat de la publication temporaire ;
- push #137 et PR #138 : succès final du code et du test qui exige la confirmation financière signée ;
- jobs réussis : `server-packages`, `android-debug-apk` et contrôle `android-permanent-apk` ;
- l’environnement GitHub `production` ne contient toujours pas les deux secrets Android permanents. Le job le signale et ne publie aucune APK de mauvaise signature.

**État Cloudflare :**
Production vérifiée mais non modifiée par cette étape. `/health` répond correctement avec la version encore déployée `2.3.1-cloudflare`. Le Worker v2.6.1 doit être déployé avant tout test Achat/Vente de la nouvelle APK.

**Worker :**
`blue-magic-api` — `https://blue-magic-api.mbolodelorpro.workers.dev` — production actuelle `2.3.1-cloudflare`; source prête `2.6.1-cloudflare`.

**D1 :**
Base distante `blue-magic` signalée `online` par le Worker de production. Aucun enregistrement distant n’a été modifié pendant cette livraison.

**Migrations :**
Aucune migration créée ou modifiée. Aucune migration distante appliquée pendant cette livraison.

**APK :**
`Blue-Magic-v2.6.1-Finance-Flow-Release.apk` — 107330 octets — livrable durable `/Blue-Magic-v2.6.1-Finance-Flow-Release.apk`.

**Version / versionCode :**
`2.6.1` / `41` ; paquet `com.profitloop.blueauto` ; Android minimum 6.0 conservé.

**Signature :**
Certificat permanent `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`, RSA 4096. Empreinte certificat SHA-256 `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`. Vérification `apksigner` réussie en v1, v2 et v3. Paquet et certificat identiques à la v2.6.0 ; versionCode 41 supérieur à 40 : mise à jour directe depuis v2.6.0. Même lignée que v2.5.3/v2.5.4. La v2.4.5 historique a un certificat pilote différent et ne peut pas recevoir cette APK comme mise à jour sans stratégie de migration préalable.

**SHA-256 :**
`e381764eb3a04f4d1c9aa6a7fef2e693106db5fa976a28af6c9fb94d514d3ea5`

**Problème traité :**
Sur Android 6.0.1, les boutons Achat/Vente apparaissaient gris ou blancs et ne produisaient aucune action, tandis que `TEST_NUMBER` restait bleu et fonctionnait. Le routage pouvait aussi laisser plusieurs téléphones appairés au même nœud se disputer la file.

**Cause identifiée :**
Deux causes concordaient exactement avec les captures : les boutons financiers utilisaient uniquement des variables CSS non comprises par l’ancien WebView Android 6, alors que le bouton Test utilisait des couleurs hexadécimales directes ; surtout, le flux financier appelait `window.confirm()` sans `WebChromeClient.onJsConfirm()`, ce qui supprimait silencieusement la confirmation et interrompait le clic avant toute requête. Côté serveur, la location visait le nœud mais ne procédait pas à l’élection explicite d’un seul appareil Robot lorsque le même nœud/SIM avait été appairé sur plusieurs téléphones.

**Correction apportée :**
- couleurs bleu/violet littérales de secours avant les variables CSS pour l’ancien WebView ;
- relais natif Android de la boîte de confirmation avec boutons **CONFIRMER** et **ANNULER** ;
- après la pression, prévisualisation serveur des numéros officiels du fournisseur et du bénéficiaire, de leurs nœuds et du montant ;
- empreinte SHA-256 de cette prévisualisation exigée pour toute création financière ; toute modification ultérieure produit `CONFIRMATION_CHANGED` avant composition ;
- aucun contrôle financier ajouté avant la pression : les champs locaux sont validés, puis la hiérarchie et les numéros officiels sont vérifiés après l’action de l’utilisateur ;
- au lease, numéro officiel de la SIM exécutrice inclus dans l’empreinte d’intégrité et vérifié par Android avant de construire l’unique code USSD autorisé ;
- démarrage/reprise Robot explicite : le nouveau téléphone vérifié devient l’unique appareil élu pour ce nœud, les anciens appareils passent en attente et leur heartbeat périodique ne peut pas voler la file ;
- concordance pop-up Camtel maintenue sur le destinataire et le montant avant lecture du PIN ; divergence : clic Annuler, aucun PIN, résultat `CONFIRMATION_MISMATCH` avec capture textuelle expurgée ;
- correction du détecteur de divergence pour accepter un pop-up contenant plusieurs numéros seulement si le numéro attendu est bien présent ;
- démarrage Robot sans PIN conservé pour permettre `TEST_NUMBER`; PIN et Accessibilité restent exigés seulement lorsqu’une commande financière est effectivement louée ;
- nom, version et tests CI mis à jour pour v2.6.1.

**Fichiers créés :**
- `app/src/test/finance-flow.mjs`

**Fichiers modifiés :**
- `.github/workflows/build.yml`
- `README.md`
- `app/build.gradle`
- `app/src/main/assets/app.js`
- `app/src/main/assets/style.css`
- `app/src/main/java/com/profitloop/blueauto/ApiClient.java`
- `app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java`
- `app/src/main/java/com/profitloop/blueauto/MainActivity.java`
- `app/src/main/java/com/profitloop/blueauto/RobotService.java`
- `app/src/main/java/com/profitloop/blueauto/UssdCommandFactory.java`
- `cloudflare/src/index.js`
- `cloudflare/test/integration.mjs`
- `docs/PROJECT_STATE.md`
- `docs/TEST_TERRAIN.md`

**Fichiers supprimés :**
Aucun fichier produit. L’étape temporaire de publication de l’APK interne a été retirée du workflow final.

**Tests exécutés :**
- `node app/src/test/finance-flow.mjs` : simulation Android 6 du clic Vente, prévisualisation, confirmation, annulation et non-régression Test ;
- cinq tests unitaires `CommandExecutionPolicy` dans GitHub Actions ;
- compilation `:app:assembleDebug` avec Java 17, Gradle 8.2 et compileSdk 34 ;
- `node --check app/src/main/assets/app.js` ;
- `npm run check` dans `cloudflare` avec Miniflare/D1 ;
- scénarios Worker : appairage/filiation, alias locaux, deux numéros officiels, empreinte de confirmation obligatoire, anti-doublon, FIFO, isolation multi-SIM, états complets et élection T1/T2 ;
- `git diff --check` ;
- intégrité ZIP APK ; lecture manifeste ; comparaison version/package ;
- `apksigner verify --verbose --print-certs` et comparaison du certificat avec v2.6.0 ;
- contrôle HTTP de production `/health` et D1 `online` ;
- vérification de la PR #4 ouverte, non brouillon, fusionnable et non fusionnée.

**Résultats :**
Tous les tests automatisés et les runs GitHub #137/#138 sont réussis. La simulation démontre que le chemin financier n’est plus silencieux sur l’ancien WebView et que **ANNULER** ne crée aucune commande. L’intégration démontre qu’un second téléphone explicitement démarré devient l’unique Robot de ce nœud et que l’ancien ne loue pas la commande. L’APK est intègre, correctement versionnée et signée. Le Worker de production reste volontairement inchangé à `2.3.1-cloudflare`; la validation financière terrain n’est donc pas encore autorisée et aucune réussite Camtel réelle n’est déclarée.

**Ce qui est maintenant acquis :**
- cause exacte des boutons gris et du clic silencieux identifiée et couverte par un test reproductible ;
- interface Android 6 avec couleurs de secours et confirmation native ;
- flux demandé **pression → résolution officielle → confirmation utilisateur → création → Robot exact → contrôle Camtel → PIN** implémenté ;
- hiérarchie DAE/DSM/POS et numéros officiels résolus dans D1 après la pression ;
- commande signée avec nœud et numéro fournisseur exacts ;
- élection d’un seul téléphone Robot par nœud/SIM ;
- `TEST_NUMBER`, design bleu/or, PIN chiffré, masque PIN, multi-SIM, FIFO, anti-doublon et réveil du simple verrou sans identifiant préservés ;
- APK v2.6.1 signée dans la lignée permanente et disponible.

**Solutions importantes à préserver :**
- fallback hexadécimal placé avant les variables CSS pour Android 6 ;
- `WebChromeClient.onJsConfirm()` comme relais natif obligatoire ;
- `preview_command` et `confirmation_fingerprint` pour les opérations financières ;
- `executor_phone`, `integrity_version = 2` et validation dans `UssdCommandFactory` ;
- `claim_robot` seulement au démarrage/restart, jamais comme effet d’un heartbeat périodique ;
- `SimIdentityManager`/`SimCallManager` pour SIM physique, slot et route d’appel ;
- comparaison numéro + montant avant PIN, masque confidentiel `FLAG_SECURE`, expurgation du PIN ;
- `TEST_NUMBER` indépendant du PIN et de l’Accessibilité ;
- certificat permanent et son empreinte ;
- Worker de production actuel tant que le déploiement v2.6.1 n’est pas explicitement autorisé et vérifié.

**Ce qui reste à faire :**
1. Obtenir l’autorisation explicite de lancer une fois **Déployer Blue Magic sur Cloudflare** sur `fix/blue-magic-v2-6-recovery`.
2. Vérifier le succès de la liste des migrations, de leur application sans changement, du déploiement et de `/health = 2.6.1-cloudflare`.
3. Installer v2.6.1 par-dessus v2.5.3/v2.5.4/v2.6.0 sans désinstaller. Si le téléphone est exactement en v2.4.5, arrêter et préparer la migration de signature/profils.
4. Vérifier visuellement que les boutons sont bleu/violet sur Android 6 ; appuyer sur une opération, contrôler les deux numéros et le montant, puis **ANNULER** sans fonds.
5. Après ce test sans fonds, exécuter une seule transaction minimale supervisée et vérifier la concordance Camtel, le masque PIN et la preuve opérateur.
6. Exécuter le scénario T1/T2/T3 et dix alternances sans erreur avant un montant significatif.
7. Atteindre trente transactions minimales consécutives sur le matériel exact avant autonomie financière.
8. Après stabilisation du noyau, planifier séparément les autres onglets et rôles du cahier des charges ; mercenaires et tchoronko ne sont pas déclarés livrés ici.

**Ce qui NE doit surtout PAS être modifié :**
- ne pas rendre les boutons gris ou dépendants uniquement de variables CSS ;
- ne pas retirer le relais natif de confirmation ;
- ne pas créer une commande financière avant la pression et la confirmation explicite ;
- ne pas assouplir l’empreinte de confirmation, le numéro fournisseur, le numéro bénéficiaire, le montant ou le code USSD ;
- ne pas rendre PIN/Accessibilité obligatoires pour `TEST_NUMBER` ;
- ne pas permettre à un heartbeat périodique d’un ancien téléphone de reprendre la file ;
- ne pas retirer les contrôles SIM/slot/route ;
- ne pas afficher, journaliser ou transmettre le PIN ;
- ne pas contourner un verrou Android sécurisé ;
- ne pas changer le design bleu/or ni l’appairage diagnostique pendant la validation terrain ;
- ne pas fusionner la PR #4 avant les tests terrain ;
- ne jamais changer de certificat Android pour contourner une incompatibilité.

**Régressions éventuelles :**
Les APK antérieures qui tentent de créer directement une opération financière sans prévisualisation recevront `CONFIRMATION_REQUIRED` après le déploiement du Worker v2.6.1. C’est un changement volontaire pour garantir la confirmation demandée ; tous les téléphones de commande financière doivent donc être mis à jour vers v2.6.1. `TEST_NUMBER` reste compatible.

**Risques connus :**
- aucune transaction Camtel réelle n’a encore validé cette livraison ;
- Android 6 n’offre pas d’API publique de capture d’écran par `AccessibilityService`. En cas de divergence, la v2.6.1 conserve une capture textuelle expurgée, pas une image ;
- certains fabricants cachent le dialogue USSD ou son champ derrière un verrou sécurisé ; ce verrou ne sera pas contourné ;
- le texte réel du pop-up/SMS Camtel peut varier ; toute variante non reconnue doit échouer sans PIN ;
- l’APK reste une variante pilote `debuggable`, bien que signée par le certificat permanent ;
- les secrets Android permanents manquent dans l’environnement GitHub `production` ;
- la v2.4.5 utilise une autre signature ; ne jamais la désinstaller sans stratégie de conservation des profils ;
- dépendances : application Téléphone, service Accessibilité, permissions Android, gestion batterie, SIM/réseau Camtel, Worker, D1, jetons appareils, `PAIRING_SECRET`, GitHub Actions et signature APK.

**Point de reprise pour la prochaine session :**
Lire ce document et `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`. Vérifier le HEAD de `fix/blue-magic-v2-6-recovery`, la PR #4 et les runs #137/#138. Ne modifier ni l’APK ni le Worker. Reprendre exactement par l’autorisation de déploiement unique, puis exécuter le workflow manuel existant et vérifier `/health` avant d’autoriser l’installation et le test financier.

**Prochaine action recommandée :**
Répondre explicitement : « J’autorise le déploiement unique du Worker `2.6.1-cloudflare` et la vérification distante D1/migrations via le workflow GitHub, sans fusionner la PR #4. » Ensuite seulement, déployer, vérifier la santé, installer l’APK et tester d’abord le bouton financier avec **ANNULER**, sans fonds.

**Autorisation nécessaire avant la prochaine action :**
Oui.

**Si oui, préciser exactement l’autorisation nécessaire :**
Autorisation d’exécuter une fois le workflow **Déployer Blue Magic sur Cloudflare** sur `fix/blue-magic-v2-6-recovery`, incluant la lecture des migrations distantes, l’application idempotente des migrations déjà présentes, le déploiement de `blue-magic-api` et le contrôle `/health`, sans fusionner la PR #4 et sans modifier les secrets.
