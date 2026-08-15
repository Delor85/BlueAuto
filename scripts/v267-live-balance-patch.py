from pathlib import Path


def read(path):
    return Path(path).read_text()


def write(path, value):
    Path(path).write_text(value)


def replace_once(path, old, new):
    value = read(path)
    if old not in value:
        raise SystemExit(f"anchor not found in {path}: {old[:120]!r}")
    write(path, value.replace(old, new, 1))


# ---------------------------------------------------------------------------
# D1 0004 remains the one and only new production migration for this release.
# It augments the existing 0003 account_balances state instead of creating a
# second competing balance table.
# ---------------------------------------------------------------------------
migration_path = "cloudflare/migrations/0004_blue_message_intelligence_and_modules.sql"
m = read(migration_path)
marker = "CREATE TABLE IF NOT EXISTS operator_messages ("
additions = """ALTER TABLE account_balances ADD COLUMN evidence_priority INTEGER NOT NULL DEFAULT 0;
ALTER TABLE account_balances ADD COLUMN operator_event_at TEXT;
ALTER TABLE account_balances ADD COLUMN balance_quality TEXT NOT NULL DEFAULT 'EXACT'
    CHECK (balance_quality IN ('EXACT','ESTIMATED','NEEDS_RECHECK'));
ALTER TABLE account_balances ADD COLUMN last_transaction_id TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS balance_evidence_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_code TEXT NOT NULL REFERENCES nodes(node_code) ON UPDATE CASCADE ON DELETE CASCADE,
    command_public_id TEXT REFERENCES commands(public_id) ON DELETE SET NULL,
    balance INTEGER NOT NULL CHECK (balance >= 0),
    evidence_kind TEXT NOT NULL,
    evidence_priority INTEGER NOT NULL DEFAULT 0,
    balance_quality TEXT NOT NULL DEFAULT 'EXACT',
    operator_event_at TEXT,
    transaction_id TEXT NOT NULL DEFAULT '',
    accepted INTEGER NOT NULL DEFAULT 0 CHECK (accepted IN (0,1)),
    decision_reason TEXT NOT NULL DEFAULT '',
    observed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_balance_evidence_node_time
    ON balance_evidence_log(node_code, observed_at DESC);

"""
if additions not in m:
    if marker not in m:
        raise SystemExit("0004 operator_messages anchor missing")
    m = m.replace(marker, additions + marker, 1)
receipt_index = """CREATE UNIQUE INDEX IF NOT EXISTS idx_operator_messages_receipt_unique
    ON operator_messages(node_code, receipt_number, message_kind)
    WHERE receipt_number IS NOT NULL AND length(receipt_number) > 0;
"""
if receipt_index not in m:
    anchor = "CREATE INDEX IF NOT EXISTS idx_operator_messages_node_time\n    ON operator_messages(node_code, created_at DESC);\n"
    if anchor not in m:
        raise SystemExit("operator message index anchor missing")
    m = m.replace(anchor, anchor + receipt_index, 1)
write(migration_path, m)


# ---------------------------------------------------------------------------
# Cloudflare Blue/Camtel parser: exact field messages supplied by the user.
# First mini-statement entry is explicitly the newest one.
# ---------------------------------------------------------------------------
parser_path = "cloudflare/src/blue-message.mjs"
s = read(parser_path)
s = s.replace(
    "const DATE_TIME = /(\\d{2}[-/]\\d{2}[-/]\\d{2,4})[^\\d]{0,16}(\\d{1,2}:\\d{2}(?::\\d{2})?)/i;",
    "const DATE_TIME = /(\\d{2}[-/]\\d{2}[-/]\\d{2,4})[^\\d]{0,16}(\\d{1,2}:\\d{2}(?::\\d{2})?\\s*(?:AM|PM)?)/i;",
    1,
)
s = s.replace(
    "const AMOUNT = /(?:Amount(?:\\s+is)?|Amount:|Dr:|Cr:|Transfer\\s+Balance\\s+of|Topup\\s+Amount)\\s*([0-9][0-9 .,'’]*?(?:[.,]\\d{1,2})?)\\s*(?:F\\s*CFA|FCFA|XAF)/i;",
    "const AMOUNT = /(?:Amount(?:\\s+is)?|Amount:|(?:Dr|Cr)\\s*:?|Transfer\\s+Balance\\s+of|Topup\\s+Amount)\\s*([0-9][0-9 .,'’]*?(?:[.,]\\d{1,2})?)\\s*(?:F\\s*CFA|FCFA|XAF)/i;",
    1,
)
mini_function = r'''export function parseMiniStatementEntries(raw) {
  const text = normalized(raw);
  const matches = [...text.matchAll(/ReceiptNumber[\s:#=-]*([A-Za-z0-9_-]{4,64})/ig)].slice(0, 5);
  return matches.map((match, index) => {
    const end = index + 1 < matches.length ? matches[index + 1].index : text.length;
    const segment = text.slice(match.index, end).trim();
    const route = /Airtime\s+Transfer\s+(to|by)\s+(6\d{8})(?:\s*-\s*([A-Za-z0-9_.-]+))?/i.exec(segment);
    const dc = /(?:^|\s)(Dr|Cr)\s*:?\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i.exec(segment);
    const charge = /(?:CH|TransactionCharge|Charge(?:\s+Amount)?)\s*:?\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i.exec(segment);
    const commission = /(?:CM|Commission(?:\s+Amount)?)\s*:?\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i.exec(segment);
    const tax = /Tax(?:\s+Amount)?\s*:?\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i.exec(segment);
    const date = /(\d{2}[-/]\d{2}[-/]\d{2,4})/.exec(segment);
    const status = /Status\s*\\?:\s*([A-Za-z]+)/i.exec(segment);
    return {
      position_from_newest: index + 1,
      receipt_number: match[1],
      current_balance: firstMoney(/Current\s*Balance\s*[:=]?\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i, segment),
      account_no: first(/AccountNo[\s:#=-]*([A-Za-z0-9_-]{2,64})/i, segment),
      source_phone: route?.[1]?.toLowerCase() === 'by' ? route[2] : '',
      source_node: route?.[1]?.toLowerCase() === 'by' ? (route[3] || '') : '',
      target_phone: route?.[1]?.toLowerCase() === 'to' ? route[2] : '',
      target_node: route?.[1]?.toLowerCase() === 'to' ? (route[3] || '') : '',
      transaction_date: date?.[1] || '',
      debit_credit: dc?.[1] || '',
      debit_credit_amount: dc ? parseFcfaAmount(dc[2]) : null,
      charge_amount: charge ? parseFcfaAmount(charge[1]) : null,
      commission_amount: commission ? parseFcfaAmount(commission[1]) : null,
      tax_amount: tax ? parseFcfaAmount(tax[1]) : null,
      status: status?.[1] || '',
      raw_message: segment
    };
  });
}

'''
if "export function parseMiniStatementEntries" not in s:
    anchor = "export function parseBlueMessage(raw) {"
    if anchor not in s:
        raise SystemExit("blue parser export anchor missing")
    s = s.replace(anchor, mini_function + anchor, 1)
