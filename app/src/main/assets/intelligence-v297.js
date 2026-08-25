(function(){
'use strict';
/* B.I.R. 2.9.9.5 unified UI loader.
 * One modern interface for every supported Android version.
 * Stable v2.9.7 Intelligence/Cockpit foundation -> v2.9.9.3 direct-child/Tchoronko layer
 * -> v2.9.9.5 convergence layer restoring useful 2.9.9/2.9.9.1/2.9.9.2 capabilities.
 * The unstable Transaction-First DOM rebuild, Reference-Stability wake storm and old v2991/v2992
 * runtime layers remain historical only and are never loaded here.
 */
function id(x){return document.getElementById(x);}
function addCssOnce(idValue,href){if(id(idValue))return;var l=document.createElement('link');l.id=idValue;l.rel='stylesheet';l.href=href;document.head.appendChild(l);}
function addScriptOnce(idValue,src,onload){if(id(idValue)){if(onload)onload();return;}var s=document.createElement('script');s.id=idValue;s.src=src;s.async=false;if(onload)s.onload=onload;document.body.appendChild(s);}
function loadV2995(){addScriptOnce('birV2995Convergence','convergence-v2995.js');}
function loadV2993(){addCssOnce('birV2993Css','field-runtime-v2993.css');addScriptOnce('birV2993Script','field-runtime-v2993.js',function(){window.setTimeout(loadV2995,120);});}
function load(){addScriptOnce('birV297IntelligenceCore','intelligence-v297-core.js',function(){window.setTimeout(loadV2993,850);});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load);else load();
}());
