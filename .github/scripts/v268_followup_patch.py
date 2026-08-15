from pathlib import Path


def read(path): return Path(path).read_text()
def write(path, text): Path(path).write_text(text)
def one(text, old, new, label):
    if old not in text:
        raise SystemExit(f'missing patch anchor: {label}')
    return text.replace(old, new, 1)

# 1) Robot: Accessibility loss must never consume/fail a financial command.
p='app/src/main/java/com/profitloop/blueauto/RobotService.java'
s=read(p)
old='''            if (!capability.ready) {
                finishCommand(profileId, false, capability.code, capability.message, "");
                return;
            }'''
new='''            if (!capability.ready) {
                if ("ACCESSIBILITY_DISABLED".equals(capability.code)) {
                    releaseUnexecutedLease(profileId, command, api,
                            "Accessibilité Blue Magic désactivée; transaction financière conservée en file.");
                    updateNotification(robotSummary("Robot actif — Accessibilité à réactiver; achats/ventes restent en file"));
                    return;
                }
                finishCommand(profileId, false, capability.code, capability.message, "");
                return;
            }'''
s=one(s,old,new,'accessibility queue behavior')
write(p,s)

# 2) MainActivity: remove stale simple-lock copy, expose PIN maintenance and battery settings.
p='app/src/main/java/com/profitloop/blueauto/MainActivity.java'
s=read(p)
s=s.replace('? "\\n🔒 VERROU SÉCURISÉ : la commande reprendra après déverrouillage"\n                : DeviceLockState.isInsecurelyLocked(this)\n                ? "\\n✨ VERROU SIMPLE : le dialogue Téléphone sera libéré temporairement" : "")',
'''? "\\n🔒 ÉCRAN VERROUILLÉ : aucune commande USSD n’est forcée; déverrouillez normalement"
                : DeviceLockState.isInsecurelyLocked(this)
                ? "\\n🔒 VERROU SIMPLE : aucune tentative automatique de déverrouillage" : "")''')
anchor='''        @JavascriptInterface
        public void openPinSettings() {
            runOnUiThread(() -> showPinEditorDialog());
        }
'''
addition=anchor+'''
        @JavascriptInterface
        public void changeOperatorPin() {
            runOnUiThread(() -> showOperatorPinChangeDialog());
        }

        @JavascriptInterface
        public void resetOperatorPin() {
            runOnUiThread(() -> confirmResetOperatorPin());
        }

        @JavascriptInterface
        public void openBatteryOptimizationSettings() {
            runOnUiThread(() -> {
                try {
                    startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
                    toast("Choisissez Blue Magic puis « Sans restriction » / « Ne pas optimiser » si disponible.");
                } catch (Exception error) {
                    toast("Ouvrez Batterie > Blue Magic > Sans restriction / Ne pas optimiser.");
                }
            });
        }
'''
s=one(s,anchor,addition,'native PIN/battery bridge')
write(p,s)

# 3) Worker: future nodes get role default commissions; preflight is quote-only, never a reservation.
p='cloudflare/src/index.js'
s=read(p)
s=one(s,
"      'INSERT INTO nodes(node_code, role, phone_number, parent_node_code) VALUES(?, ?, ?, NULL)'\n    ).bind(node, role, phoneNumber).run();",
"      'INSERT INTO nodes(node_code, role, phone_number, parent_node_code, default_commission_bps) VALUES(?, ?, ?, NULL, ?)'\n    ).bind(node, role, phoneNumber, role === 'DAE' ? 1000 : role === 'DSM' ? 800 : 0).run();",
'new DAE commission default')
s=one(s,
"    await env.DB.prepare('INSERT INTO nodes(node_code, role, phone_number, parent_node_code) VALUES(?,?,?,?)')\n      .bind(desired, childRole, p, auth.node_code).run();",
"    await env.DB.prepare('INSERT INTO nodes(node_code, role, phone_number, parent_node_code, default_commission_bps) VALUES(?,?,?,?,?)')\n      .bind(desired, childRole, p, auth.node_code, childRole === 'DSM' ? 800 : 0).run();",
'new subordinate commission default')