old = "  const dt = DATE_TIME.exec(text);\n  const currentBalance = BALANCE_PATTERNS.map(pattern => firstMoney(pattern, text)).find(value => value != null) ?? null;"
new = "  const dt = DATE_TIME.exec(text);\n  const miniStatementEntries = parseMiniStatementEntries(text);\n  const currentBalance = miniStatementEntries.length && miniStatementEntries[0].current_balance != null\n    ? miniStatementEntries[0].current_balance\n    : (BALANCE_PATTERNS.map(pattern => firstMoney(pattern, text)).find(value => value != null) ?? null);"
if old not in s:
    raise SystemExit("currentBalance parser anchor missing")
s = s.replace(old, new, 1)
s = s.replace(
    "'successfully modified pin', 'successfully suspended', 'successfully reactivated', 'successfully frozen']);",
    "'successfully modified pin', 'successfully suspended', 'successfully reactivated', 'successfully frozen',\n    'top-up service', 'topup service', ' is successful']);",
    1,
)
s = s.replace(
    "else if (containsAny(lower, ['top up of', 'topup of', 'top-up'])) {",
    "else if (containsAny(lower, ['top up of', 'topup of', 'top-up', 'top-up service', 'topup service'])) {",
    1,
)
s = s.replace(
    "else if (lower.includes('transaction') && containsAny(lower, ['details', 'accountno', 'dr:', 'cr:'])) {",
    "else if (lower.includes('transaction') && (lower.includes('transaction information') || containsAny(lower, ['details', 'accountno', 'dr:', 'cr:', 'dr ', 'cr ']))) {",
    1,
)
s = s.replace(
    "  const target = /(?:to|vers)\\s+(6\\d{8})(?:\\s*-\\s*([A-Za-z0-9_.-]+))?/i.exec(text);",
    "  const target = /(?:to|vers)\\s+(6\\d{8})(?:\\s*-\\s*([A-Za-z0-9_.-]+))?/i.exec(text);\n  const topupTarget = /top-?up\\s+service\\s+for\\s+(6\\d{8})/i.exec(text);",
    1,
)
s = s.replace(
    "  const drcr = /(?:^|\\s)(Dr|Cr)\\s*:\\s*([0-9][0-9 .,'’]*?(?:[.,]\\d{1,2})?)\\s*(?:F\\s*CFA|FCFA|XAF)/i.exec(text);",
    "  const drcr = /(?:^|\\s)(Dr|Cr)\\s*:?\\s*([0-9][0-9 .,'’]*?(?:[.,]\\d{1,2})?)\\s*(?:F\\s*CFA|FCFA|XAF)/i.exec(text);",
    1,
)
s = s.replace(
    "  const charge = /(?:TransactionCharge|Charge|Fee)\\s*:\\s*",
    "  const charge = /(?:TransactionCharge|Charge(?:\\s+Amount)?|Fee|CH)\\s*:?\\s*",
    1,
)
s = s.replace(
    "  const commission = /(?:Commission)\\s*:\\s*",
    "  const commission = /(?:Commission(?:\\s+Amount)?|CM)\\s*:?\\s*",
    1,
)
s = s.replace(
    "  const tax = /(?:Tax)\\s*:\\s*",
    "  const tax = /(?:Tax(?:\\s+Amount)?)\\s*:?\\s*",
    1,
)
s = s.replace(
    "    target_phone: target?.[1] || '', target_node: target?.[2] || '', phone: firstPhone,",
    "    target_phone: target?.[1] || topupTarget?.[1] || '', target_node: target?.[2] || '', phone: firstPhone,",
    1,
)
s = s.replace(
    "    tax_amount: tax ? parseFcfaAmount(tax[1]) : null,\n    raw_message: text",
    "    tax_amount: tax ? parseFcfaAmount(tax[1]) : null,\n    mini_statement_entries: miniStatementEntries, raw_message: text",
    1,
)
write(parser_path, s)


# ---------------------------------------------------------------------------
# Canonical live balance in Worker.
# Chronology wins; source priority resolves equal/ambiguous chronology.
# ---------------------------------------------------------------------------
worker_path = "cloudflare/src/index.js"
s = read(worker_path)
priority_block = """const BALANCE_EVIDENCE_PRIORITY = Object.freeze({
  BALANCE_QUERY: 500,
  CHILD_BALANCE_QUERY: 500,
  HISTORY_RESULT: 450,
  FINANCIAL_RESULT: 400,
  TRANSACTION_DETAIL_RESULT: 300,
  ESTIMATED_TRANSFER: 100
});
"""
anchor = "const BALANCE_EVIDENCE_TTL_SECONDS = 3600;\n"
if priority_block not in s:
    if anchor not in s:
        raise SystemExit("worker TTL anchor missing")
    s = s.replace(anchor, anchor + priority_block, 1)

