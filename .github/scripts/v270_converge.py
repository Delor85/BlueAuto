from pathlib import Path
import re

ROOT = Path('.')


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, content):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'pattern missing for {label}')
    if text.count(old) != 1:
        raise SystemExit(f'pattern not unique for {label}: {text.count(old)}')
    return text.replace(old, new, 1)

# 1) Android metadata: preserve versionCode 51, move the converged source to v2.7.0.
gradle_path = 'app/build.gradle'
gradle = read(gradle_path)
gradle = replace_once(gradle, 'versionName "2.6.11"', 'versionName "2.7.0"', 'versionName')
if 'versionCode 51' not in gradle or 'applicationId "com.profitloop.blueauto"' not in gradle:
    raise SystemExit('protected Android identity/versionCode missing')
write(gradle_path, gradle)

# 2) Keep the complete v2.6.11 full-screen layer, then add a narrow v2.7 overlay.
index_path = 'app/src/main/assets/index.html'
index = read(index_path)
index = replace_once(
    index,
    '<link rel="stylesheet" href="control-tower-v2611.css">',
    '<link rel="stylesheet" href="control-tower-v2611.css">\n    <link rel="stylesheet" href="control-tower-v270.css">',
    'v270 css include'
)
index = replace_once(
    index,
    '  <script src="control-tower-v2611.js"></script>',
    '  <script src="control-tower-v2611.js"></script>\n  <script src="control-tower-v270.js"></script>',
    'v270 js include'
)
write(index_path, index)

# 3) Owner-only MOCK workspace. It is deliberately NOT a Camtel node and does not alter DAE/DSM/PoS hierarchy.
main_path = 'app/src/main/java/com/profitloop/blueauto/MainActivity.java'
main = read(main_path)
main = replace_once(
    main,
    '    private static final String PAIRING_DIAGNOSTIC_KEY = "pairing_diagnostic_v254";\n',
    '    private static final String PAIRING_DIAGNOSTIC_KEY = "pairing_diagnostic_v254";\n'
    '    private static final String MOCK_WORKSPACE_KEY = "bir_mock_workspace_v270";\n'
    '    private static final String MOCK_OWNER_NODE_CODE = "SU1";\n'
    '    private static final String MOCK_PROFILE_ID = "__BIR_MOCK_OWNER__";\n',
    'mock constants'
)
main = replace_once(
    main,
    '        AppConfig.migrateLegacyProfile(this);\n        applyRobotWindowPolicy();',
    '        AppConfig.migrateLegacyProfile(this);\n'
    '        if (AppConfig.prefs(this).getBoolean(MOCK_WORKSPACE_KEY, false) && !mockOwnerEligible()) {\n'
    '            AppConfig.prefs(this).edit().putBoolean(MOCK_WORKSPACE_KEY, false).commit();\n'
    '        }\n'
    '        applyRobotWindowPolicy();',
    'mock startup guard'
)
helper = '''
    private boolean mockOwnerEligible() {
        return "DAE".equalsIgnoreCase(AppConfig.role(this))
                && MOCK_OWNER_NODE_CODE.equalsIgnoreCase(AppConfig.nodeCode(this));
    }

    private boolean isMockWorkspaceActive() {
        return mockOwnerEligible() && AppConfig.prefs(this).getBoolean(MOCK_WORKSPACE_KEY, false);
    }

    private void setMockWorkspaceActive(boolean active) {
        AppConfig.prefs(this).edit().putBoolean(MOCK_WORKSPACE_KEY, active && mockOwnerEligible()).commit();
    }

'''
if helper.strip() not in main:
    main = replace_once(main, '    private void showAccountManager() {\n', helper + '    private void showAccountManager() {\n', 'mock helpers')

