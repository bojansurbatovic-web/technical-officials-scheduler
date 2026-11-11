// Checks the JS engine against tests/golden.json (made by the Python engine of the Ubuntu app).
const assert = require('assert');
const W = require('./load')(['reference.js', 'engine.js']);
const E = W.E;
const golden = require('./golden.json');
const rnd = x => x == null ? null : Math.round(x * 1e6) / 1e6;
let fails = 0;
function same(name, what, a, b) {
  a = JSON.parse(JSON.stringify(a)); b = JSON.parse(JSON.stringify(b));
  try { assert.deepStrictEqual(a, b); }
  catch (e) {
    fails++;
    console.log(`FAIL ${name}: ${what}`);
    const A = JSON.stringify(a), B = JSON.stringify(b);
    let i = 0; while (i < A.length && A[i] === B[i]) i++;
    console.log('   js:', A.slice(Math.max(0, i - 120), i + 160));
    console.log('   py:', B.slice(Math.max(0, i - 120), i + 160));
  }
}
for (const g of golden) {
  const ev = JSON.parse(JSON.stringify(g.input));
  E.normalise(ev);
  E.autoAssign(ev, true);
  const res = E.evaluate(ev), x = g.expected;
  const sk = o => Object.fromEntries(Object.keys(o).sort().map(k => [k, o[k]]));
  same(g.name, 'assignments', sk(ev.assignments), sk(x.assignments));
  same(g.name, 'timelines', Object.fromEntries(Object.entries(res.timelines).map(([k, tl]) =>
    [k, Object.fromEntries(Object.entries(tl).filter(([m]) => m !== '_segments').map(([m, v]) => [m, rnd(v)]))])), x.timelines);
  same(g.name, 'sessions', res.sessions.map(s => [s.id, s.date, rnd(s.start), rnd(s.end), s.enabled, s.people, s.name, rnd(s.s)]), x.sessions);
  same(g.name, 'rows', res.rows.map(r => [r.key, r.official, r.status, r.role, rnd(r.start), rnd(r.end), r.date, r.race]), x.rows);
  same(g.name, 'conflicts', res.conflicts.map(c => [c.official, c.a, c.b, c.level, c.gap, c.a_time, c.b_time]), x.conflicts);
  same(g.name, 'officials', res.officials.map(o => [o.name, o.primary, o.secondary, o.conflicts, o.duties.length, rnd(o.busy_min), o.races]), x.officials);
  same(g.name, 'wt', res.wt_officials.map(w => [w.name, w.duties.length, w.conflicts]), x.wt);
  same(g.name, 'radios', res.radios, x.radios);
  same(g.name, 'warnings', res.warnings, x.warnings);
  same(g.name, 'dates', res.dates, x.dates);
  same(g.name, 'counts', [res.multiday, res.n_conflict, res.n_tight], [x.multiday, x.n_conflict, x.n_tight]);
  same(g.name, 'fmt', [0, 599.5, 1439.99, 1500.25, 3000].map(res.fmt), x.fmt);
  same(g.name, 'run_sheet', E.runSheet(ev, res).map(r => [r.race, r.item, rnd(r.time)]), x.run_sheet);
  console.log((fails ? '..' : 'ok') + `  ${g.name}`);
}
// a few unit checks
assert.strictEqual(E.fmtHHMM(600.5), '10:01');
assert.strictEqual(E.fmtHHMM(-15), '-00:15');
assert.strictEqual(E.parseHHMM('9h05'), 545);
assert.strictEqual(E.parseHHMM('25:00'), null);
assert.strictEqual(E.parseDate('2027-02-30'), null);
assert.strictEqual(E.dayLabel('2026-11-21'), 'Sat 21.11.');
assert.strictEqual(E.protestMinutes({ format: 'long', category: 'elite_men' }), 45);
if (fails) { console.log(fails + ' differences'); process.exit(1); }
console.log(golden.length + ' golden events reproduced exactly');
