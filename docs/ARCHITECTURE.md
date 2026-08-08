# Architecture du noyau Robot Blue Magic v2

## Décision centrale

Le serveur transporte une intention métier (`REQUEST_SUPPLY`, `SUPPLY_CHILD`, `RETAIL_SALE`) et non un code USSD libre. Il résout les numéros autorisés dans la hiérarchie. Le Robot recalcule ensuite localement la commande avant de la composer.

```mermaid
sequenceDiagram
    participant T2 as Télécommande
    participant API as API PHP/MySQL
    participant T1 as Robot Android
    participant MMI as Téléphone / Camtel
    T2->>API: Créer ordre + clé anti-doublon
    API-->>T2: ID public / PENDING
    T1->>API: Louer le plus ancien ordre
    API-->>T1: Paramètres + lease temporaire
    T1->>MMI: *550*2*numéro*montant#
    MMI-->>T1: Confirmer numéro/montant + demander PIN
    T1->>T1: Vérifier écran, déchiffrer PIN local
    T1->>MMI: PIN + ENVOYER
    MMI-->>T1: Résultat flash ou SMS
    T1->>API: SUCCEEDED / FAILED / UNKNOWN / BLOCKED
    API-->>T2: Statut et ID Camtel
```

## Barrières anti-erreur

1. **Hiérarchie serveur** : un DSM ne peut demander qu’à son DAE enregistré; un PoS ne peut demander qu’à son DSM.
2. **Pas d’USSD arbitraire** : seules trois opérations sont admises dans ce noyau.
3. **Idempotence** : une double pression sur le bouton avec la même clé ne crée pas deux ordres.
4. **Lease** : un seul Robot peut réserver un ordre pendant 120 secondes.
5. **Recalcul local** : l’application refuse un `ussd_code` serveur incohérent avec les champs signés.
6. **Vérification du pop-up** : le PIN n’est injecté que si le texte contient le numéro à 9 chiffres et le montant attendus.
7. **Pas de retry financier aveugle** : après composition, un résultat manquant passe à `UNKNOWN`.
8. **Coupe-circuit PIN** : `Wrong PIN code` arrête le Robot dès la première occurrence.

## Consommation réseau et batterie

- location de commande toutes les 8 secondes lorsque le Robot est disponible ;
- heartbeat toutes les 60 secondes ;
- retour exponentiel jusqu’à 60 secondes après erreur réseau ;
- aucun ping JavaScript toutes les 4 secondes ;
- WakeLock partiel uniquement pendant une transaction, limité à 135 secondes ;
- notification permanente lorsque le mode Robot est actif.

## Compatibilité

- Android 6 à 7 : `ACTION_CALL` + service d’accessibilité ;
- Android 8 et plus : même chemin pour conserver une session interactive visible et contrôlable ;
- Android 5 : volontairement exclu de cette première version robuste, car le stockage AES/GCM du PIN dans Android Keystore est garanti à partir d’Android 6 ;
- téléphone Robot recommandé : une seule SIM, pas de verrouillage écran sécurisé, chargeur permanent, optimisation batterie désactivée.

## Pourquoi pas `sendUssdRequest()` seul ?

L’API, ajoutée au niveau 26, renvoie une réponse ou un échec à une requête USSD. Elle n’expose pas de méthode publique documentée permettant d’envoyer la réponse suivante dans la même session interactive. La fenêtre Camtel montrée dans le cahier des charges exige donc l’automatisation contrôlée du dialogue système.
