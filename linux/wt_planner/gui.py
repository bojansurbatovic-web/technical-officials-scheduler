"""GTK 3 user interface for the Technical Officials Scheduler (Ubuntu desktop)."""
import copy
import datetime as dt
import json
import os
import re
import tempfile

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

from . import athletes as ATH  # noqa: E402
from . import engine as E  # noqa: E402
from . import exporters as X  # noqa: E402
from . import reference as ref  # noqa: E402

DATA_DIR = os.path.join(GLib.get_user_data_dir(), "wt-planner")
LIB_DIR = os.path.join(DATA_DIR, "events")
CONF_DIR = os.path.join(GLib.get_user_config_dir(), "wt-planner")
RECENT_FILE = os.path.join(CONF_DIR, "recent.json")

STATUS_BG = {"OK": "#C6EFCE", "TIGHT": "#FFEB9C", "CONFLICT": "#FFC7CE", "UNFILLED": "#F4B183",
             "LOC / volunteer": "#DDEBF7", "": None}
UNASSIGNED = "— unassigned —"
LOC_VOL = "LOC / volunteer (leave empty)"
AUTO = "(auto)"


# ======================================================================= helpers
def slugify(text):
    s = re.sub(r"[^A-Za-z0-9]+", "-", text or "event").strip("-").lower()
    return s[:60] or "event"


def load_recent():
    try:
        with open(RECENT_FILE, encoding="utf-8") as f:
            return [p for p in json.load(f) if isinstance(p, str)]
    except (OSError, ValueError):
        return []


def save_recent(paths):
    os.makedirs(CONF_DIR, exist_ok=True)
    try:
        with open(RECENT_FILE, "w", encoding="utf-8") as f:
            json.dump(list(dict.fromkeys(paths))[:200], f, indent=1)
    except OSError:
        pass


def library_entries():
    """All known event files (library folder + recently used) with their date."""
    paths = []
    if os.path.isdir(LIB_DIR):
        paths += [os.path.join(LIB_DIR, f) for f in sorted(os.listdir(LIB_DIR)) if f.endswith(ref.FILE_SUFFIX)]
    paths += [p for p in load_recent() if os.path.isfile(p)]
    out, seen = [], set()
    for p in paths:
        rp = os.path.realpath(p)
        if rp in seen:
            continue
        seen.add(rp)
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            e = data.get("event", {})
            dates = sorted({r.get("date") or e.get("date", "") for r in data.get("races", [])} | {e.get("date", "")} - {""})
            out.append({"path": p, "name": e.get("name") or os.path.basename(p),
                        "date": dates[0] if dates else "", "dates": dates,
                        "races": len(data.get("races", [])), "officials": len(data.get("officials", []))})
        except (OSError, ValueError, AttributeError):
            continue
    return out


def spin(lower, upper, step=1.0, digits=0, value=0.0):
    adj = Gtk.Adjustment(value=value, lower=lower, upper=upper, step_increment=step, page_increment=step * 10, page_size=0)
    sb = Gtk.SpinButton(adjustment=adj, digits=digits)
    sb.set_numeric(True)
    sb.set_width_chars(7)
    return sb


def label(text, xalign=0.0, bold=False, wrap=True, dim=False):
    lb = Gtk.Label()
    if bold or dim:
        esc = GLib.markup_escape_text(text)
        lb.set_markup(f"<b>{esc}</b>" if bold else f"<span alpha='65%'>{esc}</span>")
    else:
        lb.set_text(text)
    lb.set_xalign(xalign)
    if wrap:
        lb.set_line_wrap(True)       # wrapped labels never force the window wider than the screen
        lb.set_max_width_chars(110)
    return lb


def scrolled(child, min_h=120):
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    sw.set_min_content_height(min(min_h, 180))
    sw.add(child)
    sw.set_vexpand(True)
    sw.set_hexpand(True)
    return sw


def page(child):
    """Wrap a whole tab so it scrolls instead of pushing the window off-screen."""
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    sw.add(child)
    sw.set_vexpand(True)
    sw.set_hexpand(True)
    return sw


def flow(*children):
    """A row of widgets that wraps onto the next line when the window is narrow."""
    fb = Gtk.FlowBox()
    fb.set_selection_mode(Gtk.SelectionMode.NONE)
    fb.set_homogeneous(False)
    fb.set_column_spacing(6)
    fb.set_row_spacing(4)
    fb.set_max_children_per_line(40)
    fb.set_valign(Gtk.Align.START)
    for c in children:
        fb.add(c)
    return fb


def field(text, widget):
    """Caption above an input, used inside flow() rows."""
    b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    lb = Gtk.Label(label=text)
    lb.set_xalign(0.0)
    b.pack_start(lb, False, False, 0)
    b.pack_start(widget, False, False, 0)
    return b


def screen_workarea():
    """(width, height) of the usable screen area, or None."""
    try:
        disp = Gdk.Display.get_default()
        mon = disp.get_primary_monitor() or disp.get_monitor(0)
        wa = mon.get_workarea()
        return int(wa.width), int(wa.height)
    except Exception:
        return None


WINDOW_FILE = os.path.join(CONF_DIR, "window.json")


def text_column(tree, title, idx, editable=False, on_edit=None, bg_idx=None, width=None, expand=False, weight_idx=None):
    r = Gtk.CellRendererText()
    if editable:
        r.set_property("editable", True)
        r.connect("edited", on_edit, idx)
    c = Gtk.TreeViewColumn(title, r, text=idx)
    if bg_idx is not None:
        c.add_attribute(r, "cell-background", bg_idx)
    if weight_idx is not None:
        c.add_attribute(r, "weight", weight_idx)
    c.set_resizable(True)
    if width:
        c.set_min_width(width)
    c.set_expand(expand)
    tree.append_column(c)
    return c


def spin_column(tree, title, idx, lower, upper, step, digits, on_edit, width=None):
    r = Gtk.CellRendererSpin()
    r.set_property("editable", True)
    r.set_property("adjustment", Gtk.Adjustment(value=0, lower=lower, upper=upper, step_increment=step,
                                                page_increment=step * 10, page_size=0))
    r.set_property("digits", digits)
    r.connect("edited", on_edit, idx)
    c = Gtk.TreeViewColumn(title, r, text=idx)
    c.set_resizable(True)
    if width:
        c.set_min_width(width)
    tree.append_column(c)
    return c


def combo_column(tree, title, idx, model, on_edit, width=None, bg_idx=None):
    r = Gtk.CellRendererCombo()
    r.set_property("editable", True)
    r.set_property("model", model)
    r.set_property("text-column", 0)
    r.set_property("has-entry", False)
    r.connect("edited", on_edit, idx)
    c = Gtk.TreeViewColumn(title, r, text=idx)
    if bg_idx is not None:
        c.add_attribute(r, "cell-background", bg_idx)
    c.set_resizable(True)
    if width:
        c.set_min_width(width)
    tree.append_column(c)
    return c


def toggle_column(tree, title, idx, on_toggle):
    r = Gtk.CellRendererToggle()
    r.set_property("activatable", True)
    r.connect("toggled", on_toggle, idx)
    c = Gtk.TreeViewColumn(title, r, active=idx)
    tree.append_column(c)
    return c


def str_model(items):
    m = Gtk.ListStore(str)
    for it in items:
        m.append([it])
    return m


def to_float(text, default=0.0):
    try:
        return float(str(text).replace(",", "."))
    except (TypeError, ValueError):
        return default


