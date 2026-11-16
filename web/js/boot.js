/* Start-up (kept out of index.html so the strict Content-Security-Policy needs no inline script). */
(function () {
  'use strict';
  function wantSplash() {
    if (!window.TOSSplash || navigator.webdriver) return false;              // automated tests and screenshots
    if (window.chrome && window.chrome.webview) return false;                // Windows app: starts without the animation
    return true;
  }
  function start() {
    var started = WTP.App.start();
    if (wantSplash()) {
      try { window.TOSSplash.show(document.body, { minMs: 3000, ready: Promise.resolve(started).catch(function () {}) }); }
      catch (e) { /* the app works without its opening animation */ }
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
  // Offline support for the web version (not used inside the iPhone / iPad / Mac app).
  if ('serviceWorker' in navigator && location.protocol === 'https:' && !(window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.tos)) {
    navigator.serviceWorker.register('sw.js').catch(function () { /* offline cache is optional */ });
  }
})();
