# Blue Magic Infinite — principes de design

Statut : **prototype expérimental uniquement**. Ce document ne modifie pas la v2.6.8 candidate et ne constitue pas une autorisation de production.

## Intention

Blue Magic ne doit pas copier le catalogue, les produits, les textes, les logos ni l'identité d'un concurrent. L'inspiration retenue concerne seulement des qualités d'expérience observables : lumière, lisibilité, hiérarchie, rapidité d'accès, sensation commerciale et finition.

L'identité Blue Magic reste propre : **bleu profond + cyan électrique + lumière or + symbole infini**, avec un rendu lumineux plutôt que sombre.

## Principes

1. **Une intention principale par écran** : vendre, approvisionner, piloter, vérifier, gérer.
2. **Le rôle transforme l'interface** : DAE, DSM et PoS ne voient pas la même priorité d'action.
3. **Le disponible et l'état du Robot sont visibles immédiatement**, sans transformer l'accueil en rapport comptable.
4. **Le commercial reste positif mais exact** : opérations réussies, commissions, dynamique et alertes utiles ; aucun chiffre marketing inventé en production.
5. **La magie ne doit jamais coûter de fluidité** : anciens Android = effets réduits automatiquement.
6. **Le symbole ∞ représente le réseau vivant**, la circulation du stock et la continuité du service ; il ne doit pas devenir une animation permanente lourde.
7. **Les actions sensibles sont séparées des actions quotidiennes**.
8. **Aucun catalogue tiers n'est introduit par le design**. Les capacités visibles restent celles réellement supportées par Blue Magic.
9. **Responsive d'abord** : référence minimale Android 6 / petits écrans ; aucune fonction essentielle ne doit dépendre d'une largeur moderne.
10. **Accessibilité visuelle** : contraste fort, zones tactiles généreuses, texte compréhensible, états non communiqués uniquement par couleur.

## Accueil cible

- identité Blue Magic compacte ;
- nœud actif + état Robot ;
- disponible, solde Camtel et commissions ;
- action principale adaptée au rôle ;
- indicateurs du jour ;
- raccourcis vers Réseau / Soldes / Robot ;
- capacités propres Blue Magic ;
- événements réseau récents ;
- fondations paiement affichées seulement comme infrastructure inactive tant qu'aucun rail n'est officiellement activé.

## Navigation cible

La barre principale reste courte. Le bouton central est contextuel :

- DAE : piloter / approvisionner ;
- DSM : approvisionner ses PoS ;
- PoS : vendre.

Les fonctions secondaires restent dans Réseau, Activité et Gérer. Le nombre de modules peut évoluer selon le rôle et la taille du terminal ; la contrainte historique des cinq onglets n'est pas une règle métier.

## Performance

- pas de vidéo de fond ;
- pas de particules permanentes sur petits terminaux ;
- pas de blur lourd sur Android ancien ;
- animations courtes, non bloquantes et désactivables ;
- aucun polling ajouté pour un effet visuel ;
- pas de dépendance réseau pour dessiner l'interface principale.

## Prototype

Le prototype isolé est `prototypes/blue-magic-infinite/index.html` sur la branche `experiment/blue-magic-infinite-pay`.
