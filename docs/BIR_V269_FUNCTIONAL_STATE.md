# B.I.R. / Blue Magic — état fonctionnel v2.6.9 — 2026-08-16

## Identité du projet

B.I.R. — **Blue Infinity Retail** — est le **nom commercial actuel du même projet Blue Magic**. Ce n’est pas une nouvelle application indépendante. Le moteur historique, le package Android, les données locales, les règles Camtel, Remote/Robot et l’architecture serveur restent ceux de Blue Magic.

Le nom commercial B.I.R. peut encore évoluer sans imposer un renommage technique du moteur.

## Références Git

- dépôt : `Delor85/BlueAuto`
- branche fonctionnelle B.I.R. : `feat/bir-v2-6-9-functional`
- commit métier validé : `88b47b4c49e8d20c37b8da5ecb3fae9b07d868b0`
- message : `feat: integrate BIR v2.6.9 over complete Blue Magic engine`
- branche v2.6.8 conservée : `fix/blue-magic-v2-6-recovery`
- PR #4 : ouverte, non fusionnée, head v2.6.8 `7f15fb7cb6e8112e4076cadbad6f5b784a010847`

## Android

- package : `com.profitloop.blueauto`
- versionCode : `49`
- versionName : `2.6.9`
- minSdk : `23` (Android 6)
- targetSdk : `34`
- certificat permanent SHA-256 : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- APK finale SHA-256 : `573e04ee152ff2e27f0361f408178ff3c7af7f39074a423f529f25bc406ce9dd`
- schémas de signature vérifiés : V1=true, V2=true, V3=true

La v2.6.9 utilise volontairement le même package et le même certificat permanent que Blue Magic. Elle est conçue comme une mise à jour de l’application existante et non comme une seconde application.

## Validation automatisée

Run principal : `31923100201` — **SUCCESS**.

Ce run a validé :

- catalogue Camtel ;
- intelligence messages Blue ;
- intégration Cloudflare Remote/Robot ;
- FIFO ;
- solde frais ;
- concurrence financière atomique ;
- finance-flow historique ;
- commandes directes PIN ;
- commissions et soldes v2.6.8 ;
- verrou sécurisé / verrou simple borné ;
- Centre Gérer responsive ;
- navigation/polling adaptatifs ;
- compatibilité vieux WebView ;
- ergonomie transactionnelle ;
- résilience plan de contrôle / multi-profils ;
- bandeau natif ;
- contrat B.I.R. v2.6.9 ;
- tests unitaires Java ;
- vrai `assembleRelease` Android ;
- package `com.profitloop.blueauto`, versionCode49/versionName2.6.9, minSdk23.

## Design B.I.R. intégré

Référence visuelle retenue par l’utilisateur :

- haut bleu nuit lumineux ;
- logo infini : B bleu dans la boucle gauche, R dans la boucle droite, I central or ;
- `B.I.R. — BLUE INFINITY RETAIL` ;
- signature `Rapide. Puissant. Infini.` ;
- identification compte visible avec rôle, nœud, slot SIM et numéro de la SIM ;
- solde Camtel en grande taille ;
- Disponible / Réservé confirmé / composante commission ou métrique adaptée au rôle ;
- bandeau d’action prioritaire doré ;
- modules B.I.R. plus denses ;
- textes secondaires agrandis ;
- dock : Accueil / Réseau / action centrale / Activité / Gérer ;
- action centrale : DAE=Piloter, DSM=Fournir, PoS=Vendre ;
- symbole infini doré lumineux sur le bouton central.

Les phrases méta/anti-concurrent du prototype ont été retirées. L’application parle uniquement de ses fonctions, produits Blue, réseau, activité et outils.

## Fonctions historiques explicitement préservées

Les formulaires/actions suivants restent présents et couverts par contrat :

- achat/demande auprès du supérieur ;
- approvisionnement enfant ;
- vente Blue client ;
- TEST_NUMBER ;
- solde propre ;
- 5 dernières transactions ;
- détail transaction ;
- solde enfant ;
- gel/dégel ;
- reset PIN enfant ;
- suspension/réactivation enfant ;
- modification/reset PIN Camtel ;
- comptes/slots/SIM ;
- vérification/liaison SIM ;
- permissions Accessibilité ;
- batterie ;
- démarrage/arrêt Robot ;
- état serveur ;
- rafraîchissement dashboard ;
- diagnostic/SAV ;
- modules avancés déjà présents dans `platform-v267.js`.

La règle est additive : **B.I.R. améliore l’interface sans supprimer l’ancien moteur Blue Magic**.

## Règles métier à ne jamais régresser

