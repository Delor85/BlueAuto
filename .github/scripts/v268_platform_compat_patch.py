from pathlib import Path

js = r'''(function () {
  'use strict';

  function byId(id) { return document.getElementById(id); }
  function bridge() { return typeof window.AndroidBridge === 'undefined' ? null : window.AndroidBridge; }
  function readConfiguration() {
    var value = {}, raw = '', nativeBridge = bridge();
    if (!nativeBridge || !nativeBridge.getConfiguration) return value;
    try { raw = nativeBridge.getConfiguration() || '{}'; value = JSON.parse(raw); } catch (ignored) { value = {}; }
    value.role = String(value.role || '').toUpperCase();
    value.mode = String(value.mode || '').toUpperCase();
    return value;
  }
  var configuration = readConfiguration();
  var formatter = null;
  try { if (typeof Intl !== 'undefined' && Intl.NumberFormat) formatter = new Intl.NumberFormat('fr-FR'); } catch (ignored) {}
  function money(value) {
    var number;
    if (value === null || typeof value === 'undefined' || value === '') return '—';
    number = Number(value);
    if (!isFinite(number)) return '—';
    return (formatter ? formatter.format(number) : String(Math.round(number))) + ' FCFA';
  }
  function esc(value) {
    var map = {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'};
    return String(value === null || typeof value === 'undefined' ? '' : value)
      .replace(/[&<>"']/g, function (character) { return map[character]; });
  }
  function value(id) { var element = byId(id); return element ? element.value : ''; }
  function request(action, payload) {
    var nativeBridge = bridge();
    if (!nativeBridge || !nativeBridge.platformAction) {
      alert('Cette fonction exige l’APK Blue Magic v2.6.8.');
      return;
    }
    nativeBridge.platformAction(action, JSON.stringify(payload || {}));
  }
  function add(parent, html) { if (parent) parent.insertAdjacentHTML('beforeend', html); }
  function bind(id, handler) { var element = byId(id); if (element) element.addEventListener('click', handler); }
  function each(items, handler) { var i; for (i = 0; i < items.length; i += 1) handler(items[i], i); }
  function rowsHtml(items, renderer) {
    var output = [], i;
    items = items || [];
    for (i = 0; i < items.length; i += 1) output.push(renderer(items[i], i));
    return output.join('<br>');
  }
  function isManager() { return configuration.role === 'DAE' || configuration.role === 'DSM'; }
  function isDae() { return configuration.role === 'DAE'; }
  function isRobot() { return configuration.mode === 'ROBOT'; }

  var reports = document.querySelector('[data-tab-panel="reports"], #panel-reports .panel-body, #panel-reports, [data-panel="reports"]');
  add(reports, '<details class="card v267-extra" open><summary><strong>🧠 Intelligence Blue & Bottom-Up</strong></summary>' +
    '<p>Solde certifié réutilisable jusqu’à 1 heure si aucune activité non rapprochée n’est apparue. Les débits connus et réservations restent déduits.</p>' +
    '<div class="actions"><button id="v267-audit">Rafraîchir réseau intelligent</button><button id="v267-snapshot">Rapport réseau vivant</button>' +
    '<button id="v267-messages">Preuves Blue récentes</button><button id="v267-catalog">Référentiel Camtel</button></div>' +
    '<div id="v267-report-output" class="mono small"></div></details>');

  var flux = document.querySelector('[data-tab-panel="flux"], #panel-flux .panel-body, #panel-flux, [data-panel="flux"]');
  if (isDae()) {
    add(flux, '<details class="card v267-extra"><summary><strong>🧾 Hub Mercenaires — DAE</strong></summary>' +
      '<p>Les SMS/pop-up Blue alimentent le registre structuré : ID, numéro, montant, CurrentBalance, date/heure et statut.</p>' +
      '<input id="merc-name" placeholder="Nom du mercenaire"><input id="merc-phone" placeholder="Téléphone 9 chiffres">' +
      '<input id="merc-pos" placeholder="PoS Robot dédié (ex POS16_DSM7_OU3)"><input id="merc-deposit" type="number" placeholder="Dépôt virtuel FCFA">' +
      '<button id="merc-save">Créer / créditer</button><button id="merc-refresh">Afficher les comptes</button><div id="merc-list" class="small"></div>' +
      '<hr><h4>Vendre via une SIM PoS centrale</h4><input id="merc-sale-id" type="number" placeholder="ID du mercenaire">' +
      '<input id="merc-client" placeholder="Client Blue 9 chiffres"><input id="merc-amount" type="number" placeholder="Montant recharge FCFA">' +
      '<button id="merc-sale">Confirmer et vendre</button><div id="merc-sale-status" class="small"></div></details>');
  }

  var fleet = document.querySelector('[data-tab-panel="fleet"], #panel-fleet .panel-body, #panel-fleet, [data-panel="fleet"]');
  if (isManager()) {
    add(fleet, '<details class="card v267-extra"><summary><strong>📟 Gestion avancée des enfants</strong></summary>' +
      '<p class="small">Le DAE valide ses DSM; le DSM valide ses PoS. La validation initiale est valable 48 h. Un code court est accepté seulement dans sa branche.</p>' +
      '<h4>Validation / pré-enrôlement</h4><input id="shadow-id" placeholder="ID enfant"><input id="shadow-phone" placeholder="SIM 9 chiffres">' +
      '<input id="shadow-name" placeholder="Nom / alias"><input id="shadow-zone" placeholder="Zone"><button id="shadow-save">Activer la liaison</button><hr>' +
      '<h4>💹 Commissions d’approvisionnement</h4><p class="small">DAE : taux par défaut pour les DSM. DSM : taux par défaut pour les PoS. Une exception enfant remplace seulement ce taux.</p>' +
      '<input id="commission-default" type="number" step="0.01" placeholder="Taux par défaut %"><button id="commission-default-save">Enregistrer le taux par défaut</button>' +
      '<input id="commission-child" placeholder="Enfant direct"><input id="commission-child-rate" type="number" step="0.01" placeholder="Taux personnalisé %">' +
      '<button id="commission-child-save">Personnaliser</button><button id="commission-child-default">Revenir au défaut</button><button id="commission-refresh">Afficher les taux</button>' +
      '<div id="commission-list" class="small"></div><hr><h4>Créances</h4><input id="debt-node" placeholder="ID débiteur">' +
      '<input id="debt-amount" type="number" placeholder="Montant avancé"><input id="debt-repaid" type="number" placeholder="Montant remboursé">' +
      '<input id="debt-due" placeholder="Échéance AAAA-MM-JJ"><button id="debt-save">Enregistrer la créance</button><div id="debt-list" class="small"></div></details>');
  }

  var robot = document.querySelector('[data-tab-panel="config"], #panel-robot .panel-body, #panel-robot, [data-panel="robot"]');
  add(robot, '<details class="card v267-extra"><summary><strong>🪪 Profil légal / KYC</strong></summary>' +
    '<input id="kyc-name" placeholder="Nom légal"><input id="kyc-doc" placeholder="N° pièce d’identité">' +
    '<input id="kyc-ref" placeholder="Référence locale du document"><input id="kyc-zone" placeholder="Zone">' +
    '<div class="grid-two"><input id="kyc-lat" placeholder="Latitude"><input id="kyc-lon" placeholder="Longitude"></div>' +
    '<button id="kyc-save">Enregistrer le profil KYC</button>' +
    '<p class="small">Les photos CNI ne sont pas envoyées dans D1 : seule une référence peut être conservée tant qu’un stockage documentaire chiffré dédié n’est pas configuré.</p></details>');

  var sav = document.querySelector('[data-tab-panel="support"], #panel-sav .panel-body, #panel-sav, [data-panel="sav"]');
  if (isRobot()) {
    add(sav, '<details class="card v267-extra"><summary><strong>⌨ Sandbox USSD protégée</strong></summary>' +
      '<input id="raw-ussd" placeholder="Ex: *825*3*3#"><button id="raw-run">Exécuter sur la SIM Robot</button>' +
      '<p class="small">Le Sandbox refuse automatiquement un code contenant le PIN Camtel enregistré.</p>' +
      '<p class="small">TEST : *825*3*3#. Solde, historique, détail et maintenance disposent aussi de boutons dédiés dans Flux/Flotte. Les transactions financières continuent d’utiliser la file sécurisée Remote→Worker→Robot.</p></details>');
  } else {
    add(sav, '<details class="card v267-extra"><summary><strong>ℹ Guide Remote</strong></summary>' +
      '<p class="small">Ce téléphone est une télécommande : les commandes sont créées ici puis exécutées par le Robot détenteur de la SIM. Le Sandbox USSD local est volontairement masqué.</p></details>');
  }

  bind('v267-audit', function () { request('network_balance_audit'); });
  bind('v267-snapshot', function () { request('platform_snapshot'); });
  bind('v267-messages', function () { request('operator_insights'); });
  bind('v267-catalog', function () { request('operator_catalog'); });
  bind('shadow-save', function () { request('shadow_enroll', {node_code:value('shadow-id'), phone_number:value('shadow-phone'), display_name:value('shadow-name'), zone:value('shadow-zone')}); });
  bind('commission-refresh', function () { request('commission_policy'); });
  bind('commission-default-save', function () { request('commission_set_default', {rate_bps:Math.round(Number(value('commission-default') || 0) * 100)}); });
  bind('commission-child-save', function () { request('commission_set_child', {child_node_code:value('commission-child'), rate_bps:Math.round(Number(value('commission-child-rate') || 0) * 100)}); });
  bind('commission-child-default', function () { request('commission_set_child', {child_node_code:value('commission-child'), use_default:true}); });
  bind('debt-save', function () { request('debt_save', {debtor_node_code:value('debt-node'), amount_advanced:value('debt-amount'), amount_repaid:value('debt-repaid'), due_date:value('debt-due')}); });
  bind('kyc-save', function () { request('kyc_save', {legal_name:value('kyc-name'), id_document_number:value('kyc-doc'), document_reference:value('kyc-ref'), zone:value('kyc-zone'), latitude:value('kyc-lat'), longitude:value('kyc-lon')}); });
  bind('merc-save', function () { request('mercenary_save', {display_name:value('merc-name'), phone_number:value('merc-phone'), dedicated_pos_node_code:value('merc-pos'), deposit_amount:value('merc-deposit')}); });
  bind('merc-refresh', function () { request('mercenary_list'); });
  bind('merc-sale', function () {
    var id = Number(value('merc-sale-id') || 0), phone = value('merc-client'), amount = Number(value('merc-amount') || 0), cleaned;
    cleaned = String(phone).replace(/\D/g, '');
    if (!id || !/^\d{9}$/.test(cleaned) || amount <= 0) { alert('ID mercenaire, numéro client 9 chiffres et montant sont requis.'); return; }
    if (!confirm('Vente Mercenaire : ' + amount + ' FCFA vers ' + phone + ' ? La commission de 7,5 % sera créditée automatiquement.')) return;
    request('mercenary_sale', {mercenary_id:id, target_phone:phone, amount:amount, confirmed:true, client_request_id:'merc_' + Date.now() + '_' + Math.random().toString(36).slice(2,10)});
  });
  bind('raw-run', function () { var nativeBridge = bridge(); if (nativeBridge && nativeBridge.executeRawUSSD) nativeBridge.executeRawUSSD(value('raw-ussd')); });

  window.BlueMagicNative = window.BlueMagicNative || {};
  var previous = window.BlueMagicNative.onPlatformAction;
  window.BlueMagicNative.onPlatformAction = function (data) {
    var action, out, nodes, dry, dormant, recheck, certified, coaching, i, node, rows, catalog, regions, list, children, debts, command;
    data = data || {};
    if (typeof previous === 'function') { try { previous(data); } catch (ignored) {} }
    if (data.error) { alert(data.message || 'Erreur Blue Magic'); return; }
    action = data._action || '';
    out = byId('v267-report-output');

    if (action === 'network_balance_audit') {
      if (out) out.innerHTML = 'Audit ' + esc(data.region_code || '') + ' / ' + esc(data.dae_node_code || data.scope_node_code || '') +
        ' : <b>' + Number(data.queued || 0) + '</b> requête(s), <b>' + Number(data.reused || 0) + '</b> preuve(s), <b>' +
        Number(data.deferred || 0) + '</b> différée(s), <b>' + Number(data.unavailable || 0) + '</b> indisponible(s). Finance 1 h; rapport inactif jusqu’à ' +
        Math.round(Number(data.report_freshness_seconds || 0) / 3600) + ' h sans mouvement ultérieur.';
      return;
    }

    if (action === 'platform_snapshot') {
      nodes = data.nodes || []; dry = []; dormant = []; recheck = []; certified = []; coaching = [];
      for (i = 0; i < nodes.length; i += 1) {
        node = nodes[i];
        if (node.balance !== null && typeof node.balance !== 'undefined' && Number(node.balance) < 7500) dry.push(node);
        if (node.last_activity_at && Date.now() - Date.parse(node.last_activity_at) > 48 * 3600000) dormant.push(node);
        if (node.balance_report_state === 'RECHECK_REQUIRED') recheck.push(node);
        if (node.balance_report_state === 'CERTIFIED') certified.push(node);
      }
      for (i = 0; i < dormant.length && i < 8; i += 1) {
        node = dormant[i]; coaching.push('🟠 ' + esc(node.node_code) + ' — Bonjour, votre activité Blue semble ralentie. Solde connu : ' + money(node.balance) + '. Besoin d’aide pour relancer les ventes ?');
      }
      if (out) out.innerHTML = 'Rapport vivant au <b>' + esc(data.generated_at || '') + '</b> · Flotte: <b>' + nodes.length + '</b> · Certifiés: <b>' + certified.length +
        '</b> · À revérifier: <b>' + recheck.length + '</b> · Zones sèches: <b>' + dry.length + '</b><br>' +
        rowsHtml(recheck.slice(0,12), function (item) { return '⚠ ' + esc(item.node_code) + ' — mouvement après dernière preuve ' + esc(item.evidence_at || 'inconnue'); }) +
        (recheck.length ? '<hr>' : '') + rowsHtml(dry.slice(0,12), function (item) { return '🔴 ' + esc(item.node_code) + ' — ' + money(item.balance) + ' · ' + esc(item.balance_report_state || 'UNKNOWN'); }) +
        (coaching.length ? '<hr><b>Scripts CRM suggérés</b><br>' + coaching.join('<br>') : '');
      if (data.debts && byId('debt-list')) byId('debt-list').innerHTML = rowsHtml(data.debts, function (item) { return esc(item.debtor_node_code) + ' : ' + money(Number(item.amount_advanced) - Number(item.amount_repaid)); });
      return;
    }

    if (action === 'operator_catalog') {
      catalog = data.catalog || {}; regions = catalog.regions || [];
      if (out) out.innerHTML = '<b>Référentiel Camtel ' + esc(catalog.catalog_version || '') + '</b> · Master : ' + esc(catalog.national_master_sim_name || '') + '<br>' +
        rowsHtml(regions, function (region) { return esc(region.code) + '=' + esc(region.name); }).replace(/<br>/g, ' · ') + '<br>' +
        esc((catalog.identity || {}).dae || '') + '<br>' + esc((catalog.identity || {}).dsm || '') + '<br>' + esc((catalog.identity || {}).pos || '') + '<br>' + esc((catalog.identity || {}).short_alias_rule || '');
      return;
    }

    if (action === 'operator_insights') {
      list = data.messages || [];
      if (out) out.innerHTML = rowsHtml(list.slice(0,20), function (message) {
        return esc(message.created_at) + ' · ' + esc(message.node_code) + ' · ' + esc(message.message_kind) + ' · ' + money(message.amount) + ' · solde ' + money(message.current_balance) + ' · ' + esc(message.transaction_id || message.receipt_number);
      });
      return;
    }

    if (action === 'commission_policy' || action === 'commission_set_default' || action === 'commission_set_child') {
      if (byId('commission-default')) byId('commission-default').value = String(Number(data.default_rate_bps || 0) / 100);
      children = data.children || [];
      if (byId('commission-list')) byId('commission-list').innerHTML = rowsHtml(children, function (child) {
        return esc(child.node_code) + ' : ' + String(Number(child.effective_rate_bps || 0) / 100).replace('.', ',') + ' % · ' + esc(child.source === 'CHILD_OVERRIDE' ? 'personnalisé' : 'défaut');
      }) || 'Aucun enfant direct.';
      return;
    }

    if (action === 'debt_save' || action === 'debt_list') {
      debts = data.debts || [];
      if (byId('debt-list')) byId('debt-list').innerHTML = rowsHtml(debts, function (debt) { return esc(debt.debtor_node_code) + ' : reste ' + money(debt.remaining) + ' — ' + esc(debt.state); });
      return;
    }

    if (action === 'mercenary_save' || action === 'mercenary_list') {
      rows = data.mercenaries || (data.mercenary ? [data.mercenary] : []);
      if (byId('merc-list')) byId('merc-list').innerHTML = rowsHtml(rows, function (mercenary) {
        return '#' + esc(mercenary.id) + ' · ' + esc(mercenary.display_name) + ' · virtuel ' + money(mercenary.virtual_balance) + ' · commissions ' + money(mercenary.commission_balance) + ' · PoS ' + esc(mercenary.dedicated_pos_node_code || 'à définir');
      });
      return;
    }

    if (action === 'mercenary_sale') {
      command = data.command || {};
      if (byId('merc-sale-status')) byId('merc-sale-status').textContent = 'Commande ' + (command.public_id || '') + ' créée. Montant ' + money(command.amount) + '. Suivez son état dans le registre Flux.';
      request('mercenary_list');
      return;
    }

    if (action === 'shadow_enroll') { alert('Compte fantôme ' + esc((data.shadow || {}).node_code || '') + ' activé.'); return; }
    if (action === 'kyc_save') alert('Profil KYC enregistré.');
  };
})();
'''

