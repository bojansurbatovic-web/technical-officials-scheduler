/* Athletes' guide: the schedule and course facts that matter to athletes only (no TO meetings or jobs).
 * Builds the in-app view's data, a standalone HTML guide to share or print, and an athletes' calendar (.ics). */
var WTP = (typeof WTP !== 'undefined') ? WTP : {};
(function (W) {
  'use strict';
  var E = W.E, X = W.X, ref = W.ref;
  var G = {};

  // sessions athletes attend, with the athlete-facing wording
  var SESSION_TEXT = {
    briefing_checkin: ['Briefing check-in', 'Show your accreditation or photo ID. Race packs are handed out after the briefing.'],
    athletes_briefing: ['Athletes’ briefing', 'Attendance is mandatory. Course, rules and any changes announced here are binding.'],
    swim_fam: ['Swim course familiarisation', 'Swim the course under race-like conditions. Wear your race cap if instructed.'],
    bike_fam: ['Bike course familiarisation', 'Ride the course with officials present. Helmet on and fastened.'],
    coaches_meeting: ['Coaches’ meeting', 'For team managers and coaches.']
  };
  // race-day milestones athletes need, in time order
  var RACE_TEXT = [
    ['lounge_open', 'Athlete lounge opens', 'Check in with your race number, wetsuit, cap and goggles.', false],
    ['tz_open', 'Transition opens', 'Equipment check at the entrance: helmet, bike, race numbers.', false],
    ['tz_close', 'Transition closes', 'All equipment must be in place; leave transition.', false],
    ['lounge_close', 'Athlete lounge closes', 'Be in the lounge before this time.', false],
    ['intro', 'Athlete introduction', 'Line up in start-number order.', false],
    ['start', 'START', '', false],
    ['winner', 'Expected leader finish', 'Estimate from typical race times.', true],
    ['medal', 'Medal ceremony', 'Medallists report to the ceremony area straight after finishing.', true],
    ['protest_close', 'Protest time ends', 'Protests to the Head Referee within the protest time after the finish (CR 12.4).', true]
  ];

  G.info = function (ev) {
    var a = ev.event.athletes || {};
    return { briefing_location: a.briefing_location || '', office: a.office || '', notes: a.notes || '' };
  };

  function racesFor(ev, raceId) {
    var rs = E.racesSorted(ev);
    return raceId ? rs.filter(function (r) { return r.id === raceId; }) : rs;
  }

  /** [{s, e, date, title, text, race, race_id, kind, approx}] sorted by time */
  G.items = function (ev, res, raceId) {
    var out = [], ids = racesFor(ev, raceId).map(function (r) { return r.id; });
    res.sessions.forEach(function (se) {
      if (!se.enabled || !SESSION_TEXT[se.key]) return;
      if (!se.for_races.some(function (id) { return ids.indexOf(id) >= 0; })) return;
      var t = SESSION_TEXT[se.key], who = se.name.split(' – ')[1];
      out.push({ s: se.s, e: se.e, date: se.date, title: t[0] + (who ? ' – ' + who : ''), text: t[1], race: '', race_id: 'session',
        kind: se.key, approx: false });
    });
    racesFor(ev, raceId).forEach(function (r) {
      var tl = res.timelines[r.id];
      RACE_TEXT.forEach(function (m) {
        out.push({ s: tl[m[0]], e: null, date: E.dateAt(ev, tl[m[0]]), title: m[1] + (raceId ? '' : ' – ' + r.name), text: m[2],
          race: r.name, race_id: r.id, kind: m[0], approx: m[3] });
      });
    });
    return E._h.sortBy(out, function (x) { return x.s; });
  };

  /** Course facts per race */
  G.course = function (ev, r) {
    var legs = Math.max(1, +r.legs || 1), laps = r.laps || {};
    function lap(n) { return n > 1 ? n + ' laps' : '1 lap'; }
    var rows = [
      ['Swim', (+r.swim_m) + ' m · ' + lap(+laps.swim || 1)],
      ['Bike', (+r.bike_km) + ' km · ' + lap(+laps.bike || 1) + (r.draft_legal ? ' · draft-legal' : ' · non-drafting')],
      ['Run', (+r.run_km) + ' km · ' + lap(+laps.run || 1)]
    ];
    if (legs > 1) rows.unshift(['Format', legs + ' legs per team (each athlete swims, bikes and runs)']);
    if (r.draft_legal && +r.wheel_stations > 0) rows.push(['Wheel stations', String(r.wheel_stations)]);
    if (+r.aid_stations > 0) rows.push(['Aid stations (run)', String(r.aid_stations)]);
    return rows;
  };

  G.rules = function (ev, raceId) {
    var rs = racesFor(ev, raceId), drafting = rs.some(function (r) { return r.draft_legal; });
    var nonDrafting = rs.some(function (r) { return !r.draft_legal; }), wheels = rs.some(function (r) { return r.draft_legal && +r.wheel_stations > 0; });
    var list = [
      'Attend the athletes’ briefing and bring your accreditation or photo ID.',
      'Your helmet must be on and fastened from before you take the bike off the rack until it is back on the rack.',
      'Mount after the mount line and dismount before the dismount line.',
      'Wear your race suit for the whole race; keep race numbers visible as instructed.',
      'Wetsuit use is announced on race morning according to the water temperature.'
    ];
    if (drafting) list.push('Draft-legal bike: drafting is allowed only with athletes of your own race. Lapped athletes may be removed, as announced at the briefing.');
    if (nonDrafting) list.push('Non-drafting bike: keep out of the draft zone of the athlete in front; overtake within the allowed time.');
    if (wheels) list.push('Spare wheels go to the wheel stations before the race, as explained at the briefing.');
    list.push('Time penalties are served in the penalty box shown at the briefing.');
    list.push('Protests go to the Head Referee within the protest time after the finish (CR 12.4).');
    return list;
  };

  function hm(m) { return E.fmtHHMM(((m % 1440) + 1440) % 1440); }
  function longDate(iso) {
    var p = iso.split('-'), M = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    return ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][E.weekday(iso)] + ' ' + (+p[2]) + ' ' + M[+p[1] - 1] + ' ' + p[0];
  }
  G.longDate = longDate;

  /** Standalone HTML guide (works offline, prints well) */
  G.html = function (ev, res, raceId) {
    var esc = X.esc, e = ev.event, info = G.info(ev), races = racesFor(ev, raceId), items = G.items(ev, res, raceId);
    var title = e.name || 'Event';
    var o = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
      '<title>' + esc('Athletes’ guide – ' + title) + '</title><style>',
      'body{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;color:#16202c;margin:0;background:#fff}',
      'main{max-width:760px;margin:0 auto;padding:24px 18px 48px}h1{margin:0 0 4px;font-size:26px}h2{margin:28px 0 8px;font-size:19px;border-bottom:2px solid #1f6fd1;padding-bottom:4px}',
      '.muted{color:#5d6b7c}.day{margin:18px 0 6px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;font-size:13px;color:#5d6b7c}',
      'table{border-collapse:collapse;width:100%}td{padding:7px 8px;border-bottom:1px solid #dce2ea;vertical-align:top}td.t{width:92px;font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}',
      'tr.key td{background:#eef4fd}.small{font-size:13px}.box{border:1px solid #dce2ea;border-radius:10px;padding:12px 14px;margin:10px 0}',
      'ul{padding-left:20px}li{margin:4px 0}@media print{main{padding:0}h2{break-after:avoid}tr{break-inside:avoid}}</style></head><body><main>',
      '<h1>Athletes’ guide</h1><div><strong>' + esc(title) + '</strong>' + (e.venue ? ' · ' + esc(e.venue) : '') + '</div>',
      '<div class="muted">' + esc(races.map(function (r) { return r.name; }).join(' · ')) + '</div>'];
    if (info.briefing_location || info.office || info.notes) {
      o.push('<div class="box">');
      if (info.briefing_location) o.push('<div><strong>Briefing location:</strong> ' + esc(info.briefing_location) + '</div>');
      if (info.office) o.push('<div><strong>Race office / packet pick-up:</strong> ' + esc(info.office) + '</div>');
      if (info.notes) o.push('<div style="white-space:pre-wrap;margin-top:6px">' + esc(info.notes) + '</div>');
      o.push('</div>');
    }
    o.push('<h2>Schedule</h2>');
    var day = '';
    items.forEach(function (it) {
      if (it.date !== day) { if (day) o.push('</table>'); day = it.date; o.push('<div class="day">' + esc(longDate(day)) + '</div><table>'); }
      o.push('<tr class="' + (it.kind === 'start' || it.kind === 'athletes_briefing' ? 'key' : '') + '"><td class="t">' + (it.approx ? '≈ ' : '') + hm(it.s) +
        (it.e ? '–' + hm(it.e) : '') + '</td><td><strong>' + esc(it.title) + '</strong>' + (it.text ? '<div class="small muted">' + esc(it.text) + '</div>' : '') + '</td></tr>');
    });
    if (day) o.push('</table>');
    o.push('<h2>Course</h2>');
    races.forEach(function (r) {
      o.push('<div class="box"><strong>' + esc(r.name) + '</strong> · start ' + esc(res.fmt(res.timelines[r.id].start)) + '<table class="small">' +
        G.course(ev, r).map(function (c) { return '<tr><td style="width:150px">' + esc(c[0]) + '</td><td>' + esc(c[1]) + '</td></tr>'; }).join('') + '</table></div>');
    });
    o.push('<h2>Key rules</h2><ul>' + G.rules(ev, raceId).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>');
    o.push('<p class="small muted">Times marked ≈ are estimates. The athletes’ briefing and the official race information prevail. Made with ' +
      esc(ref.APP_NAME) + ' – independent tool, not affiliated with World Triathlon.</p></main></body></html>');
    return o.join('\n');
  };

  /** Athletes' calendar */
  G.ics = function (ev, res, raceId) {
    var base = E.baseDate(ev), now = new Date();
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    function dt(m) {
      var r = E._h.pyRound(m), days = Math.floor(r / 1440), mins = r - days * 1440;
      return E.addDays(base, days).replace(/-/g, '') + 'T' + pad(Math.floor(mins / 60)) + pad(mins % 60) + '00';
    }
    function txt(s) { return String(s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\n/g, '\\n'); }
    var stamp = now.toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, 'Z');
    var L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//' + ref.APP_NAME + '//athletes//EN', 'CALSCALE:GREGORIAN'];
    G.items(ev, res, raceId).forEach(function (it, i) {
      L.push('BEGIN:VEVENT', 'UID:athlete-' + i + '-' + base + '-' + (raceId || 'all') + '@toscheduler', 'DTSTAMP:' + stamp,
        'DTSTART:' + dt(it.s), 'DTEND:' + dt(it.e || it.s + 10), 'SUMMARY:' + txt((it.approx ? '≈ ' : '') + it.title),
        'LOCATION:' + txt(it.kind === 'athletes_briefing' && G.info(ev).briefing_location ? G.info(ev).briefing_location : (ev.event.venue || '')),
        'DESCRIPTION:' + txt(it.text), 'END:VEVENT');
    });
    L.push('END:VCALENDAR');
    return L.join('\r\n') + '\r\n';
  };

  W.Athletes = G;
})(WTP);
if (typeof module !== 'undefined') module.exports = WTP;
