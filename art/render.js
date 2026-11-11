const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1024, height: 1024 } });
  const svg = fs.readFileSync(process.argv[2], 'utf8');
  // full-bleed (iOS: the system rounds the corners)
  await p.setContent(`<html><body style="margin:0;background:#000">${svg}</body></html>`);
  await p.screenshot({ path: 'icon-ios-1024.png', clip: { x: 0, y: 0, width: 1024, height: 1024 } });
  // macOS / web style: rounded square with margin, transparent background
  const inner = svg.replace('<svg ', '<svg style="position:absolute;left:100px;top:100px;width:824px;height:824px;border-radius:185px;box-shadow:0 18px 30px rgba(0,0,0,.35)" ');
  await p.setContent(`<html><body style="margin:0;background:transparent"><div style="position:relative;width:1024px;height:1024px">${inner.replace(/<svg([^>]*)>/, (m) => m)}</div></body></html>`);
  await p.evaluate(() => { const s = document.querySelector('svg'); s.style.overflow = 'hidden'; s.style.clipPath = 'inset(0 round 185px)'; });
  await p.screenshot({ path: 'icon-mac-1024.png', omitBackground: true, clip: { x: 0, y: 0, width: 1024, height: 1024 } });
  // web: rounded, no margin
  await p.setContent(`<html><body style="margin:0;background:transparent">${svg.replace('<svg ', '<svg style="clip-path:inset(0 round 225px)" ')}</body></html>`);
  await p.screenshot({ path: 'icon-web-1024.png', omitBackground: true, clip: { x: 0, y: 0, width: 1024, height: 1024 } });
  await b.close();
})();
