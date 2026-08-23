import fs from 'node:fs';
const read=p=>fs.readFileSync(p,'utf8');
const must=(c,m)=>{if(!c)throw new Error(m);};
const shim=read('app/src/main/assets/intelligence-v297.js');
const js=read('app/src/main/assets/transaction-first-v298.js');
const css=read('app/src/main/assets/transaction-first-v298.css');
const field=read('app/src/main/assets/field-ops-v297.js');

must(field.includes("s.src='intelligence-v297.js'"),'field-ops compatibility loader missing');
must(shim.includes("transaction-first-v298.css")&&shim.includes("transaction-first-v298.js"),'v2.9.8 reference layer not loaded');
must(shim.includes('does not create a second assistant or polling loop'),'single-assistant consolidation note missing');
must(!/\b(?:const|let)\b|=>/.test(js),'Android 6 Transaction-First layer must remain ES5-compatible');
must(!/createCommand\s*\(|previewCommand\s*\(/.test(js),'Transaction-First layer must never bypass historical financial engine');
must(!/setInterval\s*\(/.test(js),'Transaction-First layer must reuse existing 10 s observer, not stack another loop');
for(const token of ['VENDRE DU CRÉDIT BLUE','ACHETER DU CRÉDIT BLUE','APPROVISIONNER UN PoS','APPROVISIONNER UN DSM','Dernier solde Blue connu','ASSISTANT B.I.R.','VOIR LA WAR ROOM']) must(js.includes(token),'missing reference UI token: '+token);
must(css.includes('.bir-v298-transaction')&&css.includes('.bir-v298-situation'),'reference CSS missing');
console.log('BIR v2.9.7 Intelligence compatibility -> v2.9.8 Transaction-First reference OK');
