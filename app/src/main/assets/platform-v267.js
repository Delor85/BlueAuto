(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const bridge = () => window.AndroidBridge;
  const money = value => value == null ? '—' : new Intl.NumberFormat('fr-FR').format(Number(value)) + ' FCFA';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const request = (action, payload={}) => {
    if (!bridge() || !bridge().platformAction) return alert('Cette fonction exige l’APK Blue Magic v2.6.7.');
    bridge().platformAction(action, JSON.stringify(payload));
  };
  const add = (parent, html) => { if (parent) parent.insertAdjacentHTML('beforeend', html); };

  const reports = document.querySelector('[data-tab-panel="reports"], #panel-reports .panel-body, #panel-reports, [data-panel="reports"]');
  add(reports, `<section class="card v267-extra"><h3>🧠 Intelligence Blue & Bottom-Up</h3>
    <p>Solde certifié réutilisable jusqu’à 1 heure si aucune activité non rapprochée n’est apparue. Les débits connus et réservations restent déduits.</p>
    <div class="actions"><button id="v267-audit">Rafraîchir réseau intelligent</button><button id="v267-snapshot">Rapport réseau</button><button id="v267-messages">Preuves Blue récentes</button></div>
    <div id="v267-report-output" class="mono small"></div></section>`);

  const flux = document.querySelector('[data-tab-panel="flux"], #panel-flux .panel-body, #panel-flux, [data-panel="flux"]');
  add(flux, `<section class="card v267-extra"><h3>🧾 Registre de preuve & Mercenaires</h3>
    <p>Les SMS/pop-up Blue alimentent le registre structuré : ID, numéro, montant, CurrentBalance, date/heure et statut.</p>
    <details><summary>Hub Mercenaires — DAE</summary>
      <input id="merc-name" placeholder="Nom du mercenaire"><input id="merc-phone" placeholder="Téléphone 9 chiffres">
      <input id="merc-pos" placeholder="PoS Robot dédié (ex POS16_DSM7_OU3)"><input id="merc-deposit" type="number" placeholder="Dépôt virtuel FCFA">
      <button id="merc-save">Créer / créditer</button><button id="merc-refresh">Afficher les comptes</button><div id="merc-list" class="small"></div>
      <hr><h4>Vendre via une SIM PoS centrale</h4>
      <input id="merc-sale-id" type="number" placeholder="ID du mercenaire"><input id="merc-client" placeholder="Client Blue 9 chiffres">
      <input id="merc-amount" type="number" placeholder="Montant recharge FCFA"><button id="merc-sale">Confirmer et vendre</button>
      <div id="merc-sale-status" class="small"></div>
    </details></section>`);

  const fleet = document.querySelector('[data-tab-panel="fleet"], #panel-fleet .panel-body, #panel-fleet, [data-panel="fleet"]');
  add(fleet, `<section class="card v267-extra"><h3>📟 Pré-enrôlement Tchoronko / Compte fantôme</h3>
    <input id="shadow-id" placeholder="ID enfant"><input id="shadow-phone" placeholder="SIM 9 chiffres">
    <input id="shadow-name" placeholder="Nom / alias"><input id="shadow-zone" placeholder="Zone">
    <button id="shadow-save">Activer la liaison</button><hr>
    <h4>Créances</h4><input id="debt-node" placeholder="ID débiteur"><input id="debt-amount" type="number" placeholder="Montant avancé">
    <input id="debt-repaid" type="number" placeholder="Montant remboursé"><input id="debt-due" placeholder="Échéance AAAA-MM-JJ">
    <button id="debt-save">Enregistrer la créance</button><div id="debt-list" class="small"></div></section>`);

  const robot = document.querySelector('[data-tab-panel="config"], #panel-robot .panel-body, #panel-robot, [data-panel="robot"]');
  add(robot, `<section class="card v267-extra"><h3>🪪 Profil légal / KYC</h3>
    <input id="kyc-name" placeholder="Nom légal"><input id="kyc-doc" placeholder="N° pièce d’identité">
    <input id="kyc-ref" placeholder="Référence locale du document"><input id="kyc-zone" placeholder="Zone">
    <div class="grid-two"><input id="kyc-lat" placeholder="Latitude"><input id="kyc-lon" placeholder="Longitude"></div>
    <button id="kyc-save">Enregistrer le profil KYC</button>
    <p class="small">Les photos CNI ne sont pas envoyées dans D1 : seule une référence peut être conservée tant qu’un stockage documentaire chiffré dédié n’est pas configuré.</p></section>`);

  const sav = document.querySelector('[data-tab-panel="support"], #panel-sav .panel-body, #panel-sav, [data-panel="sav"]');
  add(sav, `<section class="card v267-extra"><h3>⌨ Sandbox USSD protégée</h3>
    <input id="raw-ussd" placeholder="Ex: *825*3*3#"><button id="raw-run">Exécuter sur la SIM Robot</button>
    <p class="small">Le Sandbox refuse automatiquement un code contenant le PIN Camtel enregistré.</p>
    <details><summary>Guide rapide</summary><p>TEST : *825*3*3#. Solde, historique, détail et maintenance disposent aussi de boutons dédiés dans Flux/Flotte. Les transactions financières continuent d’utiliser la file sécurisée Remote→Worker→Robot.</p></details></section>`);

  const bind = (id, fn) => { const el=$(id); if(el) el.addEventListener('click', fn); };
  bind('v267-audit', () => request('network_balance_audit'));
  bind('v267-snapshot', () => request('platform_snapshot'));
  bind('v267-messages', () => request('operator_insights'));
  bind('shadow-save', () => request('shadow_enroll', {node_code:$('shadow-id').value, phone_number:$('shadow-phone').value, display_name:$('shadow-name').value, zone:$('shadow-zone').value}));
  bind('debt-save', () => request('debt_save', {debtor_node_code:$('debt-node').value, amount_advanced:$('debt-amount').value, amount_repaid:$('debt-repaid').value, due_date:$('debt-due').value}));
  bind('kyc-save', () => request('kyc_save', {legal_name:$('kyc-name').value,id_document_number:$('kyc-doc').value,document_reference:$('kyc-ref').value,zone:$('kyc-zone').value,latitude:$('kyc-lat').value,longitude:$('kyc-lon').value}));
  bind('merc-save', () => request('mercenary_save', {display_name:$('merc-name').value,phone_number:$('merc-phone').value,dedicated_pos_node_code:$('merc-pos').value,deposit_amount:$('merc-deposit').value}));
  bind('merc-refresh', () => request('mercenary_list'));
  bind('merc-sale', () => {
    const id=Number($('merc-sale-id').value||0), phone=$('merc-client').value, amount=Number($('merc-amount').value||0);
    if (!id || !/^\d{9}$/.test(String(phone).replace(/\D/g,'')) || amount<=0) return alert('ID mercenaire, numéro client 9 chiffres et montant sont requis.');
    if (!confirm(`Vente Mercenaire : ${amount} FCFA vers ${phone} ? La commission de 7,5 % sera créditée automatiquement.`)) return;
    request('mercenary_sale', {mercenary_id:id,target_phone:phone,amount,confirmed:true,client_request_id:'merc_'+Date.now()+'_'+Math.random().toString(36).slice(2,10)});
  });
  bind('raw-run', () => { if(bridge()?.executeRawUSSD) bridge().executeRawUSSD($('raw-ussd').value); });

  window.BlueMagicNative = window.BlueMagicNative || {};
  const previous = window.BlueMagicNative.onPlatformAction;
  window.BlueMagicNative.onPlatformAction = data => {
    if (typeof previous === 'function') { try { previous(data); } catch (_) {} }
    if (data?.error) return alert(data.message || 'Erreur Blue Magic');
    const action = data?._action || '';
    if (action === 'network_balance_audit') {
      const out=$('v267-report-output');
      if(out) out.innerHTML=`Audit Bottom-Up lancé : <b>${Number(data.queued||0)}</b> requête(s) sélective(s), <b>${Number(data.reused||0)}</b> preuve(s) réutilisée(s), <b>${Number(data.already_pending||0)}</b> déjà en file, <b>${Number(data.unavailable||0)}</b> indisponible(s).`;
      return;
    }
    if (action === 'platform_snapshot') {
      const nodes=data.nodes||[]; const dry=nodes.filter(n => n.balance != null && Number(n.balance)<7500);
      const dormant=nodes.filter(n => n.last_activity_at && Date.now()-Date.parse(n.last_activity_at)>48*3600e3);
      const coaching=dormant.slice(0,8).map(n=>`🟠 ${esc(n.node_code)} — Bonjour, votre activité Blue semble ralentie. Solde connu : ${money(n.balance)}. Besoin d'aide pour relancer les ventes ?`);
      $('v267-report-output').innerHTML=`Flotte: <b>${nodes.length}</b> · Zones sèches: <b>${dry.length}</b> · Hibernation >48h: <b>${dormant.length}</b><br>`+
        dry.slice(0,12).map(n=>`🔴 ${esc(n.node_code)} — ${money(n.balance)}`).join('<br>') +
        (coaching.length?'<hr><b>Scripts CRM suggérés</b><br>'+coaching.join('<br>'):'');
      if (data.debts) $('debt-list').innerHTML=data.debts.map(d=>`${esc(d.debtor_node_code)} : ${money(Number(d.amount_advanced)-Number(d.amount_repaid))}`).join('<br>');
    } else if (action === 'operator_insights') {
      const list=data.messages||[]; $('v267-report-output').innerHTML=list.slice(0,20).map(m=>`${esc(m.created_at)} · ${esc(m.node_code)} · ${esc(m.message_kind)} · ${money(m.amount)} · solde ${money(m.current_balance)} · ${esc(m.transaction_id||m.receipt_number)}`).join('<br>');
    } else if (action === 'debt_save' || action === 'debt_list') {
      $('debt-list').innerHTML=(data.debts||[]).map(d=>`${esc(d.debtor_node_code)} : reste ${money(d.remaining)} — ${esc(d.state)}`).join('<br>');
    } else if (action === 'mercenary_save' || action === 'mercenary_list') {
      const rows=data.mercenaries || (data.mercenary ? [data.mercenary] : []);
      $('merc-list').innerHTML=rows.map(m=>`#${esc(m.id)} · ${esc(m.display_name)} · virtuel ${money(m.virtual_balance)} · commissions ${money(m.commission_balance)} · PoS ${esc(m.dedicated_pos_node_code||'à définir')}`).join('<br>');
    } else if (action === 'mercenary_sale') {
      const c=data.command||{}; $('merc-sale-status').textContent=`Commande ${c.public_id||''} créée. Montant ${money(c.amount)}. Suivez son état dans le registre Flux.`;
      request('mercenary_list');
    } else if (action === 'shadow_enroll') alert(`Compte fantôme ${data.shadow?.node_code||''} activé.`);
    else if (action === 'kyc_save') alert('Profil KYC enregistré.');
  };
})();
