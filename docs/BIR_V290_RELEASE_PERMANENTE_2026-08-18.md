# B.I.R. / Blue Magic — v2.9.0 permanente — état final de lancement

Date : 2026-08-18

## 1. Ancre applicative immuable

- Branche de convergence : `feat/bir-v2-9-final-convergence`.
- SHA applicatif exact validé : `9752441af955dc9b4643802234fb2484afadf11f`.
- Android : `applicationId com.profitloop.blueauto`.
- `versionName 2.9.0`.
- `versionCode 55`.
- `minSdk 23` / Android 6 minimum.
- `targetSdk 34`.
- Deux modes effectifs uniquement : `REMOTE` et `ROBOT`.
- Aucun troisième mode effectif.

Ce SHA reste l'ancre du code applicatif. Tout commit ultérieur sur la branche portant uniquement de la documentation ne change pas cette ancre.

## 2. Convergence complète

- GitHub Actions run : `32163988511` — **SUCCESS**.
- Contrats hérités 2.6.8 → 2.8.1 : verts.
- Contrats 2.9 offline/Relay/cockpit hiérarchique : verts.
- Worker/D1 dry-run : vert.
- Java/Gradle : vert.
- Tests unitaires : verts.
- APK Release : construite.
- Identité package/version : conforme.

## 3. Matrice Android sur un APK exact unique

- GitHub Actions run : `32164871871` — **SUCCESS**.
- Artefact exact : `BIR-v2.9.0-Android-Matrix-Exact`.
- SHA-256 APK de validation : `bf3be566265c6fbe0fefc3c8990d419f15894376e3ef0640f6e598889c5b591f`.
- Android 6 / API 23 : **SUCCESS** — installation, lancement, redémarrage, contrôle de crash.
- Android 8 / API 26 : **SUCCESS** — même APK exact.
- Android 11 / API 30 : **SUCCESS** — même APK exact.

Ces validations sont des validations automatisées sur émulateurs ; elles ne remplacent pas les essais USSD réels sur SIM terrain.

## 4. Cloudflare production

- Activation finale GitHub Actions : run `32166944802` — **SUCCESS**.
- Worker : `blue-magic-api`.
- Version API live : `2.9.0-cloudflare`.
- Cloudflare Worker Version ID : `da9fa354-e28b-42fa-beb6-34e8d95e5d27`.
- D1 `blue-magic` : online.
- Migrations additives `0007` et `0008` appliquées ; après activation : **No migrations to apply**.
- Tables vérifiées : `offline_events`, `relay_identities`, `ops_escalations`.
- Health live validé : `super_admin`, `free_ops_cockpit`, `dae_pro_free`, `region_national_ops_free`, `offline_sync`, `bir_relay` actifs.
- Modes annoncés par le serveur : `REMOTE`, `ROBOT` uniquement.

Un premier essai de déploiement avait échoué uniquement parce que l'URL de health-check CI était vide ; le rollback automatique du Worker précédent avait réussi avant la correction. La relance finale ci-dessus est entièrement verte.

## 5. APK permanente officielle

- Fichier : `BIR-Blue-Infinity-Retail-v2.9.0-vc55-Permanent.apk`.
- Taille : `219154` octets.
- SHA-256 : `a608f56d19536d3dfeed50b69b710e3bca0404f6514e48df996f8dbd1d337ccc`.
- Package : `com.profitloop.blueauto`.
- versionCode : `55`.
- versionName : `2.9.0`.
- Non debuggable : oui.
- zipalign 4 : vérifié.

### Signature permanente historique

