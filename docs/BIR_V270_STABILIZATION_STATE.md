# B.I.R. / Blue Magic — état de stabilisation v2.7.0

Date : 2026-08-16

## 1. Point de départ vérifié

- Produit commercial : **B.I.R. — Blue Infinity Retail**, moteur historique **Blue Magic**.
- Package Android protégé : `com.profitloop.blueauto`.
- Branche source vérifiée avant mutation : `feat/bir-v2-6-10-control-tower`.
- HEAD propre/documenté vérifié : `f1e9f3dad5c892dedcbda0c85455a418ecf76633`.
- Ancrage métier v2.6.10 : `ba02cb77583a94bcc0917a39c34c4b3fb950914a`.
- Run complet de référence : `31947181283` — SUCCESS.
- APK de référence : versionCode 50 / versionName 2.6.10 / SHA-256 `629c00caeeaf10c128c0095aa319ad78a160f39363b9e66a6ace57a2d1161943`.
- Certificat permanent protégé : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`.
- Production au début du chantier : Worker v2.6.7 + D1 jusqu’à `0004`; migration `0005` et Worker v2.6.10 non déployés.
- PR #4 : OPEN / NON MERGED.

## 2. Branche v2.7

Branche : `feat/bir-v2-7-stabilization` créée depuis le HEAD exact v2.6.10 ci-dessus.

Commit source v2.7 : `16d45ed5fbaca6adb6b9a22067ffa15c09dcbd16` — `feat: stabilize BIR v2.7 UI and legacy-server compatibility`.

Cette branche est additive. Elle ne réécrit pas le moteur financier, le moteur Remote/Robot, la file multi-SIM, le package, le PIN Keystore ni les règles de verrouillage.

## 3. Retour terrain traité

### 3.1 Interface

Le design v2.7 adapte l’interface au visuel B.I.R. validé : bleu nuit, étoiles discrètes, identité B.I.R. centrée, carte de statut Camtel, action prioritaire or, six modules principaux, activité et dock central lumineux. Les données affichées restent réelles : aucun faux chiffre de démonstration n’est introduit.

### 3.2 Saisie invisible

Les champs reçoivent explicitement une couleur de fond claire, un texte bleu nuit, `-webkit-text-fill-color`, un curseur visible et des placeholders contrastés. Le dock reste présent mais devient compact pendant la saisie afin de ne plus masquer le formulaire au-dessus du clavier.

### 3.3 « Action API inconnue » au démarrage

Cause : la couche v2.6.10 demandait automatiquement `commission_policy` au chargement alors que la production est volontairement restée sur le Worker v2.6.7. Le démarrage appelait donc un endpoint que le serveur actif ne connaît pas.

Correction v2.7 : aucune politique de commission n’est appelée au démarrage. L’application interroge d’abord `health`, lit la version du Worker et n’appelle les endpoints de commission que si le serveur est au moins v2.6.10. Sur le Worker v2.6.7, les boutons de taux restent sûrs et affichent une explication locale sans mutation ni popup `file://` d’API inconnue.

### 3.4 Taux de commission

- validation locale stricte de 0 à 50 %;
- taux par défaut DAE/DSM et exception enfant conservés;
- aucune écriture si le serveur actif ne possède pas encore les endpoints;
- une fois migration `0005` + Worker compatible déployés sous autorisation séparée, les mêmes contrôles appellent `commission_set_default`, `commission_set_child` et `commission_policy`.

## 4. Acquis protégés

Ne pas régresser :

1. insertion PIN sous verrou Android simple/non sécurisé validée terrain;
2. aucun contournement d’un verrou Android sécurisé;
3. package `com.profitloop.blueauto` et certificat permanent historique;
4. Remote/Robot et changement de mode;
5. multi-comptes et multi-SIM avec isolation des files;
6. Test numéro, Achat, Vente, Approvisionnement, confirmations et contrôle du pop-up Camtel;
7. preuves de solde, réutilisation intelligente et lecture du solde enfant;
8. annulation avant composition et FIFO;
9. Accessibilité uniquement quand nécessaire à la transaction financière;
10. KYC, Tchoronko/compte fantôme, Bottom-Up, créances, mercenaires, sandbox et autres modules déjà présents dans le code, sans prétendre que les sous-modules nécessitant un serveur plus récent sont actifs en production.

## 5. Version Android préparée

- versionName : `2.7.0`
- versionCode : `51`
- minSdk : `23` (Android 6)
- targetSdk : `34`
- applicationId : `com.profitloop.blueauto`

Une CI v2.7 dédiée compile uniquement une APK de validation avec une clé éphémère. Elle ne publie pas l’APK permanente et ne touche pas Cloudflare/D1.

## 6. Production

**Aucun déploiement de production n’est autorisé par ce commit.**

Restent séparément soumis à autorisation explicite :

- application de la migration D1 `0005_commission_policies_and_financial_quotes.sql`;
- déploiement d’un Worker compatible commissions;
- publication de l’APK permanente depuis le SHA exact v2.7 avec le certificat protégé;
- fusion de PR.

## 7. Tests obligatoires après le commit

CI :

- `npm run check` Cloudflare;
- `node --check` sur les scripts Android/Web;
- suite finance v2.6.x et contrats v2.6.8;
- `v270-ui-contract.mjs`;
- tests unitaires Android;
- `assembleRelease` de validation;
- `zipalign`, `apksigner`, versionCode/versionName.

Terrain après APK permanente :

1. Android 6, 8 et 11 : mise à jour sans désinstallation;
2. vérifier absence de popup « Action API inconnue » au premier lancement;
3. vérifier lisibilité des champs pendant la frappe;
4. vérifier dock compact pendant clavier puis dock complet après fermeture;
5. vérifier Remote/Robot et Test numéro;
6. vérifier Achat/Vente/Approvisionnement sans régression;
7. vérifier PIN sous verrou simple;
8. vérifier synchronisation de plusieurs profils/SIM;
9. vérifier lecture distante du solde enfant sur le Remote;
10. après autorisation serveur seulement : vérifier taux par défaut, taux enfant et taux ponctuel.

## 8. Procédure obligatoire de reprise

Toute nouvelle conversation doit lire dans cet ordre :

1. `/Blue Magic/BIR-REPRISE-COMPLETE-v2.6.10-2026-08-16.md`;
2. `docs/BIR_V270_STABILIZATION_STATE.md`;
3. `docs/BIR_V2610_CONTROL_TOWER_STATE.md`;
4. `docs/BIR_V269_FUNCTIONAL_STATE.md`;
5. les reprises v2.6.8 et `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`;
6. vérifier ensuite GitHub en direct : branche, HEAD, PR, Actions et artefacts;
7. vérifier la production Cloudflare/D1 avant toute mutation serveur;
8. ne jamais considérer une conversation ChatGPT comme source de vérité supérieure à GitHub, Actions, Cloudflare/D1 et les APK vérifiés.

À la fin de chaque étape, consigner obligatoirement : Version, Branche, Commit, GitHub/PR/Actions, Cloudflare/D1, APK/versionCode/SHA/certificat, problème, cause, correction, fichiers, tests, résultats, acquis, reste à faire, interdictions, point de reprise, régression et autorisation nécessaire.