# Estimated post-command values stay visible but must be recertified before finance.
s = s.replace(
    "\"evidence_kind = 'ESTIMATED_TRANSFER', confidence = 'DERIVED_FROM_EXPLICIT', \"\n      + 'source_command_public_id = ?, '",
    "\"evidence_kind = 'ESTIMATED_TRANSFER', confidence = 'DERIVED_FROM_EXPLICIT', \"\n      + \"evidence_priority = 100, balance_quality = 'ESTIMATED', operator_event_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), \"\n      + 'source_command_public_id = ?, '",
)

old = """function explicitBalanceEvidence(command, message) {
  const value = parseBalanceFcfa(message);
  if (value == null) return null;
  if (command.command_kind === 'BALANCE_CHILD' && command.target_node_code) {
    return {nodeCode: command.target_node_code, value, kind: 'CHILD_BALANCE_QUERY'};
  }
  const kinds = {
    BALANCE_OWN: 'BALANCE_QUERY',
    HISTORY_LAST5: 'HISTORY_RESULT',
    TRANSACTION_DETAIL: 'TRANSACTION_DETAIL_RESULT'
  };
  if (kinds[command.command_kind]) {
    return {nodeCode: command.executor_node_code, value, kind: kinds[command.command_kind]};
  }
  if (['DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER'].includes(command.operation)) {
    return {nodeCode: command.executor_node_code, value, kind: 'FINANCIAL_RESULT'};
  }
  return null;
}
"""
new = """function explicitBalanceEvidence(command, message) {
  const parsed = parseBlueMessage(message);
  const value = parsed.current_balance;
  if (value == null) return null;
  if (command.command_kind === 'BALANCE_CHILD' && command.target_node_code) {
    return {nodeCode: command.target_node_code, value, kind: 'CHILD_BALANCE_QUERY', parsed};
  }
  const kinds = {
    BALANCE_OWN: 'BALANCE_QUERY',
    HISTORY_LAST5: 'HISTORY_RESULT',
    TRANSACTION_DETAIL: 'TRANSACTION_DETAIL_RESULT'
  };
  if (kinds[command.command_kind]) {
    return {nodeCode: command.executor_node_code, value, kind: kinds[command.command_kind], parsed};
  }
  if (['DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER'].includes(command.operation)) {
    return {nodeCode: command.executor_node_code, value, kind: 'FINANCIAL_RESULT', parsed};
  }
  return null;
}
"""
if old not in s:
    raise SystemExit("explicitBalanceEvidence anchor missing")
s = s.replace(old, new, 1)

old = """    await saveObservedBalance(env, explicitEvidence.nodeCode, explicitEvidence.value, publicId,
      explicitEvidence.kind);"""
new = """    await saveObservedBalance(env, explicitEvidence.nodeCode, explicitEvidence.value, publicId,
      explicitEvidence.kind, {
        operatorEventAt: operatorEventAt(explicitEvidence.parsed) || new Date().toISOString(),
        transactionId: explicitEvidence.parsed.transaction_id || explicitEvidence.parsed.receipt_number || '',
        passive: false
      });"""
if old not in s:
    raise SystemExit("applyTerminalEffects save anchor missing")
s = s.replace(old, new, 1)

start = s.index("async function saveObservedBalance(")
end = s.index("\nfunction parseBalanceFcfa(message)", start)
new_block = r'''function balanceEvidencePriority(kind) {
  return Number(BALANCE_EVIDENCE_PRIORITY[kind] || 0);
}

function operatorEventAt(parsed) {
  const date = String(parsed?.transaction_date || '').trim();
  const time = String(parsed?.transaction_time || '').trim();
  if (!date || !time) return '';
  const dm = /^(\d{2})[-/](\d{2})[-/](\d{2,4})$/.exec(date);
  const tm = /^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?$/i.exec(time);
  if (!dm || !tm) return '';
  let year = Number(dm[3]);
  if (year < 100) year += 2000;
  let hour = Number(tm[1]);
  const ampm = String(tm[4] || '').toUpperCase();
  if (ampm === 'PM' && hour < 12) hour += 12;
  if (ampm === 'AM' && hour === 12) hour = 0;
  // CAMTEL/Blue timestamps are Cameroon local time (UTC+1, no DST).
  const value = new Date(Date.UTC(year, Number(dm[2]) - 1, Number(dm[1]), hour - 1,
    Number(tm[2]), Number(tm[3] || 0)));
  return Number.isNaN(value.getTime()) ? '' : value.toISOString();
}

async function saveObservedBalance(env, nodeCode, value, publicId, evidenceKind, metadata = {}) {
  const priority = balanceEvidencePriority(evidenceKind);
  const incomingEventAt = cleanText(metadata.operatorEventAt, 64)
    || (metadata.passive ? '' : new Date().toISOString());
  const transactionId = cleanText(metadata.transactionId, 80);
  const current = await env.DB.prepare(
    'SELECT balance, evidence_kind, evidence_priority, operator_event_at, observed_at, balance_quality '
    + 'FROM account_balances WHERE node_code = ?'
  ).bind(nodeCode).first();
  let accepted = true;
  let reason = current ? 'NEWER_OR_STRONGER_EVIDENCE' : 'FIRST_EXPLICIT_EVIDENCE';
  if (current) {
    const currentAt = String(current.operator_event_at || current.observed_at || '');
    const incomingMs = incomingEventAt ? Date.parse(incomingEventAt) : NaN;
    const currentMs = currentAt ? Date.parse(currentAt) : NaN;
    if (Number.isFinite(incomingMs) && Number.isFinite(currentMs) && incomingMs < currentMs) {
      accepted = false;
      reason = 'STALE_OPERATOR_EVENT';
    } else if (Number.isFinite(incomingMs) && Number.isFinite(currentMs)
        && incomingMs === currentMs && priority < Number(current.evidence_priority || 0)) {
      accepted = false;
      reason = 'LOWER_PRIORITY_SAME_EVENT';
    } else if (!incomingEventAt && metadata.passive && current.balance_quality === 'EXACT') {
      accepted = false;
      reason = 'PASSIVE_EVENT_WITHOUT_SAFE_CHRONOLOGY';
    }
  }
  await env.DB.prepare(
    'INSERT INTO balance_evidence_log(node_code, command_public_id, balance, evidence_kind, '
    + 'evidence_priority, balance_quality, operator_event_at, transaction_id, accepted, decision_reason) '
    + 'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(nodeCode, publicId || null, value, evidenceKind, priority, 'EXACT',
    incomingEventAt || null, transactionId, accepted ? 1 : 0, reason).run();
  if (!accepted) return {accepted: false, reason};
  await env.DB.prepare(
    'INSERT INTO account_balances(node_code, balance, source, evidence_kind, confidence, '
    + 'source_command_public_id, evidence_command_public_id, observed_at, valid_until, '
    + 'evidence_priority, operator_event_at, balance_quality, last_transaction_id) '
    + "VALUES(?, ?, 'USSD', ?, 'OPERATOR_EXPLICIT', ?, ?, "
    + "strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), "
    + "strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+' || ? || ' seconds'), ?, ?, 'EXACT', ?) "
    + 'ON CONFLICT(node_code) DO UPDATE SET balance = excluded.balance, source = excluded.source, '
    + 'evidence_kind = excluded.evidence_kind, confidence = excluded.confidence, '
    + 'source_command_public_id = excluded.source_command_public_id, '
    + 'evidence_command_public_id = excluded.evidence_command_public_id, '
    + 'observed_at = excluded.observed_at, valid_until = excluded.valid_until, '
    + 'evidence_priority = excluded.evidence_priority, operator_event_at = excluded.operator_event_at, '
    + "balance_quality = 'EXACT', last_transaction_id = excluded.last_transaction_id, "
    + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
  ).bind(nodeCode, value, evidenceKind, publicId || null, publicId || null,
    BALANCE_EVIDENCE_TTL_SECONDS, priority, incomingEventAt || null, transactionId).run();
  return {accepted: true, reason};
}
'''
s = s[:start] + new_block + s[end:]