Path('app/src/main/assets/platform-v267.js').write_text(js)

test = r'''import fs from 'node:fs';
const js=fs.readFileSync('app/src/main/assets/platform-v267.js','utf8');
for(const required of ['platform_snapshot','operator_insights','shadow_enroll','mercenary_save','commission_policy','commission_set_child','kyc_save','executeRawUSSD']){
  if(!js.includes(required)) throw new Error('platform function lost: '+required);
}
for(const banned of ['=>','?.','??','const ','let ','`']){
  if(js.includes(banned)) throw new Error('old WebView incompatible syntax remains: '+banned);
}
if(!js.includes("configuration.role === 'DAE'")||!js.includes("configuration.role === 'DSM'")) throw new Error('role gating missing');
if(!js.includes('if (isDae())')||!js.includes('if (isManager())')) throw new Error('advanced module role scope missing');
if(!js.includes('if (isRobot())')) throw new Error('Robot-only Sandbox gating missing');
if(!js.includes('var formatter = null')) throw new Error('cached number formatter missing');
if(!js.includes('<details class="card v267-extra"')) throw new Error('collapsible advanced modules missing');
console.log('v2.6.8 platform extension: ES5 WebView compatibility and role-scoped advanced modules OK');
'''
Path('app/src/test/v268-platform-compat.mjs').write_text(test)
