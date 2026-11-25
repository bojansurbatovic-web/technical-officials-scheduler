"""Checks www.trisport.me/versions.json for a newer version of this app (Windows and Ubuntu desktop apps).

Runs in a background thread, at most once a day, never blocks or fails the app, and sends nothing about the user:
it is one plain download of a public file. Usage (Tkinter):

    checker = update_check.start("triofficial", VERSION, state_dir)
    ...poll from the UI thread: info = checker.result()  -> None while running / no update, else a dict

`info` has: version, message (English template, see TEXTS), url (what Update opens), command (snap refresh line or None).
Call tk_banner(root, checker, tr=...) to show it as a bar at the top of the window.
"""
import json, os, sys, threading, time, urllib.request

MANIFEST = "https://www.trisport.me/versions.json"
DAY = 24 * 3600

# English texts (apps translate them with their own tr function; placeholders {v} and {cmd})
MSG_GENERIC = "Version {v} is available."
MSG_STORE = "Version {v} is available in the Microsoft Store."
MSG_INSTALLER = "Version {v} is available. Download the new installer."
MSG_SNAP = "Version {v} is available. Ubuntu installs it automatically, or update now with: {cmd}"
BTN_UPDATE, BTN_LATER, BTN_COPY = "Update", "Not now", "Copy command"
MENU_CHECK = "Check for updates"
MSG_NEWEST = "You have the newest version ({v})."
MSG_FAILED = "Could not check for updates. Please check your internet connection."
TEXTS = [MSG_GENERIC, MSG_STORE, MSG_INSTALLER, MSG_SNAP, BTN_UPDATE, BTN_LATER, BTN_COPY, MENU_CHECK, MSG_NEWEST,
         MSG_FAILED]


def parse(v):
    out = []
    for p in str(v).split("."):
        n = "".join(c for c in p if c.isdigit())
        out.append(int(n) if n else 0)
    return tuple(out + [0] * (4 - len(out)))


def is_newer(latest, current):
    return parse(latest) > parse(current)


def platform():
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "ubuntu"


def from_microsoft_store():
    # MSIX (Store) installs run from C:\Program Files\WindowsApps\…
    return "\\windowsapps\\" in (sys.executable + "\\" + os.path.abspath(__file__)).lower()


