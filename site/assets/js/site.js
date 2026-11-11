/* TriSport.me — site script. No external dependencies. */

/* ------------------------------------------------------------------
   APP LINKS — the only place you need to edit.
   Paste each App Store address between the quotes, e.g.
   appStore: "https://apps.apple.com/app/id1234567890"
   While a link is empty, the button opens an App Store search for
   the app name instead.
------------------------------------------------------------------- */
var APP_LINKS = {
  tricarbon:  { name: "TriCarbon",                    appStore: "https://apps.apple.com/us/app/tricarbon-race-carbon-tracker/id6826201612" },
  trianatomy: { name: "TriAnatomy",                   appStore: "https://apps.apple.com/us/app/trianatomy/id6829890027" },
  triofficial:{ name: "TriOfficial",                  appStore: "https://apps.apple.com/us/app/triofficial-race-officials/id6823983576" },
  scheduler:  { name: "Technical Officials Scheduler", appStore: "" }
};

(function () {
  "use strict";

  /* App Store links */
  document.querySelectorAll("[data-store]").forEach(function (a) {
    var app = APP_LINKS[a.getAttribute("data-store")];
    if (!app) return;
    a.href = app.appStore || "https://apps.apple.com/us/search?term=" + encodeURIComponent(app.name);
  });

  /* Mobile menu */
  var menuBtn = document.getElementById("menu-btn");
  var nav = document.getElementById("nav");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) { nav.classList.remove("open"); menuBtn.setAttribute("aria-expanded", "false"); }
    });
  }

  /* Footer year */
  var y = document.getElementById("year");
  if (y) y.textContent = new Date().getFullYear();

  /* Toast */
  var toastEl = document.getElementById("toast"), toastTimer;
  function toast(msg) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, 2600);
  }

  /* Tabs */
  var tabs = Array.prototype.slice.call(document.querySelectorAll('[role="tab"]'));
  function selectTab(tab, focus) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      var panel = document.getElementById(t.getAttribute("aria-controls"));
      if (panel) panel.hidden = !on;
    });
    if (focus) tab.focus();
  }
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { selectTab(t); });
    t.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") selectTab(tabs[(i + 1) % tabs.length], true);
      if (e.key === "ArrowLeft") selectTab(tabs[(i - 1 + tabs.length) % tabs.length], true);
    });
  });
  document.querySelectorAll("[data-open-tab]").forEach(function (el) {
    el.addEventListener("click", function () {
      var t = document.getElementById("tab-" + el.getAttribute("data-open-tab"));
      if (t) selectTab(t);
    });
  });

  /* TriCarbon — simplified illustration, not the app's calculation */
  var people = document.getElementById("c-people");
  var vehicles = document.getElementById("c-vehicles");
  var travel = document.getElementById("c-travel");
  function fmt(n, d) { return n.toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d }); }
  function updateCarbon() {
    if (!people) return;
    var p = +people.value, v = +vehicles.value;
    var perPerson = { regional: 0.015, continental: 0.024, world: 0.048 }[travel.value];
    var travelT = p * perPerson, vehT = v * 0.35, total = travelT + vehT;
    document.getElementById("c-people-out").textContent = fmt(p, 0);
    document.getElementById("c-vehicles-out").textContent = fmt(v, 0);
    document.getElementById("c-total").textContent = fmt(total, 1) + " t";
    document.getElementById("c-per").textContent = fmt(total * 1000 / p, 1) + " kg";
    var tp = Math.round(travelT / total * 100);
    document.getElementById("c-bar-travel").style.width = tp + "%";
    document.getElementById("c-bar-veh").style.width = (100 - tp) + "%";
    document.getElementById("c-pct-travel").textContent = tp + "%";
    document.getElementById("c-pct-veh").textContent = (100 - tp) + "%";
  }
  [people, vehicles, travel].forEach(function (el) { if (el) el.addEventListener("input", updateCarbon); });
  updateCarbon();

  /* Scheduler — sample roster with fictional names */
  var roster = [
    { name: "A. Marković",  level: "Level 2", pos: "Swim start",          time: "07:00 – 09:30" },
    { name: "L. Fontaine",  level: "Level 1", pos: "Transition",          time: "07:15 – 10:00" },
    { name: "K. Tanaka",    level: "Level 2", pos: "Bike course (moto)",  time: "08:00 – 11:30" },
    { name: "S. Okafor",    level: "Level 1", pos: "Run course",          time: "09:00 – 12:45" },
    { name: "E. Lindqvist", level: "Level 2", pos: "Penalty box",         time: "09:00 – 12:45" },
    { name: "R. Costa",     level: "Level 1", pos: "Finish",              time: "09:30 – 13:00" }
  ];
  var rosterBody = document.getElementById("roster");
  function renderRoster() {
    if (!rosterBody) return;
    rosterBody.innerHTML = "";
    roster.forEach(function (r) {
      var tr = document.createElement("tr");
      [[r.name], [r.level], [r.pos, "pos"], [r.time, "time"]].forEach(function (c) {
        var td = document.createElement("td");
        td.textContent = c[0];
        if (c[1]) td.className = c[1];
        tr.appendChild(td);
      });
      rosterBody.appendChild(tr);
    });
  }
  renderRoster();
  var rotate = document.getElementById("roster-rotate");
  if (rotate) rotate.addEventListener("click", function () {
    var positions = roster.map(function (r) { return r.pos; });
    positions.unshift(positions.pop());
    roster.forEach(function (r, i) { r.pos = positions[i]; });
    renderRoster();
    toast("Sample positions rotated");
  });

  /* TriAnatomy — sample content */
  var anatomy = {
    swim: { title: "Swim: the pull and the catch", muscles: "Latissimus dorsi, rotator cuff, core",
            note: "A stable shoulder and trunk keep the body aligned through each stroke.",
            list: ["Scapular pull-ups", "Band external rotations", "Pallof press"] },
    bike: { title: "Bike: power from the hips", muscles: "Gluteus maximus, quadriceps, posterior chain",
            note: "Strong hips and a resilient lower back make the aero position sustainable.",
            list: ["Split squats", "Romanian deadlifts", "Hip flexor mobility"] },
    run:  { title: "Run: stiffness and return", muscles: "Soleus and gastrocnemius, tibialis anterior, hamstrings",
            note: "Calf capacity and hamstring strength help hold form when running off the bike.",
            list: ["Bent-knee calf raises", "Single-leg hops", "Nordic hamstring curls"] }
  };
  var segBtns = Array.prototype.slice.call(document.querySelectorAll("[data-seg]"));
  function showAnatomy(key) {
    var d = anatomy[key];
    if (!d || !document.getElementById("a-title")) return;
    segBtns.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-seg") === key ? "true" : "false"); });
    document.getElementById("a-title").textContent = d.title;
    document.getElementById("a-muscles").textContent = d.muscles;
    document.getElementById("a-note").textContent = d.note;
    var ul = document.getElementById("a-list");
    ul.innerHTML = "";
    d.list.forEach(function (x) {
      var li = document.createElement("li");
      li.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-check"/></svg>';
      li.appendChild(document.createTextNode(x));
      ul.appendChild(li);
    });
  }
  segBtns.forEach(function (b) { b.addEventListener("click", function () { showAnatomy(b.getAttribute("data-seg")); }); });
  showAnatomy("swim");
})();
