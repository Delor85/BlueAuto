from pathlib import Path
import re

def read(path):
    return Path(path).read_text()

def write(path, text):
    Path(path).write_text(text)

def one(text, old, new, label):
    if old not in text:
        raise SystemExit(f'missing patch anchor: {label}')
    return text.replace(old, new, 1)

# Android Robot: never fight the keyguard; keep polling persistent.
p='app/src/main/java/com/profitloop/blueauto/RobotService.java'
s=read(p)
s=s.replace('private static final long WATCHDOG_INTERVAL_MS = 15 * 60_000L;',
            'private static final long WATCHDOG_INTERVAL_MS = 60_000L;')
s=s.replace('    private static final long SYSTEM_USSD_SCREEN_WAKE_MS = 45_000L;\n','')
s=s.replace('    private PowerManager.WakeLock commandScreenWakeLock;\n','')
s=s.replace('    private boolean insecureKeyguardDismissed;\n','')
s=one(s,
'''                        if (UssdCommandFactory.requiresPin(command)
                                && DeviceLockState.isSecurelyLocked(this)) {
                            releaseLockedLease(profileId, command, api);
                            nextDelay = AppConfig.LOCKED_POLL_MS;
                            return;
                        }''',
'''                        if (DeviceLockState.blocksUssd(this)) {
                            releaseLockedLease(profileId, command, api);
                            nextDelay = AppConfig.LOCKED_POLL_MS;
                            return;
                        }''','lease lock gate')
old='''            acquireCommandWakeLock();
            try {
                boolean needsWakeSettle = !DeviceLockState.isScreenInteractive(this)
                        || DeviceLockState.isInsecurelyLocked(this);
                acquireCommandScreenWakeLock();
                if (!prepareSystemUssdSurface(needsWakeSettle)) {
                    releaseUnexecutedLease(profileId, command, api,
                            "Le verrou Android est encore visible; aucune composition n’a été lancée.");
                    updateNotification(robotSummary(
                            "Commande différée — retirez le verrou ou réveillez l’écran"));
                    return;
                }
                PendingCommandStore.updateState(this, profileId, PendingCommandStore.DIALING);
                api.sendEvent(command, "DIALING", "Composition USSD déclenchée sur le Robot.", "");
                updateNotification("Commande " + AppConfig.nodeCode(this, profileId) + " en cours");

                String next = requiresPin ? PendingCommandStore.AWAITING_PIN
                        : PendingCommandStore.AWAITING_RESULT;
                PendingCommandStore.updateState(this, profileId, next);
                api.sendEvent(command, next, requiresPin
                        ? "En attente de la fenêtre de confirmation PIN."
                        : "En attente du résultat opérateur.", "");
                SimCallManager.placeUssdCall(this, ussd, profileId);
                if (requiresPin) BlueAccessibilityService.kick(this);
            } catch (SecurityException permissionError) {'''
new='''            if (DeviceLockState.blocksUssd(this)) {
                releaseLockedLease(profileId, command, api);
                return;
            }
            acquireCommandWakeLock();
            try {
                PendingCommandStore.updateState(this, profileId, PendingCommandStore.DIALING);
                api.sendEvent(command, "DIALING", "Composition USSD déclenchée sur le Robot déverrouillé.", "");
                updateNotification("Commande " + AppConfig.nodeCode(this, profileId) + " en cours");

                String next = requiresPin ? PendingCommandStore.AWAITING_PIN
                        : PendingCommandStore.AWAITING_RESULT;
                PendingCommandStore.updateState(this, profileId, next);
                api.sendEvent(command, next, requiresPin
                        ? "En attente de la fenêtre de confirmation PIN."
                        : "Commande directe avec PIN local déjà composé; attente du résultat opérateur.", "");
                SimCallManager.placeUssdCall(this, ussd, profileId);
                if (requiresPin) BlueAccessibilityService.kick(this);
            } catch (SecurityException permissionError) {'''
s=one(s,old,new,'execute lock surface')
s=re.sub(r'\n    private boolean prepareSystemUssdSurface\(boolean needsWakeSettle\) \{.*?\n    \}\n\n    private void reportProgress',
         '\n\n    private void reportProgress',s,flags=re.S)
