# Installer gratuitement Blue Magic sur Cloudflare

Cette option est recommandée pour le pilote. Cloudflare Workers est conçu pour recevoir les requêtes automatiques du Robot Android; D1 stocke les nœuds, appareils et commandes. Le même déploiement sert l’API et l’interface Blue Magic en HTTPS.

## Ce qu’il faut

- un compte GitHub contenant ce dépôt;
- un compte Cloudflare gratuit;
- un ordinateur avec Node.js 20 ou plus récent pour la première installation;
- aucun numéro de carte bancaire n’est nécessaire pour le plan gratuit.

Ne publiez jamais le PIN Camtel, le secret d’appairage, un jeton appareil ou une clé Cloudflare sur GitHub.

## 1. Télécharger le projet

1. Sur GitHub, ouvrez la branche indiquée dans la Pull Request Blue Magic v2.
2. Cliquez **Code**, puis **Download ZIP**.
3. Décompressez le ZIP sur l’ordinateur.
4. Ouvrez un terminal dans le sous-dossier `cloudflare`.

## 2. Installer l’outil Cloudflare

Exécutez :

```bash
npm install
npx wrangler login
```

Une page Cloudflare s’ouvre. Connectez-vous et autorisez Wrangler.

## 3. Créer la base gratuite D1

Exécutez :

```bash
npx wrangler d1 create blue-magic
```

La commande affiche un `database_id`. Ouvrez `wrangler.jsonc` et remplacez uniquement :

```text
REPLACE_WITH_D1_DATABASE_ID
```

par cet identifiant, sans supprimer les guillemets.

Initialisez ensuite les tables :

```bash
npx wrangler d1 migrations apply blue-magic --remote
```

Répondez `Y` si Wrangler demande confirmation.

## 4. Créer le secret d’appairage

Créez une phrase aléatoire d’au moins 24 caractères. Elle doit être différente du PIN Camtel et de votre mot de passe Cloudflare.

Exécutez :

```bash
npx wrangler secret put PAIRING_SECRET
```

Collez le secret quand Wrangler le demande. Rien ne s’affiche pendant la saisie : c’est normal. Conservez ce secret hors de GitHub dans un gestionnaire de mots de passe.

## 5. Déployer

Exécutez :

```bash
npm run deploy
```

Wrangler affiche une adresse semblable à :

```text
https://blue-magic-api.votre-nom.workers.dev
```

Vérifiez l’API dans un navigateur :

```text
https://blue-magic-api.votre-nom.workers.dev/api?action=health
```

Le résultat attendu contient `"ok":true`, `"database":"online"` et `"version":"2.3.0-cloudflare"`.

Au repos, un Robot vérifie la file toutes les 30 secondes : une commande peut donc attendre jusqu’à environ 30 secondes avant sa composition. Ce réglage réduit fortement la batterie et reste adapté au quota gratuit. Il pourra être ajusté après mesure sur le terrain.

## 6. Configurer le téléphone Robot

L’adresse Cloudflare est intégrée à l’application et n’est plus demandée. À l’écran d’appairage, utilisez :

- **Code nœud** : par exemple `DAE-01`;
- **Rôle** : `DAE`;
- **Mode** : `ROBOT`;
- **Code d’activation initiale** : celui saisi avec `wrangler secret put`; après le premier succès il est conservé chiffré dans le téléphone et disparaît des appairages suivants;
- **PIN Camtel** : quatre chiffres, enregistré uniquement dans le téléphone.

Les Télécommandes utilisent la même URL et le même secret pendant l’appairage, mais le mode `REMOTE`. Elles ne doivent pas recevoir le PIN du Robot.

## 7. Mettre à jour plus tard

Après une nouvelle version du dépôt :

```bash
npm install
npm run deploy
```

N’exécutez une nouvelle migration D1 que si un nouveau fichier apparaît dans `cloudflare/migrations`.

## 8. Limites et récupération

- Faites d’abord `TEST_NUMBER`; ne testez pas d’argent réel avant la checklist `TEST_TERRAIN.md`.
- Exportez périodiquement D1 depuis Cloudflare. Le plan gratuit fournit aussi une restauration dans le temps limitée.
- Si les limites gratuites sont atteintes, les requêtes échouent au lieu de créer silencieusement des transactions supplémentaires.
- Gardez InfinityFree en secours jusqu’à ce que dix tests terrain consécutifs soient validés.
