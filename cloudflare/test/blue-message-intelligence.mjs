import assert from 'node:assert/strict';
import {parseBlueMessage, parseFcfaAmount} from '../src/blue-message.mjs';

assert.equal(parseFcfaAmount('10.00'), 10);
assert.equal(parseFcfaAmount('1 250.00'), 1250);
assert.equal(parseFcfaAmount('35,000'), 35000);
assert.equal(parseBlueMessage('Votre solde actuel est de 900 FCFA').current_balance, 900);

let parsed = parseBlueMessage('You received Airtime from 620451087 - DSM7_OU3. Amount is 10.00 FCFA. Now your balance is 13.00 FCFA. TransactionID 102404198047 on 22-06-2026 at 12:19:22');
assert.equal(parsed.kind, 'TRANSFER_RECEIVED');
assert.equal(parsed.source_phone, '620451087');
assert.equal(parsed.amount_fcfa, 10);
assert.equal(parsed.current_balance, 13);
assert.equal(parsed.transaction_id, '102404198047');

parsed = parseBlueMessage('Your Transfer Airtime to 621081275 - POS16_DSM7_OU3 has been successfully processed.Amount is 5.00 FCFA. Now your balance is 10.00 FCFA. TransactionID 102404199999 on 22-06-2026 at 12:20:22');
assert.equal(parsed.kind, 'TRANSFER_SENT');
assert.equal(parsed.target_phone, '621081275');
assert.equal(parsed.current_balance, 10);

parsed = parseBlueMessage('ReceiptNumber:ABCD123 CurrentBalance:15.00 FCFA AccountNo:OU3 Details:Transfer Dr:5.00 FCFA TransactionCharge:0.00 FCFA Commission:0.00 FCFA Tax:0.00 FCFA Status:Completed');
assert.equal(parsed.kind, 'MINI_STATEMENT');
assert.equal(parsed.current_balance, 15);
assert.equal(parsed.debit_credit, 'Dr');
assert.equal(parsed.debit_credit_amount, 5);

parsed = parseBlueMessage('Request is processed successfully.');
assert.equal(parsed.kind, 'REQUEST_ACK');
assert.equal(parsed.processing, true);
assert.equal(parsed.success, false);
console.log('Blue message intelligence: canonical SMS/popups OK');
