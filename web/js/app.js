/* Technical Officials Scheduler – user interface (plain JavaScript, works offline).
 * Same data model and plan as the Ubuntu app: one event = one .wtplan.json document. */
var WTP = (typeof WTP !== 'undefined') ? WTP : {};
(function (W) {
  'use strict';
  var E = W.E, X = W.X, ref = W.ref, Store = W.Store;
  var A = W.App = {
    ev: null, res: null, docId: null, undo: [], redo: [], auto: true,
    group: 'events', section: 'library', library: [],
    filt: { race: '', q: '', problems: false },
    gantt: { day: '', mode: 'officials', zoom: 3, dark: false },
    sched: '', shiftRace: '', selDay: '', cal: null, saveTimer: null, wide: false
  };

  // ============================================================ navigation model
  var GROUPS = [
    { id: 'events', label: 'Events', icon: 'calendar', sections: [['library', 'Calendar & events']] },
    { id: 'setup', label: 'Setup', icon: 'sliders', sections: [['event', 'Event'], ['races', 'Races'], ['officials', 'Officials'],
      ['participation', 'Who works which race'], ['positions', 'Positions'], ['duties', 'Duty times & tweaks'], ['meetings', 'Meetings & briefings']] },
    { id: 'plan', label: 'Plan', icon: 'check', sections: [['assignments', 'Assignments'], ['conflicts', 'Conflicts']] },
    { id: 'views', label: 'Views', icon: 'chart', sections: [['schedules', 'Personal schedules'], ['gantt', 'Gantt'], ['timeline', 'Timeline']] },
    { id: 'athletes', label: 'Athletes', icon: 'runner', sections: [['athletes', 'Athletes’ guide']] },
    { id: 'more', label: 'More', icon: 'more', sections: [['export', 'Export & share'], ['references', 'Rules & references'], ['about', 'About & privacy']] }
  ];
  var ICONS = {
    calendar: 'M7 2v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2H7zm-2 8h14v10H5V10z',
    sliders: 'M4 6h10v2H4V6zm12-1h2v1h2v2h-2v1h-2V5zM4 16h4v2H4v-2zm6-1h2v1h8v2h-8v1h-2v-4zM4 11h8v2H4v-2zm10-1h2v4h-2v-1h0v-2z M18 11h2v2h-2z',
    check: 'M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4z',
    chart: 'M3 5h8v3H3V5zm4 5.5h10v3H7v-3zM11 16h10v3H11v-3z',
    runner: 'M13.5 2a2 2 0 1 1 0 4 2 2 0 0 1 0-4zM10 7h4l2.6 4.6 3 .9-.6 1.9-3.8-1.1-1.2-2.1-1 3.3 2.5 2.5V22h-2v-4.2l-2.6-2.6-1.3 3.6L6 22l-1.5-1.3L7.7 17l1.8-6.1-2 1.5V15h-2v-3.6z',
    more: 'M6 10.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm6 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z',
    undo: 'M12.5 8c-2.65 0-5.05 1-6.9 2.6L2 7v9h9l-3.62-3.62A7.95 7.95 0 0 1 12.5 10.5c3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z',
    redo: 'M18.4 10.6C16.55 9 14.15 8 11.5 8c-4.65 0-8.58 3.03-9.96 7.22l2.36.78A8 8 0 0 1 11.5 10.5c1.95 0 3.73.72 5.12 1.88L13 16h9V7l-3.6 3.6z',
    lock: 'M12 2a5 5 0 0 0-5 5v3H5v12h14V10h-2V7a5 5 0 0 0-5-5zm-3 8V7a3 3 0 0 1 6 0v3H9z',
    unlock: 'M12 2a5 5 0 0 0-5 5h2a3 3 0 0 1 6 0v3H5v12h14V10h-2V7a5 5 0 0 0-5-5z',
    trash: 'M9 3v1H4v2h16V4h-5V3H9zM5 8l1 13h12l1-13H5z',
    plus: 'M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z',
    copy: 'M8 3h11v13h-2V5H8V3zM4 7h11v14H4V7z'
  };
  function icon(name, size) {
    var s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    s.setAttribute('viewBox', '0 0 24 24'); s.setAttribute('width', size || 20); s.setAttribute('height', size || 20);
    s.setAttribute('aria-hidden', 'true');
    var p = document.createElementNS('http://www.w3.org/2000/svg', 'path'); p.setAttribute('d', ICONS[name] || ''); p.setAttribute('fill', 'currentColor');
    s.appendChild(p); return s;
  }

  // ============================================================ DOM helpers
  function h(tag, attrs) {
    var el = document.createElement(tag), kids = Array.prototype.slice.call(arguments, 2);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === undefined || v === null || v === false) return;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k === 'on') Object.keys(v).forEach(function (ev) { el.addEventListener(ev, v[ev]); });
      else if (k === 'style') el.setAttribute('style', v);
      else if (k === 'value' || k === 'checked' || k === 'selected' || k === 'disabled' || k === 'indeterminate') el[k] = v;
      else el.setAttribute(k, v === true ? '' : v);
    });
    kids.forEach(function add(c) {
      if (c === null || c === undefined || c === false) return;
      if (Array.isArray(c)) c.forEach(add);
      else el.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
    });
    return el;
  }
  function field(label, control, hint, cls) {
    var simple = control && /^(INPUT|SELECT|TEXTAREA)$/.test(control.tagName || '');
    if (simple && !control.getAttribute('aria-label')) control.setAttribute('aria-label', label);
    return h(simple ? 'label' : 'div', { class: 'field ' + (cls || '') }, h('span', { class: 'flabel', text: label }), control,
      hint ? h('span', { class: 'fhint', text: hint }) : null);
  }
  function input(key, value, onChange, o) {
    o = o || {};
    var el = h('input', { type: o.type || 'text', 'data-k': key, value: value == null ? '' : String(value), placeholder: o.placeholder,
      min: o.min, max: o.max, step: o.step, inputmode: o.inputmode, class: o.cls, 'aria-label': o.aria, autocomplete: 'off',
      autocapitalize: o.autocap || 'sentences', spellcheck: 'false', list: o.list });
    el.addEventListener('change', function () { onChange(el.value, el); });
    return el;
  }
  function numIn(key, value, onChange, o) {
    o = Object.assign({ type: 'number', inputmode: 'decimal', step: 'any' }, o || {});
    return input(key, value, function (v, el) {
      if (v === '' && o.allowEmpty) return onChange(null);
      var n = parseFloat(v);
      if (!isFinite(n)) { toast('Please enter a number'); el.value = value == null ? '' : value; return; }
      onChange(n);
    }, o);
  }
  function select(key, options, value, onChange, o) {
    o = o || {};
    var el = h('select', { 'data-k': key, class: o.cls, 'aria-label': o.aria });
    options.forEach(function (op) {
      if (op.group) {
        var g = h('optgroup', { label: op.group });
        op.options.forEach(function (x) { g.appendChild(h('option', { value: x[0], text: x[1], selected: String(x[0]) === String(value), disabled: x[2] })); });
        el.appendChild(g);
      } else el.appendChild(h('option', { value: op[0], text: op[1], selected: String(op[0]) === String(value), disabled: op[2] }));
    });
    el.addEventListener('change', function () { onChange(el.value, el); });
    return el;
  }
  function check(key, checked, onChange, label, o) {
    o = o || {};
    var el = h('input', { type: 'checkbox', 'data-k': key, checked: !!checked, 'aria-label': o.aria || label, class: o.switch ? 'switch' : '' });
    el.addEventListener('change', function () { onChange(el.checked); });
    return label ? h('label', { class: 'check' }, el, h('span', { text: label })) : el;
  }
  function btn(label, onClick, cls, ic, title) {
    var b = h('button', { type: 'button', class: 'btn ' + (cls || ''), title: title || null, 'aria-label': title || null },
      ic ? icon(ic, 18) : null, label ? h('span', { text: label }) : null);
    b.addEventListener('click', function (e) { e.preventDefault(); onClick(e); });
    return b;
  }
  function card(title, body, extra, cls) {
    return h('section', { class: 'card ' + (cls || '') }, title ? h('div', { class: 'card-head' }, h('h3', { text: title }), extra || null) : null, body);
  }
  function chip(status) {
    var cls = { 'OK': 'ok', 'TIGHT': 'tight', 'CONFLICT': 'bad', 'UNFILLED': 'unf', 'LOC / volunteer': 'loc', 'WARNING': 'tight' }[status] || 'neutral';
    return h('span', { class: 'chip ' + cls, text: status });
  }
  function note(text, cls) { return h('p', { class: 'note ' + (cls || ''), text: text }); }
  function empty(text) { return h('div', { class: 'empty', text: text }); }
  var fmtT = function (m) { return A.res ? A.res.fmt(m) : E.fmtHHMM(m); };
  function hm(m) { return E.fmtHHMM(((m % 1440) + 1440) % 1440); }
  function raceById(id) { return A.ev.races.filter(function (r) { return r.id === id; })[0]; }
  function posTitle(k) { return ref.POSITION_INDEX[k] ? ref.POSITION_INDEX[k].title : k; }
  function plural(n, w) { return n + ' ' + w + (n === 1 ? '' : 's'); }
  function longDate(iso) {
    if (!iso) return '';
    var p = iso.split('-'), M = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return E.dayLabel(iso).split(' ')[0] + ' ' + (+p[2]) + ' ' + M[+p[1] - 1] + ' ' + p[0];
  }

  // ============================================================ toast & dialogs
  var toastTimer = null;
  function toast(msg, ms) {
    var t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.classList.remove('show'); }, ms || 2600);
  }
  A.toast = toast;
  function dialog(title, body, buttons) {
    return new Promise(function (resolve) {
      var dlg = h('dialog', { class: 'dlg' });
      var foot = h('div', { class: 'dlg-foot' });
      (buttons || [['OK', true, 'primary']]).forEach(function (b) {
        foot.appendChild(btn(b[0], function () { var v = typeof b[1] === 'function' ? b[1]() : b[1]; if (v === undefined) return; dlg.close(); dlg.remove(); resolve(v); }, b[2]));
      });
      dlg.appendChild(h('form', { method: 'dialog', on: { submit: function (e) { e.preventDefault(); } } },
        h('h2', { text: title }), h('div', { class: 'dlg-body' }, body), foot));
      dlg.addEventListener('cancel', function (e) { e.preventDefault(); dlg.close(); dlg.remove(); resolve(null); });
      document.body.appendChild(dlg);
      dlg.showModal();
      var f = dlg.querySelector('input, select, textarea'); if (f && !('ontouchstart' in window)) f.focus();
    });
  }
  function confirmBox(title, text, okLabel, danger) {
    return dialog(title, h('p', { text: text }), [['Cancel', false, ''], [okLabel || 'OK', true, danger ? 'danger' : 'primary']]);
  }

  // ============================================================ state, undo, saving
  function recompute() { A.res = E.evaluate(A.ev); }
  function snapshot() { return JSON.stringify(A.ev); }
  function edit(fn, opts) {
    opts = opts || {};
    A.undo.push(snapshot()); if (A.undo.length > 60) A.undo.shift();
    A.redo = [];
    try { fn(); } catch (err) { console.error(err); toast('Could not apply: ' + err.message); }
    afterChange(opts);
  }
  A.edit = edit;
  function afterChange(opts) {
    opts = opts || {};
    if (A.auto && !opts.noPlan) E.autoAssign(A.ev, true);
    recompute(); scheduleSave(); render();
  }
  function undo() {
    if (!A.undo.length) return toast('Nothing to undo');
    A.redo.push(snapshot()); A.ev = JSON.parse(A.undo.pop()); recompute(); scheduleSave(); render();
  }
  function redo() {
    if (!A.redo.length) return toast('Nothing to redo');
    A.undo.push(snapshot()); A.ev = JSON.parse(A.redo.pop()); recompute(); scheduleSave(); render();
  }
  function meta() {
    var e = A.ev.event;
    return { name: e.name || 'Event', venue: e.venue || '', dates: E.raceDates(A.ev), races: A.ev.races.length,
      officials: A.ev.officials.length, unfilled: A.res ? A.res.unfilled.length : 0, conflicts: A.res ? A.res.n_conflict : 0 };
  }
  function scheduleSave() {
    clearTimeout(A.saveTimer);
    A.saveTimer = setTimeout(saveNow, 500);
  }
  function saveNow() {
    if (!A.ev || !A.docId) return Promise.resolve();
    clearTimeout(A.saveTimer);
    return Store.save(A.docId, X.toJSON(A.ev), meta()).then(function () {
      Store.setPref('lastDoc', A.docId);
      return refreshLibrary();
    }).catch(function (e) { toast('Not saved: ' + e.message, 5000); });
  }
  function refreshLibrary() { return Store.list().then(function (l) { A.library = l || []; if (A.section === 'library') render(); }); }
  function newDocId() { return 'ev-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 6); }
  function openEvent(ev, docId, goTo) {
    A.ev = E.normalise(ev); A.docId = docId || newDocId(); A.undo = []; A.redo = [];
    if (!Object.keys(A.ev.assignments || {}).length) E.autoAssign(A.ev, true);
    recompute();
    A.gantt.day = ''; A.sched = ''; A.shiftRace = ''; A.filt = { race: '', q: '', problems: false };
    Store.setPref('lastDoc', A.docId);
    saveNow();
    go(goTo || 'assignments');
  }
  A.openJSONText = function (text, name) {
    try {
      var ev = X.fromJSON(text);
      openEvent(ev, null, 'assignments');
      toast('Opened ' + (name || ev.event.name || 'event'));
    } catch (e) { toast('Not a plan file: ' + e.message, 5000); }
  };
  A.openExternal = A.openJSONText;          // called by the native app when a file is opened from Files / Finder

  // ============================================================ rendering
  function go(section) {
    GROUPS.forEach(function (g) { g.sections.forEach(function (s) { if (s[0] === section) A.group = g.id; }); });
    A.section = section;
    Store.setPref('section', section);
    render(true);
  }
  A.go = go;
  var SECTIONS = {};
  function render(resetScroll) {
    var main = document.getElementById('main');
    var active = document.activeElement, focusKey = active && active.getAttribute && active.getAttribute('data-k');
    var scroll = resetScroll ? 0 : main.scrollTop;
    renderChrome();
    var body = h('div', { class: 'section sec-' + A.section });
    if (A.section !== 'library' && A.section !== 'about' && A.section !== 'references' && !A.ev) {
      body.appendChild(empty('Open or create an event first.'));
    } else {
      try { (SECTIONS[A.section] || SECTIONS.library)(body); }
      catch (err) { console.error(err); body.appendChild(note('Something went wrong drawing this page: ' + err.message, 'bad')); }
    }
    main.replaceChildren(subnav(), body);
    main.scrollTop = scroll;
    if (focusKey) {
      var el = main.querySelector('[data-k="' + focusKey.replace(/"/g, '\\"') + '"]');
      if (el && el !== active) try { el.focus({ preventScroll: true }); } catch (e) { /* ignore */ }
    }
  }
  A.render = render;
  function renderChrome() {
    var title = document.getElementById('doc-title');
    title.textContent = A.ev ? (A.ev.event.name || 'Untitled event') : ref.APP_NAME;
    var sub = document.getElementById('doc-sub');
    sub.textContent = A.ev ? (E.raceDates(A.ev).map(longDate).join(' – ') + (A.ev.event.venue ? ' · ' + A.ev.event.venue : '')) : '';
    var pill = document.getElementById('status-pill');
    pill.replaceChildren();
    if (A.res) {
      var r = A.res, bad = r.n_conflict, unf = r.unfilled.length, tight = r.n_tight;
      pill.className = 'pill ' + (bad ? 'bad' : unf ? 'unf' : tight || r.warnings.length ? 'tight' : 'ok');
      pill.textContent = bad || unf || tight ? (bad + ' conflicts · ' + tight + ' tight · ' + unf + ' unfilled') : 'All jobs covered';
      pill.hidden = false;
    } else pill.hidden = true;
    document.getElementById('btn-undo').disabled = !A.undo.length;
    document.getElementById('btn-redo').disabled = !A.redo.length;
    document.getElementById('auto-toggle').checked = A.auto;
    // sidebar + tab bar
    var side = document.getElementById('sidebar'); side.replaceChildren();
    GROUPS.forEach(function (g) {
      side.appendChild(h('div', { class: 'side-group' }, icon(g.icon, 16), h('span', { text: g.label })));
      g.sections.forEach(function (s) {
        side.appendChild(h('a', { href: '#' + s[0], class: 'side-link' + (A.section === s[0] ? ' active' : ''),
          'aria-current': A.section === s[0] ? 'page' : null, on: { click: function (e) { e.preventDefault(); go(s[0]); } } }, s[1]));
      });
    });
    var tabs = document.getElementById('tabbar'); tabs.replaceChildren();
    GROUPS.forEach(function (g) {
      tabs.appendChild(h('button', { type: 'button', class: 'tab' + (A.group === g.id ? ' active' : ''), 'aria-label': g.label,
        on: { click: function () { var last = Store.getPref('last.' + g.id, g.sections[0][0]); go(last); } } }, icon(g.icon, 24), h('span', { text: g.label })));
    });
    Store.setPref('last.' + A.group, A.section);
  }
  function subnav() {
    var g = GROUPS.filter(function (x) { return x.id === A.group; })[0];
    if (!g || g.sections.length < 2) return h('div', { class: 'subnav empty-subnav' });
    return h('div', { class: 'subnav', role: 'tablist' }, g.sections.map(function (s) {
      return h('button', { type: 'button', role: 'tab', class: 'seg' + (A.section === s[0] ? ' active' : ''), 'aria-selected': A.section === s[0] ? 'true' : 'false',
        on: { click: function () { go(s[0]); } } }, s[1]);
    }));
  }
  function header(title, desc, actions) {
    return h('div', { class: 'sec-head' }, h('div', null, h('h2', { text: title }), desc ? h('p', { class: 'muted', text: desc }) : null),
      actions ? h('div', { class: 'actions' }, actions) : null);
  }

  // ============================================================ Events: calendar + library
  SECTIONS.library = function (root) {
    var today = E.todayIso();
    if (!A.cal) { var t = (A.ev ? E.raceDates(A.ev)[0] : today).split('-'); A.cal = { y: +t[0], m: +t[1] }; }
    var marks = {};
    A.library.forEach(function (d) { (d.dates || []).forEach(function (x) { (marks[x] = marks[x] || []).push(d); }); });
    root.appendChild(header('Calendar & events', 'Every event is saved automatically on this device. Tap a day to see its events or start a new one.',
      [btn('New event', function () { newEventDialog(A.selDay || today); }, 'primary', 'plus'),
        btn('Open file…', importFile, '', null, 'Open a .wtplan.json file')]));
    var y = A.cal.y, m = A.cal.m, first = y + '-' + (m < 10 ? '0' : '') + m + '-01';
    var startPad = E.weekday(first), nDays = new Date(Date.UTC(y, m, 0)).getUTCDate();
    var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    var grid = h('div', { class: 'cal-grid', role: 'grid' });
    ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].forEach(function (d) { grid.appendChild(h('div', { class: 'cal-dow', text: d })); });
    for (var i = 0; i < startPad; i++) grid.appendChild(h('div', { class: 'cal-pad' }));
    for (var d = 1; d <= nDays; d++) {
      (function (iso, d) {
        var ev = marks[iso] || [];
        var cur = A.ev && E.eventDates(A.ev).indexOf(iso) >= 0;
        grid.appendChild(h('button', { type: 'button', class: 'cal-day' + (iso === today ? ' today' : '') + (iso === A.selDay ? ' sel' : '') + (ev.length ? ' has' : '') + (cur ? ' cur' : ''),
          'aria-label': longDate(iso) + (ev.length ? ', ' + plural(ev.length, 'event') : ''),
          on: { click: function () { A.selDay = A.selDay === iso ? '' : iso; render(); }, dblclick: function () { newEventDialog(iso); } } },
        h('span', { text: String(d) }), ev.length ? h('i', { class: 'dot' }) : null));
      })(first.slice(0, 8) + (d < 10 ? '0' : '') + d, d);
    }
    function shift(n) { var mm = A.cal.m + n, yy = A.cal.y; if (mm < 1) { mm = 12; yy--; } if (mm > 12) { mm = 1; yy++; } A.cal = { y: yy, m: mm }; render(); }
    var calCard = card(MONTHS[m - 1] + ' ' + y, grid, h('div', { class: 'row-btns' },
      btn('', function () { shift(-1); }, 'icon', null, 'Previous month'), btn('Today', function () { var t = today.split('-'); A.cal = { y: +t[0], m: +t[1] }; A.selDay = today; render(); }, 'small'),
      btn('', function () { shift(1); }, 'icon', null, 'Next month')), 'cal-card');
    calCard.querySelectorAll('.row-btns .icon')[0].textContent = '‹';
    calCard.querySelectorAll('.row-btns .icon')[1].textContent = '›';
    var list = A.selDay ? A.library.filter(function (x) { return (x.dates || []).indexOf(A.selDay) >= 0; }) : A.library;
    var lib = h('div', { class: 'lib-list' });
    if (!list.length) lib.appendChild(empty(A.selDay ? 'No event on ' + longDate(A.selDay) + '.' : 'No saved events yet.'));
    list.forEach(function (d) {
      var isCur = d.id === A.docId;
      lib.appendChild(h('div', { class: 'lib-item' + (isCur ? ' current' : '') },
        h('button', { type: 'button', class: 'lib-open', on: { click: function () { openDoc(d.id); } } },
          h('strong', { text: d.name || 'Event' }),
          h('span', { class: 'muted', text: (d.dates || []).map(longDate).join(' – ') + (d.venue ? ' · ' + d.venue : '') }),
          h('span', { class: 'muted small', text: plural(d.races || 0, 'race') + ' · ' + plural(d.officials || 0, 'official') +
            (d.unfilled ? ' · ' + d.unfilled + ' unfilled' : '') + (isCur ? ' · open now' : '') })),
        h('div', { class: 'row-btns' },
          btn('', function () { duplicateDoc(d.id); }, 'icon', 'copy', 'Duplicate'),
          btn('', function () { deleteDoc(d); }, 'icon danger-text', 'trash', 'Delete'))));
    });
    var libCard = card(A.selDay ? 'Events on ' + longDate(A.selDay) : 'All events', lib,
      A.selDay ? btn('New event on this day', function () { newEventDialog(A.selDay); }, 'small', 'plus') : null);
    var ex = card('Examples', h('div', { class: 'stack' },
      note('Placeholder officials (TO 01, TO 02 …). Open one, then replace the names with your team on the Officials page.'),
      h('div', { class: 'row-btns wrap' },
        btn('Elite back-to-back (standard)', function () { openEvent(JSON.parse(JSON.stringify(W.examples.example_q3)), null, 'assignments'); }),
        btn('Two-day weekend (sprint + relay)', function () { openEvent(JSON.parse(JSON.stringify(W.examples.example_multiday)), null, 'assignments'); }))));
    root.appendChild(h('div', { class: 'grid-2' }, calCard, h('div', { class: 'stack' }, libCard, ex)));
  };
  function openDoc(id) {
    if (id === A.docId) return go('assignments');
    saveNow().then(function () { return Store.load(id); }).then(function (text) {
      openEvent(X.fromJSON(text), id, 'assignments');
    }).catch(function (e) { toast('Could not open: ' + e.message, 5000); });
  }
  function duplicateDoc(id) {
    Store.load(id).then(function (text) {
      var ev = X.fromJSON(text); ev.event.name = (ev.event.name || 'Event') + ' (copy)';
      openEvent(ev, null, 'event'); toast('Duplicated');
    });
  }
  function deleteDoc(d) {
    confirmBox('Delete event?', '“' + (d.name || 'Event') + '” will be removed from this device. Exported files are not affected.', 'Delete', true).then(function (ok) {
      if (!ok) return;
      Store.remove(d.id).then(function () {
        if (d.id === A.docId) { A.ev = null; A.res = null; A.docId = null; Store.setPref('lastDoc', ''); }
        return refreshLibrary();
      }).then(function () { toast('Deleted'); render(); });
    });
  }
  function newEventDialog(date) {
    var f = { name: 'New event', date: date || E.todayIso(), n: 18, fmt: 'standard', cat: 'elite_women', start: '10:00', venue: '' };
    var body = h('div', { class: 'form-grid' },
      field('Event name', input('ne-name', f.name, function (v) { f.name = v; })),
      field('Venue', input('ne-venue', '', function (v) { f.venue = v; })),
      field('First race day', input('ne-date', f.date, function (v) { f.date = v; }, { type: 'date' })),
      field('First race start', input('ne-start', f.start, function (v) { f.start = v; }, { type: 'time' })),
      field('Format', select('ne-fmt', ref.FORMAT_ORDER.map(function (k) { return [k, ref.FORMATS[k].label]; }), f.fmt, function (v) { f.fmt = v; })),
      field('Category', select('ne-cat', ref.CATEGORY_ORDER.map(function (k) { return [k, ref.CATEGORIES[k].label]; }), f.cat, function (v) { f.cat = v; })),
      field('Number of officials', numIn('ne-n', f.n, function (v) { f.n = Math.max(0, Math.min(200, Math.round(v))); }, { min: 0, max: 200, step: 1, inputmode: 'numeric' })));
    body.querySelectorAll('input,select').forEach(function (el) { el.addEventListener('input', function () { el.dispatchEvent(new Event('change')); }); });
    dialog('New event', body, [['Cancel', null, ''], ['Create', true, 'primary']]).then(function (ok) {
      if (!ok) return;
      var race = E.newRace(f.fmt, f.cat, f.start || '10:00', null, f.date);
      var ev = E.newEvent(f.name || 'New event', f.date, [race], 0);
      ev.event.venue = f.venue;
      for (var i = 0; i < f.n; i++) ev.officials.push(E.newOfficial('TO ' + (i < 9 ? '0' : '') + (i + 1)));
      openEvent(ev, null, 'races');
      toast('Event created – add races and officials');
    });
  }
  function importFile() {
    var inp = h('input', { type: 'file', accept: '.json,.wtplan,application/json,text/plain', style: 'display:none' });
    inp.addEventListener('change', function () {
      var file = inp.files && inp.files[0]; if (!file) return;
      var rd = new FileReader();
      rd.onload = function () { A.openJSONText(String(rd.result), file.name); inp.remove(); };
      rd.onerror = function () { toast('Could not read the file'); inp.remove(); };
      rd.readAsText(file);
    });
    document.body.appendChild(inp); inp.click();
  }
  A.importFile = importFile;

  // ============================================================ Setup: event
  SECTIONS.event = function (root) {
    var e = A.ev.event;
    function set(k) { return function (v) { edit(function () { e[k] = v; }, { noPlan: k !== 'td' && k !== 'md' }); }; }
    root.appendChild(header('Event', 'Name, place and the World Triathlon officials. Races, officials and positions are on the next pages.'));
    var jury = h('div', { class: 'stack' }, (e.jury || []).map(function (j, i) {
      return h('div', { class: 'inline' }, input('jury-' + i, j, function (v) { edit(function () { e.jury[i] = v; }, { noPlan: true }); },
        { placeholder: 'Jury member ' + (i + 2) + ' (appointed by the TD)' }),
      btn('', function () { edit(function () { e.jury.splice(i, 1); }, { noPlan: true }); }, 'icon danger-text', 'trash', 'Remove'));
    }), btn('Add Jury member', function () { edit(function () { e.jury.push(''); }, { noPlan: true }); }, 'small', 'plus'));
    root.appendChild(h('div', { class: 'grid-2' },
      card('Event', h('div', { class: 'form-grid' },
        field('Event name', input('ev-name', e.name, set('name'))),
        field('Venue', input('ev-venue', e.venue, set('venue'))),
        field('Event date', input('ev-date', e.date, function (v) { edit(function () { e.date = v; }); }, { type: 'date' }), 'Used for races without their own date'),
        field('Notes', h('textarea', { 'data-k': 'ev-notes', rows: 4, on: { change: function (ev) { var v = ev.target.value; edit(function () { e.notes = v; }, { noPlan: true }); } } }, e.notes || ''), null, 'span2'))),
      card('World Triathlon officials', h('div', { class: 'form-grid' },
        field('Technical Delegate', input('ev-td', e.td, set('td'), { placeholder: 'Name (optional)' }), 'Chairs the Competition Jury (CR 12.6)'),
        field('Medical Delegate', input('ev-md', e.md, set('md'), { placeholder: 'Name (optional)' })),
        field('Competition Jury (other members)', jury, 'Not a TO, coach or athlete (CR 12.6)', 'span2'))),
      card('Radios', h('div', { class: 'stack' },
        h('div', { class: 'form-grid' },
          field('VCC base radios', numIn('ev-vcc', e.vcc_base, function (v) { edit(function () { e.vcc_base = Math.max(0, Math.round(v)); }, { noPlan: true }); }, { min: 0, step: 1, inputmode: 'numeric' })),
          field('Spare radios (%)', numIn('ev-spare', e.spare_pct, function (v) { edit(function () { e.spare_pct = Math.max(0, v); }, { noPlan: true }); }, { min: 0, step: 1 }))),
        radiosTable())),
      card('Races at a glance', raceOverview())));
  };
  function radiosTable() {
    var r = A.res.radios;
    return h('table', { class: 'tbl compact' }, h('tbody', null,
      [['Personal radios (TOs, TD, MD)', r.personal], ['VCC base radio', r.vcc], ['Spares', r.spare], ['Total', r.total]].map(function (x, i) {
        return h('tr', { class: i === 3 ? 'strong' : '' }, h('td', { text: x[0] }), h('td', { class: 'num', text: String(x[1]) }));
      })), h('caption', { class: 'muted small', text: 'One radio per TO who needs one (tick on the Officials page), plus the TD and MD (EOM 6.6.2).' }));
  }
  function raceOverview() {
    var box = h('div', { class: 'stack' });
    E.racesSorted(A.ev).forEach(function (r) {
      var tl = A.res.timelines[r.id];
      box.appendChild(h('div', { class: 'race-line' }, h('i', { class: 'swatch', style: 'background:' + X.raceColour(A.ev, r.id) }),
        h('div', null, h('strong', { text: r.name }), h('div', { class: 'muted small', text: fmtT(tl.start) + ' start · winner ≈ ' + hm(tl.winner) + ' · last finisher ≈ ' + hm(tl.last_finisher) }))));
    });
    A.res.warnings.forEach(function (w) { box.appendChild(note('⚠ ' + w, 'warn')); });
    box.appendChild(btn('Edit races', function () { go('races'); }, 'small'));
    return box;
  }

  // ============================================================ Setup: races
  function nextSlot() {
    var rs = E.racesSorted(A.ev); if (!rs.length) return { date: A.ev.event.date || E.todayIso(), start: '10:00' };
    var last = rs[rs.length - 1], d = E.raceDate(A.ev, last), s = E.parseHHMM(last.start, 600) + 165;
    if (s > 17 * 60) return { date: E.addDays(d, 1), start: '10:00' };
    return { date: d, start: E.fmtHHMM(s) };
  }
  function autoName(r) { return ref.CATEGORIES[r.category].label + ' – ' + ref.FORMATS[r.format].label.split(' (')[0]; }
  SECTIONS.races = function (root) {
    root.appendChild(header('Races', 'Each race has its own date and start time. Changing the format or category resets distances, laps and paces to the defaults.',
      [btn('Add race', function () {
        var sl = nextSlot(), last = E.racesSorted(A.ev).slice(-1)[0];
        edit(function () { A.ev.races.push(E.newRace(last ? last.format : 'standard', last ? (last.category === 'elite_women' ? 'elite_men' : last.category) : 'elite_women', sl.start, null, sl.date)); });
        toast('Race added on ' + longDate(sl.date) + ' at ' + sl.start);
      }, 'primary', 'plus')]));
    A.res.warnings.forEach(function (w) { root.appendChild(note('⚠ ' + w, 'warn')); });
    var wrap = h('div', { class: 'cards' });
    E.racesSorted(A.ev).forEach(function (r) { wrap.appendChild(raceCard(r)); });
    if (!A.ev.races.length) wrap.appendChild(empty('No races yet – add one.'));
    root.appendChild(wrap);
  };
  function raceCard(r) {
    var tl = A.res.timelines[r.id], sg = tl._segments, k = 'r-' + r.id + '-';
    function set(path, plan) {
      return function (v) {
        edit(function () {
          var o = r, p = path.split('.');
          for (var i = 0; i < p.length - 1; i++) o = o[p[i]];
          o[p[p.length - 1]] = v;
        }, { noPlan: plan === false });
      };
    }
    var dateVal = E.raceDate(A.ev, r);
    var main = h('div', { class: 'form-grid' },
      field('Name', input(k + 'name', r.name, set('name', false)), null, 'span2'),
      field('Date', input(k + 'date', dateVal, function (v) { if (!E.parseDate(v)) return toast('Choose a date'); set('date')(v); }, { type: 'date' })),
      field('Start', input(k + 'start', r.start, function (v) { if (E.parseHHMM(v) === null) return toast('Time as HH:MM'); set('start')(E.fmtHHMM(E.parseHHMM(v))); }, { type: 'time' })),
      field('Format', select(k + 'fmt', ref.FORMAT_ORDER.map(function (x) { return [x, ref.FORMATS[x].label]; }), r.format, function (v) {
        edit(function () { var wasAuto = r.name === autoName(r); E.applyFormat(r, v, r.category); if (wasAuto) r.name = autoName(r); });
      }), null, 'span2'),
      field('Category', select(k + 'cat', ref.CATEGORY_ORDER.map(function (x) { return [x, ref.CATEGORIES[x].label]; }), r.category, function (v) {
        edit(function () { var wasAuto = r.name === autoName(r); E.applyFormat(r, r.format, v); if (wasAuto) r.name = autoName(r); });
      }), null, 'span2'));
    var course = h('div', { class: 'form-grid g4' },
      field('Legs', numIn(k + 'legs', r.legs, function (v) { set('legs')(Math.max(1, Math.round(v))); }, { min: 1, step: 1 })),
      field('Swim (m)', numIn(k + 'swim', r.swim_m, set('swim_m'), { min: 0, step: 50 })),
      field('Bike (km)', numIn(k + 'bike', r.bike_km, set('bike_km'), { min: 0, step: 0.5 })),
      field('Run (km)', numIn(k + 'run', r.run_km, set('run_km'), { min: 0, step: 0.1 })),
      field('Swim laps', numIn(k + 'ls', r.laps.swim, function (v) { set('laps.swim')(Math.max(1, Math.round(v))); }, { min: 1, step: 1 })),
      field('Bike laps', numIn(k + 'lb', r.laps.bike, function (v) { set('laps.bike')(Math.max(1, Math.round(v))); }, { min: 1, step: 1 })),
      field('Run laps', numIn(k + 'lr', r.laps.run, function (v) { set('laps.run')(Math.max(1, Math.round(v))); }, { min: 1, step: 1 })),
      field('Start-line TOs', numIn(k + 'sl', r.start_line, function (v) { set('start_line')(Math.max(0, Math.round(v))); }, { min: 0, step: 1 })),
      field('Wheel stations', numIn(k + 'ws', r.wheel_stations, function (v) { set('wheel_stations')(Math.max(0, Math.round(v))); }, { min: 0, step: 1 })),
      field('Aid stations', numIn(k + 'as', r.aid_stations, function (v) { set('aid_stations')(Math.max(0, Math.round(v))); }, { min: 0, step: 1 })),
      h('div', { class: 'field span2' }, h('span', { class: 'flabel', text: 'Drafting' }), check(k + 'dl', r.draft_legal, set('draft_legal'), 'Draft-legal')));
    var P = r.paces, S = r.schedule;
    var adv = h('details', { class: 'adv' }, h('summary', { text: 'Paces, field spread and race-day times' }),
      h('div', { class: 'form-grid g4' },
        field('Swim pace (min/100 m)', numIn(k + 'sp', P.swim_pace, set('paces.swim_pace'), { step: 0.01 })),
        field('Bike speed (km/h)', numIn(k + 'bs', P.bike_speed, set('paces.bike_speed'), { step: 0.1 })),
        field('Run pace (min/km)', numIn(k + 'rp', P.run_pace, set('paces.run_pace'), { step: 0.01 })),
        field('T1 / T2 (min)', h('div', { class: 'inline' }, numIn(k + 't1', P.t1, set('paces.t1'), { step: 0.05 }), numIn(k + 't2', P.t2, set('paces.t2'), { step: 0.05 }))),
        field('Last out of water (+%)', numIn(k + 'gs', P.gap_swim, set('paces.gap_swim'), { step: 1 })),
        field('Last into T2 (+%)', numIn(k + 'gb', P.gap_t2, set('paces.gap_t2'), { step: 1 })),
        field('Last finisher (+%)', numIn(k + 'gf', P.gap_finish, set('paces.gap_finish'), { step: 1 }))),
      h('div', { class: 'form-grid g3' }, Object.keys(ref.SCHEDULE_DEFAULTS).map(function (s) {
        return field(ref.SCHEDULE_LABELS[s], numIn(k + 'sch-' + s, S[s], set('schedule.' + s), { step: 5 }));
      })),
      note('Typical Elite split times are not in the rule documents; these are editable defaults.', 'small'));
    var summary = h('div', { class: 'race-sum' },
      ['Swim ' + E.fmtDur(sg.swim), 'T1 ' + E.fmtDur(sg.t1), 'Bike ' + E.fmtDur(sg.bike), 'T2 ' + E.fmtDur(sg.t2), 'Run ' + E.fmtDur(sg.run)].map(function (t) { return h('span', { text: t }); }),
      h('span', { class: 'strong', text: 'Winner ≈ ' + hm(tl.winner) }), h('span', { text: 'Last finisher ≈ ' + hm(tl.last_finisher) }));
    var c = card(null, h('div', { class: 'stack' }, main, summary, h('details', { class: 'adv' }, h('summary', { text: 'Course, laps and stations' }), course), adv), null, 'race-card');
    c.style.setProperty('--race', X.raceColour(A.ev, r.id));
    c.insertBefore(h('div', { class: 'card-head' }, h('h3', null, h('i', { class: 'swatch', style: 'background:' + X.raceColour(A.ev, r.id) }), r.name),
      h('div', { class: 'row-btns' },
        btn('', function () { edit(function () { r.date = E.addDays(E.raceDate(A.ev, r), -1); }); }, 'icon small', null, 'Previous day'),
        btn('', function () { edit(function () { r.date = E.addDays(E.raceDate(A.ev, r), 1); }); }, 'icon small', null, 'Next day'),
        btn('', function () { edit(function () { var c2 = JSON.parse(JSON.stringify(r)); c2.id = E.newId('r'); var sl = nextSlot(); c2.date = sl.date; c2.start = sl.start; A.ev.races.push(c2); }); }, 'icon', 'copy', 'Duplicate race'),
        btn('', function () {
          if (A.ev.races.length < 2) return toast('An event needs at least one race');
          confirmBox('Delete race?', '“' + r.name + '” and its assignments will be removed.', 'Delete', true).then(function (ok) {
            if (ok) edit(function () { A.ev.races = A.ev.races.filter(function (x) { return x.id !== r.id; }); });
          });
        }, 'icon danger-text', 'trash', 'Delete race'))), c.firstChild);
    var hb = c.querySelectorAll('.card-head .icon.small'); hb[0].textContent = '−1 day'; hb[1].textContent = '+1 day';
    return c;
  }

  // ============================================================ Setup: officials
  function renameOfficial(oldN, newN) {
    Object.keys(A.ev.assignments).forEach(function (k) { if (A.ev.assignments[k].official === oldN) A.ev.assignments[k].official = newN; });
    if (A.ev._primary && A.ev._primary[oldN]) { A.ev._primary[newN] = A.ev._primary[oldN]; delete A.ev._primary[oldN]; }
  }
  function primaryOptions() {
    var main = [], short = [];
    E.positionsByPriority().forEach(function (k) {
      var p = ref.POSITION_INDEX[k];
      (p.kind === 'primary' ? main : short).push([k, p.title]);
    });
    return [['', 'Automatic'], { group: 'Main positions', options: main }, { group: 'Short jobs', options: short }];
  }
  SECTIONS.officials = function (root) {
    var offs = A.ev.officials;
    function setN(n) {
      n = Math.max(0, Math.min(200, n));
      edit(function () {
        while (offs.length < n) {
          var i = offs.length + 1, name = 'TO ' + (i < 10 ? '0' : '') + i, names = offs.map(function (o) { return o.name; });
          while (names.indexOf(name) >= 0) { i++; name = 'TO ' + (i < 10 ? '0' : '') + i; }
          offs.push(E.newOfficial(name));
        }
        while (offs.length > n) {
          var gone = offs.pop().name;
          Object.keys(A.ev.assignments).forEach(function (k) { if (A.ev.assignments[k].official === gone) delete A.ev.assignments[k]; });
        }
      });
    }
    root.appendChild(header('Officials', 'Your team of Technical Officials. A preferred position is honoured when possible; availability applies every event day.',
      [h('div', { class: 'stepper' }, btn('−', function () { setN(offs.length - 1); }, 'icon', null, 'One official fewer'),
        numIn('off-n', offs.length, function (v) { setN(Math.round(v)); }, { min: 0, max: 200, step: 1, inputmode: 'numeric', aria: 'Number of officials', cls: 'num-n' }),
        btn('+', function () { setN(offs.length + 1); }, 'icon', null, 'One official more')),
      btn('Paste names…', pasteNames)]));
    var popts = primaryOptions(), names = {};
    var list = h('div', { class: 'list officials-list' });
    list.appendChild(h('div', { class: 'list-head off-row' }, ['Name', 'Country', 'Preferred position', 'Max. short jobs / day', 'Available from', 'Available to', 'Radio', ''].map(function (t) { return h('span', { text: t }); })));
    offs.forEach(function (o, i) {
      var dup = names[o.name]; names[o.name] = 1;
      var resO = A.res.officials[i] || {};
      list.appendChild(h('div', { class: 'list-row off-row' + (dup ? ' dup' : '') },
        field('Name', input('o' + i + 'name', o.name, function (v) {
          v = v.trim(); if (!v) return toast('A name is needed');
          if (offs.some(function (x, j) { return j !== i && x.name === v; })) return toast('That name is already used');
          var old = o.name; edit(function () { o.name = v; renameOfficial(old, v); });
        }, { autocap: 'words' }), resO.primary ? '→ ' + resO.primary + (resO.secondary && resO.secondary.length ? ' + ' + resO.secondary.length + ' short' : '') : (o.name ? 'no job yet' : '')),
        field('Country', input('o' + i + 'cty', o.country, function (v) { edit(function () { o.country = v.toUpperCase(); }, { noPlan: true }); }, { placeholder: 'e.g. CRO', autocap: 'characters', cls: 'short' })),
        field('Preferred position', select('o' + i + 'pri', popts, o.primary || '', function (v) { edit(function () { o.primary = v; }); })),
        field('Max. short jobs / day', numIn('o' + i + 'max', o.max_secondary, function (v) { edit(function () { o.max_secondary = Math.max(0, Math.round(v)); }); }, { min: 0, max: 20, step: 1, inputmode: 'numeric', cls: 'short' })),
        field('Available from', input('o' + i + 'af', o.available_from, function (v) { edit(function () { o.available_from = v; }); }, { type: 'time' })),
        field('Available to', input('o' + i + 'at', o.available_to, function (v) { edit(function () { o.available_to = v; }); }, { type: 'time' })),
        h('div', { class: 'field' }, h('span', { class: 'flabel', text: 'Radio' }), check('o' + i + 'radio', o.radio !== false, function (v) { edit(function () { o.radio = v; }, { noPlan: true }); }, 'Radio')),
        h('div', { class: 'field end' }, btn('', function () {
          confirmBox('Remove official?', (o.name || 'This official') + ' and their assignments will be removed.', 'Remove', true).then(function (ok) {
            if (ok) edit(function () {
              Object.keys(A.ev.assignments).forEach(function (k) { if (A.ev.assignments[k].official === o.name) delete A.ev.assignments[k]; });
              offs.splice(i, 1);
            });
          });
        }, 'icon danger-text', 'trash', 'Remove official'))));
    });
    if (!offs.length) list.appendChild(empty('No officials yet. Use + or Paste names…'));
    root.appendChild(list);
  };
  function pasteNames() {
    var ta = h('textarea', { rows: 10, placeholder: 'One official per line.\nOptional country after a comma or tab, e.g.\nJane Doe, CRO' });
    var mode = { replace: true };
    var body = h('div', { class: 'stack' }, ta, check('paste-mode', true, function (v) { mode.replace = v; }, 'Replace the current names (keeps preferences in order)'));
    dialog('Paste names', body, [['Cancel', null, ''], ['Use names', function () { return ta.value; }, 'primary']]).then(function (text) {
      if (!text) return;
      var lines = text.split(/\r?\n/).map(function (l) { return l.trim(); }).filter(Boolean);
      edit(function () {
        var offs = A.ev.officials;
        lines.forEach(function (l, i) {
          var parts = l.split(/\t|;|,/), name = parts[0].trim(), cty = (parts[1] || '').trim().toUpperCase();
          if (mode.replace && i < offs.length) { var old = offs[i].name; offs[i].name = name; if (cty) offs[i].country = cty; renameOfficial(old, name); }
          else { var o = E.newOfficial(name); o.country = cty; offs.push(o); }
        });
      });
      toast(plural(lines.length, 'name') + ' added');
    });
  }

  // ============================================================ Setup: participation
  SECTIONS.participation = function (root) {
    var races = E.racesSorted(A.ev), offs = A.ev.officials;
    root.appendChild(header('Who works which race', 'Untick a race and that official is never planned for it. All-day jobs on a day (registration, wheel stations, transition, technology) need every race of that day ticked.'));
    function setAll(oList, rList, val) {
      edit(function () { oList.forEach(function (o) { rList.forEach(function (r) { if (val) delete o.races[r.id]; else o.races[r.id] = false; }); }); });
    }
    var thead = h('tr', null, h('th', { class: 'sticky', text: 'Official' }), races.map(function (r) {
      var n = offs.filter(function (o) { return E.takesPart(o, r.id); }).length;
      return h('th', null, h('div', { class: 'th-race' }, h('i', { class: 'swatch', style: 'background:' + X.raceColour(A.ev, r.id) }),
        h('span', { text: r.name }), h('span', { class: 'muted small', text: fmtT(A.res.timelines[r.id].start) + ' · ' + n + ' TOs' }),
        h('span', { class: 'row-btns' }, btn('All', function () { setAll(offs, [r], true); }, 'tiny'), btn('None', function () { setAll(offs, [r], false); }, 'tiny'))));
    }), h('th', { text: '' }));
    var tbody = h('tbody', null, offs.map(function (o, i) {
      return h('tr', null, h('th', { class: 'sticky', text: o.name }), races.map(function (r) {
        return h('td', { class: 'center' }, check('p' + i + r.id, E.takesPart(o, r.id), function (v) {
          edit(function () { if (v) delete o.races[r.id]; else o.races[r.id] = false; });
        }, null, { aria: o.name + ' works ' + r.name }));
      }), h('td', null, h('span', { class: 'row-btns' }, btn('All', function () { setAll([o], races, true); }, 'tiny'), btn('None', function () { setAll([o], races, false); }, 'tiny'))));
    }));
    root.appendChild(h('div', { class: 'table-wrap' }, h('table', { class: 'tbl part' }, h('thead', null, thead), tbody)));
  };

  // ============================================================ Setup: positions
  SECTIONS.positions = function (root) {
    root.appendChild(header('Positions', 'The proposed positions are ticked (TO Checklist 2025 and Competition Rules). Untick, add extras, or set your own number.',
      [btn('Reset to proposal', function () { edit(function () { E.resetPositions(A.ev); }); }, '')]));
    var firstRace = E.racesSorted(A.ev)[0], tl = firstRace ? A.res.timelines[firstRace.id] : null;
    ['primary', 'secondary'].forEach(function (kind) {
      var list = h('div', { class: 'list' });
      E.positionsByPriority().forEach(function (k) {
        var p = ref.POSITION_INDEX[k];
        if (p.kind !== kind) return;
        var cfg = A.ev.positions[k] || { enabled: p.proposed, count: null };
        var applies = A.ev.races.some(function (r) { return E.raceApplies(r, p.applies); });
        var prop = E.proposedCount(A.ev, p), n = E.positionCount(A.ev, k);
        var win = '';
        if (tl && firstRace && E.raceApplies(firstRace, p.applies)) {
          win = p.activities.map(function (a) { var w = E.activityWindow(a, tl, A.ev.settings, firstRace.shifts); return ref.ACTIVITIES[a][0] + ' ' + hm(w[0]) + '–' + hm(w[1]); }).join(' · ');
        }
        list.appendChild(h('div', { class: 'list-row pos-row' + (applies ? '' : ' na') },
          check('pos-' + k, cfg.enabled === undefined ? p.proposed : !!cfg.enabled, function (v) {
            edit(function () { A.ev.positions[k] = Object.assign({}, A.ev.positions[k] || {}, { enabled: v }); });
          }, null, { aria: 'Use ' + p.title }),
          h('div', { class: 'grow' }, h('strong', { text: p.title }), h('div', { class: 'muted small', text: p.toc + (applies ? '' : ' · not needed for these races') + (win ? ' · ' + firstRace.name + ': ' + win : '') })),
          field('Number', numIn('posn-' + k, cfg.count, function (v) {
            edit(function () { A.ev.positions[k] = Object.assign({}, A.ev.positions[k] || { enabled: true }, { count: v === null ? null : Math.max(0, Math.round(v)) }); });
          }, { allowEmpty: true, placeholder: String(prop), min: 0, step: 1, inputmode: 'numeric', cls: 'short' }), n ? n + ' in plan' : '—', 'narrow')));
      });
      root.appendChild(card(kind === 'primary' ? 'Main positions (one person all day)' : 'Short jobs (usually a second job for someone)', list));
    });
  };

  // ============================================================ Setup: duty times & tweaks
  SECTIONS.duties = function (root) {
    root.appendChild(header('Duty times & tweaks', 'Time allowances from the TO Checklist (pre-event, event and post-event duties). Change one and every plan uses it.',
      [btn('Reset all to defaults', function () { edit(function () { A.ev.settings = E.dutyDefaults(); A.ev.races.forEach(function (r) { r.shifts = {}; }); }); })]));
    var list = h('div', { class: 'list' });
    ref.DUTY_DEFAULTS.forEach(function (d) {
      var v = A.ev.settings[d[0]];
      list.appendChild(h('div', { class: 'list-row duty-row' + (v !== d[1] ? ' edited' : '') },
        h('div', { class: 'grow' }, h('strong', { text: d[2] }), h('div', { class: 'muted small', text: d[3] + (v !== d[1] ? ' · default ' + d[1] + ' min' : '') })),
        field('Minutes', numIn('duty-' + d[0], v, function (n) { edit(function () { A.ev.settings[d[0]] = n; }); }, { step: 1, cls: 'short' }), null, 'narrow')));
    });
    var races = E.racesSorted(A.ev);
    if (!A.shiftRace || !raceById(A.shiftRace)) A.shiftRace = races[0] ? races[0].id : '';
    var r = raceById(A.shiftRace), tw = h('div', { class: 'stack' });
    if (r) {
      var tl = A.res.timelines[r.id], used = [];
      E.positionsByPriority().forEach(function (k) {
        var p = ref.POSITION_INDEX[k];
        if (E.positionCount(A.ev, k) && E.raceApplies(r, p.applies)) p.activities.forEach(function (a) { if (used.indexOf(a) < 0) used.push(a); });
      });
      tw.appendChild(h('div', { class: 'inline' }, field('Race', select('shift-race', races.map(function (x) { return [x.id, x.name + ' · ' + fmtT(A.res.timelines[x.id].start)]; }), r.id, function (v) { A.shiftRace = v; render(); })),
        btn('Reset this race', function () { edit(function () { r.shifts = {}; }); }, 'small')));
      var l2 = h('div', { class: 'list' });
      used.forEach(function (a) {
        var sh = (r.shifts || {})[a] || [0, 0], w = E.activityWindow(a, tl, A.ev.settings, r.shifts);
        function setS(i) { return function (n) { edit(function () { var s = (r.shifts[a] || [0, 0]).slice(); s[i] = n; if (!s[0] && !s[1]) delete r.shifts[a]; else r.shifts[a] = s; }); }; }
        l2.appendChild(h('div', { class: 'list-row duty-row' + (sh[0] || sh[1] ? ' edited' : '') },
          h('div', { class: 'grow' }, h('strong', { text: ref.ACTIVITIES[a][0] }), h('div', { class: 'muted small', text: hm(w[0]) + '–' + hm(w[1]) + ' · ' + ref.ACTIVITIES[a][7] })),
          field('Start ±min', numIn('sh-' + r.id + a + '0', sh[0], setS(0), { step: 5, cls: 'short' }), null, 'narrow'),
          field('End ±min', numIn('sh-' + r.id + a + '1', sh[1], setS(1), { step: 5, cls: 'short' }), null, 'narrow')));
      });
      tw.appendChild(l2);
    }
    root.appendChild(h('div', { class: 'grid-2' }, card('Time allowances (all races)', list), card('Move a duty window in one race', tw)));
  };

  // ============================================================ Setup: meetings & briefings
  SECTIONS.meetings = function (root) {
    root.appendChild(header('Meetings & briefings', 'Obligations outside the races, from the rules: Elite athletes’ briefing at 16:00 the day before the first competition day (CR 2.7 b), Jury meetings (CR 12.9), rehearsals and race-week meetings (EOM Table 14, 6.9, 6.11.4), familiarisation (EOM 3.2.8) and daily TO briefings (EOM 2.13 e). Everyone who must attend is booked, so nobody gets a clashing job.',
      [btn('Add meeting', addMeetingDialog, 'primary', 'plus'), btn('Reset all to rules', function () { edit(function () { A.ev.sessions = {}; }); })]));
    A.res.warnings.forEach(function (w) { root.appendChild(note('⚠ ' + w, 'warn')); });
    var list = h('div', { class: 'list' }), lastDay = '';
    E._h.sortBy(A.res.sessions, function (x) { return [x.s, x.e]; }).forEach(function (se) {
      if (se.date !== lastDay) { lastDay = se.date; list.appendChild(h('div', { class: 'list-day', text: longDate(se.date) })); }
      var custom = !!se.custom, k = 'se-' + se.id;
      function setOv(field_, val) {
        edit(function () {
          if (custom) { var c = A.ev.custom_sessions.filter(function (x) { return x.id === se.id; })[0]; if (c) c[field_] = val; }
          else { var o = A.ev.sessions[se.id] = A.ev.sessions[se.id] || {}; o[field_] = val; }
        });
      }
      list.appendChild(h('div', { class: 'list-row meet-row' + (se.enabled ? '' : ' off') + (se.edited || custom ? ' edited' : '') + (se.key === 'athletes_briefing' ? ' key' : '') },
        check(k + 'on', se.enabled, function (v) { setOv('enabled', v); }, null, { aria: 'Held: ' + se.name }),
        h('div', { class: 'grow' },
          custom ? input(k + 'name', se.name, function (v) { setOv('name', v || 'Meeting'); }) : h('strong', { text: se.name + (se.edited ? ' (edited)' : '') }),
          h('div', { class: 'muted small', text: 'Who: ' + E.attendeeLabel(se.attendees) }),
          h('div', { class: 'small', text: (se.people || []).join(', ') || '—' }),
          h('div', { class: 'muted small', text: se.ref })),
        h('div', { class: 'meet-times' },
          field('Date', input(k + 'date', se.date, function (v) { if (E.parseDate(v)) setOv('date', v); }, { type: 'date' })),
          field('From', input(k + 'from', E.fmtHHMM(se.start), function (v) { if (E.parseHHMM(v) !== null) setOv('start', E.fmtHHMM(E.parseHHMM(v))); }, { type: 'time' })),
          field('To', input(k + 'to', E.fmtHHMM(se.end), function (v) { if (E.parseHHMM(v) !== null) setOv('end', E.fmtHHMM(E.parseHHMM(v))); }, { type: 'time' })),
          custom ? field('Who must attend', select(k + 'who', [['', 'Change…']].concat(Object.keys(ref.SESSION_PRESETS).map(function (p) { return [p, p]; })), '', function (v) {
            if (v) setOv('attendees', ref.SESSION_PRESETS[v].slice());
          })) : null),
        h('div', { class: 'row-btns' },
          !custom && se.edited ? btn('Reset', function () { edit(function () { delete A.ev.sessions[se.id]; }); }, 'small') : null,
          custom ? btn('', function () { edit(function () { A.ev.custom_sessions = A.ev.custom_sessions.filter(function (x) { return x.id !== se.id; }); }); }, 'icon danger-text', 'trash', 'Remove meeting') : null)));
    });
    root.appendChild(list);
  };
  function addMeetingDialog() {
    var days = A.res.dates, f = { name: 'Meeting', date: days[0], start: '19:00', end: '20:00', who: 'All TOs + TD' };
    var body = h('div', { class: 'form-grid' },
      field('Name', input('am-name', f.name, function (v) { f.name = v; }), null, 'span2'),
      field('Date', input('am-date', f.date, function (v) { f.date = v; }, { type: 'date' })),
      field('Who must attend', select('am-who', Object.keys(ref.SESSION_PRESETS).map(function (p) { return [p, p]; }), f.who, function (v) { f.who = v; })),
      field('From', input('am-from', f.start, function (v) { f.start = v; }, { type: 'time' })),
      field('To', input('am-to', f.end, function (v) { f.end = v; }, { type: 'time' })));
    body.querySelectorAll('input,select').forEach(function (el) { el.addEventListener('input', function () { el.dispatchEvent(new Event('change')); }); });
    dialog('Add meeting', body, [['Cancel', null, ''], ['Add', true, 'primary']]).then(function (ok) {
      if (!ok) return;
      if (!E.parseDate(f.date) || E.parseHHMM(f.start) === null || E.parseHHMM(f.end) === null) return toast('Check the date and times');
      edit(function () {
        A.ev.custom_sessions.push({ id: E.newId('s'), name: f.name || 'Meeting', date: f.date, start: f.start, end: f.end,
          attendees: ref.SESSION_PRESETS[f.who].slice(), enabled: true });
      });
    });
  }

  // ============================================================ Plan: assignments
  SECTIONS.assignments = function (root) {
    var r = A.res, ev = A.ev, names = ev.officials.map(function (o) { return o.name; }).filter(Boolean);
    root.appendChild(header('Assignments', 'Choose a person in any row to fix it (locked rows are kept when the planner runs again). Status: OK, TIGHT (hand-over shorter than the buffer), CONFLICT, UNFILLED.',
      [btn('Auto-assign', function () { edit(function () { E.autoAssign(ev, true); }, { noPlan: true }); toast('Planned – locked rows kept'); }, 'primary'),
        btn('Re-plan from scratch', function () {
          confirmBox('Re-plan from scratch?', 'All assignments, including locked rows, are planned again.', 'Re-plan', true).then(function (ok) {
            if (ok) edit(function () { ev.assignments = {}; delete ev._primary; E.autoAssign(ev, false); }, { noPlan: true });
          });
        }),
        btn('Lock all', function () { edit(function () { E.lockAll(ev, true); }, { noPlan: true }); }, '', 'lock'),
        btn('Unlock all', function () { edit(function () { E.lockAll(ev, false); }); }, '', 'unlock'),
        btn('Swap two officials…', swapDialog)]));
    root.appendChild(h('div', { class: 'stats' },
      stat(r.rows.length, 'jobs'), stat(r.rows.filter(function (x) { return x.official; }).length, 'covered'),
      stat(r.unfilled.length, 'unfilled', r.unfilled.length ? 'unf' : ''), stat(r.n_conflict, 'conflicts', r.n_conflict ? 'bad' : ''),
      stat(r.n_tight, 'tight', r.n_tight ? 'tight' : ''), stat(r.radios.total, 'radios')));
    var raceOpts = [['', 'All races']].concat(E.racesSorted(ev).map(function (x) { return [x.id, x.name]; }));
    if (r.multiday) r.dates.forEach(function (d) { if (E.raceDates(ev).indexOf(d) >= 0) raceOpts.push(['day:' + d, 'All-day jobs ' + E.dayLabel(d)]); });
    root.appendChild(h('div', { class: 'filters' },
      field('Race', select('f-race', raceOpts, A.filt.race, function (v) { A.filt.race = v; render(); })),
      field('Search', input('f-q', A.filt.q, function (v) { A.filt.q = v; render(); }, { type: 'search', placeholder: 'Name or position' })),
      h('div', { class: 'field' }, h('span', { class: 'flabel', text: 'Show' }), check('f-prob', A.filt.problems, function (v) { A.filt.problems = v; render(); }, 'Problems only'))));
    var q = (A.filt.q || '').toLowerCase();
    var rows = r.rows.filter(function (x) {
      if (A.filt.race) {
        if (A.filt.race.indexOf('day:') === 0 ? x.race_id !== A.filt.race : !(x.race_id === A.filt.race || x.races_of.indexOf(A.filt.race) >= 0)) return false;
      }
      if (A.filt.problems && x.status === 'OK') return false;
      if (q && (x.title + ' ' + x.official + ' ' + x.race).toLowerCase().indexOf(q) < 0) return false;
      return true;
    });
    var list = h('div', { class: 'list asg-list' });
    list.appendChild(h('div', { class: 'list-head asg-row' }, ['Position', 'Race', 'Time', 'Official', '', 'Status'].map(function (t) { return h('span', { text: t }); })));
    var lastSlot = '';
    rows.forEach(function (x) {
      var opts = [['__auto', 'Automatic (planner decides)'], ['__loc', 'LOC / volunteer – no TO']];
      if (!x.official) opts.unshift(['__none', '— unfilled —', true]);
      var avail = names.map(function (n) {
        var o = ev.officials.filter(function (z) { return z.name === n; })[0];
        var works = x.races_of.every(function (rid) { return E.takesPart(o, rid); });
        return [n, n + (works ? '' : ' (not working this race)')];
      });
      var val = x.official ? x.official : (x.locked ? '__loc' : '__none');
      var sel = select('a-' + x.key, opts.concat([{ group: 'Officials', options: avail }]), val, function (v) {
        if (v === '__none') return;
        edit(function () {
          if (v === '__auto') delete ev.assignments[x.key];
          else if (v === '__loc') E.setAssignment(ev, x.key, '', true);
          else E.setAssignment(ev, x.key, v, true);
        });
      }, { aria: 'Official for ' + x.title + ', ' + x.race });
      var lockBtn = btn('', function () {
        edit(function () {
          if (x.locked) { if (ev.assignments[x.key]) ev.assignments[x.key].locked = false; if (!x.official) delete ev.assignments[x.key]; }
          else E.setAssignment(ev, x.key, x.official, true);
        });
      }, 'icon lock' + (x.locked ? ' on' : ''), x.locked ? 'lock' : 'unlock', x.locked ? 'Locked – tap to let the planner change it' : 'Lock this row');
      var newSlot = x.slot !== lastSlot; lastSlot = x.slot;
      list.appendChild(h('div', { class: 'list-row asg-row st-' + x.status.replace(/[^A-Z]/g, '') + (newSlot ? ' first' : '') },
        h('div', { class: 'asg-pos' }, h('strong', { text: x.title }), h('span', { class: 'muted small', text: x.toc + (x.role ? ' · ' + x.role : '') })),
        h('div', { class: 'asg-race' }, h('i', { class: 'swatch', style: 'background:' + X.raceColour(ev, x.race_id) }), h('span', { text: x.race })),
        h('div', { class: 'asg-time', text: x.start === null ? '' : fmtT(x.start) + '–' + hm(x.end) }),
        h('div', { class: 'asg-who' }, sel), lockBtn, h('div', { class: 'asg-st' }, chip(x.status))));
    });
    if (!rows.length) list.appendChild(empty('No rows match the filter.'));
    root.appendChild(list);
  };
  function stat(n, label, cls) { return h('div', { class: 'stat ' + (cls || '') }, h('strong', { text: String(n) }), h('span', { text: label })); }
  function swapDialog() {
    var names = A.ev.officials.map(function (o) { return o.name; }).filter(Boolean);
    if (names.length < 2) return toast('Add officials first');
    var f = { a: names[0], b: names[1] }, opts = names.map(function (n) { return [n, n]; });
    var body = h('div', { class: 'form-grid' },
      field('Official A', select('sw-a', opts, f.a, function (v) { f.a = v; })),
      field('Official B', select('sw-b', opts, f.b, function (v) { f.b = v; })),
      note('All jobs of A go to B and the other way round. The swapped rows are locked.', 'span2'));
    dialog('Swap two officials', body, [['Cancel', null, ''], ['Swap', true, 'primary']]).then(function (ok) {
      if (!ok || f.a === f.b) return;
      edit(function () {
        var asg = A.ev.assignments;
        Object.keys(asg).forEach(function (k) {
          if (asg[k].official === f.a) asg[k] = { official: f.b, locked: true };
          else if (asg[k].official === f.b) asg[k] = { official: f.a, locked: true };
        });
        var oa = A.ev.officials.filter(function (o) { return o.name === f.a; })[0], ob = A.ev.officials.filter(function (o) { return o.name === f.b; })[0];
        var t = oa.primary; oa.primary = ob.primary; ob.primary = t;
        if (A.ev._primary) { var pa = A.ev._primary[f.a]; A.ev._primary[f.a] = A.ev._primary[f.b]; A.ev._primary[f.b] = pa; }
      });
      toast('Swapped ' + f.a + ' and ' + f.b);
    });
  }

  // ============================================================ Plan: conflicts
  SECTIONS.conflicts = function (root) {
    var r = A.res;
    root.appendChild(header('Conflicts', 'Clashes, tight hand-overs, jobs without a TO and rule warnings. Meetings and briefings count as busy time.'));
    var list = h('div', { class: 'list' });
    r.warnings.forEach(function (w) { list.appendChild(h('div', { class: 'list-row conf-row' }, chip('WARNING'), h('div', { class: 'grow', text: w }))); });
    r.conflicts.forEach(function (c) {
      list.appendChild(h('div', { class: 'list-row conf-row' }, chip(c.level),
        h('div', { class: 'grow' }, h('strong', { text: c.official }),
          h('div', { text: c.a + (c.a_label && c.a_label !== c.a ? ' (' + c.a_label + ')' : '') + ' · ' + c.a_time }),
          c.b ? h('div', { text: c.b + (c.b_label && c.b_label !== c.b ? ' (' + c.b_label + ')' : '') + (c.b_time ? ' · ' + c.b_time : '') }) : null,
          c.gap !== null ? h('div', { class: 'muted small', text: c.gap < 0 ? 'Overlap ' + (-c.gap) + ' min' : 'Gap ' + c.gap + ' min (buffer ' + A.ev.settings.buffer + ')' }) : null)));
    });
    r.unfilled.forEach(function (u) {
      list.appendChild(h('div', { class: 'list-row conf-row' }, chip('UNFILLED'),
        h('div', { class: 'grow' }, h('strong', { text: u.title }), h('div', { text: u.race + ' · ' + fmtT(u.start) + '–' + hm(u.end) })),
        btn('Assign…', function () { A.filt = { race: '', q: u.title, problems: false }; go('assignments'); }, 'small')));
    });
    if (!list.children.length) list.appendChild(h('div', { class: 'empty ok', text: 'No conflicts and nothing unfilled.' }));
    root.appendChild(list);
    if (r.unfilled.length) root.appendChild(note('To cover open jobs: add an official, allow more short jobs per day, accept a LOC volunteer, or move a duty window on the Duty times page.'));
  };

  // ============================================================ Views: schedules
  SECTIONS.schedules = function (root) {
    var r = A.res, people = r.officials.concat(X.wtPeople(r));
    root.appendChild(header('Personal schedules', 'Every official’s days, job by job and meeting by meeting.',
      [field('Show', select('sch-who', [['', 'Everyone']].concat(people.map(function (o) { return [o.name, o.name]; })), A.sched, function (v) { A.sched = v; render(); }))]));
    var wrap = h('div', { class: 'cards sched' });
    people.filter(function (o) { return !A.sched || o.name === A.sched; }).forEach(function (o) {
      var lastDay = '', items = h('div', { class: 'tl' });
      o.duties.forEach(function (d) {
        var day = d.date || '';
        if (r.multiday && day !== lastDay) { lastDay = day; items.appendChild(h('div', { class: 'list-day', text: longDate(day) })); }
        items.appendChild(h('div', { class: 'tl-item st-' + String(d.status).replace(/[^A-Z]/g, '') + (d.kind === 'session' ? ' meet' : '') },
          h('span', { class: 'tl-time', text: hm(d.start) + '–' + hm(d.end) }),
          h('i', { class: 'swatch', style: 'background:' + X.raceColour(A.ev, d.race_id) }),
          h('div', { class: 'grow' }, h('strong', { text: d.title }), h('div', { class: 'muted small', text: d.race + ' · ' + d.role })),
          d.status && d.status !== 'OK' ? chip(d.status) : null));
      });
      if (!o.duties.length) items.appendChild(empty('No jobs.'));
      wrap.appendChild(card(o.name, items, h('span', { class: 'muted small', text: o.primary ? o.primary + (o.secondary && o.secondary.length ? ' + ' + o.secondary.join(', ') : '') : (o.role || '') })));
    });
    root.appendChild(wrap);
  };

  // ============================================================ Views: Gantt
  SECTIONS.gantt = function (root) {
    var r = A.res, days = r.dates;
    if (days.indexOf(A.gantt.day) < 0) { var rd = E.raceDates(A.ev); A.gantt.day = rd[0] || days[0]; }
    root.appendChild(header('Gantt', 'One event day at a time. Solid = main job, light = short job, purple = meetings. Scroll sideways; tap a bar for details.',
      [btn('Export SVG', function () { exportSvg(); }, '')]));
    root.appendChild(h('div', { class: 'filters' },
      field('Day', select('g-day', days.map(function (d) { return [d, longDate(d)]; }), A.gantt.day, function (v) { A.gantt.day = v; render(); })),
      field('Rows', select('g-mode', [['officials', 'By official'], ['positions', 'By position']], A.gantt.mode, function (v) { A.gantt.mode = v; render(); })),
      field('Zoom', select('g-zoom', [[1.5, 'Whole day'], [2, 'Small'], [3, 'Medium'], [4, 'Large'], [6, 'Extra large']], A.gantt.zoom, function (v) { A.gantt.zoom = +v; render(); })),
      h('div', { class: 'field' }, h('span', { class: 'flabel', text: 'Colours' }), check('g-dark', A.gantt.dark, function (v) { A.gantt.dark = v; render(); }, 'Dark'))));
    var svg = X.ganttSvg(A.ev, r, { day: A.gantt.day, mode: A.gantt.mode, pxPerMin: A.gantt.zoom, dark: A.gantt.dark });
    var box = h('div', { class: 'gantt-wrap' }); box.innerHTML = svg;
    box.addEventListener('click', function (e) {
      var t = e.target.closest && e.target.closest('rect'); var ttl = t && t.querySelector('title');
      if (ttl) toast(ttl.textContent, 4000);
    });
    root.appendChild(box);
  };
  function exportSvg() {
    var svg = X.ganttSvg(A.ev, A.res, { day: A.gantt.day, mode: A.gantt.mode, pxPerMin: 4, dark: A.gantt.dark });
    Store.exportFile(fileBase() + '-gantt-' + (A.gantt.day || 'day') + '.svg', 'image/svg+xml', svg).then(exported);
  }

  // ============================================================ Views: timeline
  SECTIONS.timeline = function (root) {
    var r = A.res, sheet = E.runSheet(A.ev, r);
    root.appendChild(header('Timeline', 'All race milestones and meetings in time order, and the splits of each race.'));
    var list = h('div', { class: 'list' }), lastDay = '';
    sheet.forEach(function (m) {
      var day = E.dateAt(A.ev, m.time);
      if (day !== lastDay) { lastDay = day; list.appendChild(h('div', { class: 'list-day', text: longDate(day) })); }
      list.appendChild(h('div', { class: 'list-row tl-row' + (m.key === 'start' ? ' key' : '') },
        h('span', { class: 'tl-time', text: hm(m.time) }), h('i', { class: 'swatch', style: 'background:' + X.raceColour(A.ev, m.race_id) }),
        h('div', { class: 'grow' }, h('strong', { text: m.item }), h('div', { class: 'muted small', text: m.race }))));
    });
    var splits = h('div', { class: 'table-wrap' }, h('table', { class: 'tbl' },
      h('thead', null, h('tr', null, ['Race', 'Start', 'Swim', 'T1', 'Bike', 'T2', 'Run', 'Winner', 'Last finisher'].map(function (t) { return h('th', { text: t }); }))),
      h('tbody', null, E.racesSorted(A.ev).map(function (rc) {
        var tl = r.timelines[rc.id], sg = tl._segments;
        return h('tr', null, h('td', null, h('i', { class: 'swatch', style: 'background:' + X.raceColour(A.ev, rc.id) }), ' ' + rc.name), h('td', { text: fmtT(tl.start) }),
          [sg.swim, sg.t1, sg.bike, sg.t2, sg.run].map(function (v) { return h('td', { class: 'num', text: E.fmtDur(v) }); }),
          h('td', { text: hm(tl.winner) }), h('td', { text: hm(tl.last_finisher) }));
      }))));
    root.appendChild(h('div', { class: 'grid-2 wide-left' }, card('Run sheet', list), card('Splits (leader)', splits)));
  };

  // ============================================================ Athletes: guide
  SECTIONS.athletes = function (root) {
    var Ath = W.Athletes, races = E.racesSorted(A.ev);
    if (A.athRace && !raceById(A.athRace)) A.athRace = '';
    var info = Ath.info(A.ev);
    function setInfo(k) {
      return function (v) { edit(function () { A.ev.event.athletes = Object.assign(Ath.info(A.ev), A.ev.event.athletes || {}); A.ev.event.athletes[k] = v; }, { noPlan: true }); };
    }
    root.appendChild(header('Athletes’ guide', 'Only what athletes need: briefing, familiarisation and race-day times, the course and the key rules – no officials’ meetings or jobs. Share it as a page athletes can open on any phone, or as a calendar.',
      [btn('Share guide', function () {
        Store.exportFile(fileBase() + '-athletes-guide.html', 'text/html', Ath.html(A.ev, A.res, A.athRace)).then(exported);
      }, 'primary'),
      btn('Athletes’ calendar (.ics)', function () {
        Store.exportFile(fileBase() + '-athletes.ics', 'text/calendar', Ath.ics(A.ev, A.res, A.athRace)).then(exported);
      })]));
    root.appendChild(h('div', { class: 'filters' },
      field('Race', select('ath-race', [['', 'All races']].concat(races.map(function (r) { return [r.id, r.name + ' · ' + fmtT(A.res.timelines[r.id].start)]; })),
        A.athRace || '', function (v) { A.athRace = v; render(); }))));
    // schedule
    var list = h('div', { class: 'list' }), day = '';
    Ath.items(A.ev, A.res, A.athRace).forEach(function (it) {
      if (it.date !== day) { day = it.date; list.appendChild(h('div', { class: 'list-day', text: longDate(day) })); }
      list.appendChild(h('div', { class: 'list-row tl-row ath-row' + (it.kind === 'start' || it.kind === 'athletes_briefing' ? ' key' : '') },
        h('span', { class: 'tl-time ath-time', text: (it.approx ? '≈ ' : '') + hm(it.s) + (it.e ? '–' + hm(it.e) : '') }),
        h('i', { class: 'swatch', style: 'background:' + X.raceColour(A.ev, it.race_id) }),
        h('div', { class: 'grow' }, h('strong', { text: it.title }), it.text ? h('div', { class: 'muted small', text: it.text }) : null)));
    });
    if (!list.children.length) list.appendChild(empty('No athlete events for this selection.'));
    // course
    var courses = h('div', { class: 'stack' }, (A.athRace ? races.filter(function (r) { return r.id === A.athRace; }) : races).map(function (r) {
      return h('div', null, h('div', { class: 'race-line' }, h('i', { class: 'swatch', style: 'background:' + X.raceColour(A.ev, r.id) }),
        h('strong', { text: r.name + ' · start ' + fmtT(A.res.timelines[r.id].start) })),
      h('table', { class: 'tbl compact' }, h('tbody', null, Ath.course(A.ev, r).map(function (c) {
        return h('tr', null, h('td', { class: 'muted', text: c[0] }), h('td', { text: c[1] }));
      }))));
    }));
    var rules = h('ul', { class: 'bullets' }, Ath.rules(A.ev, A.athRace).map(function (x) { return h('li', { text: x }); }));
    var infoCard = card('Information for athletes', h('div', { class: 'form-grid' },
      field('Briefing location', input('ath-brief', info.briefing_location, setInfo('briefing_location'), { placeholder: 'e.g. Hotel ballroom, 1st floor' })),
      field('Race office / packet pick-up', input('ath-office', info.office, setInfo('office'), { placeholder: 'e.g. Race office at the expo, 09:00–18:00' })),
      field('Notes for athletes', h('textarea', { 'data-k': 'ath-notes', rows: 4, placeholder: 'Parking, shuttle, bag drop, contact…',
        on: { change: function (ev) { setInfo('notes')(ev.target.value); } } }, info.notes), 'Shown at the top of the shared guide', 'span2')));
    root.appendChild(h('div', { class: 'grid-2 wide-left' },
      h('div', { class: 'stack' }, card('Schedule', list), infoCard),
      h('div', { class: 'stack' }, card('Course', courses), card('Key rules', rules),
        note('Times marked ≈ are estimates from typical race times. The athletes’ briefing and official race information prevail.', 'small'))));
  };

  // ============================================================ More: export
  function fileBase() {
    return (A.ev.event.name || 'event').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '-').slice(0, 60) || 'event';
  }
  function exported(how) {
    toast({ downloaded: 'Downloaded', cancelled: 'Cancelled', saved: 'Saved', shared: 'Shared', failed: 'Could not export' }[how] || 'Done');
  }
  SECTIONS.export = function (root) {
    root.appendChild(header('Export & share', Store.native ? 'Each export opens the share sheet: save to Files, AirDrop, mail or open it in another app.' :
      'Each export downloads a file.'));
    function item(title, desc, onClick, label) {
      return h('div', { class: 'list-row exp-row' }, h('div', { class: 'grow' }, h('strong', { text: title }), h('div', { class: 'muted small', text: desc })), btn(label || 'Export', onClick, 'primary'));
    }
    var list = h('div', { class: 'list' },
      item('Excel workbook (.xlsx)', 'Assignments, officials & radios, participation, personal schedules, timeline, meetings, a colour Gantt per day, conflicts, settings.',
        function () { Store.exportFile(fileBase() + '.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', X.xlsx(A.ev, A.res)).then(exported); }),
      item('LibreOffice / Numbers (.ods)', 'The same sheets in OpenDocument format.',
        function () { Store.exportFile(fileBase() + '.ods', 'application/vnd.oasis.opendocument.spreadsheet', X.ods(A.ev, A.res)).then(exported); }),
      item('Athletes’ guide (.html)', 'Schedule, course and key rules for athletes only – opens on any phone or computer and prints well.',
        function () { Store.exportFile(fileBase() + '-athletes-guide.html', 'text/html', W.Athletes.html(A.ev, A.res, '')).then(exported); }),
      item('Calendar (.ics)', 'Races, every meeting and briefing, and each official’s duties – for Apple Calendar, Google Calendar or Outlook.',
        function () { Store.exportFile(fileBase() + '.ics', 'text/calendar', X.ics(A.ev, A.res)).then(exported); }),
      item('Gantt picture (.svg)', 'The Gantt of the day chosen on the Gantt page (' + longDate(A.gantt.day || E.raceDates(A.ev)[0]) + ').', exportSvg),
      item('Plan file (.wtplan.json)', 'The whole event. Opens in this app on iPhone, iPad and Mac, and in the Ubuntu desktop version.',
        function () { Store.exportFile(fileBase() + '.wtplan.json', 'application/json', X.toJSON(A.ev)).then(exported); }),
      item('Copy plan as text', 'Puts the plan file (JSON) on the clipboard.', function () { Store.copyText(X.toJSON(A.ev)).then(function () { toast('Copied'); }); }, 'Copy'),
      item('Open a plan file', 'Import a .wtplan.json file (from this app, a colleague or the Ubuntu version).', importFile, 'Open…'));
    root.appendChild(list);
  };

  // ============================================================ More: references & about
  var OBLIGATIONS = [
    ['Day before, 08:30–09:15', 'Motorbike & boat drivers’ briefing', 'TD, Chief Bike, Chief Vehicular, TO motorbikes, Chief Swim', 'EOM 6.9, Table 14'],
    ['Day before, 09:30–10:00', 'Medical meeting', 'TD, Medical Delegate', 'EOM Table 14'],
    ['Day before, 10:00–11:00', 'Swim familiarisation', 'Chief Swim, Assistant Swim', 'EOM 3.2.8'],
    ['Day before, 11:15–12:00', 'Start rehearsal', 'TD, Head Referee, CRO, Chief Swim, start crew', 'EOM 6.11.4, Table 14'],
    ['Day before, 11:15–12:45', 'Bike familiarisation (mandatory)', 'Chief Bike, Chief Vehicular, TO motorbikes', 'EOM 3.2.8'],
    ['Day before, 12:45–13:15', 'Finish rehearsal', 'TD, Chief Finish, Assistant Finish, Chief Technology', 'EOM Table 14'],
    ['Day before, 13:15 / 13:45', 'Timing meeting, TV meeting', 'TD with Chief Technology / Video Review', 'EOM Table 14'],
    ['Day before, 14:00–15:00', 'TOs’ meeting', 'TD and all TOs', 'EOM Table 14, 2.13'],
    ['Day before, 15:00 (off by default)', 'Coaches’ meeting', 'TD', 'CR 2.7 b(i): 1 h before the briefing, if scheduled'],
    ['Day before, 15:30–17:30', 'Briefing check-in and race packets', 'Registration', 'CR 2.7 b(vi), c(ii)'],
    ['Day before, 16:00–17:00', 'Elite athletes’ briefing', 'TD, Head Referee', 'CR 2.7 b(iv), (vii)'],
    ['After the briefing', 'Competition Jury meeting', 'TD, Jury', 'CR 12.9'],
    ['Each competition day', 'TO briefing 75 min before the first lounge; de-briefing 45 min after the last finisher', 'All TOs', 'EOM 2.13 e'],
    ['Each race', 'Jury meeting 1 h before the start, and after the last finisher once the protest time is over', 'TD, Jury', 'CR 12.9, 12.4']
  ];
  SECTIONS.references = function (root) {
    root.appendChild(header('Rules & references', 'Where every default comes from. All times can be changed in the app.'));
    var tbl = h('div', { class: 'table-wrap' }, h('table', { class: 'tbl' },
      h('thead', null, h('tr', null, ['When', 'Meeting', 'Who must attend', 'Source'].map(function (t) { return h('th', { text: t }); }))),
      h('tbody', null, OBLIGATIONS.map(function (o) { return h('tr', { class: /briefing’?$/.test(o[1]) && o[1].indexOf('Elite') === 0 ? 'strong' : '' }, o.map(function (c) { return h('td', { text: c }); })); }))));
    var rules = h('ul', { class: 'bullets' },
      h('li', { text: 'Head Referee: on duty until the protest time is over – last finisher + results sign-off + 5 + 15 min (Elite standard and shorter) or 15 + 30 min (middle/long distance and Age-Group), CR 12.4. In back-to-back racing the CRO usually starts the next race.' }),
      h('li', { text: 'Time between Elite starts on one day: sprint 2 h, standard 3 h, mixed relay 2 h 30, or 15 min less with TD approval (EOM 2.10.2 Table 3).' }),
      h('li', { text: 'U23, Junior, Para and Mixed-relay briefings are held the day before their own race; a Mixed relay on the same day as the Elite races shares their briefing (CR 2.7 b(v), (viii)).' }),
      h('li', { text: 'Duty windows per position follow the World Triathlon TO Checklist 2025 (pre-event, event, post-event duties).' }));
    root.appendChild(h('div', { class: 'stack' }, card('Obligations of the appointed officials', tbl), card('Other rules used', rules),
      card('Sources', h('pre', { class: 'refs', text: ref.REFERENCES }))));
  };
  SECTIONS.about = function (root) {
    root.appendChild(header(ref.APP_NAME, 'Version ' + ref.APP_VERSION));
    root.appendChild(h('div', { class: 'grid-2' },
      card('What it does', h('div', { class: 'stack' },
        h('p', { text: 'Plans Technical Official positions for triathlon events run under the World Triathlon Competition Rules: one main position per official, short jobs as second positions without time clashes, meetings and briefings from the rules, and exports to Excel, LibreOffice, calendars and pictures.' }),
        h('p', { class: 'muted', text: 'Independent tool. Not affiliated with, endorsed by or sponsored by World Triathlon. Always check the plan against the current rules and your Technical Delegate.' }))),
      card('Privacy', h('div', { class: 'stack' },
        h('p', { text: 'Your events stay on your device. The app has no account, no analytics, no advertising and makes no network requests.' }),
        h('p', { text: Store.native ? 'Events are saved as files in the app’s folder (Files app → On My iPhone/iPad → TO Scheduler, or the app container on Mac). Deleting the app deletes them – export the ones you want to keep.' :
          'In a browser, events are kept in this browser’s storage on this device only.' }),
        h('p', { class: 'muted', text: 'Anything you export or share leaves the app only where you send it.' }))),
      card('Keyboard', h('ul', { class: 'bullets' },
        h('li', { text: Store.platform === 'macos' ? '⌥⌘Z – undo a plan change, ⌥⇧⌘Z – redo, ⌘R – auto-assign' : '⌘Z / Ctrl+Z – undo, ⇧⌘Z / Ctrl+Shift+Z – redo' }),
        h('li', { text: '⌘N – new event, ⌘O – open a plan file' + (Store.platform === 'macos' ? ', ⌘E – export' : '') }))),
      card('Open source', h('p', null, 'MIT licence. Source and the Ubuntu desktop version: ',
        h('a', { href: 'https://github.com/bojansurbatovic-web/technical-officials-scheduler', on: { click: function (e) { e.preventDefault(); Store.openLink(e.currentTarget.href); } } }, 'github.com/bojansurbatovic-web/technical-officials-scheduler')))));
  };

  // ============================================================ commands, keys, start-up
  A.command = function (name) {
    if (name === 'new') newEventDialog(A.selDay || E.todayIso());
    else if (name === 'open') importFile();
    else if (name === 'export') go('export');
    else if (name === 'undo') undo();
    else if (name === 'redo') redo();
    else if (name === 'replan' && A.ev) edit(function () { E.autoAssign(A.ev, true); }, { noPlan: true });
  };
  function onKey(e) {
    var mod = e.metaKey || e.ctrlKey, tag = (e.target.tagName || '').toLowerCase();
    if (!mod) return;
    var k = e.key.toLowerCase();
    if (k === 'z' && tag !== 'input' && tag !== 'textarea') { e.preventDefault(); if (e.shiftKey) redo(); else undo(); }
    else if (k === 'y' && tag !== 'input') { e.preventDefault(); redo(); }
    else if (k === 'n' && !Store.native) { e.preventDefault(); A.command('new'); }
    else if (k === 'o' && !Store.native) { e.preventDefault(); A.command('open'); }
  }
  A.start = function () {
    document.getElementById('btn-undo').addEventListener('click', undo);
    document.getElementById('btn-redo').addEventListener('click', redo);
    document.getElementById('auto-toggle').addEventListener('change', function (e) {
      A.auto = e.target.checked; Store.setPref('auto', A.auto ? '1' : '0');
      if (A.auto && A.ev) edit(function () { E.autoAssign(A.ev, true); }, { noPlan: true }); else render();
      toast(A.auto ? 'Re-plans after every change (locked rows kept)' : 'Auto re-plan off – use Auto-assign on the Assignments page');
    });
    document.getElementById('status-pill').addEventListener('click', function () { if (A.ev) go('conflicts'); });
    document.getElementById('btn-home').addEventListener('click', function () { go('library'); });
    document.addEventListener('keydown', onKey);
    A.auto = Store.getPref('auto', '1') !== '0';
    window.addEventListener('pagehide', function () { saveNow(); });
    document.addEventListener('visibilitychange', function () { if (document.hidden) saveNow(); });
    Store.init().then(function () {
      document.documentElement.setAttribute('data-platform', Store.platform);
      return Store.list();
    }).then(function (lib) {
      A.library = lib || [];
      var last = Store.getPref('lastDoc', '');
      var pick = A.library.filter(function (d) { return d.id === last; })[0] || A.library[0];
      if (pick) {
        return Store.load(pick.id).then(function (text) {
          A.ev = X.fromJSON(text); A.docId = pick.id; recompute();
          var sec = Store.getPref('section', 'assignments');
          go(SECTIONS[sec] ? sec : 'assignments');
        });
      }
      openEvent(JSON.parse(JSON.stringify(W.examples.example_q3)), null, 'library');
      toast('Welcome! An example event is open – tap New event for your own.', 4500);
    }).catch(function (e) {
      console.error(e);
      openEvent(JSON.parse(JSON.stringify(W.examples.example_q3)), null, 'library');
    }).then(function () { Store.ready(); });
  };
})(WTP);
