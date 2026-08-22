# B.I.R. / Blue Magic 2.9.7 — audit, stabilisation terrain et reprise

Date de vérité : **23 août 2026 — Africa/Douala**

## 1. Règle de reprise et source de vérité

Ordre obligatoire : **GitHub → GitHub Actions → Cloudflare/D1 → branches/commits/PR → APK/artefacts → conversations précédentes seulement comme contexte**.

Socle 2.9.6 vérifié avant toute modification :

- branche : `fix/bir-v2-9-5-identity-balance-sync` ;
- PR : `#66`, ouverte, non fusionnée ;
- source fonctionnelle : `85d49d4a06e1e96d2c47064281460bedc0afb52b` ;
- head d'autorisation 2.9.6 : `a6cdf9edf7729cdcaa052ab51926b247064b6e23` ;
- run 2.9.6 : `32400502528` — SUCCESS ;
- APK terrain 2.9.6 : `versionCode 61`, SHA-256 `d5fc06b0978d8d9a9c96cbc0d6ba4f9c03ab8699d5a1022f84cd07a5dafa7a87` ;
- production à préserver : Worker `2.9.2-cloudflare`, D1 online selon le dernier audit/live health déjà certifié ;
- migrations `0010`/`0011` : prêtes en Git mais non déployées.

**Interdiction : ne fusionner aucune PR et ne déployer aucun Worker / migration D1 sans autorisation explicite séparée.**

## 2. Branche et PR 2.9.7

- branche candidate : `fix/bir-v2-9-7-field-resilience-ai` ;
- base exacte : head 2.9.6 `a6cdf9edf7729cdcaa052ab51926b247064b6e23` ;
- PR : `#67`, brouillon, empilée sur la branche 2.9.6 pour isoler le delta 2.9.7 ;
- Android : `versionName 2.9.7`, `versionCode 62`, minSdk 23 conservé ;
- aucune mutation Cloudflare/D1 ;
- aucune modification de commande USSD, de PIN financier, de leasing FIFO ou de confirmation financière.

## 3. Problèmes terrain ciblés

1. Le Robot PoS1 traite enfin la file, mais l'utilisateur ne voit plus suffisamment la file ni l'activité.
2. `Mes outils` semble inactif parce que le détail est rendu après toute la grille.
3. Le bouton de rafraîchissement du solde n'est pas assez visible, particulièrement en Remote.
4. La télémétrie Robot ↔ Remote doit apparaître dans l'interface au plus tard en 30 s, cible 5 s, sans provoquer d'USSD automatiques inutiles.
5. La perte d'Accessibilité peut stopper un Robot au moment du PIN ; l'alerte doit devenir prioritaire et visible côté Remote.
6. Sur Android 8 dual-SIM, un téléphone peut héberger deux Robots et parfois une relation supérieur/enfant ; le routage SMS doit utiliser le slot physique en priorité et ne jamais attribuer un message à un compte en cas d'ambiguïté.
7. L'Assistant opérationnel local prévu dans la trajectoire 2.9.3/2.9.4 doit être réellement visible et utilisable.

## 4. Correctifs 2.9.7 réalisés

### 4.1 File et activité en direct

Nouveau module `field-ops-v297` chargé depuis `index.html` :

- carte `Robot ⇄ Remote — File & activité en direct` placée près du solde ;
- compteurs En attente / À vérifier / Incidents ;
- dernières commandes/activités visibles ;
- rafraîchissement de la télémétrie serveur et de la file toutes les **5 s lorsque l'interface est visible** ;
- aucun nouvel USSD n'est lancé automatiquement par cette boucle ;
- polling suspendu quand la WebView n'est pas visible pour limiter batterie et requêtes.

### 4.2 Solde visible et volontaire

Ajout d'un bouton prioritaire **ACTUALISER SOLDE** dans la carte live. Il réutilise le flux historique `CHECK_BALANCE` : en Remote l'ordre est envoyé au Robot ; côté Robot l'USSD reste une action explicite de l'utilisateur, jamais un effet secondaire de la télémétrie 5 s.

### 4.3 `Mes outils` dynamique

Le panneau historique `v292Detail` est déplacé dynamiquement juste après l'outil sélectionné. Aucun outil n'est supprimé et les gestionnaires historiques restent exécutés avant le repositionnement.

### 4.4 Assistant opérationnel B.I.R. local

Assistant léger, gratuit et hors ligne, sans LLM embarqué :

- questions guidées : `Pourquoi ça ne part pas ?`, `Que dois-je faire ?`, `Pourquoi le Robot est malade ?`, `Puis-je vendre ?` ;
- interprétation déterministe de la file, du mode, de la SIM, du PIN, de l'Accessibilité, de la disponibilité du Robot et de la preuve de solde locale ;
- saisie libre limitée aux thèmes opérationnels ;
- **interdiction de créer, prévisualiser, confirmer ou répéter une transaction** ;
- aucune donnée commerciale envoyée à une IA tierce.

