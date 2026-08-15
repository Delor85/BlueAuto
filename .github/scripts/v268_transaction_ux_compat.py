from pathlib import Path

p = Path('app/src/main/assets/app.js')
s = p.read_text()
old = "function fieldIssue(id,message){var input=byId(id);showToast(message);if(!input){return;}input.setAttribute('aria-invalid','true');if(input.scrollIntoView){input.scrollIntoView({block:'center'});}window.setTimeout(function(){try{input.focus();}catch(ignored){}},80);}"
new = "function fieldIssue(id,message){var input=byId(id);showToast(message);if(!input){return;}if(input.setAttribute){input.setAttribute('aria-invalid','true');}if(input.scrollIntoView){input.scrollIntoView(true);}window.setTimeout(function(){try{input.focus();}catch(ignored){}},80);}"
if old not in s:
    raise SystemExit('fieldIssue compatibility anchor missing')
s = s.replace(old, new, 1)
old = "function setBusy(value){actionInFlight=!!value;each('button[data-action]',function(button){button.disabled=value;button.setAttribute('aria-busy',value?'true':'false');});}"
new = "function setBusy(value){actionInFlight=!!value;each('button[data-action]',function(button){button.disabled=value;if(button.setAttribute){button.setAttribute('aria-busy',value?'true':'false');}});}"
if old not in s:
    raise SystemExit('setBusy compatibility anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

# A successful retail creation now intentionally clears phone + amount to prevent an accidental
# duplicate sale. Re-enter them explicitly before testing the subsequent user-cancel flow.
p = Path('app/src/test/finance-flow.mjs')
t = p.read_text()
old = """confirmResult = false;
const callsBeforeCancel = bridgeCalls.length;
actions.find(item => item.action === 'retail-sale').onclick();"""
new = """confirmResult = false;
elements.get('retailPhone').value = '620550255';
elements.get('retailAmount').value = '1';
const callsBeforeCancel = bridgeCalls.length;
actions.find(item => item.action === 'retail-sale').onclick();"""
if old not in t:
    raise SystemExit('repeat sale test anchor missing')
p.write_text(t.replace(old, new, 1))
