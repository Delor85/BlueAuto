from pathlib import Path

path = Path('cloudflare/src/index.js')
s = path.read_text()
old = "    + '(a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)) '\n"
new = "    + 'AND (a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)) '\n"
if old not in s:
    raise SystemExit('FIFO activity predicate anchor missing')
path.write_text(s.replace(old, new, 1))
print('FIFO SQL predicate corrected')
