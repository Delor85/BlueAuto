from pathlib import Path


def load(path):
    return Path(path).read_text(encoding='utf-8')


def save(path, text):
    Path(path).write_text(text, encoding='utf-8')


def replace_once(path, old, new):
    text = load(path)
    if old not in text:
        raise SystemExit('missing patch anchor in %s: %r' % (path, old[:120]))
    text = text.replace(old, new, 1)
    save(path, text)


# Version / identity. Package and minSdk are deliberately untouched.
replace_once('app/build.gradle', 'versionCode 52\n        versionName "2.7.1"', 'versionCode 53\n        versionName "2.8.0"')
replace_once('app/src/main/java/com/profitloop/blueauto/ApiClient.java', 'payload.put("app_version", "2.7.1");', 'payload.put("app_version", "2.8.0");')
replace_once('app/src/main/java/com/profitloop/blueauto/ApiClient.java', 'payload.put("app_version", "2.7.1");', 'payload.put("app_version", "2.8.0");')

# Wire the v2.8 additive UI overlay after all inherited layers.
replace_once('app/src/main/assets/index.html', '<link rel="stylesheet" href="control-tower-v271.css">', '<link rel="stylesheet" href="control-tower-v271.css">\n    <link rel="stylesheet" href="control-tower-v280.css">')
replace_once('app/src/main/assets/index.html', '  <script src="control-tower-v271.js"></script>\n</body>', '  <script src="control-tower-v271.js"></script>\n  <script src="control-tower-v280.js"></script>\n</body>')

# A one-shot commission must never leak into the next transaction in the same process.
replace_once(
    'app/src/main/assets/control-tower-v271.js',
    "window.BIRCommissionPolicy={getRateBps:effectiveRate,setOneShotRate:function(child,bps){oneShot[upper(child)]=Number(bps||0);},serverSupportsPersistent:function(){return commissionServerSupport===true;}};",
    "window.BIRCommissionPolicy={getRateBps:effectiveRate,setOneShotRate:function(child,bps){oneShot[upper(child)]=Number(bps||0);},clearOneShotRate:function(child){delete oneShot[upper(child)];},serverSupportsPersistent:function(){return commissionServerSupport===true;}};"
)
replace_once(
    'app/src/main/assets/app.js',
    "onCommandCreated:function(data){var submitted=submittedForm;setBusy(false);pendingPreview=null;submittedForm=null;if(data.error)",
    "onCommandCreated:function(data){var submitted=submittedForm;if(submitted&&submitted.type==='SUPPLY_CHILD'&&window.BIRCommissionPolicy&&window.BIRCommissionPolicy.clearOneShotRate){window.BIRCommissionPolicy.clearOneShotRate(submitted.node);}setBusy(false);pendingPreview=null;submittedForm=null;if(data.error)"
)

# ApiClient: owner entitlement header, enrollment, control polling and expanded source-only APIs.
replace_once(
    'app/src/main/java/com/profitloop/blueauto/ApiClient.java',
    '    private final String profileIdOverride;\n',
    '    private final String profileIdOverride;\n    private String ownerTokenOverride = "";\n'
)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/ApiClient.java',
    '    JSONObject platformAction(String action, JSONObject payload) throws Exception {\n        String safe = action == null ? "" : action.trim();\n        if (!safe.matches("(?:operator_insights|operator_catalog|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale|commission_policy|commission_set_default|commission_set_child)")) {',
    '    ApiClient withOwnerToken(String token) {\n        this.ownerTokenOverride = token == null ? "" : token.trim();\n        return this;\n    }\n\n    JSONObject ownerEnroll(String kind, String code) throws Exception {\n        JSONObject payload = new JSONObject();\n        payload.put("kind", kind == null ? "" : kind.trim().toUpperCase());\n        payload.put("owner_code", code == null ? "" : code.trim());\n        return post("owner_enroll", payload, true);\n    }\n\n    JSONObject controlPoll() throws Exception {\n        return postControl("device_control_poll", new JSONObject(), true);\n    }\n\n    JSONObject controlAck(long actionId, boolean success, String message) throws Exception {\n        JSONObject payload = new JSONObject();\n        payload.put("action_id", actionId);\n        payload.put("success", success);\n        payload.put("message", message == null ? "" : trim(message, 500));\n        return post("device_control_ack", payload, true);\n    }\n\n    JSONObject platformAction(String action, JSONObject payload) throws Exception {\n        String safe = action == null ? "" : action.trim();\n        if (!safe.matches("(?:operator_insights|operator_catalog|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale|commission_policy|commission_set_default|commission_set_child|accounting_summary|transaction_ledger|owner_snapshot|owner_transactions|owner_audit|owner_control|owner_assist)")) {'
)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/ApiClient.java',
    '            connection.setRequestProperty("X-Device-Token", requestToken);\n        }\n',
    '            connection.setRequestProperty("X-Device-Token", requestToken);\n        }\n        if (!ownerTokenOverride.isEmpty()) {\n            connection.setRequestProperty("X-Owner-Token", ownerTokenOverride);\n        }\n'
)

