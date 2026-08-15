from pathlib import Path


def read(path): return Path(path).read_text()
def write(path, text): Path(path).write_text(text)
def one(text, old, new, label):
    if old not in text:
        raise SystemExit('missing patch anchor: ' + label)
    return text.replace(old, new, 1)

# 1) Align Cloudflare package metadata with source API version.
for path in ['cloudflare/package.json', 'cloudflare/package-lock.json']:
    s = read(path)
    s = s.replace('"version": "2.6.7"', '"version": "2.6.8"')
    write(path, s)

# 2) Replace stale README with a concise source-of-truth overview.
readme = r'''# Blue Magic v2.6.8 — stabilisation terrain, commissions et interface adaptative

Blue Magic automatise la distribution Blue/Camtel selon le trajet sécurisé **Remote → Worker/D1 → Robot détenteur de la SIM → USSD → preuve opérateur**. La branche de développement actuelle prépare `2.6.8` (`versionCode 48`, `minSdk 23`, `targetSdk 34`) sans modifier la production tant que la validation terrain et une nouvelle autorisation explicite n’ont pas été données.

> **Production réellement active :** Worker `2.6.7-cloudflare`, D1 migrée jusqu’à `0004`, APK permanente v2.6.7.  
> **Développement :** v2.6.8 sur `fix/blue-magic-v2-6-recovery`, PR #4 ouverte/non fusionnée, migration additive `0005` présente dans les sources mais **non appliquée en production**.

## Noyau financier à préserver

- Chaque SIM Blue/Camtel est liée à son profil et à son slot physique.
- Un téléphone physique n’exécute qu’une session USSD à la fois.
- Les commandes financières sont prévisualisées puis confirmées par l’utilisateur avant création de la réservation D1.
- Le précontrôle de capacité est une **cotation seulement** : il ne réserve et ne déduit aucun FCFA. La réservation devient réelle uniquement à la création de la commande confirmée.
- La création finale garde une vérification atomique de capacité afin d’empêcher deux commandes concurrentes de dépenser le même stock.
- Un résultat incertain devient `UNKNOWN` et n’est jamais rejoué automatiquement.
- Le PIN Camtel reste local au téléphone, chiffré, absent du Worker, de D1 et du JavaScript.

## Commandes Camtel

Le catalogue opérateur est centralisé dans :

- Android : `app/src/main/java/com/profitloop/blueauto/CamtelUssdCatalog.java` ;
- Worker : `cloudflare/src/camtel-catalog.mjs` ;
- documentation : `docs/CAMTEL_OPERATOR_CATALOG.md`.

Les commandes non financières qui embarquent déjà le PIN local — solde, cinq dernières transactions, détail, solde enfant et administration — sont des USSD directs et **ne dépendent pas de l’Accessibilité**. Les transferts financiers restent interactifs et utilisent l’Accessibilité pour la fenêtre PIN Camtel.

## Solde vivant et preuves

`Solde Camtel` représente le dernier solde canonique connu pour **ce nœud**, jamais la somme de sa sous-arborescence. `Réservé après confirmation` représente les commandes financières confirmées encore non terminales. `Disponible = Solde Camtel - Réservé`.

La chronologie opérateur prévaut sur la priorité d’une source : un SMS ancien arrivé en retard ne peut pas faire régresser une preuve plus récente. Pour une décision financière, une preuve exacte peut être réutilisée jusqu’à **1 heure** uniquement en l’absence d’activité financière non rapprochée postérieure. Pour un rapport, une preuve exacte peut rester exploitable jusqu’à **14 heures** dans la même condition.

## Commissions v2.6.8

La migration source `0005_commission_policies_and_financial_quotes.sql` introduit :

- DAE → DSM : taux par défaut 10 % (`1000 bps`) et surcharge possible par DSM ;
- DSM → PoS : taux par défaut 8 % (`800 bps`) et surcharge possible par PoS ;
- mémorisation du montant de base, du taux et de la commission dans la cotation/commande ;
- confirmation 1/2 affichant **base + commission = total réellement transféré** ;
- calcul entier du montant de base maximal compatible avec le solde disponible ;
- empreinte de confirmation incluant le taux afin qu’un changement de commission invalide une ancienne confirmation.

Les vues DAE/DSM peuvent décomposer un solde réel Camtel en stock de base + composante de commission selon le taux par défaut. Il s’agit d’une vue comptable dérivée, pas de trois comptes Camtel séparés.

## Navigation et ergonomie adaptatives

Blue Magic garde les modules fonctionnels Rapports, Flotte/Réseau, Flux, Robot et SAV, mais leur présentation est adaptée au rôle :

- **DAE :** Pilotage, Réseau, Flux, Robot, SAV ;
- **DSM :** Soldes, Réseau, Flux, Robot, SAV ;
- **PoS :** Solde, Vente, Robot, Aide — la Flotte administrative est masquée.

Le panneau natif **GÉRER** est un centre de gestion défilable et responsive. Il utilise deux colonnes compactes lorsque la largeur le permet et repasse à une colonne sur les écrans très étroits. Les modules avancés sont repliables et exposés seulement aux rôles concernés.

Les vieux WebView Android restent pris en charge : l’extension plateforme n’emploie plus les syntaxes JavaScript modernes susceptibles de casser Android 6. Les petits écrans utilisent aussi un rendu visuel allégé (moins d’animation, de flou et d’ombres).

## Fluidité Remote ↔ Robot / multi-SIM

Le polling applicatif n’est plus exécuté aveuglément :

- les commandes sont interrogées seulement lorsqu’elles sont non terminales et que l’application est visible ;
- le tableau de bord est actualisé seulement dans les écrans où il est utile ;
- les appels de contrôle retry-safe (`heartbeat`, `lease_command`, `command_status`, tableau de bord) ont des délais réseau plus courts que les opérations transactionnelles ;
- un profil dont la route réseau ralentit est temporairement différé localement afin que les autres SIM/profils du téléphone continuent leur file ;
- la fréquence de base n’est pas augmentée inutilement, afin de préserver batterie et réseau.

## Verrou Android et Accessibilité

Blue Magic ne contourne jamais un PIN, schéma, mot de passe ou verrou biométrique. Sous verrou sécurisé, la commande reste/revient en file et un déverrouillage humain est requis.

Pour un simple verrou sans identifiant, une activité transparente peut faire **une tentative courte et bornée** au moment précis où une commande attend. Un cooldown empêche les boucles qui faisaient trembler certains téléphones. En cas d’échec, Blue Magic renonce à forcer l’écran et demande un déverrouillage humain.

Android conserve l’autorité sur l’activation de l’AccessibilityService : Blue Magic peut garder le Robot logiquement actif, surveiller/reprendre la file et guider l’utilisateur, mais ne peut pas s’auto-accorder silencieusement cette autorisation.

## Rôles et périmètres

La nomenclature canonique Camtel reste :

- DAE : `XXY` (`OU3`, `CE04`, `LT10`) ;
- DSM : `DSMZ_XXY` (`DSM7_OU3`) ;
- PoS : `POSA_DSMZ_XXY` (`POS16_DSM7_OU3`).

Le DAE voit sa propre pyramide ; un DSM voit son compte et ses PoS directs ; un PoS voit son propre compte. Les activités et soldes suivent le même périmètre. Les alias courts ne sont résolus que dans le contexte hiérarchique qui les rend non ambigus.

## CI et livraison

Les tests permanents couvrent le Worker/D1, les règles financières historiques, les contrats v2.6.8, la syntaxe WebView, les tests unitaires Java et un vrai `assembleRelease`.

Un build CI ordinaire doit utiliser une signature **éphémère**. Les secrets de signature permanente restent confinés au job `production`. Une future publication permanente v2.6.8 ne doit être possible qu’après une autorisation explicite visant un SHA exact, puis un lancement manuel avec le garde correspondant. Une compilation de validation n’est jamais une autorisation de production.

## Points de reprise

- état détaillé : `docs/PROJECT_STATE.md` ;
- procédure obligatoire : `docs/BLUE_MAGIC_DELIVERY_PROCEDURE.md` et `docs/PROCEDURE_REPRISE_EXTERNE.md` ;
- tests terrain : `docs/TEST_TERRAIN.md` ;
- catalogue opérateur : `docs/CAMTEL_OPERATOR_CATALOG.md`.

**Ne pas fusionner PR #4, ne pas appliquer `0005`, ne pas déployer Worker 2.6.8 et ne pas publier d’APK permanente v2.6.8 avant validation terrain et autorisation explicite séparée.**
'''
write('README.md', readme)

