"""Phase 2b – Fassaden-Details, Innenraum-Moebel, zusaetzliche Schaeden (wird von gebaeude2.bauen() aufgerufen).

Kabel und Leerrohre, Hausanschluss vom Strommast, Strom-/Gaszaehler, Wandlampen, Fallrohre an Flachdaechern,
Rollgitter vor Laeden, Zettel/Plakate (erfundene allgemeine Texte), Zahnschnitt-Gesimse, Schmutz- und
Rostfahnen unter Fenstern, Ausbluehungen, Hausnummern, Such-Markierungen an Tueren, Moebel in den Raeumen.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

import fassade as FA
import viertel_lib as V

S = FA.SLOT
# Decal-Material-Indizes im *_Decals-Objekt (siehe gebaeude2.deko_materialien)
D_RUSS, D_SCHWARZ, D_ROT, D_WEISS, D_SCHMUTZ, D_ROSTFAHNE, D_SALZ, D_PAPIER, D_PAPIERTEXT = range(9)
PLAKATE = ["MISSING\nHAVE YOU SEEN\nTHIS MAN?", "SHELTER AT\nTHE SCHOOL", "BOIL WATER\nNOTICE", "CURFEW\n6 PM", "EVACUATION\nROUTE ->",
           "NO LOOTING", "LOST DOG", "WE WENT\nNORTH - J."]


def _rohr(b, pa, pb, r, mat, seg=6):
    d = pb - pa
    if d.length < 1e-3:
        return
    bm2 = bmesh.new()
    m = Matrix.Translation((pa + pb) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.create_cone(bm2, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length, matrix=m)
    b.mesh_einfuegen(bm2, mat)


def _plakat(b, w, s, z, rnd):
    bw, bh = rnd.uniform(0.25, 0.45), rnd.uniform(0.32, 0.6)
    ang = rnd.uniform(-0.12, 0.12)
    b.decal(w, s - bw / 2, s + bw / 2, z - bh / 2, z + bh / 2, D_PAPIER, n=-0.006)
    import gebaeude2 as G2
    m = G2._wand_matrix(w, s, -0.009, z + bh * 0.1) @ Matrix.Rotation(ang, 4, "Z")
    V.text_mesh(b.deko, rnd.choice(PLAKATE), min(0.055, bw / 9), m, D_PAPIERTEXT, extrude=0.0)


def fassade(b, g, rnd, masten):
    """Details fuer Gebaeude mit b.info = {'top', 'geschosse', 'ops'}."""
    info = getattr(b, "info", None)
    if not info:
        return
    W, D = b.r.W, b.r.D
    top = info["top"]
    z0 = b.z0
    typ = g["typ"]
    ops = info.get("ops", {})
    # 1) Schmutz-/Rostfahnen unter Fenstern, Ausbluehungen am Sockel
    for seite, liste in ops.items():
        w = b.wand(seite, info.get("dicke", 0.3))
        for o in liste:
            if o["s1"] - o["s0"] > 2.5 or o["z0"] < z0 + 0.3:
                continue
            if rnd.random() < 0.75:
                breite = (o["s1"] - o["s0"]) * rnd.uniform(0.5, 1.1)
                sc = (o["s0"] + o["s1"]) / 2 + rnd.uniform(-0.1, 0.1)
                lang = rnd.uniform(0.6, 1.9)
                b.decal(w, sc - breite / 2, sc + breite / 2, o["z0"] - 0.08 - lang, o["z0"] - 0.08, D_SCHMUTZ, n=-0.004)
        if typ in (1, 3, 8) and "Ziegel" in g["fassade"]:
            for k in range(rnd.randint(1, 3)):
                sc = rnd.uniform(w.s0 + 0.5, w.s1 - 0.5)
                b.decal(w, sc - rnd.uniform(0.4, 1.2), sc + rnd.uniform(0.4, 1.2), z0 + 0.05, z0 + rnd.uniform(0.4, 0.9), D_SALZ, n=-0.003)
    # 2) Fallrohre (D 10 cm) mit Speier an der Attika (Flachdaecher), eines teils abgerissen
    if typ in (1, 3, 5, 6, 8):
        for (u, v, seite) in ((0.15, D + 0.08, "hinten"), (W - 0.15, D + 0.08, "hinten"), (W + 0.08, D * 0.5, "rechts")):
            if rnd.random() < 0.35:
                continue
            x, y = b.r.p(u, v)
            oben = top + 0.2
            if rnd.random() < 0.2:  # abgerissen: oberes Stueck fehlt, unteres haengt schief
                _rohr(b, Vector((x, y, z0 + 0.2)), Vector((x + rnd.uniform(-0.3, 0.3), y, oben - 2.5)), 0.05, S["Metall"], 8)
            else:
                _rohr(b, Vector((x, y, z0 + 0.15)), Vector((x, y, oben)), 0.05, S["Metall"], 8)
            b.box(u - 0.15, v - 0.12, u + 0.15, v + 0.12, oben - 0.1, oben + 0.25, S["Metall"])
    # 3) Leerrohr/Kabel an der Fassade + Zaehler an Seite/Rueckseite
    for seite in ("hinten", "links") if typ != 2 else ("links",):
        w = b.wand(seite, info.get("dicke", 0.3))
        sc = rnd.uniform(w.s0 + 0.6, w.s1 - 0.6)
        FA.box_welt(b.bm, w, sc - 0.17, sc + 0.17, -0.2, 0.0, z0 + 1.1, z0 + 1.6, S["Metall"])  # Zaehlerkasten
        FA.box_welt(b.bm, w, sc - 0.02, sc + 0.02, -0.07, -0.03, z0 + 1.6, min(top, z0 + 5.8), S["Rost"])  # Leerrohr
        if rnd.random() < 0.6:  # Gaszaehler mit Leitung
            gs = sc + rnd.choice([-1.2, 1.2])
            FA.box_welt(b.bm, w, gs - 0.15, gs + 0.15, -0.25, -0.02, z0 + 0.4, z0 + 0.8, S["Lack"])
            FA.box_welt(b.bm, w, gs - 0.02, gs + 0.02, -0.12, -0.08, z0 - 0.1, z0 + 0.4, S["Lack"])
    # 4) Hausanschluss vom naechsten Strommast (durchhaengendes Kabel)
    if masten:
        fx, fy = b.r.p(W * rnd.uniform(0.2, 0.8), -0.1)
        anschluss = Vector((fx, fy, min(top - 0.3, z0 + rnd.uniform(5.0, 6.2))))
        best = min(masten, key=lambda m: (m.x - fx) ** 2 + (m.y - fy) ** 2)
        if (best.xy - anschluss.xy).length < 32 and rnd.random() < 0.8:
            b.kabel.append((best, anschluss))
            _rohr(b, anschluss - Vector((0, 0, 0.4)), anschluss + Vector((0, 0, 0.2)), 0.025, S["Metall"], 6)
    # 5) Wandlampen ueber Tueren, Schwanenhals-Lampen ueber Schildband (Typ 3)
    wv = b.wand("vorne", info.get("dicke", 0.3))
    if typ == 3:
        for k in range(rnd.randint(2, 3)):
            sc = (k + 0.5) * W / 3
            zz = z0 + info.get("eg", 4.2) - 0.05
            pa = wv.welt(sc, 0.0, zz)
            pb = wv.welt(sc, -0.6, zz + 0.35)
            _rohr(b, pa, pb, 0.015, S["Metall"], 5)
            hang = rnd.random() < 0.3
            q = pb + (Vector((0, 0, -0.25)) if hang else Vector((0, 0, 0)))
            bm2 = bmesh.new()
            bmesh.ops.create_cone(bm2, cap_ends=True, segments=12, radius1=0.16, radius2=0.04, depth=0.16, matrix=Matrix.Translation(q - Vector((0, 0, 0.08))))
            b.mesh_einfuegen(bm2, S["Lack"])
    elif typ in (1, 2):
        sc = W / 2 + 0.85
        zz = info.get("tuer_oben", z0 + 2.6)
        FA.box_welt(b.bm, wv, sc - 0.08, sc + 0.08, -0.18, 0.0, zz, zz + 0.28, S["Metall"])
        V.text_mesh(b.bm, str(100 + int(g["id"][1:]) * 4), 0.12, Matrix.Translation(wv.welt(W / 2 - 0.9, -0.012, zz + 0.1)) @ _richtung(wv), S["Lack"], extrude=0.005)
    # 6) Rollgitter vor dem Schaufenster (Typ 3, 35 %): Kasten + teils heruntergelassene Lamellen
    if typ == 3 and rnd.random() < 0.35:
        p = 0.45
        zo = z0 + 3.65
        FA.box_welt(b.bm, wv, p, W - p, -0.32, 0.0, zo, zo + 0.32, S["Metall"])
        unten = zo - rnd.uniform(0.6, 2.8)
        k = 0
        z = zo
        while z > unten:
            FA.box_welt(b.bm, wv, p + 0.05, W - p - 0.05, -0.25 - 0.01 * (k % 2), -0.22, z - 0.09, z, S["Rost"] if rnd.random() < 0.3 else S["Metall"])
            z -= 0.1
            k += 1
    # 7) Zahnschnitt unter dem Ziergesims (Typ 3) / Gesimskonsolen (Typ 1)
    if typ == 3:
        zz = top + g["attika"] - 0.55
        s = 0.1
        while s < W - 0.1:
            if not (g["zerstoerung"] == "schwer" and rnd.random() < 0.3):
                b.box(s, -0.32, s + 0.12, 0.0, zz - 0.14, zz, S["Beton"])
            s += 0.26
    elif typ == 1:
        zz = top - 0.45
        s = 0.3
        while s < W - 0.3:
            b.box(s, -0.3, s + 0.18, 0.0, zz - 0.3, zz, S["Beton"])
            s += 1.1
    # 8) Zettel, Plakate, Such-Markierungen (X) an Tueren
    for k in range(rnd.randint(1, 4)):
        _plakat(b, wv, rnd.uniform(0.7, W - 0.7), z0 + rnd.uniform(1.2, 2.0), rnd)
    if rnd.random() < 0.5:
        tx = W / 2
        m = Matrix.Translation(wv.welt(tx, -0.02, z0 + 1.6)) @ _richtung(wv)
        V.text_mesh(b.deko, "X", 0.9, m, rnd.choice([D_ROT, D_SCHWARZ]), extrude=0.0)
        for (dx, dz, t) in ((-0.32, 0.0, rnd.choice(["2", "0", "1"])), (0.32, 0.0, rnd.choice(["9-14", "10-3"])), (0.0, 0.38, rnd.choice(["G", "TF"])), (0.0, -0.38, rnd.choice(["0", "3"]))):
            V.text_mesh(b.deko, t, 0.13, Matrix.Translation(wv.welt(tx + dx, -0.021, z0 + 1.6 + dz)) @ _richtung(wv), D_SCHWARZ, extrude=0.0)
    # 9) Satellitenschuessel an der Fassade (Wohnhaeuser)
    if typ in (1, 2) and rnd.random() < 0.5:
        ws = b.wand(rnd.choice(["links", "rechts"]), info.get("dicke", 0.3))
        sc = rnd.uniform(ws.s0 + 1, ws.s1 - 1)
        zz = min(top - 1.0, z0 + rnd.uniform(3.0, 6.5))
        p = ws.welt(sc, -0.45, zz)
        bm2 = bmesh.new()
        bmesh.ops.create_uvsphere(bm2, u_segments=14, v_segments=7, radius=0.32)
        for vv in bm2.verts:
            vv.co.z = max(vv.co.z, 0.18)
        bmesh.ops.transform(bm2, verts=bm2.verts, matrix=Matrix.Translation(p) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z") @ Matrix.Rotation(1.2, 4, "X"))
        b.mesh_einfuegen(bm2, S["Lack"])
        _rohr(b, ws.welt(sc, 0.0, zz), p, 0.02, S["Metall"], 5)


def _richtung(w):
    p = w.welt(0, 0, 0)
    ex = (w.welt(1, 0, 0) - p).normalized()
    ez = (w.welt(0, -1, 0) - p).normalized()
    return Matrix((ex, Vector((0, 0, 1)), ez)).transposed().to_4x4()


def innenraum(b, g, rnd):
    """Moebel hinter den Fenstern (Mittel-/Nahbereich): Tische, Stuehle, Schraenke, Betten, Sofas, teils umgekippt."""
    info = getattr(b, "info", None)
    if not info or g["typ"] not in (1, 3, 5, 6, 8):
        return
    W, D = b.r.W, b.r.D
    d = info.get("dicke", 0.3)
    geschosse = info["geschosse"][1:] if g["typ"] == 3 else info["geschosse"]
    buero = g["typ"] in (5, 6)
    for zf in geschosse:
        n = int((W + D) * 0.35)
        for k in range(n):
            seite = rnd.random()
            if seite < 0.5:
                u, v = rnd.uniform(d + 0.6, W - d - 0.6), rnd.choice([rnd.uniform(d + 0.5, min(3.8, D / 2)), rnd.uniform(max(D - 3.8, D / 2), D - d - 0.5)])
            else:
                u, v = rnd.choice([rnd.uniform(d + 0.5, min(3.8, W / 2)), rnd.uniform(max(W - 3.8, W / 2), W - d - 0.5)]), rnd.uniform(d + 0.6, D - d - 0.6)
            art = rnd.random()
            kipp = rnd.random() < 0.3
            if buero:
                if art < 0.6:  # Schreibtisch
                    b.box(u - 0.7, v - 0.4, u + 0.7, v + 0.4, zf + 0.72, zf + 0.75, S["Holz"])
                    if not kipp:
                        b.box(u - 0.65, v - 0.35, u - 0.6, v + 0.35, zf, zf + 0.72, S["Metall"])
                        b.box(u + 0.6, v - 0.35, u + 0.65, v + 0.35, zf, zf + 0.72, S["Metall"])
                else:  # Aktenschrank
                    b.box(u - 0.25, v - 0.3, u + 0.25, v + 0.3, zf, zf + (0.5 if kipp else 1.3), S["Metall"])
            else:
                if art < 0.25:  # Tisch
                    b.box(u - 0.6, v - 0.45, u + 0.6, v + 0.45, zf + (0.0 if kipp else 0.72), zf + (0.04 if kipp else 0.76), S["Holz"])
                elif art < 0.45:  # Schrank / Regal
                    b.box(u - 0.5, v - 0.25, u + 0.5, v + 0.25, zf, zf + (0.5 if kipp else 1.9), S["Holz"])
                elif art < 0.65:  # Sofa
                    b.box(u - 0.9, v - 0.45, u + 0.9, v + 0.45, zf, zf + 0.45, S["Stoff"])
                    b.box(u - 0.9, v + 0.3, u + 0.9, v + 0.45, zf + 0.45, zf + 0.85, S["Stoff"])
                elif art < 0.8:  # Bett/Matratze
                    b.box(u - 0.75, v - 1.0, u + 0.75, v + 1.0, zf, zf + 0.45, S["Stoff"])
                else:  # Stuhl
                    b.box(u - 0.22, v - 0.22, u + 0.22, v + 0.22, zf + (0.0 if kipp else 0.45), zf + (0.05 if kipp else 0.49), S["Holz"])
        for k in range(rnd.randint(1, 3)):  # Deckenlampe (haengend)
            u, v = rnd.uniform(1.5, W - 1.5), rnd.uniform(1.5, D - 1.5)
            zd = zf + (3.8 if buero else 3.2) - 0.25
            hz = zd - rnd.uniform(0.3, 1.0)
            b.box(u - 0.005, v - 0.005, u + 0.005, v + 0.005, hz, zd, S["Metall"])
            b.box(u - 0.2, v - 0.2, u + 0.2, v + 0.2, hz - 0.12, hz, S["Lack"])


def zusatzschaden(b, g, rnd, ops):
    """Mittlere Schaeden: 1-2 Mauerdurchbrueche, fehlende Attika-Stuecke (Ziegel darunter). Liefert zusaetzliche Oeffnungen."""
    if g["zerstoerung"] != "mittel" or g["typ"] not in (1, 3):
        return {}
    info = b.info
    W = b.r.W
    neu = {}
    seite = rnd.choice(["links", "rechts", "hinten"]) if g["typ"] == 1 else "hinten"
    w = b.wand(seite, info.get("dicke", 0.3))
    for k in range(rnd.randint(1, 2)):
        sc = rnd.uniform(w.s0 + 1.2, w.s1 - 1.2)
        zz = rnd.uniform(b.z0 + 0.5, info["top"] - 2.0)
        o = {"s0": sc - rnd.uniform(0.4, 0.8), "s1": sc + rnd.uniform(0.4, 0.8), "z0": zz, "z1": zz + rnd.uniform(0.7, 1.4)}
        if not any(not (o["s1"] + 0.2 < q["s0"] or o["s0"] - 0.2 > q["s1"] or o["z1"] + 0.2 < q["z0"] or o["z0"] - 0.2 > q["z1"]) for q in ops.get(seite, [])):
            neu.setdefault(seite, []).append(o)
            b.boden_teile.append((w.welt(sc, -1.0, 0), "schuttkegel:1.2:0.35"))
    return neu
