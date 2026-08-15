from pathlib import Path

p = Path('app/src/test/finance-flow.mjs')
s = p.read_text()
old = "assert.match(uiRuntime, /30000/);"
new = """assert.match(uiRuntime, /scheduleCommandPoll/);
assert.match(uiRuntime, /scheduleDashboardPoll/);
assert.match(uiRuntime, /60000/);
assert.match(uiRuntime, /visibilityState/);
assert.doesNotMatch(uiRuntime, /setInterval\\(refresh,15000\\)/);"""
if old not in s:
    raise SystemExit('legacy 30-second dashboard contract anchor missing')
p.write_text(s.replace(old, new, 1))
