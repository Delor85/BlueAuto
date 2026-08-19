from pathlib import Path
import re


def read(path):
    return Path(path).read_text(encoding='utf-8')

def write(path, text):
    Path(path).write_text(text, encoding='utf-8')

def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1 anchor, got {count}')
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Version metadata
# ---------------------------------------------------------------------------
p='app/build.gradle'; s=read(p)
s=re.sub(r'versionCode\s+57\b','versionCode 58',s,count=1)
s=re.sub(r'versionName\s+"2\.9\.2"','versionName "2.9.3"',s,count=1)
write(p,s)

# ---------------------------------------------------------------------------
# Local event synchronization: only explicitly safe event kinds become pending.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/LocalEventStore.java'; s=read(p)
old='''        v.put("payload", payload == null ? "{}" : payload.toString());\n        v.put("created_at", System.currentTimeMillis()); v.put("sync_state", "LOCAL_COMMAND_RESULT".equals(kind) ? "PENDING" : "LOCAL");\n'''
new='''        v.put("payload", payload == null ? "{}" : payload.toString());\n        String safeKind = kind == null ? "EVENT" : kind;\n        boolean syncable = "LOCAL_COMMAND_RESULT".equals(safeKind)\n                || "LOCAL_COMMAND_QUEUED".equals(safeKind)\n                || "REMOTE_ORDER_RECEIVED".equals(safeKind)\n                || "LOCAL_PROGRESS".equals(safeKind)\n                || "QUEUE_RECOVERY".equals(safeKind)\n                || "ACCESSIBILITY_STATE".equals(safeKind);\n        v.put("created_at", System.currentTimeMillis());\n        v.put("sync_state", syncable ? "PENDING" : "LOCAL");\n'''
s=once(s,old,new,'LocalEventStore sync state')
write(p,s)

# ---------------------------------------------------------------------------
# Accessibility: immediately promote a trusted operator balance to native store.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java'; s=read(p)
old='''            if ((parsedBlue.terminalSuccess() || (!parsedBlue.processing && containsAny(resultNormalized, "processed successfully",\n                    "successfully transferred", "transfer successfully", "you transfer")))\n                    && resultBelongsToVerifiedSession(command)) {\n                lastResultAt = System.currentTimeMillis();\n                RobotService.operatorResult(this, profileId, true, "",\n'''
new='''            if ((parsedBlue.terminalSuccess() || (!parsedBlue.processing && containsAny(resultNormalized, "processed successfully",\n                    "successfully transferred", "transfer successfully", "you transfer")))\n                    && resultBelongsToVerifiedSession(command)) {\n                lastResultAt = System.currentTimeMillis();\n                if (parsedBlue.currentBalanceFcfa != null) {\n                    CertifiedBalanceStore.observeTrusted(this, profileId, parsedBlue);\n                }\n                RobotService.operatorResult(this, profileId, true, "",\n'''
s=once(s,old,new,'Accessibility financial proof')
old='''        if (("BALANCE_OWN".equals(operation) || "BALANCE_CHILD".equals(operation))\n                && !trustedResult.isEmpty()) {\n            lastResultAt = System.currentTimeMillis();\n            RobotService.operatorResult(this, profileId, true, "",\n'''
new='''        if (("BALANCE_OWN".equals(operation) || "BALANCE_CHILD".equals(operation))\n                && !trustedResult.isEmpty()) {\n            lastResultAt = System.currentTimeMillis();\n            if ("BALANCE_OWN".equals(operation) && parsedBlue.currentBalanceFcfa != null) {\n                CertifiedBalanceStore.observeTrusted(this, profileId, parsedBlue);\n            }\n            RobotService.operatorResult(this, profileId, true, "",\n'''
s=once(s,old,new,'Accessibility own balance proof')
old='''        if ((isRecognizedInformationResult(operation, normalize(trustedResult))\n                || isRecognizedAdministrationResult(operation, normalize(trustedResult)))\n                && !trustedResult.isEmpty()) {\n            lastResultAt = System.currentTimeMillis();\n            RobotService.operatorResult(this, profileId, true, "",\n'''
new='''        if ((isRecognizedInformationResult(operation, normalize(trustedResult))\n                || isRecognizedAdministrationResult(operation, normalize(trustedResult)))\n                && !trustedResult.isEmpty()) {\n            lastResultAt = System.currentTimeMillis();\n            if (("HISTORY_LAST5".equals(operation) || "TRANSACTION_DETAIL".equals(operation))\n                    && parsedBlue.currentBalanceFcfa != null) {\n                CertifiedBalanceStore.observeTrusted(this, profileId, parsedBlue);\n            }\n            RobotService.operatorResult(this, profileId, true, "",\n'''
s=once(s,old,new,'Accessibility information proof')
write(p,s)

