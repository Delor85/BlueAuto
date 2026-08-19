# B.I.R. — Blue Distribution Command Center
## Vision opérateur et périmètre autonome — v2.9.3

### 1. Positionnement
B.I.R. n'est pas présenté comme un simple automate USSD. Il constitue une couche intelligente d'exploitation du réseau de distribution Blue, capable de fonctionner quotidiennement sans API Camtel.

Le principe d'architecture est :
- **J0 autonome B.I.R.** : commandes, preuves opérateur, soldes, événements, file, comptabilité, supervision, prévisions et anomalies sont construits avec les données réellement observées par B.I.R. ;
- **J+1/J+2 facultatif Camtel** : un fichier officiel peut ensuite confirmer, corriger ou compléter la clôture historique et les statistiques ;
- **aucune dépendance API Camtel** pour permettre à un DAE, DSM ou PoS de travailler.

### 2. Distribution Command Center
Le Command Center doit fonctionner sur tout l'arbre DAE → DSM → PoS, sans code spécifique à un compte de test.

#### 2.1 Stock Protection Radar
Pour chaque compte : solde connu, âge de la preuve, sorties récentes, débit journalier estimé, couverture en jours et risque de rupture.

États initiaux :
- **CRITICAL** : couverture estimée < 1 jour ;
- **WATCH** : couverture estimée < 3 jours ;
- **COMFORTABLE** : couverture >= 3 jours ;
- **UNKNOWN** : données insuffisantes.

Le radar reste une aide à la décision. Il ne déclenche jamais seul un transfert financier.

#### 2.2 Queue Control Tower
Une même vue doit rapprocher :
- commandes Remote en attente ;
- commande active du Robot ;
- événements locaux hors ligne ;
- âge de la plus ancienne commande ;
- état du lease ;
- état de synchronisation ;
- raison d'un blocage ;
- récupération sûre d'une commande LEASED perdue localement.

Après `DIALING`, la récupération devient uniquement observation/vérification : aucune recomposition aveugle.

#### 2.3 Proof Ledger et qualité des soldes
Chaque solde doit porter sa provenance et sa chronologie. La priorité est donnée à une preuve Blue fiable et récente. TransactionID, ReceiptNumber et command_id empêchent qu'une même transaction soit comptée deux fois.

Niveaux de confiance proposés :
1. preuve opérateur Blue reconnue ;
2. preuve certifiée de solde/historique ;
3. solde recalculé à partir d'une preuve + mouvements confirmés non inclus dans cette preuve ;
4. estimation B.I.R. à rapprocher ;
5. donnée manuelle ou importée en attente de rapprochement.

#### 2.4 Reconciliation Center
Le centre rapproche :
- commande B.I.R. ;
- résultat opérateur observé ;
- TransactionID / ReceiptNumber ;
- montant ;
- date/heure opérateur ;
- solde après opération lorsqu'il est disponible ;
- éventuel fichier Camtel J+1/J+2.

États : `MATCHED`, `MISMATCH`, `BIR_ONLY`, `BLUE_ONLY`, `UNMATCHED`, `REVIEW`.

#### 2.5 Service Quality Intelligence
B.I.R. différencie autant que possible :
- problème d'un seul téléphone/Robot ;
- Accessibilité autorisée mais momentanément déconnectée ;
- SIM/route locale en difficulté ;
- file serveur vieillissante ;
- hausse anormale des échecs sur un nœud ;
- hausse simultanée sur plusieurs nœuds, signalée comme **incident opérateur probable**.

Aucun signal automatique ne doit accuser un agent de fraude. Les anomalies sont des éléments **à vérifier**.

#### 2.6 Robot Fleet Health
Par appareil : dernière télémétrie, rôle, nœud, version B.I.R., version Android, état Robot, Accessibilité accordée/connectée, batterie lorsque disponible, événements hors ligne et ancienneté de la dernière présence.

#### 2.7 Business Health
Indicateurs possibles par DAE/DSM/PoS : volume, fréquence, croissance, activité récente, part de jours actifs, vitesse de consommation, risque de rupture, fréquence des doubles tentatives, commandes vieillissantes, qualité des preuves et taux de rapprochement.

#### 2.8 Flow Graph
B.I.R. reconstitue les flux connus DAE → DSM → PoS et PoS → clients à partir des commandes et preuves qu'il possède. Les catégories commerciales/statistiques Camtel telles que « intra-réseau » et « extra-réseau » ne doivent être attribuées que si les données observées ou un fichier Camtel permettent de les déterminer sans invention.

#### 2.9 SAV et dossier de preuve
Un incident doit pouvoir produire un dossier : chronologie, commande, états, preuve opérateur, TransactionID/Receipt, solde avant/après connu, état Robot, Accessibilité, synchronisation, version de l'application et décision de rapprochement.

#### 2.10 Executive Reporting
Rapports journaliers/hebdomadaires/mensuels : activité, flux, stock, ruptures évitées, anomalies, qualité de service, files, appareils, rapprochement, tendances et performance par hiérarchie/région lorsque la région est connue.

### 3. Commission : séparation des notions
Les références par défaut sont : DAE 10 %, DSM 9 %, PoS 8 %.

B.I.R. distingue désormais :
- **taux entrant/effectif du compte** : commission réellement reçue par ce compte ;
- **politique commerciale vers les enfants** : taux que le DAE applique à ses DSM ou que le DSM applique à ses PoS.

