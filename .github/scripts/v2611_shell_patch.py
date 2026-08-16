from pathlib import Path


def patch(path, old, new):
    p=Path(path); s=p.read_text(encoding='utf-8')
    if new in s:
        return
    if old not in s:
        raise SystemExit(f'missing shell anchor in {path}: {old[:100]!r}')
    p.write_text(s.replace(old,new,1),encoding='utf-8')

# Le shell natif reste présent comme filet de sécurité, mais ne gaspille plus l'écran :
# l'identité, Comptes et Gérer sont servis par le header/dock B.I.R. et restent actionnables.
patch('app/src/main/java/com/profitloop/blueauto/MainActivity.java',
      '        page.setPadding(dp(10), dp(8), dp(10), dp(6));\n',
      '        page.setPadding(0, 0, 0, 0);\n')
patch('app/src/main/java/com/profitloop/blueauto/MainActivity.java',
      '        page.addView(nativeStatus);\n',
      '        page.addView(nativeStatus);\n        nativeStatus.setVisibility(View.GONE);\n')
patch('app/src/main/java/com/profitloop/blueauto/MainActivity.java',
      '        page.addView(compactBar);\n',
      '        page.addView(compactBar);\n        compactBar.setVisibility(View.GONE);\n')

# Header Web : menu fonctionnel, compte cliquable et état Robot rafraîchi au retour des réglages.
p=Path('app/src/main/assets/control-tower-v2611.js'); s=p.read_text(encoding='utf-8')
old="function startOrResume(c){if(upper(c.mode)!=='ROBOT')return;if(window.AndroidBridge&&window.AndroidBridge.startRobot)window.AndroidBridge.startRobot();}"
new="function startOrResume(c){if(upper(c.mode)!=='ROBOT')return;if(window.AndroidBridge&&window.AndroidBridge.startRobot)window.AndroidBridge.startRobot();window.setTimeout(function(){updateRuntimeStatus(cfg());},1200);}"
if new not in s:
    if old not in s: raise SystemExit('missing startOrResume anchor')
    s=s.replace(old,new,1)

old=" updateRuntimeStatus(c);if(simBad)makeSimNoticeActionable();buildQuickControls(c);roleFields(c);buildRoleModules(c);resultCard();commissionCard(c);hideDuplicates();bindKeyboardVisibility();wrapCallbacks(c);"
new=" updateRuntimeStatus(c);buildHeaderControls(c);if(simBad)makeSimNoticeActionable();buildQuickControls(c);roleFields(c);buildRoleModules(c);resultCard();commissionCard(c);hideDuplicates();bindKeyboardVisibility();wrapCallbacks(c);"
if new not in s:
    if old not in s: raise SystemExit('missing boot header anchor')
    s=s.replace(old,new,1)

anchor="function quickButton(key,icon,label){return '<button id=\"'+key+'\"><b>'+icon+'</b>'+label+'</button>';}"
insert="function buildHeaderControls(c){var header=document.querySelector('.bir-topbar'),menu,chip;if(!header)return;menu=document.createElement('button');menu.type='button';menu.className='bir-menu-button';menu.setAttribute('aria-label','Ouvrir la gestion B.I.R.');menu.innerHTML='<span></span><span></span><span></span>';menu.onclick=function(){if(window.AndroidBridge&&window.AndroidBridge.openManagement)window.AndroidBridge.openManagement();};header.appendChild(menu);chip=document.querySelector('.bir-account-chip');if(chip){chip.title='Changer de compte';chip.onclick=function(){if(window.AndroidBridge&&window.AndroidBridge.openAccounts)window.AndroidBridge.openAccounts();};}}\n"+anchor
if 'function buildHeaderControls(c)' not in s:
    if anchor not in s: raise SystemExit('missing quickButton anchor')
    s=s.replace(anchor,insert,1)

old="if(balanceState){balanceState.textContent='ROBOT ARRÊTÉ';balanceState.className='bir-robot-orb off';}}"
new="if(balanceState){balanceState.innerHTML='ROBOT ARRÊTÉ<small>Toucher pour démarrer</small>';balanceState.className='bir-robot-orb off';balanceState.onclick=function(){startOrResume(c);};}}"
if new not in s:
    if old not in s: raise SystemExit('missing balance robot-off anchor')
    s=s.replace(old,new,1)
