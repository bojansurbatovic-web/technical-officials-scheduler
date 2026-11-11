"""Planning engine: race timelines, duty windows, auto-assignment, conflict checks.

The event is a plain dict (exactly what is saved to JSON), so the GUI,
the exporters and the tests all share one data model.
"""
import copy
import datetime as _dt
import math
import re
import uuid

from . import reference as ref

ALL = "ALL"  # legacy pseudo race id (single-day files); now "day:YYYY-MM-DD"
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ---------------------------------------------------------------- time helpers
def parse_hhmm(text, default=None):
    """'10:00' -> 600.0 minutes after midnight."""
    if isinstance(text, (int, float)):
        return float(text)
    m = re.match(r"^\s*(\d{1,2})[:.h](\d{2})\s*$", str(text or ""))
    if not m:
        return default
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        return default
    return float(h * 60 + mi)


def fmt_hhmm(minutes, seconds=False):
    if minutes is None:
        return ""
    total_s = int(round(minutes * 60))
    sign = "-" if total_s < 0 else ""
    total_s = abs(total_s)
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    if seconds:
        return f"{sign}{h:02d}:{m:02d}:{s:02d}"
    if s >= 30:
        m += 1
        if m == 60:
            h, m = h + 1, 0
    return f"{sign}{h:02d}:{m:02d}"


def parse_date(text):
    try:
        return _dt.date.fromisoformat(str(text or "").strip())
    except ValueError:
        return None


def race_date(ev, race):
    """The race's own date, else the event date, else today."""
    return parse_date(race.get("date")) or parse_date(ev["event"].get("date")) or _dt.date.today()


def race_dates(ev):
    return sorted({race_date(ev, r) for r in ev["races"]}) or [parse_date(ev["event"].get("date")) or _dt.date.today()]


def event_dates(ev):
    """Race days plus the days of enabled meetings/briefings (e.g. the briefing the day before)."""
    days = set(race_dates(ev))
    days |= {se["date"] for se in build_sessions(ev) if se["enabled"]}
    return sorted(days)


def base_date(ev):
    return event_dates(ev)[0]


def is_multiday(ev):
    return len(event_dates(ev)) > 1


def race_offset(ev, race):
    """Minutes from midnight of the first event day to midnight of the race day."""
    return float((race_date(ev, race) - base_date(ev)).days * 1440)


def day_key(d):
    return "day:" + d.isoformat()


def is_day_key(rid):
    return rid == ALL or str(rid).startswith("day:")


def day_label(d):
    return f"{WEEKDAYS[d.weekday()]} {d.day:02d}.{d.month:02d}."


def when_formatter(ev):
    """Function minutes -> 'HH:MM' (one day) or 'Sat 21.11. HH:MM' (several days)."""
    base, multi = base_date(ev), is_multiday(ev)

    def fmt(minutes):
        if minutes is None:
            return ""
        if not multi:
            return fmt_hhmm(minutes)
        days = int(math.floor(minutes / 1440.0))
        d = base + _dt.timedelta(days=days)
        return f"{day_label(d)} {fmt_hhmm(minutes - days * 1440)}"
    return fmt


def date_at(ev, minutes):
    return base_date(ev) + _dt.timedelta(days=int(math.floor(minutes / 1440.0)))


def takes_part(official, race_id):
    return bool(official.get("races", {}).get(race_id, True))


def fmt_dur(minutes):
    total_s = int(round(minutes * 60))
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ---------------------------------------------------------------- model builders
def new_id(prefix="r"):
    return f"{prefix}{uuid.uuid4().hex[:6]}"


def duty_defaults():
    return {k: v for k, v, _l, _s in ref.DUTY_DEFAULTS}


def new_race(fmt="standard", category="elite_women", start="10:00", name=None, date=""):
    f = ref.FORMATS[fmt]
    cat = ref.CATEGORIES[category]
    laps = f["laps_elite"] if cat["draft_legal"] else f["laps_ag"]
    return {
        "id": new_id("r"),
        "name": name or f"{cat['label']} – {f['label'].split(' (')[0]}",
        "category": category,
        "format": fmt,
        "date": date,    # "" = first event day (event date)
        "start": start,
        "legs": f["legs"],
        "swim_m": f["swim_m"], "bike_km": f["bike_km"], "run_km": f["run_km"],
        "laps": {"swim": laps[0], "bike": laps[1], "run": laps[2]},
        "wheel_stations": f["wheel_stations"] if cat["draft_legal"] else 0,
        "aid_stations": f["aid_stations"],
        "start_line": f["start_line"],
        "draft_legal": cat["draft_legal"],
        "paces": {k: cat[k] for k in ("swim_pace", "bike_speed", "run_pace", "t1", "t2",
                                       "gap_swim", "gap_t2", "gap_finish")},
        "schedule": dict(ref.SCHEDULE_DEFAULTS),
        "shifts": {},  # activity key -> [start shift, end shift] minutes
    }


def apply_format(race, fmt=None, category=None):
    """Reset distances/laps/paces after the user changes format or category."""
    fmt = fmt or race["format"]
    category = category or race["category"]
    fresh = new_race(fmt, category, race.get("start", "10:00"))
    for k in ("format", "category", "legs", "swim_m", "bike_km", "run_km", "laps",
              "wheel_stations", "aid_stations", "start_line", "draft_legal", "paces"):
        race[k] = copy.deepcopy(fresh[k])
    return race


def new_event(name="New event", date="", races=None, n_officials=0):
    ev = {
        "app": "wt-planner", "version": 1,
        "event": {"name": name, "venue": "", "date": date, "notes": "",
                  "td": "", "md": "", "jury": ["", ""],
                  "vcc_base": ref.RADIO_DEFAULTS["vcc_base"], "spare_pct": ref.RADIO_DEFAULTS["spare_pct"]},
        "settings": duty_defaults(),
        "races": races or [new_race()],
        "officials": [],
        "positions": {},
        "assignments": {},
        "sessions": {},          # overrides of rule-based meetings: id -> {enabled, date, start, end}
        "custom_sessions": [],   # user meetings: {id, name, date, start, end, attendees, ref}
    }
    for i in range(n_officials):
        ev["officials"].append(new_official(f"Official {i + 1}"))
    reset_positions(ev)
    return ev


