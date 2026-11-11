// Simulates the iPhone/iPad/Mac shell (window.webkit.messageHandlers.tos with promise replies, as WKScriptMessageHandlerWithReply)
// and checks the page uses it for storage, export and opened files.
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const page = await b.newPage({ viewport: { width: 820, height: 1180 } });
  const errors = []; page.on('pageerror', e => errors.push(String(e)));
  await page.addInitScript(() => {
    const files = JSON.parse(sessionStorage.getItem('mf') || '{}'), index = JSON.parse(sessionStorage.getItem('mi') || '{}'), log = [];
    const persist = () => { sessionStorage.setItem('mf', JSON.stringify(files)); sessionStorage.setItem('mi', JSON.stringify(index)); };
    window.__native = { files, index, log };
    window.webkit = { messageHandlers: { tos: { postMessage(m) {
      log.push(m.action);
      return new Promise((res, rej) => setTimeout(() => {
        switch (m.action) {
          case 'hello': return res({ result: { platform: 'ipados' } });
          case 'ready': return res({ result: true });
          case 'list': return res({ result: Object.values(index) });
          case 'load': return files[m.id] ? res({ result: files[m.id] }) : rej(new Error('Event not found'));
          case 'save': files[m.id] = m.json; index[m.id] = Object.assign({}, m.meta, { id: m.id }); persist(); return res({ result: m.meta });
          case 'delete': delete files[m.id]; delete index[m.id]; return res({ result: true });
          case 'share': window.__native.shared = { name: m.filename, size: atob(m.base64).length }; return res({ result: 'shared' });
          case 'copy': return res({ result: true });
          default: rej(new Error('Unknown action ' + m.action));
        }
      }, 5));
    } } } };
  });
  await page.goto('http://localhost:8765/index.html');
  await page.waitForFunction(() => window.__native.log.includes('ready'));
  await page.waitForTimeout(700);
  const r1 = await page.evaluate(() => ({ platform: document.documentElement.dataset.platform, saved: Object.keys(window.__native.files).length,
    native: WTP.Store.native }));
  await page.evaluate(() => WTP.App.go('export'));
  await page.locator('.exp-row', { hasText: 'Excel workbook' }).locator('button').click();
  await page.waitForTimeout(200);
  const shared = await page.evaluate(() => window.__native.shared);
  // a file opened from Files / Finder
  const text = await page.evaluate(() => { const ev = JSON.parse(JSON.stringify(WTP.examples.example_multiday)); return JSON.stringify(ev); });
  await page.evaluate(t => WTP.App.openExternal.apply(null, [t, 'weekend.wtplan.json']), text);
  await page.waitForTimeout(800);
  const r2 = await page.evaluate(() => ({ name: WTP.App.ev.event.name, docs: Object.keys(window.__native.files).length }));
  // reload: the last event comes back from native storage
  await page.reload(); await page.waitForFunction(() => window.WTP && WTP.App && WTP.App.res); await page.waitForTimeout(300);
  const r3 = await page.evaluate(() => WTP.App.ev.event.name);
  console.log({ r1, shared, r2, r3, errors });
  const ok = r1.native && r1.platform === 'ipados' && r1.saved === 1 && shared && /\.xlsx$/.test(shared.name) && shared.size > 5000 &&
    r2.docs === 2 && /Two-day/.test(r2.name) && r3 === r2.name && !errors.length;
  console.log(ok ? 'native bridge ok' : 'native bridge FAILED');
  await b.close(); process.exit(ok ? 0 : 1);
})();
