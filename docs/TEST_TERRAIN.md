# Protocole de test terrain — avant argent réel

## Gate 0 — installation et diagnostic v2.6.5

1. Depuis la v2.6.4 permanente actuellement installée, installer la v2.6.5 **par-dessus**, sans désinstallation, puis confirmer `2.6.5 • versionCode 45`. La CI doit avoir réussi la mise à jour v2.6.4→v2.6.5 sur API 23, 26, 30 et 36 avec conservation des données. Si le téléphone refuse encore, ne pas désinstaller : relever la version installée, le modèle, Android et le message exact.
2. Toucher **VÉRIFIER LE SERVEUR** avant de saisir un secret.
3. Noter le code affiché : `SERVER_CHECK_OK` confirme HTTPS, le Worker et D1 depuis le téléphone ; `NETWORK_DNS`, `NETWORK_TIMEOUT`, `NETWORK_TLS` ou `NETWORK_CONNECT` isole le réseau Android.
4. Remplir le formulaire puis toucher **APPAIRER CE TÉLÉPHONE**.
5. Photographier le dialogue et son code exact si l’appairage échoue. Aucun secret ne doit apparaître dans la photo.
6. Ne poursuivre vers un test financier qu’après `PAIRING_COMPLETE` et l’ouverture de l’écran de contrôle.

Si le compte est déjà appairé, ne le supprimez pas et ne saisissez aucun secret : ouvrez directement l’écran de contrôle.

## Gate 1 — rétablissement de `TEST_NUMBER` sans fonds

1. Sur le compte Robot, accordez Téléphone et État du téléphone, puis utilisez **VÉRIFIER / LIER LA SIM**.
2. Désactivez temporairement l’Accessibilité Blue Magic : l’interface doit avertir que seule la finance est indisponible.
3. Démarrez le Robot. Il doit rester actif au lieu d’être arrêté pour absence d’Accessibilité.
4. Depuis le même profil polyvalent ou depuis le Remote, lancez **Tester la SIM Robot**.
5. Le Remote doit afficher soit `ONLINE` avec « Robot détenteur de la SIM connecté », soit un diagnostic explicite `OFFLINE`/`STALE`. Il ne doit plus prétendre que la commande a été transmise quand aucun Robot ne communique.
6. Si `ONLINE` est affiché, le Robot doit louer la commande en moins de 10 secondes et composer uniquement `*825*3*3#`. Relevez le numéro affiché et le code d’erreur exact si la composition n’a pas lieu.
7. Réactivez l’Accessibilité avant toute transaction financière.

Ce Gate valide la correction de la régression principale sans exposer de fonds. Aucun achat ni vente ne doit être tenté avant sa réussite.

## Gate 2 — insertion du PIN sous verrou simple

1. Utilisez un téléphone Robot physiquement surveillé, avec un simple verrou par glissement, sans PIN, schéma, mot de passe ni empreinte Android.
2. Lancez une transaction minimale supervisée seulement après la réussite de Gate 1.
3. Le verrou simple doit être retiré temporairement pour exposer la fenêtre système USSD, puis restauré après l'opération.
4. Après vérification du numéro et du montant, Blue Magic doit écrire le PIN puis toucher le bouton de validation. Aucun voile « PIN protégé » ne doit recouvrir ou gêner le dialogue. Le PIN peut être visible physiquement pendant ces quelques secondes, mais il doit rester absent des journaux, du Worker et de D1.
5. Un verrou Android sécurisé ne doit jamais être contourné ; la commande financière doit être différée jusqu’au déverrouillage.

## Gate 3 — cartes et opérations financières

Après la mise à jour, ouvrez successivement chaque compte déjà appairé, sans le supprimer :

- `DAE` doit voir **Approvisionnement**, mais pas Achat ni Vente client ;
- `DSM` doit voir **Achat de crédit** et **Approvisionnement** ;
- `POS` doit voir **Achat de crédit** et **Vente client** ;
- chaque écran doit afficher une phrase qui confirme explicitement les actions autorisées pour le rôle.
- sur Android 6 comme sur les versions récentes, Achat, Vente et Test doivent avoir le même état actif bleu, jamais gris ou blanc au repos ;
- après pression, l’écran doit afficher « Vérification des numéros officiels et de la filiation… », puis la confirmation native avec fournisseur, bénéficiaire et montant ;
- **ANNULER** ne doit créer ni composer aucune commande ; **CONFIRMER** doit transmettre exactement l’empreinte de cette prévisualisation.

