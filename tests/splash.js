// The opening animation: shown at start (web / Apple apps), gone after ~3 s or a tap, never in the Windows app.
// Playwright marks the browser as automated (navigator.webdriver), which normally skips the splash – undone here.
const { chromium } = require('playwright');
const URL = process.env.APP_URL || 'http://localhost:8765/index.html';
(async () => {
  const b = await chromium.launch(Object.assign({ args: ['--autoplay-policy=no-user-gesture-required'] }, process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {}));
  const errors = [];
  async function page(windows) {
    const p = await b.newPage({ viewport: { width: 1280, height: 800 } });
    p.on('pageerror', e => errors.push(String(e)));
    await p.addInitScript(() => Object.defineProperty(navigator, 'webdriver', { get: () => false }));
    if (windows) await p.addInitScript(() => { window.chrome = { webview: { addEventListener() {}, postMessage() {} } }; });
    await p.goto(URL);
    return p;
  }
  // 1. web: the splash covers the app, shows the name and the website, then leaves by itself
  const p = await page(false);
  await p.waitForSelector('.tos-splash', { timeout: 3000 });
  await p.waitForTimeout(1600);
  const shown = await p.evaluate(() => {
    const s = document.querySelector('.tos-splash');
    return { text: s.innerText.replace(/\s+/g, ' '), layout: s.className, panels: s.querySelectorAll('canvas').length,
      covers: getComputedStyle(s).position === 'fixed' && s.getBoundingClientRect().width === innerWidth };
  });
  await p.waitForSelector('.tos-splash', { state: 'detached', timeout: 6000 });
  const appUsable = await p.evaluate(() => !!(WTP.App.ev && document.querySelector('main, #content')));
  // 2. a tap skips it straight away
  const q = await page(false);
  await q.waitForSelector('.tos-splash');
  await q.waitForTimeout(300);
  await q.mouse.click(640, 400);
  const t0 = Date.now();
  await q.waitForSelector('.tos-splash', { state: 'detached', timeout: 2000 });
  const skipMs = Date.now() - t0;
  // 3. Windows app: no splash at all
  const w = await page(true);
  await w.waitForTimeout(1200);
  const onWindows = await w.evaluate(() => !!document.querySelector('.tos-splash'));
  console.log({ shown, appUsable, skipMs, onWindows, errors });
  const ok = /Technical Officials/.test(shown.text) && /Scheduler/.test(shown.text) && /www\.trisport\.me/.test(shown.text) &&
    /band/.test(shown.layout) && shown.panels === 3 && shown.covers && appUsable && skipMs < 1500 && !onWindows && !errors.length;
  console.log(ok ? 'splash ok' : 'splash FAILED');
  await b.close(); process.exit(ok ? 0 : 1);
})();
