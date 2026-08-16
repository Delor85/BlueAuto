# B.I.R. v2.8.0 — état de reprise opérations / ADMIN

Date : 2026-08-16

## Ancrage exact validé

- Branche de travail : `feat/bir-v2-8-operations-admin`
- **SHA applicatif exact validé : `4c24ded4e2053aa30640f654ddaf5ddf55908c20`**
- Package : `com.profitloop.blueauto`
- versionName : `2.8.0`
- versionCode : `53`
- minSdk : `23` / Android 6
- targetSdk : `34`
- **Run de validation exacte : `31972497493` — SUCCESS**
- Android 6 / API23 : **SUCCESS**
- Android 8 / API26 : **SUCCESS**
- Android 11 / API30 : **SUCCESS**
- APK de validation éphémère SHA-256 : `753b1d81565f8260ba9a58965139078396b9f2b69bd273968d63976fbef73a8d`
- Certificat de validation éphémère SHA-256 : `5e30cb40cc4b5ce2b936aba4c94be4d9ffc5082b90e6539a1b4b48be726fabc9`
- Artefact de validation : `BIR-v2.8.0-validation-ephemeral`, ID `9270175799`
- Digest ZIP de l'artefact : `fba343b694fbbba6d5a6aca13bc22b09d62ce518298b1cab35b316c67506478d`
- Signature de validation : V1=true, V2=true, V3=false. Cette signature est volontairement éphémère et **NE DOIT PAS** être livrée comme APK permanente.

Le run précédent `31971788221` avait déjà validé en vert API23/API26/API30 le noyau v2.8 au SHA `73b2623446457b698013aa3cef4406abfbf7b885`. Le run `31972497493` remplace cet ancrage et valide en plus la gestion ADMIN auditée des Tchoronkos présente au SHA final `4c24ded...`.

## Corrections et extensions intégrées

### Icône Android

Le manifeste Android référence maintenant `@drawable/ic_launcher_bir` pour `android:icon` et `android:roundIcon`. Le dessin reprend la **géométrie du logo B.I.R. déjà présent dans l'application** : infini cyan à gauche, infini doré à droite, I central doré, B et R intégrés. L'ancienne tête Android n'est plus l'icône déclarée du launcher.

### Bilingue FR / EN

La couche v2.8 étend la traduction du cœur visible de l'interface et applique dynamiquement le vocabulaire FR/EN aux composants ajoutés. Le choix de langue reste local. Les identifiants internes historiques nécessaires aux parseurs opérateur ne sont pas renommés aveuglément. Les libellés visibles utilisent **Blue**.

### Commissions — règle définitive

Trois niveaux sont distincts :

1. `DEFAULT` persistant : taux réseau fixé par le DAE pour ses DSM ou par le DSM pour ses PoS. Il s'applique à tout enfant qui n'a pas de taux personnalisé.
2. `CHILD_SPECIFIC` persistant : exception propre à un seul enfant, bonus ou rétrogradation, jusqu'à modification ou suppression par son supérieur.
3. `ONE_SHOT` éphémère : taux choisi pour une seule transaction au moment de la confirmation.

Priorité : **`ONE_SHOT > CHILD_SPECIFIC > DEFAULT`**.

Le taux ponctuel est consommé après création de la commande et également en cas d'annulation, erreur de prévisualisation ou certification incomplète. Il ne peut donc pas contaminer la transaction suivante et ne modifie jamais les deux taux persistants.

La persistance inter-appareils des deux politiques durables est préparée par la migration source `0005_commission_policies_and_financial_quotes.sql`, mais elle n'est pas active en production tant que D1 0005 et le Worker correspondant n'ont pas reçu une autorisation distincte.

### Moteur de solde événementiel

`balance-engine-v280.js` conserve la dernière preuve Blue sûre, applique les mouvements financiers confirmés postérieurs et classe le résultat en `CERTIFIED`, `RECALCULATED` ou `UNCERTAIN`. Une preuve récente ou un solde recalculable évite une nouvelle interrogation USSD ; un événement ambigu, inconnu ou trop ancien force une recertification. La règle de chronologie reste prioritaire : un résultat financier retardé sans horodatage opérateur fiable ne peut pas faire régresser une preuve plus récente.

