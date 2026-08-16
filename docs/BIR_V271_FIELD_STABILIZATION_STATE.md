# B.I.R. v2.7.1 — stabilisation terrain

Date : 2026-08-16

## Base

Cette étape part du HEAD documentaire v2.7.0 `b3db1e3b2baac3424f4d7192ecb62d8b61020e8c` et conserve comme APK terrain précédente le SHA applicatif `c92e62e5f3a22369f99c3c2bfe04592abe18cb16`.

## Corrections v2.7.1

- Reprise Robot après reboot : le souhait Robot est persisté synchroniquement. Les états transitoires de la radio/SIM au démarrage ne désactivent plus le Robot. Seuls `NUMBER_MISMATCH` et `SIM_CHANGED` révoquent automatiquement le Robot.
- MOCK privé : il n'est plus listé dans les comptes normaux. Il se découvre uniquement dans Ajouter/Ouvrir en saisissant `MOCK` puis le code propriétaire. L'autorisation MOCK est une session mémoire, perdue à la fermeture du processus.
- MOCK non invasif : quitter MOCK ou choisir un vrai compte reconstruit immédiatement l'interface réelle, même si ce compte était déjà le profil de routage sous-jacent.
- Appairage simplifié : serveur et secret sont masqués du parcours normal; un téléphone vierge affiche seulement une activation administrateur ponctuelle.
- Commissions : politique locale compacte par acteur (défaut DAE 10 %, DSM 8 %, exceptions enfant). Avec le Worker production 2.6.7, un taux non nul est converti en total base+commission puis ce total est recertifié une seule fois par le serveur, supprimant la boucle 0 %.
- Limite commissions : un `REQUEST_SUPPLY` initié sur un autre téléphone ne peut pas partager automatiquement la politique locale du supérieur tant que Worker/D1 0005 ne sont pas déployés. Aucun déploiement serveur n'est inclus ici.
- Solde : cache local chronologique. Une preuve plus vieille ou sans horodatage sûr ne peut pas écraser une preuve locale plus récente. La dernière preuve fiable s'affiche immédiatement au lieu de laisser le solde vide pendant plusieurs minutes.
- Journal : achats/ventes sauvegardés localement, plus récents en premier, jusqu'à 5 000 entrées et environ 1,9 Mo avant élagage. Une mise à jour APK conserve ce journal; une désinstallation/effacement des données le supprime.
- Marque : les textes visibles utilisent Blue. Les parseurs/protocoles ne sont pas renommés aveuglément.
- Bilingue : bouton FR/EN dans la barre supérieure pour le cœur de l'interface, avec préférence locale; les diagnostics profonds gardent le français comme langue de repli.
- Ergonomie : textes secondaires légèrement agrandis; le dock reste visible/compact lors de la saisie.

## Interdictions conservées

- ne pas fusionner PR #4;
- ne pas déployer Worker;
- ne pas appliquer D1 0005;
- ne pas utiliser la clé permanente pendant la CI normale;
- ne pas modifier le package `com.profitloop.blueauto`;
- ne pas contourner un verrou sécurisé Android.
