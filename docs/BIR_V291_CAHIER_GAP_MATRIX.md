# B.I.R. / Blue Magic — matrice Cahier des charges ↔ code réel après v2.9.1

Date : 2026-08-18

## Règle de lecture

Cette matrice distingue :

- **ACQUIS** : présent et testé dans le code.
- **PRÉSENT MAIS ENFOUI** : fonction existante, désormais indexée par la recherche globale v2.9.1.
- **PARTIEL** : présent mais incomplet par rapport au cahier maître.
- **À DÉFINIR** : le cahier maître lui-même ne fixe pas encore une spécification normative complète ; ne pas simuler une fausse complétude.
- **EXCLU POUR L’INSTANT** : volontairement hors périmètre utilisateur actuel.

Le correctif terrain v2.9.1 reste volontairement focalisé sur synchronisation, soldes, Secours/SAV, recherche et réveil Remote→Robot. Les modules lourds incomplets ci-dessous doivent être ajoutés par lots 2.9.x additifs après la recette terrain de 2.9.1.

## 1. ACQUIS / renforcé v2.9.1

| Domaine | État | Preuve/code | Décision |
|---|---|---|---|
| Remote ↔ Robot | ACQUIS + RENFORCÉ | RobotService, ApiClient, Worker | Snapshot Remote 5 s côté observateur, heartbeat 20 s, backoff borné, Auto‑Réveil adaptatif sans polling permanent agressif. |
| Réveil distant | NOUVEAU 2.9.1 | `force_sync`, `sync_wake_requests` | Remote demande un réveil uniquement au Robot actif/vérifié du même `node_code`; aucune commande financière ni USSD. |
| Secours/SAV | CORRIGÉ 2.9.1 | `MainActivity.onJsPrompt` | Dialogue texte multiline distinct du taux de commission numérique. |
| Recherche globale | NOUVEAU 2.9.1 | `field-recovery-v291.js` | Recherche en langage simple : solde, Secours, SIM, KYC, commission, historique, créance, flotte, etc. |
| Solde/prévision | RENFORCÉ 2.9.1 | `balance-engine-v280.js` | Débit d’approvisionnement tient compte de la commission ; état incertain affiché comme estimation à rapprocher. |
| Modes | ACQUIS | MainActivity/AppConfig | REMOTE/ROBOT seulement ; HYBRID historique migré silencieusement vers ROBOT. |
| PIN Blue | ACQUIS | Android Keystore | Aucun accès serveur/Remote/Admin/SuperAdmin en clair. |
| Anti-double-finance | ACQUIS | Worker/Robot | Fence serveur et idempotence conservées ; Auto‑Réveil ne simule jamais une transaction. |
| Relay | ACQUIS | Wi‑Fi Direct + Bluetooth | Événements/résultats seulement, signés/idempotents ; pas d’ordre financier exécutable ; pas SMS fallback. |
| DAE Pro / cockpit | ACQUIS | v2.9 | Gratuit, hiérarchie PoS→DSM→DAE→ADMIN, DAE sans microgestion normale du PoS. |
| Admin Région/National | ACQUIS | v2.9 | Réservé Admin ; SuperAdmin séparé et unique. |

## 2. PRÉSENT MAIS ENFOUI — rendu accessible par la recherche v2.9.1

- TEST_NUMBER sans fonds.
- Solde/proof Blue, 5 dernières transactions, détail transaction.
- Approvisionnement enfant, demande de stock, vente client.
- Comptes/SIM, vérification/liaison SIM, permissions, gestion PIN, batterie, Robot.
- Flotte/réseau et santé des Robots.
- Journal d’activité.
- Commissions par défaut/enfant.
- Créances et remboursements.
- Rapport réseau vivant et audit intelligent des soldes.
- Preuves opérateur Blue récentes et référentiel Camtel.
- Administration enfant : suspension/réactivation/gel/reset PIN initial.
- KYC textuel/GPS de base.
- Mercenaires existants dans le code, sous réserve des règles de finalisation ci-dessous.
- Comptabilité, audit propriétaire, Tchoronko shadow et outils Admin déjà présents dans les overlays 2.8/2.9.

## 3. PARTIEL — vraies lacunes du cahier maître

### 3.1 KYC documentaire complet

**Existant** : nom légal, numéro de pièce, référence locale du document, zone, latitude/longitude.

**Manquant pour conformité au cahier** :