# Remove AVAILABLE preflight holds from reusable balance precheck.
old='''    + "AND c.state NOT IN ('FAILED','CANCELLED')),0) - "
    + "COALESCE((SELECT SUM(p.requested_amount) FROM purchase_preflights p "
    + "WHERE p.supplier_node_code = b.node_code AND p.state = 'AVAILABLE' "
    + "AND p.purchase_command_public_id IS NULL "
    + "AND p.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ','now')),0)) AS available "'''
new='''    + "AND c.state NOT IN ('FAILED','CANCELLED')),0)) AS available "'''
s=one(s,old,new,'remove preflight hold from balance')
s=s.replace('''  // Reservation is decided in the same SQLite write statement that inserts the preflight.
  // D1 serializes writes, therefore the first request received by the network consumes the
  // available capacity before the next one is evaluated. No two callers can reserve the same FCFA.''',
'''  // This step certifies/quotes capacity only. It must NOT reserve or visually deduct stock.
  // The atomic reservation happens only when createCommand inserts the confirmed financial command.''')
s=s.replace("'Demande réservée selon l ordre d arrivée. Solde encore disponible après cette réservation : ' ",
            "'Montant disponible au contrôle. Aucune réservation avant confirmation. Disponible : ' ")
s=s.replace("'Les demandes arrivées avant sont prioritaires. Solde encore disponible du supérieur : ' ",
            "'Montant insuffisant au contrôle. Disponible du supérieur : ' ")

# Waiting preflights: no held-preflight subtraction; every waiting request gets a quote from real command reservations only.
old='''    const held = await env.DB.prepare(
      "SELECT COALESCE(SUM(requested_amount),0) AS total FROM purchase_preflights "
      + "WHERE supplier_node_code = ? AND state = 'AVAILABLE' AND purchase_command_public_id IS NULL "
      + "AND expires_at > strftime('%Y-%m-%dT%H:%M:%fZ','now')"
    ).bind(nodeCode).first();
    const available = Math.max(0, effective.available - Number(held?.total || 0));'''
new='''    const available = Math.max(0, effective.available);'''
s=one(s,old,new,'waiting preflight no hold')
s=s.replace('''    const message = accepted
      ? `Demande prioritaire réservée. Solde encore disponible après cette réservation : ${remaining} FCFA.`
      : `Les demandes arrivées avant sont prioritaires. Solde encore disponible du supérieur : ${remaining} FCFA.`;''',
'''    const message = accepted
      ? `Montant disponible au contrôle : ${available} FCFA. Aucune réservation avant confirmation.`
      : `Montant insuffisant au contrôle. Solde disponible du supérieur : ${available} FCFA.`;''')

# Capacity view makes quote-only semantics explicit.
old='''    message: state === 'EXPIRED' ? 'Le contrôle de solde a expiré; relancez la demande.'
      : row.result_message || '',
    expires_at: row.expires_at || ''
  };'''
new='''    reservation_applied: false,
    message: state === 'EXPIRED' ? 'Le contrôle de solde a expiré; relancez la demande.'
      : row.result_message || '',
    expires_at: row.expires_at || ''
  };'''
s=one(s,old,new,'capacity reservation flag')
write(p,s)

# 4) UI: hierarchical network rendering, max order suggestion, battery/PIN controls.
p='app/src/main/assets/app.js'
s=read(p)
# native actions
s=s.replace("else if(action==='pin'){window.AndroidBridge.openPinSettings();}",
'''else if(action==='pin'){window.AndroidBridge.openPinSettings();}
            else if(action==='change-pin'){window.AndroidBridge.changeOperatorPin();}
            else if(action==='reset-pin'){window.AndroidBridge.resetOperatorPin();}
            else if(action==='battery-settings'){window.AndroidBridge.openBatteryOptimizationSettings();}''')
