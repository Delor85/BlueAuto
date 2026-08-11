# Blue Magic v2.5.3 — appairage visible et opérations financières libérées

Blue Magic automatise, sur un téléphone Android dédié, les transferts de crédit de distribution Blue/Camtel qui nécessitent désormais deux étapes :

1. composition de `*550*2*numéro*montant#` ou `*550*1*numéro*montant#` ;
2. vérification de la confirmation Camtel, saisie locale du PIN puis clic sur **ENVOYER**.

Cette version maintient le trajet critique **Télécommande → serveur → Robot → fenêtre USSD → PIN → preuve opérateur** et rétablit l’affichage des actions financières sur les profils migrés d’anciennes versions, notamment sous Android 6.

L’appairage initial ne peut plus échouer silencieusement : chaque champ invalide affiche maintenant une erreur ciblée et un message visible, le numéro accepte aussi le format `+237`, et l’appel réseau signale immédiatement son démarrage puis son résultat.

## Ce qui change par rapport à l’ancien code

- le PIN n’est jamais envoyé au serveur ni au JavaScript ; il est chiffré par Android Keystore ;
- l’interface web ne peut plus demander l’exécution d’un code USSD arbitraire ;
- numéro et montant sont recalculés par le Robot et comparés au pop-up Camtel avant le PIN ;
- chaque opération financière reçoit une confirmation lisible sur la Télécommande, puis une seconde confirmation automatique sur le pop-up Camtel ;
- chaque profil Robot est lié à l’empreinte de sa SIM physique : SIM absente, déplacée ou différente signifie arrêt avant la location d’une commande ;
- le Worker n’accorde un lease qu’à un appareil Robot ayant envoyé une attestation SIM valide ;
- chaque commande louée indique explicitement son nœud exécuteur et possède une empreinte d’intégrité contrôlée dans Android ;
- chaque demande possède une clé d’idempotence et un lease anti-double exécution ;
- les états réels sont `PENDING → LEASED → DIALING → AWAITING_PIN → PIN_SUBMITTED → AWAITING_RESULT → SUCCEEDED/FAILED/UNKNOWN/BLOCKED` ;
- une absence de confirmation devient `UNKNOWN` et n’est jamais retentée automatiquement, afin d’éviter une double recharge ;
- un seul message « Wrong PIN » bloque immédiatement le Robot.
- au repos, un Robot interroge la file toutes les 30 secondes et envoie un heartbeat toutes les 5 minutes, soit environ 3 168 requêtes par jour; les boucles rapides ne sont utilisées que pendant une commande.
- le détecteur PIN inspecte toutes les fenêtres Android accessibles, réacquiert le champ à chaque tentative, vérifie la saisie et possède une méthode de secours locale temporaire ;
- chaque compte choisit explicitement SIM 1, SIM 2, SIM 3 ou SIM 4 selon le téléphone ;
- plusieurs comptes DAE, DSM et PoS peuvent être conservés sur le même téléphone ; tous les profils Robots démarrés restent actifs même lorsqu’un compte Remote est affiché ;
- deux Robots associés à deux SIM d’un même téléphone partagent un ordonnanceur équitable et n’ouvrent jamais deux sessions USSD en même temps ;
- l’interface de commande ES5 est intégrée dans l’APK : elle reste compatible avec l’ancien WebView d’Android 6 et ne dépend plus d’un `index.html` distant ;
- les codes courts sont résolus uniquement dans leur branche (`DSM7` → `DSM7_SU2`, `POS5` → `POS5_DSM7_SU2`) ; plusieurs DSM peuvent appartenir au même DAE, chacun avec son numéro Camtel unique ;
- les commandes récentes affichent leur horodatage local ;
- `ROBOT` est polyvalent (exécution + création de commandes) ; `REMOTE` reste uniquement télécommande.
- un ancien profil dont le rôle local est vide ou obsolète récupère prudemment `DSM`/`POS` depuis son identifiant canonique, ou `DAE` depuis l’absence de supérieur ; le Worker conserve l’autorité finale sur chaque permission financière ;
- l’écran explique les opérations permises par le rôle actif, afin de distinguer une règle hiérarchique d’un blocage technique ;
- au repos, seul le service Robot fonctionne : l’écran peut s’éteindre normalement et n’est plus maintenu allumé ;
- lors d’une commande, seule la surface Téléphone/USSD est réveillée brièvement ; l’activité Blue Magic ne s’affiche pas au-dessus du verrou ;
- une synchronisation finale en panne ne bloque plus les files des autres SIM et se réconcilie automatiquement avec le statut serveur ;
- une garde globale détecte et neutralise les anciens états locaux qui prétendraient avoir deux sessions USSD simultanées ;
- le même compte passe de `ROBOT` à `REMOTE`, ou inversement, sans suppression ni nouvel appairage ;
- l’appairage utilise uniquement l’adresse Cloudflare choisie dans le formulaire : aucune bascule silencieuse vers l’ancien hébergement `gt.tc` ;
- l’adresse du serveur, le secret d’appairage et le PIN redeviennent vérifiables dans le formulaire, avec affichage volontaire via la case prévue.

## Structure

- `app/` : application Android native Java, compatible Android 6.0+ ;
- `cloudflare/` : API Workers + base D1 + interface web, option gratuite recommandée ;
- `htdocs/` : interface PWA et API PHP/MySQL pour InfinityFree ;
- `docs/INSTALLATION_CLOUDFLARE.md` : déploiement Cloudflare pas à pas ;
- `docs/INSTALLATION_PAS_A_PAS.md` : procédure destinée à un débutant ;
- `docs/TEST_TERRAIN.md` : validation obligatoire avant argent réel ;
- `.github/workflows/build.yml` : compilation automatique de l’APK de test.

La signature de l’APK pilote est conservée dans le cache privé de GitHub Actions afin que les correctifs suivants puissent être installés comme des mises à jour. Cette signature de test ne doit jamais être utilisée pour une publication commerciale.

## Limite technique honnête

Android ne fournit pas d’API publique universelle pour répondre à la deuxième étape d’une session USSD interactive. `TelephonyManager.sendUssdRequest()` sait obtenir une réponse à une requête, mais ne fournit pas de méthode publique pour continuer la session avec le PIN. Blue Magic utilise donc `ACTION_CALL` puis un `AccessibilityService` contrôlé et limité à la transaction attendue. La v2.5.1 réveille brièvement la fenêtre MMI lorsqu’une commande arrive, sans maintenir l’écran allumé au repos. Un simple écran de glissement sans code est retiré uniquement pendant la transaction puis restauré. Cela ne supprime pas cryptographiquement un mot de passe ou un schéma Android : derrière un verrou sécurisé, la commande attend le déverrouillage et le Robot reste actif. Un essai sur le modèle exact du Robot reste obligatoire.

La version gratuite d’InfinityFree est adaptée à l’interface web et fournit PHP/MySQL, mais son hébergement gratuit peut filtrer les clients automatisés et n’est pas présenté comme une plateforme d’API. Le dossier `cloudflare/` fournit donc le backend recommandé, conçu pour les clients automatisés. InfinityFree reste disponible comme solution de repli.

## Démarrage

Pour l’option recommandée, suivre [docs/INSTALLATION_CLOUDFLARE.md](docs/INSTALLATION_CLOUDFLARE.md), puis [docs/INSTALLATION_PAS_A_PAS.md](docs/INSTALLATION_PAS_A_PAS.md) à partir de l’étape APK et enfin [docs/TEST_TERRAIN.md](docs/TEST_TERRAIN.md).
