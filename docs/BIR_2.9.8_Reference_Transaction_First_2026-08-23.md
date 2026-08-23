# B.I.R. / Blue Magic 2.9.8 — Transaction First Reference

Date de décision : **23 août 2026 — Africa/Douala**

## 1. Statut et intention

Cette version transforme les arbitrages terrain de la 2.9.7 en une référence UX sans réécrire le moteur financier. La priorité produit devient explicitement : **vendre, acheter/demander du crédit, approvisionner**, puis sécuriser, comprendre et administrer.

Source de vérité obligatoire : **GitHub → GitHub Actions → artefacts APK → Cloudflare/D1 → anciens chats uniquement comme contexte**.

Socle de départ : branche `fix/bir-v2-9-7-field-resilience-ai`, head de livraison 2.9.7 `c92a62c2cccba62f2475a6544e92607e3d6e14e7`, source applicative permanente 2.9.7 `bd3401bf131eb647ea7cbeb2ad6c2213b691b20d`.

Branche 2.9.8 : `fix/bir-v2-9-8-transaction-first-reference`.

**Aucun déploiement Worker/D1 et aucune fusion de PR ne sont autorisés par cette livraison APK.**

## 2. Règles métier et UX désormais de référence

1. PoS = lui-même : aucun KPI, service de recherche ou administration « enfant » ne doit apparaître.
2. PoS : **VENDRE** est l'action principale ; **ACHETER / demander au DSM** est immédiatement disponible.
3. DSM : **APPROVISIONNER UN PoS** est principal ; **ACHETER / demander au DAE** est immédiatement disponible.
4. DAE : **APPROVISIONNER UN DSM** est principal ; son propre stock et sa nécessité de renforcement restent visibles sans inventer une commande opérateur inexistante.
5. Un solde réellement connu reste affiché même lorsqu'il n'est plus réutilisable pour une décision financière. Son statut est explicite : `VÉRIFIÉ`, `ESTIMÉ`, `ANCIEN` ou `À VÉRIFIER`.
6. **Afficher n'est pas certifier** : le préflight financier conserve ses règles historiques de preuve fraîche/réutilisable.
7. `null`, absence de débit ou données insuffisantes = **À estimer**, jamais « Rupture ».
8. L'état de la donnée et l'état commercial sont séparés.
9. La War Room devient secondaire/collapsible ; elle remonte par le résumé Situation B.I.R. lorsqu'une urgence existe.
10. Un seul Assistant B.I.R. opérationnel local reste la destination de tous les raccourcis Assistant.
11. La recherche est filtrée selon le rôle et **exécute réellement** les services cliquables au lieu de seulement scroller/focaliser.
12. L'identité affiche alias + identité officielle complète lorsque la filiation locale permet de la reconstruire : `DSM1_SU1`, `POS1_DSM1_SU1`.
13. Les outils historiques restent présents dans un espace secondaire repliable ; aucune fonction métier n'est supprimée.
14. La télémétrie applicative Robot↔Remote reste à **10 s**, l'alerte silence Robot à **60 s**, sans nouvel USSD automatique.

## 3. Architecture de consolidation

`field-ops-v297.js` reste le socle terrain pour file, activité, alertes et Assistant local. Son chargement historique de `intelligence-v297.js` est conservé pour compatibilité, mais ce fichier devient un **shim** qui charge une seule couche de référence `transaction-first-v298.js` / `transaction-first-v298.css`.

La 2.9.8 ne crée donc pas un quatrième cockpit concurrent : elle **consolide et réorganise** les interfaces existantes. Les cartes historiques sont conservées dans `Tous les outils` et restent adressables par leur ID et leurs handlers d'origine.

Le nouveau héros transactionnel ne crée jamais de commande financière lui-même. Il renseigne les champs historiques puis déclenche le bouton historique correspondant ; validation, préflight, double confirmation, idempotence, FIFO, PIN et Accessibilité restent dans le moteur acquis.

## 4. Anti-régression obligatoire

- package `com.profitloop.blueauto` ; minSdk 23 ; targetSdk 34 ; versionCode 63 ; versionName 2.9.8 ;
- REMOTE/ROBOT uniquement ;
- aucun `SEND_SMS` ;
- aucun appel `createCommand()`/`previewCommand()` depuis la couche Transaction-First ;
- aucun nouveau polling `setInterval()` dans cette couche ;
- PoS sans services enfants ;
- recherche click-through testée ;
- ancien solde visible mais non promu artificiellement en preuve financière ;
- `null != 0` pour la prévision de rupture ;
- reconstruction locale d'identité testée ;
- Cloudflare source identique au head 2.9.7 pendant ce chantier.

## 5. Recette terrain de référence

### PoS
- ouverture : identité courte + officielle, dernier solde connu et son statut ;
- vendre 1 montant minimal via le héros ; vérifier confirmation 1/2 puis résultat Blue ;
- acheter/demander au DSM depuis le héros ;
- aucun texte « Enfants en rupture / à assister » ;
- recherche `solde` puis clic : l'action correspondante s'exécute ;
- recherche `administration enfant` : aucun résultat ;
- Assistant B.I.R. : un seul panneau opérationnel s'ouvre ;
- fermeture/réouverture : dernier solde connu reste visible avec fraîcheur honnête.

### DSM
- approvisionner un PoS puis demander du stock au DAE ;
- recherche filtrée : services PoS enfant autorisés, aucun service hors périmètre ;
- War Room secondaire mais accessible ;
- identité `DSMx_DAE` visible si reconstruisible localement.

### DAE
- approvisionner un DSM ;
- stock et besoin de renforcement visibles sans fausse commande d'achat ;
- vue réseau et outils complets disponibles via la couche secondaire.

### Android
- upgrade en place depuis la permanente 2.9.7, sans désinstallation ;
- API23/Android 6 et API26/Android 8 obligatoires en CI ;
- appareils terrain Android 6/8 : Remote↔Robot, dual-SIM, Accessibilité, veille et redémarrage à confirmer.

## 6. Production

Cette release est une **release APK seulement**. Aucun Worker Cloudflare, aucune migration D1, aucun changement de production serveur, aucune fusion n'est nécessaire pour corriger ces défauts UI/UX. La canonicalisation D1 `0010/0011` reste une décision séparée après audit et autorisation explicite.

## 7. Règle pour le futur cahier des charges

Si la 2.9.8 passe CI, upgrade permanent et recette terrain, elle devient la **référence fonctionnelle et ergonomique** à partir de laquelle le nouveau cahier des charges sera réécrit. Les anciennes versions restent une mémoire de contraintes et d'acquis, pas une invitation à réintroduire des choix abandonnés.

## 8. Procédure de reprise

Avant toute modification future : lire ce fichier, vérifier le dernier SHA applicatif 2.9.8 et sa preuve de livraison permanente, relire les acquis finance/Robot/Remote/SIM/PIN, comparer le delta GitHub, vérifier que Cloudflare/D1 n'a pas été modifié sans autorisation, puis créer une version incrémentale. Ne jamais réécrire l'historique pour « simplifier ».
