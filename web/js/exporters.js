/* Exports without libraries: XLSX, ODS (stored ZIP), JSON, ICS, SVG Gantt. Port of exporters.py. */
var WTP = (typeof WTP !== 'undefined') ? WTP : {};
(function (W) {
  'use strict';
  var E = W.E, ref = W.ref, X = {};
  var SESSION_COLOUR = X.SESSION_COLOUR = '#7B4FA0';
  var RACE_COLOURS = X.RACE_COLOURS = ['#3B7DD8', '#E8743B', '#2E9E5B', '#8E5BD0', '#C9A227', '#D04F7A', '#4BA3A3', '#7A7A7A'];
  var STATUS_COLOURS = X.STATUS_COLOURS = { 'OK': '#C6EFCE', 'TIGHT': '#FFEB9C', 'CONFLICT': '#FFC7CE', 'UNFILLED': '#F4B183',
    'LOC / volunteer': '#DDEBF7' };
  var cmp = E._h.cmp, sortBy = E._h.sortBy;

  function hex2(n) { var s = n.toString(16).toUpperCase(); return s.length < 2 ? '0' + s : s; }
  X.lighten = function (c, f) {
    f = f === undefined ? 0.55 : f;
    var h = c.replace('#', ''), rgb = [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16); });
    return '#' + rgb.map(function (v) { return hex2(Math.trunc(v + (255 - v) * f)); }).join('');
  };
  X.raceColour = function (ev, rid) {
    if (rid === 'session') return SESSION_COLOUR;
    if (E.isDayKey(rid)) return '#5A5A5A';
    var ids = E.racesSorted(ev).map(function (r) { return r.id; }), i = ids.indexOf(rid);
    return i >= 0 ? RACE_COLOURS[i % RACE_COLOURS.length] : '#5A5A5A';
  };
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
  }
  X.esc = esc;
  function wtPeople(res) { return (res.wt_officials || []).filter(function (w) { return w.duties.length; }); }
  X.wtPeople = wtPeople;
  function round1(x) { return Math.round(x * 10) / 10; }

  // ============================================================ tables shared by XLSX / ODS
  X.buildTables = function (ev, res) {
    res = res || E.evaluate(ev);
    var sheets = [], e = ev.event, fmt = res.fmt, races = E.racesSorted(ev);
    var raceIds = races.map(function (r) { return r.id; });
    var rows, styles, tw = res.multiday ? 16 : 8;
    function st(r, c, s) { styles[r + ',' + c] = s; }

    rows = [['Position', 'Race', 'Name and surname', 'Role', 'From', 'To', 'Status', 'Locked', 'TOC / CR']]; styles = {};
    res.rows.forEach(function (r) {
      rows.push([r.title, r.race, r.official || '—', r.role || '', fmt(r.start), fmt(r.end), r.status, r.locked ? 'yes' : '', r.toc]);
      st(rows.length - 1, 6, 'st_' + r.status);
    });
    sheets.push(['Assignments', rows, [40, 26, 24, 11, tw, tw, 14, 8, 18], styles]);

    rows = [['Name and surname', 'Country', 'Primary position', 'Secondary position(s)', 'Busy (h)', 'Radio', 'Conflicts']]; styles = {};
    var offmap = {}; ev.officials.forEach(function (o) { offmap[o.name] = o; });
    res.officials.forEach(function (o) {
      var om = offmap[o.name] || {};
      rows.push([o.name, o.country, o.primary || '—', o.secondary.join('; ') || '—', round1(o.busy_min / 60),
        om.radio === false ? 'no' : 'yes', o.conflicts]);
      if (o.conflicts) st(rows.length - 1, 6, 'st_CONFLICT');
    });
    rows.push([]);
    rows.push(['World Triathlon officials (not TOs)', '', '', '', '', '', '']); st(rows.length - 1, 0, 'bold');
    rows.push(['Technical Delegate', '', e.td || '—', 'Chair of the Competition Jury', '', e.td ? 'yes' : '', '']);
    rows.push(['Medical Delegate', '', e.md || '—', '', '', e.md ? 'yes' : '', '']);
    (e.jury || []).forEach(function (n, j) {
      rows.push(['Competition Jury – member ' + (j + 2), '', n || 'to be appointed by TD', 'not a TO, coach or athlete (CR 12.6)', '', '', '']);
    });
    rows.push([]);
    var rd = res.radios;
    rows.push(['Radios (TO talk group)', '', '', '', '', '', '']); st(rows.length - 1, 0, 'bold');
    rows.push(['Personal radios', rd.personal, 'one per TO + TD + MD', '', '', '', '']);
    rows.push(['VCC base radio', rd.vcc, 'EOM 6.6.2 a', '', '', '', '']);
    rows.push(['Spares', rd.spare, (e.spare_pct == null ? 10 : e.spare_pct) + ' % rounded up', '', '', '', '']);
    rows.push(['TOTAL', rd.total, 'EOM: min. 12, TO equipment list 25', '', '', '', '']); st(rows.length - 1, 0, 'bold');
    sheets.push(['Officials', rows, [30, 10, 34, 60, 9, 7, 10], styles]);

    rows = [['Name and surname'].concat(races.map(function (r) { return r.name + ' (' + fmt(res.timelines[r.id].start) + ')'; }))]; styles = {};
    ev.officials.forEach(function (o) {
      rows.push([o.name].concat(races.map(function (r) { return E.takesPart(o, r.id) ? '✓' : '—'; })));
      races.forEach(function (r, ci) { st(rows.length - 1, ci + 1, E.takesPart(o, r.id) ? 'st_OK' : 'default'); });
    });
    rows.push(['Officials per race'].concat(races.map(function (r) {
      return ev.officials.filter(function (o) { return E.takesPart(o, r.id); }).length;
    })));
    st(rows.length - 1, 0, 'bold');
    sheets.push(['Participation', rows, [26].concat(races.map(function () { return 24; })), styles]);

    rows = [['Name and surname', 'From', 'To', 'Position', 'Race', 'Duty', 'Role', 'Status']]; styles = {};
    res.officials.concat(wtPeople(res)).forEach(function (o) {
      o.duties.forEach(function (d) {
        d.windows.slice().sort(cmp).forEach(function (w) {
          rows.push([o.name, fmt(w[0]), fmt(w[1]), d.title, d.race, w[2] + (w[3] ? '' : ' (non-blocking)'), d.role, d.status]);
          st(rows.length - 1, 7, 'st_' + d.status);
        });
      });
    });
    sheets.push(['Personal schedules', rows, [24, tw, tw, 38, 24, 40, 11, 12], styles]);

    rows = [['Time', 'Race', 'Milestone']]; styles = {};
    E.runSheet(ev, res).forEach(function (m) {
      rows.push([fmt(m.time), m.race, m.item]);
      if (m.key === 'start') st(rows.length - 1, 2, 'bold');
    });
    rows.push([]);
    rows.push(['Race', 'Format', 'Category', 'Start', 'Swim', 'T1', 'Bike', 'T2', 'Run', 'Winner', 'Last finisher']);
    for (var c = 0; c < 11; c++) st(rows.length - 1, c, 'header');
    races.forEach(function (r) {
      var tl = res.timelines[r.id], sg = tl._segments;
      rows.push([r.name, ref.FORMATS[r.format].label, ref.CATEGORIES[r.category].label, fmt(tl.start),
        E.fmtDur(sg.swim), E.fmtDur(sg.t1), E.fmtDur(sg.bike), E.fmtDur(sg.t2), E.fmtDur(sg.run), fmt(tl.winner), fmt(tl.last_finisher)]);
    });
    sheets.push(['Race timeline', rows, [26, 34, 26, tw, 8, 7, 8, 7, 8, tw, 14], styles]);

    rows = [['Date', 'From', 'To', 'Meeting / briefing', 'Who must attend', 'People', 'Rule / reference', 'In plan']]; styles = {};
    sortBy(res.sessions, function (x) { return [x.s, x.e]; }).forEach(function (se) {
      rows.push([E.dayLabel(se.date) + ' ' + se.date, E.fmtHHMM(se.start), E.fmtHHMM(se.end), se.name + (se.edited ? ' (edited)' : ''),
        E.attendeeLabel(se.attendees), (se.people || []).join(', ') || '—', se.ref, se.enabled ? 'yes' : 'no (not scheduled)']);
      st(rows.length - 1, 7, se.enabled ? 'st_OK' : 'default');
      if (se.key === 'athletes_briefing' && se.enabled) st(rows.length - 1, 3, 'bold');
    });
    sheets.push(['Meetings & briefings', rows, [18, 7, 7, 42, 46, 60, 60, 16], styles]);

    var base = E.baseDate(ev);
    res.dates.forEach(function (day) {
      var lo = E.diffDays(day, base) * 1440, span = X.span(res, lo), t0 = span[0], t1 = span[1], step = 5, times = [];
      for (var t = t0; t <= t1; t += step) times.push(t);
      rows = [['Name and surname', 'Primary'].concat(times.map(function (t) { return E.fmtHHMM(t - lo); }))]; styles = {};
      res.officials.concat(wtPeople(res)).forEach(function (o) {
        var row = [o.name, o.primary || o.role || ''].concat(times.map(function () { return ''; }));
        o.duties.forEach(function (d) {
          d.windows.forEach(function (w) {
            if (!w[3] || w[1] <= t0 || w[0] >= t1 + step) return;
            times.forEach(function (t, ci) {
              if (t + step > w[0] && t < w[1]) {
                var idx = 2 + ci, rid = d.race_id, s;
                if (rid === 'session') s = 'g_sess';
                else if (E.isDayKey(rid) || raceIds.indexOf(rid) < 0) s = 'g_all';
                else s = 'g' + (raceIds.indexOf(rid) % RACE_COLOURS.length);
                if (d.role === 'Secondary') s += 's';
                if (d.status === 'CONFLICT') s = 'st_CONFLICT';
                styles[rows.length + ',' + idx] = s;
                row[idx] = d.role === 'Secondary' ? 'S' : (rid === 'session' ? 'M' : '');
              }
            });
          });
        });
        rows.push(row);
      });
      sheets.push([res.multiday ? 'Gantt ' + E.dayLabel(day) : 'Gantt', rows, [24, 26].concat(times.map(function () { return 3; })), styles]);
    });

    rows = [['Level', 'Name and surname', 'Position A', 'Duty A', 'Time A', 'Position B', 'Duty B', 'Time B', 'Gap (min)']]; styles = {};
    res.conflicts.forEach(function (c) {
      rows.push([c.level, c.official, c.a, c.a_label, c.a_time, c.b, c.b_label, c.b_time, c.gap === null ? '' : c.gap]);
      st(rows.length - 1, 0, 'st_' + c.level);
    });
    res.warnings.forEach(function (w) { rows.push(['WARNING', '', w, '', '', '', '', '', '']); st(rows.length - 1, 0, 'st_TIGHT'); });
    res.unfilled.forEach(function (u) {
      rows.push(['UNFILLED', '', u.title, '', fmt(u.start) + '–' + E.fmtHHMM(u.end % 1440), u.race, '', '', '']);
      st(rows.length - 1, 0, 'st_UNFILLED');
    });
    if (rows.length === 1) { rows.push(['OK', 'No conflicts and nothing unfilled', '', '', '', '', '', '', '']); st(1, 0, 'st_OK'); }
    sheets.push(['Conflicts', rows, [12, 24, 36, 30, 13, 36, 30, 13, 9], styles]);

    rows = [['Event', e.name || ''], ['Venue', e.venue || ''], ['Date(s)', res.dates.join(', ')], []];
    styles = { '4,0': 'header', '4,1': 'header', '4,2': 'header' };
    rows.push(['Duty parameter', 'Minutes', 'Source']);
    ref.DUTY_DEFAULTS.forEach(function (d) { rows.push([d[2], ev.settings[d[0]], d[3]]); });
    rows.push([]);
    ref.REFERENCES.trim().split('\n').forEach(function (line) { rows.push([line]); });
    sheets.push(['Settings & references', rows, [60, 10, 50], styles]);
    return sheets;
  };

  X.span = function (res, lo) {
    function inside(t) { return lo === undefined || lo === null || (lo <= t && t < lo + 1440); }
    var vals = [];
    res.rows.forEach(function (r) { if (r.start !== null && inside(r.start)) vals.push(r.start, r.end); });
    Object.keys(res.timelines).forEach(function (k) {
      var tl = res.timelines[k];
      if (inside(tl.start)) vals.push(tl.lounge_open, tl.last_finisher);
    });
    res.sessions.forEach(function (se) { if (se.enabled && inside(se.s)) vals.push(se.s, se.e); });
    if (!vals.length) { var l = lo || 0; return [l + 480, l + 720]; }
    var mn = Math.trunc(Math.min.apply(null, vals)), mx = Math.trunc(Math.max.apply(null, vals));
    return [Math.floor(mn / 15) * 15, Math.floor((mx + 14) / 15) * 15];
  };

  function styleTable() {
    var s = { 'default': [null, false, null], header: ['#1F3864', true, '#FFFFFF'], bold: [null, true, null] };
    Object.keys(STATUS_COLOURS).forEach(function (k) { s['st_' + k] = [STATUS_COLOURS[k], true, null]; });
    s.st_ = [null, false, null];
    RACE_COLOURS.forEach(function (c, i) { s['g' + i] = [c, false, '#FFFFFF']; s['g' + i + 's'] = [X.lighten(c), false, '#000000']; });
    s.g_all = ['#5A5A5A', false, '#FFFFFF']; s.g_alls = ['#AAAAAA', false, '#000000'];
    s.g_sess = [SESSION_COLOUR, false, '#FFFFFF']; s.g_sesss = [X.lighten(SESSION_COLOUR), false, '#000000'];
    return s;
  }

  // ============================================================ ZIP (stored, no compression)
  var CRC = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
    return t;
  })();
  function crc32(b) { var c = 0xFFFFFFFF; for (var i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
  function utf8(s) { return new TextEncoder().encode(s); }
  X.utf8 = utf8;
  X.zip = function (files) {     // files: [[name, string|Uint8Array], ...]
    var parts = [], central = [], offset = 0, now = new Date();
    var dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1);
    var dosDate = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
    function u16(a, v) { a.push(v & 255, (v >>> 8) & 255); }
    function u32(a, v) { a.push(v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255); }
    files.forEach(function (f) {
      var name = utf8(f[0]), data = typeof f[1] === 'string' ? utf8(f[1]) : f[1], crc = crc32(data), h = [];
      u32(h, 0x04034b50); u16(h, 20); u16(h, 0x0800); u16(h, 0); u16(h, dosTime); u16(h, dosDate);
      u32(h, crc); u32(h, data.length); u32(h, data.length); u16(h, name.length); u16(h, 0);
      parts.push(new Uint8Array(h), name, data);
      var c = [];
      u32(c, 0x02014b50); u16(c, 20); u16(c, 20); u16(c, 0x0800); u16(c, 0); u16(c, dosTime); u16(c, dosDate);
      u32(c, crc); u32(c, data.length); u32(c, data.length); u16(c, name.length); u16(c, 0); u16(c, 0); u16(c, 0); u16(c, 0);
      u32(c, 0); u32(c, offset);
      central.push(new Uint8Array(c), name);
      offset += h.length + name.length + data.length;
    });
    var csize = central.reduce(function (a, p) { return a + p.length; }, 0), end = [];
    u32(end, 0x06054b50); u16(end, 0); u16(end, 0); u16(end, files.length); u16(end, files.length);
    u32(end, csize); u32(end, offset); u16(end, 0);
    var all = parts.concat(central, [new Uint8Array(end)]);
    var out = new Uint8Array(all.reduce(function (a, p) { return a + p.length; }, 0)), pos = 0;
    all.forEach(function (p) { out.set(p, pos); pos += p.length; });
    return out;
  };

  // ============================================================ XLSX
  function col(n) { var s = ''; n += 1; while (n) { var r = (n - 1) % 26; n = Math.floor((n - 1) / 26); s = String.fromCharCode(65 + r) + s; } return s; }
  function isNum(v) { return typeof v === 'number' && isFinite(v); }
  X.xlsx = function (ev, res) {
    var sheets = X.buildTables(ev, res), sd = styleTable(), names = Object.keys(sd);
    var fills = ['<fill><patternFill patternType="none"/></fill>', '<fill><patternFill patternType="gray125"/></fill>'];
    var fonts = ['<font><sz val="10"/><name val="Arial"/></font>'], xfs = [], idx = {};
    names.forEach(function (n, i) {
      var d = sd[n], fi = 0, fo = 0;
      if (d[0]) { fills.push('<fill><patternFill patternType="solid"><fgColor rgb="FF' + d[0].slice(1) + '"/><bgColor indexed="64"/></patternFill></fill>'); fi = fills.length - 1; }
      if (d[1] || d[2]) {
        fonts.push('<font>' + (d[1] ? '<b/>' : '') + '<sz val="10"/>' + (d[2] ? '<color rgb="FF' + d[2].slice(1) + '"/>' : '') + '<name val="Arial"/></font>');
        fo = fonts.length - 1;
      }
      xfs.push('<xf numFmtId="0" fontId="' + fo + '" fillId="' + fi + '" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment vertical="top" wrapText="0"/></xf>');
      idx[n] = i;
    });
    var hdr = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>';
    var stylesXml = hdr + '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
      '<fonts count="' + fonts.length + '">' + fonts.join('') + '</fonts><fills count="' + fills.length + '">' + fills.join('') + '</fills>' +
      '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>' +
      '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
      '<cellXfs count="' + xfs.length + '">' + xfs.join('') + '</cellXfs>' +
      '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>';
    var files = [], sheetFiles = [];
    sheets.forEach(function (sh, si) {
      var name = sh[0], rows = sh[1], widths = sh[2], styles = sh[3];
      var cols = widths.map(function (w, i) { return '<col min="' + (i + 1) + '" max="' + (i + 1) + '" width="' + w + '" customWidth="1"/>'; }).join('');
      var out = rows.map(function (row, ri) {
        var cells = row.map(function (v, ci) {
          var stn = styles[ri + ',' + ci] || (ri === 0 ? 'header' : 'default'), s = idx[stn] || 0, r = col(ci) + (ri + 1);
          if (v === null || v === undefined || v === '') return s ? '<c r="' + r + '" s="' + s + '"/>' : '';
          if (typeof v === 'boolean') v = v ? 'yes' : 'no';
          if (isNum(v)) return '<c r="' + r + '" s="' + s + '"><v>' + v + '</v></c>';
          return '<c r="' + r + '" s="' + s + '" t="inlineStr"><is><t xml:space="preserve">' + esc(v) + '</t></is></c>';
        }).join('');
        return '<row r="' + (ri + 1) + '">' + cells + '</row>';
      }).join('');
      var freeze = name.indexOf('Gantt') === 0 ?
        '<sheetViews><sheetView workbookViewId="0"><pane xSplit="2" ySplit="1" topLeftCell="C2" activePane="bottomRight" state="frozen"/></sheetView></sheetViews>' :
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>';
      sheetFiles.push(['xl/worksheets/sheet' + (si + 1) + '.xml', hdr + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
        freeze + '<cols>' + cols + '</cols><sheetData>' + out + '</sheetData></worksheet>']);
    });
    var wb = hdr + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' +
      sheets.map(function (s, i) { return '<sheet name="' + esc(s[0].slice(0, 31)) + '" sheetId="' + (i + 1) + '" r:id="rId' + (i + 1) + '"/>'; }).join('') + '</sheets></workbook>';
    var rels = hdr + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      sheets.map(function (s, i) { return '<Relationship Id="rId' + (i + 1) + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet' + (i + 1) + '.xml"/>'; }).join('') +
      '<Relationship Id="rId' + (sheets.length + 1) + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>';
    var ctypes = hdr + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>' +
      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
      '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
      sheets.map(function (s, i) { return '<Override PartName="/xl/worksheets/sheet' + (i + 1) + '.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'; }).join('') + '</Types>';
    var rootRels = hdr + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>';
    files.push(['[Content_Types].xml', ctypes], ['_rels/.rels', rootRels], ['xl/workbook.xml', wb], ['xl/_rels/workbook.xml.rels', rels], ['xl/styles.xml', stylesXml]);
    return X.zip(files.concat(sheetFiles));
  };

  // ============================================================ ODS
  X.ods = function (ev, res) {
    var sheets = X.buildTables(ev, res), sd = styleTable(), auto = [], colstyles = {}, colOrder = [], tables = [];
    Object.keys(sd).forEach(function (n) {
      var d = sd[n], props = d[0] ? '<style:table-cell-properties fo:background-color="' + d[0] + '"/>' : '', tp = '';
      if (d[1] || d[2]) tp = '<style:text-properties' + (d[1] ? ' fo:font-weight="bold"' : '') + (d[2] ? ' fo:color="' + d[2] + '"' : '') + '/>';
      auto.push('<style:style style:name="c_' + n + '" style:family="table-cell">' + props + tp + '</style:style>');
    });
    sheets.forEach(function (sh) {
      var name = sh[0], rows = sh[1], widths = sh[2], styles = sh[3];
      var cols = widths.map(function (w) {
        var cm = Math.round(Math.max(0.6, w * 0.19) * 100) / 100, sn = 'co' + String(cm).replace('.', '_');
        if (!colstyles[sn]) { colstyles[sn] = cm; colOrder.push(sn); }
        return '<table:table-column table:style-name="' + sn + '"/>';
      }).join('');
      var trs = rows.map(function (row, ri) {
        var tds = row.map(function (v, ci) {
          var stn = styles[ri + ',' + ci] || (ri === 0 ? 'header' : 'default');
          var sa = stn !== 'default' ? ' table:style-name="c_' + stn + '"' : '';
          if (v === null || v === undefined || v === '') return '<table:table-cell' + sa + '/>';
          if (isNum(v)) return '<table:table-cell' + sa + ' office:value-type="float" office:value="' + v + '"><text:p>' + v + '</text:p></table:table-cell>';
          return '<table:table-cell' + sa + ' office:value-type="string"><text:p>' + esc(v) + '</text:p></table:table-cell>';
        }).join('');
        return '<table:table-row>' + (tds || '<table:table-cell/>') + '</table:table-row>';
      }).join('');
      tables.push('<table:table table:name="' + esc(name.slice(0, 31)) + '">' + cols + trs + '</table:table>');
    });
    var colxml = colOrder.map(function (sn) {
      return '<style:style style:name="' + sn + '" style:family="table-column"><style:table-column-properties style:column-width="' + colstyles[sn] + 'cm"/></style:style>';
    }).join('');
    var ns = 'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" ' +
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" ' +
      'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"';
    var content = '<?xml version="1.0" encoding="UTF-8"?><office:document-content ' + ns + ' office:version="1.2"><office:font-face-decls/>' +
      '<office:automatic-styles>' + colxml + auto.join('') + '</office:automatic-styles><office:body><office:spreadsheet>' + tables.join('') +
      '</office:spreadsheet></office:body></office:document-content>';
    var styles = '<?xml version="1.0" encoding="UTF-8"?><office:document-styles ' + ns + ' office:version="1.2"><office:styles>' +
      '<style:default-style style:family="table-cell"><style:text-properties style:font-name="Arial" fo:font-size="10pt"/></style:default-style></office:styles></office:document-styles>';
    var meta = '<?xml version="1.0" encoding="UTF-8"?><office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" ' +
      'xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" office:version="1.2"><office:meta><meta:generator>' +
      esc(ref.APP_NAME + ' ' + ref.APP_VERSION) + '</meta:generator></office:meta></office:document-meta>';
    var manifest = '<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">' +
      '<manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>' +
      '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/><manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>' +
      '<manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/></manifest:manifest>';
    return X.zip([['mimetype', 'application/vnd.oasis.opendocument.spreadsheet'], ['content.xml', content], ['styles.xml', styles],
      ['meta.xml', meta], ['META-INF/manifest.xml', manifest]]);
  };

  // ============================================================ JSON
  X.toJSON = function (ev) {
    var clean = {};
    Object.keys(ev).forEach(function (k) { if (k.charAt(0) !== '_') clean[k] = ev[k]; });
    clean._primary = ev._primary || {};
    return JSON.stringify(clean, null, 2);
  };
  X.fromJSON = function (text) {
    var ev = JSON.parse(text);
    if (!ev || typeof ev !== 'object' || !Array.isArray(ev.races)) throw new Error("Not a Technical Officials Scheduler file (no 'races').");
    return E.normalise(ev);
  };

  // ============================================================ ICS
  function icsText(s) { return String(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\n/g, '\\n'); }
  function hash(s) { var h = 5381; for (var i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0; return h.toString(36); }
  X.ics = function (ev, res, includeDuties) {
    res = res || E.evaluate(ev);
    if (includeDuties === undefined) includeDuties = true;
    var base = E.baseDate(ev), fmt = res.fmt, now = new Date();
    var stamp = now.getUTCFullYear() + pad(now.getUTCMonth() + 1) + pad(now.getUTCDate()) + 'T' + pad(now.getUTCHours()) + pad(now.getUTCMinutes()) + pad(now.getUTCSeconds()) + 'Z';
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    function dt(m) {
      var r = E._h.pyRound(m), days = Math.floor(r / 1440), mins = r - days * 1440, d = E.addDays(base, days).replace(/-/g, '');
      return d + 'T' + pad(Math.floor(mins / 60)) + pad(mins % 60) + '00';
    }
    var venue = icsText(ev.event.venue || ''), L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//' + ref.APP_NAME + '//' + ref.APP_VERSION + '//EN', 'CALSCALE:GREGORIAN'];
    E.racesSorted(ev).forEach(function (r) {
      var tl = res.timelines[r.id];
      L.push('BEGIN:VEVENT', 'UID:race-' + r.id + '-' + base + '@toscheduler', 'DTSTAMP:' + stamp, 'DTSTART:' + dt(tl.lounge_open),
        'DTEND:' + dt(tl.medal + 15), 'SUMMARY:' + icsText(r.name + ' – start ' + fmt(tl.start)), 'LOCATION:' + venue,
        'DESCRIPTION:' + icsText(ref.FORMATS[r.format].label + '\nWinner ≈' + fmt(tl.winner) + ', last finisher ≈' + fmt(tl.last_finisher)), 'END:VEVENT');
    });
    res.sessions.forEach(function (se) {
      if (!se.enabled) return;
      L.push('BEGIN:VEVENT', 'UID:session-' + icsText(se.id) + '-' + base + '@toscheduler', 'DTSTAMP:' + stamp, 'DTSTART:' + dt(se.s), 'DTEND:' + dt(se.e),
        'SUMMARY:' + icsText(se.name), 'LOCATION:' + venue,
        'DESCRIPTION:' + icsText('Attend: ' + E.attendeeLabel(se.attendees) + '\n' + (se.people || []).join(', ') + '\n' + se.ref),
        'CATEGORIES:Meetings & briefings', 'END:VEVENT');
    });
    var n = 0;
    if (includeDuties) {
      res.officials.concat(wtPeople(res)).forEach(function (o) {
        o.duties.forEach(function (d) {
          if (d.kind === 'session') return;
          d.windows.forEach(function (w) {
            if (!w[3]) return;
            n++;
            L.push('BEGIN:VEVENT', 'UID:duty-' + n + '-' + hash(o.name + '|' + d.key + '|' + w[0]) + '@toscheduler', 'DTSTAMP:' + stamp,
              'DTSTART:' + dt(w[0]), 'DTEND:' + dt(w[1]), 'SUMMARY:' + icsText(o.name + ': ' + d.title),
              'DESCRIPTION:' + icsText(w[2] + ' · ' + d.race + ' · ' + d.role), 'CATEGORIES:' + icsText(o.name), 'END:VEVENT');
          });
        });
      });
    }
    L.push('END:VCALENDAR');
    return L.join('\r\n') + '\r\n';
  };

  // ============================================================ SVG Gantt
  function f1(x) { return (Math.round(x * 10) / 10).toFixed(1); }
  X.ganttSvg = function (ev, res, opts) {
    res = res || E.evaluate(ev); opts = opts || {};
    var mode = opts.mode || 'officials', ppm = opts.pxPerMin || 4, dark = !!opts.dark, day = opts.day;
    if (res.dates.indexOf(day) < 0) { var rd = E.raceDates(ev); day = rd.length ? rd[0] : res.dates[0]; }
    var lo = E.diffDays(day, E.baseDate(ev)) * 1440;
    function onDay(w) { return lo <= w[0] && w[0] < lo + 1440; }
    var sp = X.span(res, lo), t0 = sp[0], t1 = sp[1];
    var left = 260, top = 70, rowH = 26, barH = 16;
    var fg = dark ? '#E8E8E8' : '#1A1A1A', bg = dark ? '#1E1E1E' : '#FFFFFF', grid = dark ? '#3A3A3A' : '#E2E2E2', sub = dark ? '#AAAAAA' : '#666666';
    var rows = [];
    if (mode === 'officials') {
      res.officials.concat(wtPeople(res)).forEach(function (o) {
        var items = [];
        o.duties.forEach(function (d) { d.windows.forEach(function (w) { if (onDay(w)) items.push([d, w]); }); });
        rows.push([o.name, o.primary || o.role || '', items]);
      });
      var unf = [];
      res.unfilled.forEach(function (u) { u.windows.forEach(function (w) { if (onDay(w)) unf.push([u, w]); }); });
      if (unf.length) rows.push(['UNFILLED', 'needs a TO or LOC volunteer', unf]);
    } else {
      var by = {}, order = [];
      res.rows.forEach(function (r) {
        if (!by[r.title]) { by[r.title] = []; order.push(r.title); }
        r.windows.forEach(function (w) { if (onDay(w)) by[r.title].push([r, w]); });
      });
      order.forEach(function (t) { rows.push([t, '', by[t]]); });
      res.sessions.forEach(function (se) {
        if (se.enabled && lo <= se.s && se.s < lo + 1440) {
          var d = { title: se.name, race_id: 'session', race: 'Meetings & briefings', role: 'Obligation', status: '', official: (se.people || []).length + ' people' };
          rows.push([se.name, '', [[d, [se.s, se.e, se.name, true, 'session']]]]);
        }
      });
    }
    var races = E.racesSorted(ev).filter(function (r) { var s = res.timelines[r.id].start; return lo <= s && s < lo + 1440; });
    var width = left + Math.trunc((t1 - t0) * ppm) + 40;
    var height = top + rowH * (rows.length + 1) + 30 + 22 * (Math.floor((races.length + 3) / 4) + 1);
    function Xp(t) { return left + (t - t0) * ppm; }
    var o = ['<svg xmlns="http://www.w3.org/2000/svg" width="' + width + '" height="' + height + '" viewBox="0 0 ' + width + ' ' + height + '" font-family="-apple-system, system-ui, Helvetica, Arial, sans-serif" font-size="12">',
      '<rect width="100%" height="100%" fill="' + bg + '"/>',
      '<text x="12" y="24" font-size="16" font-weight="bold" fill="' + fg + '">' + esc(ev.event.name || '') + ' – ' + (mode === 'officials' ? 'officials' : 'positions') + ' Gantt</text>',
      '<text x="12" y="44" fill="' + sub + '">' + esc(E.dayLabel(day) + ' ' + day) + '  ' + esc(ev.event.venue || '') + '  · solid = primary, light = secondary, red outline = conflict</text>'];
    for (var t = t0; t <= t1; t += 15) {
      var x = Xp(t), major = t % 60 === 0;
      o.push('<line x1="' + f1(x) + '" y1="' + (top - 8) + '" x2="' + f1(x) + '" y2="' + (top + rowH * rows.length) + '" stroke="' + grid + '" stroke-width="' + (major ? 1.2 : 0.6) + '"/>');
      if (t % 30 === 0) o.push('<text x="' + f1(x) + '" y="' + (top - 12) + '" text-anchor="middle" fill="' + (major ? fg : sub) + '" font-weight="' + (major ? 'bold' : 'normal') + '">' + E.fmtHHMM(t - lo) + '</text>');
    }
    races.forEach(function (r) {
      var x = Xp(res.timelines[r.id].start), c = X.raceColour(ev, r.id);
      o.push('<line x1="' + f1(x) + '" y1="' + (top - 6) + '" x2="' + f1(x) + '" y2="' + (top + rowH * rows.length) + '" stroke="' + c + '" stroke-width="2" stroke-dasharray="5,4"/>');
    });
    rows.forEach(function (row, i) {
      var y = top + i * rowH, label = row[0], subl = row[1];
      if (i % 2 === 0) o.push('<rect x="0" y="' + y + '" width="' + width + '" height="' + rowH + '" fill="' + fg + '" opacity="0.04"/>');
      o.push('<text x="12" y="' + (y + 17) + '" fill="' + (label === 'UNFILLED' ? '#C00000' : fg) + '" font-weight="bold">' + esc(label.slice(0, 30)) + '</text>');
      if (subl) o.push('<text x="250" y="' + (y + 17) + '" text-anchor="end" fill="' + sub + '" font-size="10">' + esc(subl.slice(0, 26)) + '</text>');
      row[2].forEach(function (it) {
        var d = it[0], w = it[1], s = w[0], e = w[1], blk = w[3], c = X.raceColour(ev, d.race_id);
        var secondary = d.role === 'Secondary', fill = blk ? (secondary ? X.lighten(c) : c) : 'none';
        var stroke = d.status === 'CONFLICT' ? '#C00000' : (d.status === 'TIGHT' ? '#C9A227' : c);
        var sw = (d.status === 'CONFLICT' || d.status === 'TIGHT') ? 2.5 : 1;
        if (!blk) { stroke = c; sw = 1; }
        var xs = Xp(s), xe = Math.max(Xp(e), Xp(s) + 2);
        var title = d.title + ' · ' + w[2] + ' · ' + d.race + ' · ' + E.fmtHHMM(s - lo) + '–' + E.fmtHHMM(e - lo);
        if (mode !== 'officials' && d.official) title += ' · ' + d.official;
        o.push('<rect x="' + f1(xs) + '" y="' + (y + (rowH - barH) / 2) + '" width="' + f1(xe - xs) + '" height="' + barH + '" rx="3" fill="' + fill +
          '" stroke="' + stroke + '" stroke-width="' + sw + '"' + (blk ? '' : ' stroke-dasharray="3,3"') + '><title>' + esc(title) + '</title></rect>');
        var text = mode === 'officials' ? d.title : (d.official || 'UNFILLED');
        if (blk && xe - xs > 60) {
          o.push('<text x="' + f1(xs + 4) + '" y="' + (y + 17) + '" font-size="10" fill="' + (secondary ? '#000' : '#FFF') + '">' + esc(text.slice(0, Math.trunc((xe - xs) / 6))) + '</text>');
        }
      });
    });
    var ly = top + rowH * rows.length + 26;
    races.concat([{ id: E.ALL, name: 'All-day positions' }, { id: 'session', name: 'Meetings, briefings, rehearsals' }]).forEach(function (r, i) {
      var lx = 12 + (i % 4) * 300, yy = ly + Math.floor(i / 4) * 22, c = X.raceColour(ev, r.id);
      o.push('<rect x="' + lx + '" y="' + (yy - 11) + '" width="14" height="14" rx="2" fill="' + c + '"/><text x="' + (lx + 20) + '" y="' + yy + '" fill="' + fg + '">' +
        esc(r.name.slice(0, 40)) + (r.id === E.ALL || r.id === 'session' ? '' : ' – start ' + esc(r.start || '')) + '</text>');
    });
    o.push('</svg>');
    return o.join('\n');
  };

  W.X = X;
})(WTP);
if (typeof module !== 'undefined') module.exports = WTP;
