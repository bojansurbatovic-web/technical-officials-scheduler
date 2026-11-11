/* Start-up (kept out of index.html so the strict Content-Security-Policy needs no inline script). */
(function () {
  'use strict';
  function start() { WTP.App.start(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
  // Offline support for the web version (not used inside the iPhone / iPad / Mac app).
  if ('serviceWorker' in navigator && location.protocol === 'https:' && !(window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.tos)) {
    navigator.serviceWorker.register('sw.js').catch(function () { /* offline cache is optional */ });
  }
})();
