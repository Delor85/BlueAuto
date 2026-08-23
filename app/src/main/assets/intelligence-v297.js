(function(){
'use strict';
/* v2.9.9 compatibility loader: one Transaction-First shell + one Reference-Stability layer.
 * No second assistant and no second polling loop are created here. */
function id(x){return document.getElementById(x);}
function loadV299(){if(id('birV299Script'))return;var css=document.createElement('link');css.rel='stylesheet';css.href='reference-stability-v299.css';css.id='birV299Css';document.head.appendChild(css);var s=document.createElement('script');s.id='birV299Script';s.src='reference-stability-v299.js';s.async=false;document.body.appendChild(s);}
function load(){if(id('birV298Script')){loadV299();return;}var css=document.createElement('link');css.rel='stylesheet';css.href='transaction-first-v298.css';css.id='birV298Css';document.head.appendChild(css);var s=document.createElement('script');s.id='birV298Script';s.src='transaction-first-v298.js';s.async=false;s.onload=loadV299;document.body.appendChild(s);}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',load);else load();
}());
