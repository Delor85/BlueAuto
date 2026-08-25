(function(){
'use strict';
/* B.I.R. 2.9.9.6 unified UI loader.
 * One modern interface for every supported Android version.
 * Stable v2.9.7 Intelligence/Cockpit -> v2993 children/Tchoronko -> v2995 truth/network/commission
 * -> v2996 role-safe discovery -> authoritative role catalogue guard.
 * Historical unstable Transaction-First/reference-stability/v2991/v2992 runtimes are never loaded.
 */
function id(x){return document.getElementById(x);}
function addCssOnce(idValue,href){if(id(idValue))return;var l=document.createElement('link');l.id=idValue;l.rel='stylesheet';l.href=href;document.head.appendChild(l);}
function addScriptOnce(idValue,src,onload){if(id(idValue)){if(onload)onload();return;}var s=document.createElement('script');s.id=idValue;s.src=src;s.async=false;if(onload)s.onload=onload;document.body.appendChild(s);}
function loadRoleGuard(){addScriptOnce('birV2996RoleCatalogue','role-catalog-v2996.js');}
function loadV2996(){addCssOnce('birV2996Css','convergence-v2996.css');addScriptOnce('birV2996Convergence','convergence-v2996.js',function(){window.setTimeout(loadRoleGuard,90);});}
function loadV2995(){addScriptOnce('birV2995Convergence','convergence-v2995.js',function(){window.setTimeout(loadV2996,120);});}
function loadV2993(){addCssOnce('birV2993Css','field-runtime-v2993.css');addScriptOnce('birV2993Script','field-runtime-v2993.js',function(){window.setTimeout(loadV2995,120);});}
function load(){addScriptOnce('birV297IntelligenceCore','intelligence-v297-core.js',function(){window.setTimeout(loadV2993,850);});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load);else load();
}());
