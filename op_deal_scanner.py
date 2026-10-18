"""
Grand Line Deal-Scanner - One-Piece-Oberflaeche (tkinter, in Python enthalten).
Start:  python op_deal_scanner.py
"""

import csv
import math
import os
import queue
import random
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import deal_core as core

C = {
    "night": "#06172e", "sea": "#0d2c52", "sea2": "#174a80", "sea3": "#2a6aa8", "foam": "#a8dcef",
    "panel": "#0c2344", "panel2": "#13335e",
    "parch": "#f7e9c6", "parch2": "#efdcae", "parch3": "#e3c98f", "ink": "#3b2614", "ink2": "#7a5531",
    "red": "#c8102e", "red2": "#e0354b", "gold": "#f2b632", "gold2": "#ffd36b",
    "hot": "#ffd98c", "text": "#f4ecd6", "muted": "#9fb2cf", "hat": "#ecc767", "hatline": "#a87b25",
}


def blend(a, b, t):
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(x + (y - x) * t):02x}" for x, y in zip(a, b))


def eur(v):
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- Bausteine
class FlatButton(tk.Label):
    def __init__(self, master, text, command, bg, fg, hover, font, padx=14, pady=7, **kw):
        super().__init__(master, text=text, bg=bg, fg=fg, font=font, padx=padx, pady=pady,
                         cursor="hand2", **kw)
        self._bg, self._hover, self._cmd = bg, hover, command
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))
        self.bind("<Button-1>", lambda e: self._cmd())


class Chip(tk.Label):
    def __init__(self, master, text, on_toggle, font):
        super().__init__(master, text=text, font=font, padx=11, pady=4, cursor="hand2", bd=0)
        self.active = False
        self._cb = on_toggle
        self.bind("<Button-1>", lambda e: self.toggle())
        self.bind("<Enter>", lambda e: self._paint(True))
        self.bind("<Leave>", lambda e: self._paint(False))
        self._paint(False)

    def toggle(self):
        self.active = not self.active
        self._paint(False)
        self._cb()

    def set(self, v):
        self.active = v
        self._paint(False)

    def _paint(self, hover):
        if self.active:
            self.config(bg=C["gold2"] if hover else C["gold"], fg=C["ink"])
        else:
            self.config(bg=C["sea3"] if hover else C["sea2"], fg=C["foam"])


class FlowFrame(tk.Frame):
    """Ordnet Kinder wie Woerter in Zeilen an und bricht automatisch um."""

    def __init__(self, master, gap=6, **kw):
        super().__init__(master, **kw)
        self.gap = gap
        self.items = []
        self.bind("<Configure>", lambda e: self.relayout())

    def add(self, w):
        self.items.append(w)
        self.after_idle(self.relayout)

    def clear(self):
        for w in self.items:
            w.destroy()
        self.items = []

    def relayout(self):
        width = max(self.winfo_width(), 200)
        x = y = 0
        row_h = 0
        for w in self.items:
            rw, rh = w.winfo_reqwidth(), w.winfo_reqheight()
            if x and x + rw > width:
                x, y = 0, y + row_h + self.gap
                row_h = 0
            w.place(x=x, y=y)
            x += rw + self.gap
            row_h = max(row_h, rh)
        h = y + row_h
        if int(self.cget("height")) != h:
            self.config(height=h)


