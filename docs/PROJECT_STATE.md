# ÉTAT DU PROJET APRÈS CETTE ÉTAPE

État vérifié le 12 août 2026. Ce document est la source de reprise obligatoire avec `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`.

**Version :**
2.6.0 — reprise fonctionnelle du noyau Robot USSD, validation terrain encore obligatoire.

**Branche :**
`fix/blue-magic-v2-6-recovery`

**Commit :**
`48c662b26f0a5e646757f00e7f161b09a4a49e59` pour le dernier état code/workflow testé. Le commit contenant le présent document constitue le HEAD documentaire de reprise.

**État GitHub :**
Branche publiée. PR non brouillon, fusionnable sans conflit, non fusionnée. La PR #3 historique reste distincte et ne doit pas être fusionnée pour livrer la v2.6.

**PR :**
PR #4 ouverte : https://github.com/Delor85/BlueAuto/pull/4

**GitHub Actions :**
- run push #122 : succès sur `9c385919de6660c3231f970e52c7a58632790fc7` ; cinq tests unitaires Android, compilation APK et intégration Worker réussis. Ce run a fourni une seule APK temporaire, récupérée pour re-signature puis retirée du workflow ; elle ne doit jamais être installée ;
- run push #123 : succès sur `48c662b26f0a5e646757f00e7f161b09a4a49e59` ; workflow final sans publication temporaire ;
- run PR #124 : succès sur le même commit ; `android-debug-apk` et `server-packages` réussis, job permanent correctement ignoré sur PR ;
- l’environnement GitHub `production` ne contient toujours pas les deux secrets Android permanents : le job push le signale proprement et ne publie aucune APK de mauvaise signature.

**État Cloudflare :**
Inchangé par cette livraison Android. Le déploiement de production était au vert avant cette étape ; aucun déploiement n’a été relancé.

**Worker :**
`blue-magic-api` — `https://blue-magic-api.mbolodelorpro.workers.dev`. Version de santé précédemment vérifiée : `2.3.1-cloudflare`.

**D1 :**
Base distante `blue-magic`, précédemment signalée `online` par le Worker. Aucun contenu D1 n’a été modifié.

**Migrations :**
Aucune migration créée, appliquée ou modifiée. La v2.6 reste compatible avec le Worker et le schéma déjà déployés.

**APK :**
`Blue-Magic-v2.6.0-Recovery-Release.apk` — 107330 octets — `/Blue Magic/APK/Blue-Magic-v2.6.0-Recovery-Release.apk`.

**Version / versionCode :**
`2.6.0` / `40` ; paquet `com.profitloop.blueauto` ; Android minimum 6.0 conservé.

**Signature :**
Certificat permanent `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`, RSA 4096. Empreinte certificat SHA-256 `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`. Vérification `apksigner` réussie en v1, v2 et v3. Certificat, paquet et lignée identiques à la v2.5.4, avec `versionCode` 40 supérieur à 34 : installation directe en mise à jour, sans désinstallation.

**SHA-256 :**
`6f0305c92e70d15d0adeacb15bb5091fade44aecf62d04216fe16d4884c79cd5`

**Problème traité :**
Dans toutes les versions 2.5 testées, le Robot pouvait s’ouvrir mais `TEST_NUMBER`, les achats et les ventes ne partaient plus. L’utilisateur observait donc une régression par rapport à la v2.4.5.

**Cause identifiée :**
Le durcissement v2.5 avait regroupé dans `RobotService.checkReadiness()` la sécurité de route SIM et les prérequis propres à la finance. L’absence d’Accessibilité, de PIN chiffré ou un ancien état `pinBlocked` arrêtait ainsi le Robot avant heartbeat/lease, y compris pour `TEST_NUMBER` qui ne contient ni montant, ni destinataire, ni PIN. `MainActivity.startRobotSafely()` appliquait le même blocage au démarrage. Enfin, la garde de verrou sécurisé était globale au lieu d’être limitée aux commandes financières.

**Correction apportée :**
- séparation explicite entre la route sûre, requise pour toutes les commandes, et la capacité financière, requise uniquement pour `DISTRIBUTION_TRANSFER`/`RETAIL_TRANSFER` ;
- restauration du démarrage et de l’exécution de `TEST_NUMBER` sans PIN ni Accessibilité, tout en conservant SIM physique, slot exact, permissions Téléphone et route d’appel obligatoire ;
- un PIN bloqué ne bloque plus le test, mais bloque toujours achats et ventes ;
- un verrou Android sécurisé ne diffère plus les tests et ne s’applique qu’aux commandes avec PIN ; le retrait temporaire du simple verrou sans identifiant est conservé ;
- masque confidentiel plein écran pendant la saisie/validation automatique du PIN, non cliquable, sans permission `SYSTEM_ALERT_WINDOW`, marqué `FLAG_SECURE` et retiré après validation ou délai de sécurité ;
- affichage persistant des codes exacts d’erreur de création de commande et des prérequis financiers manquants ;
- protocole terrain v2.6 ordonné : test sans fonds, confidentialité/verrou simple, transaction minimale, puis multi-SIM.

