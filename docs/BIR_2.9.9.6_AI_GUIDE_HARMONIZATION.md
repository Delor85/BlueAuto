# B.I.R. 2.9.9.6 — Harmonisation Assistant / Guide utilisateur

Date : 2026-08-25
Branche : `feat/bir-v2-9-9-6-ai-guide-harmonization`
Base : `fix/bir-v2-9-9-3-android11-child-warroom-tchoronko` @ `e27a0ead275b44be880461a9be548bb3c9c5a0c5`

## Objectif

Converger les demandes UX/IA du 25 août 2026 avec les acquis B.I.R. 2.9.7 → 2.9.9.5, sans réécrire le moteur financier et sans réintroduire les couches historiques ayant provoqué des instabilités Android 11.

## Changements apportés

1. Le sélecteur de langue existant `EN` / `FR` est réutilisé et déplacé dans un emplacement compact de 42 px à gauche, juste sous la zone supérieure de l'interface. Il reste bien visible mais ne monopolise plus la largeur.
2. L'espace horizontal est utilisé par une barre de découverte de l'Assistant B.I.R. avec exemples tournants : brief complet, alerte POS1, diagnostic boutons, Check Réseau, actualisation, synchronisation, ouverture Réseau, état serveur, commissions, préparation d'approvisionnement, liste des services, aide Tchoronko.
3. Le clic sur un exemple ouvre l'Assistant et soumet la question correspondante.
4. Un catalogue local des services est ajouté par rubrique : Accueil, Réseau, Piloter/Fournir/Vendre, Activité, Gérer.
5. L'Assistant peut répondre à des formulations comme :
   - « Donne-moi la liste des services d'Accueil » ;
   - « Liste toutes les fonctionnalités » ;
   - « Comment utiliser Tchoronko ? » ;
   - « Comment fonctionne l'Assistant B.I.R. ? ».
6. La commande naturelle « Prépare 5 000 FCFA pour POS1 » ouvre le formulaire normal et préremplit uniquement l'enfant et le montant. Elle ne crée, ne prévisualise, ne confirme et n'exécute aucune transaction.
7. La couche reste ES5 / Android 6+ et ne contient ni `MutationObserver`, ni `setInterval`, ni composition USSD, ni appel direct au moteur financier.

## Convergence avec les cahiers des charges

Le cahier maître du 24 août demandait un guide utilisateur hors ligne plus complet et indiquait que l'Assistant devait pouvoir orienter l'utilisateur tout en restant séparé de l'exécution financière. Cette évolution ferme une partie importante de ce manque sans casser la frontière financière.

Les services documentés correspondent aux capacités actuellement présentes dans la lignée stable : identité/solde/preuves, War Room, Check Réseau, Tchoronko, commissions, transactions, file/journal, comptes, SIM/slots, Remote/Robot, PIN, Accessibilité, synchronisation et diagnostic.

## Invariants préservés

- aucune modification Cloudflare / D1 ;
- aucune modification des migrations ;
- aucune modification du Worker ;
- aucun changement des règles de preflight, double confirmation, FIFO, lease, idempotence ou UNKNOWN ;
- aucun changement du stockage PIN ;
- aucun changement du moteur USSD / Accessibilité ;
- aucun changement du multi-SIM / unicité Robot ;
- aucun changement de certificat/signature ;
- aucune réactivation des couches `transaction-first-v298.js`, `reference-stability-v299.js`, `field-runtime-v2991.js` ou `field-runtime-v2992.js`.

## Fichiers

- `app/src/main/assets/ai-guide-v2996.css` — nouveau ;
- `app/src/main/assets/ai-guide-v2996.js` — nouveau ;
- `app/src/main/assets/intelligence-v297.js` — loader étendu de manière additive ;
- `app/src/test/v2996-ai-guide-harmonization-contract.mjs` — nouveau contrat statique de non-régression.

## État de validation

Le contrat 2.9.9.6 est présent dans le dépôt mais aucun workflow GitHub Actions n'a été déclenché automatiquement par les commits de cette branche au moment de cette sauvegarde.

La version Android déclarée reste volontairement `2.9.9.5` / `versionCode 69` tant qu'une validation complète et une décision de livraison 2.9.9.6 n'ont pas été prises. Aucun APK 2.9.9.6 n'est donc revendiqué dans cet état.

## Validation terrain recommandée avant livraison

- Android 6 : position/visibilité EN-FR, clic barre IA, clavier, scroll et onglets ;
- Android 11 : absence de régression écran bleu/figé et War Room enfant ;
- Android récent : rendu responsive ;
- FR → EN → FR : persistance et reload ;
- toutes les questions proposées par la barre ;
- « Prépare 5 000 FCFA pour POS1 » : préremplissage seulement ;
- tentative avec rôle PoS : aucune préparation d'approvisionnement enfant ;
- finance réelle : parcours existant inchangé, confirmations habituelles inchangées.

## Point de reprise

HEAD de la branche après sauvegarde documentaire : voir dernier commit GitHub de `feat/bir-v2-9-9-6-ai-guide-harmonization`.
Ne pas déployer ni incrémenter la version sans validation CI + terrain et autorisation explicite de livraison/production.
