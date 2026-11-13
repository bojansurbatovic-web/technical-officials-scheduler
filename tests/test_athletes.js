// Athletes' guide: only athlete-facing items, correct times, standalone HTML and calendar.
const assert = require('assert');
const W = require('./load')(['reference.js', 'engine.js', 'exporters.js', 'athletes.js']);
const { E, Athletes } = W;
const golden = require('./golden.json');
const ev = E.normalise(JSON.parse(JSON.stringify(golden.find(g => g.name === 'example_q3').input)));
E.autoAssign(ev); const res = E.evaluate(ev);
const items = Athletes.items(ev, res, '');
const titles = items.map(i => i.title).join(' | ');
// no officials' meetings or jobs
for (const bad of ['TOs', 'Jury', 'rehearsal', 'drivers', 'Medical', 'TO briefing', 'de-briefing', 'Timing', 'TV']) assert(!titles.includes(bad), 'leaked: ' + bad);
// briefing at 16:00 the day before the first race, check-in before it
const first = E.racesSorted(ev)[0], dayBefore = E.addDays(E.raceDate(ev, first), -1);
const brief = items.find(i => i.kind === 'athletes_briefing');
assert.strictEqual(brief.date, dayBefore); assert.strictEqual(E.fmtHHMM(brief.s % 1440), '16:00');
assert(items.find(i => i.kind === 'briefing_checkin').s < brief.s);
assert(items.some(i => i.kind === 'swim_fam') && items.some(i => i.kind === 'bike_fam'));
// race day: each race has start, transition and lounge times in order
for (const r of ev.races) {
  const mine = items.filter(i => i.race_id === r.id);
  const t = k => mine.find(i => i.kind === k).s;
  assert(t('lounge_open') < t('tz_close') && t('tz_close') < t('start') && t('start') < t('winner') && t('winner') < t('protest_close'));
}
// one race only
const one = Athletes.items(ev, res, ev.races[1].id);
assert(one.every(i => i.race_id === ev.races[1].id || i.race_id === 'session'));
assert(!one.some(i => i.race_id === ev.races[0].id));
// HTML and calendar
ev.event.athletes = { briefing_location: 'Hall <A>', office: '', notes: 'Bring ID' };
const html = Athletes.html(ev, res, '');
assert(html.startsWith('<!DOCTYPE html>') && html.includes('Hall &lt;A&gt;') && html.includes('16:00') && html.includes('Key rules') && !html.includes('Jury meeting'));
const ics = Athletes.ics(ev, res, '');
assert(ics.includes('BEGIN:VCALENDAR') && ics.includes('LOCATION:Hall <A>') && (ics.match(/BEGIN:VEVENT/g) || []).length === items.length);
assert.strictEqual(JSON.stringify(Athletes.course(ev, ev.races[0]).map(c => c[0])), JSON.stringify(['Swim', 'Bike', 'Run', 'Wheel stations', 'Aid stations (run)']));
console.log(`athletes' guide ok – ${items.length} items, no officials' meetings`);
