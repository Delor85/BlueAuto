# B.I.R. / Blue Magic — état de reprise v2.9

Date de gel : 2026-08-18

## Source de vérité

1. GitHub / code et SHA exacts.
2. GitHub Actions / étapes réellement exécutées et artefacts.
3. Cloudflare Worker + D1 vérifiés après propagation.
4. APK permanente et certificat.
5. Conversations uniquement comme contexte complémentaire.

## Référence terrain à ne pas casser

- Android B.I.R. v2.8.1 : `versionName 2.8.1`, `versionCode 54`, `applicationId com.profitloop.blueauto`.
- Source permanente validée : `eef53c4bf483ffc2557a57b0715561412f4c7e10`.
- Worker production conservé pendant la convergence : `2.8.0-cloudflare`.
- D1 production conservé pendant la convergence : migrations 0005 + 0006 déjà actives.
- PR #4 : ne pas fusionner dans le chantier v2.9.

## Décisions utilisateur v2.9 obligatoires

- Deux modes effectifs uniquement : `REMOTE` et `ROBOT`.
- Une ancienne valeur `HYBRID` provenant d'une installation antérieure est migrée silencieusement vers `ROBOT`; elle n'est jamais proposée comme troisième mode.
- Le Robot devient offline-first pour toute opération que la SIM locale peut réellement exécuter sans serveur.
- `REQUEST_SUPPLY` reste réseau-dépendant car l'ordre doit atteindre le Robot du supérieur situé ailleurs.
- Pour une commande Remote, le serveur reste le routeur initial et conserve un unique verrou/fence d'idempotence avant la composition; après ce point le Robot doit pouvoir terminer localement et synchroniser le résultat après exécution.
- Aucune répétition financière aveugle après coupure ou redémarrage.
- Chaque SIM conserve sa propre file et son propre état persistant.
- B.I.R. Relay transporte seulement des événements/résultats en attente entre appareils proches par Wi‑Fi Direct ou Bluetooth.
- Aucun SMS de secours n'est implémenté dans v2.9.
- Aucun PIN, secret d'appairage, token appareil ni commande USSD exécutable n'est transporté par Relay.
- Les enveloppes Relay sont signées avec une identité RSA liée à AndroidKeyStore; le serveur doit accepter uniquement une clé enregistrée pour l'appareil source.
- Maximum 3 sauts Relay; `event_id` serveur unique = idempotence.
- Pas de déploiement d'expansion nationale, Durable Objects, D1 régional, Queue ou R2 dans ce chantier. Préparation architecturale seulement.

## Solde DAE / DSM

Présentation obligatoire en trois valeurs :

1. **Solde réel hors commission** — valeur principale, la plus visible.
2. **Commission au taux par défaut**.
3. **Solde global réel** = solde principal + commission.

Le PoS conserve un seul solde.

La séparation utilise exclusivement le taux par défaut synchronisé. Un taux ponctuel ou personnalisé d'une transaction ne doit pas modifier la présentation permanente du solde.

## Continuité Android / Accessibilité

B.I.R. ne peut pas s'octroyer lui-même une permission système d'Accessibilité. La règle v2.9 est donc :

- si l'autorisation est réellement désactivée : alerter et guider l'utilisateur une fois de façon utile;
- si l'autorisation est toujours accordée mais le service Android est momentanément déconnecté : ne pas redemander la permission, conserver le Robot et sa file, attendre `onServiceConnected`, puis reprendre;
- aucune perte de commande lors de cette attente;
- aucune composition nécessitant le PIN avant connexion effective du service;
- pas de keep-awake permanent.

## Hors connexion — cible v2.9

Exécutable localement par le Robot quand la route SIM et les données nécessaires sont disponibles :

- TEST_NUMBER;
- CHECK_BALANCE;
- LAST_TRANSACTIONS;
- TRANSACTION_DETAILS;
- SUPPLY_CHILD pour DAE/DSM avec annuaire enfant déjà synchronisé;
- RETAIL_SALE pour PoS;
- CHILD_BALANCE;
- RESET_PIN_SELF / MODIFY_PIN_LOCAL;
- FREEZE_SELF;
- INIT_CHILD_PIN_RESET;
- SUSPEND_CHILD / REACTIVATE_CHILD;
- FREEZE_CHILD / REACTIVATE_FROZEN_CHILD.

`REQUEST_SUPPLY` n'est pas prétendu hors ligne : il doit atteindre un autre appareil distant.

## Ledger local / Outbox

- SQLite local append-first.
- `event_id` unique avant synchronisation.
- résultat opérateur et hash d'intégrité conservés.
- synchronisation bornée et idempotente.
- un Worker 2.8 qui ne connaît pas le nouvel endpoint ne doit jamais provoquer une ré-exécution; l'événement reste local et le chemin historique passif peut uniquement remonter une preuve opérateur.

## Serveur v2.9 préparé

Migration additive source : `0007_offline_events_and_bir_relay.sql`.

Nouvelles capacités source :

- `sync_local_events`;
- `relay_register`;
- `relay_sync`;
- registre `relay_identities`;
- registre idempotent `offline_events`.

Pendant la validation Android, ces changements ne doivent pas muter Cloudflare production.

## Gates obligatoires avant APK permanente v2.9

