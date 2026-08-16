# B.I.R. — Prototype UX complet

**Blue Infinity Retail — Rapide. Puissant. Infini.**

Statut : **prototype expérimental, non connecté au moteur de production**.

Cette maquette est la référence visuelle actuelle de B.I.R. Elle n'est pas intégrée à l'APK v2.6.8, ne compose aucun USSD, ne réserve aucun stock, ne déploie aucun Worker et ne manipule aucun paiement réel.

## Parcours couverts

La navigation comporte cinq espaces :

1. **Accueil** — disponible, solde Camtel, commissions, réservations confirmées, indicateurs du jour et raccourcis ;
2. **Réseau** — contenu différent selon DAE / DSM / PoS ;
3. **Action** — action principale du rôle ;
4. **Activité** — événements et preuves présentés de façon commerciale et lisible ;
5. **Gérer** — Compte & SIM, PIN Camtel, Robot & téléphone, Files & sécurité, puis fondation paiement verrouillée.

Le bouton central change de sens selon le rôle :

- DAE : **Piloter** ;
- DSM : **Fournir** ;
- PoS : **Vendre**.

## Règles de périmètre simulées

- DAE : sa pyramide DSM → PoS ;
- DSM : lui-même et ses PoS directs ;
- PoS : lui-même uniquement.

Les données affichées sont explicitement des **données de démonstration** et ne doivent jamais être reprises comme chiffres réels.

## Paiement

La carte `B.I.R. PAY` est volontairement **NON OPÉRATIONNELLE** :

- aucun fournisseur ;
- aucun connecteur ;
- aucune clé API ;
- aucun endpoint ;
- aucun bouton de paiement ;
- aucun débit.

Elle représente seulement la future séparation `Intention → Routeur → Adaptateurs`, indépendante du moteur Camtel/USSD.

## Responsive validé

Contrôles locaux exécutés avec Chromium/Playwright :

- 280×568 ;
- 320×568 ;
- 412×915.

Vérifications réussies :

- chargement sans erreur JavaScript ;
- changement DAE → DSM → PoS ;
- navigation entre les cinq écrans ;
- quatre raccourcis adaptés au rôle ;
- écran Action différent par rôle ;
- PoS limité à son propre nœud dans Réseau ;
- fondation paiement bien verrouillée ;
- Centre Gérer en une colonne sur largeur ≤ 330 px.

## Fichiers

- `index.html`
- `bir.css`
- `bir.js`

Branche : `experiment/bir-full-ux`.

Cette branche ne doit pas être fusionnée directement dans la v2.6.8. Toute intégration dans l'application réelle devra être découpée en lots, reliée aux données réelles existantes et repasser toute la suite de non-régression Blue Magic Engine.
