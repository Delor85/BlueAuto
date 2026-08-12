# ÉTAT DU PROJET APRÈS CETTE ÉTAPE

État vérifié le 12 août 2026. Ce document est la source de reprise obligatoire avec `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`.

**Version :**
2.6.2 — finances Android 6+ corrigées, Worker correspondant déployé et APK permanente produite ; validation terrain encore obligatoire.

**Branche :**
`fix/blue-magic-v2-6-recovery`

**Commit :**
`4c2f6cf8d7c7e0246a3f0c608fc8cf3dfe7fc0b1` pour le code v2.6.2 ; `c34995bde25658f83149f92f09b025d221009bd5` pour l’export APK unique autorisé ; `257d89a54cad9263fbd9a708147f4a1618948481` pour son retrait immédiat. Le commit contenant ce document constitue le HEAD documentaire suivant.

**État GitHub :**
Branche publiée. PR ouverte, non brouillon, fusionnable et non fusionnée. Aucun déclencheur automatique Cloudflare ne subsiste.

**PR :**
PR #4 — `Blue Magic v2.6.2 — finances Android 6+ et Robot lié à la SIM` — https://github.com/Delor85/BlueAuto/pull/4

**GitHub Actions :**
- Build push #141 et PR #142 : succès du commit code v2.6.2 ;
- déploiement Cloudflare #3 : succès ;
- Build #149 : succès et production de l’unique artefact interne autorisé ; PR #150 : succès sans export ;
- Build final push #151 et PR #152 : succès après retrait immédiat de l’étape d’export ;
- jobs Android : compilation Gradle 8.2/Java 17, tests unitaires et simulation financière réussis ;
- jobs serveur : Miniflare/D1 local, paquets serveur et contrôles syntaxiques réussis ;
- l’environnement `production` ne possède toujours pas les deux secrets Android permanents ; l’APK interne temporaire a donc été re-signée hors GitHub avec le certificat permanent existant, sans modifier les secrets.

**État Cloudflare :**
Déploiement unique effectué et vérifié. Contrôle indépendant : `{"ok":true,"data":{"service":"blue-magic-api","version":"2.6.2-cloudflare","database":"online"}}`.

**Worker :**
`blue-magic-api` — `https://blue-magic-api.mbolodelorpro.workers.dev` — version active `2.6.2-cloudflare`. Version Cloudflare signalée par Wrangler : `6a60171a-8869-4056-9de5-ae96d61334d5`.

**D1 :**
Base distante `blue-magic` en ligne. Binding `DB (blue-magic)` vérifié pendant le dry-run et le déploiement. Aucune donnée distante éditée manuellement.

**Migrations :**
Aucune migration créée ou modifiée. Les commandes distantes `migrations list` puis `migrations apply` ont toutes deux répondu `No migrations to apply`.

**APK :**
`Blue-Magic-v2.6.2-Finance-Robot-Release.apk` — 107330 octets — livrable permanent `/Blue-Magic-v2.6.2-Finance-Robot-Release.apk`. L’APK interne temporaire ne doit jamais être installée.

**Version / versionCode :**
`2.6.2` / `42`, paquet `com.profitloop.blueauto`, minSdk 23 (Android 6.0), targetSdk 34. Valeurs vérifiées dans l’APK décodée, pas seulement dans les sources.

**Signature :**
Certificat permanent `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`, RSA 4096, empreinte certificat SHA-256 `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`. `apksigner` confirme v1, v2 et v3. Certificat directement comparé et identique aux APK v2.6.0 et v2.6.1 ; versionCode 42 supérieur à 40/41 : mise à jour directe, sans désinstallation. Les v2.5.3/v2.5.4 appartiennent à la même lignée permanente selon l’état validé antérieur. La v2.4.5 historique reste d’une autre signature.

**SHA-256 :**
`90d62337d1f8c7f52a89c4a240656bb8c57a56e43ba9c8bb7bfb25afa63c2724`

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
Livrable hors dépôt : `Blue-Magic-v2.6.2-Finance-Robot-Release.apk`. Aucun nouveau fichier source.

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
Aucun. L’étape d’export APK a été retirée immédiatement et ne figure pas dans l’état final GitHub. Son unique artefact GitHub est configuré pour expirer le 13 août 2026.

