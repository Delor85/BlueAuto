# B.I.R. v2.7.0 — compte MOCK propriétaire national

Date : 2026-08-16

## Décision

Le compte MOCK n'utilise plus `SU1` ni aucun autre DAE comme identité propriétaire. Les dix régions officielles restent AD, CE, ES, EN, LT, NO, NW, OU, SU et SW. MOCK est un espace virtuel propriétaire au-dessus de ces régions, hors grammaire Camtel DAE/DSM/PoS.

## Activation propriétaire

MOCK est verrouillé par un code propriétaire haute entropie. Seul son SHA-256 est embarqué dans l'APK. Le code n'est jamais envoyé au Worker ni stocké en clair par cette modification. L'activation est locale au téléphone.

## Portée réelle sans modification Cloudflare/D1

Le Worker 2.6.11 authentifie chaque requête par un jeton d'appareil rattaché à un nœud réel. Par conséquent, sans modifier le Worker ni D1, MOCK ne peut pas inventer un super-token national. Il agrège à la place tous les profils DAE réellement appairés sur le téléphone et utilise explicitement le jeton du DAE sélectionné pour les actions Mercenaires. Les régions sans profil DAE appairé sont affichées comme non connectées.

## Choix du PoS

Pour une route DAE donnée, le tableau national charge les descendants réellement visibles de ce DAE et propose les PoS de cette flotte. Le champ `dedicated_pos_node_code` du Hub Mercenaires peut être alimenté par ce sélecteur. Le Worker conserve son contrôle `resolveDescendant`: un PoS extérieur à la flotte du DAE choisi reste refusé.

## Transactions interdites dans MOCK

MOCK ne peut pas créer directement un approvisionnement DAE/DSM, une vente détail PoS, un précontrôle d'approvisionnement, un USSD brut ou une opération qui ferait de MOCK un Robot/SIM. Pour ces opérations, il faut revenir au compte réseau réel. La vente Mercenaire reste possible via le DAE sélectionné et son PoS dédié, car elle est explicitement contrôlée côté Worker.

## Production

Aucune source `cloudflare/` ni migration D1 n'est modifiée par cette étape. Aucun déploiement Worker n'est effectué. La publication permanente précédemment autorisée pour le SHA `fbbb17d05e16f03dd82224df4b9aa67277272197` ne doit pas être lancée après cette correction, car ce SHA contient encore l'ancien verrou SU1. Un nouveau SHA exact devra être autorisé après validation.
