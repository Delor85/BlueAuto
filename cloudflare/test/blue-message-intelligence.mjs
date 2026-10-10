import assert from 'node:assert/strict';
import {parseBlueMessage, parseFcfaAmount, parseMiniStatementEntries} from '../src/blue-message.mjs';

assert.equal(parseFcfaAmount('10.00'), 10);
assert.equal(parseFcfaAmount('1 250.00'), 1250);
assert.equal(parseFcfaAmount('35,000'), 35000);
assert.equal(parseBlueMessage('Votre solde actuel est de 900 FCFA').current_balance, 900);

let parsed = parseBlueMessage('You received Airtime from 620451087 - DSM7_OU3. Amount is 10.00 FCFA. Now your balance is 13.00 FCFA. TransactionID 102404198047 on 22-06-2026 at 12:19:22');
assert.equal(parsed.kind, 'TRANSFER_RECEIVED');
assert.equal(parsed.source_phone, '620451087');
assert.equal(parsed.source_node, 'DSM7_OU3');
assert.equal(parsed.amount_fcfa, 10);
assert.equal(parsed.current_balance, 13);
assert.equal(parsed.transaction_id, '102404198047');

parsed = parseBlueMessage('Your Transfer Airtime to 621081275 - POS16_DSM7_OU3 has been successfully processed.Amount is 5.00 FCFA. Now your balance is 10.00 FCFA. TransactionID 102404199999 on 22-06-2026 at 12:20:22');
assert.equal(parsed.kind, 'TRANSFER_SENT');
assert.equal(parsed.target_phone, '621081275');
assert.equal(parsed.target_node, 'POS16_DSM7_OU3');
assert.equal(parsed.current_balance, 10);

parsed = parseBlueMessage('ReceiptNumber:ABCD123 CurrentBalance:15.00 FCFA AccountNo:OU3 Details:Transfer Dr:5.00 FCFA TransactionCharge:0.00 FCFA Commission:0.00 FCFA Tax:0.00 FCFA Status:Completed');
assert.equal(parsed.kind, 'MINI_STATEMENT');
assert.equal(parsed.current_balance, 15);
assert.equal(parsed.debit_credit, 'Dr');
assert.equal(parsed.debit_credit_amount, 5);


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

parsed = parseBlueMessage('Request is processed successfully.');
assert.equal(parsed.kind, 'REQUEST_ACK');
assert.equal(parsed.processing, true);
assert.equal(parsed.success, false);
console.log('Blue message intelligence: canonical SMS/popups OK');