# AppConfig: audited admin controls may switch the local operating mode without recreating an account.
replace_once(
    'app/src/main/java/com/profitloop/blueauto/AppConfig.java',
    '    static String mode(Context context, String profileId) {\n        JSONObject profile = profile(context, profileId);\n        return profile == null ? "REMOTE" : profile.optString("device_mode", "REMOTE");\n    }\n',
    '    static String mode(Context context, String profileId) {\n        JSONObject profile = profile(context, profileId);\n        return profile == null ? "REMOTE" : profile.optString("device_mode", "REMOTE");\n    }\n\n    static synchronized boolean updateMode(Context context, String profileId, String mode) {\n        String normalized = mode == null ? "REMOTE" : mode.trim().toUpperCase(Locale.ROOT);\n        if (!"REMOTE".equals(normalized) && !"ROBOT".equals(normalized)) return false;\n        JSONArray all = profiles(context);\n        for (int i = 0; i < all.length(); i++) {\n            JSONObject profile = all.optJSONObject(i);\n            if (profile != null && profileId.equals(profile.optString("id", ""))) {\n                try {\n                    profile.put("device_mode", normalized);\n                    if ("REMOTE".equals(normalized)) setRobotEnabled(context, profileId, false);\n                    return prefs(context).edit().putString(PROFILES_KEY, all.toString()).commit();\n                } catch (Exception ignored) { return false; }\n            }\n        }\n        return false;\n    }\n'
)

# MainActivity: private ADMIN entry in the same Add/Open form. It is not a Blue role.
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '    private static final String UI_LANGUAGE_KEY = "bir_ui_language_v271";\n',
    '    private static final String UI_LANGUAGE_KEY = "bir_ui_language_v271";\n    private static final String OWNER_ADMIN_WORKSPACE_KEY = "bir_owner_admin_workspace_v280";\n    private static final String OWNER_ADMIN_RETURN_PROFILE_KEY = "bir_owner_admin_return_profile_v280";\n'
)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '    private static boolean mockSessionAuthorized;\n',
    '    private static boolean mockSessionAuthorized;\n    private static boolean adminSessionAuthorized;\n'
)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '        EditText nodeCode = field(ui("Identifiant Blue (ex. OU3, DSM7_OU3, POS16_DSM7_OU3) — ou MOCK",\n                "Blue ID (e.g. OU3, DSM7_OU3, POS16_DSM7_OU3) — or MOCK"), "", false);',
    '        EditText nodeCode = field(ui("Identifiant Blue (ex. OU3, DSM7_OU3, POS16_DSM7_OU3) — ou MOCK / ADMIN",\n                "Blue ID (e.g. OU3, DSM7_OU3, POS16_DSM7_OU3) — or MOCK / ADMIN"), "", false);'
)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '        EditText mockCode = field(ui("Code privé MOCK", "Private MOCK code"), "", true);\n        mockCode.setVisibility(View.GONE);\n        form.addView(mockCode);\n',
    '        EditText mockCode = field(ui("Code privé MOCK", "Private MOCK code"), "", true);\n        mockCode.setVisibility(View.GONE);\n        form.addView(mockCode);\n        EditText adminCode = field(ui("Code privé ADMIN propriétaire", "Private owner ADMIN code"), "", true);\n        adminCode.setVisibility(View.GONE);\n        form.addView(adminCode);\n'
)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '                boolean mock = "MOCK".equalsIgnoreCase(value.toString().trim());\n                mockCode.setVisibility(mock ? View.VISIBLE : View.GONE);\n                realFields.setVisibility(mock ? View.GONE : View.VISIBLE);\n                adminActivation.setVisibility(mock ? View.GONE : (hasPairingSecret() ? View.GONE : View.VISIBLE));\n                feedback.setText(mock\n                        ? ui("Accès propriétaire privé. Le compte MOCK ne sera jamais affiché dans la liste normale des comptes.",\n                                "Private owner access. MOCK will never appear in the normal account list.")\n                        : ui("Les réglages techniques du serveur sont gérés automatiquement par B.I.R.",\n                                "B.I.R. manages server technical settings automatically."));',
    '                String requested = value.toString().trim();\n                boolean mock = "MOCK".equalsIgnoreCase(requested);\n                boolean admin = "ADMIN".equalsIgnoreCase(requested);\n                mockCode.setVisibility(mock ? View.VISIBLE : View.GONE);\n                adminCode.setVisibility(admin ? View.VISIBLE : View.GONE);\n                realFields.setVisibility((mock || admin) ? View.GONE : View.VISIBLE);\n                adminActivation.setVisibility((mock || admin) ? View.GONE : (hasPairingSecret() ? View.GONE : View.VISIBLE));\n                feedback.setText(mock\n                        ? ui("Accès propriétaire privé. Le compte MOCK ne sera jamais affiché dans la liste normale des comptes.",\n                                "Private owner access. MOCK will never appear in the normal account list.")\n                        : admin ? ui("Tour de contrôle propriétaire privée. ADMIN n’est pas un rôle Blue et exige un entitlement cryptographique serveur.",\n                                "Private owner control tower. ADMIN is not a Blue role and requires a cryptographic server entitlement.")\n                        : ui("Les réglages techniques du serveur sont gérés automatiquement par B.I.R.",\n                                "B.I.R. manages server technical settings automatically."));'
)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '            if ("MOCK".equals(node)) {\n                openMockFromPairing(mockCode.getText().toString().trim(), feedback);\n                return;\n            }\n',
    '            if ("MOCK".equals(node)) {\n                openMockFromPairing(mockCode.getText().toString().trim(), feedback);\n                return;\n            }\n            if ("ADMIN".equals(node)) {\n                openOwnerAdminFromPairing(adminCode.getText().toString().trim(), feedback);\n                return;\n            }\n'
)

