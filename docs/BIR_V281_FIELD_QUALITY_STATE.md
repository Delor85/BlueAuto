# B.I.R. v2.8.1 — état terrain, permanence Robot/Remote et montée en charge

Date : 2026-08-17

## 1. Ancrage applicatif exact

- Dépôt : `Delor85/BlueAuto`
- Branche de travail : `feat/bir-v2-8-operations-admin`
- **SHA applicatif exact v2.8.1 : `eef53c4bf483ffc2557a57b0715561412f4c7e10`**
- Package historique : `com.profitloop.blueauto`
- versionName : `2.8.1`
- versionCode : `54`
- minSdk : `23` / Android 6
- targetSdk : `34`
- Certificat permanent historique attendu : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- **Aucune signature permanente v2.8.1 n'est autorisée par le présent chantier.** Une nouvelle autorisation exact-SHA visant `eef53c4...` est obligatoire avant publication permanente.

## 2. Retour terrain traité

Les photos et tests terrain du 17 août 2026 ont confirmé que B.I.R. est très avancée mais nécessitait un durcissement sur cinq points : reconnexion Accessibilité/Robot, observation Remote plus continue, accès `GÉRER` sur Android 6/8, bilinguisme supplémentaire, et coexistence des espaces propriétaires ADMIN/MOCK avec les comptes Blue normaux.

### 2.1 Accessibilité / Robot

Android reste l'unique autorité qui peut accorder ou retirer le service d'Accessibilité. B.I.R. ne tente pas de modifier `Settings.Secure`, de s'auto-octroyer une autorisation, ni de contourner un verrou sécurisé.

La v2.8.1 distingue désormais :

- permission Accessibilité désactivée par Android ;
- permission accordée mais service momentanément déconnecté/reconnecté ;
- service réellement connecté.

Pour les commandes nécessitant le PIN, B.I.R. n'exécute pas la composition financière tant que le service n'est pas réellement connecté. Le lease non exécuté est libéré proprement, la file et l'intention Robot sont conservées, puis la reprise est déclenchée immédiatement lorsque `BlueAccessibilityService.onServiceConnected()` est rappelé par Android.

`TEST_NUMBER` et les commandes directes ne nécessitant pas le PIN conservent leur chemin direct historique.

### 2.2 Remote toujours attentif mais sans finance silencieuse

`RobotService` maintient désormais un observateur Remote en tâche de fond pour les profils REMOTE appairés :

- heartbeat périodique ;
- snapshot `dashboard` adaptatif ;
- cache local court pour rendre l'interface immédiatement réactive ;
- backoff réseau par profil ;
- reprise après boot/package replacement via le watchdog commun.

Cet observateur est **strictement en lecture** : il n'appelle ni `lease_command`, ni `create_command`, ni USSD et ne peut donc déclencher une opération financière sans demande/confirmation utilisateur.

Le polling d'environ 15 s reste un durcissement terrain pour quelques profils sur un téléphone ; **il ne doit jamais devenir le mécanisme national à 10 régions**. La montée en charge nationale doit passer à une architecture événementielle (WebSocket/DO hibernation, D1 indexée, Queue sélective, R2, push optionnel).

### 2.3 Android 6 / Android 8 : GÉRER

Une barre native de secours apparaît désormais sur API <= 26 indépendamment du WebView. `☰ GÉRER` est placé en premier, donc en haut à gauche, avec `COMPTES` à côté. Le shell moderne reste inchangé sur les versions Android plus récentes.

### 2.4 ADMIN / MOCK dans la liste des comptes

Après enrôlement, `MOCK` et `ADMIN` apparaissent comme comptes virtuels propriétaires dans le même sélecteur que les profils DAE/DSM/PoS. Il est possible de passer :

`DAE/DSM/PoS → MOCK → ADMIN → profil Blue`

sans supprimer les comptes et sans rendre ADMIN/MOCK des rôles Camtel. Les jetons propriétaires restent séparés et protégés localement.

Quitter momentanément un espace propriétaire ne détruit plus la session authentifiée. En revanche, **après 30 minutes sans interaction**, la session propriétaire est verrouillée et le code doit être fourni à nouveau avant de réouvrir MOCK ou ADMIN.

### 2.5 Bilinguisme