- capture CNI recto/verso depuis caméra (`accept="image/*" capture="camera"`) ;
- sélection depuis galerie ;
- selfie/portrait si requis par le parcours ;
- stockage documentaire chiffré dédié et références D1, sans mettre les photos en clair dans D1 ;
- état de vérification/rejet, date, opérateur de vérification et audit ;
- visualisation strictement limitée aux rôles autorisés ;
- politique de rétention/suppression documentaire.

**Lot recommandé** : v2.9.2 KYC documentaire sécurisé.

### 3.2 Rapports, graphes et exports

**Existant** : rapport réseau vivant, audit soldes, comptabilité et preuves.

**Manquant/partiel** :

- filtres jour/semaine/mois/trimestre/année cohérents sur tous les rapports ;
- graphiques lisibles sur vieux Android ;
- export CSV/PDF nettoyé avec masquage des données sensibles ;
- export des preuves/rapports sélectionnés ;
- partage/impression explicite sans exposer PIN/secrets/tokens.

**Lot recommandé** : v2.9.3 Reporting & Export.

### 3.3 SAV / diagnostic reproductible

**Existant** : santé serveur, codes d’erreur, cockpit incidents, Secours/SAV hiérarchique.

**Manquant/partiel** :

- bouton « Générer diagnostic » ;
- paquet JSON/ZIP local contenant version APK, Android/modèle, modes, permissions, slots, empreinte SIM courte, health Worker, dernier public_id/état, timestamps sync ;
- nettoyage obligatoire : aucun PIN, pairing secret, token, keystore, mot de passe, code USSD contenant PIN ;
- FAQ guidée par symptôme ;
- export/partage explicite par l’utilisateur.

**Lot recommandé** : v2.9.2 ou v2.9.3 selon recette terrain.

### 3.4 Sauvegarde / export opérationnel

**Existant** : procédures de sauvegarde GitHub/D1 avant migrations à risque.

**Manquant/partiel dans l’UI** :

- export utilisateur des données autorisées ;
- politique de rétention configurable pour logs/événements ;
- contrôle Admin/SuperAdmin des exports et traces d’audit ;
- restauration encadrée uniquement pour données non transactionnelles ou selon procédure validée.

### 3.5 Réconciliation d’écarts de solde

**Existant** : preuve certifiée, solde recalculé, audit, état « à rapprocher ».

**À finir** : assistant explicite de rapprochement lorsqu’une transaction s’est produite hors B.I.R. ou qu’un message opérateur est ambigu : afficher preuve précédente, mouvements connus, nouvelle preuve, écart, résolution auditée — sans inventer un solde.

## 4. À DÉFINIR / ne pas prétendre complet

### Tchoronko

Le cahier maître normatif indique explicitement que le concept Tchoronko reste **[À DÉFINIR]**. Des briques `TCHORONKO_SHADOW` existent déjà, mais elles ne doivent pas être présentées comme une implémentation métier complète tant que les règles exactes d’identité, permissions, preuves, transaction, audit et cycle de vie ne sont pas gelées.

### Mercenaires

Des fonctions existent (compte, dépôt virtuel, vente, PoS dédié, commission). Avant de déclarer le module complet, il faut geler définitivement : éligibilité, plafond, disponibilité, révocation, fraude, remboursement/annulation, responsabilité du PoS central, KYC et règles de commission.

## 5. EXCLU POUR L’INSTANT

- B.I.R. Academy Offline : exclu à la demande utilisateur.
- API Business : exclu à la demande utilisateur.
- redimensionnement/expansion nationale technique : préparation architecturale seulement ; aucun déploiement maintenant.
- SMS fallback : interdit.
- troisième mode Hybrid : interdit comme mode effectif.

## 6. Ordre d’intégration après v2.9.1 terrain

1. **v2.9.2 — KYC documentaire + diagnostic/SAV exportable + assistant rapprochement.**
2. **v2.9.3 — rapports/graphes/CSV/PDF + sauvegarde/export utilisateur/audit.**
3. **v2.9.4 — finalisation Mercenaires après règles gelées.**
4. **Tchoronko — uniquement après spécification normative explicite.**

Chaque lot doit repartir du dernier APK permanent validé, conserver `com.profitloop.blueauto` et le certificat historique, repasser tous les contrats hérités, produire un seul APK exact pour API23/API26/API30, puis seulement envisager Worker/D1 et signature permanente.
