# Procédure obligatoire de reprise externe — Blue Magic

Ce document permet à un autre développeur ou agent de reprendre Blue Magic sans dépendre de la conversation ChatGPT. Il commence à la demande initiale, conserve les acquis des versions historiques, consigne les régressions et les blocages rencontrés, puis décrit le trajet critique, la compilation, le déploiement, les tests et la livraison.

Il est volontairement plus complet qu'une simple note de version. En cas de contradiction avec une réponse de conversation, le code publié, les preuves GitHub Actions, l'état Cloudflare et les limites écrites ici priment.

## 0AA. Chantier v2.6.7 — 14 août 2026 — publication et production autorisées

Le 14 août 2026, le propriétaire a explicitement autorisé, et uniquement pour v2.6.7 : l'indexation, le commit et le push sur `fix/blue-magic-v2-6-recovery`/PR #4, la CI complète, l'application de la seule migration D1 `0003`, un déploiement du Worker `2.6.7-cloudflare`, puis un lancement manuel produisant l'APK Release permanente, sa vérification Android 6–16 et sa livraison. Aucun autre changement de production n'est autorisé.

Il précise en même temps une règle d'architecture du cahier : les modules doivent partager les preuves fiables déjà obtenues et éviter les commandes USSD en double. Une consultation de solde, un historique des cinq dernières transactions, un détail ou un résultat financier peut donc alimenter le même registre de solde si — et seulement si — la fenêtre Camtel fiable contient un solde actuel explicite.

### Demande et acquis à préserver

Le propriétaire confirme que les onglets v2.6.6 ne suffisent pas encore et demande simultanément :

1. une installation/mise à jour vérifiée sur Android 6, 7, 8, 9, 10, 11, 12, 13, 14 et versions suivantes ;
2. la suppression définitive de la surface/du « voile » qui empêche la saisie du PIN sous verrou simple ;
3. avant la confirmation 1/2 d'un achat DSM/PoS auprès de son supérieur, une lecture du solde du fournisseur, puis un refus indiquant le montant exact disponible si le stock est insuffisant ;
4. des onglets réellement alimentés par le serveur et l'activation progressive des commandes du cahier révisé ;
5. aucune régression de Test/Achat/Vente, Remote/Robot, FIFO, confirmation, contrôle SIM/slot, remplacement du Robot fantôme et messages de prérequis.

Le cahier source maître de cette reprise est `Blue Magic Cahier des Charges Fonctionnel juillet 2026(3).docx`. Son texte a été extrait intégralement, sa structure a été analysée et un rendu de contrôle de 81 pages a été produit. En cas de contradiction interne, sa partie révisée précédant l'ancien « Cahier définitif v2 » est prioritaire. Les codes Camtel retenus sont ceux du répertoire révisé : transfert `*550*2*...`, vente `*550*1*...`, solde propre `*550*3*1*PIN#`, historique/détail et maintenance `*550*3/*4/*5`.

### Audit Codex demandé par le propriétaire

Un audit indépendant, sans modification de fichiers, a constaté :

- aucun `TYPE_ACCESSIBILITY_OVERLAY` ni texte « PIN protégé » ne subsiste dans la source ou l'APK v2.6.6 ;
- la cause du voile observable est le lancement de la **MainActivity complète** pour retirer le keyguard, puis la poursuite de la composition après quatre secondes sans preuve que le verrou simple a disparu ;
- v2.6.6 prenait le simple retour `true` de la première action `ACTION_SET_TEXT` comme preuve d'écriture, même si un dialer Android 11 acceptait l'action sans modifier le champ ;
- l'APK v2.6.6 livrée est encore un build `debuggable=true` re-signé ; le certificat permanent est correct et identique à v2.6.2/v2.6.4/v2.6.5, mais certains installateurs OEM peuvent refuser un APK débogable ;
- le contrôle binaire a apporté une preuve supplémentaire : `resources.arsc` de la finale v2.6.6 commence à l'offset `103141`, non divisible par 4, donc l'APK a perdu son alignement ZIP après la re-signature manuelle. La v2.6.4 présente le même défaut (`94857`) alors que v2.6.0/2.6.1/2.6.2 et la v2.6.5 utilisée comme passerelle sont alignées. Cette corrélation explique les refus Android 11 de v2.6.4/v2.6.6 malgré le certificat correct ;
- la CI historique testait une APK temporaire proche, pas le vrai type Release final, et omettait Android 7/9/10/12/13/14/15.

### Correctif verrou simple et PIN

- `MainActivity` n'est plus relancée pour une transaction en veille.
- Une activité interne `InsecureKeyguardDismissActivity` est transparente, sans contenu, sans assombrissement, `noHistory` et exclue des récents. Elle ne sert qu'à fournir le jeton d'activité exigé par Android 8+ pour retirer un verrou par simple glissement, puis se ferme immédiatement.
- Le service garde l'écran réveillé pendant 45 secondes au maximum, retire temporairement le verrou simple et **vérifie `isKeyguardLocked()==false` avant de passer à `DIALING`**. Si le verrou reste visible, le lease est relâché sans composition et sans état financier incertain.
- Un mot de passe, PIN, schéma ou verrou biométrique Android n'est jamais contourné.
- L'Accessibilité refuse toute écriture/clic tant qu'un keyguard existe. Elle essaie d'abord un collage local sur le champ initialement vide, puis des remplacements déterministes par `ACTION_SET_TEXT` ; elle ne concatène jamais deux méthodes dans le même essai. Le premier booléen positif n'est plus une preuve suffisante.
- Les textes solde, succès, échec et mauvais PIN ne sont plus agrégés depuis toutes les applications : ils doivent provenir d'une seule fenêtre du dialer par défaut ou d'un composant Phone/Telecom système. Le bouton OK/Fermer est lui aussi recherché uniquement dans cette fenêtre fiable.
- Un champ n'est considéré comme rempli que s'il contient les quatre chiffres exacts, quatre glyphes de masque reconnus, ou si la dernière méthode a ciblé un champ réellement visible et focalisé sans keyguard.
- Le PIN peut être physiquement visible comme demandé ; il reste chiffré dans Android Keystore, masqué dans les preuves et absent du JavaScript, du Worker et de D1.

### Contrôle du solde avant achat

Le nouveau trajet `REQUEST_SUPPLY` est le suivant :

1. la Télécommande envoie `check_purchase_capacity` avec montant et clé anti-doublon ;
2. le Worker recherche d'abord une preuve opérateur explicite encore valide, âgée de 180 secondes au maximum. Elle peut provenir de `BALANCE_OWN`, `BALANCE_CHILD`, `HISTORY_LAST5`, `TRANSACTION_DETAIL` ou du résultat fiable d'une finance ;
3. un historique ou détail sans libellé explicite de solde actuel n'est jamais interprété à partir des montants de transactions. « Transfer Balance of 1 FCFA » n'est notamment pas un solde ;
4. les transferts déjà réussis, inconnus ou en attente depuis cette preuve sont déduits. Un succès connu fait évoluer la preuve par dérivation sans prolonger sa date d'expiration ;
5. si aucune preuve réutilisable n'existe, le Worker place une lecture fraîche `BALANCE_OWN` dans la file du Robot du supérieur. Une seule lecture en cours est partagée entre tous les enfants ; le Robot construit localement `*550*3*1*PIN#` et le Worker ne reçoit jamais le PIN ;
6. l'Accessibilité renvoie uniquement le texte de la fenêtre Phone/Telecom fiable ; le Worker exige un libellé de solde actuel et extrait le premier montant FCFA/XAF directement associé, jamais les frais ;
7. montant inférieur ou égal : l'app poursuit vers la prévisualisation et la confirmation 1/2 inchangée ; elle indique si aucune commande USSD supplémentaire n'a été nécessaire ;
8. montant supérieur : aucune commande financière n'est créée. L'app affiche exactement le solde disponible et demande de recommencer rapidement avec un montant inférieur ou égal, car un autre enfant peut consommer le stock ;
9. le contrôle expire après 120 secondes et ne réserve pas l'argent réel chez Camtel. À la création, un `INSERT … SELECT … WHERE` D1 revalide aussi l'expiration de la preuve et recalcule atomiquement le disponible en soustrayant achats de distribution, ventes détail et commandes déjà réservées. Deux enfants ne peuvent donc pas engager simultanément le même stock. L'index unique empêche la réutilisation d'un contrôle.

La migration additive `0003_balance_preflight_and_modules.sql` ajoute `account_balances`, `purchase_preflights`, le type logique de commande, son argument local et le lien de capacité. Elle ne modifie ni ne supprime les lignes existantes. **Elle n'est pas encore appliquée en production.**

### Onglets et commandes réellement activés dans le code v2.6.7

