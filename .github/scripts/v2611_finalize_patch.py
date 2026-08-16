from pathlib import Path


def replace(path, old, new, required=True, count=-1):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    if old not in s:
        if required:
            raise SystemExit(f'missing patch anchor in {path}: {old[:120]!r}')
        return False
    s = s.replace(old, new, count)
    p.write_text(s, encoding='utf-8')
    return True

# Version Android et identité client.
replace('app/build.gradle', 'versionCode 50', 'versionCode 51')
replace('app/build.gradle', 'versionName "2.6.10"', 'versionName "2.6.11"')
replace('app/src/main/java/com/profitloop/blueauto/ApiClient.java', '"2.6.10"', '"2.6.11"')

# Charger uniquement la nouvelle couche visuelle finalisée.
replace('app/src/main/assets/index.html', 'control-tower-v2610.css', 'control-tower-v2611.css')
replace('app/src/main/assets/index.html', 'control-tower-v2610.js', 'control-tower-v2611.js')

# Version serveur et négociation de capacités. La v2.6.11 peut ainsi détecter proprement
# un serveur 2.6.7 sans envoyer commission_policy et sans produire "Action API inconnue".
replace('cloudflare/src/index.js', "const API_VERSION = '2.6.10-cloudflare';", "const API_VERSION = '2.6.11-cloudflare';")
replace('cloudflare/src/index.js',
        "return success({service: 'blue-magic-api', version: API_VERSION, database: 'online'}, 200, headers);",
        "return success({service: 'blue-magic-api', version: API_VERSION, database: 'online', capabilities: {commissions: true, commission_override: true, remote_results: true, force_sync: true, network_audit: true}}, 200, headers);")
replace('cloudflare/package.json', '"version": "2.6.8"', '"version": "2.6.11"')
replace('cloudflare/package-lock.json', '"version": "2.6.8"', '"version": "2.6.11"')

# Les contrats historiques doivent vérifier la cohérence actuelle sans figer l'identité 2.6.8.
for test in [
    'app/src/test/finance-flow.mjs',
    'app/src/test/v268-release-hygiene.mjs',
    'app/src/test/bir-v269-functional-contract.mjs'
]:
    p = Path(test)
    s = p.read_text(encoding='utf-8')
    s = s.replace('versionCode 50', 'versionCode 51')
    s = s.replace('versionName "2.6.10"', 'versionName "2.6.11"')
    s = s.replace('versionCode 49', 'versionCode 51')
    s = s.replace('versionName "2.6.9"', 'versionName "2.6.11"')
    s = s.replace('/versionCode 50/', '/versionCode 51/')
    s = s.replace('/versionName "2\\.6\\.10"/', '/versionName "2\\.6\\.11"/')
    s = s.replace("pkg.version!=='2.6.8'", "pkg.version!=='2.6.11'")
    s = s.replace("Cloudflare package version not 2.6.8", "Cloudflare package version not 2.6.11")
    s = s.replace("lock.version!=='2.6.8'", "lock.version!=='2.6.11'")
    s = s.replace("lock.packages[''].version!=='2.6.8'", "lock.packages[''].version!=='2.6.11'")
    s = s.replace("Cloudflare lock root version not 2.6.8", "Cloudflare lock root version not 2.6.11")
    p.write_text(s, encoding='utf-8')

# Nouveau contrat v2.6.11 : design validé, saisie visible, négociation de capacités et absence
# de commission_policy automatique avant confirmation de compatibilité serveur.
contract = Path('app/src/test/v2611-finalization-contract.mjs')
contract.write_text(r'''import fs from 'node:fs';
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
const css=fs.readFileSync('app/src/main/assets/control-tower-v2611.css','utf8');
const js=fs.readFileSync('app/src/main/assets/control-tower-v2611.js','utf8');
const gradle=fs.readFileSync('app/build.gradle','utf8');
const worker=fs.readFileSync('cloudflare/src/index.js','utf8');
const api=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/ApiClient.java','utf8');
if(!html.includes('control-tower-v2611.css')||!html.includes('control-tower-v2611.js')) throw new Error('v2611 assets not wired');
for(const x of ['bir-topbar','bir-control-balance','bir-modules-grid','bir-bottom-nav','form-editing .module-tabs','-webkit-text-fill-color:#071b3a','scroll-margin-bottom:150px']) if(!css.includes(x)) throw new Error('visual/input contract missing: '+x);
for(const x of ['REMOTE PRÊT','buildRoleModules','bindKeyboardVisibility','detectCapabilities','serverSupportsCommissions','commission_policy','Aucun message d\\\'erreur ne sera affiché']) if(!js.includes(x)) throw new Error('control tower contract missing: '+x);
if(/commissionCard\([\s\S]{0,800}platform\('commission_policy'/.test(js)) throw new Error('commission_policy must not run blindly at card creation');
if(!worker.includes("2.6.11-cloudflare")||!worker.includes('capabilities: {commissions: true')) throw new Error('worker capabilities missing');
if(!gradle.includes('versionCode 51')||!gradle.includes('versionName "2.6.11"')) throw new Error('android version mismatch');
if(!api.includes('"2.6.11"')) throw new Error('api client version mismatch');
console.log('BIR v2.6.11 finalization: reference UI, keyboard visibility, capability negotiation and commissions gate OK');
''', encoding='utf-8')
