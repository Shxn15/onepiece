"""
One Piece Deal-Scanner - Oberflaeche (tkinter, in Python enthalten).
Start:  python op_deal_scanner.py
"""

import csv
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

import deal_core as core

BG, PANEL, ACCENT, GOOD, TEXT = "#14213d", "#1d2d50", "#fca311", "#43aa8b", "#f1f1f1"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("One Piece Deal-Scanner")
        self.geometry("1180x720")
        self.minsize(900, 560)
        self.configure(bg=BG)
        self.rows, self.shown = [], []
        self._style()
        self._build()
        self.after(200, lambda: self.load(False))

    # ------------------------------------------------------------------ UI
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=PANEL, foreground=TEXT, fieldbackground="#24375f", font=("Segoe UI", 10))
        s.configure("TLabel", background=PANEL, foreground=TEXT)
        s.configure("Head.TLabel", background=BG, foreground=ACCENT, font=("Segoe UI", 18, "bold"))
        s.configure("Sub.TLabel", background=BG, foreground="#b8c1d9")
        s.configure("TButton", background=ACCENT, foreground="#111", padding=6, borderwidth=0)
        s.map("TButton", background=[("active", "#ffbd45")])
        s.configure("Treeview", background="#f7f7fb", foreground="#111", rowheight=26, fieldbackground="#f7f7fb")
        s.configure("Treeview.Heading", background=BG, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        s.configure("TCombobox", foreground="#111")
        s.configure("TCheckbutton", background=PANEL, foreground=TEXT)

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(12, 4))
        ttk.Label(top, text="⚓ One Piece Deal-Scanner", style="Head.TLabel").pack(side="left")
        self.status = ttk.Label(top, text="", style="Sub.TLabel")
        self.status.pack(side="right")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=8)

        # ---- Filterleiste
        f = tk.Frame(body, bg=PANEL, padx=12, pady=12)
        f.pack(side="left", fill="y")
        self.v = {
            "search": tk.StringVar(), "kind": tk.StringVar(value="Alles"),
            "foil": tk.StringVar(value="Normal + Foil"),
            "min_price": tk.StringVar(value="0"), "max_price": tk.StringVar(value="500"),
            "min_market": tk.StringVar(value="5"), "min_discount": tk.StringVar(value="30"),
            "min_savings": tk.StringVar(value="3"), "sort": tk.StringVar(value="Ersparnis (EUR)"),
            "lang": tk.StringVar(value="Englisch"), "cond": tk.StringVar(value="Near Mint"),
        }

        def lbl(t):
            ttk.Label(f, text=t).pack(anchor="w", pady=(8, 2))

        lbl("Suche (Name, Kartencode, Set)")
        e = ttk.Entry(f, textvariable=self.v["search"], width=28)
        e.pack(fill="x")
        lbl("Art")
        ttk.Combobox(f, textvariable=self.v["kind"], state="readonly",
                     values=["Alles", "Einzelkarten", "Sealed (Booster, Displays)"]).pack(fill="x")
        lbl("Foil")
        ttk.Combobox(f, textvariable=self.v["foil"], state="readonly",
                     values=["Normal + Foil", "Nur normal", "Nur Foil"]).pack(fill="x")

        lbl("Preis von / bis (EUR)")
        pr = tk.Frame(f, bg=PANEL)
        pr.pack(fill="x")
        ttk.Entry(pr, textvariable=self.v["min_price"], width=8).pack(side="left")
        ttk.Label(pr, text=" – ").pack(side="left")
        ttk.Entry(pr, textvariable=self.v["max_price"], width=8).pack(side="left")

        lbl("Mindest-Marktwert (EUR)")
        ttk.Entry(f, textvariable=self.v["min_market"]).pack(fill="x")
        lbl("Mindest-Rabatt (%)")
        ttk.Scale(f, from_=0, to=90, orient="horizontal",
                  command=lambda x: (self.v["min_discount"].set(str(int(float(x)))), self.apply())
                  ).pack(fill="x")
        ttk.Entry(f, textvariable=self.v["min_discount"]).pack(fill="x")
        lbl("Mindest-Ersparnis (EUR)")
        ttk.Entry(f, textvariable=self.v["min_savings"]).pack(fill="x")
        lbl("Sortieren nach")
        ttk.Combobox(f, textvariable=self.v["sort"], state="readonly",
                     values=["Ersparnis (EUR)", "Rabatt (%)", "Preis aufsteigend", "Marktwert", "Name"]).pack(fill="x")

        ttk.Separator(f).pack(fill="x", pady=12)
        ttk.Label(f, text="Live-Angebote öffnen mit:").pack(anchor="w")
        lbl("Sprache")
        ttk.Combobox(f, textvariable=self.v["lang"], state="readonly", values=list(core.LANGUAGES)).pack(fill="x")
        lbl("Mindestzustand")
        ttk.Combobox(f, textvariable=self.v["cond"], state="readonly", values=list(core.CONDITIONS)).pack(fill="x")

        btns = tk.Frame(f, bg=PANEL)
        btns.pack(fill="x", pady=(14, 0))
        ttk.Button(btns, text="🔄 Neu laden", command=lambda: self.load(True)).pack(fill="x", pady=2)
        ttk.Button(btns, text="💾 Als CSV exportieren", command=self.export).pack(fill="x", pady=2)

        for k in ("search", "kind", "foil", "min_price", "max_price", "min_market",
                  "min_discount", "min_savings", "sort"):
            self.v[k].trace_add("write", lambda *_: self.apply())

        # ---- Tabelle
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))
        cols = ("name", "foil", "low", "market", "avg30", "discount", "savings")
        heads = ("Karte / Produkt", "Foil", "Ab (EUR)", "Marktwert", "Ø 30 Tage", "Rabatt", "Ersparnis")
        widths = (420, 50, 90, 95, 95, 80, 95)
        self.tree = ttk.Treeview(right, columns=cols, show="headings", selectmode="browse")
        for c, h, w in zip(cols, heads, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w" if c == "name" else "e")
        sb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        self.tree.tag_configure("hot", background="#d8f3e6")
        self.tree.tag_configure("odd", background="#eef0f7")
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.tree.bind("<Return>", lambda e: self.open_selected())

        tip = tk.Label(self, bg=BG, fg="#b8c1d9", anchor="w",
                       text="Doppelklick auf eine Zeile öffnet die aktuellen Angebote auf Cardmarket "
                            "(mit deinem Sprach- und Zustandsfilter). Grün = mindestens 50 % unter Marktwert.")
        tip.pack(fill="x", padx=16, pady=(0, 10))

    # ------------------------------------------------------------- Logik
    def num(self, key, default):
        try:
            return float(self.v[key].get().replace(",", "."))
        except ValueError:
            return default

    def load(self, force):
        self.status.config(text="Lade Daten von Cardmarket ...")

        def work():
            try:
                data = core.load_data(force, progress=lambda t: self.after(0, self.status.config, {"text": t}))
                rows = core.build_rows(data)
                self.after(0, self._loaded, rows, data["createdAt"])
            except Exception as e:
                self.after(0, lambda: (self.status.config(text="Fehler beim Laden"),
                                       messagebox.showerror("Fehler", f"Daten konnten nicht geladen werden:\n{e}")))
        threading.Thread(target=work, daemon=True).start()

    def _loaded(self, rows, created):
        self.rows = rows
        self.created = created
        self.apply()

    def apply(self):
        if not self.rows:
            return
        filt = {"search": self.v["search"].get(), "kind": self.v["kind"].get(), "foil": self.v["foil"].get(),
                "min_price": self.num("min_price", 0), "max_price": self.num("max_price", 1e9),
                "min_market": self.num("min_market", 0), "min_discount": self.num("min_discount", 0),
                "min_savings": self.num("min_savings", 0), "sort": self.v["sort"].get()}
        self.shown = core.filter_rows(self.rows, filt)[:2000]
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.shown):
            tag = "hot" if r["discount"] >= 50 else ("odd" if i % 2 else "")
            self.tree.insert("", "end", iid=str(i), tags=(tag,), values=(
                r["name"], "✦" if r["foil"] else "", f"{r['low']:.2f}", f"{r['market']:.2f}",
                f"{r['avg30']:.2f}" if r["avg30"] else "–", f"-{r['discount']:.0f} %", f"{r['savings']:.2f}"))
        self.status.config(text=f"{len(self.shown)} Treffer · Preisstand {self.created}")

    def open_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        r = self.shown[int(sel[0])]
        webbrowser.open(core.offer_url(r, core.LANGUAGES[self.v["lang"].get()],
                                       core.CONDITIONS[self.v["cond"].get()]))

    def export(self):
        if not self.shown:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                         initialfile="one_piece_deals.csv")
        if not p:
            return
        with open(p, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Name", "Foil", "Ab", "Marktwert", "Avg30", "Rabatt %", "Ersparnis", "Link"])
            for r in self.shown:
                w.writerow([r["name"], "ja" if r["foil"] else "", r["low"], r["market"], r["avg30"],
                            r["discount"], r["savings"], core.offer_url(r)])
        messagebox.showinfo("Export", f"{len(self.shown)} Zeilen gespeichert.")


if __name__ == "__main__":
    App().mainloop()
