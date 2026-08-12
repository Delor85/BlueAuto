# ÉTAT DU PROJET APRÈS CETTE ÉTAPE

État vérifié le 12 août 2026. Ce document est la source de reprise obligatoire avec `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`.

**Version :**
2.6.2 — finances Android 6+ corrigées dans les sources et Worker correspondant déployé ; APK terrain v2.6.2 encore à produire.

**Branche :**
`fix/blue-magic-v2-6-recovery`

**Commit :**
`4c2f6cf8d7c7e0246a3f0c608fc8cf3dfe7fc0b1` pour le code v2.6.2 ; `3abe820caf3fed5c44c6efd1ae8751da0565a915` pour le retour du workflow Cloudflare en mode manuel uniquement. Le commit contenant ce document constitue le HEAD documentaire suivant.

**État GitHub :**
Branche publiée. PR ouverte, non brouillon, fusionnable et non fusionnée. Aucun déclencheur automatique Cloudflare ne subsiste.

**PR :**
PR #4 — `Blue Magic v2.6.2 — finances Android 6+ et Robot lié à la SIM` — https://github.com/Delor85/BlueAuto/pull/4

**GitHub Actions :**
- Build push #141 et PR #142 : succès du commit code v2.6.2 ;
- déploiement Cloudflare #3 : succès ;
- Build final push #145 et PR #146 : succès après retrait du déclencheur temporaire ;
- jobs Android : compilation Gradle 8.2/Java 17, tests unitaires et simulation financière réussis ;
- jobs serveur : Miniflare/D1 local, paquets serveur et contrôles syntaxiques réussis ;
- l’environnement `production` ne possède toujours pas les deux secrets Android permanents : aucune APK permanente GitHub n’est publiée.

**État Cloudflare :**
Déploiement unique effectué et vérifié. Contrôle indépendant : `{"ok":true,"data":{"service":"blue-magic-api","version":"2.6.2-cloudflare","database":"online"}}`.

**Worker :**
`blue-magic-api` — `https://blue-magic-api.mbolodelorpro.workers.dev` — version active `2.6.2-cloudflare`. Version Cloudflare signalée par Wrangler : `6a60171a-8869-4056-9de5-ae96d61334d5`.

**D1 :**
Base distante `blue-magic` en ligne. Binding `DB (blue-magic)` vérifié pendant le dry-run et le déploiement. Aucune donnée distante éditée manuellement.

**Migrations :**
Aucune migration créée ou modifiée. Les commandes distantes `migrations list` puis `migrations apply` ont toutes deux répondu `No migrations to apply`.

**APK :**
La v2.6.2 a été compilée avec succès en CI mais aucun binaire v2.6.2 téléchargeable n’a été publié. Dernier binaire livré : `Blue-Magic-v2.6.1-Finance-Flow-Release.apk` (ne pas l’utiliser pour valider les deux corrections v2.6.2).

**Version / versionCode :**
Sources et compilation CI : `2.6.2` / `42`, paquet `com.profitloop.blueauto`, Android minimum 6.0. Dernier APK livré : `2.6.1` / `41`.

**Signature :**
Signature prévue pour v2.6.2 : certificat permanent `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`, empreinte certificat SHA-256 `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`. La signature v2.6.2 n’est pas encore vérifiable faute de binaire produit. Ne pas présenter l’APK temporaire CI comme livrable.

**SHA-256 :**
v2.6.2 : non disponible tant que l’APK permanente n’est pas produite. Dernier APK v2.6.1 : `e381764eb3a04f4d1c9aa6a7fef2e693106db5fa976a28af6c9fb94d514d3ea5`.

**Problème traité :**
1. Achat/Vente ne fonctionnaient sur aucune version Android ; Android 6 rendait seulement la différence visuelle plus évidente.
2. La règle « Robot le plus récent gagnant » pouvait déconnecter le vrai téléphone Robot si un Remote passait en Robot par erreur.

**Cause identifiée :**
- le flux financier de l’APK appelle `preview_command`, absent de l’ancien Worker `2.3.1-cloudflare` encore en production ; `TEST_NUMBER` n’utilisait pas cette route et continuait donc à fonctionner ;
- les boutons financiers et Test utilisaient des classes/couleurs différentes ;
- l’ancien `claim_robot` désactivait tous les autres appareils du même nœud dès qu’un téléphone plus récent revendiquait le rôle ;
- le démarrage Android local lançait le service avant de rendre un refus serveur visible.