| Cahier | État v2.6.7 local | Preuve/limite |
|---|---|---|
| Flux Achat/Vente/Test | Conservé | mêmes résolutions hiérarchiques, preview, idempotence, FIFO et contrôle Camtel |
| Solde propre | Actif | commande locale `*550*3*1*PIN#`, preuve D1 horodatée et mutualisable 180 s entre modules |
| 5 dernières transactions | Actif | `*550*3*3*PIN#` construit uniquement sur le Robot |
| Détail transaction | Actif | `*550*3*2*ID*PIN#`, ID validé côté Worker et Android |
| Solde enfant direct | Actif DAE/DSM | `*550*5*2*numéro*PIN#`, enfant résolu par la filiation serveur |
| Init reset PIN enfant | Actif avec confirmation sensible | `*550*4*1*numéro*PIN#` |
| Suspendre/réactiver enfant | Actif avec confirmation sensible | `*550*4*2` / `*550*4*3` |
| Geler/réactiver SIM enfant | Actif avec confirmation sensible | `*550*5*3` / `*550*5*4` |
| Geler sa propre SIM | Actif avec confirmation sensible | cible forcée sur le numéro officiel du compte |
| Rapports | Actif, première tranche serveur | soldes connus, fraîcheur, volume, activité et arborescence visible |
| Flotte | Actif, première tranche serveur | nœuds, numéros, Android ou terminal non enregistré, comptes/SIM et maintenance Camtel ; ne pas inventer un Tchoronko sans donnée dédiée |
| Robot/Configuration | Actif pour le socle | hall, permissions, liaison SIM, PIN local, démarrage et multi-comptes |
| SAV | Actif pour le socle | santé Worker/D1, diagnostic et retour vers test sans fonds |
| KYC complet, créances, géographie, mercenaires et SAV conversationnel | Restant | ne pas prétendre qu'ils sont livrés ; ils nécessitent modèles de données, écrans et règles métier supplémentaires |

### Installation Android 6 à 16

- Version préparée : `2.6.7`, `versionCode 47`, `minSdk 23`, `targetSdk 34`.
- Le type livré devient un vrai `assembleRelease`, signé directement par la configuration permanente quand les secrets autorisés sont présents. Il ne doit plus contenir `android:debuggable="true"` et ne doit plus être « décapé puis re-signé » à partir d'un debug.
- Le workflow exécute `zipalign -c -v 4` et `apksigner verify` sur l'APK finale avant l'export. Aucun octet ne doit être modifié après cette vérification/signature.
- La même applicationId `com.profitloop.blueauto`, le versionCode croissant et le certificat permanent restent les trois conditions de mise à jour.
- La matrice couvre un API représentatif de chaque Android majeur : 23/6, 24/7, 26/8, 28/9, 29/10, 30/11, 31/12, 33/13, 34/14, 35/15 et 36/16.
- Cette couverture est échantillonnée par version majeure : les variantes intermédiaires API 25/Android 7.1, API 27/Android 8.1 et API 32/Android 12L ne sont pas des lignes séparées. Elles restent compatibles par plage SDK mais pourront être ajoutées si un modèle terrain signale un comportement propre à ces variantes.
- Chaque job sépare le résultat `adb install` du démarrage, installe v2.6.5 avec la même clé permanente, conserve un marqueur, applique `adb install -r` sur **l'artefact Release permanent exact du run**, vérifie la version et refuse le drapeau `DEBUGGABLE`. Il désinstalle ensuite la référence et vérifie aussi l'installation propre du même artefact sur chaque API. L'export permanent et la matrice complète ne s'exécutent qu'en lancement manuel autorisé.
- Une incompatibilité de signature avec une ancienne APK v2.4.5/v2.5.1 reste techniquement impossible à contourner : ces anciennes APK portent un autre certificat. Relever `adb install -r` et `dumpsys package` avant toute désinstallation.

### Vérifications déjà réalisées et blocages actuels

- `node app/src/test/finance-flow.mjs` : réussi après extension des scénarios UI, confirmation et solde insuffisant.
- `node --check cloudflare/src/index.js` : réussi.
- `npm run check` dans `cloudflare` : couvre Remote/Robot, FIFO, preuve fraîche, réutilisation depuis l'historique, rejet d'un faux « Transfer Balance », expiration à 180 s, deux préflights concurrents de 600 FCFA sur 1 000 FCFA (un succès et un `409 BALANCE_CHANGED`) et les états complets.
- migrations 0001→0003 appliquées dans SQLite en mémoire et `PRAGMA integrity_check` : `ok`.
- simulation SQL isolée de la garde atomique : engagement 600 FCFA accepté, engagement concurrent 500 FCFA refusé sur un solde observé de 1 000 FCFA ; total réservé final 600 FCFA.
- parseur solde isolé : « solde 1 250 FCFA, frais 0 FCFA » → 1 250 ; un message de transfert sans libellé solde/balance → refusé.
- YAML du workflow chargé et matrice des onze API contrôlée.
- `git diff --check` : réussi.
- Gradle/SDK Android ne sont pas installés dans ce terminal ; compilation Java, APK Release, vérification non-débogable et émulateurs restent donc des gates CI.
- Aucun commit, push, run CI, APK, déploiement Worker ou migration D1 de production n'a encore été effectué pour v2.6.7. Le Worker public reste `2.6.5-cloudflare` et ne connaît pas les nouveaux endpoints.

### Périmètre distant reçu

L'autorisation ci-dessus est suffisante pour cette remise coordonnée seulement. Consigner ci-dessous les identifiants réels du commit, de la migration, de la version Cloudflare, des runs et de l'APK ; ne pas réutiliser cette autorisation après la livraison.

## 0A. Journal de reprise v2.6.6 — 13 août 2026

### Retour du propriétaire conservé comme preuve terrain

- La v2.6.5 a pu être installée et ouverte sous Android 11 après plusieurs essais avec désinstallations/réinstallations. Ce n’est pas une preuve de mise à jour directe fiable sur ce modèle.
- Les autres versions Android essayées ont accepté la mise à jour.
- Le message qui attribue correctement l’échec financier à l’Accessibilité ou aux autorisations manquantes du Robot est jugé utile et doit rester.
- Le propriétaire ne demande pas de réécrire le moteur financier. Tout comportement non critiqué reste un acquis, notamment Test/Achat/Vente, Remote/Robot, confirmation 1/2, contrôle de la SIM et refus d’un slot déjà occupé par une autre SIM.

### Problèmes demandés

1. Le réglage du PIN se trouvait tout en bas d’un panneau **Gérer** haut de 260 dp, sans indicateur de défilement assez évident.
2. Sous un verrou simple sans mot de passe, le dialogue Camtel pouvait être présent mais la saisie semblait tourner : le dialer acceptait parfois `ACTION_SET_TEXT` tout en masquant ou en ne réexposant pas la valeur à l’Accessibilité ; l’ancienne logique attendait alors la dernière des cinq tentatives.
3. Le réveil et le retrait temporaire du verrou simple avaient lieu trop près de la composition. Certains OEM avaient besoin que l’activité normale devienne visible et que le keyguard soit réellement libéré avant l’ouverture USSD.
4. Les cinq onglets, encore placés entre le nœud actif et les opérations, occupaient une zone de lecture importante et les modules hors Flux contenaient surtout des annonces.

### Décisions et modifications v2.6.6 livrées

- Version : `2.6.6`, `versionCode 46`, Android 6.0+ inchangé.
- **Gérer** : barre verticale persistante, fading edge et texte d’indice ; **MODIFIER LE PIN CAMTEL** devient le premier réglage Robot et ouvre une fenêtre dédiée avec affichage volontaire possible.
- Verrou simple : réveiller l’écran, désactiver seulement le keyguard sans identifiant, demander à Android 8+ de le libérer via l’activité normale si nécessaire, attendre la surface interactive, puis composer. Ne jamais utiliser cette voie pour un PIN, schéma, mot de passe ou verrou biométrique Android.
- PIN : après concordance du bénéficiaire et du montant, un retour vrai de `ACTION_SET_TEXT` ou du collage local temporaire suffit comme preuve d’écriture même si le dialer garde le champ vide/masqué pour l’Accessibilité. Il n’existe aucun overlay Blue Magic et aucune prétendue dissimulation du PIN à l’écran.
- Fin de transaction : conserver le wake lock de l’écran jusqu’au résultat/finalisation ; restaurer ensuite le verrou simple. Le PIN reste chiffré localement et n’est jamais journalisé ou transmis.
- Navigation : dock inférieur flottant à cinq entrées, Flux au centre ; dock caché pendant la saisie clavier pour ne pas recouvrir les formulaires.
- Modules activés sans changer le protocole financier : rapports locaux, accès Comptes/SIM dans Flotte, commandes sûres du hall Robot, santé serveur et accès au test sans fonds dans SAV.
- Backend : aucune modification du Worker, aucune migration D1. La production reste `2.6.5-cloudflare` tant que l’API n’a pas de besoin fonctionnel nouveau.
- CI : la matrice doit désormais tester la mise à jour v2.6.5 → v2.6.6 sur API 23, 26, 30 et 36 et conserver un marqueur de données. Le test Android 11 reste obligatoire.
- Livraison APK : si les secrets permanents ne sont toujours pas disponibles dans GitHub, le workflow peut exporter l’APK interne une seule fois, uniquement sur la branche de reprise et pour le message exact du commit v2.6.6, avec une rétention d’un jour. Télécharger une fois, re-signer hors dépôt, vérifier, puis supprimer immédiatement cette étape et ne jamais relancer le run complet.

