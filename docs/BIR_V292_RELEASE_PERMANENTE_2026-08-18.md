# B.I.R. / Blue Magic — v2.9.2 permanente — Premium gratuit & pilotage hiérarchique simple

Date : 2026-08-18

## 1. Ancre applicative immuable

- Branche fonctionnelle : `feat/bir-v2-9-2-free-premium-pilotage`
- SHA applicatif exact : `f123e766271511c6270305c5641ab4db93401c99`
- Package Android : `com.profitloop.blueauto`
- `versionName` : `2.9.2`
- `versionCode` : `57`
- `minSdk` : `23`
- `targetSdk` : `34`
- Modes effectifs : `REMOTE`, `ROBOT` uniquement
- Aucun SMS fallback
- Aucun PIN Blue serveur/Remote/Admin
- Aucun réveil financier fictif

Les commits documentaires ultérieurs ne changent pas cette ancre applicative.

## 2. Nouvelle règle produit officielle : Premium pour tous, 0 FCFA

La logique commerciale payante proposée auparavant pour Continuity Pro / DAE Pro / DSM Pro / Fleet Health / Audit & Proof / Rescue / Treasury Forecast / Smart Commission n'est pas appliquée aux utilisateurs B.I.R.

**Dans B.I.R. 2.9.2, tous les outils opérationnels, de continuité, de supervision, de prévision, de preuve et d'assistance disponibles pour un rôle sont inclus gratuitement.**

Cela signifie :

- aucun paywall ;
- aucun quota Premium ;
- aucune transaction bloquée pour absence d'abonnement ;
- aucun niveau `Standard / Business / Enterprise` à acheter pour accéder à la qualité de service B.I.R. ;
- le même socle de qualité est fourni gratuitement à tous les utilisateurs ;
- les permissions métier et de sécurité restent toutefois strictement hiérarchiques.

**Premium gratuit ne signifie pas Super-Admin pour tous.** Un DSM reste DSM, un DAE reste DAE, et les fonctions sensibles ADMIN/SUPER-ADMIN ne sont pas distribuées à des rôles qui ne doivent pas les posséder.

## 3. Hiérarchie d'assistance et de pilotage

### PoS

- voit son propre état ;
- peut lancer une réparation/synchronisation sûre sur son propre compte ;
- remonte son problème à son DSM si nécessaire.

### DSM — responsable opérationnel direct des PoS

Le DSM est le premier et principal pilote de ses PoS.

Il peut :

- voir l'état de ses PoS directs ;
- identifier les files en attente ;
- suivre santé Robot, synchronisation, continuité et alertes ;
- lancer `AIDER` sur un PoS direct ;
- demander un réveil de synchronisation non financier ;
- escalader au DAE seulement un cas devenu `HOT` ou `CRITICAL`.

Le serveur vérifie que le PoS ciblé est réellement un enfant direct de ce DSM.

### DAE — responsable opérationnel direct des DSM

Le DAE pilote d'abord ses DSM.

Il peut :

- voir et aider ses DSM directs ;
- suivre les indicateurs agrégés de son réseau ;
- voir les tendances, risques et alertes ;
- venir au secours d'un DSM quand une situation devient chaude ou grave.

**Le DAE ne peut pas utiliser `ops_assist` directement sur un PoS ordinaire.**

Une intervention DAE → PoS n'est acceptée que si :

1. une escalade est ouverte ;
2. elle est assignée à ce DAE ;
3. le PoS appartient à un DSM de ce DAE ;
4. la sévérité est `HOT` ou `CRITICAL`.

Cette règle protège le domaine quotidien du DSM et évite une présence permanente du DAE dans la gestion des PoS.

## 4. Tableau de bord ultra-simple

Le nouveau cockpit `pilotage-v292` se place dans l'espace Rapports/Pilotage et masque le vieux cockpit comme interface principale tout en conservant ce dernier comme fallback compatible.

L'interface commence par :

**★ PREMIUM POUR TOUS — 0 FCFA**

Puis, selon le rôle :

- DAE : **Mes DSM aujourd'hui** ;
- DSM : **Mes PoS aujourd'hui** ;
- PoS : **Mon PoS aujourd'hui**.

Le principe d'ergonomie est :

**Aujourd'hui → ce qui demande une attention → ce que je dois faire maintenant.**

Le bloc principal `À FAIRE MAINTENANT` affiche une phrase simple et un gros bouton `AIDER MAINTENANT` lorsqu'une action sûre existe.

Les indicateurs principaux sont :

