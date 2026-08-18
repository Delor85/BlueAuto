import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

const main = await readFile(new URL('../main/java/com/profitloop/blueauto/MainActivity.java', import.meta.url), 'utf8');
const service = await readFile(new URL('../main/java/com/profitloop/blueauto/RobotService.java', import.meta.url), 'utf8');
const readiness = await readFile(new URL('../main/java/com/profitloop/blueauto/RobotReadiness.java', import.meta.url), 'utf8');
const html = await readFile(new URL('../main/assets/index.html', import.meta.url), 'utf8');
const js = await readFile(new URL('../main/assets/app.js', import.meta.url), 'utf8');

assert.match(main, /REMOTE/);
assert.match(main, /ROBOT/);
assert.match(service, /leaseCommand/);
assert.match(service, /commandEvent/);
assert.match(service, /releaseCommand/);
assert.match(service, /DeviceLockState\.blocksUssd\(this\)/);
assert.ok(service.indexOf('DeviceLockState.blocksUssd(this)')
  < service.indexOf('SimCallManager.placeUssdCall(this, ussd, profileId)'));
assert.doesNotMatch(service, /prepareSystemUssdSurface/);
assert.doesNotMatch(service, /SYSTEM_USSD_SCREEN_WAKE_MS/);
assert.doesNotMatch(service, /InsecureKeyguardDismissActivity/);
assert.doesNotMatch(service, /SCREEN_BRIGHT_WAKE_LOCK|ACQUIRE_CAUSES_WAKEUP|disableKeyguard/);
assert.doesNotMatch(readiness, /verifyCallRoute/);

const manifest = await readFile(new URL('../main/AndroidManifest.xml', import.meta.url), 'utf8');
assert.match(manifest, /foregroundServiceType="dataSync\|specialUse"/);

const gradleConfig = await readFile(new URL('../../build.gradle', import.meta.url), 'utf8');
assert.match(gradleConfig, /minSdk 23/);
assert.match(gradleConfig, /versionCode (?:51|52|53|54|55)/);
assert.match(gradleConfig, /versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1)|2\.9\.0)"/);
assert.match(gradleConfig, /release \{[\s\S]*signingConfig signingConfigs\.pilotDebug/);

const apiClient = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/ApiClient.java', import.meta.url), 'utf8');
assert.match(apiClient, /replace_device_id/);
assert.match(apiClient, /repair_sim_fingerprint/);
assert.match(apiClient, /replace_verified_same_sim_robot/);

const appConfig = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/AppConfig.java', import.meta.url), 'utf8');
assert.match(appConfig, /profileIds/);
assert.match(appConfig, /activeProfileId/);
assert.match(appConfig, /slotIndex/);
assert.match(appConfig, /simSubscriptionId/);
assert.match(appConfig, /isRobotMode/);

assert.match(html, /Blue Infinity Retail|Blue Magic/i);
assert.match(js, /requestSupply|SUPPLY_CHILD|RETAIL_SALE|TEST_NUMBER/);

console.log('Finance flow contract OK');
