from pathlib import Path


def read(p): return Path(p).read_text(encoding='utf-8')
def write(p,t): Path(p).write_text(t,encoding='utf-8')
def once(p,old,new):
    text=read(p)
    if old not in text: raise SystemExit('missing anchor in %s: %r' % (p,old[:120]))
    write(p,text.replace(old,new,1))

# A one-shot rate belongs to one attempted transfer only. Consume it not just after successful
# command creation, but also on cancellation or preview error so it can never leak to a later child supply.
once('app/src/main/assets/app.js',
"    function clearSubmittedFields(submitted){if(!submitted){return;}if(submitted.type==='REQUEST_SUPPLY'",
"    function clearOneShotCommission(preview){if(preview&&preview.type==='SUPPLY_CHILD'&&window.BIRCommissionPolicy&&window.BIRCommissionPolicy.clearOneShotRate){window.BIRCommissionPolicy.clearOneShotRate(preview.node);}}\n    function clearSubmittedFields(submitted){if(!submitted){return;}if(submitted.type==='REQUEST_SUPPLY'")

once('app/src/main/assets/app.js',
"        if(data&&data.error){setBusy(false);pendingPreview=null;showActionError(data);return;}\n        preview=data&&data.preview||{};fingerprint=String(preview.confirmation_fingerprint||'');",
"        if(data&&data.error){clearOneShotCommission(pendingPreview);setBusy(false);pendingPreview=null;submittedForm=null;showActionError(data);return;}\n        preview=data&&data.preview||{};fingerprint=String(preview.confirmation_fingerprint||'');")

once('app/src/main/assets/app.js',
"        if(!fingerprint){setBusy(false);pendingPreview=null;showActionError({code:'PREVIEW_INCOMPLETE',message:'Le serveur n’a pas certifié les numéros de cette commande.'});return;}",
"        if(!fingerprint){clearOneShotCommission(pendingPreview);setBusy(false);pendingPreview=null;submittedForm=null;showActionError({code:'PREVIEW_INCOMPLETE',message:'Le serveur n’a pas certifié les numéros de cette commande.'});return;}")

once('app/src/main/assets/app.js',
"        if(!decision){setBusy(false);pendingPreview=null;submittedForm=null;showToast('Commande annulée avant toute composition.');return;}",
"        if(!decision){clearOneShotCommission(pendingPreview);setBusy(false);pendingPreview=null;submittedForm=null;showToast('Commande annulée avant toute composition. Le taux ponctuel a été supprimé.');return;}")

# Existing onCommandCreated clearing remains as the successful terminal consumption path.
contract='app/src/test/v280-operations-admin-contract.mjs'
text=read(contract)
anchor="ok(v271.includes('clearOneShotRate')&&app.includes('clearOneShotRate'),'one-shot rate must be consumed after one transaction');"
new=anchor+"\nok(app.includes('clearOneShotCommission(pendingPreview)')&&app.includes('Le taux ponctuel a été supprimé'),'one-shot rate must also be consumed on cancellation/error and never leak to the next transaction');"
if new not in text:
    if anchor not in text: raise SystemExit('v280 one-shot contract anchor missing')
    text=text.replace(anchor,new,1)
write(contract,text)
print('B.I.R. v2.8 one-shot commission lifecycle hardened')