### Tchoronkos

Les DSM / PoS pré-enrôlés `TCHORONKO_SHADOW` sont intégrés à la vue réseau DAE/DSM. Le mécanisme réutilise les données et routes déjà préparées par `shadow_accounts`, `shadow_enroll` et `platform_snapshot` au lieu de créer une seconde hiérarchie parallèle.

L'ADMIN dispose en plus d'une gestion auditée `owner_tchoronko_save` pour créer/rattacher ou réparer un Tchoronko DSM/PoS. Le serveur contrôle obligatoirement la hiérarchie : **un DSM Tchoronko dépend d'un DAE ; un PoS Tchoronko dépend d'un DSM**. Toute modification est inscrite dans le journal ADMIN.

### Comptabilité générale

Un tableau de comptabilité rapide calcule localement, sans requête serveur obligatoire, les achats, ventes, commissions, flux net, réussites et échecs pour : **aujourd'hui, semaine, mois, trimestre et année**. Une consolidation serveur multi-appareils est préparée par `accounting_summary` lorsque le Worker v2.8 sera autorisé.

### Compte ADMIN propriétaire

`ADMIN` est un espace propriétaire séparé des rôles Blue DAE/DSM/POS. Il n'apparaît pas dans la liste normale des comptes et s'ouvre depuis **Ajouter/Ouvrir** en saisissant `ADMIN` puis le code propriétaire. L'entitlement est lié à l'appareil et stocké localement sous AndroidKeyStore AES/GCM ; le serveur ne conserve que le hash du token.

Le tableau de bord ADMIN source prépare : vue nationale nœuds/appareils, états Robot/Remote, alertes, transactions globales, journal administrateur, synchronisation, arrêt/démarrage Robot, bascule Remote/Robot, libération de file, assistance utilisateur et gestion auditée des Tchoronkos. Toute action de contrôle est auditée. Une assistance financière ADMIN prépare une commande mais exige la confirmation de l'utilisateur et n'expose jamais son PIN.

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
- `owner_tchoronko_save`
- `device_control_poll`
- `device_control_ack`
- `accounting_summary`
- `transaction_ledger`

La migration source `0006_owner_admin_control_and_audit.sql` prépare : `owner_entitlements`, `admin_audit_log`, `device_control_actions`, `admin_assist_requests`.

La chaîne D1 `0001` à `0006` a été exécutée uniquement dans une base SQLite mémoire de CI pour vérifier le schéma. Aucun `wrangler deploy`, aucune migration D1 distante et aucune mutation Cloudflare de production n'ont été exécutés pendant cette étape.

## Validation Android finale

Le run `31972497493` vérifie l'APK Release non-debuggable puis utilise un APK debug issu des mêmes sources pour injecter le profil de test Robot. Le test de reboot utilise le watchdog interne B.I.R. plutôt que de prétendre qu'un émulateur sans vraie SIM peut maintenir un Robot physiquement vivant. Il valide la persistance de l'intention Robot et l'absence de crash ; la readiness réelle de la SIM reste un test terrain.

Résultat final : **`verify-build`, Android 6/API23, Android 8/API26 et Android 11/API30 = SUCCESS.**

La Release de validation prouve aussi : package `com.profitloop.blueauto`, versionCode 53, versionName 2.8.0, minSdk23, targetSdk34, APK non-debuggable, launcher icon présent et zipalign valide.

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

Une autorisation distincte est requise avant toute activation serveur des politiques de commission inter-appareils, de l'ADMIN national, de l'entitlement MOCK cryptographique, de la gestion ADMIN Tchoronko et de la comptabilité consolidée. Cette activation nécessitera une préparation contrôlée de D1 `0005`, D1 `0006` et du Worker v2.8 avec sauvegarde/contrôles avant et après.

Une autre autorisation visant le **SHA applicatif exact `4c24ded4e2053aa30640f654ddaf5ddf55908c20`** sera requise avant toute signature/publication d'une APK permanente v2.8.0 avec le certificat historique.