# Insert admin enrollment after current local MOCK enrollment helper. ADMIN intentionally has no offline bypass.
anchor = '    private void showPairingScreen(boolean addingAccount) {'
admin_methods = '''    private boolean isOwnerAdminWorkspaceActive() {\n        return adminSessionAuthorized && AppConfig.prefs(this).getBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                && SecureOwnerStore.has(this, "OWNER_ADMIN");\n    }\n\n    private void openOwnerAdminFromPairing(String code, TextView feedback) {\n        if (!AppConfig.hasProfiles(this)) {\n            feedback.setText(ui("Ajoutez d’abord au moins un compte Blue réel sur ce téléphone.",\n                    "Add at least one real Blue account on this phone first."));\n            feedback.setTextColor(Color.rgb(255, 139, 152));\n            return;\n        }\n        if (code == null || code.trim().length() < 24) {\n            feedback.setText(ui("Code ADMIN incomplet.", "Incomplete ADMIN code."));\n            feedback.setTextColor(Color.rgb(255, 139, 152));\n            return;\n        }\n        feedback.setTextColor(CYAN);\n        feedback.setText(ui("Vérification cryptographique ADMIN auprès du serveur…",\n                "Checking cryptographic ADMIN entitlement with the server…"));\n        new Thread(() -> {\n            try {\n                JSONObject data = new ApiClient(this).ownerEnroll("OWNER_ADMIN", code.trim());\n                String token = data.optString("owner_token", "");\n                String entitlementId = data.optString("entitlement_id", "");\n                SecureOwnerStore.save(this, "OWNER_ADMIN", entitlementId, token);\n                adminSessionAuthorized = true;\n                AppConfig.prefs(this).edit()\n                        .putString(OWNER_ADMIN_RETURN_PROFILE_KEY, AppConfig.profileId(this))\n                        .putBoolean(OWNER_ADMIN_WORKSPACE_KEY, true).commit();\n                runOnUiThread(this::recreate);\n            } catch (Exception error) {\n                runOnUiThread(() -> {\n                    feedback.setTextColor(Color.rgb(255, 139, 152));\n                    feedback.setText(ui("ADMIN non activé : ", "ADMIN not enabled: ") + readable(error)\n                            + ui(". Si le Worker v2.8 n’est pas encore autorisé en production, cette fonction reste volontairement inactive.",\n                            ". If the v2.8 Worker is not yet authorized in production, this feature intentionally stays inactive."));\n                });\n            }\n        }, "BIR-OwnerAdminEnroll-v280").start();\n    }\n\n'''
text = load('app/src/main/java/com/profitloop/blueauto/MainActivity.java')
if anchor not in text:
    raise SystemExit('missing MainActivity admin insertion anchor')
text = text.replace(anchor, admin_methods + anchor, 1)
save('app/src/main/java/com/profitloop/blueauto/MainActivity.java', text)

# Configuration advertises the separate owner workspace without changing the underlying Blue role.
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '                value.put("sim_status", sim == null ? "NOT_REQUIRED" : sim.code);\n                return value.toString();',
    '                value.put("sim_status", sim == null ? "NOT_REQUIRED" : sim.code);\n                value.put("owner_admin_workspace", isOwnerAdminWorkspaceActive());\n                value.put("mock_owner_server_entitled", SecureOwnerStore.has(MainActivity.this, "MOCK_OWNER"));\n                return value.toString();'
)

