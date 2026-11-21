// Race card panels (Course, Paces, Daylight and tides) stay open or closed while the person edits fields inside them.
const { chromium } = require('playwright');
const URL = process.env.APP_URL || 'http://localhost:8765/index.html';
(async () => {
  const b = await chromium.launch(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {});
  const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = []; p.on('pageerror', e => errors.push(String(e)));
  await p.goto(URL);
  await p.waitForFunction(() => window.WTP && WTP.App && WTP.App.res);
  await p.evaluate(() => WTP.App.go('races'));
  const rid = await p.evaluate(() => WTP.App.ev.races[0].id);
  const card = () => p.locator('.race-card').first();
  const isOpen = name => card().locator('details.adv', { has: p.locator('summary', { hasText: name }) }).evaluate(d => d.open);
  const res = {};

  // open Course, type into three fields one after another, Tab between them like a person would
  await card().locator('summary', { hasText: 'Course, laps and stations' }).click();
  for (const [key, val] of [['swim', '1600'], ['bike', '42'], ['ls', '3']]) {
    const f = p.locator(`[data-k="r-${rid}-${key}"]`);
    await f.click(); await f.press('Control+A'); await p.keyboard.type(val); await p.keyboard.press('Tab');
    await p.waitForTimeout(100);
    res['course after ' + key] = await isOpen('Course, laps and stations');
  }
  res.values = await p.evaluate(() => { const r = WTP.App.ev.races[0]; return [r.swim_m, r.bike_km, r.laps.swim]; });

  // open Paces, edit a pace and a schedule time
  await card().locator('summary', { hasText: 'Paces, field spread' }).click();
  const sp = p.locator(`[data-k="r-${rid}-sp"]`); await sp.fill('1.25'); await sp.press('Tab'); await p.waitForTimeout(100);
  res.pacesOpen = await isOpen('Paces, field spread');
  res.courseStillOpen = await isOpen('Course, laps and stations');

  // Daylight and tides: open, add a tide, type its height
  await card().locator('summary', { hasText: 'Daylight and tides' }).click();
  await card().getByRole('button', { name: 'Add high or low water' }).click(); await p.waitForTimeout(100);
  const th = p.locator(`[data-k="r-${rid}-th0"]`); await th.fill('0.8 m'); await th.press('Tab'); await p.waitForTimeout(100);
  res.sunOpen = await isOpen('Daylight and tides');

  // closing with the triangle sticks, also after more edits
  await card().locator('summary', { hasText: 'Course, laps and stations' }).click();
  await sp.fill('1.3'); await sp.press('Tab'); await p.waitForTimeout(100);
  res.courseClosedAfterEdit = !(await isOpen('Course, laps and stations'));
  res.pacesStillOpen = await isOpen('Paces, field spread');

  // other races keep their own state: a second race starts closed
  await p.evaluate(() => { const A = WTP.App; if (A.ev.races.length < 2) A.edit(() => { const c = JSON.parse(JSON.stringify(A.ev.races[0])); c.id = WTP.E.newId('r'); A.ev.races.push(c); }); });
  res.secondClosed = await p.locator('.race-card').nth(1).locator('details.adv[open]').count() === 0 ||
    await p.evaluate(() => { const r = WTP.App.ev.races[1], d = WTP.E.daylight(r); return !!(d.moved || !d.ok); });

  console.log(res, errors);
  const ok = Object.keys(res).filter(k => k.startsWith('course after')).every(k => res[k]) &&
    JSON.stringify(res.values) === '[1600,42,3]' && res.pacesOpen && res.courseStillOpen && res.sunOpen &&
    res.courseClosedAfterEdit && res.pacesStillOpen && res.secondClosed && !errors.length;
  console.log(ok ? 'panels ui ok' : 'panels ui FAILED');
  await b.close(); process.exit(ok ? 0 : 1);
})();
