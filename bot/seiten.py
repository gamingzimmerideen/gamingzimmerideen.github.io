"""Baut für jede Idee aus ideen.json eine eigene Seite auf der Website.

Aufruf (vom Hauptordner der Website aus):
  python bot/seiten.py --ziel ideen

Ergebnis:
  ideen/index.html        Übersicht aller Ideen, sortiert nach Pinnwand
  ideen/<id>.html         eine Seite pro Idee (Ziel der Pin-Links)
  ideen/bilder/<id>.jpg   Bild zur Idee
  sitemap.xml             Liste aller Seiten für Suchmaschinen

Produkte: Hat eine Idee ein Feld "produkte" (Liste aus {"name", "link", "text"}),
erscheinen sie als Abschnitt "Passende Produkte" – z. B. mit Amazon-Partnerlinks.
"""
import argparse
import html
import json
import re
from pathlib import Path

from render import zeichne

BASIS = Path(__file__).parent
SITE = "https://gamingzimmerideen.github.io"
E = html.escape


def lade(name):
    return json.loads((BASIS / name).read_text(encoding="utf-8"))


def slug(text):
    t = text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def einleitung(beschreibung):
    """Beschreibung ohne die Pinterest-Sätze ("Merk dir den Pin ...")."""
    saetze = re.split(r"(?<=[.!?])\s+", beschreibung.strip())
    return " ".join(s for s in saetze if "Pin" not in s)


def rahmen(titel, beschreibung, inhalt, tiefe=1, kanonisch=""):
    vor = "../" * tiefe
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(titel)} | Gaming Zimmer Ideen</title>
<meta name="description" content="{E(beschreibung[:160])}">
<link rel="canonical" href="{E(kanonisch)}">
<link rel="icon" href="{vor}logo.png">
<link rel="stylesheet" href="{vor}style.css">
</head>
<body>
<header>
  <img src="{vor}logo.png" alt="Logo Gaming Zimmer Ideen">
  <a class="brand" href="{vor}index.html">Gaming Zimmer Ideen</a>
  <nav><a href="{vor}index.html">Start</a><a class="active" href="{vor}ideen/index.html">Ideen</a><a href="{vor}datenschutz.html">Datenschutz</a><a href="{vor}impressum.html">Impressum</a></nav>
</header>
<main>
{inhalt}
</main>
<footer><span>© 2026 Gaming Zimmer Ideen</span><a href="{vor}datenschutz.html">Datenschutz</a><a href="{vor}impressum.html">Impressum</a></footer>
</body>
</html>
"""


def ideen_seite(idee, verwandte):
    if "punkte" in idee:
        liste = "<ol class='punkte'>" + "".join(f"<li>{E(p)}</li>" for p in idee["punkte"]) + "</ol>"
    else:
        liste = "<ul class='farben'>" + "".join(
            f"<li><span class='swatch' style='background:rgb{tuple(f['farben'][0])}'></span>"
            f"<strong>{E(f['name'])}</strong> – {E(f['text'])}</li>" for f in idee["farben"]) + "</ul>"
    tipp = f"<div class='card tipp'><strong>Tipp:</strong> {E(idee['tipp'])}</div>" if idee.get("tipp") else ""
    produkte = ""
    if idee.get("produkte"):
        eintraege = "".join(
            f"<li><a href='{E(p['link'])}' rel='sponsored nofollow noopener' target='_blank'>{E(p['name'])}</a>"
            + (f" – {E(p['text'])}" if p.get("text") else "") + "</li>" for p in idee["produkte"])
        produkte = (f"<h2>Passende Produkte</h2><ul>{eintraege}</ul>"
                    "<p class='note'>* Affiliate-Links: Als Amazon-Partner verdienen wir an qualifizierten Verkäufen. "
                    "Für dich ändert sich am Preis nichts.</p>")
    mehr = "".join(f"<li><a href='{E(v['id'])}.html'>{E(v['bildtitel'])}</a></li>" for v in verwandte)
    inhalt = f"""  <p class="crumbs"><a href="index.html">Ideen</a> › <a href="index.html#{slug(idee['pinnwand'])}">{E(idee['pinnwand'])}</a></p>
  <h1>{E(idee['titel'])}</h1>
  <img class="idee-bild" src="bilder/{E(idee['id'])}.jpg" alt="{E(idee.get('alt', ''))}" width="600" height="900">
  <p>{E(einleitung(idee['beschreibung']))}</p>
  <h2>Auf einen Blick</h2>
  {liste}
  {tipp}
  {produkte}
  <h2>Mehr Ideen aus „{E(idee['pinnwand'])}“</h2>
  <ul>{mehr}</ul>
  <a class="btn" href="https://de.pinterest.com/gamingzimmer_ideen/">Mehr Ideen auf Pinterest</a>"""
    return rahmen(idee["titel"], einleitung(idee["beschreibung"]), inhalt,
                  kanonisch=f"{SITE}/ideen/{idee['id']}.html")


def uebersicht(ideen):
    gruppen = {}
    for i in ideen:
        gruppen.setdefault(i["pinnwand"], []).append(i)
    teile = ["  <h1>Alle <span>Ideen</span> fürs Gaming-Zimmer</h1>",
             f"  <p>{len(ideen)} Ideen für Setups, LED-Beleuchtung, Deko und Ordnung am Schreibtisch.</p>"]
    for pinnwand, liste in gruppen.items():
        teile.append(f"  <h2 id='{slug(pinnwand)}'>{E(pinnwand)}</h2><div class='raster'>")
        for i in liste:
            teile.append(f"<a class='kachel' href='{E(i['id'])}.html'><img src='bilder/{E(i['id'])}.jpg' "
                         f"alt='' loading='lazy' width='600' height='900'><span>{E(i['bildtitel'])}</span></a>")
        teile.append("</div>")
    return rahmen("Alle Ideen", "Alle Ideen für dein Gaming-Zimmer: Setups, LED, Deko und Schreibtisch.",
                  "\n".join(teile), kanonisch=f"{SITE}/ideen/")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ziel", default="ideen", help="Ordner für die Seiten")
    p.add_argument("--sitemap", default="sitemap.xml")
    args = p.parse_args()

    config, ideen = lade("config.json"), lade("ideen.json")
    ziel = Path(args.ziel)
    (ziel / "bilder").mkdir(parents=True, exist_ok=True)

    for n, idee in enumerate(ideen):
        bild = ziel / "bilder" / f"{idee['id']}.jpg"
        if not bild.exists():
            zeichne(idee, config["marke"]).convert("RGB").resize((600, 900)).save(bild, quality=82, optimize=True)
        gleiche = [i for i in ideen if i["pinnwand"] == idee["pinnwand"] and i["id"] != idee["id"]]
        start = gleiche.index(next((i for i in gleiche if ideen.index(i) > n), gleiche[0])) if gleiche else 0
        verwandte = (gleiche[start:] + gleiche[:start])[:4]
        (ziel / f"{idee['id']}.html").write_text(ideen_seite(idee, verwandte), encoding="utf-8")

    (ziel / "index.html").write_text(uebersicht(ideen), encoding="utf-8")

    urls = [f"{SITE}/", f"{SITE}/ideen/"] + [f"{SITE}/ideen/{i['id']}.html" for i in ideen]
    Path(args.sitemap).write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    print(f"{len(ideen)} Ideen-Seiten in {ziel}/ erstellt")


if __name__ == "__main__":
    main()