def new_official(name):
    return {"name": name, "country": "", "primary": "", "max_secondary": 3,
            "available_from": "", "available_to": "", "radio": True, "notes": "",
            "races": {}}   # race id -> False when the official does NOT work that race


def normalise(ev):
    """Fill missing keys after loading an older/hand-made file."""
    base = new_event()
    for k in base:
        ev.setdefault(k, copy.deepcopy(base[k]))
    for k, v in base["event"].items():
        ev["event"].setdefault(k, copy.deepcopy(v))
    for k, v in duty_defaults().items():
        ev["settings"].setdefault(k, v)
    for r in ev["races"]:
        tmpl = new_race(r.get("format", "standard"), r.get("category", "elite_women"))
        for k, v in tmpl.items():
            if k == "id":
                r.setdefault("id", new_id("r"))
            else:
                r.setdefault(k, copy.deepcopy(v))
        for k, v in tmpl["paces"].items():
            r["paces"].setdefault(k, v)
        for k, v in tmpl["schedule"].items():
            r["schedule"].setdefault(k, v)
        for k, v in tmpl["laps"].items():
            r["laps"].setdefault(k, v)
    for o in ev["officials"]:
        for k, v in new_official("").items():
            o.setdefault(k, copy.deepcopy(v))
    for key in ref.POSITION_INDEX:
        ev["positions"].setdefault(key, {"enabled": ref.POSITION_INDEX[key]["proposed"], "count": None})
    # files from version 1.0.0 used "|ALL" for all-day positions
    dk = day_key(race_dates(ev)[0])
    ev["assignments"] = {(k[:-4] + "|" + dk if k.endswith("|" + ALL) else k): v
                         for k, v in ev.get("assignments", {}).items()}
    return ev


# ---------------------------------------------------------------- positions
def race_applies(race, cond):
    laps = race.get("laps", {})
    if cond == "all":
        return True
    if cond == "draft_legal":
        return bool(race.get("draft_legal"))
    if cond == "non_drafting":
        return not race.get("draft_legal")
    if cond == "relay":
        return int(race.get("legs", 1)) > 1
    if cond == "laps":
        return int(laps.get("bike", 1)) > 1 or int(laps.get("run", 1)) > 1
    if cond == "run_laps":
        return int(laps.get("run", 1)) > 1
    if cond == "bike_laps":
        return int(laps.get("bike", 1)) > 1
    if cond == "wheel":
        return bool(race.get("draft_legal")) and int(race.get("wheel_stations", 0)) > 0
    if cond == "aid":
        return int(race.get("aid_stations", 0)) > 0
    return True


def proposed_count(ev, pos):
    c = pos["count"]
    races = [r for r in ev["races"] if race_applies(r, pos["applies"])]
    if not races:
        return 0
    if isinstance(c, int):
        return c
    if c == "wheel_extra":
        return max(0, max(int(r.get("wheel_stations", 0)) for r in races) - 1)
    if c == "aid_extra":
        return max(0, max(int(r.get("aid_stations", 0)) for r in races) - 1)
    if c == "start_line":
        return max(int(r.get("start_line", 4)) for r in races)
    if c == "bike_pb":
        out = 0
        for r in races:
            per = 30.0 if r.get("format") in ("middle", "long") else 10.0
            out = max(out, int(math.ceil(float(r.get("bike_km", 40)) / per)))
        return out
    return 1


def reset_positions(ev):
    ev["positions"] = {p["key"]: {"enabled": p["proposed"], "count": None}
                       for p in ref.POSITION_INDEX.values()}
    return ev


def position_count(ev, key):
    pos = ref.POSITION_INDEX[key]
    cfg = ev["positions"].get(key, {})
    if not cfg.get("enabled", pos["proposed"]):
        return 0
    if not any(race_applies(r, pos["applies"]) for r in ev["races"]):
        return 0
    if cfg.get("count") not in (None, ""):
        return max(0, int(cfg["count"]))
    return proposed_count(ev, pos)


# ---------------------------------------------------------------- timelines
def protest_minutes(race):
    """CR 12.4: announce within 5 min + form within 15 min (Elite standard and shorter);
    15 + 30 min for middle/long distance and Age-Group."""
    if race.get("format") in ("middle", "long") or race.get("category") == "age_group":
        return 45.0
    return 20.0


def race_timeline(race, offset=0.0):
    """Milestones in minutes from midnight of the first event day (offset = race day)."""
    S = parse_hhmm(race.get("start"), 600.0) + float(offset)
    p = race["paces"]
    sch = race["schedule"]
    legs = max(1, int(race.get("legs", 1)))
    laps = race["laps"]
    sw = float(race["swim_m"]) / 100.0 * float(p["swim_pace"])
    bk = float(race["bike_km"]) / max(1e-6, float(p["bike_speed"])) * 60.0
    rn = float(race["run_km"]) * float(p["run_pace"])
    t1, t2 = float(p["t1"]), float(p["t2"])
    L = sw + t1 + bk + t2 + rn
    gs, gb, gf = float(p["gap_swim"]) / 100.0, float(p["gap_t2"]) / 100.0, float(p["gap_finish"]) / 100.0
    last_leg_start = S + (legs - 1) * L * (1 + gf)
    tl = {
        "start": S,
        "lounge_open": S - float(sch["lounge_open"]),
        "lounge_close": S - float(sch["lounge_close"]),
        "tz_open": S - float(sch["tz_open"]),
        "tz_close": S - float(sch["tz_close"]),
        "intro": S - float(sch["intro"]),
        "swim_first_out": S + sw,
        "swim_last_out": last_leg_start + sw * (1 + gs),
        "t1_first": S + sw,
        "t1_last": last_leg_start + (sw + t1) * (1 + gs),
        "bike_lap1": S + sw + t1 + bk / max(1, int(laps.get("bike", 1))),
        "t2_first": S + sw + t1 + bk,
        "t2_last": last_leg_start + (sw + t1 + bk) * (1 + gb),
        "run_first": S + sw + t1 + bk + t2,
        "winner": S + legs * L,
        "last_finisher": S + legs * L * (1 + gf),
    }
    rl = max(1, int(laps.get("run", 1)))
    tl["run_lap1_leader"] = tl["run_first"] + rn / rl
    last_run_start = tl["t2_last"] + t2 * (1 + gb)
    tl["run_lap_last"] = last_run_start + (tl["last_finisher"] - last_run_start) / rl
    tl["medal"] = tl["winner"] + float(sch["medal_after_winner"])
    tl["protest_close"] = tl["last_finisher"] + protest_minutes(race)
    tl["_segments"] = {"swim": sw, "t1": t1, "bike": bk, "t2": t2, "run": rn, "leg": L, "legs": legs}
    return tl