# insufficient message includes max base and commission
old="""            showActionError({code:'SOLDE_SUPÉRIEUR_INSUFFISANT',message:'Vous ne pouvez pas commander ce montant. Le solde actuellement disponible du supérieur est de '+formatMoney(capacity.available_balance||0)+' FCFA. Cliquez sur OK puis recommencez avec un montant inférieur ou égal. Faites vite : un autre DSM/PoS peut utiliser ce solde avant vous.'});"""
new="""            var maxBase=Number(capacity.maximum_base_amount||0), rate=Number(capacity.commission_rate_bps||0), maxCommission=Math.floor(maxBase*rate/10000), maxTotal=maxBase+maxCommission;
            showActionError({code:'SOLDE_SUPÉRIEUR_INSUFFISANT',message:'Vous ne pouvez pas commander ce montant. Solde actuellement disponible : '+formatMoney(capacity.available_balance||0)+' FCFA. Avec votre taux '+String(rate/100).replace('.',',')+' %, le montant commandable maximum est '+formatMoney(maxBase)+' FCFA + '+formatMoney(maxCommission)+' FCFA de commission = '+formatMoney(maxTotal)+' FCFA à recevoir. Aucune somme n’est réservée tant que vous n’avez pas confirmé.'});"""
s=one(s,old,new,'max capacity UI')
# available message clarifies not reserved
s=s.replace("+'Disponible : '+formatMoney(capacity.available_balance||0)+' FCFA. Vérification des numéros officiels…');",
            "+'Disponible : '+formatMoney(capacity.available_balance||0)+' FCFA. Rien n’est réservé avant votre confirmation. Vérification des numéros officiels…');")