**Correction apportée :**
- Worker `2.6.2-cloudflare` déployé avec `preview_command`, empreinte de confirmation et vérification des numéros officiels ;
- Achat, Approvisionnement, Vente et Test partagent le même état actif bleu explicite sur Android 6+ ;
- `WebChromeClient.onJsConfirm()` reste le relais natif de la confirmation ;
- ajout de `activate_robot` : la transition Remote → Robot vérifie la SIM physique avant toute mutation locale ;
- activation atomique refusée avec `ROBOT_ALREADY_ACTIVE` tant qu’un autre appareil actif possède le nœud/SIM ;
- aucun appareil existant n’est désactivé automatiquement, même si le nouvel appairage est plus récent ;
- transfert autorisé seulement après arrêt explicite, déplacement de la SIM, vérification sur le nouveau téléphone et activation ;
- démarrage Robot prévalidé par le serveur ; tout refus apparaît dans un dialogue et laisse le Robot local arrêté ;
- l’arrêt local envoie un heartbeat de libération avant la fermeture du service ;
- heartbeats périodiques incapables de promouvoir ou d’évincer un téléphone ;
- protocole T1/T2/T3 réécrit selon cet ordre sécurisé.

**Fichiers créés :**
Aucun.

**Fichiers modifiés :**
- `.github/workflows/build.yml`
- `README.md`
- `app/build.gradle`
- `app/src/main/assets/index.html`
- `app/src/main/assets/style.css`
- `app/src/main/java/com/profitloop/blueauto/ApiClient.java`
- `app/src/main/java/com/profitloop/blueauto/MainActivity.java`
- `app/src/main/java/com/profitloop/blueauto/RobotService.java`
- `app/src/main/java/com/profitloop/blueauto/SimIdentityManager.java`
- `app/src/test/finance-flow.mjs`
- `cloudflare/package.json`
- `cloudflare/package-lock.json`
- `cloudflare/public/index.html`
- `cloudflare/public/style.css`
- `cloudflare/src/index.js`
- `cloudflare/test/integration.mjs`
- `docs/PROJECT_STATE.md`
- `docs/TEST_TERRAIN.md`

**Fichiers supprimés :**
Aucun. Le déclencheur Cloudflare temporaire et la tentative locale d’étape d’export APK ont été retirés ; ils ne figurent pas dans l’état final GitHub.

**Tests exécutés :**
- `node app/src/test/finance-flow.mjs` ;
- `npm run check` dans `cloudflare` avec Miniflare/D1 ;
- `git diff --check` ;
- GitHub Actions #141/#142 puis #145/#146 ;
- compilation `:app:testDebugUnitTest` et `:app:assembleDebug` avec Java 17/Gradle 8.2 ;
- scénario Worker : Remote sans SIM refusé, Remote avec SIM refusé pendant que l’ancien Robot est actif, ancien Robot toujours locataire, arrêt explicite, activation du remplaçant, ancien téléphone en attente ;
- workflow Cloudflare #3 : test, dry-run, liste migrations distante, application migrations distante, déploiement et santé ;
- contrôle HTTP indépendant de `/health` après propagation.

**Résultats :**
Tous les tests de code et runs finaux sont réussis. Le test serveur prouve que le plus récent ne gagne plus et que l’ancien Robot continue de recevoir sa file jusqu’à son arrêt explicite. D1 est en ligne sans migration en attente. Le Worker 2.6.2 est actif. La validation Camtel réelle reste impossible tant que l’APK v2.6.2 permanente n’est pas produite et installée.

**Ce qui est maintenant acquis :**
- cause générale du blocage financier identifiée : incompatibilité APK v2.6.1 / Worker ancien, pas seulement Android 6 ;
- Worker financier correspondant déployé ;
- boutons d’action homogènes sur Android 6+ ;
- ancien Robot prioritaire, sans éjection « dernier arrivé » ;
- refus lisible du second Robot et ordre de transfert explicite ;
- confirmation financière après pression, résolution D1 des deux numéros, empreinte signée et contrôle Camtel avant PIN ;
- `TEST_NUMBER`, design bleu/or, PIN chiffré et masqué, SIM/slot/route, multi-SIM, FIFO, anti-doublon et verrou simple sans identifiant préservés.

**Solutions importantes à préserver :**
- `preview_command` + `confirmation_fingerprint` ;
- `WebChromeClient.onJsConfirm()` ;
- styles littéraux Android 6 et classe commune `transaction-action` ;
- `activate_robot` avec `NOT EXISTS` sur tout autre Robot actif ;
- ne jamais désactiver un autre appareil dans `claimRobotSlot` ;
- heartbeats périodiques non promoteurs ;
- inspection SIM avant mutation Remote → Robot ;
- arrêt explicite puis heartbeat de libération ;
- `SimIdentityManager`, `SimCallManager`, `executor_phone` et intégrité v2 ;
- comparaison numéro + montant avant PIN et masque confidentiel ;
- certificat Android permanent attendu.