# 3) Prepend current v2.6.8 state without erasing history.
p = 'docs/PROJECT_STATE.md'
s = read(p)
if '# ÉTAT COURANT — v2.6.8' not in s:
    current = r'''# ÉTAT COURANT — v2.6.8 STABILISATION / PRODUCTION v2.6.7 INCHANGÉE

Mise à jour de reprise : 15 août 2026. Cette section est prioritaire sur les états historiques conservés plus bas.

## A. Références actuelles

- Dépôt : `Delor85/BlueAuto`
- Branche : `fix/blue-magic-v2-6-recovery`
- PR : `#4`, ouverte et **non fusionnée**
- Android source : `2.6.8`, `versionCode 48`, `minSdk 23`, `targetSdk 34`
- Worker source : `2.6.8-cloudflare`
- Migration source additive : `0005_commission_policies_and_financial_quotes.sql`
- Production réellement active : Worker `2.6.7-cloudflare`, version Cloudflare `83bc2dd7-e28c-41f2-88f9-710c1b9dd649`, D1 migrée jusqu’à `0004`, APK permanente v2.6.7
- Migration `0005` : **NON APPLIQUÉE EN PRODUCTION**
- Worker 2.6.8 : **NON DÉPLOYÉ EN PRODUCTION**
- APK permanente 2.6.8 : **NON PUBLIÉE**

## B. Acquis v2.6.8

- précontrôle d’approvisionnement transformé en cotation sans réservation ; seule la commande financière confirmée réserve réellement la capacité ;
- commission DAE→DSM par défaut 10 % et DSM→PoS 8 %, avec surcharge par enfant et total base+commission ;
- suppression du « Solde cumulé connu » ; séparation Solde Camtel / Réservé après confirmation / Disponible ;
- périmètres DAE/DSM/PoS bornés à leur branche ;
- rafraîchissement intelligent et réutilisation des preuves exactes : finance 1 h, rapport 14 h sous condition d’absence de mouvement non rapproché ;
- commandes non financières directes avec PIN local, sans dépendance Accessibilité ;
- perte d’Accessibilité : une finance non composée doit rester/revenir en file plutôt que d’être consommée ;
- verrou sécurisé : aucun contournement ; verrou simple : assistance transparente, ponctuelle, bornée et avec cooldown, puis déverrouillage humain si nécessaire ;
- Centre GÉRER responsive ; navigation adaptée au rôle ; affichage allégé sur petit écran ; extension plateforme compatible vieux WebView ;
- saisie transactionnelle optimisée : claviers numériques, normalisation, focus erreur, anti-double action et nettoyage uniquement après création réussie ;
- polling UI adaptatif et suspendu en arrière-plan ;
- contrôle Remote↔Robot multi-SIM : timeouts courts seulement pour le plan de contrôle et isolement temporaire d’un profil réseau lent afin de ne pas bloquer les autres SIM ;
- bandeau natif compact : un Remote ne réclame plus SIM/Accessibilité ; un Robot n’affiche une deuxième ligne que lorsqu’une action est requise.

## C. Jalons de validation source

- `02e15878305a45e3126c7109666f32f132decf29` — stabilisation finance/Robot + GÉRER responsive ;
- `2ef2055e17a53b0a269f07903e5946dfc61d86d4` — baseline Java/tests/assembleRelease vert ;
- `ece06e793c590fe79d5fe18124b3ed864e1ada80` — navigation/polling adaptatifs ;
- `ee5bf4955cc55b4bed9ab9a5cbac239df05e737f` — compatibilité extension plateforme Android 6 ;
- `47b024ff8dbe7244c8037ddc24e2fb75a72522b3` — ergonomie transactionnelle ;
- `71d2ea762e531f76e97fc8386283d08e06bd4033` — résilience Remote↔Robot / profils réseau lents ;
- `46821fcc27b9c2fd153f2e977d6c3b92076f666b` — bandeau natif compact.

Chaque lot ci-dessus a été validé avec les contrats Worker/historiques/v2.6.8, les tests unitaires Android et un vrai `assembleRelease` avant persistance.

## D. Interdictions de reprise

- ne pas fusionner PR #4 avant validation terrain et autorisation explicite ;
- ne pas appliquer `0005` ni déployer Worker 2.6.8 sans nouvelle autorisation de production ;
- ne pas publier d’APK permanente v2.6.8 à partir d’une simple compilation CI ;
- ne pas réintroduire `disableKeyguard()`, le contournement d’un verrou sécurisé, la réservation au préflight ou le solde agrégé de sous-arbre ;
- ne pas faire dépendre les commandes directes avec PIN local de l’Accessibilité ;
- ne pas réécrire le cœur Remote → Worker/D1 → Robot → USSD déjà validé terrain.

## E. Prochaine étape terrain

Après production autorisée et livraison future : tester Android 6, 8 et 11 réels ; TEST_NUMBER ; verrou simple ; perte/réactivation Accessibilité ; Remote→Robot ; files multi-SIM ; solde propre/enfant/historique/détail ; DAE→DSM à 10 % et surcharge ; DSM→PoS à 8 % et surcharge ; PoS→client ; concurrence de deux commandes ; rafraîchissement soldes/activités ; annulation et reprise après verrouillage/redémarrage.

---

# HISTORIQUE CONSERVÉ

'''
    s = current + s
