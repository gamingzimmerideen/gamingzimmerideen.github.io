"""Gaming Zimmer Ideen – Pin-Bot (Version 1)

Was der Bot macht:
  1. Nimmt die nächsten noch nicht genutzten Ideen aus ideen.json
  2. Zeichnet daraus Pin-Bilder (1000 x 1500)
  3. Verteilt sie auf einen Wochenplan (Standard: 2 Pins pro Tag)
  4. Schreibt eine CSV-Datei für den Sammel-Upload bei Pinterest
     (Einstellungen -> Inhalte importieren -> .csv hochladen)
  5. Erstellt eine Vorschau-Seite (vorschau.html) zum Durchsehen

Aufruf:
  python bot.py                      -> nächste Woche ab Montag
  python bot.py --start 2026-11-30   -> Woche ab einem bestimmten Tag
  python bot.py --tage 3             -> nur 3 Tage planen
  python bot.py --probe              -> nichts als "benutzt" merken (Testlauf)
"""
import argparse
import csv
import html
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from render import zeichne

BASIS = Path(__file__).parent
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
SPALTEN = ["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"]


def lade(name, standard=None):
    pfad = BASIS / name
    if not pfad.exists():
        return standard
    return json.loads(pfad.read_text(encoding="utf-8"))


def speichere(name, daten):
    (BASIS / name).write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")


def naechster_montag(heute=None):
    heute = heute or date.today()
    return heute + timedelta(days=(7 - heute.weekday()) % 7 or 7)


def zu_utc(tag, uhrzeit, zonenname):
    """Lokale Uhrzeit -> UTC-Text, wie Pinterest ihn verlangt."""
    stunde, minute = map(int, uhrzeit.split(":"))
    lokal = datetime(tag.year, tag.month, tag.day, stunde, minute)
    try:
        from zoneinfo import ZoneInfo
        lokal = lokal.replace(tzinfo=ZoneInfo(zonenname))
    except Exception:
        # Fallback ohne Zeitzonen-Daten: deutsche Sommerzeit grob von Ende März bis Ende Oktober
        sommer = 4 <= tag.month <= 10
        lokal = lokal.replace(tzinfo=timezone(timedelta(hours=2 if sommer else 1)))
    return lokal.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def waehle_ideen(ideen, benutzt, anzahl):
    """Nimmt unbenutzte Ideen, verteilt sie gleichmäßig auf alle Pinnwände
    und vermeidet dieselbe Pinnwand zweimal hintereinander."""
    offen = [i for i in ideen if i["id"] not in benutzt]
    if len(offen) < anzahl:
        print(f"Achtung: nur noch {len(offen)} neue Ideen übrig, gebraucht werden {anzahl}.")
        anzahl = len(offen)
    auswahl, zaehler = [], {}
    while len(auswahl) < anzahl:
        letzte = auswahl[-1]["pinnwand"] if auswahl else None
        kandidaten = [i for i in offen if i["pinnwand"] != letzte] or offen
        kandidat = min(kandidaten, key=lambda i: zaehler.get(i["pinnwand"], 0))
        offen.remove(kandidat)
        auswahl.append(kandidat)
        zaehler[kandidat["pinnwand"]] = zaehler.get(kandidat["pinnwand"], 0) + 1
    if len(offen) < anzahl:
        print(f"Hinweis: danach sind nur noch {len(offen)} Ideen übrig – bald neue Ideen ergänzen.")
    return auswahl


def pruefe(idee):
    fehler = []
    if len(idee["titel"]) > 100:
        fehler.append(f"Titel zu lang ({len(idee['titel'])} > 100)")
    if len(idee["beschreibung"]) > 500:
        fehler.append(f"Beschreibung zu lang ({len(idee['beschreibung'])} > 500)")
    return fehler