class Header(tk.Canvas):
    """Nachthimmel, Titel und animierte Wellen mit schaukelndem Strohhut."""

    H = 124

    def __init__(self, master, serif, sans):
        super().__init__(master, height=self.H, highlightthickness=0, bg=C["night"])
        self.serif, self.sans = serif, sans
        self.phase = 0.0
        self.status = "Setze Segel ..."
        self.stars = [(random.random(), random.random() * 0.55, random.choice((1, 1, 2)))
                      for _ in range(70)]
        self.bind("<Configure>", lambda e: self.draw_static())
        self.after(80, self.tick)

    def draw_static(self):
        self.delete("static")
        w, h = self.winfo_width(), self.H
        steps = 30
        for i in range(steps):
            y0 = i * h / steps
            self.create_rectangle(0, y0, w, y0 + h / steps + 1, outline="",
                                  fill=blend(C["night"], C["sea2"], i / (steps - 1)), tags="static")
        for sx, sy, r in self.stars:
            self.create_oval(sx * w, sy * h, sx * w + r, sy * h + r, fill="#dfe9ff", outline="",
                             tags="static")
        # Mond
        self.create_oval(w * 0.62, 14, w * 0.62 + 30, 44, fill="#f8efcf", outline="", tags="static")
        self.create_oval(w * 0.62 + 9, 10, w * 0.62 + 39, 40, fill=blend(C["night"], C["sea2"], 0.15),
                         outline="", tags="static")
        x = 128
        self.create_text(x + 3, 42 + 3, text="GRAND LINE", anchor="w", fill="#020a17",
                         font=(self.serif, 30, "bold"), tags="static")
        self.create_text(x, 42, text="GRAND LINE", anchor="w", fill=C["gold"],
                         font=(self.serif, 30, "bold"), tags="static")
        self.create_text(x + 2, 76, anchor="w", fill=C["foam"], font=(self.sans, 11, "bold"),
                         text="DEAL SCANNER   ·   One-Piece-Schätze unter Marktwert auf Cardmarket",
                         tags="static")
        self.status_id = self.create_text(w - 20, 66, anchor="e", fill=C["text"],
                                          font=(self.sans, 10), text=self.status, tags="static")
        if hasattr(self, "btn_win"):
            self.coords(self.btn_win, w - 18, 20)
        self.tag_raise("wave")
        self.tag_raise("hat")
        self.tag_raise("btn")

    def set_buttons(self, frame):
        self.btn_win = self.create_window(self.winfo_width() - 18, 20, window=frame, anchor="ne",
                                          tags="btn")

    def set_status(self, text):
        self.status = text
        if hasattr(self, "status_id"):
            self.itemconfig(self.status_id, text=text)

    def tick(self):
        self.phase += 0.06
        self.delete("wave", "hat")
        w, h = self.winfo_width(), self.H
        layers = [(h - 30, 5, 0.020, 1.0, C["sea3"]), (h - 20, 4, 0.028, 1.6, C["sea2"]),
                  (h - 10, 3, 0.035, 2.3, C["night"])]
        # Strohhut zwischen den Wellen, schaukelt mit
        hx = 64
        hy = h - 46 + math.sin(self.phase * 1.3) * 3
        tilt = math.sin(self.phase * 1.3 + 0.8) * 4
        for i, (base, amp, freq, speed, col) in enumerate(layers):
            pts = [0, h]
            for x in range(0, w + 12, 12):
                pts += [x, base + amp * math.sin(x * freq + self.phase * speed)]
            pts += [w, h]
            self.create_polygon(pts, fill=col, outline="", tags="wave")
            if i == 0:
                self._hat(hx, hy, tilt)
        self.tag_raise("btn")
        self.after(70, self.tick)

    def _hat(self, x, y, tilt):
        t = tilt
        self.create_oval(x - 46, y + 2 + t * 0.3, x + 46, y + 20 - t * 0.3, fill=C["hat"],
                         outline=C["hatline"], width=2, tags="hat")
        self.create_arc(x - 26, y - 24, x + 26, y + 26, start=0, extent=180, style="chord",
                        fill=C["hat"], outline=C["hatline"], width=2, tags="hat")
        self.create_rectangle(x - 25, y - 6, x + 25, y + 1, fill=C["red"], outline="", tags="hat")
        for dx in (-30, -10, 12, 32):
            self.create_line(x + dx, y + 8, x + dx + 6, y + 13, fill=C["hatline"], tags="hat")


