// Drives the web app in Chromium at phone, tablet and desktop sizes: every section renders without errors,
// key edits work, exports produce files. Screenshots go to $SHOTS.
const { chromium, devices } = require('playwright');
const fs = require('fs');
const URL_ = process.env.APP_URL || 'http://localhost:8765/index.html';
const SHOTS = process.env.SHOTS || '/tmp/shots';
fs.mkdirSync(SHOTS, { recursive: true });
const sections = ['library', 'event', 'races', 'officials', 'participation', 'positions', 'duties', 'meetings', 'assignments', 'conflicts', 'schedules', 'gantt', 'timeline', 'export', 'references', 'about'];
(async () => {
  const browser = await chromium.launch();
  const sizes = [['phone', { ...devices['iPhone 13'] }], ['tablet', { viewport: { width: 1024, height: 1366 }, deviceScaleFactor: 1 }], ['desktop', { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 }]];
  let problems = 0;
  for (const [name, opts] of sizes) {
    const ctx = await browser.newContext({ ...opts, acceptDownloads: true });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    await page.goto(URL_);
    await page.waitForFunction(() => window.WTP && WTP.App && WTP.App.res);
    for (const s of sections) {
      await page.evaluate(s => WTP.App.go(s), s);
      await page.waitForTimeout(80);
      const bad = await page.evaluate(() => document.querySelector('.note.bad') ? document.querySelector('.note.bad').textContent : '');
      if (bad) { errors.push(s + ': ' + bad); }
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
      if (overflow) errors.push(s + ': page wider than the screen');
      if (['library', 'races', 'officials', 'meetings', 'assignments', 'gantt', 'schedules'].includes(s))
        await page.screenshot({ path: `${SHOTS}/${name}-${s}.png` });
    }
    // edits: rename an official, change a start time, lock a row, undo
    const r = await page.evaluate(() => {
      const A = WTP.App, out = {};
      A.go('officials');
      const inp = document.querySelector('[data-k="o0name"]'); inp.value = 'Alex Example'; inp.dispatchEvent(new Event('change'));
      out.renamed = Object.values(A.ev.assignments).some(a => a.official === 'Alex Example');
      A.go('races');
      const st = document.querySelector('[data-k$="-start"]'); st.value = '13:00'; st.dispatchEvent(new Event('change'));
      out.warnings = A.res.warnings.length;
      A.go('assignments');
      const sel = document.querySelector('.asg-who select'); sel.value = '__loc'; sel.dispatchEvent(new Event('change'));
      out.loc = A.res.rows.some(x => x.status === 'LOC / volunteer');
      document.getElementById('btn-undo').click();
      out.undone = !A.res.rows.some(x => x.status === 'LOC / volunteer');
      return out;
    });
    if (!r.renamed || !r.loc || !r.undone) errors.push('edit checks failed ' + JSON.stringify(r));
    // exports (downloads in a browser)
    await page.evaluate(() => WTP.App.go('export'));
    for (const label of ['Excel workbook (.xlsx)', 'Calendar (.ics)', 'Plan file (.wtplan.json)']) {
      const [dl] = await Promise.all([page.waitForEvent('download'), page.locator('.exp-row', { hasText: label }).locator('button').click()]);
      const p = await dl.path(); if (!p || fs.statSync(p).size < 200) errors.push('export failed: ' + label);
    }
    // new event dialog
    await page.evaluate(() => WTP.App.go('library'));
    await page.locator('button', { hasText: 'New event' }).first().click();
    await page.locator('dialog [data-k="ne-name"]').fill('Test Cup');
    await page.locator('dialog button', { hasText: 'Create' }).click();
    await page.waitForTimeout(150);
    const created = await page.evaluate(() => WTP.App.ev.event.name === 'Test Cup' && WTP.App.ev.officials.length === 18);
    if (!created) errors.push('new event failed');
    await page.evaluate(() => WTP.App.go('races'));
    await page.screenshot({ path: `${SHOTS}/${name}-newevent-races.png` });
    console.log(name.padEnd(8), errors.length ? 'PROBLEMS:\n  ' + errors.join('\n  ') : 'ok – all sections, edits, exports, new event');
    problems += errors.length;
    await ctx.close();
  }
  await browser.close();
  process.exit(problems ? 1 : 0);
})();