Le dictionnaire FR/EN a été élargi pour les états, menus, autorisations, synchronisation, comptes, soldes, activités et sessions propriétaires. Les chaînes opérateur/Camtel, codes USSD, identifiants techniques et textes qui doivent impérativement rester en français ne sont pas forcés artificiellement en anglais.

## 3. Fichiers applicatifs principaux modifiés au SHA exact

- `app/build.gradle`
- `app/src/main/java/com/profitloop/blueauto/ApiClient.java`
- `app/src/main/java/com/profitloop/blueauto/AppConfig.java`
- `app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java`
- `app/src/main/java/com/profitloop/blueauto/RobotService.java`
- `app/src/main/java/com/profitloop/blueauto/BootReceiver.java`
- `app/src/main/java/com/profitloop/blueauto/MainActivity.java`
- `app/src/main/assets/app.js`
- `app/src/main/assets/control-tower-v280.js`
- contrats de compatibilité historiques adaptés à l'identité v2.8.1 et aux nouveaux invariants propriétaires ;
- `app/src/test/v281-field-quality-contract.mjs`.

Aucun fichier `cloudflare/` n'est modifié par le SHA applicatif v2.8.1 relativement à l'ancrage serveur v2.8 actuellement en production.

## 4. Validation CI

### Convergence applicative

Run `32039853267` : **SUCCESS**.

Couvre notamment : contrats historiques, contrat v2.8.1, syntaxe JavaScript, tests Java/Gradle, `assembleRelease`, package/version, Release non-debuggable et APK de validation éphémère.

### Validation exacte du SHA applicatif `eef53c4...`

Run `32040847963` :

- `verify-build` : **SUCCESS** ;
- Android 6 / API23 : **SUCCESS** ;
- Android 8 / API26 : **SUCCESS** ;
- Android 11 / API30 dans le harnais standard : échec d'infrastructure **avant exécution de l'app**, GitHub `codeload.github.com` répondant HTTP 429 au téléchargement d'actions tierces.

Pour séparer cette panne GitHub de l'application, le même APK exact a été testé avec un harnais indépendant des actions externes :

- run manuel Android 11 / API30 `32042171976` : **SUCCESS** ;
- APK exact Artifact `9291927600` ;
- SHA-256 APK de validation : `8d557602dc7da67b8024a97dd9298a56bc71fadb5fc1178dc544ec8131875c88` ;
- installation, lancement `com.profitloop.blueauto/.MainActivity`, versionName `2.8.1`, versionCode `54` et absence de crash vérifiés.

Ainsi, le même candidat exact `eef53c4...` est validé par CI sur Android 6, Android 8 et Android 11.

## 5. Production — inchangée par ce chantier applicatif

- Worker production : `2.8.0-cloudflare`
- D1 : migrations `0005` + `0006` déjà appliquées
- aucun nouveau déploiement Worker ;
- aucune nouvelle migration D1 ;
- aucun changement de secret serveur ;
- aucune fusion de PR #4.

La PR #4 doit rester **OPEN / NON MERGED** jusqu'à autorisation explicite distincte.

## 6. Architecture "mode saturé" retenue pour la planification

Le document de capacité associé est :

`BIR-v2.8.1-Architecture-Saturee-Qualite-Cout-2026-08-17.docx` / PDF correspondant.

Hypothèses de référence, à remplacer progressivement par des métriques terrain :

- 1 DAE complet : 1 DAE + 10 DSM + 200 PoS = 211 nœuds ;
- 1 Région : 20 cellules DAE = 4 220 nœuds ;
- 3 Régions : 12 660 nœuds ;
- 10 Régions : 42 200 nœuds.

Un polling national à 15 s ferait exploser inutilement le volume : environ 1,2 M requêtes/jour pour une cellule DAE et environ 243 M requêtes/jour pour 10 régions selon cette hypothèse.

Cible nationale :

