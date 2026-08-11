# Installation pas à pas — Blue Magic v2 Robot Core

Cette procédure commence par le serveur, puis l’APK, puis le Robot DAE, puis une Télécommande. Ne testez pas d’argent réel avant d’avoir terminé la checklist terrain.

## 1. Sauvegarder l’ancienne version InfinityFree

1. Dans le File Manager, ouvrez `htdocs`.
2. Téléchargez tout le dossier sous forme ZIP et conservez-le hors ligne.
3. Ne supprimez pas encore l’ancien dossier. Créez si possible un sous-dossier de sauvegarde daté.
4. Les anciens fichiers `*.sqlite` contiennent des données : ne les publiez jamais sur GitHub et ne les laissez pas téléchargeables.

## 2. Créer la base MySQL dans InfinityFree

1. Ouvrez le panneau de contrôle InfinityFree.
2. Allez dans **MySQL Databases**.
3. Créez une base nommée par exemple `blue_magic`.
4. Notez exactement : **MySQL Host Name**, **Database Name**, **MySQL User Name** et votre mot de passe de compte/base.
5. La base n’est pas appelée directement par Android : seul `api.php`, hébergé sur InfinityFree, s’y connecte.

## 3. Préparer `config.php`

1. Dans le paquet, ouvrez `htdocs/config.example.php`.
2. Faites-en une copie appelée `config.php`.
3. Remplacez les cinq valeurs `CHANGE_ME`.
4. Pour `pairing_secret`, utilisez au moins 24 caractères aléatoires, différents de votre PIN Camtel et du mot de passe MySQL.
5. Conservez `allowed_origin` à `https://magicservice-blue.gt.tc`.
6. Laissez provisoirement `setup_enabled` à `true`.
7. Ne déposez jamais `config.php` sur GitHub; il est déjà exclu par `.gitignore`.

## 4. Déployer `htdocs`

1. Envoyez dans le `htdocs` InfinityFree : `api.php`, `setup.php`, `schema.sql`, `index.html`, `app.js`, `style.css`, `sw.js`, `manifest.json`, `.htaccess` et votre `config.php`.
2. N’envoyez pas les anciennes bases SQLite dans le nouveau dossier public.
3. Ouvrez `https://magicservice-blue.gt.tc/setup.php`.
4. Entrez le secret d’appairage défini dans `config.php`.
5. Attendez le message **Base initialisée**.
6. Dans `config.php`, passez immédiatement `setup_enabled` à `false`.
7. Ouvrez `https://magicservice-blue.gt.tc/api.php?action=health`. Le résultat attendu est un JSON contenant `"ok":true` et `"database":"online"`.

Si une page HTML de sécurité apparaît au lieu du JSON, arrêtez ici : le filtrage InfinityFree empêche le mode API natif. Le moteur Android est conservé, mais l’API devra être déplacée vers un hébergement conçu pour les clients automatisés.

## 5. Compiler l’APK avec GitHub Actions

Après publication autorisée du code dans votre dépôt :

1. Ouvrez le dépôt GitHub `Delor85/BlueAuto`.
2. Cliquez sur **Actions** puis **Build Blue Magic APK**.
3. Cliquez sur **Run workflow**.
4. Attendez le feu vert du job `android-debug-apk`.
5. Ouvrez le job, section **Artifacts**, puis téléchargez `Blue-Magic-v2-Robot-Core`.
6. Décompressez et récupérez `app-debug.apk`.

L’APK debug sert au pilote. Une version finale devra être signée avec votre propre keystore conservé hors de GitHub.

## 6. Installer et préparer le téléphone Robot DAE (T1)

Conditions recommandées : téléphone Android 6+, une seule SIM active, chargeur permanent, aucun code de verrouillage écran, réseau Blue stable et Internet stable.

1. Autorisez l’installation d’applications provenant du navigateur ou gestionnaire de fichiers utilisé.
2. Installez `app-debug.apk` puis ouvrez **Blue Magic**.
3. Le serveur est choisi automatiquement par Blue Magic. Saisissez seulement :
   - nœud : `DAE-01` ;
   - numéro SIM : les 9 chiffres de la Master SIM ;
   - supérieur : vide ;
   - rôle : `DAE` ;
   - mode : `ROBOT` ;
   - code d’activation initiale : celui défini sur le serveur ; il ne sera demandé qu’une fois puis conservé chiffré ;
   - PIN Camtel : les 4 chiffres exacts.
4. Appuyez sur **Appairer ce téléphone**.
5. Appuyez sur **1. AUTORISATIONS** et accordez :
   - Téléphone ;
   - réception SMS ;
   - notifications ;
   - Accessibilité > **Automatisation PIN Blue Magic** ;
   - affichage au-dessus des autres applications ;
   - Batterie > Blue Magic > **Sans restriction / Ne pas optimiser**.
6. Revenez dans Blue Magic et appuyez sur **2. DÉMARRER ROBOT**.
7. Vérifiez la notification permanente **Blue Magic — DAE-01**.

## 7. Créer un compte DSM et sa Télécommande (T2)

Le nœud parent doit exister avant l’enfant.

1. Installez l’APK sur T2.
2. Saisissez : nœud `DSM-01/DAE-01`, le numéro de la SIM DSM, parent `DAE-01`, rôle `DSM` et mode `REMOTE`. L’adresse du serveur n’apparaît pas et l’activation déjà mémorisée n’est pas redemandée.
3. Le PIN peut rester vide sur une pure Télécommande : le PIN DAE reste seulement dans T1.
4. Appairez.
5. L’interface montre **Demander à mon supérieur**.

## 8. Premier test sans argent

1. Dans T2 ou sur l’interface du compte DAE, lancez **Tester la SIM Robot**.
2. T1 doit composer `*825*3*3#`.
3. Le résultat doit apparaître sur T1 et la commande passer à **Réussie** ou, si le format n’est pas encore reconnu, **À vérifier** sans transaction financière.
4. Si rien ne se lance, consultez `docs/TEST_TERRAIN.md`.

## 9. Premier test financier contrôlé

1. Utilisez un DSM connu et un montant minimal autorisé, par exemple 5 FCFA si Camtel l’accepte.
2. Filmez l’écran de T1 avec un deuxième appareil pour garder une preuve du test.
3. Sur T2, demandez la recharge.
4. Contrôlez visuellement que T1 affiche le bon numéro et le bon montant avant que Blue Magic remplisse le PIN.
5. Vérifiez le SMS ou popup de succès et l’ID de transaction.
6. Comparez le solde réel des deux SIM.
7. Répétez dix fois avec des montants minimaux avant toute utilisation commerciale.
