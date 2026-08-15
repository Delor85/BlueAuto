from pathlib import Path


def read(path):
    return Path(path).read_text()


def write(path, text):
    Path(path).write_text(text)


def one(text, old, new, label):
    if old not in text:
        raise SystemExit('missing patch anchor: ' + label)
    return text.replace(old, new, 1)


# -----------------------------------------------------------------------------
# 1) HTML — mobile keyboards, limits, clear semantics, non-numbered dynamic copy.
# -----------------------------------------------------------------------------
p = 'app/src/main/assets/index.html'
s = read(p)
replacements = {
'''            <p class="eyebrow">ONGLET 1 — GRAPHES & RAPPORTS</p>
            <h3>Centre pilote local</h3>
            <p class="muted">Première brique du cahier des charges : synthèse vérifiable des opérations conservées sur ce téléphone. Les consolidations DAE/DSM/PoS seront ajoutées sans modifier le moteur USSD.</p>''':
'''            <p class="eyebrow">PILOTAGE & RAPPORTS</p>
            <h3 id="reportsIntroTitle">Vue utile du compte</h3>
            <p id="reportsIntroText" class="muted">Soldes, activité et opérations sont affichés selon le périmètre réel de votre rôle, sans exposer le PIN Camtel.</p>''',
'''            <label>Montant (FCFA)</label><input id="requestSupplyAmount" type="text" inputmode="numeric" placeholder="Ex. 50000">''':
'''            <label for="requestSupplyAmount">Montant (FCFA)</label><input id="requestSupplyAmount" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="9" autocomplete="off" data-digits-only="9" placeholder="Ex. 50000">''',
'''            <label>Code du DSM/PoS</label><input id="childNode" type="text" autocomplete="off" placeholder="Ex. DSM7 ou POS5">
            <label>Montant (FCFA)</label><input id="childAmount" type="text" inputmode="numeric" placeholder="Ex. 25000">''':
'''            <label for="childNode">Code du DSM/PoS</label><input id="childNode" type="text" autocomplete="off" autocapitalize="characters" spellcheck="false" data-uppercase="true" maxlength="64" placeholder="Ex. DSM7 ou POS5">
            <label for="childAmount">Montant (FCFA)</label><input id="childAmount" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="9" autocomplete="off" data-digits-only="9" placeholder="Ex. 25000">''',
'''            <label>Numéro client (9 chiffres)</label><input id="retailPhone" type="text" inputmode="numeric" placeholder="6XXXXXXXX">
            <label>Montant (FCFA)</label><input id="retailAmount" type="text" inputmode="numeric" placeholder="Ex. 1000">''':
'''            <label for="retailPhone">Numéro client (9 chiffres)</label><input id="retailPhone" type="tel" inputmode="numeric" pattern="[0-9]*" maxlength="9" autocomplete="tel" data-digits-only="9" placeholder="6XXXXXXXX">
            <label for="retailAmount">Montant (FCFA)</label><input id="retailAmount" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="9" autocomplete="off" data-digits-only="9" placeholder="Ex. 1000">''',
'''            <label>Identifiant Camtel</label><input id="transactionId" type="text" autocomplete="off" placeholder="Ex. 123456789">''':
'''            <label for="transactionId">Identifiant Camtel</label><input id="transactionId" type="text" inputmode="numeric" autocomplete="off" autocapitalize="off" spellcheck="false" maxlength="64" placeholder="Ex. 123456789">''',
'''            <label>Code du nœud enfant</label><input id="balanceChildNode" type="text" autocomplete="off" placeholder="Ex. DSM7 ou POS5">''':
'''            <label for="balanceChildNode">Code du nœud enfant</label><input id="balanceChildNode" type="text" autocomplete="off" autocapitalize="characters" spellcheck="false" data-uppercase="true" maxlength="64" placeholder="Ex. DSM7 ou POS5">''',
'''            <p class="eyebrow">ONGLET 3 — FLOTTE & CYCLE DE VIE</p>''':
'''            <p class="eyebrow">FLOTTE & RÉSEAU</p>''',
'''            <label>Code du DSM / PoS enfant</label><input id="adminChildNode" type="text" autocomplete="off" placeholder="Ex. DSM7 ou POS5">''':
'''            <label for="adminChildNode">Code du DSM / PoS enfant</label><input id="adminChildNode" type="text" autocomplete="off" autocapitalize="characters" spellcheck="false" data-uppercase="true" maxlength="64" placeholder="Ex. DSM7 ou POS5">''',
'''            <p class="eyebrow">ONGLET 4 — CONFIGURATION & ROBOTIQUE</p>''':
'''            <p class="eyebrow">ROBOT & CONFIGURATION</p>''',
'''            <p class="eyebrow">ONGLET 5 — SAV & DIAGNOSTIC</p>''':
'''            <p class="eyebrow">SAV & DIAGNOSTIC</p>'''
}
for old, new in replacements.items():
    s = one(s, old, new, 'index ergonomics: ' + old[:35])