# Replace flat dashboard renderer with role-aware hierarchy.
start=s.index('    function renderDashboard(){')
end=s.index('    function cancelRemote(', start)
new_renderer=r'''    function nodeCard(n){
        var balanceText=n.balance===null||typeof n.balance==='undefined'?'Non lu':formatMoney(n.balance)+' FCFA';
        var reserved=Number(n.reserved_amount||0), available=n.available_balance===null||typeof n.available_balance==='undefined'?null:Number(n.available_balance);
        var evidenceText=n.balance===null||typeof n.balance==='undefined'?'':(' • '+(n.balance_quality==='EXACT'?'confirmé':'estimé')+' / '+(n.evidence_kind||n.balance_source||'source inconnue'));
        var activity=n.last_activity_at?(' • activité '+formatTime(n.last_activity_at)):'';
        var split='';
        if((n.role==='DAE'||n.role==='DSM')&&n.balance!==null&&typeof n.balance!=='undefined'){
            split='<br><small>Stock hors commission : '+escapeHtml(formatMoney(n.commission_base_balance||0))+' • part taux par défaut : '+escapeHtml(formatMoney(n.commission_component_balance||0))+' • total réel : '+escapeHtml(formatMoney(n.balance))+' • taux '+escapeHtml(String(Number(n.default_commission_bps||0)/100).replace('.',','))+' %</small>';
        }
        return '<article class="network-item"><div><strong>'+escapeHtml(n.node_code||'—')+'</strong><span>'+escapeHtml((n.role||'—')+' • '+(n.device_kind||'—')+evidenceText+activity)+'</span></div><div class="network-balance"><b>Solde Camtel : '+escapeHtml(balanceText)+'</b><br><small>Réservé après confirmation : '+escapeHtml(formatMoney(reserved))+' FCFA • Disponible : '+escapeHtml(available===null?'—':formatMoney(available)+' FCFA')+'</small>'+split+'</div></article>';
    }
    function fleetCard(n){return '<article class="network-item"><div><strong>'+escapeHtml(n.node_code||'—')+'</strong><span>'+escapeHtml(n.phone_number||'—')+'</span></div><div class="network-balance">'+escapeHtml(n.device_kind||'—')+'</div></article>';}
    function renderDashboard(){
        var nodes=dashboard&&dashboard.nodes||[],html='',fleet='',i,n,own=null,known=0,byParent={},direct=[],children=[];
        for(i=0;i<nodes.length;i+=1){n=nodes[i];if(n.node_code===configuration.node_code){own=n;}if(n.balance!==null&&typeof n.balance!=='undefined'){known+=1;}if(!byParent[n.parent_node_code||'']){byParent[n.parent_node_code||'']=[];}byParent[n.parent_node_code||''].push(n);}
        if(own){html+=nodeCard(own);fleet+=fleetCard(own);}
        direct=byParent[configuration.node_code]||[];
        if(configuration.role==='DAE'){
            for(i=0;i<direct.length;i+=1){n=direct[i];if(n.role!=='DSM'){continue;}children=byParent[n.node_code]||[];html+='<details class="panel" open><summary><strong>'+escapeHtml(n.node_code)+'</strong> — DSM direct • '+String(children.length)+' PoS</summary>'+nodeCard(n)+(children.length?'<details><summary>Afficher / masquer les PoS de '+escapeHtml(n.node_code)+'</summary>'+children.map(nodeCard).join('')+'</details>':'')+'</details>';fleet+='<details><summary>'+escapeHtml(n.node_code)+' • DSM</summary>'+fleetCard(n)+children.map(fleetCard).join('')+'</details>';}
        }else if(configuration.role==='DSM'){
            for(i=0;i<direct.length;i+=1){if(direct[i].role==='POS'){html+=nodeCard(direct[i]);fleet+=fleetCard(direct[i]);}}
        }
        byId('networkList').innerHTML=html||'<p class="muted">Aucun nœud visible dans votre périmètre.</p>';
        byId('fleetNetworkList').innerHTML=fleet||'<p class="muted">Aucun terminal rattaché.</p>';
        byId('fleetNetworkTitle').textContent=configuration.role==='DAE'?'Mes DSM et leurs PoS — '+String(nodes.length)+' nœud(s)':configuration.role==='DSM'?'Mes PoS — '+String(nodes.length)+' nœud(s)':'Mon terminal';
        byId('ownBalance').textContent=own&&own.balance!==null?formatMoney(own.balance)+' FCFA':'À actualiser';
        byId('balanceFreshness').textContent=own&&own.observed_at
            ? ('Dernière observation : '+formatTime(own.operator_event_at||own.observed_at)+' • '+(own.balance_quality==='EXACT'?'confirmé Camtel':'estimé')+' • '+(own.evidence_kind||own.balance_source||'source inconnue')
                +(own.available_balance!==null&&typeof own.available_balance!=='undefined'?' • disponible '+formatMoney(own.available_balance)+' FCFA':'')
                +(own.balance_reusable?' • réutilisable sans nouvel USSD':' • à recertifier avant finance'))
            :'Aucune lecture Camtel horodatée.';
    }
'''
s=s[:start]+new_renderer+s[end:]
write(p,s)

# 5) HTML: visible own PIN maintenance + battery stability controls in Robot tab.
p='app/src/main/assets/index.html'
s=read(p)
anchor='''            <div class="module-actions">
                <button type="button" class="secondary" data-native-action="permissions">1. Autorisations</button>
                <button type="button" class="secondary" data-native-action="pin">2. PIN Camtel</button>
                <button type="button" class="secondary" data-native-action="manage">Tous les réglages</button>
                <button type="button" data-native-action="start-robot">Démarrer le Robot</button>
            </div>'''
new='''            <div class="module-actions">
                <button type="button" class="secondary" data-native-action="permissions">1. Autorisations</button>
                <button type="button" class="secondary" data-native-action="battery-settings">2. Batterie sans restriction</button>
                <button type="button" class="secondary" data-native-action="pin">3. Enregistrer le PIN local</button>
                <button type="button" class="secondary" data-native-action="change-pin">Modifier mon PIN Camtel</button>
                <button type="button" class="secondary" data-native-action="reset-pin">Demander reset PIN</button>
                <button type="button" class="secondary" data-native-action="manage">Tous les réglages</button>
                <button type="button" data-native-action="start-robot">Démarrer / reprendre le Robot</button>
            </div>
            <p class="muted">Le Robot reste déclaré actif après veille/redémarrage. Android garde toutefois le contrôle de l’autorisation Accessibilité : si le système ou l’utilisateur la désactive, Blue Magic conserve les achats/ventes dans la file et demande sa réactivation au lieu de les échouer.</p>'''
