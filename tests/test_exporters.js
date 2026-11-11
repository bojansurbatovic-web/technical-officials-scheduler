// The JS exporters must build the same tables and calendar as the Python exporters.
const assert = require('assert');
const W = require('./load')(['reference.js', 'engine.js', 'exporters.js']);
const { E, X } = W;
const golden = require('./golden.json'), gt = require('./golden_tables.json');
const plain = x => JSON.parse(JSON.stringify(x));
let n = 0;
for (const name of Object.keys(gt)) {
  const ev = E.normalise(plain(golden.find(g => g.name === name).input));
  E.autoAssign(ev); const res = E.evaluate(ev);
  const tables = plain(X.buildTables(ev, res));
  const exp = gt[name].tables;
  assert.strictEqual(tables.length, exp.length, name + ' sheet count');
  tables.forEach((t, i) => {
    const sheet = exp[i][0];
    if (sheet === 'Settings & references') t[1] = t[1].slice(0, 30), exp[i][1] = exp[i][1].slice(0, 30);
    assert.strictEqual(t[0], sheet);
    t[1].forEach((row, r) => assert.deepStrictEqual(row, exp[i][1][r], `${name} / ${sheet} row ${r}`));
    assert.strictEqual(t[1].length, exp[i][1].length, `${name} / ${sheet} rows`);
    assert.deepStrictEqual(t[2], exp[i][2], `${name} / ${sheet} widths`);
    assert.deepStrictEqual(t[3], exp[i][3], `${name} / ${sheet} styles`);
  });
  const ics = X.ics(ev, res).split('\r\n').filter(l => !l.startsWith('DTSTAMP') && !l.startsWith('UID:duty') && !l.startsWith('PRODID'))
    .map(l => l.replace('@toscheduler', '@wtplanner'));
  assert.deepStrictEqual(ics, gt[name].ics, name + ' ics');
  const svg = X.ganttSvg(ev, res);
  assert.strictEqual((svg.match(/<rect/g) || []).length, gt[name].svg_rects, name + ' svg bars');
  const fs = require('fs'), dir = process.env.OUT || '/tmp';
  fs.writeFileSync(`${dir}/${name}.xlsx`, X.xlsx(ev, res)); fs.writeFileSync(`${dir}/${name}.ods`, X.ods(ev, res));
  fs.writeFileSync(`${dir}/${name}.svg`, svg);
  console.log('ok ', name); n++;
}
console.log(n + ' events: tables, styles, calendar and Gantt match the Ubuntu app');
