# Blue Magic v2.6.8 — stabilisation terrain, commissions et interface adaptative

Blue Magic automatise la distribution Blue/Camtel selon le trajet sécurisé **Remote → Worker/D1 → Robot détenteur de la SIM → USSD → preuve opérateur**. La branche de développement actuelle prépare `2.6.8` (`versionCode 48`, `minSdk 23`, `targetSdk 34`) sans modifier la production tant que la validation terrain et une nouvelle autorisation explicite n’ont pas été données.

> **Production réellement active :** Worker `2.6.7-cloudflare`, D1 migrée jusqu’à `0004`, APK permanente v2.6.7.
> **Développement :** v2.6.8 sur `fix/blue-magic-v2-6-recovery`, PR #4 ouverte/non fusionnée, migration additive `0005` présente dans les sources mais **non appliquée en production**.

## Noyau financier à préserver

- Chaque SIM Blue/Camtel est liée à son profil et à son slot physique.
- Un téléphone physique n’exécute qu’une session USSD à la fois.
- Les commandes financières sont prévisualisées puis confirmées par l’utilisateur avant création de la réservation D1.
- Le précontrôle de capacité est une **cotation seulement** : il ne réserve et ne déduit aucun FCFA. La réservation devient réelle uniquement à la création de la commande confirmée.
- La création finale garde une vérification atomique de capacité afin d’empêcher deux commandes concurrentes de dépenser le même stock.
- Un résultat incertain devient `UNKNOWN` et n’est jamais rejoué automatiquement.
- Le PIN Camtel reste local au téléphone, chiffré, absent du Worker, de D1 et du JavaScript.

## Commandes Camtel

Le catalogue opérateur est centralisé dans :

- Android : `app/src/main/java/com/profitloop/blueauto/CamtelUssdCatalog.java` ;
- Worker : `cloudflare/src/camtel-catalog.mjs` ;
- documentation : `docs/CAMTEL_OPERATOR_CATALOG.md`.

Les commandes non financières qui embarquent déjà le PIN local — solde, cinq dernières transactions, détail, solde enfant et administration — sont des USSD directs et **ne dépendent pas de l’Accessibilité**. Les transferts financiers restent interactifs et utilisent l’Accessibilité pour la fenêtre PIN Camtel.

## Solde vivant et preuves

`Solde Camtel` représente le dernier solde canonique connu pour **ce nœud**, jamais la somme de sa sous-arborescence. `Réservé après confirmation` représente les commandes financières confirmées encore non terminales. `Disponible = Solde Camtel - Réservé`.

La chronologie opérateur prévaut sur la priorité d’une source : un SMS ancien arrivé en retard ne peut pas faire régresser une preuve plus récente. Pour une décision financière, une preuve exacte peut être réutilisée jusqu’à **1 heure** uniquement en l’absence d’activité financière non rapprochée postérieure. Pour un rapport, une preuve exacte peut rester exploitable jusqu’à **14 heures** dans la même condition.

## Commissions v2.6.8

La migration source `0005_commission_policies_and_financial_quotes.sql` introduit :

- DAE → DSM : taux par défaut 10 % (`1000 bps`) et surcharge possible par DSM ;
- DSM → PoS : taux par défaut 8 % (`800 bps`) et surcharge possible par PoS ;
- mémorisation du montant de base, du taux et de la commission dans la cotation/commande ;
- confirmation 1/2 affichant **base + commission = total réellement transféré** ;
- calcul entier du montant de base maximal compatible avec le solde disponible ;
- empreinte de confirmation incluant le taux afin qu’un changement de commission invalide une ancienne confirmation.

Les vues DAE/DSM peuvent décomposer un solde réel Camtel en stock de base + composante de commission selon le taux par défaut. Il s’agit d’une vue comptable dérivée, pas de trois comptes Camtel séparés.

## Navigation et ergonomie adaptatives

Blue Magic garde les modules fonctionnels Rapports, Flotte/Réseau, Flux, Robot et SAV, mais leur présentation est adaptée au rôle :