MILESTONES = [
    ("lounge_open", "Athlete lounge opens"), ("tz_open", "Transition opens"),
    ("lounge_close", "Athlete lounge closes"), ("tz_close", "Transition closes"),
    ("intro", "Athlete introduction"), ("start", "START"),
    ("swim_first_out", "Swim leader out"), ("swim_last_out", "Last athlete out of the water"),
    ("bike_lap1", "Bike leader completes lap 1"), ("t2_first", "Bike leader into T2"),
    ("t2_last", "Last athlete into T2"), ("run_lap1_leader", "Run leader completes lap 1"),
    ("winner", "Winner"), ("last_finisher", "Last finisher"), ("medal", "Medal ceremony"),
]


def activity_window(act_key, tl, settings, shifts=None):
    a = ref.ACTIVITIES[act_key]
    _label, sa, sp, ss, ea, ep, es, _toc = a

    def edge(anchor, param, sign):
        base = tl[anchor]
        if param is None:
            return base + float(sign)
        return base + float(sign) * float(settings.get(param, 0))

    s, e = edge(sa, sp, ss), edge(ea, ep, es)
    if shifts and act_key in shifts:
        ds, de = shifts[act_key]
        s += float(ds or 0)
        e += float(de or 0)
    if e < s:
        e = s
    return s, e


# ---------------------------------------------------------------- meetings & briefings
def _ceil15(m):
    return float(math.ceil(m / 15.0) * 15)