s=re.sub(r'\n    @SuppressWarnings\("deprecation"\)\n    private void acquireCommandScreenWakeLock\(\) \{.*?\n    \}\n\n    private void releaseCommandWakeLock',
         '\n\n    private void releaseCommandWakeLock',s,flags=re.S)
s=one(s,
'''    private void releaseCommandWakeLock() {
        if (commandWakeLock != null && commandWakeLock.isHeld()) commandWakeLock.release();
        commandWakeLock = null;
        releaseCommandScreenWakeLock();
        if (insecureKeyguardDismissed) DeviceLockState.restoreInsecureKeyguard();
        insecureKeyguardDismissed = false;
    }

    private void releaseCommandScreenWakeLock() {
        if (commandScreenWakeLock != null && commandScreenWakeLock.isHeld()) {
            commandScreenWakeLock.release();
        }
        commandScreenWakeLock = null;
    }''',
'''    private void releaseCommandWakeLock() {
        if (commandWakeLock != null && commandWakeLock.isHeld()) commandWakeLock.release();
        commandWakeLock = null;
    }''','release wake lock')
s=s.replace('Téléphone verrouillé par un mot de passe ou schéma; exécution différée.',
            'Écran verrouillé. Le titulaire doit déverrouiller normalement le téléphone; aucune tentative de déverrouillage automatique n’est effectuée.')
s=s.replace('Commande différée — déverrouillez le téléphone',
            'Écran verrouillé — déverrouillez le téléphone puis Blue Magic reprendra la file')
for banned in ['dismissInsecureKeyguard','InsecureKeyguardDismissActivity','SCREEN_BRIGHT_WAKE_LOCK','ACQUIRE_CAUSES_WAKEUP','commandScreenWakeLock']:
    if banned in s:
        raise SystemExit('banned keyguard/wake mechanism remains: '+banned)
write(p,s)

p='app/src/main/java/com/profitloop/blueauto/AppConfig.java'
s=read(p).replace('static final long HEARTBEAT_MS = 300_000L;','static final long HEARTBEAT_MS = 60_000L;')
write(p,s)

# Real selective dashboard refresh.
p='app/src/main/java/com/profitloop/blueauto/MainActivity.java'
s=read(p)
anchor='''        @JavascriptInterface
        public void loadDashboard() {
            new Thread(() -> {
                try {
                    callback("onDashboard", new ApiClient(MainActivity.this).dashboard());
                } catch (Exception error) {
                    callbackError("onDashboard", error);
                }
            }).start();
        }
'''
addition=anchor+'''
        @JavascriptInterface
        public void refreshDashboardLive() {
            new Thread(() -> {
                try {
                    JSONObject audit = new ApiClient(MainActivity.this).networkBalanceAudit();
                    audit.put("_action", "network_balance_audit");
                    callback("onPlatformAction", audit);
                    callback("onDashboard", new ApiClient(MainActivity.this).dashboard());
                    if (AppConfig.anyRobotEnabled(MainActivity.this)) {
                        RobotService.startEnabled(MainActivity.this);
                    }
                } catch (Exception error) {
                    callbackError("onPlatformAction", error);
                }
            }).start();
        }
'''
s=one(s,anchor,addition,'refreshDashboardLive')
write(p,s)

# API bridge whitelist/version.
p='app/src/main/java/com/profitloop/blueauto/ApiClient.java'
s=read(p)
s=s.replace('mercenary_save|mercenary_list|mercenary_sale)',
            'mercenary_save|mercenary_list|mercenary_sale|commission_policy|commission_set_default|commission_set_child)')
s=s.replace('payload.put("app_version", "2.6.7");','payload.put("app_version", "2.6.8");')
write(p,s)

