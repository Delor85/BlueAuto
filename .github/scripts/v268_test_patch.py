from pathlib import Path

# Full v2.6.7 integration suite is restored by workflow before this script.
p = Path('cloudflare/test/integration.mjs')
s = p.read_text()
old = "'0003_balance_preflight_and_modules.sql', '0004_blue_message_intelligence_and_modules.sql']"
new = "'0003_balance_preflight_and_modules.sql', '0004_blue_message_intelligence_and_modules.sql',\n    '0005_commission_policies_and_financial_quotes.sql']"
if old not in s:
    raise SystemExit('migration fixture anchor missing')
p.write_text(s.replace(old, new, 1))

p = Path('app/src/test/finance-flow.mjs')
s = p.read_text()
old = """assert.ok(service.indexOf('prepareSystemUssdSurface(needsWakeSettle)')
  < service.indexOf('SimCallManager.placeUssdCall(this, ussd, profileId)'));
assert.match(service, /SYSTEM_USSD_SCREEN_WAKE_MS = 45_000L/);
assert.match(service, /InsecureKeyguardDismissActivity\\.class/);
assert.doesNotMatch(service, /new Intent\\(this, MainActivity\\.class\\)[\\s\\S]{0,180}PREPARE_INSECURE_USSD/);
assert.doesNotMatch(service, /\"PIN_SUBMITTED\"\\.equals\\(state\\)\\) releaseCommandScreenWakeLock/);"""
new = """assert.match(service, /DeviceLockState\\.blocksUssd\\(this\\)/);
assert.ok(service.indexOf('DeviceLockState.blocksUssd(this)')
  < service.indexOf('SimCallManager.placeUssdCall(this, ussd, profileId)'));
assert.doesNotMatch(service, /prepareSystemUssdSurface/);
assert.doesNotMatch(service, /SYSTEM_USSD_SCREEN_WAKE_MS/);
assert.doesNotMatch(service, /InsecureKeyguardDismissActivity/);
assert.doesNotMatch(service, /SCREEN_BRIGHT_WAKE_LOCK|ACQUIRE_CAUSES_WAKEUP|disableKeyguard/);"""
if old not in s:
    raise SystemExit('legacy lock contract anchor missing')
s = s.replace(old, new, 1)
s = s.replace('assert.match(gradleConfig, /versionCode 47/);',
              'assert.match(gradleConfig, /versionCode 48/);')
s = s.replace('assert.match(gradleConfig, /versionName "2\\.6\\.7"/);',
              'assert.match(gradleConfig, /versionName "2\\.6\\.8"/);')
p.write_text(s)