Le test 2.9.7 refuse le build si ce module commence à appeler `createCommand()` ou `previewCommand()`.

### 4.5 Urgences visibles

Bannière prioritaire en haut de l'interface pour :

- PIN bloqué ;
- SIM Robot non vérifiée ;
- Accessibilité désactivée ;
- Accessibilité autorisée mais service déconnecté ;
- Robot local arrêté ;
- Robot Remote déclaré stale/offline par la télémétrie connue.

Le message commence par la cause essentielle afin de rester compréhensible même si Android tronque le texte secondaire.

### 4.6 Dual-SIM supérieur/enfant — routage prudent

`SmsReceiver` conserve la règle principale : **subscriptionId / slot Android exact d'abord**. Si certains firmwares Android 8 omettent l'information de slot et plusieurs Robots sont possibles, B.I.R. n'utilise en secours que des preuves locales fortes :

- numéro de SIM configuré contenu dans le message ;
- cible d'une commande locale active unique ;
- montant attendu comme indice secondaire ;
- relation parent → enfant unique pour un `TRANSFER_RECEIVED`.

Si deux profils obtiennent le même meilleur score, le message n'est attribué à aucun compte : mieux vaut laisser une preuve à réconcilier que contaminer un solde réel.

## 5. Anti-régression

Les fonctions historiques restent obligatoires : achat enfant, approvisionnement, vente client, test numéro, solde, cinq dernières transactions, détail transaction, solde enfant, gel/suspension/réactivation, comptes/slots, vérification SIM, permissions, PIN, batterie, centre Gérer, Robot et santé serveur.

Contrats supplémentaires 2.9.7 :

- assets `field-ops-v297.js/css` obligatoirement chargés ;
- syntaxe JavaScript vérifiée par Node ;
- télémétrie 5 s présente ;
- Assistant sans appels financiers ;
- polling arrêté quand l'UI est masquée ;
- SMS dual-SIM `fail closed` en cas d'égalité ;
- slot Android physique reste prioritaire.

## 6. Accessibilité — limite Android à ne pas masquer

Une application ne peut pas garantir que le système Android/OEM ne tuera jamais un service d'Accessibilité ni réactiver silencieusement une autorisation retirée par l'utilisateur/système. B.I.R. doit donc combiner :

1. permission Accessibilité explicitement accordée ;
2. Foreground Service / WakeLock déjà présents ;
3. exclusion de l'optimisation batterie au niveau du téléphone ;
4. détection de `enabled` versus `connected` ;
5. maintien de la file au lieu de recréer la transaction ;
6. alerte prioritaire Remote quand la télémétrie indique que le Robot devient inaccessible.

La 2.9.7 renforce les points 5/6 dans l'interface. Un durcissement OEM spécifique (Tecno/Infinix/Samsung/Xiaomi selon appareil exact) doit être validé sur chaque téléphone terrain avant toute promesse de permanence absolue.

## 7. Tests automatiques et terrain

### Automatiques obligatoires

- Worker/D1 : parsing, intégration, FIFO, concurrence atomique, soldes frais ;
- WebView : contrats historiques + 2.9.7 ;
- Java : tests unitaires existants ;
- Android : assemblage Release ;
- APK : package `com.profitloop.blueauto`, `versionName 2.9.7`, `versionCode 62`, minSdk 23 ;
- aucun déploiement Cloudflare pendant ces tests.

### Terrain avant toute fusion/déploiement

**Android 6**
1. mise à jour en place sans désinstaller ;
2. Remote : ouvrir Accueil, vérifier File/Activité et Assistant ;
3. passer au Robot si prévu et lancer `TEST_NUMBER` ;
4. verrou simple, veille, redémarrage, reprise ;
5. vérifier qu'aucune donnée 2.9.6 n'est perdue.

**Android 8 — téléphone deux Robots**
1. vérifier les deux slots et les deux profils ;
2. lancer une file PoS1 et laisser le téléphone en veille au moins 15–30 min ;
3. surveiller Accessibilité ;
4. si elle tombe, vérifier bannière urgente et conservation de la commande ;
5. vérifier que la reprise ne nécessite pas de recréer la transaction.

**DSM1 / PoS1**
1. DSM1 : compte officiel `DSM1_SU1`, SIM terrain connue, supérieur `SU1` ;
2. PoS1 : alias `POS1`, supérieur complet `DSM1_SU1`, identité officielle `POS1_DSM1_SU1` ;
3. acheter/approvisionner un montant minimal réel supervisé ;
4. contrôler les deux SMS supérieur/enfant ;
5. contrôler que le solde supérieur et le solde enfant ne sont pas inversés ;
6. fermer/rouvrir les deux applications et vérifier que les preuves restent cohérentes.

