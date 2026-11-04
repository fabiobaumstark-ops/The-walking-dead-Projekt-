#!/usr/bin/env python3
"""Kontaktbogen der Grundmodell-Vorschau (benoetigt Pillow: pip install pillow).

Aufruf:  python3 scripts/phase3/kontaktbogen.py
Ergebnis: renders/test/phase3_grund_uebersicht.png (8 Zeilen x 4 Ansichten) + je Typ phase3_grund_<Typ>_bogen.png
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
R = os.path.join(ROOT, "renders", "test")
TYPEN = json.load(open(os.path.join(ROOT, "scripts", "configs", "fahrzeuge.json"), encoding="utf-8"))["typen"]
ANSICHTEN = ["vorne", "seite", "hinten", "innen"]


def schrift(gr):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, gr)
    return ImageFont.load_default()


def main():
    w, h = 400, 225
    zeilen = [t for t in "ABCDEFGH" if os.path.exists(os.path.join(R, f"phase3_grund_{t}_vorne.png"))]
    bogen = Image.new("RGB", (w * 4 + 150, h * len(zeilen)), (24, 24, 24))
    d = ImageDraw.Draw(bogen)
    f1, f2 = schrift(30), schrift(15)
    for zi, t in enumerate(zeilen):
        T = TYPEN[t]
        d.text((12, zi * h + 20), t, fill=(240, 240, 240), font=f1)
        txt = f"{T['name']}\n{T['L']:.2f} x {T['B']:.2f}\nx {T['H']:.2f} m\nRadst. {T['radstand']:.2f}"
        d.multiline_text((12, zi * h + 65), txt, fill=(200, 200, 200), font=f2, spacing=4)
        einzel = []
        for ai, a in enumerate(ANSICHTEN):
            p = os.path.join(R, f"phase3_grund_{t}_{a}.png")
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGB")
            einzel.append(im)
            bogen.paste(im.resize((w, h)), (150 + ai * w, zi * h))
        if len(einzel) == 4:
            ew, eh = einzel[0].size
            b = Image.new("RGB", (ew * 2, eh * 2))
            for i, im in enumerate(einzel):
                b.paste(im, ((i % 2) * ew, (i // 2) * eh))
            b.save(os.path.join(R, f"phase3_grund_{t}_bogen.png"))
    bogen.save(os.path.join(R, "phase3_grund_uebersicht.png"))
    print("Kontaktbogen:", os.path.join(R, "phase3_grund_uebersicht.png"))


if __name__ == "__main__":
    main()
