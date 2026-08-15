import fs from 'node:fs';
const robot=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/RobotService.java','utf8');
const lock=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/DeviceLockState.java','utf8');
const policy=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/CommandExecutionPolicy.java','utf8');
const ui=fs.readFileSync('app/src/main/assets/app.js','utf8');
const worker=fs.readFileSync('cloudflare/src/index.js','utf8');
for(const banned of ['disableKeyguard','SCREEN_BRIGHT_WAKE_LOCK','ACQUIRE_CAUSES_WAKEUP','dismissInsecureKeyguard']){
  if(robot.includes(banned)||lock.includes(banned)) throw new Error('forbidden keyguard mechanism: '+banned);
}
if(!robot.includes('DeviceLockState.blocksUssd(this)')) throw new Error('locked-screen USSD gate missing');
if(!policy.includes('needsAccessibility(operation)')||!policy.includes('return isFinancial(operation)')) throw new Error('direct PIN commands still tied to Accessibility');
if(ui.includes('Solde cumulé connu')) throw new Error('aggregate balance label still exposed');
if(!ui.includes('Réservé : ')||!ui.includes('Solde Camtel : ')) throw new Error('balance/reservation separation missing');
if(!worker.includes('commissionRateFor')||!worker.includes('commission_amount')||!worker.includes('requested_base_amount')) throw new Error('commission quote persistence missing');
console.log('v2.6.8 field contract: lock safety, direct PIN, balances and commissions OK');
