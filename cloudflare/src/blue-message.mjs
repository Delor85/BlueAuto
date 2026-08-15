const MONEY_LIMIT = 9_999_999_999;

export function parseFcfaAmount(raw) {
  if (raw == null) return null;
  let value = String(raw).trim().replace(/[\u00a0\u202f\s]/g, '').replace(/’/g, "'");
  if (!value) return null;
  const dot = value.lastIndexOf('.');
  const comma = value.lastIndexOf(',');
  const decimal = Math.max(dot, comma);
  let normalized;
  if (decimal >= 0 && value.length - decimal - 1 <= 2) {
    const whole = value.slice(0, decimal).replace(/\D/g, '') || '0';
    const fraction = value.slice(decimal + 1).replace(/\D/g, '') || '0';
    normalized = `${whole}.${fraction}`;
  } else {
    normalized = value.replace(/\D/g, '');
  }
  if (!normalized) return null;
  const parsed = Math.floor(Number(normalized));
  return Number.isSafeInteger(parsed) && parsed >= 0 && parsed <= MONEY_LIMIT ? parsed : null;
}

function normalized(raw) {
  return String(raw || '').replace(/[\u00a0\u202f]/g, ' ').replace(/[\r\n]+/g, ' ')
    .replace(/\s+/g, ' ').trim();
}

function first(pattern, text, group = 1) {
  const match = pattern.exec(text);
  return match ? String(match[group] || '').trim() : '';
}

function firstMoney(pattern, text) {
  const value = first(pattern, text);
  return value ? parseFcfaAmount(value) : null;
}

function containsAny(lower, values) { return values.some(value => lower.includes(value)); }