Si le rôle reste « — », n’effectuez aucune opération financière : utilisez **☰ GÉRER → VÉRIFIER / RÉPARER L’APPAIRAGE** et contrôlez le nœud ainsi que son supérieur.

## Gate A — Serveur

- `api.php?action=health` renvoie du JSON, jamais une page HTML ;
- le Robot s’appaire et reçoit un jeton ;
- deux pressions rapides sur une demande n’entraînent qu’une commande avec la même clé ;
- une Télécommande ne peut pas créer un ordre pour un nœud hors de sa hiérarchie.

## Gate B — Téléphone Robot

- autorisation Téléphone accordée ;
- autorisation État du téléphone accordée sur un appareil multi-SIM ;
- autorisation Numéro de téléphone accordée lorsqu’Android la propose ;
- Accessibilité Blue Magic active ;
- batterie sans restriction ;
- slot exact de la SIM Blue enregistré dans le compte (`SIM 1`, `SIM 2`, etc.) ;
- **VÉRIFIER / LIER LA SIM** affiche le bon nœud, le bon numéro Camtel et le bon slot ;
- au repos, vérifier que l’écran s’éteint normalement ; avec mot de passe ou schéma, tester séparément le comportement du champ PIN après veille ;
- notification Robot permanente ;
- test `*825*3*3#` lancé à distance.

## Gate C — Confirmation PIN

Effectuer d’abord une transaction manuelle minimale et noter le texte exact du pop-up.

- le pop-up expose un `EditText` à l’accessibilité ;
- le texte contient le numéro destinataire à 9 chiffres ;
- le texte contient le montant en FCFA ;
- le bouton porte un libellé reconnu : `ENVOYER`, `SEND`, `CONFIRMER`, `VALIDER` ou `OK` ;
- Blue Magic remplit le PIN seulement lorsque numéro et montant correspondent ;
- la Télécommande affiche d’abord **CONFIRMATION 1 SUR 2** avec opération, montant et destinataire ;
- en modifiant volontairement le montant attendu dans un environnement sans fonds, le Robot doit annuler/refuser avec `CONFIRMATION_MISMATCH` ;
- ne testez jamais volontairement un mauvais PIN sur une SIM de production.

## Gate D — Résultat et anti-doublon

- succès popup détecté ;
- succès SMS détecté sans créer un deuxième résultat ;
- ID Camtel extrait si présent ;
- absence de résultat après 120 secondes → `UNKNOWN`, sans retry automatique ;
- coupure Internet après composition → `UNKNOWN` ou statut à rapprocher manuellement, jamais nouvelle recharge automatique ;
- cinq demandes simultanées sont traitées FIFO, une seule session USSD à la fois.

## Diagnostic rapide

| Symptôme | Cause probable | Action |
|---|---|---|
| `INVALID_RESPONSE` | InfinityFree renvoie HTML/challenge au client natif | Ouvrir l’API dans WebView, vérifier cookies; si persistant, migrer l’API |
| Rien ne s’ouvre sur T1 | surface USSD en arrière-plan bloquée par le fabricant | désactiver l’optimisation batterie et redémarrer le Robot après un déverrouillage |
| `PIN_PROMPT_NOT_ACCESSIBLE` | le dialogue ou le champ PIN n’est pas exposé après 30 secondes | laisser le dialogue visible et envoyer une capture du message ; ne pas retenter avec argent |
| Écran verrouillé, dialogue PIN invisible | l’application Téléphone du fabricant masque le champ MMI derrière le keyguard | déverrouiller le téléphone ; la commande ne doit jamais contourner le verrou sécurisé |
| `PIN_FIELD_REJECTED` | le champ est visible mais l’application Téléphone refuse les méthodes de saisie | garder le pop-up ouvert, vérifier Accessibilité, puis relever le modèle et la version de l’application Téléphone |
| `CONFIRM_BUTTON_NOT_FOUND` | libellé/bouton OEM non reconnu | relever le texte exact et l’identifiant d’accessibilité |
| `SIM_PERMISSION_MISSING` | l’autorisation État du téléphone manque | Autorisations → Téléphone/État du téléphone → Autoriser |
| `SIM_SELECTION_FAILED` | slot vide ou compte d’appel Android non associé | vérifier la SIM choisie dans le compte et qu’elle est active pour les appels |
| `ROBOT_SIM_NOT_VERIFIED` | SIM non liée, déplacée ou attestation serveur absente | ouvrir **☰ GÉRER → VÉRIFIER / LIER LA SIM**, puis redémarrer ce Robot |
| `OFFLINE` | aucun Robot vérifié n’est actuellement élu pour ce nœud | ouvrir le téléphone portant la SIM, vérifier la SIM, puis démarrer le Robot |
| `STALE` | un ancien Robot est enregistré mais n’envoie plus de heartbeat | ouvrir l’ancien téléphone s’il existe ; sinon réparer l’appairage sur le téléphone qui possède physiquement la SIM puis redémarrer le Robot |
| `CONFIRMATION_MISMATCH` | numéro/montant formaté différemment ou réellement faux | ne pas forcer; capturer le pop-up et adapter le parseur |
| `WRONG_PIN` | PIN local erroné | arrêter, vérifier manuellement, enregistrer le bon PIN; aucune répétition |
| `UNKNOWN` | transfert possiblement exécuté sans preuve captée | vérifier solde et cinq dernières transactions avant toute nouvelle tentative |

