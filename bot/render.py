"""Zeichnet Pin-Bilder (1000 x 1500) im Neon-Look von Gaming Zimmer Ideen."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1000, 1500
BASIS = Path(__file__).parent
# Schriften: erst im Bot-Ordner suchen, sonst die Systemschrift (z. B. auf dem GitHub-Server)
FONTS = next((p for p in [BASIS / "fonts", Path("/usr/share/fonts/opentype/inter")] if (p / "Inter-Bold.otf").exists()), BASIS / "fonts")
LOGO = next((p for p in [BASIS / "assets" / "logo.png", BASIS.parent / "logo.png"] if p.exists()), BASIS / "assets" / "logo.png")

MAG = (255, 64, 200)
CYA = (40, 220, 255)
VIO = (150, 90, 255)
AKZENTE = {
    "neon": (MAG, CYA),
    "violet": (VIO, CYA),
    "pink": (MAG, VIO),
    "cyan": (CYA, (90, 255, 180)),
    "warm": ((255, 150, 60), MAG),
}


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def mischen(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hintergrund(oben=(24, 20, 48), unten=(8, 8, 20)):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=mischen(oben, unten, y / H))
    return img.convert("RGBA")


def verlauf(groesse, c1, c2):
    w, h = groesse
    g = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(g)
    for i in range(w):
        d.line([(i, 0), (i, h)], fill=mischen(c1, c2, i / max(1, w - 1)))
    return g


def leuchten(img, xy, r, farbe, alpha=90):
    schicht = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(schicht).ellipse([xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r], fill=farbe + (alpha,))
    return Image.alpha_composite(img, schicht.filter(ImageFilter.GaussianBlur(r * 0.6)))


def umbrechen(d, text, fnt, maxbreite):
    woerter, zeilen, aktuell = text.split(), [], ""
    for w in woerter:
        t = (aktuell + " " + w).strip()
        if d.textlength(t, font=fnt) <= maxbreite:
            aktuell = t
        else:
            if aktuell:
                zeilen.append(aktuell)
            aktuell = w
    if aktuell:
        zeilen.append(aktuell)
    return zeilen


def verlaufstext(img, xy, text, fnt, c1, c2):
    d = ImageDraw.Draw(img)
    box = d.textbbox(xy, text, font=fnt)
    breite = max(1, int(box[2] - box[0]))
    maske = Image.new("L", (W, H), 0)
    ImageDraw.Draw(maske).text(xy, text, font=fnt, fill=255)
    voll = Image.new("RGB", (W, H), c1)
    voll.paste(verlauf((breite, H), c1, c2), (int(box[0]), 0))
    schicht = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    schicht.paste(voll, (0, 0), maske)
    return Image.alpha_composite(img, schicht)


_LOGO = None


def fusszeile(img, c1, c2, name, handle):
    global _LOGO
    if _LOGO is None:
        _LOGO = Image.open(LOGO).convert("RGB").resize((84, 84), Image.LANCZOS)
    rund = Image.new("L", (84, 84), 0)
    ImageDraw.Draw(rund).ellipse([0, 0, 83, 83], fill=255)
    d = ImageDraw.Draw(img)
    y = H - 130
    img.paste(verlauf((W - 120, 4), c1, c2), (60, y - 30))
    img.paste(_LOGO, (60, y), rund)
    d.text((165, y + 6), name, font=font("Inter-Bold.otf", 34), fill=(255, 255, 255))
    d.text((165, y + 48), handle, font=font("Inter-Medium.otf", 26), fill=(170, 170, 200))
    return img


def kopf(img, etikett, titel, akzentwort, c1, c2):
    d = ImageDraw.Draw(img)
    tf = font("Inter-SemiBold.otf", 28)
    tb = d.textlength(etikett.upper(), font=tf)
    pille = (int(tb) + 48, 54)
    pm = Image.new("L", pille, 0)
    ImageDraw.Draw(pm).rounded_rectangle([0, 0, pille[0] - 1, 53], radius=27, fill=255)
    img.paste(verlauf(pille, c1, c2), (60, 70), pm)
    d = ImageDraw.Draw(img)
    d.text((84, 80), etikett.upper(), font=tf, fill=(15, 12, 30))
    groesse = 92
    while True:
        fnt = font("InterDisplay-ExtraBold.otf", groesse)
        zeilen = umbrechen(d, titel, fnt, W - 120)
        passt = all(d.textlength(z, font=fnt) <= W - 120 for z in zeilen)
        if (len(zeilen) <= 4 and passt) or groesse <= 56:
            break
        groesse -= 4
    y, zh = 160, int(groesse * 1.1)
    for zeile in zeilen:
        if akzentwort and akzentwort in zeile:
            vor, nach = zeile.split(akzentwort, 1)
            x = 60
            d.text((x, y), vor, font=fnt, fill=(255, 255, 255))
            x += d.textlength(vor, font=fnt)
            img = verlaufstext(img, (x, y), akzentwort, fnt, c1, c2)
            d = ImageDraw.Draw(img)
            x += d.textlength(akzentwort, font=fnt)
            d.text((x, y), nach, font=fnt, fill=(255, 255, 255))
        else:
            d.text((60, y), zeile, font=fnt, fill=(255, 255, 255))
        y += zh
    return img, y


def listen_pin(idee, marke):
    c1, c2 = AKZENTE[idee.get("akzent", "neon")]
    img = hintergrund()
    img = leuchten(img, (W - 80, 140), 260, c2, 70)
    img = leuchten(img, (60, H - 300), 300, c1, 55)
    img, y = kopf(img, idee["etikett"], idee["bildtitel"], idee.get("akzentwort"), c1, c2)
    d = ImageDraw.Draw(img)
    punkte = idee["punkte"]
    platz = (H - 200) - (y + 40)
    nf = font("InterDisplay-Bold.otf", 34)
    groesse = 50
    while True:
        tf = font("Inter-Medium.otf", groesse)
        bloecke = [umbrechen(d, p, tf, W - 210) for p in punkte]
        gesamt = sum(len(b) * int(groesse * 1.3) for b in bloecke) + (len(punkte) - 1) * 26
        if gesamt <= platz or groesse <= 32:
            break
        groesse -= 2
    extra = min(40, max(0, (platz - gesamt) // len(punkte)))
    yy = y + 40 + max(0, (platz - gesamt - extra * (len(punkte) - 1)) // 2)
    for i, b in enumerate(bloecke):
        kreis = Image.new("L", (60, 60), 0)
        ImageDraw.Draw(kreis).ellipse([0, 0, 59, 59], fill=255)
        ky = yy + int(groesse * 0.65) - 30
        img.paste(verlauf((60, 60), c1, c2), (60, ky), kreis)
        d = ImageDraw.Draw(img)
        nr = str(i + 1)
        d.text((90 - d.textlength(nr, font=nf) / 2, ky + 8), nr, font=nf, fill=(15, 12, 30))
        for j, zeile in enumerate(b):
            farbe = (235, 235, 250) if j == 0 else (200, 200, 225)
            d.text((150, yy + j * int(groesse * 1.3)), zeile, font=tf, fill=farbe)
        yy += len(b) * int(groesse * 1.3) + 26 + extra
    img = fusszeile(img, c1, c2, marke["name"], marke["handle"])
    return img.convert("RGB")


def farb_pin(idee, marke):
    c1, c2 = AKZENTE[idee.get("akzent", "neon")]
    img = hintergrund()
    img = leuchten(img, (W - 80, 140), 260, c2, 70)
    img, y = kopf(img, idee["etikett"], idee["bildtitel"], idee.get("akzentwort"), c1, c2)
    d = ImageDraw.Draw(img)
    kombis = idee["farben"]
    platz = (H - 200) - (y + 70)
    zeile_h = min(210, platz // len(kombis))
    yy = y + 70 + max(0, (platz - zeile_h * len(kombis)) // 2)
    lf, sf = font("Inter-Bold.otf", 44), font("Inter-Medium.otf", 32)
    for k in kombis:
        sw = 110
        for n, farbe in enumerate(k["farben"]):
            x = 60 + n * (sw - 18)
            m = Image.new("L", (sw, sw), 0)
            ImageDraw.Draw(m).ellipse([0, 0, sw - 1, sw - 1], fill=255)
            ring = Image.new("L", (sw + 8, sw + 8), 0)
            ImageDraw.Draw(ring).ellipse([0, 0, sw + 7, sw + 7], fill=255)
            img.paste((12, 10, 26, 255), (x - 4, yy - 4), ring)
            img.paste(tuple(farbe) + (255,), (x, yy), m)
        d = ImageDraw.Draw(img)
        tx = 60 + len(k["farben"]) * (sw - 18) + 50
        d.text((tx, yy + 6), k["name"], font=lf, fill=(240, 240, 255))
        for j, zeile in enumerate(umbrechen(d, k["text"], sf, W - tx - 60)[:2]):
            d.text((tx, yy + 60 + j * 40), zeile, font=sf, fill=(190, 190, 215))
        yy += zeile_h
    img = fusszeile(img, c1, c2, marke["name"], marke["handle"])
    return img.convert("RGB")


def zeichne(idee, marke):
    return farb_pin(idee, marke) if idee.get("farben") else listen_pin(idee, marke)