# ---------------------------------------------------------------------------
# API client: version + queue reconciliation methods + command-center actions.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/ApiClient.java'; s=read(p)
s=s.replace('payload.put("app_version", "2.9.2");','payload.put("app_version", "2.9.3");')
old='''    JSONObject leaseCommand() throws Exception {\n        return postControl("lease_command", new JSONObject(), true);\n    }\n\n'''
new='''    JSONObject leaseCommand() throws Exception {\n        return postControl("lease_command", new JSONObject(), true);\n    }\n\n    JSONObject queueSnapshot() throws Exception {\n        return postControl("queue_snapshot", new JSONObject(), true);\n    }\n\n    JSONObject recoverLease(String publicId) throws Exception {\n        JSONObject payload = new JSONObject();\n        payload.put("command_id", publicId == null ? "" : publicId.trim());\n        return postControl("recover_lease", payload, true);\n    }\n\n'''
s=once(s,old,new,'ApiClient queue methods')
old='''(?:operator_insights|operator_catalog|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale|commission_policy|commission_set_default|commission_set_child|accounting_summary|transaction_ledger|ops_cockpit|ops_assist|ops_escalate|ops_resolve|owner_ops_cockpit|owner_ops_resolve|owner_snapshot|owner_transactions|owner_audit|owner_control|owner_assist|owner_tchoronko_save)'''
new='''(?:operator_insights|operator_catalog|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale|commission_policy|commission_set_default|commission_set_child|accounting_summary|transaction_ledger|ops_cockpit|ops_assist|ops_escalate|ops_resolve|distribution_command_center|reconciliation_center|owner_distribution_command_center|owner_ops_cockpit|owner_ops_resolve|owner_snapshot|owner_transactions|owner_audit|owner_control|owner_assist|owner_tchoronko_save)'''
s=once(s,old,new,'ApiClient platform whitelist')
write(p,s)

# ---------------------------------------------------------------------------
# Main bridge: expose native balance and unified queue; refresh server queue.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/MainActivity.java'; s=read(p)
old='''                value.put("offline_pending_events", LocalEventStore.pendingCount(MainActivity.this));\n                value.put("robot_offline_capable", AppConfig.isRobotMode(MainActivity.this));\n                return value.toString();\n'''
new='''                value.put("offline_pending_events", LocalEventStore.pendingCount(MainActivity.this));\n                value.put("robot_offline_capable", AppConfig.isRobotMode(MainActivity.this));\n                JSONObject certified = CertifiedBalanceStore.get(MainActivity.this, AppConfig.profileId(MainActivity.this));\n                value.put("certified_balance", certified == null ? JSONObject.NULL : certified);\n                value.put("unified_queue", ServerQueueMirrorStore.unified(MainActivity.this, AppConfig.profileId(MainActivity.this)));\n                return value.toString();\n'''
s=once(s,old,new,'Main configuration native truth')
old='''        @JavascriptInterface\n        public void previewCommand(String requestType, String targetNode, String targetPhone,\n'''
new='''        @JavascriptInterface\n        public String getCertifiedBalance() {\n            return CertifiedBalanceStore.json(MainActivity.this, AppConfig.profileId(MainActivity.this));\n        }\n\n        @JavascriptInterface\n        public String getUnifiedQueueSnapshot() {\n            return ServerQueueMirrorStore.unified(MainActivity.this, AppConfig.profileId(MainActivity.this)).toString();\n        }\n\n        @JavascriptInterface\n        public void refreshQueueSnapshot() {\n            final String profileId = AppConfig.profileId(MainActivity.this);\n            new Thread(() -> {\n                try {\n                    JSONObject snapshot = ApiClient.forProfile(MainActivity.this, profileId).queueSnapshot();\n                    ServerQueueMirrorStore.save(MainActivity.this, profileId, snapshot);\n                    callback("onQueueSnapshot", snapshot);\n                } catch (Exception error) {\n                    JSONObject cached = ServerQueueMirrorStore.get(MainActivity.this, profileId);\n                    if (cached != null) callback("onQueueSnapshot", cached);\n                    else callbackError("onQueueSnapshot", error);\n                }\n            }, "BIR-QueueSnapshot-v293").start();\n        }\n\n        @JavascriptInterface\n        public void previewCommand(String requestType, String targetNode, String targetPhone,\n'''
s=once(s,old,new,'Main bridge queue methods')
write(p,s)

