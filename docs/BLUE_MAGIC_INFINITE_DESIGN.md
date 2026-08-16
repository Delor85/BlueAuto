# B.I.R. — Blue Infinity Retail — principes de design

Statut : **prototype expérimental uniquement**. Ce document ne modifie pas la v2.6.8 candidate et ne constitue pas une autorisation de production.

## Architecture de marque

- **Nom commercial cible** : `B.I.R.`
- **Nom développé** : `Blue Infinity Retail`
- **Signature de travail** : `Rapide. Puissant. Infini.`
- **Positionnement public** : l'excellence du retail Blue, un réseau commercial vivant, rapide, fiable et extensible.
- **Nom technique transitoire** : `Blue Magic Engine` pour le moteur existant Remote → Worker/D1 → Robot → USSD, tant que les identifiants techniques et l'historique n'ont pas fait l'objet d'une migration séparée.

Le choix de l'acronyme B.I.R. évoque pour le propriétaire une idée d'élite, de discipline, de rapidité et d'efficacité. Cette inspiration doit rester **conceptuelle**. L'identité commerciale ne doit reprendre aucun emblème, uniforme, devise, insigne ou autre élément susceptible de créer une confusion avec une institution militaire ou publique.

## Intention

B.I.R. ne doit pas copier le catalogue, les produits, les textes, les logos ni l'identité d'un concurrent. L'inspiration retenue concerne seulement des qualités d'expérience observables : lumière, lisibilité, hiérarchie, rapidité d'accès, sensation commerciale et finition.

L'identité B.I.R. est propre : **bleu profond + cyan électrique + lumière or + symbole infini**, avec un rendu lumineux plutôt que sombre.

Le symbole `∞` incarne l'extension du réseau et la continuité. Le monogramme `BIR` porte l'identité commerciale. Les deux peuvent coexister sans transformer l'interface en emblème militaire.

## Principes

1. **Une intention principale par écran** : vendre, approvisionner, piloter, vérifier, gérer.
2. **Le rôle transforme l'interface** : DAE, DSM et PoS ne voient pas la même priorité d'action.
3. **Le disponible et l'état du Robot sont visibles immédiatement**, sans transformer l'accueil en rapport comptable.
4. **Le commercial reste positif mais exact** : opérations réussies, commissions, dynamique et alertes utiles ; aucun chiffre marketing inventé en production.
5. **La puissance ne doit jamais coûter de fluidité** : anciens Android = effets réduits automatiquement.
6. **Le symbole ∞ représente le réseau vivant**, la circulation du stock et la continuité du service ; il ne doit pas devenir une animation permanente lourde.
7. **Les actions sensibles sont séparées des actions quotidiennes**.
8. **Aucun catalogue tiers n'est introduit par le design**. Les capacités visibles restent celles réellement supportées par B.I.R./Blue Magic Engine.
9. **Responsive d'abord** : référence minimale Android 6 / petits écrans ; aucune fonction essentielle ne doit dépendre d'une largeur moderne.
10. **Accessibilité visuelle** : contraste fort, zones tactiles généreuses, texte compréhensible, états non communiqués uniquement par couleur.

## Accueil cible

- identité `B.I.R. / Blue Infinity Retail` compacte ;
- nœud actif + état Robot ;
- disponible, solde Camtel et commissions ;
- action principale adaptée au rôle ;
- indicateurs du jour ;
- raccourcis vers Réseau / Soldes / Robot ;
- capacités propres de B.I.R. ;
- événements réseau récents ;
- fondations paiement affichées seulement comme infrastructure inactive tant qu'aucun rail n'est officiellement activé.

## Navigation cible

La barre principale reste courte. Le bouton central est contextuel :

- DAE : piloter / approvisionner ;
- DSM : approvisionner ses PoS ;
- PoS : vendre.

Les fonctions secondaires restent dans Réseau, Activité et Gérer. Le nombre de modules peut évoluer selon le rôle et la taille du terminal ; la contrainte historique des cinq onglets n'est pas une règle métier.

## Ton de marque

B.I.R. doit donner quatre sensations simultanées :

- **maîtrise** : les chiffres sont nets, les états sont explicites ;
- **vitesse** : action fréquente en un minimum d'étapes ;
- **puissance** : le réseau, le Robot et les preuves semblent former un système cohérent ;
- **croissance** : l'utilisateur voit que son réseau peut s'étendre sans perdre le contrôle.

Le vocabulaire public recommandé est commercial et technologique : `réseau`, `performance`, `puissance`, `rapidité`, `excellence`, `infini`, `maîtrise`, `distribution`, `croissance`. Éviter le vocabulaire de combat ou les références officielles aux forces armées dans l'interface commerciale.

## Performance

- pas de vidéo de fond ;
- pas de particules permanentes sur petits terminaux ;
- pas de blur lourd sur Android ancien ;
- animations courtes, non bloquantes et désactivables ;
- aucun polling ajouté pour un effet visuel ;
- pas de dépendance réseau pour dessiner l'interface principale.

## Prototype

Le prototype isolé est `prototypes/blue-magic-infinite/index.html` sur la branche `experiment/blue-magic-infinite-pay`. Le chemin conserve provisoirement le nom historique afin d'éviter une migration de fichiers inutile pendant l'expérimentation ; son identité visible est désormais B.I.R.
