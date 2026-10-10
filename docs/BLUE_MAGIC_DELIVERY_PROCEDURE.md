# Procédure obligatoire — clôture, sauvegarde et reprise de Blue Magic

Cette procédure est obligatoire avant, pendant et après toute modification de Blue Magic. GitHub est la mémoire permanente et la source de vérité du projet.

## 1. Avant toute modification

1. Lire `docs/PROJECT_STATE.md` sur la branche de reprise.
2. Vérifier la branche, le dernier commit validé, la PR et les derniers workflows.
3. Inventorier les acquis protégés, les fichiers concernés et toutes les dépendances Android, APK, signature, GitHub Actions, Cloudflare, Worker, D1 et migrations.
4. Signaler avant modification tout acquis susceptible d’être touché.
5. Ne jamais supprimer ni réécrire une solution fonctionnelle sans cause technique démontrée et solution de retour arrière.

## 2. Traçabilité de chaque résolution

Documenter systématiquement :

`Problème → Cause → Solution → Fichiers concernés → Tests → Résultat → Commit`

Une correction n’est jamais déclarée validée sur la seule base d’une modification de code. Toute solution précédemment validée est un acquis protégé et doit recevoir un test de non-régression lorsqu’elle peut être touchée.

## 3. GitHub

À chaque livraison :

- travailler sur la branche appropriée ;
- enregistrer un commit identifiable et communiquer son hash exact ;
- indiquer la PR ;
- vérifier et documenter chaque GitHub Action réussie, ignorée ou échouée ;
- actualiser `docs/PROJECT_STATE.md` ;
- ne fusionner que lorsque les tests requis, y compris le test terrain lorsqu’il est nécessaire, sont validés.

## 4. Cloudflare et secrets

Après toute modification Cloudflare, vérifier le Worker, D1, les migrations, le déploiement et les workflows concernés.

Ne jamais afficher ni demander dans une conversation : jeton API, mot de passe, `PAIRING_SECRET`, clé privée, mot de passe de keystore, secret GitHub ou autre identifiant confidentiel. Les secrets restent uniquement dans leurs systèmes sécurisés.

## 5. APK

Chaque livraison APK doit indiquer : nom, version, versionCode, signature, SHA-256, compatibilité avec l’APK précédente, mode d’installation, emplacement et résultat de vérification de signature. Une mise à jour ne peut être livrée sans comparaison de signature avec la version précédente.

## 6. Tests et non-régression

Avant clôture :

1. exécuter les tests de la correction ;
2. vérifier les fonctions critiques acquises susceptibles d’être touchées ;
3. vérifier GitHub Actions ;
4. vérifier Cloudflare/D1 si concernés ;
5. documenter tous les résultats.

Tout échec doit indiquer le test, l’erreur, la cause probable, l’impact et son caractère bloquant ou non.

## 7. État de reprise obligatoire

À chaque livraison, mettre à jour `docs/PROJECT_STATE.md` avec :

- version, branche, commits, état GitHub, PR et Actions ;
- état Cloudflare, Worker, D1 et migrations ;
- APK, versionCode, signature, SHA-256 et compatibilité ;
- problème, cause, correction et fichiers créés/modifiés/supprimés ;
- tests et résultats ;
- acquis et solutions à préserver ;
- reste à faire, interdictions de modification, régressions et risques ;
- point de reprise, prochaine action et autorisation requise.

## 8. Protection des acquis

Avant toute approche nouvelle : identifier l’acquis menacé, expliquer la nécessité, sauvegarder l’état actuel, isoler la modification, tester et conserver un retour possible vers le dernier état validé.

## 9. Reprise d’une nouvelle session

Une nouvelle session commence obligatoirement par la lecture de `docs/PROJECT_STATE.md`, puis par la vérification du commit, de la branche, des fichiers, workflows, acquis et problèmes ouverts. La reprise se fait exactement au point indiqué dans ce document, jamais à partir de zéro.

## 10. Critère de fin

Une livraison est terminée uniquement si les quatre conditions sont remplies :

- **Code** : enregistré dans Git ;
- **Vérification** : tests exécutés et résultats connus ;
- **Sauvegarde** : état complet enregistré dans GitHub ;
- **Reprise** : un autre agent peut poursuivre depuis le commit indiqué sans dépendre de la conversation.

Si une condition manque, la livraison reste **NON TERMINÉE**.
