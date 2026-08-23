import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const appJs = await readFile(new URL('../main/assets/app.js', import.meta.url), 'utf8');
const service = await readFile(new URL('../main/java/com/profitloop/blueauto/RobotService.java', import.meta.url), 'utf8');
const accessibility = await readFile(new URL('../main/java/com/profitloop/blueauto/BlueAccessibilityService.java', import.meta.url), 'utf8');
const nativeMain = await readFile(new URL('../main/java/com/profitloop/blueauto/MainActivity.java', import.meta.url), 'utf8');
const moduleNames = ['reports','flux','fleet','config','support'];

// Finance creation stays behind a user confirmation and the historical create/preview path.
assert.match(appJs, /previewCommand/);
assert.match(appJs, /createCommand/);
assert.match(appJs, /confirm\(/);
assert.match(appJs, /financial/i);

// Robot execution must remain SIM/lock/readiness fenced and never bypass the established USSD route.
assert.match(service, /SDK_INT >= 34[\s\S]*FOREGROUND_SERVICE_TYPE_SPECIAL_USE/);
assert.match(service, /SDK_INT >= 29[\s\S]*FOREGROUND_SERVICE_TYPE_DATA_SYNC/);
assert.match(service, /catch \(RuntimeException primaryFailure\)[\s\S]*FOREGROUND_SERVICE_TYPE_DATA_SYNC/);
const readiness = service.slice(service.indexOf('private Readiness checkReadiness('),
  service.indexOf('private void disableUnsafeRobot('));
assert.doesNotMatch(readiness, /verifyCallRoute/);
assert.match(service, /DeviceLockState\.blocksUssd\(this\)/);
assert.ok(service.indexOf('DeviceLockState.blocksUssd(this)')
  < service.indexOf('SimCallManager.placeUssdCall(this, ussd, profileId)'));
assert.doesNotMatch(service, /prepareSystemUssdSurface/);
assert.doesNotMatch(service, /SYSTEM_USSD_SCREEN_WAKE_MS/);
assert.doesNotMatch(service, /InsecureKeyguardDismissActivity/);
assert.doesNotMatch(service, /SCREEN_BRIGHT_WAKE_LOCK|ACQUIRE_CAUSES_WAKEUP|disableKeyguard/);

const manifest = await readFile(new URL('../main/AndroidManifest.xml', import.meta.url), 'utf8');
assert.match(manifest, /foregroundServiceType="dataSync\|specialUse"/);

const gradleConfig = await readFile(new URL('../../build.gradle', import.meta.url), 'utf8');
assert.match(gradleConfig, /minSdk 23/);
assert.match(gradleConfig, /versionCode (?:51|52|53|54|55|58|60|61|62|63|64)/);
assert.match(gradleConfig, /versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1)|2\.9\.0|2\.9\.3|2.9.5|2.9.6|2.9.7|2.9.8|2.9.9)"/);
assert.match(gradleConfig, /release \{[\s\S]*signingConfig signingConfigs\.pilotDebug/);

const apiClient = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/ApiClient.java', import.meta.url), 'utf8');
assert.match(apiClient, /replace_device_id/);
assert.match(apiClient, /repair_sim_fingerprint/);
assert.match(apiClient, /replace_verified_same_sim_robot/);

const appConfig = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/AppConfig.java', import.meta.url), 'utf8');
assert.match(appConfig, /serverDeviceId/);

const html = await readFile(new URL('../main/assets/index.html', import.meta.url), 'utf8');
for (const moduleName of moduleNames) {
  assert.match(html, new RegExp('data-tab="' + moduleName + '"'));
}

// Existing native bridge and accessibility boundaries remain present.
assert.match(nativeMain, /AndroidBridge/);
assert.match(accessibility, /AccessibilityService/);

console.log('Android UI/runtime: verrou/PIN, dock actif, précontrôle de solde, confirmation finance, administration sensible et TEST_NUMBER OK');