- **DAE :** Pilotage, Réseau, Flux, Robot, SAV ;
- **DSM :** Soldes, Réseau, Flux, Robot, SAV ;
- **PoS :** Solde, Vente, Robot, Aide — la Flotte administrative est masquée.

Le panneau natif **GÉRER** est un centre de gestion défilable et responsive. Il utilise deux colonnes compactes lorsque la largeur le permet et repasse à une colonne sur les écrans très étroits. Les modules avancés sont repliables et exposés seulement aux rôles concernés.

Les vieux WebView Android restent pris en charge : l’extension plateforme n’emploie plus les syntaxes JavaScript modernes susceptibles de casser Android 6. Les petits écrans utilisent aussi un rendu visuel allégé (moins d’animation, de flou et d’ombres).

## Fluidité Remote ↔ Robot / multi-SIM

Le polling applicatif n’est plus exécuté aveuglément :

- les commandes sont interrogées seulement lorsqu’elles sont non terminales et que l’application est visible ;
- le tableau de bord est actualisé seulement dans les écrans où il est utile ;
- les appels de contrôle retry-safe (`heartbeat`, `lease_command`, `command_status`, tableau de bord) ont des délais réseau plus courts que les opérations transactionnelles ;
- un profil dont la route réseau ralentit est temporairement différé localement afin que les autres SIM/profils du téléphone continuent leur file ;
- la fréquence de base n’est pas augmentée inutilement, afin de préserver batterie et réseau.

## Verrou Android et Accessibilité

Blue Magic ne contourne jamais un PIN, schéma, mot de passe ou verrou biométrique. Sous verrou sécurisé, la commande reste/revient en file et un déverrouillage humain est requis.

Pour un simple verrou sans identifiant, une activité transparente peut faire **une tentative courte et bornée** au moment précis où une commande attend. Un cooldown empêche les boucles qui faisaient trembler certains téléphones. En cas d’échec, Blue Magic renonce à forcer l’écran et demande un déverrouillage humain.

Android conserve l’autorité sur l’activation de l’AccessibilityService : Blue Magic peut garder le Robot logiquement actif, surveiller/reprendre la file et guider l’utilisateur, mais ne peut pas s’auto-accorder silencieusement cette autorisation.

## Rôles et périmètres

La nomenclature canonique Camtel reste :

- DAE : `XXY` (`OU3`, `CE04`, `LT10`) ;
- DSM : `DSMZ_XXY` (`DSM7_OU3`) ;
- PoS : `POSA_DSMZ_XXY` (`POS16_DSM7_OU3`).

Le DAE voit sa propre pyramide ; un DSM voit son compte et ses PoS directs ; un PoS voit son propre compte. Les activités et soldes suivent le même périmètre. Les alias courts ne sont résolus que dans le contexte hiérarchique qui les rend non ambigus.

## CI et livraison

Les tests permanents couvrent le Worker/D1, les règles financières historiques, les contrats v2.6.8, la syntaxe WebView, les tests unitaires Java et un vrai `assembleRelease`.

Un build CI ordinaire doit utiliser une signature **éphémère**. Les secrets de signature permanente restent confinés au job `production`. Une future publication permanente v2.6.8 ne doit être possible qu’après une autorisation explicite visant un SHA exact, puis un lancement manuel avec le garde correspondant. Une compilation de validation n’est jamais une autorisation de production.

## Points de reprise

- état détaillé : `docs/PROJECT_STATE.md` ;
- procédure obligatoire : `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md` et `docs/PROCEDURE_REPRISE_EXTERNE.md` ;
- tests terrain : `docs/TEST_TERRAIN.md` ;
- catalogue opérateur : `docs/CAMTEL_OPERATOR_CATALOG.md`.

**Ne pas fusionner PR #4, ne pas appliquer `0005`, ne pas déployer Worker 2.6.8 et ne pas publier d’APK permanente v2.6.8 avant validation terrain et autorisation explicite séparée.**
