from pathlib import Path


def patch(path, old, new, count=1):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f'{path}: expected {count} occurrence(s), got {actual} for anchor {old[:80]!r}')
    p.write_text(text.replace(old, new, count), encoding='utf-8')

# Release identity: never overwrite the already released permanent code 55.
patch('app/build.gradle', 'versionCode 55', 'versionCode 56')
patch('app/build.gradle', 'versionName "2.9.0"', 'versionName "2.9.1"')

# API telemetry identifies this Android hotfix while remaining compatible with Worker 2.9.
api = Path('app/src/main/java/com/profitloop/blueauto/ApiClient.java')
api_text = api.read_text(encoding='utf-8')
if api_text.count('payload.put("app_version", "2.9.0");') != 2:
    raise SystemExit('ApiClient app_version anchors changed')
api.write_text(api_text.replace('payload.put("app_version", "2.9.0");', 'payload.put("app_version", "2.9.1");'), encoding='utf-8')

main = Path('app/src/main/java/com/profitloop/blueauto/MainActivity.java')
text = main.read_text(encoding='utf-8')
old_prompt = '''            @Override
            public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, JsPromptResult result) {
                final EditText input = new EditText(MainActivity.this);
                input.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
                input.setText(defaultValue == null ? "" : defaultValue);
                input.setSelectAllOnFocus(true);
                int pad = dp(18); input.setPadding(pad, dp(8), pad, dp(8));
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("Taux de commission")
                        .setMessage(message)
                        .setView(input)
                        .setPositiveButton("VALIDER LE TAUX", (dialog, which) -> result.confirm(input.getText().toString().trim()))
                        .setNegativeButton("ANNULER", (dialog, which) -> result.cancel())
                        .setOnCancelListener(dialog -> result.cancel())
                        .show();
                return true;
            }
'''
new_prompt = '''            @Override
            public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, JsPromptResult result) {
                final String promptMessage = message == null ? "" : message;
                final String normalizedPrompt = promptMessage.toLowerCase(Locale.ROOT);
                final boolean commissionPrompt = normalizedPrompt.contains("commission")
                        || normalizedPrompt.contains("taux") || normalizedPrompt.contains("rate");
                final boolean supportPrompt = normalizedPrompt.contains("décrivez très simplement")
                        || normalizedPrompt.contains("decrivez tres simplement")
                        || normalizedPrompt.contains("describe the problem")
                        || normalizedPrompt.contains("secours") || normalizedPrompt.contains("sav");
                final EditText input = new EditText(MainActivity.this);
                if (commissionPrompt) {
                    input.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
                    input.setSelectAllOnFocus(true);
                } else {
                    input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                            | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
                    input.setMinLines(3);
                    input.setMaxLines(6);
                    input.setSingleLine(false);
                }
                input.setText(defaultValue == null ? "" : defaultValue);
                int pad = dp(18); input.setPadding(pad, dp(8), pad, dp(8));
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle(commissionPrompt ? "Taux de commission"
                                : supportPrompt ? "Secours / SAV" : "Saisie B.I.R.")
                        .setMessage(promptMessage)
                        .setView(input)
                        .setPositiveButton(commissionPrompt ? "VALIDER LE TAUX"
                                : supportPrompt ? "ENVOYER" : "VALIDER",
                                (dialog, which) -> result.confirm(input.getText().toString().trim()))
                        .setNegativeButton("ANNULER", (dialog, which) -> result.cancel())
                        .setOnCancelListener(dialog -> result.cancel())
                        .show();
                return true;
            }
'''
if text.count(old_prompt) != 1:
    raise SystemExit('MainActivity onJsPrompt anchor changed')