- Worker stateless léger : authentification, idempotence, routage ;
- D1 : ledger financier + état courant indexé + agrégats pré-calculés ;
- Durable Objects shardés par cellule DAE / sous-ensemble régional pour présence, ordre local et fanout, avec WebSocket hibernation ;
- Queue uniquement pour side-effects durables, réconciliation et absorption de pics ;
- R2 pour preuves/audits historiques compressés ;
- FCM optionnel comme réveil gratuit sur appareils GMS, jamais comme source de vérité ;
- fallback adaptive pull pour anciens Android/non-GMS ;
- backoff + jitter, séquences monotones, idempotency keys, DLQ, circuit breakers et mode dégradé ;
- sous saturation : sacrifier d'abord la fraîcheur du dashboard, jamais l'intégrité financière.

## 7. Ordres de grandeur de coût de planification

Sous les hypothèses optimisées documentées (et non comme devis garanti), le plan vise environ :

- 1 DAE complet : ~5 USD/mois, soit ~2 828 FCFA ;
- 1 Région : ~5,36 USD/mois, soit ~3 031 FCFA ;
- 3 Régions : ~10,34 USD/mois, soit ~5 846 FCFA ;
- 10 Régions : ~32,52 USD/mois, soit ~18 394 FCFA.

Le taux de travail utilisé dans le document est 1 USD = 565,548 XAF au 17/08/2026. Ces coûts devront être recalculés avec les métriques `rows_read`, `rows_written`, Queue ops, événements métier, reconnexions et CPU réellement mesurés.

## 8. Produits complémentaires prioritaires

Priorité faible coût / forte valeur potentielle :

1. **B.I.R. Insight** : alertes anomalies, synthèses DAE/DSM/région et ruptures/retards ;
2. **B.I.R. Audit & Proof** : dossiers de preuve, exports SAV/litiges et archivage R2 ;
3. **B.I.R. Fleet Health** : santé Robot/SIM/appareil/batterie/réseau ;
4. B.I.R. Rescue : diagnostic guidé et assistance premium ;
5. B.I.R. Treasury Forecast : prévision de besoins d'approvisionnement ;
6. B.I.R. Smart Commission : simulation de taux/marges avant validation ;
7. B.I.R. Academy : micro-formation offline ;
8. B.I.R. API Business : connecteurs compta/ERP/SAV ;
9. White-label/multi-opérateur seulement après validation juridique/commerciale.

Ces produits ne doivent pas introduire de finance silencieuse ni mélanger commissions Camtel/Blue et revenus commerciaux B.I.R.

## 9. Recette terrain obligatoire avant publication permanente

1. Android 6 : GÉRER en haut à gauche, COMPTES, navigation, pas de chevauchement.
2. Android 8 : mêmes contrôles + Remote/Robot.
3. Android 11 : comptes/SIM, Remote, Robot, synchronisation.
4. Couper/revenir de l'Accessibilité : Robot logique conservé, file conservée, aucune finance tant que runtime non connecté, reprise automatique au retour.
5. Générer un événement enfant et vérifier sa remontée Remote sans approbation financière automatique.
6. Basculer profil Blue ↔ MOCK ↔ ADMIN ↔ profil Blue.
7. Laisser MOCK/ADMIN inactif >30 min et confirmer la nouvelle demande de code.
8. Vérifier FR puis EN sur écrans clés sans altérer les chaînes Camtel/USSD.
9. Refaire TEST_NUMBER puis une seule transaction financière supervisée de faible montant.
10. Redémarrer les téléphones et vérifier reprise Remote/Robot et isolation multi-SIM.

## 10. Point de reprise obligatoire

AVANT DE MODIFIER LE PROJET :

1. lire le présent fichier et `docs/BIR_V280_PRODUCTION_AND_PERMANENT_FINAL.md` ;
2. considérer `eef53c4bf483ffc2557a57b0715561412f4c7e10` comme **SHA applicatif v2.8.1 exact validé** ;
3. vérifier en direct la branche, la PR #4 et les Actions ;
4. ne pas déployer Worker/D1 pour ces correctifs applicatifs ;
5. ne pas fusionner PR #4 sans autorisation distincte ;
6. ne pas signer une APK permanente v2.8.1 sans autorisation exact-SHA séparée visant `eef53c4...`, versionCode54 et certificat historique ;
7. ne jamais exposer keystore, mot de passe, codes propriétaires ou tokens ;
8. préserver tous les acquis Remote/Robot, multi-SIM, PIN/verrou simple, preuve/solde chronologique, commissions, ADMIN/MOCK et compatibilité Android 6+.