def build_sessions(ev):
    """Obligations outside the race itself, generated from the races (CR 2.7 b, 12.9; EOM 2.13, 3.2.8,
    Table 14). Each: id, key, name, date (date), start/end (minutes of that day), attendees, ref, enabled,
    for_races (race ids whose officials attend). User changes are in ev["sessions"] / ev["custom_sessions"]."""
    races = sorted(ev["races"], key=lambda r: (race_date(ev, r), parse_hhmm(r.get("start"), 600.0)))
    out = []
    if not races:
        return out
    settings = ev.get("settings", {})
    tl0 = {r["id"]: race_timeline(r) for r in races}
    rd = {r["id"]: race_date(ev, r) for r in races}
    by_date = {}
    for r in races:
        by_date.setdefault(rd[r["id"]], []).append(r)
    one_day = _dt.timedelta(days=1)

    def busy_until(d):
        if d not in by_date:
            return None
        return max(tl0[r["id"]]["last_finisher"] for r in by_date[d])

    def add(key, sid, d, start, end, served, suffix=""):
        name, att, rf, enabled = ref.SESSIONS[key]
        out.append({"id": sid, "key": key, "name": name + suffix, "date": d, "start": float(start), "end": float(end),
                    "attendees": list(att), "ref": rf, "enabled": enabled,
                    "for_races": [r["id"] for r in served], "custom": False})

    # A) once per event – the day before the first competition day
    first = races[0]
    prep = rd[first["id"]] - one_day
    # A fixed, conflict-free order for the day before (every time can be edited in the app):
    # drivers 08:30, medical 09:30, swim fam 10:00, start rehearsal + bike fam 11:15, finish rehearsal 12:45,
    # timing 13:15, TV 13:45, TOs' meeting 14:00-15:00, (coaches 15:00 if scheduled), briefing check-in 15:30,
    # Elite briefing 16:00 (CR 2.7 b(vii)), Jury 17:00 (CR 12.9).
    add("drivers_briefing", "drivers_briefing", prep, 8 * 60 + 30, 9 * 60 + 15, races)
    add("medical_meeting", "medical_meeting", prep, 9 * 60 + 30, 10 * 60, races)
    add("start_rehearsal", "start_rehearsal", prep, 11 * 60 + 15, 12 * 60, races)
    add("finish_rehearsal", "finish_rehearsal", prep, 12 * 60 + 45, 13 * 60 + 15, races)
    add("timing_meeting", "timing_meeting", prep, 13 * 60 + 15, 13 * 60 + 45, races)
    add("tv_meeting", "tv_meeting", prep, 13 * 60 + 45, 14 * 60, races)
    add("to_meeting", "to_meeting", prep, 14 * 60, 15 * 60, races)

    # B) swim and bike familiarisation per group (Elite/U23/Junior, Para, Age-Group)
    fam = {}
    for r in races:
        fam.setdefault(ref.BRIEFING_GROUPS.get(r["category"], ("elite", "elite"))[1], []).append(r)
    fam_days = {}                            # groups whose familiarisation falls on the same day share it
    for g, rs in fam.items():
        fam_days.setdefault(rd[rs[0]["id"]] - one_day, []).append(g)
    for d, gs in fam_days.items():
        rs = [r for g in gs for r in fam[g]]
        sg = 10 * 60.0                       # morning of the day before; the TD may set race time instead
        bu = busy_until(d)
        if bu is not None:                   # that day has racing: after the TO de-briefing
            sg = max(sg, _ceil15(bu + 90))
        sfx = "" if len(fam) == 1 else " – " + " + ".join(ref.BRIEFING_LABELS.get(g, g).split(" team")[0] for g in gs)
        gid = "+".join(gs)
        add("swim_fam", f"swim_fam:{gid}", d, sg, sg + 60, rs, sfx)
        add("bike_fam", f"bike_fam:{gid}", d, sg + 75, sg + 165, rs, sfx)

    # C) athletes' briefings per category, the day before that category's first race
    groups = {}
    for r in races:
        g = "relay" if int(r.get("legs", 1)) > 1 else ref.BRIEFING_GROUPS.get(r["category"], ("elite", "elite"))[0]
        groups.setdefault(g, []).append(r)
    if "relay" in groups and "elite" in groups and \
            rd[groups["relay"][0]["id"]] == rd[groups["elite"][0]["id"]]:
        groups["elite"] += groups.pop("relay")   # CR 2.7 b(v): may be held together
    order = ["elite", "u23", "junior", "relay", "para", "age_group"]
    by_prep = {}
    for g in order:
        if g in groups:
            by_prep.setdefault(rd[groups[g][0]["id"]] - one_day, []).append(g)
    for d, gs in by_prep.items():
        t = 16 * 60.0                                 # CR 2.7 b(vii): first briefing at 16:00
        last_end = t
        for g in gs:
            rs = groups[g]
            label = ref.BRIEFING_LABELS.get(g, g)
            if g == "elite" and any(int(r.get("legs", 1)) > 1 for r in rs) and any(int(r.get("legs", 1)) == 1 for r in rs):
                label = "Elite + Mixed relay"
            add("coaches_meeting", f"coaches_meeting:{g}", d, t - 60, t - 15, rs, f" – {label}")
            add("briefing_checkin", f"briefing_checkin:{g}", d, t - 30, t + 90, rs, f" – {label}")
            add("athletes_briefing", f"athletes_briefing:{g}", d, t, t + 60, rs, f" – {label}")
            if g == "age_group":          # only at World / Continental Championships (CR 2.7 b(ii))
                out[-1]["enabled"] = out[-2]["enabled"] = False
            last_end = t + 60
            t += 75
        add("jury_after_briefing", f"jury_after_briefing:{d.isoformat()}", d, last_end, last_end + 30,
            [r for g in gs for r in groups[g]])

    # D) every competition day: TO briefing before the first lounge opens, de-briefing after the last race
    for d, rs in by_date.items():
        first_lounge = min(tl0[r["id"]]["lounge_open"] for r in rs)
        add("to_briefing", f"to_briefing:{d.isoformat()}", d, first_lounge - 75, first_lounge - 45, rs)
        end = max(tl0[r["id"]]["last_finisher"] for r in rs) + 45
        add("to_debriefing", f"to_debriefing:{d.isoformat()}", d, end, end + 30, rs)

    # E) Competition Jury around every race
    sign = float(settings.get("hr_signoff", 15))
    prev_after = None
    for r in races:
        tl = tl0[r["id"]]
        b0, b1 = tl["start"] - 60, tl["start"] - 45
        if prev_after and prev_after["date"] == rd[r["id"]] and prev_after["start"] < b1 and b0 < prev_after["end"]:
            # the previous race's post-race meeting runs into this race's pre-race meeting: hold one meeting
            prev_after["start"], prev_after["end"] = min(prev_after["start"], b0), max(prev_after["end"], b1)
            prev_after["name"] += f" + 1 h before start – {r['name']}"
            prev_after["for_races"].append(r["id"])
        else:
            add("jury_before_race", f"jury_before_race:{r['id']}", rd[r["id"]], b0, b1, [r], f" – {r['name']}")
        add("jury_after_race", f"jury_after_race:{r['id']}", rd[r["id"]], tl["protest_close"] + sign,
            tl["protest_close"] + sign + 20, [r], f" – {r['name']}")
        prev_after = out[-1]

    # user changes
    over = ev.get("sessions", {}) or {}
    for se in out:
        o = over.get(se["id"])
        if not o:
            continue
        if "enabled" in o:
            se["enabled"] = bool(o["enabled"])
        if parse_date(o.get("date")):
            se["date"] = parse_date(o["date"])
        if parse_hhmm(o.get("start")) is not None:
            se["start"] = parse_hhmm(o["start"])
        if parse_hhmm(o.get("end")) is not None:
            se["end"] = parse_hhmm(o["end"])
        se["edited"] = True
    # the Jury meets after the (possibly moved) briefing of that day
    for se in out:
        if se["key"] == "jury_after_briefing" and not se.get("edited"):
            ends = [b["end"] for b in out if b["key"] == "athletes_briefing" and b["enabled"] and b["date"] == se["date"]]
            if ends:
                se["start"], se["end"] = max(ends), max(ends) + 30
    for c in ev.get("custom_sessions", []) or []:
        d = parse_date(c.get("date")) or rd[first["id"]]
        st_, en_ = parse_hhmm(c.get("start"), 600.0), parse_hhmm(c.get("end"), 660.0)
        out.append({"id": c.get("id") or new_id("s"), "key": "custom", "name": c.get("name") or "Meeting",
                    "date": d, "start": st_, "end": max(en_, st_), "attendees": list(c.get("attendees") or ["all_tos"]),
                    "ref": "added by user", "enabled": bool(c.get("enabled", True)),
                    "for_races": [r["id"] for r in races], "custom": True})
    for se in out:
        if se["end"] < se["start"]:
            se["end"] = se["start"]
    out.sort(key=lambda x: (x["date"], x["start"]))
    return out


ATTENDEE_WORDS = {"td": "Technical Delegate", "md": "Medical Delegate", "jury": "Competition Jury", "all_tos": "all TOs"}


