(function(){
'use strict';
/* B.I.R. 2.9.9.3 loader.
 * Android 11/API30 returns to the proven pre-2.9.8 rendering foundation: the stable base UI,
 * War Room v2.9.4 and Field Ops v2.9.7 remain loaded by index/field-ops, while the post-2.9.7
 * UI layers that appeared in the 2.9.8/2.9.9 line are deliberately skipped on API30.
 * Every other Android keeps the complete modern chain. The isolated v2.9.9.3 layer is loaded on
 * every platform for child War Rooms and Tchoronko. No finance/USSD handler is replaced here. */
function id(x){return document.getElementById(x);}
function api30(){return /Android\s+11(?:\D|$)/i.test(navigator.userAgent||'');}
function addCssOnce(idValue,href){if(id(idValue))return;var l=document.createElement('link');l.id=idValue;l.rel='stylesheet';l.href=href;document.head.appendChild(l);}
function addScriptOnce(idValue,src,onload){if(id(idValue)){if(onload)onload();return;}var s=document.createElement('script');s.id=idValue;s.src=src;s.async=false;if(onload)s.onload=onload;document.body.appendChild(s);}
function loadV2993(){addCssOnce('birV2993Css','field-runtime-v2993.css');addScriptOnce('birV2993Script','field-runtime-v2993.js');}
function loadV2992(){if(id('birV2992Script')){loadV2993();return;}addCssOnce('birV2992Css','field-runtime-v2992.css');addScriptOnce('birV2992Script','field-runtime-v2992.js',loadV2993);}
function loadV2991(){if(id('birV2991Script')){loadV2992();return;}addCssOnce('birV2991Css','field-runtime-v2991.css');addScriptOnce('birV2991Script','field-runtime-v2991.js',loadV2992);}
function loadV299(){if(id('birV299Script')){loadV2991();return;}addCssOnce('birV299Css','reference-stability-v299.css');addScriptOnce('birV299Script','reference-stability-v299.js',loadV2991);}
function loadModern(){if(id('birV298Script')){loadV299();return;}addCssOnce('birV298Css','transaction-first-v298.css');addScriptOnce('birV298Script','transaction-first-v298.js',loadV299);}
function load(){if(api30()){
    document.documentElement.className+=(document.documentElement.className?' ':'')+'bir-v2993-api30-legacy';
    if(document.body)document.body.className+=(document.body.className?' ':'')+'bir-v2993-api30-legacy';
    loadV2993();
    return;
  }
  loadModern();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load);else load();
}());