# ---------------------------------------------------------------------------
# RobotService: safe same-device lease recovery + accessibility reconnect grace.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/RobotService.java'; s=read(p)
old='''    private static final long SIMPLE_UNLOCK_WAIT_MS = 3_500L;\n    private static final long SIMPLE_UNLOCK_COOLDOWN_MS = 30_000L;\n'''
new='''    private static final long SIMPLE_UNLOCK_WAIT_MS = 3_500L;\n    private static final long SIMPLE_UNLOCK_COOLDOWN_MS = 30_000L;\n    private static final long ACCESSIBILITY_RECONNECT_GRACE_MS = 45_000L;\n'''
s=once(s,old,new,'Robot accessibility grace constant')
old='''                    if (lease.optBoolean("available", false)) {\n                        JSONObject command = lease.optJSONObject("command");\n'''
new='''                    if (lease.optBoolean("busy", false)) {\n                        ServerQueueMirrorStore.observeBusy(this, profileId, lease);\n                        JSONObject active = lease.optJSONObject("active_command");\n                        if (active != null && PendingCommandStore.get(this, profileId) == null\n                                && PendingCommandStore.LEASED.equals(active.optString("state", ""))) {\n                            try {\n                                JSONObject recovered = api.recoverLease(active.optString("public_id", ""));\n                                if (recovered.optBoolean("recovered", false)) {\n                                    JSONObject restored = recovered.optJSONObject("command");\n                                    if (restored != null) {\n                                        restored.put("local_profile_id", profileId);\n                                        restored.put("local_state", PendingCommandStore.LEASED);\n                                        restored.put("leased_at", System.currentTimeMillis());\n                                        restored.put("state_changed_at", System.currentTimeMillis());\n                                        restored.put("lease_recovered", true);\n                                        PendingCommandStore.save(this, profileId, restored);\n                                        JSONObject evidence = new JSONObject(restored.toString());\n                                        evidence.remove("lease_token");\n                                        LocalEventStore.append(this, profileId, restored.optString("public_id"),\n                                                "QUEUE_RECOVERY", evidence);\n                                        updateNotification(robotSummary("File serveur récupérée sans recomposer la transaction"));\n                                        nextDelay = 250L;\n                                        return;\n                                    }\n                                }\n                            } catch (Exception ignored) {\n                                // The command stays visible in the mirror and will be retried safely.\n                            }\n                        }\n                    }\n                    if (lease.optBoolean("available", false)) {\n                        JSONObject command = lease.optJSONObject("command");\n'''
s=once(s,old,new,'Robot busy lease recovery')
old='''    private void holdLeaseForAccessibility(String profileId, JSONObject command, ApiClient api) {\n        boolean granted = BlueAccessibilityService.isEnabled(this);\n        if (command != null && command.optBoolean("local_origin", false)) {\n            updateNotification(robotSummary(granted ? "Accessibilité autorisée, service Android en reconnexion — commande locale conservée" : "Accessibilité désactivée par Android/utilisateur — commande locale conservée, réactivation requise"));\n            scheduleWatchdog(this, granted ? 5_000L : 30_000L); return;\n        }\n        String reason = granted\n                ? "Accessibilité Android autorisée mais service en reconnexion; aucune composition financière avant reconnexion."\n                : "Accessibilité Android désactivée; réactivation utilisateur requise avant achat/vente.";\n        releaseUnexecutedLease(profileId, command, api, reason);\n        apiRetryAtByProfile.put(profileId, System.currentTimeMillis() + (granted ? 5_000L : 30_000L));\n        updateNotification(robotSummary(granted\n                ? "Accessibilité en reconnexion — Robot conservé, reprise automatique dès retour du service"\n                : "Accessibilité désactivée — Robot conservé, achat/vente en attente de réactivation"));\n    }\n'''
new='''    private void holdLeaseForAccessibility(String profileId, JSONObject command, ApiClient api) {\n        boolean granted = BlueAccessibilityService.isEnabled(this);\n        long now = System.currentTimeMillis();\n        if (command != null && command.optBoolean("local_origin", false)) {\n            updateNotification(robotSummary(granted ? "Accessibilité autorisée, service Android en reconnexion — commande locale conservée" : "Accessibilité désactivée par Android/utilisateur — commande locale conservée, réactivation requise"));\n            scheduleWatchdog(this, granted ? 5_000L : 30_000L); return;\n        }\n        if (granted && command != null) {\n            long started = command.optLong("accessibility_wait_started_at", 0L);\n            if (started <= 0L) {\n                started = now;\n                try {\n                    command.put("accessibility_wait_started_at", started);\n                    PendingCommandStore.save(this, profileId, command);\n                    JSONObject event = new JSONObject();\n                    event.put("state", "AUTHORIZED_RECONNECTING");\n                    LocalEventStore.append(this, profileId, command.optString("public_id"),\n                            "ACCESSIBILITY_STATE", event);\n                } catch (Exception ignored) {}\n            }\n            if (now - started < ACCESSIBILITY_RECONNECT_GRACE_MS) {\n                updateNotification(robotSummary("Accessibilité toujours autorisée — reconnexion Android en cours, lease conservé"));\n                scheduleWatchdog(this, 5_000L);\n                return;\n            }\n        }\n        String reason = granted\n                ? "Accessibilité toujours autorisée mais reconnexion trop longue; lease relâché avant expiration, sans composition."\n                : "Accessibilité Android réellement désactivée; réactivation utilisateur requise avant achat/vente.";\n        releaseUnexecutedLease(profileId, command, api, reason);\n        apiRetryAtByProfile.put(profileId, now + (granted ? 5_000L : 30_000L));\n        updateNotification(robotSummary(granted\n                ? "Accessibilité autorisée mais service instable — file conservée côté serveur"\n                : "Accessibilité désactivée — Robot conservé, achat/vente en attente de réactivation"));\n    }\n'''
s=once(s,old,new,'Robot accessibility lease grace')
old='''            acquireCommandWakeLock();\n            try {\n                PendingCommandStore.updateState(this, profileId, PendingCommandStore.DIALING);\n'''
new='''            acquireCommandWakeLock();\n            try {\n                PendingCommandStore.putLong(this, profileId, "accessibility_wait_started_at", 0L);\n                PendingCommandStore.updateState(this, profileId, PendingCommandStore.DIALING);\n'''
s=once(s,old,new,'Robot clear accessibility wait')
write(p,s)

