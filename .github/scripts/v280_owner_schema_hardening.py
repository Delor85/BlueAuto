from pathlib import Path


def load(path): return Path(path).read_text(encoding='utf-8')
def save(path,text): Path(path).write_text(text,encoding='utf-8')
def replace_once(path,old,new):
    text=load(path)
    if old not in text: raise SystemExit('missing anchor in %s: %s' % (path,old[:100]))
    save(path,text.replace(old,new,1))

# account_balances has no persisted available_balance/reserved_amount columns. Keep owner snapshot truthful:
# expose only stored evidence fields; availability remains derived by normal balance logic when needed.
replace_once('cloudflare/src/index.js',
"    'SELECT n.node_code,n.role,n.phone_number,n.parent_node_code,n.active,n.created_at,b.balance,b.available_balance,b.reserved_amount,b.balance_quality,b.evidence_kind,b.observed_at,b.operator_event_at,s.terminal_type,s.display_name,s.zone ' +",
"    'SELECT n.node_code,n.role,n.phone_number,n.parent_node_code,n.active,n.created_at,n.default_commission_bps,b.balance,b.balance_quality,b.evidence_kind,b.observed_at,b.operator_event_at,s.terminal_type,s.display_name,s.zone ' +")

# MOCK remains usable against current production v2.6.7, but opportunistically acquires a device-bound
# cryptographic server entitlement as soon as v2.8 owner endpoints are deployed. No clear token reaches JS.
old='''        mockSessionAuthorized = true;\n        AppConfig.prefs(this).edit()\n                .putString(MOCK_RETURN_PROFILE_KEY, AppConfig.profileId(this))\n                .putBoolean(MOCK_OWNER_ENABLED_KEY, false)\n                .putBoolean(MOCK_WORKSPACE_KEY, true)\n                .commit();\n        mockRouteProfile();\n        recreate();\n'''
new='''        mockSessionAuthorized = true;\n        AppConfig.prefs(this).edit()\n                .putString(MOCK_RETURN_PROFILE_KEY, AppConfig.profileId(this))\n                .putBoolean(MOCK_OWNER_ENABLED_KEY, false)\n                .putBoolean(MOCK_WORKSPACE_KEY, true)\n                .commit();\n        mockRouteProfile();\n        final String ownerCode = code.trim();\n        new Thread(() -> {\n            try {\n                JSONObject data = new ApiClient(MainActivity.this).ownerEnroll("MOCK_OWNER", ownerCode);\n                String token = data.optString("owner_token", "");\n                String entitlementId = data.optString("entitlement_id", "");\n                if (!token.isEmpty() && !entitlementId.isEmpty()) {\n                    SecureOwnerStore.save(MainActivity.this, "MOCK_OWNER", entitlementId, token);\n                }\n            } catch (Exception ignored) {\n                // Production v2.6.7 has no owner endpoint yet. Local private MOCK remains available\n                // until a separately authorized v2.8 Worker/D1 rollout enables server verification.\n            }\n        }, "BIR-MockOwnerEnroll-v280").start();\n        recreate();\n'''
replace_once('app/src/main/java/com/profitloop/blueauto/MainActivity.java',old,new)

# When a server MOCK entitlement already exists, attach it to routed Mercenary actions. Current Worker
# safely ignores the extra header; v2.8 can verify it without exposing the token to JavaScript.
old='''                        client = ApiClient.forProfile(MainActivity.this, routeProfile);\n                    }\n                    JSONObject data = client.platformAction(action, payload);'''
new='''                        client = ApiClient.forProfile(MainActivity.this, routeProfile);\n                        String mockOwnerToken = SecureOwnerStore.token(MainActivity.this, "MOCK_OWNER");\n                        if (!mockOwnerToken.isEmpty()) {\n                            client.withOwnerToken(mockOwnerToken);\n                            payload.put("mock_owner_entitled", true);\n                        }\n                    }\n                    JSONObject data = client.platformAction(action, payload);'''
replace_once('app/src/main/java/com/profitloop/blueauto/MainActivity.java',old,new)

# Strengthen the source contract with the schema truth and server-entitled MOCK bridge.
p='app/src/test/v280-operations-admin-contract.mjs'
text=load(p)
anchor="ok(main.includes('owner_admin_workspace')&&main.includes('exitOwnerAdminWorkspace'),'admin workspace lifecycle');"
addition=anchor+"\nok(main.includes('ownerEnroll(\"MOCK_OWNER\"')&&main.includes('mock_owner_entitled'),'MOCK must bridge to device-bound server entitlement without breaking current production');"
if addition not in text:
    if anchor not in text: raise SystemExit('missing v280 contract anchor')
    text=text.replace(anchor,addition,1)
anchor2="ok(worker.includes(\"case 'owner_snapshot'\")&&worker.includes(\"case 'owner_control'\")&&worker.includes(\"case 'owner_assist'\")&&worker.includes('authenticateOwner'),'server owner control source');"
addition2=anchor2+"\nok(!worker.includes('b.available_balance')&&!worker.includes('b.reserved_amount'),'owner snapshot must query only real account_balances columns');"
if addition2 not in text:
    text=text.replace(anchor2,addition2,1)
anchor3="ok(html.includes('control-tower-v280.css')&&html.includes('control-tower-v280.js'),'v2.8 overlay wired');"
addition3=anchor3+"\nok(html.includes('balance-engine-v280.js'),'event-driven balance engine wired');"
if addition3 not in text:
    text=text.replace(anchor3,addition3,1)
save(p,text)
print('v2.8 owner/schema hardening applied')
