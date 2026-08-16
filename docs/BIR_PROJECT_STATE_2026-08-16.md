# B.I.R. — état de reprise 2026-08-16

## Marque et design retenus

- **B.I.R. = Blue Infinity Retail**
- Signature de travail : **Rapide. Puissant. Infini.**
- B.I.R. devient la marque visible ; **Blue Magic Engine** reste provisoirement le nom technique du moteur.
- Design choisi : bleu nuit/électrique + blanc lumineux + or premium.
- Logo : infini légèrement incliné, **B bleu dans la boucle gauche, R dans la boucle droite, I central distinct**.
- Bouton central : **∞ doré, brillant et lumineux**, jamais l’éclair pour Piloter/Fournir/Vendre.
- Textes secondaires agrandis pour les petits terminaux.
- Aucun produit ni catalogue du concurrent n’est intégré.

## Branche UX

- Branche : `experiment/bir-full-ux`
- Commit ayant déclenché le premier APK installable : `99d5e3702571f91c86aa03393849f3f39c578ac5`
- Workflow : `BIR Preview APK`
- Run : `31921511805` — **SUCCESS**

## APK preview

- `BIR-Blue-Infinity-Retail-Preview-v2.6.9.apk`
- applicationId : `com.profitloop.birpreview`
- versionName : `2.6.9-bir-preview.1`
- versionCode : `49`
- SHA-256 : `de4147d42c3a2ec66acdf44e7e998af7d27961de07486fb27bc1b03b315a9046`
- Signature : éphémère de preview ; ne pas confondre avec la signature permanente Blue Magic.
- Peut coexister avec Blue Magic car le package est séparé.
- La preview B.I.R. n’envoie aucun USSD depuis son interface de démonstration et B.I.R. Pay est totalement inactif.
- Dans Gérer, un bouton ouvre le Blue Magic Engine v2.6.8 embarqué dans le package preview ; sa configuration est séparée de l’application Blue Magic installée.

## Moteur fonctionnel à préserver

- Branche : `fix/blue-magic-v2-6-recovery`
- HEAD de référence : `7f15fb7cb6e8112e4076cadbad6f5b784a010847`
- PR #4 : **OPEN / NON MERGED**
- Dernier build propre : `31914976939` SUCCESS
- Production : dernier ancrage v2.6.7 vérifié
- D1 `0005` : NON appliquée
- Worker 2.6.8 : NON déployé
- APK permanente 2.6.8 : NON publiée

## Cahier des charges

Le redesign B.I.R. ne supprime aucun besoin historique. Toute intégration réelle doit préserver DAE/DSM/PoS, Remote/Robot, multi-SIM, files et reprise, achats/approvisionnements/ventes, commissions, soldes/preuves, chronologie opérateur, commandes directes non financières, finance avec PIN/Accessibilité, verrou simple borné, verrou sécurisé jamais contourné, administration, activité, SAV, diagnostic et croissance du réseau.

## Paiement

B.I.R. Pay reste uniquement : `Intention → Routeur → Adaptateurs → Statut → Rapprochement`.

Aucun connecteur, aucune clé API, aucun débit et aucun contournement opérateur ne doivent être activés sans étape et autorisation distinctes.

## Reprise obligatoire

Avant toute mutation :

1. lire `/Blue Magic/BIR-REPRISE-OBLIGATOIRE-2026-08-16.md` dans la bibliothèque ;
2. lire `docs/PROJECT_STATE_V268_FINAL.md` ;
3. lire `docs/PROJECT_STATE.md` ;
4. lire `docs/PROCEDURE_REPRISE_EXTERNE.md` ;
5. lire `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md` ;
6. vérifier en direct les deux branches et PR #4 ;
7. ne jamais reconstruire le projet depuis les chats.

## Interdictions

- ne pas fusionner PR #4 sans autorisation explicite ;
- ne pas appliquer D1 `0005` sans autorisation ;
- ne pas déployer Worker 2.6.8 sans autorisation ;
- ne pas publier avec la signature permanente sans autorisation bornée au SHA exact ;
- ne pas faire disparaître des fonctions du cahier au nom du nouveau design ;
- ne pas rendre B.I.R. Pay opérationnel à ce stade.