- hiérarchie DAE → DSM → PoS ;
- DAE voit sa pyramide ; DSM lui-même + ses PoS ; PoS lui-même ;
- DAE→DSM 10 % par défaut ; DSM→PoS 8 % par défaut ; surcharge individuelle possible ;
- préflight financier = cotation uniquement, aucune réservation ;
- réservation seulement après confirmation/création de commande ;
- Solde Camtel = solde réel du nœud, jamais somme du sous-arbre ;
- `Réservé après confirmation` séparé ;
- commandes non financières avec PIN local = USSD directs sans Accessibilité ;
- finance = pop-up PIN + Accessibilité ;
- perte Accessibilité avant composition = lease libéré, commande conservée en file, Robot logiquement actif ;
- verrou sécurisé jamais contourné ;
- verrou simple = tentative ponctuelle bornée + cooldown, jamais `disableKeyguard()` ;
- multi-SIM : un profil lent ne doit pas bloquer les autres ;
- aucune réintroduction du « Solde cumulé connu ».

## Paiement

`B.I.R. Pay` reste une fondation **NON OPÉRATIONNELLE**. Aucun fournisseur, connecteur, credential, endpoint de collecte ou débit Mobile Money n’est activé dans cette version.

## Production serveur

Cette livraison Android n’a pas modifié la production serveur :

- Worker production reste sur le dernier ancrage vérifié `2.6.7-cloudflare` ;
- D1 production reste appliquée jusqu’à `0004` ;
- migration source `0005_commission_policies_and_financial_quotes.sql` n’est pas appliquée en production ;
- aucun Worker v2.6.8/v2.6.9 n’a été déployé pendant cette intégration B.I.R.

Toute mutation D1/Worker reste une opération distincte nécessitant une autorisation explicite.

## Android terrain

La Preview antérieure était une mauvaise base de livraison car elle utilisait `com.profitloop.birpreview` et une signature éphémère ; elle pouvait donc apparaître à côté de Blue Magic et l’utilisateur a signalé un échec d’installation Android 11.

La présente APK corrige l’identité de mise à jour : même package `com.profitloop.blueauto`, version supérieure et certificat permanent historique.

À confirmer immédiatement sur appareils réels :

1. Android 11 : installation par-dessus Blue Magic existante, lancement, données/profil conservés ;
2. Android 6 : mise à jour + lancement + petit écran ;
3. Android 8 si disponible ;
4. TEST_NUMBER ;
5. solde propre ;
6. Remote↔Robot ;
7. Accessibilité finance ;
8. verrou simple et sécurisé ;
9. vente/approvisionnement selon rôle ;
10. SIM phone number affiché dans l’identification.

Ne pas classer Android 11 « validé terrain » avant ce test physique.

## Reprise obligatoire dans un nouveau chat

Copier-coller :

> Reprends le même projet Blue Magic désormais présenté commercialement comme B.I.R. — Blue Infinity Retail. Commence par lire `docs/BIR_V269_FUNCTIONAL_STATE.md`, puis `docs/PROJECT_STATE_V268_FINAL.md`, `docs/PROJECT_STATE.md`, `docs/PROCEDURE_REPRISE_EXTERNE.md` et `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md`. Vérifie GitHub en direct avant toute modification. La branche fonctionnelle B.I.R. est `feat/bir-v2-6-9-functional`; le commit métier validé est `88b47b4c49e8d20c37b8da5ecb3fae9b07d868b0`; le run complet `31923100201` est SUCCESS. B.I.R. n’est pas une nouvelle app : package `com.profitloop.blueauto`, versionCode49/versionName2.6.9, certificat permanent `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`. L’APK finale a SHA-256 `573e04ee152ff2e27f0361f408178ff3c7af7f39074a423f529f25bc406ce9dd`. Préserve absolument toutes les fonctions Blue Magic et les règles métier listées dans ce document. Le design retenu est bleu nuit/cyan/or, logo infini B-gauche/I-centre/R-droite, identification compte + numéro SIM, grand solde, bandeau action doré, modules denses, textes secondaires lisibles et dock Accueil/Réseau/Piloter-Fournir-Vendre/Activité/Gérer. Ne réintroduis aucun texte méta sur un concurrent/catalogue. B.I.R. Pay reste non opérationnel. PR #4 reste ouverte/non fusionnée. Production Worker/D1 reste v2.6.7 + 0004 : ne pas appliquer 0005 ni déployer Worker sans nouvelle autorisation. La prochaine priorité est le test terrain de l’APK fonctionnelle sur Android 11 puis Android 6/8 et les scénarios USSD réels.