write(p, s)


# -----------------------------------------------------------------------------
# 2) app.js — single-flight guard, inline field focus, input normalization,
#              role-specific report title and success-only form cleanup.
# -----------------------------------------------------------------------------
p = 'app/src/main/assets/app.js'
s = read(p)
s = one(s,
'''    var activeTab = 'flux', commandPollTimer = null, dashboardPollTimer = null;
    var commandPollCursor = 0, dashboardLoadedAt = 0;''',
'''    var activeTab = 'flux', commandPollTimer = null, dashboardPollTimer = null;
    var commandPollCursor = 0, dashboardLoadedAt = 0, actionInFlight = false;
    var submittedForm = null;''',
'action single-flight state')

s = one(s,
'''        onCommandCreated:function(data){setBusy(false);pendingPreview=null;if(data.error){showActionError(data);return;}clearActionError();var command=data.command||{};if(!command.public_id){showActionError({code:'INVALID_RESPONSE',message:'Réponse serveur incomplète.'});return;}upsert(command);render();scheduleCommandPoll(1200);if(command.robot_ready===false){showActionProgress((command.robot_status||'ROBOT_OFFLINE')+' — '+(command.robot_message||'Commande créée, mais le Robot ne communique pas encore.'));showToast('Commande créée, mais Robot hors ligne.');return;}showActionProgress('Commande créée. Le Robot détenteur de la SIM est connecté et va la prendre.');showToast(data.duplicate?'Cette demande existait déjà.':'Commande créée et transmise au Robot exact.');},''',
'''        onCommandCreated:function(data){var submitted=submittedForm;setBusy(false);pendingPreview=null;submittedForm=null;if(data.error){showActionError(data);return;}clearActionError();var command=data.command||{};if(!command.public_id){showActionError({code:'INVALID_RESPONSE',message:'Réponse serveur incomplète.'});return;}clearSubmittedFields(submitted);upsert(command);render();scheduleCommandPoll(1200);if(command.robot_ready===false){showActionProgress((command.robot_status||'ROBOT_OFFLINE')+' — '+(command.robot_message||'Commande créée, mais le Robot ne communique pas encore.'));showToast('Commande créée, mais Robot hors ligne.');return;}showActionProgress('Commande créée. Le Robot détenteur de la SIM est connecté et va la prendre.');showToast(data.duplicate?'Cette demande existait déjà.':'Commande créée et transmise au Robot exact.');},''',
'created success cleanup')

