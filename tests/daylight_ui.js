// Sunrise / sunset from the venue, daylight-moved starts, tides, TO levels and What's new – through the screens.
const { chromium } = require('playwright');
const URL = process.env.APP_URL || 'http://localhost:8765/index.html';
(async () => {
  const b = await chromium.launch(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {});
  const p = await b.newPage({ viewport: { width: 1280, height: 900 }, timezoneId: 'Europe/Zagreb' });
  const errors = []; p.on('pageerror', e => errors.push(String(e)));
  await p.goto(URL);
  await p.waitForFunction(() => window.WTP && WTP.App && WTP.App.res);
  // a coastal venue (Split, Croatia) on 12 September 2026, first race planned before sunrise
  await p.evaluate(() => { const A = WTP.App; A.edit(() => { A.ev.event.date = '2026-09-12'; A.ev.races.forEach(r => r.date = ''); A.ev.races[0].start = '06:15'; }); A.go('event'); });
  const loc = p.locator('[data-k="ev-loc"]'); await loc.fill('43.5081, 16.4402'); await loc.dispatchEvent('change');
  const tz = p.locator('[data-k="ev-tz"]'); await tz.fill('Europe/Zagreb'); await tz.dispatchEvent('change');
  await p.waitForTimeout(200);
  const ev1 = await p.evaluate(() => { const A = WTP.App, r = A.ev.races[0], d = WTP.E.daylight(r);
    return { sunrise: r.sunrise, sunset: r.sunset, moved: d.moved, start: WTP.E.fmtHHMM(A.res.timelines[r.id].start % 1440), notes: A.res.daylight,
      table: document.querySelector('.tbl.compact') ? document.querySelector('.tbl.compact').innerText : '' }; });
  // races page: the daylight box, a tide, notes
  await p.evaluate(() => WTP.App.go('races'));
  const rid = await p.evaluate(() => WTP.App.ev.races[0].id);
  await p.locator('.race-card').first().locator('summary', { hasText: 'Daylight and tides' }).waitFor();
  await p.locator('.race-card').first().getByRole('button', { name: 'Add high or low water' }).click();
  const tt = p.locator(`[data-k="r-${rid}-tt0"]`); await tt.fill('08:40'); await tt.dispatchEvent('change');
  const th = p.locator(`[data-k="r-${rid}-th0"]`); await th.fill('1.3 m'); await th.dispatchEvent('change');
  const raceText = await p.locator('.race-card').first().innerText();
  // officials: a certification level
  await p.evaluate(() => WTP.App.go('officials'));
  await p.locator('[data-k="o0lvl"]').selectOption('3b');
  const level = await p.evaluate(() => WTP.App.ev.officials[0].level);
  // exports and athletes' guide carry the new information
  const out = await p.evaluate(() => { const A = WTP.App, X = WTP.X, G = WTP.Athletes;
    const t = X.buildTables(A.ev, A.res), off = t.find(s => s[0] === 'Officials')[1], tl = t.find(s => s[0] === 'Race timeline')[1];
    const head = tl.find(r => r[0] === 'Race'), row = tl[tl.indexOf(head) + 1];
    return { offHead: off[0], off1: off[1], tlHead: head, tlRow: row, guide: G.html(A.ev, A.res, '') }; });
  // What's new
  await p.evaluate(() => WTP.App.go('whatsnew'));
  const wn = await p.locator('main, #content, body').first().innerText();
  console.log({ ev1, level, offLevel: out.off1[7], tlRow: out.tlRow.slice(11), errors });
  const ok = ev1.sunrise === '06:30' && /^19:1\d$/.test(ev1.sunset) && ev1.moved === 'sunrise' && ev1.start === '06:45' &&
    /start moved from 06:15 to 06:45/.test(ev1.notes.join(' ')) && /06:30/.test(ev1.table) &&
    /The plan uses 06:45/.test(raceText) && /Rising tide at the start: high water 08:40 \(1\.3 m\)/.test(raceText) &&
    level === '3b' && out.offHead[7] === 'TO level' && out.off1[7] === 'Level 3b' &&
    out.tlHead[12] === 'Sunrise' && out.tlRow[11] === '06:15' && out.tlRow[12] === '06:30' && out.tlRow[14] === 'Start moved to after sunrise' &&
    /Sunrise \/ sunset/.test(out.guide) && /High water 08:40 \(1\.3 m\)/.test(out.guide) &&
    /Version 1\.0\.3/.test(wn) && /TO certification level/.test(wn) && !errors.length;
  console.log(ok ? 'daylight ui ok' : 'daylight ui FAILED');
  await b.close(); process.exit(ok ? 0 : 1);
})();
