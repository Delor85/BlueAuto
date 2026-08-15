from pathlib import Path

# This patch runs after v268_responsive_manage_lock_patch.py inside CI.
# It preserves historical semantic contracts while pointing the old full test at the safer helper.
p = Path('app/src/main/java/com/profitloop/blueauto/MainActivity.java')
s = p.read_text()
s = s.replace('managementActionButton("🔁 CHANGER PIN CAMTEL", CYAN)',
              'managementActionButton("🔁 MODIFIER LE PIN CAMTEL", CYAN)', 1)
s = s.replace('managementActionButton("✓ AUTORISATIONS", GOLD)',
              'managementActionButton("1. AUTORISATIONS", GOLD)', 1)
p.write_text(s)

p = Path('app/src/test/finance-flow.mjs')
s = p.read_text()
old = '''const unlockActivity = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/InsecureKeyguardDismissActivity.java', import.meta.url), 'utf8');
assert.match(unlockActivity, /requestDismissKeyguard/);
assert.match(unlockActivity, /finishAndRemoveTask/);'''
new = '''const unlockActivity = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/SimpleKeyguardAssistActivity.java', import.meta.url), 'utf8');
assert.match(unlockActivity, /requestDismissKeyguard/);
assert.match(unlockActivity, /DeviceLockState\.isSecurelyLocked/);
assert.match(unlockActivity, /finishQuietly/);
assert.doesNotMatch(unlockActivity, /disableKeyguard/);'''
if old not in s:
    raise SystemExit('historical keyguard test anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)