# Worker commission model and quote integrity.
p='cloudflare/src/index.js'
s=read(p)
s=s.replace("const API_VERSION = '2.6.7-cloudflare';","const API_VERSION = '2.6.8-cloudflare';")
s=one(s,"        case 'platform_snapshot': return await platformSnapshot(env, auth, headers);",
      "        case 'platform_snapshot': return await platformSnapshot(env, auth, headers);\n        case 'commission_policy': return await commissionPolicy(env, auth, headers);\n        case 'commission_set_default': return await commissionSetDefault(env, auth, input, headers);\n        case 'commission_set_child': return await commissionSetChild(env, auth, input, headers);",'commission routes')

old='''    return {
      executor: parent.node_code, executorPhone: parent.phone_number,
      targetNode: requester, targetPhone: auth.phone_number,
      amount: value, operation: 'DISTRIBUTION_TRANSFER',
      ussd: CAMTEL_USSD.distributionTransfer(auth.phone_number, value), requiresPin: 1
    };'''
new='''    const policy = await commissionRateFor(env, parent.node_code, requester);
    const quote = commissionQuote(value, policy.rate_bps);
    return {
      executor: parent.node_code, executorPhone: parent.phone_number,
      targetNode: requester, targetPhone: auth.phone_number,
      amount: quote.total_amount, requestedBaseAmount: value,
      commissionRateBps: policy.rate_bps, commissionAmount: quote.commission_amount,
      commissionSource: policy.source, operation: 'DISTRIBUTION_TRANSFER',
      ussd: CAMTEL_USSD.distributionTransfer(auth.phone_number, quote.total_amount), requiresPin: 1
    };'''
s=one(s,old,new,'request supply commission')
old='''    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: child.node_code, targetPhone: child.phone_number, amount: value,
      operation: 'DISTRIBUTION_TRANSFER', ussd: CAMTEL_USSD.distributionTransfer(child.phone_number, value), requiresPin: 1
    };'''
new='''    const policy = await commissionRateFor(env, requester, child.node_code);
    const quote = commissionQuote(value, policy.rate_bps);
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: child.node_code, targetPhone: child.phone_number, amount: quote.total_amount,
      requestedBaseAmount: value, commissionRateBps: policy.rate_bps,
      commissionAmount: quote.commission_amount, commissionSource: policy.source,
      operation: 'DISTRIBUTION_TRANSFER',
      ussd: CAMTEL_USSD.distributionTransfer(child.phone_number, quote.total_amount), requiresPin: 1
    };'''
s=one(s,old,new,'supply child commission')

s=one(s,"    amount: values.amount,\n    operation: values.commandKind || values.operation,",
      "    amount: values.amount,\n    requested_base_amount: values.requestedBaseAmount || values.amount,\n    commission_rate_bps: Number(values.commissionRateBps || 0),\n    commission_amount: Number(values.commissionAmount || 0),\n    commission_source: values.commissionSource || '',\n    operation: values.commandKind || values.operation,",'preview commission fields')

s=s.replace("+ 'requires_pin, capacity_check_id) '",
            "+ 'requires_pin, capacity_check_id, requested_base_amount, commission_rate_bps, commission_amount) '")
s=s.replace("+ 'SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? '",
            "+ 'SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? '")
s=s.replace('values.amount, values.ussd, values.requiresPin, values.capacityCheckId,\n      values.capacityCheckId, auth.node_code, values.executor, values.amount, values.amount',
            'values.amount, values.ussd, values.requiresPin, values.capacityCheckId,\n      values.requestedBaseAmount || values.amount, Number(values.commissionRateBps || 0), Number(values.commissionAmount || 0),\n      values.capacityCheckId, auth.node_code, values.executor, values.amount, values.amount')
s=s.replace("+ 'requires_pin, capacity_check_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'",
            "+ 'requires_pin, capacity_check_id, requested_base_amount, commission_rate_bps, commission_amount) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'" )
s=s.replace('values.amount, values.ussd, values.requiresPin, null\n    );',
            'values.amount, values.ussd, values.requiresPin, null,\n      values.requestedBaseAmount || values.amount, Number(values.commissionRateBps || 0), Number(values.commissionAmount || 0)\n    );')