**Ce qui reste à faire :**
1. Obtenir l’autorisation explicite distincte de publier pendant un seul run l’APK interne compilée comme artefact GitHub à rétention un jour, uniquement pour la télécharger et la re-signer avec le certificat permanent, puis retirer immédiatement cette étape.
2. Produire `Blue-Magic-v2.6.2-Finance-Robot-Release.apk`, vérifier versionCode 42, signature v1/v2/v3, certificat, SHA-256 et compatibilité.
3. Installer v2.6.2 sans désinstaller uniquement sur un téléphone de la lignée permanente v2.5.3/v2.5.4/v2.6.0/v2.6.1.
4. Tester d’abord la confirmation financière puis **ANNULER**, sans fonds, sur Android 6 et une version récente.
5. Exécuter ensuite une transaction minimale supervisée, puis le protocole T1/T2/T3.
6. Ne fusionner la PR #4 qu’après validation terrain explicite.

**Ce qui NE doit surtout PAS être modifié :**
- ne pas rétablir la règle « dernier Robot créé gagne » ;
- ne pas permettre à un Remote de désactiver le Robot existant ;
- ne pas créer une opération financière avant la pression et la confirmation humaine ;
- ne pas retirer la résolution D1 ou les contrôles fournisseur/bénéficiaire/montant ;
- ne pas rendre PIN/Accessibilité obligatoires pour `TEST_NUMBER` ;
- ne pas retirer les contrôles SIM/slot/route ;
- ne pas afficher, transmettre ou journaliser le PIN ;
- ne pas changer le design bleu/or ;
- ne pas modifier les secrets ;
- ne pas relancer Cloudflare sans nouvelle autorisation ;
- ne pas fusionner la PR #4 ;
- ne pas changer de certificat Android.

**Régressions éventuelles :**
Les APK antérieures qui créent directement une opération financière sans `preview_command` ne sont pas compatibles avec la finance stricte du Worker 2.6.2 et recevront `CONFIRMATION_REQUIRED`. `TEST_NUMBER` reste compatible. Le transfert de Robot exige désormais l’arrêt explicite de l’ancien appareil ; si l’ancien téléphone est perdu ou définitivement hors ligne, une procédure de récupération administrative reste à concevoir.

**Risques connus :**
- aucune transaction Camtel réelle n’a validé la v2.6.2 ;
- aucun APK v2.6.2 permanent n’est encore disponible ;
- certains fabricants masquent le dialogue USSD derrière un verrou Android sécurisé ;
- Android 6 ne permet pas à l’AccessibilityService de produire une capture d’écran image universelle : seule la preuve textuelle expurgée est garantie ;
- le texte réel Camtel peut varier et doit échouer sans PIN s’il n’est pas reconnu ;
- l’APK reste une variante `debuggable` même lorsqu’elle est signée avec le certificat permanent ;
- la v2.4.5 historique utilise un autre certificat ;
- dépendances : application Téléphone, Accessibilité, permissions Android, batterie, SIM/réseau Camtel, Worker, D1, jetons, secrets sécurisés, GitHub Actions et signature APK.

**Point de reprise pour la prochaine session :**
Lire ce document et `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`. Vérifier le HEAD de `fix/blue-magic-v2-6-recovery`, la PR #4, les runs #145/#146, le workflow Cloudflare #3 et `/health = 2.6.2-cloudflare`. Ne redéployer ni ne modifier D1. Reprendre uniquement par la production contrôlée de l’APK v2.6.2.

**Prochaine action recommandée :**
Autoriser explicitement l’export temporaire d’un artefact APK interne GitHub à rétention un jour, destiné uniquement au téléchargement et à la re-signature locale contrôlée, suivi du retrait immédiat de l’étape de workflow.

**Autorisation nécessaire avant la prochaine action :**
Oui.

**Si oui, préciser exactement l’autorisation nécessaire :**
« J’autorise la publication, pendant un seul run GitHub Actions, de l’APK interne v2.6.2 compilée comme artefact privé du workflow avec une rétention d’un jour, uniquement afin que Codex la télécharge, la re-signe avec le certificat permanent Blue Magic déjà disponible, vérifie la signature et le SHA-256, puis retire immédiatement l’étape d’export. Je n’autorise ni modification des secrets, ni nouveau déploiement Cloudflare, ni fusion de la PR #4. »