# ---------------------------------------------------------------------------
# Control tower: carry transaction identity + evidence identity end-to-end.
# ---------------------------------------------------------------------------
p='app/src/main/assets/control-tower-v271.js'; s=read(p)
old="tx:String(c.transaction_id||''),at:commandTime(c),msg:String(c.result_message||'').slice(0,220)"
new="tx:String(c.operator_transaction_id||c.transaction_id||''),receipt:String(c.receipt_number||''),operator_at:String(c.operator_event_at||''),at:commandTime(c),msg:String(c.result_message||'').slice(0,220)"
s=once(s,old,new,'Control tower compact transaction identity')
old="balanceSave({balance:own.balance,available_balance:own.available_balance,reserved_amount:own.reserved_amount,balance_quality:own.balance_quality,evidence_kind:own.evidence_kind,observed_at:own.observed_at,operator_event_at:own.operator_event_at,ts:incoming});"
new="balanceSave({balance:own.balance,available_balance:own.available_balance,reserved_amount:own.reserved_amount,balance_quality:own.balance_quality,evidence_kind:own.evidence_kind,observed_at:own.observed_at,operator_event_at:own.operator_event_at,last_transaction_id:own.last_transaction_id||'',source_command_public_id:own.source_command_public_id||'',evidence_command_public_id:own.evidence_command_public_id||'',ts:incoming});"
s=once(s,old,new,'Control tower guard evidence identity')
old="balanceSave({balance:own.balance,available_balance:own.available_balance,reserved_amount:own.reserved_amount,balance_quality:own.balance_quality,evidence_kind:own.evidence_kind,observed_at:own.observed_at,operator_event_at:own.operator_event_at,ts:stamp(own.operator_event_at||own.observed_at)||Date.now()});"
new="balanceSave({balance:own.balance,available_balance:own.available_balance,reserved_amount:own.reserved_amount,balance_quality:own.balance_quality,evidence_kind:own.evidence_kind,observed_at:own.observed_at,operator_event_at:own.operator_event_at,last_transaction_id:own.last_transaction_id||'',source_command_public_id:own.source_command_public_id||'',evidence_command_public_id:own.evidence_command_public_id||'',ts:stamp(own.operator_event_at||own.observed_at)||Date.now()});"
s=once(s,old,new,'Control tower dashboard evidence identity')
write(p,s)

