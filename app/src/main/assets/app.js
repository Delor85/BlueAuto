(function () {
    'use strict';
    var TERMINAL = {SUCCEEDED:true,FAILED:true,UNKNOWN:true,BLOCKED:true,CANCELLED:true};
    var labels = {PENDING:'En attente',LEASED:'Réservée au Robot',DIALING:'Composition USSD',AWAITING_PIN:'Vérification du pop-up',PIN_SUBMITTED:'PIN validé',AWAITING_RESULT:'Confirmation Camtel',SUCCEEDED:'Réussie',FAILED:'Échec',UNKNOWN:'À vérifier',BLOCKED:'Robot bloqué — PIN',CANCELLED:'Annulée'};
    var configuration = {}, commands = [], pendingPreview = null, capacityPolls = 0, dashboard = null;
    function byId(id){return document.getElementById(id);}
    function each(selector,fn){var items=document.querySelectorAll(selector),i;for(i=0;i<items.length;i+=1){fn(items[i]);}}
    function bridge(){return typeof window.AndroidBridge!=='undefined';}
    window.BlueMagicNative={
        onCommandPreview:function(data){handlePreview(data);},
        onPurchaseCapacity:function(data){handlePurchaseCapacity(data);},
        onCommandCreated:function(data){setBusy(false);pendingPreview=null;if(data.error){showActionError(data);return;}clearActionError();var command=data.command||{};if(!command.public_id){showActionError({code:'INVALID_RESPONSE',message:'Réponse serveur incomplète.'});return;}upsert(command);render();if(command.robot_ready===false){showActionProgress((command.robot_status||'ROBOT_OFFLINE')+' — '+(command.robot_message||'Commande créée, mais le Robot ne communique pas encore.'));showToast('Commande créée, mais Robot hors ligne.');return;}showActionProgress('Commande créée. Le Robot détenteur de la SIM est connecté et va la prendre.');showToast(data.duplicate?'Cette demande existait déjà.':'Commande créée et transmise au Robot exact.');},
        onCommandStatus:function(data){if(data&&data.command){upsert(data.command);render();if(TERMINAL[data.command.state]){window.AndroidBridge.loadDashboard();}}},
        onCommandCancelled:function(data){if(data.error){showToast(data.message||'Annulation impossible.');return;}if(data.command){upsert(data.command);render();showToast('Commande annulée.');}},
        onServerHealth:function(data){var line=byId('serverHealthStatus');if(data&&data.error){line.textContent=(data.code||'SERVER_ERROR')+' — '+(data.message||'Serveur inaccessible.');line.className='health-line notice-danger';showToast('Serveur inaccessible.');return;}line.textContent='EN LIGNE — '+(data.service||'blue-magic-api')+' • '+(data.version||'version inconnue')+' • D1 '+(data.database||'inconnu');line.className='health-line muted';showToast('Serveur Blue Magic en ligne.');},
        onDashboard:function(data){if(data&&data.error){showToast((data.code||'DASHBOARD_ERROR')+' — '+(data.message||'Rapport indisponible.'));return;}dashboard=data||{};renderDashboard();}
    };
    function initialize(){
        if(!bridge()){byId('nativeBadge').textContent='PONT ABSENT';byId('browserNotice').className='notice';return;}
        try{configuration=JSON.parse(window.AndroidBridge.getConfiguration()||'{}');}catch(ignored){configuration={};}
        configuration.role=normalizeRole(configuration);
        commands=load();byId('nativeBadge').textContent='PONT NATIF ACTIF';byId('nativeBadge').className='badge badge-ok';
        byId('nodeCode').textContent=configuration.node_code||'Nœud non configuré';
        byId('nodeMeta').textContent=(configuration.role||'—')+' • '+(configuration.mode||'—')+' • SIM '+((configuration.sim_slot||0)+1);
        byId('robotState').textContent=configuration.robot_enabled?'ROBOT ACTIF':'ROBOT ARRÊTÉ';
        if(configuration.pin_blocked){byId('fatalNotice').textContent='PIN BLOQUÉ pour les achats et ventes. TEST_NUMBER et les fonctions Remote restent disponibles.';byId('fatalNotice').className='notice notice-danger';}
        else if(configuration.mode==='ROBOT'&&!configuration.sim_verified){byId('fatalNotice').textContent='SIM NON VÉRIFIÉE : le Robot est arrêté et ne peut réserver aucune commande. Ouvrez ☰ GÉRER > VÉRIFIER / LIER LA SIM.';byId('fatalNotice').className='notice notice-danger';}
        if(configuration.role==='DAE'){showRoleNotice('Profil DAE : approvisionnement des DSM disponible. Un DAE n’achète pas auprès d’un supérieur et ne vend pas aux clients finaux.');}
        else if(configuration.role==='DSM'){showRoleNotice('Profil DSM : achat auprès du DAE et approvisionnement des PoS disponibles.');}
        else if(configuration.role==='POS'){showRoleNotice('Profil PoS : achat auprès du DSM et vente aux clients finaux disponibles.');}
        else{byId('fatalNotice').textContent='RÔLE NON RECONNU : ouvrez ☰ GÉRER > VÉRIFIER / RÉPARER L’APPAIRAGE. Aucune opération financière ne sera envoyée tant que le profil n’est pas identifié.';byId('fatalNotice').className='notice notice-danger';}
        if(configuration.mode==='ROBOT'&&!configuration.pin_configured){showActionError({code:'FINANCE_PIN_REQUIRED',message:'TEST_NUMBER reste disponible. Enregistrez le PIN Camtel chiffré avant un achat ou une vente.'});}
        else if(configuration.mode==='ROBOT'&&!configuration.accessibility_enabled){showActionError({code:'FINANCE_ACCESSIBILITY_REQUIRED',message:'TEST_NUMBER reste disponible. Activez l’Accessibilité Blue Magic avant un achat ou une vente.'});}
        if(configuration.role==='DSM'||configuration.role==='POS'){byId('requestSupplyCard').className='panel command-card';}
        if(configuration.role==='DAE'||configuration.role==='DSM'){byId('supplyChildCard').className='panel command-card';}
        if(configuration.role==='DAE'||configuration.role==='DSM'){byId('childBalanceCard').className='panel command-card';}
        if(configuration.role==='DAE'||configuration.role==='DSM'){byId('childAdminCard').className='panel module-card';}
        if(configuration.role==='POS'){byId('retailCard').className='panel command-card';}
        each('button[data-action]',function(button){button.onclick=function(){execute(button.getAttribute('data-action'));};});
        each('button[data-native-action]',function(button){button.onclick=function(){runNativeAction(button.getAttribute('data-native-action'));};});
        initializeTabs();
        byId('refreshCommands').onclick=refresh;
        document.addEventListener('focusin',function(event){if(event.target&&event.target.tagName==='INPUT'){document.body.className='form-editing';try{window.AndroidBridge.setFormEditing(true);}catch(ignored){}}});
        document.addEventListener('focusout',function(){window.setTimeout(function(){if(!document.activeElement||document.activeElement.tagName!=='INPUT'){document.body.className='';try{window.AndroidBridge.setFormEditing(false);}catch(ignored){}}},180);});
        render();refresh();window.AndroidBridge.loadDashboard();window.setInterval(refresh,15000);
        window.setInterval(function(){if(document.visibilityState!=='hidden'){try{window.AndroidBridge.loadDashboard();}catch(ignored){}}},30000);
        document.addEventListener('visibilitychange',function(){if(document.visibilityState!=='hidden'){try{window.AndroidBridge.loadDashboard();}catch(ignored){}}});
    }
    function initializeTabs(){
        var saved=localStorage.getItem('blue_magic_active_module')||'flux';
        each('button[data-tab]',function(button){button.onclick=function(){showTab(button.getAttribute('data-tab'));};});
        showTab(saved);
    }
    function showTab(name){
        var found=false;
        each('[data-tab-panel]',function(panel){var active=panel.getAttribute('data-tab-panel')===name;found=found||active;panel.className=active?'module-screen':'module-screen hidden';});
        if(!found&&name!=='flux'){showTab('flux');return;}
        each('button[data-tab]',function(button){button.className=button.getAttribute('data-tab')===name?'module-tab active':'module-tab';});
        each('button[data-tab="flux"]',function(button){button.className=button.getAttribute('data-tab')===name?'module-tab module-tab-primary active':'module-tab module-tab-primary';});
        localStorage.setItem('blue_magic_active_module',name);
        window.scrollTo(0,0);
    }

    function runNativeAction(action){
        if(!bridge()){return;}
        try{
            if(action==='accounts'){window.AndroidBridge.openAccounts();}
            else if(action==='verify-sim'){window.AndroidBridge.verifySim();}
            else if(action==='permissions'){window.AndroidBridge.prepareRobotPermissions();}
            else if(action==='pin'){window.AndroidBridge.openPinSettings();}
            else if(action==='manage'){window.AndroidBridge.openManagement();}
            else if(action==='start-robot'){window.AndroidBridge.startRobot();showToast('Contrôle du Robot lancé. Suivez le message Android.');}
            else if(action==='server-health'){byId('serverHealthStatus').textContent='Vérification HTTPS et D1 en cours…';window.AndroidBridge.checkServerHealth();}
            else if(action==='refresh-dashboard'){if(window.AndroidBridge.refreshDashboardLive){window.AndroidBridge.refreshDashboardLive();showToast('Actualisation intelligente : preuves récentes réutilisées, USSD seulement si nécessaire.');}else{window.AndroidBridge.loadDashboard();}}
            else if(action==='go-test'){showTab('flux');var test=document.querySelector('button[data-action="test-number"]');if(test&&test.parentNode&&test.parentNode.scrollIntoView){test.parentNode.scrollIntoView(true);}}
        }catch(error){showToast('Action Android indisponible : '+error.message);}
    }
    function normalizeRole(config){
        var role=String(config.role||'').replace(/^\s+|\s+$/g,'').toUpperCase(),node,parent;
        if(role==='DAE'||role==='DSM'||role==='POS'){return role;}
        node=String(config.node_code||'').replace(/^\s+|\s+$/g,'').toUpperCase();
        parent=String(config.parent_node_code||'').replace(/^\s+|\s+$/g,'');
        if(/^POS(?:[-_\/]|\d)/.test(node)){return 'POS';}
        if(/^DSM(?:[-_\/]|\d)/.test(node)){return 'DSM';}
        if(node&&!parent){return 'DAE';}
        return '';
    }
    function showRoleNotice(message){var notice=byId('roleNotice');notice.textContent=message;notice.className='notice';}
    function execute(action){
        if(!bridge()){return;}var type='',node='',phone='',amount='',argument='';
        if(action==='request-supply'){type='REQUEST_SUPPLY';amount=byId('requestSupplyAmount').value.replace(/^\s+|\s+$/g,'');}
        else if(action==='supply-child'){type='SUPPLY_CHILD';node=byId('childNode').value.replace(/^\s+|\s+$/g,'').toUpperCase();amount=byId('childAmount').value.replace(/^\s+|\s+$/g,'');}
        else if(action==='retail-sale'){type='RETAIL_SALE';phone=byId('retailPhone').value.replace(/\D/g,'');amount=byId('retailAmount').value.replace(/^\s+|\s+$/g,'');}
        else if(action==='check-balance'){type='CHECK_BALANCE';}
        else if(action==='last-transactions'){type='LAST_TRANSACTIONS';}
        else if(action==='transaction-details'){type='TRANSACTION_DETAILS';argument=byId('transactionId').value.replace(/^\s+|\s+$/g,'');}
        else if(action==='child-balance'){type='CHILD_BALANCE';node=byId('balanceChildNode').value.replace(/^\s+|\s+$/g,'').toUpperCase();}
        else if(action==='init-child-pin-reset'){type='INIT_CHILD_PIN_RESET';node=byId('adminChildNode').value.replace(/^\s+|\s+$/g,'').toUpperCase();}
        else if(action==='suspend-child'){type='SUSPEND_CHILD';node=byId('adminChildNode').value.replace(/^\s+|\s+$/g,'').toUpperCase();}
        else if(action==='reactivate-child'){type='REACTIVATE_CHILD';node=byId('adminChildNode').value.replace(/^\s+|\s+$/g,'').toUpperCase();}
        else if(action==='freeze-child'){type='FREEZE_CHILD';node=byId('adminChildNode').value.replace(/^\s+|\s+$/g,'').toUpperCase();}
        else if(action==='reactivate-frozen-child'){type='REACTIVATE_FROZEN_CHILD';node=byId('adminChildNode').value.replace(/^\s+|\s+$/g,'').toUpperCase();}
        else if(action==='freeze-self'){type='FREEZE_SELF';}
        else{type='TEST_NUMBER';}
        if((type==='REQUEST_SUPPLY'||type==='SUPPLY_CHILD'||type==='RETAIL_SALE')&&!/^[1-9]\d{0,8}$/.test(amount)){showToast('Saisissez un montant entier valide.');return;}
        if(type==='SUPPLY_CHILD'&&!node){showToast('Saisissez le code du nœud enfant.');return;}
        if(type==='CHILD_BALANCE'&&!node){showToast('Saisissez le code du nœud enfant.');return;}
        if((type==='INIT_CHILD_PIN_RESET'||type==='SUSPEND_CHILD'||type==='REACTIVATE_CHILD'||type==='FREEZE_CHILD'||type==='REACTIVATE_FROZEN_CHILD')&&!node){showToast('Saisissez le code du nœud enfant à administrer.');return;}
        if(type==='RETAIL_SALE'&&!/^\d{9}$/.test(phone)){showToast('Le numéro client doit avoir 9 chiffres.');return;}
        if(type==='TRANSACTION_DETAILS'&&!/^[A-Za-z0-9_-]{6,64}$/.test(argument)){showToast('Saisissez un identifiant Camtel valide.');return;}
        pendingPreview={type:type,node:node,phone:phone,amount:amount,argument:argument,request_id:requestId(),capacity_check_id:''};
        setBusy(true);clearActionError();
        if(type==='REQUEST_SUPPLY'){
            capacityPolls=0;showActionProgress('Lecture du solde disponible du supérieur avant confirmation…');
            window.AndroidBridge.checkPurchaseCapacity(amount,pendingPreview.request_id);
            return;
        }
        if(type==='TEST_NUMBER'||type==='CHECK_BALANCE'||type==='LAST_TRANSACTIONS'||type==='TRANSACTION_DETAILS'||type==='CHILD_BALANCE'){
            window.AndroidBridge.createCommand(type,node,phone,amount,pendingPreview.request_id,'','',argument);
            return;
        }
        showActionProgress('Vérification des numéros officiels et de la filiation…');
        window.AndroidBridge.previewCommand(type,node,phone,amount,pendingPreview.request_id,'',argument);
    }
    function handlePurchaseCapacity(data){
        var capacity=data&&data.capacity||{},state=String(capacity.state||'');
        if(!pendingPreview){setBusy(false);return;}
        if(data&&data.error){setBusy(false);pendingPreview=null;showActionError(data);return;}
        if(state==='WAITING'){
            capacityPolls+=1;
            showActionProgress('Solde du '+(capacity.supplier_node_code||'supérieur')+' en cours de lecture par son Robot…');
            if(capacityPolls>30){setBusy(false);pendingPreview=null;showActionError({code:'BALANCE_CHECK_TIMEOUT',message:'La lecture du solde dépasse 45 secondes. Vérifiez le Robot du supérieur.'});return;}
            window.setTimeout(function(){if(pendingPreview){window.AndroidBridge.getPurchaseCapacityStatus(capacity.capacity_check_id);}},1500);
            return;
        }
        if(state==='INSUFFICIENT'){
            setBusy(false);pendingPreview=null;
            showActionError({code:'SOLDE_SUPÉRIEUR_INSUFFISANT',message:'Vous ne pouvez pas commander ce montant. Le solde actuellement disponible du supérieur est de '+formatMoney(capacity.available_balance||0)+' FCFA. Cliquez sur OK puis recommencez avec un montant inférieur ou égal. Faites vite : un autre DSM/PoS peut utiliser ce solde avant vous.'});
            return;
        }
        if(state!=='AVAILABLE'){
            setBusy(false);pendingPreview=null;showActionError({code:'BALANCE_CHECK_'+(state||'FAILED'),message:capacity.message||'Le solde du supérieur n’a pas pu être certifié.'});return;
        }
        pendingPreview.capacity_check_id=String(capacity.capacity_check_id||'');
        showActionProgress((capacity.balance_reused
            ? 'Solde Camtel récent réutilisé — aucune commande USSD supplémentaire. '
            : 'Solde Camtel actualisé. ')
            +'Disponible : '+formatMoney(capacity.available_balance||0)+' FCFA. Vérification finale des numéros…');
        window.AndroidBridge.previewCommand(pendingPreview.type,pendingPreview.node,pendingPreview.phone,
            pendingPreview.amount,pendingPreview.request_id,pendingPreview.capacity_check_id,pendingPreview.argument);
    }
    function handlePreview(data){
        var preview,fingerprint;
        if(!pendingPreview){setBusy(false);return;}
        if(data&&data.error){setBusy(false);pendingPreview=null;showActionError(data);return;}
        preview=data&&data.preview||{};fingerprint=String(preview.confirmation_fingerprint||'');
        if(!fingerprint){setBusy(false);pendingPreview=null;showActionError({code:'PREVIEW_INCOMPLETE',message:'Le serveur n’a pas certifié les numéros de cette commande.'});return;}
        clearActionError();
        if(preview.robot_ready===false){showActionProgress((preview.robot_status||'ROBOT_OFFLINE')+' — '+(preview.robot_message||'Le Robot ne communique pas encore. La commande peut être mise en attente.'));}
        if(!confirmFinancial(preview)){setBusy(false);pendingPreview=null;showToast('Commande annulée avant toute composition.');return;}
        showActionProgress('Commande confirmée. Transmission au Robot de la SIM fournisseur…');
        window.AndroidBridge.createCommand(pendingPreview.type,pendingPreview.node,pendingPreview.phone,
            pendingPreview.amount,pendingPreview.request_id,fingerprint,pendingPreview.capacity_check_id,pendingPreview.argument);
    }
    function confirmFinancial(preview){
        if(preview.dangerous){
            return window.confirm('COMMANDE CAMTEL SENSIBLE\n\n'+(preview.operation_label||preview.operation||'Maintenance SIM')+'\n\nCOMPTE EXÉCUTEUR : '+(preview.executor_node_code||'—')+' — '+(preview.executor_phone||'—')+'\nCIBLE : '+(preview.target_node_code||preview.executor_node_code||'—')+' — '+(preview.target_phone||preview.executor_phone||'—')+'\n\nCette commande peut suspendre ou geler une SIM. Vérifiez la cible avant de confirmer. Le PIN reste uniquement sur le Robot.\n\nCONFIRMER CETTE COMMANDE ?');
        }
        var title=preview.operation==='RETAIL_TRANSFER'?'VENTE À UN CLIENT':'TRANSFERT DE CRÉDIT';
        var supplier=(preview.executor_node_code||'FOURNISSEUR')+' — '+(preview.executor_phone||'numéro absent');
        var beneficiary=(preview.target_node_code||'CLIENT')+' — '+(preview.target_phone||'numéro absent');
        var base=Number(preview.requested_base_amount||preview.amount||0), commission=Number(preview.commission_amount||0), rate=Number(preview.commission_rate_bps||0)/100;
        var quote=preview.operation==='DISTRIBUTION_TRANSFER'
            ? ('\nMONTANT COMMANDÉ : '+formatMoney(base)+' FCFA\nCOMMISSION ('+String(rate).replace('.',',')+' %) : '+formatMoney(commission)+' FCFA\nTOTAL À RECEVOIR : '+formatMoney(preview.amount)+' FCFA')
            : ('\nMONTANT : '+formatMoney(preview.amount)+' FCFA');
        return window.confirm('CONFIRMATION 1 SUR 2\n\n'+title+'\n\nFOURNISSEUR : '+supplier+'\nBÉNÉFICIAIRE : '+beneficiary+quote+'\n\nSi le taux de commission ne vous convient pas, annulez maintenant et contactez votre supérieur. Après confirmation, le Robot composera le montant total certifié. Blue Magic contrôlera ensuite les mêmes données dans le pop-up Camtel avant d’insérer le PIN.\n\nCONFIRMER CETTE TRANSACTION ?');
    }
    function formatMoney(value){return String(value).replace(/\B(?=(\d{3})+(?!\d))/g,' ');}
    function refresh(){var i;if(!bridge()){return;}for(i=0;i<commands.length;i+=1){if(!TERMINAL[commands[i].state]){window.AndroidBridge.getCommandStatus(commands[i].public_id);}}}
    function upsert(command){var i,index=-1,key;for(i=0;i<commands.length;i+=1){if(commands[i].public_id===command.public_id){index=i;break;}}if(index<0){commands.unshift(command);}else{for(key in command){if(Object.prototype.hasOwnProperty.call(command,key)){commands[index][key]=command[key];}}}commands=commands.slice(0,20);localStorage.setItem(storageKey(),JSON.stringify(commands));}
    function load(){try{var value=JSON.parse(localStorage.getItem(storageKey())||'[]');return Object.prototype.toString.call(value)==='[object Array]'?value:[];}catch(ignored){return [];}}
    function storageKey(){return 'blue_magic_embedded_commands_'+(configuration.profile_id||configuration.node_code||'default');}
    function render(){var html='',i,c,state,detail,time;if(!commands.length){byId('commandList').innerHTML='<p class="muted">Aucune commande sur ce téléphone.</p>';updateModuleData();return;}for(i=0;i<commands.length;i+=1){c=commands[i];state=escapeHtml(c.state||'PENDING');detail=escapeHtml(c.result_message||c.operation||'Commande');time=c.updated_at||c.created_at||'';html+='<article class="command-item"><div class="command-item-top"><span class="command-id">'+escapeHtml(c.public_id||'')+'</span><span class="command-state state-'+state+'">'+escapeHtml(labels[c.state]||c.state||'—')+'</span></div><div class="command-detail">'+detail+'</div>'+(time?'<div class="command-time">Horodatage : '+escapeHtml(formatTime(time))+'</div>':'')+(c.state==='PENDING'?'<button type="button" class="button-small secondary" data-cancel-command="'+escapeHtml(c.public_id||'')+'">Annuler cette commande</button>':'')+'</article>';}byId('commandList').innerHTML=html;each('button[data-cancel-command]',function(button){button.onclick=function(){cancelRemote(button.getAttribute('data-cancel-command'));};});updateModuleData();}
    function updateModuleData(){
        var success=0,pending=0,terminal=0,finance=0,i,c,start,end,duration='—',support='Aucun blocage local détecté.',last=null;
        for(i=0;i<commands.length;i+=1){
            c=commands[i];
            if(c.state==='SUCCEEDED'){success+=1;}
            if(!TERMINAL[c.state]){pending+=1;}
            else{terminal+=1;}
            if(c.operation&&c.operation!=='TEST_NUMBER'){finance+=1;}
            if(!last){last=c;}
            if(duration==='—'&&c.created_at&&(c.completed_at||TERMINAL[c.state]&&c.updated_at)){
                start=new Date(c.created_at);end=new Date(c.completed_at||c.updated_at);
                if(!isNaN(start.getTime())&&!isNaN(end.getTime())&&end.getTime()>=start.getTime()){
                    duration=Math.round((end.getTime()-start.getTime())/1000)+' s';
                }
            }
        }
        byId('metricCommandCount').textContent=String(commands.length);
        byId('metricSuccessCount').textContent=String(success);
        byId('metricPendingCount').textContent=String(pending);
        byId('metricLastDuration').textContent=duration;
        byId('metricSuccessRate').textContent=terminal?Math.round(success*100/terminal)+' %':'—';
        byId('metricFinanceCount').textContent=String(finance);
        byId('reportActivityTitle').textContent=last?(labels[last.state]||last.state||'Commande locale'):'Aucune activité locale';
        byId('reportActivityDetail').textContent=last?((last.operation||'Commande')+' • '+formatTime(last.updated_at||last.created_at||'')):'Les résultats apparaîtront ici sans exposer le PIN.';
        byId('fleetNodeStatus').textContent=(configuration.node_code||'Nœud non configuré')+' • '+(configuration.role||'—')+' • '+(configuration.mode||'—');
        byId('fleetSimStatus').textContent=configuration.mode==='ROBOT'
            ? ('SIM '+((configuration.sim_slot||0)+1)+' • '+(configuration.sim_verified?'VÉRIFIÉE':'À VÉRIFIER / LIER')+' • '+(configuration.robot_enabled?'ROBOT ACTIF':'HALL ROBOT — ARRÊTÉ'))
            : 'Mode Remote : aucune SIM n’est requise. Passez dans le hall Robot avant de demander les autorisations.';
        byId('configRobotStatus').textContent=configuration.mode==='ROBOT'
            ? ((configuration.robot_enabled?'Robot actif.':'Hall Robot ouvert, Robot non démarré.')+' Accessibilité '+(configuration.accessibility_enabled?'OK.':'à activer.')+' PIN '+(configuration.pin_configured?'enregistré localement.':'à enregistrer.'))
            : 'Compte Remote. Le passage vers Robot ouvre d’abord le hall sans exiger de permission.';
        if(configuration.pin_blocked){support='PIN BLOQUÉ : corrigez le PIN dans ☰ GÉRER avant une finance.';}
        else if(configuration.mode==='ROBOT'&&!configuration.sim_verified){support='SIM non vérifiée : le Robot reste sans privilège dans son hall.';}
        else if(pending){support=String(pending)+' commande(s) non terminale(s) à suivre dans le registre Flux.';}
        byId('supportStatus').textContent=support;
    }
    function renderDashboard(){
        var nodes=dashboard&&dashboard.nodes||[],html='',fleet='',i,n,own=null,known=0;
        for(i=0;i<nodes.length;i+=1){
            n=nodes[i];if(n.node_code===configuration.node_code){own=n;}
            if(n.balance!==null&&typeof n.balance!=='undefined'){known+=1;}
            var balanceText=n.balance===null||typeof n.balance==='undefined'?'Non lu':formatMoney(n.balance)+' FCFA';
            var reserved=Number(n.reserved_amount||0), available=n.available_balance===null||typeof n.available_balance==='undefined'?null:Number(n.available_balance);
            var evidenceText=n.balance===null||typeof n.balance==='undefined'?'':(' • '+(n.balance_quality==='EXACT'?'confirmé':'estimé')+' / '+(n.evidence_kind||n.balance_source||'source inconnue'));
            var split='';
            if((n.role==='DAE'||n.role==='DSM')&&n.balance!==null&&typeof n.balance!=='undefined'){split='<br><small>Stock hors commission : '+escapeHtml(formatMoney(n.commission_base_balance||0))+' • part taux par défaut : '+escapeHtml(formatMoney(n.commission_component_balance||0))+' • taux '+escapeHtml(String(Number(n.default_commission_bps||0)/100).replace('.',','))+' %</small>';}
            html+='<article class="network-item"><div><strong>'+escapeHtml(n.node_code||'—')+'</strong><span>'+escapeHtml((n.role||'—')+' • '+(n.device_kind||'—')+evidenceText)+'</span></div><div class="network-balance"><b>Solde Camtel : '+escapeHtml(balanceText)+'</b><br><small>Réservé : '+escapeHtml(formatMoney(reserved))+' FCFA • Disponible : '+escapeHtml(available===null?'—':formatMoney(available)+' FCFA')+'</small>'+split+'</div></article>';
            fleet+='<article class="network-item"><div><strong>'+escapeHtml(n.node_code||'—')+'</strong><span>'+escapeHtml(n.phone_number||'—')+'</span></div><div class="network-balance">'+escapeHtml(n.device_kind||'—')+'</div></article>';
        }
        byId('networkList').innerHTML=html||'<p class="muted">Aucun nœud visible dans cette arborescence.</p>';
        byId('fleetNetworkList').innerHTML=fleet||'<p class="muted">Aucun terminal rattaché.</p>';
        byId('fleetNetworkTitle').textContent=String(nodes.length)+' nœud(s) • '+String(known)+' solde(s) connu(s)';
        byId('ownBalance').textContent=own&&own.balance!==null?formatMoney(own.balance)+' FCFA':'À actualiser';
        byId('balanceFreshness').textContent=own&&own.observed_at
            ? ('Dernière observation : '+formatTime(own.observed_at)+' • '+(own.balance_quality==='EXACT'?'confirmé Camtel':'estimé')+' • '+(own.evidence_kind||own.balance_source||'source inconnue')
                +(own.available_balance!==null&&typeof own.available_balance!=='undefined'?' • disponible '+formatMoney(own.available_balance)+' FCFA':'')
                +(own.balance_reusable?' • partageable sans nouvel USSD':' • à recertifier avant finance'))
            :'Aucune lecture Camtel horodatée.';
    }
    function cancelRemote(commandId){if(!bridge()||!window.confirm('Annuler cette commande encore en attente ?')){return;}window.AndroidBridge.cancelCommand(commandId);}
    function formatTime(value){var d=new Date(value);if(isNaN(d.getTime())){return String(value);}return two(d.getDate())+'/'+two(d.getMonth()+1)+'/'+d.getFullYear()+' à '+two(d.getHours())+':'+two(d.getMinutes())+':'+two(d.getSeconds());}
    function two(value){return value<10?'0'+value:String(value);}
    function requestId(){return 'req_'+new Date().getTime()+'_'+Math.random().toString(36).slice(2,14);}
    function setBusy(value){each('button[data-action]',function(button){button.disabled=value;});}
    function showActionProgress(message){var notice=byId('actionNotice');notice.textContent=message;notice.className='notice';}
    function showActionError(data){var code=String(data&&data.code||'ACTION_FAILED'),message=String(data&&data.message||'Action impossible.'),notice=byId('actionNotice');notice.textContent=code+' — '+message;notice.className='notice notice-danger';showToast(code+' — '+message);}
    function clearActionError(){var notice=byId('actionNotice');notice.textContent='';notice.className='notice notice-danger hidden';}
    function showToast(message){var toast=byId('toast');toast.textContent=message;toast.className='toast';window.setTimeout(function(){toast.className='toast hidden';},4000);}
    function escapeHtml(value){var entities={'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'};return String(value).replace(/[&<>'"]/g,function(c){return entities[c];});}
    if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',initialize);}else{initialize();}
}());
