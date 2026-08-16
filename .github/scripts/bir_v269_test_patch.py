from pathlib import Path
p=Path('app/src/test/finance-flow.mjs')
s=p.read_text(encoding='utf-8')
old="""assert.match(tabButtons.find(item => item.tab === 'flux').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen');\ntabButtons.find(item => item.tab === 'reports').onclick();\nassert.match(tabButtons.find(item => item.tab === 'reports').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen');\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen hidden');\nassert.equal(localStorage.getItem('blue_magic_active_module'), 'reports');\n"""
new="""assert.match(tabButtons.find(item => item.tab === 'reports').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen');\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen hidden');\ntabButtons.find(item => item.tab === 'flux').onclick();\nassert.match(tabButtons.find(item => item.tab === 'flux').className, /active/);\nassert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen');\nassert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen hidden');\nassert.equal(localStorage.getItem('bir_active_module_v269'), 'flux');\n"""
if old not in s:
    raise SystemExit('finance-flow navigation anchor not found')
p.write_text(s.replace(old,new,1),encoding='utf-8')
