(function () {
    'use strict';
    var TERMINAL = {SUCCEEDED:true,FAILED:true,UNKNOWN:true,BLOCKED:true,CANCELLED:true};
    var labels = {PENDING:'En attente',LEASED:'Réservée au Robot',DIALING:'Composition USSD',AWAITING_PIN:'Vérification du pop-up',PIN_SUBMITTED:'PIN validé',AWAITING_RESULT:'Confirmation Camtel',SUCCEEDED:'Réussie',FAILED:'Échec',UNKNOWN:'À vérifier',BLOCKED:'Robot bloqué — PIN',CANCELLED:'Annulée'};
    var configuration = {}, commands = [], pendingPreview = null, capacityPolls = 0, dashboard = null;
    var activeTab = 'reports', commandPollTimer = null, dashboardPollTimer = null;
    var commandPollCursor = 0, dashboardLoadedAt = 0, actionInFlight = false;
    var submittedForm = null, financialPreview = null;
    function byId(id){return document.getElementById(id);}
    function each(selector,fn){var items=document.querySelectorAll(selector),i;for(i=0;i<items.length;i+=1){fn(items[i]);}}
    function bridge(){return typeof window.AndroidBridge!=='undefined';}
    window.BlueMagicNative={
        onCommandPreview:function(data){handlePreview(data);},
        onPurchaseCapacity:function(data){handlePurchaseCapacity(data);},
        onCommandCreated:function(data){var submitted=submittedForm;setBusy(false);pendingPreview=null;submittedForm=null;if(data.error){showActionError(data);return;}clearActionError();var command=data.command||{};if(!command.public_id){showActionError({code:'INVALID_RESPONSE',message:'Réponse serveur incomplète.'});return;}clearSubmittedFields(submitted);upsert(command);render();scheduleCommandPoll(1200);if(command.robot_ready===false){showActionProgress((command.robot_status||'ROBOT_OFFLINE')+' — '+(command.robot_message||'Commande créée, mais le Robot ne communique pas encore.'));showToast('Commande créée, mais Robot hors ligne.');return;}showActionProgress('Commande créée. Le Robot détenteur de la SIM est connecté et va la prendre.');showToast(data.duplicate?'Cette demande existait déjà.':'Commande créée et transmise au Robot exact.');},
        onCommandStatus:function(data){if(data&&data.command){upsert(data.command);render();if(TERMINAL[data.command.state]){surfaceCommandResult(data.command);requestDashboard(true);}scheduleCommandPoll(5000);}},
        onCommandCancelled:function(data){if(data.error){showToast(data.message||'Annulation impossible.');return;}if(data.command){upsert(data.command);render();showToast('Commande annulée.');}},
        onServerHealth:function(data){var line=byId('serverHealthStatus');if(data&&data.error){line.textContent=(data.code||'SERVER_ERROR')+' — '+(data.message||'Serveur inaccessible.');line.className='health-line notice-danger';showToast('Serveur inaccessible.');return;}line.textContent='EN LIGNE — '+(data.service||'blue-magic-api')+' • '+(data.version||'version inconnue')+' • D1 '+(data.database||'inconnu');line.className='health-line muted';showToast('Serveur B.I.R. / Blue Magic Engine en ligne.');},
        onDashboard:function(data){if(data&&data.error){showToast((data.code||'DASHBOARD_ERROR')+' — '+(data.message||'Rapport indisponible.'));scheduleDashboardPoll();return;}dashboard=data||{};dashboardLoadedAt=new Date().getTime();refreshConfiguration();if(dashboard.viewer_identity&&dashboard.viewer_identity.node_code){configuration.official_node_code=dashboard.viewer_identity.node_code;}renderConfigurationState();renderDashboard();scheduleDashboardPoll();},
        onLocalSync:function(){refreshConfiguration();refresh(true);requestDashboard(true);if(byId('birSyncState'))byId('birSyncState').textContent='Synchronisation relancée à '+formatTime(new Date().toISOString());}
    };
    function initialize(){
        if(!bridge()){byId('nativeBadge').textContent='PONT ABSENT';byId('browserNotice').className='notice';return;}
        try{configuration=JSON.parse(window.AndroidBridge.getConfiguration()||'{}');}catch(ignored){configuration={};}
        configuration.role=normalizeRole(configuration);
        commands=load();byId('nativeBadge').textContent='PONT NATIF ACTIF';byId('nativeBadge').className='badge badge-ok';
        renderConfigurationState();
        if(configuration.pin_blocked){byId('fatalNotice').textContent='PIN BLOQUÉ : achats et ventes suspendus. Touchez ici pour corriger le PIN local.';byId('fatalNotice').className='notice notice-danger';byId('fatalNotice').onclick=function(){runNativeAction('pin');};}
        else if(configuration.mode==='ROBOT'&&!configuration.sim_verified){byId('fatalNotice').textContent='SIM NON VÉRIFIÉE : touchez ici pour vérifier / lier la SIM et reprendre le Robot.';byId('fatalNotice').className='notice notice-danger';byId('fatalNotice').onclick=function(){runNativeAction('verify-sim');};}
        if(configuration.role==='DAE'){showRoleNotice('DAE actif : pilotez vos DSM, leurs PoS, les soldes et les approvisionnements depuis votre propre pyramide.');if(byId('birRoleActionTitle')){byId('birRoleActionTitle').textContent='ACTIONS DAE PRIORITAIRES';byId('birRoleActionSub').textContent='Pilotez, approvisionnez et développez votre réseau.';byId('birTransactionModuleTitle').textContent='Approvisionnement Blue';}byId('reportsIntroTitle').textContent='Pilotage de mon réseau';byId('reportsIntroText').textContent='Mon solde, mes DSM et leurs PoS sont présentés dans ma propre pyramide uniquement, avec les activités et preuves disponibles.';}
        else if(configuration.role==='DSM'){showRoleNotice('DSM actif : demandez du stock au DAE, approvisionnez vos PoS et suivez votre réseau direct.');if(byId('birRoleActionTitle')){byId('birRoleActionTitle').textContent='ACTIONS DSM PRIORITAIRES';byId('birRoleActionSub').textContent='Approvisionnez vos PoS et maîtrisez votre stock.';byId('birTransactionModuleTitle').textContent='Approvisionnement PoS';}byId('reportsIntroTitle').textContent='Mes soldes et mes PoS';byId('reportsIntroText').textContent='Mon compte et mes PoS directs sont suivis ici sans exposer les autres DSM ni les autres branches du DAE.';}
        else if(configuration.role==='POS'){showRoleNotice('PoS actif : vendez du crédit Blue, demandez du stock à votre DSM et suivez votre propre activité.');if(byId('birRoleActionTitle')){byId('birRoleActionTitle').textContent='VENDRE & SUIVRE';byId('birRoleActionSub').textContent='Vendez du crédit Blue rapidement et gardez votre solde sous contrôle.';byId('birTransactionModuleTitle').textContent='Vente Blue';}byId('reportsIntroTitle').textContent='Mon solde et mon activité';byId('reportsIntroText').textContent='Ce PoS affiche uniquement son propre solde Camtel, son disponible, ses ventes et ses preuves récentes.';}
        else{byId('fatalNotice').textContent='RÔLE NON RECONNU : ouvrez ☰ GÉRER > VÉRIFIER / RÉPARER L’APPAIRAGE. Aucune opération financière ne sera envoyée tant que le profil n’est pas identifié.';byId('fatalNotice').className='notice notice-danger';}
        applyRoleFieldSemantics();
        if(configuration.mode==='ROBOT'&&!configuration.pin_configured){showActionError({code:'FINANCE_PIN_REQUIRED',message:'TEST_NUMBER reste disponible. Enregistrez le PIN Camtel chiffré avant un achat ou une vente.'});}
        else if(configuration.mode==='ROBOT'&&!configuration.accessibility_enabled){showActionError({code:'FINANCE_ACCESSIBILITY_REQUIRED',message:'TEST_NUMBER reste disponible. Activez l’Accessibilité Blue Magic avant un achat ou une vente.'});}
        if(configuration.role==='DSM'||configuration.role==='POS'){byId('requestSupplyCard').className='panel command-card';}
        if(configuration.role==='DAE'||configuration.role==='DSM'){byId('supplyChildCard').className='panel command-card';}
        if(configuration.role==='DAE'||configuration.role==='DSM'){byId('childBalanceCard').className='panel command-card';}
        if(configuration.role==='DAE'||configuration.role==='DSM'){byId('childAdminCard').className='panel module-card';}
        if(configuration.role==='POS'){byId('retailCard').className='panel command-card';}
        each('button[data-action]',function(button){button.onclick=function(){execute(button.getAttribute('data-action'));};});
        each('button[data-native-action]',function(button){button.onclick=function(){runNativeAction(button.getAttribute('data-native-action'));};});
        initializeInputErgonomics();
        initializeTabs();
        each('[data-tab-jump]',function(button){button.onclick=function(){showTab(button.getAttribute('data-tab-jump'));};});
        byId('refreshCommands').onclick=function(){refresh(true);};
        document.addEventListener('focusin',function(event){if(event.target&&event.target.tagName==='INPUT'){document.body.className='form-editing';try{window.AndroidBridge.setFormEditing(true);}catch(ignored){}}});
        document.addEventListener('focusout',function(){window.setTimeout(function(){if(!document.activeElement||document.activeElement.tagName!=='INPUT'){document.body.className='';try{window.AndroidBridge.setFormEditing(false);}catch(ignored){}}},180);});
        render();refresh(true);scheduleCommandPoll(5000);
        if(dashboardRelevant()){requestDashboard(true);}scheduleDashboardPoll();
        document.addEventListener('visibilitychange',function(){
            if(document.visibilityState==='hidden'){clearPollingTimers();return;}
            scheduleCommandPoll(250);
            if(dashboardRelevant()){requestDashboard(false);}
            scheduleDashboardPoll();
        });
    }
    function initializeTabs(){
        var saved='reports';
        applyRoleNavigation();
        each('button[data-tab]',function(button){button.onclick=function(){showTab(button.getAttribute('data-tab'));};});
        showTab(saved);
    }
    function tabLabel(tab,value){
        var button=document.querySelector('button[data-tab="'+tab+'"]'),spans;
        if(!button){return;}spans=button.querySelectorAll('span');
        if(spans.length>1){spans[spans.length-1].textContent=value;}
    }
    function applyRoleNavigation(){
        var fleet=document.querySelector('button[data-tab="fleet"]');
        if(fleet){fleet.className='module-tab';fleet.setAttribute('aria-hidden','false');}
        tabLabel('reports','Accueil');tabLabel('fleet','Réseau');tabLabel('support','Activité');tabLabel('config','Gérer');
        if(configuration.role==='DAE'){tabLabel('flux','Piloter');}
        else if(configuration.role==='DSM'){tabLabel('flux','Fournir');}
        else if(configuration.role==='POS'){tabLabel('flux','Vendre');}
        else{tabLabel('flux','Action');}
        updateTabAttention();
    }
    function showTab(name){
        var found=false;
        activeTab=name;
        each('[data-tab-panel]',function(panel){var active=panel.getAttribute('data-tab-panel')===name;found=found||active;panel.className=active?'module-screen':'module-screen hidden';});
        if(!found&&name!=='flux'){showTab('flux');return;}
        each('button[data-tab]',function(button){
            var tab=button.getAttribute('data-tab'),isActive=tab===name,isPrimary=tab==='flux';
            button.className='module-tab'+(isPrimary?' module-tab-primary':'')+(isActive?' active':'');
        });
        localStorage.setItem('bir_active_module_v2610',name);
        if(dashboardRelevant()){requestDashboard(false);}scheduleDashboardPoll();
        updateTabAttention();
        window.scrollTo(0,0);
    }
    function ensureTabBadge(tab){
        var button=document.querySelector('button[data-tab="'+tab+'"]'),badge;
        if(!button){return null;}badge=button.querySelector('.module-tab-attention');
        if(!badge){badge=document.createElement('b');badge.className='module-tab-attention hidden';button.appendChild(badge);}return badge;
    }
    function updateTabAttention(){
        var pending=0,i,flux=ensureTabBadge('flux'),robot=ensureTabBadge('config'),needsRobot=false;
        for(i=0;i<commands.length;i+=1){if(!TERMINAL[commands[i].state]){pending+=1;}}
        if(flux){flux.textContent=pending>9?'9+':String(pending);flux.className=pending?'module-tab-attention':'module-tab-attention hidden';}
        needsRobot=configuration.mode==='ROBOT'&&(!configuration.sim_verified||!configuration.pin_configured||!configuration.accessibility_enabled||!configuration.robot_enabled||configuration.pin_blocked);
        if(robot){robot.textContent='!';robot.className=needsRobot?'module-tab-attention module-tab-warning':'module-tab-attention hidden';}
    }

    function runNativeAction(action){
        if(!bridge()){return;}
        try{
            if(action==='accounts'){window.AndroidBridge.openAccounts();}
            else if(action==='verify-sim'){window.AndroidBridge.verifySim();}
            else if(action==='permissions'){window.AndroidBridge.prepareRobotPermissions();}
            else if(action==='pin'){window.AndroidBridge.openPinSettings();}
            else if(action==='change-pin'){window.AndroidBridge.changeOperatorPin();}
            else if(action==='reset-pin'){window.AndroidBridge.resetOperatorPin();}
            else if(action==='battery-settings'){window.AndroidBridge.openBatteryOptimizationSettings();}
            else if(action==='manage'){window.AndroidBridge.openManagement();}
            else if(action==='start-robot'||action==='toggle-robot'){if(configuration.mode!=='ROBOT'){showToast('Ce téléphone est Remote. Passez d’abord ce compte en Robot depuis Gérer.');return;}if(configuration.robot_enabled){if(window.confirm('Arrêter ce Robot ? Les commandes resteront au serveur jusqu’à sa reprise.'))window.AndroidBridge.stopRobot();}else{window.AndroidBridge.startRobot();}window.setTimeout(refreshConfiguration,700);}
            else if(action==='synchronize'){if(byId('birSyncState'))byId('birSyncState').textContent='Synchronisation en cours…';if(window.AndroidBridge.synchronizeNow){window.AndroidBridge.synchronizeNow();}refresh(true);requestDashboard(true);showToast('Synchronisation relancée sans créer de transaction.');}
            else if(action==='server-health'){byId('serverHealthStatus').textContent='Vérification HTTPS et D1 en cours…';window.AndroidBridge.checkServerHealth();}
            else if(action==='refresh-dashboard'){if(window.AndroidBridge.refreshDashboardLive){window.AndroidBridge.refreshDashboardLive();showToast('Actualisation intelligente : preuves récentes réutilisées, USSD seulement si nécessaire.');}else{window.AndroidBridge.loadDashboard();}}
            else if(action==='go-test'){showTab('flux');var test=document.querySelector('button[data-action="test-number"]');if(test&&test.parentNode&&test.parentNode.scrollIntoView){test.parentNode.scrollIntoView(true);}}
        }catch(error){showToast('Action Android indisponible : '+error.message);}
    }
    function refreshConfiguration(){
        if(!bridge())return;try{var fresh=JSON.parse(window.AndroidBridge.getConfiguration()||'{}');fresh.role=normalizeRole(fresh);if(configuration.official_node_code)fresh.official_node_code=configuration.official_node_code;configuration=fresh;renderConfigurationState();applyRoleFieldSemantics();updateModuleData();}catch(ignored){}
    }
    function displayNodeCode(raw){return configuration.official_node_code&&String(raw||'')===String(configuration.node_code||'')?configuration.official_node_code:(raw||'—');}
    function renderConfigurationState(){
        var accountPhone=configuration.phone_number||'Numéro non renseigné',official=displayNodeCode(configuration.node_code),robot=byId('robotState'),rb,rs;
        if(byId('nodeCode'))byId('nodeCode').textContent=official||'Nœud non configuré';
        if(byId('nodeMeta'))byId('nodeMeta').textContent=(configuration.role||'—')+' • '+(configuration.mode||'—')+' • SIM '+((configuration.sim_slot||0)+1)+' • '+accountPhone;
        if(byId('birAccountRole'))byId('birAccountRole').textContent=configuration.role||'COMPTE';
        if(byId('birAccountNode'))byId('birAccountNode').textContent=official||'—';
        if(byId('birAccountPhone'))byId('birAccountPhone').textContent='SIM '+((configuration.sim_slot||0)+1)+' • '+accountPhone;
        var waiting=configuration.mode==='ROBOT'&&configuration.robot_enabled&&(!configuration.sim_verified||!configuration.pin_configured||!configuration.accessibility_enabled||configuration.accessibility_connected===false),statusText=configuration.robot_enabled?(waiting?'ROBOT EN ATTENTE':'ROBOT ACTIF'):'ROBOT ARRÊTÉ';
        if(robot){robot.className='bir-robot-control '+(configuration.robot_enabled?'robot-on':'robot-off');rb=robot.querySelector?robot.querySelector('b'):null;rs=robot.querySelector?robot.querySelector('small'):null;if(rb)rb.textContent=configuration.mode==='ROBOT'?statusText:'MODE REMOTE';if(rs)rs.textContent=configuration.mode==='ROBOT'?(configuration.robot_enabled?(waiting?'Reprise automatique • toucher':'Touchez pour arrêter'):'Touchez pour démarrer'):'Robot distant piloté';}
        if(byId('birQuickRobotState'))byId('birQuickRobotState').textContent=configuration.mode==='ROBOT'?(configuration.robot_enabled?(waiting?'En attente — reprise auto':'Actif — toucher pour arrêter'):'Arrêté — toucher pour démarrer'):'Remote — suivre le Robot';
        if(byId('birPermissionState'))byId('birPermissionState').textContent=configuration.mode==='ROBOT'?(configuration.accessibility_enabled?(configuration.accessibility_connected===false?'Activée, service en reprise':'Accessibilité active'):'À activer'):'Réglages du Remote';
        var health=byId('birRobotHealth'),buttons=health&&health.querySelectorAll?health.querySelectorAll('button'):[];
        if(health)health.className='bir-health-grid'+(configuration.mode==='ROBOT'?'':' bir-health-remote');
        if(buttons&&buttons.length>=3){if(configuration.mode==='ROBOT'){buttons[0].setAttribute('data-native-action','permissions');buttons[0].innerHTML='<b>✓ Autorisations</b><small id="birPermissionState2">'+escapeHtml(configuration.accessibility_enabled?'Accessibilité '+(configuration.accessibility_connected===false?'en reprise':'active'):'À activer')+'</small>';buttons[1].setAttribute('data-native-action','toggle-robot');buttons[1].innerHTML='<b>∞ Robot</b><small>'+escapeHtml(configuration.robot_enabled?(waiting?'Reprise automatique':'Actif'):'Démarrer')+'</small>';buttons[2].setAttribute('data-native-action','battery-settings');buttons[2].innerHTML='<b>▣ Batterie</b><small>Sans restriction</small>';}else{buttons[0].setAttribute('data-native-action','synchronize');buttons[0].innerHTML='<b>↻ Synchroniser</b><small>Commandes & preuves</small>';buttons[1].setAttribute('data-native-action','accounts');buttons[1].innerHTML='<b>∞ Comptes</b><small>Remote / Robots</small>';buttons[2].setAttribute('data-native-action','manage');buttons[2].innerHTML='<b>⚙ Réglages</b><small>Compte & sécurité</small>';}}
        var fatal=byId('fatalNotice');if(fatal){if(configuration.pin_blocked){fatal.textContent='PIN BLOQUÉ : touchez ici pour corriger le PIN local.';fatal.className='notice notice-danger';fatal.onclick=function(){runNativeAction('pin');};}else if(configuration.mode==='ROBOT'&&!configuration.sim_verified){fatal.textContent='SIM NON VÉRIFIÉE : touchez ici pour vérifier / lier la SIM. Le Robot reste logiquement actif et reprendra automatiquement.';fatal.className='notice notice-danger';fatal.onclick=function(){runNativeAction('verify-sim');};}else{fatal.textContent='';fatal.className='notice notice-danger hidden';fatal.onclick=null;}}
    }
    function applyRoleFieldSemantics(){
        var childLabel=byId('childNodeLabel'),child=byId('childNode'),balLabel=byId('balanceChildNodeLabel'),bal=byId('balanceChildNode'),admLabel=byId('adminChildNodeLabel'),adm=byId('adminChildNode'),commLabel=byId('commissionChildLabel'),comm=byId('commission-child');
        if(configuration.role==='DAE'){
            if(byId('commissionControlCard'))byId('commissionControlCard').className='panel module-card';
            if(childLabel)childLabel.textContent='Code du DSM';if(child)child.placeholder='Ex. DSM1';if(balLabel)balLabel.textContent='Code du DSM';if(bal)bal.placeholder='Ex. DSM1';if(admLabel)admLabel.textContent='Code du DSM';if(adm)adm.placeholder='Ex. DSM1';if(commLabel)commLabel.textContent='DSM direct';if(comm)comm.placeholder='Ex. DSM1';
            if(byId('childBalanceTitle'))byId('childBalanceTitle').textContent='Consulter le solde d’un DSM';if(byId('commissionControlTitle'))byId('commissionControlTitle').textContent='Commissions de mes DSM';
        }else if(configuration.role==='DSM'){
            if(byId('commissionControlCard'))byId('commissionControlCard').className='panel module-card';
            if(childLabel)childLabel.textContent='Code du PoS';if(child)child.placeholder='Ex. POS1';if(balLabel)balLabel.textContent='Code du PoS';if(bal)bal.placeholder='Ex. POS1';if(admLabel)admLabel.textContent='Code du PoS';if(adm)adm.placeholder='Ex. POS1';if(commLabel)commLabel.textContent='PoS direct';if(comm)comm.placeholder='Ex. POS1';
            if(byId('childBalanceTitle'))byId('childBalanceTitle').textContent='Consulter le solde d’un PoS';if(byId('requestSupplyTitle'))byId('requestSupplyTitle').textContent='Demander à mon DAE';if(byId('requestSupplyHint'))byId('requestSupplyHint').textContent='Votre DAE décide du taux et son Robot approvisionnera votre SIM.';if(byId('commissionControlTitle'))byId('commissionControlTitle').textContent='Commissions de mes PoS';
        }else if(configuration.role==='POS'){
            if(byId('requestSupplyTitle'))byId('requestSupplyTitle').textContent='Demander à mon DSM';if(byId('requestSupplyHint'))byId('requestSupplyHint').textContent='Votre DSM direct décide du taux et son Robot approvisionnera votre SIM.';
        }
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
    function initializeInputErgonomics(){
        each('input[data-digits-only]',function(input){input.addEventListener('input',function(){var max=Number(input.getAttribute('data-digits-only')||0),clean=input.value.replace(/\D/g,'');if(max>0){clean=clean.slice(0,max);}if(input.value!==clean){input.value=clean;}clearFieldIssue(input);});});
        each('input[data-uppercase]',function(input){input.addEventListener('input',function(){var upper=input.value.toUpperCase();if(input.value!==upper){input.value=upper;}clearFieldIssue(input);});});
        each('input',function(input){input.addEventListener('input',function(){clearFieldIssue(input);});});
    }
    function clearFieldIssue(input){if(input&&input.removeAttribute){input.removeAttribute('aria-invalid');}}
    function fieldIssue(id,message){var input=byId(id);showToast(message);if(!input){return;}if(input.setAttribute){input.setAttribute('aria-invalid','true');}if(input.scrollIntoView){input.scrollIntoView(true);}window.setTimeout(function(){try{input.focus();}catch(ignored){}},80);}
    function snapshotForm(type){return {type:type,node:byId('childNode')?byId('childNode').value:'',phone:byId('retailPhone')?byId('retailPhone').value:'',requestAmount:byId('requestSupplyAmount')?byId('requestSupplyAmount').value:'',childAmount:byId('childAmount')?byId('childAmount').value:'',retailAmount:byId('retailAmount')?byId('retailAmount').value:'',transactionId:byId('transactionId')?byId('transactionId').value:''};}
    function clearSubmittedFields(submitted){if(!submitted){return;}if(submitted.type==='REQUEST_SUPPLY'&&byId('requestSupplyAmount')&&byId('requestSupplyAmount').value===submitted.requestAmount){byId('requestSupplyAmount').value='';}else if(submitted.type==='SUPPLY_CHILD'){if(byId('childAmount')&&byId('childAmount').value===submitted.childAmount){byId('childAmount').value='';}}else if(submitted.type==='RETAIL_SALE'){if(byId('retailPhone')&&byId('retailPhone').value===submitted.phone){byId('retailPhone').value='';}if(byId('retailAmount')&&byId('retailAmount').value===submitted.retailAmount){byId('retailAmount').value='';}}else if(submitted.type==='TRANSACTION_DETAILS'&&byId('transactionId')&&byId('transactionId').value===submitted.transactionId){byId('transactionId').value='';}}
    function execute(action){
        if(!bridge()){return;}if(actionInFlight){showToast('Une commande est déjà en préparation. Attendez sa confirmation ou son annulation.');return;}var type='',node='',phone='',amount='',argument='';
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
        if(type==='REQUEST_SUPPLY'&&!/^[1-9]\d{0,8}$/.test(amount)){fieldIssue('requestSupplyAmount','Saisissez un montant entier valide.');return;}
        if(type==='SUPPLY_CHILD'&&!node){fieldIssue('childNode','Saisissez le code du nœud enfant.');return;}
        if(type==='SUPPLY_CHILD'&&!/^[1-9]\d{0,8}$/.test(amount)){fieldIssue('childAmount','Saisissez un montant entier valide.');return;}
        if(type==='CHILD_BALANCE'&&!node){fieldIssue('balanceChildNode','Saisissez le code du nœud enfant.');return;}
        if((type==='INIT_CHILD_PIN_RESET'||type==='SUSPEND_CHILD'||type==='REACTIVATE_CHILD'||type==='FREEZE_CHILD'||type==='REACTIVATE_FROZEN_CHILD')&&!node){fieldIssue('adminChildNode','Saisissez le code du nœud enfant à administrer.');return;}
        if(type==='RETAIL_SALE'&&!/^\d{9}$/.test(phone)){fieldIssue('retailPhone','Le numéro client doit avoir 9 chiffres.');return;}
        if(type==='RETAIL_SALE'&&!/^[1-9]\d{0,8}$/.test(amount)){fieldIssue('retailAmount','Saisissez un montant entier valide.');return;}
        if(type==='TRANSACTION_DETAILS'&&!/^[A-Za-z0-9_-]{6,64}$/.test(argument)){fieldIssue('transactionId','Saisissez un identifiant Camtel valide.');return;}
        pendingPreview={type:type,node:node,phone:phone,amount:amount,argument:argument,request_id:requestId(),capacity_check_id:'',commission_rate_bps:''};
        submittedForm=snapshotForm(type);setBusy(true);clearActionError();
        if(type==='REQUEST_SUPPLY'){
            capacityPolls=0;showActionProgress('Lecture du solde disponible du supérieur avant confirmation…');
            window.AndroidBridge.checkPurchaseCapacity(amount,pendingPreview.request_id);
            return;
        }
        if(type==='TEST_NUMBER'||type==='CHECK_BALANCE'||type==='LAST_TRANSACTIONS'||type==='TRANSACTION_DETAILS'||type==='CHILD_BALANCE'){
            window.AndroidBridge.createCommand(type,node,phone,amount,pendingPreview.request_id,'','',argument,'');
            return;
        }
        showActionProgress('Vérification des numéros officiels et de la filiation…');
        window.AndroidBridge.previewCommand(type,node,phone,amount,pendingPreview.request_id,'',argument,pendingPreview.commission_rate_bps||'');
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
            var rate=Number(capacity.commission_rate_bps||0), maxBase=Number(capacity.maximum_base_amount||0), available=Number(capacity.available_balance||0);
            if(maxBase<=0&&available>0){maxBase=Math.floor(available*10000/(10000+rate));while(maxBase>0&&(maxBase+Math.floor(maxBase*rate/10000))>available){maxBase-=1;}}
            var maxCommission=Math.floor(maxBase*rate/10000), maxTotal=maxBase+maxCommission;
            showActionError({code:'SOLDE_SUPÉRIEUR_INSUFFISANT',message:'Vous ne pouvez pas commander ce montant. Solde actuellement disponible : '+formatMoney(available)+' FCFA. Avec votre taux '+String(rate/100).replace('.',',')+' %, le montant commandable maximum est '+formatMoney(maxBase)+' FCFA + '+formatMoney(maxCommission)+' FCFA de commission = '+formatMoney(maxTotal)+' FCFA à recevoir. Aucune somme n’est réservée tant que vous n’avez pas confirmé : un autre DSM/PoS peut confirmer avant vous et modifier le disponible.'});
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
            pendingPreview.amount,pendingPreview.request_id,pendingPreview.capacity_check_id,pendingPreview.argument,'');
    }
    function handlePreview(data){
        var preview,fingerprint;
        if(!pendingPreview){setBusy(false);return;}
        if(data&&data.error){setBusy(false);pendingPreview=null;closeFinancialModal();showActionError(data);return;}
        preview=data&&data.preview||{};fingerprint=String(preview.confirmation_fingerprint||'');
        if(!fingerprint){setBusy(false);pendingPreview=null;showActionError({code:'PREVIEW_INCOMPLETE',message:'Le serveur n’a pas certifié les numéros de cette commande.'});return;}
        clearActionError();
        if(preview.robot_ready===false){showActionProgress((preview.robot_status||'ROBOT_OFFLINE')+' — '+(preview.robot_message||'Le Robot ne communique pas encore. La commande peut être mise en attente.'));}
        if(preview.dangerous){
            if(!confirmDangerous(preview)){setBusy(false);pendingPreview=null;submittedForm=null;showToast('Commande annulée avant toute composition.');return;}
            transmitPreview(preview);return;
        }
        openFinancialModal(preview);
    }
    function confirmDangerous(preview){
        return window.confirm('COMMANDE CAMTEL SENSIBLE\n\n'+(preview.operation_label||preview.operation||'Maintenance SIM')+'\n\nCOMPTE EXÉCUTEUR : '+(preview.executor_official_node_code||preview.executor_node_code||'—')+' — '+(preview.executor_phone||'—')+'\nCIBLE : '+(preview.target_official_node_code||preview.target_node_code||preview.executor_official_node_code||preview.executor_node_code||'—')+' — '+(preview.target_phone||preview.executor_phone||'—')+'\n\nCette commande peut suspendre ou geler une SIM. Vérifiez la cible avant de confirmer. Le PIN reste uniquement sur le Robot.\n\nCONFIRMER CETTE COMMANDE ?');
    }
    function openFinancialModal(preview){
        var modal=byId('financialConfirmModal'),facts=byId('financialConfirmFacts'),editor=byId('financialRateEditor'),input=byId('financialRateInput'),advice=byId('financialConfirmAdvice');
        var title=preview.operation==='RETAIL_TRANSFER'?'VENTE À UN CLIENT':'TRANSFERT DE CRÉDIT';
        var supplier=(preview.executor_official_node_code||preview.executor_node_code||'FOURNISSEUR')+' — '+(preview.executor_phone||'numéro absent');
        var beneficiary=(preview.target_official_node_code||preview.target_node_code||'CLIENT')+' — '+(preview.target_phone||'numéro absent');
        var base=Number(preview.requested_base_amount||preview.amount||0),commission=Number(preview.commission_amount||0),rateBps=Number(preview.commission_rate_bps||0),rate=rateBps/100;
        financialPreview=preview;if(byId('financialConfirmTitle'))byId('financialConfirmTitle').textContent=title;
        facts.innerHTML='<b>FOURNISSEUR :</b> '+escapeHtml(supplier)+'<br><b>BÉNÉFICIAIRE :</b> '+escapeHtml(beneficiary)+(preview.operation==='DISTRIBUTION_TRANSFER'?'<br><b>MONTANT DE BASE :</b> '+formatMoney(base)+' FCFA<br><b>COMMISSION ('+String(rate).replace('.',',')+' %) :</b> '+formatMoney(commission)+' FCFA<br><b>TOTAL À RECEVOIR :</b> '+formatMoney(preview.amount)+' FCFA':'<br><b>MONTANT :</b> '+formatMoney(preview.amount)+' FCFA');
        if(preview.request_type==='SUPPLY_CHILD'||preview.commission_decider==='REQUESTER_PARENT'){
            editor.className='bir-rate-editor';input.value=String(rate).replace(',','.');advice.textContent='Vous êtes le supérieur qui approvisionne cet enfant : ce taux est votre décision. Vous pouvez le valider ou le modifier pour cette transaction uniquement.';
        }else if(preview.request_type==='REQUEST_SUPPLY'||preview.commission_decider==='SUPERIOR_PARENT'){
            editor.className='bir-rate-editor hidden';advice.textContent='Ce taux est fixé par votre supérieur direct. S’il ne vous convient pas, annulez la demande et contactez-le avant de recommencer.';
        }else{editor.className='bir-rate-editor hidden';advice.textContent='Vérifiez le fournisseur, le bénéficiaire et le montant avant de confirmer.';}
        byId('financialConfirmCancel').onclick=function(){closeFinancialModal();setBusy(false);pendingPreview=null;submittedForm=null;showToast('Transaction annulée avant toute composition.');};
        byId('financialConfirmOk').onclick=function(){
            if(!financialPreview||!pendingPreview)return;
            if(financialPreview.request_type==='SUPPLY_CHILD'||financialPreview.commission_decider==='REQUESTER_PARENT'){
                var rateValue=Number(String(input.value||'').replace(',','.')),newBps=Math.round(rateValue*100);
                if(!isFinite(rateValue)||rateValue<0||rateValue>50){fieldIssue('financialRateInput','Le taux doit être compris entre 0 et 50 %.');return;}
                if(newBps!==Number(financialPreview.commission_rate_bps||0)){
                    pendingPreview.commission_rate_bps=String(newBps);closeFinancialModal();showActionProgress('Recalcul du total avec le taux choisi…');
                    window.AndroidBridge.previewCommand(pendingPreview.type,pendingPreview.node,pendingPreview.phone,pendingPreview.amount,pendingPreview.request_id,pendingPreview.capacity_check_id,pendingPreview.argument,pendingPreview.commission_rate_bps);return;
                }
            }
            var finalPreview=financialPreview;closeFinancialModal();transmitPreview(finalPreview);
        };
        modal.className='bir-modal';
    }
    function closeFinancialModal(){var modal=byId('financialConfirmModal');if(modal)modal.className='bir-modal hidden';financialPreview=null;}
    function transmitPreview(preview){
        var fingerprint=String(preview.confirmation_fingerprint||'');showActionProgress('Commande confirmée. Transmission au Robot de la SIM fournisseur…');
        window.AndroidBridge.createCommand(pendingPreview.type,pendingPreview.node,pendingPreview.phone,pendingPreview.amount,pendingPreview.request_id,fingerprint,pendingPreview.capacity_check_id,pendingPreview.argument,pendingPreview.commission_rate_bps||'');
    }
    function formatMoney(value){return String(value).replace(/\B(?=(\d{3})+(?!\d))/g,' ');}
    function hasPendingCommands(){var i;for(i=0;i<commands.length;i+=1){if(!TERMINAL[commands[i].state]){return true;}}return false;}
    function clearPollingTimers(){if(commandPollTimer){window.clearTimeout(commandPollTimer);commandPollTimer=null;}if(dashboardPollTimer){window.clearTimeout(dashboardPollTimer);dashboardPollTimer=null;}}
    function scheduleCommandPoll(delay){
        if(commandPollTimer){window.clearTimeout(commandPollTimer);commandPollTimer=null;}
        if(document.visibilityState==='hidden'||!hasPendingCommands()){return;}
        commandPollTimer=window.setTimeout(function(){commandPollTimer=null;refresh(false);},Math.max(250,delay||5000));
    }
    function refresh(forceAll){
        var pending=[],i,start,count=0,max=forceAll?999:4;
        if(!bridge()||document.visibilityState==='hidden'){return;}
        for(i=0;i<commands.length;i+=1){if(!TERMINAL[commands[i].state]){pending.push(commands[i]);}}
        if(!pending.length){updateTabAttention();return;}
        start=commandPollCursor%pending.length;
        for(i=0;i<pending.length&&count<max;i+=1){
            window.AndroidBridge.getCommandStatus(pending[(start+i)%pending.length].public_id);count+=1;
        }
        commandPollCursor=(start+count)%pending.length;
        updateTabAttention();scheduleCommandPoll(5000);
    }
    function dashboardRelevant(){return true;}
    function requestDashboard(force){
        var now=new Date().getTime();
        if(!bridge()||document.visibilityState==='hidden'){return;}
        if(!force&&dashboardLoadedAt&&now-dashboardLoadedAt<15000){return;}
        try{window.AndroidBridge.loadDashboard();dashboardLoadedAt=now;}catch(ignored){}
    }
    function scheduleDashboardPoll(){
        if(dashboardPollTimer){window.clearTimeout(dashboardPollTimer);dashboardPollTimer=null;}
        if(document.visibilityState==='hidden'||!dashboardRelevant()){return;}
        dashboardPollTimer=window.setTimeout(function(){dashboardPollTimer=null;requestDashboard(false);scheduleDashboardPoll();},60000);
    }
    function upsert(command){var i,index=-1,key;for(i=0;i<commands.length;i+=1){if(commands[i].public_id===command.public_id){index=i;break;}}if(index<0){commands.unshift(command);}else{for(key in command){if(Object.prototype.hasOwnProperty.call(command,key)){commands[index][key]=command[key];}}}commands=commands.slice(0,20);localStorage.setItem(storageKey(),JSON.stringify(commands));updateTabAttention();if(hasPendingCommands()){scheduleCommandPoll(5000);}}
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
        if(byId('birActivityLine')){byId('birActivityLine').textContent=last?((labels[last.state]||last.state||'Commande')+' • '+(last.operation||'opération')+' • '+formatTime(last.updated_at||last.created_at||'')):'Aucune commande locale récente.';}
        if(byId('birActivityDetail')){byId('birActivityDetail').textContent=last?('Dernière activité : '+(labels[last.state]||last.state||'Commande')+' • '+(last.operation||'opération')+' • '+formatTime(last.updated_at||last.created_at||'')):'Aucune activité locale récente. Les preuves Camtel et diagnostics restent disponibles ci-dessous.';}
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
        else if(pending){support=String(pending)+' commande(s) non terminale(s) à suivre. Utilisez Synchroniser si un résultat tarde, sans créer de transaction de déblocage.';}
        byId('supportStatus').textContent=support;updateTabAttention();
    }
    function nodeCard(n){
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
        var nodes=dashboard&&dashboard.nodes||[],html='',fleet='',i,n,own=null,known=0,byParent={},direct=[],children=[],byCode={},raw,par;
        if(dashboard&&dashboard.viewer_identity&&dashboard.viewer_identity.node_code){configuration.official_node_code=dashboard.viewer_identity.node_code;renderConfigurationState();}
        for(i=0;i<nodes.length;i+=1){n=nodes[i];raw=n.node_code_raw||n.node_code;par=n.parent_node_code_raw||n.parent_node_code||'';n.node_code_raw=raw;n.parent_node_code_raw=par;byCode[raw]=n;if(raw===configuration.node_code){own=n;}if(n.balance!==null&&typeof n.balance!=='undefined'){known+=1;}if(!byParent[par]){byParent[par]=[];}byParent[par].push(n);}
        function officialFor(item){var r=item.node_code_raw||item.node_code,p=item.parent_node_code_raw||item.parent_node_code||'',parent;if(r===configuration.node_code&&configuration.official_node_code)return configuration.official_node_code;if(item.role==='DAE'||r.indexOf('_')>=0)return r;if(item.role==='DSM')return p?r+'_'+p:r;if(item.role==='POS'){parent=byCode[p];if(parent){return r+'_'+officialFor(parent);}return r;}return r;}
        for(i=0;i<nodes.length;i+=1){nodes[i].node_code=officialFor(nodes[i]);}
        if(own){html+=nodeCard(own);fleet+=fleetCard(own);}
        direct=byParent[configuration.node_code]||[];
        if(configuration.role==='DAE'){
            for(i=0;i<direct.length;i+=1){n=direct[i];if(n.role!=='DSM'){continue;}children=byParent[n.node_code_raw||n.node_code]||[];html+='<details class="panel" open><summary><strong>'+escapeHtml(n.node_code)+'</strong> — DSM direct • '+String(children.length)+' PoS</summary>'+nodeCard(n)+(children.length?'<details><summary>Afficher / masquer les PoS de '+escapeHtml(n.node_code)+'</summary>'+children.map(nodeCard).join('')+'</details>':'')+'</details>';fleet+='<details><summary>'+escapeHtml(n.node_code)+' • DSM</summary>'+fleetCard(n)+children.map(fleetCard).join('')+'</details>';}
        }else if(configuration.role==='DSM'){
            for(i=0;i<direct.length;i+=1){if(direct[i].role==='POS'){html+=nodeCard(direct[i]);fleet+=fleetCard(direct[i]);}}
        }
        byId('networkList').innerHTML=html||'<p class="muted">Aucun nœud visible dans votre périmètre.</p>';
        byId('fleetNetworkList').innerHTML=fleet||'<p class="muted">Aucun terminal rattaché.</p>';
        byId('fleetNetworkTitle').textContent=configuration.role==='DAE'?'Mes DSM et leurs PoS — '+String(nodes.length)+' nœud(s)':configuration.role==='DSM'?'Mes PoS — '+String(nodes.length)+' nœud(s)':'Mon terminal';
        byId('ownBalance').textContent=own&&own.balance!==null?formatMoney(own.balance)+' FCFA':'À actualiser';
        if(byId('birCamtelBalance')){byId('birCamtelBalance').textContent=own&&own.balance!==null?formatMoney(own.balance):'À actualiser';}
        if(byId('birAvailableBalance')){byId('birAvailableBalance').textContent=own&&own.available_balance!==null&&typeof own.available_balance!=='undefined'?formatMoney(own.available_balance)+' F':'—';}
        if(byId('birReservedBalance')){byId('birReservedBalance').textContent=own?formatMoney(Number(own.reserved_amount||0))+' F':'—';}
        if(byId('birThirdMetricLabel')&&byId('birThirdMetricValue')){
            if(own&&(configuration.role==='DAE'||configuration.role==='DSM')){byId('birThirdMetricLabel').textContent='Composante commission';byId('birThirdMetricValue').textContent=formatMoney(Number(own.commission_component_balance||0))+' F';}
            else{byId('birThirdMetricLabel').textContent='Commandes réussies';byId('birThirdMetricValue').textContent=byId('metricSuccessCount')?byId('metricSuccessCount').textContent:'0';}
        }
        if(byId('birBalanceFreshness')){byId('birBalanceFreshness').textContent=own&&own.observed_at?((own.balance_quality==='EXACT'?'Confirmé Camtel':'Estimé')+' • '+formatTime(own.operator_event_at||own.observed_at)):'Aucune lecture Camtel horodatée.';}
        byId('balanceFreshness').textContent=own&&own.observed_at
            ? ('Dernière observation : '+formatTime(own.operator_event_at||own.observed_at)+' • '+(own.balance_quality==='EXACT'?'confirmé Camtel':'estimé')+' • '+(own.evidence_kind||own.balance_source||'source inconnue')
                +(own.available_balance!==null&&typeof own.available_balance!=='undefined'?' • disponible '+formatMoney(own.available_balance)+' FCFA':'')
                +(own.balance_reusable?' • réutilisable / partageable sans nouvel USSD':' • à recertifier avant finance'))
            :'Aucune lecture Camtel horodatée.';
    }
    function surfaceCommandResult(command){
        if(!command||!command.result_message)return;var op=String(command.operation||''),title='Résultat Camtel';
        if(op==='BALANCE_CHILD')title='Solde de '+(command.target_node_code||'l’enfant');else if(op==='BALANCE_OWN')title='Solde Camtel';else if(op==='LAST_TRANSACTIONS')title='5 dernières transactions';else if(op==='TRANSACTION_DETAILS')title='Détail de transaction';
        if(op==='BALANCE_CHILD'||op==='BALANCE_OWN'||op==='LAST_TRANSACTIONS'||op==='TRANSACTION_DETAILS'||op==='TEST_NUMBER'){
            byId('birInfoResultTitle').textContent=title;byId('birInfoResultBody').textContent=command.result_message;byId('birInfoResult').className='bir-info-result';showToast(title+' reçu et affiché.');
        }
    }
    function cancelRemote(commandId){if(!bridge()||!window.confirm('Annuler cette commande encore en attente ?')){return;}window.AndroidBridge.cancelCommand(commandId);}
    function formatTime(value){var d=new Date(value);if(isNaN(d.getTime())){return String(value);}return two(d.getDate())+'/'+two(d.getMonth()+1)+'/'+d.getFullYear()+' à '+two(d.getHours())+':'+two(d.getMinutes())+':'+two(d.getSeconds());}
    function two(value){return value<10?'0'+value:String(value);}
    function requestId(){return 'req_'+new Date().getTime()+'_'+Math.random().toString(36).slice(2,14);}
    function setBusy(value){actionInFlight=!!value;each('button[data-action]',function(button){button.disabled=value;if(button.setAttribute){button.setAttribute('aria-busy',value?'true':'false');}});}
    function showActionProgress(message){var notice=byId('actionNotice');notice.textContent=message;notice.className='notice';}
    function showActionError(data){var code=String(data&&data.code||'ACTION_FAILED'),message=String(data&&data.message||'Action impossible.'),notice=byId('actionNotice');notice.textContent=code+' — '+message;notice.className='notice notice-danger';showToast(code+' — '+message);}
    function clearActionError(){var notice=byId('actionNotice');notice.textContent='';notice.className='notice notice-danger hidden';}
    function showToast(message){var toast=byId('toast');toast.textContent=message;toast.className='toast';window.setTimeout(function(){toast.className='toast hidden';},4000);}
    function escapeHtml(value){var entities={'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'};return String(value).replace(/[&<>'"]/g,function(c){return entities[c];});}
    if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',initialize);}else{initialize();}
}());
