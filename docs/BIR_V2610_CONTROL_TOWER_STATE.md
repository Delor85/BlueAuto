# B.I.R. / Blue Magic — état fonctionnel v2.6.10 — 2026-08-16

## Identité et règle de continuité

B.I.R. — **Blue Infinity Retail** — reste le nom commercial du même projet **Blue Magic**. Le package Android reste `com.profitloop.blueauto`. Toute évolution doit être additive : conserver Remote/Robot, multi-SIM, files, USSD, PIN, historiques, preuves, soldes, comptes, réseau, SAV, administration Camtel et les acquis terrain.

## Git

- dépôt : `Delor85/BlueAuto`
- branche : `feat/bir-v2-6-10-control-tower`
- ancrage métier validé : `ba02cb77583a94bcc0917a39c34c4b3fb950914a`
- HEAD propre après retrait des échafaudages CI : `3554cb77d5053d580c4b331f7473e73e72045b48`
- base terrain v2.6.9 : `94d3229e4a6569edc1570c3a59084afe314a06af`
- run complet de validation : `31947181283` — SUCCESS
- PR #4 historique v2.6.8 : doit rester OPEN / NON MERGED jusqu’à autorisation explicite distincte.

## Android v2.6.10

- package : `com.profitloop.blueauto`
- versionCode : `50`
- versionName : `2.6.10`
- minSdk : `23` (Android 6)
- targetSdk : `34`
- signature de livraison : clé permanente historique Blue Magic/B.I.R.
- empreinte certificat SHA-256 attendue : `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`
- APK Release permanente finale : `BIR-Blue-Infinity-Retail-v2.6.10-Control-Tower-Release.apk`
- SHA-256 APK : `629c00caeeaf10c128c0095aa319ad78a160f39363b9e66a6ace57a2d1161943`
- signatures vérifiées : V1=true, V2=true, V3=true.

## Acquis terrain à ne pas régresser

La v2.6.9 précédente a été installée par l’utilisateur sur ses trois téléphones Android 6 / Android 8 / Android 11. Le terrain a confirmé notamment que l’assistance de verrouillage simple/non sécurisé pouvait réveiller le scénario USSD et permettre l’insertion du PIN Camtel. Ne jamais remplacer ce mécanisme par une logique agressive ou un contournement d’un verrou sécurisé.

## Évolutions v2.6.10

### Tour de contrôle visible

- le bloc solde Camtel est remonté en haut pour être immédiatement visible ;
- le bloc Compte actif / Robot a un contraste renforcé et une densité réduite ;
- `ROBOT ARRÊTÉ` devient actionnable pour démarrer/reprendre le Robot ;
- `SIM NON VÉRIFIÉE` devient actionnable pour vérifier/lier la SIM ;
- accès immédiats à Autorisations / Robot / Batterie / Synchroniser ;
- les doublons correspondants sont retirés de l’interface visible du centre `GÉRER` afin de le désengorger ;
- le dock du bas reste visible pendant l’édition d’un formulaire : suppression fonctionnelle du comportement `.form-editing .module-tabs{display:none}` par surcharge v2.6.10 ;
- design toujours dérivé de la référence B.I.R. bleu nuit / cyan / or, mais sans retirer les fonctions Blue Magic.

### Hiérarchie et noms officiels

- DAE : enfant direct affiché/saisi comme DSM uniquement ;
- DSM : enfant direct affiché/saisi comme PoS uniquement ;
- PoS : supérieur direct = DSM ;
- DSM : supérieur direct = DAE ;
- l’interface privilégie les noms officiels généalogiques (`DSM1_SU1`, `POS1_DSM1_SU1`) lorsqu’elle dispose du parent ; les alias courts restent des facilités de contexte direct et ne doivent pas devenir des identifiants globaux.

### Commissions

- gestion visible du taux par défaut et des taux personnalisés par enfant via les API déjà prévues `commission_policy`, `commission_set_default`, `commission_set_child` ;
- demande d’achat `REQUEST_SUPPLY` : le demandeur voit que le taux est décidé par son supérieur et peut annuler/contacter ce supérieur ;
- approvisionnement proactif `SUPPLY_CHILD` : le supérieur n’est plus invité à “voir son supérieur” ; il valide le taux qu’il décide ;
- le supérieur peut modifier le taux dans la confirmation 1/2 pour ce seul envoi ; une modification déclenche une nouvelle prévisualisation/certification serveur avant création de la commande ;
- l’override ponctuel accepte 0 à 50 % et est marqué `TRANSACTION_OVERRIDE` ; il ne modifie pas le taux par défaut/persistant de l’enfant.

### Remote, preuves et solde enfant