def attendee_label(tokens):
    """Readable list of who must attend: position titles or group words."""
    titles = {p[0]: p[1] for p in ref.POSITIONS}
    out = []
    for t in tokens:
        out.append(ATTENDEE_WORDS.get(t) or titles.get(t, t).split(" (")[0])
    return ", ".join(out)


def sessions_abs(ev):
    """Sessions with absolute minutes (from midnight of the first event day)."""
    base = base_date(ev)
    out = []
    for se in build_sessions(ev):
        off = (se["date"] - base).days * 1440.0
        se = dict(se, s=off + se["start"], e=off + se["end"])
        out.append(se)
    return out


def start_window_warnings(ev):
    """EOM 2.10.2 Table 3 – minimum time from one Elite start to the next on the same day."""
    warn = []
    rs = races_sorted(ev)
    for a, b in zip(rs, rs[1:]):
        if race_date(ev, a) != race_date(ev, b):
            continue
        need = ref.START_WINDOWS.get(a["format"])
        if not need or not ref.CATEGORIES[a["category"]]["draft_legal"]:
            continue
        gap = parse_hhmm(b["start"], 0) - parse_hhmm(a["start"], 0)
        if gap < need - 15:
            warn.append(f"{a['name']} → {b['name']}: {int(gap)} min between starts; EOM 2.10.2 asks for "
                        f"{need} min (minimum {need - 15} min with TD approval).")
        elif gap < need:
            warn.append(f"{a['name']} → {b['name']}: {int(gap)} min between starts is below {need} min – "
                        f"allowed only with TD approval (EOM 2.10.2).")
    for se in build_sessions(ev):
        if se["key"] == "athletes_briefing" and se.get("edited") and se["enabled"] and \
                se["id"].endswith(":elite") and abs(se["start"] - 16 * 60) > 0.1:
            warn.append(f"{se['name']} moved to {fmt_hhmm(se['start'])}: CR 2.7 b(vii) sets 16:00 the day before "
                        "(changes must be published 45 days in advance, CR 2.7 b(ix)).")
    return warn


# ---------------------------------------------------------------- slots
def races_sorted(ev):
    return sorted(ev["races"], key=lambda r: race_offset(ev, r) + parse_hhmm(r.get("start"), 0.0))


def build_slots(ev):
    """Every position instance with its duty windows per race (or per day for all-day jobs)."""
    settings = ev["settings"]
    races = races_sorted(ev)
    tls = {r["id"]: race_timeline(r, race_offset(ev, r)) for r in races}
    rdate = {r["id"]: race_date(ev, r) for r in races}
    slots = []
    for key, pos in sorted(ref.POSITION_INDEX.items(), key=lambda kv: kv[1]["priority"]):
        n = position_count(ev, key)
        if n <= 0:
            continue
        app_races = [r for r in races if race_applies(r, pos["applies"])]
        for i in range(n):
            sid = f"{key}#{i + 1}"
            title = pos["title"] + (f" #{i + 1}" if n > 1 else "")
            windows = {}
            for r in app_races:
                wl = []
                for act in pos["activities"]:
                    s, e = activity_window(act, tls[r["id"]], settings, r.get("shifts"))
                    wl.append((s, e, ref.ACTIVITIES[act][0], act not in ref.NON_BLOCKING, act))
                windows[r["id"]] = wl
            day_races = {}
            if pos["all_day"] and windows:
                merged = {}
                for rid, wl in windows.items():
                    dk = day_key(rdate[rid])
                    day_races.setdefault(dk, []).append(rid)
                    merged.setdefault(dk, []).extend(w for w in wl if w[3])
                windows = {dk: [(min(w[0] for w in bl), max(w[1] for w in bl), pos["title"] + " (all day)",
                                 True, pos["activities"][0])] for dk, bl in merged.items()}
            else:
                day_races = {rid: [rid] for rid in windows}
            slots.append({"id": sid, "key": key, "title": title, "kind": pos["kind"],
                          "priority": pos["priority"], "toc": pos["toc"], "all_day": pos["all_day"],
                          "windows": windows, "races_of": day_races})
    return slots, tls


def slot_keys(slot):
    return [f"{slot['id']}|{rid}" for rid in slot["windows"]]


# ---------------------------------------------------------------- assignment
def _blocking(windows):
    return [(s, e) for s, e, _l, b, _a in windows if b]


def _gap(a, b):
    """Minutes between two intervals (negative = overlap)."""
    return max(b[0] - a[1], a[0] - b[1])


def outside_hours(s, e, af, at):
    """Daily availability (HH:MM each day) check for an interval in absolute minutes."""
    day = math.floor(s / 1440.0) * 1440.0
    return (af is not None and s - day < af) or (at is not None and e - day > at)


