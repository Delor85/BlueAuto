(function(){
'use strict';
/* B.I.R. 2.9.9.3 unified UI loader.
 * One modern interface for every supported Android version.
 * The proven v2.9.7 Intelligence/Cockpit engine is restored as the common UI foundation and the
 * v2.9.9.3 additive layer is then loaded identically on Android 6+. No API-specific visual fork,
 * no Transaction-First DOM rebuild, no Reference-Stability focus/pageshow wake storm.
 */
function id(x){return document.getElementById(x);}
function addCssOnce(idValue,href){if(id(idValue))return;var l=document.createElement('link');l.id=idValue;l.rel='stylesheet';l.href=href;document.head.appendChild(l);}
function addScriptOnce(idValue,src,onload){if(id(idValue)){if(onload)onload();return;}var s=document.createElement('script');s.id=idValue;s.src=src;s.async=false;if(onload)s.onload=onload;document.body.appendChild(s);}
function loadV2993(){addCssOnce('birV2993Css','field-runtime-v2993.css');addScriptOnce('birV2993Script','field-runtime-v2993.js');}
function load(){addScriptOnce('birV297IntelligenceCore','intelligence-v297-core.js',function(){window.setTimeout(loadV2993,850);});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load);else load();
}());
