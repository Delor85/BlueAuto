# Blue Magic — Référentiel opérateur Camtel / Blue

Version applicative : **2.6.7**. Ce document décrit le référentiel actif. Il ne contient aucun PIN, secret d’appairage ni donnée de signature.

## Identités canoniques

- DAE : `XXY`, par exemple `OU3`, `CE04`, `LT10`. `XX` est l’abréviation régionale et `Y` le rang du DAE dans la région.
- DSM : `DSMZ_XXY`, par exemple `DSM7_OU3`. Dans l’arborescence du DAE `OU3`, le raccourci `DSM7` est accepté; la base conserve toujours `DSM7_OU3`.
- PoS : `POSA_DSMZ_XXY`, par exemple `POS16_DSM7_OU3`. Dans l’arborescence du DSM `DSM7_OU3`, le raccourci `POS16` est accepté; la base conserve toujours le nom complet.
- Accès direct DAE vers un PoS : nom complet obligatoire, car plusieurs DSM peuvent chacun posséder un `POS5`.
- `node_code` est globalement unique et le numéro SIM est globalement unique. Les messages Blue/Camtel sont rapprochés du nœud canonique par numéro SIM quand celui-ci est connu.

## Régions

`AD` Adamaoua · `CE` Centre · `ES` Est · `EN` Extrême-Nord · `LT` Littoral · `NO` Nord · `NW` Nord-Ouest · `OU` Ouest · `SU` Sud · `SW` Sud-Ouest.

## Validation de création

Le DAE pré-enrôle/valide ses DSM et le DSM pré-enrôle/valide ses PoS. La première activation doit intervenir dans les 48 heures de cette validation. La création d’un DAE racine reste protégée par le mécanisme super-admin d’appairage. Un rôle ne peut pré-enrôler que le niveau immédiatement inférieur.

## Où modifier si Camtel change les noms ou les codes

1. `cloudflare/src/camtel-catalog.mjs` : régions, grammaire canonique, filiation et catalogue public des commandes.
2. `app/src/main/java/com/profitloop/blueauto/CamtelUssdCatalog.java` : commandes réellement composées par Android.
3. Mettre à jour les tests `cloudflare/test/camtel-catalog.mjs`, `cloudflare/test/blue-message-intelligence.mjs` et les contrats Android avant tout déploiement.

Le Worker reste l’autorité pour la filiation. L’APK ne devine jamais l’identité à partir d’un montant de solde anonyme : une réponse `BALANCE_CHILD` est attribuée au `target_node_code` complet déjà connu de la commande.

## Audit nocturne

La fraîcheur financière reste limitée à 1 heure. Pour le rapport du matin, une preuve EXACTE peut être réutilisée jusqu’à 14 heures si aucun mouvement financier non rapproché n’est postérieur à la preuve. Les audits sont répartis de façon déterministe : PoS à partir de 02:00, DSM à partir de 03:00, DAE à partir de 04:00, puis un petit balayage final DAE avant 06:00. Le Worker limite chaque vague à de petits lots et traite d’abord les comptes `P0_RECHECK`, puis aveugles/actifs, puis dormants.

Le rapport est **vivant** : il est recalculé au moment de l’ouverture. Une transaction postérieure à l’audit avec `CurrentBalance` remplace la preuve; sans `CurrentBalance`, le compte passe à `RECHECK_REQUIRED`.