# ---------------------------------------------------------------------------
# Replace event balance engine with chronology + transaction identity dedupe.
# ---------------------------------------------------------------------------
p='app/src/main/assets/balance-engine-v280.js'
engine=r'''(function(){
'use strict';
function bridge(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}
function parse(raw,fallback){try{return JSON.parse(raw);}catch(e){return fallback;}}
function cfg(){try{return parse((bridge()&&bridge().getConfiguration&&bridge().getConfiguration())||'{}',{});}catch(e){return {};}}
function upper(v){return String(v||'').toUpperCase();}
function num(v){var n=Number(v);return isFinite(n)?n:0;}
function key(c,prefix){return prefix+String(c.profile_id||c.node_code||'default');}
function stamp(v){var n=Date.parse(v||'');return isNaN(n)?0:n;}
function money(v){return String(Math.round(num(v))).replace(/\B(?=(\d{3})+(?!\d))/g,' ');}
var configuration=cfg();
var PROOF_KEY=key(configuration,'bir_balance_guard_v271_');
var JOURNAL_KEY=key(configuration,'bir_transaction_journal_v271_');
var STATE_KEY=key(configuration,'bir_event_balance_v280_');
var FINANCE_FRESH_MS=60*60*1000;
var MAX_RECONCILED_AGE_MS=14*60*60*1000;

function localProof(){return parse(localStorage.getItem(PROOF_KEY)||'null',null);}
function nativeProof(){var b=bridge(),p=null,raw;if(!b||!b.getCertifiedBalance)return null;try{raw=b.getCertifiedBalance();p=parse(raw||'{}',{});}catch(e){return null;}if(!p||p.balance===null||typeof p.balance==='undefined')return null;return {balance:num(p.balance),available_balance:num(p.balance),reserved_amount:0,balance_quality:'EXACT',evidence_kind:'NATIVE_BLUE_PROOF',observed_at:p.observed_at||'',operator_event_at:p.operator_event_at||p.observed_at||'',last_transaction_id:p.transaction_id||p.receipt_number||'',receipt_number:p.receipt_number||'',source_command_public_id:'',evidence_command_public_id:'',ts:Number(p.chronology_ms||p.operator_event_at_ms||p.captured_at_ms||stamp(p.operator_event_at)||Date.now()),native:true};}
function saveProof(p){if(!p||p.balance===null||typeof p.balance==='undefined')return;var old=localProof(),next=Number(p.ts||stamp(p.operator_event_at||p.observed_at)||0);if(old&&Number(old.ts||0)>next)return;p.ts=next||Date.now();try{localStorage.setItem(PROOF_KEY,JSON.stringify(p));}catch(e){}}
function proof(){var l=localProof(),n=nativeProof();if(n&&(!l||Number(n.ts||0)>=Number(l.ts||0))){saveProof(n);return n;}return l;}
function journal(){return parse(localStorage.getItem(JOURNAL_KEY)||'[]',[]);}
function movement(entry){if(!entry||upper(entry.state)!=='SUCCEEDED')return 0;var op=upper(entry.op),target=upper(entry.target),node=upper(configuration.node_code),amount=num(entry.amount),base=num(entry.base||entry.amount),commission=num(entry.commission),total=(base||amount)+commission;if(!amount&&!base)return 0;if(op.indexOf('RETAIL')>=0||op==='RETAIL_SALE')return -amount;if(op.indexOf('DISTRIBUTION')>=0||op==='SUPPLY_CHILD'||op==='REQUEST_SUPPLY')return target===node?(base||amount):-(commission>0?total:amount);return 0;}
function normalizedId(v){return upper(String(v||'').replace(/[^A-Z0-9]/g,''));}
function sameEvidenceMovement(entry,p){if(!entry||!p)return false;var tx=normalizedId(entry.tx),receipt=normalizedId(entry.receipt),last=normalizedId(p.last_transaction_id),pr=normalizedId(p.receipt_number),id=normalizedId(entry.id),src=normalizedId(p.source_command_public_id),ev=normalizedId(p.evidence_command_public_id);if(tx&&last&&tx===last)return true;if(receipt&&last&&receipt===last)return true;if(tx&&pr&&tx===pr)return true;if(receipt&&pr&&receipt===pr)return true;if(id&&src&&id===src)return true;if(id&&ev&&id===ev)return true;return false;}
function movementTime(entry){return stamp(entry&&entry.operator_at)||stamp(entry&&entry.at);}
function isUncertain(entry,baseTs,p){if(!entry||sameEvidenceMovement(entry,p))return false;var ts=movementTime(entry);if(ts&&ts<=baseTs)return false;var state=upper(entry.state),op=upper(entry.op);if(/UNKNOWN|BLOCKED/.test(state)&&(/TRANSFER|SUPPLY|RETAIL|SALE/.test(op)))return true;if(entry.chronology_safe===false)return true;return false;}
function recompute(){var p=proof(),items=journal(),now=Date.now(),baseTs,i,e,ts,delta=0,movements=0,uncertain=false,state;if(!p||p.balance===null||typeof p.balance==='undefined'){state={quality:'UNCERTAIN',reason:'NO_CERTIFIED_PROOF',balance:null,reusable:false,updated_at:new Date().toISOString()};localStorage.setItem(STATE_KEY,JSON.stringify(state));render(state);return state;}baseTs=Number(p.ts||stamp(p.operator_event_at||p.observed_at)||0);for(i=0;i<items.length;i+=1){e=items[i];if(sameEvidenceMovement(e,p))continue;ts=movementTime(e);if(ts&&ts<=baseTs)continue;if(isUncertain(e,baseTs,p)){uncertain=true;continue;}var d=movement(e);if(d){delta+=d;movements+=1;}}var age=baseTs?now-baseTs:MAX_RECONCILED_AGE_MS+1;if(uncertain||age>MAX_RECONCILED_AGE_MS){state={quality:'UNCERTAIN',reason:uncertain?'UNRECONCILED_FINANCIAL_EVENT':'PROOF_TOO_OLD',balance:num(p.balance)+delta,base_balance:num(p.balance),delta:delta,movements:movements,reusable:false,proof_at:baseTs,last_transaction_id:p.last_transaction_id||'',updated_at:new Date().toISOString()};}else if(movements){state={quality:'RECALCULATED',reason:'CERTIFIED_PROOF_PLUS_CONFIRMED_MOVEMENTS',balance:num(p.balance)+delta,base_balance:num(p.balance),delta:delta,movements:movements,reusable:true,proof_at:baseTs,last_transaction_id:p.last_transaction_id||'',updated_at:new Date().toISOString()};}else{state={quality:age<=FINANCE_FRESH_MS?'CERTIFIED':'RECALCULATED',reason:age<=FINANCE_FRESH_MS?'RECENT_CERTIFIED_PROOF':'CERTIFIED_PROOF_NO_LATER_MOVEMENT',balance:num(p.balance),base_balance:num(p.balance),delta:0,movements:0,reusable:true,proof_at:baseTs,last_transaction_id:p.last_transaction_id||'',updated_at:new Date().toISOString()};}localStorage.setItem(STATE_KEY,JSON.stringify(state));render(state);return state;}
function render(s){var card=document.getElementById('birBalanceFreshness'),own=document.getElementById('ownBalance'),main=document.getElementById('birCamtelBalance'),label;if(!s)return;if(s.balance!==null){label=(s.reusable?'':'≈ ')+money(s.balance);if(own)own.textContent=label+' FCFA';if(main)main.textContent=label;}if(card){if(s.quality==='CERTIFIED')card.textContent='Preuve Blue certifiée • aucune interrogation USSD nécessaire';else if(s.quality==='RECALCULATED')card.textContent='Solde recalculé • preuve certifiée + '+String(s.movements||0)+' mouvement(s) confirmé(s)';else card.textContent='≈ Estimation B.I.R. à rapprocher • ne pas la confondre avec un solde Blue certifié';}}
function get(){return parse(localStorage.getItem(STATE_KEY)||'null',null)||recompute();}
function shouldRecertify(){var s=get();return !s||s.reusable!==true||s.quality==='UNCERTAIN';}
window.BIREventBalanceV280={recompute:recompute,get:get,shouldRecertify:shouldRecertify,sameEvidenceMovement:sameEvidenceMovement};
window.BlueMagicNative=window.BlueMagicNative||{};
var status=window.BlueMagicNative.onCommandStatus;window.BlueMagicNative.onCommandStatus=function(data){if(typeof status==='function')try{status(data);}catch(e){};setTimeout(recompute,50);};
var created=window.BlueMagicNative.onCommandCreated;window.BlueMagicNative.onCommandCreated=function(data){if(typeof created==='function')try{created(data);}catch(e){};setTimeout(recompute,50);};
var dashboard=window.BlueMagicNative.onDashboard;window.BlueMagicNative.onDashboard=function(data){if(typeof dashboard==='function')try{dashboard(data);}catch(e){};setTimeout(recompute,50);};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){setTimeout(recompute,80);});else setTimeout(recompute,80);
}());
'''
write(p,engine)