class _Check:
    def __init__(self, app_id, current, state_dir, force):
        self.app_id, self.current, self.force = app_id, current, force
        self.state_path = os.path.join(state_dir, "update-check.json") if state_dir else None
        self._info = None
        self.done = False
        self.failed = False
        threading.Thread(target=self._run, daemon=True).start()

    def _state(self):
        try:
            with open(self.state_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, st):
        if not self.state_path:
            return
        try:
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(st, f)
        except Exception:
            pass

    def _run(self):
        try:
            st = self._state()
            if not self.force and time.time() - st.get("last_check", 0) < DAY:
                latest = st.get("latest")
            else:
                req = urllib.request.Request(MANIFEST, headers={"User-Agent": f"{self.app_id}/{self.current}"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = json.load(r)
                latest = data["apps"][self.app_id].get(platform())
                st.update(last_check=time.time(), latest=latest)
                self._save(st)
            if latest and is_newer(latest["version"], self.current) and (self.force or st.get("dismissed") != latest["version"]):
                self._info = self._describe(latest)
        except Exception:
            self.failed = True  # offline, blocked or malformed: stay silent
        finally:
            self.done = True

    def _describe(self, latest):
        # "message" is an English template with {v} / {cmd}; tk_banner translates it with tr() and fills it in.
        v = latest["version"]
        p = platform()
        info = {"version": v, "url": latest.get("url"), "command": None, "message": MSG_GENERIC}
        if p == "windows":
            if from_microsoft_store() and latest.get("store"):
                info.update(url=latest["store"], message=MSG_STORE)
            else:
                info["message"] = MSG_INSTALLER
        elif p == "ubuntu" and os.environ.get("SNAP") and latest.get("snap"):
            info.update(command=f"sudo snap refresh {latest['snap']}", message=MSG_SNAP)
        return info

    def result(self):
        return self._info

    def dismiss(self):
        if self._info:
            st = self._state(); st["dismissed"] = self._info["version"]; self._save(st)


def start(app_id, current, state_dir=None, force=False):
    """Start a background check. force=True ignores the once-a-day limit and 'not now' (for a menu command)."""
    return _Check(app_id, current, state_dir, force)


def open_url(url):
    import webbrowser
    try:
        if sys.platform.startswith("win"):
            os.startfile(url)  # also opens ms-windows-store:// links
        else:
            webbrowser.open(url)
    except Exception:
        webbrowser.open(url)


def tk_banner(root, checker, parent=None, tr=lambda t: t, on_shown=None, delay=1500):
    """Poll the checker from Tk's event loop and show a thin banner at the top of `parent` (default root)."""
    import tkinter as tk

    def poll():
        if not checker.done:
            root.after(500, poll); return
        info = checker.result()
        if not info:
            return
        host = parent or root
        old = getattr(root, "_update_bar", None)
        if old is not None and old.winfo_exists():
            old.destroy()
        bar = root._update_bar = tk.Frame(host, bg="#1f6feb")
        text = tr(info["message"]).format(v=info["version"], cmd=info.get("command") or "")
        tk.Label(bar, text="⬆  " + text, bg="#1f6feb", fg="white", anchor="w", wraplength=700,
                 justify="left").pack(side="left", padx=10, pady=6, fill="x", expand=True)
        def close(dismiss):
            if dismiss: checker.dismiss()
            bar.destroy()
        tk.Button(bar, text=tr(BTN_LATER), command=lambda: close(True), relief="flat").pack(side="right", padx=(4, 10), pady=4)
        if info.get("command"):
            def copy():
                root.clipboard_clear(); root.clipboard_append(info["command"])
            tk.Button(bar, text=tr(BTN_COPY), command=copy, relief="flat").pack(side="right", padx=4, pady=4)
        if info.get("url"):
            tk.Button(bar, text=tr(BTN_UPDATE), command=lambda: open_url(info["url"]), relief="flat").pack(side="right", padx=4, pady=4)
        children = host.pack_slaves()
        if children:
            bar.pack(side="top", fill="x", before=children[0])
        elif host.grid_slaves():
            bar.place(x=0, y=0, relwidth=1)  # window laid out with grid: float the bar over the top edge
        else:
            bar.pack(side="top", fill="x")
        if on_shown: on_shown(info)
    root.after(delay, poll)


def tk_check_now(root, app_id, current, state_dir=None, tr=lambda t: t, title=""):
    """For a "Check for updates" menu item: check now and show the banner, or say it is the newest / failed."""
    from tkinter import messagebox
    checker = start(app_id, current, state_dir, force=True)

    def poll():
        if not checker.done:
            root.after(300, poll); return
        if checker.result():
            tk_banner(root, checker, tr=tr, delay=0)
        elif checker.failed:
            messagebox.showwarning(title or tr(MENU_CHECK), tr(MSG_FAILED), parent=root)
        else:
            messagebox.showinfo(title or tr(MENU_CHECK), tr(MSG_NEWEST).format(v=current), parent=root)
    root.after(300, poll)


def gtk_infobar(checker, tr=lambda t: t, on_dismiss=None):
    """GTK 3: returns a hidden Gtk.InfoBar that shows itself when the background check finds a newer version.
    Put it at the top of the window (e.g. in a vertical Gtk.Box above the content)."""
    from gi.repository import GLib, Gtk
    bar = Gtk.InfoBar()
    bar.set_message_type(Gtk.MessageType.INFO)
    bar.set_no_show_all(True)
    label = Gtk.Label(xalign=0)
    label.set_line_wrap(True)
    bar.get_content_area().pack_start(label, True, True, 0)
    state = {}

    def show(info):
        for b in bar.get_action_area().get_children():
            bar.get_action_area().remove(b)
        state["info"] = info
        label.set_text(tr(info["message"]).format(v=info["version"], cmd=info.get("command") or ""))
        if info.get("url"):
            bar.add_button(tr(BTN_UPDATE), 1)
        if info.get("command"):
            bar.add_button(tr(BTN_COPY), 2)
        bar.add_button(tr(BTN_LATER), 3)
        label.show(); bar.show_all(); bar.show()

    def on_response(_bar, rid):
        info = state.get("info") or {}
        if rid == 1:
            open_url(info["url"])
        elif rid == 2:
            from gi.repository import Gdk
            Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(info["command"], -1)
        elif rid == 3:
            bar.checker.dismiss(); bar.hide()

    def poll():
        c = bar.checker
        if not c.done:
            return True
        if c.result():
            show(c.result())
        elif getattr(bar, "on_finished", None):
            bar.on_finished(c)
        return False

    def watch(c):
        bar.checker = c
        GLib.timeout_add(500, poll)

    bar.connect("response", on_response)
    bar.watch = watch  # bar.watch(start(..., force=True)) re-checks (for a "Check for updates" menu item)
    watch(checker)
    return bar