def vorschau_html(eintraege, ziel):
    karten = []
    for e in eintraege:
        karten.append(
            f"<div class='k'><img src='bilder/{html.escape(e['datei'])}' alt=''>"
            f"<p class='z'>{html.escape(e['zeit_lokal'])} · {html.escape(e['pinnwand'])}</p>"
            f"<h3>{html.escape(e['titel'])}</h3><p>{html.escape(e['beschreibung'])}</p></div>"
        )
    seite = (
        "<!DOCTYPE html><html lang='de'><meta charset='utf-8'><title>Pin-Vorschau</title>"
        "<style>body{font-family:system-ui,sans-serif;background:#0d0c1d;color:#ecebff;margin:20px}"
        ".g{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px}"
        ".k{background:#17152e;border:1px solid #2a2750;border-radius:12px;padding:12px}"
        ".k img{width:100%;border-radius:8px}.z{color:#28dcff;font-size:13px}h3{font-size:15px;margin:6px 0}"
        "p{font-size:13px;color:#c9c7e6}</style><h1>Pin-Vorschau</h1><div class='g'>"
        + "".join(karten) + "</div></html>"
    )
    (ziel / "vorschau.html").write_text(seite, encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Pin-Bot für Gaming Zimmer Ideen")
    p.add_argument("--start", help="Erster Tag (JJJJ-MM-TT), Standard: nächster Montag")
    p.add_argument("--tage", type=int, default=7, help="Wie viele Tage geplant werden")
    p.add_argument("--probe", action="store_true", help="Testlauf: Ideen nicht als benutzt merken")
    p.add_argument("--ausgabe", default=str(BASIS / "ausgabe"), help="Ordner für die Ergebnisse")
    args = p.parse_args()

    config = lade("config.json")
    ideen = lade("ideen.json", [])
    verlauf = lade("verlauf.json", {"benutzt": []})
    start = date.fromisoformat(args.start) if args.start else naechster_montag()

    pro_tag = config["pins_pro_tag"]
    uhrzeiten = config["uhrzeiten_lokal"][:pro_tag]
    ziel = Path(args.ausgabe) / start.isoformat()
    if (ziel / "plan.json").exists() and not args.probe:
        print(f"Für die Woche ab {start} gibt es schon Pins ({ziel}). Nichts zu tun.")
        return
    bild_url = config["bild_basis_url"].format(start=start.isoformat())

    auswahl = waehle_ideen(ideen, set(verlauf["benutzt"]), args.tage * pro_tag)
    if not auswahl:
        sys.exit("Keine neuen Ideen mehr. Bitte neue Ideen in ideen.json eintragen.")

    (ziel / "bilder").mkdir(parents=True, exist_ok=True)

    eintraege = []
    for n, idee in enumerate(auswahl):
        fehler = pruefe(idee)
        if fehler:
            sys.exit(f"Idee '{idee['id']}': " + "; ".join(fehler))
        tag = start + timedelta(days=n // pro_tag)
        uhrzeit = uhrzeiten[n % pro_tag]
        datei = f"{tag.isoformat()}-{idee['id']}.png"
        zeichne(idee, config["marke"]).save(ziel / "bilder" / datei, optimize=True)
        eintraege.append({
            "datei": datei,
            "titel": idee["titel"],
            "beschreibung": idee["beschreibung"],
            "pinnwand": idee["pinnwand"],
            "zeit_lokal": f"{WOCHENTAGE[tag.weekday()]} {tag.strftime('%d.%m.')} {uhrzeit}",
            "zeit_utc": zu_utc(tag, uhrzeit, config["zeitzone"]),
            "keywords": ", ".join(idee.get("keywords", [])),
            "link": idee.get("link") or config.get("seiten_basis_url", "").format(id=idee["id"]) or config.get("standard_link", ""),
            "alt": idee.get("alt", ""),
        })
        print(f"  {tag} {uhrzeit}  {idee['pinnwand']:<30}  {idee['titel']}")

    with open(ziel / "pinterest_upload.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(SPALTEN)
        for e in eintraege:
            w.writerow([e["titel"], bild_url + e["datei"], e["pinnwand"], "",
                        e["beschreibung"], e["link"], e["zeit_utc"], e["keywords"]])

    vorschau_html(eintraege, ziel)
    speichere_plan = [{k: e[k] for k in ("datei", "titel", "pinnwand", "zeit_lokal", "zeit_utc", "alt")} for e in eintraege]
    (ziel / "plan.json").write_text(json.dumps(speichere_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.probe:
        verlauf["benutzt"] += [i["id"] for i in auswahl]
        speichere("verlauf.json", verlauf)

    print(f"\nFertig: {len(eintraege)} Pins in {ziel}")
    print("Nächste Schritte:")
    print("  pinterest_upload.csv bei Pinterest hochladen (Einstellungen -> Inhalte importieren)")


if __name__ == "__main__":
    main()