### Invariants explicitement non modifiés

- ne jamais réintroduire une route `PhoneAccount` parfaite comme prérequis au démarrage ou au lease ;
- ne pas toucher à la prévisualisation, à la confirmation 1/2, à l’idempotence, au FIFO, au lease ou au résultat `UNKNOWN` ;
- `TEST_NUMBER` reste sans PIN et sans Accessibilité ;
- une finance reste interdite si PIN/Accessibilité/permissions manquent ;
- un Remote, une SIM différente ou une preuve de slot invalide ne peut pas éjecter un Robot vivant ;
- aucune modification de schéma D1, de secret ou de clé de signature n’est incluse.

### Publication, CI, export et signature v2.6.6

- Autorisation exacte exécutée : publication publique sur `fix/blue-magic-v2-6-recovery`/PR `#4`, CI Android, export interne unique pendant un jour, téléchargement unique, re-signature permanente, livraison, puis retrait de l’export avec `[skip ci]`. Aucun Worker et aucune migration D1 n’étaient autorisés ou nécessaires.
- Commit GitHub fonctionnel : `45cca8f33b871a066e049f2b08b7a16e69cab8c5`. Son arbre `5fa0d70b2f8e40a07864ca0858f59dccbd9981ab` est identique à celui du commit local autorisé `b502bfd81168dea7e8cc0004f77ef2c67a6d332b`; seul l’objet commit a été recréé par l’API GitHub.
- Run push/export : `31722781395`. Run PR indépendant : `31722786172`, puis relance du seul job API 36. L’événement PR n’a jamais exporté d’APK interne.
- Compilation Android, `finance-flow.mjs`, tests unitaires, contrôle Worker/D1 et création des paquets serveur : réussis. Les sources USSD, le protocole financier, le Worker et les migrations sont identiques à la v2.6.5.
- Mise à jour v2.6.5 → v2.6.6 avec conservation du marqueur local : réussie sur API 23/Android 6, API 26/Android 8 et API 30/Android 11. Le job Android 11 distinct a réellement démarré la v2.6.6 et le profil Robot mémorisé sans crash dans le run PR.
- Les échecs API 30 et Android 11 du run push étaient des délais `am start -W` de l’émulateur ; les mêmes scénarios ont réussi dans le run PR. API 36 a été exécutée deux fois puis relancée une fois : à chaque échec, l’émulateur logiciel très lent a expiré sur le démarrage de la v2.6.5 de référence avant l’installation v2.6.6. `MainActivity` était bien l’activité active et aucun crash Blue Magic n’est présent. API 36 reste donc non prouvée par ce harnais, sans constituer une régression applicative démontrée.
- Artefact interne unique : `Blue-Magic-v2.6.6-Internal-Resign`, identifiant `9190012328`, créé le 13 août 2026 à 16:52 UTC et expirant le 14 août à 16:52 UTC. Taille ZIP 107 636 octets ; SHA-256 `671b0041d44c96d292bce5e00e4abdbfef50fc59dc78ddd3d14bec25fdbe7e1b`. Ne jamais installer ni redistribuer cet artefact interne.
- APK finale : `Blue-Magic-v2.6.6-Ergonomie-Verrou-PIN-Release.apk`, 119 515 octets, SHA-256 `9ff5fc65925030b4ef29a07550d0010cebb1d93c06fdc7d86bf7f4c5cdf3602b` ; paquet `com.profitloop.blueauto`, `versionName 2.6.6`, `versionCode 46`, `minSdk 23`, `targetSdk 34`.
- Signature : v1, v2 et v3 valides ; certificat `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`, RSA 4096, SHA-256 `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`, identique à la v2.6.5.
- Le décodage de l’APK confirme que `index.html`, `app.js` et `style.css` embarqués correspondent octet pour octet aux sources publiées. Le dock inférieur, le réglage PIN prioritaire et le traitement du verrou simple sont présents ; l’ancien overlay de confidentialité et le texte trompeur « PIN protégé » sont absents.
- L’étape d’export ponctuel a été supprimée après usage. Le commit de nettoyage porte `[skip ci]`; vérifier que le HEAD de branche ne déclenche aucun nouveau run.
- Limite terrain : ni GitHub Actions ni un émulateur ne possèdent une SIM Camtel ou le dialer du fabricant. Le test réel sous verrou simple, d’abord avec `TEST_NUMBER`, puis avec une transaction minimale supervisée, reste obligatoire avant de déclarer ce cas validé.

## 0. Résumé de la reprise v2.6.5 au 13 août 2026

- Le propriétaire a autorisé explicitement la mise en index, le commit et le push de la v2.6.5 sur `fix/blue-magic-v2-6-recovery`/PR `#4`, son déploiement unique sans migration D1, l'export interne unique, la re-signature permanente et la livraison. Il a ensuite autorisé explicitement la publication publique, dans son dépôt `Delor85/BlueAuto`, de la procédure interne, des états, des scénarios de test et des workflows contenus dans le commit local `c7dbce4`.
- Le commit GitHub publié est `c7b9404e22e8c314f95723105b2e474e2b21194c`. Son arbre `43cfc0fdb69c2ac7e504cd58d1508fb432eded47` est exactement celui du commit local autorisé `c7dbce4`; l'identifiant du commit diffère uniquement parce que l'objet a été recréé par l'API GitHub avec ses propres métadonnées.
- Le commit de nettoyage distant est `9b1d35f05630effa5e1683bfaa3da2195691ed61`, HEAD de la PR `#4` ouverte et non fusionnée. Il supprime le marqueur et le workflow Cloudflare ponctuels. Son message contient `[skip ci]`, donc il n'a déclenché aucun nouveau build, export ou déploiement.
- Le Worker de production `blue-magic-api` exécute maintenant `2.6.5-cloudflare` avec D1 `blue-magic` en ligne. Version Cloudflare : `b2cc65a1-9d86-4d37-8d18-9e48b746e90e`.
- Le workflow Cloudflare `31710676858` a réussi les tests, le dry-run, la vérification `No migrations to apply!` et le déploiement. Son contrôle de santé immédiat a seul échoué en lisant encore `2.6.4` pendant la propagation ; le contrôle indépendant suivant a confirmé `2.6.5-cloudflare` et D1 `online`.
- Le build GitHub Actions est le run `31710676903`. L'artefact interne unique `Blue-Magic-v2.6.5-Internal-Resign`, identifiant `9185102053`, a été créé le 13 août à 14:32 UTC et expire le 14 août à 14:32 UTC.
- API 23 (Android 6) et API 26 (Android 8) ont validé la mise à jour v2.6.4 → v2.6.5 avec conservation du fichier de données. Les trois échecs ont été relancés une fois, sans recréer l'artefact interne. Sur API 30 et 36, le runner très ralenti a renvoyé `Status: timeout` ou `Broken pipe` pendant le lancement de la v2.6.4 de référence, donc avant l'installation v2.6.5. Le job de lancement Android 11 a installé l'APK avec succès mais le gestionnaire Activity a immédiatement renvoyé une fois `MainActivity does not exist`, en contradiction avec le manifeste décodé. Aucun de ces journaux ne contient un crash Blue Magic, mais Android 11/36 ne sont pas validés pour la v2.6.5. Une correction du harnais a été préparée localement puis écartée de la publication, car l'autorisation publique visait exactement les workflows de `c7dbce4`.
- L'APK finale est `Blue-Magic-v2.6.5-Hall-SIM-Tabs-Release.apk`, paquet `com.profitloop.blueauto`, `versionName 2.6.5`, `versionCode 45`, `minSdk 23` et `targetSdk 34`.
- Son SHA-256 est `5b95a1bf61f397b3e1f4fe81328ccddda2e011704c18c13e955e7bda6b023384`. Sa taille est 115 522 octets. Les signatures v1/v2/v3 sont valides et le certificat permanent RSA 4096 a l'empreinte `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`, identique à la v2.6.4.
- Le déclencheur et le workflow de déploiement ponctuels ont été supprimés après usage. La suppression de l'étape d'export dans `build.yml` a été préparée localement mais sa publication a été refusée, car elle modifierait un workflow au-delà du contenu public exactement autorisé. L'étape distante reste bornée au message exact du commit de remise : aucun futur commit ordinaire ne peut l'activer. Ne jamais relancer le run complet `31710676903`; une nouvelle autorisation explicite de publication de `build.yml` permettra de la retirer définitivement.
- La validation terrain Test/Achat/Vente en moins de 30 secondes reste celle de la v2.6.4. La v2.6.5 doit d'abord être installée par-dessus, sans désinstallation, puis valider `TEST_NUMBER` avant tout essai financier supervisé.
- La version publique GitHub de cette procédure reste celle exactement autorisée dans `c7dbce4`. Les résultats postérieurs ont été refusés à la publication publique faute d'autorisation distincte ; la présente version finale est conservée dans l'espace durable du propriétaire et constitue la relève complète.

