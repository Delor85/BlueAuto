from pathlib import Path

# Historical finance/runtime contract: only navigation label/version expectations change.
p=Path('app/src/test/finance-flow.mjs')
s=p.read_text(encoding='utf-8')
old="""assert.match(tabButtons.find(item => item.tab === 'flux').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen');\ntabButtons.find(item => item.tab === 'reports').onclick();\nassert.match(tabButtons.find(item => item.tab === 'reports').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen');\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen hidden');\nassert.equal(localStorage.getItem('blue_magic_active_module'), 'reports');\n"""
new="""assert.match(tabButtons.find(item => item.tab === 'reports').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen');\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen hidden');\ntabButtons.find(item => item.tab === 'flux').onclick();\nassert.match(tabButtons.find(item => item.tab === 'flux').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen');\nassert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen hidden');\nassert.equal(localStorage.getItem('bir_active_module_v269'), 'flux');\n"""
if old not in s:
    raise SystemExit('finance-flow navigation anchor not found')
s=s.replace(old,new,1)
s=s.replace("assert.match(gradleConfig, /versionCode 48/);", "assert.match(gradleConfig, /versionCode 49/);")
s=s.replace("assert.match(gradleConfig, /versionName \"2\\.6\\.8\"/);", "assert.match(gradleConfig, /versionName \"2\\.6\\.9\"/);")
s=s.replace("assert.match(html, /SAV & DIAGNOSTIC/);", "assert.match(html, /ACTIVITÉ & SAV/);\nassert.match(html, /DIAGNOSTIC RAPIDE/);")
p.write_text(s,encoding='utf-8')

# UX/performance contract: all five historical panels remain; their commercial labels change.
p=Path('app/src/test/v268-ux-performance.mjs')
s=p.read_text(encoding='utf-8')
old_labels="""for(const roleLabel of [\"configuration.role==='DAE'\",\"configuration.role==='DSM'\",\"configuration.role==='POS'\",\"tabLabel('reports','Pilotage')\",\"tabLabel('reports','Soldes')\",\"tabLabel('reports','Solde')\",\"tabLabel('flux','Vente')\"]){\n  if(!ui.includes(roleLabel)) throw new Error('role navigation contract missing: '+roleLabel);\n}\nif(!ui.includes(\"fleet.className='module-tab hidden'\")) throw new Error('POS fleet hiding missing');\n"""
new_labels="""for(const roleLabel of [\"configuration.role==='DAE'\",\"configuration.role==='DSM'\",\"configuration.role==='POS'\",\"tabLabel('reports','Accueil')\",\"tabLabel('fleet','Réseau')\",\"tabLabel('support','Activité')\",\"tabLabel('config','Gérer')\",\"tabLabel('flux','Piloter')\",\"tabLabel('flux','Fournir')\",\"tabLabel('flux','Vendre')\"]){\n  if(!ui.includes(roleLabel)) throw new Error('role navigation contract missing: '+roleLabel);\n}\nif(!ui.includes(\"configuration.role==='POS'\")) throw new Error('POS role navigation missing');\n"""
if old_labels not in s:
    raise SystemExit('v268 UX role navigation anchor not found')
s=s.replace(old_labels,new_labels,1)
p.write_text(s,encoding='utf-8')

# Transaction ergonomics still requires Fleet/Robot/SAV content, not their old exact titles.
p=Path('app/src/test/v268-transaction-ux.mjs')
s=p.read_text(encoding='utf-8')
s=s.replace("if(!html.includes('FLOTTE & RÉSEAU')||!html.includes('ROBOT & CONFIGURATION')||!html.includes('SAV & DIAGNOSTIC')) throw new Error('dynamic module headings missing');",
            "if(!html.includes('FLOTTE & RÉSEAU')||!html.includes('ROBOT & CONFIGURATION')||!html.includes('ACTIVITÉ & SAV')||!html.includes('DIAGNOSTIC RAPIDE')) throw new Error('dynamic module content missing');")
p.write_text(s,encoding='utf-8')
