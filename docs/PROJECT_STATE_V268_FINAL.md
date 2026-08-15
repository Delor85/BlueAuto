# BLUE MAGIC — ÉTAT DE REPRISE v2.6.8 APRÈS STABILISATION ET OPTIMISATION

Date de gel documentaire : 16 août 2026.

Ce document complète `docs/PROJECT_STATE.md`. Il décrit le dernier état **source/test** de la v2.6.8. Il ne constitue aucune autorisation de production.

## 1. Références de reprise

- Dépôt : `Delor85/BlueAuto`
- Branche : `fix/blue-magic-v2-6-recovery`
- PR : `#4`, à garder **OUVERTE ET NON FUSIONNÉE** jusqu’à validation terrain et nouvelle autorisation explicite.
- Base source propre avant ce document : `d13069bba15e0fede659d72fcc724473c804e963`
- Android source : `versionName 2.6.8`, `versionCode 48`, `minSdk 23`, `targetSdk 34`
- Worker source : `2.6.8-cloudflare`
- Migration source additive : `0005_commission_policies_and_financial_quotes.sql`

### Production inchangée par ce lot

Dernier ancrage de production vérifié avant cette stabilisation :

- Worker : `2.6.7-cloudflare`
- Cloudflare Version ID : `83bc2dd7-e28c-41f2-88f9-710c1b9dd649`
- D1 : migrations appliquées jusqu’à `0004_blue_message_intelligence_and_modules.sql`
- APK permanente : v2.6.7, package `com.profitloop.blueauto`, versionCode 47
- certificat permanent connu : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`

**Pendant la préparation v2.6.8 : aucun Worker 2.6.8 n’a été déployé, `0005` n’a pas été appliquée en production, aucune APK permanente v2.6.8 n’a été publiée et PR #4 n’a pas été fusionnée.**

## 2. Acquis fonctionnels v2.6.8

### Finance / solde

- Le précontrôle d’approvisionnement est une **cotation sans réservation**.
- Aucun FCFA n’est retranché du disponible avant confirmation de la commande financière.
- La réservation réelle commence uniquement à la création de la commande confirmée.
- La garde atomique D1 à la création finale empêche deux commandes concurrentes de dépenser le même stock.
- `Solde Camtel` est le dernier solde canonique du nœud, jamais la somme de la sous-arborescence.
- `Réservé après confirmation` représente les commandes financières confirmées non terminales.
- `Disponible = Solde Camtel - Réservé après confirmation`.
- Une preuve EXACTE peut être réutilisée jusqu’à 1 h pour une décision financière si aucun mouvement financier non rapproché n’est postérieur.
- Une preuve EXACTE peut rester utilisable jusqu’à 14 h pour un rapport si aucune activité non rapprochée ne la rend incohérente.
- La chronologie opérateur prévaut sur la priorité de source : un ancien SMS retardé ne fait pas régresser un solde plus récent.

### Commissions

- DAE → DSM : taux par défaut 10 % (`1000 bps`).
- DSM → PoS : taux par défaut 8 % (`800 bps`).
- Taux personnalisable par enfant direct.
- Confirmation 1/2 : montant de base + commission = total réellement transféré.
- Le montant de base maximal compatible avec un solde restant est calculé en FCFA entiers.
- Base, taux et commission participent à l’empreinte de confirmation ; une modification de taux invalide une ancienne confirmation.
- Les vues stock / composante commission / total sont des vues comptables dérivées d’un seul solde Camtel réel.

### Commandes USSD

- Les transferts financiers restent interactifs et utilisent le pop-up PIN Camtel.
- Les commandes non financières avec PIN local incorporé — solde, cinq dernières transactions, détail, solde enfant et administration — sont des USSD directs et ne dépendent pas de l’Accessibilité.
- `TEST_NUMBER` reste direct.
- Aucun résultat intermédiaire `Request is processed successfully` n’est considéré comme succès financier final.

## 3. Robot, Accessibilité et verrou Android

- Android reste seul maître de l’autorisation AccessibilityService ; Blue Magic ne tente pas de s’auto-accorder cette permission.
- Si l’Accessibilité disparaît avant composition d’une finance, le lease est relâché sans échec financier, la commande reste/revient en file et le Robot reste logiquement actif.
- Un verrou PIN/schéma/mot de passe/biométrique n’est jamais contourné.
- Un simple verrou sans identifiant peut recevoir une tentative transparente, courte et ponctuelle au moment où une commande attend.
- Cette tentative possède un délai borné et un cooldown par profil afin d’éviter le tremblement d’écran observé avec les anciens mécanismes.
- Si le verrou simple ne peut pas être libéré proprement, Blue Magic renonce, rend la commande à la file et demande un déverrouillage humain.
- L’ancien `InsecureKeyguardDismissActivity` / mécanisme `disableKeyguard()` a été supprimé.

## 4. Interface et ergonomie

### Centre GÉRER

L’ancien panneau fixe de 260 dp a été remplacé par un centre de gestion responsive :

- groupes `COMPTE & SIM`, `PIN CAMTEL`, `ROBOT & TÉLÉPHONE`, `FILES & SÉCURITÉ` ;
- deux colonnes compactes quand la largeur le permet ;
- retour automatique à une colonne sur les écrans extrêmement étroits ;
- écran principal non repoussé par le panneau ;
- actions sensibles toujours accessibles par défilement.

### Navigation par rôle

- DAE : `Pilotage / Réseau / Flux / Robot / SAV`.
- DSM : `Soldes / Réseau / Flux / Robot / SAV`.
- PoS : `Solde / Vente / Robot / Aide` ; la Flotte administrative est masquée.
- Des badges signalent les commandes en attente et les problèmes Robot nécessitant une action.

### Petits et anciens téléphones

- rendu graphique allégé sur petite largeur/hauteur : animation poussière désactivée, flou et ombres réduits ;
- extension plateforme réécrite sans syntaxes JavaScript modernes fragiles sur vieux WebView (`const`, `let`, fonctions fléchées, optional chaining, nullish coalescing, template literals) ;
- modules avancés repliables et filtrés par rôle ;
- Remote : bandeau natif compact, sans fausse demande de SIM/Accessibilité ;
- Robot : deuxième ligne uniquement lorsqu’une action réelle est requise.

### Saisie transactionnelle

- claviers numériques/téléphone adaptés ;
- limitation et nettoyage des chiffres ;
- codes de nœuds normalisés en majuscules ;
- focus sur le champ invalide ;
- protection single-flight contre les doubles appuis ;
- les champs ne sont effacés qu’après création réussie, pas après annulation ou erreur.

## 5. Fluidité Remote ↔ Robot / multi-SIM

- Le polling UI n’est plus permanent et aveugle.
- Il s’arrête lorsque l’application est masquée.
- Seules les commandes non terminales sont interrogées ; les grandes files sont parcourues par petits groupes rotatifs.
- Le tableau de bord est actualisé principalement dans les onglets où il est utile.
- Le polling de base Robot reste à environ 5 s afin de ne pas augmenter inutilement la consommation batterie/réseau.
- Les appels retry-safe de contrôle (`heartbeat`, `lease_command`, `command_status`, tableau de bord) utilisent des timeouts plus courts que les opérations transactionnelles.
- Les appels financiers/événements conservent les délais conservateurs.
- Un profil dont la route réseau ralentit est temporairement différé localement avec backoff borné ; les autres SIM/profils continuent au lieu de rester bloqués derrière lui.

## 6. Périmètres de visibilité

- DAE : son compte, ses DSM directs et les PoS de sa propre pyramide.
- DSM : son compte et ses PoS directs uniquement.
- PoS : son propre compte uniquement.
- Les activités et soldes suivent le même périmètre.
- Les alias courts ne sont admis que dans un contexte hiérarchique non ambigu.

## 7. Jalons de validation

Principaux commits métier/optimisation :

- `02e15878305a45e3126c7109666f32f132decf29` — finance/Robot + Centre GÉRER responsive ;
- `2ef2055e17a53b0a269f07903e5946dfc61d86d4` — baseline Java/tests/assembleRelease ;
- `ece06e793c590fe79d5fe18124b3ed864e1ada80` — navigation/polling adaptatifs ;
- `ee5bf4955cc55b4bed9ab9a5cbac239df05e737f` — compatibilité vieux WebView ;
- `47b024ff8dbe7244c8037ddc24e2fb75a72522b3` — ergonomie transactionnelle ;
- `71d2ea762e531f76e97fc8386283d08e06bd4033` — isolation des profils réseau lents ;
- `46821fcc27b9c2fd153f2e977d6c3b92076f666b` — bandeau natif compact ;
- `3049ab4324fb91a97aae58fc279d3e418a108234` — documentation/métadonnées v2.6.8 ;
- `0154ae7b92dac164550461219888d6eda46cb72d` — workflow Android durci et validé.

Runs structurants :

- `31912541712` — baseline complet : SUCCESS ;
- `31912708159` — UX/performance : SUCCESS ;
- `31912826222` — vieux WebView : SUCCESS ;
- `31913194962` — ergonomie transactionnelle : SUCCESS ;
- `31913433933` — Remote↔Robot / multi-SIM : SUCCESS ;
- `31913528590` — bandeau compact : SUCCESS ;
- `31914207818` — hygiène documentation/métadonnées : SUCCESS ;
- `31914394704` — workflow standard durci : backend + APK Release de validation SUCCESS ; jobs permanents SKIPPED.

### Smoke Android v2.6.8

- Android 6 / API 23 : installation, lancement `MainActivity`, processus vivant, aucun crash détecté — SUCCESS (`31913804892`).
- Android 8 / API 26 : SUCCESS (`31914066517`).
- Android 11 / API 30 : SUCCESS (`31914066517`).
- Android 14 / API 34 : SUCCESS (`31914066517`).
- Android 16 / API 36 : **limite du harnais d’émulation** : le job `android-emulator-runner` est resté bloqué plus d’une heure dans son étape d’installation/lancement malgré un timeout prévu de 35 min et sans log final exploitable. Ce n’est pas enregistré comme échec applicatif ; API 36 reste obligatoire dans la matrice permanente lors d’une future livraison autorisée.

Ces smoke-tests ne simulent pas le réseau USSD Camtel réel. Ils valident installation/lancement/non-crash de l’APK Release éphémère.

## 8. CI/livraison durcie

Le workflow standard `build.yml` est désormais fail-closed :

- un push normal utilise exclusivement une clé Android éphémère ;
- les secrets de signature permanente ne sont lus que dans l’environnement `production` ;
- une future publication permanente exige `workflow_dispatch`, `publish_permanent=true` ET `authorized_sha == github.sha` ;
- le job vérifie une deuxième fois que le checkout correspond au SHA autorisé ;
- le build permanent exécute la même batterie de tests v2.6.8 que le build ordinaire ;
- le nom prévu du futur livrable est `Blue-Magic-v2.6.8-Stabilisation-Ergonomie-Release.apk` ;
- les matrices de livraison permanente conservent Android 6 à Android 16 et la vérification de mise à jour depuis la v2.6.5.

Le run standard `31914394704` a démontré que sur un simple push : backend et APK de validation passent, tandis que `android-permanent-apk`, `android-11-launch` permanent et `android-upgrade-*` sont SKIPPED.

## 9. Nettoyage

Avant ce gel :

- tous les scripts temporaires `v268_*` sous `.github/scripts` ont été supprimés ;
- tous les workflows temporaires de patch, compatibilité et smoke ont été supprimés ;
- sous `.github/workflows`, il ne reste que `build.yml` et `deploy-cloudflare.yml` ;
- aucun force-push n’a été utilisé ;
- l’historique existant n’a pas été écrasé.

## 10. Ce qu’il reste à tester sur téléphones réels

Avant toute déclaration « terrain validé » :

1. Android 6, 8 et 11 réels avec la future APK permanente signée ;
2. TEST_NUMBER écran actif et verrou simple ;
3. perte/réactivation AccessibilityService pendant attente d’une finance ;
4. Remote → Robot et reprise après veille/redémarrage ;
5. plusieurs profils/SIM sur le même téléphone, y compris une route réseau lente ;
6. solde propre, cinq dernières transactions, détail et solde enfant ;
7. DAE→DSM : 10 %, 9,5 %, 9,25 % et autre surcharge réelle ;
8. DSM→PoS : 8 % et surcharge réelle ;
9. calcul du montant maximal entier avec faible solde ;
10. annulation à la confirmation sans réservation ;
11. concurrence de deux demandes : deux cotations possibles, première confirmation réserve, seconde doit être refusée/recalculée si le stock a changé ;
12. PoS→client et validation du CurrentBalance final ;
13. rafraîchissement des soldes/activités et périmètres DAE/DSM/PoS ;
14. verrou sécurisé : file conservée jusqu’au déverrouillage humain ;
15. verrou simple : aucune boucle/tremblement et reprise correcte ;
16. Android 16 / API 36 dans la matrice de livraison permanente et, idéalement, sur un terminal physique si disponible.

## 11. Ce qu’il NE faut surtout PAS modifier

- Ne pas fusionner PR #4 sans autorisation distincte.
- Ne pas appliquer `0005` en production sans autorisation distincte.
- Ne pas déployer Worker 2.6.8 sans autorisation distincte.
- Ne pas publier d’APK permanente v2.6.8 sans autorisation visant un SHA exact.
- Ne pas réintroduire la réservation au préflight.
- Ne pas réintroduire le « Solde cumulé connu ».
- Ne pas contourner les verrous sécurisés Android.
- Ne pas réintroduire `disableKeyguard()`.
- Ne pas faire dépendre les commandes USSD directes avec PIN local de l’Accessibilité.
- Ne pas remplacer le noyau Remote → Worker/D1 → Robot → USSD déjà validé par une réécriture globale.
- Ne pas exposer le PIN Camtel ou les secrets de signature dans les logs, D1, Worker ou JavaScript.

## 12. Procédure obligatoire de reprise dans un autre chat

### AVANT DE MODIFIER LE PROJET

1. Lire ce fichier en premier.
2. Lire `docs/PROJECT_STATE.md` pour l’historique détaillé.
3. Lire `docs/PROCEDURE_REPRISE_EXTERNE.md` et `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`.
4. Vérifier en direct le HEAD de `fix/blue-magic-v2-6-recovery` et l’état de PR #4.
5. Vérifier les derniers runs GitHub Actions du HEAD.
6. Vérifier séparément l’état production avant toute proposition de mutation Cloudflare/D1.
7. Ne jamais supposer qu’une ancienne autorisation couvre une nouvelle version ou un nouveau SHA.
8. Préserver les tests existants ; si un test historique devient incompatible avec une règle approuvée, démontrer d’abord qu’il s’agit d’une attente obsolète avant de le modifier.
9. Travailler par petits lots indépendants et refaire Worker + contrats v2.6.8 + Java/unit + `assembleRelease` après chaque lot risqué.
10. Après toute livraison autorisée, enregistrer SHA, runs, Worker Version ID, migrations appliquées, APK, SHA-256, certificat et résultats terrain.

### MESSAGE DE REPRISE À COPIER

> Reprends Blue Magic depuis `Delor85/BlueAuto`, branche `fix/blue-magic-v2-6-recovery`, PR #4. Commence par lire `docs/PROJECT_STATE_V268_FINAL.md`, puis `docs/PROJECT_STATE.md`, `docs/PROCEDURE_REPRISE_EXTERNE.md` et `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`. Vérifie le HEAD et les Actions en direct avant toute modification. La source cible est v2.6.8 / versionCode 48 ; la production reste sur l’ancrage v2.6.7 précédemment vérifié tant qu’une nouvelle autorisation n’a pas été donnée. La migration source `0005_commission_policies_and_financial_quotes.sql` ne doit pas être appliquée sans autorisation. Ne fusionne pas PR #4. Préserve : préflight sans réservation, réservation seulement après confirmation, commissions 10 % DAE→DSM / 8 % DSM→PoS avec surcharges, Solde Camtel non agrégé, commandes non financières directes, perte d’Accessibilité sans consommation de finance, verrou sécurisé jamais contourné, verrou simple borné sans tremblement, navigation responsive par rôle, multi-SIM non bloquant et CI permanente SHA-gatée. Reprends par la validation du dernier run standard propre puis prépare uniquement les tests terrain ou la prochaine étape explicitement autorisée.

## 13. Autorisation nécessaire avant prochaine mutation production

**OUI.** Toute application D1 `0005`, tout déploiement Worker 2.6.8 et toute production d’APK permanente v2.6.8 exigent une nouvelle autorisation explicite et bornée au SHA concerné.