s=one(s,anchor,new,'robot controls')
write(p,s)

# 6) Integration tests: default commission on future nodes and quote-only preflight.
p='cloudflare/test/integration.mjs'
s=read(p)
s=s.replace("assert.equal(firstDaeLease.data.command.ussd_code, '*550*2*699000002*200#');",
            "assert.equal(firstDaeLease.data.command.ussd_code, '*550*2*699000002*220#');")
s=s.replace("assert.equal(leased.data.command.ussd_code, '*550*2*699000002*500#');",
            "assert.equal(leased.data.command.ussd_code, '*550*2*699000002*550#');")
s=s.replace('assert.equal(status.data.command.amount, 500);','assert.equal(status.data.command.amount, 550);')
# Old second preflight expected first preflight hold (1000-500=500). Now no hold: request 1500 remains insufficient against 1000.
s=s.replace('assert.equal(insufficient.data.capacity.available_balance, 500);','assert.equal(insufficient.data.capacity.available_balance, 1000);')
# Capacity request base 500 @10% actually needs 550; assert quote fields.
needle="""  assert.equal(capacityReady.data.capacity.state, 'AVAILABLE');
  assert.equal(capacityReady.data.capacity.available_balance, 1000);"""
replacement=needle+"""
  assert.equal(capacityReady.data.capacity.base_amount, 500);
  assert.equal(capacityReady.data.capacity.commission_rate_bps, 1000);
  assert.equal(capacityReady.data.capacity.commission_amount, 50);
  assert.equal(capacityReady.data.capacity.requested_amount, 550);
  assert.equal(capacityReady.data.capacity.reservation_applied, false);"""
s=one(s,needle,replacement,'capacity commission assertions')
needle="""  assert.equal(supplyPreview.data.preview.target_phone, '699000002');
  assert.match(supplyPreview.data.preview.confirmation_fingerprint, /^[a-f0-9]{64}$/);"""
replacement="""  assert.equal(supplyPreview.data.preview.target_phone, '699000002');
  assert.equal(supplyPreview.data.preview.requested_base_amount, 500);
  assert.equal(supplyPreview.data.preview.commission_rate_bps, 1000);
  assert.equal(supplyPreview.data.preview.commission_amount, 50);
  assert.equal(supplyPreview.data.preview.amount, 550);
  assert.match(supplyPreview.data.preview.confirmation_fingerprint, /^[a-f0-9]{64}$/);"""
s=one(s,needle,replacement,'preview commission assertions')
# Waiting dsmTwo @10% base700 needs770; operator balance650 remains insufficient.
# dashboard after preflight must not show a preflight reservation.
needle="""  assert.equal(checkedCapacity.data.capacity.state, 'INSUFFICIENT');
  assert.equal(checkedCapacity.data.capacity.available_balance, 650);"""
replacement=needle+"""
  assert.equal(checkedCapacity.data.capacity.reservation_applied, false);"""
s=one(s,needle,replacement,'waiting no reservation assertion')
write(p,s)

# 7) Strengthen source contract.
p='app/src/test/v268-field-contract.mjs'
s=read(p)
s += """
if(!robot.includes('ACCESSIBILITY_DISABLED')||!robot.includes('transaction financière conservée en file')) throw new Error('accessibility queue preservation missing');
if(worker.includes("SUM(p.requested_amount) FROM purchase_preflights")) throw new Error('preflight still reserves stock before confirmation');
if(!worker.includes('reservation_applied: false')) throw new Error('quote-only preflight marker missing');
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
if(!html.includes('Batterie sans restriction')||!html.includes('Demander reset PIN')||!html.includes('Modifier mon PIN Camtel')) throw new Error('Robot maintenance controls missing');
"""
write(p,s)