write(p, s)

# 4) Harden the normal/permanent Android delivery workflow.
p = '.github/workflows/build.yml'
s = read(p)
s = one(s, '''  workflow_dispatch:\n''', '''  workflow_dispatch:\n    inputs:\n      publish_permanent:\n        description: "Publier l’APK permanente du SHA explicitement autorisé"\n        required: true\n        type: boolean\n        default: false\n      authorized_sha:\n        description: "SHA Git 40 caractères explicitement autorisé pour la publication permanente"\n        required: false\n        type: string\n        default: ""\n''', 'workflow dispatch guards')

start = s.index('      - name: Préparer et contrôler la signature Android\n')
end = s.index('      - name: Tester et compiler le vrai APK Release\n', start)
ephemeral = '''      - name: Préparer une signature éphémère de validation\n        run: |\n          set -euo pipefail\n          mkdir -p .pilot-signing\n          openssl rand -hex 32 > .pilot-signing/keystore.password\n          pilot_password="$(tr -d '\\r\\n' < .pilot-signing/keystore.password)"\n          echo "::add-mask::$pilot_password"\n          keytool -genkeypair \\\n            -keystore .pilot-signing/debug.keystore \\\n            -storepass "$pilot_password" \\\n            -alias androiddebugkey \\\n            -keypass "$pilot_password" \\\n            -dname "CN=Blue Magic CI Validation,O=ProfitLoop,C=CM" \\\n            -keyalg RSA -keysize 2048 -validity 30 -noprompt\n          echo "BLUE_MAGIC_PILOT_KEYSTORE_PASSWORD=$pilot_password" >> "$GITHUB_ENV"\n          echo "BLUE_MAGIC_SIGNING_KIND=temporary" >> "$GITHUB_ENV"\n\n'''
s = s[:start] + ephemeral + s[end:]