# ---------------------------------------------------------------------------
# app.js: merge server queue into same local register and request snapshots.
# ---------------------------------------------------------------------------
p='app/src/main/assets/app.js'; s=read(p)
old="onDashboard:function(data){if(data&&data.error){showToast((data.code||'DASHBOARD_ERROR')+' — '+(data.message||'Rapport indisponible.'));scheduleDashboardPoll();return;}dashboard=data||{};dashboardLoadedAt=new Date().getTime();renderDashboard();scheduleDashboardPoll();}"
new="onDashboard:function(data){if(data&&data.error){showToast((data.code||'DASHBOARD_ERROR')+' — '+(data.message||'Rapport indisponible.'));scheduleDashboardPoll();return;}dashboard=data||{};dashboardLoadedAt=new Date().getTime();renderDashboard();scheduleDashboardPoll();},onQueueSnapshot:function(data){mergeQueueSnapshot(data||{});}"
s=once(s,old,new,'app onQueueSnapshot')
old="render();refresh(true);scheduleCommandPoll(5000);"
new="render();refresh(true);refreshQueueSnapshot();scheduleCommandPoll(5000);"
s=once(s,old,new,'app initial queue refresh')
insert="""
    function refreshQueueSnapshot(){if(!bridge()||!window.AndroidBridge.refreshQueueSnapshot)return;try{window.AndroidBridge.refreshQueueSnapshot();}catch(ignored){}}
    function mergeQueueSnapshot(data){var list=data&&data.commands||[],i;for(i=0;i<list.length;i+=1){if(list[i]&&list[i].public_id)upsert(list[i]);}render();}
"""
anchor="    function upsert(command){"
if anchor not in s: raise SystemExit('app queue function anchor missing')
s=s.replace(anchor,insert+anchor,1)
# Refresh queue after command creation and terminal propagation.
s=s.replace("scheduleCommandPoll(1200);if(command.robot_ready===false)","refreshQueueSnapshot();scheduleCommandPoll(1200);if(command.robot_ready===false)",1)
s=s.replace("requestDashboard(true);}scheduleCommandPoll(5000);", "requestDashboard(true);refreshQueueSnapshot();}scheduleCommandPoll(5000);",1)
write(p,s)

# ---------------------------------------------------------------------------
# Field recovery: force unified queue refresh during self-healing pulses.
# ---------------------------------------------------------------------------
p='app/src/main/assets/field-recovery-v291.js'; s=read(p)
old="try{if(b.kickSynchronization)b.kickSynchronization();else if(b.synchronizeNow)b.synchronizeNow();}catch(e){}window.setTimeout(function(){try{if(b.loadDashboard)b.loadDashboard();}catch(e){}},700);"
new="try{if(b.kickSynchronization)b.kickSynchronization();else if(b.synchronizeNow)b.synchronizeNow();if(b.refreshQueueSnapshot)b.refreshQueueSnapshot();}catch(e){}window.setTimeout(function(){try{if(b.loadDashboard)b.loadDashboard();}catch(e){}},700);"
s=once(s,old,new,'field recovery queue refresh')
write(p,s)

print('B.I.R. v2.9.3 Android coherence patch applied')
