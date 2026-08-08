# Blue Magic v2.2 — PIN renforcé, Android 6 et Robots simultanés

Blue Magic automatise, sur un téléphone Android dédié, les transferts de crédit de distribution Blue/Camtel qui nécessitent désormais deux étapes :

1. composition de `*550*2*numéro*montant#` ou `*550*1*numéro*montant#` ;
2. vérification de la confirmation Camtel, saisie locale du PIN puis clic sur **ENVOYER**.

Cette version reconstruit en priorité le trajet critique **Télécommande → serveur → Robot → fenêtre USSD → PIN → preuve opérateur**. Les cinq onglets ERP complets viendront après la validation terrain de ce noyau.

## Ce qui change par rapport à l’ancien code

- le PIN n’est jamais envoyé au serveur ni au JavaScript ; il est chiffré par Android Keystore ;
- l’interface web ne peut plus demander l’exécution d’un code USSD arbitraire ;
- numéro et montant sont recalculés par le Robot et comparés au pop-up Camtel avant le PIN ;
- chaque demande possède une clé d’idempotence et un lease anti-double exécution ;
- les états réels sont `PENDING → LEASED → DIALING → AWAITING_PIN → PIN_SUBMITTED → AWAITING_RESULT → SUCCEEDED/FAILED/UNKNOWN/BLOCKED` ;
- une absence de confirmation devient `UNKNOWN` et n’est jamais retentée automatiquement, afin d’éviter une double recharge ;
- un seul message « Wrong PIN » bloque immédiatement le Robot.
- au repos, un Robot interroge la file toutes les 30 secondes et envoie un heartbeat toutes les 5 minutes, soit environ 3 168 requêtes par jour; les boucles rapides ne sont utilisées que pendant une commande.
- le détecteur PIN inspecte toutes les fenêtres Android accessibles, réacquiert le champ à chaque tentative, vérifie la saisie et possède une méthode de secours locale temporaire ;
- chaque compte choisit explicitement SIM 1, SIM 2, SIM 3 ou SIM 4 selon le téléphone ;
- plusieurs comptes DAE, DSM et PoS peuvent être conservés sur le même téléphone ; tous les profils Robots démarrés restent actifs même lorsqu’un compte Remote est affiché ;
- deux Robots associés à deux SIM d’un même téléphone partagent un ordonnanceur FIFO et n’ouvrent jamais deux sessions USSD en même temps ;
- l’interface de commande utilise du JavaScript ES5 compatible avec l’ancien WebView d’Android 6 ;
- les codes courts sont résolus dans leur branche (`DSM7` → `DSM7_SU2`, `POS5` → `POS5_DSM7_SU2`) ;
- les commandes récentes affichent leur horodatage local ;
- `ROBOT` est polyvalent (exécution + création de commandes) ; `REMOTE` reste uniquement télécommande.

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

Android ne fournit pas d’API publique universelle pour répondre à la deuxième étape d’une session USSD interactive. `TelephonyManager.sendUssdRequest()` sait obtenir une réponse à une requête, mais ne fournit pas de méthode publique pour continuer la session avec le PIN. Blue Magic utilise donc `ACTION_CALL` puis un `AccessibilityService` contrôlé et limité à la transaction attendue. Le comportement de la fenêtre MMI dépend du fabricant et de l’application Téléphone : un essai sur le modèle exact du Robot est obligatoire.

La version gratuite d’InfinityFree est adaptée à l’interface web et fournit PHP/MySQL, mais son hébergement gratuit peut filtrer les clients automatisés et n’est pas présenté comme une plateforme d’API. Le dossier `cloudflare/` fournit donc le backend recommandé, conçu pour les clients automatisés. InfinityFree reste disponible comme solution de repli.

## Démarrage

Pour l’option recommandée, suivre [docs/INSTALLATION_CLOUDFLARE.md](docs/INSTALLATION_CLOUDFLARE.md), puis [docs/INSTALLATION_PAS_A_PAS.md](docs/INSTALLATION_PAS_A_PAS.md) à partir de l’étape APK et enfin [docs/TEST_TERRAIN.md](docs/TEST_TERRAIN.md).
