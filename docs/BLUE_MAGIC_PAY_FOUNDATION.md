# B.I.R. Pay — fondation NON OPÉRATIONNELLE

Statut : **architecture seulement**. Aucun paiement réel, aucune clé API, aucun secret opérateur, aucun endpoint de collecte et aucun débit ne doit être activé depuis cette branche.

## Architecture de nommage

- produit commercial cible : **B.I.R. — Blue Infinity Retail** ;
- future couche paiement : **B.I.R. Pay** ;
- moteur technique actuel : **Blue Magic Engine** tant qu'une migration technique séparée n'est pas décidée.

## Objectif

Préparer B.I.R. à recevoir plus tard un ou plusieurs moyens de paiement officiels sans coupler ces moyens de paiement au moteur Camtel/USSD déjà stabilisé.

Le futur paiement doit rester une brique indépendante :

`Intention de paiement → Routeur → Adaptateur fournisseur → Statut → Rapprochement`

Le cœur technique actuel reste :

`Remote → Worker/D1 → Robot → USSD → preuve Camtel`

Les deux chaînes ne doivent jamais être fusionnées dans une même transaction technique opaque.

## Contrat abstrait futur

Chaque fournisseur devra implémenter conceptuellement :

- `quote(amount, context)` : coût estimé et contraintes avant paiement ;
- `createPayment(intent)` : création idempotente d'une demande ;
- `getStatus(providerReference)` : état officiel ;
- `cancel(...)` uniquement si le fournisseur le permet réellement ;
- `refund(...)` uniquement si le contrat fournisseur et le cadre réglementaire le permettent ;
- `health()` : disponibilité technique ;
- `capabilities()` : collection, payout, remboursement, limites et devises supportées.

Aucune de ces méthodes n'est connectée aujourd'hui.

## Modèle d'intention

Une future `payment_intent` devra au minimum contenir :

- identifiant public B.I.R. ;
- nœud demandeur ;
- montant et devise ;
- finalité ;
- fournisseur/route choisi ou `AUTO` ;
- clé d'idempotence ;
- état ;
- référence fournisseur lorsqu'elle existe ;
- timestamps ;
- coût du rail ;
- frais facturés au client ;
- preuve de rapprochement.

Le PIN Mobile Money, OTP, code secret ou credential utilisateur ne doit jamais être enregistré dans D1 ni journalisé par B.I.R.

## États proposés

`DRAFT → QUOTED → AWAITING_CUSTOMER → SUBMITTED → PROVIDER_PENDING → SUCCEEDED`

États alternatifs : `FAILED`, `EXPIRED`, `CANCELLED`, `REVIEW_REQUIRED`, `UNKNOWN`.

`UNKNOWN` doit être traité comme un état de rapprochement, jamais comme un motif pour rejouer automatiquement un débit.

## Routeur futur

Le routeur pourra plus tard comparer uniquement des rails **officiellement contractualisés et activés** selon :

- disponibilité ;
- coût marchand ;
- plafond/minimum ;
- type de transaction ;
- délai ;
- liquidité ;
- fiabilité récente ;
- préférence explicite du client lorsque pertinente.

Aucun contournement d'authentification, KYC, frais, contrôle opérateur ou règle de paiement ne fait partie de cette architecture.

## Séparation comptable

Ne jamais confondre :

- solde Camtel / stock de crédit ;
- solde d'un compte de paiement ;
- montant en attente de collecte ;
- commission B.I.R. ;
- coût du rail de paiement ;
- réservation financière Camtel.

Ces grandeurs doivent avoir des écritures et des preuves distinctes.

## Activation future obligatoire

Avant tout premier test réel, il faudra une étape distincte et explicitement autorisée comprenant au minimum :

1. fournisseur officiel choisi et contrat/onboarding confirmé ;
2. documentation API officielle vérifiée ;
3. sandbox fournisseur réelle ;
4. secrets stockés uniquement dans l'environnement approprié ;
5. endpoints callback/webhook authentifiés ;
6. idempotence et anti-double-débit testées ;
7. politique de rapprochement ;
8. limites, frais et taxes documentés ;
9. tests sans fonds ou sandbox ;
10. autorisation explicite avant passage à l'argent réel.

## Interdiction actuelle

La branche `experiment/blue-magic-infinite-pay` ne doit contenir aucun credential réel et ne doit déployer aucun composant de paiement en production. Le prototype visuel affiche volontairement l'état **NON OPÉRATIONNEL**.