class _State:
    def __init__(self, ev, slots):
        self.ev = ev
        self.slots = {s["id"]: s for s in slots}
        self.buffer = float(ev["settings"].get("buffer", 5))
        self.names = [o["name"] for o in ev["officials"] if o.get("name", "").strip()]
        self.off = {o["name"]: o for o in ev["officials"] if o.get("name", "").strip()}
        self.assign = {}       # "slot|race" -> name
        self.locked = set()
        self.primary = {}      # name -> slot id
        self.busy = {n: [] for n in self.names}  # name -> list of (s, e, key)
        self.sessions = [se for se in sessions_abs(ev) if se["enabled"]]
        self.attending = {n: set() for n in self.names}

    def implied(self, name, key):
        """Meetings/briefings this job brings with it that the official does not attend yet."""
        sid, rid = key.split("|")
        slot = self.slots[sid]
        races = set(slot["races_of"].get(rid, [rid]))
        return [se for se in self.sessions if se["id"] not in self.attending[name]
                and (slot["key"] in se["attendees"] or "all_tos" in se["attendees"])
                and races & set(se["for_races"])]

    def windows_of(self, key):
        sid, rid = key.split("|")
        return self.slots[sid]["windows"].get(rid, [])

    def part(self, name, key):
        sid, rid = key.split("|")
        o = self.off[name]
        return all(takes_part(o, r) for r in self.slots[sid]["races_of"].get(rid, [rid]))

    def put(self, key, name):
        sessions = self.implied(name, key)
        self.assign[key] = name
        for s, e in _blocking(self.windows_of(key)):
            self.busy[name].append((s, e, key))
        for se in sessions:
            self.attending[name].add(se["id"])
            self.busy[name].append((se["s"], se["e"], "session:" + se["id"]))

    def key_day(self, key):
        wins = self.windows_of(key)
        return int(math.floor(min((w[0] for w in wins), default=0) / 1440.0))

    def secondaries(self, name, day=None):
        """Distinct secondary positions of an official (on one event day if day is given)."""
        prim = self.primary.get(name)
        return {k.split("|")[0] for k, n in self.assign.items()
                if n == name and k.split("|")[0] != prim and (day is None or self.key_day(k) == day)}

    def holder_rules(self, name):
        sid = self.primary.get(name)
        if not sid:
            return None
        return ref.POSITION_INDEX[self.slots[sid]["key"]]["holder_rules"]

    def fits(self, name, key, min_gap):
        if not self.part(name, key):
            return False
        o = self.off[name]
        af, at = parse_hhmm(o.get("available_from")), parse_hhmm(o.get("available_to"))
        sid = key.split("|")[0]
        own = _blocking(self.windows_of(key))
        meet = [(se["s"], se["e"]) for se in self.implied(name, key)]
        for s, e in own:
            if outside_hours(s, e, af, at):
                return False
        for i, (s, e) in enumerate(own + meet):
            is_meet = i >= len(own)
            for bs, be, bkey in self.busy[name]:
                if bkey.split("|")[0] == sid:
                    continue
                need = 0.0 if (is_meet and bkey.startswith("session:")) else min_gap
                if _gap((s, e), (bs, be)) < need:
                    return False
        for s, e in meet:                       # the job itself vs the meetings it brings
            for os_, oe in own:
                if _gap((s, e), (os_, oe)) < min_gap:
                    return False
        return True


def auto_assign(ev, keep_locked=True):
    """Fill the event's assignments. Locked assignments are kept."""
    slots, _tls = build_slots(ev)
    st = _State(ev, slots)
    old = ev.get("assignments", {}) if keep_locked else {}
    valid_keys = {k for s in slots for k in slot_keys(s)}
    for k, v in old.items():
        if v.get("locked") and k in valid_keys and v.get("official") in st.off:
            st.put(k, v["official"])
            st.locked.add(k)
        elif v.get("locked") and k in valid_keys and not v.get("official"):
            st.assign[k] = ""          # locked empty = deliberately left to LOC/volunteer
            st.locked.add(k)

    by_key = {}
    for s in slots:
        by_key.setdefault(s["key"], []).append(s)

    def free_keys(slot, name=None):
        return [k for k in slot_keys(slot) if k not in st.assign or (name and st.assign.get(k) == name)]

    def take_primary(name, slot, keys=None):
        st.primary[name] = slot["id"]
        for k in (keys if keys is not None else slot_keys(slot)):
            if k not in st.assign:
                st.put(k, name)

    def coverable(name, slot):
        """Free keys of this slot in races the official works and can fit."""
        return [k for k in slot_keys(slot) if k not in st.assign and st.fits(name, k, 0.0)]

    # primaries already implied by locks (a locked person on a primary-kind slot)
    for k in sorted(st.locked):
        n = st.assign.get(k)
        sid = k.split("|")[0]
        if n and n not in st.primary and st.slots[sid]["kind"] == "primary":
            st.primary[n] = sid

    # 1) explicit primaries chosen by the user
    for name in st.names:
        if name in st.primary:
            continue
        want = st.off[name].get("primary") or ""
        if want and want in by_key:
            for slot in by_key[want]:
                mine = [k for k in slot_keys(slot) if st.part(name, k)]
                if mine and all(k not in st.assign for k in mine):
                    keys = coverable(name, slot)
                    if keys:
                        take_primary(name, slot, keys)
                        break

    def give(slot, queue):
        """Hand the free parts of a slot to queued officials (one per day/race group if needed)."""
        while queue:
            best, best_keys = None, []
            for name in queue:
                keys = coverable(name, slot)
                if len(keys) > len(best_keys):
                    best, best_keys = name, keys
                    if len(keys) == len([k for k in slot_keys(slot) if k not in st.assign]):
                        break
            if not best:
                return
            queue.remove(best)
            take_primary(best, slot, best_keys)
            if all(k in st.assign for k in slot_keys(slot)):
                return

    # 2) automatic primaries, by priority (only in races the official works and is available for)
    prim_slots = [s for s in slots if s["kind"] == "primary"]
    queue = [n for n in st.names if n not in st.primary]
    for slot in prim_slots:
        if not queue:
            break
        if not free_keys(slot):
            continue
        give(slot, queue)
    # 3) spare officials take secondary-kind positions as their primary
    #    (not the ones that naturally belong to HR / CRO, e.g. Starter)
    natural = {"head_referee", "cro"}
    for slot in [s for s in slots if s["kind"] == "secondary"
                 and ref.POSITION_INDEX[s["key"]]["prefer_holder"] not in natural]:
        if not queue:
            break
        if not free_keys(slot):
            continue
        give(slot, queue)

    # 4) fill everything else as secondary jobs
    todo = []
    for s in slots:
        for k in slot_keys(s):
            if k not in st.assign:
                wins = st.windows_of(k)
                start = min((w[0] for w in wins), default=0)
                todo.append((s["priority"], start, k))
    todo.sort()

    def candidates(key):
        sid = key.split("|")[0]
        slot = st.slots[sid]
        pos = ref.POSITION_INDEX[slot["key"]]
        out = []
        for name in st.names:
            rules = st.holder_rules(name)
            if rules is not None and slot["key"] not in rules:
                continue
            secs = st.secondaries(name, st.key_day(key))
            maxs = int(st.off[name].get("max_secondary", 3) or 0)
            if sid not in secs and len(secs) >= maxs:
                continue
            if not st.fits(name, key, 0.0):
                continue
            score = 40 if st.fits(name, key, st.buffer) else 0
            if any(st.assign.get(k) == name for k in slot_keys(slot)):
                score += 100
            prim = st.primary.get(name)
            if prim and pos["prefer_holder"] and st.slots[prim]["key"] == pos["prefer_holder"]:
                score += 60
            score -= 12 * len(secs)
            if not prim:
                score += 5
            out.append((score, -st.names.index(name), name))
        out.sort(reverse=True)
        return [n for _s, _i, n in out]

    for _p, _s, key in todo:
        if key in st.assign:
            continue
        cands = candidates(key)
        if cands:
            st.put(key, cands[0])

    new = {}
    for k in valid_keys:
        if k in st.assign:
            new[k] = {"official": st.assign[k], "locked": k in st.locked}
    ev["assignments"] = new
    ev["_primary"] = dict(st.primary)
    return ev