# ---------------------------------------------------------------- App
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Grand Line Deal-Scanner · One Piece")
        self.geometry("1440x860")
        self.minsize(1180, 700)
        self.configure(bg=C["night"])
        fams = set(tkfont.families())
        self.serif = next((f for f in ("Georgia", "Palatino Linotype", "Book Antiqua", "DejaVu Serif",
                                       "Times New Roman") if f in fams), "Times")
        self.sans = next((f for f in ("Segoe UI", "Bahnschrift", "DejaVu Sans", "Arial") if f in fams),
                         "Helvetica")
        self.settings = core.load_settings()
        self.data = None
        self.rows, self.shown = [], []
        self.created = "?"
        self._pending = None
        self._style()
        self._build()
        self._restore_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(250, lambda: self.load(False))

    # ------------------------------------------------------------ Stil
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        f = (self.sans, 10)
        s.configure(".", font=f, background=C["panel"], foreground=C["text"])
        s.configure("TEntry", fieldbackground=C["parch"], foreground=C["ink"], insertcolor=C["ink"],
                    bordercolor=C["ink2"], lightcolor=C["parch"], darkcolor=C["parch"], padding=5)
        s.configure("TCombobox", fieldbackground=C["parch"], background=C["parch2"], foreground=C["ink"],
                    arrowcolor=C["ink"], bordercolor=C["ink2"], lightcolor=C["parch"],
                    darkcolor=C["parch"], padding=4)
        s.map("TCombobox", fieldbackground=[("readonly", C["parch"])],
              foreground=[("readonly", C["ink"])], selectbackground=[("readonly", C["parch"])],
              selectforeground=[("readonly", C["ink"])])
        self.option_add("*TCombobox*Listbox.background", C["parch"])
        self.option_add("*TCombobox*Listbox.foreground", C["ink"])
        self.option_add("*TCombobox*Listbox.selectBackground", C["red"])
        self.option_add("*TCombobox*Listbox.selectForeground", "white")
        self.option_add("*TCombobox*Listbox.font", f)
        s.configure("Treeview", background=C["parch"], fieldbackground=C["parch"], foreground=C["ink"],
                    rowheight=29, borderwidth=0, font=f)
        s.map("Treeview", background=[("selected", C["red"])], foreground=[("selected", "white")])
        s.configure("Treeview.Heading", background=C["sea"], foreground=C["gold"], relief="flat",
                    font=(self.serif, 10, "bold"), padding=(8, 7), bordercolor=C["night"])
        s.map("Treeview.Heading", background=[("active", C["sea2"])])
        s.configure("Vertical.TScrollbar", troughcolor=C["panel"], background=C["sea2"],
                    arrowcolor=C["gold"], bordercolor=C["panel"], lightcolor=C["sea2"],
                    darkcolor=C["sea2"])
        s.configure("Horizontal.TScale", background=C["gold"], troughcolor=C["sea"],
                    bordercolor=C["panel"], lightcolor=C["gold"], darkcolor=C["gold"])

    # ------------------------------------------------------------ Aufbau
    def _build(self):
        self.v = {
            "search": tk.StringVar(), "kind": tk.StringVar(value="Alles"),
            "foil": tk.StringVar(value="Normal + Foil"),
            "min_price": tk.StringVar(value="0"), "max_price": tk.StringVar(value="500"),
            "min_market": tk.StringVar(value="5"), "min_discount": tk.StringVar(value="30"),
            "min_savings": tk.StringVar(value="3"), "sort": tk.StringVar(value="Ersparnis (EUR)"),
            "lang": tk.StringVar(value="Englisch"), "cond": tk.StringVar(value="Near Mint"),
            "country": tk.StringVar(value="Deutschland"),
        }

        # Kopfzeile
        self.header = Header(self, self.serif, self.sans)
        self.header.pack(fill="x")
        bf = tk.Frame(self.header, bg=C["night"])
        bfont = (self.sans, 10, "bold")
        FlatButton(bf, "☸  Neu laden", lambda: self.load(True), C["gold"], C["ink"], C["gold2"],
                   bfont).pack(side="left", padx=4)
        FlatButton(bf, "Als CSV speichern", self.export, C["sea2"], C["text"], C["sea3"],
                   bfont).pack(side="left", padx=4)
        FlatButton(bf, "Kategorien & Länder bearbeiten", self.edit_settings, C["sea2"], C["text"],
                   C["sea3"], bfont).pack(side="left", padx=4)
        self.header.set_buttons(bf)

        body = tk.Frame(self, bg=C["night"])
        body.pack(fill="both", expand=True, padx=16, pady=(4, 6))
        self._build_filters(body)
        self._build_poster(body)
        self._build_table(body)

        self.foot = tk.Label(self, bg=C["night"], fg=C["muted"], anchor="w", font=(self.sans, 9),
                             text="Doppelklick oder Enter öffnet die Live-Angebote auf Cardmarket mit "
                                  "deinem Land-, Sprach- und Zustandsfilter.   Gold = mindestens 50 % "
                                  "unter Marktwert.")
        self.foot.pack(fill="x", padx=18, pady=(0, 8))

        for k in ("search", "kind", "foil", "min_price", "max_price", "min_market",
                  "min_discount", "min_savings", "sort"):
            self.v[k].trace_add("write", lambda *_: self.schedule_apply())

    def _section(self, parent, text, bg):
        tk.Label(parent, text=text, bg=bg, fg=C["gold"], font=(self.serif, 13, "bold"),
                 anchor="w").pack(fill="x", pady=(2, 4))
        tk.Frame(parent, bg=C["gold"], height=2).pack(fill="x", pady=(0, 6))

    def _label(self, parent, text, bg, fg=None):
        tk.Label(parent, text=text, bg=bg, fg=fg or C["muted"], font=(self.sans, 9, "bold"),
                 anchor="w").pack(fill="x", pady=(7, 2))

    def _build_filters(self, body):
        f = tk.Frame(body, bg=C["panel"], padx=14, pady=12, width=262)
        f.pack(side="left", fill="y")
        f.pack_propagate(False)
        self._section(f, "⚓  Kurs setzen", C["panel"])
        bg = C["panel"]
        self._label(f, "SUCHE  (Name, Kartencode, Set)", bg)
        ttk.Entry(f, textvariable=self.v["search"]).pack(fill="x")
        self._label(f, "ART", bg)
        ttk.Combobox(f, textvariable=self.v["kind"], state="readonly",
                     values=["Alles", "Einzelkarten", "Sealed (Booster, Displays)"]).pack(fill="x")
        self._label(f, "FOIL", bg)
        ttk.Combobox(f, textvariable=self.v["foil"], state="readonly",
                     values=["Normal + Foil", "Nur normal", "Nur Foil"]).pack(fill="x")
        self._label(f, "PREIS VON / BIS (€)", bg)
        pr = tk.Frame(f, bg=bg)
        pr.pack(fill="x")
        ttk.Entry(pr, textvariable=self.v["min_price"], width=9).pack(side="left", fill="x", expand=True)
        tk.Label(pr, text="–", bg=bg, fg=C["text"]).pack(side="left", padx=6)
        ttk.Entry(pr, textvariable=self.v["max_price"], width=9).pack(side="left", fill="x", expand=True)
        self._label(f, "MINDEST-MARKTWERT (€)", bg)
        ttk.Entry(f, textvariable=self.v["min_market"]).pack(fill="x")

        row = tk.Frame(f, bg=bg)
        row.pack(fill="x", pady=(7, 2))
        tk.Label(row, text="MINDEST-RABATT", bg=bg, fg=C["muted"], font=(self.sans, 9, "bold")).pack(side="left")
        self.disc_lbl = tk.Label(row, text="30 %", bg=bg, fg=C["gold"], font=(self.serif, 11, "bold"))
        self.disc_lbl.pack(side="right")
        self.scale = ttk.Scale(f, from_=0, to=90, orient="horizontal", command=self._on_scale)
        self.scale.set(30)
        self.scale.pack(fill="x")

        self._label(f, "MINDEST-ERSPARNIS (€)", bg)
        ttk.Entry(f, textvariable=self.v["min_savings"]).pack(fill="x")
        self._label(f, "SORTIEREN NACH", bg)
        ttk.Combobox(f, textvariable=self.v["sort"], state="readonly",
                     values=["Ersparnis (EUR)", "Rabatt (%)", "Preis aufsteigend", "Marktwert",
                             "Name"]).pack(fill="x")
        FlatButton(f, "Filter zurücksetzen", self.reset_filters, C["panel2"], C["foam"], C["sea2"],
                   (self.sans, 9, "bold"), pady=6).pack(fill="x", pady=(16, 0))

    def _build_table(self, body):
        mid = tk.Frame(body, bg=C["night"])
        mid.pack(side="left", fill="both", expand=True, padx=12)

        top = tk.Frame(mid, bg=C["night"])
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text="KATEGORIEN", bg=C["night"], fg=C["gold"], font=(self.serif, 10, "bold")
                 ).pack(anchor="w", pady=(0, 4))
        self.chips = FlowFrame(top, bg=C["night"], height=30)
        self.chips.pack(fill="x")
        self._build_chips()

        wrap = tk.Frame(mid, bg=C["ink2"], padx=2, pady=2)
        wrap.pack(fill="both", expand=True)
        cols = ("name", "cats", "foil", "low", "market", "avg30", "discount", "savings")
        heads = ("Karte / Produkt", "Kategorie", "Foil", "Ab", "Marktwert", "Ø 30 T.", "Rabatt", "Ersparnis")
        widths = (245, 115, 48, 76, 84, 72, 64, 84)
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        for c, h, w in zip(cols, heads, widths):
            self.tree.heading(c, text=h, command=lambda c=c: self._sort_by(c))
            self.tree.column(c, width=w, minwidth=40, stretch=c in ("name", "cats"),
                             anchor="w" if c in ("name", "cats") else ("center" if c == "foil" else "e"))
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.tag_configure("odd", background=C["parch2"])
        self.tree.tag_configure("hot", background=C["hot"], foreground="#7a0f12",
                                font=(self.sans, 10, "bold"))
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.tree.bind("<Return>", lambda e: self.open_selected())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_detail())

    def _build_chips(self):
        self.chips.clear()
        self.chip_map = {}
        cf = (self.sans, 9, "bold")
        self.chip_all = Chip(self.chips, "★ Alle", self._chip_all, cf)
        self.chip_all.set(True)
        self.chips.add(self.chip_all)
        for name in self.settings["kategorien"]:
            ch = Chip(self.chips, name, self._chip_changed, cf)
            self.chip_map[name] = ch
            self.chips.add(ch)

    def _build_poster(self, body):
        outer = tk.Frame(body, bg=C["ink"], padx=3, pady=3, width=300)
        outer.pack(side="right", fill="y")
        outer.pack_propagate(False)
        p = tk.Frame(outer, bg=C["parch"], padx=16, pady=10)
        p.pack(fill="both", expand=True)
        pb = C["parch"]
        tk.Label(p, text="WANTED", bg=pb, fg=C["ink"], font=(self.serif, 30, "bold")).pack()
        tk.Frame(p, bg=C["ink"], height=2).pack(fill="x", pady=(0, 8))

        # "Steckbrief-Bild": Kartencode gross, darunter Kategorien
        self.pic = tk.Canvas(p, height=118, bg=C["parch3"], highlightthickness=2,
                             highlightbackground=C["ink2"])
        self.pic.pack(fill="x")
        self.d_name = tk.Label(p, text="Wähle eine Karte\naus der Liste", bg=pb, fg=C["ink"],
                               font=(self.serif, 13, "bold"), wraplength=250, justify="center")
        self.d_name.pack(pady=(8, 2))
        tk.Label(p, text="– DEAL OR ALIVE –", bg=pb, fg=C["ink2"], font=(self.serif, 9, "italic")).pack()
        self.d_price = tk.Label(p, text="", bg=pb, fg=C["red"], font=(self.serif, 26, "bold"))
        self.d_price.pack(pady=(2, 0))

        grid = tk.Frame(p, bg=pb)
        grid.pack(fill="x", pady=(4, 6))
        self.d_vals = {}
        for i, k in enumerate(("Marktwert", "Ø 30 Tage", "Ersparnis", "Rabatt")):
            tk.Label(grid, text=k, bg=pb, fg=C["ink2"], font=(self.sans, 9)).grid(row=i, column=0, sticky="w")
            lab = tk.Label(grid, text="–", bg=pb, fg=C["ink"], font=(self.sans, 10, "bold"))
            lab.grid(row=i, column=1, sticky="e")
            self.d_vals[k] = lab
        grid.columnconfigure(1, weight=1)

        tk.Frame(p, bg=C["ink2"], height=1).pack(fill="x", pady=(2, 6))
        tk.Label(p, text="ANGEBOTE ÖFFNEN MIT", bg=pb, fg=C["ink"], font=(self.serif, 10, "bold")).pack(anchor="w")
        for key, lab, vals in (("country", "Land des Verkäufers", list(self.settings["laender"])),
                               ("lang", "Sprache der Karte", list(core.LANGUAGES)),
                               ("cond", "Mindestzustand", list(core.CONDITIONS))):
            tk.Label(p, text=lab, bg=pb, fg=C["ink2"], font=(self.sans, 9)).pack(anchor="w", pady=(4, 1))
            cb = ttk.Combobox(p, textvariable=self.v[key], state="readonly", values=vals)
            cb.pack(fill="x")
            if key == "country":
                self.country_cb = cb
        FlatButton(p, "⚔  LIVE-ANGEBOTE ÖFFNEN", self.open_selected, C["red"], "white", C["red2"],
                   (self.sans, 10, "bold"), pady=9).pack(fill="x", side="bottom", pady=(8, 0))
        self._draw_pic(None)

    def _draw_pic(self, r):
        c = self.pic
        c.delete("all")
        c.update_idletasks()
        w = max(c.winfo_width(), 260)
        h = 118
        # Holzmaserung
        for i in range(0, h, 7):
            c.create_line(0, i, w, i + 3, fill=blend(C["parch3"], C["parch2"], (i % 21) / 21))
        if not r:
            c.create_text(w / 2, h / 2 - 8, text="☠", fill=C["ink2"], font=(self.serif, 40))
            c.create_text(w / 2, h - 18, text="Noch kein Ziel im Visier", fill=C["ink2"],
                          font=(self.sans, 9, "italic"))
            return
        c.create_text(w / 2, 40, text=r["code"] or ("SEALED" if not r["single"] else "★"),
                      fill=C["ink"], font=(self.serif, 26, "bold"))
        tags = r["cats"][:3] + (["Foil"] if r["foil"] else [])
        x = 10
        for t in tags:
            tw = tkfont.Font(family=self.sans, size=8, weight="bold").measure(t) + 14
            c.create_rectangle(x, h - 34, x + tw, h - 14, fill=C["ink"], outline="")
            c.create_text(x + tw / 2, h - 24, text=t, fill=C["gold2"], font=(self.sans, 8, "bold"))
            x += tw + 6

    # ------------------------------------------------------------ Filter-Logik
    def _on_scale(self, x):
        v = str(int(float(x)))
        self.disc_lbl.config(text=f"{v} %")
        if self.v["min_discount"].get() != v:
            self.v["min_discount"].set(v)

    def _chip_all(self):
        for ch in self.chip_map.values():
            ch.set(False)
        self.chip_all.set(True)
        self.schedule_apply()

    def _chip_changed(self):
        self.chip_all.set(not any(ch.active for ch in self.chip_map.values()))
        self.schedule_apply()

    def reset_filters(self):
        for k, val in (("search", ""), ("kind", "Alles"), ("foil", "Normal + Foil"), ("min_price", "0"),
                       ("max_price", "500"), ("min_market", "5"), ("min_savings", "3"),
                       ("sort", "Ersparnis (EUR)")):
            self.v[k].set(val)
        self.scale.set(30)
        self._chip_all()

    def _sort_by(self, col):
        m = {"name": "Name", "low": "Preis aufsteigend", "market": "Marktwert",
             "discount": "Rabatt (%)", "savings": "Ersparnis (EUR)"}
        if col in m:
            self.v["sort"].set(m[col])

    def num(self, key, default):
        try:
            return float(self.v[key].get().replace(",", "."))
        except ValueError:
            return default

    def schedule_apply(self):
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(140, self.apply)

    def apply(self):
        self._pending = None
        if not self.rows:
            return
        filt = {"search": self.v["search"].get(), "kind": self.v["kind"].get(), "foil": self.v["foil"].get(),
                "min_price": self.num("min_price", 0), "max_price": self.num("max_price", 1e9),
                "min_market": self.num("min_market", 0), "min_discount": self.num("min_discount", 0),
                "min_savings": self.num("min_savings", 0), "sort": self.v["sort"].get(),
                "cats": [n for n, ch in self.chip_map.items() if ch.active]}
        allhits = core.filter_rows(self.rows, filt)
        self.shown = allhits[:2000]
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.shown):
            tag = "hot" if r["discount"] >= 50 else ("odd" if i % 2 else "")
            cats = ", ".join(r["cats"][:2]) or ("Sealed" if not r["single"] else "")
            self.tree.insert("", "end", iid=str(i), tags=(tag,), values=(
                r["name"], cats, "✦" if r["foil"] else "", eur(r["low"]), eur(r["market"]),
                eur(r["avg30"]) if r["avg30"] else "–", f"−{r['discount']:.0f} %", eur(r["savings"])))
        more = f" (zeige die besten 2000)" if len(allhits) > 2000 else ""
        self.header.set_status(f"☠ {len(allhits)} Schätze gefunden{more}   ·   Preisstand {self.created}")
        if self.shown:
            self.tree.selection_set("0")
        else:
            self._draw_pic(None)

    def show_detail(self):
        sel = self.tree.selection()
        if not sel:
            return
        r = self.shown[int(sel[0])]
        self.d_name.config(text=r["name"])
        self.d_price.config(text=eur(r["low"]))
        self.d_vals["Marktwert"].config(text=eur(r["market"]))
        self.d_vals["Ø 30 Tage"].config(text=eur(r["avg30"]) if r["avg30"] else "–")
        self.d_vals["Ersparnis"].config(text=eur(r["savings"]), fg="#1e7a3c")
        self.d_vals["Rabatt"].config(text=f"−{r['discount']:.0f} %", fg=C["red"])
        self._draw_pic(r)

    # ------------------------------------------------------------ Aktionen
    def load(self, force):
        self.header.set_status("Setze Segel ... lade Daten von Cardmarket")
        self.settings = core.load_settings()
        self._refresh_settings_widgets()
        q = queue.Queue()
        cats = self.settings["kategorien"]

        def work():
            try:
                data = core.load_data(force, progress=lambda t: q.put(("status", t)))
                q.put(("done", core.build_rows(data, cats), data.get("createdAt", "?")))
            except Exception as e:
                q.put(("error", str(e)))
        threading.Thread(target=work, daemon=True).start()
        self.after(100, self._poll, q)

    def _poll(self, q):
        while True:
            try:
                msg = q.get_nowait()
            except queue.Empty:
                break
            if msg[0] == "status":
                self.header.set_status(msg[1])
            elif msg[0] == "done":
                self._loaded(msg[1], msg[2])
                return
            else:
                self.header.set_status("Sturm auf See: Laden fehlgeschlagen")
                messagebox.showerror("Fehler", f"Daten konnten nicht geladen werden:\n{msg[1]}")
                return
        self.after(100, self._poll, q)

    def _refresh_settings_widgets(self):
        if set(self.chip_map) != set(self.settings["kategorien"]):
            active = {n for n, ch in self.chip_map.items() if ch.active}
            self._build_chips()
            for n in active & set(self.chip_map):
                self.chip_map[n].set(True)
            self.chip_all.set(not active & set(self.chip_map))
        self.country_cb.config(values=list(self.settings["laender"]))
        if self.v["country"].get() not in self.settings["laender"]:
            self.v["country"].set("Alle")

    def _loaded(self, rows, created):
        self.rows = rows
        self.created = created
        self.apply()

    def open_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        r = self.shown[int(sel[0])]
        webbrowser.open(core.offer_url(r, core.LANGUAGES.get(self.v["lang"].get()),
                                       core.CONDITIONS.get(self.v["cond"].get()),
                                       self.settings["laender"].get(self.v["country"].get())))

    def edit_settings(self):
        path = core.settings_path()
        if not os.path.exists(path):
            core.save_settings(self.settings)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass
        messagebox.showinfo("Kategorien & Länder",
                            "Die Einstellungsdatei ist geöffnet:\n" + path +
                            "\n\nDort kannst du Kategorien (Suchwörter) und Länder ändern. "
                            "Danach speichern und hier auf „Neu laden“ klicken.")

    def export(self):
        if not self.shown:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                         initialfile="one_piece_deals.csv")
        if not p:
            return
        lang = core.LANGUAGES.get(self.v["lang"].get())
        cond = core.CONDITIONS.get(self.v["cond"].get())
        land = self.settings["laender"].get(self.v["country"].get())
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Name", "Kategorien", "Foil", "Ab", "Marktwert", "Avg30", "Rabatt %", "Ersparnis", "Link"])
            for r in self.shown:
                w.writerow([r["name"], ", ".join(r["cats"]), "ja" if r["foil"] else "", r["low"], r["market"],
                            r["avg30"], r["discount"], r["savings"], core.offer_url(r, lang, cond, land)])
        messagebox.showinfo("Export", f"{len(self.shown)} Zeilen gespeichert.")

    # ------------------------------------------------------------ Merken
    UI_KEYS = ("kind", "foil", "min_price", "max_price", "min_market", "min_discount", "min_savings",
               "sort", "lang", "cond", "country")

    def _restore_ui(self):
        ui = self.settings.get("ui", {})
        for k in self.UI_KEYS:
            if k in ui:
                self.v[k].set(ui[k])
        try:
            self.scale.set(float(self.v["min_discount"].get()))
        except ValueError:
            pass
        for n in ui.get("cats", []):
            if n in self.chip_map:
                self.chip_map[n].set(True)
        self.chip_all.set(not any(ch.active for ch in self.chip_map.values()))

    def _on_close(self):
        ui = {k: self.v[k].get() for k in self.UI_KEYS}
        ui["cats"] = [n for n, ch in self.chip_map.items() if ch.active]
        self.settings["ui"] = ui
        core.save_settings(self.settings)
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
