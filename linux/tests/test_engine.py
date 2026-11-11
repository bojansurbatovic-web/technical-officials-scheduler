import json
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from wt_planner import engine as E  # noqa: E402
from wt_planner import exporters as X  # noqa: E402

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "wt_planner", "data", "example_q3.wtplan.json")


def q3():
    return X.load_json(EXAMPLE)


def by_name(res, name):
    return next(o for o in res["officials"] if o["name"] == name)


# placeholder officials in the example, by their preferred primary position
HR, CRO, REG, WHEEL, ASST_WHEEL, LAP, BIKE, TECH = "TO 01", "TO 02", "TO 03", "TO 04", "TO 10", "TO 08", "TO 12", "TO 18"


def test_q3_timeline_matches_hand_calculation():
    ev = q3()
    women = next(r for r in ev["races"] if r["name"] == "Elite Women")
    tl = E.race_timeline(women)
    assert E.fmt_hhmm(tl["t1_first"], True) == "10:19:30"
    assert E.fmt_hhmm(tl["t2_first"], True) == "11:20:15"
    assert E.fmt_hhmm(tl["winner"], True) == "11:54:45"
    assert E.fmt_hhmm(tl["lounge_open"]) == "08:45" and E.fmt_hhmm(tl["tz_close"]) == "09:45"
    assert abs(tl["last_finisher"] - (12 * 60 + 5)) < 1.0


def test_q3_plan_has_no_conflicts_and_respects_checker_rules():
    ev = q3()
    E.auto_assign(ev, keep_locked=False)
    res = E.evaluate(ev)
    assert res["n_conflict"] == 0
    # with briefings, rehearsals and protest windows counted, only assistant jobs may stay open
    assert all(u["pos_key"].startswith("asst_") for u in res["unfilled"]), [u["title"] for u in res["unfilled"]]
    assert by_name(res, REG)["secondary"] == []      # registration busy all day
    assert by_name(res, WHEEL)["secondary"] == []      # wheel station busy all day
    assert by_name(res, ASST_WHEEL)["secondary"] == []
    louis = by_name(res, LAP)
    assert not any("Finish" in s for s in louis["secondary"])      # lap auditor not on finish
    assert len(by_name(res, CRO)["secondary"]) >= 2  # CRO used prominently
    assert "Starter" in by_name(res, HR)["secondary"]
    assert res["radios"]["total"] == 23


def test_relay_format_creates_relay_positions():
    ev = E.new_event("Relay", "2026-07-01", races=[E.new_race("mixed_relay", "elite_men", "14:00")], n_officials=16)
    E.auto_assign(ev)
    res = E.evaluate(ev)
    keys = {s["key"] for s in res["slots"]}
    assert "chief_relay_zone" in keys and "asst_relay_zone" in keys
    tl = res["timelines"][ev["races"][0]["id"]]
    assert abs(tl["winner"] - (tl["start"] + 4 * tl["_segments"]["leg"])) < 1e-6
    assert tl["start"] % 1440 == 840


def test_age_group_gets_bike_penalty_boxes_and_no_wheel_station():
    ev = E.new_event("AG", "2026-07-02", races=[E.new_race("standard", "age_group", "08:00")], n_officials=20)
    res = E.evaluate(ev)
    keys = [s["key"] for s in res["slots"]]
    assert keys.count("bike_penalty_box") == 4          # CR 10.8 b: one per 10 km
    assert "chief_wheel_station" not in keys


def test_too_few_officials_reports_unfilled():
    ev = q3()
    ev["officials"] = ev["officials"][:6]
    ev["assignments"] = {}
    E.auto_assign(ev)
    res = E.evaluate(ev)
    assert len(res["unfilled"]) > 10


def test_locked_assignment_is_kept():
    ev = q3()
    key = next(k for k in ev["assignments"] if k.startswith("asst_finish#1|"))
    E.set_assignment(ev, key, TECH, locked=True)
    E.auto_assign(ev, keep_locked=True)
    assert ev["assignments"][key]["official"] == TECH
    res = E.evaluate(ev)
    row = next(r for r in res["rows"] if r["key"] == key)
    assert row["status"] in ("CONFLICT", "TIGHT", "OK")