# ======================================================================= main window
class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=ref.APP_NAME)
        self.set_icon_name("wt-planner")
        self._fit_to_screen()
        self.ev = E.new_event("New event", dt.date.today().isoformat())
        self.path = None
        self.dirty = False
        self.result = None
        self.undo, self.redo = [], []
        self._loading = False
        self._refresh_pending = False
        self.auto_mode = True
        self.selected_race = None

        self._build_actions(app)
        self._build_header()
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.sidebar = Gtk.ScrolledWindow()
        self.sidebar.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.sidebar.add(self._build_sidebar())
        paned.pack1(self.sidebar, False, False)
        self.nb = Gtk.Notebook()
        self.nb.set_scrollable(True)
        paned.pack2(self.nb, True, True)
        paned.set_position(290)
        self.paned = paned
        self.add(paned)

        self._tab_event()
        self._tab_officials()
        self._tab_participation()
        self._tab_positions()
        self._tab_duties()
        self._tab_sessions()
        self._tab_assignments()
        self._tab_personal()
        self._tab_gantt()
        self._tab_timeline()
        self._tab_athletes()
        self._tab_conflicts()
        self._tab_references()
        self.nb.connect("switch-page", self._on_switch_page)
        self.connect("delete-event", self._on_delete)

        self.load_event(self._demo_event(), None, dirty=False)
        self.show_all()
        if self._small_screen:
            self.side_btn.set_active(False)

    # ------------------------------------------------------------------ window size
    def _fit_to_screen(self):
        """Size the window to the screen (and to the last size the user chose)."""
        wa = screen_workarea() or (1280, 800)
        self._small_screen = wa[0] < 1200 or wa[1] < 760
        w, h = min(1400, int(wa[0] * 0.92)), min(900, int(wa[1] * 0.90))
        maximized = self._small_screen
        try:
            with open(WINDOW_FILE, encoding="utf-8") as f:
                g = json.load(f)
            w, h = min(int(g.get("w", w)), wa[0]), min(int(g.get("h", h)), wa[1])
            maximized = bool(g.get("maximized", maximized))
        except (OSError, ValueError, TypeError):
            pass
        self.set_default_size(max(640, w), max(480, h))
        if maximized:
            self.maximize()

    def _save_geometry(self):
        try:
            os.makedirs(CONF_DIR, exist_ok=True)
            w, h = self.get_size()
            with open(WINDOW_FILE, "w", encoding="utf-8") as f:
                json.dump({"w": int(w), "h": int(h), "maximized": bool(self.is_maximized())}, f)
        except (OSError, TypeError, ValueError):
            pass

    # ------------------------------------------------------------------ actions
    def _build_actions(self, app):
        acts = {
            "new": (self.on_new, ["<Primary>n"]), "open": (self.on_open, ["<Primary>o"]),
            "save": (self.on_save, ["<Primary>s"]), "save_as": (self.on_save_as, ["<Primary><Shift>s"]),
            "save_library": (self.on_save_library, []),
            "export_xlsx": (lambda *a: self.on_export("xlsx"), ["<Primary>e"]),
            "export_ods": (lambda *a: self.on_export("ods"), []),
            "export_json": (lambda *a: self.on_export("json"), []),
            "export_ics": (lambda *a: self.on_export("ics"), []),
            "export_athletes": (lambda *a: self.on_export_athletes("html"), []),
            "trisport": (lambda *a: self._open_uri("https://www.trisport.me/"), []),
            "export_svg": (lambda *a: self.on_export("svg"), []),
            "share": (self.on_share, []), "copy_json": (self.on_copy_json, []),
            "open_library": (self.on_open_library, []), "undo": (self.on_undo, ["<Primary>z"]),
            "redo": (self.on_redo, ["<Primary><Shift>z", "<Primary>y"]),
            "auto": (lambda *a: self.on_auto(keep=True), ["F5"]),
            "auto_fresh": (lambda *a: self.on_auto(keep=False), []),
            "swap": (self.on_swap, []), "about": (self.on_about, []),
            "example_q3": (lambda *a: self.open_example("example_q3.wtplan.json"), []),
            "example_multi": (lambda *a: self.open_example("example_multiday.wtplan.json"), []),
            "sidebar": (lambda *a: self.side_btn.set_active(not self.side_btn.get_active()), ["F9"]),
        }
        for name, (cb, accels) in acts.items():
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)
            if accels:
                app.set_accels_for_action(f"win.{name}", accels)

    def _build_header(self):
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = ref.APP_NAME
        self.hb = hb
        self.side_btn = Gtk.ToggleButton()
        self.side_btn.add(Gtk.Image.new_from_icon_name("x-office-calendar-symbolic", Gtk.IconSize.BUTTON))
        self.side_btn.set_tooltip_text("Show / hide the calendar panel (F9)")
        self.side_btn.set_active(True)
        self.side_btn.connect("toggled", lambda w: self.sidebar.set_visible(w.get_active()))
        hb.pack_start(self.side_btn)
        for icon, action, tip in (("document-new-symbolic", "win.new", "New event (Ctrl+N)"),
                                  ("document-open-symbolic", "win.open", "Open event file (Ctrl+O)"),
                                  ("document-save-symbolic", "win.save", "Save (Ctrl+S)")):
            b = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            b.set_action_name(action)
            b.set_tooltip_text(tip)
            hb.pack_start(b)
        ub = Gtk.Button.new_from_icon_name("edit-undo-symbolic", Gtk.IconSize.BUTTON)
        ub.set_action_name("win.undo")
        ub.set_tooltip_text("Undo (Ctrl+Z)")
        rb = Gtk.Button.new_from_icon_name("edit-redo-symbolic", Gtk.IconSize.BUTTON)
        rb.set_action_name("win.redo")
        rb.set_tooltip_text("Redo (Ctrl+Shift+Z)")
        box = Gtk.Box(spacing=0)
        box.get_style_context().add_class("linked")
        box.pack_start(ub, False, False, 0)
        box.pack_start(rb, False, False, 0)
        hb.pack_start(box)

        menu = Gio.Menu()
        sec1 = Gio.Menu()
        sec1.append("Save as…", "win.save_as")
        sec1.append("Save to calendar library", "win.save_library")
        sec1.append("Open library folder", "win.open_library")
        menu.append_section(None, sec1)
        sec2 = Gio.Menu()
        sec2.append("Export table to Excel (.xlsx)…", "win.export_xlsx")
        sec2.append("Export table to LibreOffice (.ods)…", "win.export_ods")
        sec2.append("Export Gantt (.svg)…", "win.export_svg")
        sec2.append("Export calendar (.ics)…", "win.export_ics")
        sec2.append("Export athletes’ guide (.html)…", "win.export_athletes")
        sec2.append("Export event as JSON…", "win.export_json")
        menu.append_section("Export", sec2)
        sec3 = Gio.Menu()
        sec3.append("Share JSON with another app…", "win.share")
        sec3.append("Copy JSON to clipboard", "win.copy_json")
        menu.append_section("Share", sec3)
        sec4 = Gio.Menu()
        sec4.append("Re-plan keeping locked rows (F5)", "win.auto")
        sec4.append("Re-plan from scratch", "win.auto_fresh")
        sec4.append("Swap two officials…", "win.swap")
        menu.append_section("Plan", sec4)
        sec5 = Gio.Menu()
        sec5.append("Example: two races back to back (Q3)", "win.example_q3")
        sec5.append("Example: two-day weekend, 3 races", "win.example_multi")
        sec5.append("TriSport.me – website, help and other apps", "win.trisport")
        sec5.append("References & about", "win.about")
        menu.append_section(None, sec5)
        mb = Gtk.MenuButton()
        mb.set_menu_model(menu)
        mb.add(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        hb.pack_end(mb)

        ab = Gtk.Button(label="Auto-assign")
        ab.get_style_context().add_class("suggested-action")
        ab.set_action_name("win.auto")
        ab.set_tooltip_text("Re-plan secondary positions; rows you edited or locked are kept (F5)")
        hb.pack_end(ab)
        self.auto_check = Gtk.CheckButton(label="Auto")
        self.auto_check.set_active(True)
        self.auto_check.set_tooltip_text("Re-plan automatically after every change (locked rows are kept)")
        self.auto_check.connect("toggled", lambda w: setattr(self, "auto_mode", w.get_active()))
        hb.pack_end(self.auto_check)
        self.set_titlebar(hb)

    # ------------------------------------------------------------------ sidebar
    def _build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(8)
        box.pack_start(label("Calendar", bold=True), False, False, 0)
        self.cal = Gtk.Calendar()
        self.cal.set_halign(Gtk.Align.CENTER)
        self.cal.connect("month-changed", lambda w: self.refresh_calendar())
        self.cal.connect("day-selected", lambda w: self.refresh_day_list())
        self.cal.connect("day-selected-double-click", lambda w: self.on_new_on_date())
        box.pack_start(self.cal, False, False, 0)
        hb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        b1 = Gtk.Button(label="New on this date")
        b1.connect("clicked", lambda w: self.on_new_on_date())
        b2 = Gtk.Button(label="Set event date")
        b2.set_tooltip_text("Use the selected calendar day as the date of the open event")
        b2.connect("clicked", lambda w: self.on_set_date_from_cal())
        hb.pack_start(b1, True, True, 0)
        hb.pack_start(b2, True, True, 0)
        box.pack_start(hb, False, False, 0)
        box.pack_start(label("Events on selected day", bold=True), False, False, 4)
        self.day_list = Gtk.ListBox()
        self.day_list.connect("row-activated", self._on_day_row)
        box.pack_start(scrolled(self.day_list, 120), True, True, 0)
        box.pack_start(label("All saved events", bold=True), False, False, 4)
        self.all_list = Gtk.ListBox()
        self.all_list.connect("row-activated", self._on_day_row)
        box.pack_start(scrolled(self.all_list, 160), True, True, 0)
        tip = label("Double-click a day to start a new event on it. Saved events (.wtplan.json) can be "
                    "opened by any app via Share.", wrap=True, dim=True)
        box.pack_start(tip, False, False, 0)
        return box

    def refresh_calendar(self):
        self.cal.clear_marks()
        y, m0, _d = self.cal.get_date()
        self._lib = library_entries()
        for e in self._lib:
            for ds in e.get("dates") or [e["date"]]:
                try:
                    d = dt.date.fromisoformat(ds)
                except (TypeError, ValueError):
                    continue
                if d.year == y and d.month == m0 + 1:
                    self.cal.mark_day(d.day)
        self._fill_list(self.all_list, sorted(self._lib, key=lambda e: e["date"] or "9999"))
        self.refresh_day_list()

    def refresh_day_list(self):
        y, m0, d = self.cal.get_date()
        iso = f"{y:04d}-{m0 + 1:02d}-{d:02d}"
        self._fill_list(self.day_list, [e for e in getattr(self, "_lib", []) if iso in (e.get("dates") or [e["date"]])])

    def _fill_list(self, lb, entries):
        for ch in lb.get_children():
            lb.remove(ch)
        for e in entries:
            row = Gtk.ListBoxRow()
            row.path = e["path"]
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            v.set_border_width(4)
            v.pack_start(label(e["name"], bold=True), False, False, 0)
            span = e["date"] if len(e.get("dates") or []) < 2 else f"{e['dates'][0]} → {e['dates'][-1]}"
            v.pack_start(label(f"{span or 'no date'} · {e['races']} race(s) · {e['officials']} TOs", dim=True), False, False, 0)
            row.add(v)
            row.set_tooltip_text(e["path"])
            lb.add(row)
        if not entries:
            row = Gtk.ListBoxRow()
            row.path = None
            row.add(label("  (none)", dim=True))
            row.set_activatable(False)
            lb.add(row)
        lb.show_all()

    def _on_day_row(self, lb, row):
        if getattr(row, "path", None) and self.confirm_discard():
            self.open_path(row.path)

    def on_new_on_date(self):
        if not self.confirm_discard():
            return
        y, m0, d = self.cal.get_date()
        ev = E.new_event("New event", f"{y:04d}-{m0 + 1:02d}-{d:02d}", n_officials=18)
        E.auto_assign(ev)
        self.load_event(ev, None, dirty=True)

    def on_set_date_from_cal(self):
        y, m0, d = self.cal.get_date()
        self.edit(lambda: self.ev["event"].__setitem__("date", f"{y:04d}-{m0 + 1:02d}-{d:02d}"), replan=False)
        self._load_event_fields()

    # ------------------------------------------------------------------ tab: event & races
    def _tab_event(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_border_width(10)
        self.f = {}
        fields = [("name", "Event name", 30), ("venue", "Venue", 22), ("date", "Date (YYYY-MM-DD)", 12),
                  ("td", "Technical Delegate", 22), ("md", "Medical Delegate", 22),
                  ("jury0", "Jury member 2", 22), ("jury1", "Jury member 3", 22)]
        items = []
        for k, t, wc in fields:
            en = Gtk.Entry()
            en.set_width_chars(wc)
            en.connect("changed", self._on_event_field, k)
            self.f[k] = en
            items.append(field(t, en))
        self.f_vcc = spin(0, 5, 1, 0, 1)
        self.f_vcc.connect("value-changed", lambda w: self._on_event_num("vcc_base", w))
        self.f_spare = spin(0, 50, 1, 0, 10)
        self.f_spare.connect("value-changed", lambda w: self._on_event_num("spare_pct", w))
        items += [field("Radios: VCC base", self.f_vcc), field("Radios: spares %", self.f_spare)]
        outer.pack_start(flow(*items), False, False, 0)

        outer.pack_start(label("Races – edit cells directly (format/category reset distances, laps and paces)", bold=True), False, False, 4)
        # id, name, format, category, start, legs, swim_m, bike_km, run_km, lap s, lap b, lap r, wheel, aid, start_line, draft
        self.race_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, bool, str)
        self.race_tree = Gtk.TreeView(model=self.race_store)
        self.fmt_labels = [ref.FORMATS[k]["label"] for k in ref.FORMAT_ORDER]
        self.cat_labels = [ref.CATEGORIES[k]["label"] for k in ref.CATEGORY_ORDER]
        text_column(self.race_tree, "Race name", 1, True, self._on_race_edit, width=180, expand=True)
        combo_column(self.race_tree, "Format", 2, str_model(self.fmt_labels), self._on_race_edit, width=220)
        combo_column(self.race_tree, "Category", 3, str_model(self.cat_labels), self._on_race_edit, width=140)
        text_column(self.race_tree, "Date", 16, True, self._on_race_edit, width=95)
        text_column(self.race_tree, "Start", 4, True, self._on_race_edit, width=60)
        spin_column(self.race_tree, "Legs", 5, 1, 8, 1, 0, self._on_race_edit)
        spin_column(self.race_tree, "Swim m", 6, 100, 5000, 50, 0, self._on_race_edit)
        spin_column(self.race_tree, "Bike km", 7, 1, 200, 0.5, 1, self._on_race_edit)
        spin_column(self.race_tree, "Run km", 8, 0.5, 50, 0.1, 1, self._on_race_edit)
        spin_column(self.race_tree, "Swim laps", 9, 1, 6, 1, 0, self._on_race_edit)
        spin_column(self.race_tree, "Bike laps", 10, 1, 20, 1, 0, self._on_race_edit)
        spin_column(self.race_tree, "Run laps", 11, 1, 10, 1, 0, self._on_race_edit)
        spin_column(self.race_tree, "Wheel st.", 12, 0, 4, 1, 0, self._on_race_edit)
        spin_column(self.race_tree, "Aid st.", 13, 0, 20, 1, 0, self._on_race_edit)
        spin_column(self.race_tree, "Start-line TOs", 14, 0, 12, 1, 0, self._on_race_edit)
        toggle_column(self.race_tree, "Draft-legal", 15, self._on_race_toggle)
        self.race_tree.get_selection().connect("changed", self._on_race_selected)
        outer.pack_start(scrolled(self.race_tree, 140), True, True, 0)
        btns = []
        for txt, cb in (("Add race", self.on_add_race), ("Duplicate", self.on_dup_race),
                        ("Remove", self.on_del_race), ("Set date from calendar", self.on_race_date_from_cal),
                        ("Next day", lambda: self.on_race_day_step(1)), ("Previous day", lambda: self.on_race_day_step(-1))):
            b = Gtk.Button(label=txt)
            b.connect("clicked", lambda w, c=cb: c())
            btns.append(b)
        outer.pack_start(flow(*btns), False, False, 0)
        outer.pack_start(label("Each race has its own date and start time, so one event can run over several days. "
                               "A new race starts 2 h 45 min after the previous one (Masterfile back-to-back example), "
                               "or the next morning if that would be after 17:00. Age-group waves can be added as separate races. "
                               "Choose who works which race on the 'Who works which race' tab.", dim=True), False, False, 0)

        # race tweaks
        fr = Gtk.Frame(label=" Selected race – fine-tune paces, field spread and schedule ")
        tbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        tbox.set_border_width(8)
        titems = []
        self.tw = {}
        pace_fields = [("swim_pace", "Swim pace (min/100 m)", 0.8, 4, 0.01, 3), ("bike_speed", "Bike speed (km/h)", 15, 55, 0.1, 1),
                       ("run_pace", "Run pace (min/km)", 2.5, 9, 0.01, 2), ("t1", "T1 (min)", 0.2, 10, 0.05, 2),
                       ("t2", "T2 (min)", 0.2, 10, 0.05, 2), ("gap_swim", "Last out of water (+% of swim)", 0, 300, 1, 0),
                       ("gap_t2", "Last into T2 (+% of time to T2)", 0, 300, 1, 0), ("gap_finish", "Last finisher (+% of winning time)", 0, 300, 1, 0)]
        for k, t, lo, hi, st, dg in pace_fields:
            sb = spin(lo, hi, st, dg)
            sb.connect("value-changed", self._on_race_tweak, "paces", k)
            self.tw[("paces", k)] = sb
            titems.append(field(t, sb))
        for k, t in ref.SCHEDULE_LABELS.items():
            sb = spin(0, 240, 1, 0)
            sb.connect("value-changed", self._on_race_tweak, "schedule", k)
            self.tw[("schedule", k)] = sb
            titems.append(field(t, sb))
        tbox.pack_start(flow(*titems), False, False, 0)
        rbtn = Gtk.Button(label="Reset race to format/category defaults")
        rbtn.set_halign(Gtk.Align.START)
        rbtn.connect("clicked", lambda w: self.on_reset_race())
        tbox.pack_start(rbtn, False, False, 0)
        self.race_summary = label("", wrap=True)
        tbox.pack_start(self.race_summary, False, False, 0)
        fr.add(tbox)
        outer.pack_start(fr, False, False, 0)
        self.nb.append_page(page(outer), Gtk.Label(label="Event & races"))

    def _on_event_field(self, entry, key):
        if self._loading:
            return
        val = entry.get_text()

        def apply():
            if key.startswith("jury"):
                j = self.ev["event"].setdefault("jury", ["", ""])
                while len(j) < 2:
                    j.append("")
                j[int(key[-1])] = val
            else:
                self.ev["event"][key] = val
        self.edit(apply, replan=False, coalesce=f"field:{key}")
        if key == "date":
            self._sync_calendar_to_event()

    def _on_event_num(self, key, w):
        if self._loading:
            return
        self.edit(lambda: self.ev["event"].__setitem__(key, int(w.get_value())), replan=False, coalesce=f"num:{key}")

    def _race_by_path(self, path):
        rid = self.race_store[path][0]
        return next((r for r in self.ev["races"] if r["id"] == rid), None)

    def _on_race_edit(self, renderer, path, text, idx):
        race = self._race_by_path(path)
        if race is None:
            return

        def apply():
            if idx == 1:
                race["name"] = text.strip() or race["name"]
            elif idx == 2:
                key = ref.FORMAT_ORDER[self.fmt_labels.index(text)] if text in self.fmt_labels else race["format"]
                E.apply_format(race, fmt=key)
            elif idx == 3:
                key = ref.CATEGORY_ORDER[self.cat_labels.index(text)] if text in self.cat_labels else race["category"]
                E.apply_format(race, category=key)
            elif idx == 4:
                t = E.parse_hhmm(text)
                if t is not None:
                    race["start"] = E.fmt_hhmm(t)
            elif idx == 5:
                race["legs"] = max(1, int(to_float(text, race["legs"])))
            elif idx == 6:
                race["swim_m"] = int(to_float(text, race["swim_m"]))
            elif idx == 7:
                race["bike_km"] = to_float(text, race["bike_km"])
            elif idx == 8:
                race["run_km"] = to_float(text, race["run_km"])
            elif idx in (9, 10, 11):
                race["laps"][("swim", "bike", "run")[idx - 9]] = max(1, int(to_float(text, 1)))
            elif idx == 12:
                race["wheel_stations"] = max(0, int(to_float(text, 0)))
            elif idx == 13:
                race["aid_stations"] = max(0, int(to_float(text, 0)))
            elif idx == 14:
                race["start_line"] = max(0, int(to_float(text, 4)))
            elif idx == 16:
                d = E.parse_date(text)
                if d is not None or not text.strip():
                    race["date"] = d.isoformat() if d else ""
        self.edit(apply)

    def _on_race_toggle(self, renderer, path, idx):
        race = self._race_by_path(path)
        if race is not None:
            self.edit(lambda: race.__setitem__("draft_legal", not race["draft_legal"]))

    def _on_race_selected(self, sel):
        model, it = sel.get_selected()
        if it is None:
            return
        self.selected_race = model[it][0]
        self._load_race_tweaks()

    def _current_race(self):
        r = next((r for r in self.ev["races"] if r["id"] == self.selected_race), None)
        return r or (self.ev["races"][0] if self.ev["races"] else None)

    def _load_race_tweaks(self):
        race = self._current_race()
        if race is None:
            return
        self._loading = True
        for (grp, k), sb in self.tw.items():
            sb.set_value(float(race[grp].get(k, 0)))
        self._loading = False
        self._update_race_summary()

    def _update_race_summary(self):
        race = self._current_race()
        if race is None or not self.result:
            self.race_summary.set_text("")
            return
        tl = self.result["timelines"].get(race["id"]) or E.race_timeline(race)
        F = self.result["fmt"]
        sg = tl["_segments"]
        legs = f"{sg['legs']} legs × " if sg["legs"] > 1 else ""
        self.race_summary.set_markup(
            f"<b>{GLib.markup_escape_text(race['name'])}</b>: {legs}swim {E.fmt_dur(sg['swim'])} · T1 {E.fmt_dur(sg['t1'])} · "
            f"bike {E.fmt_dur(sg['bike'])} · T2 {E.fmt_dur(sg['t2'])} · run {E.fmt_dur(sg['run'])}   →   "
            f"start {F(tl['start'])} · last out of water {F(tl['swim_last_out'])} · "
            f"leader T2 {F(tl['t2_first'])} · last T2 {F(tl['t2_last'])} · "
            f"<b>winner {F(tl['winner'])}</b> · last finisher {F(tl['last_finisher'])} · "
            f"medals {F(tl['medal'])}"
            + "".join(f"\n⚠ {GLib.markup_escape_text(w)}" for w in self.result.get("warnings", [])
                      if race["name"] in w))

    def _on_race_tweak(self, sb, grp, key):
        if self._loading:
            return
        race = self._current_race()
        if race is None:
            return
        v = sb.get_value()
        self.edit(lambda: race[grp].__setitem__(key, round(v, 3)), coalesce=f"tweak:{race['id']}:{grp}:{key}")

    def _next_slot(self, race):
        """Date and start for a race following `race`: +2 h 45 min, or next day if after 17:00."""
        d = E.race_date(self.ev, race)
        t = E.parse_hhmm(race["start"], 600) + 165
        if t > 17 * 60:
            first = min((E.parse_hhmm(r["start"], 600) for r in self.ev["races"]
                         if E.race_date(self.ev, r) == d), default=600)
            return (d + dt.timedelta(days=1)).isoformat(), E.fmt_hhmm(first)
        return d.isoformat(), E.fmt_hhmm(t)

    def on_add_race(self):
        def apply():
            races = E.races_sorted(self.ev)
            if races:
                last = races[-1]
                date, start = self._next_slot(last)
                cat = "elite_men" if last["category"] == "elite_women" else last["category"]
                r = E.new_race(last["format"], cat, start, date=date)
            else:
                r = E.new_race()
            self.ev["races"].append(r)
            self.selected_race = r["id"]
        self.edit(apply)

    def on_dup_race(self):
        race = self._current_race()
        if race is None:
            return

        def apply():
            r = copy.deepcopy(race)
            r["id"] = E.new_id("r")
            r["name"] = race["name"] + " (copy)"
            r["date"], r["start"] = self._next_slot(race)
            self.ev["races"].append(r)
            self.selected_race = r["id"]
        self.edit(apply)

    def on_del_race(self):
        race = self._current_race()
        if race is None or len(self.ev["races"]) <= 1:
            self.info("At least one race is needed.")
            return
        self.edit(lambda: self.ev["races"].remove(race))
        self.selected_race = None

    def on_race_date_from_cal(self):
        race = self._current_race()
        if race is None:
            return
        y, m0, d = self.cal.get_date()
        self.edit(lambda: race.__setitem__("date", f"{y:04d}-{m0 + 1:02d}-{d:02d}"))

    def on_race_day_step(self, step):
        race = self._current_race()
        if race is None:
            return
        new = (E.race_date(self.ev, race) + dt.timedelta(days=step)).isoformat()
        self.edit(lambda: race.__setitem__("date", new))

    def on_reset_race(self):
        race = self._current_race()
        if race is not None:
            self.edit(lambda: (E.apply_format(race), race.__setitem__("schedule", dict(ref.SCHEDULE_DEFAULTS)),
                               race.__setitem__("shifts", {})))

    # ------------------------------------------------------------------ tab: officials
    def _tab_officials(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        box.pack_start(label("Technical Officials available – the planner gives each one a primary position and fills the "
                             "short jobs as secondary positions without time clashes.", wrap=True), False, False, 0)
        # name, country, primary title, max sec, from, to, radio, notes, idx
        self.off_store = Gtk.ListStore(str, str, str, str, str, str, bool, str, int)
        self.off_tree = Gtk.TreeView(model=self.off_store)
        self.pos_titles = [AUTO] + [p["title"] for p in sorted(ref.POSITION_INDEX.values(), key=lambda p: p["priority"])]
        self.pos_by_title = {p["title"]: k for k, p in ref.POSITION_INDEX.items()}
        text_column(self.off_tree, "Name and surname", 0, True, self._on_off_edit, width=200, expand=True)
        text_column(self.off_tree, "Country / NF", 1, True, self._on_off_edit, width=80)
        combo_column(self.off_tree, "Preferred primary position", 2, str_model(self.pos_titles), self._on_off_edit, width=260)
        spin_column(self.off_tree, "Max secondary jobs", 3, 0, 8, 1, 0, self._on_off_edit)
        text_column(self.off_tree, "Available from", 4, True, self._on_off_edit, width=70)
        text_column(self.off_tree, "Available to", 5, True, self._on_off_edit, width=70)
        toggle_column(self.off_tree, "Radio", 6, self._on_off_toggle)
        text_column(self.off_tree, "Notes", 7, True, self._on_off_edit, width=160)
        box.pack_start(scrolled(self.off_tree, 300), True, True, 0)
        bb = flow()
        b = Gtk.Button(label="Add official")
        b.connect("clicked", lambda w: self.on_add_official())
        bb.add(b)
        b = Gtk.Button(label="Remove selected")
        b.connect("clicked", lambda w: self.on_del_official())
        bb.add(b)
        bb.add(label("   Officials available:"))
        self.n_off = spin(1, 120, 1, 0, 18)
        bb.add(self.n_off)
        b = Gtk.Button(label="Set number")
        b.set_tooltip_text("Adds placeholder officials or removes the last ones")
        b.connect("clicked", lambda w: self.on_set_n_officials())
        bb.add(b)
        b = Gtk.Button(label="Paste names…")
        b.set_tooltip_text("One per line: Name; Country; Primary position (country and position optional)")
        b.connect("clicked", lambda w: self.on_paste_names())
        bb.add(b)
        b = Gtk.Button(label="Clear preferred primaries")
        b.connect("clicked", lambda w: self.edit(lambda: [o.__setitem__("primary", "") for o in self.ev["officials"]]))
        bb.add(b)
        box.pack_start(bb, False, False, 0)
        box.pack_start(label("Times as HH:MM (each day). Max secondary jobs = how many extra positions the planner may give "
                             "that person per day. Which races each official works is set on the 'Who works which race' tab.",
                             dim=True), False, False, 0)
        self.nb.append_page(page(box), Gtk.Label(label="Officials"))

    def _on_off_edit(self, renderer, path, text, idx):
        i = self.off_store[path][8]
        o = self.ev["officials"][i]
        old_name = o["name"]

        def apply():
            if idx == 0:
                new = text.strip()
                if new and new != old_name and new not in [x["name"] for x in self.ev["officials"]]:
                    o["name"] = new
                    for v in self.ev["assignments"].values():
                        if v.get("official") == old_name:
                            v["official"] = new
                    prim = self.ev.get("_primary", {})
                    if old_name in prim:
                        prim[new] = prim.pop(old_name)
            elif idx == 1:
                o["country"] = text.strip()
            elif idx == 2:
                o["primary"] = "" if text == AUTO else self.pos_by_title.get(text, "")
            elif idx == 3:
                o["max_secondary"] = max(0, int(to_float(text, 3)))
            elif idx in (4, 5):
                t = E.parse_hhmm(text)
                o["available_from" if idx == 4 else "available_to"] = E.fmt_hhmm(t) if t is not None else ""
            elif idx == 7:
                o["notes"] = text
        self.edit(apply, replan=idx in (2, 3, 4, 5))

    def _on_off_toggle(self, renderer, path, idx):
        i = self.off_store[path][8]
        o = self.ev["officials"][i]
        self.edit(lambda: o.__setitem__("radio", not o.get("radio", True)), replan=False)

    def _unique_name(self, base="Official"):
        names = {o["name"] for o in self.ev["officials"]}
        i = len(names) + 1
        while f"{base} {i}" in names:
            i += 1
        return f"{base} {i}"

    def on_add_official(self):
        self.edit(lambda: self.ev["officials"].append(E.new_official(self._unique_name())))

    def on_del_official(self):
        model, it = self.off_tree.get_selection().get_selected()
        if it is None:
            return
        i = model[it][8]
        name = self.ev["officials"][i]["name"]

        def apply():
            self.ev["officials"].pop(i)
            self.ev["assignments"] = {k: v for k, v in self.ev["assignments"].items() if v.get("official") != name}
        self.edit(apply)

    def on_set_n_officials(self):
        n = int(self.n_off.get_value())

        def apply():
            offs = self.ev["officials"]
            while len(offs) < n:
                offs.append(E.new_official(self._unique_name()))
            while len(offs) > n:
                gone = offs.pop()["name"]
                self.ev["assignments"] = {k: v for k, v in self.ev["assignments"].items() if v.get("official") != gone}
        self.edit(apply)

    def on_paste_names(self):
        d = Gtk.Dialog(title="Paste officials", transient_for=self, modal=True)
        d.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Replace list", 1, "_Append", 2)
        d.set_default_size(560, 420)
        area = d.get_content_area()
        area.set_border_width(8)
        area.pack_start(label("One official per line:  Name; Country; Primary position  (country and position optional; "
                              "position must match a title in the Positions tab)", wrap=True), False, False, 4)
        tv = Gtk.TextView()
        tv.set_monospace(True)
        area.pack_start(scrolled(tv, 300), True, True, 0)
        d.show_all()
        resp = d.run()
        buf = tv.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        d.destroy()
        if resp not in (1, 2):
            return
        rows = []
        for line in text.splitlines():
            parts = [p.strip() for p in re.split(r"[;\t]", line)]
            if not parts or not parts[0]:
                continue
            o = E.new_official(parts[0])
            if len(parts) > 1:
                o["country"] = parts[1]
            if len(parts) > 2:
                o["primary"] = self.pos_by_title.get(parts[2], "")
            rows.append(o)

        def apply():
            if resp == 1:
                self.ev["officials"] = []
                self.ev["assignments"] = {}
            names = {o["name"] for o in self.ev["officials"]}
            for o in rows:
                if o["name"] not in names:
                    self.ev["officials"].append(o)
                    names.add(o["name"])
        self.edit(apply)

    # ------------------------------------------------------------------ tab: who works which race
    def _tab_participation(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        box.pack_start(label("Tick the races each official works. Unticked = the planner never gives that person a job "
                             "in that race (all-day jobs need every race of that day ticked). Use this for officials who "
                             "come only for some days or only for some races.", wrap=True), False, False, 0)
        self.part_grid = Gtk.Grid(column_spacing=10, row_spacing=2)
        self.part_grid.set_halign(Gtk.Align.START)
        box.pack_start(self.part_grid, False, False, 0)
        self._part_sig = None
        self.nb.append_page(page(box), Gtk.Label(label="Who works which race"))

    def _fill_participation(self):
        races = E.races_sorted(self.ev)
        offs = self.ev["officials"]
        fmt = self.result["fmt"]
        sig = json.dumps([[r["id"], r["name"], r.get("date"), r["start"]] for r in races] +
                         [[o["name"], o.get("races", {})] for o in offs], sort_keys=True)
        if sig == self._part_sig:
            return
        self._part_sig = sig
        for ch in self.part_grid.get_children():
            self.part_grid.remove(ch)
        self._loading = True
        self.part_grid.attach(label("Official", bold=True, wrap=False), 0, 0, 1, 1)
        for c, r in enumerate(races, 1):
            hdr = label(f"{r['name']}\n{fmt(self.result['timelines'][r['id']]['start'])}", bold=True)
            hdr.set_max_width_chars(18)
            self.part_grid.attach(hdr, c, 0, 1, 1)
        self.part_grid.attach(label("All", bold=True, wrap=False), len(races) + 1, 0, 1, 1)
        for i, o in enumerate(offs, 1):
            self.part_grid.attach(label(o["name"], wrap=False), 0, i, 1, 1)
            for c, r in enumerate(races, 1):
                cb = Gtk.CheckButton()
                cb.set_active(E.takes_part(o, r["id"]))
                cb.set_halign(Gtk.Align.CENTER)
                cb.connect("toggled", self._on_part_toggle, o["name"], r["id"])
                self.part_grid.attach(cb, c, i, 1, 1)
            allb = Gtk.Button(label="all / none")
            allb.connect("clicked", lambda w, n=o["name"]: self._on_part_row(n))
            self.part_grid.attach(allb, len(races) + 1, i, 1, 1)
        n = len(offs) + 1
        self.part_grid.attach(label("Whole race", bold=True, wrap=False), 0, n, 1, 1)
        for c, r in enumerate(races, 1):
            b = Gtk.Button(label="all / none")
            b.connect("clicked", lambda w, rid=r["id"]: self._on_part_col(rid))
            self.part_grid.attach(b, c, n, 1, 1)
        self.part_grid.attach(label("Officials per race", dim=True, wrap=False), 0, n + 1, 1, 1)
        for c, r in enumerate(races, 1):
            cnt = sum(1 for o in offs if E.takes_part(o, r["id"]))
            self.part_grid.attach(label(str(cnt), xalign=0.5, wrap=False), c, n + 1, 1, 1)
        self.part_grid.show_all()
        self._loading = False

    def _official(self, name):
        return next((o for o in self.ev["officials"] if o["name"] == name), None)

    def _on_part_toggle(self, cb, name, rid):
        if self._loading:
            return
        o = self._official(name)
        if o is None:
            return
        val = cb.get_active()

        def apply():
            races = o.setdefault("races", {})
            if val:
                races.pop(rid, None)
            else:
                races[rid] = False
        self.edit(apply)

    def _on_part_row(self, name):
        o = self._official(name)
        if o is None:
            return
        ids = [r["id"] for r in self.ev["races"]]
        all_on = all(E.takes_part(o, rid) for rid in ids)
        self.edit(lambda: o.__setitem__("races", {rid: False for rid in ids} if all_on else {}))

    def _on_part_col(self, rid):
        offs = self.ev["officials"]
        all_on = all(E.takes_part(o, rid) for o in offs)

        def apply():
            for o in offs:
                races = o.setdefault("races", {})
                if all_on:
                    races[rid] = False
                else:
                    races.pop(rid, None)
        self.edit(apply)

    # ------------------------------------------------------------------ tab: positions
    def _tab_positions(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        box.pack_start(label("Positions needed – ticked rows are the proposal from the TO Checklist and the rules. "
                             "Untick what you don't need, tick extras, or set a different number.", wrap=True), False, False, 0)
        # key, include, title, kind, count text, proposed count, toc, applies, note
        self.pos_store = Gtk.ListStore(str, bool, str, str, str, str, str, str, str)
        self.pos_tree = Gtk.TreeView(model=self.pos_store)
        toggle_column(self.pos_tree, "Use", 1, self._on_pos_toggle)
        text_column(self.pos_tree, "Position", 2, width=280, expand=True)
        text_column(self.pos_tree, "Type", 3, width=90)
        text_column(self.pos_tree, "Number (edit)", 4, True, self._on_pos_count, width=90)
        text_column(self.pos_tree, "Proposed", 5, width=70)
        text_column(self.pos_tree, "Reference", 6, width=120)
        text_column(self.pos_tree, "Applies to", 7, width=110)
        text_column(self.pos_tree, "Duty window", 8, width=300)
        box.pack_start(scrolled(self.pos_tree, 300), True, True, 0)
        bb = flow()
        b = Gtk.Button(label="Reset to proposal")
        b.connect("clicked", lambda w: self.edit(lambda: E.reset_positions(self.ev)))
        bb.add(b)
        b = Gtk.Button(label="Use all positions")
        b.connect("clicked", lambda w: self.edit(lambda: [v.__setitem__("enabled", True) for v in self.ev["positions"].values()]))
        bb.add(b)
        box.pack_start(bb, False, False, 0)
        box.pack_start(label("Type: primary = someone's main job; secondary = short job normally covered by someone in their "
                             "free time. Leave Number empty to use the proposed number.", dim=True), False, False, 0)
        self.nb.append_page(page(box), Gtk.Label(label="Positions"))

    APPLIES_TXT = {"all": "all races", "draft_legal": "draft-legal races", "non_drafting": "draft-illegal races",
                   "relay": "relay races", "laps": "multi-lap races", "run_laps": "multi-lap runs",
                   "wheel": "races with wheel stations", "aid": "races with aid stations", "bike_laps": "multi-lap bikes"}

    def _on_pos_toggle(self, renderer, path, idx):
        key = self.pos_store[path][0]
        cfg = self.ev["positions"].setdefault(key, {"enabled": False, "count": None})
        self.edit(lambda: cfg.__setitem__("enabled", not cfg.get("enabled")))

    def _on_pos_count(self, renderer, path, text, idx):
        key = self.pos_store[path][0]
        cfg = self.ev["positions"].setdefault(key, {"enabled": True, "count": None})
        t = text.strip()

        def apply():
            cfg["count"] = None if t == "" else max(0, int(to_float(t, 0)))
            if cfg["count"]:
                cfg["enabled"] = True
        self.edit(apply)

    # ------------------------------------------------------------------ tab: duty times & shifts
    def _tab_duties(self):
        box = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_border_width(10)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.pack_start(label("Duty times from the TO Checklist (pre-event, event, post-event) – all races", bold=True), False, False, 0)
        self.duty_store = Gtk.ListStore(str, str, str, str)
        tree = Gtk.TreeView(model=self.duty_store)
        text_column(tree, "Parameter", 1, width=360, expand=True)
        spin_column(tree, "Minutes", 2, -60, 240, 1, 0, self._on_duty_edit)
        text_column(tree, "Source", 3, width=200)
        left.pack_start(scrolled(tree, 300), True, True, 0)
        b = Gtk.Button(label="Reset all duty times")
        b.connect("clicked", lambda w: self.edit(lambda: self.ev.__setitem__("settings", E.duty_defaults())))
        left.pack_start(b, False, False, 0)
        box.pack1(left, True, True)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right.pack_start(label("Small adjustments per race – move a duty window earlier (−) or later (+)", bold=True), False, False, 0)
        hb = Gtk.Box(spacing=6)
        hb.pack_start(label("Race:"), False, False, 0)
        self.shift_race = Gtk.ComboBoxText()
        self.shift_race.connect("changed", lambda w: self._fill_shifts())
        hb.pack_start(self.shift_race, True, True, 0)
        right.pack_start(hb, False, False, 0)
        self.shift_store = Gtk.ListStore(str, str, str, str, str, str)
        st = Gtk.TreeView(model=self.shift_store)
        text_column(st, "Duty window", 1, width=240, expand=True)
        spin_column(st, "Start ± min", 2, -180, 180, 1, 0, self._on_shift_edit)
        spin_column(st, "End ± min", 3, -180, 180, 1, 0, self._on_shift_edit)
        text_column(st, "Now", 4, width=110)
        text_column(st, "Reference", 5, width=90)
        right.pack_start(scrolled(st, 300), True, True, 0)
        b = Gtk.Button(label="Clear adjustments for this race")
        b.connect("clicked", lambda w: self._clear_shifts())
        right.pack_start(b, False, False, 0)
        box.pack2(right, True, True)
        self.nb.append_page(page(box), Gtk.Label(label="Duty times & tweaks"))

    def _on_duty_edit(self, renderer, path, text, idx):
        key = self.duty_store[path][0]
        self.edit(lambda: self.ev["settings"].__setitem__(key, to_float(text, self.ev["settings"].get(key, 0))))

    def _shift_race_obj(self):
        rid = self.shift_race.get_active_id()
        return next((r for r in self.ev["races"] if r["id"] == rid), None)

    def _fill_shifts(self):
        self.shift_store.clear()
        race = self._shift_race_obj()
        if race is None:
            return
        tl = E.race_timeline(race)
        for key, a in ref.ACTIVITIES.items():
            if key in ("cro_prepost",):
                continue
            ds, de = race.get("shifts", {}).get(key, [0, 0])
            s, e = E.activity_window(key, tl, self.ev["settings"], race.get("shifts"))
            self.shift_store.append([key, a[0], f"{float(ds):+g}", f"{float(de):+g}", f"{E.fmt_hhmm(s)}–{E.fmt_hhmm(e)}", a[7]])

    def _on_shift_edit(self, renderer, path, text, idx):
        race = self._shift_race_obj()
        if race is None:
            return
        key = self.shift_store[path][0]

        def apply():
            sh = race.setdefault("shifts", {}).setdefault(key, [0, 0])
            sh[0 if idx == 2 else 1] = to_float(text, 0)
            if sh == [0, 0] or sh == [0.0, 0.0]:
                race["shifts"].pop(key, None)
        self.edit(apply)

    def _clear_shifts(self):
        race = self._shift_race_obj()
        if race is not None:
            self.edit(lambda: race.__setitem__("shifts", {}))

    # ------------------------------------------------------------------ tab: meetings & briefings
    def _tab_sessions(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        box.pack_start(label(
            "Obligations outside the races, generated from the rules: Elite athletes' briefing at 16:00 the day before "
            "the first competition day (CR 2.7 b), Jury meetings (CR 12.9), TOs' meeting, rehearsals, drivers' and "
            "medical meetings (EOM Table 14, 6.9, 6.11.4), familiarisation (EOM 3.2.8), daily TO briefing and "
            "de-briefing (EOM 2.13 e). Everyone who must attend is booked for that time, so the planner never puts "
            "them on a job that clashes. Untick a meeting that is not held, or edit its date and times.", wrap=True),
            False, False, 0)
        self.se_warn = label("", wrap=True)
        box.pack_start(self.se_warn, False, False, 0)
        # id, held, date, from, to, name, attendees, people, ref, bg, weight, custom
        self.se_store = Gtk.ListStore(str, bool, str, str, str, str, str, str, str, str, int, bool)
        self.se_tree = Gtk.TreeView(model=self.se_store)
        toggle_column(self.se_tree, "Held", 1, self._on_session_toggle)
        text_column(self.se_tree, "Date", 2, editable=True, on_edit=self._on_session_edit, width=105, bg_idx=9)
        text_column(self.se_tree, "From", 3, editable=True, on_edit=self._on_session_edit, width=55)
        text_column(self.se_tree, "To", 4, editable=True, on_edit=self._on_session_edit, width=55)
        text_column(self.se_tree, "Meeting / briefing", 5, editable=True, on_edit=self._on_session_edit, width=260,
                    weight_idx=10)
        self.se_preset_model = str_model(list(ref.SESSION_PRESETS))
        combo_column(self.se_tree, "Who must attend", 6, self.se_preset_model, self._on_session_who, width=220)
        text_column(self.se_tree, "People", 7, width=260, expand=True)
        text_column(self.se_tree, "Rule / reference", 8, width=220)
        box.pack_start(scrolled(self.se_tree, 300), True, True, 0)
        bb = flow()
        for txt, cb, tip in (("Add meeting…", self.on_add_session, "Add your own meeting, e.g. a welcome dinner"),
                             ("Remove added meeting", self.on_del_session, "Only meetings you added can be removed"),
                             ("Reset selected to rules", self.on_reset_session, "Undo your changes to the selected meeting"),
                             ("Reset all to rules", self.on_reset_sessions, "Undo all changes to rule-based meetings")):
            b = Gtk.Button(label=txt)
            b.set_tooltip_text(tip)
            b.connect("clicked", lambda w, c=cb: c())
            bb.add(b)
        box.pack_start(bb, False, False, 0)
        box.pack_start(label("Dates as YYYY-MM-DD, times as HH:MM. For meetings you added, the name and "
                             "'Who must attend' can be changed too. Moving the Elite briefing away from 16:00 "
                             "shows a warning (CR 2.7 b(vii), b(ix)).", dim=True), False, False, 0)
        self.nb.append_page(page(box), Gtk.Label(label="Meetings & briefings"))

    def _session_path(self, path):
        row = self.se_store[path]
        return row[0], row[11]

    def _custom_session(self, sid):
        return next((c for c in self.ev.get("custom_sessions", []) if c.get("id") == sid), None)

    def _on_session_toggle(self, renderer, path, idx):
        sid, custom = self._session_path(path)
        val = not self.se_store[path][1]

        def apply():
            if custom:
                self._custom_session(sid)["enabled"] = val
            else:
                self.ev.setdefault("sessions", {}).setdefault(sid, {})["enabled"] = val
        self.edit(apply)

    def _on_session_edit(self, renderer, path, text, idx):
        sid, custom = self._session_path(path)
        text = (text or "").strip()
        field_ = {2: "date", 3: "start", 4: "end", 5: "name"}[idx]
        if field_ == "date" and not E.parse_date(text):
            self.toast("Date must be YYYY-MM-DD")
            return
        if field_ in ("start", "end"):
            m = E.parse_hhmm(text)
            if m is None:
                self.toast("Time must be HH:MM")
                return
            text = E.fmt_hhmm(m)
        if field_ == "name" and not custom:
            self.toast("Rule-based meetings keep their name – add your own meeting instead")
            return

        def apply():
            if custom:
                self._custom_session(sid)[field_] = text
            else:
                self.ev.setdefault("sessions", {}).setdefault(sid, {})[field_] = text
        self.edit(apply)

    def _on_session_who(self, renderer, path, text, idx):
        sid, custom = self._session_path(path)
        if not custom:
            self.toast("Who attends a rule-based meeting follows the rules – add your own meeting instead")
            return
        if text in ref.SESSION_PRESETS:
            self.edit(lambda: self._custom_session(sid).__setitem__("attendees", list(ref.SESSION_PRESETS[text])))

    def _selected_session(self):
        model, it = self.se_tree.get_selection().get_selected()
        if it is None:
            return None, False
        return model[it][0], model[it][11]

    def on_add_session(self):
        d = Gtk.Dialog(title="Add meeting", transient_for=self, modal=True)
        d.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Add", Gtk.ResponseType.OK)
        g = Gtk.Grid(column_spacing=8, row_spacing=6)
        g.set_border_width(10)
        name, date, st, en = Gtk.Entry(), Gtk.Entry(), Gtk.Entry(), Gtk.Entry()
        name.set_text("Meeting")
        days = self.result["dates"] if self.result else E.event_dates(self.ev)
        date.set_text(days[0].isoformat())
        st.set_text("19:00")
        en.set_text("20:00")
        who = Gtk.ComboBoxText()
        for k in ref.SESSION_PRESETS:
            who.append(k, k)
        who.set_active_id("All TOs + TD")
        for i, (t, w) in enumerate((("Name", name), ("Date (YYYY-MM-DD)", date), ("From (HH:MM)", st),
                                    ("To (HH:MM)", en), ("Who must attend", who))):
            g.attach(label(t), 0, i, 1, 1)
            g.attach(w, 1, i, 1, 1)
        d.get_content_area().add(g)
        d.show_all()
        resp = d.run()
        vals = (name.get_text().strip(), date.get_text().strip(), st.get_text().strip(), en.get_text().strip(),
                who.get_active_id() or "All TOs")
        d.destroy()
        if resp != Gtk.ResponseType.OK:
            return
        if not E.parse_date(vals[1]) or E.parse_hhmm(vals[2]) is None or E.parse_hhmm(vals[3]) is None:
            self.toast("Check the date (YYYY-MM-DD) and times (HH:MM)")
            return
        item = {"id": E.new_id("s"), "name": vals[0] or "Meeting", "date": vals[1], "start": vals[2], "end": vals[3],
                "attendees": list(ref.SESSION_PRESETS[vals[4]]), "enabled": True}
        self.edit(lambda: self.ev.setdefault("custom_sessions", []).append(item))

    def on_del_session(self):
        sid, custom = self._selected_session()
        if not sid:
            return
        if not custom:
            self.toast("Rule-based meetings can't be removed – untick 'Held' if it does not take place")
            return
        self.edit(lambda: self.ev.__setitem__("custom_sessions",
                                              [c for c in self.ev.get("custom_sessions", []) if c.get("id") != sid]))

    def on_reset_session(self):
        sid, custom = self._selected_session()
        if sid and not custom:
            self.edit(lambda: self.ev.setdefault("sessions", {}).pop(sid, None))

    def on_reset_sessions(self):
        self.edit(lambda: self.ev.__setitem__("sessions", {}))

    def _fill_sessions(self):
        res = self.result
        sel, _c = self._selected_session()

        def do():
            self.se_store.clear()
            for se in sorted(res["sessions"], key=lambda x: (x["s"], x["e"])):
                bg = "#EADCF5" if se["enabled"] else "#EEEEEE"
                if se.get("edited") or se.get("custom"):
                    bg = "#FFF2CC" if se["enabled"] else "#EEEEEE"
                name = se["name"] + (" (edited)" if se.get("edited") else "")
                self.se_store.append([se["id"], se["enabled"], se["date"].isoformat(), E.fmt_hhmm(se["start"]),
                                      E.fmt_hhmm(se["end"]), name, E.attendee_label(se["attendees"]),
                                      ", ".join(se.get("people", [])) or "—", se["ref"], bg,
                                      700 if se["key"] == "athletes_briefing" else 400, bool(se.get("custom"))])
        self._keep_scroll(self.se_tree, do)
        if sel:
            for row in self.se_store:
                if row[0] == sel:
                    self.se_tree.get_selection().select_iter(row.iter)
        w = res.get("warnings", [])
        held = sum(1 for se in res["sessions"] if se["enabled"])
        txt = f"<b>{held}</b> meetings and briefings in the plan."
        if w:
            txt += "\n" + "\n".join(f"<span background='{STATUS_BG['TIGHT']}'> ⚠ </span> {GLib.markup_escape_text(x)}" for x in w)
        self.se_warn.set_markup(txt)

    # ------------------------------------------------------------------ tab: assignments
    def _tab_assignments(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        self.summary = label("", wrap=True)
        box.pack_start(self.summary, False, False, 0)
        fb = Gtk.Box(spacing=6)
        fb.pack_start(label("Filter:"), False, False, 0)
        self.a_search = Gtk.SearchEntry()
        self.a_search.set_width_chars(14)
        self.a_search.set_placeholder_text("position or name…")
        self.a_search.connect("search-changed", lambda w: self._fill_assignments())
        fb.pack_start(self.a_search, True, True, 0)
        self.a_race = Gtk.ComboBoxText()
        self.a_race.connect("changed", lambda w: self._fill_assignments())
        fb.pack_start(self.a_race, False, False, 0)
        self.a_problems = Gtk.CheckButton(label="Only problems")
        self.a_problems.connect("toggled", lambda w: self._fill_assignments())
        fb.pack_start(self.a_problems, False, False, 0)
        box.pack_start(fb, False, False, 0)
        # key, position, race, official, role, from, to, status, bg, locked, toc, weight
        self.a_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, bool, str, int)
        self.a_tree = Gtk.TreeView(model=self.a_store)
        self.off_combo_model = Gtk.ListStore(str)
        text_column(self.a_tree, "Position", 1, width=280, expand=True, weight_idx=11)
        text_column(self.a_tree, "Race", 2, width=140)
        combo_column(self.a_tree, "Name and surname (choose)", 3, self.off_combo_model, self._on_assign_edit, width=200, bg_idx=8)
        text_column(self.a_tree, "Role", 4, width=80)
        text_column(self.a_tree, "From", 5, width=55)
        text_column(self.a_tree, "To", 6, width=55)
        text_column(self.a_tree, "Status", 7, width=90, bg_idx=8)
        toggle_column(self.a_tree, "Locked", 9, self._on_assign_lock)
        text_column(self.a_tree, "Reference", 10, width=110)
        box.pack_start(scrolled(self.a_tree, 300), True, True, 0)
        bb = flow()
        for txt, cb, tip in (("Auto-assign (keep locked)", lambda: self.on_auto(True), "Re-plan all rows that are not locked"),
                             ("Re-plan from scratch", lambda: self.on_auto(False), "Ignore all locks and plan again"),
                             ("Clear unlocked", lambda: self.edit(lambda: E.clear_unlocked(self.ev), replan=False), ""),
                             ("Lock all", lambda: self.edit(lambda: E.lock_all(self.ev, True), replan=False), "Freeze the current plan"),
                             ("Unlock all", lambda: self.edit(lambda: E.lock_all(self.ev, False), replan=False), ""),
                             ("Swap two officials…", self.on_swap, "Exchange all jobs of two people")):
            b = Gtk.Button(label=txt)
            if tip:
                b.set_tooltip_text(tip)
            b.connect("clicked", lambda w, c=cb: c())
            bb.add(b)
        box.pack_start(bb, False, False, 0)
        box.pack_start(label("Choosing a name locks the row. Locked rows are never changed by the planner. "
                             "Choose 'LOC / volunteer' to leave a job deliberately without a TO.", dim=True), False, False, 0)
        self.nb.append_page(page(box), Gtk.Label(label="Assignments"))

    def _on_assign_edit(self, renderer, path, text, idx):
        key = self.a_store[path][0]
        if text == UNASSIGNED:
            self.edit(lambda: self.ev["assignments"].pop(key, None), replan=False)
        elif text == LOC_VOL:
            self.edit(lambda: E.set_assignment(self.ev, key, "", True), replan=False)
        else:
            self.edit(lambda: E.set_assignment(self.ev, key, text, True), replan=False)

    def _on_assign_lock(self, renderer, path, idx):
        key = self.a_store[path][0]
        v = self.ev["assignments"].get(key)
        if v is None:
            return
        self.edit(lambda: v.__setitem__("locked", not v.get("locked")), replan=False)

    def on_swap(self, *a):
        names = [o["name"] for o in self.ev["officials"]]
        if len(names) < 2:
            return
        d = Gtk.Dialog(title="Swap two officials", transient_for=self, modal=True)
        d.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Swap", Gtk.ResponseType.OK)
        g = Gtk.Grid(column_spacing=8, row_spacing=6)
        g.set_border_width(10)
        ca, cb = Gtk.ComboBoxText(), Gtk.ComboBoxText()
        for n in names:
            ca.append_text(n)
            cb.append_text(n)
        ca.set_active(0)
        cb.set_active(1)
        g.attach(label("Official A"), 0, 0, 1, 1)
        g.attach(ca, 1, 0, 1, 1)
        g.attach(label("Official B"), 0, 1, 1, 1)
        g.attach(cb, 1, 1, 1, 1)
        g.attach(label("All jobs (primary and secondary) are exchanged and locked.", dim=True), 0, 2, 2, 1)
        d.get_content_area().add(g)
        d.show_all()
        resp = d.run()
        a_, b_ = ca.get_active_text(), cb.get_active_text()
        d.destroy()
        if resp != Gtk.ResponseType.OK or not a_ or not b_ or a_ == b_:
            return

        def apply():
            for v in self.ev["assignments"].values():
                if v.get("official") == a_:
                    v["official"], v["locked"] = b_, True
                elif v.get("official") == b_:
                    v["official"], v["locked"] = a_, True
            offs = {o["name"]: o for o in self.ev["officials"]}
            offs[a_]["primary"], offs[b_]["primary"] = offs[b_].get("primary", ""), offs[a_].get("primary", "")
            prim = self.ev.setdefault("_primary", {})
            prim[a_], prim[b_] = prim.get(b_), prim.get(a_)
        self.edit(apply, replan=False)

    # ------------------------------------------------------------------ tab: personal schedules
    def _tab_personal(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        box.pack_start(label("Personal schedule of every official (expand a name)", bold=True), False, False, 0)
        self.p_store = Gtk.TreeStore(str, str, str, str, str, str, str, str, int)
        self.p_tree = Gtk.TreeView(model=self.p_store)
        text_column(self.p_tree, "Official / position", 0, width=300, expand=True, weight_idx=8)
        text_column(self.p_tree, "From", 1, width=55)
        text_column(self.p_tree, "To", 2, width=55)
        text_column(self.p_tree, "Race", 3, width=140)
        text_column(self.p_tree, "Duty", 4, width=240)
        text_column(self.p_tree, "Role", 5, width=80)
        text_column(self.p_tree, "Status", 6, width=90, bg_idx=7)
        box.pack_start(scrolled(self.p_tree, 300), True, True, 0)
        bb = flow()
        b = Gtk.Button(label="Expand all")
        b.connect("clicked", lambda w: self.p_tree.expand_all())
        bb.add(b)
        b = Gtk.Button(label="Collapse all")
        b.connect("clicked", lambda w: self.p_tree.collapse_all())
        bb.add(b)
        box.pack_start(bb, False, False, 0)
        self.nb.append_page(page(box), Gtk.Label(label="Personal schedules"))

    # ------------------------------------------------------------------ tab: gantt
    def _tab_gantt(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(6)
        tb = flow()
        tb.add(label("Rows:"))
        self.g_day = Gtk.ComboBoxText()
        self.g_day.set_tooltip_text("Event day shown in the Gantt")
        self.g_day.connect("changed", lambda w: None if self._loading else self.refresh_gantt())
        tb.add(label("Day:", wrap=False))
        tb.add(self.g_day)
        self.g_mode = Gtk.ComboBoxText()
        self.g_mode.append("officials", "Officials")
        self.g_mode.append("positions", "Positions")
        self.g_mode.set_active_id("officials")
        self.g_mode.connect("changed", lambda w: self.refresh_gantt())
        tb.add(self.g_mode)
        tb.add(label("Zoom (px per minute):"))
        self.g_zoom = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1.0, 12.0, 0.5)
        self.g_zoom.set_value(4.0)
        self.g_zoom.set_size_request(200, -1)
        self.g_zoom.connect("value-changed", lambda w: self._queue_gantt())
        tb.add(self.g_zoom)
        self.g_dark = Gtk.CheckButton(label="Dark")
        self.g_dark.connect("toggled", lambda w: self.refresh_gantt())
        tb.add(self.g_dark)
        b = Gtk.Button(label="Export SVG…")
        b.set_action_name("win.export_svg")
        tb.add(b)
        b = Gtk.Button(label="Open in image viewer")
        b.connect("clicked", lambda w: self.on_open_gantt_external())
        tb.add(b)
        box.pack_start(tb, False, False, 0)
        self.g_image = Gtk.Image()
        self.g_image.set_halign(Gtk.Align.START)
        self.g_image.set_valign(Gtk.Align.START)
        self.g_msg = label("", wrap=True)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vb.pack_start(self.g_msg, False, False, 0)
        vb.pack_start(self.g_image, False, False, 0)
        box.pack_start(scrolled(vb, 300), True, True, 0)
        self._gantt_src = None
        self._gantt_page = self.nb.append_page(box, Gtk.Label(label="Gantt"))

    def _queue_gantt(self):
        if getattr(self, "_gantt_timer", None):
            GLib.source_remove(self._gantt_timer)
        self._gantt_timer = GLib.timeout_add(250, self._gantt_timeout)

    def _gantt_timeout(self):
        self._gantt_timer = None
        self.refresh_gantt()
        return False

    def refresh_gantt(self):
        if self.result is None:
            return
        days = [d.isoformat() for d in self.result["dates"]]
        cur = self.g_day.get_active_id()
        self._loading = True
        self.g_day.remove_all()
        for d in self.result["dates"]:
            self.g_day.append(d.isoformat(), f"{E.day_label(d)} {d.isoformat()}")
        first_race = E.race_dates(self.ev)[0].isoformat()
        self.g_day.set_active_id(cur if cur in days else (first_race if first_race in days else days[0]))
        self._loading = False
        svg = X.gantt_svg(self.ev, self.result, day=self.g_day.get_active_id(), mode=self.g_mode.get_active_id() or "officials",
                          px_per_min=self.g_zoom.get_value(), dark=self.g_dark.get_active())
        self._gantt_src = svg
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(svg.encode("utf-8"))
            loader.close()
            self.g_image.set_from_pixbuf(loader.get_pixbuf())
            self.g_msg.set_text("")
        except GLib.Error as err:
            self.g_image.clear()
            self.g_msg.set_text("The SVG image loader is missing (install package librsvg2-common). "
                                f"Use 'Open in image viewer' or export the SVG. ({err.message})")

    def on_open_gantt_external(self):
        if not self._gantt_src:
            self.refresh_gantt()
        fd, path = tempfile.mkstemp(prefix="wt-gantt-", suffix=".svg")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(self._gantt_src or "")
        Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(path, None), None)

    # ------------------------------------------------------------------ tab: timeline
    def _tab_timeline(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        box.pack_start(label("Race timeline – all races in time order (from paces, field spread and the Masterfile schedule)", bold=True),
                       False, False, 0)
        self.t_store = Gtk.ListStore(str, str, str, str, int)
        tree = Gtk.TreeView(model=self.t_store)
        text_column(tree, "Time", 0, width=60, weight_idx=4)
        text_column(tree, "Race", 1, width=200, bg_idx=3)
        text_column(tree, "Milestone", 2, width=300, expand=True, weight_idx=4)
        box.pack_start(scrolled(tree, 260), True, True, 0)
        box.pack_start(label("Splits per race", bold=True), False, False, 0)
        self.s_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, str, str)
        st = Gtk.TreeView(model=self.s_store)
        for i, t in enumerate(["Race", "Start", "Swim", "T1", "Bike", "T2", "Run", "Leg time", "Winner", "Last finisher", "Medals"]):
            text_column(st, t, i, width=70 if i else 200)
        box.pack_start(scrolled(st, 110), False, False, 0)
        self.nb.append_page(page(box), Gtk.Label(label="Timeline"))

    # ------------------------------------------------------------------ tab: athletes' guide
    def _tab_athletes(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(10)
        box.pack_start(label("Athletes’ guide – only what athletes need: briefing, familiarisation and race-day times, the course "
                             "and the key rules. No officials’ meetings or jobs. Save it as a page athletes can open on any phone "
                             "or print, or as a calendar.", wrap=True), False, False, 0)
        self.ath_race = Gtk.ComboBoxText()
        self.ath_race.connect("changed", lambda w: (not self._ath_filling) and self._fill_athletes())
        self._ath_filling = False
        b1 = Gtk.Button(label="Save athletes’ guide (.html)…")
        b1.connect("clicked", lambda w: self.on_export_athletes("html"))
        b2 = Gtk.Button(label="Save athletes’ calendar (.ics)…")
        b2.connect("clicked", lambda w: self.on_export_athletes("ics"))
        box.pack_start(flow(field("Race", self.ath_race), b1, b2), False, False, 0)
        self.ath_brief = Gtk.Entry()
        self.ath_brief.set_placeholder_text("e.g. Hotel ballroom, 1st floor")
        self.ath_brief.set_width_chars(34)
        self.ath_office = Gtk.Entry()
        self.ath_office.set_placeholder_text("e.g. Race office at the expo, 09:00–18:00")
        self.ath_office.set_width_chars(34)
        for w, key in ((self.ath_brief, "briefing_location"), (self.ath_office, "office")):
            w.connect("activate", lambda e, k=key: self._ath_set(k, e.get_text()))
            w.connect("focus-out-event", lambda e, ev, k=key: self._ath_set(k, e.get_text()) or False)
        self.ath_notes = Gtk.TextView()
        self.ath_notes.set_wrap_mode(Gtk.WrapMode.WORD)
        self.ath_notes.set_size_request(-1, 60)
        self.ath_notes.connect("focus-out-event", lambda w, ev: self._ath_set("notes", self._tv_text(w)) or False)
        nsw = scrolled(self.ath_notes, 60)
        nsw.set_vexpand(False)
        box.pack_start(flow(field("Briefing location", self.ath_brief), field("Race office / packet pick-up", self.ath_office)),
                       False, False, 0)
        box.pack_start(label("Notes for athletes (shown at the top of the saved guide)", dim=True), False, False, 0)
        box.pack_start(nsw, False, False, 0)
        pan = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        # time, item, details, weight, bg
        self.ath_store = Gtk.ListStore(str, str, str, int, str)
        tree = Gtk.TreeView(model=self.ath_store)
        text_column(tree, "Time", 0, width=110, weight_idx=3, bg_idx=4)
        text_column(tree, "Schedule", 1, width=280, weight_idx=3, bg_idx=4)
        text_column(tree, "What to do", 2, width=320, expand=True, bg_idx=4)
        pan.pack1(scrolled(tree, 320), True, True)
        self.ath_text = Gtk.TextView()
        self.ath_text.set_editable(False)
        self.ath_text.set_wrap_mode(Gtk.WrapMode.WORD)
        self.ath_text.set_left_margin(10)
        self.ath_text.set_top_margin(8)
        buf = self.ath_text.get_buffer()
        buf.create_tag("h", weight=700, scale=1.15)
        buf.create_tag("b", weight=700)
        pan.pack2(scrolled(self.ath_text, 320), True, True)
        box.pack_start(pan, True, True, 0)
        box.pack_start(label("Times marked ≈ are estimates from typical race times. The athletes’ briefing and official race "
                             "information prevail.", dim=True), False, False, 0)
        self.nb.append_page(page(box), Gtk.Label(label="Athletes’ guide"))

    @staticmethod
    def _tv_text(tv):
        b = tv.get_buffer()
        return b.get_text(b.get_start_iter(), b.get_end_iter(), False)

    def _ath_set(self, key, value):
        cur = ATH.info(self.ev)
        if cur.get(key, "") == value:
            return
        def apply():
            a = dict(ATH.info(self.ev))
            a[key] = value
            self.ev["event"]["athletes"] = a
        self.edit(apply, replan=False, coalesce="ath-" + key)

    def _fill_athletes(self):
        if not self.result:
            return
        races = E.races_sorted(self.ev)
        want = [("", "All races")] + [(r["id"], r["name"]) for r in races]
        cur = self.ath_race.get_active_id() or ""
        have = [(row[1], row[0]) for row in self.ath_race.get_model()] if self.ath_race.get_model() else []
        if have != want:
            self._ath_filling = True
            self.ath_race.remove_all()
            for rid, name in want:
                self.ath_race.append(rid, name)
            self.ath_race.set_active_id(cur if any(rid == cur for rid, _ in want) else "")
            self._ath_filling = False
        race_id = self.ath_race.get_active_id() or ""
        inf = ATH.info(self.ev)
        if not self.ath_brief.has_focus():
            self.ath_brief.set_text(inf["briefing_location"])
        if not self.ath_office.has_focus():
            self.ath_office.set_text(inf["office"])
        if not self.ath_notes.has_focus() and self._tv_text(self.ath_notes) != inf["notes"]:
            self.ath_notes.get_buffer().set_text(inf["notes"])
        self.ath_store.clear()
        day = None
        for it in ATH.items(self.ev, self.result, race_id):
            if it["date"] != day:
                day = it["date"]
                self.ath_store.append(["", ATH.long_date(day).upper(), "", 700, "#E8ECF2"])
            key = it["kind"] in ("start", "athletes_briefing")
            self.ath_store.append([ATH.time_text(it), it["title"], it["text"], 700 if key else 400, "#EEF4FD" if key else "#FFFFFF"])
        buf = self.ath_text.get_buffer()
        buf.set_text("")
        it_ = buf.get_end_iter()
        buf.insert_with_tags_by_name(it_, "Course\n", "h")
        for r in [r for r in races if not race_id or r["id"] == race_id]:
            buf.insert_with_tags_by_name(buf.get_end_iter(), f"{r['name']} – start {self.result['fmt'](self.result['timelines'][r['id']]['start'])}\n", "b")
            for a, b in ATH.course(self.ev, r):
                buf.insert(buf.get_end_iter(), f"   {a}: {b}\n")
        buf.insert_with_tags_by_name(buf.get_end_iter(), "\nKey rules\n", "h")
        for x in ATH.rules(self.ev, race_id):
            buf.insert(buf.get_end_iter(), f"• {x}\n")

    def on_export_athletes(self, kind):
        race_id = self.ath_race.get_active_id() or ""
        ext = ".html" if kind == "html" else ".ics"
        pats = ("Web page", "*.html") if kind == "html" else ("iCalendar", "*.ics")
        folder = os.path.dirname(self.path) if self.path else GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
        p = self._file_dialog("Save athletes’ guide", Gtk.FileChooserAction.SAVE,
                              self._default_name("_athletes" + ext), folder, patterns=(pats,))
        if not p:
            return
        if not p.endswith(ext):
            p += ext
        res = self.result or E.evaluate(self.ev)
        try:
            text = ATH.guide_html(self.ev, res, race_id) if kind == "html" else ATH.guide_ics(self.ev, res, race_id)
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(text)
        except OSError as err:
            self.info("Could not save", str(err), Gtk.MessageType.ERROR)
            return
        self.toast(f"Saved {os.path.basename(p)}", open_path=p)

    # ------------------------------------------------------------------ tab: conflicts
    def _tab_conflicts(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)
        self.c_label = label("", wrap=True)
        box.pack_start(self.c_label, False, False, 0)
        self.c_store = Gtk.ListStore(str, str, str, str, str, str, str, str, str, str)
        tree = Gtk.TreeView(model=self.c_store)
        for i, (t, w) in enumerate([("Level", 80), ("Official", 160), ("Position A", 200), ("Duty A", 170), ("Time A", 90),
                                    ("Position B", 200), ("Duty B", 170), ("Time B", 90), ("Gap (min)", 60)]):
            text_column(tree, t, i, width=w, bg_idx=9 if i == 0 else None)
        box.pack_start(scrolled(tree, 300), True, True, 0)
        box.pack_start(label("TIGHT = less than the hand-over buffer between two jobs; CONFLICT = jobs overlap. "
                             "Fix by choosing another person in Assignments, moving a duty window in 'Duty times & tweaks', "
                             "or adding an official.", dim=True, wrap=True), False, False, 0)
        self.nb.append_page(page(box), Gtk.Label(label="Conflicts"))

    # ------------------------------------------------------------------ tab: references
    def _tab_references(self):
        tv = Gtk.TextView()
        tv.set_editable(False)
        tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.set_left_margin(12)
        tv.set_top_margin(12)
        lines = [ref.REFERENCES, "", "Race formats"]
        for k in ref.FORMAT_ORDER:
            f = ref.FORMATS[k]
            lines.append(f"• {f['label']}: {f['ref']}")
        lines += ["", "Positions and their reference"]
        for p in sorted(ref.POSITION_INDEX.values(), key=lambda p: p["priority"]):
            acts = ", ".join(ref.ACTIVITIES[a][0] for a in p["activities"])
            lines.append(f"• {p['title']} ({p['toc']}) – {acts}")
        lines += ["", "Duty-time defaults"]
        for k, v, lb, src in ref.DUTY_DEFAULTS:
            lines.append(f"• {lb}: {v} min – {src}")
        tv.get_buffer().set_text("\n".join(lines))
        self.nb.append_page(scrolled(tv, 300), Gtk.Label(label="References"))

    # ------------------------------------------------------------------ editing core
    def edit(self, fn, replan=True, coalesce=None):
        """Every change goes through here: undo snapshot, apply, re-plan, refresh."""
        if self._loading:
            return
        snap = json.dumps(self.ev)
        if not (coalesce and getattr(self, "_last_coalesce", None) == coalesce):
            self.undo.append(snap)
            self.undo = self.undo[-80:]
        self._last_coalesce = coalesce
        self.redo.clear()
        fn()
        if replan and self.auto_mode:
            E.auto_assign(self.ev, keep_locked=True)
        self.set_dirty(True)
        self.queue_refresh()

    def on_undo(self, *a):
        if not self.undo:
            return
        self.redo.append(json.dumps(self.ev))
        self.ev = E.normalise(json.loads(self.undo.pop()))
        self._last_coalesce = None
        self.set_dirty(True)
        self._load_event_fields()
        self.queue_refresh()

    def on_redo(self, *a):
        if not self.redo:
            return
        self.undo.append(json.dumps(self.ev))
        self.ev = E.normalise(json.loads(self.redo.pop()))
        self._last_coalesce = None
        self.set_dirty(True)
        self._load_event_fields()
        self.queue_refresh()

    def on_auto(self, keep=True):
        self.edit(lambda: E.auto_assign(self.ev, keep_locked=keep), replan=False)

    def set_dirty(self, d):
        self.dirty = d
        name = self.ev["event"].get("name") or "Untitled"
        self.hb.props.title = ("• " if d else "") + name
        self.hb.set_subtitle(self.path or "not saved yet")

    def queue_refresh(self):
        if not self._refresh_pending:
            self._refresh_pending = True
            GLib.idle_add(self._do_refresh)

    def _do_refresh(self):
        self._refresh_pending = False
        self.refresh_all()
        return False

    # ------------------------------------------------------------------ refresh views
    def refresh_all(self):
        try:
            self.result = E.evaluate(self.ev)
        except Exception as err:  # keep the window alive on odd input
            self.summary.set_text(f"Could not calculate: {err}")
            return
        self._fill_races()
        self._fill_officials()
        self._fill_participation()
        self._fill_positions()
        self._fill_duties()
        self._fill_sessions()
        self._fill_shift_races()
        self._fill_assignments()
        self._fill_personal()
        self._fill_timeline()
        self._fill_athletes()
        self._fill_conflicts()
        self._update_race_summary()
        if self.nb.get_current_page() == self._gantt_page:
            self.refresh_gantt()

    def _keep_scroll(self, tree, fn):
        sw = tree.get_parent()
        adj = sw.get_vadjustment() if isinstance(sw, Gtk.ScrolledWindow) else None
        val = adj.get_value() if adj else 0
        fn()
        if adj:
            GLib.idle_add(lambda: adj.set_value(val) and False)

    def _fill_races(self):
        def do():
            sel = self.selected_race
            self.race_store.clear()
            for r in E.races_sorted(self.ev):
                g = lambda v: f"{float(v):g}"
                self.race_store.append([r["id"], r["name"], ref.FORMATS[r["format"]]["label"],
                                        ref.CATEGORIES[r["category"]]["label"], r["start"], g(r["legs"]),
                                        g(r["swim_m"]), g(r["bike_km"]), g(r["run_km"]),
                                        g(r["laps"]["swim"]), g(r["laps"]["bike"]), g(r["laps"]["run"]),
                                        g(r["wheel_stations"]), g(r["aid_stations"]), g(r["start_line"]),
                                        bool(r["draft_legal"]), E.race_date(self.ev, r).isoformat()])
            for row in self.race_store:
                if row[0] == sel:
                    self.race_tree.get_selection().select_iter(row.iter)
                    break
            else:
                if len(self.race_store):
                    self.race_tree.get_selection().select_path(Gtk.TreePath.new_first())
        self._keep_scroll(self.race_tree, do)
        self._load_race_tweaks()

    def _fill_officials(self):
        def do():
            self.off_store.clear()
            for i, o in enumerate(self.ev["officials"]):
                prim = ref.POSITION_INDEX.get(o.get("primary") or "", {}).get("title", AUTO)
                self.off_store.append([o["name"], o.get("country", ""), prim, str(int(o.get("max_secondary", 3))),
                                       o.get("available_from", ""), o.get("available_to", ""), bool(o.get("radio", True)),
                                       o.get("notes", ""), i])
        self._keep_scroll(self.off_tree, do)
        self._loading = True
        self.n_off.set_value(len(self.ev["officials"]))
        self._loading = False

    def _fill_positions(self):
        def do():
            self.pos_store.clear()
            for p in sorted(ref.POSITION_INDEX.values(), key=lambda p: p["priority"]):
                cfg = self.ev["positions"].get(p["key"], {})
                pc = E.proposed_count(self.ev, p)
                cnt = "" if cfg.get("count") in (None, "") else str(cfg["count"])
                acts = "; ".join(ref.ACTIVITIES[a][0] for a in p["activities"])
                self.pos_store.append([p["key"], bool(cfg.get("enabled", p["proposed"])), p["title"], p["kind"], cnt,
                                       f"{pc}{' ✓' if p['proposed'] else ''}", p["toc"],
                                       self.APPLIES_TXT.get(p["applies"], p["applies"]),
                                       acts + (" · all day" if p["all_day"] else "")])
        self._keep_scroll(self.pos_tree, do)

    def _fill_duties(self):
        self.duty_store.clear()
        for k, _v, lb, src in ref.DUTY_DEFAULTS:
            self.duty_store.append([k, lb, f"{float(self.ev['settings'].get(k, _v)):g}", src])

    def _fill_shift_races(self):
        cur = self.shift_race.get_active_id()
        self._loading = True
        self.shift_race.remove_all()
        for r in E.races_sorted(self.ev):
            self.shift_race.append(r["id"], f"{r['start']}  {r['name']}")
        if cur and any(r["id"] == cur for r in self.ev["races"]):
            self.shift_race.set_active_id(cur)
        else:
            self.shift_race.set_active(0)
        self._loading = False
        self._fill_shifts()
        # race filter on the assignment tab
        cur = self.a_race.get_active_id()
        self._loading = True
        self.a_race.remove_all()
        self.a_race.append("*", "All races")
        multi = self.result["multiday"] if self.result else False
        for d in (self.result["dates"] if self.result else []):
            self.a_race.append(E.day_key(d), f"All-day positions – {E.day_label(d)}" if multi else "All-day positions")
        fmt = self.result["fmt"] if self.result else E.fmt_hhmm
        for r in E.races_sorted(self.ev):
            tl = self.result["timelines"].get(r["id"]) if self.result else None
            self.a_race.append(r["id"], f"{r['name']} ({fmt(tl['start'])})" if tl else r["name"])
        if not self.a_race.set_active_id(cur or "*"):
            self.a_race.set_active_id("*")
        self._loading = False

    def _fill_assignments(self):
        if self.result is None or self._loading:
            return
        self.off_combo_model.clear()
        for n in [UNASSIGNED, LOC_VOL] + [o["name"] for o in self.ev["officials"]]:
            self.off_combo_model.append([n])
        q = (self.a_search.get_text() or "").lower()
        race = self.a_race.get_active_id() or "*"
        only = self.a_problems.get_active()

        F = self.result["fmt"]

        def do():
            self.a_store.clear()
            for r in self.result["rows"]:
                if race != "*" and r["race_id"] != race:
                    continue
                if q and q not in r["title"].lower() and q not in (r["official"] or "").lower():
                    continue
                if only and r["status"] in ("OK",):
                    continue
                self.a_store.append([r["key"], r["title"], r["race"], r["official"] or UNASSIGNED, r["role"],
                                     F(r["start"]), F(r["end"]), r["status"],
                                     STATUS_BG.get(r["status"]) or "#FFFFFF", r["locked"], r["toc"],
                                     700 if r["kind"] == "primary" and r["role"] == "Primary" else 400])
        self._keep_scroll(self.a_tree, do)
        res = self.result
        rd = res["radios"]
        n_rows = len(res["rows"])
        filled = sum(1 for r in res["rows"] if r["official"])
        self.summary.set_markup(
            f"<b>{len(self.ev['officials'])}</b> officials · <b>{n_rows}</b> jobs ({filled} filled) · "
            f"<span background='{STATUS_BG['UNFILLED']}'> unfilled {len(res['unfilled'])} </span> · "
            f"<span background='{STATUS_BG['CONFLICT']}'> conflicts {res['n_conflict']} </span> · "
            f"<span background='{STATUS_BG['TIGHT']}'> tight {res['n_tight']} </span> · "
            f"radios {rd['total']} ({rd['personal']} personal + {rd['vcc']} VCC + {rd['spare']} spare)")

    def _fill_personal(self):
        expanded = set()

        def collect(tree, path, _data):
            expanded.add(self.p_store[path][0])
        self.p_tree.map_expanded_rows(collect, None)
        self.p_store.clear()
        wt = [dict(w, primary=w["role"], secondary=[], races=[r["id"] for r in self.ev["races"]])
              for w in self.result.get("wt_officials", []) if w["duties"]]
        for o in self.result["officials"] + wt:
            worst = "OK"
            for d in o["duties"]:
                if d["status"] == "CONFLICT":
                    worst = "CONFLICT"
                elif d["status"] == "TIGHT" and worst != "CONFLICT":
                    worst = "TIGHT"
            sec = f" + {len(o['secondary'])} secondary" if o["secondary"] else ""
            if len(o["races"]) < len(self.ev["races"]):
                sec += f" · works {len(o['races'])} of {len(self.ev['races'])} races"
            parent = self.p_store.append(None, [o["name"], "", "", "", f"{o['primary'] or 'no primary'}{sec}", "",
                                                worst if o["duties"] else "no job", STATUS_BG.get(worst) or "#FFFFFF", 700])
            for d in o["duties"]:
                for s, e, lb, b, _a in sorted(d["windows"]):
                    self.p_store.append(parent, [d["title"], self.result["fmt"](s), self.result["fmt"](e), d["race"],
                                                 lb + ("" if b else " (non-blocking)"), d["role"], d["status"],
                                                 STATUS_BG.get(d["status"]) or "#FFFFFF", 400])
        it = self.p_store.get_iter_first()
        while it:
            if self.p_store[it][0] in expanded:
                self.p_tree.expand_row(self.p_store.get_path(it), False)
            it = self.p_store.iter_next(it)

    def _fill_timeline(self):
        self.t_store.clear()
        races = E.races_sorted(self.ev)
        for m in E.run_sheet(self.ev, self.result):
            rid = m.get("race_id")
            self.t_store.append([self.result["fmt"](m["time"]), m["race"], m["item"], X._lighten(X.race_colour(self.ev, rid), 0.7),
                                 700 if m["key"] in ("start", "winner") else 400])
        self.s_store.clear()
        for r in races:
            tl = self.result["timelines"][r["id"]]
            sg = tl["_segments"]
            F = self.result["fmt"]
            self.s_store.append([r["name"], F(tl["start"]), E.fmt_dur(sg["swim"]), E.fmt_dur(sg["t1"]), E.fmt_dur(sg["bike"]),
                                 E.fmt_dur(sg["t2"]), E.fmt_dur(sg["run"]), E.fmt_dur(sg["leg"]),
                                 F(tl["winner"]), F(tl["last_finisher"]), F(tl["medal"])])

    def _fill_conflicts(self):
        self.c_store.clear()
        for c in self.result["conflicts"]:
            self.c_store.append([c["level"], c["official"], c["a"], c["a_label"], c["a_time"], c["b"], c["b_label"],
                                 c["b_time"], "" if c["gap"] is None else str(c["gap"]), STATUS_BG.get(c["level"]) or "#FFFFFF"])
        for w in self.result.get("warnings", []):
            self.c_store.append(["WARNING", "", w, "", "", "", "", "", "", STATUS_BG["TIGHT"]])
        for u in self.result["unfilled"]:
            self.c_store.append(["UNFILLED", "", u["title"], u["race"], f"{self.result['fmt'](u['start'])}–{E.fmt_hhmm(u['end'] % 1440)}",
                                 "", "", "", "", STATUS_BG["UNFILLED"]])
        n = len(self.result["conflicts"]) + len(self.result["unfilled"])
        nw = len(self.result.get("warnings", []))
        self.c_label.set_markup(("<b>No conflicts and nothing unfilled.</b>" if n == 0 else
                                 f"<b>{self.result['n_conflict']}</b> conflict(s), <b>{self.result['n_tight']}</b> tight hand-over(s), "
                                 f"<b>{len(self.result['unfilled'])}</b> unfilled job(s).")
                                + (f" <b>{nw}</b> rule warning(s)." if nw else "")
                                + " Meetings and briefings count as busy time.")

    def _on_switch_page(self, nb, page, num):
        if num == getattr(self, "_gantt_page", -1):
            GLib.idle_add(lambda: self.refresh_gantt() and False)

    # ------------------------------------------------------------------ load / save
    def _demo_event(self):
        demo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "example_q3.wtplan.json")
        if os.path.isfile(demo):
            try:
                return X.load_json(demo)
            except (OSError, ValueError):
                pass
        ev = E.new_event("New event", dt.date.today().isoformat(), n_officials=18)
        E.auto_assign(ev)
        return ev

    def open_example(self, filename):
        if not self.confirm_discard():
            return
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", filename)
        try:
            self.load_event(X.load_json(p), None, dirty=True)
        except (OSError, ValueError) as err:
            self.info("Could not open the example", str(err), Gtk.MessageType.ERROR)

    def load_event(self, ev, path, dirty=False):
        self.ev = E.normalise(ev)
        self.path = path
        self.undo.clear()
        self.redo.clear()
        self.selected_race = None
        self._load_event_fields()
        self.set_dirty(dirty)
        self.refresh_all()
        self._sync_calendar_to_event()

    def _load_event_fields(self):
        self._loading = True
        e = self.ev["event"]
        for k, en in self.f.items():
            if k.startswith("jury"):
                j = e.get("jury", ["", ""])
                i = int(k[-1])
                en.set_text(j[i] if i < len(j) else "")
            else:
                en.set_text(str(e.get(k, "") or ""))
        self.f_vcc.set_value(int(e.get("vcc_base", 1)))
        self.f_spare.set_value(int(e.get("spare_pct", 10)))
        self._loading = False

    def _sync_calendar_to_event(self):
        try:
            d = dt.date.fromisoformat(self.ev["event"].get("date", ""))
        except (TypeError, ValueError):
            self.refresh_calendar()
            return
        self.cal.select_month(d.month - 1, d.year)
        self.cal.select_day(d.day)
        self.refresh_calendar()

    def confirm_discard(self):
        if not self.dirty:
            return True
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                              buttons=Gtk.ButtonsType.NONE, text="Save changes to this event?")
        d.format_secondary_text("Your changes will be lost if you don't save them.")
        d.add_buttons("_Don't save", Gtk.ResponseType.NO, "_Cancel", Gtk.ResponseType.CANCEL, "_Save", Gtk.ResponseType.YES)
        resp = d.run()
        d.destroy()
        if resp == Gtk.ResponseType.YES:
            return self.on_save()
        return resp == Gtk.ResponseType.NO

    def _on_delete(self, *a):
        if not self.confirm_discard():
            return True
        self._save_geometry()
        return False

    def on_new(self, *a):
        if not self.confirm_discard():
            return
        ev = E.new_event("New event", dt.date.today().isoformat(), n_officials=18)
        E.auto_assign(ev)
        self.load_event(ev, None, dirty=True)

    def _file_dialog(self, title, action, name=None, folder=None, patterns=(("Planner files", "*" + ref.FILE_SUFFIX),)):
        accept = "_Save" if action == Gtk.FileChooserAction.SAVE else "_Open"
        d = Gtk.FileChooserNative.new(title, self, action, accept, "_Cancel")
        for nm, pat in patterns:
            ff = Gtk.FileFilter()
            ff.set_name(nm)
            for p in pat.split(";"):
                ff.add_pattern(p)
            d.add_filter(ff)
        ff = Gtk.FileFilter()
        ff.set_name("All files")
        ff.add_pattern("*")
        d.add_filter(ff)
        if action == Gtk.FileChooserAction.SAVE:
            d.set_do_overwrite_confirmation(True)
            if name:
                d.set_current_name(name)
        if folder and os.path.isdir(folder):
            d.set_current_folder(folder)
        resp = d.run()
        path = d.get_filename() if resp == Gtk.ResponseType.ACCEPT else None
        d.destroy()
        return path

    def on_open(self, *a):
        if not self.confirm_discard():
            return
        p = self._file_dialog("Open event", Gtk.FileChooserAction.OPEN, folder=LIB_DIR,
                              patterns=(("Planner files", "*" + ref.FILE_SUFFIX + ";*.json"),))
        if p:
            self.open_path(p)

    def open_path(self, path):
        try:
            ev = X.load_json(path)
        except (OSError, ValueError) as err:
            self.info(f"Could not open {os.path.basename(path)}", str(err), Gtk.MessageType.ERROR)
            return
        self.load_event(ev, path, dirty=False)
        save_recent([path] + load_recent())
        self.refresh_calendar()

    def _default_name(self, ext):
        e = self.ev["event"]
        return f"{e.get('date') or 'undated'}_{slugify(e.get('name'))}{ext}"

    def on_save(self, *a):
        if not self.path:
            return self.on_save_as()
        return self._write(self.path)

    def on_save_as(self, *a):
        os.makedirs(LIB_DIR, exist_ok=True)
        p = self._file_dialog("Save event", Gtk.FileChooserAction.SAVE, self._default_name(ref.FILE_SUFFIX), LIB_DIR)
        if not p:
            return False
        if not p.endswith(".json"):
            p += ref.FILE_SUFFIX
        return self._write(p)

    def on_save_library(self, *a):
        os.makedirs(LIB_DIR, exist_ok=True)
        p = os.path.join(LIB_DIR, self._default_name(ref.FILE_SUFFIX))
        ok = self._write(p, set_path=self.path is None)
        if ok:
            self.toast(f"Saved to calendar library: {os.path.basename(p)}")
        return ok

    def _write(self, path, set_path=True):
        try:
            X.save_json(path, self.ev)
        except OSError as err:
            self.info("Could not save", str(err), Gtk.MessageType.ERROR)
            return False
        if set_path:
            self.path = path
        self.set_dirty(False)
        save_recent([path] + load_recent())
        self.refresh_calendar()
        return True

    def on_export(self, kind):
        ext = {"xlsx": ".xlsx", "ods": ".ods", "json": ref.FILE_SUFFIX, "ics": ".ics", "svg": ".svg"}[kind]
        pats = {"xlsx": ("Excel workbook", "*.xlsx"), "ods": ("OpenDocument spreadsheet", "*.ods"),
                "json": ("Planner JSON", "*.json"), "ics": ("iCalendar", "*.ics"), "svg": ("SVG image", "*.svg")}[kind]
        folder = os.path.dirname(self.path) if self.path else GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
        p = self._file_dialog("Export", Gtk.FileChooserAction.SAVE, self._default_name(ext), folder, patterns=(pats,))
        if not p:
            return
        if not p.endswith(ext.split(".")[-1]):
            p += ext
        res = self.result or E.evaluate(self.ev)
        try:
            if kind == "xlsx":
                X.write_xlsx(p, self.ev, res)
            elif kind == "ods":
                X.write_ods(p, self.ev, res)
            elif kind == "json":
                X.save_json(p, self.ev)
            elif kind == "ics":
                X.write_ics(p, self.ev, res)
            elif kind == "svg":
                X.write_svg(p, X.gantt_svg(self.ev, res, day=self.g_day.get_active_id(), mode=self.g_mode.get_active_id() or "officials",
                                           px_per_min=self.g_zoom.get_value(), dark=self.g_dark.get_active()))
        except (OSError, ValueError) as err:
            self.info("Export failed", str(err), Gtk.MessageType.ERROR)
            return
        self.toast(f"Exported {os.path.basename(p)}", open_path=p)

    def on_share(self, *a):
        """Hand the event JSON to another installed application."""
        path = self.path
        if not path or self.dirty:
            fd, path = tempfile.mkstemp(prefix=slugify(self.ev["event"].get("name")) + "-", suffix=ref.FILE_SUFFIX)
            os.close(fd)
            X.save_json(path, self.ev)
        d = Gtk.AppChooserDialog.new_for_content_type(self, Gtk.DialogFlags.MODAL, "application/json")
        d.set_heading("Choose an application to open the event JSON")
        resp = d.run()
        info = d.get_app_info() if resp == Gtk.ResponseType.OK else None
        d.destroy()
        if info:
            try:
                info.launch([Gio.File.new_for_path(path)], None)
            except GLib.Error as err:
                self.info("Could not start the application", err.message, Gtk.MessageType.ERROR)

    def _open_uri(self, uri):
        try:
            Gtk.show_uri_on_window(self, uri, Gdk.CURRENT_TIME)
        except GLib.Error as err:
            self.info("Could not open the browser", err.message, Gtk.MessageType.ERROR)

    def on_copy_json(self, *a):
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(X.to_json(self.ev), -1)
        self.toast("Event JSON copied to the clipboard")

    def on_open_library(self, *a):
        os.makedirs(LIB_DIR, exist_ok=True)
        Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(LIB_DIR, None), None)

    def on_about(self, *a):
        d = Gtk.AboutDialog(transient_for=self, modal=True)
        d.set_program_name(ref.APP_NAME)
        d.set_version(ref.APP_VERSION)
        d.set_logo_icon_name("wt-planner")
        d.set_comments("Plans Technical Official assignments for World Triathlon races: primary and secondary positions, "
                       "time clashes, Gantt chart, race timeline and radio count.\n\n" + ref.REFERENCES)
        d.set_license_type(Gtk.License.MIT_X11)
        d.set_website("https://www.trisport.me/")
        d.set_website_label("www.trisport.me")
        d.run()
        d.destroy()

    # ------------------------------------------------------------------ messages
    def info(self, text, secondary=None, kind=Gtk.MessageType.INFO):
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=kind, buttons=Gtk.ButtonsType.OK, text=text)
        if secondary:
            d.format_secondary_text(secondary)
        d.run()
        d.destroy()

    def toast(self, text, open_path=None):
        """Short notice in the header subtitle; optionally offer to open the file."""
        self.hb.set_subtitle(text)
        GLib.timeout_add_seconds(6, lambda: self.set_dirty(self.dirty) or False)
        if open_path:
            d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.INFO,
                                  buttons=Gtk.ButtonsType.NONE, text=text)
            d.add_buttons("_Close", Gtk.ResponseType.CLOSE, "_Open file", Gtk.ResponseType.OK)
            resp = d.run()
            d.destroy()
            if resp == Gtk.ResponseType.OK:
                Gio.AppInfo.launch_default_for_uri(GLib.filename_to_uri(open_path, None), None)


# ======================================================================= application
class PlannerApp(Gtk.Application):
    def __init__(self):
        flags = Gio.ApplicationFlags.HANDLES_OPEN
        if os.environ.get("SNAP"):
            # a strictly confined snap may not own the D-Bus name org.wtplanner.WTPlanner; registering would fail
            # ("Failed to register: AccessDenied") and the app would quit before showing a window
            flags |= Gio.ApplicationFlags.NON_UNIQUE
        super().__init__(application_id=ref.APP_ID, flags=flags)
        self.win = None

    def do_activate(self):
        if self.win is None:
            self.win = MainWindow(self)
        self.win.present()

    def do_open(self, files, n_files, hint):
        self.do_activate()
        if files:
            path = files[0].get_path()
            if path and self.win.confirm_discard():
                self.win.open_path(path)


def main(argv=None):
    import sys
    app = PlannerApp()
    return app.run(argv if argv is not None else sys.argv)
