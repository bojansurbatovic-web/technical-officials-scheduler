"""Athletes' guide: the schedule and course facts that matter to athletes only (no TO meetings or jobs).
Same content as web/js/athletes.js in the iPhone/iPad/Mac/web version."""
import datetime as dt
import html

from . import engine as E
from . import reference as ref

SESSION_TEXT = {
    "briefing_checkin": ("Briefing check-in", "Show your accreditation or photo ID. Race packs are handed out after the briefing."),
    "athletes_briefing": ("Athletes’ briefing", "Attendance is mandatory. Course, rules and any changes announced here are binding."),
    "swim_fam": ("Swim course familiarisation", "Swim the course under race-like conditions. Wear your race cap if instructed."),
    "bike_fam": ("Bike course familiarisation", "Ride the course with officials present. Helmet on and fastened."),
    "coaches_meeting": ("Coaches’ meeting", "For team managers and coaches."),
}
RACE_TEXT = [
    ("lounge_open", "Athlete lounge opens", "Check in with your race number, wetsuit, cap and goggles.", False),
    ("tz_open", "Transition opens", "Equipment check at the entrance: helmet, bike, race numbers.", False),
    ("tz_close", "Transition closes", "All equipment must be in place; leave transition.", False),
    ("lounge_close", "Athlete lounge closes", "Be in the lounge before this time.", False),
    ("intro", "Athlete introduction", "Line up in start-number order.", False),
    ("start", "START", "", False),
    ("winner", "Expected leader finish", "Estimate from typical race times.", True),
    ("medal", "Medal ceremony", "Medallists report to the ceremony area straight after finishing.", True),
    ("protest_close", "Protest time ends", "Protests to the Head Referee within the protest time after the finish (CR 12.4).", True),
]


def info(ev):
    a = ev["event"].get("athletes") or {}
    return {"briefing_location": a.get("briefing_location", ""), "office": a.get("office", ""), "notes": a.get("notes", "")}


def _races(ev, race_id=""):
    rs = E.races_sorted(ev)
    return [r for r in rs if r["id"] == race_id] if race_id else rs


def items(ev, res, race_id=""):
    """[{s, e, date, title, text, race, race_id, kind, approx}] sorted by time."""
    ids = [r["id"] for r in _races(ev, race_id)]
    out = []
    for se in res["sessions"]:
        if not se["enabled"] or se["key"] not in SESSION_TEXT:
            continue
        if not any(i in ids for i in se["for_races"]):
            continue
        title, text = SESSION_TEXT[se["key"]]
        parts = se["name"].split(" – ", 1)
        who = parts[1] if len(parts) > 1 else ""
        out.append({"s": se["s"], "e": se["e"], "date": se["date"], "title": title + (f" – {who}" if who else ""), "text": text,
                    "race": "", "race_id": "session", "kind": se["key"], "approx": False})
    for r in _races(ev, race_id):
        tl = res["timelines"][r["id"]]
        for key, title, text, approx in RACE_TEXT:
            out.append({"s": tl[key], "e": None, "date": E.date_at(ev, tl[key]), "title": title + ("" if race_id else f" – {r['name']}"),
                        "text": text, "race": r["name"], "race_id": r["id"], "kind": key, "approx": approx})
    return sorted(out, key=lambda x: x["s"])


def course(ev, r):
    legs = max(1, int(r.get("legs", 1) or 1))
    laps = r.get("laps", {})

    def lap(n):
        n = int(n or 1)
        return f"{n} laps" if n > 1 else "1 lap"

    def num(x):
        x = float(x)
        return str(int(x)) if x == int(x) else f"{x:g}"
    rows = [("Swim", f"{num(r['swim_m'])} m · {lap(laps.get('swim', 1))}"),
            ("Bike", f"{num(r['bike_km'])} km · {lap(laps.get('bike', 1))} · {'draft-legal' if r.get('draft_legal') else 'non-drafting'}"),
            ("Run", f"{num(r['run_km'])} km · {lap(laps.get('run', 1))}")]
    if legs > 1:
        rows.insert(0, ("Format", f"{legs} legs per team (each athlete swims, bikes and runs)"))
    if r.get("draft_legal") and int(r.get("wheel_stations", 0) or 0) > 0:
        rows.append(("Wheel stations", str(r["wheel_stations"])))
    if int(r.get("aid_stations", 0) or 0) > 0:
        rows.append(("Aid stations (run)", str(r["aid_stations"])))
    return rows


def rules(ev, race_id=""):
    rs = _races(ev, race_id)
    out = ["Attend the athletes’ briefing and bring your accreditation or photo ID.",
           "Your helmet must be on and fastened from before you take the bike off the rack until it is back on the rack.",
           "Mount after the mount line and dismount before the dismount line.",
           "Wear your race suit for the whole race; keep race numbers visible as instructed.",
           "Wetsuit use is announced on race morning according to the water temperature."]
    if any(r.get("draft_legal") for r in rs):
        out.append("Draft-legal bike: drafting is allowed only with athletes of your own race. "
                   "Lapped athletes may be removed, as announced at the briefing.")
    if any(not r.get("draft_legal") for r in rs):
        out.append("Non-drafting bike: keep out of the draft zone of the athlete in front; overtake within the allowed time.")
    if any(r.get("draft_legal") and int(r.get("wheel_stations", 0) or 0) > 0 for r in rs):
        out.append("Spare wheels go to the wheel stations before the race, as explained at the briefing.")
    out.append("Time penalties are served in the penalty box shown at the briefing.")
    out.append("Protests go to the Head Referee within the protest time after the finish (CR 12.4).")
    return out


