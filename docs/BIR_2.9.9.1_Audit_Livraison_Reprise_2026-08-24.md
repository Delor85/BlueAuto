# B.I.R. 2.9.9.1 — Audit, livraison et reprise — 24 août 2026

## Source de vérité et périmètre
Ordre de vérification obligatoire : GitHub → GitHub Actions → Cloudflare/D1 → branches/commits/PR → APK/artefacts → conversations précédentes en contexte uniquement.

Base applicative 2.9.9 figée : `a13bafc76aa23157bb409a72904f4bc64f5cf815`.
Branche corrective : `fix/bir-v2-9-9-1-field-runtime`.
PR : #71, Draft, non fusionnée.
Identité cible : `com.profitloop.blueauto`, versionName `2.9.9.1`, versionCode `65`, minSdk 23, targetSdk 34.

## Corrections 2.9.9.1
1. Achat DAE/DSM/POS : traitement visuel vert distinct.
2. Multi-Remote : plusieurs appareils REMOTE d'un même compte relisent la vérité serveur et déclenchent une convergence événementielle bornée, sans créer un second Robot ni un second polling permanent.
3. Commissions : dashboard Réseau avec taux habituel, taux personnalisés et taux ponctuels inférés à partir de `transaction_ledger` comparé à `commission_policy` existant.
4. Android 11/API30 : mode de rendu ciblé réduisant animations, blur/backdrop, compositing, transforms/sticky/fixed et ajoutant un repaint borné après interaction/reprise.
5. Assistant B.I.R. : compréhension locale élargie + fallback `ops_assist`; aucune transaction financière n'est exécutée par l'Assistant.
6. CI : correction du défaut historique où le chemin APK disparaissait avant `adb install`; la qualification réutilise l'APK exacte.

## Invariants anti-régression
- moteur financier, préflight, double confirmation, FIFO et idempotence : inchangés ;
- PIN et Accessibilité : inchangés ;
- dual-SIM et attribution SIM : inchangés ;
- un seul Robot actif par compte ;
- REMOTE_SNAPSHOT_MS = 10 s conservé ;
- pas de boucle `setInterval` supplémentaire ;
- aucun changement du dossier `cloudflare/` depuis la base applicative ;
- aucune migration D1 ;
- aucune fusion de PR ;
- certificat permanent historique obligatoire : SHA-256 `f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5`.

## État de validation
Les contrats historiques et le nouveau contrat 2.9.9.1 ont déjà été exécutés avec succès dans la chaîne de validation intermédiaire avant l'étape de signature. Le défaut de signature Actions identifié est l'absence des secrets permanents dans GitHub Actions, pas une erreur de l'application.

Un gate critique Android 6/API23, Android 8/API26 et Android 11/API30 est attaché au code 2.9.9.1 et doit installer/interagir avec la même candidate avant livraison. Au moment de cette sauvegarde, les runs correspondants sont encore en file GitHub Actions (`queued`). Une APK permanente ne doit donc pas être déclarée livrée avant leur conclusion SUCCESS.

## Signature permanente
La clé permanente est conservée hors GitHub conformément à `SIGNING-RECOVERY.txt` : fichier `BlueMagic-permanent-release.keystore`, alias `androiddebugkey`, PKCS12, mot de passe séparé. Ne jamais publier la clé ni le mot de passe dans GitHub, Actions, e-mail ou dépôt public.

Procédure de livraison :
1. récupérer l'APK qualification exacte ayant passé le gate Android ;
2. re-signer localement ce payload avec la clé permanente historique ;
3. vérifier v1/v2/v3, un seul signataire, certificat SHA-256 historique, package/version/minSdk/targetSdk et zipalign ;
4. comparer toutes les entrées applicatives non-signature entre candidate testée et APK permanente ;
5. calculer SHA-256 final ;
6. archiver APK + SHA-256 + rapport de vérification.

## Production
Aucune mutation de production n'est autorisée ni effectuée par cette correction. Le dernier état de production durablement documenté demeure Worker `2.9.2-cloudflare`, D1 online. Une vérification directe du compte Cloudflare doit précéder toute future mutation. Aucun déploiement Worker ni migration D1 n'est requis pour les corrections 2.9.9.1 actuellement codées.

