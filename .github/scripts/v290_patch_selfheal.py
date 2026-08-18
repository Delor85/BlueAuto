from pathlib import Path
p=Path(__file__).with_name('v290_robot_offline_relay.py')
s=p.read_text(encoding='utf-8')

old='''s=once(s,'                value.put("mock_owner_server_entitled", SecureOwnerStore.has(MainActivity.this, "MOCK_OWNER"));', '                value.put("mock_owner_server_entitled", SecureOwnerStore.has(MainActivity.this, "MOCK_OWNER"));\\n                value.put("offline_pending_events", LocalEventStore.pendingCount(MainActivity.this));\\n                value.put("robot_offline_capable", AppConfig.isRobotMode(MainActivity.this));')'''
new='''s=once(s,'                value.put("mock_owner_server_entitled", SecureOwnerStore.has(MainActivity.this, "MOCK_OWNER"));', '                value.put("mock_owner_server_entitled", SecureOwnerStore.has(MainActivity.this, "MOCK_OWNER"));\\n                value.put("offline_pending_events", LocalEventStore.pendingCount(MainActivity.this));\\n                value.put("robot_offline_capable", AppConfig.isRobotMode(MainActivity.this));','configuration offline state')'''
if old in s:s=s.replace(old,new,1)

# Only final local results are server/Relay outbox items; progress stays local audit.
s=s.replace('''v.put("created_at", System.currentTimeMillis()); v.put("sync_state", "PENDING");''','''v.put("created_at", System.currentTimeMillis()); v.put("sync_state", "LOCAL_COMMAND_RESULT".equals(kind) ? "PENDING" : "LOCAL");''')

# Non-financial local USSD must not carry amount=0 because factory rejects unexpected transfer parameters.
s=s.replace('''p.put("amount",String.valueOf(total));p.put("requested_base_amount",base);''','''p.put("amount",("SUPPLY_CHILD".equals(type)||"RETAIL_SALE".equals(type))?String.valueOf(total):"");p.put("requested_base_amount",base);''')
s=s.replace('''cmd.put("amount",String.valueOf(p.optInt("total_amount",0)));cmd.put("requested_base_amount",p.optInt("base_amount",0));''','''cmd.put("amount",p.optString("amount",""));cmd.put("requested_base_amount",p.optInt("base_amount",0));''')

# FREEZE_SELF is a local self-operation: bind its own node and phone into the envelope.
s=s.replace('''String op=operation(type); validate(role,type,node,phone,amt,argument);''','''if("FREEZE_SELF".equals(type)){node=AppConfig.nodeCode(c,profile);phone=digits(AppConfig.phoneNumber(c,profile));}\n        String op=operation(type); validate(role,type,node,phone,amt,argument);''')

# Back off every final event if the new sync endpoint is not live yet.
s=s.replace('''for(int i=0;i<items.length();i++){JSONObject e=items.optJSONObject(i);if(e==null)continue;JSONObject p=e.optJSONObject("payload");String raw=p==null?"":p.optString("result_message","");if(raw.length()<4)continue;try{ApiClient.forProfile(c,profile).recordOperatorMessage(raw);}catch(Exception ignored){break;}LocalEventStore.retryLater(c,e.optString("event_id"),60_000L);}''','''for(int i=0;i<items.length();i++){JSONObject e=items.optJSONObject(i);if(e==null)continue;JSONObject p=e.optJSONObject("payload");String raw=p==null?"":p.optString("result_message","");if(raw.length()>=4){try{ApiClient.forProfile(c,profile).recordOperatorMessage(raw);}catch(Exception ignored){}}LocalEventStore.retryLater(c,e.optString("event_id"),60_000L);}''')

p.write_text(s,encoding='utf-8')
print('v290 generator self-healed')
