# B.I.R. v2.8.0 — état de reprise opérations / ADMIN

Date : 2026-08-16

## Ancrage exact validé

- Branche de travail : `feat/bir-v2-8-operations-admin`
- SHA applicatif exact validé : `73b2623446457b698013aa3cef4406abfbf7b885`
- Package : `com.profitloop.blueauto`
- versionName : `2.8.0`
- versionCode : `53`
- minSdk : `23` / Android 6
- targetSdk : `34`
- Run de validation exacte : `31971788221` — SUCCESS
- Android 6 / API23 : SUCCESS
- Android 8 / API26 : SUCCESS
- Android 11 / API30 : SUCCESS
- APK de validation éphémère SHA-256 : `255e3361f1c5178701d0b2574ca4d19b4a3a057bd5e617e23ba2df350e327e45`
- Certificat de validation éphémère SHA-256 : `dd9d61e7cbdb680ad29d05e3f9333614ed579290e36a3d5ba3278f231f4a3b3c`
- Artefact de validation : `BIR-v2.8.0-validation-ephemeral`, ID `9269996806`
- Signature de validation : V1=true, V2=true, V3=false. Cette signature est volontairement éphémère et NE DOIT PAS être livrée comme APK permanente.

## Corrections et extensions intégrées

### Icône Android

Le manifeste Android référence maintenant `@drawable/ic_launcher_bir` pour `android:icon` et `android:roundIcon`. Le dessin reprend la géométrie du logo B.I.R. déjà présent dans l'application : infini cyan à gauche, infini doré à droite, I central doré, B et R intégrés. L'ancienne tête Android n'est plus l'icône déclarée du launcher.

### Bilingue FR / EN

La couche v2.8 étend la traduction du cœur visible de l'interface et applique dynamiquement le vocabulaire FR/EN aux composants ajoutés. Les identifiants internes historiques nécessaires aux parseurs opérateur ne sont pas renommés aveuglément. Les libellés visibles utilisent Blue.

### Commissions — règle définitive

Trois niveaux sont distincts :

1. `DEFAULT` persistant : taux réseau fixé par le DAE pour ses DSM ou par le DSM pour ses PoS.
2. `CHILD_SPECIFIC` persistant : exception propre à un seul enfant jusqu'à modification ou suppression par le supérieur.
3. `ONE_SHOT` éphémère : taux choisi pour une seule transaction au moment de la confirmation.

Priorité : `ONE_SHOT > CHILD_SPECIFIC > DEFAULT`.

Le taux ponctuel est maintenant consommé non seulement après la création de la commande, mais également en cas d'annulation ou d'erreur de prévisualisation. Il ne peut donc pas contaminer la transaction suivante.

La persistance inter-appareils des deux politiques durables est préparée par la migration source `0005_commission_policies_and_financial_quotes.sql`, mais elle n'est pas active en production tant que D1 0005 et le Worker correspondant n'ont pas reçu une autorisation distincte.

### Moteur de solde événementiel

`balance-engine-v280.js` conserve la dernière preuve Blue sûre, applique les mouvements financiers confirmés postérieurs et classe le résultat en `CERTIFIED`, `RECALCULATED` ou `UNCERTAIN`. Une preuve récente ou un solde recalculable évite une nouvelle interrogation USSD; un événement ambigu, inconnu ou trop ancien force une recertification. L'ancienne règle de chronologie reste prioritaire : un résultat financier retardé sans horodatage opérateur fiable ne peut pas faire régresser une preuve plus récente.

### Tchoronkos

Les DSM / PoS pré-enrôlés `TCHORONKO_SHADOW` sont intégrés à la vue réseau DAE/DSM. Le mécanisme réutilise les données et routes déjà préparées par `shadow_accounts`, `shadow_enroll` et `platform_snapshot` au lieu de créer une seconde hiérarchie parallèle.

### Comptabilité générale