## 0.1 Socle v2.6.4 conservé

- Le Worker de production `blue-magic-api` exécute `2.6.4-cloudflare` avec D1 `blue-magic` en ligne.
- L'APK permanente livrée est `Blue-Magic-v2.6.4-Remote-Robot-Release.apk`.
- Le paquet est `com.profitloop.blueauto`, `versionName 2.6.4`, `versionCode 44`, `minSdk 23` et `targetSdk 34`.
- Le certificat est identique à celui des APK permanentes v2.5.3, v2.5.4, v2.6.0, v2.6.1 et v2.6.2.
- Le SHA-256 de l'APK est `76dcb157723da77aa68794c3a4f8ff9abc98c04e4f34388d17b98d0c9cc58e6b`.
- Le flux Remote distinct vers Robot distinct, `TEST_NUMBER`, Achat, Approvisionnement et Vente sont couverts par les tests Android/JavaScript et Worker/D1.
- L'ouverture sous Android 11 et le redémarrage avec un profil Robot mémorisé sont prouvés par la CI sur API 30.
- Le retour terrain du 13 août confirme que Test, Achat et Vente fonctionnent en Remote et Robot, avec une durée observée inférieure ou égale à 30 secondes.
- La PR `#4` reste ouverte et non fusionnée jusqu'à la répétition de ce verdict terrain avec la v2.6.5.

## 0.2 Retour terrain v2.6.4 et chantier ciblé v2.6.5

Le propriétaire a validé le cœur v2.6.4 sur de vraies SIM Camtel : opérations financières et test réussis en Remote comme en Robot. Cet acquis devient le nouveau socle de non-régression.

Quatre limites ont ensuite été constatées :

1. sous verrou simple sans mot de passe/schéma/empreinte, le voile d'Accessibilité « PIN protégé » empêchait ou perturbait l'insertion ; écran ouvert, le PIN était de toute façon visible malgré le message contraire ;
2. Remote → Robot exigeait la SIM et les autorisations avant d'ouvrir l'espace Robot, alors que le comportement attendu est un hall sans privilège, puis autorisations, slot, liaison SIM, PIN et démarrage ;
3. supprimer localement un compte Robot pouvait retirer son jeton avant la confirmation d'arrêt serveur et créer un propriétaire fantôme récent ;
4. installation/mise à jour : Android 8 a accepté la mise à jour directe, Android 6.0.1 a exigé une désinstallation et Android 11 a accepté v2.6.4 après installation intermédiaire de v2.6.2.

La v2.6.5 est le lot minimal publié pour ces cas. Elle ne modifie ni la création financière, ni la confirmation, ni la FIFO, ni le routage USSD validé. Son Worker est actif depuis que le contrôle indépendant de `/health` renvoie `2.6.5-cloudflare` et D1 `online`.

## Partie I — mémoire complète depuis le début du projet

### A. Sources utilisées pour reconstruire cette mémoire

La reprise a été reconstruite à partir de quatre sources, recoupées entre elles :

1. le cahier des charges fonctionnel maître de juillet 2026 ;
2. les anciens échanges fournis par le propriétaire, notamment les versions 2.4 à 2.6.3 ;
3. l'historique Git complet de `Delor85/BlueAuto` ;
4. les sources Android, Worker, migrations, tests et workflows réellement présents sur la branche.

Il ne faut jamais se fier uniquement au numéro affiché dans une ancienne réponse. Pour toute reprise, vérifier la version dans l'APK décodée, le certificat avec `apksigner`, le commit Git, le run CI et `/api?action=health`.

### B. Demande initiale et cahier des charges à conserver

#### B.1 Problème métier

Blue Magic doit supprimer la dépendance à une personne physiquement présente devant la Master SIM. La chaîne Camtel/Blue est hiérarchique :

```text
SIM nationale/régionale → DAE → DSM → PoS → client final
```

- Le DAE alimente ses DSM.
- Le DSM alimente ses PoS.
- Le PoS vend le crédit de communication au client final.
- Chaque niveau ne doit être alimenté que par son supérieur officiel.
- La pression opérationnelle existe 24 h/24 : sommeil, réunions, déplacements ou absence de réseau du responsable ne doivent plus arrêter la distribution.

#### B.2 Solution prioritaire demandée

Deux téléphones distincts doivent coopérer par Internet :

- le téléphone **Remote/Télécommande** crée et suit l'ordre ;
- le serveur joue la boîte aux lettres et l'unique source de vérité ;
- le téléphone **Robot**, qui détient la SIM réelle, prend l'ordre et compose l'USSD ;
- le résultat Camtel remonte jusqu'au Remote.

Le projet d'origine utilisait InfinityFree, `api.php` et SQLite. La production active a ensuite été migrée vers un Worker Cloudflare et D1, sans changer le principe de boîte aux lettres.

#### B.3 Contraintes non négociables du cahier des charges

- Android 6 et versions supérieures lorsque la plateforme Android le permet.
- Remote et Robot distincts, avec un ancien profil Hybride accepté en compatibilité de migration.
- multi-comptes, multi-rôles et multi-SIM sans mélange de PIN, de nœud ou de file ;
- file FIFO, lease atomique, idempotence et anti-double-exécution ;
- confirmation avant toute opération financière ;
- contrôle fournisseur, bénéficiaire et montant avant insertion du PIN ;
- PIN Camtel chiffré uniquement sur le téléphone Robot, jamais sur Internet ni dans D1 ;
- arrêt immédiat du profil en cas de mauvais PIN, sans trois tentatives automatiques ;
- test sans fonds indépendant du PIN financier ;
- service Robot persistant et économe, avec notification et gestion de la veille ;
- interface lisible bleu/or et fonctionnement des WebView anciennes ;
- coût d'exploitation minimal ;
- procédure détaillée permettant à un tiers de reprendre sans la conversation.

#### B.4 Périmètre ERP plus large demandé mais non entièrement livré

Le cahier maître décrit également cinq familles d'onglets : graphes/rapports, flux de crédit et preuve, flotte/cycle de vie, configuration/robotique, puis SAV/diagnostic. Il contient aussi des idées de comptes Tchoronko, mercenaires, CRM, KYC, GPS, audit de soldes, SMS et reporting comptable.

La priorité explicite était toutefois de rétablir d'abord l'interaction avec le téléphone Robot. La v2.6.4 livre et sécurise ce trajet critique. Elle ne doit pas être présentée comme l'ERP complet à cinq onglets. Les modules étendus doivent être planifiés séparément après validation terrain des opérations.

### C. Matrice du cahier des charges et état réel

| Exigence | État v2.6.4 | Preuve ou limite |
|---|---|---|
| Remote → serveur → Robot distinct | Acquis et validé terrain | Le test Worker crée avec le jeton Remote A et loue uniquement avec le jeton Robot B ; le terrain confirme Remote et Robot. |
| Achat DSM/PoS | Acquis et validé terrain | Prévisualisation, confirmation, création D1, lease, contrôles, PIN et résultat Camtel fonctionnent. |
| Approvisionnement DAE→DSM / DSM→PoS | Acquis et validé terrain | Hiérarchie, numéros officiels, montant et exécution sont conservés. |
| Vente PoS→client | Acquis et validé terrain | Réservée au rôle PoS ; destinataire externe et montant contrôlés. |
| Test sans fonds `*825*3*3#` | Acquis et validé terrain | Fonctionne en Remote et Robot et reste indépendant du PIN. |
| Confirmation 1/2 | Acquis | Aucun ordre financier n'est créé avant confirmation. |
| Contrôle du pop-up Camtel 2/2 | Implémenté défensivement | L'Accessibilité exige les mêmes numéros et le même montant ; toute variation non reconnue échoue sans PIN. Dépend du dialer du fabricant. |
| PIN local uniquement | Acquis | Android Keystore/chiffrement local ; Worker et D1 ne le reçoivent pas. |
| Anti-mauvais PIN | Acquis | Un mauvais PIN bloque le profil concerné ; les autres SIM/profils continuent. |
| FIFO, lease, idempotence | Acquis | Tests D1/Miniflare, expiration, annulation avant lease et absence de rejeu après composition. |
| Liaison à la SIM physique et au slot | Acquis | Attestation avant activation, lease et composition. |
| Multi-SIM et multi-comptes | Implémenté et testé au niveau logiciel | Validation recommandée sur chaque fabricant/dialer réel. |
| Propriété Robot | Acquis v2.6.4, précisé v2.6.5 | Un Remote ordinaire ne remplace personne. Lors d'un conflit explicite, seul le téléphone qui revérifie la même SIM physique au bon slot peut remplacer l'ancien propriétaire de cette empreinte. |
| Android 6+ | Paramétré et partiellement prouvé | `minSdk 23`; anciens appareils Android 6/8 ont ouvert l'app ; API 30 prouvée par émulateur ; chaque téléphone terrain reste à tester. |
| Robot après veille/redémarrage | Implémenté | Foreground Service, watchdog et réveil ; après redémarrage complet, Android peut exiger un premier déverrouillage. |
| Cinq onglets ERP complets | Démarré en v2.6.5 | Navigation Rapports, Flux, Flotte, Robot et SAV ; Flux conserve le moteur existant, les autres modules commencent par des synthèses isolées. |
| Reporting, KYC, CRM, Tchoronko, mercenaires | Non livré ou seulement présent dans le cahier | À traiter dans des lots futurs après validation financière. |

