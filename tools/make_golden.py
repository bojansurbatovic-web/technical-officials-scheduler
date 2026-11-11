"""Builds tests/golden.json: input events + what the Python engine (the Ubuntu app) plans for them.
The JS test (tests/test_engine.js) must reproduce every number. Usage:
  PYTHONHASHSEED=0 python3 tools/make_golden.py path/to/wt-planner"""
import sys, json, copy, os, random
sys.path.insert(0, sys.argv[1])
from wt_planner import engine as E, exporters as X

random.seed(7)
def R(*a, **k):
    r = E.new_race(*a, **k); return r

def officials(n, prefix="TO"):
    return [E.new_official(f"{prefix} {i+1:02d}") for i in range(n)]

cases = []
data = os.path.join(sys.argv[1], "wt_planner", "data")
for fn in ("example_q3.wtplan.json", "example_multiday.wtplan.json"):
    ev = X.load_json(os.path.join(data, fn)); ev["assignments"] = {}; ev.pop("_primary", None)
    cases.append((fn.split(".")[0], ev))

def mk(name, races, n, date="2027-06-12", tweak=None):
    ev = E.new_event(name, date, races=races); ev["officials"] = officials(n)
    if tweak: tweak(ev)
    cases.append((name, ev))

mk("sprint_ag_and_elite", [R("sprint", "age_group", "07:30"), R("sprint", "elite_women", "12:00"), R("sprint", "elite_men", "14:00")], 20)
mk("middle_long", [R("middle", "age_group", "07:00"), R("long", "age_group", "06:45", date="2027-06-13")], 16)
mk("relay_same_day", [R("sprint", "elite_women", "09:00"), R("sprint", "elite_men", "11:00"), R("mixed_relay", "elite_men", "15:00")], 22)
mk("youth_para_multi", [R("sprint", "junior_women", "09:00", date="2027-06-12"), R("sprint", "junior_men", "11:00", date="2027-06-12"),
                         R("sprint", "para", "08:00", date="2027-06-13"), R("standard", "u23_men", "13:00", date="2027-06-14")], 24)
mk("super_sprint_short_staff", [R("super_sprint", "elite_women", "10:00"), R("super_sprint", "elite_men", "10:45")], 9)

def tw1(ev):
    o = ev["officials"]
    o[0]["primary"] = "head_referee"; o[1]["primary"] = "cro"; o[2]["primary"] = "chief_swim"
    o[3]["available_from"] = "09:30"; o[4]["available_to"] = "11:00"; o[5]["max_secondary"] = 0
    o[6]["races"] = {ev["races"][1]["id"]: False}; o[7]["radio"] = False
    ev["event"]["td"] = "TD"; ev["event"]["md"] = "MD"; ev["event"]["jury"] = ["J1", "J2", ""]
    ev["positions"]["moto_to"]["enabled"] = True; ev["positions"]["asst_finish"]["count"] = 3
    ev["positions"]["chaperone"]["enabled"] = True; ev["positions"]["asst_aid_station"]["count"] = 0
    ev["races"][0]["shifts"] = {"finish_asst": [-5, 5], "aid": [10, 0]}
    ev["races"][1]["paces"]["gap_finish"] = 14; ev["races"][1]["schedule"]["lounge_open"] = 90
    ev["settings"]["buffer"] = 8; ev["settings"]["aid_pre"] = 40
    ev["sessions"] = {"to_meeting": {"enabled": False}, "athletes_briefing:elite": {"start": "16:30", "end": "17:30"},
                      "drivers_briefing": {"date": ev["races"][0]["date"] or "2027-06-12", "start": "07:00", "end": "07:30"}}
    ev["custom_sessions"] = [{"id": "c1", "name": "Dinner", "date": "2027-06-11", "start": "19:00", "end": "21:00", "attendees": ["all_tos"]},
                             {"id": "c2", "name": "Chiefs lunch", "date": "2027-06-12", "start": "12:00", "end": "12:30", "attendees": ["td", "chief_swim", "chief_run"]}]
mk("tweaks_and_overrides", [R("standard", "elite_women", "10:00"), R("standard", "elite_men", "13:30")], 21, tweak=tw1)

def tw2(ev):
    # locked rows and a LOC/volunteer row, then re-plan
    E.auto_assign(ev, keep_locked=False)
    keys = sorted(ev["assignments"])
    for k in keys[:6]: ev["assignments"][k]["locked"] = True
    ev["assignments"][keys[7]] = {"official": "", "locked": True}
    for k in keys[8:]: ev["assignments"].pop(k)
    ev.pop("_primary", None)
mk("locked_rows", [R("standard", "elite_women", "10:00"), R("standard", "elite_men", "12:45")], 18, tweak=tw2)

def summary(ev, res):
    rnd = lambda x: None if x is None else round(x, 6)
    return {
        "assignments": ev["assignments"],
        "rows": [[r["key"], r["official"], r["status"], r["role"], rnd(r["start"]), rnd(r["end"]), r["date"], r["race"]] for r in res["rows"]],
        "conflicts": [[c["official"], c["a"], c["b"], c["level"], c["gap"], c["a_time"], c["b_time"]] for c in res["conflicts"]],
        "sessions": [[s["id"], s["date"].isoformat(), rnd(s["start"]), rnd(s["end"]), s["enabled"], s["people"], s["name"], rnd(s["s"])] for s in res["sessions"]],
        "officials": [[o["name"], o["primary"], o["secondary"], o["conflicts"], len(o["duties"]), rnd(o["busy_min"]), o["races"]] for o in res["officials"]],
        "wt": [[w["name"], len(w["duties"]), w["conflicts"]] for w in res["wt_officials"]],
        "radios": res["radios"], "warnings": res["warnings"], "dates": [d.isoformat() for d in res["dates"]],
        "multiday": res["multiday"], "n_conflict": res["n_conflict"], "n_tight": res["n_tight"],
        "timelines": {k: {m: rnd(v) for m, v in tl.items() if m != "_segments"} for k, tl in res["timelines"].items()},
        "fmt": [res["fmt"](m) for m in (0, 599.5, 1439.99, 1500.25, 3000)],
        "run_sheet": [[x["race"], x["item"], rnd(x["time"])] for x in E.run_sheet(ev, res)],
    }

out = []
for name, ev in cases:
    E.normalise(ev)
    inp = copy.deepcopy(ev)
    E.auto_assign(ev, keep_locked=True)
    res = E.evaluate(ev)
    out.append({"name": name, "input": inp, "expected": summary(ev, res)})
    print(f"{name:28s} rows {len(res['rows']):3d} unfilled {len(res['unfilled']):2d} conflicts {res['n_conflict']} tight {res['n_tight']}")
p = os.path.join(os.path.dirname(__file__), "..", "tests", "golden.json")
json.dump(out, open(p, "w"), ensure_ascii=False, indent=0, default=str)
print("wrote", os.path.normpath(p))