def hm(m):
    return E.fmt_hhmm(m % 1440)


def long_date(d):
    return d.strftime("%A ") + str(d.day) + d.strftime(" %B %Y")


def time_text(it):
    return ("≈ " if it["approx"] else "") + hm(it["s"]) + (("–" + hm(it["e"])) if it["e"] is not None else "")


def guide_html(ev, res, race_id=""):
    esc = html.escape
    e, inf, races = ev["event"], info(ev), _races(ev, race_id)
    title = e.get("name") or "Event"
    o = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
         f"<title>{esc('Athletes’ guide – ' + title)}</title><style>",
         'body{font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Ubuntu,Arial,sans-serif;color:#16202c;margin:0;background:#fff}',
         "main{max-width:760px;margin:0 auto;padding:24px 18px 48px}h1{margin:0 0 4px;font-size:26px}"
         "h2{margin:28px 0 8px;font-size:19px;border-bottom:2px solid #1f6fd1;padding-bottom:4px}",
         ".muted{color:#5d6b7c}.day{margin:18px 0 6px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;font-size:13px;color:#5d6b7c}",
         "table{border-collapse:collapse;width:100%}td{padding:7px 8px;border-bottom:1px solid #dce2ea;vertical-align:top}"
         "td.t{width:92px;font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}",
         "tr.key td{background:#eef4fd}.small{font-size:13px}.box{border:1px solid #dce2ea;border-radius:10px;padding:12px 14px;margin:10px 0}",
         "ul{padding-left:20px}li{margin:4px 0}@media print{main{padding:0}h2{break-after:avoid}tr{break-inside:avoid}}</style></head><body><main>",
         f"<h1>Athletes’ guide</h1><div><strong>{esc(title)}</strong>{(' · ' + esc(e['venue'])) if e.get('venue') else ''}</div>",
         f"<div class=\"muted\">{esc(' · '.join(r['name'] for r in races))}</div>"]
    if inf["briefing_location"] or inf["office"] or inf["notes"]:
        o.append('<div class="box">')
        if inf["briefing_location"]:
            o.append(f"<div><strong>Briefing location:</strong> {esc(inf['briefing_location'])}</div>")
        if inf["office"]:
            o.append(f"<div><strong>Race office / packet pick-up:</strong> {esc(inf['office'])}</div>")
        if inf["notes"]:
            o.append(f'<div style="white-space:pre-wrap;margin-top:6px">{esc(inf["notes"])}</div>')
        o.append("</div>")
    o.append("<h2>Schedule</h2>")
    day = None
    for it in items(ev, res, race_id):
        if it["date"] != day:
            if day is not None:
                o.append("</table>")
            day = it["date"]
            o.append(f'<div class="day">{esc(long_date(day))}</div><table>')
        key = "key" if it["kind"] in ("start", "athletes_briefing") else ""
        sub = f'<div class="small muted">{esc(it["text"])}</div>' if it["text"] else ""
        o.append(f'<tr class="{key}"><td class="t">{time_text(it)}</td><td><strong>{esc(it["title"])}</strong>{sub}</td></tr>')
    if day is not None:
        o.append("</table>")
    o.append("<h2>Course</h2>")
    for r in races:
        rows = "".join(f'<tr><td style="width:150px">{esc(a)}</td><td>{esc(b)}</td></tr>' for a, b in course(ev, r))
        o.append(f'<div class="box"><strong>{esc(r["name"])}</strong> · start {esc(res["fmt"](res["timelines"][r["id"]]["start"]))}'
                 f'<table class="small">{rows}</table></div>')
    o.append("<h2>Key rules</h2><ul>" + "".join(f"<li>{esc(x)}</li>" for x in rules(ev, race_id)) + "</ul>")
    o.append(f'<p class="small muted">Times marked ≈ are estimates. The athletes’ briefing and the official race information prevail. '
             f"Made with {esc(ref.APP_NAME)} – independent tool, not affiliated with World Triathlon.</p></main></body></html>")
    return "\n".join(o)


def guide_ics(ev, res, race_id=""):
    base = E.base_date(ev)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def when(m):
        t = dt.datetime.combine(base, dt.time()) + dt.timedelta(minutes=round(m))
        return t.strftime("%Y%m%dT%H%M00")

    def txt(s):
        return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    inf = info(ev)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{ref.APP_NAME}//athletes//EN", "CALSCALE:GREGORIAN"]
    for i, it in enumerate(items(ev, res, race_id)):
        loc = inf["briefing_location"] if it["kind"] == "athletes_briefing" and inf["briefing_location"] else ev["event"].get("venue", "")
        lines += ["BEGIN:VEVENT", f"UID:athlete-{i}-{base.isoformat()}-{race_id or 'all'}@toscheduler", f"DTSTAMP:{stamp}",
                  f"DTSTART:{when(it['s'])}", f"DTEND:{when(it['e'] if it['e'] is not None else it['s'] + 10)}",
                  f"SUMMARY:{txt(('≈ ' if it['approx'] else '') + it['title'])}", f"LOCATION:{txt(loc)}",
                  f"DESCRIPTION:{txt(it['text'])}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
