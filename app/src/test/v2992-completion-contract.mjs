import fs from 'node:fs';
import assert from 'node:assert/strict';

const read = p => fs.readFileSync(p, 'utf8');
const gradle = read('app/build.gradle');
const manifest = read('app/src/main/AndroidManifest.xml');
const loader = read('app/src/main/assets/intelligence-v297.js');
const js = read('app/src/main/assets/field-runtime-v2992.js');
const css = read('app/src/main/assets/field-runtime-v2992.css');
const v30 = read('app/src/main/res/values-v30/bir_rendering.xml');
const v31 = read('app/src/main/res/values-v31/bir_rendering.xml');
const baseBool = read('app/src/main/res/values/bir_rendering.xml');
const robot = read('app/src/main/java/com/profitloop/blueauto/RobotService.java');
const api = read('app/src/main/java/com/profitloop/blueauto/ApiClient.java');

assert.match(gradle, /versionCode\s+66\b/);
assert.match(gradle, /versionName\s+"2\.9\.9\.2"/);
assert.match(loader, /field-runtime-v2992\.css/);
assert.match(loader, /field-runtime-v2992\.js/);
assert.match(loader, /This loader does not create a second assistant or polling loop/);

// Android 11 is isolated from the hardware compositor only on API30.
assert.match(manifest, /android:hardwareAccelerated="@bool\/bir_main_hardware_accelerated"/);
assert.match(baseBool, /bir_main_hardware_accelerated">true</);
assert.match(v30, /bir_main_hardware_accelerated">false</);
assert.match(v31, /bir_main_hardware_accelerated">true</);
assert.match(css, /body\.bir-v2992-api30 main\{padding-bottom:12px!important/);
assert.match(css, /\.module-screen\.hidden/);

// Tchoronko is a real DAE/DSM child-account flow backed by existing production actions.
assert.match(js, /shadow_enroll/);
assert.match(js, /platform_snapshot/);
assert.match(js, /network_balance_audit/);
assert.match(js, /TCHORONKO/);
assert.match(js, /CHECK RÉSEAU/);
assert.match(js, /INACTIF >48H/);
assert.match(js, /STOCK FAIBLE/);
assert.match(js, /findByPhone/);
assert.match(api, /shadow_enroll/);
assert.match(api, /platform_snapshot/);
assert.match(api, /network_balance_audit/);

// No second finance engine, no raw-USSD bypass, no new permanent polling loop, no Mercenaires exposure.
assert.doesNotMatch(js, /createCommand|previewCommand|create_command|preview_command/);
assert.doesNotMatch(js, /setInterval\s*\(/);
assert.doesNotMatch(js, /\*550|\*825/);
assert.doesNotMatch(js, /mercenary|mercenaire/i);
assert.doesNotMatch(js, /\b(?:const|let)\b|=>/);

// Historical Remote cadence remains the only persistent Remote snapshot cadence.
assert.match(robot, /REMOTE_SNAPSHOT_MS\s*=\s*10_000L/);

console.log('BIR 2.9.9.2 completion contract: OK');