main = replace_once(
    main,
    '        String[] labels = AppConfig.profileLabels(this);\n        String[] ids = AppConfig.profileIds(this);',
    '        String[] baseLabels = AppConfig.profileLabels(this);\n'
    '        String[] baseIds = AppConfig.profileIds(this);\n'
    '        List<String> labelsList = new ArrayList<>();\n'
    '        List<String> idsList = new ArrayList<>();\n'
    '        boolean mockActive = isMockWorkspaceActive();\n'
    '        for (int i = 0; i < baseLabels.length; i++) {\n'
    '            String current = baseLabels[i] == null ? "Compte inconnu" : baseLabels[i];\n'
    '            if (mockActive && current.startsWith("✓ ")) current = current.substring(2);\n'
    '            labelsList.add(current);\n'
    '            idsList.add(baseIds[i]);\n'
    '        }\n'
    '        if (mockOwnerEligible()) {\n'
    '            labelsList.add((mockActive ? "✓ " : "") + "MOCK • ESPACE PROPRIÉTAIRE • HORS RÉSEAU");\n'
    '            idsList.add(MOCK_PROFILE_ID);\n'
    '        }\n'
    '        String[] labels = labelsList.toArray(new String[0]);\n'
    '        String[] ids = idsList.toArray(new String[0]);',
    'mock account list'
)
main = replace_once(
    main,
    '                    if (index < 0 || index >= ids.length) return;\n'
    '                    if (ids[index].equals(AppConfig.profileId(this))) {\n'
    '                        showSimSlotChooser();\n'
    '                        return;\n'
    '                    }\n'
    '                    if (AppConfig.activateProfile(this, ids[index])) recreate();',
    '                    if (index < 0 || index >= ids.length) return;\n'
    '                    if (MOCK_PROFILE_ID.equals(ids[index])) {\n'
    '                        setMockWorkspaceActive(true);\n'
    '                        recreate();\n'
    '                        return;\n'
    '                    }\n'
    '                    setMockWorkspaceActive(false);\n'
    '                    if (ids[index].equals(AppConfig.profileId(this))) {\n'
    '                        showSimSlotChooser();\n'
    '                        return;\n'
    '                    }\n'
    '                    if (AppConfig.activateProfile(this, ids[index])) recreate();',
    'mock account selection'
)
main = replace_once(
    main,
    '        @JavascriptInterface\n        public void openAccounts() {\n            runOnUiThread(() -> showAccountManager());\n        }\n',
    '        @JavascriptInterface\n        public void openAccounts() {\n            runOnUiThread(() -> showAccountManager());\n        }\n\n'
    '        @JavascriptInterface\n'
    '        public boolean isMockWorkspace() {\n'
    '            return isMockWorkspaceActive();\n'
    '        }\n\n'
    '        @JavascriptInterface\n'
    '        public void exitMockWorkspace() {\n'
    '            runOnUiThread(() -> {\n'
    '                setMockWorkspaceActive(false);\n'
    '                recreate();\n'
    '            });\n'
    '        }\n',
    'mock bridge methods'
)
main = replace_once(
    main,
    '        public void platformAction(String action, String payloadJson) {\n            new Thread(() -> {',
    '        public void platformAction(String action, String payloadJson) {\n'
    '            String normalizedAction = action == null ? "" : action.trim().toLowerCase(Locale.ROOT);\n'
    '            if ((normalizedAction.startsWith("mercenary_") || normalizedAction.startsWith("monetization_"))\n'
    '                    && !isMockWorkspaceActive()) {\n'
    '                callbackError("onPlatformAction", new SecurityException(\n'
    '                        "Cette rubrique est réservée au compte MOCK propriétaire."));\n'
    '                return;\n'
    '            }\n'
    '            new Thread(() -> {',
    'mock API guard'
)
write(main_path, main)