Un tableau de comptabilité rapide calcule localement, sans requête serveur obligatoire, les achats, ventes, commissions, flux net, réussites et échecs pour : aujourd'hui, semaine, mois, trimestre et année. Une consolidation serveur multi-appareils est préparée par `accounting_summary` lorsque le Worker v2.8 sera autorisé.

### Compte ADMIN propriétaire

`ADMIN` est un espace propriétaire séparé des rôles Blue DAE/DSM/POS. Il n'apparaît pas dans la liste normale des comptes et s'ouvre depuis Ajouter/Ouvrir avec un entitlement cryptographique propriétaire. L'entitlement est lié à l'appareil et stocké localement sous AndroidKeyStore AES/GCM; le serveur ne conserve que le hash du token.

Le tableau de bord ADMIN source prépare : vue nationale nœuds/appareils, états Robot/Remote, alertes, transactions globales, journal administrateur, synchronisation, arrêt/démarrage Robot, bascule Remote/Robot, libération de file et assistance utilisateur. Toute action de contrôle est auditée. Une assistance financière ADMIN prépare une commande mais exige la confirmation de l'utilisateur et n'expose jamais son PIN.

Le contrôle à distance reste soumis aux contrôles locaux du téléphone : un `START_ROBOT` ne contourne ni la propriété de la SIM ni la readiness Robot. La commande est appliquée lors d'un poll de contrôle (démarrage/app ouverte/service actif). Une future notification push peut accélérer le réveil sans transformer l'ADMIN en mécanisme de contournement Android.

### MOCK propriétaire cryptographique

Le MOCK privé local continue à fonctionner avec la production actuelle. Le code v2.8 sait en plus acquérir, dès que le backend v2.8 sera autorisé, un entitlement `MOCK_OWNER` lié à l'appareil et protégé par AndroidKeyStore. Ce droit est distinct des rôles Blue et n'est pas exposé à JavaScript.

## Backend v2.8 préparé mais NON déployé

La source Worker est alignée `2.8.0-cloudflare` et prépare notamment :

- `owner_enroll`
- `owner_snapshot`
- `owner_transactions`
- `owner_audit`
- `owner_control`
- `owner_assist`
- `device_control_poll`
- `device_control_ack`
- `accounting_summary`
- `transaction_ledger`

La migration source `0006_owner_admin_control_and_audit.sql` prépare : `owner_entitlements`, `admin_audit_log`, `device_control_actions`, `admin_assist_requests`.

La chaîne D1 `0001` à `0006` a été exécutée uniquement dans une base SQLite mémoire de CI pour vérifier le schéma. Aucun `wrangler deploy`, aucune migration D1 distante et aucune mutation Cloudflare de production n'ont été exécutés pendant cette étape.

## Validation Android

Le run `31971788221` vérifie l'APK Release non-debuggable puis utilise un APK debug issu des mêmes sources pour injecter le profil de test Robot. Le test de reboot utilise le watchdog interne B.I.R. plutôt que de prétendre qu'un émulateur sans vraie SIM peut maintenir un Robot physiquement vivant. Il valide la persistance de l'intention Robot et l'absence de crash, tandis que la readiness réelle de la SIM reste un test terrain.

Résultat : `verify-build`, API23, API26 et API30 sont tous SUCCESS.

## Interdictions et état production

- PR #4 : doit rester OPEN / NON MERGED.
- Worker production : aucun déploiement v2.8 autorisé pendant cette étape.
- D1 0005 : NON appliquée ici.
- D1 0006 : NON appliquée ici.
- Certificat permanent historique : NON utilisé pendant cette étape.
- APK permanente v2.8.0 : NON publiée.
- Package `com.profitloop.blueauto` : à ne jamais modifier.
- Aucun contournement du verrou sécurisé Android, du PIN ou de la propriété SIM.

## Prochaine autorisation nécessaire

Une autorisation distincte est requise avant toute activation serveur des politiques de commission inter-appareils, de l'ADMIN national, de l'entitlement MOCK cryptographique et de la comptabilité consolidée. Une autre autorisation visant un SHA applicatif exact sera requise avant toute signature/publication d'une APK permanente v2.8.0 avec le certificat historique.