old = """async function recordOperatorMessageApi(env, auth, input, headers) {
  const message = cleanText(input.message, 2000);
  if (!message) throw new ApiError('MESSAGE_REQUIRED', 'Message Blue/Camtel requis.', 422);
  const parsed = await recordParsedOperatorMessage(env, auth.node_code, message, null, null, 'PASSIVE');
  if (parsed.current_balance != null) {
    const kind = parsed.kind === 'MINI_STATEMENT' ? 'HISTORY_RESULT' : 'FINANCIAL_RESULT';
    await saveObservedBalance(env, auth.node_code, parsed.current_balance, null, kind);
    await refreshWaitingPreflights(env, auth.node_code);
  }
  return success({operator_message: publicOperatorMessage(parsed)}, 201, headers);
}
"""
new = """async function recordOperatorMessageApi(env, auth, input, headers) {
  const message = cleanText(input.message, 2000);
  if (!message) throw new ApiError('MESSAGE_REQUIRED', 'Message Blue/Camtel requis.', 422);
  const parsed = await recordParsedOperatorMessage(env, auth.node_code, message, null, null, 'PASSIVE');
  // Generic balance messages are deliberately not promoted passively: Camtel uses the same wording
  // for a child balance. Command context is mandatory to distinguish own vs child balance safely.
  const passiveFinancialKinds = new Set(['TRANSFER_RECEIVED','TRANSFER_SENT','RETAIL_TOPUP_RECEIVED','RETAIL_TOPUP_SENT']);
  const promotable = parsed.kind === 'MINI_STATEMENT' || passiveFinancialKinds.has(parsed.kind);
  if (promotable && parsed.current_balance != null) {
    const kind = parsed.kind === 'MINI_STATEMENT' ? 'HISTORY_RESULT' : 'FINANCIAL_RESULT';
    const result = await saveObservedBalance(env, auth.node_code, parsed.current_balance, null, kind, {
      operatorEventAt: operatorEventAt(parsed),
      transactionId: parsed.transaction_id || parsed.receipt_number || '',
      passive: true
    });
    if (result.accepted) await refreshWaitingPreflights(env, auth.node_code);
  }
  return success({operator_message: publicOperatorMessage(parsed)}, 201, headers);
}
"""
if old not in s:
    raise SystemExit("recordOperatorMessageApi anchor missing")
s = s.replace(old, new, 1)

# Persist all five mini-statement blocks, while keeping first block as the canonical newest balance.
anchor = """  ).bind(publicId, nodeCodeValue, parsed.kind, parsed.status, tx, parsed.receipt_number,
    parsed.source_phone, parsed.source_node, parsed.target_phone, parsed.target_node,
    parsed.amount_fcfa, parsed.current_balance, parsed.account_no, parsed.transaction_date,
    parsed.transaction_time, parsed.debit_credit, parsed.charge_amount, parsed.commission_amount,
    parsed.tax_amount, cleanText(parsed.raw_message, 1800)).run();

  const financial = command && ['DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER'].includes(command.operation)
    && ['SUCCEEDED', 'UNKNOWN'].includes(commandState);"""
