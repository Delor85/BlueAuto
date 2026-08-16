import fs from 'node:fs';
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
const ui=fs.readFileSync('app/src/main/assets/app.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
for(const id of ['requestSupplyAmount','childAmount','retailPhone','retailAmount']){
  const at=html.indexOf('id="'+id+'"'); if(at<0) throw new Error('field missing: '+id);
  const tail=html.slice(at,at+260); if(!tail.includes('inputmode="numeric"')) throw new Error('numeric keyboard missing: '+id);
}
if(!html.includes('id="retailPhone" type="tel"')) throw new Error('phone tel semantics missing');
if(!html.includes('maxlength="9" autocomplete="tel" data-digits-only="9"')) throw new Error('phone input constraints missing');
for(const id of ['childNode','balanceChildNode','adminChildNode']){
  const at=html.indexOf('id="'+id+'"'); if(at<0||!html.slice(at,at+260).includes('data-uppercase="true"')) throw new Error('uppercase node input missing: '+id);
}
for(const contract of ['actionInFlight','initializeInputErgonomics','fieldIssue','snapshotForm','clearSubmittedFields','aria-busy']){
  if(!ui.includes(contract)) throw new Error('transaction UX contract missing: '+contract);
}
if(!ui.includes("Une commande est déjà en préparation")) throw new Error('single-flight user feedback missing');
if(!ui.includes("submitted.type==='RETAIL_SALE'")) throw new Error('success-only retail cleanup missing');
if(!html.includes('PILOTAGE & RAPPORTS')||html.includes('ONGLET 1 —')) throw new Error('obsolete numbered report heading remains');
if(!html.includes('FLOTTE & RÉSEAU')||!html.includes('ROBOT & CONFIGURATION')||!html.includes('ACTIVITÉ & SAV')||!html.includes('DIAGNOSTIC RAPIDE')) throw new Error('dynamic module headings missing');
if(!css.includes('input[aria-invalid="true"]')) throw new Error('field error styling missing');
console.log('v2.6.8 transaction UX: mobile keyboards, single-flight, focused validation and success cleanup OK');
