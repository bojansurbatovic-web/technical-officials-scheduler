/* Windows app: gives the page the same bridge as the iPhone / iPad / Mac app
 * (window.webkit.messageHandlers.tos.postMessage → Promise of {result}), carried over WebView2's
 * chrome.webview messages. Injected by the Windows shell before the page's own scripts run. */
(function () {
  'use strict';
  if (!(window.chrome && window.chrome.webview) || location.hostname !== 'app.tos-scheduler.example') return;
  var pending = {}, seq = 0;
  window.chrome.webview.addEventListener('message', function (e) {
    var m = e.data;
    if (!m || typeof m.__tos !== 'number' || !pending[m.__tos]) return;
    var p = pending[m.__tos];
    delete pending[m.__tos];
    if (m.error) p.reject(new Error(m.error)); else p.resolve({ result: m.result });
  });
  var tos = {
    postMessage: function (msg) {
      return new Promise(function (resolve, reject) {
        var id = ++seq;
        pending[id] = { resolve: resolve, reject: reject };
        window.chrome.webview.postMessage({ __tos: id, msg: msg });
      });
    }
  };
  window.webkit = window.webkit || {};
  window.webkit.messageHandlers = window.webkit.messageHandlers || {};
  window.webkit.messageHandlers.tos = tos;
})();
