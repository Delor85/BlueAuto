(function(){
'use strict';
/* v2.9.9.1 compatibility loader: Transaction-First -> Reference-Stability -> Field-Runtime.
 * This loader does not create a second assistant or polling loop.
 * It never bypasses historical finance/USSD guards. */
function id(x){return document.getElementById(x);}
function loadV2991(){if(id('birV2991Script'))return;var css=document.createElement('link');css.rel='stylesheet';css.href='field-runtime-v2991.css';css.id='birV2991Css';document.head.appendChild(css);var s=document.createElement('script');s.id='birV2991Script';s.src='field-runtime-v2991.js';s.async=false;document.body.appendChild(s);}
function loadV299(){if(id('birV299Script')){loadV2991();return;}var css=document.createElement('link');css.rel='stylesheet';css.href='reference-stability-v299.css';css.id='birV299Css';document.head.appendChild(css);var s=document.createElement('script');s.id='birV299Script';s.src='reference-stability-v299.js';s.async=false;s.onload=loadV2991;document.body.appendChild(s);}
function load(){if(id('birV298Script')){loadV299();return;}var css=document.createElement('link');css.rel='stylesheet';css.href='transaction-first-v298.css';css.id='birV298Css';document.head.appendChild(css);var s=document.createElement('script');s.id='birV298Script';s.src='transaction-first-v298.js';s.async=false;s.onload=loadV299;document.body.appendChild(s);}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load);else load();
}());
