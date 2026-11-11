"""Exports without third-party libraries: XLSX, ODS, JSON, ICS, SVG Gantt."""
import datetime as _dt
import html
import json
import zipfile

from . import engine as E
from . import reference as ref

SESSION_COLOUR = "#7B4FA0"     # meetings, briefings, rehearsals
RACE_COLOURS = ["#3B7DD8", "#E8743B", "#2E9E5B", "#8E5BD0", "#C9A227", "#D04F7A", "#4BA3A3", "#7A7A7A"]
STATUS_COLOURS = {"OK": "#C6EFCE", "TIGHT": "#FFEB9C", "CONFLICT": "#FFC7CE", "UNFILLED": "#F4B183",
                  "LOC / volunteer": "#DDEBF7"}


def _lighten(hexcol, f=0.55):
    h = hexcol.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r, g, b = (int(c + (255 - c) * f) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def race_colour(ev, race_id):
    if race_id == "session":
        return SESSION_COLOUR
    if E.is_day_key(race_id):
        return "#5A5A5A"
    ids = [r["id"] for r in E.races_sorted(ev)]
    if race_id in ids:
        return RACE_COLOURS[ids.index(race_id) % len(RACE_COLOURS)]
    return "#5A5A5A"


# =============================================================== tables (shared by XLSX/ODS)
def build_tables(ev, result=None):
    """Return list of sheets: (name, rows, widths, styles) where styles is {(r, c): style}."""
    res = result or E.evaluate(ev)
    sheets = []
    e = ev["event"]
    fmt = res["fmt"]
    race_ids = [x["id"] for x in E.races_sorted(ev)]

    # --- Assignments
    rows = [["Position", "Race", "Name and surname", "Role", "From", "To", "Status", "Locked", "TOC / CR"]]
    styles = {}
    for r in res["rows"]:
        rows.append([r["title"], r["race"], r["official"] or "—", r["role"] or "",
                     fmt(r["start"]), fmt(r["end"]), r["status"], "yes" if r["locked"] else "", r["toc"]])
        styles[(len(rows) - 1, 6)] = "st_" + r["status"]
    tw = 16 if res["multiday"] else 8
    sheets.append(("Assignments", rows, [40, 26, 24, 11, tw, tw, 14, 8, 18], styles))

    # --- Officials (one row per person)
    rows = [["Name and surname", "Country", "Primary position", "Secondary position(s)", "Busy (h)", "Radio", "Conflicts"]]
    styles = {}
    offmap = {o["name"]: o for o in ev["officials"]}
    for o in res["officials"]:
        rows.append([o["name"], o["country"], o["primary"] or "—", "; ".join(o["secondary"]) or "—",
                     round(o["busy_min"] / 60.0, 1), "yes" if offmap.get(o["name"], {}).get("radio", True) else "no",
                     o["conflicts"]])
        if o["conflicts"]:
            styles[(len(rows) - 1, 6)] = "st_CONFLICT"
    rows.append([])
    rows.append(["World Triathlon officials (not TOs)", "", "", "", "", "", ""])
    styles[(len(rows) - 1, 0)] = "bold"
    rows.append(["Technical Delegate", "", e.get("td") or "—", "Chair of the Competition Jury", "", "yes" if e.get("td") else "", ""])
    rows.append(["Medical Delegate", "", e.get("md") or "—", "", "", "yes" if e.get("md") else "", ""])
    for j, n in enumerate(e.get("jury", []), 2):
        rows.append([f"Competition Jury – member {j}", "", n or "to be appointed by TD", "not a TO, coach or athlete (CR 12.6)", "", "", ""])
    rows.append([])
    rd = res["radios"]
    rows.append(["Radios (TO talk group)", "", "", "", "", "", ""])
    styles[(len(rows) - 1, 0)] = "bold"
    rows.append(["Personal radios", rd["personal"], "one per TO + TD + MD", "", "", "", ""])
    rows.append(["VCC base radio", rd["vcc"], "EOM 6.6.2 a", "", "", "", ""])
    rows.append(["Spares", rd["spare"], f"{e.get('spare_pct', 10)} % rounded up", "", "", "", ""])
    rows.append(["TOTAL", rd["total"], "EOM: min. 12, TO equipment list 25", "", "", "", ""])
    styles[(len(rows) - 1, 0)] = "bold"
    sheets.append(("Officials", rows, [30, 10, 34, 60, 9, 7, 10], styles))

    # --- Participation (who works which race)
    races = E.races_sorted(ev)
    rows = [["Name and surname"] + [f"{r['name']} ({fmt(res['timelines'][r['id']]['start'])})" for r in races]]
    styles = {}
    for o in ev["officials"]:
        rows.append([o["name"]] + ["✓" if E.takes_part(o, r["id"]) else "—" for r in races])
        for ci, r in enumerate(races, 1):
            styles[(len(rows) - 1, ci)] = "st_OK" if E.takes_part(o, r["id"]) else "default"
    rows.append(["Officials per race"] + [sum(1 for o in ev["officials"] if E.takes_part(o, r["id"])) for r in races])
    styles[(len(rows) - 1, 0)] = "bold"
    sheets.append(("Participation", rows, [26] + [24] * len(races), styles))

    # --- Personal schedules
    rows = [["Name and surname", "From", "To", "Position", "Race", "Duty", "Role", "Status"]]
    styles = {}
    for o in res["officials"] + _wt_people(res):
        for d in o["duties"]:
            for s, en, label, b, _a in sorted(d["windows"]):
                rows.append([o["name"], fmt(s), fmt(en), d["title"], d["race"], label + ("" if b else " (non-blocking)"),
                             d["role"], d["status"]])
                styles[(len(rows) - 1, 7)] = "st_" + d["status"]
    sheets.append(("Personal schedules", rows, [24, tw, tw, 38, 24, 40, 11, 12], styles))

    # --- Race timeline
    rows = [["Time", "Race", "Milestone"]]
    styles = {}
    for m in E.run_sheet(ev, res):
        rows.append([fmt(m["time"]), m["race"], m["item"]])
        if m["key"] == "start":
            styles[(len(rows) - 1, 2)] = "bold"
    rows.append([])
    rows.append(["Race", "Format", "Category", "Start", "Swim", "T1", "Bike", "T2", "Run", "Winner", "Last finisher"])
    styles.update({(len(rows) - 1, c): "header" for c in range(11)})
    for r in E.races_sorted(ev):
        tl = res["timelines"][r["id"]]
        sg = tl["_segments"]
        rows.append([r["name"], ref.FORMATS[r["format"]]["label"], ref.CATEGORIES[r["category"]]["label"], fmt(tl["start"]),
                     E.fmt_dur(sg["swim"]), E.fmt_dur(sg["t1"]), E.fmt_dur(sg["bike"]), E.fmt_dur(sg["t2"]),
                     E.fmt_dur(sg["run"]), fmt(tl["winner"]), fmt(tl["last_finisher"])])
    sheets.append(("Race timeline", rows, [26, 34, 26, tw, 8, 7, 8, 7, 8, tw, 14], styles))

    # --- Meetings & briefings (rule-based obligations)
    rows = [["Date", "From", "To", "Meeting / briefing", "Who must attend", "People", "Rule / reference", "In plan"]]
    styles = {}
    for se in sorted(res.get("sessions", []), key=lambda x: (x["s"], x["e"])):
        rows.append([E.day_label(se["date"]) + " " + se["date"].isoformat(), E.fmt_hhmm(se["start"]), E.fmt_hhmm(se["end"]),
                     se["name"] + (" (edited)" if se.get("edited") else ""), E.attendee_label(se["attendees"]),
                     ", ".join(se.get("people", [])) or "—", se["ref"], "yes" if se["enabled"] else "no (not scheduled)"])
        styles[(len(rows) - 1, 7)] = "st_OK" if se["enabled"] else "default"
        if se["key"] == "athletes_briefing" and se["enabled"]:
            styles[(len(rows) - 1, 3)] = "bold"
    sheets.append(("Meetings & briefings", rows, [18, 7, 7, 42, 46, 60, 60, 16], styles))

    # --- Gantt grid (5-minute cells), one sheet per event day
    base = E.base_date(ev)
    for day in res["dates"]:
        lo = (day - base).days * 1440
        t0, t1 = _span(res, lo)
        step = 5
        times = list(range(int(t0), int(t1) + step, step))
        header = ["Name and surname", "Primary"] + [E.fmt_hhmm(t - lo) for t in times]
        rows = [header]
        styles = {}
        for o in res["officials"] + _wt_people(res):
            row = [o["name"], o.get("primary") or o.get("role", "")] + [""] * len(times)
            for d in o["duties"]:
                for s, en, _l, b, _a in d["windows"]:
                    if not b or en <= t0 or s >= t1 + step:
                        continue
                    for ci, t in enumerate(times):
                        if t + step > s and t < en:
                            idx = 2 + ci
                            rid = d["race_id"]
                            if rid == "session":
                                st = "g_sess"
                            elif E.is_day_key(rid) or rid not in race_ids:
                                st = "g_all"
                            else:
                                st = f"g{race_ids.index(rid) % len(RACE_COLOURS)}"
                            if d["role"] == "Secondary":
                                st += "s"
                            if d["status"] in ("CONFLICT",):
                                st = "st_CONFLICT"
                            styles[(len(rows), idx)] = st
                            row[idx] = "S" if d["role"] == "Secondary" else ("M" if rid == "session" else "")
            rows.append(row)
        widths = [24, 26] + [3] * len(times)
        sheets.append(("Gantt " + E.day_label(day) if res["multiday"] else "Gantt", rows, widths, styles))

    # --- Conflicts
    rows = [["Level", "Name and surname", "Position A", "Duty A", "Time A", "Position B", "Duty B", "Time B", "Gap (min)"]]
    styles = {}
    for c in res["conflicts"]:
        rows.append([c["level"], c["official"], c["a"], c["a_label"], c["a_time"], c["b"], c["b_label"], c["b_time"],
                     "" if c["gap"] is None else c["gap"]])
        styles[(len(rows) - 1, 0)] = "st_" + c["level"]
    for w in res.get("warnings", []):
        rows.append(["WARNING", "", w, "", "", "", "", "", ""])
        styles[(len(rows) - 1, 0)] = "st_TIGHT"
    for u in res["unfilled"]:
        rows.append(["UNFILLED", "", u["title"], "", f"{fmt(u['start'])}–{E.fmt_hhmm(u['end'] % 1440)}", u["race"], "", "", ""])
        styles[(len(rows) - 1, 0)] = "st_UNFILLED"
    if len(rows) == 1:
        rows.append(["OK", "No conflicts and nothing unfilled", "", "", "", "", "", "", ""])
        styles[(1, 0)] = "st_OK"
    sheets.append(("Conflicts", rows, [12, 24, 36, 30, 13, 36, 30, 13, 9], styles))

    # --- Settings (inputs, so the file documents itself)
    rows = [["Event", e.get("name", "")], ["Venue", e.get("venue", "")],
            ["Date(s)", ", ".join(d.isoformat() for d in res["dates"])], []]
    rows.append(["Duty parameter", "Minutes", "Source"])
    styles = {(4, 0): "header", (4, 1): "header", (4, 2): "header"}
    for k, _v, label, src in ref.DUTY_DEFAULTS:
        rows.append([label, ev["settings"].get(k), src])
    rows.append([])
    for line in ref.REFERENCES.strip().splitlines():
        rows.append([line])
    sheets.append(("Settings & references", rows, [60, 10, 50], styles))
    return sheets


def _wt_people(res):
    """TD / MD / Jury members with their meeting obligations (only if named)."""
    return [w for w in res.get("wt_officials", []) if w["duties"]]


def _span(res, day_lo=None):
    """Time range to draw; with day_lo only that event day (minutes day_lo .. day_lo+1440)."""
    def inside(t):
        return day_lo is None or day_lo <= t < day_lo + 1440
    vals = []
    for r in res["rows"]:
        if r["start"] is not None and inside(r["start"]):
            vals += [r["start"], r["end"]]
    for tl in res["timelines"].values():
        if inside(tl["start"]):
            vals += [tl["lounge_open"], tl["last_finisher"]]
    for se in res.get("sessions", []):
        if se["enabled"] and inside(se["s"]):
            vals += [se["s"], se["e"]]
    if not vals:
        lo = day_lo or 0
        return lo + 480, lo + 720
    t0 = (int(min(vals)) // 15) * 15
    t1 = ((int(max(vals)) + 14) // 15) * 15
    return t0, t1


def _style_table(ev):
    """Style name -> (fill, bold, font colour)."""
    st = {"default": (None, False, None), "header": ("#1F3864", True, "#FFFFFF"), "bold": (None, True, None)}
    for k, c in STATUS_COLOURS.items():
        st["st_" + k] = (c, True, None)
    st["st_"] = (None, False, None)
    for i, c in enumerate(RACE_COLOURS):
        st[f"g{i}"] = (c, False, "#FFFFFF")
        st[f"g{i}s"] = (_lighten(c), False, "#000000")
    st["g_all"] = ("#5A5A5A", False, "#FFFFFF")
    st["g_alls"] = ("#AAAAAA", False, "#000000")
    st["g_sess"] = (SESSION_COLOUR, False, "#FFFFFF")
    st["g_sesss"] = (_lighten(SESSION_COLOUR), False, "#000000")
    return st


# =============================================================== XLSX
def _col(n):
    s = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _x(s):
    return html.escape(str(s), quote=True)


def write_xlsx(path, ev, result=None):
    sheets = build_tables(ev, result)
    stdef = _style_table(ev)
    names = list(stdef)
    fills = ['<fill><patternFill patternType="none"/></fill>', '<fill><patternFill patternType="gray125"/></fill>']
    fonts = ['<font><sz val="10"/><name val="Arial"/></font>']
    xfs = []
    for n in names:
        fill, bold, colour = stdef[n]
        fi = 0
        if fill:
            fills.append(f'<fill><patternFill patternType="solid"><fgColor rgb="FF{fill[1:]}"/><bgColor indexed="64"/></patternFill></fill>')
            fi = len(fills) - 1
        fo = 0
        if bold or colour:
            b_tag = "<b/>" if bold else ""
            c_tag = f'<color rgb="FF{colour[1:]}"/>' if colour else ""
            fonts.append(f'<font>{b_tag}<sz val="10"/>{c_tag}<name val="Arial"/></font>')
            fo = len(fonts) - 1
        xfs.append(f'<xf numFmtId="0" fontId="{fo}" fillId="{fi}" borderId="0" xfId="0" applyFont="1" applyFill="1">'
                   f'<alignment vertical="top" wrapText="0"/></xf>')
    style_idx = {n: i for i, n in enumerate(names)}
    styles_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                  f'<fonts count="{len(fonts)}">{"".join(fonts)}</fonts>'
                  f'<fills count="{len(fills)}">{"".join(fills)}</fills>'
                  '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
                  '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
                  f'<cellXfs count="{len(xfs)}">{"".join(xfs)}</cellXfs>'
                  '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
                  '</styleSheet>')
    sheet_xml = []
    for name, rows, widths, styles in sheets:
        cols = "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths))
        out = []
        for ri, row in enumerate(rows):
            cells = []
            for ci, v in enumerate(row):
                stn = styles.get((ri, ci), "header" if ri == 0 else "default")
                s = style_idx.get(stn, 0)
                ref_ = f"{_col(ci)}{ri + 1}"
                if v is None or v == "":
                    if s:
                        cells.append(f'<c r="{ref_}" s="{s}"/>')
                    continue
                if isinstance(v, bool):
                    v = "yes" if v else "no"
                if isinstance(v, (int, float)):
                    cells.append(f'<c r="{ref_}" s="{s}"><v>{v}</v></c>')
                else:
                    cells.append(f'<c r="{ref_}" s="{s}" t="inlineStr"><is><t xml:space="preserve">{_x(v)}</t></is></c>')
            out.append(f'<row r="{ri + 1}">{"".join(cells)}</row>')
        freeze = ('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
                  '</sheetView></sheetViews>')
        if name.startswith("Gantt"):
            freeze = ('<sheetViews><sheetView workbookViewId="0"><pane xSplit="2" ySplit="1" topLeftCell="C2" activePane="bottomRight" state="frozen"/>'
                      '</sheetView></sheetViews>')
        sheet_xml.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                         f'{freeze}<cols>{cols}</cols><sheetData>{"".join(out)}</sheetData></worksheet>')
    wb = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
          + "".join(f'<sheet name="{_x(n[:31])}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, (n, *_r) in enumerate(sheets))
          + '</sheets></workbook>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                      f'Target="worksheets/sheet{i + 1}.xml"/>' for i in range(len(sheets)))
            + f'<Relationship Id="rId{len(sheets) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="xml" ContentType="application/xml"/>'
              '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
              '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
              + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
                        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(len(sheets)))
              + '</Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                 '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/styles.xml", styles_xml)
        for i, sx in enumerate(sheet_xml):
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", sx)
    return path


# =============================================================== ODS
def write_ods(path, ev, result=None):
    sheets = build_tables(ev, result)
    stdef = _style_table(ev)
    auto = []
    for n, (fill, bold, colour) in stdef.items():
        props = f'<style:table-cell-properties fo:background-color="{fill}"/>' if fill else ""
        tprops = ""
        if bold or colour:
            tprops = ('<style:text-properties' + (' fo:font-weight="bold"' if bold else "")
                      + (f' fo:color="{colour}"' if colour else "") + "/>")
        auto.append(f'<style:style style:name="c_{n}" style:family="table-cell">{props}{tprops}</style:style>')
    colstyles = {}
    tables = []
    for name, rows, widths, styles in sheets:
        cols = []
        for w in widths:
            cm = round(max(0.6, w * 0.19), 2)
            sn = f"co{str(cm).replace('.', '_')}"
            colstyles[sn] = cm
            cols.append(f'<table:table-column table:style-name="{sn}"/>')
        trs = []
        for ri, row in enumerate(rows):
            tds = []
            for ci, v in enumerate(row):
                stn = styles.get((ri, ci), "header" if ri == 0 else "default")
                sattr = f' table:style-name="c_{stn}"' if stn != "default" else ""
                if v is None or v == "":
                    tds.append(f"<table:table-cell{sattr}/>")
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    tds.append(f'<table:table-cell{sattr} office:value-type="float" office:value="{v}"><text:p>{v}</text:p></table:table-cell>')
                else:
                    tds.append(f'<table:table-cell{sattr} office:value-type="string"><text:p>{_x(v)}</text:p></table:table-cell>')
            trs.append(f"<table:table-row>{''.join(tds) or '<table:table-cell/>'}</table:table-row>")
        tables.append(f'<table:table table:name="{_x(name[:31])}">{"".join(cols)}{"".join(trs)}</table:table>')
    colxml = "".join(f'<style:style style:name="{sn}" style:family="table-column">'
                     f'<style:table-column-properties style:column-width="{cm}cm"/></style:style>' for sn, cm in colstyles.items())
    ns = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
          'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
          'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
          'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
          'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" '
          'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"')
    content = (f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {ns} office:version="1.2">'
               '<office:font-face-decls/>'
               f'<office:automatic-styles>{colxml}{"".join(auto)}</office:automatic-styles>'
               f'<office:body><office:spreadsheet>{"".join(tables)}</office:spreadsheet></office:body></office:document-content>')
    styles = (f'<?xml version="1.0" encoding="UTF-8"?><office:document-styles {ns} office:version="1.2">'
              '<office:styles><style:default-style style:family="table-cell">'
              '<style:text-properties style:font-name="Arial" fo:font-size="10pt"/></style:default-style></office:styles>'
              '</office:document-styles>')
    meta = ('<?xml version="1.0" encoding="UTF-8"?><office:document-meta '
            'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" office:version="1.2">'
            f'<office:meta><meta:generator>{ref.APP_NAME} {ref.APP_VERSION}</meta:generator></office:meta></office:document-meta>')
    manifest = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">'
                '<manifest:file-entry manifest:full-path="/" manifest:version="1.2" '
                'manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>'
                '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
                '<manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>'
                '<manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>'
                '</manifest:manifest>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.oasis.opendocument.spreadsheet",
                   compress_type=zipfile.ZIP_STORED)
        z.writestr("content.xml", content, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("styles.xml", styles, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("meta.xml", meta, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("META-INF/manifest.xml", manifest, compress_type=zipfile.ZIP_DEFLATED)
    return path


# =============================================================== JSON
def to_json(ev):
    clean = {k: v for k, v in ev.items() if not k.startswith("_")}
    clean["_primary"] = ev.get("_primary", {})
    return json.dumps(clean, indent=2, ensure_ascii=False)


def save_json(path, ev):
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_json(ev))
    return path


def load_json(path):
    with open(path, encoding="utf-8") as f:
        ev = json.load(f)
    if not isinstance(ev, dict) or "races" not in ev:
        raise ValueError("Not a Technical Officials Scheduler file (no 'races').")
    return E.normalise(ev)


# =============================================================== ICS
def _ics_text(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def write_ics(path, ev, result=None, include_duties=True):
    res = result or E.evaluate(ev)
    d = E.base_date(ev)
    date = d.isoformat()
    fmt = res["fmt"]
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def dt(minutes):
        base = _dt.datetime.combine(d, _dt.time(0, 0)) + _dt.timedelta(minutes=round(minutes))
        return base.strftime("%Y%m%dT%H%M%S")

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{ref.APP_NAME}//{ref.APP_VERSION}//EN", "CALSCALE:GREGORIAN"]
    n = 0
    for r in E.races_sorted(ev):
        tl = res["timelines"][r["id"]]
        n += 1
        lines += ["BEGIN:VEVENT", f"UID:race-{r['id']}-{date}@wtplanner", f"DTSTAMP:{stamp}",
                  f"DTSTART:{dt(tl['lounge_open'])}", f"DTEND:{dt(tl['medal'] + 15)}",
                  f"SUMMARY:{_ics_text(r['name'] + ' – start ' + fmt(tl['start']))}",
                  f"LOCATION:{_ics_text(ev['event'].get('venue', ''))}",
                  f"DESCRIPTION:{_ics_text(ref.FORMATS[r['format']]['label'] + chr(10) + 'Winner ≈' + fmt(tl['winner']) + ', last finisher ≈' + fmt(tl['last_finisher']))}",
                  "END:VEVENT"]
    for se in res.get("sessions", []):
        if not se["enabled"]:
            continue
        n += 1
        lines += ["BEGIN:VEVENT", f"UID:session-{_ics_text(se['id'])}-{date}@wtplanner", f"DTSTAMP:{stamp}",
                  f"DTSTART:{dt(se['s'])}", f"DTEND:{dt(se['e'])}", f"SUMMARY:{_ics_text(se['name'])}",
                  f"LOCATION:{_ics_text(ev['event'].get('venue', ''))}",
                  f"DESCRIPTION:{_ics_text('Attend: ' + E.attendee_label(se['attendees']) + chr(10) + ', '.join(se.get('people', [])) + chr(10) + se['ref'])}",
                  "CATEGORIES:Meetings & briefings", "END:VEVENT"]
    if include_duties:
        for o in res["officials"] + _wt_people(res):
            for duty in o["duties"]:
                if duty.get("kind") == "session":
                    continue                     # listed once above, with everyone who attends
                for s, e, label, b, _a in duty["windows"]:
                    if not b:
                        continue
                    n += 1
                    lines += ["BEGIN:VEVENT", f"UID:duty-{n}-{abs(hash((o['name'], duty['key'], s)))}@wtplanner",
                              f"DTSTAMP:{stamp}", f"DTSTART:{dt(s)}", f"DTEND:{dt(e)}",
                              f"SUMMARY:{_ics_text(o['name'] + ': ' + duty['title'])}",
                              f"DESCRIPTION:{_ics_text(label + ' · ' + duty['race'] + ' · ' + duty['role'])}",
                              f"CATEGORIES:{_ics_text(o['name'])}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")
    return path


# =============================================================== SVG Gantt
def gantt_svg(ev, result=None, mode="officials", px_per_min=4.0, dark=False, day=None):
    """Gantt for one event day (default: first day)."""
    res = result or E.evaluate(ev)
    if isinstance(day, str):
        day = E.parse_date(day)
    if day not in res["dates"]:
        rd = E.race_dates(ev)
        day = rd[0] if rd else res["dates"][0]      # default: first competition day
    lo = (day - E.base_date(ev)).days * 1440
    on_day = lambda w: lo <= w[0] < lo + 1440  # noqa: E731
    t0, t1 = _span(res, lo)
    left, top, row_h, bar_h = 260, 70, 26, 16
    fg, bg, grid, sub = ("#E8E8E8", "#1E1E1E", "#3A3A3A", "#AAAAAA") if dark else ("#1A1A1A", "#FFFFFF", "#E2E2E2", "#666666")
    if mode == "officials":
        rows = [(o["name"], o.get("primary") or o.get("role", ""), [(d, w) for d in o["duties"] for w in d["windows"] if on_day(w)])
                for o in res["officials"] + _wt_people(res)]
        unf = [(u, w) for u in res["unfilled"] for w in u["windows"] if on_day(w)]
        if unf:
            rows.append(("UNFILLED", "needs a TO or LOC volunteer", unf))
    else:
        by = {}
        for r in res["rows"]:
            by.setdefault(r["title"], []).extend((r, w) for w in r["windows"] if on_day(w))
        rows = [(t, "", items) for t, items in by.items()]
        for se in res.get("sessions", []):
            if se["enabled"] and lo <= se["s"] < lo + 1440:
                d = {"title": se["name"], "race_id": "session", "race": "Meetings & briefings", "role": "Obligation",
                     "status": "", "official": f"{len(se.get('people', []))} people"}
                rows.append((se["name"], "", [(d, (se["s"], se["e"], se["name"], True, "session"))]))
    races = [r for r in E.races_sorted(ev) if lo <= res["timelines"][r["id"]]["start"] < lo + 1440]
    width = left + int((t1 - t0) * px_per_min) + 40
    height = top + row_h * (len(rows) + 1) + 30 + 22 * ((len(races) + 3) // 4 + 1)
    X = lambda t: left + (t - t0) * px_per_min
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
         f'font-family="Ubuntu, Arial, sans-serif" font-size="12">',
         f'<rect width="100%" height="100%" fill="{bg}"/>',
         f'<text x="12" y="24" font-size="16" font-weight="bold" fill="{fg}">{_x(ev["event"].get("name", ""))} – '
         f'{"officials" if mode == "officials" else "positions"} Gantt</text>',
         f'<text x="12" y="44" fill="{sub}">{_x(E.day_label(day) + " " + day.isoformat())}  {_x(ev["event"].get("venue", ""))}  '
         f'· solid = primary, light = secondary, red outline = conflict</text>']
    t = t0
    while t <= t1:
        x = X(t)
        major = t % 60 == 0
        o.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{top + row_h * len(rows)}" stroke="{grid}" '
                 f'stroke-width="{1.2 if major else 0.6}"/>')
        if t % 30 == 0:
            o.append(f'<text x="{x:.1f}" y="{top - 12}" text-anchor="middle" fill="{fg if major else sub}" '
                     f'font-weight="{"bold" if major else "normal"}">{E.fmt_hhmm(t - lo)}</text>')
        t += 15
    for r in races:
        tl = res["timelines"][r["id"]]
        c = race_colour(ev, r["id"])
        x = X(tl["start"])
        o.append(f'<line x1="{x:.1f}" y1="{top - 6}" x2="{x:.1f}" y2="{top + row_h * len(rows)}" stroke="{c}" '
                 f'stroke-width="2" stroke-dasharray="5,4"/>')
    for i, (label, subl, items) in enumerate(rows):
        y = top + i * row_h
        if i % 2 == 0:
            o.append(f'<rect x="0" y="{y}" width="{width}" height="{row_h}" fill="{fg}" opacity="0.04"/>')
        o.append(f'<text x="12" y="{y + 17}" fill="{"#C00000" if label == "UNFILLED" else fg}" font-weight="bold">{_x(label[:30])}</text>')
        if subl:
            o.append(f'<text x="250" y="{y + 17}" text-anchor="end" fill="{sub}" font-size="10">{_x(subl[:26])}</text>')
        for d, (s, e, wlabel, blocking, _a) in items:
            c = race_colour(ev, d["race_id"])
            secondary = d.get("role") == "Secondary"
            fill = _lighten(c) if secondary else c
            if not blocking:
                fill = "none"
            stroke = "#C00000" if d.get("status") == "CONFLICT" else ("#C9A227" if d.get("status") == "TIGHT" else c)
            sw = 2.5 if d.get("status") in ("CONFLICT", "TIGHT") else 1
            if not blocking:
                stroke, sw = c, 1
            dash = ' stroke-dasharray="3,3"' if not blocking else ""
            xs, xe = X(s), max(X(e), X(s) + 2)
            title = f"{d['title']} · {wlabel} · {d['race']} · {E.fmt_hhmm(s - lo)}–{E.fmt_hhmm(e - lo)}"
            if mode != "officials" and d.get("official"):
                title += f" · {d['official']}"
            o.append(f'<rect x="{xs:.1f}" y="{y + (row_h - bar_h) / 2}" width="{xe - xs:.1f}" height="{bar_h}" rx="3" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}><title>{_x(title)}</title></rect>')
            text = d["title"] if mode == "officials" else (d.get("official") or "UNFILLED")
            if blocking and xe - xs > 60:
                tc = "#000" if secondary or not blocking else "#FFF"
                o.append(f'<text x="{xs + 4:.1f}" y="{y + 17}" font-size="10" fill="{tc if blocking else fg}">'
                         f'{_x(text[:int((xe - xs) / 6)])}</text>')
    ly = top + row_h * len(rows) + 26
    for i, r in enumerate(races + [{"id": E.ALL, "name": "All-day positions"},
                                   {"id": "session", "name": "Meetings, briefings, rehearsals"}]):
        lx = 12 + (i % 4) * 300
        yy = ly + (i // 4) * 22
        c = race_colour(ev, r["id"])
        o.append(f'<rect x="{lx}" y="{yy - 11}" width="14" height="14" rx="2" fill="{c}"/>'
                 f'<text x="{lx + 20}" y="{yy}" fill="{fg}">{_x(r["name"][:40])}'
                 f'{"" if r["id"] in (E.ALL, "session") else " – start " + _x(r.get("start", ""))}</text>')
    o.append("</svg>")
    return "\n".join(o)


def write_svg(path, svg):
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path