s=one(s,"      operation: values.commandKind || values.operation, amount: values.amount,\n      created_at: createdAt, updated_at: createdAt,",
      "      operation: values.commandKind || values.operation, amount: values.amount,\n      requested_base_amount: values.requestedBaseAmount || values.amount,\n      commission_rate_bps: Number(values.commissionRateBps || 0),\n      commission_amount: Number(values.commissionAmount || 0),\n      created_at: createdAt, updated_at: createdAt,",'created command commission')

s=one(s,"    + 'requested_amount, available_balance, balance_command_public_id, balance_reused, balance_observed_at, '\n    + 'state, result_message, expires_at) '",
      "    + 'requested_amount, base_amount, commission_rate_bps, commission_amount, available_balance, balance_command_public_id, balance_reused, balance_observed_at, '\n    + 'state, result_message, expires_at) '",'preflight columns reusable')
s=one(s,"    + 'SELECT ?, ?, ?, ?, request.amount, snapshot.available, '",
      "    + 'SELECT ?, ?, ?, ?, request.amount, ?, ?, ?, snapshot.available, '",'preflight select reusable')
s=one(s,'  ).bind(values.amount, values.executor, checkId, clientId, auth.node_code, values.executor).first();',
      '  ).bind(values.amount, values.executor, checkId, clientId, auth.node_code, values.executor,\n    values.requestedBaseAmount || values.amount, Number(values.commissionRateBps || 0), Number(values.commissionAmount || 0)).first();','preflight bind reusable')
s=one(s,"    + 'supplier_node_code, requested_amount, balance_command_public_id, state, result_message, expires_at) '\n    + \"VALUES(?, ?, ?, ?, ?, ?, 'WAITING', ?, \"",
      "    + 'supplier_node_code, requested_amount, base_amount, commission_rate_bps, commission_amount, balance_command_public_id, state, result_message, expires_at) '\n    + \"VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 'WAITING', ?, \"",'preflight waiting columns')
s=one(s,"  ).bind(checkId, clientId, auth.node_code, values.executor, values.amount,\n    balanceCommand.public_id, 'Lecture mutualisée du solde du supérieur en cours; priorité conservée par ordre d arrivée.').run();",
      "  ).bind(checkId, clientId, auth.node_code, values.executor, values.amount,\n    values.requestedBaseAmount || values.amount, Number(values.commissionRateBps || 0), Number(values.commissionAmount || 0),\n    balanceCommand.public_id, 'Lecture mutualisée du solde du supérieur en cours; priorité conservée par ordre d arrivée.').run();",'preflight waiting bind')
s=one(s,"    capacity_check_id: checkId, state: 'WAITING', requested_amount: values.amount,",
      "    capacity_check_id: checkId, state: 'WAITING', requested_amount: values.amount,\n    base_amount: values.requestedBaseAmount || values.amount, commission_rate_bps: Number(values.commissionRateBps || 0),\n    commission_amount: Number(values.commissionAmount || 0),",'capacity waiting response')
s=one(s,"    requested_amount: Number(row.requested_amount),\n    available_balance:",
      "    requested_amount: Number(row.requested_amount),\n    base_amount: Number(row.base_amount || row.requested_amount),\n    commission_rate_bps: Number(row.commission_rate_bps || 0),\n    commission_amount: Number(row.commission_amount || 0),\n    maximum_base_amount: maxBaseForTotal(Number(row.available_balance || 0), Number(row.commission_rate_bps || 0)),\n    available_balance:",'capacity view commission')
s=one(s,"    values.operation || '', values.commandKind || '', values.commandArgument || '', values.ussd || '',\n    values.requiresPin ? '1' : '0',",
      "    values.operation || '', values.commandKind || '', values.commandArgument || '', values.ussd || '',\n    values.requestedBaseAmount || '', values.commissionRateBps || '', values.commissionAmount || '',\n    values.requiresPin ? '1' : '0',",'preview fingerprint commission')

