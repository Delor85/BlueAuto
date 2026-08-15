from pathlib import Path

path = Path('cloudflare/src/index.js')
s = path.read_text()
old = "    + '(a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)) '\n"
new = "    + 'AND (a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)) '\n"
if old not in s:
    raise SystemExit('FIFO activity predicate anchor missing')
s = s.replace(old, new, 1)

old_msg = "    + \"|| (snapshot.available - request.amount) || ' FCFA.' ELSE \"\n    + \"'Les demandes arrivées avant sont prioritaires. Solde encore disponible du supérieur : ' \"\n    + \"|| snapshot.available || ' FCFA.' END, \"\n"
new_msg = "    + \"|| CAST((snapshot.available - request.amount) AS INTEGER) || ' FCFA.' ELSE \"\n    + \"'Les demandes arrivées avant sont prioritaires. Solde encore disponible du supérieur : ' \"\n    + \"|| CAST(snapshot.available AS INTEGER) || ' FCFA.' END, \"\n"
if old_msg not in s:
    raise SystemExit('FIFO message formatting anchor missing')
s = s.replace(old_msg, new_msg, 1)
path.write_text(s)

# The historical integration expected every preflight to see the full certified balance.
# Under FIFO soft reservations, a later request must see the amount left after earlier AVAILABLE holds.
test = Path('cloudflare/test/integration.mjs')
t = test.read_text()
old_test = "  assert.equal(insufficient.data.capacity.available_balance, 1000);\n"
new_test = "  assert.equal(insufficient.data.capacity.available_balance, 500);\n"
if old_test not in t:
    raise SystemExit('legacy capacity assertion anchor missing')
test.write_text(t.replace(old_test, new_test, 1))

print('FIFO SQL predicate, remaining-balance formatting and legacy assertion corrected')