old_test = '''      - name: Tester et compiler le vrai APK Release\n        run: |\n          node app/src/test/finance-flow.mjs\n          gradle --no-daemon :app:testDebugUnitTest :app:assembleRelease\n'''
new_test = '''      - name: Tester et compiler le vrai APK Release\n        run: |\n          set -euo pipefail\n          node app/src/test/finance-flow.mjs\n          node app/src/test/v268-field-contract.mjs\n          node app/src/test/v268-responsive-management.mjs\n          node app/src/test/v268-ux-performance.mjs\n          node app/src/test/v268-platform-compat.mjs\n          node app/src/test/v268-transaction-ux.mjs\n          node app/src/test/v268-control-plane.mjs\n          node app/src/test/v268-native-status.mjs\n          node --check app/src/main/assets/app.js\n          node --check app/src/main/assets/platform-v267.js\n          gradle --no-daemon :app:testDebugUnitTest :app:assembleRelease\n'''
s = one(s, old_test, new_test, 'normal regression suite')

old_condition = "${{ github.event_name == 'workflow_dispatch' || (github.event_name == 'push' && github.event.head_commit.message == 'release: authorized Blue Magic v2.6.7 permanent APK once') }}"
new_condition = "${{ github.event_name == 'workflow_dispatch' && inputs.publish_permanent == true && inputs.authorized_sha == github.sha }}"
if old_condition not in s:
    raise SystemExit('permanent release condition missing')