## Tests terrain obligatoires après APK permanente
- mise à jour par-dessus la version permanente existante, sans désinstallation ;
- Android 6, Android 8 et Android 11 réels ;
- DSM1 et POS1 ;
- soldes réels parent/enfant, en vérifiant qu'un solde enfant ne remplace jamais le solde propre du parent ;
- deux téléphones REMOTE du même compte : transaction/rafraîchissement depuis l'un, convergence rapide sur l'autre ;
- dashboard commissions : défaut, personnalisés, ponctuels ;
- Android 11 : taps répétés, scroll, sortie/reprise, absence de gel/écran bleu/blanc/capture blanche en bas Accueil ;
- Assistant : `IA`, question libre, réseau, solde, commission, incident Android, finance ; réponse pertinente mais aucune exécution financière directe par l'Assistant.

## ÉTAT DU PROJET APRÈS CETTE ÉTAPE
- Version : B.I.R. 2.9.9.1 / vc65
- Base applicative : `a13bafc76aa23157bb409a72904f4bc64f5cf815`
- Branche : `fix/bir-v2-9-9-1-field-runtime`
- PR : #71 Draft / OPEN / NON FUSIONNÉE
- Problèmes traités : Achat couleur ; multi-Remote ; dashboard commissions ; Android 11 ; Assistant ; CI Android
- Cloudflare : aucune mutation
- D1 : aucune migration
- APK : qualification/permanente non déclarée tant que gate Android exact n'est pas SUCCESS
- Régression possible : aucune régression métier démontrée par les contrats ; validation runtime Android exacte encore requise
- Autorisation nécessaire : OUI avant toute fusion PR, déploiement Worker ou migration D1 ; NON pour terminer la qualification/signature/livraison APK demandée

## AVANT DE MODIFIER LE PROJET
1. Lire ce fichier et le dernier `PROJECT_STATE` / document de reprise disponible.
2. Vérifier GitHub puis Actions puis Cloudflare/D1 puis commits/PR puis APK.
3. Ne jamais repartir d'un ancien chat comme source principale.
4. Ne pas modifier le moteur financier, FIFO/idempotence, PIN, Accessibilité, dual-SIM, Robot unique, polling 10 s ou certificat permanent sans justification et tests spécifiques.
5. Ne jamais considérer une APK éphémère comme une mise à jour permanente.

## Procédure obligatoire de clôture, sauvegarde et reprise
À chaque clôture :
1. enregistrer le SHA applicatif exact et le HEAD documentaire ;
2. enregistrer branche, PR, état merge, runs Actions et conclusions ;
3. enregistrer état Worker/D1 et préciser explicitement s'ils ont été modifiés ;
4. archiver APK permanente, SHA-256 et vérification de signature ;
5. conserver keystore et mot de passe séparés et hors GitHub ;
6. mettre à jour ce document de reprise et les fichiers d'état du dépôt ;
7. au nouveau chat, commencer par un audit en lecture seule selon l'ordre de vérité ;
8. une demande vague comme « continue » n'autorise jamais merge, Worker ou D1.

### Prompt de reprise recommandé
`BLUE MAGIC / B.I.R. — REPRISE 2.9.9.1. Vérifier dans cet ordre : GitHub → Actions → Cloudflare/D1 → commits/PR → APK → anciens chats. Lire docs/BIR_2.9.9.1_Audit_Livraison_Reprise_2026-08-24.md. Branche fix/bir-v2-9-9-1-field-runtime, PR #71 Draft/non fusionnée, base applicative a13bafc76aa23157bb409a72904f4bc64f5cf815, version 2.9.9.1 vc65. Ne rien fusionner ni déployer sans autorisation explicite. Reprendre d'abord par la conclusion des gates Android exacts, puis signer localement l'APK candidate exacte avec le certificat historique f51e1d84… et livrer APK+SHA+rapport ; ensuite seulement tests terrain Android 6/8/11, DSM1/POS1, multi-Remote et soldes réels.`