Une stratégie commerciale personnalisée ne doit jamais modifier rétroactivement la commission propre du compte.

### 4. Fonctions Super ADMIN / partenaire opérateur
Selon le partenariat, Blue/Camtel peut recevoir un espace national avec :
- vue nationale DAE/DSM/PoS ;
- Stock Protection Radar ;
- Queue Control Tower ;
- Robot Fleet Health ;
- Service Quality Intelligence ;
- Reconciliation Center ;
- Proof Ledger ;
- statistiques agrégées ;
- incidents/SAV ;
- santé des versions Android/B.I.R. ;
- journal d'audit ADMIN/Super ADMIN ;
- exports de reporting ;
- gouvernance des accès et périmètres.

Ces fonctions n'impliquent pas que Camtel fournisse une API transactionnelle.

### 5. Apports Camtel réellement utiles — non bloquants
B.I.R. peut fonctionner sans ces éléments. Les demandes à Camtel doivent donc être limitées à ce qui apporte une vraie valeur de certification ou de gouvernance :

1. **Fichier journalier ou J+1/J+2 des transactions concernant les numéros B.I.R.**. CSV/Excel suffit. Champs minimaux souhaités : TransactionID/Receipt, compte/MSISDN source, destination, type d'opération, montant, état final et date/heure. Solde après opération s'il existe dans l'export.
2. **Historique initial 30 à 90 jours**, si facilement exportable, uniquement pour initialiser tendances, rapprochement et références statistiques.
3. **Référentiel officiel périodique des comptes reconnus**, uniquement comme certification du registre B.I.R. : numéro, rôle DAE/DSM/PoS, parent hiérarchique et statut lorsque Camtel dispose réellement de ces données sous une forme exploitable.
4. **Définitions officielles des catégories statistiques que Camtel souhaite voir** : notamment la définition exacte de vente/achat intra-réseau, extra-réseau, distribution, retail, annulation ou autres catégories internes utiles à leurs tableaux de bord.
5. **Point de contact humain technique/exploitation**, pour confirmer rapidement un incident général ou un changement de grammaire USSD/message. Pas de SLA automatisé requis.
6. **Autorisation administrative d'usage** de B.I.R. dans le réseau de distribution, avec règles éventuelles de marque, confidentialité, conservation et audit.
7. **Si partenariat ou prise de participation** : règles de gouvernance du Super ADMIN, niveau d'accès de Blue, responsabilités de validation des versions et politique d'export/conservation.
8. **Format stable des fichiers remis** : noms de colonnes, fuseau horaire, période couverte, encodage et idéalement total de lignes ou empreinte de fichier pour détecter les fichiers incomplets.
9. **Documentation statique des commandes/messages USSD**, si disponible et facile à transmettre. C'est utile mais non bloquant, B.I.R. pouvant être mis à jour rapidement lorsqu'une commande change.

### 6. Ce que B.I.R. ne doit pas demander comme prérequis
Ne pas présenter comme indispensables : API de solde, API transactionnelle, webhook Camtel, OAuth/mTLS Camtel, sandbox opérateur, API incrémentale, API de statut SIM ou SLA machine-to-machine. Ces éléments pourraient être intéressants un jour, mais la proposition de valeur actuelle repose sur l'autonomie de B.I.R.

### 7. Fonctions supplémentaires réalistes à forte valeur
- **Allocation Advisor** : simule la meilleure répartition d'un stock disponible entre enfants menacés de rupture, sans exécuter automatiquement le transfert.
- **Downstream Impact** : estime combien de DSM/PoS seront affectés si un DAE ou DSM tombe en rupture.
- **Dormancy Radar** : repère les comptes actifs administrativement mais commercialement inactifs ou fortement ralentis.
- **Velocity/Concentration Watch** : signale des volumes/fréquences atypiques par rapport à l'historique propre du compte, sans accusation automatique.
- **Duplicate Pressure** : mesure les doubles tentatives évitées par l'idempotence et distingue impatience utilisateur, latence ou file bloquée.
- **Evidence Quality Score** : mesure la part d'opérations avec preuve opérateur, TransactionID/Receipt et rapprochement complet.
- **Forecast Confidence** : accompagne toute prévision de rupture d'un niveau de confiance dépendant de la fraîcheur du solde et du volume d'historique.
- **Device/Android Compatibility Radar** : classe les incidents par version Android, modèle de téléphone et version B.I.R. pour identifier les régressions techniques.
- **What-if Commission Simulator** : simule l'effet d'une politique 10/9,5/9/etc. sur marge, distribution et couverture sans modifier les paramètres réels.
- **Dispute Pack** : export d'un dossier de contestation complet à partir des preuves B.I.R. et, le cas échéant, du fichier Camtel rapproché.
- **Data Completeness Monitor** : détecte journées manquantes, trous de chronologie, événements non synchronisés et fichiers Camtel incomplets.
- **Offline Continuity KPI** : mesure combien d'opérations/informations ont continué localement et combien d'événements ont été resynchronisés ou relayés ensuite.

### 8. Règle de présentation
La démonstration doit montrer d'abord que B.I.R. fonctionne **sans accès privilégié Camtel**, puis montrer comment un partenariat Camtel augmente la valeur de certification, de gouvernance et de reporting sans rendre l'application dépendante de Camtel.
