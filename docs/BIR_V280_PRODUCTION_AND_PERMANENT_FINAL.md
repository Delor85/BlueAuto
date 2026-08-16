# B.I.R. v2.8.0 — production activée et APK permanente finalisée

Date : 2026-08-16

## Ancrages immuables

- Application exacte autorisée : `4c24ded4e2053aa30640f654ddaf5ddf55908c20`
- Package : `com.profitloop.blueauto`
- versionName : `2.8.0`
- versionCode : `53`
- minSdk : `23`
- targetSdk : `34`
- Certificat permanent historique SHA-256 : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- PR #4 : doit rester OPEN / NON MERGED jusqu'à autorisation distincte.

## Validation exacte de l'application

Run GitHub Actions `31972497493` : SUCCESS.

- verify-build : SUCCESS
- Android 6 / API23 : SUCCESS
- Android 8 / API26 : SUCCESS
- Android 11 / API30 : SUCCESS
- APK de validation exacte SHA-256 : `753b1d81565f8260ba9a58965139078396b9f2b69bd273968d63976fbef73a8d`

Cette validation a contrôlé l'identité Android, le launcher B.I.R., la Release non-debuggable, les contrats historiques et v2.8, les tests Worker sans déploiement et le comportement de reprise Robot du harnais.

## Activation serveur autorisée — terminée

Source serveur exacte activée : `a6426433aad0972d6359574314737ba9cdf399c3`.

Run d'activation production : `31974344187` — SUCCESS.

Le workflow a vérifié avant mutation que la production servait encore `2.6.7-cloudflare`, que D1 était en ligne et que seules les migrations `0005` et `0006` étaient en attente. Une exportation de sécurité D1 a été effectuée sur le runner avant migration.

Résultat :

- D1 `0005_commission_policies_and_financial_quotes.sql` : APPLIQUÉE
- D1 `0006_owner_admin_control_and_audit.sql` : APPLIQUÉE
- Worker production : `2.8.0-cloudflare`
- Version de déploiement observée : `5489944f-e450-4a85-8f1c-237dd8aeca4c`
- Base D1 : online
- commissions : active
- commission_override : active
- owner_admin : active
- owner_mock_entitlement : active
- accounting : active
- tchoronko : active
- event_balance : active

Le bootstrap propriétaire ne publie dans GitHub que des empreintes SHA-256 des codes d'enrôlement. Les codes propriétaires en clair et le matériel de signature permanent ne doivent jamais être commités.

## ADMIN / MOCK

ADMIN et MOCK_OWNER sont des entitlements propriétaires séparés des rôles Blue DAE/DSM/POS. Ils sont liés à l'appareil et le token obtenu est protégé localement par AndroidKeyStore AES/GCM. L'ADMIN prépare et audite les actions de contrôle ; il ne contourne pas le PIN, le verrou sécurisé, la propriété SIM ni la readiness Robot.

## APK permanente v2.8.0

Le workflow GitHub de signature permanente `31974464670` a validé le SHA applicatif, la production v2.8, PR #4, l'identité application et tous les contrats, mais s'est arrêté à la lecture du keystore car les deux secrets de signature n'étaient pas présents dans l'environnement GitHub `production`.

Le matériel permanent historique déjà conservé dans l'espace privé du projet a ensuite été vérifié localement par empreinte avant utilisation. Le certificat correspond exactement à l'empreinte historique attendue.

L'APK permanente a été produite par re-signature de l'APK Release issue du run exact `31972497493`. Avant et après signature, les entrées ZIP non liées aux signatures ont été comparées : elles sont identiques. La re-signature n'a donc pas modifié le code, les ressources, le manifeste ni l'icône validés au SHA `4c24ded...`.

Livrable : `BIR-Blue-Infinity-Retail-v2.8.0-vc53-Permanent.apk`

- SHA-256 APK : `bd41ef60bc6dbcc60da87b93c3cf3ccb9fb9d3a872fe379e6c1ad55fd71aa25e`
- Taille : `190176` octets
- Certificat SHA-256 : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- Signature V1 : true
- Signature V2 : true
- Signature V3 : true
- V3.1/V4 : non requis
- zipalign `-c -v 4` : SUCCESS
- Release non-debuggable : conservée depuis l'APK exacte validée
- Launcher : `ic_launcher_bir`, conservé byte-for-byte dans les entrées non-signature

## Règle d'installation terrain

Installer la v2.8.0 permanente PAR-DESSUS l'application B.I.R./Blue Magic existante. Ne pas désinstaller d'abord. Le package et le certificat historiques sont conservés afin de permettre l'upgrade et de préserver les données locales.

Ordre de recette recommandé après mise à jour :

1. Ouvrir l'application et vérifier que l'icône B.I.R. apparaît dans le launcher.
2. Vérifier les comptes existants et les slots SIM.
3. TEST_NUMBER.
4. Solde propre et réutilisation de preuve récente.
5. Remote puis Robot.
6. Redémarrage téléphone avec profil Robot actif.
7. Verrou simple et insertion PIN ; confirmer qu'aucun verrou sécurisé n'est contourné.
8. Une transaction financière supervisée.
9. Taux DEFAULT, CHILD_SPECIFIC puis ONE_SHOT sur cas contrôlés.
10. Comptabilité locale.
11. Enrôlement MOCK_OWNER puis ADMIN propriétaire sur appareil autorisé.
12. ADMIN : snapshot, journal, contrôle Robot/Remote, libération de file et Tchoronko sur cas non financier avant toute assistance financière.

## Ce qu'il ne faut surtout pas modifier sans nouvelle autorisation

- Ne pas changer `com.profitloop.blueauto`.
- Ne pas changer de certificat de signature.
- Ne pas fusionner PR #4 implicitement.
- Ne pas introduire de contournement de verrou sécurisé ou de PIN.
- Ne pas rendre ADMIN ou MOCK accessible comme un rôle Blue ordinaire.
- Ne pas faire régresser le moteur de solde avec une preuve ancienne ou un message retardé.
- Ne pas exposer les codes propriétaires, keystore ou mot de passe dans GitHub, logs ou documentation.

## Point de reprise

Production : Worker `2.8.0-cloudflare`, D1 0005 + 0006 appliquées, run `31974344187` SUCCESS.

Application : SHA exact `4c24ded4e2053aa30640f654ddaf5ddf55908c20`, run exact `31972497493` SUCCESS.

APK permanente : SHA-256 `bd41ef60bc6dbcc60da87b93c3cf3ccb9fb9d3a872fe379e6c1ad55fd71aa25e`, certificat historique `f51e1d...b769b5`, V1/V2/V3 true.

Prochaine étape : recette terrain par mise à jour sans désinstallation, puis correction uniquement à partir des résultats observés.
