(function(){
'use strict';
/* B.I.R. 2.9.9.6 unified UI loader.
 * One modern interface for every supported Android version.
 * Stable v2.9.7 Intelligence/Cockpit foundation -> v2.9.9.3 direct-child/Tchoronko layer
 * -> v2.9.9.5 convergence -> v2.9.9.6 AI discovery/guide + role guard.
 * The v2.9.9.6 layer is additive and UI/read-plane only: natural-language finance may prefill
 * an existing form, but never creates, previews, confirms or executes the operation itself.
 * The role guard additionally prevents PoS from receiving DAE/DSM-only Assistant guidance.
 * The unstable Transaction-First DOM rebuild, Reference-Stability wake storm and old v2991/v2992
 * runtime layers remain historical only and are never loaded here.
 */
function id(x){return document.getElementById(x);}
function addCssOnce(idValue,href){if(id(idValue))return;var l=document.createElement('link');l.id=idValue;l.rel='stylesheet';l.href=href;document.head.appendChild(l);}
function addScriptOnce(idValue,src,onload){if(id(idValue)){if(onload)onload();return;}var s=document.createElement('script');s.id=idValue;s.src=src;s.async=false;if(onload)s.onload=onload;document.body.appendChild(s);}
function loadRoleGuard(){addScriptOnce('birV2996AiRoleGuard','ai-role-guard-v2996.js');}
function loadV2996(){addCssOnce('birV2996AiGuideCss','ai-guide-v2996.css');addScriptOnce('birV2996AiGuide','ai-guide-v2996.js',function(){window.setTimeout(loadRoleGuard,40);});}
function loadV2995(){addScriptOnce('birV2995Convergence','convergence-v2995.js',function(){window.setTimeout(loadV2996,160);});}
function loadV2993(){addCssOnce('birV2993Css','field-runtime-v2993.css');addScriptOnce('birV2993Script','field-runtime-v2993.js',function(){window.setTimeout(loadV2995,120);});}
function load(){addScriptOnce('birV297IntelligenceCore','intelligence-v297-core.js',function(){window.setTimeout(loadV2993,850);});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load);else load();
}());