### D. Chronologie technique et leçons des versions

#### D.1 Premiers essais et reconstruction v2

Le dépôt contient de nombreux premiers commits Android, SMS et Accessibilité, puis une suppression/reconstruction. Le commit `2e82396` a rétabli un noyau Robot v2 propre : Android/WebView, backend, distribution et pipeline CI.

Les v2.1 à v2.3 ont ajouté successivement :

- PIN automatisé, multi-SIM et multi-comptes ;
- durcissement de l'isolement des Robots et des PIN ;
- pause des profils verrouillés, sérialisation multi-SIM et file d'attente.

Acquis à conserver : un profil défaillant ne doit pas arrêter les autres, et une SIM ne doit jamais exécuter deux sessions USSD simultanées.

#### D.2 Série v2.4 — Remote, appairage, veille et verrouillage

- **v2.4** : réparation de l'appairage et remise en attente du Robot sous Android 6.
- **v2.4.1** : protection du mode Remote et isolation des files multi-SIM.
- **v2.4.2** : conservation des preuves en attente sans bloquer les autres SIM ; meilleure synchronisation Remote/Robot et annulation.
- **v2.4.3** : service persistant et watchdog sans garder l'écran allumé.
- **v2.4.4** : renouvellement automatique d'un jeton appareil D1 invalide.
- **v2.4.5** : retrait de l'overlay applicatif et réveil de la surface USSD système pour préserver Remote, FIFO, multi-SIM et compatibilité Android 6.

Limite découverte : `TelephonyManager.sendUssdRequest()` n'est disponible qu'à partir d'Android 8 et ne résout pas universellement les dialogues interactifs Camtel. La voie retenue combine composition système, Accessibilité et échec fermé. Aucun code Android ne peut contourner légalement et universellement un verrou sécurisé du téléphone.

#### D.3 Série v2.5 — routage SIM et sûreté financière

- **v2.5.0** : durcissement du routage SIM et contrôle de l'intégrité financière.
- **v2.5.1** : repli Android 6 sur une seule SIM vérifiée et gestion du verrou simple.
- **v2.5.2 à v2.5.4** : récupération des profils migrés, lignée de signature permanente, diagnostics d'appairage et affichage explicite des erreurs.

Une régression s'est installée : la recherche d'une route `PhoneAccount` parfaite a progressivement été traitée comme condition de démarrage du Robot. Sur plusieurs dialers, cette métadonnée n'existe pas avant l'appel réel. L'interface restait vivante, mais le Robot ne louait plus les commandes.

#### D.4 Série v2.6 avant la présente reprise

- **v2.6.0** : tentative de restauration du flux Robot et de la récupération.
- **v2.6.1** : restauration de la finance Android 6 et confirmation financière signée côté Worker.
- **v2.6.2** : Worker financier correspondant déployé, boutons financiers réparés et protection du Robot actif contre le « dernier appareil arrivé ».
- **v2.6.3** : suppression du blocage de route parfaite avant démarrage/lease. Une APK a été produite, mais le problème Remote→Robot n'était pas encore éliminé et Android 11 n'était pas prouvé.

Le point positif majeur de v2.6.3 à préserver est la distinction suivante : **vérifier la SIM avant le lease, résoudre la route Téléphone seulement au moment de composer**.

### E. Journal complet de ce chat de reprise v2.6.4

#### E.1 État signalé par le propriétaire

Au début de cette reprise :

- les boutons répondaient ;
- `CONFIRMATION 1 SUR 2` apparaissait ;
- après confirmation, Achat, Vente et Test n'aboutissaient pas ;
- le Remote ne commandait pas le Robot ;
- l'application s'ouvrait sous Android 6 et 8 mais pas sous Android 11 ;
- la réflexion précédente avait été interrompue avant une livraison complète.

Cette description a été traitée comme une rupture de la chaîne après l'interface, pas comme un simple problème de bouton.

#### E.2 Audits exécutés

La reprise a :

1. relu les anciens échanges fournis et le cahier des charges maître ;
2. audité l'historique Git et comparé les acquis v2.4.5, v2.5 et v2.6 ;
3. inspecté Android, Worker, D1, tests et workflows ;
4. vérifié l'ancien état de production, alors encore en `2.6.2-cloudflare` ;
5. reproduit les flux avec deux identités appareils réellement distinctes ;
6. ajouté des tests de réparation de jeton, propriétaire fantôme et profil migré ;
7. ajouté un démarrage réel d'APK sous émulateur Android 11/API 30.

#### E.3 Deux causes racines cumulatives

**Cause Android — route exigée trop tôt :** les versions 2.5/2.6 exigeaient une « route d'appel parfaite » avant de démarrer le Robot et avant de louer une commande. Sur Android 6/8/11, plusieurs dialers ne l'exposent qu'au moment de l'appel. Le Robot paraissait actif, mais ne prenait rien.

**Cause Worker — propriétaire Robot fantôme :** lors d'une réparation de jeton, `pair_device` pouvait créer une nouvelle ligne appareil et laisser l'ancienne ligne avec `robot_enabled = 1`. D1 attribuait la file à l'ancien identifiant silencieux. Le vrai téléphone affichait Robot, mais le serveur attendait un appareil disparu.

Ces causes expliquent pourquoi une correction uniquement visuelle, une correction uniquement Android ou un test avec le même jeton des deux côtés ne suffisait pas.

#### E.4 Corrections v2.6.4

- Le Robot démarre et loue après vérification de la SIM, sans attendre une route `PhoneAccount` prématurée.
- La route exacte est résolue juste avant la composition ; le repli dialer n'est permis que pour une seule SIM physiquement vérifiée.
- La réparation du jeton cible la même ligne par `replace_device_id`.
- Un profil migré peut retrouver son appareil par l'empreinte de la même SIM attestée.
- Un propriétaire fantôme non attesté ne bloque plus la file.
- Un Robot de la même SIM silencieux depuis 15 minutes peut être récupéré, mais un Robot vivant reste prioritaire.
- Le Remote reçoit `robot_ready`, `robot_status`, le dernier passage et un message honnête.
- L'interface n'annonce plus « transmise au Robot » si le Robot est hors ligne.
- Le test d'intégration utilise un Remote A et un Robot B distincts.
- Le service de premier plan utilise les types compatibles API 23–28, 29–33 et 34+.
- Le démarrage automatique du Robot mémorisé se fait après le premier rendu de l'activité.

#### E.5 Tests et incidents de CI

Les tests locaux `finance-flow.mjs` et `cloudflare/test/integration.mjs` ont réussi. Le premier ajout du test Android 11 a rencontré trois défauts du **script CI**, pas trois crashs de l'application : mot de passe de signature non transmis à Gradle, `pipefail` utilisé avec un shell non compatible, puis variables non persistantes entre lignes d'émulateur. Les commits `8826566`, `185fe41` et `5e42a0f` ont corrigé ce harnais.

Le run final antérieur `#167` a alors réellement : installé l'APK sur API 30, ouvert une installation propre, injecté un profil Robot mémorisé, redémarré à froid, conservé le processus vivant et confirmé l'absence de crash.

#### E.6 Autorisation et déploiement de production

Le propriétaire a explicitement autorisé le déploiement du Worker v2.6.4 et l'export temporaire de l'APK interne pour re-signature permanente.

Pour borner cette autorisation :

- un déclencheur unique lié au message exact du commit `53806cb` a été ajouté ;
- l'export APK n'était actif que pour ce commit ;
- aucune étape de migration D1 n'a été exécutée, car v2.6.4 n'en nécessite aucune ;
- le workflow a seulement listé les migrations, obtenu `No migrations to apply!`, puis déployé le Worker concerné ;
- les déclencheurs temporaires ont ensuite été retirés du dépôt.

