"""
Kernlogik des One Piece Deal-Scanners: Daten laden, cachen, kategorisieren, filtern.
Getrennt von der Oberflaeche, damit sie testbar bleibt.
"""

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime

BASE = "https://downloads.s3.cardmarket.com/productCatalog"
UA = "Mozilla/5.0 (op-deal-scanner; private use)"

# Cardmarket-Sprach-IDs fuer den Link-Filter
LANGUAGES = {"Alle": None, "Englisch": 1, "Franzoesisch": 2, "Deutsch": 3,
             "Italienisch": 5, "Japanisch": 7}
# Cardmarket-Zustands-IDs (1 = Mint ... 7 = Poor)
CONDITIONS = {"Egal": None, "Mint": 1, "Near Mint": 2, "Excellent": 3,
              "Good": 4, "Light Played": 5, "Played": 6}

# Standardwerte fuer die Einstellungsdatei. Alles hier kann der Nutzer in
# %APPDATA%\OPDealScanner\einstellungen.json aendern.
DEFAULT_SETTINGS = {
    # Cardmarket-Laender-IDs fuer den Verkaeufer-Filter (sellerCountry)
    "laender": {
        "Alle": None, "Deutschland": 7, "Oesterreich": 1, "Schweiz": 4,
        "Belgien": 2, "Daenemark": 8, "Finnland": 11, "Frankreich": 12,
        "Griechenland": 14, "Irland": 16, "Italien": 17, "Luxemburg": 20,
        "Niederlande": 23, "Norwegen": 24, "Polen": 25, "Portugal": 26,
        "Schweden": 28, "Spanien": 10, "Tschechien": 6, "Ungarn": 15,
        "Vereinigtes Koenigreich": 13, "Japan": 35,
    },
    # Kategorien: Name -> Liste von Suchmustern (regulaere Ausdruecke,
    # Gross-/Kleinschreibung egal). Eine Karte gehoert zur Kategorie, wenn
    # eines der Muster im Produktnamen vorkommt.
    "kategorien": {
        "Leader": [r"\bleader\b"],
        "DON!!-Karten": [r"\bdon!!", r"\bdon card\b"],
        "Alt Art / Parallel": [r"alternate art", r"\balt\.? ?art\b", r"parallel", r"\(v\.\s?[2-9]\)"],
        "Manga Art": [r"\bmanga\b"],
        "SP-Karten": [r"\bsp\b", r"special card"],
        "Treasure Rare": [r"treasure rare", r"\btr\b"],
        "Promos": [r"\bp-\d{3}\b", r"\bpromo"],
        "Booster Display": [r"\bdisplay\b", r"booster box"],
        "Booster": [r"\bbooster\b(?!\s*(box|display))"],
        "Decks": [r"starter deck", r"\bdeck\b(?!\s*box)"],
        "Zubehoer": [r"playmat", r"sleeve", r"deck ?box", r"binder", r"case"],
    },
    "ui": {},
}


def app_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "OPDealScanner")
    os.makedirs(d, exist_ok=True)
    return d


cache_dir = app_dir  # alter Name, bleibt kompatibel


def settings_path():
    return os.path.join(app_dir(), "einstellungen.json")


def load_settings():
    """Liest die Einstellungen. Fehlt die Datei, wird sie mit Standardwerten
    angelegt, damit der Nutzer sie im Editor anpassen kann."""
    s = json.loads(json.dumps(DEFAULT_SETTINGS))
    p = settings_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                user = json.load(f)
            for k in s:
                if isinstance(user.get(k), dict):
                    s[k] = user[k]
        except Exception:
            pass
    else:
        save_settings(s)
    return s


def save_settings(s):
    try:
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def compile_categories(cats):
    out = {}
    for name, pats in cats.items():
        rx = []
        for p in pats if isinstance(pats, list) else [pats]:
            try:
                rx.append(re.compile(p, re.I))
            except re.error:
                rx.append(re.compile(re.escape(p), re.I))
        out[name] = rx
    return out


def categorize(name, compiled):
    return [c for c, rxs in compiled.items() if any(r.search(name) for r in rxs)]


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def detect_game_id(progress=None):
    for gid in range(1, 40):
        if progress:
            progress(f"Suche One-Piece-Katalog ({gid}/39) ...")
        try:
            data = fetch_json(f"{BASE}/productList/products_singles_{gid}.json")
            prods = data.get("products", [])
            if prods and "one piece" in prods[0].get("categoryName", "").lower():
                return gid
        except Exception:
            continue
    raise RuntimeError("One-Piece-Katalog bei Cardmarket nicht gefunden.")


