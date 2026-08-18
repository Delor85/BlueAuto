import fs from 'node:fs';
function read(p){return fs.readFileSync(p,'utf8');}
function need(v, token, label){if(!v.includes(token)) throw new Error('Missing '+label+': '+token);}
const gradle=read('app/build.gradle');
const main=read('app/src/main/java/com/profitloop/blueauto/MainActivity.java');
const appConfig=read('app/src/main/java/com/profitloop/blueauto/AppConfig.java');
const robot=read('app/src/main/java/com/profitloop/blueauto/RobotService.java');
const boot=read('app/src/main/java/com/profitloop/blueauto/BootReceiver.java');
const access=read('app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java');
const js=read('app/src/main/assets/control-tower-v280.js');
if(!(gradle.includes('versionCode 54')||gradle.includes('versionCode 55'))) throw new Error('Missing release identity: vc54/vc55'); if(!(gradle.includes('versionName \"2.8.1\"')||gradle.includes('versionName \"2.9.0\"'))) throw new Error('Missing release identity: v2.8.1/v2.9.0');
need(main,'OWNER_SESSION_IDLE_MS = 30L * 60_000L','30-minute owner timeout');
need(main,'MOCK_PROFILE_ID.equals(selected)','MOCK virtual account row');
need(main,'ADMIN_PROFILE_ID.equals(selected)','ADMIN virtual account row');
need(main,'openOwnerVirtualAccount','owner reauthentication');
need(main,'Build.VERSION.SDK_INT <= Build.VERSION_CODES.O','Android 6/8 native Manage fallback');
need(main,'compactBar.addView(manageButton, weighted())','Manage top-left first');
need(main,'AppConfig.anyRobotEnabled(this) || AppConfig.anyRemoteProfile(this)','Remote resume observer');
need(main,'RobotService.cachedRemoteDashboard','Remote local cache');
need(appConfig,'remoteProfileIds','Remote profile selection');
need(robot,'REMOTE_SNAPSHOT_MS = 15_000L','adaptive Remote snapshot');
need(robot,'api.dashboard()','Remote read-only dashboard');
need(robot,'accessibilityReadyFor','Accessibility runtime guard');
need(robot,'Accessibilité en reconnexion','automatic accessibility recovery status');
need(robot,'|| AppConfig.anyRemoteProfile(this)','Remote service persistence');
need(boot,'!AppConfig.anyRobotEnabled(context) && !AppConfig.anyRemoteProfile(context)','boot Remote observer');
need(access,'RobotService.forceSync(this)','accessibility reconnect wake');
need(js,'v280AdminAccounts','ADMIN account switch');
need(js,'30 minutes d’inactivité','owner bilingual lock wording');
if(robot.includes('Settings.Secure.put')||access.includes('Settings.Secure.put')) throw new Error('Forbidden accessibility privilege escalation');
if(robot.includes('leaseCommand();') && !robot.includes('Read-only Remote observer')) { throw new Error('Remote observer boundary missing'); }
console.log('BIR v2.8.1 field-quality contract: OK');
