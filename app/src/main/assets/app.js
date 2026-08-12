(function () {
    'use strict';
    var TERMINAL = {SUCCEEDED:true,FAILED:true,UNKNOWN:true,BLOCKED:true,CANCELLED:true};
    var labels = {PENDING:'En attente',LEASED:'Réservée au Robot',DIALING:'Composition USSD',AWAITING_PIN:'Vérification du pop-up',PIN_SUBMITTED:'PIN validé',AWAITING_RESULT:'Confirmation Camtel',SUCCEEDED:'Réussie',FAILED:'Échec',UNKNOWN:'À vérifier',BLOCKED:'Robot bloqué — PIN',CANCELLED:'Annulée'};
    var configuration = {}, commands = [], pendingPreview = null;
    function byId(id){return document.getElementById(id);}
    function each(selector,fn){var items=document.querySelectorAll(selector),i;for(i=0;i<items.length;i+=1){fn(items[i]);}}
    function bridge(){return typeof window.AndroidBridge!=='undefined';}
    window.BlueMagicNative={
        onCommandPreview:function(data){handlePreview(data);},
        onCommandCreated:function(data){setBusy(false);pendingPreview=null;if(data.error){showActionError(data);return;}clearActionError();var command=data.command||{};if(!command.public_id){showActionError({code:'INVALID_RESPONSE',message:'Réponse serveur incomplète.'});return;}upsert(command);render();showToast(data.duplicate?'Cette demande existait déjà.':'Commande créée et transmise au Robot exact.');},
        onCommandStatus:function(data){if(data&&data.command){upsert(data.command);render();}},
        onCommandCancelled:function(data){if(data.error){showToast(data.message||'Annulation impossible.');return;}if(data.command){upsert(data.command);render();showToast('Commande annulée.');}}
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
        if(configuration.role==='POS'){byId('retailCard').className='panel command-card';}
        each('button[data-action]',function(button){button.onclick=function(){execute(button.getAttribute('data-action'));};});
        byId('refreshCommands').onclick=refresh;
        document.addEventListener('focusin',function(event){if(event.target&&event.target.tagName==='INPUT'){try{window.AndroidBridge.setFormEditing(true);}catch(ignored){}}});
        document.addEventListener('focusout',function(){window.setTimeout(function(){if(!document.activeElement||document.activeElement.tagName!=='INPUT'){try{window.AndroidBridge.setFormEditing(false);}catch(ignored){}}},180);});
        render();refresh();window.setInterval(refresh,15000);
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
        if(!bridge()){return;}var type='',node='',phone='',amount='';
        if(action==='request-supply'){type='REQUEST_SUPPLY';amount=byId('requestSupplyAmount').value.replace(/^\s+|\s+$/g,'');}
        else if(action==='supply-child'){type='SUPPLY_CHILD';node=byId('childNode').value.replace(/^\s+|\s+$/g,'').toUpperCase();amount=byId('childAmount').value.replace(/^\s+|\s+$/g,'');}
        else if(action==='retail-sale'){type='RETAIL_SALE';phone=byId('retailPhone').value.replace(/\D/g,'');amount=byId('retailAmount').value.replace(/^\s+|\s+$/g,'');}
        else{type='TEST_NUMBER';}
        if(type!=='TEST_NUMBER'&&!/^[1-9]\d{0,8}$/.test(amount)){showToast('Saisissez un montant entier valide.');return;}
        if(type==='SUPPLY_CHILD'&&!node){showToast('Saisissez le code du nœud enfant.');return;}
        if(type==='RETAIL_SALE'&&!/^\d{9}$/.test(phone)){showToast('Le numéro client doit avoir 9 chiffres.');return;}
        pendingPreview={type:type,node:node,phone:phone,amount:amount,request_id:requestId()};
        setBusy(true);clearActionError();
        if(type==='TEST_NUMBER'){
            window.AndroidBridge.createCommand(type,node,phone,amount,pendingPreview.request_id,'');
            return;
        }
        showActionProgress('Vérification des numéros officiels et de la filiation…');
        window.AndroidBridge.previewCommand(type,node,phone,amount,pendingPreview.request_id);
    }
    function handlePreview(data){
        var preview,fingerprint;
        if(!pendingPreview){setBusy(false);return;}
        if(data&&data.error){setBusy(false);pendingPreview=null;showActionError(data);return;}
        preview=data&&data.preview||{};fingerprint=String(preview.confirmation_fingerprint||'');
        if(!fingerprint){setBusy(false);pendingPreview=null;showActionError({code:'PREVIEW_INCOMPLETE',message:'Le serveur n’a pas certifié les numéros de cette commande.'});return;}
        clearActionError();
        if(!confirmFinancial(preview)){setBusy(false);pendingPreview=null;showToast('Commande annulée avant toute composition.');return;}
        showActionProgress('Commande confirmée. Transmission au Robot de la SIM fournisseur…');
        window.AndroidBridge.createCommand(pendingPreview.type,pendingPreview.node,pendingPreview.phone,
            pendingPreview.amount,pendingPreview.request_id,fingerprint);
    }
    function confirmFinancial(preview){
        var title=preview.operation==='RETAIL_TRANSFER'?'VENTE À UN CLIENT':'TRANSFERT DE CRÉDIT';
        var supplier=(preview.executor_node_code||'FOURNISSEUR')+' — '+(preview.executor_phone||'numéro absent');
        var beneficiary=(preview.target_node_code||'CLIENT')+' — '+(preview.target_phone||'numéro absent');
        return window.confirm('CONFIRMATION 1 SUR 2\n\n'+title+'\n\nFOURNISSEUR : '+supplier+'\nBÉNÉFICIAIRE : '+beneficiary+'\nMONTANT : '+formatMoney(preview.amount)+' FCFA\n\nConfirmez uniquement si les deux numéros et le montant sont exacts. Après confirmation, le Robot composera la commande. Blue Magic contrôlera ensuite les mêmes données dans le pop-up Camtel avant d’insérer le PIN.\n\nCONFIRMER CETTE TRANSACTION ?');
    }
    function formatMoney(value){return String(value).replace(/\B(?=(\d{3})+(?!\d))/g,' ');}
    function refresh(){var i;if(!bridge()){return;}for(i=0;i<commands.length;i+=1){if(!TERMINAL[commands[i].state]){window.AndroidBridge.getCommandStatus(commands[i].public_id);}}}
    function upsert(command){var i,index=-1,key;for(i=0;i<commands.length;i+=1){if(commands[i].public_id===command.public_id){index=i;break;}}if(index<0){commands.unshift(command);}else{for(key in command){if(Object.prototype.hasOwnProperty.call(command,key)){commands[index][key]=command[key];}}}commands=commands.slice(0,20);localStorage.setItem(storageKey(),JSON.stringify(commands));}
    function load(){try{var value=JSON.parse(localStorage.getItem(storageKey())||'[]');return Object.prototype.toString.call(value)==='[object Array]'?value:[];}catch(ignored){return [];}}
    function storageKey(){return 'blue_magic_embedded_commands_'+(configuration.profile_id||configuration.node_code||'default');}
    function render(){var html='',i,c,state,detail,time;if(!commands.length){byId('commandList').innerHTML='<p class="muted">Aucune commande sur ce téléphone.</p>';return;}for(i=0;i<commands.length;i+=1){c=commands[i];state=escapeHtml(c.state||'PENDING');detail=escapeHtml(c.result_message||c.operation||'Commande');time=c.updated_at||c.created_at||'';html+='<article class="command-item"><div class="command-item-top"><span class="command-id">'+escapeHtml(c.public_id||'')+'</span><span class="command-state state-'+state+'">'+escapeHtml(labels[c.state]||c.state||'—')+'</span></div><div class="command-detail">'+detail+'</div>'+(time?'<div class="command-time">Horodatage : '+escapeHtml(formatTime(time))+'</div>':'')+(c.state==='PENDING'?'<button type="button" class="button-small secondary" data-cancel-command="'+escapeHtml(c.public_id||'')+'">Annuler cette commande</button>':'')+'</article>';}byId('commandList').innerHTML=html;each('button[data-cancel-command]',function(button){button.onclick=function(){cancelRemote(button.getAttribute('data-cancel-command'));};});}
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
