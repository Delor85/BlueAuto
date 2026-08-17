# B.I.R. v2.8.1 — APK permanente publiée

Date : 2026-08-17

## Autorisation exacte

Publication permanente autorisée pour :

- source applicative exacte : `eef53c4bf483ffc2557a57b0715561412f4c7e10`
- package : `com.profitloop.blueauto`
- versionName : `2.8.1`
- versionCode : `54`
- certificat permanent historique SHA-256 : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- sans déploiement Worker/D1
- sans fusion de PR #4

## Preuves du candidat exact

- run de validation exact : `32040847963`
- artifact exact : `9291927600` — `BIR-v2.8.1-exact-eef53c4-validation-ephemeral`
- SHA-256 APK de validation : `8d557602dc7da67b8024a97dd9298a56bc71fadb5fc1178dc544ec8131875c88`
- `verify-build` : SUCCESS
- Android 6 / API23 : SUCCESS
- Android 8 / API26 : SUCCESS
- le job standard Android 11 a rencontré une panne d'infrastructure GitHub codeload HTTP 429 avant exécution applicative
- run indépendant Android 11 / API30 utilisant le même APK exact : `32042171976` — SUCCESS

## APK permanente livrée

- fichier : `BIR-Blue-Infinity-Retail-v2.8.1-vc54-Permanent.apk`
- taille : `194272` octets
- SHA-256 : `bfcd4eea0d2d6ba85377afb51a7499be4cf2ded49e68a3afb3788a7e67d3183c`
- package : `com.profitloop.blueauto`
- versionName : `2.8.1`
- versionCode : `54`
- minSdk : `23`
- targetSdk : `34`
- signer : `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`
- certificat SHA-256 : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- RSA 4096
- v1 : true
- v2 : true
- v3 : true
- zipalign 4 : Verification successful
- signer count : 1

Les 22 entrées ZIP applicatives hors signatures ont un contenu SHA-256 identique entre l'APK exacte validée et l'APK permanente. Seule la couche de signature/packaging a été remplacée par la signature permanente historique.

## Continuité d'installation

La v2.8.0 permanente existante utilise le même package et le même certificat permanent. La v2.8.1 fait progresser `versionCode` de 53 à 54. Le chemin de recette est donc une mise à jour par-dessus l'application permanente existante, sans désinstallation préalable.

## Publication privée durable

Copies archivées dans la Library privée :

- `/Blue Magic/APK/BIR-Blue-Infinity-Retail-v2.8.1-vc54-Permanent.apk`
- `/Blue Magic/APK/BIR-v2.8.1-Permanent.sha256.txt`
- `/Blue Magic/APK/BIR-v2.8.1-Permanent-release-info.txt`
- `/Blue Magic/APK/BIR-v2.8.1-Permanent-verification.txt`

Aucun keystore, mot de passe, code propriétaire ou token n'est publié dans GitHub.

## Garde-fous préservés

- aucun déploiement Worker déclenché par cette publication ;
- aucune migration D1 déclenchée par cette publication ;
- aucune modification Cloudflare/D1 nécessaire pour l'APK ;
- PR #4 reste OPEN / NON MERGED ;
- le SHA applicatif de référence reste `eef53c4bf483ffc2557a57b0715561412f4c7e10` même si la branche reçoit ensuite des commits CI/documentation.

## Recette terrain recommandée

Installer l'APK v2.8.1 directement par-dessus la v2.8.0 permanente et vérifier dans cet ordre : conservation des comptes, GÉRER Android 6/8, TEST_NUMBER, Accessibilité/Robot, Remote, multi-SIM, bascule Blue↔MOCK↔ADMIN, verrouillage propriétaire après 30 minutes, FR/EN, puis une seule opération financière supervisée de faible montant.
