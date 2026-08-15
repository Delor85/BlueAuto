import fs from 'node:fs';
const ui=fs.readFileSync('app/src/main/assets/app.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
for(const tab of ['reports','fleet','flux','config','support']){
  if(!html.includes('data-tab="'+tab+'"')) throw new Error('historical module missing: '+tab);
}
for(const roleLabel of ["configuration.role==='DAE'","configuration.role==='DSM'","configuration.role==='POS'","tabLabel('reports','Pilotage')","tabLabel('reports','Soldes')","tabLabel('reports','Solde')","tabLabel('flux','Vente')"]){
  if(!ui.includes(roleLabel)) throw new Error('role navigation contract missing: '+roleLabel);
}
if(!ui.includes("fleet.className='module-tab hidden'")) throw new Error('POS fleet hiding missing');
if(ui.includes('window.setInterval(refresh,15000)')) throw new Error('legacy unconditional command polling remains');
if(ui.includes('},30000)')) throw new Error('legacy unconditional dashboard polling remains');
for(const contract of ['scheduleCommandPoll','scheduleDashboardPoll','dashboardRelevant','commandPollCursor','document.visibilityState','updateTabAttention']){
  if(!ui.includes(contract)) throw new Error('adaptive runtime contract missing: '+contract);
}
if(!css.includes('flex:1 1 0;width:auto')) throw new Error('flexible 4/5 tab dock missing');
if(!css.includes('.module-tab-attention')) throw new Error('tab attention badge styling missing');
if(!css.includes('body::before{animation:none;opacity:.42}')) throw new Error('low-end static magic mode missing');
if(!css.includes('@media(max-width:329px)')) throw new Error('ultra-narrow one-column actions missing');
if(!css.includes('.admin-actions button{width:calc(100% - 8px)}')) throw new Error('long admin actions compact fallback missing');
console.log('v2.6.8 UX/performance: role dock, adaptive polling, attention badges and low-end mode OK');