# ---------------------------------------------------------------- evaluation
def primary_map(ev, slots):
    """name -> primary slot id (explicit choice, else first primary-kind slot held)."""
    sl = {s["id"]: s for s in slots}
    held = {}
    for k, v in ev.get("assignments", {}).items():
        n = v.get("official")
        if n:
            held.setdefault(n, []).append(k.split("|")[0])
    out = {}
    for o in ev["officials"]:
        n = o.get("name")
        if not n or n not in held:
            continue
        ids = [i for i in dict.fromkeys(held[n]) if i in sl]
        want = o.get("primary")
        pick = next((i for i in ids if sl[i]["key"] == want), None)
        if pick is None:
            stored = ev.get("_primary", {}).get(n)
            pick = stored if stored in ids else None
        if pick is None:
            prim = [i for i in ids if sl[i]["kind"] == "primary"]
            pick = (sorted(prim, key=lambda i: sl[i]["priority"]) or ids or [None])[0]
        if pick:
            out[n] = pick
    return out


def evaluate(ev):
    """Everything the GUI and exporters show."""
    slots, tls = build_slots(ev)
    sl = {s["id"]: s for s in slots}
    race_by_id = {r["id"]: r for r in ev["races"]}
    fmt = when_formatter(ev)
    multi = is_multiday(ev)

    def race_name(rid):
        if is_day_key(rid):
            if not multi:
                return "All races"
            d = parse_date(rid[4:]) if rid.startswith("day:") else base_date(ev)
            return f"All races – {day_label(d)}"
        return race_by_id[rid]["name"]
    buffer = float(ev["settings"].get("buffer", 5))
    asg = ev.get("assignments", {})
    prim = primary_map(ev, slots)

    rows = []
    for s in slots:
        for rid, wins in s["windows"].items():
            k = f"{s['id']}|{rid}"
            v = asg.get(k, {})
            name = v.get("official", "")
            bl = _blocking(wins) or [(w[0], w[1]) for w in wins]
            start = min((w[0] for w in bl), default=None)
            end = max((w[1] for w in bl), default=None)
            role = ""
            if name:
                role = "Primary" if prim.get(name) == s["id"] else "Secondary"
            rows.append({
                "key": k, "slot": s["id"], "pos_key": s["key"], "title": s["title"], "kind": s["kind"],
                "race_id": rid, "race": race_name(rid), "races_of": s["races_of"].get(rid, [rid]),
                "date": date_at(ev, start).isoformat() if start is not None else "",
                "official": name, "locked": bool(v.get("locked")), "role": role,
                "start": start, "end": end, "windows": wins, "toc": s["toc"], "status": "",
                "priority": s["priority"],
            })

    # meetings & briefings each official must attend (from the positions they hold)
    sess = sessions_abs(ev)
    sess_on = [se for se in sess if se["enabled"]]
    attend = {}
    for r in rows:
        n = r["official"]
        if not n:
            continue
        for se in sess_on:
            if (r["pos_key"] in se["attendees"] or "all_tos" in se["attendees"]) and set(r["races_of"]) & set(se["for_races"]):
                attend.setdefault(n, {})[se["id"]] = se
    e_ = ev["event"]
    wt_people = [("td", e_.get("td") or "Technical Delegate", "Technical Delegate"),
                 ("md", e_.get("md") or "Medical Delegate", "Medical Delegate")]
    jury = [j for j in e_.get("jury", []) if j] or ["Competition Jury"]
    wt_people += [("jury", j, "Competition Jury member") for j in jury]

    def session_row(se, who):
        return {"key": "session:" + se["id"], "slot": "session:" + se["id"], "pos_key": "session",
                "title": se["name"], "kind": "session", "race_id": "session", "race": "Meetings & briefings",
                "races_of": se["for_races"], "date": se["date"].isoformat(), "official": who, "locked": False,
                "role": "Obligation", "start": se["s"], "end": se["e"],
                "windows": [(se["s"], se["e"], se["name"], True, "session")], "toc": se["ref"], "status": "",
                "priority": 0}

    session_rows = {n: [session_row(se, n) for se in d.values()] for n, d in attend.items()}
    for tok, who, _role in wt_people:
        session_rows[who] = [session_row(se, who) for se in sess_on if tok in se["attendees"]]

    # conflicts per official
    per = {}
    for r in rows:
        if r["official"]:
            for s, e, label, b, _a in r["windows"]:
                if b:
                    per.setdefault(r["official"], []).append((s, e, r["key"], r["title"], label))
    for n, srows in session_rows.items():
        for r in srows:
            per.setdefault(n, []).append((r["start"], r["end"], r["key"], r["title"], "meeting / briefing"))
    conflicts = []
    status = {}
    for name, items in per.items():
        items.sort()
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if a[2].split("|")[0] == b[2].split("|")[0]:
                    continue
                g = _gap((a[0], a[1]), (b[0], b[1]))
                both_meetings = a[2].startswith("session:") and b[2].startswith("session:")
                if g < (0.0 if both_meetings else buffer):
                    level = "CONFLICT" if g < 0 else "TIGHT"
                    conflicts.append({"official": name, "a": a[3], "a_label": a[4], "b": b[3], "b_label": b[4],
                                      "a_time": f"{fmt(a[0])}–{fmt_hhmm(a[1] % 1440)}",
                                      "b_time": f"{fmt(b[0])}–{fmt_hhmm(b[1] % 1440)}",
                                      "gap": round(g, 1), "level": level})
                    for key in (a[2], b[2]):
                        if status.get((name, key)) != "CONFLICT":
                            status[(name, key)] = level
    # availability
    off = {o["name"]: o for o in ev["officials"]}
    for r in rows:
        n = r["official"]
        if n and n in off:
            o = off[n]
            if not all(takes_part(o, x) for x in r["races_of"]):
                status[(n, r["key"])] = "CONFLICT"
                conflicts.append({"official": n, "a": r["title"], "a_label": "does not work this race",
                                  "b": r["race"], "b_label": "", "a_time": f"{fmt(r['start'])}–{fmt_hhmm((r['end'] or 0) % 1440)}",
                                  "b_time": "", "gap": None, "level": "CONFLICT"})
            af, at = parse_hhmm(o.get("available_from")), parse_hhmm(o.get("available_to"))
            if r["start"] is not None and outside_hours(r["start"], r["end"], af, at):
                status[(n, r["key"])] = "CONFLICT"
                conflicts.append({"official": n, "a": r["title"], "a_label": "outside availability",
                                  "b": "", "b_label": "", "a_time": f"{fmt(r['start'])}–{fmt_hhmm(r['end'] % 1440)}",
                                  "b_time": f"{off[n].get('available_from') or '…'}–{off[n].get('available_to') or '…'}",
                                  "gap": None, "level": "CONFLICT"})
        elif n and n not in off:
            status[(n, r["key"])] = "CONFLICT"
    for r in rows:
        if not r["official"]:
            r["status"] = "UNFILLED" if not r["locked"] else "LOC / volunteer"
        else:
            r["status"] = status.get((r["official"], r["key"]), "OK")
    for n, srows in session_rows.items():
        for r in srows:
            r["status"] = status.get((n, r["key"]), "OK")

    rows.sort(key=lambda r: (r["priority"], r["slot"], r["start"] if r["start"] is not None else 0))

    # officials summary
    officials = []
    for o in ev["officials"]:
        n = o["name"]
        mine = [r for r in rows if r["official"] == n]
        p = prim.get(n)
        officials.append({
            "name": n, "country": o.get("country", ""),
            "races": [r["id"] for r in races_sorted(ev) if takes_part(o, r["id"])],
            "primary": sl[p]["title"] if p in sl else "",
            "secondary": sorted({r["title"] for r in mine if r["slot"] != p}),
            "duties": sorted(mine + session_rows.get(n, []), key=lambda r: r["start"] or 0),
            "conflicts": sum(1 for c in conflicts if c["official"] == n),
            "busy_min": sum((r["end"] or 0) - (r["start"] or 0) for r in mine),
        })

    # radios
    e = ev["event"]
    personal = sum(1 for o in ev["officials"] if o.get("radio", True) and o.get("name"))
    personal += (1 if e.get("td") else 0) + (1 if e.get("md") else 0)
    vcc = int(e.get("vcc_base", 1) or 0)
    spare = int(math.ceil(personal * float(e.get("spare_pct", 10) or 0) / 100.0))
    radios = {"personal": personal, "vcc": vcc, "spare": spare, "total": personal + vcc + spare}

    wt_officials = [{"name": who, "role": role, "duties": sorted(session_rows.get(who, []), key=lambda r: r["start"]),
                     "conflicts": sum(1 for c in conflicts if c["official"] == who)} for _t, who, role in wt_people]
    names_by_session = {}
    for n, d in attend.items():
        for sid in d:
            names_by_session.setdefault(sid, []).append(n)
    for se in sess:
        wt = [who for tok, who, _r in wt_people if tok in se["attendees"]]
        se["people"] = wt + sorted(names_by_session.get(se["id"], []))
    unfilled = [r for r in rows if r["status"] == "UNFILLED"]
    return {"slots": slots, "timelines": tls, "rows": rows, "conflicts": conflicts, "fmt": fmt,
            "sessions": sess, "wt_officials": wt_officials, "warnings": start_window_warnings(ev),
            "multiday": multi, "dates": event_dates(ev),
            "officials": officials, "radios": radios, "unfilled": unfilled,
            "n_conflict": sum(1 for c in conflicts if c["level"] == "CONFLICT"),
            "n_tight": sum(1 for c in conflicts if c["level"] == "TIGHT")}


def run_sheet(ev, result=None):
    """Chronological list of race milestones for all races."""
    result = result or evaluate(ev)
    out = []
    for r in races_sorted(ev):
        tl = result["timelines"][r["id"]]
        for key, label in MILESTONES:
            out.append({"time": tl[key], "race": r["name"], "item": label, "key": key, "race_id": r["id"]})
    for se in result.get("sessions", []):
        if se["enabled"]:
            out.append({"time": se["s"], "race": "Meetings & briefings", "item": f"{se['name']} (until {fmt_hhmm(se['end'])})",
                        "key": "session", "race_id": "session"})
    out.sort(key=lambda x: x["time"])
    return out


def set_assignment(ev, key, official, locked=True):
    if official:
        ev.setdefault("assignments", {})[key] = {"official": official, "locked": locked}
    else:
        ev.setdefault("assignments", {})[key] = {"official": "", "locked": locked}


def clear_unlocked(ev):
    ev["assignments"] = {k: v for k, v in ev.get("assignments", {}).items() if v.get("locked")}


def lock_all(ev, locked=True):
    for v in ev.get("assignments", {}).values():
        v["locked"] = locked
