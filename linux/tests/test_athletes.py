"""Athletes' guide (Ubuntu): athlete-only items, correct times, HTML and calendar."""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from wt_planner import athletes as ATH  # noqa: E402
from wt_planner import engine as E  # noqa: E402
from wt_planner import exporters as X  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "wt_planner", "data", "example_q3.wtplan.json")


def setup():
    ev = X.load_json(EX)
    E.auto_assign(ev)
    return ev, E.evaluate(ev)


def test_only_athlete_items():
    ev, res = setup()
    titles = " | ".join(i["title"] for i in ATH.items(ev, res))
    for bad in ("TOs", "Jury", "rehearsal", "drivers", "Medical", "TO briefing", "de-briefing", "Timing", "TV"):
        assert bad not in titles, bad


def test_briefing_day_before_at_16():
    ev, res = setup()
    items = ATH.items(ev, res)
    first = E.races_sorted(ev)[0]
    br = next(i for i in items if i["kind"] == "athletes_briefing")
    assert br["date"] == E.race_date(ev, first) - dt.timedelta(days=1)
    assert E.fmt_hhmm(br["s"] % 1440) == "16:00"
    assert next(i for i in items if i["kind"] == "briefing_checkin")["s"] < br["s"]


def test_race_day_order_and_filter():
    ev, res = setup()
    for r in ev["races"]:
        mine = {i["kind"]: i["s"] for i in ATH.items(ev, res) if i["race_id"] == r["id"]}
        assert mine["lounge_open"] < mine["tz_close"] < mine["start"] < mine["winner"] < mine["protest_close"]
    one = ATH.items(ev, res, ev["races"][1]["id"])
    assert not any(i["race_id"] == ev["races"][0]["id"] for i in one)


def test_html_and_ics():
    ev, res = setup()
    ev["event"]["athletes"] = {"briefing_location": "Hall <A>", "office": "", "notes": "Bring ID"}
    html = ATH.guide_html(ev, res)
    assert html.startswith("<!DOCTYPE html>") and "Hall &lt;A&gt;" in html and "16:00" in html and "Jury meeting" not in html
    ics = ATH.guide_ics(ev, res)
    assert "LOCATION:Hall <A>" in ics and ics.count("BEGIN:VEVENT") == len(ATH.items(ev, res))
    assert [c[0] for c in ATH.course(ev, ev["races"][0])] == ["Swim", "Bike", "Run", "Wheel stations", "Aid stations (run)"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("athletes' guide tests passed")
