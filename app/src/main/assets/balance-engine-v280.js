(function(){
'use strict';
function bridge(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}
function parse(raw,fallback){try{return JSON.parse(raw);}catch(e){return fallback;}}
function cfg(){try{return parse((bridge()&&bridge().getConfiguration&&bridge().getConfiguration())||'{}',{});}catch(e){return {};}}
function upper(v){return String(v||'').toUpperCase();}
function num(v){var n=Number(v);return isFinite(n)?n:0;}
function key(c,prefix){return prefix+String(c.profile_id||c.node_code||'default');}
function stamp(v){var n=Date.parse(v||'');return isNaN(n)?0:n;}
function money(v){return String(Math.round(num(v))).replace(/\B(?=(\d{3})+(?!\d))/g,' ');}
var configuration=cfg();
var PROOF_KEY=key(configuration,'bir_balance_guard_v271_');
var JOURNAL_KEY=key(configuration,'bir_transaction_journal_v271_');
var STATE_KEY=key(configuration,'bir_event_balance_v280_');
var FINANCE_FRESH_MS=60*60*1000;
var MAX_RECONCILED_AGE_MS=14*60*60*1000;

function proof(){return parse(localStorage.getItem(PROOF_KEY)||'null',null);}
function journal(){return parse(localStorage.getItem(JOURNAL_KEY)||'[]',[]);}
function movement(entry){
  if(!entry||upper(entry.state)!=='SUCCEEDED')return 0;
  var op=upper(entry.op),target=upper(entry.target),node=upper(configuration.node_code),amount=num(entry.amount);
  if(!amount)return 0;
  if(op.indexOf('RETAIL')>=0||op==='RETAIL_SALE')return -amount;
  if(op.indexOf('DISTRIBUTION')>=0||op==='SUPPLY_CHILD'||op==='REQUEST_SUPPLY')return target===node?amount:-amount;
  return 0;
}
function isUncertain(entry,baseTs){
  if(!entry)return false;var ts=stamp(entry.at);if(ts&&ts<=baseTs)return false;
  var state=upper(entry.state),op=upper(entry.op);
  if(/UNKNOWN|BLOCKED/.test(state)&&(/TRANSFER|SUPPLY|RETAIL|SALE/.test(op)))return true;
  if(entry.chronology_safe===false)return true;
  return false;
}
function recompute(){
  var p=proof(),items=journal(),now=Date.now(),baseTs,i,e,ts,delta=0,movements=0,uncertain=false,state;
  if(!p||p.balance===null||typeof p.balance==='undefined'){
    state={quality:'UNCERTAIN',reason:'NO_CERTIFIED_PROOF',balance:null,reusable:false,updated_at:new Date().toISOString()};
    localStorage.setItem(STATE_KEY,JSON.stringify(state));render(state);return state;
  }
  baseTs=Number(p.ts||stamp(p.operator_event_at||p.observed_at)||0);
  for(i=0;i<items.length;i+=1){e=items[i];ts=stamp(e.at);if(ts&&ts<=baseTs)continue;if(isUncertain(e,baseTs)){uncertain=true;continue;}var d=movement(e);if(d){delta+=d;movements+=1;}}
  var age=baseTs?now-baseTs:MAX_RECONCILED_AGE_MS+1;
  if(uncertain||age>MAX_RECONCILED_AGE_MS){state={quality:'UNCERTAIN',reason:uncertain?'UNRECONCILED_FINANCIAL_EVENT':'PROOF_TOO_OLD',balance:num(p.balance)+delta,base_balance:num(p.balance),delta:delta,movements:movements,reusable:false,proof_at:baseTs,updated_at:new Date().toISOString()};}
  else if(movements){state={quality:'RECALCULATED',reason:'CERTIFIED_PROOF_PLUS_CONFIRMED_MOVEMENTS',balance:num(p.balance)+delta,base_balance:num(p.balance),delta:delta,movements:movements,reusable:true,proof_at:baseTs,updated_at:new Date().toISOString()};}
  else{state={quality:age<=FINANCE_FRESH_MS?'CERTIFIED':'RECALCULATED',reason:age<=FINANCE_FRESH_MS?'RECENT_CERTIFIED_PROOF':'CERTIFIED_PROOF_NO_LATER_MOVEMENT',balance:num(p.balance),base_balance:num(p.balance),delta:0,movements:0,reusable:true,proof_at:baseTs,updated_at:new Date().toISOString()};}
  localStorage.setItem(STATE_KEY,JSON.stringify(state));render(state);return state;
}
function render(s){var card=document.getElementById('birBalanceFreshness'),own=document.getElementById('ownBalance'),main=document.getElementById('birCamtelBalance');if(!s)return;if(s.balance!==null&&s.reusable){if(own)own.textContent=money(s.balance)+' FCFA';if(main)main.textContent=money(s.balance);}if(card){if(s.quality==='CERTIFIED')card.textContent='Preuve Blue certifiée • aucune interrogation USSD nécessaire';else if(s.quality==='RECALCULATED')card.textContent='Solde recalculé • preuve certifiée + '+String(s.movements||0)+' mouvement(s) confirmé(s)';else card.textContent='Solde à rapprocher • une nouvelle preuve Blue sera requise avant finance';}}
function get(){return parse(localStorage.getItem(STATE_KEY)||'null',null)||recompute();}
function shouldRecertify(){var s=get();return !s||s.reusable!==true||s.quality==='UNCERTAIN';}
window.BIREventBalanceV280={recompute:recompute,get:get,shouldRecertify:shouldRecertify};
window.BlueMagicNative=window.BlueMagicNative||{};
var status=window.BlueMagicNative.onCommandStatus;window.BlueMagicNative.onCommandStatus=function(data){if(typeof status==='function')try{status(data);}catch(e){};setTimeout(recompute,50);};
var created=window.BlueMagicNative.onCommandCreated;window.BlueMagicNative.onCommandCreated=function(data){if(typeof created==='function')try{created(data);}catch(e){};setTimeout(recompute,50);};
var dashboard=window.BlueMagicNative.onDashboard;window.BlueMagicNative.onDashboard=function(data){if(typeof dashboard==='function')try{dashboard(data);}catch(e){};setTimeout(recompute,50);};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){setTimeout(recompute,80);});else setTimeout(recompute,80);
}());