**Fichiers créés :**
- `app/src/main/java/com/profitloop/blueauto/CommandExecutionPolicy.java`
- `app/src/test/java/com/profitloop/blueauto/CommandExecutionPolicyTest.java`

**Fichiers modifiés :**
- `.github/workflows/build.yml`
- `README.md`
- `app/build.gradle`
- `app/src/main/assets/app.js`
- `app/src/main/assets/index.html`
- `app/src/main/java/com/profitloop/blueauto/ApiClient.java`
- `app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java`
- `app/src/main/java/com/profitloop/blueauto/MainActivity.java`
- `app/src/main/java/com/profitloop/blueauto/RobotService.java`
- `docs/PROJECT_STATE.md`
- `docs/TEST_TERRAIN.md`

**Fichiers supprimés :**
Aucun.

**Tests exécutés :**
- cinq tests unitaires de `CommandExecutionPolicy` dans les runs #122, #123 et #124 ;
- compilation `:app:assembleDebug` avec Java 17 et Gradle 8.2 dans les mêmes runs ;
- analyse syntaxique des 17 fichiers Java ;
- `node --check` sur l’interface JavaScript embarquée ;
- validation YAML et `git diff --check` ;
- `npm run check` dans `cloudflare`, incluant Remote/mode, annulation, isolation par SIM, alias hiérarchiques et flux d’états ;
- contrôle du périmètre confirmant l’absence de modification de `cloudflare/**`, `htdocs/**`, D1 et migrations ;
- intégrité ZIP de l’APK, lecture du manifeste, SHA-256, vérification de signature v1/v2/v3 et comparaison du certificat avec la v2.5.4 ;
- calcul GitHub de la PR #4 : fusionnable, état `clean`.

**Résultats :**
Tous les tests statiques, unitaires, d’intégration et de compilation automatisés sont réussis. Les cinq assertions prouvent notamment que `TEST_NUMBER` reste autorisé sans PIN/Accessibilité et avec un ancien `pinBlocked`, tandis que les deux commandes financières restent refusées si leur PIN ou l’Accessibilité manque. L’APK finale est intègre, signée et compatible en mise à jour. Aucun test sur le téléphone/Camtel réel n’a encore été exécuté : la validation fonctionnelle terrain reste bloquante avant fusion ou argent significatif.

**Ce qui est maintenant acquis :**
- une branche v2.6 isolée, une PR #4 propre et une APK signée compatible ;
- la régression logique qui bloquait aussi `TEST_NUMBER` est supprimée dans le code et couverte par tests ;
- les contrôles SIM/slot/route/commande exacte restent obligatoires ;
- les exigences PIN/Accessibilité restent obligatoires uniquement au moment approprié pour la finance ;
- la confirmation 1/2 côté interface, la concordance 2/2 du pop-up Camtel, l’anti-doublon et les statuts `UNKNOWN/BLOCKED` sont préservés ;
- le PIN est chiffré localement et désormais masqué visuellement pendant son injection ;
- le design bleu/or, l’adaptation petits écrans/clavier, l’appairage diagnostique, Remote, FIFO, multi-SIM, Android 6 et la reprise automatique sont conservés.

**Solutions importantes à préserver :**
- le socle opérationnel v2.4.5 : appel USSD par la surface Téléphone, WakeLock CPU au repos et réveil écran bref seulement pendant la commande ;
- `CommandExecutionPolicy` comme frontière entre test et finance ;
- `SimIdentityManager` et `SimCallManager` pour lier une SIM physique au slot et refuser toute route ambiguë ;
- `UssdCommandFactory` pour reconstruire la seule commande autorisée et valider son empreinte ;
- confirmation exacte numéro/montant avant lecture du PIN, puis masque confidentiel ;
- certificat permanent et son empreinte ;
- appairage diagnostique, affichage des erreurs exactes et documentation de reprise ;
- Worker/D1 de production actuellement fonctionnels et inchangés.

