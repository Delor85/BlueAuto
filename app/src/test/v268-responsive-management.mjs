import fs from 'node:fs';
const main=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/MainActivity.java','utf8');
const lock=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/DeviceLockState.java','utf8');
const assist=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/SimpleKeyguardAssistActivity.java','utf8');
const robot=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/RobotService.java','utf8');
const manifest=fs.readFileSync('app/src/main/AndroidManifest.xml','utf8');
if(main.includes('MATCH_PARENT, dp(260)')) throw new Error('legacy fixed 260dp management panel still present');
for(const needle of ['showManagementCenter','COMPTE & SIM','PIN CAMTEL','ROBOT & TÉLÉPHONE','FILES & SÉCURITÉ','addManagementPair']){
  if(!main.includes(needle)) throw new Error('responsive management contract missing: '+needle);
}
if(!main.includes('widthDp < 290f')) throw new Error('ultra-narrow management fallback missing');
if(!manifest.includes('.SimpleKeyguardAssistActivity')) throw new Error('simple lock assist activity not registered');
if(manifest.includes('android.permission.DISABLE_KEYGUARD')) throw new Error('deprecated DISABLE_KEYGUARD permission must stay absent');
for(const banned of ['disableKeyguard','SCREEN_BRIGHT_WAKE_LOCK','ACQUIRE_CAUSES_WAKEUP']){
  if(assist.includes(banned)||robot.includes(banned)||lock.includes(banned)) throw new Error('unsafe repeated lock mechanism: '+banned);
}
if(!assist.includes('DeviceLockState.isSecurelyLocked(this)')) throw new Error('secure-lock gate missing in assist activity');
if(!assist.includes('requestDismissKeyguard')||!assist.includes('FLAG_DISMISS_KEYGUARD')) throw new Error('versioned simple-lock dismissal path missing');
if(!robot.includes('SIMPLE_UNLOCK_COOLDOWN_MS')||!robot.includes('beginSimpleUnlockAssist')) throw new Error('bounded/cooldown simple-lock policy missing');
if(!robot.includes('contactez le titulaire/supérieur')) throw new Error('human-unlock notification missing');
console.log('v2.6.8 responsive management + bounded simple-lock assist contract OK');
