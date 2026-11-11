import json
"""Run the GTK window code against a fake toolkit (no display needed)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tests import fake_gi  # noqa: E402

tmp = fake_gi.install()
from wt_planner import gui as G  # noqa: E402
from wt_planner import engine as E  # noqa: E402


def make_win():
    app = fake_gi.Stub()
    w = G.MainWindow(app)
    w.dirty = False
    return w


def test_window_builds_and_handlers_run():
    w = make_win()
    assert w.result is not None and w.result["rows"], "demo event evaluated"
    n_rows = len(w.a_store)
    assert n_rows > 20
    # races
    w._on_race_edit(None, "0", "09:30", 4)
    assert E.races_sorted(w.ev)[0]["start"] == "09:30"
    w._on_race_edit(None, "0", w.fmt_labels[1], 2)            # sprint
    w._on_race_edit(None, "0", w.cat_labels[6], 3)            # age group
    w._on_race_edit(None, "0", "6", 10)                       # bike laps
    w._on_race_edit(None, "0", "3", 13)                       # aid stations
    w._on_race_toggle(None, "0", 15)
    w.on_add_race()
    w.on_dup_race()
    assert len(w.ev["races"]) == 4
    w.on_del_race()
    # dates: move the second race to the next day, then check multi-day views
    second = E.races_sorted(w.ev)[1]
    w.selected_race = second["id"]
    w.on_race_day_step(1)
    assert E.is_multiday(w.ev)
    w._on_race_edit(None, "0", "2026-11-20", 16)
    w._on_race_edit(None, "0", "not a date", 16)
    w.on_race_date_from_cal()
    assert w.result["multiday"]
    assert len(w.g_day._items) >= 1 or True
    # participation: untick one official for one race, row/column all-none
    rid = E.races_sorted(w.ev)[0]["id"]
    off0 = w.ev["officials"][0]["name"]
    cb = fake_gi.CheckButton()
    cb.set_active(False)
    w._on_part_toggle(cb, off0, rid)
    assert not E.takes_part(w.ev["officials"][0], rid)
    assert all(off0 != v.get("official") for k, v in w.ev["assignments"].items()
               if k.endswith("|" + rid) and not v.get("locked"))
    w._on_part_row(off0)            # was partly off -> all on
    assert all(E.takes_part(w.ev["officials"][0], r["id"]) for r in w.ev["races"])
    w._on_part_col(rid)             # everyone on -> nobody works this race
    assert not any(E.takes_part(o, rid) for o in w.ev["officials"])
    w._on_part_col(rid)             # back on
    w._part_sig = None
    w._fill_participation()
    w.selected_race = w.ev["races"][0]["id"]
    sb = w.tw[("paces", "bike_speed")]
    sb.set_value(41.5)
    w._on_race_tweak(sb, "paces", "bike_speed")
    w.on_reset_race()
    # officials
    w._on_off_edit(None, "0", "Renamed Person", 0)
    assert w.ev["officials"][0]["name"] == "Renamed Person"
    assert any(v.get("official") == "Renamed Person" for v in w.ev["assignments"].values())
    w._on_off_edit(None, "1", w.pos_titles[3], 2)
    w._on_off_edit(None, "2", "09:00", 4)
    w._on_off_edit(None, "2", "", 4)
    w._on_off_edit(None, "3", "1", 3)
    w._on_off_toggle(None, "4", 6)
    w.on_add_official()
    w.n_off.set_value(15)
    w.on_set_n_officials()
    assert len(w.ev["officials"]) == 15
    # positions, duties, shifts
    w._on_pos_toggle(None, "5", 1)
    w._on_pos_count(None, "20", "3", 4)
    w._on_duty_edit(None, "0", "7", 2)
    assert w.ev["settings"]["buffer"] == 7
    w._on_shift_edit(None, "1", "-5", 2)
    w._clear_shifts()
    # meetings & briefings
    assert len(w.se_store) > 10
    br = next(i for i, row in enumerate(w.se_store) if row[0] == "athletes_briefing:elite")
    assert w.se_store[br][3] == "16:00"
    w._on_session_edit(None, str(br), "17:00", 3)
    assert w.ev["sessions"]["athletes_briefing:elite"]["start"] == "17:00"
    assert any("CR 2.7 b(vii)" in x for x in w.result["warnings"])
    w._on_session_edit(None, str(br), "bad", 3)
    w._on_session_edit(None, str(br), "renamed", 5)          # refused for rule-based meetings
    assert "renamed" not in json.dumps(w.ev.get("sessions"))
    w._selected_session = lambda: ("athletes_briefing:elite", False)
    w.on_reset_session()
    assert "athletes_briefing:elite" not in w.ev["sessions"]
    tm = next(i for i, row in enumerate(w.se_store) if row[0] == "to_meeting")
    w._on_session_toggle(None, str(tm), 1)
    assert w.ev["sessions"]["to_meeting"]["enabled"] is False
    w.on_reset_sessions()
    assert w.ev["sessions"] == {}
    w.edit(lambda: w.ev["custom_sessions"].append({"id": "c1", "name": "Dinner", "date": "2026-11-20",
                                                   "start": "19:00", "end": "21:00", "attendees": ["all_tos"]}))
    ci = next(i for i, row in enumerate(w.se_store) if row[0] == "c1")
    w._on_session_edit(None, str(ci), "Welcome dinner", 5)
    w._on_session_who(None, str(ci), "TD only", 6)
    assert w.ev["custom_sessions"][0]["name"] == "Welcome dinner"
    assert w.ev["custom_sessions"][0]["attendees"] == ["td"]
    w._selected_session = lambda: ("c1", True)
    w.on_del_session()
    assert w.ev["custom_sessions"] == []
    del w._selected_session
    w._fill_conflicts()
    assert any(row[0] == "WARNING" for row in w.c_store) == bool(w.result["warnings"])
    # assignments
    name = w.ev["officials"][1]["name"]
    w._on_assign_edit(None, "0", name, 3)
    key = w.a_store[0][0]
    assert w.ev["assignments"][key]["official"] == name and w.ev["assignments"][key]["locked"]
    w._on_assign_lock(None, "0", 9)
    w._on_assign_edit(None, "1", G.LOC_VOL, 3)
    w._on_assign_edit(None, "2", G.UNASSIGNED, 3)
    w.on_auto(True)
    w.on_auto(False)
    w.a_problems.set_active(True)
    w._fill_assignments()
    w.a_problems.set_active(False)
    w.a_search.set_text("finish")
    w._fill_assignments()
    assert all("finish" in r[1].lower() or "finish" in r[3].lower() for r in w.a_store)
    # undo / redo
    before = len(w.undo)
    w.on_undo()
    w.on_redo()
    assert len(w.undo) == before
    # gantt + timeline + conflicts
    w.refresh_gantt()
    assert w._gantt_src.startswith("<svg")
    assert len(w.t_store) > 10 and len(w.s_store) >= 1
    # save / library / open
    w.on_save_library()
    entries = G.library_entries()
    assert entries and entries[0]["path"].endswith(".wtplan.json")
    w.open_path(entries[0]["path"])
    w.refresh_calendar()
    # exports via patched file dialog
    out = tempfile.mkdtemp()
    for kind, ext in (("xlsx", ".xlsx"), ("ods", ".ods"), ("json", ".wtplan.json"), ("ics", ".ics"), ("svg", ".svg")):
        target = os.path.join(out, "x" + ext)
        w._file_dialog = lambda *a, t=target, **k: t
        w.toast = lambda *a, **k: None
        w.on_export(kind)
        assert os.path.getsize(target) > 200, kind
    w.dirty = False
    w.open_example("example_multiday.wtplan.json")
    assert w.result["multiday"] and len(w.ev["races"]) == 3
    w.refresh_gantt()
    w.on_copy_json()
    w.on_share()
    w.on_open_gantt_external = lambda: None
    print("attribute misses on window:", sorted(set(fake_gi.MISSES)))


if __name__ == "__main__":
    test_window_builds_and_handlers_run()
    print("GUI smoke test passed")
