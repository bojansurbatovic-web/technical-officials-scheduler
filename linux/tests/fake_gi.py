"""A minimal stand-in for PyGObject/GTK so the GUI code paths can run headless.

It does NOT prove GTK API correctness; it executes every Python line of the
window construction, refresh and edit handlers to catch logic/name errors.
"""
import html
import sys
import tempfile
import types


class Meta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Callable()


MISSES = []


class Stub(metaclass=Meta):
    def __init__(self, *a, **k):
        self._parent = None
        self._children = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if type(self).__name__ == "MainWindow":
            MISSES.append(name)
        return _Callable()

    def add(self, child):
        self._children.append(child)
        try:
            child._parent = self
        except Exception:
            pass

    def pack_start(self, child, *a):
        self.add(child)

    def pack_end(self, child, *a):
        self.add(child)

    def attach(self, child, *a):
        self.add(child)

    def get_parent(self):
        return self._parent

    def get_children(self):
        return list(self._children)

    def remove(self, child):
        if child in self._children:
            self._children.remove(child)

    def connect(self, *a, **k):
        return 1


class _Callable(Stub):
    def __call__(self, *a, **k):
        return _Callable()

    def __iter__(self):
        return iter([])

    def __bool__(self):
        return True


class Entry(Stub):
    def __init__(self, *a, **k):
        super().__init__()
        self._t = ""

    def set_text(self, t):
        self._t = t

    def get_text(self):
        return self._t


class SearchEntry(Entry):
    pass


class SpinButton(Stub):
    def __init__(self, *a, **k):
        super().__init__()
        self._v = 0.0

    def set_value(self, v):
        self._v = float(v)

    def get_value(self):
        return self._v


class Scale(SpinButton):
    @classmethod
    def new_with_range(cls, *a):
        s = cls()
        s._v = 4.0
        return s


class CheckButton(Stub):
    def __init__(self, *a, **k):
        super().__init__()
        self._a = False

    def set_active(self, a):
        self._a = bool(a)

    def get_active(self):
        return self._a


class ComboBoxText(Stub):
    def __init__(self, *a, **k):
        super().__init__()
        self._items = []
        self._active = -1

    def append(self, id_, text):
        self._items.append((id_, text))

    def append_text(self, text):
        self._items.append((text, text))

    def remove_all(self):
        self._items, self._active = [], -1

    def set_active(self, i):
        self._active = i if 0 <= i < len(self._items) else -1

    def set_active_id(self, id_):
        for i, (k, _t) in enumerate(self._items):
            if k == id_:
                self._active = i
                return True
        return False

    def get_active_id(self):
        return self._items[self._active][0] if self._active >= 0 else None

    def get_active_text(self):
        return self._items[self._active][1] if self._active >= 0 else None


class Calendar(Stub):
    def get_date(self):
        return (2026, 10, 21)


class Notebook(Stub):
    def __init__(self, *a, **k):
        super().__init__()
        self._n = 0
        self.current = 0

    def append_page(self, child, lab=None):
        self._n += 1
        return self._n - 1

    def get_current_page(self):
        return self.current


class Row(list):
    def __init__(self, values, it):
        super().__init__(values)
        self.iter = it


class ListStore:
    def __init__(self, *types_):
        self.rows = []

    def append(self, *args):
        values = args[-1]
        it = len(self.rows)
        self.rows.append(Row(values, it))
        return it

    def clear(self):
        self.rows = []

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, path):
        return self.rows[int(str(path).split(":")[0])]


class TreeStore(ListStore):
    def append(self, parent, values):
        if parent is None:
            it = len(self.rows)
            self.rows.append(Row(values, it))
            return it
        return parent

    def get_iter_first(self):
        return 0 if self.rows else None

    def iter_next(self, it):
        return it + 1 if it + 1 < len(self.rows) else None

    def get_path(self, it):
        return it


class Selection(Stub):
    def get_selected(self):
        return (None, None)


class TreeView(Stub):
    def __init__(self, *a, model=None, **k):
        super().__init__()
        self._sel = Selection()

    def get_selection(self):
        return self._sel

    def map_expanded_rows(self, fn, data):
        return None


class ScrolledWindow(Stub):
    def get_vadjustment(self):
        return SpinButton()


class PixbufLoader(Stub):
    def write(self, data):
        self.data = data

    def close(self):
        pass


class GError(Exception):
    message = "fake"


def _idle(fn, *a):
    fn(*a)
    return 1


def install():
    gi = types.ModuleType("gi")
    gi.require_version = lambda *a: None
    repo = types.ModuleType("gi.repository")

    def module(name, **classes):
        m = types.ModuleType(name)

        def ga(attr):
            return classes.get(attr, Stub)
        m.__getattr__ = ga
        for k, v in classes.items():
            setattr(m, k, v)
        return m

    Gtk = module("Gtk", Entry=Entry, SearchEntry=SearchEntry, SpinButton=SpinButton, Scale=Scale,
                 CheckButton=CheckButton, ComboBoxText=ComboBoxText, Calendar=Calendar, Notebook=Notebook,
                 ListStore=ListStore, TreeStore=TreeStore, TreeView=TreeView, ScrolledWindow=ScrolledWindow)
    tmp = tempfile.mkdtemp(prefix="wtp-fake-")
    GLib = module("GLib", Error=GError)
    GLib.markup_escape_text = lambda t: html.escape(t)
    GLib.get_user_data_dir = lambda: tmp
    GLib.get_user_config_dir = lambda: tmp
    GLib.idle_add = _idle
    GLib.timeout_add = lambda ms, fn, *a: 1
    GLib.timeout_add_seconds = lambda s, fn, *a: 1
    GLib.source_remove = lambda i: None
    GdkPixbuf = module("GdkPixbuf", PixbufLoader=PixbufLoader)
    Gio = module("Gio")
    Gdk = module("Gdk")
    for n, m in (("Gtk", Gtk), ("GLib", GLib), ("GdkPixbuf", GdkPixbuf), ("Gio", Gio), ("Gdk", Gdk)):
        setattr(repo, n, m)
        sys.modules["gi.repository." + n] = m
    gi.repository = repo
    sys.modules["gi"] = gi
    sys.modules["gi.repository"] = repo
    return tmp