**Remote ⇄ Robot**
1. exécuter une action sur Robot ;
2. chronométrer l'apparition sur Remote, cible ≤ 5 s, plafond terrain 30 s ;
3. créer une action depuis Remote et vérifier sa prise en charge Robot ;
4. couper Internet brièvement, puis rétablir : la file doit survivre ;
5. ne jamais dupliquer une commande pour “aider” la reprise.

## 8. Évolutions proposées après stabilisation 2.9.7

À ne pas mélanger au correctif terrain actuel :

- centre de notifications unique : Urgences → Finance → Technique ;
- instrumentation Android réelle API23/API26 dans CI ;
- télémétrie “dernier heartbeat / dernière activité / dernière preuve” standardisée dans toutes les vues ;
- diagnostic constructeur pour restrictions batterie/auto-start ;
- assistant conversationnel serveur optionnel uniquement pour rapports/comptabilité, sans droit d'exécution financière et avec données minimisées ;
- prévisions de rupture de stock et recommandations de réapprovisionnement basées sur historiques certifiés.

## 9. Rentabilisation pragmatique

Le cœur transactionnel quotidien doit rester accessible. Monétiser les gains de pilotage :

- **Robot Pro** : santé Robot, historique long, alertes avancées, reprise assistée ;
- **DAE Pilotage** : War Room réseau, prévisions de rupture, commissions, rapprochements, exports ;
- **SAV/Rescue** : assistance prioritaire et migration/remplacement guidé ;
- **API Business** : exports ERP/comptables et preuves signées lorsque l'API sera stabilisée ;
- **White Label** : autres distributeurs/opérateurs après validation contractuelle ;
- **Academy** : formation/certification des DSM/PoS.

Les hypothèses 2.9.6 de 1 000–2 500 FCFA/terminal/mois pour Robot Pro et 15 000–30 000 FCFA/DAE/mois pour Pilotage restent des **hypothèses pilote**, à valider avec usage réel avant tarification définitive.

## 10. Procédure obligatoire de sauvegarde et reprise vers un autre chat

Avant de quitter cette conversation :

1. relever la branche 2.9.7, la PR #67, son head exact et le dernier run CI ;
2. conserver le socle 2.9.6 : source `85d49d4a06e1e96d2c47064281460bedc0afb52b`, head `a6cdf9edf7729cdcaa052ab51926b247064b6e23`, run `32400502528`, APK/SHA 2.9.6 ;
3. conserver ce rapport 2.9.7 dans GitHub ;
4. si une APK 2.9.7 candidate est produite, relever son nom, sa nature **EPHEMERAL ou PERMANENTE**, son SHA-256 et le run exact ;
5. noter l'état production séparément : Worker `2.9.2-cloudflare`, D1 online d'après le dernier état vérifié ; aucune migration 0010/0011 ni aucun Worker 2.9.6/2.9.7 ne doit être supposé déployé sans preuve ;
6. joindre au nouveau chat le cahier des charges le plus récent et ce rapport ;
7. ne jamais coller PIN Blue, secret d'appairage, token GitHub/Cloudflare, mot de passe de keystore ou keystore dans le chat ;
8. imposer la même source de vérité GitHub → Actions → Cloudflare/D1 → commits/PR → APK → anciens chats ;
9. reprendre par les tests terrain, pas par une refonte.

### Prompt de reprise 2.9.7

> BLUE MAGIC / B.I.R. — REPRISE 2.9.7. Vérifier dans cet ordre : GitHub → Actions → Cloudflare/D1 → commits/PR → APK → anciens chats. Lire `docs/BIR_2.9.7_Audit_Livraison_Reprise_2026-08-23.md`, puis le dernier cahier des charges. Socle : branche `fix/bir-v2-9-5-identity-balance-sync`, PR #66, source `85d49d4a06e1e96d2c47064281460bedc0afb52b`, head 2.9.6 `a6cdf9edf7729cdcaa052ab51926b247064b6e23`, run `32400502528` SUCCESS, APK permanente 2.9.6 code61 SHA-256 `d5fc06b0978d8d9a9c96cbc0d6ba4f9c03ab8699d5a1022f84cd07a5dafa7a87`. Candidate 2.9.7 : branche `fix/bir-v2-9-7-field-resilience-ai`, PR #67 brouillon empilée sur 2.9.6, Android code62. Production à préserver : Worker `2.9.2-cloudflare`, D1 online selon dernier audit ; ne rien fusionner ni déployer sans autorisation explicite. Reprendre par CI puis tests terrain Android 6/8, DSM1/POS1, file/activité, soldes réels, Accessibilité, Robot↔Remote ≤ 5–30 s et dual-SIM supérieur/enfant.

## 11. Point de reprise technique

Ne jamais recommencer l'architecture. La 2.9.7 est une couche additive au socle 2.9.6 : si un test échoue, corriger le défaut ciblé et ajouter/renforcer un contrat de non-régression avant de poursuivre.