marker='async function mercenarySave(env, auth, input, headers) {'
functions='''async function commissionRateFor(env, parentNodeCode, childNodeCode) {
  const override = await env.DB.prepare(
    'SELECT rate_bps FROM commission_overrides WHERE parent_node_code=? AND child_node_code=?'
  ).bind(parentNodeCode, childNodeCode).first();
  if (override) return {rate_bps: Number(override.rate_bps), source: 'CHILD_OVERRIDE'};
  const parent = await env.DB.prepare('SELECT default_commission_bps FROM nodes WHERE node_code=?')
    .bind(parentNodeCode).first();
  return {rate_bps: Number(parent?.default_commission_bps || 0), source: 'PARENT_DEFAULT'};
}

function commissionQuote(baseAmount, rateBps) {
  const base = Number(baseAmount || 0);
  const rate = Number(rateBps || 0);
  const commission = Math.floor(base * rate / 10000);
  return {base_amount: base, rate_bps: rate, commission_amount: commission,
    total_amount: base + commission};
}

function maxBaseForTotal(totalAmount, rateBps) {
  const total = Math.max(0, Math.floor(Number(totalAmount || 0)));
  const rate = Math.max(0, Math.floor(Number(rateBps || 0)));
  let base = Math.floor(total * 10000 / (10000 + rate));
  while (base > 0 && commissionQuote(base, rate).total_amount > total) base -= 1;
  while (commissionQuote(base + 1, rate).total_amount <= total) base += 1;
  return base;
}

async function commissionPolicy(env, auth, headers) {
  if (!['DAE','DSM'].includes(auth.role)) {
    return success({node_code: auth.node_code, role: auth.role, default_rate_bps: 0, children: []}, 200, headers);
  }
  const childRole = auth.role === 'DAE' ? 'DSM' : 'POS';
  const parent = await env.DB.prepare('SELECT default_commission_bps FROM nodes WHERE node_code=?')
    .bind(auth.node_code).first();
  const children = await env.DB.prepare(
    'SELECT n.node_code,n.phone_number,o.rate_bps AS override_rate_bps FROM nodes n '
    + 'LEFT JOIN commission_overrides o ON o.parent_node_code=? AND o.child_node_code=n.node_code '
    + 'WHERE n.parent_node_code=? AND n.role=? AND n.active=1 ORDER BY n.node_code'
  ).bind(auth.node_code, auth.node_code, childRole).all();
  return success({node_code:auth.node_code, role:auth.role,
    default_rate_bps:Number(parent?.default_commission_bps || 0),
    children:(children.results||[]).map(row=>({...row,
      effective_rate_bps: row.override_rate_bps == null ? Number(parent?.default_commission_bps || 0) : Number(row.override_rate_bps),
      source: row.override_rate_bps == null ? 'PARENT_DEFAULT' : 'CHILD_OVERRIDE'}))},200,headers);
}

async function commissionSetDefault(env, auth, input, headers) {
  if (!['DAE','DSM'].includes(auth.role)) throw new ApiError('REQUEST_NOT_ALLOWED','Seul un DAE ou DSM définit un taux enfant.',403);
  const rate = Number(input.rate_bps);
  if (!Number.isInteger(rate) || rate < 0 || rate > 5000) throw new ApiError('INVALID_COMMISSION_RATE','Taux invalide.',422);
  await env.DB.prepare('UPDATE nodes SET default_commission_bps=? WHERE node_code=?')
    .bind(rate,auth.node_code).run();
  return commissionPolicy(env,auth,headers);
}

async function commissionSetChild(env, auth, input, headers) {
  if (!['DAE','DSM'].includes(auth.role)) throw new ApiError('REQUEST_NOT_ALLOWED','Seul un DAE ou DSM personnalise un taux enfant.',403);
  const childRole=auth.role==='DAE'?'DSM':'POS';
  const child=await resolveDirectChild(env,auth.node_code,input.child_node_code,childRole);
  if(!child) throw new ApiError('CHILD_NOT_FOUND','Enfant direct introuvable.',422);
  if (input.use_default === true) {
    await env.DB.prepare('DELETE FROM commission_overrides WHERE parent_node_code=? AND child_node_code=?')
      .bind(auth.node_code,child.node_code).run();
  } else {
    const rate=Number(input.rate_bps);
    if(!Number.isInteger(rate)||rate<0||rate>5000) throw new ApiError('INVALID_COMMISSION_RATE','Taux invalide.',422);
    await env.DB.prepare(
      "INSERT INTO commission_overrides(parent_node_code,child_node_code,rate_bps,updated_by_node_code) VALUES(?,?,?,?) "
      + "ON CONFLICT(parent_node_code,child_node_code) DO UPDATE SET rate_bps=excluded.rate_bps,updated_by_node_code=excluded.updated_by_node_code,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
    ).bind(auth.node_code,child.node_code,rate,auth.node_code).run();
  }
  return commissionPolicy(env,auth,headers);
}

'''
if marker not in s:
    raise SystemExit('missing commission insertion marker')