**Ce qui reste à faire :**
1. Installer la v2.6 par-dessus la version installée, sans désinstaller ni supprimer les comptes.
2. Exécuter Gate 1 : `TEST_NUMBER` sans Accessibilité et sans argent, sur chaque SIM.
3. Exécuter Gate 2 : verrou simple sans identifiant et vérifier que le PIN n’est jamais visible ; tester séparément qu’un verrou sécurisé n’est pas contourné.
4. Exécuter Gate 3 avec une transaction minimale supervisée et relever le code exact en cas d’échec.
5. Exécuter le scénario T1/T2/T3 de déplacement SIM et dix alternances sans erreur avant argent significatif.
6. Atteindre le seuil pilote de 30 transactions minimales consécutives sur le matériel exact avant production autonome.
7. Après stabilisation du noyau financier, planifier et livrer séparément les autres onglets et rôles du cahier des charges, notamment mercenaires et tchoronko ; ils ne sont pas déclarés livrés par cette APK.
8. Ajouter ultérieurement les secrets Android permanents dans GitHub `production` pour automatiser la publication sans jamais les transmettre dans un chat.

**Ce qui NE doit surtout PAS être modifié :**
- ne pas fusionner la PR #4 avant le test terrain du noyau ;
- ne pas fusionner la PR #3 comme substitut de la v2.6 ;
- ne pas modifier Cloudflare, D1, migrations, variables ou secrets pour diagnostiquer un problème Android ;
- ne pas assouplir la vérification de la SIM physique, du slot, du nœud exécuteur, du code USSD, du numéro, du montant ou de l’empreinte de commande ;
- ne pas rendre PIN/Accessibilité obligatoires pour `TEST_NUMBER` ;
- ne pas retirer le garde-fou qui transforme une absence de preuve en `UNKNOWN` sans nouvelle exécution automatique ;
- ne jamais changer de certificat Android pour une mise à jour ;
- ne pas réécrire le design, l’appairage, le multi-SIM ou l’arborescence sans cas de test démontré et autorisation.

**Régressions éventuelles :**
Aucune régression détectée par les tests automatisés. La non-régression terrain n’est pas encore acquise. Le nouveau masque PIN doit notamment être vérifié sur l’application Téléphone/Camtel exacte avant d’être considéré comme validé.

**Risques connus :**
- Android ne fournit pas d’API publique universelle pour poursuivre une session USSD interactive ; le comportement dépend du fabricant, de la version Android et de l’application Téléphone ;
- un verrou Android avec PIN, schéma, mot de passe ou empreinte ne peut et ne doit pas être contourné ;
- certaines SIM ne publient pas leur numéro à Android et exigent une liaison explicite par ICCID/abonnement ;
- la réception de preuve dépend du texte réel du pop-up/SMS Camtel ; toute variante inconnue doit échouer fermée ;
- l’APK reste `debuggable`, héritage du pilote ; une vraie variante release durcie reste à produire après validation fonctionnelle ;
- les secrets de signature permanents manquent dans GitHub `production` ;
- l’artefact temporaire du run #122 porte une signature éphémère et ne doit jamais être installé ;
- dépendances externes : Android Téléphone/Accessibilité/permissions/batterie, SIM et réseau Camtel, Worker Cloudflare, D1, jetons appareils, `PAIRING_SECRET`, GitHub Actions et certificat APK permanent.

**Point de reprise pour la prochaine session :**
Lire ce document et `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`, vérifier le HEAD de `fix/blue-magic-v2-6-recovery`, la PR #4 et les runs #123/#124. Ne modifier aucun fichier avant de recevoir le résultat de Gate 1. Le premier diagnostic attendu est : le Robot démarre-t-il, `*825*3*3#` s’ouvre-t-il sur la bonne SIM, et quel code exact reste visible en cas d’échec ?

**Prochaine action recommandée :**
Installer `Blue-Magic-v2.6.0-Recovery-Release.apk` comme mise à jour, ouvrir le compte Robot, utiliser **VÉRIFIER / LIER LA SIM**, démarrer le Robot puis lancer uniquement **Tester la SIM Robot**. Ne tester aucun montant avant ce succès.

**Autorisation nécessaire avant la prochaine action :**
Oui pour toute nouvelle modification, fusion ou extension fonctionnelle. Non pour exécuter le protocole de test terrain déjà documenté.

**Si oui, préciser exactement l’autorisation nécessaire :**
Communiquer le résultat de Gate 1 et, en cas d’échec, le code exact sans PIN ni secret ; autoriser ensuite soit la correction ciblée, soit, après tous les Gates réussis, la fusion explicite de la PR #4. Une autorisation séparée est requise avant toute modification Cloudflare/D1 ou avant le chantier des autres modules du cahier des charges.