# Réinitialiser le clic quand Robot/Remote est déjà prêt.
s=s.replace("if(balanceState){balanceState.textContent='REMOTE PRÊT';balanceState.className='bir-robot-orb remote';}","if(balanceState){balanceState.textContent='REMOTE PRÊT';balanceState.className='bir-robot-orb remote';balanceState.onclick=null;}")
s=s.replace("if(balanceState){balanceState.textContent='ROBOT ACTIF';balanceState.className='bir-robot-orb';}","if(balanceState){balanceState.textContent='ROBOT ACTIF';balanceState.className='bir-robot-orb';balanceState.onclick=null;}")

old="if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();"
new="document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')updateRuntimeStatus(cfg());});window.addEventListener('focus',function(){window.setTimeout(function(){updateRuntimeStatus(cfg());},120);});if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();"
if new not in s:
    if old not in s: raise SystemExit('missing final boot anchor')
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

# CSS du menu fonctionnel et du compte cliquable.
p=Path('app/src/main/assets/control-tower-v2611.css'); s=p.read_text(encoding='utf-8')
extra="""
.bir-menu-button{position:absolute!important;left:13px!important;top:19px!important;width:46px!important;height:42px!important;padding:8px!important;margin:0!important;border:0!important;border-radius:12px!important;background:rgba(1,20,54,.62)!important;box-shadow:0 0 12px rgba(50,175,255,.13)!important;z-index:4!important;display:flex!important;flex-direction:column!important;justify-content:center!important;gap:5px!important}
.bir-menu-button span{display:block!important;width:100%!important;height:3px!important;border-radius:3px!important;background:#fff!important;box-shadow:0 0 5px rgba(90,220,255,.45)!important}
.bir-account-chip{cursor:pointer!important}.bir-robot-orb.off{cursor:pointer!important}.bir-robot-orb small{display:block!important;font-size:.54rem!important;line-height:1.2!important;margin-top:3px!important;color:inherit!important}
@media(max-width:360px){.bir-menu-button{left:7px!important;top:11px!important;width:40px!important;height:38px!important}}
"""
if '.bir-menu-button{' not in s:
    s += extra
p.write_text(s,encoding='utf-8')

# Contrat shell : pas de barre/titre natif dupliqué, menu BIR réellement actionnable.
Path('app/src/test/v2611-shell-contract.mjs').write_text(r'''import fs from 'node:fs';
const manifest=fs.readFileSync('app/src/main/AndroidManifest.xml','utf8');
const styles=fs.readFileSync('app/src/main/res/values/styles.xml','utf8');
const main=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/MainActivity.java','utf8');
const js=fs.readFileSync('app/src/main/assets/control-tower-v2611.js','utf8');
const css=fs.readFileSync('app/src/main/assets/control-tower-v2611.css','utf8');
if(!manifest.includes('android:theme="@style/BlueMagicAppTheme"')) throw new Error('BIR app theme not applied');
if(!styles.includes('Theme.Material.Light.NoActionBar')||!styles.includes('BlueMagicAppTheme')) throw new Error('no-actionbar shell missing');
if(!main.includes('page.setPadding(0, 0, 0, 0)')) throw new Error('native shell still adds a visible outer gutter');
if(!main.includes('nativeStatus.setVisibility(View.GONE)')||!main.includes('compactBar.setVisibility(View.GONE)')) throw new Error('duplicate native shell remains visible');
for(const x of ['buildHeaderControls','openManagement','openAccounts','visibilitychange','Toucher pour démarrer']) if(!js.includes(x)) throw new Error('interactive BIR shell missing '+x);
if(!css.includes('.bir-menu-button{')||!css.includes('.bir-account-chip{cursor:pointer')) throw new Error('header action styling missing');
console.log('BIR v2.6.11 shell: edge-to-edge, no duplicate native toolbar, functional menu/account and live Robot state OK');
''',encoding='utf-8')