1. Génération déterministe depuis la base v2.8.1 prouvée.
2. Contrats hérités v2.6.8 → v2.8.1 tous verts.
3. Contrat v2.9 offline/Relay vert.
4. Compilation Android Release réelle, non debuggable, zipalign OK.
5. APK éphémère version 2.9.0 / code 55 créée et hashée.
6. Validation Android API 23 et API 26 automatisée, puis Android 11/API 30 réelle ou harnais validé.
7. Aucun déploiement Worker/D1 avant validation source + APK.
8. Avant migration 0007 : export D1 de sécurité et preuve que seule 0007 est en attente.
9. Déployer Worker 2.9 avec rollback automatique si health/capacités échouent.
10. Produire ensuite seulement l'APK permanente avec le certificat historique, vérifier upgrade 2.8.1 → 2.9.0, clean install, apksigner et SHA-256.
11. Tests terrain : Remote, Robot connecté, Robot sans Internet, coupure pendant exécution, reboot, multi-SIM, permission Accessibilité déconnectée/reconnectée, Wi‑Fi Direct Relay, Bluetooth Relay, doublon Relay, verrou sécurisé, soldes DAE/DSM/PoS.
12. Ne jamais déclarer la release permanente si une étape critique est `skipped`.

## Ce qu'il ne faut surtout pas modifier

- package Android;
- certificat permanent;
- PIN local uniquement;
- hiérarchie DAE → DSM → PoS;
- idempotence et verrou anti-double-finance;
- file indépendante par SIM;
- Remote déjà fonctionnel en 2.8.1;
- compatibilité Android 6;
- PR #4 sans autorisation distincte;
- production Cloudflare avant les gates v2.9;
- aucun SMS fallback;
- aucun troisième mode effectif;
- aucun redimensionnement national maintenant.

## Procédure obligatoire de sauvegarde et de reprise dans un autre chat

À la clôture de chaque étape :

1. relever branche + SHA exacts;
2. relever PR et état merge/non-merge;
3. relever tous les runs GitHub Actions utilisés et distinguer success/failure/skipped;
4. relever versionName/versionCode/applicationId;
5. relever SHA-256 APK et SHA-256 certificat si APK permanente;
6. relever Worker live `/api?action=health` et sa version;
7. relever migrations D1 appliquées et migrations encore en attente;
8. documenter fichiers modifiés, tests, acquis, reste à faire et régression possible;
9. mettre à jour ce document ou le document `PROJECT_STATE` le plus récent dans GitHub;
10. dans le nouveau chat, demander de relire d'abord ce document et de vérifier ensuite GitHub/Actions/Cloudflare avant toute modification.

### Bloc de reprise à copier dans un nouveau chat

`BLUE MAGIC / B.I.R. — REPRISE. Lis d'abord le dernier document docs/BIR_V290_REPRISE_ET_DECISIONS.md puis vérifie GitHub, GitHub Actions, Cloudflare/D1 et les artefacts. Ne pars jamais de main si une branche de release plus récente existe. Ne modifie rien avant d'avoir identifié la dernière APK permanente, son SHA source, les versions Worker/D1 et les gates non terminés. Deux modes effectifs seulement REMOTE/ROBOT; aucun SMS fallback; B.I.R. Relay Wi‑Fi Direct/Bluetooth événements seulement; pas d'expansion nationale maintenant; aucune régression de v2.8.1.`


## Décisions produit gratuites v2.9 — 18 août 2026
- DAE Pro, Continuity/Relay, Fleet Health, Audit & Proof, Rescue/SAV, Treasury Forecast et Smart Commission sont inclus gratuitement dès la v2.9.
- Région Control et National Ops sont réservés au compte ADMIN.
- SUPERADMIN est un entitlement unique, promu depuis un ADMIN déjà autorisé sur le même appareil ; il est seul à recevoir les contrôles techniques sensibles.
- Hiérarchie opérationnelle : PoS → DSM d'abord ; DSM → DAE en escalade ; DAE → ADMIN pour les cas de son DSM. Le DAE ne micro-gère pas les PoS hors escalade.
- Le PIN Blue reste exclusivement dans le stockage sécurisé Android du Robot. Aucun endpoint, Relay, dashboard, ADMIN ou SUPERADMIN ne peut obtenir sa valeur en clair.
- Academy Offline et API Business sont explicitement hors périmètre de la v2.9.
- Les files offline non joignables ne sont jamais inventées : le cockpit distingue télémétrie confirmée et dernier état connu.


## Finition cockpit 2.9 — taux honnête et résolution Admin
- Le taux Continuity/Relay porte sur une fenêtre de 24 h et utilise les événements offline confirmés par le serveur plus les événements encore en attente selon la dernière télémétrie connue des appareils.
- Le cockpit affiche simultanément le nombre confirmé et le nombre en attente ; aucune valeur 100 % n’est inventée lorsque le dénominateur est inconnu.
- ADMIN / SUPER-ADMIN peuvent clôturer une escalade DAE → ADMIN via `owner_ops_resolve`, avec audit propriétaire.
- La hiérarchie PoS → DSM → DAE → ADMIN reste inchangée ; cette finition ne donne aucun droit DAE direct supplémentaire sur les PoS.
- Aucun PIN Blue, mot de passe, secret ou jeton n’est ajouté aux données du cockpit ou aux événements Relay.