- Certificat SHA-256 : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`.
- DN : `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`.
- RSA : 4096 bits.
- Signataires : 1.
- APK Signature Scheme v1 : true.
- APK Signature Scheme v2 : true.
- APK Signature Scheme v3 : true.
- v3.1 / v3.2 / v4 : non requis pour cette continuité de release.

### Continuité de mise à jour

La v2.8.1 permanente et la v2.9.0 permanente ont :

- le même package `com.profitloop.blueauto` ;
- le même certificat permanent exact ;
- un versionCode croissant `54 → 55`.

L'identité de mise à jour est donc préservée ; ne pas désinstaller volontairement l'application permanente précédente avant mise à jour terrain, sauf test de clean install explicitement séparé.

## 6. Preuve d'intégrité du binaire permanent

Comparaison entre l'APK exacte de la matrice Android et l'APK permanente :

- entrées ZIP applicatives non liées à la signature : `26` ;
- entrées manquantes : `0` ;
- entrées ajoutées : `0` ;
- entrées modifiées : `0`.

Seules les informations de signature/packaging ont changé. Le code et les ressources validés sur API 23/26/30 sont donc identiques dans l'APK permanente.

## 7. Fonctionnalités 2.9 gratuites et hiérarchie

Toutes les fonctions suivantes sont incluses gratuitement dans la v2.9 :

- DAE Pro pour DAE ;
- Continuity / Relay ;
- Fleet Health ;
- Audit & Proof ;
- Rescue / SAV ;
- Treasury Forecast ;
- Smart Commission ;
- cockpit opérationnel et prévisionnel simplifié ;
- Région Control et National Ops pour ADMIN ;
- SUPERADMIN unique pour la gouvernance sensible.

Règle opérationnelle :

1. PoS → son DSM en premier recours.
2. DSM → son DAE lorsque l'incident exige une escalade.
3. DAE → ADMIN pour les cas régionaux/nationaux ou les situations encore non résolues.
4. Le DAE ne micro-gère pas normalement les PoS ; il vient au secours du DSM lorsque la gravité le justifie.
5. ADMIN / SUPERADMIN clôturent les escalades autorisées avec audit.

## 8. Protection PIN / secrets

- Le PIN Blue reste local au Robot dans le stockage sécurisé Android.
- Aucun dashboard, Relay, endpoint, ADMIN ou SUPERADMIN ne peut récupérer le PIN Blue en clair.
- Les commandes distantes refusent les champs ressemblant à PIN/password/secret/token.
- Aucun keystore, mot de passe de signature, clé privée, secret propriétaire ou token n'est enregistré dans ce document.
- La clé permanente reste conservée uniquement dans `/Blue Magic/Signature permanente`.

## 9. Offline-first et Relay

- Robot offline-first pour les actions pouvant être réellement exécutées localement avec la SIM et les données déjà disponibles.
- Anti-double-transaction prioritaire : les commandes Remote financières gardent la fence serveur irréversible avant composition.
- Résultat local durable puis synchronisation ultérieure.
- Relay : événements/résultats de continuité uniquement.
- Transports : Wi‑Fi Direct + Bluetooth.
- Enveloppes Relay signées ; contrôle d'identité serveur ; idempotence par `event_id`.
- Aucun ordre financier n'est relayé comme commande exécutable.
- Aucun fallback SMS n'est ajouté ; `SEND_SMS` reste absent.

## 10. Hors périmètre volontaire de v2.9

- B.I.R. Academy Offline : non activé pour l'instant.
- API Business : non activé pour l'instant.
- expansion/redimensionnement national : non lancé ; architecture seulement préparée.
- PR #4 : reste explicitement hors fusion sans autorisation distincte.

## 11. Tests terrain encore nécessaires après installation réelle

La release permanente est produite et vérifiée, mais les tests physiques suivants restent à réaliser avec les vraies SIM :

1. mise à jour en place depuis v2.8.1 sans désinstallation ;
2. Android 6, Android 8, Android 11 physiques ;
3. Remote → Robot et résultat retour ;
4. Robot local avec Internet ;
5. Robot local sans Internet puis resynchronisation ;
6. coupure réseau pendant exécution sans double transaction ;
7. reboot avec reprise de file ;
8. multi-SIM et indépendance des files ;
9. accessibilité désactivée puis reconnectée ;
10. verrou simple et verrou sécurisé selon limites Android ;
11. Relay Wi‑Fi Direct réel ;
12. Relay Bluetooth réel ;
13. doublon Relay / idempotence ;
14. soldes DAE/DSM en trois parties et solde PoS unique ;
15. cockpit PoS→DSM→DAE→ADMIN et escalades graves ;
16. contrôle SUPERADMIN sans exposition PIN ;
17. une seule transaction financière supervisée de faible montant après TEST_NUMBER.

## 12. ÉTAT DU PROJET APRÈS CETTE ÉTAPE

- Version : `2.9.0`.
- Branche applicative : `feat/bir-v2-9-final-convergence`.
- SHA applicatif validé : `9752441af955dc9b4643802234fb2484afadf11f`.
- État GitHub : convergence et matrice Android vertes ; PR déclencheurs à ne pas fusionner ; PR #4 non fusionnée.
- État Cloudflare : Worker `2.9.0-cloudflare` actif ; D1 online, migrations jusqu'à `0008`.
- APK : `BIR-Blue-Infinity-Retail-v2.9.0-vc55-Permanent.apk` / code 55 / SHA-256 `a608f56d19536d3dfeed50b69b710e3bca0404f6514e48df996f8dbd1d337ccc`.
- Problème traité : lancement complet v2.9 offline/Relay + cockpit gratuit + hiérarchie + SuperAdmin.
- Cause des derniers blocages : harnais CI / configuration de secrets et health-check, pas régression fonctionnelle du noyau.
- Correction : CI fail-closed, migrations additives, health-check canonique, signature permanente locale avec clé historique, vérifications Android officielles.
- Tests exécutés : contrats hérités et 2.9, Worker/D1 dry-run, tests Java, assembleRelease, API 23/26/30, production health, apksigner/aapt/zipalign, comparaison ZIP.
- Résultats : verts pour les gates automatisés ; terrain USSD réel à effectuer.
- Acquis : production 2.9 + APK permanente compatible avec l'identité historique.
- Reste à faire : recette physique terrain listée ci-dessus puis corrections additives uniquement si un défaut réel est observé.
- NE PAS modifier : package, certificat, anti-double-finance, PIN local, hiérarchie, Remote acquis, files par SIM, deux modes seulement, Relay événements seulement, pas SMS fallback, PR #4 sans autorisation.
- Régression possible : aucune détectée par les tests automatisés ; risques terrain Android/USSD/constructeur encore à valider physiquement.
- Autorisation nécessaire avant prochaine action : non pour la recette/diagnostic ; oui avant toute nouvelle mutation de production hors corrections explicitement autorisées ou expansion/redimensionnement.

## 13. Procédure obligatoire de sauvegarde et reprise dans un autre chat

1. Lire d'abord ce fichier `docs/BIR_V290_RELEASE_PERMANENTE_2026-08-18.md`.
2. Vérifier ensuite le SHA applicatif `9752441af955dc9b4643802234fb2484afadf11f` sur GitHub.
3. Vérifier les runs `32163988511`, `32164871871` et `32166944802`.
4. Vérifier le Worker live `/api?action=health` avant toute mutation.
5. Vérifier D1 et confirmer qu'aucune migration inattendue n'est en attente.
6. Vérifier l'APK permanente par son SHA-256 et le certificat permanent historique.
7. Lire les résultats de recette physique les plus récents avant de modifier le moteur USSD.
8. Toute correction doit être additive et repasser les anciens contrats avant release.
9. Ne jamais reconstruire l'historique à partir de la conversation seule : GitHub → Actions → Cloudflare/D1 → APK/artefacts → conversation.

### Prompt prêt à copier

`BLUE MAGIC / B.I.R. — REPRISE v2.9. Lis d'abord docs/BIR_V290_RELEASE_PERMANENTE_2026-08-18.md. Ancre applicative : 9752441af955dc9b4643802234fb2484afadf11f. Production : Worker 2.9.0-cloudflare, D1 jusqu'à 0008. APK permanente : com.profitloop.blueauto, versionCode55/versionName2.9.0, SHA256 a608f56d19536d3dfeed50b69b710e3bca0404f6514e48df996f8dbd1d337ccc, certificat SHA256 f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5. Runs : convergence 32163988511, Android API23/26/30 32164871871, production 32166944802. Deux modes REMOTE/ROBOT seulement ; pas SMS fallback ; Relay Wi-Fi Direct/Bluetooth événements uniquement ; PIN jamais serveur/Relay/dashboard ; PoS→DSM→DAE→ADMIN ; DAE Pro gratuit ; Région/National pour Admin ; SuperAdmin unique ; Academy/API Business ignorés ; pas d'expansion nationale. Commence par vérifier GitHub/Actions/Cloudflare et les résultats terrain avant toute mutation.`
