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
