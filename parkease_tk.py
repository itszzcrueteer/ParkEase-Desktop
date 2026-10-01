import csv
import hashlib
import os
import re
import sys
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

try:
    BASE = os.path.dirname(os.path.abspath(__file__))
except NameError:       
    BASE = os.getcwd()

# ------------------------------------------------------------------ theme
BG, CARD, BORDER = "#f7f7f7", "#ffffff", "#e6e6e6"
TEXT, MUTED, FAINT = "#111111", "#6b6b6b", "#9a9a9a"
GREEN, RED, AMBER = "#1f9d55", "#d64545", "#f2b134"
FONT = "Segoe UI" if sys.platform.startswith("win") else "Helvetica"

GARAGE = "Metro Central Garage"
ADDRESS = "420 Market St, San Francisco \u00b7 Zone B"
SECTIONS = {"A": 32, "B": 24, "C": 36, "D": 36}
ACTIVE = ("awaiting", "confirmed")
STATUS_LABEL = {"awaiting": "Awaiting Arrival", "confirmed": "Confirmed",
                "expired": "Expired", "cancelled": "Cancelled"}
LABEL_STATUS = {v: k for k, v in STATUS_LABEL.items()}
ROLE_LABEL = {"user": "Driver", "attendant": "Attendant", "admin": "Admin"}
LABEL_ROLE = {v: k for k, v in ROLE_LABEL.items()}

USERS, VEHICLES, SPACES, RESERVATIONS = [], [], [], []
SESSIONS, HISTORY, ALERTS, NOTIFICATIONS, SUPPORT = [], [], [], [], []
SETTINGS = {}
_next_id = {"users": 0, "vehicles": 0, "reservations": 0, "sessions": 0,
            "history": 0, "alerts": 0, "notifications": 0, "support": 0}


def nid(table):
    """Next auto-increment id for one of the in-memory tables above."""
    _next_id[table] += 1
    return _next_id[table]


def find(rows, **kw):
    """First record in `rows` matching all key=value pairs, or None."""
    for r in rows:
        if all(r.get(k) == v for k, v in kw.items()):
            return r
    return None


def find_all(rows, **kw):
    """Every record in `rows` matching all key=value pairs."""
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 60000).hex()


def new_hash(pw):
    salt = os.urandom(8).hex()
    return salt, _hash(pw, salt)


def check_pw(row, pw):
    return _hash(pw, row["salt"]) == row["pw"]


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def stamp():
    return datetime.now().strftime("%b %d %H:%M")


def hhmm(ts):
    return datetime.fromisoformat(ts).strftime("%H:%M")


def full_name(u):
    return f"{u['first_name']} {u['last_name']}".strip()


def log(event):
    HISTORY.append({"id": nid("history"), "ts": stamp(), "event": event})


def notify(uid, body):
    if uid:
        NOTIFICATIONS.append({"id": nid("notifications"), "user_id": uid,
                              "body": body, "ts": stamp(), "seen": 0})


def space_set(space, status):
    s = find(SPACES, id=space)
    if s:
        s["status"] = status


def system_active():
    return SETTINGS.get("system_active", "1") == "1"


def add_user(first, last, email, pw, role="user", vehicle=None, plate="", vtype="Gas"):
    salt, h = new_hash(pw)
    uid = nid("users")
    USERS.append({"id": uid, "first_name": first, "last_name": last, "email": email.lower(),
                 "salt": salt, "pw": h, "role": role, "flags": 0,
                 "notify_email": 1, "notify_sms": 0})
    if vehicle:
        VEHICLES.append({"id": nid("vehicles"), "user_id": uid, "label": vehicle,
                         "plate": plate, "vtype": vtype, "is_primary": 1})
    return uid


def active_res(uid):
    cands = [r for r in RESERVATIONS if r["user_id"] == uid and r["status"] in ACTIVE]
    return cands[-1] if cands else None    # list is in id order, so last = newest


def make_res(uid, name, space, status="awaiting", hours=2.0):
    now = datetime.now()
    rid = nid("reservations")
    RESERVATIONS.append({
        "id": rid, "user_id": uid, "user_name": name, "space": space,
        "start_ts": now.isoformat(timespec="seconds"),
        "end_ts": (now + timedelta(hours=hours)).isoformat(timespec="seconds"),
        "status": status, "rate": 4.5, "garage": GARAGE,
    })
    space_set(space, "reserved" if status == "awaiting" else "occupied")
    return rid


def set_res_status(rid, status):
    """Change a reservation's status and keep its space in sync."""
    r = find(RESERVATIONS, id=rid)
    if not r:
        return None
    prev = r["status"]
    r["status"] = status
    if prev in ACTIVE or status in ACTIVE:      # inactive -> inactive leaves the space alone
        space_set(r["space"], {"awaiting": "reserved", "confirmed": "occupied"}.get(status, "available"))
    return r


def lot_summary():
    """Per-section counts plus overall totals."""
    per = {s: {"total": 0, "free": 0} for s in SECTIONS}
    for s in SPACES:
        per[s["section"]]["total"] += 1
        per[s["section"]]["free"] += s["status"] == "available"
    total = sum(v["total"] for v in per.values())
    free = sum(v["free"] for v in per.values())
    return per, total, free


def init_db():
    seed()


def seed():
    now = datetime.now()
    add_user("Admin", "User", "admin@parkease.com", "admin123", "admin")
    add_user("Sarah", "", "sarah@parkease.com", "staff1234", "attendant")
    daniel = add_user("Daniel", "Whitman", "daniel@example.com", "demo1234", "user",
                      "Honda Civic \u00b7 Silver", "7KLM-294")
    VEHICLES.append({"id": nid("vehicles"), "user_id": daniel, "label": "Tesla Model 3",
                     "plate": "8RNP-102", "vtype": "EV", "is_primary": 0})
    jordan = add_user("Jordan", "Lee", "jordan@example.com", "demo1234", "user", "Mazda 3", "4JLE-118")
    sam = add_user("Sam", "Chen", "sam@example.com", "demo1234", "user", "Ford Focus", "6SAM-330")
    priya = add_user("Priya", "Nair", "priya@example.com", "demo1234", "user", "Toyota Yaris", "2PNR-771")
    mark = add_user("Mark", "S.", "mark@example.com", "demo1234", "user", "VW Golf", "9MRK-045")
    lena = add_user("Lena", "Cruz", "lena@example.com", "demo1234", "user", "Kia Rio", "3LNC-512")

    for s, n in SECTIONS.items():
        for i in range(1, n + 1):
            SPACES.append({"id": f"{s}-{i:02d}", "section": s, "status": "available"})
    busy = ([f"A-{i:02d}" for i in range(1, 33)] + ["B-01", "B-02", "B-03", "B-04", "B-06", "B-07"]
            + [f"C-{i:02d}" for i in range(1, 25)] + [f"D-{i:02d}" for i in range(3, 31)])
    for b in busy:
        space_set(b, "occupied")
    space_set("B-14", "reserved")

    def res(uid, name, space, status, start, end):
        RESERVATIONS.append({
            "id": nid("reservations"), "user_id": uid, "user_name": name, "space": space,
            "start_ts": start.isoformat(timespec="seconds"), "end_ts": end.isoformat(timespec="seconds"),
            "status": status, "rate": 4.5, "garage": GARAGE,
        })

    end = now + timedelta(hours=1, minutes=24, seconds=55)
    res(daniel, "Daniel Whitman", "B-14", "awaiting", end - timedelta(hours=5, minutes=30), end)
    res(jordan, "Jordan Lee", "A-08", "confirmed", now - timedelta(minutes=45), now + timedelta(hours=2))
    res(sam, "Sam Chen", "C-22", "confirmed", now - timedelta(hours=3), now + timedelta(minutes=30))
    res(priya, "Priya Nair", "D-11", "confirmed", now - timedelta(hours=1), now + timedelta(hours=3))
    res(mark, "Mark S.", "D-02", "expired", now - timedelta(hours=2), now - timedelta(hours=1))
    res(lena, "Lena Cruz", "C-30", "cancelled", now - timedelta(hours=4), now - timedelta(hours=2))

    today = now.date()
    past = [("Bayview Marina Lot", "3h 15m", 3.25, "Space A-07", 14.63),
            ("SFO Terminal 2 Garage", "6h 40m", 6.67, "Space C-22", 30.40),
            ("Mission District Street", "1h 50m", 1.83, "Meter 114", 6.00),
            (GARAGE, "5h 05m", 5.08, "Space B-09", 22.85)]
    for k, (place, dur, hrs, spot, price) in enumerate(past):
        d = today.replace(day=max(1, today.day - (k * 3 + 1)))
        SESSIONS.append({"id": nid("sessions"), "user_id": daniel, "place": place, "date": d.isoformat(),
                         "duration": dur, "hours": hrs, "spot": spot, "price": price})

    ALERTS.append({"id": nid("alerts"), "kind": "warning", "title": "Reservation Expired",
                  "body": "User 'Mark S.' failed to confirm Space D-02 within 5 mins.", "ts": stamp()})
    ALERTS.append({"id": nid("alerts"), "kind": "info", "title": "Manual Release",
                  "body": "Space B-05 released by attendant 'Sarah'.", "ts": "2 mins ago"})
    for line in ("Space B-05 released by attendant Sarah.",
                 "Reservation confirmed for Jordan Lee - Space A-08.",
                 "Reservation confirmed for Sam Chen - Space C-22."):
        log(line)
    notify(daniel, f"Your reservation at {GARAGE} is confirmed for space B-14.")
    notify(daniel, "A receipt is available for your most recent session.")
    SETTINGS["system_active"] = "1"

def fnt(size=10, bold=False):
    return (FONT, size, "bold" if bold else "normal")


def label(p, text="", size=10, bold=False, fg=TEXT, bg=None, **kw):
    return tk.Label(p, text=text, font=fnt(size, bold), fg=fg, bg=bg or p.cget("bg"), **kw)


def button(p, text, cmd, kind="black", size=10, padx=16, pady=8):
    """Flat label-based button (looks the same on every platform)."""
    dark = kind == "black"
    b = tk.Label(p, text=text, font=fnt(size, True), fg="white" if dark else TEXT,
                 bg=TEXT if dark else "white", padx=padx, pady=pady, cursor="hand2",
                 highlightthickness=1, highlightbackground=TEXT if dark else BORDER)
    b.base, b.hover, b.enabled = (TEXT if dark else "white"), ("#333333" if dark else "#f2f2f2"), True
    b.bind("<Button-1>", lambda e: cmd() if b.enabled else None)
    b.bind("<Enter>", lambda e: b.config(bg=b.hover) if b.enabled else None)
    b.bind("<Leave>", lambda e: b.config(bg=b.base))
    return b


def disable(b, text=None):
    b.enabled = False
    b.base = "#8a8a8a"
    b.config(bg=b.base, fg="white", cursor="arrow", highlightbackground=b.base)
    if text:
        b.config(text=text)


