"""tests/golden_tables.json: the spreadsheet tables and ICS the Python exporters make for two golden events."""
import sys, json, copy, os
sys.path.insert(0, sys.argv[1])
from wt_planner import engine as E, exporters as X
g = json.load(open(os.path.join(os.path.dirname(__file__), "..", "tests", "golden.json")))
out = {}
for case in g[:2] + [c for c in g if c["name"] == "tweaks_and_overrides"]:
    ev = E.normalise(copy.deepcopy(case["input"])); E.auto_assign(ev); res = E.evaluate(ev)
    tables = [[n, rows, w, {f"{r},{c}": s for (r, c), s in st.items()}] for n, rows, w, st in X.build_tables(ev, res)]
    import tempfile; p = os.path.join(tempfile.mkdtemp(), "g.ics"); X.write_ics(p, ev, res)
    ics = [l for l in open(p, newline="").read().split("\r\n") if not l.startswith(("DTSTAMP", "UID:duty", "PRODID"))]
    svg = X.gantt_svg(ev, res)
    out[case["name"]] = {"tables": tables, "ics": ics, "svg_len": len(svg), "svg_rects": svg.count("<rect")}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "tests", "golden_tables.json"), "w"), ensure_ascii=False, default=str)
print("ok")
