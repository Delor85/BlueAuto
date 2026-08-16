from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'app/src/main/assets/control-tower-v271.js'
text = path.read_text(encoding='utf-8')
old = "function guardDashboard(data){if(!data||data.error)return data;var own=ownNode(data),cached=balanceLoad(),incoming;if(!own||!cached)return data;incoming=stamp(own.operator_event_at||own.observed_at);if(own.balance===null||typeof own.balance==='undefined'||!incoming||incoming<Number(cached.ts||0)){own.balance=cached.balance;own.available_balance=cached.available_balance;own.reserved_amount=cached.reserved_amount;own.balance_quality=cached.balance_quality||'EXACT';own.evidence_kind=cached.evidence_kind||'LOCAL_NEWER_PROOF';own.observed_at=cached.observed_at;own.operator_event_at=cached.operator_event_at||cached.observed_at;own.balance_reusable=true;own.client_balance_guard=true;}else{balanceSave({balance:own.balance,available_balance:own.available_balance,reserved_amount:own.reserved_amount,balance_quality:own.balance_quality,evidence_kind:own.evidence_kind,observed_at:own.observed_at,operator_event_at:own.operator_event_at,ts:incoming});}return data;}"
new = "function guardDashboard(data){if(!data||data.error)return data;var own=ownNode(data),cached=balanceLoad(),incoming,kind,unsafeLateFinancial;if(!own)return data;kind=upper(own.evidence_kind||own.balance_source||'');unsafeLateFinancial=(kind==='FINANCIAL_RESULT'&&!own.operator_event_at);incoming=unsafeLateFinancial?0:stamp(own.operator_event_at||own.observed_at);if(unsafeLateFinancial&&!cached){own.balance=null;own.available_balance=null;own.reserved_amount=0;own.balance_quality='UNKNOWN';own.evidence_kind='FINANCIAL_RESULT_A_RAPPROCHER';own.balance_reusable=false;own.client_balance_guard=true;own.client_balance_reason='LATE_FINANCIAL_RESULT_WITHOUT_OPERATOR_TIME';return data;}if(!cached)return data;if(unsafeLateFinancial||own.balance===null||typeof own.balance==='undefined'||!incoming||incoming<Number(cached.ts||0)){own.balance=cached.balance;own.available_balance=cached.available_balance;own.reserved_amount=cached.reserved_amount;own.balance_quality=cached.balance_quality||'EXACT';own.evidence_kind=cached.evidence_kind||'LOCAL_NEWER_PROOF';own.observed_at=cached.observed_at;own.operator_event_at=cached.operator_event_at||cached.observed_at;own.balance_reusable=true;own.client_balance_guard=true;own.client_balance_reason=unsafeLateFinancial?'LATE_FINANCIAL_RESULT_IGNORED':'OLDER_OR_UNDATED_EVIDENCE_IGNORED';}else{balanceSave({balance:own.balance,available_balance:own.available_balance,reserved_amount:own.reserved_amount,balance_quality:own.balance_quality,evidence_kind:own.evidence_kind,observed_at:own.observed_at,operator_event_at:own.operator_event_at,ts:incoming});}return data;}"
if text.count(old) != 1:
    raise SystemExit(f'guardDashboard expected once, found {text.count(old)}')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')

test_path = ROOT / 'app/src/test/v271-field-stabilization-contract.mjs'
test = test_path.read_text(encoding='utf-8')
anchor = "ok(v271.includes('bir_balance_guard_v271_')&&v271.includes('incoming<Number(cached.ts||0)'),'chronology-first balance guard');"
replacement = "ok(v271.includes('bir_balance_guard_v271_')&&v271.includes('incoming<Number(cached.ts||0)'),'chronology-first balance guard');\nok(v271.includes(\"kind==='FINANCIAL_RESULT'&&!own.operator_event_at\")&&v271.includes('LATE_FINANCIAL_RESULT_IGNORED'),'late financial balance without operator chronology must never override a newer proof');"
if test.count(anchor) != 1:
    raise SystemExit('v271 balance contract anchor missing')
test_path.write_text(test.replace(anchor, replacement, 1), encoding='utf-8')
print('v2.7.1 balance chronology hardening prepared')
