# Backend Cloudflare — option recommandée

Ce dossier déploie **la même API Blue Magic v2** sur Cloudflare Workers + D1 et sert aussi l’interface web. L’application Android utilise simplement une URL différente :

`https://blue-magic-api.<votre-sous-domaine>.workers.dev/api`

Le PIN Camtel n’est jamais envoyé à Cloudflare. Il reste chiffré dans le Keystore du téléphone Robot.

La procédure complète, pensée pour un premier déploiement, se trouve dans [`docs/INSTALLATION_CLOUDFLARE.md`](../docs/INSTALLATION_CLOUDFLARE.md).