replacement = """  ).bind(publicId, nodeCodeValue, parsed.kind, parsed.status, tx, parsed.receipt_number,
    parsed.source_phone, parsed.source_node, parsed.target_phone, parsed.target_node,
    parsed.amount_fcfa, parsed.current_balance, parsed.account_no, parsed.transaction_date,
    parsed.transaction_time, parsed.debit_credit, parsed.charge_amount, parsed.commission_amount,
    parsed.tax_amount, cleanText(parsed.raw_message, 1800)).run();

  for (const entry of (parsed.mini_statement_entries || []).slice(0, 5)) {
    await env.DB.prepare(
      'INSERT OR IGNORE INTO operator_messages(command_public_id, node_code, message_kind, status, '
      + 'receipt_number, source_phone, source_node_code, target_phone, target_node_code, amount, '
      + 'current_balance, account_no, transaction_date, debit_credit, charge_amount, commission_amount, '
      + 'tax_amount, raw_message) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    ).bind(publicId, nodeCodeValue, 'MINI_STATEMENT_ENTRY', entry.status || 'INFO',
      entry.receipt_number || null, entry.source_phone || '', entry.source_node || '',
      entry.target_phone || '', entry.target_node || '', entry.debit_credit_amount,
      entry.current_balance, entry.account_no || '', entry.transaction_date || '',
      entry.debit_credit || '', entry.charge_amount, entry.commission_amount, entry.tax_amount,
      cleanText(entry.raw_message, 1800)).run();
  }

  const passiveFinancial = !command && ['TRANSFER_RECEIVED','TRANSFER_SENT','RETAIL_TOPUP_RECEIVED','RETAIL_TOPUP_SENT'].includes(parsed.kind)
    && parsed.status === 'SUCCEEDED';
  const financial = (command && ['DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER'].includes(command.operation)
    && ['SUCCEEDED', 'UNKNOWN'].includes(commandState)) || passiveFinancial;"""
if anchor not in s:
    raise SystemExit("recordParsedOperatorMessage anchor missing")
s = s.replace(anchor, replacement, 1)

# Only EXACT canonical evidence can authorize a new financial request.
s = s.replace(
    "'SELECT b.balance, b.observed_at, b.valid_until, b.confidence, '\n    + 'b.source_command_public_id, b.evidence_command_public_id, c.id AS source_command_id '",
    "'SELECT b.balance, b.observed_at, b.valid_until, b.confidence, b.balance_quality, b.evidence_kind, b.evidence_priority, '\n    + 'b.source_command_public_id, b.evidence_command_public_id, c.id AS source_command_id '",
    1,
)
s = s.replace(
    "|| !['OPERATOR_EXPLICIT', 'DERIVED_FROM_EXPLICIT'].includes(snapshot.confidence))) return null;",
    "|| snapshot.balance_quality !== 'EXACT'\n      || !['OPERATOR_EXPLICIT', 'DERIVED_FROM_EXPLICIT'].includes(snapshot.confidence))) return null;",
    1,
)

# For passive evidence there is no source command id. Reserve only commands created after the
# observation instead of subtracting the entire historical ledger.
old = """  const reserved = await env.DB.prepare(
    "SELECT COALESCE(SUM(amount), 0) AS total FROM commands WHERE executor_node_code = ? "
    + "AND operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
    + 'AND id > COALESCE(?, 0) '
    + "AND state NOT IN ('FAILED','CANCELLED')"
  ).bind(node, snapshot.source_command_id).first();"""
new = """  const reserved = await env.DB.prepare(
    "SELECT COALESCE(SUM(amount), 0) AS total FROM commands WHERE executor_node_code = ? "
    + "AND operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
    + 'AND ((? IS NOT NULL AND id > ?) OR (? IS NULL AND created_at > ?)) '
    + "AND state NOT IN ('FAILED','CANCELLED')"
  ).bind(node, snapshot.source_command_id, snapshot.source_command_id,
    snapshot.source_command_id, snapshot.observed_at).first();"""
if old not in s:
    raise SystemExit("effectiveAvailableBalance reservation anchor missing")
s = s.replace(old, new, 1)

# Atomic supply creation uses the same reservation rule as effectiveAvailableBalance.
old = """      + 'AND ? <= b.balance - COALESCE((SELECT SUM(reserved.amount) FROM commands reserved '
      + "WHERE reserved.executor_node_code = p.supplier_node_code "
      + "AND reserved.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
      + "AND reserved.id > COALESCE(source.id, 0) "
      + "AND reserved.state NOT IN ('FAILED','CANCELLED')), 0))"""
new = """      + 'AND ? <= b.balance - COALESCE((SELECT SUM(reserved.amount) FROM commands reserved '
      + "WHERE reserved.executor_node_code = p.supplier_node_code "
      + "AND reserved.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
      + "AND ((source.id IS NOT NULL AND reserved.id > source.id) "
      + "OR (source.id IS NULL AND reserved.created_at > b.observed_at)) "
      + "AND reserved.state NOT IN ('FAILED','CANCELLED')), 0))"""
if old not in s:
    raise SystemExit("atomic supply reservation anchor missing")
s = s.replace(old, new, 1)

# Dashboard exposes the same canonical balance and immediately usable balance used by preflight.
old = """    + 'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code, '
    + 'b.balance, b.source AS balance_source, b.observed_at, '
    + '(SELECT MAX(c.updated_at) FROM commands c WHERE c.requester_node_code = n.node_code '
    + 'OR c.executor_node_code = n.node_code OR c.target_node_code = n.node_code) AS last_activity_at, '
    + '(SELECT COUNT(*) FROM devices d WHERE d.node_code = n.node_code AND d.active = 1) AS android_devices '
    + 'FROM network x JOIN nodes n ON n.node_code = x.node_code '
    + 'LEFT JOIN account_balances b ON b.node_code = n.node_code ORDER BY n.role, n.node_code'"""
