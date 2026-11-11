/* Planning engine: race timelines, duty windows, meetings, auto-assignment, conflict checks.
 * A line-by-line port of the Ubuntu app's engine.py; tests/golden.json checks both give the same plan.
 * The event is a plain object (exactly what is saved as .wtplan.json).
 * Dates are ISO strings "YYYY-MM-DD"; times are minutes from midnight of the first event day. */
var WTP = (typeof WTP !== 'undefined') ? WTP : {};
(function (W) {
  'use strict';
  var ref = W.ref;
  var E = {};
  var ALL = E.ALL = 'ALL';
  var WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  // ------------------------------------------------------------ small Python-like helpers
  function has(o, k) { return o != null && Object.prototype.hasOwnProperty.call(o, k); }
  function get(o, k, d) { return (o != null && has(o, k) && o[k] !== undefined) ? o[k] : d; }
  function deep(x) { return x === undefined ? undefined : JSON.parse(JSON.stringify(x)); }
  function pyInt(x) { var n = Number(x); return isFinite(n) ? Math.trunc(n) : 0; }
  function num(x, d) { var n = parseFloat(x); return isFinite(n) ? n : (d === undefined ? 0 : d); }
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  /** Python round(): halves go to the even neighbour. */
  function pyRound(x) {
    var f = Math.floor(x), d = x - f;
    if (Math.abs(d - 0.5) < 1e-9) return (f % 2 === 0) ? f : f + 1;
    return Math.round(x);
  }
  function cmp(a, b) {             // compare tuples (arrays) like Python
    if (Array.isArray(a)) {
      for (var i = 0; i < Math.min(a.length, b.length); i++) {
        var c = cmp(a[i], b[i]);
        if (c) return c;
      }
      return a.length - b.length;
    }
    return a < b ? -1 : (a > b ? 1 : 0);
  }
  function sortBy(arr, keyFn, reverse) {
    var dec = arr.map(function (x, i) { return [keyFn(x), i, x]; });
    dec.sort(function (p, q) { var c = cmp(p[0], q[0]); if (reverse) c = -c; return c || (p[1] - q[1]); });
    return dec.map(function (p) { return p[2]; });
  }
  function minOf(a, d) { return a.length ? Math.min.apply(null, a) : d; }
  function maxOf(a, d) { return a.length ? Math.max.apply(null, a) : d; }
  function uniq(a) { var s = {}, o = []; a.forEach(function (x) { if (!has(s, x)) { s[x] = 1; o.push(x); } }); return o; }
  function intersects(a, b) { for (var i = 0; i < a.length; i++) if (b.indexOf(a[i]) >= 0) return true; return false; }
  E._h = { pyRound: pyRound, cmp: cmp, sortBy: sortBy, deep: deep };

  // ------------------------------------------------------------ dates
  function isoToDays(iso) { var p = iso.split('-'); return Math.round(Date.UTC(+p[0], +p[1] - 1, +p[2]) / 86400000); }
  function daysToIso(n) { var d = new Date(n * 86400000); return d.getUTCFullYear() + '-' + pad2(d.getUTCMonth() + 1) + '-' + pad2(d.getUTCDate()); }
  function addDays(iso, n) { return daysToIso(isoToDays(iso) + n); }
  function diffDays(a, b) { return isoToDays(a) - isoToDays(b); }
  function todayIso() { var d = new Date(); return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate()); }
  E.addDays = addDays; E.diffDays = diffDays; E.todayIso = todayIso; E.isoToDays = isoToDays; E.daysToIso = daysToIso;

  // ------------------------------------------------------------ time helpers
  E.parseHHMM = function (text, dflt) {
    if (dflt === undefined) dflt = null;
    if (typeof text === 'number') return text;
    var m = /^\s*(\d{1,2})[:.h](\d{2})\s*$/.exec(String(text == null ? '' : text));
    if (!m) return dflt;
    var h = +m[1], mi = +m[2];
    if (h > 23 || mi > 59) return dflt;
    return h * 60 + mi;
  };
  E.fmtHHMM = function (minutes, seconds) {
    if (minutes == null) return '';
    var total = pyRound(minutes * 60);
    var sign = total < 0 ? '-' : '';
    total = Math.abs(total);
    var h = Math.floor(total / 3600), rem = total % 3600, m = Math.floor(rem / 60), s = rem % 60;
    if (seconds) return sign + pad2(h) + ':' + pad2(m) + ':' + pad2(s);
    if (s >= 30) { m += 1; if (m === 60) { h += 1; m = 0; } }
    return sign + pad2(h) + ':' + pad2(m);
  };
  E.parseDate = function (text) {
    var s = String(text == null ? '' : text).trim();
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (!m) return null;
    var d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    if (d.getUTCFullYear() !== +m[1] || d.getUTCMonth() !== +m[2] - 1 || d.getUTCDate() !== +m[3]) return null;
    return s;
  };
  E.raceDate = function (ev, race) {
    return E.parseDate(race.date) || E.parseDate(ev.event.date) || todayIso();
  };
  E.raceDates = function (ev) {
    var d = uniq(ev.races.map(function (r) { return E.raceDate(ev, r); })).sort();
    return d.length ? d : [E.parseDate(ev.event.date) || todayIso()];
  };
  E.eventDates = function (ev) {
    var d = E.raceDates(ev).slice();
    E.buildSessions(ev).forEach(function (se) { if (se.enabled) d.push(se.date); });
    return uniq(d).sort();
  };
  E.baseDate = function (ev) { return E.eventDates(ev)[0]; };
  E.isMultiday = function (ev) { return E.eventDates(ev).length > 1; };
  E.raceOffset = function (ev, race) { return diffDays(E.raceDate(ev, race), E.baseDate(ev)) * 1440; };
  E.dayKey = function (d) { return 'day:' + d; };
  E.isDayKey = function (rid) { return rid === ALL || String(rid).indexOf('day:') === 0; };
  E.weekday = function (iso) { return (new Date(isoToDays(iso) * 86400000).getUTCDay() + 6) % 7; };
  E.dayLabel = function (iso) {
    var p = iso.split('-');
    return WEEKDAYS[E.weekday(iso)] + ' ' + p[2] + '.' + p[1] + '.';
  };
  E.whenFormatter = function (ev) {
    var base = E.baseDate(ev), multi = E.isMultiday(ev);
    return function (minutes) {
      if (minutes == null) return '';
      if (!multi) return E.fmtHHMM(minutes);
      var days = Math.floor(minutes / 1440);
      return E.dayLabel(addDays(base, days)) + ' ' + E.fmtHHMM(minutes - days * 1440);
    };
  };
  E.dateAt = function (ev, minutes) { return addDays(E.baseDate(ev), Math.floor(minutes / 1440)); };
  E.takesPart = function (official, raceId) { var r = official.races || {}; return has(r, raceId) ? !!r[raceId] : true; };
  E.fmtDur = function (minutes) {
    var total = pyRound(minutes * 60), h = Math.floor(total / 3600), rem = total % 3600;
    var m = Math.floor(rem / 60), s = rem % 60;
    return h ? h + ':' + pad2(m) + ':' + pad2(s) : m + ':' + pad2(s);
  };

  // ------------------------------------------------------------ model builders
  E.newId = function (prefix) {
    var hex = '';
    for (var i = 0; i < 6; i++) hex += Math.floor(Math.random() * 16).toString(16);
    return (prefix || 'r') + hex;
  };
  E.dutyDefaults = function () { var o = {}; ref.DUTY_DEFAULTS.forEach(function (d) { o[d[0]] = d[1]; }); return o; };
  E.newRace = function (fmt, category, start, name, date) {
    fmt = fmt || 'standard'; category = category || 'elite_women';
    var f = ref.FORMATS[fmt], cat = ref.CATEGORIES[category];
    var laps = cat.draft_legal ? f.laps_elite : f.laps_ag;
    var paces = {};
    ['swim_pace', 'bike_speed', 'run_pace', 't1', 't2', 'gap_swim', 'gap_t2', 'gap_finish'].forEach(function (k) { paces[k] = cat[k]; });
    return {
      id: E.newId('r'),
      name: name || (cat.label + ' – ' + f.label.split(' (')[0]),
      category: category, format: fmt, date: date || '', start: start || '10:00',
      legs: f.legs, swim_m: f.swim_m, bike_km: f.bike_km, run_km: f.run_km,
      laps: { swim: laps[0], bike: laps[1], run: laps[2] },
      wheel_stations: cat.draft_legal ? f.wheel_stations : 0,
      aid_stations: f.aid_stations, start_line: f.start_line, draft_legal: cat.draft_legal,
      paces: paces, schedule: deep(ref.SCHEDULE_DEFAULTS), shifts: {}
    };
  };
  E.applyFormat = function (race, fmt, category) {
    fmt = fmt || race.format; category = category || race.category;
    var fresh = E.newRace(fmt, category, race.start || '10:00');
    ['format', 'category', 'legs', 'swim_m', 'bike_km', 'run_km', 'laps', 'wheel_stations', 'aid_stations',
      'start_line', 'draft_legal', 'paces'].forEach(function (k) { race[k] = deep(fresh[k]); });
    return race;
  };
  E.newOfficial = function (name) {
    return { name: name, country: '', primary: '', max_secondary: 3, available_from: '', available_to: '',
      radio: true, notes: '', races: {} };
  };
  E.newEvent = function (name, date, races, nOfficials) {
    var ev = {
      app: 'wt-planner', version: 1,
      event: { name: name || 'New event', venue: '', date: date || '', notes: '', td: '', md: '', jury: ['', ''],
        vcc_base: ref.RADIO_DEFAULTS.vcc_base, spare_pct: ref.RADIO_DEFAULTS.spare_pct },
      settings: E.dutyDefaults(),
      races: races || [E.newRace()],
      officials: [], positions: {}, assignments: {}, sessions: {}, custom_sessions: []
    };
    for (var i = 0; i < (nOfficials || 0); i++) ev.officials.push(E.newOfficial('Official ' + (i + 1)));
    E.resetPositions(ev);
    return ev;
  };
  function setdefault(o, k, v) { if (!has(o, k)) o[k] = v; return o[k]; }
  E.normalise = function (ev) {
    var base = E.newEvent();
    Object.keys(base).forEach(function (k) { setdefault(ev, k, deep(base[k])); });
    Object.keys(base.event).forEach(function (k) { setdefault(ev.event, k, deep(base.event[k])); });
    var dd = E.dutyDefaults();
    Object.keys(dd).forEach(function (k) { setdefault(ev.settings, k, dd[k]); });
    ev.races.forEach(function (r) {
      var tmpl = E.newRace(r.format || 'standard', r.category || 'elite_women');
      Object.keys(tmpl).forEach(function (k) { setdefault(r, k, deep(tmpl[k])); });
      ['paces', 'schedule', 'laps'].forEach(function (sub) {
        if (!r[sub] || typeof r[sub] !== 'object') r[sub] = {};
        Object.keys(tmpl[sub]).forEach(function (k) { setdefault(r[sub], k, tmpl[sub][k]); });
      });
      if (r.date == null) r.date = '';
      if (!r.shifts || typeof r.shifts !== 'object') r.shifts = {};
    });
    ev.officials.forEach(function (o) {
      var t = E.newOfficial('');
      Object.keys(t).forEach(function (k) { setdefault(o, k, deep(t[k])); });
      if (!o.races || typeof o.races !== 'object') o.races = {};
    });
    Object.keys(ref.POSITION_INDEX).forEach(function (key) {
      setdefault(ev.positions, key, { enabled: ref.POSITION_INDEX[key].proposed, count: null });
    });
    var dk = E.dayKey(E.raceDates(ev)[0]), na = {};
    Object.keys(ev.assignments || {}).forEach(function (k) {
      var nk = /\|ALL$/.test(k) ? k.slice(0, -4) + '|' + dk : k;
      na[nk] = ev.assignments[k];
    });
    ev.assignments = na;
    if (!ev.sessions || typeof ev.sessions !== 'object' || Array.isArray(ev.sessions)) ev.sessions = {};
    if (!Array.isArray(ev.custom_sessions)) ev.custom_sessions = [];
    return ev;
  };

  // ------------------------------------------------------------ positions
  E.raceApplies = function (race, cond) {
    var laps = race.laps || {};
    switch (cond) {
      case 'all': return true;
      case 'draft_legal': return !!race.draft_legal;
      case 'non_drafting': return !race.draft_legal;
      case 'relay': return pyInt(get(race, 'legs', 1)) > 1;
      case 'laps': return pyInt(get(laps, 'bike', 1)) > 1 || pyInt(get(laps, 'run', 1)) > 1;
      case 'run_laps': return pyInt(get(laps, 'run', 1)) > 1;
      case 'bike_laps': return pyInt(get(laps, 'bike', 1)) > 1;
      case 'wheel': return !!race.draft_legal && pyInt(get(race, 'wheel_stations', 0)) > 0;
      case 'aid': return pyInt(get(race, 'aid_stations', 0)) > 0;
    }
    return true;
  };
  E.proposedCount = function (ev, pos) {
    var c = pos.count;
    var races = ev.races.filter(function (r) { return E.raceApplies(r, pos.applies); });
    if (!races.length) return 0;
    if (typeof c === 'number') return c;
    if (c === 'wheel_extra') return Math.max(0, maxOf(races.map(function (r) { return pyInt(get(r, 'wheel_stations', 0)); })) - 1);
    if (c === 'aid_extra') return Math.max(0, maxOf(races.map(function (r) { return pyInt(get(r, 'aid_stations', 0)); })) - 1);
    if (c === 'start_line') return maxOf(races.map(function (r) { return pyInt(get(r, 'start_line', 4)); }));
    if (c === 'bike_pb') {
      var out = 0;
      races.forEach(function (r) {
        var per = (r.format === 'middle' || r.format === 'long') ? 30 : 10;
        out = Math.max(out, Math.ceil(num(get(r, 'bike_km', 40)) / per));
      });
      return out;
    }
    return 1;
  };
  E.resetPositions = function (ev) {
    ev.positions = {};
    Object.keys(ref.POSITION_INDEX).forEach(function (k) {
      ev.positions[k] = { enabled: ref.POSITION_INDEX[k].proposed, count: null };
    });
    return ev;
  };
  E.positionCount = function (ev, key) {
    var pos = ref.POSITION_INDEX[key], cfg = ev.positions[key] || {};
    if (!get(cfg, 'enabled', pos.proposed)) return 0;
    if (!ev.races.some(function (r) { return E.raceApplies(r, pos.applies); })) return 0;
    if (cfg.count !== null && cfg.count !== undefined && cfg.count !== '') return Math.max(0, pyInt(cfg.count));
    return E.proposedCount(ev, pos);
  };

  // ------------------------------------------------------------ timelines
  E.protestMinutes = function (race) {
    if (race.format === 'middle' || race.format === 'long' || race.category === 'age_group') return 45;
    return 20;
  };
  E.raceTimeline = function (race, offset) {
    var S = E.parseHHMM(race.start, 600) + num(offset || 0);
    var p = race.paces, sch = race.schedule, laps = race.laps;
    var legs = Math.max(1, pyInt(get(race, 'legs', 1)));
    var sw = num(race.swim_m) / 100 * num(p.swim_pace);
    var bk = num(race.bike_km) / Math.max(1e-6, num(p.bike_speed)) * 60;
    var rn = num(race.run_km) * num(p.run_pace);
    var t1 = num(p.t1), t2 = num(p.t2);
    var L = sw + t1 + bk + t2 + rn;
    var gs = num(p.gap_swim) / 100, gb = num(p.gap_t2) / 100, gf = num(p.gap_finish) / 100;
    var lls = S + (legs - 1) * L * (1 + gf);
    var tl = {
      start: S,
      lounge_open: S - num(sch.lounge_open), lounge_close: S - num(sch.lounge_close),
      tz_open: S - num(sch.tz_open), tz_close: S - num(sch.tz_close), intro: S - num(sch.intro),
      swim_first_out: S + sw, swim_last_out: lls + sw * (1 + gs),
      t1_first: S + sw, t1_last: lls + (sw + t1) * (1 + gs),
      bike_lap1: S + sw + t1 + bk / Math.max(1, pyInt(get(laps, 'bike', 1))),
      t2_first: S + sw + t1 + bk, t2_last: lls + (sw + t1 + bk) * (1 + gb),
      run_first: S + sw + t1 + bk + t2,
      winner: S + legs * L, last_finisher: S + legs * L * (1 + gf)
    };
    var rl = Math.max(1, pyInt(get(laps, 'run', 1)));
    tl.run_lap1_leader = tl.run_first + rn / rl;
    var lrs = tl.t2_last + t2 * (1 + gb);
    tl.run_lap_last = lrs + (tl.last_finisher - lrs) / rl;
    tl.medal = tl.winner + num(sch.medal_after_winner);
    tl.protest_close = tl.last_finisher + E.protestMinutes(race);
    tl._segments = { swim: sw, t1: t1, bike: bk, t2: t2, run: rn, leg: L, legs: legs };
    return tl;
  };
  E.MILESTONES = [
    ['lounge_open', 'Athlete lounge opens'], ['tz_open', 'Transition opens'],
    ['lounge_close', 'Athlete lounge closes'], ['tz_close', 'Transition closes'],
    ['intro', 'Athlete introduction'], ['start', 'START'],
    ['swim_first_out', 'Swim leader out'], ['swim_last_out', 'Last athlete out of the water'],
    ['bike_lap1', 'Bike leader completes lap 1'], ['t2_first', 'Bike leader into T2'],
    ['t2_last', 'Last athlete into T2'], ['run_lap1_leader', 'Run leader completes lap 1'],
    ['winner', 'Winner'], ['last_finisher', 'Last finisher'], ['medal', 'Medal ceremony']
  ];
  E.activityWindow = function (actKey, tl, settings, shifts) {
    var a = ref.ACTIVITIES[actKey];
    function edge(anchor, param, sign) {
      var b = tl[anchor];
      if (param === null || param === undefined) return b + num(sign);
      return b + num(sign) * num(get(settings, param, 0));
    }
    var s = edge(a[1], a[2], a[3]), e = edge(a[4], a[5], a[6]);
    if (shifts && has(shifts, actKey)) {
      s += num(shifts[actKey][0] || 0);
      e += num(shifts[actKey][1] || 0);
    }
    if (e < s) e = s;
    return [s, e];
  };

  // ------------------------------------------------------------ meetings & briefings
  function ceil15(m) { return Math.ceil(m / 15) * 15; }
  E.buildSessions = function (ev) {
    var races = sortBy(ev.races, function (r) { return [E.raceDate(ev, r), E.parseHHMM(r.start, 600)]; });
    var out = [];
    if (!races.length) return out;
    var settings = ev.settings || {};
    var tl0 = {}, rd = {}, byDate = {}, dateOrder = [];
    races.forEach(function (r) {
      tl0[r.id] = E.raceTimeline(r); rd[r.id] = E.raceDate(ev, r);
      if (!has(byDate, rd[r.id])) { byDate[rd[r.id]] = []; dateOrder.push(rd[r.id]); }
      byDate[rd[r.id]].push(r);
    });
    function busyUntil(d) {
      if (!has(byDate, d)) return null;
      return maxOf(byDate[d].map(function (r) { return tl0[r.id].last_finisher; }));
    }
    function add(key, sid, d, start, end, served, suffix) {
      var S = ref.SESSIONS[key];
      out.push({ id: sid, key: key, name: S[0] + (suffix || ''), date: d, start: start, end: end,
        attendees: S[1].slice(), ref: S[2], enabled: S[3], for_races: served.map(function (r) { return r.id; }),
        custom: false });
    }
    var first = races[0], prep = addDays(rd[first.id], -1);
    add('drivers_briefing', 'drivers_briefing', prep, 510, 555, races);
    add('medical_meeting', 'medical_meeting', prep, 570, 600, races);
    add('start_rehearsal', 'start_rehearsal', prep, 675, 720, races);
    add('finish_rehearsal', 'finish_rehearsal', prep, 765, 795, races);
    add('timing_meeting', 'timing_meeting', prep, 795, 825, races);
    add('tv_meeting', 'tv_meeting', prep, 825, 840, races);
    add('to_meeting', 'to_meeting', prep, 840, 900, races);

    var fam = {}, famOrder = [];
    races.forEach(function (r) {
      var g = (ref.BRIEFING_GROUPS[r.category] || ['elite', 'elite'])[1];
      if (!has(fam, g)) { fam[g] = []; famOrder.push(g); }
      fam[g].push(r);
    });
    var famDays = {}, famDayOrder = [];      // groups whose familiarisation falls on the same day share it
    famOrder.forEach(function (g) {
      var d = addDays(rd[fam[g][0].id], -1);
      if (!has(famDays, d)) { famDays[d] = []; famDayOrder.push(d); }
      famDays[d].push(g);
    });
    famDayOrder.forEach(function (d) {
      var gs = famDays[d], rs = [], sg = 600, bu = busyUntil(d);
      gs.forEach(function (g) { rs = rs.concat(fam[g]); });
      if (bu !== null) sg = Math.max(sg, ceil15(bu + 90));   // after the TO de-briefing of that day
      var sfx = famOrder.length === 1 ? '' : ' – ' + gs.map(function (g) { return (ref.BRIEFING_LABELS[g] || g).split(' team')[0]; }).join(' + ');
      var gid = gs.join('+');
      add('swim_fam', 'swim_fam:' + gid, d, sg, sg + 60, rs, sfx);
      add('bike_fam', 'bike_fam:' + gid, d, sg + 75, sg + 165, rs, sfx);
    });

    var groups = {};
    races.forEach(function (r) {
      var g = pyInt(get(r, 'legs', 1)) > 1 ? 'relay' : (ref.BRIEFING_GROUPS[r.category] || ['elite', 'elite'])[0];
      (groups[g] = groups[g] || []).push(r);
    });
    if (groups.relay && groups.elite && rd[groups.relay[0].id] === rd[groups.elite[0].id]) {
      groups.elite = groups.elite.concat(groups.relay); delete groups.relay;
    }
    var order = ['elite', 'u23', 'junior', 'relay', 'para', 'age_group'], byPrep = {}, prepOrder = [];
    order.forEach(function (g) {
      if (!groups[g]) return;
      var d = addDays(rd[groups[g][0].id], -1);
      if (!has(byPrep, d)) { byPrep[d] = []; prepOrder.push(d); }
      byPrep[d].push(g);
    });
    prepOrder.forEach(function (d) {
      var gs = byPrep[d], t = 960, lastEnd = t, served = [];
      gs.forEach(function (g) {
        var rs = groups[g], label = ref.BRIEFING_LABELS[g] || g;
        served = served.concat(rs);
        if (g === 'elite' && rs.some(function (r) { return pyInt(get(r, 'legs', 1)) > 1; }) &&
            rs.some(function (r) { return pyInt(get(r, 'legs', 1)) === 1; })) label = 'Elite + Mixed relay';
        add('coaches_meeting', 'coaches_meeting:' + g, d, t - 60, t - 15, rs, ' – ' + label);
        add('briefing_checkin', 'briefing_checkin:' + g, d, t - 30, t + 90, rs, ' – ' + label);
        add('athletes_briefing', 'athletes_briefing:' + g, d, t, t + 60, rs, ' – ' + label);
        if (g === 'age_group') { out[out.length - 1].enabled = false; out[out.length - 2].enabled = false; }
        lastEnd = t + 60; t += 75;
      });
      add('jury_after_briefing', 'jury_after_briefing:' + d, d, lastEnd, lastEnd + 30, served);
    });

    dateOrder.forEach(function (d) {
      var rs = byDate[d];
      var fl = minOf(rs.map(function (r) { return tl0[r.id].lounge_open; }));
      add('to_briefing', 'to_briefing:' + d, d, fl - 75, fl - 45, rs);
      var end = maxOf(rs.map(function (r) { return tl0[r.id].last_finisher; })) + 45;
      add('to_debriefing', 'to_debriefing:' + d, d, end, end + 30, rs);
    });

    var sign = num(get(settings, 'hr_signoff', 15)), prevAfter = null;
    races.forEach(function (r) {
      var tl = tl0[r.id], b0 = tl.start - 60, b1 = tl.start - 45;
      if (prevAfter && prevAfter.date === rd[r.id] && prevAfter.start < b1 && b0 < prevAfter.end) {
        prevAfter.start = Math.min(prevAfter.start, b0); prevAfter.end = Math.max(prevAfter.end, b1);
        prevAfter.name += ' + 1 h before start – ' + r.name;
        prevAfter.for_races.push(r.id);
      } else {
        add('jury_before_race', 'jury_before_race:' + r.id, rd[r.id], b0, b1, [r], ' – ' + r.name);
      }
      add('jury_after_race', 'jury_after_race:' + r.id, rd[r.id], tl.protest_close + sign,
        tl.protest_close + sign + 20, [r], ' – ' + r.name);
      prevAfter = out[out.length - 1];
    });

    var over = ev.sessions || {};
    out.forEach(function (se) {
      var o = over[se.id];
      if (!o || !Object.keys(o).length) return;
      if (has(o, 'enabled')) se.enabled = !!o.enabled;
      if (E.parseDate(o.date)) se.date = E.parseDate(o.date);
      if (E.parseHHMM(o.start) !== null) se.start = E.parseHHMM(o.start);
      if (E.parseHHMM(o.end) !== null) se.end = E.parseHHMM(o.end);
      se.edited = true;
    });
    out.forEach(function (se) {             // the Jury meets after the (possibly moved) briefing of that day
      if (se.key !== 'jury_after_briefing' || se.edited) return;
      var ends = out.filter(function (b) { return b.key === 'athletes_briefing' && b.enabled && b.date === se.date; })
        .map(function (b) { return b.end; });
      if (ends.length) { se.start = maxOf(ends); se.end = se.start + 30; }
    });
    (ev.custom_sessions || []).forEach(function (c) {
      var d = E.parseDate(c.date) || rd[first.id];
      var st = E.parseHHMM(c.start, 600), en = E.parseHHMM(c.end, 660);
      out.push({ id: c.id || E.newId('s'), key: 'custom', name: c.name || 'Meeting', date: d, start: st,
        end: Math.max(en, st), attendees: (c.attendees && c.attendees.length ? c.attendees : ['all_tos']).slice(),
        ref: 'added by user', enabled: !!get(c, 'enabled', true),
        for_races: races.map(function (r) { return r.id; }), custom: true });
    });
    out.forEach(function (se) { if (se.end < se.start) se.end = se.start; });
    return sortBy(out, function (x) { return [x.date, x.start]; });
  };
  E.ATTENDEE_WORDS = { td: 'Technical Delegate', md: 'Medical Delegate', jury: 'Competition Jury', all_tos: 'all TOs' };
  E.attendeeLabel = function (tokens) {
    return tokens.map(function (t) {
      if (E.ATTENDEE_WORDS[t]) return E.ATTENDEE_WORDS[t];
      var p = ref.POSITION_INDEX[t];
      return (p ? p.title : t).split(' (')[0];
    }).join(', ');
  };
  E.sessionsAbs = function (ev) {
    var base = E.baseDate(ev);
    return E.buildSessions(ev).map(function (se) {
      var off = diffDays(se.date, base) * 1440;
      var c = Object.assign({}, se); c.s = off + se.start; c.e = off + se.end;
      return c;
    });
  };
  E.startWindowWarnings = function (ev) {
    var warn = [], rs = E.racesSorted(ev);
    for (var i = 0; i + 1 < rs.length; i++) {
      var a = rs[i], b = rs[i + 1];
      if (E.raceDate(ev, a) !== E.raceDate(ev, b)) continue;
      var need = ref.START_WINDOWS[a.format];
      if (!need || !ref.CATEGORIES[a.category].draft_legal) continue;
      var gap = E.parseHHMM(b.start, 0) - E.parseHHMM(a.start, 0);
      if (gap < need - 15) {
        warn.push(a.name + ' → ' + b.name + ': ' + Math.trunc(gap) + ' min between starts; EOM 2.10.2 asks for ' +
          need + ' min (minimum ' + (need - 15) + ' min with TD approval).');
      } else if (gap < need) {
        warn.push(a.name + ' → ' + b.name + ': ' + Math.trunc(gap) + ' min between starts is below ' + need +
          ' min – allowed only with TD approval (EOM 2.10.2).');
      }
    }
    E.buildSessions(ev).forEach(function (se) {
      if (se.key === 'athletes_briefing' && se.edited && se.enabled && /:elite$/.test(se.id) &&
          Math.abs(se.start - 960) > 0.1) {
        warn.push(se.name + ' moved to ' + E.fmtHHMM(se.start) + ': CR 2.7 b(vii) sets 16:00 the day before ' +
          '(changes must be published 45 days in advance, CR 2.7 b(ix)).');
      }
    });
    return warn;
  };

  // ------------------------------------------------------------ slots
  E.racesSorted = function (ev) {
    return sortBy(ev.races, function (r) { return E.raceOffset(ev, r) + E.parseHHMM(r.start, 0); });
  };
  E.positionsByPriority = function () {
    return sortBy(Object.keys(ref.POSITION_INDEX), function (k) { return ref.POSITION_INDEX[k].priority; });
  };
  E.buildSlots = function (ev) {
    var settings = ev.settings, races = E.racesSorted(ev), tls = {}, rdate = {}, slots = [];
    races.forEach(function (r) { tls[r.id] = E.raceTimeline(r, E.raceOffset(ev, r)); rdate[r.id] = E.raceDate(ev, r); });
    E.positionsByPriority().forEach(function (key) {
      var pos = ref.POSITION_INDEX[key], n = E.positionCount(ev, key);
      if (n <= 0) return;
      var appRaces = races.filter(function (r) { return E.raceApplies(r, pos.applies); });
      for (var i = 0; i < n; i++) {
        var sid = key + '#' + (i + 1), title = pos.title + (n > 1 ? ' #' + (i + 1) : '');
        var windows = {}, wkeys = [];
        appRaces.forEach(function (r) {
          windows[r.id] = pos.activities.map(function (act) {
            var w = E.activityWindow(act, tls[r.id], settings, r.shifts);
            return [w[0], w[1], ref.ACTIVITIES[act][0], ref.NON_BLOCKING.indexOf(act) < 0, act];
          });
          wkeys.push(r.id);
        });
        var dayRaces = {};
        if (pos.all_day && wkeys.length) {
          var merged = {}, mOrder = [];
          wkeys.forEach(function (rid) {
            var dk = E.dayKey(rdate[rid]);
            if (!has(merged, dk)) { merged[dk] = []; dayRaces[dk] = []; mOrder.push(dk); }
            dayRaces[dk].push(rid);
            windows[rid].forEach(function (w) { if (w[3]) merged[dk].push(w); });
          });
          windows = {};
          mOrder.forEach(function (dk) {
            var bl = merged[dk];
            windows[dk] = [[minOf(bl.map(function (w) { return w[0]; })), maxOf(bl.map(function (w) { return w[1]; })),
              pos.title + ' (all day)', true, pos.activities[0]]];
          });
        } else {
          wkeys.forEach(function (rid) { dayRaces[rid] = [rid]; });
        }
        slots.push({ id: sid, key: key, title: title, kind: pos.kind, priority: pos.priority, toc: pos.toc,
          all_day: pos.all_day, windows: windows, races_of: dayRaces });
      }
    });
    return [slots, tls];
  };
  E.slotKeys = function (slot) { return Object.keys(slot.windows).map(function (rid) { return slot.id + '|' + rid; }); };

  // ------------------------------------------------------------ assignment
  function blocking(ws) { return ws.filter(function (w) { return w[3]; }).map(function (w) { return [w[0], w[1]]; }); }
  function gap(a, b) { return Math.max(b[0] - a[1], a[0] - b[1]); }
  E._blocking = blocking; E._gap = gap;
  E.outsideHours = function (s, e, af, at) {
    var day = Math.floor(s / 1440) * 1440;
    return (af !== null && s - day < af) || (at !== null && e - day > at);
  };
  function sid(key) { return key.split('|')[0]; }
  function rid(key) { return key.split('|')[1]; }

  function State(ev, slots) {
    var self = this;
    this.ev = ev;
    this.slots = {}; slots.forEach(function (s) { self.slots[s.id] = s; });
    this.buffer = num(get(ev.settings, 'buffer', 5));
    this.names = []; this.off = {};
    ev.officials.forEach(function (o) {
      if ((o.name || '').trim()) { self.names.push(o.name); self.off[o.name] = o; }
    });
    this.assign = {}; this.locked = {}; this.primary = {};
    this.busy = {}; this.attending = {};
    this.names.forEach(function (n) { self.busy[n] = []; self.attending[n] = {}; });
    this.sessions = E.sessionsAbs(ev).filter(function (se) { return se.enabled; });
  }
  State.prototype.implied = function (name, key) {
    var slot = this.slots[sid(key)], r = rid(key), att = this.attending[name];
    var races = has(slot.races_of, r) ? slot.races_of[r] : [r];
    return this.sessions.filter(function (se) {
      return !has(att, se.id) && (se.attendees.indexOf(slot.key) >= 0 || se.attendees.indexOf('all_tos') >= 0) &&
        intersects(races, se.for_races);
    });
  };
  State.prototype.windowsOf = function (key) { return get(this.slots[sid(key)].windows, rid(key), []); };
  State.prototype.part = function (name, key) {
    var slot = this.slots[sid(key)], r = rid(key), o = this.off[name];
    var races = has(slot.races_of, r) ? slot.races_of[r] : [r];
    return races.every(function (x) { return E.takesPart(o, x); });
  };
  State.prototype.put = function (key, name) {
    var sessions = this.implied(name, key), self = this;
    this.assign[key] = name;
    blocking(this.windowsOf(key)).forEach(function (w) { self.busy[name].push([w[0], w[1], key]); });
    sessions.forEach(function (se) {
      self.attending[name][se.id] = 1;
      self.busy[name].push([se.s, se.e, 'session:' + se.id]);
    });
  };
  State.prototype.keyDay = function (key) {
    var ws = this.windowsOf(key);
    return Math.floor(minOf(ws.map(function (w) { return w[0]; }), 0) / 1440);
  };
  State.prototype.secondaries = function (name, day) {
    var prim = this.primary[name], self = this, out = {};
    Object.keys(this.assign).forEach(function (k) {
      if (self.assign[k] === name && sid(k) !== prim && (day === undefined || day === null || self.keyDay(k) === day)) out[sid(k)] = 1;
    });
    return out;
  };
  State.prototype.holderRules = function (name) {
    var s = this.primary[name];
    if (!s) return null;
    return ref.POSITION_INDEX[this.slots[s].key].holder_rules;
  };
  State.prototype.fits = function (name, key, minGap) {
    if (!this.part(name, key)) return false;
    var o = this.off[name];
    var af = E.parseHHMM(o.available_from), at = E.parseHHMM(o.available_to);
    var s0 = sid(key), own = blocking(this.windowsOf(key));
    var meet = this.implied(name, key).map(function (se) { return [se.s, se.e]; });
    var i, j, busy = this.busy[name];
    for (i = 0; i < own.length; i++) if (E.outsideHours(own[i][0], own[i][1], af, at)) return false;
    var all = own.concat(meet);
    for (i = 0; i < all.length; i++) {
      var isMeet = i >= own.length;
      for (j = 0; j < busy.length; j++) {
        var b = busy[j];
        if (sid(b[2]) === s0) continue;
        var need = (isMeet && b[2].indexOf('session:') === 0) ? 0 : minGap;
        if (gap(all[i], [b[0], b[1]]) < need) return false;
      }
    }
    for (i = 0; i < meet.length; i++) for (j = 0; j < own.length; j++) if (gap(meet[i], own[j]) < minGap) return false;
    return true;
  };

  E.autoAssign = function (ev, keepLocked) {
    if (keepLocked === undefined) keepLocked = true;
    var r0 = E.buildSlots(ev), slots = r0[0];
    var st = new State(ev, slots);
    var old = keepLocked ? (ev.assignments || {}) : {};
    var validKeys = [];
    slots.forEach(function (s) { validKeys = validKeys.concat(E.slotKeys(s)); });
    var valid = {}; validKeys.forEach(function (k) { valid[k] = 1; });
    Object.keys(old).forEach(function (k) {
      var v = old[k];
      if (v.locked && valid[k] && has(st.off, v.official)) { st.put(k, v.official); st.locked[k] = 1; }
      else if (v.locked && valid[k] && !v.official) { st.assign[k] = ''; st.locked[k] = 1; }
    });
    var byKey = {};
    slots.forEach(function (s) { (byKey[s.key] = byKey[s.key] || []).push(s); });
    function freeKeys(slot, name) {
      return E.slotKeys(slot).filter(function (k) { return !has(st.assign, k) || (name && st.assign[k] === name); });
    }
    function takePrimary(name, slot, keys) {
      st.primary[name] = slot.id;
      (keys || E.slotKeys(slot)).forEach(function (k) { if (!has(st.assign, k)) st.put(k, name); });
    }
    function coverable(name, slot) {
      return E.slotKeys(slot).filter(function (k) { return !has(st.assign, k) && st.fits(name, k, 0); });
    }
    Object.keys(st.locked).sort().forEach(function (k) {
      var n = st.assign[k], s = sid(k);
      if (n && !has(st.primary, n) && st.slots[s].kind === 'primary') st.primary[n] = s;
    });
    // 1) explicit primaries
    st.names.forEach(function (name) {
      if (has(st.primary, name)) return;
      var want = st.off[name].primary || '';
      if (!want || !byKey[want]) return;
      for (var i = 0; i < byKey[want].length; i++) {
        var slot = byKey[want][i];
        var mine = E.slotKeys(slot).filter(function (k) { return st.part(name, k); });
        if (mine.length && mine.every(function (k) { return !has(st.assign, k); })) {
          var keys = coverable(name, slot);
          if (keys.length) { takePrimary(name, slot, keys); break; }
        }
      }
    });
    function give(slot, queue) {
      while (queue.length) {
        var best = null, bestKeys = [];
        for (var i = 0; i < queue.length; i++) {
          var keys = coverable(queue[i], slot);
          if (keys.length > bestKeys.length) {
            best = queue[i]; bestKeys = keys;
            var freeN = E.slotKeys(slot).filter(function (k) { return !has(st.assign, k); }).length;
            if (keys.length === freeN) break;
          }
        }
        if (!best) return;
        queue.splice(queue.indexOf(best), 1);
        takePrimary(best, slot, bestKeys);
        if (E.slotKeys(slot).every(function (k) { return has(st.assign, k); })) return;
      }
    }
    // 2) automatic primaries by priority
    var queue = st.names.filter(function (n) { return !has(st.primary, n); });
    var i, s;
    var prim = slots.filter(function (x) { return x.kind === 'primary'; });
    for (i = 0; i < prim.length; i++) {
      if (!queue.length) break;
      if (!freeKeys(prim[i]).length) continue;
      give(prim[i], queue);
    }
    // 3) spare officials take secondary-kind positions as their primary (not Starter etc.)
    var natural = ['head_referee', 'cro'];
    var secs = slots.filter(function (x) {
      return x.kind === 'secondary' && natural.indexOf(ref.POSITION_INDEX[x.key].prefer_holder) < 0;
    });
    for (i = 0; i < secs.length; i++) {
      if (!queue.length) break;
      if (!freeKeys(secs[i]).length) continue;
      give(secs[i], queue);
    }
    // 4) everything else as secondary jobs
    var todo = [];
    slots.forEach(function (sl) {
      E.slotKeys(sl).forEach(function (k) {
        if (!has(st.assign, k)) {
          var ws = st.windowsOf(k);
          todo.push([sl.priority, minOf(ws.map(function (w) { return w[0]; }), 0), k]);
        }
      });
    });
    todo.sort(cmp);
    function candidates(key) {
      var s1 = sid(key), slot = st.slots[s1], pos = ref.POSITION_INDEX[slot.key], out = [];
      st.names.forEach(function (name, idx) {
        var rules = st.holderRules(name);
        if (rules !== null && rules !== undefined && rules.indexOf(slot.key) < 0) return;
        var sc = st.secondaries(name, st.keyDay(key)), nsec = Object.keys(sc).length;
        var maxs = pyInt(get(st.off[name], 'max_secondary', 3) || 0);
        if (!has(sc, s1) && nsec >= maxs) return;
        if (!st.fits(name, key, 0)) return;
        var score = st.fits(name, key, st.buffer) ? 40 : 0;
        if (E.slotKeys(slot).some(function (k) { return st.assign[k] === name; })) score += 100;
        var p = st.primary[name];
        if (p && pos.prefer_holder && st.slots[p].key === pos.prefer_holder) score += 60;
        score -= 12 * nsec;
        if (!p) score += 5;
        out.push([score, -idx, name]);
      });
      out.sort(function (a, b) { return -cmp(a, b); });
      return out.map(function (x) { return x[2]; });
    }
    todo.forEach(function (t) {
      var key = t[2];
      if (has(st.assign, key)) return;
      var c = candidates(key);
      if (c.length) st.put(key, c[0]);
    });
    var nw = {};
    validKeys.forEach(function (k) { if (has(st.assign, k)) nw[k] = { official: st.assign[k], locked: !!st.locked[k] }; });
    ev.assignments = nw;
    ev._primary = Object.assign({}, st.primary);
    return ev;
  };

  // ------------------------------------------------------------ evaluation
  E.primaryMap = function (ev, slots) {
    var sl = {}; slots.forEach(function (s) { sl[s.id] = s; });
    var held = {}, out = {};
    Object.keys(ev.assignments || {}).forEach(function (k) {
      var n = ev.assignments[k].official;
      if (n) (held[n] = held[n] || []).push(sid(k));
    });
    ev.officials.forEach(function (o) {
      var n = o.name;
      if (!n || !held[n]) return;
      var ids = uniq(held[n]).filter(function (i) { return has(sl, i); });
      var pick = null, want = o.primary;
      for (var i = 0; i < ids.length; i++) if (sl[ids[i]].key === want) { pick = ids[i]; break; }
      if (pick === null) {
        var stored = (ev._primary || {})[n];
        pick = ids.indexOf(stored) >= 0 ? stored : null;
      }
      if (pick === null) {
        var pr = sortBy(ids.filter(function (i) { return sl[i].kind === 'primary'; }), function (i) { return sl[i].priority; });
        pick = (pr.length ? pr : (ids.length ? ids : [null]))[0];
      }
      if (pick) out[n] = pick;
    });
    return out;
  };

  E.evaluate = function (ev) {
    var r0 = E.buildSlots(ev), slots = r0[0], tls = r0[1];
    var sl = {}; slots.forEach(function (s) { sl[s.id] = s; });
    var raceById = {}; ev.races.forEach(function (r) { raceById[r.id] = r; });
    var fmt = E.whenFormatter(ev), multi = E.isMultiday(ev);
    function raceName(r) {
      if (E.isDayKey(r)) {
        if (!multi) return 'All races';
        var d = r.indexOf('day:') === 0 ? E.parseDate(r.slice(4)) : E.baseDate(ev);
        return 'All races – ' + E.dayLabel(d);
      }
      return raceById[r].name;
    }
    var buffer = num(get(ev.settings, 'buffer', 5)), asg = ev.assignments || {}, prim = E.primaryMap(ev, slots);
    var rows = [];
    slots.forEach(function (s) {
      Object.keys(s.windows).forEach(function (r) {
        var wins = s.windows[r], k = s.id + '|' + r, v = asg[k] || {}, name = v.official || '';
        var bl = blocking(wins); if (!bl.length) bl = wins.map(function (w) { return [w[0], w[1]]; });
        var start = bl.length ? minOf(bl.map(function (w) { return w[0]; })) : null;
        var end = bl.length ? maxOf(bl.map(function (w) { return w[1]; })) : null;
        var role = name ? (prim[name] === s.id ? 'Primary' : 'Secondary') : '';
        rows.push({ key: k, slot: s.id, pos_key: s.key, title: s.title, kind: s.kind, race_id: r, race: raceName(r),
          races_of: has(s.races_of, r) ? s.races_of[r] : [r], date: start !== null ? E.dateAt(ev, start) : '',
          official: name, locked: !!v.locked, role: role, start: start, end: end, windows: wins, toc: s.toc,
          status: '', priority: s.priority });
      });
    });
    var sess = E.sessionsAbs(ev), sessOn = sess.filter(function (se) { return se.enabled; });
    var attend = {}, attendOrder = [];
    rows.forEach(function (r) {
      var n = r.official;
      if (!n) return;
      sessOn.forEach(function (se) {
        if ((se.attendees.indexOf(r.pos_key) >= 0 || se.attendees.indexOf('all_tos') >= 0) && intersects(r.races_of, se.for_races)) {
          if (!has(attend, n)) { attend[n] = {}; attendOrder.push(n); }
          attend[n][se.id] = se;
        }
      });
    });
    var e_ = ev.event;
    var wtPeople = [['td', e_.td || 'Technical Delegate', 'Technical Delegate'], ['md', e_.md || 'Medical Delegate', 'Medical Delegate']];
    var jury = (e_.jury || []).filter(function (j) { return j; });
    if (!jury.length) jury = ['Competition Jury'];
    jury.forEach(function (j) { wtPeople.push(['jury', j, 'Competition Jury member']); });
    function sessionRow(se, who) {
      return { key: 'session:' + se.id, slot: 'session:' + se.id, pos_key: 'session', title: se.name, kind: 'session',
        race_id: 'session', race: 'Meetings & briefings', races_of: se.for_races, date: se.date, official: who,
        locked: false, role: 'Obligation', start: se.s, end: se.e, windows: [[se.s, se.e, se.name, true, 'session']],
        toc: se.ref, status: '', priority: 0 };
    }
    var sessionRows = {};
    attendOrder.forEach(function (n) { sessionRows[n] = Object.keys(attend[n]).map(function (id) { return sessionRow(attend[n][id], n); }); });
    wtPeople.forEach(function (w) {
      sessionRows[w[1]] = sessOn.filter(function (se) { return se.attendees.indexOf(w[0]) >= 0; }).map(function (se) { return sessionRow(se, w[1]); });
    });
    // conflicts
    var per = {}, perOrder = [];
    function addPer(n, item) { if (!has(per, n)) { per[n] = []; perOrder.push(n); } per[n].push(item); }
    rows.forEach(function (r) {
      if (!r.official) return;
      r.windows.forEach(function (w) { if (w[3]) addPer(r.official, [w[0], w[1], r.key, r.title, w[2]]); });
    });
    Object.keys(sessionRows).forEach(function (n) {
      sessionRows[n].forEach(function (r) { addPer(n, [r.start, r.end, r.key, r.title, 'meeting / briefing']); });
    });
    var conflicts = [], status = {};
    function skey(n, k) { return n + '\u0000' + k; }
    perOrder.forEach(function (name) {
      var items = per[name].slice().sort(cmp);
      for (var i = 0; i < items.length; i++) {
        for (var j = i + 1; j < items.length; j++) {
          var a = items[i], b = items[j];
          if (sid(a[2]) === sid(b[2])) continue;
          var g = gap([a[0], a[1]], [b[0], b[1]]);
          var both = a[2].indexOf('session:') === 0 && b[2].indexOf('session:') === 0;
          if (g < (both ? 0 : buffer)) {
            var level = g < 0 ? 'CONFLICT' : 'TIGHT';
            conflicts.push({ official: name, a: a[3], a_label: a[4], b: b[3], b_label: b[4],
              a_time: fmt(a[0]) + '–' + E.fmtHHMM(((a[1] % 1440) + 1440) % 1440),
              b_time: fmt(b[0]) + '–' + E.fmtHHMM(((b[1] % 1440) + 1440) % 1440),
              gap: Math.round(g * 10) / 10, level: level });
            [a[2], b[2]].forEach(function (k) { if (status[skey(name, k)] !== 'CONFLICT') status[skey(name, k)] = level; });
          }
        }
      }
    });
    var off = {}; ev.officials.forEach(function (o) { off[o.name] = o; });
    rows.forEach(function (r) {
      var n = r.official;
      if (n && has(off, n)) {
        var o = off[n];
        if (!r.races_of.every(function (x) { return E.takesPart(o, x); })) {
          status[skey(n, r.key)] = 'CONFLICT';
          conflicts.push({ official: n, a: r.title, a_label: 'does not work this race', b: r.race, b_label: '',
            a_time: fmt(r.start) + '–' + E.fmtHHMM((r.end || 0) % 1440), b_time: '', gap: null, level: 'CONFLICT' });
        }
        var af = E.parseHHMM(o.available_from), at = E.parseHHMM(o.available_to);
        if (r.start !== null && E.outsideHours(r.start, r.end, af, at)) {
          status[skey(n, r.key)] = 'CONFLICT';
          conflicts.push({ official: n, a: r.title, a_label: 'outside availability', b: '', b_label: '',
            a_time: fmt(r.start) + '–' + E.fmtHHMM(r.end % 1440),
            b_time: (o.available_from || '…') + '–' + (o.available_to || '…'), gap: null, level: 'CONFLICT' });
        }
      } else if (n && !has(off, n)) {
        status[skey(n, r.key)] = 'CONFLICT';
      }
    });
    rows.forEach(function (r) {
      if (!r.official) r.status = r.locked ? 'LOC / volunteer' : 'UNFILLED';
      else r.status = status[skey(r.official, r.key)] || 'OK';
    });
    Object.keys(sessionRows).forEach(function (n) {
      sessionRows[n].forEach(function (r) { r.status = status[skey(n, r.key)] || 'OK'; });
    });
    rows = sortBy(rows, function (r) { return [r.priority, r.slot, r.start !== null ? r.start : 0]; });
    var rsorted = E.racesSorted(ev);
    var officials = ev.officials.map(function (o) {
      var n = o.name, mine = rows.filter(function (r) { return r.official === n; }), p = prim[n];
      return {
        name: n, country: o.country || '',
        races: rsorted.filter(function (r) { return E.takesPart(o, r.id); }).map(function (r) { return r.id; }),
        primary: has(sl, p) ? sl[p].title : '',
        secondary: uniq(mine.filter(function (r) { return r.slot !== p; }).map(function (r) { return r.title; })).sort(),
        duties: sortBy(mine.concat(sessionRows[n] || []), function (r) { return r.start || 0; }),
        conflicts: conflicts.filter(function (c) { return c.official === n; }).length,
        busy_min: mine.reduce(function (a, r) { return a + ((r.end || 0) - (r.start || 0)); }, 0)
      };
    });
    var e = ev.event;
    var personal = ev.officials.filter(function (o) { return get(o, 'radio', true) && o.name; }).length;
    personal += (e.td ? 1 : 0) + (e.md ? 1 : 0);
    var vcc = pyInt(get(e, 'vcc_base', 1) || 0);
    var spare = Math.ceil(personal * num(get(e, 'spare_pct', 10) || 0) / 100);
    var radios = { personal: personal, vcc: vcc, spare: spare, total: personal + vcc + spare };
    var wtOfficials = wtPeople.map(function (w) {
      return { name: w[1], role: w[2], duties: sortBy(sessionRows[w[1]] || [], function (r) { return r.start; }),
        conflicts: conflicts.filter(function (c) { return c.official === w[1]; }).length };
    });
    var namesBy = {};
    attendOrder.forEach(function (n) { Object.keys(attend[n]).forEach(function (id) { (namesBy[id] = namesBy[id] || []).push(n); }); });
    sess.forEach(function (se) {
      var wt = wtPeople.filter(function (w) { return se.attendees.indexOf(w[0]) >= 0; }).map(function (w) { return w[1]; });
      se.people = wt.concat((namesBy[se.id] || []).slice().sort());
    });
    return { slots: slots, timelines: tls, rows: rows, conflicts: conflicts, fmt: fmt, sessions: sess,
      wt_officials: wtOfficials, warnings: E.startWindowWarnings(ev), multiday: multi, dates: E.eventDates(ev),
      officials: officials, radios: radios, unfilled: rows.filter(function (r) { return r.status === 'UNFILLED'; }),
      n_conflict: conflicts.filter(function (c) { return c.level === 'CONFLICT'; }).length,
      n_tight: conflicts.filter(function (c) { return c.level === 'TIGHT'; }).length };
  };

  E.runSheet = function (ev, result) {
    result = result || E.evaluate(ev);
    var out = [];
    E.racesSorted(ev).forEach(function (r) {
      var tl = result.timelines[r.id];
      E.MILESTONES.forEach(function (m) { out.push({ time: tl[m[0]], race: r.name, item: m[1], key: m[0], race_id: r.id }); });
    });
    result.sessions.forEach(function (se) {
      if (se.enabled) out.push({ time: se.s, race: 'Meetings & briefings', item: se.name + ' (until ' + E.fmtHHMM(se.end) + ')', key: 'session', race_id: 'session' });
    });
    return sortBy(out, function (x) { return x.time; });
  };
  E.setAssignment = function (ev, key, official, locked) {
    if (locked === undefined) locked = true;
    ev.assignments = ev.assignments || {};
    ev.assignments[key] = { official: official || '', locked: locked };
  };
  E.clearUnlocked = function (ev) {
    var n = {};
    Object.keys(ev.assignments || {}).forEach(function (k) { if (ev.assignments[k].locked) n[k] = ev.assignments[k]; });
    ev.assignments = n;
  };
  E.lockAll = function (ev, locked) {
    Object.keys(ev.assignments || {}).forEach(function (k) { ev.assignments[k].locked = locked !== false; });
  };

  W.E = E;
})(WTP);
if (typeof module !== 'undefined') module.exports = WTP;
