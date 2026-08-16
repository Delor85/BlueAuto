# B.I.R. / Blue Magic — convergence v2.7 sur la base v2.6.11

Date : 2026-08-16

## Découverte de reprise

La bibliothèque durable contient `BIR-v2.6.11-ETAT-REPRISE-2026-08-16.md`. GitHub confirme que `fix/bir-v2-6-11-finalization` est au SHA `e3f9e9016e86c1193ba4170e2a9fce1ba466eb86`. La branche v2.7 antérieure `feat/bir-v2-7-stabilization` issue de `f1e9f3d...` diverge et ne contient pas les 15 commits v2.6.11.

Par règle de non-régression, l'autorisation de publication permanente visant le SHA `45f814f7b41ce57c845cb0a476af3c53f5d96309` est mise en attente : produire cet APK comme nouvelle livraison terrain ferait repartir avant la finalisation v2.6.11.

## Nouvelle base

Branche : `feat/bir-v2-7-finalization`
Base exacte : `e3f9e9016e86c1193ba4170e2a9fce1ba466eb86`
Version Android cible : 2.7.0 / versionCode 51 / package historique inchangé.

## MOCK propriétaire

MOCK est un espace virtuel local, pas un nœud Camtel. Il n'entre jamais dans la hiérarchie DAE/DSM/PoS et n'a ni SIM ni Robot. Dans l'APK officielle actuelle il est visible uniquement lorsque le profil actif est le DAE `SU1`. Les appels `mercenary_*` sont bloqués nativement hors MOCK. Les rubriques Mercenaires, rentabilisation, sources de revenus, B.I.R. Pay expérimental, White-label et Robot as a Service sont regroupées dans cet espace.

## Fiabilité du solde

Règle renforcée côté expérience utilisateur : une réponse financière donnant un nouveau solde n'est pas affichée comme preuve A lorsqu'elle n'apporte pas une chronologie opérateur suffisamment sûre. Une réponse tardive/ambiguë doit être rapprochée et ne doit jamais justifier la régression d'une preuve de solde plus récente.

Aucune modification Cloudflare/D1 n'est réalisée dans cette convergence. Le durcissement serveur éventuel de la promotion des `FINANCIAL_RESULT` sans horodatage explicite reste un chantier séparé soumis à autorisation serveur distincte.