s=s.replace(marker,functions+marker,1)

s=s.replace("'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code, '",
            "'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code, n.default_commission_bps, '",1)
old='''      return {...row, balance, reserved_amount: reserved,
        available_balance: balance == null ? null : Math.max(0, balance - reserved),'''
new='''      const defaultRate = Number(row.default_commission_bps || 0);
      const baseEquivalent = balance == null ? null : maxBaseForTotal(balance, defaultRate);
      return {...row, balance, default_commission_bps: defaultRate, reserved_amount: reserved,
        commission_base_balance: baseEquivalent,
        commission_component_balance: balance == null ? null : balance - baseEquivalent,
        available_balance: balance == null ? null : Math.max(0, balance - reserved),'''
s=one(s,old,new,'dashboard commission decomposition')
write(p,s)

# Embedded UI: no aggregate balance; real refresh; quote commission.
p='app/src/main/assets/app.js'
s=read(p)
s=s.replace("else if(action==='refresh-dashboard'){window.AndroidBridge.loadDashboard();showToast('Actualisation du réseau lancée.');}",
            "else if(action==='refresh-dashboard'){if(window.AndroidBridge.refreshDashboardLive){window.AndroidBridge.refreshDashboardLive();showToast('Actualisation intelligente : preuves récentes réutilisées, USSD seulement si nécessaire.');}else{window.AndroidBridge.loadDashboard();}}")
old="""        var title=preview.operation==='RETAIL_TRANSFER'?'VENTE À UN CLIENT':'TRANSFERT DE CRÉDIT';
        var supplier=(preview.executor_node_code||'FOURNISSEUR')+' — '+(preview.executor_phone||'numéro absent');
        var beneficiary=(preview.target_node_code||'CLIENT')+' — '+(preview.target_phone||'numéro absent');
        return window.confirm('CONFIRMATION 1 SUR 2\\n\\n'+title+'\\n\\nFOURNISSEUR : '+supplier+'\\nBÉNÉFICIAIRE : '+beneficiary+'\\nMONTANT : '+formatMoney(preview.amount)+' FCFA\\n\\nConfirmez uniquement si les deux numéros et le montant sont exacts. Après confirmation, le Robot composera la commande. Blue Magic contrôlera ensuite les mêmes données dans le pop-up Camtel avant d’insérer le PIN.\\n\\nCONFIRMER CETTE TRANSACTION ?');"""
new="""        var title=preview.operation==='RETAIL_TRANSFER'?'VENTE À UN CLIENT':'TRANSFERT DE CRÉDIT';
        var supplier=(preview.executor_node_code||'FOURNISSEUR')+' — '+(preview.executor_phone||'numéro absent');
        var beneficiary=(preview.target_node_code||'CLIENT')+' — '+(preview.target_phone||'numéro absent');
        var base=Number(preview.requested_base_amount||preview.amount||0), commission=Number(preview.commission_amount||0), rate=Number(preview.commission_rate_bps||0)/100;
        var quote=preview.operation==='DISTRIBUTION_TRANSFER'
            ? ('\\nMONTANT COMMANDÉ : '+formatMoney(base)+' FCFA\\nCOMMISSION ('+String(rate).replace('.',',')+' %) : '+formatMoney(commission)+' FCFA\\nTOTAL À RECEVOIR : '+formatMoney(preview.amount)+' FCFA')
            : ('\\nMONTANT : '+formatMoney(preview.amount)+' FCFA');
        return window.confirm('CONFIRMATION 1 SUR 2\\n\\n'+title+'\\n\\nFOURNISSEUR : '+supplier+'\\nBÉNÉFICIAIRE : '+beneficiary+quote+'\\n\\nSi le taux de commission ne vous convient pas, annulez maintenant et contactez votre supérieur. Après confirmation, le Robot composera le montant total certifié. Blue Magic contrôlera ensuite les mêmes données dans le pop-up Camtel avant d’insérer le PIN.\\n\\nCONFIRMER CETTE TRANSACTION ?');"""