text = text.replace(old_prompt, new_prompt, 1)
text = text.replace('AppConfig.profileId(MainActivity.this), 20_000L);', 'AppConfig.profileId(MainActivity.this), 6_000L);', 1)
old_sync = '''        @JavascriptInterface
        public void synchronizeNow() {
            RobotService.forceSync(MainActivity.this);
            runOnUiThread(() -> toast("Synchronisation de tous les comptes relancée immédiatement."));
        }
'''
new_sync = '''        @JavascriptInterface
        public void synchronizeNow() {
            RobotService.forceSync(MainActivity.this);
            runOnUiThread(() -> toast("Synchronisation de tous les comptes relancée immédiatement."));
        }

        @JavascriptInterface
        public void kickSynchronization() {
            // Silent, non-financial control-plane wake used by the field self-healing layer.
            // It never creates a command and never dials USSD.
            RobotService.forceSync(MainActivity.this);
        }
'''
if text.count(old_sync) != 1:
    raise SystemExit('MainActivity synchronizeNow anchor changed')
text = text.replace(old_sync, new_sync, 1)
main.write_text(text, encoding='utf-8')

robot = Path('app/src/main/java/com/profitloop/blueauto/RobotService.java')
text = robot.read_text(encoding='utf-8')
for old, new in [
    ('private static final long REMOTE_SNAPSHOT_MS = 15_000L;', 'private static final long REMOTE_SNAPSHOT_MS = 5_000L;'),
    ('private static final long REMOTE_HEARTBEAT_MS = 60_000L;', 'private static final long REMOTE_HEARTBEAT_MS = 20_000L;'),
    ('private static final long REMOTE_MAX_RETRY_MS = 120_000L;', 'private static final long REMOTE_MAX_RETRY_MS = 30_000L;')
]:
    if text.count(old) != 1:
        raise SystemExit(f'RobotService constant anchor changed: {old}')
    text = text.replace(old, new, 1)
old_force = '''        if (ACTION_FORCE_SYNC.equals(action)) {
            apiRetryAtByProfile.clear();
            apiFailureCountByProfile.clear();
            lastHeartbeatByProfile.clear();
            backoffMs = 250L;
            updateNotification(robotSummary("Synchronisation forcée de tous les comptes"));
            scheduleCycle(0L);
            return START_STICKY;
        }
'''
new_force = '''        if (ACTION_FORCE_SYNC.equals(action)) {
            apiRetryAtByProfile.clear();
            apiFailureCountByProfile.clear();
            lastHeartbeatByProfile.clear();
            lastRemoteSnapshotByProfile.clear();
            backoffMs = 250L;
            updateNotification(robotSummary("Auto-Réveil — reprise immédiate de la synchronisation"));
            executor.execute(() -> {
                OfflineSyncManager.syncSome(this, 25);
                retryDueFinalReports(8);
            });
            scheduleCycle(0L);
            scheduleWatchdog(this, 5_000L);
            return START_STICKY;
        }
'''
if text.count(old_force) != 1:
    raise SystemExit('RobotService FORCE_SYNC anchor changed')
text = text.replace(old_force, new_force, 1)
robot.write_text(text, encoding='utf-8')

app = Path('app/src/main/assets/app.js')
text = app.read_text(encoding='utf-8')
if text.count('now-dashboardLoadedAt<15000') != 1:
    raise SystemExit('app.js dashboard throttle anchor changed')
text = text.replace('now-dashboardLoadedAt<15000', 'now-dashboardLoadedAt<5000', 1)
if text.count('requestDashboard(false);scheduleDashboardPoll();},60000);') != 1:
    raise SystemExit('app.js dashboard timer anchor changed')
text = text.replace('requestDashboard(false);scheduleDashboardPoll();},60000);', 'requestDashboard(false);scheduleDashboardPoll();},5000);', 1)
old_created = 'clearSubmittedFields(submitted);upsert(command);render();scheduleCommandPoll(1200);'
new_created = 'clearSubmittedFields(submitted);upsert(command);render();try{if(window.AndroidBridge.kickSynchronization){window.AndroidBridge.kickSynchronization();}}catch(ignored){}scheduleCommandPoll(1200);'
if text.count(old_created) != 1:
    raise SystemExit('app.js created wake anchor changed')