# 4) v2.7 overlay: MOCK account, monetization lab and visible balance-evidence caution.
v270_js = r'''(function () {
'use strict';
function byId(id){return document.getElementById(id);}
function bridge(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}
function isMock(){var b=bridge();try{return !!(b&&b.isMockWorkspace&&b.isMockWorkspace());}catch(e){return false;}}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function versionAtLeast(version,maj,min,patch){var m=String(version||'').match(/(\d+)\.(\d+)\.(\d+)/),a;if(!m)return false;a=[Number(m[1]),Number(m[2]),Number(m[3])];if(a[0]!==maj)return a[0]>maj;if(a[1]!==min)return a[1]>min;return a[2]>=patch;}
function findMercenary(){var items=document.querySelectorAll('details.v267-extra'),i,t;for(i=0;i<items.length;i+=1){t=String(items[i].textContent||'');if(t.indexOf('Hub Mercenaires')>=0)return items[i];}return null;}
function hideMercenaryOutsideMock(){var merc=findMercenary();if(merc)merc.style.display='none';}
function addEvidencePolicy(){var reports=document.querySelector('[data-tab-panel="reports"]'),card;if(!reports||byId('v270EvidencePolicy'))return;card=document.createElement('article');card.id='v270EvidencePolicy';card.className='panel v270-evidence-policy';card.innerHTML='<p class="eyebrow">FIABILITÉ DU SOLDE</p><h3>Preuve avant priorité</h3><div class="v270-evidence-grid"><div><b>A — CERTIFIÉ CAMTEL</b><span>Lecture directe du solde propre ou preuve opérateur explicitement actuelle.</span></div><div><b>A — CERTIFIÉ TRANSACTION, sous chronologie sûre</b><span>Une réponse de transfert avec nouveau solde n\'est A que si son ordre temporel est sûr. Une réponse retardée ne doit jamais faire régresser une preuve plus récente.</span></div><div><b>A — HISTORIQUE / CURRENTBALANCE</b><span>Les 5 dernières transactions peuvent certifier le solde lorsque le CurrentBalance est explicitement identifié et chronologiquement cohérent.</span></div><div><b>À RAPPROCHER</b><span>Réponse tardive, ambiguë ou sans horodatage fiable : conserver comme preuve de transaction, pas comme vérité de solde supérieure.</span></div></div>';reports.insertBefore(card,reports.firstChild);}
function mockRevenueHtml(){return '<article class="panel v270-mock-card"><p class="eyebrow">RENTABILISATION — LAB</p><h3>Modèles de revenus à tester</h3><p class="muted">Aucune facturation n\'est activée ici. Ce sont des hypothèses commerciales approuvées à mesurer sur le terrain.</p><div class="v270-business-grid"><div><b>B.I.R. Core PoS</b><span>Gratuit ou quasi-gratuit pour maximiser l\'adoption et le volume Blue.</span></div><div><b>B.I.R. Pro DSM</b><span>Hypothèse : 2 000 à 5 000 F CFA/mois pour réseau, soldes, CRM, automatisation et SAV.</span></div><div><b>B.I.R. Business DAE</b><span>Hypothèse : 10 000 à 30 000 F CFA/mois selon le nombre de nœuds et les outils de pilotage.</span></div><div><b>Robot as a Service</b><span>Installation + téléphone compatible + configuration + maintenance + abonnement de support.</span></div><div><b>White-label</b><span>Licencier la plateforme à d\'autres distributeurs/réseaux avec identité et règles dédiées.</span></div><div><b>Audit & Preuves Pro</b><span>Rapports, rapprochement Camtel, exports, anti-contestation et diagnostics avancés.</span></div><div><b>SAV Premium / CRM</b><span>Assistance prioritaire, alertes d\'hibernation, coaching et suivi des performances.</span></div><div><b>Cloud Vending</b><span>Pool de PoS Robots servant des vendeurs virtuels avec comptabilité, plafonds et traçabilité.</span></div></div></article>';}
function mockOffNetworkHtml(){return '<article class="panel v270-mock-card"><p class="eyebrow">HORS RÉSEAU DAE / DSM / POS</p><h3>Laboratoire propriétaire</h3><div class="v270-business-grid"><div><b>Mercenaires</b><span>Vendeurs virtuels servis par des PoS Robots. Les fonctions serveur restent désactivées tant que le Worker compatible n\'est pas autorisé en production.</span></div><div><b>B.I.R. Pay</b><span>NON OPÉRATIONNEL : aucune collecte, clé, débit Mobile Money ou webhook n\'est activé.</span></div><div><b>Partenariats / services</b><span>Zone de conception pour offres, revendeurs externes, white-label et services non rattachés à une SIM Camtel hiérarchique.</span></div><div><b>Règle d\'isolement</b><span>MOCK n\'est pas un node_code Camtel et ne peut jamais devenir DAE, DSM, PoS, Robot ou propriétaire d\'une SIM.</span></div></div></article>';}
function setMercenaryCapability(ok,version){var merc=findMercenary(),buttons,i,status;if(!merc)return;merc.style.display='block';buttons=merc.querySelectorAll('button');for(i=0;i<buttons.length;i+=1)buttons[i].disabled=!ok;status=byId('v270MercenaryCapability');if(status)status.innerHTML=ok?'Serveur '+esc(version||'compatible')+' : fonctions Mercenaires disponibles pour essai contrôlé.':'Production '+esc(version||'non identifiée')+' : fonctions Mercenaires verrouillées pour éviter « Action API inconnue ». Aucun ordre ne sera envoyé.';}
function renderMock(){var main=document.querySelector('main'),merc=findMercenary(),shell,children,i,b;if(!main)return;document.body.className=(document.body.className?document.body.className+' ':'')+'v270-mock-active';shell=document.createElement('section');shell.id='birMockWorkspace';shell.className='v270-mock-workspace';shell.innerHTML='<article class="v270-mock-hero"><div><p class="eyebrow">COMPTE SPÉCIAL</p><h2>MOCK</h2><p>Espace propriétaire • Hors réseau Camtel • Aucune SIM sollicitée par l\'ouverture de cet espace.</p></div><button id="v270ExitMock" type="button">REVENIR AU RÉSEAU</button></article><article class="panel v270-mock-card"><p class="eyebrow">MERCENAIRES / CLOUD VENDING</p><h3>Centre propriétaire</h3><p id="v270MercenaryCapability" class="v270-capability">Vérification du serveur…</p><div id="v270MercenaryMount"></div></article>'+mockRevenueHtml()+mockOffNetworkHtml();main.insertBefore(shell,main.firstChild);if(merc){merc.style.display='block';merc.open=true;byId('v270MercenaryMount').appendChild(merc);}children=main.children;for(i=0;i<children.length;i+=1){if(children[i]!==shell)children[i].className+=' v270-network-hidden';}b=document.querySelector('.module-tabs');if(b)b.style.display='none';if(byId('birAccountRole'))byId('birAccountRole').textContent='MOCK';if(byId('birAccountNode'))byId('birAccountNode').textContent='PROPRIÉTAIRE';if(byId('birAccountPhone'))byId('birAccountPhone').textContent='HORS RÉSEAU';byId('v270ExitMock').onclick=function(){var n=bridge();if(n&&n.exitMockWorkspace)n.exitMockWorkspace();};installHealthGate();var n=bridge();if(n&&n.checkServerHealth){try{n.checkServerHealth();}catch(e){}}}
function installHealthGate(){window.BlueMagicNative=window.BlueMagicNative||{};var old=window.BlueMagicNative.onServerHealth;window.BlueMagicNative.onServerHealth=function(data){if(typeof old==='function'){try{old(data);}catch(e){}}if(!isMock()||!data||data.error)return;var caps=data.capabilities||{},version=String(data.version||''),ok=caps.mercenaries===true||versionAtLeast(version,2,6,10);setMercenaryCapability(ok,version);};setMercenaryCapability(false,'2.6.7');}
function installEvidenceObserver(){window.BlueMagicNative=window.BlueMagicNative||{};var old=window.BlueMagicNative.onCommandStatus;window.BlueMagicNative.onCommandStatus=function(data){if(typeof old==='function'){try{old(data);}catch(e){}}var c=data&&data.command,msg,op,target;if(!c||c.state!=='SUCCEEDED')return;op=String(c.operation||'');if(op!=='DISTRIBUTION_TRANSFER'&&op!=='RETAIL_TRANSFER')return;msg=String(c.result_message||'');if(!/(current\s*balance|solde|balance)/i.test(msg))return;target=byId('reportActivityDetail');if(!target)return;if(/\b\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}\b/.test(msg)&&/\b\d{1,2}:\d{2}\b/.test(msg)){target.textContent='Résultat financier avec solde reçu. Chronologie opérateur présente : peut contribuer à une preuve certifiée, sans jamais écraser une preuve plus récente.';}else{target.textContent='Résultat financier avec solde reçu sans chronologie opérateur certaine : à rapprocher. Une réponse retardée ne doit pas être utilisée pour faire régresser le solde connu.';}};}
function boot(){if(isMock()){renderMock();return;}hideMercenaryOutsideMock();addEvidencePolicy();installEvidenceObserver();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
}());
'''
write('app/src/main/assets/control-tower-v270.js', v270_js)