new = """    + 'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code, '
    + 'b.balance, b.source AS balance_source, b.evidence_kind, b.confidence, b.observed_at, b.valid_until, '
    + 'b.evidence_priority, b.operator_event_at, b.balance_quality, b.last_transaction_id, '
    + 'a.last_financial_activity_at, a.last_unbalanced_activity_at, '
    + "COALESCE((SELECT SUM(r.amount) FROM commands r LEFT JOIN commands src ON src.public_id = b.source_command_public_id "
    + "WHERE r.executor_node_code = n.node_code AND r.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
    + "AND ((src.id IS NOT NULL AND r.id > src.id) OR (src.id IS NULL AND r.created_at > b.observed_at)) "
    + "AND r.state NOT IN ('FAILED','CANCELLED')),0) AS reserved_amount, "
    + '(SELECT MAX(c.updated_at) FROM commands c WHERE c.requester_node_code = n.node_code '
    + 'OR c.executor_node_code = n.node_code OR c.target_node_code = n.node_code) AS last_activity_at, '
    + '(SELECT COUNT(*) FROM devices d WHERE d.node_code = n.node_code AND d.active = 1) AS android_devices '
    + 'FROM network x JOIN nodes n ON n.node_code = x.node_code '
    + 'LEFT JOIN account_balances b ON b.node_code = n.node_code '
    + 'LEFT JOIN node_activity_state a ON a.node_code = n.node_code ORDER BY n.role, n.node_code'"""
if old not in s:
    raise SystemExit("network dashboard query anchor missing")
s = s.replace(old, new, 1)
old = """    nodes: nodes.results.map(row => ({...row,
      balance: row.balance == null ? null : Number(row.balance),
      android_devices: Number(row.android_devices || 0),
      device_kind: Number(row.android_devices || 0) > 0 ? 'ANDROID' : 'NON_ENREGISTRE'
    })),"""
new = """    nodes: nodes.results.map(row => {
      const balance = row.balance == null ? null : Number(row.balance);
      const reserved = Number(row.reserved_amount || 0);
      const unbalancedAfterEvidence = Boolean(row.last_unbalanced_activity_at && row.observed_at
        && Date.parse(row.last_unbalanced_activity_at) > Date.parse(row.observed_at));
      const reusable = balance != null && row.balance_quality === 'EXACT'
        && Date.parse(row.valid_until || '') > Date.now() && !unbalancedAfterEvidence;
      return {...row, balance, reserved_amount: reserved,
        available_balance: balance == null ? null : Math.max(0, balance - reserved),
        balance_reusable: reusable,
        balance_age_seconds: row.observed_at
          ? Math.max(0, Math.floor((Date.now() - Date.parse(row.observed_at)) / 1000)) : null,
        android_devices: Number(row.android_devices || 0),
        device_kind: Number(row.android_devices || 0) > 0 ? 'ANDROID' : 'NON_ENREGISTRE'};
    }),"""
if old not in s:
    raise SystemExit("network dashboard map anchor missing")
s = s.replace(old, new, 1)
write(worker_path, s)


# ---------------------------------------------------------------------------
# Android: recognize the exact PoS receipt and safely correlate child-balance
# replies that omit the child phone. Passive exact receipts already go to D1.
# ---------------------------------------------------------------------------
android_parser_path = "app/src/main/java/com/profitloop/blueauto/BlueMessageParser.java"
s = read(android_parser_path)
s = s.replace(
    '"your transfer airtime", "top up of", "topup of", "successfully modified pin",',
    '"your transfer airtime", "top up of", "topup of", "top-up service", "topup service", " is successful", "successfully modified pin",',
    1,
)
s = s.replace(
    '} else if (containsAny(lower, "top up of", "topup of", "top-up")) {',
    '} else if (containsAny(lower, "top up of", "topup of", "top-up", "top-up service", "topup service")) {',
    1,
)
write(android_parser_path, s)

sms_path = "app/src/main/java/com/profitloop/blueauto/SmsReceiver.java"
s = read(sms_path)
old = """            String expectedPhone = active.optString("target_phone", "").replaceAll("\\D", "");
            long expectedAmount = active.optLong("amount", 0L);
            boolean correlated = expectedPhone.isEmpty() || parsed.primaryPhone.endsWith(expectedPhone)
                    || message.replaceAll("\\D", "").contains(expectedPhone);"""
new = """            String expectedPhone = active.optString("target_phone", "").replaceAll("\\D", "");
            long expectedAmount = active.optLong("amount", 0L);
            String activeOperation = UssdCommandFactory.operation(active);
            boolean targetOptional = "BALANCE_CHILD".equals(activeOperation)
                    || "INIT_CHILD_PIN_RESET".equals(activeOperation)
                    || "SUSPEND_CHILD".equals(activeOperation)
                    || "REACTIVATE_CHILD".equals(activeOperation)
                    || "FREEZE_CHILD".equals(activeOperation)
                    || "REACTIVATE_FROZEN_CHILD".equals(activeOperation);
            boolean correlated = targetOptional || expectedPhone.isEmpty() || parsed.primaryPhone.endsWith(expectedPhone)
                    || message.replaceAll("\\D", "").contains(expectedPhone);"""
if old not in s:
    raise SystemExit("SmsReceiver correlation anchor missing")
s = s.replace(old, new, 1)
old_audit = """                if (parsed.kind.equals("TRANSFER_RECEIVED") || parsed.kind.equals("MINI_STATEMENT")) {
                    RobotService.requestAudit(context, profileId);
                }
"""
if old_audit not in s:
    raise SystemExit("SmsReceiver passive audit anchor missing")
s = s.replace(old_audit, "", 1)
write(sms_path, s)


# ---------------------------------------------------------------------------
# UI: network dashboard is refreshed from D1 every 30 s while visible. This is
# a server read, never a USSD dial. It shows exact/estimated/reusable state.
# ---------------------------------------------------------------------------
app_path = "app/src/main/assets/app.js"
s = read(app_path)
old = "render();refresh();window.AndroidBridge.loadDashboard();window.setInterval(refresh,15000);"
new = """render();refresh();window.AndroidBridge.loadDashboard();window.setInterval(refresh,15000);
        window.setInterval(function(){if(document.visibilityState!=='hidden'){try{window.AndroidBridge.loadDashboard();}catch(ignored){}}},30000);
        document.addEventListener('visibilitychange',function(){if(document.visibilityState!=='hidden'){try{window.AndroidBridge.loadDashboard();}catch(ignored){}}});"""