def test_availability_limits_assignment():
    ev = q3()
    for o in ev["officials"]:
        if o["name"] == BIKE:
            o["available_to"] = "11:00"
            o["primary"] = ""
    ev["assignments"] = {}
    E.auto_assign(ev)
    res = E.evaluate(ev)
    for r in res["rows"]:
        if r["official"] == BIKE:
            assert r["end"] - (r["start"] // 1440) * 1440 <= 11 * 60


def test_disabled_position_disappears():
    ev = q3()
    ev["positions"]["asst_finish"]["enabled"] = False
    res = E.evaluate(ev)
    assert not any(s["key"] == "asst_finish" for s in res["slots"])
    ev["positions"]["asst_finish"] = {"enabled": True, "count": 4}
    res = E.evaluate(ev)
    assert sum(1 for s in res["slots"] if s["key"] == "asst_finish") == 4


def test_shift_moves_window():
    ev = q3()
    race = ev["races"][0]
    tl = E.race_timeline(race)
    s0, _ = E.activity_window("finish_asst", tl, ev["settings"], None)
    race["shifts"] = {"finish_asst": [-10, 0]}
    s1, _ = E.activity_window("finish_asst", tl, ev["settings"], race["shifts"])
    assert s1 == s0 - 10


def test_json_roundtrip_and_minimal_file():
    ev = q3()
    d = tempfile.mkdtemp()
    p = os.path.join(d, "a.wtplan.json")
    X.save_json(p, ev)
    ev2 = X.load_json(p)
    assert len(E.evaluate(ev2)["rows"]) == len(E.evaluate(ev)["rows"])
    p2 = os.path.join(d, "min.json")
    with open(p2, "w") as f:
        json.dump({"races": [{"format": "sprint", "category": "elite_men", "start": "15:00"}],
                   "officials": [{"name": "A"}, {"name": "B"}]}, f)
    ev3 = X.load_json(p2)
    E.auto_assign(ev3)
    assert E.evaluate(ev3)["rows"]


def test_three_races_and_exports():
    ev = q3()
    ev["races"].append(E.new_race("sprint", "junior_women", "15:30", "Junior Women"))
    E.auto_assign(ev)
    res = E.evaluate(ev)
    d = tempfile.mkdtemp()
    X.write_xlsx(os.path.join(d, "a.xlsx"), ev, res)
    X.write_ods(os.path.join(d, "a.ods"), ev, res)
    X.write_ics(os.path.join(d, "a.ics"), ev, res)
    svg = X.gantt_svg(ev, res, mode="positions")
    assert svg.startswith("<svg") and "Junior Women" in svg
    with zipfile.ZipFile(os.path.join(d, "a.ods")) as z:
        first = z.infolist()[0]
        assert first.filename == "mimetype" and first.compress_type == zipfile.ZIP_STORED
    with zipfile.ZipFile(os.path.join(d, "a.xlsx")) as z:
        assert "xl/worksheets/sheet1.xml" in z.namelist()
    try:
        import openpyxl
    except ImportError:
        return
    wb = openpyxl.load_workbook(os.path.join(d, "a.xlsx"))
    assert wb.sheetnames[:2] == ["Assignments", "Officials"]
    assert wb["Assignments"]["A1"].value == "Position"


def multiday_event():
    ev = E.new_event("Three-day event", "2026-06-12")
    r1 = E.new_race("sprint", "elite_women", "10:00", "Elite Women Sprint", date="2026-06-12")
    r2 = E.new_race("sprint", "elite_men", "10:00", "Elite Men Sprint", date="2026-06-13")
    r3 = E.new_race("mixed_relay", "elite_men", "09:00", "Mixed Relay", date="2026-06-14")
    ev["races"] = [r3, r1, r2]          # deliberately unsorted
    ev["officials"] = [E.new_official(f"TO {i + 1:02d}") for i in range(20)]
    for o in ev["officials"][14:]:      # six officials only work the first day
        o["races"] = {r2["id"]: False, r3["id"]: False}
    E.reset_positions(ev)
    E.auto_assign(ev)
    return ev, (r1, r2, r3)


def test_multiday_timeline_and_per_day_jobs():
    ev, (r1, r2, r3) = multiday_event()
    res = E.evaluate(ev)
    assert res["multiday"] and [d.isoformat() for d in res["dates"]] == ["2026-06-11", "2026-06-12", "2026-06-13", "2026-06-14"]
    assert [r["id"] for r in E.races_sorted(ev)] == [r1["id"], r2["id"], r3["id"]]
    t1, t2, t3 = (res["timelines"][r["id"]]["start"] for r in (r1, r2, r3))
    assert t2 - t1 == 1440 and t3 - t1 == 2 * 1440 - 60
    reg = [r for r in res["rows"] if r["pos_key"] == "chief_registration"]
    assert sorted(r["race_id"] for r in reg) == ["day:2026-06-12", "day:2026-06-13", "day:2026-06-14"]
    assert res["fmt"](res["timelines"][r2["id"]]["start"]) == "Sat 13.06. 10:00"


def test_participation_is_respected():
    ev, races = multiday_event()
    res = E.evaluate(ev)
    off = {o["name"]: o for o in ev["officials"]}
    for r in res["rows"]:
        if r["official"]:
            assert all(E.takes_part(off[r["official"]], x) for x in r["races_of"]), (r["title"], r["race"], r["official"])
    # day-1-only officials appear only on day 1
    for name in [f"TO {i:02d}" for i in range(15, 21)]:
        for r in res["rows"]:
            if r["official"] == name:
                assert r["date"] == "2026-06-12"
    assert res["n_conflict"] == 0


def test_assigning_someone_to_a_race_they_do_not_work_is_flagged():
    ev, (r1, r2, r3) = multiday_event()
    key = next(k for k in ev["assignments"] if k.endswith("|" + r2["id"]))
    E.set_assignment(ev, key, "TO 20", locked=True)
    res = E.evaluate(ev)
    row = next(r for r in res["rows"] if r["key"] == key)
    assert row["status"] == "CONFLICT"
    assert any(c["a_label"] == "does not work this race" for c in res["conflicts"])


def test_multiday_exports_have_day_sheets():
    ev, (r1, r2, r3) = multiday_event()
    res = E.evaluate(ev)
    names = [t[0] for t in X.build_tables(ev, res)]
    assert "Participation" in names
    assert sum(1 for n in names if n.startswith("Gantt ")) == len(res["dates"]) >= 4   # day before + 3 race days
    svg2 = X.gantt_svg(ev, res, day="2026-06-13")
    assert "Elite Men Sprint" in svg2 and "Elite Women Sprint" not in svg2
    d = tempfile.mkdtemp()
    X.write_xlsx(os.path.join(d, "m.xlsx"), ev, res)
    X.write_ods(os.path.join(d, "m.ods"), ev, res)
    X.write_ics(os.path.join(d, "m.ics"), ev, res)
    with open(os.path.join(d, "m.ics")) as f:
        txt = f.read()
    assert "DTSTART:20260613T" in txt and "DTSTART:20260614T" in txt
    assert "DTSTART:20260611T160000" in txt          # Elite briefing the day before, 16:00


def test_old_all_keys_are_migrated():
    ev = q3()
    k = next(k for k in ev["assignments"] if "|day:" in k)
    old = dict(ev)
    old["assignments"] = {k.split("|")[0] + "|ALL": ev["assignments"][k]}
    ev2 = E.normalise(json.loads(json.dumps(old)))
    assert k in ev2["assignments"]


# ---------------------------------------------------------------- rules: briefings, jury, protests
def sessions_by_key(ev):
    out = {}
    for se in E.build_sessions(ev):
        out.setdefault(se["key"], []).append(se)
    return out


def test_elite_briefing_is_16_00_day_before_first_competition_day():
    ev = q3()
    first = E.races_sorted(ev)[0]
    br = [se for se in sessions_by_key(ev)["athletes_briefing"] if se["id"].endswith(":elite")][0]
    assert br["date"] == E.race_date(ev, first) - __import__("datetime").timedelta(days=1)
    assert br["start"] == 16 * 60 and br["enabled"]
    assert "td" in br["attendees"] and "head_referee" in br["attendees"]
    chk = sessions_by_key(ev)["briefing_checkin"][0]
    assert chk["start"] < br["start"] and chk["end"] > br["end"]          # check-in before, packets after
    assert not sessions_by_key(ev)["coaches_meeting"][0]["enabled"]        # only "if scheduled"
    assert sessions_by_key(ev)["coaches_meeting"][0]["start"] == 15 * 60   # 1 h before the briefing


def test_jury_meets_after_briefing_before_each_start_and_after_last_finisher():
    ev = q3()
    k = sessions_by_key(ev)
    assert len(k["jury_after_briefing"]) == 1
    ev2 = X.load_json(EXAMPLE.replace("example_q3", "example_multiday"))   # two sprints on one day
    merged = [se for se in E.build_sessions(ev2) if se["key"] == "jury_after_race" and len(se["for_races"]) == 2]
    assert len(merged) == 1 and "1 h before start" in merged[0]["name"]
    assert E.evaluate(ev2)["n_conflict"] == 0
    for r in ev["races"]:
        tl = E.race_timeline(r)
        before = [se for se in k["jury_before_race"] if se["for_races"] == [r["id"]]][0]
        after = [se for se in k["jury_after_race"] if se["for_races"] == [r["id"]]][0]
        assert before["start"] == tl["start"] - 60
        assert after["start"] >= tl["last_finisher"]


def test_head_referee_protest_window_follows_cr_12_4():
    ev = q3()
    res = E.evaluate(ev)
    sign = ev["settings"]["hr_signoff"]
    for r in res["rows"]:
        if r["pos_key"] == "head_referee":
            tl = res["timelines"][r["race_id"]]
            assert abs(r["end"] - (tl["last_finisher"] + sign + 20)) < 1e-6      # 5 + 15 min Elite standard
    ag = E.new_race("standard", "age_group", "08:00")
    assert E.protest_minutes(ag) == 45                                        # 15 + 30 min Age-Group


def test_start_window_warning_eom_2_10_2():
    ev = q3()
    w = E.start_window_warnings(ev)
    assert any("TD approval" in x for x in w)               # 2 h 45 between standard starts
    ev["races"][1]["start"] = "13:00"
    assert not E.start_window_warnings(ev)


def test_sessions_are_counted_for_officials_and_can_be_edited():
    ev = q3()
    res = E.evaluate(ev)
    reg = by_name(res, REG)
    assert any(d["kind"] == "session" and "Briefing check-in" in d["title"] for d in reg["duties"])
    assert any("TO briefing" in d["title"] for d in reg["duties"])
    sid = next(se["id"] for se in E.build_sessions(ev) if se["key"] == "to_meeting")
    ev["sessions"] = {sid: {"enabled": False}}
    res2 = E.evaluate(ev)
    assert not any(d["title"].startswith("TOs' meeting") for d in by_name(res2, REG)["duties"])
    ev["custom_sessions"] = [{"id": "c1", "name": "Welcome dinner", "date": "2026-11-20", "start": "19:00",
                              "end": "21:00", "attendees": ["all_tos"]}]
    res3 = E.evaluate(ev)
    assert all(any(d["title"] == "Welcome dinner" for d in o["duties"]) for o in res3["officials"])
    ev["sessions"] = {next(se["id"] for se in E.build_sessions(ev) if se["id"] == "athletes_briefing:elite"): {"start": "17:00"}}
    assert any("CR 2.7 b(vii)" in x for x in E.start_window_warnings(ev))


def test_relay_briefing_separate_day_and_merged_same_day():
    ev, (r1, r2, r3) = multiday_event()
    k = sessions_by_key(ev)
    ids = {se["id"] for se in k["athletes_briefing"]}
    assert "athletes_briefing:relay" in ids                # relay day after the individual races -> own briefing
    ev2 = E.new_event("same day", "2026-07-01")
    ev2["races"] = [E.new_race("sprint", "elite_women", "10:00"), E.new_race("mixed_relay", "elite_men", "14:00")]
    ids2 = {se["id"] for se in E.build_sessions(ev2) if se["key"] == "athletes_briefing"}
    assert ids2 == {"athletes_briefing:elite"}             # CR 2.7 b(v): may be held together


if __name__ == "__main__":
    import inspect
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and inspect.isfunction(fn):
            fn()
            n += 1
            print("ok ", name)
    print(f"{n} engine tests passed")