text = text.replace(old_created, new_created, 1)
old_terminal = 'if(TERMINAL[data.command.state]){requestDashboard(true);}'
new_terminal = 'if(TERMINAL[data.command.state]){try{if(window.AndroidBridge.kickSynchronization){window.AndroidBridge.kickSynchronization();}}catch(ignored){}requestDashboard(true);}'
if text.count(old_terminal) != 1:
    raise SystemExit('app.js terminal wake anchor changed')
text = text.replace(old_terminal, new_terminal, 1)
app.write_text(text, encoding='utf-8')

balance = Path('app/src/main/assets/balance-engine-v280.js')
text = balance.read_text(encoding='utf-8')
old_move = "  var op=upper(entry.op),target=upper(entry.target),node=upper(configuration.node_code),amount=num(entry.amount);\n  if(!amount)return 0;\n  if(op.indexOf('RETAIL')>=0||op==='RETAIL_SALE')return -amount;\n  if(op.indexOf('DISTRIBUTION')>=0||op==='SUPPLY_CHILD'||op==='REQUEST_SUPPLY')return target===node?amount:-amount;\n"
new_move = "  var op=upper(entry.op),target=upper(entry.target),node=upper(configuration.node_code),amount=num(entry.amount),base=num(entry.base||entry.amount),commission=num(entry.commission),total=(base||amount)+commission;\n  if(!amount&&!base)return 0;\n  if(op.indexOf('RETAIL')>=0||op==='RETAIL_SALE')return -amount;\n  if(op.indexOf('DISTRIBUTION')>=0||op==='SUPPLY_CHILD'||op==='REQUEST_SUPPLY')return target===node?(base||amount):-(commission>0?total:amount);\n"
if text.count(old_move) != 1:
    raise SystemExit('balance movement anchor changed')
text = text.replace(old_move, new_move, 1)
old_render = "function render(s){var card=document.getElementById('birBalanceFreshness'),own=document.getElementById('ownBalance'),main=document.getElementById('birCamtelBalance');if(!s)return;if(s.balance!==null&&s.reusable){if(own)own.textContent=money(s.balance)+' FCFA';if(main)main.textContent=money(s.balance);}if(card){if(s.quality==='CERTIFIED')card.textContent='Preuve Blue certifiée • aucune interrogation USSD nécessaire';else if(s.quality==='RECALCULATED')card.textContent='Solde recalculé • preuve certifiée + '+String(s.movements||0)+' mouvement(s) confirmé(s)';else card.textContent='Solde à rapprocher • une nouvelle preuve Blue sera requise avant finance';}}"
new_render = "function render(s){var card=document.getElementById('birBalanceFreshness'),own=document.getElementById('ownBalance'),main=document.getElementById('birCamtelBalance'),label;if(!s)return;if(s.balance!==null){label=(s.reusable?'':'≈ ')+money(s.balance);if(own)own.textContent=label+' FCFA';if(main)main.textContent=label;}if(card){if(s.quality==='CERTIFIED')card.textContent='Preuve Blue certifiée • aucune interrogation USSD nécessaire';else if(s.quality==='RECALCULATED')card.textContent='Solde recalculé • preuve certifiée + '+String(s.movements||0)+' mouvement(s) confirmé(s)';else card.textContent='≈ Estimation B.I.R. à rapprocher • ne pas la confondre avec un solde Blue certifié';}}"
if text.count(old_render) != 1:
    raise SystemExit('balance render anchor changed')
text = text.replace(old_render, new_render, 1)
balance.write_text(text, encoding='utf-8')

index = Path('app/src/main/assets/index.html')
text = index.read_text(encoding='utf-8')
css_anchor = '    <link rel="stylesheet" href="control-tower-v290-ops.css">\n'
js_anchor = '<script src="control-tower-v290-ops.js"></script>\n'
if text.count(css_anchor) != 1 or text.count(js_anchor) != 1:
    raise SystemExit('index v2.9 anchors changed')
text = text.replace(css_anchor, css_anchor + '    <link rel="stylesheet" href="field-recovery-v291.css">\n', 1)
text = text.replace(js_anchor, js_anchor + '<script src="field-recovery-v291.js"></script>\n', 1)
index.write_text(text, encoding='utf-8')

print('BIR v2.9.1 field recovery patch applied')