1. **Santé Robots** — robots sains / connus ;
2. **Synchronisation** — taux/confirmations et événements en attente ;
3. **Prévision stock** — couverture estimée en jours avec message prudent.

Couleurs et niveaux :

- Vert : fonctionnement normal ;
- Orange : attention ;
- Rouge : chaud / critique.

## 5. Outils Premium désormais inclus gratuitement

Le tableau de bord rend directement accessibles les familles suivantes :

### Continuité / Relay

- état de synchronisation ;
- confirmations ;
- événements en attente ;
- événements directs / relayés lorsque disponibles ;
- continuité offline-first déjà acquise.

### Supervision des files

- identification des comptes avec événements en attente ;
- nombre d'événements ;
- action hiérarchique `AIDER` lorsque permise ;
- conservation des mécanismes d'idempotence et de non-double-exécution.

### Santé Robots / Fleet Health

- santé du Robot connue par le cockpit ;
- sévérité ;
- message/action recommandée ;
- état exploitable par DSM pour ses PoS et par DAE pour ses DSM.

### Taux de synchronisation / qualité de continuité

Le KPI de synchronisation n'est plus vendu comme SLA Premium : il fait partie gratuitement de la qualité de service B.I.R. disponible au responsable concerné.

### Nœuds silencieux / anomalies de présence

Ils restent traités via les états de santé, ancienneté des données, sévérités et alertes du cockpit. Une absence de contact n'est pas automatiquement assimilée à une transaction perdue.

### Audit & Proof

- accès aux événements/preuves rapprochés ;
- accès aux preuves Blue existantes ;
- continuité des mécanismes d'audit déjà acquis.

### Rescue / SAV

- nombre de cas à traiter ;
- action rapide au bon niveau hiérarchique ;
- réparation de synchronisation non financière ;
- escalade DSM → DAE seulement HOT/CRITICAL ;
- aucun accès au PIN Blue.

### Treasury / Stock Forecast

- couverture de stock en jours lorsque les données sont suffisantes ;
- message de risque ;
- prévision purement décisionnelle : **aucun approvisionnement automatique silencieux**.

### Smart Commission

- lecture des commissions confirmées ;
- accès aux taux/simulations existants ;
- **aucune modification automatique silencieuse de taux**.

### Business Health

Score opérationnel simple et explicable :

- 40 % santé Robots ;
- 30 % synchronisation ;
- 20 % incidents ;
- 10 % couverture stock.

Ce score :

- sert à repérer où aider ;
- ne bloque jamais un utilisateur ;
- ne refuse jamais automatiquement un crédit ;
- ne remplace jamais une décision humaine.

## 6. Recherche globale

La recherche de services de la 2.9.1 est enrichie avec :

- Tableau de bord / Pilotage ;
- Continuité / Relay ;
- Files en attente ;
- Santé Robots ;
- Business Health.

L'utilisateur peut donc chercher un besoin par des mots simples au lieu de mémoriser l'emplacement d'un menu.

## 7. Nouvelle action serveur `ops_assist`

`ops_assist` est une action de réparation volontairement très limitée.

Elle n'accepte que :

`WAKE_SYNC`

Elle :

- rejette les payloads sensibles ;
- réutilise la table `sync_wake_requests` créée par la migration 0009 ;
- déduplique une demande déjà en attente ;
- cible un Robot actif, activé et SIM vérifiée ;
- ne crée aucune ligne dans `commands` ;
- ne compose aucun USSD ;
- ne vend rien ;
- ne fournit aucun crédit ;
- ne modifie aucun PIN ;
- ne lit aucun PIN ;
- ne remet pas le SMS fallback.

Hiérarchie serveur :

- PoS → soi-même ;
- DSM → PoS direct ;
- DAE → DSM direct ;
- DAE → PoS seulement avec escalade ouverte HOT/CRITICAL assignée et appartenant à sa branche.

## 8. Capacités Worker 2.9.2

Production active :

- Worker : `2.9.2-cloudflare`
- Worker Version ID : `0d6acb10-cda7-43b0-b9dc-7ef07ab4460d`
- D1 : jusqu'à `0009`, **aucune nouvelle migration pour 2.9.2**
- `sync_wake_requests` : présente
- aucune migration en attente lors de l'activation

Nouvelles capacités `/health` :

- `premium_for_all: true`
- `hierarchical_rescue: true`
- `simple_pilotage: true`

Capacités de sécurité/continuité conservées :

