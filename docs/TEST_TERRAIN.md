# Protocole de test terrain — avant argent réel

## Gate A — Serveur

- `api.php?action=health` renvoie du JSON, jamais une page HTML ;
- le Robot s’appaire et reçoit un jeton ;
- deux pressions rapides sur une demande n’entraînent qu’une commande avec la même clé ;
- une Télécommande ne peut pas créer un ordre pour un nœud hors de sa hiérarchie.

## Gate B — Téléphone Robot

- autorisation Téléphone accordée ;
- Accessibilité Blue Magic active ;
- superposition active ;
- batterie sans restriction ;
- une seule SIM ou SIM Blue choisie comme SIM d’appel par défaut ;
- aucun écran de verrouillage sécurisé ;
- notification Robot permanente ;
- test `*825*3*3#` lancé à distance.

## Gate C — Confirmation PIN

Effectuer d’abord une transaction manuelle minimale et noter le texte exact du pop-up.

- le pop-up expose un `EditText` à l’accessibilité ;
- le texte contient le numéro destinataire à 9 chiffres ;
- le texte contient le montant en FCFA ;
- le bouton porte un libellé reconnu : `ENVOYER`, `SEND`, `CONFIRMER`, `VALIDER` ou `OK` ;
- Blue Magic remplit le PIN seulement lorsque numéro et montant correspondent ;
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
| Rien ne s’ouvre sur T1 | démarrage d’activité en arrière-plan bloqué | accorder superposition, garder Blue Magic visible, retirer verrouillage écran |
| `PIN_FIELD_NOT_FOUND` | application Téléphone du fabricant masque le champ | tester un autre modèle/téléphone ou adapter les sélecteurs à ce modèle |
| `CONFIRM_BUTTON_NOT_FOUND` | libellé/bouton OEM non reconnu | relever le texte exact et l’identifiant d’accessibilité |
| `CONFIRMATION_MISMATCH` | numéro/montant formaté différemment ou réellement faux | ne pas forcer; capturer le pop-up et adapter le parseur |
| `WRONG_PIN` | PIN local erroné | arrêter, vérifier manuellement, enregistrer le bon PIN; aucune répétition |
| `UNKNOWN` | transfert possiblement exécuté sans preuve captée | vérifier solde et cinq dernières transactions avant toute nouvelle tentative |

## Critère de passage en production

Le même modèle de téléphone, la même version Android, la même application Téléphone et la même SIM doivent réussir au moins 30 transactions minimales consécutives, y compris un test réseau lent et un redémarrage. Tant que ce seuil n’est pas atteint, le système reste un pilote supervisé.