def load_data(force=False, progress=None):
    """Laedt Preisliste + Katalog. Nutzt einen Tages-Cache, damit Cardmarket
    nicht bei jedem Klick erneut abgefragt wird."""
    cpath = os.path.join(app_dir(), "cache.json")
    today = datetime.now().strftime("%Y-%m-%d")
    cached = None
    if os.path.exists(cpath):
        try:
            with open(cpath, encoding="utf-8") as f:
                cached = json.load(f)
        except Exception:
            cached = None
    if cached and cached.get("day") == today and not force:
        return cached

    gid = (cached or {}).get("game_id") or detect_game_id(progress)
    if progress:
        progress("Lade Preisliste ...")
    prices = fetch_json(f"{BASE}/priceGuide/price_guide_{gid}.json")
    products = {}
    for kind in ("singles", "nonsingles"):
        if progress:
            progress(f"Lade Katalog ({kind}) ...")
        try:
            for p in fetch_json(f"{BASE}/productList/products_{kind}_{gid}.json").get("products", []):
                p["_single"] = kind == "singles"
                products[str(p["idProduct"])] = p
        except Exception:
            pass
    data = {"day": today, "game_id": gid, "createdAt": prices.get("createdAt", "?"),
            "priceGuides": prices.get("priceGuides", []), "products": products}
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


CODE_RX = re.compile(r"\b([A-Z]{1,4}\d{0,2}-\d{3})\b")


def build_rows(data, categories=None):
    """Eine Zeile pro Produkt und Variante (normal / Foil)."""
    compiled = compile_categories(categories or DEFAULT_SETTINGS["kategorien"])
    rows = []
    for pg in data["priceGuides"]:
        prod = data["products"].get(str(pg["idProduct"]), {})
        name = prod.get("name", f"Produkt {pg['idProduct']}")
        single = prod.get("_single", True)
        cats = categorize(name, compiled)
        m = CODE_RX.search(name)
        for foil in (False, True):
            suf = "-foil" if foil else ""
            low = pg.get("low" + suf)
            vals = [v for v in (pg.get("trend" + suf), pg.get("avg7" + suf)) if v]
            if not low or not vals:
                continue
            market = min(vals)  # konservativ: Trend-Ausreisser zaehlen nicht
            rows.append({
                "id": pg["idProduct"], "name": name, "foil": foil, "single": single,
                "code": m.group(1) if m else "", "cats": cats,
                "low": float(low), "market": float(market),
                "avg30": float(pg.get("avg30" + suf) or 0),
                "discount": round((1 - low / market) * 100, 1),
                "savings": round(market - low, 2),
            })
    return rows


def filter_rows(rows, f):
    q = [w for w in f.get("search", "").lower().split() if w]
    want_cats = set(f.get("cats") or [])
    out = []
    for r in rows:
        n = r["name"].lower()
        if q and not all(w in n for w in q):
            continue
        if want_cats and not want_cats.intersection(r["cats"]):
            continue
        if f.get("kind") == "Einzelkarten" and not r["single"]:
            continue
        if f.get("kind") == "Sealed (Booster, Displays)" and r["single"]:
            continue
        if f.get("foil") == "Nur normal" and r["foil"]:
            continue
        if f.get("foil") == "Nur Foil" and not r["foil"]:
            continue
        if r["low"] < f.get("min_price", 0) or r["low"] > f.get("max_price", 1e9):
            continue
        if r["market"] < f.get("min_market", 0):
            continue
        if r["discount"] < f.get("min_discount", 0):
            continue
        if r["savings"] < f.get("min_savings", 0):
            continue
        out.append(r)
    key = {"Ersparnis (EUR)": lambda r: -r["savings"], "Rabatt (%)": lambda r: -r["discount"],
           "Preis aufsteigend": lambda r: r["low"], "Marktwert": lambda r: -r["market"],
           "Name": lambda r: r["name"].lower()}.get(f.get("sort"), lambda r: -r["savings"])
    out.sort(key=key)
    return out


def offer_url(row, language=None, condition=None, country=None):
    """Link zu den Live-Angeboten auf Cardmarket, mit Sprach-, Zustands- und
    Laenderfilter (Land des Verkaeufers)."""
    # Kartencode wie OP01-024 ist die eindeutigste Suche, sonst der Name
    params = {"searchString": row.get("code") or row["name"]}
    if language:
        params["language"] = language
    if condition:
        params["minCondition"] = condition
    if country:
        params["sellerCountry"] = country
    if row["foil"]:
        params["isFoil"] = "Y"
    return "https://www.cardmarket.com/de/OnePiece/Products/Search?" + urllib.parse.urlencode(params)