v270_css = r'''/* B.I.R. v2.7.0 — overlay additive au shell plein écran v2.6.11. */
.v270-network-hidden{display:none!important}.v270-evidence-policy{margin:8px 0!important}.v270-evidence-grid,.v270-business-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.v270-evidence-grid>div,.v270-business-grid>div{padding:10px;border:1px solid #d2e3f4;border-radius:13px;background:#f8fbff;color:#102f58}.v270-evidence-grid b,.v270-business-grid b{display:block;color:#082d68;font-size:.77rem;margin-bottom:4px}.v270-evidence-grid span,.v270-business-grid span{display:block;color:#4b6782;font-size:.69rem;line-height:1.35}.v270-mock-workspace{padding-top:8px}.v270-mock-hero{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:8px 0 12px;padding:16px;border-radius:20px;background:linear-gradient(135deg,#031a48,#073d7e);color:#fff;box-shadow:0 10px 24px rgba(2,31,77,.2)}.v270-mock-hero .eyebrow{color:#f4bc3d}.v270-mock-hero h2{font-size:2rem;letter-spacing:.12em;margin:2px 0;color:#fff}.v270-mock-hero p{margin:3px 0;color:#ccecff;font-size:.76rem}.v270-mock-hero button{min-width:126px;background:linear-gradient(110deg,#d89b27,#ffd66c);color:#08224a;border:0;border-radius:14px;font-weight:900;padding:11px}.v270-mock-card{margin:9px 0!important}.v270-capability{padding:9px 10px;border-radius:10px;background:#fff3d7;color:#795000;font-size:.72rem;font-weight:800}.v270-mock-active .bir-topbar{border-bottom-color:#f0bd48!important}.v270-mock-active .bir-account-chip{border-color:#f1c765!important}.v270-mock-active details.v267-extra{display:block!important}.v270-mock-active details.v267-extra button:disabled{opacity:.45!important;filter:grayscale(.35);cursor:not-allowed!important}@media(max-width:520px){.v270-evidence-grid,.v270-business-grid{grid-template-columns:1fr}.v270-mock-hero{align-items:flex-start;flex-direction:column}.v270-mock-hero button{width:100%}}
'''
write('app/src/main/assets/control-tower-v270.css', v270_css)