s = one(s,
'''        if(configuration.role==='DAE'){showRoleNotice('Profil DAE : approvisionnement des DSM disponible. Un DAE n’achète pas auprès d’un supérieur et ne vend pas aux clients finaux.');}
        else if(configuration.role==='DSM'){showRoleNotice('Profil DSM : achat auprès du DAE et approvisionnement des PoS disponibles.');}
        else if(configuration.role==='POS'){showRoleNotice('Profil PoS : achat auprès du DSM et vente aux clients finaux disponibles.');}''',
'''        if(configuration.role==='DAE'){showRoleNotice('Profil DAE : approvisionnement des DSM disponible. Un DAE n’achète pas auprès d’un supérieur et ne vend pas aux clients finaux.');byId('reportsIntroTitle').textContent='Pilotage de mon réseau';byId('reportsIntroText').textContent='Mon solde, mes DSM et leurs PoS sont présentés dans ma propre pyramide uniquement, avec les activités et preuves disponibles.';}
        else if(configuration.role==='DSM'){showRoleNotice('Profil DSM : achat auprès du DAE et approvisionnement des PoS disponibles.');byId('reportsIntroTitle').textContent='Mes soldes et mes PoS';byId('reportsIntroText').textContent='Mon compte et mes PoS directs sont suivis ici sans exposer les autres DSM ni les autres branches du DAE.';}
        else if(configuration.role==='POS'){showRoleNotice('Profil PoS : achat auprès du DSM et vente aux clients finaux disponibles.');byId('reportsIntroTitle').textContent='Mon solde et mon activité';byId('reportsIntroText').textContent='Ce PoS affiche uniquement son propre solde Camtel, son disponible, ses ventes et ses preuves récentes.';}''',
'role report copy')

s = one(s,
'''        each('button[data-native-action]',function(button){button.onclick=function(){runNativeAction(button.getAttribute('data-native-action'));};});
        initializeTabs();''',
'''        each('button[data-native-action]',function(button){button.onclick=function(){runNativeAction(button.getAttribute('data-native-action'));};});
        initializeInputErgonomics();
        initializeTabs();''',
'input ergonomics initialization')

s = one(s,
'''    function showRoleNotice(message){var notice=byId('roleNotice');notice.textContent=message;notice.className='notice';}
    function execute(action){
        if(!bridge()){return;}var type='',node='',phone='',amount='',argument='';''',
'''    function showRoleNotice(message){var notice=byId('roleNotice');notice.textContent=message;notice.className='notice';}
    function initializeInputErgonomics(){
        each('input[data-digits-only]',function(input){input.addEventListener('input',function(){var max=Number(input.getAttribute('data-digits-only')||0),clean=input.value.replace(/\\D/g,'');if(max>0){clean=clean.slice(0,max);}if(input.value!==clean){input.value=clean;}clearFieldIssue(input);});});
        each('input[data-uppercase]',function(input){input.addEventListener('input',function(){var upper=input.value.toUpperCase();if(input.value!==upper){input.value=upper;}clearFieldIssue(input);});});
        each('input',function(input){input.addEventListener('input',function(){clearFieldIssue(input);});});
    }
    function clearFieldIssue(input){if(input&&input.removeAttribute){input.removeAttribute('aria-invalid');}}
    function fieldIssue(id,message){var input=byId(id);showToast(message);if(!input){return;}input.setAttribute('aria-invalid','true');if(input.scrollIntoView){input.scrollIntoView({block:'center'});}window.setTimeout(function(){try{input.focus();}catch(ignored){}},80);}
    function snapshotForm(type){return {type:type,node:byId('childNode')?byId('childNode').value:'',phone:byId('retailPhone')?byId('retailPhone').value:'',requestAmount:byId('requestSupplyAmount')?byId('requestSupplyAmount').value:'',childAmount:byId('childAmount')?byId('childAmount').value:'',retailAmount:byId('retailAmount')?byId('retailAmount').value:'',transactionId:byId('transactionId')?byId('transactionId').value:''};}
    function clearSubmittedFields(submitted){if(!submitted){return;}if(submitted.type==='REQUEST_SUPPLY'&&byId('requestSupplyAmount')&&byId('requestSupplyAmount').value===submitted.requestAmount){byId('requestSupplyAmount').value='';}else if(submitted.type==='SUPPLY_CHILD'){if(byId('childAmount')&&byId('childAmount').value===submitted.childAmount){byId('childAmount').value='';}}else if(submitted.type==='RETAIL_SALE'){if(byId('retailPhone')&&byId('retailPhone').value===submitted.phone){byId('retailPhone').value='';}if(byId('retailAmount')&&byId('retailAmount').value===submitted.retailAmount){byId('retailAmount').value='';}}else if(submitted.type==='TRANSACTION_DETAILS'&&byId('transactionId')&&byId('transactionId').value===submitted.transactionId){byId('transactionId').value='';}}
    function execute(action){
        if(!bridge()){return;}if(actionInFlight){showToast('Une commande est déjà en préparation. Attendez sa confirmation ou son annulation.');return;}var type='',node='',phone='',amount='',argument='';''',
'field helpers and single-flight')