**Tests exécutés :**
- `node app/src/test/finance-flow.mjs` ;
- `npm run check` dans `cloudflare` avec Miniflare/D1 ;
- `git diff --check` ;
- GitHub Actions #141/#142, export unique #149, PR sans export #150, puis nettoyage final #151/#152 ;
- compilation `:app:testDebugUnitTest` et `:app:assembleDebug` avec Java 17/Gradle 8.2 ;
- scénario Worker : Remote sans SIM refusé, Remote avec SIM refusé pendant que l’ancien Robot est actif, ancien Robot toujours locataire, arrêt explicite, activation du remplaçant, ancien téléphone en attente ;
- workflow Cloudflare #3 : test, dry-run, liste migrations distante, application migrations distante, déploiement et santé ;
- contrôle HTTP indépendant de `/health` après propagation ;
- intégrité ZIP de l’artefact interne ;
- décodage APK : paquet, versionName 2.6.2, versionCode 42, minSdk 23 et targetSdk 34 ;
- `apksigner verify --verbose --print-certs` : v1/v2/v3, certificat RSA 4096 et empreinte ;
- comparaison directe du certificat avec les APK v2.6.0 et v2.6.1 ;
- intégrité ZIP finale, taille et SHA-256.

**Résultats :**
Tous les tests de code et runs finaux sont réussis. Le test serveur prouve que le plus récent ne gagne plus et que l’ancien Robot continue de recevoir sa file jusqu’à son arrêt explicite. D1 est en ligne sans migration en attente. Le Worker 2.6.2 est actif. L’APK 2.6.2 est produite, intègre et correctement signée. La réussite Camtel réelle reste à valider sur les téléphones.

**Ce qui est maintenant acquis :**
- cause générale du blocage financier identifiée : incompatibilité APK v2.6.1 / Worker ancien, pas seulement Android 6 ;
- Worker financier correspondant déployé ;
- boutons d’action homogènes sur Android 6+ ;
- ancien Robot prioritaire, sans éjection « dernier arrivé » ;
- refus lisible du second Robot et ordre de transfert explicite ;
- confirmation financière après pression, résolution D1 des deux numéros, empreinte signée et contrôle Camtel avant PIN ;
- `TEST_NUMBER`, design bleu/or, PIN chiffré et masqué, SIM/slot/route, multi-SIM, FIFO, anti-doublon et verrou simple sans identifiant préservés ;
- APK v2.6.2 signée dans la lignée permanente et disponible.

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
1. Installer v2.6.2 par-dessus, sans désinstaller, sur un téléphone de la lignée permanente v2.5.3/v2.5.4/v2.6.0/v2.6.1. Si Android refuse la mise à jour, ne rien désinstaller et relever la version exacte.
2. Tester d’abord la confirmation financière puis **ANNULER**, sans fonds, sur Android 6 et une version récente.
3. Exécuter ensuite une seule transaction minimale supervisée et relever le résultat exact.
4. Exécuter le protocole T1/T2/T3 : tentative du second Robot refusée, arrêt explicite de l’ancien, déplacement/vérification SIM, puis activation du nouveau.
5. Ne fusionner la PR #4 qu’après validation terrain explicite.

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
- certains fabricants masquent le dialogue USSD derrière un verrou Android sécurisé ;
- Android 6 ne permet pas à l’AccessibilityService de produire une capture d’écran image universelle : seule la preuve textuelle expurgée est garantie ;
- le texte réel Camtel peut varier et doit échouer sans PIN s’il n’est pas reconnu ;
- l’APK reste une variante `debuggable` même lorsqu’elle est signée avec le certificat permanent ;
- la v2.4.5 historique utilise un autre certificat ;
- dépendances : application Téléphone, Accessibilité, permissions Android, batterie, SIM/réseau Camtel, Worker, D1, jetons, secrets sécurisés, GitHub Actions et signature APK.

**Point de reprise pour la prochaine session :**
Lire ce document et `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`. Vérifier le HEAD de `fix/blue-magic-v2-6-recovery`, la PR #4, les runs finaux #151/#152, le workflow Cloudflare #3 et `/health = 2.6.2-cloudflare`. Ne redéployer ni ne modifier D1. Reprendre par l’installation de l’APK v2.6.2 et les Gates 1 à 3 de `docs/TEST_TERRAIN.md`.

**Prochaine action recommandée :**
Installer l’APK v2.6.2 sans désinstallation, vérifier l’écran de version, puis tester une opération financière jusqu’à la confirmation 1/2 et choisir **ANNULER**, sans fonds.

**Autorisation nécessaire avant la prochaine action :**
Non pour l’installation et le test sans fonds. Toute nouvelle modification du code, tout nouveau déploiement Cloudflare ou toute fusion exigera une autorisation séparée après le retour terrain.

**Si oui, préciser exactement l’autorisation nécessaire :**
Sans objet à ce stade.