## Critère de passage en production

Le même modèle de téléphone, la même version Android, la même application Téléphone et la même SIM doivent réussir au moins 30 transactions minimales consécutives, y compris un test réseau lent et un redémarrage. Tant que ce seuil n’est pas atteint, le système reste un pilote supervisé.

## Test de plusieurs comptes sur un téléphone

1. Ajoutez d’abord le DAE, puis ses DSM, puis les PoS, afin que chaque supérieur existe déjà sur le serveur.
2. Utilisez **COMPTES** pour passer d’un profil à l’autre. Le changement d’écran n’arrête plus les autres Robots.
   Touchez le compte déjà actif pour modifier son slot SIM; cette modification reste bloquée pendant sa propre commande.
3. Démarrez séparément chacun des profils Robots souhaités. Ils restent tous actifs; un ordonnanceur unique exécute une seule session USSD à la fois.
4. Une commande Remote peut être créée pendant la surveillance; si une session USSD est déjà ouverte, elle attend son tour.
5. Chaque profil garde séparément son jeton, son PIN chiffré, son slot SIM et son historique local.
6. Lancez deux demandes rapprochées : la seconde doit rester `PENDING` jusqu’à la fermeture complète de la première, puis démarrer après le délai de séparation.

## Test obligatoire de déplacement ou remplacement d’une SIM

1. Sur T1, liez POS1 au slot 2 et DSM1 au slot 1, puis démarrez les deux Robots.
2. Depuis T2, appairez POS1 en mode **REMOTE**, puis entrez dans le **hall Robot**. Cette entrée ne doit demander aucune permission et ne doit pas démarrer le Robot.
3. Dans le hall, accordez les autorisations, choisissez le slot réel et confirmez **VÉRIFIER / LIER LA SIM**. Sans la SIM, le démarrage doit rester impossible.
4. Cas normal : arrêtez explicitement T1, déplacez la SIM vers T2 et démarrez T2.
5. Cas fantôme : si le compte de T1 a été supprimé et que `ROBOT_ALREADY_ACTIVE` apparaît, T2 doit proposer **VÉRIFIER LA SIM ET REMPLACER**. La même SIM au bon slot doit désactiver uniquement l'ancien propriétaire correspondant et démarrer T2. Une SIM absente ou différente doit être refusée.
6. Sur T1, l’ancien profil POS1 doit rester en attente serveur et ne jamais louer la file, tandis que DSM1 reste actif. Une SIM physiquement absente doit toujours arrêter localement son profil Robot.
7. Depuis T3 Remote, lancez uniquement `TEST_NUMBER` pour POS1 : T2 doit louer et exécuter la commande ; T1 ne doit ni composer le test ni capturer la commande.
8. Répétez avec un deuxième `TEST_NUMBER` pour DSM1 : seul le slot 1 de T1 doit être utilisé.
9. Ne passez à une transaction de 1 FCFA qu’après dix alternances POS1/DSM1 sans erreur de SIM, de slot ou de nœud.