s = s.replace(old_condition, new_condition)

checkout_anchor = '''      - name: Récupérer le code\n        uses: actions/checkout@v5\n\n      - name: Installer Java 17\n'''
# Only add SHA verification to first occurrence AFTER android-permanent-apk.
perm = s.index('  android-permanent-apk:')
idx = s.index(checkout_anchor, perm)
replacement = '''      - name: Récupérer le code\n        uses: actions/checkout@v5\n\n      - name: Vérifier le SHA explicitement autorisé\n        run: |\n          set -euo pipefail\n          test "${{ inputs.authorized_sha }}" = "$(git rev-parse HEAD)"\n          test "$(git rev-parse HEAD)" = "${{ github.sha }}"\n\n      - name: Installer Java 17\n'''
s = s[:idx] + s[idx:].replace(checkout_anchor, replacement, 1)

s = s.replace('Blue-Magic-v2.6.7-Plateforme-Solde-Release.apk', 'Blue-Magic-v2.6.8-Stabilisation-Ergonomie-Release.apk')
s = s.replace('/tmp/blue-magic-v267-final', '/tmp/blue-magic-v268-final')
s = s.replace('/tmp/blue-magic-v267.sha256', '/tmp/blue-magic-v268.sha256')
s = s.replace('android-upgrade-v265-to-v267:', 'android-upgrade-v265-to-v268:')
s = s.replace('/tmp/v267-', '/tmp/v268-')
s = s.replace('versionName=2.6.7', 'versionName=2.6.8')
write(p, s)

# 5) Add a static workflow safety contract.
contract = r'''import fs from 'node:fs';
const build=fs.readFileSync('.github/workflows/build.yml','utf8');
const pkg=JSON.parse(fs.readFileSync('cloudflare/package.json','utf8'));
const lock=JSON.parse(fs.readFileSync('cloudflare/package-lock.json','utf8'));
if(pkg.version!=='2.6.8') throw new Error('Cloudflare package version not 2.6.8');
if(lock.version!=='2.6.8'||(lock.packages&&lock.packages['']&&lock.packages[''].version!=='2.6.8')) throw new Error('Cloudflare lock root version not 2.6.8');
for(const required of ['publish_permanent','authorized_sha','inputs.authorized_sha == github.sha','Préparer une signature éphémère de validation','v268-native-status.mjs','Blue-Magic-v2.6.8-Stabilisation-Ergonomie-Release.apk','versionName=2.6.8']){
  if(!build.includes(required)) throw new Error('release hygiene missing: '+required);
}
if(build.includes("github.event_name == 'workflow_dispatch' ||")) throw new Error('manual dispatch can still publish without explicit guard');
if(build.includes('release: authorized Blue Magic v2.6.7 permanent APK once')) throw new Error('old v2.6.7 trigger remains');
const normal=build.slice(build.indexOf('android-debug-apk:'),build.indexOf('android-permanent-apk:'));
if(normal.includes('BLUE_MAGIC_ANDROID_KEYSTORE_BASE64')||normal.includes('BLUE_MAGIC_ANDROID_KEYSTORE_PASSWORD')) throw new Error('normal CI still loads permanent signing secrets');
console.log('v2.6.8 release hygiene: metadata aligned, normal CI ephemeral and permanent delivery SHA-gated OK');
'''
write('app/src/test/v268-release-hygiene.mjs', contract)