Le workflow Cloudflare `#4`, run `31683508389`, a réussi. Version Cloudflare : `ef561d4b-d46b-4644-b339-f3c0d730463b`. Le contrôle de santé immédiat du workflow a brièvement lu l'ancienne version en raison de la propagation edge. Deux contrôles indépendants avec URL non mise en cache ont ensuite confirmé :

```json
{"ok":true,"data":{"service":"blue-magic-api","version":"2.6.4-cloudflare","database":"online"}}
```

#### E.7 Export, re-signature et vérification de l'APK

- Run d'export : `31683508357`.
- Artefact temporaire : `Blue-Magic-v2.6.4-Internal-Resign`, identifiant `9174458793`, ZIP de 99 300 octets.
- L'APK interne a été utilisée uniquement comme matériau de re-signature.
- Les anciennes entrées de signature ont été retirées avant signature.
- Signature finale v1/v2/v3 avec la clé permanente, RSA 4096.
- Certificat : `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`.
- Empreinte certificat : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`.
- Taille finale : 111 323 octets.
- SHA-256 final : `76dcb157723da77aa68794c3a4f8ff9abc98c04e4f34388d17b98d0c9cc58e6b`.
- Intégrité ZIP/APK : aucune erreur.
- Valeurs vérifiées après décodage : paquet, version 2.6.4/44, minSdk 23, targetSdk 34.
- Certificat comparé directement et identique aux APK v2.5.3, v2.5.4, v2.6.0, v2.6.1 et v2.6.2.

#### E.8 Retour terrain qui clôt la régression principale

Le 13 août 2026, le propriétaire confirme :

- Test, Achat et Vente fonctionnent parfaitement en mode Remote et Robot ;
- une transaction dure au maximum environ 30 secondes ;
- Android 8 accepte la mise à jour directe ;
- Android 6.0.1 n'a accepté qu'après désinstallation ;
- Android 11 a accepté après installation préalable de v2.6.2 ;
- le refus d'un Robot sur un slot déjà occupé et vérifié est apprécié et doit rester.

Les captures montrent aussi le PIN réellement visible dans le champ Camtel lorsque l'écran est ouvert, un voile blanc/confidentiel inutile, le refus `ROBOT_ALREADY_ACTIVE`, les échecs d'installation et une erreur DNS temporaire distincte du code.

#### E.9 Corrections v2.6.5 préparées sans élargir le moteur financier

- suppression du voile `TYPE_ACCESSIBILITY_OVERLAY`; la saisie reste locale et les journaux continuent de masquer le PIN, mais l'écran physique peut l'afficher ;
- réveil et retrait temporaire uniquement d'un verrou simple, jamais d'un verrou Android sécurisé ;
- Remote → Robot ouvre un hall avec Robot arrêté, sans demander la SIM, le PIN ou l'Accessibilité ;
- les privilèges ne commencent qu'après autorisations, choix du slot, liaison de la SIM et pression sur DÉMARRER ;
- suppression d'un profil : arrêt serveur tenté avant effacement local ;
- en cas de `ROBOT_ALREADY_ACTIVE`, dialogue de remplacement explicite et seconde vérification locale de la SIM ;
- le Worker transfère atomiquement la propriété seulement entre appareils du même nœud portant exactement la même empreinte SIM ; mauvaise SIM, SIM absente ou conflit d'une autre empreinte : aucune modification ;
- création d'une navigation à cinq modules ; les opérations validées restent intactes dans Flux ;
- ajout d'un test CI de mise à jour v2.6.4 → v2.6.5 avec la même clé sur API 23, 26, 30 et 36, en contrôlant la conservation d'un fichier de données.

#### E.10 Vérifications et limite d'autorisation de la v2.6.5

Après ces changements, `node app/src/test/finance-flow.mjs`, `npm --prefix cloudflare run check` et `git diff --check` réussissent localement. Le test Worker couvre aussi le cas négatif : une autre empreinte SIM ne remplace pas l'ancien Robot, qui conserve ensuite la capacité de louer la commande. Le transfert de la même empreinte est réalisé par une seule instruction SQLite afin d'éviter un état intermédiaire où les deux Robots seraient arrêtés.

Le conteneur local ne contient ni Gradle ni émulateur Android. La compilation Java, l'installation v2.6.4 → v2.6.5, la conservation des données et le lancement API 23/26/30/36 doivent donc être prouvés par GitHub Actions après publication autorisée du commit.

Un contrôle HTTPS indépendant en lecture seule confirme encore `2.6.4-cloudflare` et D1 `online`. À cet instant de la procédure, aucune action distante v2.6.5 n'a été effectuée : pas de commit Git, pas de push, pas de redéploiement Cloudflare, pas de migration D1 et pas d'export APK. L'autorisation antérieure concernait exclusivement la livraison v2.6.4 et ne doit pas être réutilisée. La relève doit obtenir une autorisation explicite pour :

1. commiter et pousser la v2.6.5 sur la branche/PR existante ;
2. déployer une fois `2.6.5-cloudflare` en production, sans migration ;
3. exporter une fois l'APK interne, puis la re-signer avec le certificat permanent et livrer uniquement l'APK finale vérifiée.

### F. Avancées, acquis, problèmes et blocages pour la relève

#### F.1 Acquis techniques

- Production Worker et application sont enfin au même protocole v2.6.4.
- Les deux causes du silence Remote/Robot sont corrigées dans le code et couvertes par tests.
- Android 11 n'est plus une affirmation basée sur `minSdk` : un lancement API 30 est exécuté en CI.
- Le certificat permanent et la possibilité de mise à jour directe sont prouvés pour la lignée v2.5.3+.
- La procédure de diagnostic distingue interface, création D1, lease, composition, PIN et résultat.
- Les mécanismes financiers positifs des v2.4.5 à v2.6.2 sont conservés.

#### F.2 Blocages qui ne peuvent pas être levés à distance

- GitHub Actions n'a ni SIM Camtel, ni dialer fabricant, ni réseau radio : il ne peut pas prouver une opération réelle.
- Les dialogues USSD interactifs ne sont pas standardisés entre Android 6, 8, 11 et les surcouches Samsung/Tecno/Xiaomi.
- Un écran protégé par un verrou Android sécurisé peut empêcher l'Accessibilité d'agir ; Blue Magic doit échouer sans PIN, jamais contourner ce verrou.
- Le texte Camtel peut changer. Une différence de fournisseur, bénéficiaire ou montant doit bloquer la transaction jusqu'à mise à jour contrôlée des règles.

#### F.3 Règle de communication honnête

On peut désormais écrire que le cœur v2.6.4 fonctionne sur le terrain en Remote et Robot. On ne doit pas encore attribuer ce verdict à la v2.6.5 avant son déploiement borné, son APK permanente et la répétition des mêmes opérations.

## Partie II — procédure technique permanente

## 1. Dépôt et état de départ

- Dépôt : `Delor85/BlueAuto`
- Branche de travail : `fix/blue-magic-v2-6-recovery`
- PR : `#4`, à conserver ouverte et non fusionnée jusqu’à validation terrain
- Application Android : `com.profitloop.blueauto`
- Version de production au début de cette reprise : `2.6.4`, `versionCode 44`
- Version suivante préparée : `2.6.5`, `versionCode 45` ; Worker et APK non déployés/livrés à ce point de la procédure
- Android minimum : API 23, Android 6.0
- Android cible de compilation : API 34
- Worker actuel avant nouvelle autorisation : `2.6.4-cloudflare`
- Worker attendu après déploiement v2.6.5 : `2.6.5-cloudflare`
- Base : D1 `blue-magic`
- Point de santé : `GET /api?action=health`

Toujours commencer par :

```bash
git status --short --branch
git log --oneline -10
git diff --check
```

Ne jamais travailler directement sur `main`, ne jamais fusionner la PR avant les tests terrain et ne jamais désinstaller l’application d’un téléphone de production pour effectuer une mise à jour.

## 2. Objectif fonctionnel non négociable

Le système doit exécuter cette chaîne, sans raccourci :

1. Un utilisateur ouvre Blue Magic sur un téléphone Remote ou Robot.
2. Il demande Achat, Approvisionnement, Vente ou Test.
3. Pour une finance, le Worker calcule les numéros officiels et le montant.
4. L’application affiche `CONFIRMATION 1 SUR 2`.
5. Après confirmation seulement, le Worker insère une commande `PENDING` dans D1.
6. Le téléphone Robot élu pour le nœud fournisseur interroge le Worker.
7. Le Worker loue la commande uniquement à ce Robot.
8. Le Robot vérifie encore la SIM physique, le slot, le nœud, les numéros, le montant et l’intégrité.
9. Le Robot compose l’USSD.
10. Pour une finance, le service d’accessibilité vérifie le pop-up Camtel avant d’insérer le PIN local.
11. Le résultat opérateur est renvoyé au Worker et visible sur le Remote.