s=one(s,old,new,'confirmation quote')
s=s.replace("var nodes=dashboard&&dashboard.nodes||[],html='',fleet='',i,n,own=null,total=0,known=0;",
            "var nodes=dashboard&&dashboard.nodes||[],html='',fleet='',i,n,own=null,known=0;")
s=s.replace("            if(n.balance!==null&&typeof n.balance!=='undefined'){total+=Number(n.balance)||0;known+=1;}",
            "            if(n.balance!==null&&typeof n.balance!=='undefined'){known+=1;}")
old="""            var balanceText=n.balance===null||typeof n.balance==='undefined'?'Non lu':formatMoney(n.balance)+' FCFA';
            var availableText=n.available_balance===null||typeof n.available_balance==='undefined'?'':(' • dispo '+formatMoney(n.available_balance)+' FCFA');
            var evidenceText=n.balance===null||typeof n.balance==='undefined'?'':(' • '+(n.balance_quality==='EXACT'?'confirmé':'estimé')+' / '+(n.evidence_kind||n.balance_source||'source inconnue'));
            html+='<article class="network-item"><div><strong>'+escapeHtml(n.node_code||'—')+'</strong><span>'+escapeHtml((n.role||'—')+' • '+(n.device_kind||'—')+evidenceText)+'</span></div><div class="network-balance">'+escapeHtml(balanceText+availableText)+'</div></article>';"""
new="""            var balanceText=n.balance===null||typeof n.balance==='undefined'?'Non lu':formatMoney(n.balance)+' FCFA';
            var reserved=Number(n.reserved_amount||0), available=n.available_balance===null||typeof n.available_balance==='undefined'?null:Number(n.available_balance);
            var evidenceText=n.balance===null||typeof n.balance==='undefined'?'':(' • '+(n.balance_quality==='EXACT'?'confirmé':'estimé')+' / '+(n.evidence_kind||n.balance_source||'source inconnue'));
            var split='';
            if((n.role==='DAE'||n.role==='DSM')&&n.balance!==null&&typeof n.balance!=='undefined'){split='<br><small>Stock hors commission : '+escapeHtml(formatMoney(n.commission_base_balance||0))+' • part taux par défaut : '+escapeHtml(formatMoney(n.commission_component_balance||0))+' • taux '+escapeHtml(String(Number(n.default_commission_bps||0)/100).replace('.',','))+' %</small>';}
            html+='<article class="network-item"><div><strong>'+escapeHtml(n.node_code||'—')+'</strong><span>'+escapeHtml((n.role||'—')+' • '+(n.device_kind||'—')+evidenceText)+'</span></div><div class="network-balance"><b>Solde Camtel : '+escapeHtml(balanceText)+'</b><br><small>Réservé : '+escapeHtml(formatMoney(reserved))+' FCFA • Disponible : '+escapeHtml(available===null?'—':formatMoney(available)+' FCFA')+'</small>'+split+'</div></article>';"""
s=one(s,old,new,'dashboard rows')
s=s.replace("        if(nodes.length){byId('reportActivityTitle').textContent='Solde cumulé connu : '+formatMoney(total)+' FCFA';}\n",'')
write(p,s)

# Five dynamic tabs: commission controls in Flotte.
p='app/src/main/assets/platform-v267.js'
s=read(p).replace('Cette fonction exige l’APK Blue Magic v2.6.7.','Cette fonction exige l’APK Blue Magic v2.6.8.')
fleet_anchor='''    <button id="shadow-save">Activer la liaison</button><hr>
    <h4>Créances</h4>'''