- `force_sync`
- `offline_sync`
- `bir_relay`
- `free_ops_cockpit`
- `super_admin`
- modes effectifs `REMOTE`, `ROBOT`.

## 9. Validation de convergence

Run : `32191056591` — **SUCCESS**

Source validée et publiée :

`f123e766271511c6270305c5641ab4db93401c99`

APK éphémère exact :

`91098cf886ed946689e0dc5cbda7a3ba981826ef3c61f5fa99c12e694d202c26`

Validation :

- contrat v2.9.2 premium gratuit : vert ;
- règle DSM/DAE : verte ;
- `ops_assist` non financier : vert ;
- contrats hérités 2.6.x → 2.9.1 : verts ;
- garde Android 6 / WebView ES5 : vert ;
- Worker : npm/check/dry-run vert ;
- Java/Gradle/tests : verts ;
- APK Release code57 : vert ;
- non debuggable ;
- zipalign OK.

## 10. Matrice Android — même APK exact

Run final : `32191686889` — **SUCCESS**

- Android 6 / API23 : SUCCESS ;
- Android 8 / API26 : SUCCESS ;
- Android 11 / API30 : SUCCESS.

Chaque job a téléchargé le même APK SHA :

`91098cf886ed946689e0dc5cbda7a3ba981826ef3c61f5fa99c12e694d202c26`

Tests : installation, lancement, arrêt forcé, relance et absence de crash.

Le premier run `32191303572` avait échoué avant `adb install`, car `android-emulator-runner` exécutait chaque ligne de script dans un shell distinct et la variable locale contenant le chemin APK devenait vide. PR CI #49 a corrigé uniquement le harnais. L'APK n'a pas été reconstruit.

## 11. Activation production

Run : `32192700739` — **SUCCESS**

- D1 : aucune migration à appliquer ;
- table `sync_wake_requests` vérifiée ;
- D1 non modifiée ;
- ancien Worker 2.9.1 : `99554d17-3acb-4103-a478-0739002fc7cb` ;
- nouveau Worker 2.9.2 : `0d6acb10-cda7-43b0-b9dc-7ef07ab4460d` ;
- `/health` 2.9.2 : OK ;
- `premium_for_all` : true ;
- `hierarchical_rescue` : true ;
- `simple_pilotage` : true ;
- rollback : non déclenché.

## 12. APK permanente

Fichier :

`BIR-Blue-Infinity-Retail-v2.9.2-vc57-Permanent.apk`

- taille : `231732` octets ;
- SHA-256 permanent : `16096cb8bd2bebb2748236d83854eda56e4605ef29faeb4994eee7f68ceb849b` ;
- certificat SHA-256 : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5` ;
- DN : `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM` ;
- RSA : 4096 bits ;
- v1 : true ;
- v2 : true ;
- v3 : true ;
- signataires : 1 ;
- zipalign : OK ;
- non debuggable.

### Continuité de mise à jour

- v2.9.1 : package `com.profitloop.blueauto`, code56, certificat historique ;
- v2.9.2 : package identique, code57, certificat historique identique.

La mise à jour en place est conservée. Ne pas désinstaller la 2.9.1 pour le test normal de mise à jour.

### Même code que l'APK testé

L'APK permanente a été produite **sans rebuild** à partir de l'APK exact passé sur API23/API26/API30.

Comparaison en excluant uniquement les fichiers réels de signature :

- entrées applicatives testées : `30` ;
- entrées applicatives permanentes : `30` ;
- ajoutées : `0` ;
- supprimées : `0` ;
- modifiées : `0`.

## 13. Incident de signature CI fail-closed

Run GitHub `32193000955` : **FAIL-CLOSED avant signature**.

Cause : les nouveaux jobs GitHub n'ont reçu aucune valeur pour `BLUE_MAGIC_ANDROID_KEYSTORE_BASE64` / `BLUE_MAGIC_ANDROID_KEYSTORE_PASSWORD`.

Aucun nouveau certificat n'a été généré et aucune continuité n'a été contournée.

La signature finale a utilisé le keystore permanent historique conservé dans l'espace de travail privé de la session, après vérification de son certificat SHA-256 exact. Le keystore et son mot de passe ne sont ni ajoutés au dépôt, ni exportés comme livrable utilisateur.

## 14. Recette physique recommandée

Les tests émulateurs prouvent la compatibilité Android, mais pas les variantes réelles Camtel/USSD/constructeurs. Tester :

1. installer 2.9.2 directement par-dessus 2.9.1 permanente ;
2. ouvrir le nouveau tableau de bord ;
3. DSM : vérifier `Mes PoS aujourd'hui` ;
4. DSM : utiliser `AIDER` sur un PoS direct ;
5. tenter conceptuellement un PoS hors branche : il doit être refusé côté serveur ;
6. DAE : vérifier `Mes DSM aujourd'hui` ;
7. DAE : aider un DSM direct ;
8. vérifier qu'un PoS ordinaire n'est pas proposé comme domaine direct du DAE ;
9. créer/observer une escalade HOT/CRITICAL DSM → DAE puis tester l'appui DAE ;
10. rechercher `pilotage`, `continuité`, `files`, `santé`, `Business Health` ;
11. vérifier stock/prévision sans déclenchement automatique ;
12. vérifier commission sans modification silencieuse ;
13. TEST_NUMBER ;
14. solde / historique / détail ;
15. une petite transaction financière seulement après les tests non financiers.