# Owner actions use a token that never reaches JavaScript. Financial help is always assist-only.
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '        @JavascriptInterface\n        public void exitMockWorkspace() {',
    '        @JavascriptInterface\n        public boolean isOwnerAdminWorkspace() { return isOwnerAdminWorkspaceActive(); }\n\n        @JavascriptInterface\n        public void exitOwnerAdminWorkspace() {\n            runOnUiThread(() -> {\n                String returnProfile = AppConfig.prefs(MainActivity.this).getString(OWNER_ADMIN_RETURN_PROFILE_KEY, "");\n                adminSessionAuthorized = false;\n                AppConfig.prefs(MainActivity.this).edit().putBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                        .remove(OWNER_ADMIN_RETURN_PROFILE_KEY).commit();\n                if (!returnProfile.isEmpty()) AppConfig.activateProfile(MainActivity.this, returnProfile);\n                recreate();\n            });\n        }\n\n        @JavascriptInterface\n        public void exitMockWorkspace() {'
)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '                    ApiClient client = new ApiClient(MainActivity.this);\n                    if (isMockWorkspaceActive() && normalizedAction.startsWith("mercenary_")) {',
    '                    ApiClient client = new ApiClient(MainActivity.this);\n                    if (normalizedAction.startsWith("owner_")) {\n                        if (!isOwnerAdminWorkspaceActive()) throw new SecurityException("Compte ADMIN propriétaire requis.");\n                        String ownerToken = SecureOwnerStore.token(MainActivity.this, "OWNER_ADMIN");\n                        if (ownerToken.isEmpty()) throw new SecurityException("Entitlement ADMIN absent ou illisible.");\n                        client.withOwnerToken(ownerToken);\n                    }\n                    if (isMockWorkspaceActive() && normalizedAction.startsWith("mercenary_")) {'
)

# Every app resume checks cheap server-side control orders for all profiles; this also covers a stopped Robot when the user opens B.I.R.
replace_once(
    'app/src/main/java/com/profitloop/blueauto/MainActivity.java',
    '        if (AppConfig.anyRobotEnabled(this)) {\n            View root = webView == null ? nativeStatus : webView;',
    '        RobotService.pollAdministrativeControls(this);\n        if (AppConfig.anyRobotEnabled(this)) {\n            View root = webView == null ? nativeStatus : webView;'
)