fleet_new='''    <button id="shadow-save">Activer la liaison</button><hr>
    <h4>💹 Commissions d’approvisionnement</h4><p class="small">DAE : taux par défaut pour les DSM. DSM : taux par défaut pour les PoS. Une exception enfant remplace seulement ce taux.</p>
    <input id="commission-default" type="number" step="0.01" placeholder="Taux par défaut %"><button id="commission-default-save">Enregistrer le taux par défaut</button>
    <input id="commission-child" placeholder="Enfant direct"><input id="commission-child-rate" type="number" step="0.01" placeholder="Taux personnalisé %">
    <button id="commission-child-save">Personnaliser</button><button id="commission-child-default">Revenir au défaut</button><button id="commission-refresh">Afficher les taux</button><div id="commission-list" class="small"></div><hr>
    <h4>Créances</h4>'''
s=one(s,fleet_anchor,fleet_new,'commission UI')
bind_anchor="  bind('shadow-save', () => request('shadow_enroll', {node_code:$('shadow-id').value, phone_number:$('shadow-phone').value, display_name:$('shadow-name').value, zone:$('shadow-zone').value}));"
bind_new=bind_anchor+"\n  bind('commission-refresh', () => request('commission_policy'));\n  bind('commission-default-save', () => request('commission_set_default', {rate_bps:Math.round(Number($('commission-default').value||0)*100)}));\n  bind('commission-child-save', () => request('commission_set_child', {child_node_code:$('commission-child').value,rate_bps:Math.round(Number($('commission-child-rate').value||0)*100)}));\n  bind('commission-child-default', () => request('commission_set_child', {child_node_code:$('commission-child').value,use_default:true}));"
s=one(s,bind_anchor,bind_new,'commission binds')
action_anchor="    } else if (action === 'debt_save' || action === 'debt_list') {"
action_new="""    } else if (action === 'commission_policy' || action === 'commission_set_default' || action === 'commission_set_child') {
      if($('commission-default')) $('commission-default').value=String(Number(data.default_rate_bps||0)/100);
      if($('commission-list')) $('commission-list').innerHTML=(data.children||[]).map(c=>`${esc(c.node_code)} : ${String(Number(c.effective_rate_bps||0)/100).replace('.',',')} % · ${esc(c.source==='CHILD_OVERRIDE'?'personnalisé':'défaut')}`).join('<br>') || 'Aucun enfant direct.';
    } else if (action === 'debt_save' || action === 'debt_list') {"""
s=one(s,action_anchor,action_new,'commission action display')
write(p,s)

Path('app/src/test/v268-field-contract.mjs').write_text(r'''import fs from 'node:fs';
const robot=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/RobotService.java','utf8');
const lock=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/DeviceLockState.java','utf8');
const policy=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/CommandExecutionPolicy.java','utf8');
const ui=fs.readFileSync('app/src/main/assets/app.js','utf8');
const worker=fs.readFileSync('cloudflare/src/index.js','utf8');
for(const banned of ['disableKeyguard','SCREEN_BRIGHT_WAKE_LOCK','ACQUIRE_CAUSES_WAKEUP','dismissInsecureKeyguard']){
  if(robot.includes(banned)||lock.includes(banned)) throw new Error('forbidden keyguard mechanism: '+banned);
}
if(!robot.includes('DeviceLockState.blocksUssd(this)')) throw new Error('locked-screen USSD gate missing');
if(!policy.includes('needsAccessibility(operation)')||!policy.includes('return isFinancial(operation)')) throw new Error('direct PIN commands still tied to Accessibility');
if(ui.includes('Solde cumulé connu')) throw new Error('aggregate balance label still exposed');
if(!ui.includes('Réservé : ')||!ui.includes('Solde Camtel : ')) throw new Error('balance/reservation separation missing');
if(!worker.includes('commissionRateFor')||!worker.includes('commission_amount')||!worker.includes('requested_base_amount')) throw new Error('commission quote persistence missing');
console.log('v2.6.8 field contract: lock safety, direct PIN, balances and commissions OK');
''')
