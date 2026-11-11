/* Storage and sharing. In the iPhone / iPad / Mac app the native shell keeps every event as a
 * .wtplan.json file in the app's Documents folder (visible in the Files app) and opens the share sheet
 * or a save panel for exports. In a browser the same calls use localStorage and downloads. */
var WTP = (typeof WTP !== 'undefined') ? WTP : {};
(function (W) {
  'use strict';
  var S = {};
  var bridge = (typeof window !== 'undefined' && window.webkit && window.webkit.messageHandlers &&
    window.webkit.messageHandlers.tos) || null;
  S.native = !!bridge;
  S.platform = 'web';

  function call(action, args) {
    var msg = Object.assign({ action: action }, args || {});
    return Promise.resolve(bridge.postMessage(msg)).then(function (reply) {
      if (reply && reply.error) throw new Error(reply.error);
      return reply ? reply.result : null;
    });
  }

  // ------------------------------------------------------------ browser fallback (localStorage)
  var LS_INDEX = 'tos.index', LS_DOC = 'tos.doc.';
  function lsGet(k, d) { try { var v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (e) { /* ignore */ } }
  function lsIndex() { try { return JSON.parse(lsGet(LS_INDEX, '[]')) || []; } catch (e) { return []; } }

  S.init = function () {
    if (!bridge) return Promise.resolve();
    return call('hello', {}).then(function (r) { S.platform = (r && r.platform) || 'ios'; }).catch(function () { S.platform = 'ios'; });
  };

  /** [{id, name, venue, dates:[iso], races, officials, updated}] newest first */
  S.list = function () {
    if (bridge) return call('list');
    return Promise.resolve(lsIndex().sort(function (a, b) { return (b.updated || '').localeCompare(a.updated || ''); }));
  };
  S.load = function (id) {
    if (bridge) return call('load', { id: id });
    var t = lsGet(LS_DOC + id, null);
    return t === null ? Promise.reject(new Error('Event not found')) : Promise.resolve(t);
  };
  S.save = function (id, json, meta) {
    meta = Object.assign({ id: id, updated: new Date().toISOString() }, meta || {});
    if (bridge) return call('save', { id: id, json: json, meta: meta });
    if (!lsSet(LS_DOC + id, json)) return Promise.reject(new Error('Browser storage is full or blocked'));
    var idx = lsIndex().filter(function (x) { return x.id !== id; });
    idx.push(meta);
    lsSet(LS_INDEX, JSON.stringify(idx));
    return Promise.resolve(meta);
  };
  S.remove = function (id) {
    if (bridge) return call('delete', { id: id });
    lsDel(LS_DOC + id);
    lsSet(LS_INDEX, JSON.stringify(lsIndex().filter(function (x) { return x.id !== id; })));
    return Promise.resolve();
  };
  /** Tells the native app that the page is ready to receive opened files. */
  S.ready = function () { if (bridge) call('ready').catch(function () { /* ignore */ }); };
  S.getPref = function (k, d) { var v = lsGet('tos.pref.' + k, null); return v === null ? d : v; };
  S.setPref = function (k, v) { lsSet('tos.pref.' + k, String(v)); };

  // ------------------------------------------------------------ export / share
  function b64(bytes) {
    var s = '', chunk = 0x8000;
    for (var i = 0; i < bytes.length; i += chunk) s += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    return btoa(s);
  }
  /** data: string or Uint8Array */
  S.exportFile = function (filename, mime, data) {
    var bytes = typeof data === 'string' ? new TextEncoder().encode(data) : data;
    if (bridge) return call('share', { filename: filename, mime: mime, base64: b64(bytes) });
    var blob = new Blob([bytes], { type: mime }), url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = filename; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 1500);
    return Promise.resolve('downloaded');
  };
  S.copyText = function (text) {
    if (bridge) return call('copy', { text: text });
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } finally { ta.remove(); }
    return Promise.resolve();
  };
  S.openLink = function (url) {
    if (bridge) return call('openURL', { url: url });
    window.open(url, '_blank', 'noopener');
    return Promise.resolve();
  };

  W.Store = S;
})(WTP);