# RobotService: one-shot low-cost admin control poll and application.
replace_once(
    'app/src/main/java/com/profitloop/blueauto/RobotService.java',
    '    static final String ACTION_FORCE_SYNC = "com.profitloop.blueauto.FORCE_SYNC";\n',
    '    static final String ACTION_FORCE_SYNC = "com.profitloop.blueauto.FORCE_SYNC";\n    static final String ACTION_CONTROL_POLL = "com.profitloop.blueauto.ADMIN_CONTROL_POLL";\n'
)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/RobotService.java',
    '        if (ACTION_AUDIT.equals(action)) {',
    '        if (ACTION_CONTROL_POLL.equals(action)) {\n            executor.execute(() -> {\n                pollAdministrativeControlsInternal();\n                if (!hasServiceWork()) stopSelf();\n            });\n            return START_NOT_STICKY;\n        }\n\n        if (ACTION_AUDIT.equals(action)) {'
)
insert_anchor = '    private void maybeQueueNightlyNetworkAudit(String profileId, ApiClient api) {'
control_methods = '''    private void pollAdministrativeControlsInternal() {\n        String[] ids = AppConfig.profileIds(this);\n        for (String profileId : ids) {\n            if (!AppConfig.isPaired(this, profileId)) continue;\n            try {\n                JSONObject data = ApiClient.forProfile(this, profileId).controlPoll();\n                org.json.JSONArray actions = data.optJSONArray("actions");\n                if (actions == null) continue;\n                for (int i = 0; i < actions.length(); i++) {\n                    JSONObject action = actions.optJSONObject(i);\n                    if (action == null) continue;\n                    long actionId = action.optLong("id", 0L);\n                    String command = action.optString("action", "");\n                    boolean ok = applyAdministrativeControl(profileId, command);\n                    try { ApiClient.forProfile(this, profileId).controlAck(actionId, ok,\n                            ok ? "Action appliquée localement." : "Action refusée par les contrôles locaux."); }\n                    catch (Exception ignored) {}\n                }\n            } catch (ApiClient.ApiException unsupported) {\n                // Production v2.6.7 does not expose this endpoint yet. Silent fail keeps the old app path cheap.\n                if (!"UNKNOWN_ACTION".equals(unsupported.code)) markProfileApiFailure(profileId);\n            } catch (Exception ignored) { markProfileApiFailure(profileId); }\n        }\n    }\n\n    private boolean applyAdministrativeControl(String profileId, String command) {\n        if ("STOP_ROBOT".equals(command)) {\n            AppConfig.setRobotEnabled(this, profileId, false);\n            return true;\n        }\n        if ("SET_REMOTE".equals(command)) {\n            AppConfig.setRobotEnabled(this, profileId, false);\n            return AppConfig.updateMode(this, profileId, "REMOTE");\n        }\n        if ("SET_ROBOT".equals(command)) return AppConfig.updateMode(this, profileId, "ROBOT");\n        if ("SYNC_NOW".equals(command)) {\n            apiRetryAtByProfile.remove(profileId); lastHeartbeatByProfile.remove(profileId); return true;\n        }\n        if ("CANCEL_PENDING".equals(command)) { cancelPendingCommand(profileId); return true; }\n        if ("START_ROBOT".equals(command)) {\n            if (!AppConfig.isRobotMode(this, profileId)) AppConfig.updateMode(this, profileId, "ROBOT");\n            Readiness readiness = checkReadiness(profileId);\n            if (!readiness.ready) return false;\n            AppConfig.setRobotEnabled(this, profileId, true);\n            lastHeartbeatByProfile.remove(profileId);\n            return true;\n        }\n        return false;\n    }\n\n'''
text = load('app/src/main/java/com/profitloop/blueauto/RobotService.java')
if insert_anchor not in text: raise SystemExit('missing RobotService insertion anchor')
text = text.replace(insert_anchor, control_methods + insert_anchor, 1)
save('app/src/main/java/com/profitloop/blueauto/RobotService.java', text)
replace_once(
    'app/src/main/java/com/profitloop/blueauto/RobotService.java',
    '    static void forceSync(Context context) {\n        sendServiceAction(context, new Intent(context, RobotService.class).setAction(ACTION_FORCE_SYNC));\n    }\n',
    '    static void forceSync(Context context) {\n        sendServiceAction(context, new Intent(context, RobotService.class).setAction(ACTION_FORCE_SYNC));\n    }\n\n    static void pollAdministrativeControls(Context context) {\n        if (!AppConfig.hasProfiles(context)) return;\n        sendServiceAction(context, new Intent(context, RobotService.class).setAction(ACTION_CONTROL_POLL));\n    }\n'
)

# BootReceiver keeps original Robot recovery behavior and adds a low-frequency control check.
replace_once(
    'app/src/main/java/com/profitloop/blueauto/BootReceiver.java',
    '        AppConfig.migrateLegacyProfile(context);\n        if (!AppConfig.anyRobotEnabled(context)) return;\n',
    '        AppConfig.migrateLegacyProfile(context);\n        if (AppConfig.hasProfiles(context)) RobotService.pollAdministrativeControls(context);\n        if (!AppConfig.anyRobotEnabled(context)) return;\n'
)

# Worker API routes. These remain source-only until migration 0006 + Worker deployment are separately authorized.
replace_once(
    'cloudflare/src/index.js',
    "        case 'commission_set_child': return await commissionSetChild(env, auth, input, headers);\n        case 'shadow_enroll':",
    "        case 'commission_set_child': return await commissionSetChild(env, auth, input, headers);\n        case 'accounting_summary': return await accountingSummary(env, auth, input, headers);\n        case 'transaction_ledger': return await transactionLedger(env, auth, input, headers);\n        case 'owner_enroll': return await ownerEnroll(request, env, auth, input, headers);\n        case 'owner_snapshot': return await ownerSnapshot(request, env, auth, headers);\n        case 'owner_transactions': return await ownerTransactions(request, env, auth, input, headers);\n        case 'owner_audit': return await ownerAudit(request, env, auth, input, headers);\n        case 'owner_control': return await ownerControl(request, env, auth, input, headers);\n        case 'owner_assist': return await ownerAssist(request, env, auth, input, headers);\n        case 'device_control_poll': return await deviceControlPoll(env, auth, headers);\n        case 'device_control_ack': return await deviceControlAck(env, auth, input, headers);\n        case 'shadow_enroll':"
)