Une confirmation qui apparaît sans création D1, ou une création D1 sans location par le Robot, est une panne. Un bouton actif ou un test unitaire vert ne suffit jamais à déclarer cette chaîne opérationnelle.

## 3. Architecture

### Android

- `MainActivity.java` : appairage, profils, écran de gestion, WebView embarquée et pont JavaScript.
- `app/src/main/assets/app.js` : boutons, prévisualisation, confirmation 1/2, création et affichage des commandes.
- `ApiClient.java` : HTTPS, jeton appareil, réparation d’authentification et appels API.
- `RobotService.java` : heartbeat, polling FIFO, lease, composition et synchronisation.
- `SimIdentityManager.java` : attestation de la SIM physique liée au profil.
- `SimCallManager.java` : résolution du compte Téléphone et composition USSD.
- `UssdCommandFactory.java` : reconstruction et contrôle de l’ordre loué.
- `BlueAccessibilityService.java` : contrôle du dialogue Camtel, insertion PIN et clic de validation.
- `PendingCommandStore.java` : état local par profil/SIM.

### Cloudflare

- `cloudflare/src/index.js` : API unique.
- `cloudflare/migrations/0001_initial.sql` : nœuds, appareils, commandes et événements.
- `cloudflare/migrations/0002_robot_sim_attestation.sql` : attestation et slot SIM.
- `cloudflare/test/integration.mjs` : test D1/Miniflare du flux complet.
- `cloudflare/wrangler.jsonc` et fichier de production généré : Worker, assets et binding D1.

### États d’une commande

```text
PENDING
  → LEASED
  → DIALING
  → AWAITING_PIN        (finance)
  → PIN_SUBMITTED       (finance)
  → AWAITING_RESULT
  → SUCCEEDED | FAILED | UNKNOWN | BLOCKED
```

`CANCELLED` est permis uniquement avant la location. Un ordre composé mais sans preuve finale devient `UNKNOWN`, jamais automatiquement rejoué.

## 4. Causes déjà identifiées

### 4.1 Route d’appel exigée trop tôt

Les versions 2.5/2.6.2 pouvaient exiger une correspondance parfaite entre slot SIM et `PhoneAccount` avant même de démarrer le Robot ou de louer une commande. Plusieurs dialers Android 6, 8 et 11 ne publient ces informations qu’au moment de l’appel. Le Robot paraissait actif mais ne prenait aucune commande.

Correction à préserver :

- vérifier la présence et l’identité de la SIM avant le lease ;
- résoudre la route Téléphone seulement juste avant la composition ;
- utiliser le compte exact lorsqu’il est disponible ;
- sur une seule SIM active et physiquement vérifiée, permettre le dialer système par défaut ;
- ne jamais choisir arbitrairement une SIM sur un téléphone réellement ambigu.

### 4.2 Propriétaire Robot fantôme

L’ancienne réparation d’un jeton appelait `pair_device`, qui créait une nouvelle ligne `devices`. L’ancienne ligne pouvait conserver `robot_enabled = 1`. Le nouveau téléphone affichait localement Robot actif, mais le Worker réservait la file à un appareil qui n’existait plus.

Correction v2.6.4 à préserver :

- l’application transmet `replace_device_id` lors d’une réparation ;
- le Worker renouvelle le jeton de la même ligne appareil ;
- si un ancien profil Android ne connaît plus cet identifiant, le Worker retrouve cette ligne
  grâce à l’empreinte de la SIM vérifiée, au lieu de créer un second propriétaire ;
- un propriétaire historique sans attestation SIM valide ne bloque plus la file ;
- un propriétaire de la même SIM devenu silencieux depuis 15 minutes peut être libéré par le téléphone qui prouve cette même SIM ;
- un Robot vivant reste prioritaire contre un Remote ordinaire ou une empreinte différente ;
- lors d'un conflit explicite seulement, une nouvelle preuve de la même SIM physique au bon slot transfère atomiquement la propriété et désactive l'ancien propriétaire de cette empreinte ;
- un Remote sans la SIM physique ne peut pas devenir Robot ni évincer l’existant.

### 4.3 Tests trop superficiels

Un ancien test utilisait souvent le même appareil logique pour créer puis louer. Cela ne prouvait pas la communication Remote/Robot.

Le test obligatoire doit utiliser :

- jeton A : appareil `REMOTE` ;
- jeton B : appareil `ROBOT` du même nœud, avec SIM attestée ;
- création avec A ;
- lease avec B ;
- impossibilité de lease avec A ;
- états de commande visibles depuis A.

### 4.4 Démarrage Android 11

Un profil Robot mémorisé redémarre le service lorsque l’activité reprend. Les types de service de premier plan introduits sur Android 14 ne doivent pas fermer le processus sur Android 10/11.

Correction à préserver :

- API 23–28 : `startForeground(id, notification)` ;
- API 29–33 : type `dataSync` ;
- API 34+ : type `specialUse`, avec repli `dataSync` ;
- démarrage automatique après rendu initial de l’activité ;
- test émulateur API 30 avec un premier démarrage propre puis un profil Robot mémorisé.

## 5. Invariants de sécurité et d’usage

Ne pas modifier sans une preuve et un test dédiés :

- le PIN reste chiffré localement et n’est jamais envoyé au Worker, à D1 ou au JavaScript ;
- la confirmation 1/2 reste obligatoire pour toute finance ;
- `TEST_NUMBER` reste indépendant du PIN et de l’Accessibilité ;
- la SIM physique est contrôlée avant lease et avant composition ;
- le numéro fournisseur, le numéro bénéficiaire et le montant sont contrôlés avant PIN ;
- un Remote ordinaire ou une SIM différente ne peut pas éjecter un Robot vivant ; seule la procédure explicite de conflit avec seconde preuve de la même SIM peut transférer la propriété ;
- une SIM/nœud bloqué ne bloque pas les autres profils du téléphone ;
- une seule session USSD est ouverte à la fois par téléphone ;
- aucune répétition automatique après `DIALING` en cas de résultat inconnu ;
- la signature Android permanente ne change pas ;
- le design bleu/or et la compatibilité WebView Android 6 restent présents.

## 6. API utile

Les actions sont envoyées sur `/api?action=<action>` en JSON.

- `health` : version Worker et état D1.
- `pair_device` : nouvel appareil ou renouvellement ciblé avec `replace_device_id`.
- `heartbeat` : présence, mode et attestation SIM.
- `activate_robot` : tentative explicite de devenir Robot.
- `update_device_mode` : Remote ou Robot.
- `preview_command` : résolution officielle et empreinte de confirmation.
- `create_command` : création D1 idempotente.
- `lease_command` : location par le Robot élu.
- `release_command` : retour en file avant composition.
- `cancel_command` : annulation d’une commande encore `PENDING`.
- `command_event` : progression ou résultat.
- `command_status` : suivi depuis Remote ou Robot autorisé.

`preview_command` et `create_command` renvoient aussi :

- `robot_ready` ;
- `robot_status` : `ONLINE`, `OFFLINE` ou `STALE` ;
- `robot_last_seen_at` ;
- `robot_message`.

L’interface ne doit jamais afficher « transmise au Robot » lorsque `robot_ready` vaut `false`.

## 7. Tests locaux

Depuis la racine :

```bash
git diff --check
node app/src/test/finance-flow.mjs
npm --prefix cloudflare ci
npm --prefix cloudflare run check
```

Le test Cloudflare doit prouver au minimum :

- appairage hiérarchique DAE/DSM/PoS ;
- Remote distinct vers Robot distinct ;
- `TEST_NUMBER` ;
- prévisualisation et confirmation financière ;
- FIFO et isolation de deux nœuds ;
- expiration sans double exécution ;
- refus d’un second Robot vivant ;
- transfert normal après arrêt explicite, plus récupération d'un fantôme par seconde preuve de la même SIM sans toucher une empreinte différente ;
- renouvellement du même appareil sans propriétaire fantôme ;
- ancien jeton refusé et nouveau jeton opérationnel.

## 8. Compilation Android

La CI utilise Java 17 et Gradle 8.2.

Le keystore permanent n’est pas dans le dépôt. Pour une compilation locale autorisée :

1. placer le keystore hors du dépôt ;
2. fournir son mot de passe par variable de processus protégée ;
3. ne jamais afficher le mot de passe ;
4. compiler `:app:testDebugUnitTest :app:assembleDebug` ;
5. vérifier le certificat avant livraison.

Une APK temporaire signée par une clé CI ne doit jamais être installée ni livrée.

## 9. Test Android 11 obligatoire