const TX_ID = /(?:TransactionID|Transaction\s*ID|Trans\s*ID|Ref(?:erence)?)[\s:#=-]*([A-Za-z0-9_-]{5,64})/i;
const RECEIPT = /ReceiptNumber[\s:#=-]*([A-Za-z0-9_-]{4,64})/i;
const ACCOUNT = /AccountNo[\s:#=-]*([A-Za-z0-9_-]{2,64})/i;
const PHONE = /(?:^|\D)(6\d{8})(?!\d)/;
const DATE_TIME = /(\d{2}[-/]\d{2}[-/]\d{2,4})[^\d]{0,16}(\d{1,2}:\d{2}(?::\d{2})?)/i;
const AMOUNT = /(?:Amount(?:\s+is)?|Amount:|Dr:|Cr:|Transfer\s+Balance\s+of|Topup\s+Amount)\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i;
const BALANCE_PATTERNS = [
  /Current\s*Balance\s*[:=]?\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i,
  /Now\s+your\s+balance\s+is\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i,
  /(?:Available|Remaining)\s+Balance\s*(?:is|:|=)?\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i,
  /Your\s+available\s+voucher\s+stock\s+is\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i,
  /(?:votre\s+)?solde(?:\s+(?:actuel|disponible|restant))?\s*(?:est(?:\s+de)?|:|=)\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i
];

export function parseBlueMessage(raw) {
  const text = normalized(raw);
  const lower = text.toLowerCase();
  const dt = DATE_TIME.exec(text);
  const currentBalance = BALANCE_PATTERNS.map(pattern => firstMoney(pattern, text)).find(value => value != null) ?? null;
  const processing = containsAny(lower, ['request is processed successfully', 'request is being processed',
    'requête est en cours', 'requete est en cours', 'processing request']);
  const wrongPin = containsAny(lower, ['incorrect pin', 'pin incorrect', 'wrong pin', 'invalid pin']);
  const failure = !processing && containsAny(lower, ['failed', 'failure', 'not successful', 'declined',
    'insufficient', 'unable to', 'cannot', 'error', 'erreur']);
  let success = !processing && !wrongPin && containsAny(lower, ['successfully processed', 'has been successful',
    'status:completed', 'you received airtime', 'your transfer airtime', 'top up of', 'topup of',
    'successfully modified pin', 'successfully suspended', 'successfully reactivated', 'successfully frozen']);
  let kind = 'UNKNOWN';
  let status = failure ? 'FAILED' : (success ? 'SUCCEEDED' : 'INFO');
  if (wrongPin) { kind = 'WRONG_PIN'; status = 'BLOCKED'; }
  else if (processing) { kind = 'REQUEST_ACK'; status = 'PROCESSING'; }
  else if (lower.includes('you received airtime') || lower.includes('has received airtime')) { kind = 'TRANSFER_RECEIVED'; status = failure ? 'FAILED' : 'SUCCEEDED'; success = !failure; }
  else if (lower.includes('your transfer airtime to') || lower.includes('transfer airtime to')) { kind = 'TRANSFER_SENT'; status = failure ? 'FAILED' : 'SUCCEEDED'; success = !failure; }
  else if (containsAny(lower, ['top up of', 'topup of', 'top-up'])) { kind = lower.includes('received') ? 'RETAIL_TOPUP_RECEIVED' : 'RETAIL_TOPUP_SENT'; status = failure ? 'FAILED' : 'SUCCEEDED'; success = !failure; }
  else if (lower.includes('receiptnumber') && lower.includes('currentbalance')) { kind = 'MINI_STATEMENT'; status = 'SUCCEEDED'; success = true; }
  else if (currentBalance != null || containsAny(lower, ['available voucher stock', 'current balance', 'your balance', 'solde'])) { kind = 'BALANCE'; status = failure ? 'FAILED' : 'SUCCEEDED'; success = !failure && currentBalance != null; }
  else if (lower.includes('transaction') && containsAny(lower, ['details', 'accountno', 'dr:', 'cr:'])) { kind = 'TRANSACTION_DETAIL'; status = failure ? 'FAILED' : 'SUCCEEDED'; success = !failure; }
  else if (lower.includes('reset') && lower.includes('pin')) { kind = 'PIN_RESET'; status = failure ? 'FAILED' : 'SUCCEEDED'; }
  else if (lower.includes('modified pin') || lower.includes('pin changed')) { kind = 'PIN_CHANGED'; status = failure ? 'FAILED' : 'SUCCEEDED'; success = !failure; }
  else if (containsAny(lower, ['suspend', 'reactivat', 'frozen', 'freeze'])) { kind = 'ORGANIZATION_STATUS'; status = failure ? 'FAILED' : (success ? 'SUCCEEDED' : 'INFO'); }

  const source = /(?:from)\s+(6\d{8})(?:\s*-\s*([A-Za-z0-9_.-]+))?/i.exec(text);
  const target = /(?:to|vers)\s+(6\d{8})(?:\s*-\s*([A-Za-z0-9_.-]+))?/i.exec(text);
  const drcr = /(?:^|\s)(Dr|Cr)\s*:\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i.exec(text);
  const charge = /(?:TransactionCharge|Charge|Fee)\s*:\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i.exec(text);
  const commission = /(?:Commission)\s*:\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i.exec(text);
  const tax = /(?:Tax)\s*:\s*([0-9][0-9 .,'’]*?(?:[.,]\d{1,2})?)\s*(?:F\s*CFA|FCFA|XAF)/i.exec(text);
  const firstPhone = first(PHONE, text);
  return {
    kind, status, success, failure, processing, wrong_pin: wrongPin,
    transaction_id: first(TX_ID, text), receipt_number: first(RECEIPT, text),
    account_no: first(ACCOUNT, text), source_phone: source?.[1] || '', source_node: source?.[2] || '',
    target_phone: target?.[1] || '', target_node: target?.[2] || '', phone: firstPhone,
    amount_fcfa: firstMoney(AMOUNT, text), current_balance: currentBalance,
    transaction_date: dt?.[1] || '', transaction_time: dt?.[2] || '',
    debit_credit: drcr?.[1] || '', debit_credit_amount: drcr ? parseFcfaAmount(drcr[2]) : null,
    charge_amount: charge ? parseFcfaAmount(charge[1]) : null,
    commission_amount: commission ? parseFcfaAmount(commission[1]) : null,
    tax_amount: tax ? parseFcfaAmount(tax[1]) : null,
    raw_message: text
  };
}