s = one(s,
'''        if((type==='REQUEST_SUPPLY'||type==='SUPPLY_CHILD'||type==='RETAIL_SALE')&&!/^[1-9]\\d{0,8}$/.test(amount)){showToast('Saisissez un montant entier valide.');return;}
        if(type==='SUPPLY_CHILD'&&!node){showToast('Saisissez le code du nœud enfant.');return;}
        if(type==='CHILD_BALANCE'&&!node){showToast('Saisissez le code du nœud enfant.');return;}
        if((type==='INIT_CHILD_PIN_RESET'||type==='SUSPEND_CHILD'||type==='REACTIVATE_CHILD'||type==='FREEZE_CHILD'||type==='REACTIVATE_FROZEN_CHILD')&&!node){showToast('Saisissez le code du nœud enfant à administrer.');return;}
        if(type==='RETAIL_SALE'&&!/^\\d{9}$/.test(phone)){showToast('Le numéro client doit avoir 9 chiffres.');return;}
        if(type==='TRANSACTION_DETAILS'&&!/^[A-Za-z0-9_-]{6,64}$/.test(argument)){showToast('Saisissez un identifiant Camtel valide.');return;}''',
'''        if(type==='REQUEST_SUPPLY'&&!/^[1-9]\\d{0,8}$/.test(amount)){fieldIssue('requestSupplyAmount','Saisissez un montant entier valide.');return;}
        if(type==='SUPPLY_CHILD'&&!node){fieldIssue('childNode','Saisissez le code du nœud enfant.');return;}
        if(type==='SUPPLY_CHILD'&&!/^[1-9]\\d{0,8}$/.test(amount)){fieldIssue('childAmount','Saisissez un montant entier valide.');return;}
        if(type==='CHILD_BALANCE'&&!node){fieldIssue('balanceChildNode','Saisissez le code du nœud enfant.');return;}
        if((type==='INIT_CHILD_PIN_RESET'||type==='SUSPEND_CHILD'||type==='REACTIVATE_CHILD'||type==='FREEZE_CHILD'||type==='REACTIVATE_FROZEN_CHILD')&&!node){fieldIssue('adminChildNode','Saisissez le code du nœud enfant à administrer.');return;}
        if(type==='RETAIL_SALE'&&!/^\\d{9}$/.test(phone)){fieldIssue('retailPhone','Le numéro client doit avoir 9 chiffres.');return;}
        if(type==='RETAIL_SALE'&&!/^[1-9]\\d{0,8}$/.test(amount)){fieldIssue('retailAmount','Saisissez un montant entier valide.');return;}
        if(type==='TRANSACTION_DETAILS'&&!/^[A-Za-z0-9_-]{6,64}$/.test(argument)){fieldIssue('transactionId','Saisissez un identifiant Camtel valide.');return;}''',
'field-specific validation')

s = one(s,
'''        pendingPreview={type:type,node:node,phone:phone,amount:amount,argument:argument,request_id:requestId(),capacity_check_id:''};
        setBusy(true);clearActionError();''',
'''        pendingPreview={type:type,node:node,phone:phone,amount:amount,argument:argument,request_id:requestId(),capacity_check_id:''};
        submittedForm=snapshotForm(type);setBusy(true);clearActionError();''',
'submitted form snapshot')