- un bloc `RETOUR CAMTEL DISTANT` affiche le `result_message` d’une commande terminée pour les consultations de solde propre/enfant, cinq dernières transactions, détail de transaction et test numéro ;
- le Remote peut donc lire le retour Camtel produit par le Robot distant au lieu de recevoir seulement l’état `SUCCEEDED`.

### Synchronisation multi-compte

- nouvelle action `Synchroniser` / `ACTION_FORCE_SYNC` ;
- elle réveille immédiatement le Robot, efface les backoffs réseau par profil et relance le cycle de tous les profils ;
- le moteur peut réessayer jusqu’à quatre rapports finaux dus dans le même cycle au lieu d’un seul ;
- l’utilisateur ne doit plus avoir à fabriquer une transaction sur une autre SIM pour réveiller la première.

### Accessibilité / permanence Robot

- le Robot reste logique et `START_STICKY`/watchdog comme acquis ;
- l’application distingue permission Accessibilité activée et service effectivement connecté ;
- Android reste l’autorité qui accorde/révoque l’Accessibilité. B.I.R. ne peut et ne doit pas auto-octroyer cette permission ni contourner une révocation système ;
- en cas de perte, les commandes financières restent conservées et l’interface doit guider l’utilisateur via le bouton Autorisations, puis reprendre automatiquement après retour du service.

## Validation automatique v2.6.10

Run `31947181283` : SUCCESS complet.

Il couvre :
- tests Worker complets (catalogue Camtel, intelligence messages, intégration Remote/Robot, FIFO, soldes, concurrence atomique) ;
- tous les contrats Android historiques v2.6.7/v2.6.8/v2.6.9 ;
- nouveau contrat v2.6.10 Tour de contrôle ;
- vérification JS ;
- tests Java Android ;
- `assembleRelease` ;
- package/version/minSdk/non-debuggable ;
- création de l’APK Release candidate avant signature permanente.

Une erreur réelle de compilation a été détectée pendant le développement (duplication temporaire de `onInterrupt/onDestroy` dans AccessibilityService), corrigée avant le run vert en préservant les méthodes historiques. Les premiers échecs du cycle étaient uniquement des contrats de texte/navigation v2.6.8 devenus obsolètes.

## Production — NE PAS CONFONDRE AVEC LE LIVRABLE APK

La production serveur reste volontairement inchangée : **Worker v2.6.7 + D1 migration 0004**. La migration source `0005_commission_policies_and_financial_quotes.sql` n’est pas appliquée en production et le Worker v2.6.10 n’est pas déployé.

Conséquence : l’APK v2.6.10 peut être installée et les fonctions Android/Remote historiques continuent de viser la production actuelle, mais les nouvelles fonctions serveur de commissions v2.6.10 (taux persistants/override ponctuel) ne peuvent être déclarées opérationnelles en production tant que `0005` + Worker exact v2.6.10 n’ont pas reçu une autorisation de production séparée puis été déployés.

Ne jamais appliquer `0005`, déployer Worker v2.6.10 ou fusionner PR #4 sur la seule base de ce document.

## Procédure de terrain immédiate

1. Installer v2.6.10 par-dessus B.I.R./Blue Magic v2.6.9, sans désinstaller l’app.
2. Vérifier Android 6 / 8 / 11 : ouverture, dock permanent, compte/SIM, solde en haut.
3. Vérifier `ROBOT ARRÊTÉ` -> démarrage direct et `SIM NON VÉRIFIÉE` -> liaison directe.
4. Vérifier Autorisations / Batterie / Synchroniser.
5. Vérifier synchronisation de deux comptes/SIM sans fabriquer une autre transaction.
6. Vérifier consultation solde enfant depuis Remote et lecture du message Camtel obtenu.
7. Après autorisation et déploiement serveur 0005/Worker v2.6.10, vérifier commissions par défaut/personnalisées et override ponctuel dans confirmation 1/2.
8. Refaire un petit test financier réel et le scénario verrou simple déjà acquis, sans jamais tester de contournement d’un verrou sécurisé.

## Reprise obligatoire dans un autre chat

AVANT DE MODIFIER LE PROJET :

1. lire ce fichier ;
2. lire `docs/BIR_V269_FUNCTIONAL_STATE.md`, puis les documents de reprise v2.6.8 ;
3. vérifier en direct le HEAD de `feat/bir-v2-6-10-control-tower`, la PR #4 et les derniers Actions ;
4. considérer `ba02cb77583a94bcc0917a39c34c4b3fb950914a` comme l’ancrage métier v2.6.10 validé ;
5. ne pas réécrire/supprimer les acquis v2.6.9 ;
6. ne pas toucher à production sans autorisation explicite distincte ;
7. ne jamais exposer la clé/signature permanente ni ses secrets.
