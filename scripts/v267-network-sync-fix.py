from pathlib import Path

path = Path('cloudflare/src/index.js')
s = path.read_text()
fifo_old = "    + '(a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)) '\n"
fifo_new = "    + 'AND (a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)) '\n"
audit_old = "    + '(a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)'\n"
audit_new = "    + 'AND (a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)'\n"
if fifo_old not in s:
    raise SystemExit('FIFO activity predicate anchor missing')
if audit_old not in s:
    raise SystemExit('Bottom-Up freshness predicate anchor missing')
s = s.replace(fifo_old, fifo_new, 1).replace(audit_old, audit_new, 1)

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
t = t.replace(old_test, new_test, 1)

# The Bottom-Up audit intentionally queues real balance commands. Once that behavior is asserted,
# cancel only those test audit commands so they cannot perturb unrelated queue-order tests below.
audit_anchor = "  assert.ok(posAuditItem);\n  // DAE can route a PoS balance directly when the PoS/DSM Robot is unavailable; this is covered by\n"
audit_cleanup = "  assert.ok(posAuditItem);\n  await db.prepare(\"UPDATE commands SET state='CANCELLED' WHERE client_request_id LIKE 'audit_%' AND state='PENDING'\").run();\n  // DAE can route a PoS balance directly when the PoS/DSM Robot is unavailable; this is covered by\n"
if audit_anchor not in t:
    raise SystemExit('Bottom-Up integration cleanup anchor missing')
t = t.replace(audit_anchor, audit_cleanup, 1)
test.write_text(t)

print('FIFO/Bottom-Up SQL fixes and isolated audit integration test applied')
