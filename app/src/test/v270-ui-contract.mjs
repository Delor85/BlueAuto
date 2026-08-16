import fs from 'node:fs';
import assert from 'node:assert/strict';

const js = fs.readFileSync(new URL('../main/assets/control-tower-v2610.js', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../main/assets/control-tower-v2610.css', import.meta.url), 'utf8');
const gradle = fs.readFileSync(new URL('../../build.gradle', import.meta.url), 'utf8');

assert.match(gradle, /versionCode\s+51/);
assert.match(gradle, /versionName\s+"2\.7\.0"/);
assert.match(gradle, /applicationId\s+"com\.profitloop\.blueauto"/);

assert.match(css, /-webkit-text-fill-color:#071b3c!important/);
assert.match(css, /\.bir-keyboard-open \.bir-bottom-nav/);
assert.match(css, /\.bir-v270-modules/);
assert.match(css, /\.bir-v270-status-card/);
assert.match(css, /\.bir-v270-priority/);

assert.doesNotMatch(js, /commissionCard\([^)]+\)[\s\S]{0,220}platform\('commission_policy'/,
  'La politique de commission ne doit pas être appelée automatiquement pendant la création de la carte.');
assert.match(js, /supportsCommission/);
assert.match(js, /checkServerHealth/);
assert.match(js, /Action API inconnue\|UNKNOWN_ACTION/);
assert.match(js, /window\.AndroidBridge\.synchronizeNow/);
assert.match(js, /showResult\(cmd\)/);
assert.match(js, /BALANCE_CHILD/);
assert.match(js, /serverInfo\.commission/);
assert.match(js, /rate===null/);

console.log('B.I.R. v2.7.0 UI/compatibility contract: OK');
