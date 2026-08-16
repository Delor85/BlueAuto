# B.I.R. v2.7.0 — état de livraison APK permanente

Date : 2026-08-16

## Source applicative autorisée

- Branche de finalisation : `feat/bir-v2-7-finalization`
- SHA applicatif exact autorisé : `c92e62e5f3a22369f99c3c2bfe04592abe18cb16`
- Package : `com.profitloop.blueauto`
- versionName : `2.7.0`
- versionCode : `51`
- minSdk : `23`
- targetSdk : `34`

La publication permanente est strictement une livraison APK. Elle n'autorise ni fusion de la PR #4, ni déploiement Worker, ni modification ou migration Cloudflare/D1.

## Validation fonctionnelle avant signature permanente

Le run GitHub Actions `31957020674` a validé le SHA applicatif correspondant avec les contrats historiques Blue Magic/B.I.R. et les contrats v2.7, puis des démarrages propres sur Android API 23, 26 et 30 (Android 6, 8 et 11).

Le compte propriétaire `MOCK` reste indépendant de `SU1`. Les dix régions nationales sont conservées et les opérations réelles de MOCK passent par les profils DAE effectivement appairés et leurs descendants autorisés.

## Signature permanente

Certificat historique attendu et obtenu :

`f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`

Le premier workflow de publication permanente `31958061520` a volontairement échoué fermé avant compilation permanente parce que les deux secrets Android de l'environnement GitHub Actions `production` étaient absents. Aucun APK permanent n'a été publié par ce run et aucune production serveur n'a été modifiée.

La clé historique a ensuite été récupérée uniquement depuis la sauvegarde privée ChatGPT Library `Blue Magic/Signature permanente/BlueMagic-permanent-release.keystore`, avec son mot de passe privé séparé. Ni la clé ni le mot de passe n'ont été ajoutés au dépôt GitHub, aux artefacts GitHub Actions, ni à ce document.

## APK permanente livrée

Fichier : `BIR-Blue-Infinity-Retail-v2.7.0-vc51-Permanent.apk`

- SHA-256 APK : `73a45610e3b881bb42f5d4a7f36fc29a94e425777f00a2dbbfbdb19df96f79e7`
- Taille : `158300` octets
- Package : `com.profitloop.blueauto`
- versionName : `2.7.0`
- versionCode : `51`
- Certificat SHA-256 : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- APK Signature Scheme v1 : `true`
- APK Signature Scheme v2 : `true`
- APK Signature Scheme v3 : `true`
- ZIP alignment 4 octets : `true`
- Debuggable : `false`

La vérification finale a été faite avec les outils Android officiels `apksigner`, `zipalign` et `aapt`. Tous les contenus ZIP applicatifs hors fichiers de signature sont identiques à ceux de l'APK Release de validation produite depuis le SHA autorisé ; seule la couche de signature/packaging a été remplacée par la signature permanente historique.

## Stockage privé

L'APK finale et ses fichiers de contrôle ont été sauvegardés dans la Library privée :

- `/Blue Magic/APK/BIR-Blue-Infinity-Retail-v2.7.0-vc51-Permanent.apk`
- `/Blue Magic/APK/BIR-v2.7.0-Permanent.sha256.txt`
- `/Blue Magic/APK/BIR-v2.7.0-Permanent-release-info.txt`
- `/Blue Magic/APK/BIR-v2.7.0-Permanent-verification.txt`

## Production serveur

État conservé :

- PR #4 : OPEN / NON MERGED
- Worker : aucun déploiement réalisé par cette livraison
- Cloudflare/D1 : aucune modification, aucune migration réalisée par cette livraison

## Reprise obligatoire

Avant toute prochaine modification :

1. Vérifier en direct le HEAD de `feat/bir-v2-7-finalization`.
2. Vérifier que le SHA applicatif livré reste `c92e62e5f3a22369f99c3c2bfe04592abe18cb16`.
3. Vérifier que la PR #4 est toujours ouverte et non fusionnée.
4. Vérifier les derniers GitHub Actions et distinguer le run fonctionnel vert `31957020674` du run permanent GitHub `31958061520`, arrêté faute de secrets.
5. Conserver le package `com.profitloop.blueauto`, la signature historique et le mécanisme PIN/Remote/Robot existant.
6. Ne jamais publier ni committer la clé permanente ou son mot de passe.
7. Toute future migration D1, tout déploiement Worker ou toute fusion de PR nécessite une autorisation explicite distincte.