Le workflow `Build Blue Magic APK` contient le job `android-11-launch` :

1. il compile une APK éphémère ;
2. démarre un émulateur API 30 ;
3. installe et ouvre l’application sans profil ;
4. vérifie que l’activité reste vivante ;
5. injecte un profil Robot mémorisé de test ;
6. redémarre l’activité ;
7. vérifie que le processus reste vivant et qu’aucun crash du paquet n’apparaît.

Ce job ne prouve pas un USSD Camtel réel. Il prouve le démarrage Android 11 et le chemin du service. Le terrain doit encore valider les dialers des fabricants.

## 10. Déploiement Cloudflare

Le workflow ponctuel ayant servi à la remise v2.6.4 a été supprimé après usage. Le dépôt final ne conserve donc aucune capacité dormante de redéploiement en production. Pour un futur déploiement, obtenir d'abord une nouvelle autorisation explicite, puis recréer un workflow strictement borné sur une branche validée.

Ce workflow ponctuel doit :

1. installer Node 22 ;
2. exécuter tous les tests ;
3. générer la configuration D1 de production sans afficher l’identifiant ;
4. effectuer un dry-run ;
5. lister les migrations ;
6. arrêter le déploiement si une migration apparaît ; son application exige une autorisation séparée et une procédure dédiée ;
7. déployer `blue-magic-api` uniquement lorsqu'aucune migration n'est en attente ;
8. vérifier `/health`.

Avant le déploiement, confirmer :

- `PAIRING_SECRET` reste présent ;
- le binding D1 vise uniquement `blue-magic` ;
- aucune migration destructive n’existe ;
- les autres Workers et bases ne sont pas concernés.

Cette version ne nécessite aucune nouvelle migration D1.

### Déploiement v2.6.4 effectivement réalisé

- Autorisation explicite reçue le 13 août 2026.
- Commit borné : `53806cb0db407185004a3812d57012bf50555b76`.
- Run Cloudflare : `31683508389`, conclusion `success`.
- Tests, dry-run, liste des migrations, déploiement et santé exécutés.
- Réponse migrations : `No migrations to apply!` ; aucune migration n'a été appliquée.
- Seul le Worker `blue-magic-api` a été déployé.
- Version Cloudflare : `ef561d4b-d46b-4644-b339-f3c0d730463b`.
- Santé indépendante après propagation : `2.6.4-cloudflare`, base `online`.
- Le déclencheur, le workflow de déploiement et l'étape d'export APK temporaires ont été retirés immédiatement après la livraison.

## 11. Vérification et signature APK

Pour chaque APK livrée, relever :

- nom de fichier ;
- taille ;
- paquet ;
- `versionName` ;
- `versionCode` ;
- `minSdk` et `targetSdk` ;
- schémas de signature v1/v2/v3 ;
- empreinte SHA-256 du certificat ;
- SHA-256 du fichier.

Empreinte attendue du certificat permanent Blue Magic :

```text
f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5
```

L’installation doit se faire par-dessus la version permanente précédente, sans désinstallation. Une v2.4.5 historique peut appartenir à une autre lignée de signature : si Android refuse, arrêter et relever la version ; ne pas supprimer les données.

### APK v2.6.4 effectivement vérifiée

| Contrôle | Valeur |
|---|---|
| Fichier | `Blue-Magic-v2.6.4-Remote-Robot-Release.apk` |
| Taille | 111 323 octets |
| Paquet | `com.profitloop.blueauto` |
| Version | `2.6.4` / `versionCode 44` |
| Android | `minSdk 23` / `targetSdk 34` |
| Signatures | v1, v2 et v3 valides |
| Certificat | `CN=Blue Magic Permanent Release, O=ProfitLoop, C=CM`, RSA 4096 |
| SHA-256 certificat | `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5` |
| SHA-256 APK | `76dcb157723da77aa68794c3a4f8ff9abc98c04e4f34388d17b98d0c9cc58e6b` |

Le certificat a été comparé directement avec v2.5.3, v2.5.4, v2.6.0, v2.6.1 et v2.6.2 : correspondance exacte. L'installation par-dessus ces versions est donc la voie prévue. Pour v2.4.5 ou une APK inconnue, ne jamais désinstaller en cas de refus : relever d'abord la version et la signature.

## 12. Test terrain sans fonds

Ordre obligatoire :

1. installer l’APK sans désinstaller ;
2. après publication du Worker correspondant, confirmer `2.6.5 • versionCode 45` ;
3. ouvrir le téléphone Robot et vérifier la SIM/slot ;
4. démarrer le Robot ;
5. depuis un autre téléphone Remote, lancer seulement `TEST_NUMBER` ;
6. vérifier `ONLINE` côté Remote ;
7. vérifier la prise en moins de 10 secondes ;
8. vérifier uniquement `*825*3*3#` sur le Robot ;
9. recommencer sur Android 6, 8, 11 et un Android récent disponible ;
10. pour une finance, aller jusqu’à la confirmation 1/2 puis choisir `ANNULER` ;
11. aucune commande ne doit être créée après l’annulation ;
12. une transaction minimale supervisée n’est permise qu’après ces réussites.

## 13. Diagnostic de terrain

Si la confirmation apparaît mais rien ne suit :

1. noter le texte affiché après confirmation ;
2. vérifier si un identifiant de commande apparaît ;
3. relever `ONLINE`, `OFFLINE` ou `STALE` ;
4. regarder la notification du Robot ;
5. ne pas appuyer plusieurs fois ;
6. si l’ordre est `PENDING`, ne pas le recréer ;
7. vérifier le téléphone propriétaire de la SIM et redémarrer son Robot ;
8. relever le statut après 10 secondes.

Si Android 11 ne s’ouvre pas :

```bash
adb shell am force-stop com.profitloop.blueauto
adb logcat -c
adb shell am start -W -n com.profitloop.blueauto/.MainActivity
adb logcat -d -b crash
adb logcat -d | grep -iE 'blueauto|blue magic|FATAL EXCEPTION|ForegroundService'
```

Fournir la trace depuis `FATAL EXCEPTION` jusqu’au dernier `Caused by`, sans secret ni PIN.

## 14. Retour arrière

Le retour arrière serveur doit se faire par commit Git identifié, jamais par modification manuelle non tracée. Avant tout rollback :

- arrêter les tests financiers ;
- vérifier les commandes `PENDING`, `LEASED`, `DIALING` et `UNKNOWN` ;
- ne jamais rejouer automatiquement un ordre déjà composé ;
- conserver D1 ;
- déployer le dernier Worker validé ;
- vérifier `/health`.

Un rollback APK n’est possible que vers une version de même signature et de `versionCode` compatible. Android refuse normalement une baisse de `versionCode` sans désinstallation ; ne pas forcer sur un téléphone contenant des profils utiles.

## 15. Critère de livraison

La livraison n’est terminée que si :

- le code est commité et publié sur la branche ;
- la PR reste dans l’état demandé ;
- les tests Android, Worker et Android 11 sont verts ;
- le Worker correspondant est déployé et `/health` donne la bonne version ;
- l’APK permanente est signée et vérifiée ;
- le SHA-256 est communiqué ;
- `docs/PROJECT_STATE.md` est actualisé ;
- le test terrain est distingué honnêtement des tests automatisés.

Le système ne doit être déclaré opérationnel avec argent réel qu’après validation Camtel sur les téléphones du terrain.

### État de ces critères pour v2.6.4

- code v2.6.4 publié sur la branche : oui ;
- PR ouverte et non fusionnée : oui ;
- tests Android/Worker et preuve Android 11 : oui ;
- Worker v2.6.4 en production et D1 en ligne : oui ;
- APK permanente signée, décodée et vérifiée : oui ;
- procédure et état du projet actualisés : oui ;
- test sans fonds sur les téléphones physiques : oui, confirmé par le propriétaire ;
- opérations Camtel supervisées : oui, Achat et Vente validés en Remote et Robot, en 30 secondes au maximum.

### État de ces critères pour v2.6.5 après publication autorisée

- correctifs ciblés et navigation initiale à cinq modules : publiés sur la PR `#4` ;
- tests JavaScript/Android invariants, Worker/D1 et format du diff : verts localement et dans la CI ;
- compilation APK : réussie ; mise à jour API 23/26 réussie ; API 30/36 non conclue à cause des délais et erreurs du gestionnaire Activity de l'émulateur avant la v2.6.5 ;
- commit/push et mise à jour de la PR : effectués, arbre identique au commit local autorisé ;
- Worker 2.6.5 en production : oui, version Cloudflare `b2cc65a1-9d86-4d37-8d18-9e48b746e90e` ;
- migration D1 : aucune appliquée, `No migrations to apply!` ;
- APK permanente v2.6.5 : produite, re-signée et vérifiée ;
- test terrain v2.6.5 : à répéter après livraison, en commençant sans fonds.