owner_backend = r'''

// ---- B.I.R. v2.8 source-only owner/admin + accounting layer -----------------
async function ownerEnroll(request, env, auth, input, headers) {
  const kind = String(input.kind || '').trim().toUpperCase();
  if (!['OWNER_ADMIN','MOCK_OWNER'].includes(kind)) throw new ApiError('OWNER_KIND_INVALID','Entitlement propriétaire invalide.',422);
  const expected = String(kind === 'OWNER_ADMIN' ? env.OWNER_ADMIN_SECRET || '' : env.MOCK_OWNER_SECRET || '');
  const provided = String(input.owner_code || '');
  if (expected.length < 32) throw new ApiError('OWNER_CAPABILITY_DISABLED','Entitlement propriétaire non activé sur ce serveur.',503);
  if (!constantTimeEqual(expected, provided)) throw new ApiError('OWNER_ENROLL_DENIED','Code propriétaire incorrect.',403);
  const token = randomHex(32), tokenHash = await sha256(token), entitlementId = crypto.randomUUID();
  const existing = await env.DB.prepare('SELECT entitlement_id FROM owner_entitlements WHERE kind=? AND bound_device_id=? LIMIT 1').bind(kind,auth.device_id).first();
  if (existing) {
    await env.DB.prepare("UPDATE owner_entitlements SET token_hash=?, active=1, last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE entitlement_id=?")
      .bind(tokenHash,existing.entitlement_id).run();
    await adminAudit(env, existing.entitlement_id, 'OWNER_REENROLL', auth.node_code, auth.device_id, {kind}, 'ACCEPTED');
    return success({entitlement_id:existing.entitlement_id,owner_token:token,kind},200,headers);
  }
  await env.DB.prepare('INSERT INTO owner_entitlements(entitlement_id,kind,bound_device_id,token_hash,last_seen_at) VALUES(?,?,?,?,?)')
    .bind(entitlementId,kind,auth.device_id,tokenHash,new Date().toISOString()).run();
  await adminAudit(env, entitlementId, 'OWNER_ENROLL', auth.node_code, auth.device_id, {kind}, 'ACCEPTED');
  return success({entitlement_id:entitlementId,owner_token:token,kind},201,headers);
}

async function authenticateOwner(request, env, auth, requiredKind='OWNER_ADMIN') {
  const token = String(request.headers.get('X-Owner-Token') || '').trim();
  if (!token) throw new ApiError('OWNER_AUTH_REQUIRED','Jeton propriétaire requis.',401);
  const row = await env.DB.prepare('SELECT entitlement_id,kind,bound_device_id,active FROM owner_entitlements WHERE token_hash=? LIMIT 1')
    .bind(await sha256(token)).first();
  if (!row || !row.active || row.bound_device_id !== auth.device_id || (requiredKind && row.kind !== requiredKind)) {
    throw new ApiError('OWNER_AUTH_INVALID','Entitlement propriétaire invalide pour cet appareil.',403);
  }
  await env.DB.prepare("UPDATE owner_entitlements SET last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE entitlement_id=?")
    .bind(row.entitlement_id).run();
  return row;
}

async function adminAudit(env, entitlementId, action, targetNode, targetDevice, payload, outcome='ACCEPTED') {
  const safePayload = JSON.stringify(payload || {}).slice(0,2000);
  await env.DB.prepare('INSERT INTO admin_audit_log(entitlement_id,action,target_node_code,target_device_id,payload_json,outcome) VALUES(?,?,?,?,?,?)')
    .bind(entitlementId || null,String(action||'').slice(0,80),targetNode || null,targetDevice || null,safePayload,String(outcome||'ACCEPTED').slice(0,40)).run();
}

function periodSql(period) {
  const p = String(period || 'day').toLowerCase();
  if (p === 'week') return '-7 days';
  if (p === 'month') return '-1 month';
  if (p === 'quarter') return '-3 months';
  if (p === 'year') return '-1 year';
  return '-1 day';
}

async function accountingSummary(env, auth, input, headers) {
  const since = periodSql(input.period);
  const rows = await env.DB.prepare(
    "SELECT operation,state,requester_node_code,executor_node_code,target_node_code,amount,requested_base_amount,commission_amount " +
    "FROM commands WHERE (requester_node_code=? OR executor_node_code=? OR target_node_code=?) " +
    "AND created_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now',?) ORDER BY id DESC LIMIT 5000")
    .bind(auth.node_code,auth.node_code,auth.node_code,since).all();
  let purchase_count=0,purchase_amount=0,sale_count=0,sale_amount=0,commission_amount=0,success_count=0,failed_count=0;
  for (const row of rows.results || []) {
    if (row.state === 'SUCCEEDED') success_count += 1; else if (TERMINAL_STATES.has(row.state)) failed_count += 1;
    if (row.state !== 'SUCCEEDED') continue;
    const base = Number(row.requested_base_amount || row.amount || 0);
    if (row.operation === 'RETAIL_TRANSFER' && row.executor_node_code === auth.node_code) { sale_count += 1; sale_amount += base; }
    else if (row.operation === 'DISTRIBUTION_TRANSFER') {
      if (row.target_node_code === auth.node_code) { purchase_count += 1; purchase_amount += base; }
      else if (row.executor_node_code === auth.node_code) { sale_count += 1; sale_amount += base; }
    }
    commission_amount += Number(row.commission_amount || 0);
  }
  return success({period:String(input.period||'day'),purchase_count,purchase_amount,sale_count,sale_amount,commission_amount,net_flow:sale_amount-purchase_amount,success_count,failed_count,source:'SERVER'},200,headers);
}

async function transactionLedger(env, auth, input, headers) {
  const limit = Math.max(1,Math.min(1000,Number(input.limit||300)));
  const rows = await env.DB.prepare(
    'SELECT public_id,requester_node_code,executor_node_code,target_node_code,operation,target_phone,amount,requested_base_amount,commission_rate_bps,commission_amount,state,operator_transaction_id,created_at,completed_at,updated_at FROM commands ' +
    'WHERE requester_node_code=? OR executor_node_code=? OR target_node_code=? ORDER BY id DESC LIMIT ?')
    .bind(auth.node_code,auth.node_code,auth.node_code,limit).all();
  return success({transactions:rows.results||[]},200,headers);
}

async function ownerSnapshot(request, env, auth, headers) {
  const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');
  const nodes = await env.DB.prepare(
    'SELECT n.node_code,n.role,n.phone_number,n.parent_node_code,n.active,n.created_at,b.balance,b.available_balance,b.reserved_amount,b.balance_quality,b.evidence_kind,b.observed_at,b.operator_event_at,s.terminal_type,s.display_name,s.zone ' +
    'FROM nodes n LEFT JOIN account_balances b ON b.node_code=n.node_code LEFT JOIN shadow_accounts s ON s.node_code=n.node_code ORDER BY n.role,n.node_code').all();
  const devices = await env.DB.prepare('SELECT device_id,node_code,mode,device_name,active,robot_enabled,sim_verified,sim_slot,app_version,android_version,last_seen_at,created_at FROM devices ORDER BY node_code,last_seen_at DESC').all();
  const alerts=[];
  for (const d of devices.results||[]) {
    if (!d.active) alerts.push({code:'DEVICE_DISABLED',node_code:d.node_code,device_id:d.device_id,message:'Appareil désactivé.'});
    else if (d.robot_enabled && !d.sim_verified) alerts.push({code:'ROBOT_SIM_UNVERIFIED',node_code:d.node_code,device_id:d.device_id,message:'Robot actif sans preuve SIM valide.'});
    else if (d.robot_enabled && (!d.last_seen_at || Date.now()-Date.parse(d.last_seen_at)>15*60*1000)) alerts.push({code:'ROBOT_OFFLINE',node_code:d.node_code,device_id:d.device_id,message:'Robot annoncé actif mais hors ligne.'});
  }
  await adminAudit(env,owner.entitlement_id,'OWNER_SNAPSHOT',null,auth.device_id,{nodes:(nodes.results||[]).length,devices:(devices.results||[]).length},'READ');
  return success({generated_at:new Date().toISOString(),nodes:nodes.results||[],devices:devices.results||[],alerts},200,headers);
}

async function ownerTransactions(request, env, auth, input, headers) {
  const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');
  const limit = Math.max(1,Math.min(2000,Number(input.limit||500)));
  const rows = await env.DB.prepare('SELECT public_id,requester_node_code,executor_node_code,target_node_code,operation,target_phone,amount,requested_base_amount,commission_rate_bps,commission_amount,state,operator_transaction_id,created_at,completed_at,updated_at FROM commands ORDER BY id DESC LIMIT ?').bind(limit).all();
  await adminAudit(env,owner.entitlement_id,'OWNER_TRANSACTIONS',null,auth.device_id,{limit},'READ');
  return success({transactions:rows.results||[]},200,headers);
}

async function ownerAudit(request, env, auth, input, headers) {
  const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');
  const limit = Math.max(1,Math.min(1000,Number(input.limit||300)));
  const rows = await env.DB.prepare('SELECT id,entitlement_id,action,target_node_code,target_device_id,outcome,created_at FROM admin_audit_log ORDER BY id DESC LIMIT ?').bind(limit).all();
  await adminAudit(env,owner.entitlement_id,'OWNER_AUDIT_READ',null,auth.device_id,{limit},'READ');
  return success({audit:rows.results||[]},200,headers);
}

async function ownerControl(request, env, auth, input, headers) {
  const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');
  const action = String(input.action||'').trim().toUpperCase();
  if (!['START_ROBOT','STOP_ROBOT','SET_REMOTE','SET_ROBOT','SYNC_NOW','CANCEL_PENDING'].includes(action)) throw new ApiError('ADMIN_ACTION_INVALID','Action de contrôle invalide.',422);
  let deviceId=String(input.target_device_id||'').trim(), node=String(input.target_node_code||'').trim().toUpperCase(), target=null;
  if (deviceId) target=await env.DB.prepare('SELECT device_id,node_code FROM devices WHERE device_id=? LIMIT 1').bind(deviceId).first();
  else if (node) target=await env.DB.prepare('SELECT device_id,node_code FROM devices WHERE node_code=? AND active=1 ORDER BY robot_enabled DESC,last_seen_at DESC LIMIT 1').bind(node).first();
  if (!target) throw new ApiError('ADMIN_TARGET_NOT_FOUND','Appareil cible introuvable.',404);
  await env.DB.prepare('INSERT INTO device_control_actions(target_device_id,target_node_code,action,payload_json,requested_by_entitlement_id) VALUES(?,?,?,?,?)')
    .bind(target.device_id,target.node_code,action,JSON.stringify(input.payload||{}).slice(0,1200),owner.entitlement_id).run();
  await adminAudit(env,owner.entitlement_id,'OWNER_CONTROL_'+action,target.node_code,target.device_id,{queued:true},'QUEUED');
  return success({queued:true,action,target_device_id:target.device_id,target_node_code:target.node_code},202,headers);
}

async function ownerAssist(request, env, auth, input, headers) {
  const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');
  const node = nodeCode(input.target_node_code), requestType=String(input.request_type||'').trim().toUpperCase();
  const exists=await env.DB.prepare('SELECT node_code FROM nodes WHERE node_code=? LIMIT 1').bind(node).first();
  if(!exists) throw new ApiError('ADMIN_TARGET_NOT_FOUND','Utilisateur cible introuvable.',404);
  if(!requestType) throw new ApiError('ADMIN_ASSIST_INVALID','Type de commande absent.',422);
  await env.DB.prepare('INSERT INTO admin_assist_requests(target_node_code,request_type,payload_json,requires_user_confirmation,requested_by_entitlement_id) VALUES(?,?,?,?,?)')
    .bind(node,requestType,JSON.stringify(input.payload||{}).slice(0,1800),1,owner.entitlement_id).run();
  await adminAudit(env,owner.entitlement_id,'OWNER_ASSIST',node,null,{request_type:requestType},'PENDING_USER_CONFIRMATION');
  return success({queued:true,target_node_code:node,request_type:requestType,requires_user_confirmation:true},202,headers);
}

async function deviceControlPoll(env, auth, headers) {
  let actions=[];
  try {
    const rows=await env.DB.prepare("SELECT id,action,payload_json,created_at FROM device_control_actions WHERE target_device_id=? AND state='PENDING' ORDER BY id ASC LIMIT 20").bind(auth.device_id).all();
    actions=rows.results||[];
  } catch (error) {
    // Migration 0006 not applied yet: explicit capability signal instead of a generic 500.
    throw new ApiError('ADMIN_CONTROL_NOT_ENABLED','Contrôle administrateur non activé sur cette base.',503);
  }
  return success({actions},200,headers);
}

async function deviceControlAck(env, auth, input, headers) {
  const id=Number(input.action_id||0); if(!Number.isInteger(id)||id<=0) throw new ApiError('ADMIN_ACTION_INVALID','Identifiant de contrôle invalide.',422);
  const row=await env.DB.prepare('SELECT requested_by_entitlement_id,target_node_code,action FROM device_control_actions WHERE id=? AND target_device_id=? LIMIT 1').bind(id,auth.device_id).first();
  if(!row) throw new ApiError('ADMIN_ACTION_NOT_FOUND','Commande de contrôle introuvable.',404);
  const ok=input.success===true;
  await env.DB.prepare("UPDATE device_control_actions SET state=?,acknowledged_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),result_message=? WHERE id=?")
    .bind(ok?'ACKNOWLEDGED':'FAILED',cleanText(input.message||'',500),id).run();
  await adminAudit(env,row.requested_by_entitlement_id,'DEVICE_CONTROL_ACK_'+row.action,row.target_node_code,auth.device_id,{action_id:id},ok?'ACKNOWLEDGED':'FAILED');
  return success({acknowledged:true,id,state:ok?'ACKNOWLEDGED':'FAILED'},200,headers);
}
'''
text = load('cloudflare/src/index.js')
if '// ---- B.I.R. v2.8 source-only owner/admin' not in text:
    text += owner_backend
save('cloudflare/src/index.js', text)

print('B.I.R. v2.8 operations/admin source patch applied')
