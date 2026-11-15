// Simulates the Windows shell: serves the planner at https://app.tos-scheduler.example/ (as WebView2's virtual host),
// fakes chrome.webview with the same actions as windows/MainForm.cs and injects windows/bridge.js.
// Checks the page uses the bridge for storage, export, opened files and the Windows keyboard shortcuts.
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const WEB = path.join(__dirname, '..', 'web');
const TYPES = { html: 'text/html', js: 'text/javascript', css: 'text/css', json: 'application/json', png: 'image/png', svg: 'image/svg+xml', webmanifest: 'application/json' };
(async () => {
  const b = await chromium.launch(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {});
  const page = await b.newPage({ viewport: { width: 1320, height: 880 } });
  const errors = []; page.on('pageerror', e => errors.push(String(e)));
  await page.route('https://app.tos-scheduler.example/**', route => {
    let p = new URL(route.request().url()).pathname; if (p === '/') p = '/index.html';
    const file = path.join(WEB, p);
    if (!file.startsWith(WEB) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'Not found' });
    route.fulfill({ status: 200, contentType: TYPES[path.extname(file).slice(1)] || 'application/octet-stream', body: fs.readFileSync(file) });
  });
  await page.addInitScript(() => {
    const files = JSON.parse(sessionStorage.getItem('wf') || '{}'), index = JSON.parse(sessionStorage.getItem('wi') || '{}'), log = [];
    const persist = () => { sessionStorage.setItem('wf', JSON.stringify(files)); sessionStorage.setItem('wi', JSON.stringify(index)); };
    const listeners = [];
    window.__win = { files, index, log };
    const answer = (id, result, error) => setTimeout(() => listeners.forEach(fn => fn({ data: error ? { __tos: id, error } : { __tos: id, result } })), 5);
    window.chrome = { webview: {
      addEventListener(type, fn) { if (type === 'message') listeners.push(fn); },
      postMessage(o) {
        const m = o.msg; log.push(m.action);
        switch (m.action) {
          case 'hello': return answer(o.__tos, { platform: 'windows' });
          case 'ready': return answer(o.__tos, true);
          case 'list': return answer(o.__tos, Object.values(index));
          case 'load': return files[m.id] ? answer(o.__tos, files[m.id]) : answer(o.__tos, null, 'Event not found');
          case 'save': files[m.id] = m.json; index[m.id] = Object.assign({}, m.meta, { id: m.id }); persist(); return answer(o.__tos, m.meta);
          case 'delete': delete files[m.id]; delete index[m.id]; persist(); return answer(o.__tos, true);
          case 'share': window.__win.shared = { name: m.filename, size: atob(m.base64).length }; return answer(o.__tos, 'saved');
          case 'copy': case 'openURL': return answer(o.__tos, true);
          default: return answer(o.__tos, null, 'Unknown action ' + m.action);
        }
      }
    } };
  });
  await page.addInitScript({ path: path.join(__dirname, '..', 'windows', 'bridge.js') });
  await page.goto('https://app.tos-scheduler.example/index.html');
  await page.waitForFunction(() => window.__win.log.includes('ready'));
  await page.waitForTimeout(700);
  const r1 = await page.evaluate(() => ({ platform: document.documentElement.dataset.platform, native: WTP.Store.native,
    saved: Object.keys(window.__win.files).length, sw: !!(navigator.serviceWorker && navigator.serviceWorker.controller) }));
  // Ctrl+E opens Export; exporting goes through the bridge (Save dialog in the real app)
  await page.keyboard.press('Control+e');
  await page.waitForTimeout(300);
  const onExport = await page.evaluate(() => WTP.App.section);
  const exportText = await page.locator('main, #content, body').first().innerText();
  await page.locator('.exp-row', { hasText: 'Excel workbook' }).locator('button').click();
  await page.waitForTimeout(300);
  const shared = await page.evaluate(() => window.__win.shared);
  // a plan file opened with the app
  const text = await page.evaluate(() => JSON.stringify(WTP.examples.example_multiday));
  await page.evaluate(t => WTP.App.openExternal.apply(null, [t, 'weekend.wtplan.json']), text);
  await page.waitForTimeout(800);
  const r2 = await page.evaluate(() => ({ name: WTP.App.ev.event.name, docs: Object.keys(window.__win.files).length }));
  // flush (used before the window closes) and reload: the event comes back from the files
  await page.evaluate(() => WTP.App.flush());
  await page.reload(); await page.waitForFunction(() => window.WTP && WTP.App && WTP.App.res); await page.waitForTimeout(300);
  const r3 = await page.evaluate(() => WTP.App.ev.event.name);
  await page.evaluate(() => WTP.App.go('about'));
  const about = await page.locator('body').innerText();
  console.log({ r1, onExport, shared, r2, r3, errors, aboutWindows: /Documents\\Technical Officials Scheduler/.test(about), ctrlE: /Ctrl\+E/.test(about) });
  const ok = r1.native && r1.platform === 'windows' && r1.saved === 1 && !r1.sw && onExport === 'export' && /Save dialog/.test(exportText) &&
    shared && /\.xlsx$/.test(shared.name) && shared.size > 5000 && r2.docs === 2 && /Two-day/.test(r2.name) && r3 === r2.name &&
    /Documents\\Technical Officials Scheduler/.test(about) && /Ctrl\+E/.test(about) && !errors.length;
  console.log(ok ? 'windows bridge ok' : 'windows bridge FAILED');
  await b.close(); process.exit(ok ? 0 : 1);
})();
