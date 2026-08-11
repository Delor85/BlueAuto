# Protocole de test terrain — avant argent réel

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

## Test obligatoire de déplacement d’une SIM

1. Sur T1, liez POS1 au slot 2 et DSM1 au slot 1, puis démarrez les deux Robots.
2. Éteignez T1, retirez POS1 du slot 2 et insérez-la dans T2.
3. Sur T2, appairez POS1, sélectionnez son slot réel, confirmez **VÉRIFIER / LIER LA SIM**, puis démarrez le Robot.
4. Rallumez T1 : POS1 doit afficher **SIM BLOQUÉE / Robot ARRÊTÉ** tandis que DSM1 reste actif.
5. Depuis T3 Remote, lancez uniquement `TEST_NUMBER` pour POS1 : T2 doit louer et exécuter la commande ; T1 ne doit ni composer le test ni capturer la commande.
6. Répétez avec un deuxième `TEST_NUMBER` pour DSM1 : seul le slot 1 de T1 doit être utilisé.
7. Ne passez à une transaction de 1 FCFA qu’après dix alternances POS1/DSM1 sans erreur de SIM, de slot ou de nœud.
