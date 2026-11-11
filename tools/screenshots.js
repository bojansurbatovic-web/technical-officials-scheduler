// App Store screenshots from the app's own screens (same interface as the iPhone/iPad/Mac app).
// Sizes: iPhone 6.9" 1320x2868, iPad 13" 2064x2752, Mac 2880x1800.
const { chromium } = require('playwright');
const OUT = process.argv[2] || 'app-store/screenshots';
const sets = [
  ['iphone-6.9', { width: 440, height: 956 }, 3, true],
  ['ipad-13', { width: 1032, height: 1376 }, 2, true],
  ['mac', { width: 1440, height: 900 }, 2, false],
];
const shots = [['1-assignments', 'assignments'], ['2-gantt', 'gantt'], ['3-meetings', 'meetings'], ['4-races', 'races'], ['5-schedules', 'schedules'], ['6-calendar', 'library']];
(async () => {
  const b = await chromium.launch();
  for (const [name, viewport, scale, touch] of sets) {
    const ctx = await b.newContext({ viewport, deviceScaleFactor: scale, hasTouch: touch, isMobile: touch && viewport.width < 600, colorScheme: 'light', locale: 'en-GB' });
    const p = await ctx.newPage();
    await p.goto('http://localhost:8765/index.html');
    await p.waitForFunction(() => window.WTP && WTP.App && WTP.App.res);
    await p.evaluate(() => { document.getElementById('toast').remove(); WTP.App.gantt.zoom = 3; });
    for (const [file, sec] of shots) {
      await p.evaluate(s => { WTP.App.sched = 'TO 02'; WTP.App.go(s); }, sec);
      if (sec === 'gantt') await p.evaluate(() => { const g = document.querySelector('.gantt-wrap'); if (g) g.scrollLeft = 0; });
      await p.waitForTimeout(150);
      await p.screenshot({ path: `${OUT}/${name}-${file}.png` });
    }
    await ctx.close();
  }
  await b.close();
})();
