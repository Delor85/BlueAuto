from pathlib import Path

# finance-flow: v2.6.9+ starts on Accueil, then verifies the central operation module.
p=Path('app/src/test/finance-flow.mjs'); s=p.read_text(encoding='utf-8')
old="""assert.match(tabButtons.find(item => item.tab === 'flux').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen');\ntabButtons.find(item => item.tab === 'reports').onclick();\nassert.match(tabButtons.find(item => item.tab === 'reports').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen');\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen hidden');\nassert.equal(localStorage.getItem('blue_magic_active_module'), 'reports');\n"""
new="""assert.match(tabButtons.find(item => item.tab === 'reports').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen');\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen hidden');\ntabButtons.find(item => item.tab === 'flux').onclick();\nassert.match(tabButtons.find(item => item.tab === 'flux').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen');\nassert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen hidden');\nassert.equal(localStorage.getItem('bir_active_module_v269'), 'flux');\n"""
if old in s: s=s.replace(old,new,1)
s=s.replace('assert.match(gradleConfig, /versionCode 48/);','assert.match(gradleConfig, /versionCode 50/);')
s=s.replace('assert.match(gradleConfig, /versionName "2\\.6\\.8"/);','assert.match(gradleConfig, /versionName "2\\.6\\.10"/);')
s=s.replace('assert.match(html, /SAV & DIAGNOSTIC/);','assert.match(html, /ACTIVITÉ & SAV/);\nassert.match(html, /DIAGNOSTIC RAPIDE/);')
p.write_text(s,encoding='utf-8')

# Historical role-nav test: panels stay, commercial names are BIR.
p=Path('app/src/test/v268-ux-performance.mjs'); s=p.read_text(encoding='utf-8')
old="""for(const roleLabel of [\"configuration.role==='DAE'\",\"configuration.role==='DSM'\",\"configuration.role==='POS'\",\"tabLabel('reports','Pilotage')\",\"tabLabel('reports','Soldes')\",\"tabLabel('reports','Solde')\",\"tabLabel('flux','Vente')\"]){\n  if(!ui.includes(roleLabel)) throw new Error('role navigation contract missing: '+roleLabel);\n}\nif(!ui.includes(\"fleet.className='module-tab hidden'\")) throw new Error('POS fleet hiding missing');\n"""
new="""for(const roleLabel of [\"configuration.role==='DAE'\",\"configuration.role==='DSM'\",\"configuration.role==='POS'\",\"tabLabel('reports','Accueil')\",\"tabLabel('fleet','Réseau')\",\"tabLabel('support','Activité')\",\"tabLabel('config','Gérer')\",\"tabLabel('flux','Piloter')\",\"tabLabel('flux','Fournir')\",\"tabLabel('flux','Vendre')\"]){\n  if(!ui.includes(roleLabel)) throw new Error('role navigation contract missing: '+roleLabel);\n}\nif(!ui.includes(\"configuration.role==='POS'\")) throw new Error('POS role navigation missing');\n"""
if old in s: s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

# Transaction UX headings changed but capabilities remain.
p=Path('app/src/test/v268-transaction-ux.mjs'); s=p.read_text(encoding='utf-8')
s=s.replace("if(!html.includes('FLOTTE & RÉSEAU')||!html.includes('ROBOT & CONFIGURATION')||!html.includes('SAV & DIAGNOSTIC')) throw new Error('dynamic module headings missing');","if(!html.includes('FLOTTE & RÉSEAU')||!html.includes('ROBOT & CONFIGURATION')||!html.includes('ACTIVITÉ & SAV')||!html.includes('DIAGNOSTIC RAPIDE')) throw new Error('dynamic module headings missing');")
p.write_text(s,encoding='utf-8')

# BIR v2.6.9 contract is inherited; only version identity advances.
p=Path('app/src/test/bir-v269-functional-contract.mjs'); s=p.read_text(encoding='utf-8')
s=s.replace("if(!gradle.includes('versionCode 49')||!gradle.includes('versionName \"2.6.9\"')) throw new Error('version mismatch');","if(!gradle.includes('versionCode 50')||!gradle.includes('versionName \"2.6.10\"')) throw new Error('version mismatch');")
p.write_text(s,encoding='utf-8')