# 5) Contract tests: no MOCK network role, owner-only native gate, v2.6.11 shell preserved.
v270_test = r'''import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const base = new URL('../', import.meta.url);
const gradle = await readFile(new URL('../../build.gradle', import.meta.url), 'utf8');
const html = await readFile(new URL('main/assets/index.html', base), 'utf8');
const main = await readFile(new URL('main/java/com/profitloop/blueauto/MainActivity.java', base), 'utf8');
const overlay = await readFile(new URL('main/assets/control-tower-v270.js', base), 'utf8');
const css = await readFile(new URL('main/assets/control-tower-v270.css', base), 'utf8');
const worker = await readFile(new URL('../../cloudflare/src/index.js', import.meta.url), 'utf8').catch(()=>'');
assert.match(gradle,/applicationId "com\.profitloop\.blueauto"/);
assert.match(gradle,/versionCode 51/);
assert.match(gradle,/versionName "2\.7\.0"/);
assert.match(html,/control-tower-v2611\.css/);
assert.match(html,/control-tower-v270\.css/);
assert.match(html,/control-tower-v2611\.js/);
assert.match(html,/control-tower-v270\.js/);
assert.match(main,/MOCK_OWNER_NODE_CODE = "SU1"/);
assert.match(main,/MOCK_PROFILE_ID = "__BIR_MOCK_OWNER__"/);
assert.match(main,/public boolean isMockWorkspace\(\)/);
assert.match(main,/startsWith\("mercenary_"\)/);
assert.match(main,/Cette rubrique est réservée au compte MOCK propriétaire/);
assert.match(overlay,/MOCK/);
assert.match(overlay,/HORS RÉSEAU DAE \/ DSM \/ POS/);
assert.match(overlay,/B\.I\.R\. Pay/);
assert.match(overlay,/Robot as a Service/);
assert.match(overlay,/Une réponse retardée ne doit jamais faire régresser une preuve plus récente/);
assert.match(css,/v270-mock-workspace/);
assert.doesNotMatch(worker,/role\s*===\s*['"]MOCK['"]/);
console.log('B.I.R. v2.7 convergence: v2.6.11 shell, owner-only MOCK and evidence UX OK');
'''
write('app/src/test/v270-finalization-contract.mjs', v270_test)