if old not in s:
    raise SystemExit("app dashboard timer anchor missing")
s = s.replace(old, new, 1)
old = """            html+='<article class="network-item"><div><strong>'+escapeHtml(n.node_code||'—')+'</strong><span>'+escapeHtml((n.role||'—')+' • '+(n.device_kind||'—'))+'</span></div><div class="network-balance">'+(n.balance===null||typeof n.balance==='undefined'?'Non lu':formatMoney(n.balance)+' FCFA')+'</div></article>';"""
new = """            var balanceText=n.balance===null||typeof n.balance==='undefined'?'Non lu':formatMoney(n.balance)+' FCFA';
            var availableText=n.available_balance===null||typeof n.available_balance==='undefined'?'':(' • dispo '+formatMoney(n.available_balance)+' FCFA');
            var evidenceText=n.balance===null||typeof n.balance==='undefined'?'':(' • '+(n.balance_quality==='EXACT'?'confirmé':'estimé')+' / '+(n.evidence_kind||n.balance_source||'source inconnue'));
            html+='<article class="network-item"><div><strong>'+escapeHtml(n.node_code||'—')+'</strong><span>'+escapeHtml((n.role||'—')+' • '+(n.device_kind||'—')+evidenceText)+'</span></div><div class="network-balance">'+escapeHtml(balanceText+availableText)+'</div></article>';"""
if old not in s:
    raise SystemExit("app network item anchor missing")
s = s.replace(old, new, 1)
old = """        byId('ownBalance').textContent=own&&own.balance!==null?formatMoney(own.balance)+' FCFA':'À actualiser';
        byId('balanceFreshness').textContent=own&&own.observed_at?'Dernière observation : '+formatTime(own.observed_at)+' • '+(own.balance_source||'USSD'):'Aucune lecture Camtel horodatée.';"""
new = """        byId('ownBalance').textContent=own&&own.balance!==null?formatMoney(own.balance)+' FCFA':'À actualiser';
        byId('balanceFreshness').textContent=own&&own.observed_at
            ? ('Dernière observation : '+formatTime(own.observed_at)+' • '+(own.balance_quality==='EXACT'?'confirmé Camtel':'estimé')+' • '+(own.evidence_kind||own.balance_source||'source inconnue')
                +(own.available_balance!==null&&typeof own.available_balance!=='undefined'?' • disponible '+formatMoney(own.available_balance)+' FCFA':'')
                +(own.balance_reusable?' • partageable sans nouvel USSD':' • à recertifier avant finance'))
            :'Aucune lecture Camtel horodatée.';"""
if old not in s:
    raise SystemExit("app own balance anchor missing")
s = s.replace(old, new, 1)
write(app_path, s)


# ---------------------------------------------------------------------------
# Canonical parser tests from the user's field messages.
# ---------------------------------------------------------------------------
parser_test_path = "cloudflare/test/blue-message-intelligence.mjs"
s = read(parser_test_path)
s = s.replace(
    "import {parseBlueMessage, parseFcfaAmount} from '../src/blue-message.mjs';",
    "import {parseBlueMessage, parseFcfaAmount, parseMiniStatementEntries} from '../src/blue-message.mjs';",
    1,
)
extra = r'''
parsed = parseBlueMessage('Your top-up service for 620550255 on 07/07/26 02:43 PM is successful. TransactionID is 000039376500, amount is 5.00 FCFA. Now your balance is 9.00 FCFA.');
assert.equal(parsed.kind, 'RETAIL_TOPUP_SENT');
assert.equal(parsed.target_phone, '620550255');
assert.equal(parsed.amount_fcfa, 5);
assert.equal(parsed.current_balance, 9);
assert.equal(parsed.transaction_time, '02:43 PM');

const five = 'Your mini statement is: '
  + 'ReceiptNumber:000039375378 CurrentBalance:6.00 FCFA AccountNo:500000000110902045 Details: Airtime Transfer to 621081275 - POS16_DSM7_OU3 Company Airtime Account 07/07/26 Airtime Transfer Dr 3.00 FCFA CH0.00 FCFA CM0.00 FCFA Status:Completed '
  + 'ReceiptNumber:000039376351 CurrentBalance:9.00 FCFA AccountNo:500000000110902045 Details: Airtime Transfer to 621081275 - POS16_DSM7_OU3 Company Airtime Account 07/07/26 Airtime Transfer Dr 1.00 FCFA CH0.00 FCFA CM0.00 FCFA Status:Completed '
  + 'ReceiptNumber:000039376331 CurrentBalance:10.00 FCFA AccountNo:500000000110902045 Details: Airtime Transfer to 621081275 - POS16_DSM7_OU3 Company Airtime Account 07/07/26 Airtime Transfer Dr 1.00 FCFA CH0.00 FCFA CM0.00 FCFA Status:Completed '
  + 'ReceiptNumber:000039375343 CurrentBalance:11.00 FCFA AccountNo:500000000110902045 Details: Airtime Transfer to 621081275 - POS16_DSM7_OU3 Company Airtime Account 07/07/26 Airtime Transfer Dr 2.00 FCFA CH0.00 FCFA CM0.00 FCFA Status:Completed '
  + 'ReceiptNumber:000039376308 CurrentBalance:13.00 FCFA AccountNo:500000000110902045 Details: Airtime Transfer to 621081275 - POS16_DSM7_OU3 Company Airtime Account 07/07/26 Airtime Transfer Dr 1.00 FCFA CH0.00 FCFA CM0.00 FCFA Status:Completed';
const entries = parseMiniStatementEntries(five);
assert.equal(entries.length, 5);
assert.equal(entries[0].receipt_number, '000039375378');
assert.equal(entries[0].current_balance, 6);
assert.equal(entries[0].debit_credit, 'Dr');
assert.equal(entries[0].debit_credit_amount, 3);
assert.equal(parseBlueMessage(five).current_balance, 6);
'''
anchor = "parsed = parseBlueMessage('Request is processed successfully.');"
if extra not in s:
    if anchor not in s:
        raise SystemExit("parser test anchor missing")
    s = s.replace(anchor, extra + "\n" + anchor, 1)