## 15. ÉTAT DU PROJET APRÈS CETTE ÉTAPE

- Version : `2.9.2`
- Branche : `feat/bir-v2-9-2-free-premium-pilotage`
- SHA applicatif : `f123e766271511c6270305c5641ab4db93401c99`
- GitHub convergence : run `32191056591` SUCCESS
- GitHub matrice exacte : run `32191686889` SUCCESS
- Cloudflare activation : run `32192700739` SUCCESS
- Cloudflare Worker : `2.9.2-cloudflare`
- Cloudflare Version ID : `0d6acb10-cda7-43b0-b9dc-7ef07ab4460d`
- D1 : migrations jusqu'à `0009`, inchangée par 2.9.2
- APK : `2.9.2` / code57 / SHA `16096cb8bd2bebb2748236d83854eda56e4605ef29faeb4994eee7f68ceb849b`
- Certificat : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- Problème traité : Premium gratuit pour tous + cockpit ultra-simple + hiérarchie DSM/DAE + aide rapide
- Cause : les outils existaient partiellement/en profondeur mais leur présentation et le modèle Pro/payant ne correspondaient plus à la décision produit ; l'action d'aide distante devait être strictement hiérarchisée
- Correction : cockpit grand public + moteur `ops_assist` non financier + RBAC serveur + recherche globale
- Tests exécutés : contrats hérités, contrat 2.9.2, Worker dry-run, Gradle, exact Android 6/8/11, health production, signature historique, comparaison payload
- Résultat : aucune régression automatisée détectée
- Acquis : Premium 0 FCFA, DSM pilote PoS, DAE pilote DSM, appui DAE→PoS seulement escaladé HOT/CRITICAL, modes REMOTE/ROBOT, aucun SMS fallback, PIN local
- Reste : recette physique Camtel/USSD et retour terrain utilisateur
- À ne surtout pas modifier : package permanent, certificat historique, anti-double-transaction, hiérarchie, PIN local, modes REMOTE/ROBOT, absence de SMS fallback
- PR #4 : ne pas fusionner sans autorisation distincte
- Régression possible : aucune détectée automatiquement ; comportement opérateur/constructeur à confirmer physiquement
- Autorisation nécessaire avant prochaine action : diagnostic et correctifs terrain autorisés ; expansion/redimensionnement national toujours hors périmètre

## 16. Procédure obligatoire de reprise

Dans un nouveau chat :

`BLUE MAGIC / B.I.R. — REPRISE v2.9.2. Lis d'abord docs/BIR_V292_RELEASE_PERMANENTE_2026-08-18.md. Ancre applicative f123e766271511c6270305c5641ab4db93401c99. Production Worker 2.9.2-cloudflare / Version ID 0d6acb10-cda7-43b0-b9dc-7ef07ab4460d ; D1 jusqu'à 0009. APK permanente code57/name2.9.2 SHA256 16096cb8bd2bebb2748236d83854eda56e4605ef29faeb4994eee7f68ceb849b ; certificat f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5. Runs : convergence 32191056591 ; exact Android 32191686889 ; production 32192700739. Premium pour tous = 0 FCFA dans le périmètre du rôle. DSM gère ses PoS ; DAE gère ses DSM ; DAE→PoS uniquement escalade HOT/CRITICAL assignée. ops_assist = WAKE_SYNC non financier uniquement. Deux modes REMOTE/ROBOT ; aucun SMS fallback ; PIN jamais serveur/Remote/Admin ; PR #4 interdite de fusion sans autorisation distincte. Vérifie toujours GitHub→Actions→Cloudflare/D1→APK avant toute mutation.`
