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

# Effective application modes are exactly REMOTE and ROBOT. Legacy HYBRID data is interpreted as ROBOT only for migration compatibility.
marker="# ---------------------------------------------------------------------------\n# UssdCommandFactory: preserve strict server validation"
block=r"""# ---------------------------------------------------------------------------
# Two effective modes only. A legacy HYBRID value from older builds is migrated
# transparently to ROBOT and is never exposed as a third selectable mode.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/AppConfig.java'; s=read(p)
s=once(s,
'''    static String mode(Context context) {\n        JSONObject profile = activeProfile(context);\n        return profile == null ? "REMOTE" : profile.optString("device_mode", "REMOTE");\n    }\n\n    static String mode(Context context, String profileId) {\n        JSONObject profile = profile(context, profileId);\n        return profile == null ? "REMOTE" : profile.optString("device_mode", "REMOTE");\n    }''',
'''    static String mode(Context context) {\n        JSONObject profile = activeProfile(context);\n        return effectiveMode(profile == null ? "REMOTE" : profile.optString("device_mode", "REMOTE"));\n    }\n\n    static String mode(Context context, String profileId) {\n        JSONObject profile = profile(context, profileId);\n        return effectiveMode(profile == null ? "REMOTE" : profile.optString("device_mode", "REMOTE"));\n    }\n\n    private static String effectiveMode(String raw) {\n        String value = raw == null ? "REMOTE" : raw.trim().toUpperCase(Locale.ROOT);\n        if ("HYBRID".equals(value)) return "ROBOT"; // legacy data only\n        return "ROBOT".equals(value) ? "ROBOT" : "REMOTE";\n    }''','two effective modes')
s=once(s,
'''    static boolean isRobotMode(Context context) {\n        String value = mode(context);\n        return "ROBOT".equals(value) || "HYBRID".equals(value);\n    }\n\n    static boolean isRobotMode(Context context, String profileId) {\n        String value = mode(context, profileId);\n        return "ROBOT".equals(value) || "HYBRID".equals(value);\n    }\n\n    static String displayMode(String mode) {\n        return "HYBRID".equals(mode) ? "ROBOT" : mode;\n    }''',
'''    static boolean isRobotMode(Context context) { return "ROBOT".equals(mode(context)); }\n\n    static boolean isRobotMode(Context context, String profileId) {\n        return "ROBOT".equals(mode(context, profileId));\n    }\n\n    static String displayMode(String mode) { return effectiveMode(mode); }''','robot mode strict')
write(p,s)

"""
if marker in s and 'two effective modes' not in s:
    s=s.replace(marker,block+marker,1)

# Fix the DAE/DSM split so a later dashboard balance refresh can replace the previous total.
css_marker="# Include overlay after v280."
balance_patch=r'''# Keep the split reactive: if another script writes a new operator/global balance into the headline,
# treat that value as the new total before rendering the highlighted net amount.
p='app/src/main/assets/control-tower-v290.js'; s=read(p)
old="var updating=false;function updateSplit(){if(updating)return;var head=id('birCamtelBalance'),comm=id('v290CommissionBalance'),totalOut=id('v290GlobalBalance');if(!head||!comm||!totalOut)return;var total=numText(head.getAttribute('data-v290-total')||head.textContent);if(!isFinite(total))return;var bps=Math.max(0,defaultBps()),net=Math.floor(total*10000/(10000+bps)),commission=total-net;updating=true;head.setAttribute('data-v290-total',String(total));head.textContent=String(net).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' ');comm.textContent=money(commission);totalOut.textContent=money(total);if(id('v290DefaultRate'))id('v290DefaultRate').textContent=t('Taux par défaut : ','Default rate: ')+(bps/100).toFixed(bps%100?2:0)+' %';updating=false;}"
new="var updating=false,lastRenderedNet=null;function updateSplit(){if(updating)return;var head=id('birCamtelBalance'),comm=id('v290CommissionBalance'),totalOut=id('v290GlobalBalance');if(!head||!comm||!totalOut)return;var visible=numText(head.textContent),saved=numText(head.getAttribute('data-v290-total')),total;if(isFinite(visible)&&(lastRenderedNet===null||visible!==lastRenderedNet)){total=visible;head.setAttribute('data-v290-total',String(total));}else total=saved;if(!isFinite(total))return;var bps=Math.max(0,defaultBps()),net=Math.floor(total*10000/(10000+bps)),commission=total-net;updating=true;lastRenderedNet=net;head.textContent=String(net).replace(/\\B(?=(\\d{3})+(?!\\d))/g,' ');comm.textContent=money(commission);totalOut.textContent=money(total);if(id('v290DefaultRate'))id('v290DefaultRate').textContent=t('Taux par défaut : ','Default rate: ')+(bps/100).toFixed(bps%100?2:0)+' %';updating=false;}"
s=once(s,old,new,'reactive three-part balance')
write(p,s)

'''
if css_marker in s and 'reactive three-part balance' not in s:
    s=s.replace(css_marker,balance_patch+css_marker,1)

# Strengthen the contract: only REMOTE/ROBOT are effective and the balance split must accept new live totals.
s=s.replace("must(main.includes('new String[]{\"REMOTE\", \"ROBOT\"}'),'exact two modes must remain');", "must(main.includes('new String[]{\"REMOTE\", \"ROBOT\"}'),'exact two modes must remain');\nmust(text('app/src/main/java/com/profitloop/blueauto/AppConfig.java').includes('if (\"HYBRID\".equals(value)) return \"ROBOT\"; // legacy data only'),'legacy mode must collapse to ROBOT');")
s=s.replace("must(v290.includes('SOLDE RÉEL HORS COMMISSION')&&v290.includes('Commission au taux par défaut')&&v290.includes('Solde global réel'),'DAE/DSM three-part balance missing');", "must(v290.includes('SOLDE RÉEL HORS COMMISSION')&&v290.includes('Commission au taux par défaut')&&v290.includes('Solde global réel'),'DAE/DSM three-part balance missing');\nmust(v290.includes('lastRenderedNet'),'three-part balance must accept live total refreshes');")

p.write_text(s,encoding='utf-8')
print('v290 generator self-healed')