write(parser_test_path, s)


# ---------------------------------------------------------------------------
# Integration tests: old delayed SMS cannot regress a newer canonical balance;
# generic child-balance wording is never passively attributed to DAE; active
# CHILD_BALANCE updates only child; DSM reuses DAE canonical balance.
# ---------------------------------------------------------------------------
integration_path = "cloudflare/test/integration.mjs"
s = read(integration_path)
anchor = "  const raceOne = await request('check_purchase_capacity', {\n"
extra = r'''  const exactHistoryMessage = 'Your mini statement is: '
    + 'ReceiptNumber:900001 CurrentBalance:880.00 FCFA AccountNo:500001 Details: Airtime Transfer to 699000002 - DSM-TEST Company Airtime Account 15/08/26 Airtime Transfer Dr 20.00 FCFA CH0.00 FCFA CM0.00 FCFA Status:Completed '
    + 'ReceiptNumber:900000 CurrentBalance:900.00 FCFA AccountNo:500001 Details: Airtime Transfer to 699000002 - DSM-TEST Company Airtime Account 15/08/26 Airtime Transfer Dr 10.00 FCFA CH0.00 FCFA CM0.00 FCFA Status:Completed';
  const liveHistory = await request('create_command', {
    request_type: 'LAST_TRANSACTIONS', client_request_id: 'integration-live-history-priority-01'
  }, dae.data.device_token);
  const liveHistoryLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(liveHistoryLease.data.command.public_id, liveHistory.data.command.public_id);
  await complete(liveHistoryLease.data.command, dae.data.device_token, exactHistoryMessage);
  let liveDashboard = await request('network_dashboard', {}, dae.data.device_token);
  let liveDae = liveDashboard.data.nodes.find(node => node.node_code === 'DAE-TEST');
  assert.equal(liveDae.balance, 880);
  assert.equal(liveDae.evidence_kind, 'HISTORY_RESULT');
  assert.equal(liveDae.balance_quality, 'EXACT');
  assert.equal(liveDae.balance_reusable, true);

  await request('record_operator_message', {
    message: 'Your Transfer Airtime to 699000002 - DSM-TEST has been successfully processed.Amount is 5.00 FCFA. Now your balance is 100.00 FCFA. TransactionID 000039365092, 07-07-2026 at 12:14:09.'
  }, dae.data.device_token);
  liveDashboard = await request('network_dashboard', {}, dae.data.device_token);
  liveDae = liveDashboard.data.nodes.find(node => node.node_code === 'DAE-TEST');
  assert.equal(liveDae.balance, 880);

  await request('record_operator_message', {
    message: 'Your available voucher stock is: 15.00 FCFA; Uncleared balance: 0.00 FCFA; Reserved balance: 0.00 FCFA; Current balance: 15.00 FCFA.'
  }, dae.data.device_token);
  liveDashboard = await request('network_dashboard', {}, dae.data.device_token);
  assert.equal(liveDashboard.data.nodes.find(node => node.node_code === 'DAE-TEST').balance, 880);

  const childBalance = await request('create_command', {
    request_type: 'CHILD_BALANCE', target_node_code: 'DSM-TEST',
    client_request_id: 'integration-child-balance-attribution-01'
  }, dae.data.device_token);
  const childBalanceLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(childBalanceLease.data.command.public_id, childBalance.data.command.public_id);
  await complete(childBalanceLease.data.command, dae.data.device_token,
    'Your available voucher stock is: 123.00 FCFA; Uncleared balance: 0.00 FCFA; Reserved balance: 0.00 FCFA; Current balance: 123.00 FCFA.');
  liveDashboard = await request('network_dashboard', {}, dae.data.device_token);
  assert.equal(liveDashboard.data.nodes.find(node => node.node_code === 'DAE-TEST').balance, 880);
  assert.equal(liveDashboard.data.nodes.find(node => node.node_code === 'DSM-TEST_DAE-TEST').balance, 123);

  const sharedBalance = await request('check_purchase_capacity', {
    request_type: 'REQUEST_SUPPLY', amount: '100',
    client_request_id: 'integration-shared-live-balance-01'
  }, dsm.data.device_token);
  assert.equal(sharedBalance.data.capacity.state, 'AVAILABLE');
  assert.equal(sharedBalance.data.capacity.balance_reused, true);
  assert.equal(sharedBalance.data.capacity.available_balance, 880);

'''
if extra not in s:
    if anchor not in s:
        raise SystemExit("integration race anchor missing")
    s = s.replace(anchor, extra + anchor, 1)
write(integration_path, s)


# Static Android/UI guards.
finance_test_path = "app/src/test/finance-flow.mjs"
s = read(finance_test_path)
anchor = "console.log('Blue Magic v2.6.7 platform extension: UI/modules/message parser wired');"
extra = r'''
const uiRuntime = readFileSync(new URL('../main/assets/app.js', import.meta.url), 'utf8');
assert.match(uiRuntime, /30000/);
assert.match(uiRuntime, /balance_reusable/);
assert.match(uiRuntime, /partageable sans nouvel USSD/);
assert.match(messageParser, /top-up service/);
const smsReceiver = readFileSync(new URL('../main/java/com/profitloop/blueauto/SmsReceiver.java', import.meta.url), 'utf8');
assert.match(smsReceiver, /targetOptional/);
assert.doesNotMatch(smsReceiver, /RobotService\.requestAudit\(context, profileId\)/);
'''
if extra not in s:
    if anchor not in s:
        raise SystemExit("finance-flow final anchor missing")
    s = s.replace(anchor, extra + "\n" + anchor, 1)
write(finance_test_path, s)

print("Blue Magic v2.6.7 live balance patch applied")