def link(p, text, cmd, size=10, fg=TEXT, bold=True):
    l = tk.Label(p, text=text, font=(FONT, size, "bold" if bold else "normal", "underline"),
                 fg=fg, bg=p.cget("bg"), cursor="hand2")
    l.bind("<Button-1>", lambda e: cmd())
    return l


def card(p, pad=20):
    return tk.Frame(p, bg=CARD, padx=pad, pady=pad, highlightthickness=1,
                    highlightbackground=BORDER, highlightcolor=BORDER)


def hline(p, pady=0):
    f = tk.Frame(p, bg=BORDER, height=1)
    f.pack(fill="x", pady=pady)
    return f


def pill(p, text, status=None):
    bg, fg = {"confirmed": (TEXT, "white"), "awaiting": ("#eeeeee", "#444444"),
              "expired": ("#fdecec", RED), "cancelled": ("#eeeeee", "#999999")
              }.get(status, ("#eeeeee", "#444444"))
    return tk.Label(p, text=text, font=fnt(9, True), bg=bg, fg=fg, padx=10, pady=3)


def avatar(p, name, size=30):
    initials = "".join(w[0] for w in name.split()[:2]).upper() or "?"
    cv = tk.Canvas(p, width=size, height=size, bg=p.cget("bg"), highlightthickness=0)
    cv.create_oval(1, 1, size - 1, size - 1, fill="#e4e4e8", outline="")
    cv.create_text(size / 2, size / 2, text=initials, font=fnt(max(7, size // 3), True), fill="#444444")
    return cv


def logo(p, size=44):
    cv = tk.Canvas(p, width=size, height=size, bg=p.cget("bg"), highlightthickness=0)
    cv.create_rectangle(2, 2, size - 2, size - 2, outline=TEXT, width=2)
    cv.create_text(size / 2, size / 2, text="P", font=fnt(int(size * 0.42), True), fill=TEXT)
    return cv


def section(p, text):
    label(p, text.upper(), 8, True, FAINT).pack(anchor="w", pady=(16, 2))


class Field(tk.Frame):
    """Bordered entry with optional placeholder, show/hide toggle and read-only mode."""

    def __init__(self, p, placeholder="", show="", value="", readonly=False, toggle=False, width=24):
        super().__init__(p, bg="white", highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=TEXT)
        self.ph, self.pw, self.on_ph = placeholder, show, False
        self.e = tk.Entry(self, relief="flat", bd=0, font=fnt(11), bg="white", fg=TEXT,
                          insertbackground=TEXT, width=width, highlightthickness=0, show=show,
                          readonlybackground="#f5f5f5")
        self.e.pack(side="left", fill="x", expand=True, padx=8, pady=7)
        if toggle:
            self.t = link(self, "Show", self._toggle, 9, MUTED, False)
            self.t.pack(side="right", padx=8)
        if value:
            self.e.insert(0, value)
        if readonly:
            self.e.config(state="readonly")
        self.e.bind("<FocusIn>", self._in)
        self.e.bind("<FocusOut>", self._out)
        self._out()

    def _in(self, e=None):
        if self.on_ph:
            self.e.delete(0, "end")
            self.e.config(fg=TEXT, show=self.pw)
            self.on_ph = False

    def _out(self, e=None):
        if self.ph and not self.e.get():
            self.e.config(fg=FAINT, show="")
            self.e.insert(0, self.ph)
            self.on_ph = True

    def _toggle(self):
        self.pw = "" if self.pw else "\u2022"
        self.e.config(show=self.pw)
        self.t.config(text="Show" if self.pw else "Hide")

    def get(self):
        return "" if self.on_ph else self.e.get()

    def set(self, v):
        self.e.config(state="normal")
        self.e.delete(0, "end")
        self.on_ph = False
        self.e.config(fg=TEXT, show=self.pw)
        self.e.insert(0, v)

    def clear(self):
        self.set("")
        self._out()

    def flag(self, bad):
        self.config(highlightbackground=RED if bad else BORDER)


class Area(tk.Frame):
    """Bordered multi-line text box."""

    def __init__(self, p, height=4, width=36):
        super().__init__(p, bg="white", highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=TEXT)
        self.t = tk.Text(self, height=height, width=width, wrap="word", relief="flat", bd=0,
                         font=fnt(11), bg="white", fg=TEXT, insertbackground=TEXT,
                         highlightthickness=0)
        self.t.pack(fill="both", expand=True, padx=8, pady=6)

    def get(self):
        return self.t.get("1.0", "end-1c")

    def clear(self):
        self.t.delete("1.0", "end")

    def flag(self, bad):
        self.config(highlightbackground=RED if bad else BORDER)


class Scroll(tk.Frame):
    """Vertically scrolling container. Put children in .body"""

    def __init__(self, p, bg=BG):
        super().__init__(p, bg=bg)
        self.cv = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        sb = tk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.cv, bg=bg)
        self.win = self.cv.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.win, width=e.width))

    def to(self, widget):
        """Scroll so `widget` is at the top."""
        self.update_idletasks()
        h = max(1, self.body.winfo_height())
        self.cv.yview_moveto(max(0, (widget.winfo_rooty() - self.body.winfo_rooty()) / h))


def center(win, parent):
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    px = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
    py = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 3)
    win.geometry(f"+{px}+{py}")


def form(app, title, fields, submit="Save", on_submit=None, sub=""):
    """Small modal form.
    fields = [(key, label, kind, arg)] with kind one of
      entry (arg=placeholder) | password | text (arg=read-only value)
      combo (arg=values) | combo_edit (arg=values) | area
    on_submit(values) returns an error message, or None to close the dialog."""
    d = tk.Toplevel(app)
    d.title(title)
    d.configure(bg="white")
    d.resizable(False, False)
    d.transient(app)
    label(d, title, 14, True).pack(anchor="w", padx=24, pady=(20, 2))
    if sub:
        label(d, sub, 9, fg=MUTED, wraplength=340, justify="left").pack(anchor="w", padx=24)
    W, kinds = {}, {}
    for key, lab, kind, arg in fields:
        label(d, lab, 9, True).pack(anchor="w", padx=24, pady=(12, 4))
        if kind in ("combo", "combo_edit"):
            var = tk.StringVar(value="" if kind == "combo_edit" else (arg[0] if arg else ""))
            w = ttk.Combobox(d, textvariable=var, values=list(arg), width=34,
                             state="readonly" if kind == "combo" else "normal")
        elif kind == "area":
            w = Area(d, 4, 38)
        elif kind == "password":
            w = Field(d, show="\u2022", toggle=True, width=34)
        elif kind == "text":
            w = Field(d, value=arg, readonly=True, width=34)
        else:
            w = Field(d, arg or "", width=34)
        w.pack(fill="x", padx=24)
        W[key], kinds[key] = w, kind
    err = label(d, "", 9, fg=RED, wraplength=340, justify="left")
    err.pack(anchor="w", padx=24, pady=(8, 0))

    def go():
        vals = {k: (w.get() if kinds[k] == "password" else w.get().strip()) for k, w in W.items()}
        msg = on_submit(vals)
        if msg:
            err.config(text=msg)
        else:
            d.destroy()

    row = tk.Frame(d, bg="white")
    row.pack(fill="x", padx=24, pady=(16, 22))
    button(row, "Cancel", d.destroy, "outline").pack(side="left", expand=True, fill="x", padx=(0, 6))
    button(row, submit, go).pack(side="left", expand=True, fill="x", padx=(6, 0))
    center(d, app)
    try:
        d.wait_visibility()
        d.grab_set()
    except tk.TclError:
        pass
    return d