# 6) State note: explicitly record why SHA 45f must not be published after discovering the newer branch.
state = '''# B.I.R. / Blue Magic — convergence v2.7 sur la base v2.6.11\n\nDate : 2026-08-16\n\n## Découverte de reprise\n\nLa bibliothèque durable contient `BIR-v2.6.11-ETAT-REPRISE-2026-08-16.md`. GitHub confirme que `fix/bir-v2-6-11-finalization` est au SHA `e3f9e9016e86c1193ba4170e2a9fce1ba466eb86`. La branche v2.7 antérieure `feat/bir-v2-7-stabilization` issue de `f1e9f3d...` diverge et ne contient pas les 15 commits v2.6.11.\n\nPar règle de non-régression, l'autorisation de publication permanente visant le SHA `45f814f7b41ce57c845cb0a476af3c53f5d96309` est mise en attente : produire cet APK comme nouvelle livraison terrain ferait repartir avant la finalisation v2.6.11.\n\n## Nouvelle base\n\nBranche : `feat/bir-v2-7-finalization`\nBase exacte : `e3f9e9016e86c1193ba4170e2a9fce1ba466eb86`\nVersion Android cible : 2.7.0 / versionCode 51 / package historique inchangé.\n\n## MOCK propriétaire\n\nMOCK est un espace virtuel local, pas un nœud Camtel. Il n'entre jamais dans la hiérarchie DAE/DSM/PoS et n'a ni SIM ni Robot. Dans l'APK officielle actuelle il est visible uniquement lorsque le profil actif est le DAE `SU1`. Les appels `mercenary_*` sont bloqués nativement hors MOCK. Les rubriques Mercenaires, rentabilisation, sources de revenus, B.I.R. Pay expérimental, White-label et Robot as a Service sont regroupées dans cet espace.\n\n## Fiabilité du solde\n\nRègle renforcée côté expérience utilisateur : une réponse financière donnant un nouveau solde n'est pas affichée comme preuve A lorsqu'elle n'apporte pas une chronologie opérateur suffisamment sûre. Une réponse tardive/ambiguë doit être rapprochée et ne doit jamais justifier la régression d'une preuve de solde plus récente.\n\nAucune modification Cloudflare/D1 n'est réalisée dans cette convergence. Le durcissement serveur éventuel de la promotion des `FINANCIAL_RESULT` sans horodatage explicite reste un chantier séparé soumis à autorisation serveur distincte.\n'''
write('docs/BIR_V270_CONVERGENCE_STATE.md', state)

print('v2.7 convergence patch prepared')