# If a preview is rejected/cancelled, retain user fields but release single flight.
s = s.replace("if(!confirmFinancial(preview)){setBusy(false);pendingPreview=null;showToast('Commande annulée avant toute composition.');return;}",
              "if(!confirmFinancial(preview)){setBusy(false);pendingPreview=null;submittedForm=null;showToast('Commande annulée avant toute composition.');return;}", 1)

s = one(s,
'''    function setBusy(value){each('button[data-action]',function(button){button.disabled=value;});}''',
'''    function setBusy(value){actionInFlight=!!value;each('button[data-action]',function(button){button.disabled=value;button.setAttribute('aria-busy',value?'true':'false');});}''',
'logical busy state')
write(p, s)


# -----------------------------------------------------------------------------
# 3) CSS — clear focus/error state without animation overhead.
# -----------------------------------------------------------------------------
p = 'app/src/main/assets/style.css'
s = read(p)
s += '''\n/* v2.6.8 — saisie transactionnelle claire sur petit écran. */\ninput[aria-invalid="true"]{border-color:#ff8b98!important;box-shadow:0 0 0 3px rgba(255,107,122,.16)!important}\nbutton[aria-busy="true"]{cursor:wait}\n'''
write(p, s)


# -----------------------------------------------------------------------------
# 4) Historical tests: preserve functions, replace obsolete numbered-tab copy.
# -----------------------------------------------------------------------------
p = 'app/src/test/finance-flow.mjs'
s = read(p)
s = s.replace("assert.match(html, /ONGLET 1 — GRAPHES & RAPPORTS/);", "assert.match(html, /PILOTAGE & RAPPORTS/);")
s = s.replace("assert.match(html, /ONGLET 5 — SAV & DIAGNOSTIC/);", "assert.match(html, /SAV & DIAGNOSTIC/);")
write(p, s)

contract = r'''import fs from 'node:fs';
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
const ui=fs.readFileSync('app/src/main/assets/app.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
for(const id of ['requestSupplyAmount','childAmount','retailPhone','retailAmount']){
  const at=html.indexOf('id="'+id+'"'); if(at<0) throw new Error('field missing: '+id);
  const tail=html.slice(at,at+260); if(!tail.includes('inputmode="numeric"')) throw new Error('numeric keyboard missing: '+id);
}
if(!html.includes('id="retailPhone" type="tel"')) throw new Error('phone tel semantics missing');
if(!html.includes('maxlength="9" autocomplete="tel" data-digits-only="9"')) throw new Error('phone input constraints missing');
for(const id of ['childNode','balanceChildNode','adminChildNode']){
  const at=html.indexOf('id="'+id+'"'); if(at<0||!html.slice(at,at+260).includes('data-uppercase="true"')) throw new Error('uppercase node input missing: '+id);
}
for(const contract of ['actionInFlight','initializeInputErgonomics','fieldIssue','snapshotForm','clearSubmittedFields','aria-busy']){
  if(!ui.includes(contract)) throw new Error('transaction UX contract missing: '+contract);
}
if(!ui.includes("Une commande est déjà en préparation")) throw new Error('single-flight user feedback missing');
if(!ui.includes("submitted.type==='RETAIL_SALE'")) throw new Error('success-only retail cleanup missing');
if(!html.includes('PILOTAGE & RAPPORTS')||html.includes('ONGLET 1 —')) throw new Error('obsolete numbered report heading remains');
if(!html.includes('FLOTTE & RÉSEAU')||!html.includes('ROBOT & CONFIGURATION')||!html.includes('SAV & DIAGNOSTIC')) throw new Error('dynamic module headings missing');
if(!css.includes('input[aria-invalid="true"]')) throw new Error('field error styling missing');
console.log('v2.6.8 transaction UX: mobile keyboards, single-flight, focused validation and success cleanup OK');
'''
Path('app/src/test/v268-transaction-ux.mjs').write_text(contract)