FEATURES = (
    ("Real-time Availability", "Live occupancy data so you always know where an open spot is before you arrive."),
    ("Secure Reservations", "Lock in your spot ahead of time with instant confirmation and easy cancellation."),
    ("Multi-Vehicle Management", "Manage multiple cars and payment methods from one unified dashboard."),
)
STEPS = (
    ("Find", "Search by location or let us suggest the best available spots near you."),
    ("Reserve", "Pick your duration and pay securely. Your spot is held until arrival."),
    ("Park", "Drive straight to your reserved spot. No tickets, no meters, no stress."),
)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ParkEase")
        self.geometry("1180x780")
        self.minsize(860, 560)
        self.configure(bg=BG)
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Treeview", rowheight=28, font=fnt(10), background="white",
                     fieldbackground="white", borderwidth=0)
        st.configure("Treeview.Heading", font=fnt(9, True))
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self._wheel)
        self.timers, self.root_frame = [], None
        self.map_sec, self.akey = "B", "overview"
        init_db()
        self.user = None   # no persistence between runs -- always starts at the landing page
        self.route()

    # ---- plumbing --------------------------------------------------
    def _wheel(self, e):
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):
            return
        while w is not None and not isinstance(w, Scroll):
            if isinstance(w, ttk.Treeview):
                return
            w = w.master
        if w is None:
            return
        if e.num == 4:
            step = -3
        elif e.num == 5:
            step = 3
        else:
            step = -3 if e.delta > 0 else 3
        w.cv.yview_scroll(step, "units")

    def cancel_timers(self):
        for h in self.timers:
            try:
                self.after_cancel(h["id"])
            except (tk.TclError, KeyError):
                pass
        self.timers = []

    def every(self, ms, fn):
        h = {}

        def run():
            try:
                fn()
            except tk.TclError:
                return
            h["id"] = self.after(ms, run)

        h["id"] = self.after(ms, run)
        self.timers.append(h)

    def toast(self, msg):
        t = tk.Label(self, text=msg, bg=TEXT, fg="white", font=fnt(10), padx=18, pady=10)
        t.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")

        def bye():
            try:
                t.destroy()
            except tk.TclError:
                pass
        self.after(2400, bye)

    def show(self, name, *args):
        self.cancel_timers()
        if self.root_frame is not None:
            self.root_frame.destroy()
        self.root_frame = tk.Frame(self, bg=BG)
        self.root_frame.pack(fill="both", expand=True)
        getattr(self, "build_" + name)(self.root_frame, *args)

    def route(self):
        if not self.user:
            self.show("landing")
        elif self.user["role"] in ("admin", "attendant"):
            self.show("admin")
        else:
            self.show("user")

    def login(self, row, keep=False):
        # `row` is the actual dict living in the USERS list, so self.user
        # stays live -- any later update to that record (settings, flags,
        # password) is automatically visible with no re-fetch needed.
        # `keep` ("Keep me logged in") has nothing to persist to since
        # there's no storage between runs; it's accepted for UI parity only.
        self.user = row
        self.route()

    def logout(self):
        self.user = None
        self.show("landing")

    def me(self):
        return self.user

    def legal(self, name):
        messagebox.showinfo(name, f"The {name} text hasn't been written yet. "
                                  "The team should replace this placeholder.")

    # ---- landing page ---------------------------------------------
    def build_landing(self, root):
        nav = tk.Frame(root, bg="white", highlightthickness=1, highlightbackground=BORDER)
        nav.pack(fill="x")
        bar = tk.Frame(nav, bg="white")
        bar.pack(fill="x", padx=32, pady=14)
        sc = Scroll(root)
        sc.pack(fill="both", expand=True)
        b, sec = sc.body, {}
        label(bar, "ParkEase", 15, True).pack(side="left", padx=(0, 18))
        for text, key in (("Features", "features"), ("Pricing", "pricing"),
                          ("Locations", "locations"), ("Support", "support")):
            link(bar, text, lambda k=key: sc.to(sec[k]), 10, MUTED, False).pack(side="left", padx=10)
        button(bar, "Get Started", lambda: self.show("signup"), pady=6).pack(side="right")
        link(bar, "Log in", lambda: self.show("login")).pack(side="right", padx=18)

        # hero
        hero = tk.Frame(b, bg="white")
        hero.pack(fill="x")
        hero.columnconfigure(0, weight=1)
        hero.columnconfigure(1, weight=1)
        left = tk.Frame(hero, bg="white")
        left.grid(row=0, column=0, padx=(64, 20), pady=64, sticky="w")
        label(left, "Parking made\npainless.", 34, True, justify="left").pack(anchor="w")
        label(left, "Find, reserve, and pay for parking in seconds. ParkEase connects you to "
                    "thousands of spots across the city in real time.",
              11, fg=MUTED, wraplength=380, justify="left").pack(anchor="w", pady=18)
        row = tk.Frame(left, bg="white")
        row.pack(anchor="w")
        button(row, "Get Started", lambda: self.show("signup"), pady=11, padx=20).pack(side="left")
        link(row, "View Locations", lambda: sc.to(sec["locations"])).pack(side="left", padx=24)
        label(left, "\u2605  Trusted by 50,000+ drivers", 9, fg=MUTED).pack(anchor="w", pady=(22, 0))
        cv = tk.Canvas(hero, width=430, height=340, bg="#2b2b2b", highlightthickness=0)
        cv.grid(row=0, column=1, padx=(20, 64), pady=40, sticky="e")
        spot = None
        for r in range(3):
            for c in range(3):
                x0, y0 = 30 + c * 130, 24 + r * 104
                if (r, c) == (1, 1):
                    spot = cv.create_rectangle(x0, y0, x0 + 110, y0 + 84, outline="#ffffff",
                                               width=2, dash=(6, 4))
                else:
                    cv.create_rectangle(x0, y0, x0 + 110, y0 + 84, outline="#5a5a5a")
                    cv.create_rectangle(x0 + 14, y0 + 12, x0 + 96, y0 + 72, fill="#e9e9e9", outline="")
                    cv.create_rectangle(x0 + 34, y0 + 22, x0 + 76, y0 + 62, fill="#b9b9b9", outline="")
        tog = [True]

        def pulse():
            tog[0] = not tog[0]
            cv.itemconfigure(spot, outline="#ffffff" if tog[0] else "#666666")
        self.every(700, pulse)

        # features
        f = tk.Frame(b, bg=BG)
        f.pack(fill="x")
        sec["features"] = f
        label(f, "Everything you need to park smarter", 20, True).pack(pady=(54, 6))
        label(f, "ParkEase replaces circling blocks with a single tap. Built for commuters,\n"
                 "visitors, and fleets alike.", 11, fg=MUTED, justify="center").pack()
        fr = tk.Frame(f, bg=BG)
        fr.pack(fill="x", padx=60, pady=(28, 54))
        for i, (t, d) in enumerate(FEATURES):
            fr.columnconfigure(i, weight=1, uniform="feat")
            c = card(fr, 22)
            c.grid(row=0, column=i, sticky="nsew", padx=8)
            label(c, t, 12, True).pack(anchor="w")
            label(c, d, 10, fg=MUTED, wraplength=250, justify="left").pack(anchor="w", pady=(8, 0))

        # how it works
        h = tk.Frame(b, bg="white")
        h.pack(fill="x")
        sec["how"] = h
        label(h, "How it works", 20, True).pack(pady=(54, 6))
        label(h, "Three steps to your spot.", 11, fg=MUTED).pack()
        steps = tk.Frame(h, bg="white")
        steps.pack(fill="x", padx=80, pady=(30, 54))
        tk.Frame(steps, bg=BORDER, height=1).place(relx=0.17, rely=0, y=23, relwidth=0.66)
        for i, (t, d) in enumerate(STEPS):
            steps.columnconfigure(i, weight=1, uniform="step")
            col = tk.Frame(steps, bg="white")
            col.grid(row=0, column=i, sticky="n")
            dot = tk.Canvas(col, width=46, height=46, bg="white", highlightthickness=0)
            dot.create_oval(2, 2, 44, 44, fill=TEXT, outline=TEXT)
            dot.create_text(23, 23, text=str(i + 1), fill="white", font=fnt(13, True))
            dot.pack()
            label(col, t, 12, True).pack(pady=(12, 4))
            label(col, d, 10, fg=MUTED, wraplength=230, justify="center").pack()

        # app promo
        promo = tk.Frame(b, bg=BG)
        promo.pack(fill="x")
        sec["pricing"] = promo
        inner = tk.Frame(promo, bg=BG)
        inner.pack(pady=56)
        ph = tk.Canvas(inner, width=210, height=340, bg=BG, highlightthickness=0)
        ph.pack(side="left", padx=(0, 70))
        ph.create_rectangle(24, 8, 186, 332, fill="white", outline=BORDER)
        ph.create_rectangle(34, 18, 176, 322, fill=TEXT, outline="")
        ph.create_rectangle(42, 40, 168, 314, fill="white", outline="")
        ph.create_rectangle(86, 24, 124, 32, fill="#333333", outline="")
        ph.create_rectangle(52, 52, 74, 74, fill=TEXT, outline="")
        ph.create_oval(142, 52, 160, 70, fill="#cfcfd4", outline="")
        ph.create_rectangle(52, 84, 158, 160, fill="#e6e7ea", outline="")
        for gx in range(60, 156, 14):
            for gy in range(92, 158, 14):
                ph.create_oval(gx, gy, gx + 2, gy + 2, fill="#b5b5bb", outline="")
        ph.create_oval(99, 116, 111, 128, fill=TEXT, outline="")
        for y0 in (172, 208, 244):
            ph.create_rectangle(52, y0, 158, y0 + 28, outline=BORDER, fill="white")
        ph.create_rectangle(52, 280, 158, 306, fill=TEXT, outline="")
        txt = tk.Frame(inner, bg=BG)
        txt.pack(side="left")
        label(txt, "Park on the go", 20, True).pack(anchor="w")
        label(txt, "The ParkEase app puts every parking spot in the city in your pocket. Get "
                   "directions, extend sessions, and receive receipts \u2014 all from your phone.",
              11, fg=MUTED, wraplength=400, justify="left").pack(anchor="w", pady=14)
        stores = tk.Frame(txt, bg=BG)
        stores.pack(anchor="w")
        for name in ("App Store", "Google Play"):
            button(stores, name, lambda n=name: messagebox.showinfo(n, "The mobile app isn't available yet."),
                   pady=9).pack(side="left", padx=(0, 10))

        # locations
        loc = tk.Frame(b, bg="white")
        loc.pack(fill="x")
        sec["locations"] = loc
        label(loc, "Find parking near you", 20, True).pack(pady=(54, 6))
        label(loc, "Type a city or neighborhood to see live availability.", 11, fg=MUTED).pack()
        lr = tk.Frame(loc, bg="white")
        lr.pack(pady=(20, 8))
        term = Field(lr, "e.g. San Francisco, Mission District\u2026", width=38)
        term.pack(side="left", padx=(0, 10))
        res = label(loc, "", 10, fg=MUTED)
        res.pack(pady=(0, 54))

        def search(e=None):
            t = term.get().strip()
            if not t:
                res.config(text="Enter a city or neighborhood to search.")
                return
            _, total, free = lot_summary()
            res.config(text=f"{free} of {total} spaces are open at {GARAGE} near \"{t}\". "
                            "Create an account to reserve one.")
        button(lr, "Search", search, pady=9).pack(side="left")
        term.e.bind("<Return>", search)

        # support
        sup = tk.Frame(b, bg=BG)
        sup.pack(fill="x")
        sec["support"] = sup
        label(sup, "We're here to help", 20, True).pack(pady=(54, 6))
        label(sup, "Have a question before you sign up? Send us a note and we'll get back to you.",
              11, fg=MUTED).pack()
        sf = tk.Frame(sup, bg=BG)
        sf.pack(pady=(18, 54))
        em = Field(sf, "Your email", width=46)
        em.pack(fill="x")
        msg = Area(sf, 5, 46)
        msg.pack(fill="x", pady=10)

        def send():
            addr, body = em.get().strip(), msg.get().strip()
            if "@" not in addr or not body:
                messagebox.showwarning("Support", "Please enter your email and a message.")
                return
            SUPPORT.append({"id": nid("support"), "user_id": None, "email": addr, "body": body, "ts": stamp()})
            em.clear()
            msg.clear()
            messagebox.showinfo("Support", "Thanks - we'll get back to you within one business day.")
        button(sf, "Send message", send, pady=10).pack(fill="x")

        # footer
        ft = tk.Frame(b, bg="white", highlightthickness=1, highlightbackground=BORDER)
        ft.pack(fill="x")
        fi = tk.Frame(ft, bg="white")
        fi.pack(fill="x", padx=48, pady=26)
        fb = tk.Frame(fi, bg="white")
        fb.pack(side="left", padx=(0, 60))
        label(fb, "ParkEase", 12, True).pack(anchor="w")
        label(fb, "\u00a9 2026 ParkEase Inc.", 9, fg=FAINT).pack(anchor="w")
        for name in ("Privacy", "Terms", "Cookies"):
            link(fi, name, lambda n=name: self.legal(n), 9, MUTED, False).pack(side="left", padx=14)
        link(fi, "Contact", lambda: sc.to(sec["support"]), 9, MUTED, False).pack(side="left", padx=14)

    # ---- log in ----------------------------------------------------
    def build_login(self, root, email=""):
        sc = Scroll(root)
        sc.pack(fill="both", expand=True)
        c = card(sc.body, 34)
        c.pack(pady=(70, 24), padx=20)
        logo(c).pack()
        label(c, "Welcome back", 20, True).pack(pady=(14, 2))
        label(c, "Access your ParkEase account", 10, fg=MUTED).pack(pady=(0, 18))
        banner = label(c, "", 9, fg=RED, wraplength=340, justify="left")
        banner.pack(fill="x")
        label(c, "Email address", 10, True).pack(anchor="w", pady=(6, 4))
        em = Field(c, "alex@example.com", value=email, width=36)
        em.pack(fill="x")
        hd = tk.Frame(c, bg=CARD)
        hd.pack(fill="x", pady=(14, 4))
        label(hd, "Password", 10, True).pack(side="left")
        link(hd, "Forgot password?",
             lambda: messagebox.showinfo("Forgot password",
                                         "Password reset isn't available yet. Ask an administrator to help."),
             9).pack(side="right")
        pw = Field(c, show="\u2022", toggle=True, width=36)
        pw.pack(fill="x")
        keep = tk.IntVar(value=0)
        tk.Checkbutton(c, text="Keep me logged in", variable=keep, bg=CARD, activebackground=CARD,
                       selectcolor="white", fg=MUTED, font=fnt(9), highlightthickness=0,
                       bd=0).pack(anchor="w", pady=12)

        def go(e=None):
            addr, secret = em.get().strip().lower(), pw.get()
            em.flag(False)
            pw.flag(False)
            banner.config(text="")
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", addr):
                em.flag(True)
                banner.config(text="Enter a valid email address.")
                return
            if not secret:
                pw.flag(True)
                banner.config(text="Password is required.")
                return
            row = find(USERS, email=addr)
            if not row or not check_pw(row, secret):
                banner.config(text="Invalid email or password.")
                return
            self.login(row, bool(keep.get()))
        button(c, "Log in", go, pady=11).pack(fill="x")
        em.e.bind("<Return>", go)
        pw.e.bind("<Return>", go)
        dv = tk.Frame(c, bg=CARD)
        dv.pack(fill="x", pady=18)
        dv.columnconfigure(0, weight=1)
        dv.columnconfigure(2, weight=1)
        tk.Frame(dv, bg=BORDER, height=1).grid(row=0, column=0, sticky="ew")
        label(dv, "OR CONTINUE WITH", 8, fg=FAINT).grid(row=0, column=1, padx=10)
        tk.Frame(dv, bg=BORDER, height=1).grid(row=0, column=2, sticky="ew")
        oa = tk.Frame(c, bg=CARD)
        oa.pack(fill="x")
        for i, name in enumerate(("Google", "Apple")):
            oa.columnconfigure(i, weight=1, uniform="oauth")
            button(oa, name, lambda n=name: messagebox.showinfo(n, f"{n} sign-in isn't available in this version."),
                   "outline", pady=8).grid(row=0, column=i, sticky="ew",
                                           padx=(0, 6) if i == 0 else (6, 0))
        ft = tk.Frame(c, bg=CARD)
        ft.pack(pady=(20, 0))
        label(ft, "Don't have an account?", 10, fg=MUTED).pack()
        link(ft, "Sign up", lambda: self.show("signup")).pack()
        link(c, "\u2190 Back to home", lambda: self.show("landing"), 9, MUTED, False).pack(pady=(14, 0))

    # ---- sign up ---------------------------------------------------
    def build_signup(self, root):
        sc = Scroll(root)
        sc.pack(fill="both", expand=True)
        c = card(sc.body, 34)
        c.pack(pady=(40, 30), padx=20)
        logo(c).pack()
        label(c, "Create your account", 20, True).pack(pady=(14, 2))
        label(c, "Join ParkEase and manage your parking effortlessly", 10, fg=MUTED).pack(pady=(0, 6))
        F, E = {}, {}

        def fields(*rows):
            for spec in rows:
                fr = tk.Frame(c, bg=CARD)
                fr.pack(fill="x")
                for i, (k, lab, ph, secret) in enumerate(spec):
                    fr.columnconfigure(i, weight=1, uniform="sgn")
                    cell = tk.Frame(fr, bg=CARD)
                    cell.grid(row=0, column=i, sticky="ew",
                              padx=(0 if i == 0 else 8, 0 if i == len(spec) - 1 else 8))
                    label(cell, lab, 10, True).pack(anchor="w", pady=(8, 4))
                    F[k] = Field(cell, ph, show="\u2022" if secret else "", toggle=secret, width=18)
                    F[k].pack(fill="x")
                    E[k] = label(cell, "", 8, fg=RED)
                    E[k].pack(anchor="w")

        section(c, "Personal information")
        fields([("first", "First name", "Alex", False), ("last", "Last name", "Rivera", False)],
               [("email", "Email address", "alex@example.com", False)])
        section(c, "Vehicle profile")
        fields([("vehicle", "Vehicle Make/Model", "Honda Civic", False),
                ("plate", "License Plate", "ABC-1234", False)])
        label(c, "* You can add more vehicles later in your profile settings.", 8, fg=FAINT).pack(anchor="w")
        section(c, "Security")
        fields([("password", "Password", "", True), ("confirm", "Confirm password", "", True)])
        agree = tk.IntVar(value=0)
        ar = tk.Frame(c, bg=CARD)
        ar.pack(fill="x", pady=(16, 0))
        tk.Checkbutton(ar, text="I agree to the", variable=agree, bg=CARD, activebackground=CARD,
                       selectcolor="white", font=fnt(9), highlightthickness=0, bd=0).pack(side="left")
        link(ar, "Terms of Service", lambda: self.legal("Terms of Service"), 9).pack(side="left")
        label(ar, " and ", 9).pack(side="left")
        link(ar, "Privacy Policy", lambda: self.legal("Privacy Policy"), 9).pack(side="left")
        label(c, "including the reservation abuse prevention policies.", 9, fg=MUTED).pack(anchor="w", padx=24)
        terms_err = label(c, "", 8, fg=RED)
        terms_err.pack(anchor="w")

        def submit():
            v = {k: F[k].get().strip() for k in ("first", "last", "email", "vehicle", "plate")}
            pw, cf = F["password"].get(), F["confirm"].get()
            errs = {}
            if not v["first"]:
                errs["first"] = "First name is required."
            if not v["last"]:
                errs["last"] = "Last name is required."
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v["email"]):
                errs["email"] = "Enter a valid email address."
            elif find(USERS, email=v["email"].lower()):
                errs["email"] = "An account with this email already exists."
            if not v["vehicle"]:
                errs["vehicle"] = "Vehicle make/model is required."
            if not v["plate"]:
                errs["plate"] = "License plate is required."
            if len(pw) < 8:
                errs["password"] = "At least 8 characters."
            if cf != pw:
                errs["confirm"] = "Passwords do not match."
            for k in F:
                E[k].config(text=errs.get(k, ""))
                F[k].flag(k in errs)
            terms_err.config(text="" if agree.get() else "You must agree to the Terms and Privacy Policy.")
            if errs or not agree.get():
                return
            add_user(v["first"], v["last"], v["email"], pw, "user", v["vehicle"], v["plate"])
            log(f"New driver registered: {v['first']} {v['last']}.")
            messagebox.showinfo("Account created", "Your account is ready. Log in to continue.")
            self.show("login", v["email"])
        button(c, "Create Account", submit, pady=11).pack(fill="x", pady=(14, 0))
        ft = tk.Frame(c, bg=CARD)
        ft.pack(pady=(18, 0))
        label(ft, "Already have an account?", 10, fg=MUTED).pack()
        link(ft, "Log in", lambda: self.show("login")).pack()
        link(c, "\u2190 Back to home", lambda: self.show("landing"), 9, MUTED, False).pack(pady=(14, 0))

    # ---- user dashboard -------------------------------------------
    def build_user(self, root):
        side = tk.Frame(root, bg="white", width=240, highlightthickness=1, highlightbackground=BORDER)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        label(side, "ParkEase", 14, True).pack(anchor="w", padx=22, pady=(24, 22))
        self.nav = {}
        for key, text in (("dashboard", "Dashboard"), ("vehicles", "My Vehicles"),
                          ("history", "History"), ("settings", "Settings")):
            l = tk.Label(side, text=text, font=fnt(10, True), anchor="w", padx=14, pady=9,
                         cursor="hand2", bg="white", fg=TEXT)
            l.pack(fill="x", padx=12, pady=1)
            l.bind("<Button-1>", lambda e, k=key: self.user_page(k))
            self.nav[key] = l
        hb = tk.Frame(side, bg=BG, padx=14, pady=14)
        hb.pack(side="bottom", fill="x", padx=12, pady=16)
        label(hb, "Need help parking?", 10, True).pack(anchor="w")
        label(hb, "Our support team is available to assist you with any issues.", 9, fg=MUTED,
              wraplength=170, justify="left").pack(anchor="w", pady=(4, 10))
        button(hb, "Contact Support", self.contact_support, "outline", 9, pady=6).pack(fill="x")

        main = tk.Frame(root, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(main, bg="white", highlightthickness=1, highlightbackground=BORDER)
        top.pack(fill="x")
        ti = tk.Frame(top, bg="white")
        ti.pack(fill="x", padx=28, pady=14)
        self.greet = label(ti, "", 15, True)
        self.greet.pack(side="left")
        self.chip = tk.Frame(ti, bg="white", cursor="hand2")
        self.chip.pack(side="right")
        self.bell = tk.Label(ti, text="", font=fnt(10, True), bg="white", fg=MUTED, cursor="hand2", padx=6)
        self.bell.pack(side="right", padx=(0, 18))
        self.bell.bind("<Button-1>", lambda e: self.show_notifications())
        self.content = tk.Frame(main, bg=BG)
        self.content.pack(fill="both", expand=True)
        self.user_page("dashboard")

    def refresh_top(self):
        u = self.me()
        hr = datetime.now().hour
        part = "morning" if hr < 12 else "afternoon" if hr < 18 else "evening"
        self.greet.config(text=f"Good {part}, {u['first_name']}")
        n = len([r for r in NOTIFICATIONS if r["user_id"] == u["id"] and not r["seen"]])
        self.bell.config(text=f"Notifications ({n})" if n else "Notifications", fg=RED if n else MUTED)
        for w in self.chip.winfo_children():
            w.destroy()
        avatar(self.chip, full_name(u), 34).pack(side="left", padx=(0, 10))
        tx = tk.Frame(self.chip, bg="white")
        tx.pack(side="left")
        label(tx, full_name(u), 10, True).pack(anchor="w")
        label(tx, "Regular User", 9, fg=FAINT).pack(anchor="w")
        label(self.chip, "\u25be", 9, fg=FAINT).pack(side="left", padx=(8, 0))

        def wire(w):
            w.bind("<Button-1>", self.user_menu)
            for ch in w.winfo_children():
                wire(ch)
        wire(self.chip)

    def user_menu(self, e):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="Profile & Settings", command=lambda: self.user_page("settings"))
        m.add_command(label="Help & Support", command=self.contact_support)
        m.add_separator()
        m.add_command(label="Log out", command=self.logout)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def show_notifications(self):
        uid = self.user["id"]
        rows = list(reversed(find_all(NOTIFICATIONS, user_id=uid)))[:10]
        for r in find_all(NOTIFICATIONS, user_id=uid):
            r["seen"] = 1
        messagebox.showinfo("Notifications",
                            "\n\n".join(f"{r['body']}\n({r['ts']})" for r in rows)
                            if rows else "You're all caught up.")
        self.refresh_top()

    def user_page(self, key):
        self.cancel_timers()
        self.ukey = key
        for w in self.content.winfo_children():
            w.destroy()
        for k, l in self.nav.items():
            l.config(bg="#eeeeee" if k == key else "white")
        sc = Scroll(self.content)
        sc.pack(fill="both", expand=True)
        pad = tk.Frame(sc.body, bg=BG)
        pad.pack(fill="both", expand=True, padx=28, pady=24)
        getattr(self, "upage_" + key)(pad)
        self.refresh_top()

    def upage_dashboard(self, pad):
        g = tk.Frame(pad, bg=BG)
        g.pack(fill="both", expand=True)
        g.columnconfigure(0, weight=3)
        g.columnconfigure(1, weight=2, minsize=300)
        left = tk.Frame(g, bg=BG)
        left.grid(row=0, column=0, sticky="new", padx=(0, 18))
        right = tk.Frame(g, bg=BG)
        right.grid(row=0, column=1, sticky="new")
        self.card_reservation(left)
        self.card_map(left)
        self.card_recent(left)
        self.card_vehicle(right)
        self.card_month(right)

    def card_reservation(self, p):
        c = card(p, 22)
        c.pack(fill="x", pady=(0, 18))
        r = active_res(self.user["id"])
        if not r:
            label(c, "ACTIVE RESERVATION", 8, True, FAINT).pack(anchor="w")
            label(c, "No active reservation", 15, True).pack(anchor="w", pady=(4, 2))
            label(c, "Pick a free space on the live map below to reserve it.", 10, fg=MUTED).pack(anchor="w")
            return
        top = tk.Frame(c, bg=CARD)
        top.pack(fill="x")
        lf = tk.Frame(top, bg=CARD)
        lf.pack(side="left")
        label(lf, "ACTIVE RESERVATION", 8, True, FAINT).pack(anchor="w")
        label(lf, r["garage"] or GARAGE, 17, True).pack(anchor="w")
        label(lf, ADDRESS, 10, fg=MUTED).pack(anchor="w")
        tk.Label(top, text="\u25cf  " + ("Confirmed" if r["status"] == "awaiting" else "Arrived"),
                 font=fnt(9, True), bg="#eeeeee", padx=10, pady=3).pack(side="right", anchor="n")
        boxes = tk.Frame(c, bg=CARD)
        boxes.pack(fill="x", pady=16)
        vals = (("Space", r["space"]), ("Starts", hhmm(r["start_ts"])),
                ("Ends", hhmm(r["end_ts"])), ("Rate", f"${r['rate']:.2f}/hr"))
        for i, (k, v) in enumerate(vals):
            boxes.columnconfigure(i, weight=1, uniform="rbox")
            bx = tk.Frame(boxes, bg=BG, padx=12, pady=10)
            bx.grid(row=0, column=i, sticky="ew", padx=4)
            label(bx, k, 8, fg=FAINT).pack(anchor="w")
            label(bx, v, 13, True).pack(anchor="w")
        hline(c)
        bot = tk.Frame(c, bg=CARD)
        bot.pack(fill="x", pady=(14, 0))
        tl = tk.Frame(bot, bg=CARD)
        tl.pack(side="left")
        label(tl, "Time remaining", 9, fg=FAINT).pack(anchor="w")
        self.remain = label(tl, "--:--:--", 24, True)
        self.remain.pack(anchor="w")
        btns = tk.Frame(bot, bg=CARD)
        btns.pack(side="right")
        button(btns, "Extend", lambda: self.extend(r["id"]), "outline").pack(side="left", padx=8)
        cb = button(btns, "Confirm Arrival", lambda: self.arrive(r["id"]))
        cb.pack(side="left")
        if r["status"] == "confirmed":
            disable(cb, "Arrival confirmed")
        self.res_end = datetime.fromisoformat(r["end_ts"])
        self.tick()
        self.every(1000, self.tick)

    def tick(self):
        s = int((self.res_end - datetime.now()).total_seconds())
        if s <= 0:
            self.remain.config(text="Expired", fg=RED)
        else:
            self.remain.config(text=f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}")

    def extend(self, rid):
        r = find(RESERVATIONS, id=rid)
        base = max(datetime.fromisoformat(r["end_ts"]), datetime.now())
        r["end_ts"] = (base + timedelta(minutes=30)).isoformat(timespec="seconds")
        log(f"{r['user_name']} extended space {r['space']} by 30 minutes.")
        self.toast("Reservation extended by 30 minutes.")
        self.user_page("dashboard")

    def arrive(self, rid):
        r = set_res_status(rid, "confirmed")
        log(f"{r['user_name']} confirmed arrival at space {r['space']}.")
        self.toast("Arrival confirmed - enjoy your stay!")
        self.user_page("dashboard")

    def card_map(self, p):
        c = card(p, 0)
        c.pack(fill="x", pady=(0, 18))
        sp = SPACES
        free = sum(1 for s in sp if s["status"] == "available")
        head = tk.Frame(c, bg=CARD)
        head.pack(fill="x", padx=22, pady=(18, 12))
        hl = tk.Frame(head, bg=CARD)
        hl.pack(side="left")
        label(hl, "Live Lot Map", 13, True).pack(anchor="w")
        label(hl, f"{GARAGE} \u00b7 {free} of {len(sp)} spaces free", 9, fg=MUTED).pack(anchor="w")
        lg = tk.Frame(head, bg=CARD)
        lg.pack(side="right")
        for text, col in (("Free", "white"), ("Occupied", "#e9eaec"), ("Yours", TEXT)):
            tk.Frame(lg, bg=col, width=11, height=11, highlightthickness=1,
                     highlightbackground=BORDER).pack(side="left", padx=(12, 4))
            label(lg, text, 9, fg=MUTED).pack(side="left")
        hline(c)
        body = tk.Frame(c, bg=CARD)
        body.pack(fill="x", padx=22, pady=(0, 16))
        mine = active_res(self.user["id"])
        mine_space = mine["space"] if mine else None

        def render():
            for w in body.winfo_children():
                w.destroy()
            tb = tk.Frame(body, bg=CARD)
            tb.pack(fill="x", pady=(12, 8))
            label(tb, "Lot A \u00b7 Section", 9, fg=MUTED).pack(side="left")
            for s in SECTIONS:
                on = s == self.map_sec
                t = tk.Label(tb, text=s, font=fnt(9, True), padx=10, pady=2, cursor="hand2",
                             bg=TEXT if on else "#eeeeee", fg="white" if on else TEXT)
                t.pack(side="left", padx=(6, 0))
                t.bind("<Button-1>", lambda e, s=s: (setattr(self, "map_sec", s), render()))
            grid = tk.Frame(body, bg=CARD)
            grid.pack(fill="x")
            for i, s in enumerate([s for s in sp if s["section"] == self.map_sec]):
                col = i % 8
                grid.columnconfigure(col, weight=1, uniform="cell")
                if s["id"] == mine_space:
                    bg, fg = TEXT, "white"
                elif s["status"] == "available":
                    bg, fg = "white", TEXT
                else:
                    bg, fg = "#f0f1f3", "#b0b0b0"
                cell = tk.Label(grid, text=s["id"].split("-")[1], font=fnt(9, True), bg=bg, fg=fg,
                                highlightthickness=1, highlightbackground=BORDER, pady=13,
                                cursor="hand2" if s["status"] == "available" else "arrow")
                cell.grid(row=i // 8, column=col, sticky="ew", padx=3, pady=3)
                if s["status"] == "available":
                    cell.bind("<Button-1>", lambda e, sid=s["id"]: self.reserve(sid))
        render()
        hint = "Tap a free space to reserve it"
        if mine_space:
            hint += f" \u00b7 Space {mine_space} is your reservation"
        label(c, hint, 9, fg=FAINT).pack(anchor="w", padx=22, pady=(0, 16))

    def reserve(self, sid):
        if not system_active():
            messagebox.showwarning("Reservations paused",
                                   "Reservations are temporarily paused by the administrators.")
            return
        me = self.me()
        s = find(SPACES, id=sid)
        if not s or s["status"] != "available":
            self.toast(f"Space {sid} was just taken.")
            self.user_page("dashboard")
            return
        cur = active_res(me["id"])
        msg = f"Reserve space {sid} at {GARAGE}?"
        if cur:
            msg += f"\n\nThis replaces your current reservation (space {cur['space']})."
        if not messagebox.askyesno("Reserve space", msg):
            return
        if cur:
            set_res_status(cur["id"], "cancelled")
            log(f"{full_name(me)} cancelled space {cur['space']} to switch spaces.")
        make_res(me["id"], full_name(me), sid, "awaiting", 2)
        log(f"{full_name(me)} reserved space {sid}.")
        self.toast(f"Space {sid} reserved.")
        self.user_page("dashboard")

    def card_recent(self, p):
        c = card(p, 0)
        c.pack(fill="x")
        h = tk.Frame(c, bg=CARD)
        h.pack(fill="x", padx=22, pady=(18, 8))
        label(h, "Recent Activity", 13, True).pack(side="left")
        link(h, "View all", lambda: self.user_page("history"), 9, MUTED, False).pack(side="right")
        rows = sorted(find_all(SESSIONS, user_id=self.user["id"]),
                     key=lambda r: (r["date"], r["id"]), reverse=True)[:3]
        if not rows:
            label(c, "No past sessions yet.", 10, fg=FAINT).pack(anchor="w", padx=22, pady=(4, 20))
            return
        for s in rows:
            hline(c)
            r = tk.Frame(c, bg=CARD)
            r.pack(fill="x", padx=22, pady=12)
            tk.Label(r, text="\u2713", font=fnt(10, True), bg=BG, fg=TEXT, width=3,
                     pady=4).pack(side="left", padx=(0, 12))
            tx = tk.Frame(r, bg=CARD)
            tx.pack(side="left")
            label(tx, s["place"], 10, True).pack(anchor="w")
            d = datetime.fromisoformat(s["date"]).strftime("%b %d")
            label(tx, f"{d} \u00b7 {s['duration']} \u00b7 {s['spot']}", 9, fg=MUTED).pack(anchor="w")
            label(r, f"${s['price']:.2f}", 10, True).pack(side="right")

    def vehicle_row(self, p, v, big=False, manage=False):
        bg = BG if big else p.cget("bg")
        r = tk.Frame(p, bg=bg, padx=12 if big else 0, pady=10 if big else 6)
        r.pack(fill="x", pady=(0, 6))
        tk.Label(r, text="EV" if v["vtype"] == "EV" else "CAR", font=fnt(8, True), bg="white", fg=TEXT,
                 width=5, pady=6, highlightthickness=1,
                 highlightbackground=BORDER).pack(side="left", padx=(0, 12))
        tx = tk.Frame(r, bg=bg)
        tx.pack(side="left")
        label(tx, v["label"] + ("  (Primary)" if manage and v["is_primary"] else ""), 10, True).pack(anchor="w")
        label(tx, f"{v['vtype']} \u00b7 Plate {v['plate']}", 9, fg=MUTED).pack(anchor="w")
        if manage or not big:
            link(r, "Remove", lambda: self.remove_vehicle(v), 9, MUTED, False).pack(side="right")
        if manage and not v["is_primary"]:
            link(r, "Set primary", lambda: self.set_primary(v["id"]), 9).pack(side="right", padx=12)

    def set_primary(self, vid):
        for v in find_all(VEHICLES, user_id=self.user["id"]):
            v["is_primary"] = 1 if v["id"] == vid else 0
        self.toast("Primary vehicle updated.")
        self.user_page(self.ukey)

    def remove_vehicle(self, v):
        if not messagebox.askyesno("Remove vehicle", f"Remove {v['label']}?"):
            return
        VEHICLES.remove(v)
        if v["is_primary"]:
            remaining = sorted(find_all(VEHICLES, user_id=self.user["id"]), key=lambda r: r["id"])
            if remaining:
                remaining[0]["is_primary"] = 1
        self.toast(f"{v['label']} removed.")
        self.user_page(self.ukey)

    def add_vehicle(self):
        def save(v):
            if not v["model"] or not v["plate"]:
                return "Enter a make/model and a license plate."
            first = len(find_all(VEHICLES, user_id=self.user["id"])) == 0
            VEHICLES.append({"id": nid("vehicles"), "user_id": self.user["id"], "label": v["model"],
                            "plate": v["plate"], "vtype": v["type"], "is_primary": 1 if first else 0})
            self.toast(f"{v['model']} added.")
            self.user_page(self.ukey)
        form(self, "Add a vehicle",
             [("model", "Make & model", "entry", "e.g. Subaru Outback"),
              ("plate", "License plate", "entry", "e.g. 4XPL-882"),
              ("type", "Type", "combo", ["Gas", "EV", "Hybrid"])], "Add vehicle", save)

    def contact_support(self):
        def send(v):
            if not v["msg"]:
                return "Type a message first."
            SUPPORT.append({"id": nid("support"), "user_id": self.user["id"], "email": self.user["email"],
                           "body": v["msg"], "ts": stamp()})
            self.toast("Support request sent - we'll follow up by email.")
        form(self, "Contact Support", [("msg", "Message", "area", None)], "Send", send,
             "Tell us what's going on and we'll follow up by email.")

    def card_vehicle(self, p):
        c = card(p, 20)
        c.pack(fill="x", pady=(0, 18))
        label(c, "Your Vehicle", 13, True).pack(anchor="w", pady=(0, 12))
        vs = sorted(find_all(VEHICLES, user_id=self.user["id"]), key=lambda r: (-r["is_primary"], r["id"]))
        if not vs:
            label(c, "No vehicles yet.", 10, fg=MUTED).pack(anchor="w")
        else:
            self.vehicle_row(c, vs[0], big=True)
            if len(vs) > 1:
                label(c, "Other vehicles", 9, fg=FAINT).pack(anchor="w", pady=(12, 6))
                for v in vs[1:]:
                    self.vehicle_row(c, v)
        add = tk.Frame(c, bg=CARD, highlightthickness=1, highlightbackground=BORDER, cursor="hand2",
                       padx=12, pady=10)
        add.pack(fill="x", pady=(12, 0))
        a1 = label(add, "+  Add vehicle", 10, True, cursor="hand2")
        a1.pack(anchor="w")
        a2 = label(add, "Link a new plate", 9, fg=FAINT, cursor="hand2")
        a2.pack(anchor="w")
        for w in (add, a1, a2):
            w.bind("<Button-1>", lambda e: self.add_vehicle())

    def card_month(self, p):
        c = card(p, 20)
        c.pack(fill="x")
        label(c, "This Month", 13, True).pack(anchor="w", pady=(0, 6))
        month = datetime.now().strftime("%Y-%m")
        rows = [r for r in SESSIONS if r["user_id"] == self.user["id"] and r["date"][:7] == month]
        n = len(rows)
        hrs = sum(r["hours"] for r in rows)
        spent = sum(r["price"] for r in rows)
        for name, val in (("Sessions", str(n)), ("Hours parked", f"{hrs:.1f}"), ("Total spent", f"${spent:,.2f}")):
            label(c, name, 9, fg=MUTED).pack(anchor="w", pady=(10, 0))
            label(c, val, 18, True).pack(anchor="w")
        hline(c, 14)
        label(c, "Average per session", 9, fg=MUTED).pack(anchor="w")
        label(c, f"${(spent / n if n else 0):.2f}", 14, True).pack(anchor="w")

    def upage_vehicles(self, pad):
        c = card(pad, 22)
        c.pack(fill="x")
        h = tk.Frame(c, bg=CARD)
        h.pack(fill="x", pady=(0, 12))
        label(h, "My Vehicles", 15, True).pack(side="left")
        button(h, "+ Add vehicle", self.add_vehicle).pack(side="right")
        vs = sorted(find_all(VEHICLES, user_id=self.user["id"]), key=lambda r: (-r["is_primary"], r["id"]))
        if not vs:
            label(c, "You haven't added a vehicle yet.", 10, fg=MUTED).pack(anchor="w")
        for v in vs:
            self.vehicle_row(c, v, big=True, manage=True)

    def upage_history(self, pad):
        c = card(pad, 22)
        c.pack(fill="both", expand=True)
        label(c, "Parking History", 15, True).pack(anchor="w", pady=(0, 12))
        cols = ("Location", "Date", "Duration", "Space / Meter", "Total")
        t = ttk.Treeview(c, columns=cols, show="headings", height=12)
        for col, w in zip(cols, (240, 90, 90, 130, 90)):
            t.heading(col, text=col)
            t.column(col, width=w, anchor="e" if col == "Total" else "w")
        rows = sorted(find_all(SESSIONS, user_id=self.user["id"]), key=lambda r: (r["date"], r["id"]), reverse=True)
        for s in rows:
            t.insert("", "end", values=(s["place"], datetime.fromisoformat(s["date"]).strftime("%b %d"),
                                        s["duration"], s["spot"], f"${s['price']:.2f}"))
        t.pack(fill="both", expand=True)
        if not rows:
            label(c, "No past sessions yet.", 10, fg=FAINT).pack(anchor="w", pady=10)

    def upage_settings(self, pad):
        u = self.me()
        c = card(pad, 24)
        c.pack(anchor="w")
        label(c, "Settings", 15, True).pack(anchor="w", pady=(0, 4))
        F = {}
        for k, lab, val in (("first", "First name", u["first_name"]), ("last", "Last name", u["last_name"]),
                            ("email", "Email", u["email"])):
            label(c, lab, 10, True).pack(anchor="w", pady=(10, 4))
            F[k] = Field(c, value=val, width=42)
            F[k].pack(fill="x")
        ne, ns = tk.IntVar(value=u["notify_email"]), tk.IntVar(value=u["notify_sms"])
        for var, text in ((ne, "Email notifications"), (ns, "SMS reminders")):
            tk.Checkbutton(c, text=text, variable=var, bg=CARD, activebackground=CARD, selectcolor="white",
                           font=fnt(10), highlightthickness=0, bd=0).pack(anchor="w", pady=(10, 0))
        msg = label(c, "", 9, fg=RED)
        msg.pack(anchor="w", pady=(10, 0))

        def save():
            first, last, email = F["first"].get().strip(), F["last"].get().strip(), F["email"].get().strip().lower()
            if not first or not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
                msg.config(text="Enter your first name and a valid email address.")
                return
            if any(r["email"] == email and r["id"] != u["id"] for r in USERS):
                msg.config(text="That email is already used by another account.")
                return
            u["first_name"], u["last_name"], u["email"] = first, last, email
            u["notify_email"], u["notify_sms"] = ne.get(), ns.get()
            self.toast("Settings saved.")
            self.user_page("settings")
        button(c, "Save changes", save).pack(anchor="w", pady=(10, 0))

        hline(c, 20)
        label(c, "Change password", 12, True).pack(anchor="w")
        label(c, "Current password", 10, True).pack(anchor="w", pady=(10, 4))
        cur = Field(c, show="\u2022", toggle=True, width=42)
        cur.pack(fill="x")
        label(c, "New password (8+ characters)", 10, True).pack(anchor="w", pady=(10, 4))
        new = Field(c, show="\u2022", toggle=True, width=42)
        new.pack(fill="x")
        msg2 = label(c, "", 9, fg=RED)
        msg2.pack(anchor="w", pady=(10, 0))

        def change():
            if not check_pw(u, cur.get()):
                msg2.config(text="Current password is incorrect.")
            elif len(new.get()) < 8:
                msg2.config(text="New password must be at least 8 characters.")
            else:
                salt, h = new_hash(new.get())
                u["salt"], u["pw"] = salt, h
                cur.clear()
                new.clear()
                msg2.config(text="")
                self.toast("Password updated.")
        button(c, "Update password", change, "outline").pack(anchor="w", pady=(10, 0))

    # ---- admin dashboard ------------------------------------------
    def build_admin(self, root):
        side = tk.Frame(root, bg="white", width=230, highlightthickness=1, highlightbackground=BORDER)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        br = tk.Frame(side, bg="white")
        br.pack(fill="x", padx=18, pady=(22, 20))
        logo(br, 28).pack(side="left")
        label(br, "ParkEase Admin", 12, True).pack(side="left", padx=10)
        self.anav = {}
        for key, text in (("overview", "Overview"), ("map", "Live Map"), ("reservations", "Reservations"),
                          ("users", "Users"), ("history", "History")):
            l = tk.Label(side, text=text, font=fnt(10, True), anchor="w", padx=14, pady=9,
                         cursor="hand2", bg="white", fg=TEXT)
            l.pack(fill="x", padx=12, pady=1)
            l.bind("<Button-1>", lambda e, k=key: self.admin_page(k))
            self.anav[key] = l
        bt = tk.Frame(side, bg="white")
        bt.pack(side="bottom", fill="x", padx=16, pady=16)
        ur = tk.Frame(bt, bg="white")
        ur.pack(fill="x", pady=(0, 12))
        me = self.me()
        avatar(ur, full_name(me), 32).pack(side="left", padx=(0, 10))
        tx = tk.Frame(ur, bg="white")
        tx.pack(side="left")
        label(tx, full_name(me), 10, True).pack(anchor="w")
        label(tx, "Attendant Mode", 9, fg=FAINT).pack(anchor="w")
        button(bt, "Logout", self.logout, "outline", pady=8).pack(fill="x")
        self.content = tk.Frame(root, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)
        self.admin_page("overview")

    def admin_page(self, key):
        self.cancel_timers()
        self.akey = key
        for w in self.content.winfo_children():
            w.destroy()
        for k, l in self.anav.items():
            l.config(bg=TEXT if k == key else "white", fg="white" if k == key else TEXT)
        sc = Scroll(self.content)
        sc.pack(fill="both", expand=True)
        pad = tk.Frame(sc.body, bg=BG)
        pad.pack(fill="both", expand=True, padx=30, pady=26)
        title, sub = {
            "overview": ("Admin Monitoring", "Real-time parking activities and reservation management"),
            "map": ("Live Map", "Click a space to release it, or assign it to a driver"),
            "reservations": ("Reservations", "All reservations, current and past"),
            "users": ("Users", "Drivers and staff on ParkEase"),
            "history": ("History", "Log of admin and system actions"),
        }[key]
        hd = tk.Frame(pad, bg=BG)
        hd.pack(fill="x", pady=(0, 22))
        tl = tk.Frame(hd, bg=BG)
        tl.pack(side="left")
        label(tl, title, 20, True).pack(anchor="w")
        label(tl, sub, 10, fg=MUTED).pack(anchor="w")
        act = tk.Frame(hd, bg=BG)
        act.pack(side="right")
        if key == "users":
            button(act, "+ Add User", self.add_user_dialog).pack()
        elif key != "history":
            if key == "overview":
                self.sys_pill(act).pack(side="left", padx=(0, 10))
            button(act, "+ Manual Entry", self.manual_entry).pack(side="left")
        getattr(self, "apage_" + key)(pad)

    def sys_pill(self, p):
        on = system_active()
        f = tk.Frame(p, bg="white", highlightthickness=1, highlightbackground=BORDER, cursor="hand2")
        d = tk.Label(f, text="\u25cf", fg=GREEN if on else RED, bg="white", font=fnt(9))
        d.pack(side="left", padx=(12, 4), pady=7)
        t = tk.Label(f, text="System Active" if on else "System Paused", font=fnt(10, True), bg="white")
        t.pack(side="left", padx=(0, 12))
        for w in (f, d, t):
            w.bind("<Button-1>", lambda e: self.toggle_system())
        return f

    def toggle_system(self):
        on = not system_active()
        SETTINGS["system_active"] = "1" if on else "0"
        log(f"System status changed to {'Active' if on else 'Paused'} by {full_name(self.user)}.")
        self.admin_page(self.akey)

    def stat_card(self, row, i, title, value, note="", right="", pct=None):
        row.columnconfigure(i, weight=1, uniform="stat")
        c = card(row, 18)
        c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0 if i == 3 else 8))
        label(c, title, 10, fg=MUTED).pack(anchor="w")
        vr = tk.Frame(c, bg=CARD)
        vr.pack(fill="x", pady=(6, 0))
        label(vr, value, 22, True).pack(side="left")
        if right:
            label(vr, right, 8, fg=FAINT).pack(side="right", anchor="s")
        if pct is not None:
            tr = tk.Frame(c, bg="#eeeeee", height=6)
            tr.pack(fill="x", pady=(10, 0))
            tk.Frame(tr, bg=TEXT).place(relx=0, rely=0, relwidth=pct / 100, relheight=1)
        elif note:
            label(c, note, 9, fg=FAINT).pack(anchor="w", pady=(6, 0))

    def apage_overview(self, pad):
        per, total, free = lot_summary()
        used = total - free
        pct = round(100 * used / total) if total else 0
        res = list(reversed(RESERVATIONS))
        active = [r for r in res if r["status"] in ACTIVE]
        awaiting = sum(1 for r in active if r["status"] == "awaiting")
        cutoff = datetime.now() - timedelta(hours=24)
        expired = sum(1 for r in res if r["status"] == "expired"
                      and datetime.fromisoformat(r["end_ts"]) > cutoff)
        flags = sum(u["flags"] for u in USERS)
        row = tk.Frame(pad, bg=BG)
        row.pack(fill="x", pady=(0, 18))
        self.stat_card(row, 0, "Total Occupancy", f"{pct}%", right=f"{used}/{total} Spaces", pct=pct)
        self.stat_card(row, 1, "Active Reservations", str(len(active)), f"{awaiting} awaiting arrival")
        self.stat_card(row, 2, "Expired (No-show)", f"{expired:02d}", "Last 24 hours")
        self.stat_card(row, 3, "Abuse Flags", f"{flags:02d}", "Requires review")

        g = tk.Frame(pad, bg=BG)
        g.pack(fill="both", expand=True)
        g.columnconfigure(0, weight=5)
        g.columnconfigure(1, weight=3, minsize=290)
        left = card(g, 0)
        left.grid(row=0, column=0, sticky="new", padx=(0, 18))
        hd = tk.Frame(left, bg=CARD)
        hd.pack(fill="x", padx=20, pady=(18, 10))
        label(hd, "Active Reservations & Arrivals", 12, True).pack(side="left")
        button(hd, "Export", self.export_csv, "outline", 9, pady=4).pack(side="right")
        flt = tk.StringVar(value="All")
        cb = ttk.Combobox(hd, textvariable=flt, values=("All", "Awaiting Arrival", "Confirmed"),
                          state="readonly", width=15)
        cb.pack(side="right", padx=8)
        tbl = tk.Frame(left, bg=CARD)
        tbl.pack(fill="x", pady=(0, 6))
        for i, wt in enumerate((3, 1, 1, 2, 2)):
            tbl.columnconfigure(i, weight=wt)

        def draw(e=None):
            for w in tbl.winfo_children():
                w.destroy()
            for i, t in enumerate(("User", "Space", "Reserved At", "Status", "Actions")):
                label(tbl, t, 9, fg=FAINT).grid(row=0, column=i, sticky="w",
                                                padx=(20 if i == 0 else 6, 6), pady=(4, 10))
            rows = [r for r in active if flt.get() == "All" or STATUS_LABEL[r["status"]] == flt.get()]
            if not rows:
                label(tbl, "No active reservations.", 10, fg=FAINT).grid(row=1, column=0, columnspan=5, pady=24)
                return
            for n, r in enumerate(rows):
                tk.Frame(tbl, bg=BORDER, height=1).grid(row=2 * n + 1, column=0, columnspan=5, sticky="ew")
                ro = 2 * n + 2
                uc = tk.Frame(tbl, bg=CARD)
                uc.grid(row=ro, column=0, sticky="w", padx=(20, 6), pady=10)
                avatar(uc, r["user_name"], 28).pack(side="left", padx=(0, 10))
                label(uc, r["user_name"], 10).pack(side="left")
                label(tbl, r["space"], 10).grid(row=ro, column=1, sticky="w", padx=6)
                label(tbl, hhmm(r["start_ts"]), 10).grid(row=ro, column=2, sticky="w", padx=6)
                pill(tbl, STATUS_LABEL[r["status"]], r["status"]).grid(row=ro, column=3, sticky="w", padx=6)
                ac = tk.Frame(tbl, bg=CARD)
                ac.grid(row=ro, column=4, sticky="w", padx=6)
                link(ac, "Release", lambda rid=r["id"]: self.release(rid), 9).pack(side="left", padx=(0, 10))
                link(ac, "Manage", lambda rid=r["id"]: self.manage(rid), 9).pack(side="left")
        cb.bind("<<ComboboxSelected>>", draw)
        draw()

        rt = tk.Frame(g, bg=BG)
        rt.grid(row=0, column=1, sticky="new")
        self.alerts_card(rt)
        self.space_card(rt, per)

    def alerts_card(self, p):
        c = card(p, 20)
        c.pack(fill="x", pady=(0, 18))
        label(c, "Reservation Alerts", 12, True).pack(anchor="w", pady=(0, 8))
        al = list(reversed(ALERTS))
        if not al:
            label(c, "No active alerts.", 10, fg=FAINT).pack(pady=14)
        for a in al:
            warn = a["kind"] == "warning"
            box = tk.Frame(c, bg=BG if warn else CARD, padx=12, pady=10,
                           highlightthickness=1 if warn else 0, highlightbackground=BORDER)
            box.pack(fill="x", pady=(0, 8))
            tk.Label(box, text="!" if warn else "i", font=fnt(9, True), width=2,
                     bg="#fdf0d5" if warn else "#e4edfa",
                     fg="#9a6b00" if warn else "#2a6fce").pack(side="left", anchor="n", padx=(0, 10))
            tx = tk.Frame(box, bg=box.cget("bg"))
            tx.pack(side="left", fill="x", expand=True)
            label(tx, a["title"], 10, True).pack(anchor="w")
            label(tx, a["body"], 9, fg=MUTED, wraplength=210, justify="left").pack(anchor="w", pady=(2, 6))
            if warn:
                ar = tk.Frame(tx, bg=tx.cget("bg"))
                ar.pack(anchor="w")
                button(ar, "Flag User", lambda aid=a["id"]: self.flag_alert(aid), "outline", 8,
                       padx=10, pady=4).pack(side="left", padx=(0, 6))
                button(ar, "Dismiss", lambda aid=a["id"]: self.dismiss_alert(aid), "outline", 8,
                       padx=10, pady=4).pack(side="left")
            else:
                label(tx, a["ts"], 8, fg=FAINT).pack(anchor="w")
                link(tx, "Dismiss", lambda aid=a["id"]: self.dismiss_alert(aid), 8, MUTED, False).pack(anchor="w")

    def dismiss_alert(self, aid):
        a = find(ALERTS, id=aid)
        if a:
            ALERTS.remove(a)
        self.toast("Alert dismissed.")
        self.admin_page(self.akey)

    def flag_alert(self, aid):
        a = find(ALERTS, id=aid)
        m = re.search(r"'([^']+)'", a["body"]) if a else None
        name = m.group(1) if m else ""
        target = next((u for u in USERS if full_name(u).lower() == name.lower()), None)
        if target:
            target["flags"] += 1
            notify(target["id"], "Your account was flagged for review after a missed reservation.")
            log(f"{name} flagged for review from a reservation alert.")
        if a:
            ALERTS.remove(a)
        self.toast(f"{name} flagged." if target else "Couldn't find that user - alert dismissed.")
        self.admin_page(self.akey)

    def space_card(self, p, per):
        c = card(p, 20)
        c.pack(fill="x")
        label(c, "Space Management", 12, True).pack(anchor="w", pady=(0, 10))
        for s, v in per.items():
            r = tk.Frame(c, bg=CARD, highlightthickness=1, highlightbackground=BORDER, padx=10, pady=8)
            r.pack(fill="x", pady=3)
            label(r, f"Section {s}", 10).pack(side="left")
            txt = f"{v['total']}/{v['total']} Full" if v["free"] == 0 else f"{v['free']}/{v['total']} Available"
            label(r, txt, 10, True).pack(side="right")
        link(c, "View Detailed Map", lambda: self.admin_page("map"), 10).pack(pady=(12, 0))

    def apage_map(self, pad):
        c = card(pad, 22)
        c.pack(fill="x")
        lg = tk.Frame(c, bg=CARD)
        lg.pack(anchor="w", pady=(0, 14))
        for text, col in (("Available", "#dcefe0"), ("Reserved", AMBER), ("Occupied", TEXT)):
            tk.Frame(lg, bg=col, width=13, height=13).pack(side="left", padx=(0, 5))
            label(lg, text, 10).pack(side="left", padx=(0, 18))
        sp = SPACES
        for sec in SECTIONS:
            label(c, f"SECTION {sec}", 9, True, MUTED).pack(anchor="w", pady=(6, 8))
            grid = tk.Frame(c, bg=CARD)
            grid.pack(fill="x", pady=(0, 14))
            for i, spc in enumerate([s for s in sp if s["section"] == sec]):
                bg, fg = {"available": ("#dcefe0", GREEN),
                          "reserved": (AMBER, "#5a4300")}.get(spc["status"], (TEXT, "white"))
                grid.columnconfigure(i % 12, weight=1, uniform="mapcol")
                cell = tk.Label(grid, text=spc["id"].split("-")[1], font=fnt(8, True), bg=bg, fg=fg,
                                pady=7, cursor="hand2")
                cell.grid(row=i // 12, column=i % 12, sticky="ew", padx=2, pady=2)
                cell.bind("<Button-1>", lambda e, sid=spc["id"]: self.map_click(sid))

    def map_click(self, sid):
        s = find(SPACES, id=sid)
        if s["status"] == "available":
            if messagebox.askyesno(f"Space {sid}", f"Space {sid} is available. Open Manual Entry to assign it?"):
                self.manual_entry(sid)
            return
        cands = [x for x in RESERVATIONS if x["space"] == sid and x["status"] in ACTIVE]
        r = cands[-1] if cands else None
        if r:
            if messagebox.askyesno(f"Space {sid}", f"Space {sid} is {s['status']}, held by "
                                                   f"{r['user_name']}. Release it now?"):
                self.release(r["id"], ask=False)
        elif messagebox.askyesno(f"Space {sid}", f"Space {sid} is marked {s['status']} with no linked "
                                                 "reservation. Mark it available?"):
            space_set(sid, "available")
            log(f"Space {sid} manually marked available by {full_name(self.user)}.")
            self.toast(f"Space {sid} is now available.")
            self.admin_page(self.akey)

    def release(self, rid, ask=True):
        r = find(RESERVATIONS, id=rid)
        if not r:
            return
        if r["status"] not in ACTIVE:
            self.toast("That reservation isn't active.")
            return
        if ask and not messagebox.askyesno("Release space", f"Release space {r['space']} held by {r['user_name']}?"):
            return
        set_res_status(rid, "cancelled")
        log(f"Space {r['space']} released by {full_name(self.user)}.")
        notify(r["user_id"], f"Your reservation for space {r['space']} was released by staff.")
        self.toast(f"Space {r['space']} released.")
        self.admin_page(self.akey)

    def manage(self, rid):
        r = find(RESERVATIONS, id=rid)
        if not r:
            return
        cur = STATUS_LABEL[r["status"]]
        opts = [cur] + [v for v in STATUS_LABEL.values() if v != cur]

        def save(v):
            new = LABEL_STATUS[v["status"]]
            if new in ACTIVE and r["status"] not in ACTIVE:
                s = find(SPACES, id=r["space"])
                if s and s["status"] != "available":
                    return f"Space {r['space']} isn't free right now."
            set_res_status(rid, new)
            log(f"Reservation for {r['user_name']} (space {r['space']}) set to {STATUS_LABEL[new]}.")
            notify(r["user_id"], f"Your reservation for space {r['space']} is now {STATUS_LABEL[new]}.")
            self.toast("Reservation updated.")
            self.admin_page(self.akey)
        form(self, "Manage Reservation",
             [("user", "User", "text", r["user_name"]), ("space", "Space", "text", r["space"]),
              ("status", "Status", "combo", opts)], "Save", save)

    def manual_entry(self, space=None):
        free = [s["id"] for s in SPACES if s["status"] == "available"]
        if not free:
            messagebox.showinfo("Manual Entry", "There are no free spaces right now.")
            return
        if space in free:
            free.remove(space)
            free.insert(0, space)
        drivers = sorted(find_all(USERS, role="user"), key=lambda u: u["first_name"])

        def save(v):
            if not v["user"]:
                return "Enter or pick a driver name."
            match = next((u for u in drivers if full_name(u).lower() == v["user"].lower()), None)
            if match and active_res(match["id"]):
                return f"{full_name(match)} already has an active reservation."
            name = full_name(match) if match else v["user"]
            status = LABEL_STATUS[v["status"]]
            make_res(match["id"] if match else None, name, v["space"], status, 2)
            log(f"Manual entry: {name} assigned to space {v['space']} ({STATUS_LABEL[status]}).")
            if match:
                notify(match["id"], f"Staff reserved space {v['space']} for you.")
            self.toast(f"Reservation created for {name}.")
            self.admin_page(self.akey)
        form(self, "Manual Entry",
             [("user", "Driver name", "combo_edit", [full_name(u) for u in drivers]),
              ("space", "Space", "combo", free),
              ("status", "Status", "combo", ["Confirmed", "Awaiting Arrival"])],
             "Create Reservation", save, "Pick a registered driver or type a walk-in's name.")

    def export_csv(self):
        path = os.path.join(BASE, "parkease-reservations.csv")
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["User", "Space", "Reserved At", "Ends", "Status"])
                for r in reversed(RESERVATIONS):
                    w.writerow([r["user_name"], r["space"], hhmm(r["start_ts"]), hhmm(r["end_ts"]),
                                STATUS_LABEL[r["status"]]])
        except OSError as err:
            messagebox.showerror("Export failed", str(err))
            return
        messagebox.showinfo("Export complete", f"Saved to:\n{path}")

    def apage_reservations(self, pad):
        c = card(pad, 20)
        c.pack(fill="both", expand=True)
        bar = tk.Frame(c, bg=CARD)
        bar.pack(fill="x", pady=(0, 12))
        srch = Field(bar, "Search by user or space\u2026", width=30)
        srch.pack(side="left")
        st = tk.StringVar(value="All statuses")
        cb = ttk.Combobox(bar, textvariable=st, values=["All statuses"] + list(STATUS_LABEL.values()),
                          state="readonly", width=16)
        cb.pack(side="left", padx=10)
        button(bar, "Export", self.export_csv, "outline", 9, pady=6).pack(side="right")
        cols = ("User", "Space", "Reserved At", "Ends", "Status")
        tree = ttk.Treeview(c, columns=cols, show="headings", height=14, selectmode="browse")
        for col, wd in zip(cols, (200, 80, 110, 110, 140)):
            tree.heading(col, text=col)
            tree.column(col, width=wd, anchor="w")
        tree.pack(fill="both", expand=True)

        def load(e=None):
            tree.delete(*tree.get_children())
            term = srch.get().strip().lower()
            for r in reversed(RESERVATIONS):
                if st.get() != "All statuses" and STATUS_LABEL[r["status"]] != st.get():
                    continue
                if term and term not in r["user_name"].lower() and term not in r["space"].lower():
                    continue
                tree.insert("", "end", iid=str(r["id"]),
                            values=(r["user_name"], r["space"], hhmm(r["start_ts"]), hhmm(r["end_ts"]),
                                    STATUS_LABEL[r["status"]]))

        def act(fn):
            sel = tree.selection()
            if not sel:
                self.toast("Select a reservation first.")
                return
            fn(int(sel[0]))
        ar = tk.Frame(c, bg=CARD)
        ar.pack(fill="x", pady=(12, 0))
        button(ar, "Manage selected", lambda: act(self.manage), "outline").pack(side="left")
        button(ar, "Release selected", lambda: act(self.release), "outline").pack(side="left", padx=10)
        srch.e.bind("<KeyRelease>", load)
        cb.bind("<<ComboboxSelected>>", load)
        tree.bind("<Double-1>", lambda e: act(self.manage))
        load()

    def apage_users(self, pad):
        c = card(pad, 20)
        c.pack(fill="both", expand=True)
        srch = Field(c, "Search users\u2026", width=34)
        srch.pack(anchor="w", pady=(0, 12))
        cols = ("Name", "Email", "Role", "Vehicle", "Flags")
        tree = ttk.Treeview(c, columns=cols, show="headings", height=14, selectmode="browse")
        for col, wd in zip(cols, (170, 230, 90, 170, 60)):
            tree.heading(col, text=col)
            tree.column(col, width=wd, anchor="w")
        tree.pack(fill="both", expand=True)

        def load(e=None):
            tree.delete(*tree.get_children())
            term = srch.get().strip().lower()
            for u in USERS:
                if term and term not in full_name(u).lower() and term not in u["email"]:
                    continue
                vs = sorted(find_all(VEHICLES, user_id=u["id"]), key=lambda r: -r["is_primary"])
                v = vs[0] if vs else None
                tree.insert("", "end", iid=str(u["id"]),
                            values=(full_name(u), u["email"], ROLE_LABEL.get(u["role"], u["role"]),
                                    v["label"] if v else "\u2014", u["flags"] or "\u2014"))

        def act(fn):
            sel = tree.selection()
            if not sel:
                self.toast("Select a user first.")
                return
            fn(int(sel[0]))
        ar = tk.Frame(c, bg=CARD)
        ar.pack(fill="x", pady=(12, 0))
        button(ar, "Remove selected", lambda: act(self.remove_user), "outline").pack(side="left")
        button(ar, "Clear flags", lambda: act(self.clear_flags), "outline").pack(side="left", padx=10)
        srch.e.bind("<KeyRelease>", load)
        load()

    def remove_user(self, uid):
        u = find(USERS, id=uid)
        if not u:
            return
        if uid == self.user["id"]:
            messagebox.showwarning("Remove user", "You can't remove the account you're logged in with.")
            return
        if u["role"] == "admin" and len(find_all(USERS, role="admin")) < 2:
            messagebox.showwarning("Remove user", "There must be at least one admin account.")
            return
        if not messagebox.askyesno("Remove user", f"Remove {full_name(u)} and their vehicles?"):
            return
        for v in find_all(VEHICLES, user_id=uid):
            VEHICLES.remove(v)
        for n in find_all(NOTIFICATIONS, user_id=uid):
            NOTIFICATIONS.remove(n)
        USERS.remove(u)
        log(f"User {full_name(u)} removed by {full_name(self.user)}.")
        self.toast(f"{full_name(u)} removed.")
        self.admin_page(self.akey)

    def clear_flags(self, uid):
        u = find(USERS, id=uid)
        u["flags"] = 0
        log(f"Flags cleared for {full_name(u)} by {full_name(self.user)}.")
        self.toast("Flags cleared.")
        self.admin_page(self.akey)

    def add_user_dialog(self):
        def save(v):
            if not v["first"]:
                return "First name is required."
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v["email"]):
                return "Enter a valid email address."
            if find(USERS, email=v["email"].lower()):
                return "That email is already registered."
            if len(v["password"]) < 8:
                return "Password must be at least 8 characters."
            add_user(v["first"], v["last"], v["email"], v["password"], LABEL_ROLE[v["role"]])
            name = f"{v['first']} {v['last']}".strip()
            log(f"{v['role']} account created for {name}.")
            self.toast(f"{name} added.")
            self.admin_page(self.akey)
        form(self, "Add User",
             [("first", "First name", "entry", ""), ("last", "Last name", "entry", ""),
              ("email", "Email", "entry", ""), ("role", "Role", "combo", ["Driver", "Attendant", "Admin"]),
              ("password", "Password", "password", None)], "Add user", save)

    def apage_history(self, pad):
        c = card(pad, 20)
        c.pack(fill="both", expand=True)
        tree = ttk.Treeview(c, columns=("Time", "Event"), show="headings", height=18)
        tree.heading("Time", text="Time")
        tree.heading("Event", text="Event")
        tree.column("Time", width=130, anchor="w", stretch=False)
        tree.column("Event", width=700, anchor="w")
        for h in list(reversed(HISTORY))[:300]:
            tree.insert("", "end", values=(h["ts"], h["event"]))
        tree.pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
