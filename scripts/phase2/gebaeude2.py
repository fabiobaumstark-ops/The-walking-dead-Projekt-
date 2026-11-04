"""Phase 2.1/2.2 – Gebaeude mit Architektur-Details und Schadenskatalog.

Gleiche Planung wie Phase 1 (scripts/configs/gebaeude.json, Seed 42). Echte Fensteroeffnungen mit Laibung,
Rahmen, Glaszustand, Fensterbaenken, Stuerzen, Klimageraeten, Vorhaengen, Innenraeumen (Boden/Decke/Rueckwand),
Schaufenster mit Schildband (erfundene Namen), Markisen, Feuertreppen, Dachtechnik, Russ, Graffiti, Einstuerze.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "phase1"))
import blockout_gebaeude as P1  # noqa: E402
import fassade as FA  # noqa: E402
import viertel_lib as V  # noqa: E402

S = FA.SLOT
LADENNAMEN = {"Diner": "BELL'S DINER", "Friseur": "BARBER SHOP", "Eisenwaren": "MILLER HARDWARE",
              "Apotheke": "PHARMACY", "Bar": "THE LANTERN", "Gebrauchtwaren": "SECOND HAND",
              "Waschsalon": "LAUNDROMAT", "Lebensmittel": "GROCERY", "Elektro": "RADIO & TV",
              "Schuhe": "SHOE REPAIR"}
GRAFFITI = ["STAY OUT", "NO WATER", "DEAD INSIDE", "GO NORTH", "HELP", "NO FOOD", "KEEP OUT", "14", "3 INSIDE", "->"]


class Bau2(P1.Bau):
    def __init__(self, rahmen, z0, rnd):
        super().__init__(rahmen, z0)
        self.rnd = rnd
        self.deko = bmesh.new()          # Decals (Russ, Graffiti) mit eigener UV
        self.boden_teile = []            # heruntergefallene Dinge (Position, Art) fuer Schutt/Props

    def wand(self, seite, dicke=0.3):
        return FA.Wand(self, seite, dicke)

    def decal(self, wand, s0, s1, z0, z1, mat, n=-0.008):
        uvl = self.deko.loops.layers.uv.verify()
        vs = [self.deko.verts.new(wand.welt(s, n, z)) for s, z in ((s0, z0), (s1, z0), (s1, z1), (s0, z1))]
        f = self.deko.faces.new(vs)
        f.material_index = mat
        for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            lp[uvl].uv = uv

    def graffiti(self, wand, s, z, text, groesse, mat):
        rot = Matrix.Rotation(self.rnd.uniform(-0.08, 0.08), 4, "Z")
        m = _wand_matrix(wand, s, -0.006, z) @ rot
        V.text_mesh(self.deko, text, groesse, m, mat, extrude=0.0)


def _wand_matrix(wand, s, n, z):
    """Matrix: lokal x = s-Richtung, y = oben, z = aus der Wand heraus."""
    p = wand.welt(s, n, z)
    ex = (wand.welt(s + 1, n, z) - p).normalized()
    ez = (wand.welt(s, n - 1, z) - p).normalized()
    ey = Vector((0, 0, 1))
    m = Matrix((ex, ey, ez)).transposed().to_4x4()
    m.translation = p
    return m


# ------------------------------------------------------------------ Grundbausteine
def huelle(b, g, geschosse, top, oeffnungen, dicke=0.3, zacken=None, boden=None, kern=True):
    """Waende mit Oeffnungen + Geschossdecken + Kern (Rueckwand der Raeume)."""
    rnd = b.rnd
    W, D = b.r.W, b.r.D
    for seite, ops in oeffnungen.items():
        w = b.wand(seite, dicke)
        FA.wandscheibe(b.bm, w, g["zg"], top, ops, rnd, S["Fassade"], S["InnenWand"],
                       zacken=(zacken or {}).get(seite, ()))
    for k, zf in enumerate(geschosse):
        if boden:
            bm_mat = boden[min(k, len(boden) - 1)]
        else:
            bm_mat = rnd.choice([S["InnenBoden"], S["Teppich"], S["InnenBoden"], S["Fliesen"]])
        b.box(dicke, dicke, W - dicke, D - dicke, zf - 0.25, zf, S["InnenDecke"], top=bm_mat)
    if kern and W > 11 and D > 11:
        e = 4.2
        b.box(e, e, W - e, D - e, geschosse[0], top - 0.3, S["InnenWand"], top=S["InnenDecke"])


def dach_flach(b, g, top, attika, ausschnitt=None, dicke=0.3):
    """Flachdach (Bitumen) mit Attika und Betonabdeckung; ausschnitt = (u0,v0,u1,v1) eingestuerzt."""
    W, D = b.r.W, b.r.D
    if ausschnitt:
        u0, v0, u1, v1 = ausschnitt
        teile = [(0, 0, u0, D), (u1, 0, W, D), (u0, v1, u1, D), (u0, 0, u1, v0)]
    else:
        teile = [(0, 0, W, D)]
    teile = [(max(a, dicke), max(c, dicke), min(d, W - dicke), min(e, D - dicke)) for (a, c, d, e) in teile]
    for (a, c, d, e) in teile:
        if d - a > 0.05 and e - c > 0.05:
            b.box(a, c, d, e, top - 0.3, top, S["InnenDecke"], top=S["Dach"])
    if attika > 0:
        t = 0.3
        for (a, c, d, e) in ((0, 0, W, t), (0, D - t, W, D), (0, t, t, D - t), (W - t, t, W, D - t)):
            if ausschnitt and not (d <= ausschnitt[0] or a >= ausschnitt[2] or e <= ausschnitt[1] or c >= ausschnitt[3]):
                continue
            b.box(a, c, d, e, top, top + attika, S["Fassade"], top=S["Beton"])
            b.box(a - 0.03, c - 0.03, d + 0.03, e + 0.03, top + attika, top + attika + 0.06, S["Beton"])


def dachtechnik(b, top, rnd, anzahl=2, schornstein=False):
    W, D = b.r.W, b.r.D
    for k in range(anzahl):
        u, v = rnd.uniform(1.5, W - 2.6), rnd.uniform(2.0, D - 3.0)
        b.box(u, v, u + 1.2, v + 0.9, top, top + 0.95, S["Metall"])
        bm2 = bmesh.new()
        x, y = b.r.p(u + 0.6, v + 0.45)
        bmesh.ops.create_cone(bm2, cap_ends=True, segments=16, radius1=0.33, radius2=0.33, depth=0.04,
                              matrix=Matrix.Translation((x, y, top + 0.97)))
        b.mesh_einfuegen(bm2, S["Rost"])
    for k in range(rnd.randint(2, 4)):  # Lueftungsrohre mit Kappe
        u, v = rnd.uniform(1, W - 1), rnd.uniform(1, D - 1)
        x, y = b.r.p(u, v)
        bm2 = bmesh.new()
        r = rnd.uniform(0.05, 0.08)
        bmesh.ops.create_cone(bm2, cap_ends=True, segments=10, radius1=r, radius2=r, depth=0.9,
                              matrix=Matrix.Translation((x, y, top + 0.45)))
        bmesh.ops.create_cone(bm2, cap_ends=True, segments=10, radius1=r * 1.8, radius2=0.01, depth=0.12,
                              matrix=Matrix.Translation((x, y, top + 0.96)))
        b.mesh_einfuegen(bm2, S["Metall"])
    if rnd.random() < 0.5:  # Antenne
        u, v = rnd.uniform(2, W - 2), rnd.uniform(2, D - 2)
        b.box(u - 0.02, v - 0.02, u + 0.02, v + 0.02, top, top + rnd.uniform(2.5, 4.0), S["Metall"])
        for k in range(3):
            zz = top + 2.0 + k * 0.4
            b.box(u - 0.6 + k * 0.1, v - 0.01, u + 0.6 - k * 0.1, v + 0.01, zz, zz + 0.02, S["Metall"])
    if rnd.random() < 0.5:  # Satellitenschuessel
        u, v = rnd.uniform(1, W - 1.5), rnd.uniform(1, D - 1.5)
        x, y = b.r.p(u, v)
        bm2 = bmesh.new()
        bmesh.ops.create_uvsphere(bm2, u_segments=16, v_segments=8, radius=0.45)
        for vv in bm2.verts:
            vv.co.z = max(vv.co.z, 0.25)
        bmesh.ops.transform(bm2, verts=bm2.verts, matrix=Matrix.Translation((x, y, top + 1.0)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z") @ Matrix.Rotation(math.radians(60), 4, "X"))
        b.mesh_einfuegen(bm2, S["Lack"])
        b.box(u - 0.03, v - 0.03, u + 0.03, v + 0.03, top, top + 0.9, S["Metall"])
    if schornstein:
        u, v = rnd.uniform(1, W - 1.8), D - rnd.uniform(1.5, 3)
        b.box(u, v, u + 0.8, v + 0.6, top - 0.3, top + 1.8, S["Fassade"], top=S["Beton"])


def fenster_reihe(b, w, sills, breite, hoehe, abstand, rand, g, rnd, ac_anteil=0.0, aus=None, eg_index=0,
                  sturz=True, vorhaenge=0.35, rahmen=None, nah=True, sperr=()):
    """Oeffnungen + Fenster einer Wand; gibt Oeffnungsliste zurueck."""
    L = w.s1 - w.s0
    ops = []
    for k, sill in enumerate(sills):
        for sc in FA.fensterraster(L, breite, abstand, rand, w.s0):
            if aus and any(a <= sc <= c for a, c in aus if k == eg_index):
                continue
            o = {"s0": sc - breite / 2, "s1": sc + breite / 2, "z0": sill, "z1": sill + hoehe}
            if any(not (o["s1"] + 0.3 <= q["s0"] or o["s0"] - 0.3 >= q["s1"] or o["z1"] + 0.3 <= q["z0"] or o["z0"] - 0.3 >= q["z1"]) for q in sperr):
                continue
            zust = FA.fensterzustand(rnd, g["zerstoerung"], ist_eg=(k == eg_index))
            if g.get("brand") and k >= len(sills) - 3:
                zust = rnd.choice(["ausgebrannt", "fehlt", "zerbrochen"])
            ac = rnd.random() < ac_anteil and k > 0 and zust not in ("vernagelt", "ausgebrannt")
            FA.fenster(b.bm, w, o, zust, rnd, rahmen_mat=rahmen, ac=ac)
            if ac and rnd.random() < 0.15:  # heruntergefallenes Klimageraet
                b.boden_teile.append((w.welt(sc + rnd.uniform(-0.6, 0.6), -rnd.uniform(0.8, 2.2), 0), "klimageraet"))
            if zust in ("zerbrochen", "fehlt"):
                b.boden_teile.append((w.welt(sc, -0.6, 0), "glas"))
            if nah and zust not in ("vernagelt", "ausgebrannt") and rnd.random() < vorhaenge:
                FA.vorhang(b.bm, w, o, rnd)
            if sturz:
                FA.box_welt(b.bm, w, o["s0"] - 0.1, o["s1"] + 0.1, -0.015, 0.0, o["z1"], o["z1"] + 0.22, S["Fassade"])
            if zust == "ausgebrannt" or (g["zerstoerung"] != "leicht" and zust == "fehlt" and rnd.random() < 0.25):
                b.decal(w, o["s0"] - 0.35, o["s1"] + 0.35, o["z1"] - 0.3, o["z1"] + rnd.uniform(1.6, 2.8), 0)
            ops.append(o)
    return ops


def feuertreppe(b, w, s0, geschosse_z, rnd, haengend=False, breite=3.0, tiefe=1.15):
    """Feuertreppe aus Metall: Podest (Gitterrost), Gelaender mit Staeben, Leiter mit Sprossen."""
    for k, zf in enumerate(geschosse_z):
        if haengend and k == len(geschosse_z) - 1:
            # abgerissenes Podest haengt schraeg an einer Seite
            FA.schiefe_box(b.bm, w, s0, s0 + breite, -tiefe, -0.05, zf - 0.05, zf, S["Gelaender"], winkel=math.radians(35),
                           cent=Vector((s0, -tiefe / 2, zf)))
            continue
        FA.box_welt(b.bm, w, s0, s0 + breite, -tiefe, 0, zf - 0.05, zf, S["Gelaender"])
        FA.box_welt(b.bm, w, s0, s0 + breite, -tiefe, -tiefe + 0.04, zf + 0.92, zf + 0.96, S["Gelaender"])
        FA.box_welt(b.bm, w, s0, s0 + 0.04, -tiefe, 0, zf + 0.92, zf + 0.96, S["Gelaender"])
        FA.box_welt(b.bm, w, s0 + breite - 0.04, s0 + breite, -tiefe, 0, zf + 0.92, zf + 0.96, S["Gelaender"])
        n = int(breite / 0.12)
        for i in range(n + 1):
            ss = s0 + breite * i / n
            FA.box_welt(b.bm, w, ss - 0.008, ss + 0.008, -tiefe, -tiefe + 0.016, zf, zf + 0.92, S["Gelaender"])
        # Leiter zum naechsten Podest darunter
        ls = s0 + breite - 0.55
        unten = zf - (geschosse_z[1] - geschosse_z[0] if len(geschosse_z) > 1 else 3.2)
        for dz in (0.0,):
            FA.box_welt(b.bm, w, ls, ls + 0.03, -0.75, -0.72, unten, zf, S["Gelaender"])
            FA.box_welt(b.bm, w, ls + 0.42, ls + 0.45, -0.75, -0.72, unten, zf, S["Gelaender"])
        z = unten + 0.3
        while z < zf:
            FA.box_welt(b.bm, w, ls, ls + 0.45, -0.745, -0.725, z, z + 0.02, S["Gelaender"])
            z += 0.3


# ------------------------------------------------------------------ Typ 1: Wohnhaus Ziegel
def typ1(b, g, rnd):
    W, D = b.r.W, b.r.D
    n = g["geschosse"]
    stufen = rnd.randint(3, 5)
    eg = b.z0 + stufen * 0.17
    top = eg + n * 3.2
    geschosse = [eg + k * 3.2 for k in range(n)]
    sills = [z + 0.9 for z in geschosse]
    tuer = (W / 2 - 0.55, W / 2 + 0.55)
    heli = g.get("name") == "Wohnhaus_Hubschrauber"
    schwer = g["zerstoerung"] == "schwer" and not heli
    gross, ausschnitt = [], None
    if heli:  # Einschlagloch fuer den Hubschrauber im 2. OG (Phase 3)
        gross.append({"s0": W * 0.18, "s1": W * 0.82, "z0": eg + 2 * 3.2 - 0.6, "z1": eg + 3 * 3.2 - 0.25})
    if schwer:
        links = rnd.random() < 0.5
        bw = W * rnd.uniform(0.3, 0.42)
        u0, u1 = (0, bw) if links else (W - bw, W)
        gross.append({"s0": u0 - (1 if links else 0), "s1": u1 + (0 if links else 1), "z0": top - rnd.uniform(1.8, 3.6), "z1": top + 1})
        ausschnitt = (u0, 0, u1, rnd.uniform(3, 5))
        b.schiefe_platte(u0 + 0.4, u1 - 0.4, 0.6, top - 3.2 - 0.2, -1.2, top - 3.2 - 2.4, 0.22, S["Beton"])
        b.schuttkegel((u0 + u1) / 2, -1.8, rnd.uniform(2.2, 3.2), rnd.uniform(0.9, 1.4), rnd)
    ops = {}
    for seite in ("vorne", "hinten", "links", "rechts"):
        w = b.wand(seite)
        aus = [(tuer[0] - 0.7, tuer[1] + 0.7)] if seite == "vorne" else None
        ops[seite] = fenster_reihe(b, w, sills, 0.9, 1.5, 2.6, 0.9, g, rnd, ac_anteil=0.2, aus=aus,
                                   rahmen=S["Rahmen"], sperr=gross if seite == "vorne" else ())
    wv = b.wand("vorne")
    ops["vorne"].append({"s0": tuer[0], "s1": tuer[1], "z0": eg, "z1": eg + 2.3})
    _tuer(b, wv, tuer[0], tuer[1], eg, eg + 2.3, rnd)
    ops["vorne"] += gross
    zacken = {"vorne": list(range(len(ops["vorne"]) - len(gross), len(ops["vorne"])))}
    huelle(b, g, geschosse, top, ops, zacken=zacken)
    b.box(-0.04, -0.04, W + 0.04, D + 0.04, g["zg"], b.z0 + 0.35, S["Beton"])  # Sockel
    for k in range(1, n):  # Gurtgesimse
        b.box(-0.05, -0.05, W + 0.05, 0.0, eg + k * 3.2 - 0.1, eg + k * 3.2 + 0.08, S["Beton"])
    b.box(-0.3, -0.3, W + 0.3, 0.3, top - 0.45, top - 0.05, S["Beton"])
    dach_flach(b, g, top, g["attika"], ausschnitt)
    for k in range(stufen):  # Treppe 3-5 Stufen
        b.box(tuer[0] - 0.5, -0.3 * (stufen - k), tuer[1] + 0.5, 0.0, b.z0 - 0.1, b.z0 + 0.17 * (k + 1), S["Beton"])
    b.box(tuer[0] - 0.7, -1.3, tuer[1] + 0.7, 0.0, eg + 2.6, eg + 2.75, S["Beton"])  # Vordach
    b.box(tuer[1] + 0.25, -0.16, tuer[1] + 0.85, -0.02, eg + 0.9, eg + 1.7, S["Metall"])  # Briefkastenanlage
    seite = "vorne" if W >= 10 else "rechts"
    wf = b.wand(seite)
    feuertreppe(b, wf, (wf.s0 + 1.0), geschosse[1:], rnd, haengend=g["zerstoerung"] == "schwer")
    dachtechnik(b, top, rnd, anzahl=rnd.randint(1, 3), schornstein=True)
    if rnd.random() < 0.45:
        b.graffiti(wv, rnd.uniform(1.5, W - 1.5), b.z0 + 1.4, rnd.choice(GRAFFITI), rnd.uniform(0.35, 0.55), rnd.randint(1, 3))


def _ops_bereinigen(ops):
    """Fenster, die von einer grossen Oeffnung ueberdeckt werden, entfernen."""
    gross = [o for o in ops if o["s1"] - o["s0"] > 3]
    keep = []
    for o in ops:
        if o in gross or not any(not (o["s1"] <= gg["s0"] or o["s0"] >= gg["s1"] or o["z1"] <= gg["z0"] or o["z0"] >= gg["z1"]) for gg in gross):
            keep.append(o)
    ops[:] = keep


def _tuer(b, w, s0, s1, z0, z1, rnd, offen=None):
    """Tuer: Zarge + Blatt (offen, angelehnt oder fehlend)."""
    for (a, c, d, e) in [(s0, s0 + 0.08, z0, z1), (s1 - 0.08, s1, z0, z1), (s0, s1, z1 - 0.08, z1)]:
        FA.box_welt(b.bm, w, a, c, 0.12, 0.2, d, e, S["Rahmen"])
    zust = offen or rnd.choice(["zu", "offen", "offen", "fehlt"])
    if zust == "fehlt":
        return
    ang = 0 if zust == "zu" else rnd.uniform(0.4, 1.3)
    tmp = bmesh.new()
    V.box(tmp, 0, 0, z0 + 0.02, (s1 - s0) - 0.16, 0.045, z1 - 0.1)
    bmesh.ops.rotate(tmp, verts=tmp.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-ang, 3, "Z"))
    pts = []
    for f in tmp.faces:
        pts.append([w.welt(s0 + 0.08 + v.co.x, 0.16 + v.co.y, v.co.z) for v in f.verts])
    tmp.free()
    for vs in pts:
        f = b.bm.faces.new([b.bm.verts.new(p) for p in vs])
        f.material_index = S["Holz"]


# ------------------------------------------------------------------ Typ 3: Geschaeftshaus Main Street
def typ3(b, g, rnd):
    W, D = b.r.W, b.r.D
    n = g["geschosse"]
    z0 = b.z0
    eg = rnd.uniform(*g["cfg"]["eg_hoehe_typ3"])
    top = z0 + eg + (n - 1) * 3.2
    og = [z0 + eg + k * 3.2 for k in range(n - 1)]
    geschosse = [z0] + og
    p = 0.45
    ops = {"vorne": [], "hinten": [], "links": [], "rechts": []}
    wv = b.wand("vorne")
    gross, ausschnitt = [], None
    if g["zerstoerung"] == "schwer":
        links = rnd.random() < 0.5
        bw = W * rnd.uniform(0.35, 0.5)
        u0, u1 = (0, bw) if links else (W - bw, W)
        gross.append({"s0": u0 - (1 if links else 0), "s1": u1 + (0 if links else 1), "z0": top - rnd.uniform(1.6, 2.8), "z1": top + 1})
        ausschnitt = (u0, 0, u1, rnd.uniform(3, 6))
        b.schuttkegel((u0 + u1) / 2, -1.5, rnd.uniform(2.0, 2.8), rnd.uniform(0.8, 1.3), rnd)
    # Schaufensterzone: Oeffnung von 0,5 m bis 3,65 m
    sf = {"s0": p, "s1": W - p, "z0": z0 + 0.5, "z1": z0 + 3.65}
    ops["vorne"].append(sf)
    ops["vorne"] += fenster_reihe(b, wv, [z + 0.9 for z in og], 0.9, 1.55, 2.2 if W < 8 else 2.5, 0.8, g, rnd,
                                  eg_index=-1, rahmen=S["Rahmen"], sperr=gross)
    _schaufenster(b, wv, sf, g, rnd)
    wh = b.wand("hinten")
    ops["hinten"] += fenster_reihe(b, wh, [z + 0.9 for z in og], 0.9, 1.4, 2.6, 0.9, g, rnd, eg_index=-1)
    td = (W / 2 - 0.5, W / 2 + 0.5)
    ops["hinten"].append({"s0": td[0], "s1": td[1], "z0": z0, "z1": z0 + 2.2})
    _tuer(b, wh, td[0], td[1], z0, z0 + 2.2, rnd)
    for seite in ("links", "rechts"):
        if not g.get(f"nachbar_{seite}"):
            ops[seite] += fenster_reihe(b, b.wand(seite), [z + 0.9 for z in og], 0.9, 1.5, 2.6, 1.2, g, rnd, eg_index=-1)
    ops["vorne"] += gross
    zacken = {"vorne": list(range(len(ops["vorne"]) - len(gross), len(ops["vorne"])))}
    huelle(b, g, geschosse, top, ops, zacken=zacken, kern=False,
           boden=[S["Fliesen"]] + [rnd.choice([S["InnenBoden"], S["Teppich"]]) for _ in og])
    # Pilaster, Gesimse, Ziergesims
    for (a, c) in ((0, p), (W - p, W)):
        b.box(a, -0.08, c, 0, z0 - 0.05, z0 + eg - 0.1, S["Fassade"])
    for z in og[1:]:
        b.box(-0.04, -0.06, W + 0.04, 0, z - 0.12, z + 0.05, S["Beton"])
    b.box(-0.05, -0.45, W + 0.05, 0.2, top + g["attika"] - 0.5, top + g["attika"], S["Beton"])
    b.box(-0.02, -0.25, W + 0.02, 0.0, top + g["attika"] - 0.8, top + g["attika"] - 0.5, S["Fassade"])
    dach_flach(b, g, top, g["attika"], ausschnitt)
    # Schildband mit erfundenem Namen (verblasst, Buchstaben teils abgefallen)
    zs0, zs1 = z0 + 3.75, z0 + eg - 0.15
    b.box(p - 0.1, -0.12, W - p + 0.1, 0, zs0, zs1, S["Holz"])
    name = LADENNAMEN.get(g.get("laden", ""), "STORE")
    fehl = "".join(c if (c == " " or rnd.random() > 0.22) else " " for c in name)
    gr = min(0.42, (zs1 - zs0) * 0.6, (W - 2 * p) / max(len(name), 1) * 1.35)
    m = _wand_matrix(wv, W / 2, -0.125, (zs0 + zs1) / 2)
    V.text_mesh(b.bm, fehl, gr, m, S["Lack"], extrude=0.012)
    for i, c in enumerate(name):  # abgefallene Buchstaben liegen auf dem Gehweg
        if fehl[i] == " " and c != " ":
            b.boden_teile.append((wv.welt(rnd.uniform(1, W - 1), -rnd.uniform(0.5, 2.0), 0), "buchstabe:" + c))
    if rnd.random() < 0.6:
        _markise(b, wv, p, W - p, z0 + 3.68, g, rnd)
    if rnd.random() < 0.55 and n >= 2:
        feuertreppe(b, wh, W * 0.15, og, rnd, haengend=g["zerstoerung"] == "schwer", breite=min(3.0, W * 0.6))
    dachtechnik(b, top, rnd, anzahl=rnd.randint(1, 2))
    _ladeninnen(b, g, rnd, z0, z0 + eg - 0.25)
    if rnd.random() < 0.5:
        b.graffiti(wv, rnd.uniform(0.8, 2.0), z0 + 0.25, rnd.choice(GRAFFITI), 0.28, rnd.randint(1, 3))


def _schaufenster(b, w, o, g, rnd):
    """Schaufenster: Metallrahmen 20 cm zurueckgesetzt, Pfosten ~1,6 m, Kaempfer, Oberlicht, Tuer, Sockelpaneel."""
    s0, s1, z0, z1 = o["s0"], o["s1"], o["z0"], o["z1"]
    n0, t = 0.2, 0.07
    zk = z0 + 2.5
    felder = max(2, round((s1 - s0) / 1.6))
    xs = [s0 + (s1 - s0) * k / felder for k in range(felder + 1)]
    for x in xs:
        FA.box_welt(b.bm, w, x - 0.04, x + 0.04, n0, n0 + t, z0, z1, S["Metall"])
    for z in (z0, zk, z1 - 0.04):
        FA.box_welt(b.bm, w, s0, s1, n0, n0 + t, z, z + 0.06, S["Metall"])
    FA.box_welt(b.bm, w, s0 - 0.05, s1 + 0.05, -0.04, 0.0, z0 - 0.5 + 0.05, z0, S["Holz"])  # Sockelpaneel
    tuer_i = rnd.randrange(felder)
    geplndert = g["zerstoerung"] != "leicht" or rnd.random() < 0.6
    vernagelt = g["zerstoerung"] == "mittel" and rnd.random() < 0.35
    for k in range(felder):
        a, c = xs[k] + 0.04, xs[k + 1] - 0.04
        for (zu, zo) in ((z0 + 0.06, zk), (zk + 0.06, z1 - 0.04)):
            if k == tuer_i and zo <= zk + 0.01:
                continue
            zust = "fehlt" if (geplndert and rnd.random() < 0.6) else ("zerbrochen" if rnd.random() < 0.5 else "intakt")
            if zust == "intakt":
                _glas(b, w, a, c, zu, zo, n0 + t / 2)
            elif zust == "zerbrochen":
                for (cs, cz, ds, dz) in [(a, zu, 1, 1), (c, zu, -1, 1), (a, zo, 1, -1), (c, zo, -1, -1)]:
                    if rnd.random() < 0.6:
                        vs = [b.bm.verts.new(w.welt(s, n0 + t / 2, z)) for s, z in ((cs, cz), (cs + ds * rnd.uniform(0.1, 0.5), cz), (cs, cz + dz * rnd.uniform(0.15, 0.9)))]
                        f = b.bm.faces.new(vs)
                        f.material_index = S["Glas"]
                b.boden_teile.append((w.welt((a + c) / 2, -0.5, 0), "glas"))
            else:
                b.boden_teile.append((w.welt((a + c) / 2, -0.6, 0), "glas"))
    if vernagelt:  # Sperrholzplatten 1,22 x 2,44 m vor dem Schaufenster, teils fehlend
        x = s0 - 0.05
        while x < s1:
            if rnd.random() < 0.8:
                FA.schiefe_box(b.bm, w, x, min(x + 1.22, s1 + 0.05), -0.05, -0.03, z0 - 0.2, z0 + 2.3, S["Sperrholz"],
                               winkel=math.radians(rnd.uniform(-2.5, 2.5)))
            x += 1.24
    # Tuerblatt (Glastuer mit Metallrahmen), offen oder fehlend
    a, c = xs[tuer_i] + 0.04, xs[tuer_i + 1] - 0.04
    if rnd.random() < 0.6:
        tmp = bmesh.new()
        V.box(tmp, 0, 0, z0 - 0.45, (c - a), 0.05, zk - 0.05)
        bmesh.ops.rotate(tmp, verts=tmp.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-rnd.uniform(0.5, 1.4), 3, "Z"))
        pts = [[w.welt(a + v.co.x, n0 + v.co.y, v.co.z) for v in f.verts] for f in tmp.faces]
        tmp.free()
        for vs in pts:
            f = b.bm.faces.new([b.bm.verts.new(p) for p in vs])
            f.material_index = S["Metall"]


def _glas(b, w, a, c, zu, zo, n):
    vs = [b.bm.verts.new(w.welt(s, n, z)) for s, z in ((a, zu), (c, zu), (c, zo), (a, zo))]
    f = b.bm.faces.new(vs)
    f.material_index = S["Glas"]


def _markise(b, w, s0, s1, z_oben, g, rnd):
    """Stoffmarkise: Gestell (verbogen) + Stoff (zerrissen, Bahnen haengen herab)."""
    tiefe, fall = 1.6, 0.8
    nx, ny = max(4, int((s1 - s0) / 0.4)), 5
    riss = {"leicht": 0.1, "mittel": 0.3, "schwer": 0.5}[g["zerstoerung"]]
    for k in range(nx):
        sa, sb = s0 + (s1 - s0) * k / nx, s0 + (s1 - s0) * (k + 1) / nx
        haengt = rnd.random() < riss * 0.6
        for j in range(ny):
            if rnd.random() < riss * 0.5 and j > 1:
                continue
            ta, tb = j / ny, (j + 1) / ny
            pts = []
            for (s, t) in ((sa, ta), (sb, ta), (sb, tb), (sa, tb)):
                sack = 0.12 * math.sin(math.pi * (s - s0) / (s1 - s0)) * math.sin(math.pi * t)
                nn = -0.05 - tiefe * t
                z = z_oben - fall * t - sack
                if haengt and t > 0.4:
                    nn = -0.05 - tiefe * 0.4
                    z = z_oben - fall * 0.4 - (t - 0.4) * 1.6
                pts.append(w.welt(s, nn, z))
            f = b.bm.faces.new([b.bm.verts.new(p) for p in pts])
            f.material_index = S["Stoff"]
    verbogen = rnd.uniform(0, 0.25) if g["zerstoerung"] != "leicht" else 0
    for s in (s0 + 0.05, s1 - 0.05):
        FA.schiefe_box(b.bm, w, s - 0.015, s + 0.015, -tiefe - 0.05, -0.05, z_oben - fall - 0.02, z_oben - fall + 0.02,
                       S["Metall"], winkel=verbogen, cent=Vector((s, -0.05, z_oben)))
    FA.box_welt(b.bm, w, s0, s1, -tiefe - 0.07, -tiefe - 0.03, z_oben - fall - verbogen - 0.03, z_oben - fall - verbogen + 0.01, S["Metall"])


def _ladeninnen(b, g, rnd, z_boden, z_decke):
    """Geplunderter Laden: Regale (teils umgekippt), Theke, haengende Deckenlampen, Ware am Boden."""
    W, D = b.r.W, b.r.D
    for k in range(rnd.randint(2, 4)):
        v = 3.0 + k * rnd.uniform(2.5, 3.5)
        if v > D - 2:
            break
        l = rnd.uniform(1.8, W - 2.2)
        u = rnd.uniform(0.8, W - 0.8 - l)
        if rnd.random() < 0.4:  # umgekippt
            b.box(u, v, u + l, v + 1.8, z_boden, z_boden + 0.45, S["Holz"])
        else:
            b.box(u, v, u + l, v + 0.45, z_boden, z_boden + 1.8, S["Holz"])
            for h in (0.4, 0.9, 1.4):
                b.box(u, v - 0.05, u + l, v + 0.5, z_boden + h, z_boden + h + 0.03, S["Holz"])
    b.box(0.8, 1.4, 0.8 + min(3.0, W - 2), 2.0, z_boden, z_boden + 1.0, S["Holz"], top=S["Beton"])  # Theke
    for k in range(2):
        u, v = W * (0.3 + 0.4 * k), D * rnd.uniform(0.25, 0.6)
        hz = z_decke - rnd.uniform(0.6, 1.4)
        b.box(u - 0.01, v - 0.01, u + 0.01, v + 0.01, hz, z_decke, S["Metall"])
        b.box(u - 0.6, v - 0.12, u + 0.6, v + 0.12, hz - 0.08, hz, S["Metall"])
    for k in range(rnd.randint(6, 14)):  # Ware/Kartons am Boden
        u, v = rnd.uniform(0.6, W - 0.6), rnd.uniform(1.0, D - 1.0)
        s = rnd.uniform(0.15, 0.45)
        b.box(u, v, u + s, v + s * rnd.uniform(0.6, 1.3), z_boden, z_boden + s * rnd.uniform(0.4, 0.9), rnd.choice([S["Holz"], S["Stoff"], S["Lack"]]))


# ------------------------------------------------------------------ Material-Zuweisung
def slot_materialien(g):
    fas = g["fassade"]
    tint = None
    if fas in ("MAT_Holz_Verkleidung", "MAT_Ziegel_Gestrichen", "MAT_Putz"):
        tint = ["#FFFFFF", "#E4DCC6", "#C9D0D0", "#D3D6BE"][g["farbe"] % 4]
    fm = V.mat_variante(fas, g["farbe"], tint)
    dach = V.mat_schindeln() if g["typ"] == 2 else V.material("MAT_Flachdach_Bitumen")
    rahmen = V.material("MAT_Fensterrahmen_Holz") if g["typ"] in (1, 2, 8) else V.material("MAT_Metall_Rahmen")
    schutt = V.material("MAT_Ziegel_Verblasst") if ("Ziegel" in fas or g["typ"] == 2) else V.material("MAT_Beton_Grob")
    innen = V.material("MAT_Innen_Wand_Gruen") if g["farbe"] % 2 else V.material("MAT_Innen_Wand")
    lack = V.material(["MAT_Lack_Weiss", "MAT_Lack_Rot", "MAT_Lack_Gruen", "MAT_Lack_Gelb"][g["farbe"] % 4])
    stoff = V.material(["MAT_Markise_Gruen", "MAT_Markise_Rot", "MAT_Stoff_Plane", "MAT_Plane_Oliv"][g["farbe"] % 4])
    if g["typ"] == 6:
        stoff = V.material("MAT_Plane_Oliv")
    if g["typ"] == 5 and g.get("variante") == "glas":
        fm = V.material("MAT_Fensterrahmen_Dunkel")
    m = {
        "Fassade": fm, "Glas": V.mat_glas(), "Dach": dach, "Beton": V.material("MAT_Beton_Glatt"),
        "Holz": V.material("MAT_Holz_Bretter_Alt"), "Metall": V.material("MAT_Metall_Rahmen"), "Schutt": schutt,
        "InnenWand": innen, "InnenBoden": V.material("MAT_Holz_Planken"), "InnenDecke": V.material("MAT_Innen_Decke"),
        "Rahmen": rahmen, "Sperrholz": V.material("MAT_OSB" if g["farbe"] % 2 else "MAT_Sperrholz"), "Stoff": stoff,
        "Teppich": V.material("MAT_Teppich"), "Fliesen": V.material("MAT_Fliesen"), "Rost": V.material("MAT_Rost_Dunkel"),
        "Lack": lack, "Gelaender": V.material("MAT_Rost_Hell"), "Draht": V.mat_maschendraht(),
    }
    return [m[k] for k in FA.SLOT]


DEKO_MATS = None


def deko_materialien():
    return [V.mat_russ(), V.mat_farbe("MAT_Graffiti_Schwarz", "#1A1A1A", 0.35, "MAT_Beton_Grob", lokal=0.6),
            V.mat_farbe("MAT_Graffiti_Rot", "#7E1F1A", 0.35, "MAT_Beton_Grob", lokal=0.6),
            V.mat_farbe("MAT_Graffiti_Weiss", "#D9D4C8", 0.35, "MAT_Beton_Grob", lokal=0.6)]


# ------------------------------------------------------------------ Hauptfunktion
NEU = {1: typ1, 3: typ3}


def bauen():
    cfg = V.config("gebaeude.json")
    geb = P1.planen(cfg)
    # Nachbarn fuer Brandwaende (Typ 3 Reihen)
    for g in geb:
        x0, y0, x1, y1 = g["rechteck"]
        for o in geb:
            if o is g:
                continue
            a = o["rechteck"]
            ueberlapp_y = a[1] < y1 - 1 and a[3] > y0 + 1
            if ueberlapp_y and abs(a[2] - x0) < 0.6:
                g["nachbar_links" if g["front"] == "S" else "nachbar_rechts"] = True
            if ueberlapp_y and abs(a[0] - x1) < 0.6:
                g["nachbar_rechts" if g["front"] == "S" else "nachbar_links"] = True
    zaehler, ergebnis, boden_teile = {}, [], []
    for g in geb:
        rnd = random.Random(cfg["seed"] * 1000 + int(g["id"][1:]))
        g["cfg"] = cfg
        rahmen = P1.Rahmen(g["rechteck"], g["front"])
        x0, y0, x1, y1 = g["rechteck"]
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), ((x0 + x1) / 2, (y0 + y1) / 2)]
        z0 = V.h_max(pts) + 0.15
        g["zg"] = V.h_min(pts) - 0.3
        b = Bau2(rahmen, z0, rnd)
        if g["typ"] in NEU:
            NEU[g["typ"]](b, g, rnd)
        else:
            P1.BAUER[g["typ"]](b, g, rnd)
        tname = cfg["typnamen"][str(g["typ"])]
        zaehler[tname] = zaehler.get(tname, 0) + 1
        name = f"BLD_{g['name']}" if g.get("name") else f"BLD_{tname}_{zaehler[tname]:02d}"
        col = V.collection(f"03_Gebaeude/Typ{g['typ']}_{tname}")
        orig = Vector((x0, y0, z0))
        bmesh.ops.translate(b.bm, verts=b.bm.verts, vec=-orig)
        bmesh.ops.remove_doubles(b.bm, verts=b.bm.verts, dist=0.0005)
        ob = V.objekt_aus_bmesh(name, b.bm, col, location=orig, material=slot_materialien(g))
        V.fase(ob, 0.015, 2, winkel=35)
        for k in ("id", "typ", "geschosse", "zerstoerung", "fassade", "farbe", "attika", "front"):
            ob[k] = g[k]
        for k in ("laden", "brand", "kamera_dach", "variante"):
            if k in g:
                ob[k] = g[k]
        ob["hoehe_m"] = round(max(v.co.z for v in ob.data.vertices), 2)
        if len(b.deko.faces):
            bmesh.ops.translate(b.deko, verts=b.deko.verts, vec=-orig)
            d = V.objekt_aus_bmesh(name + "_Decals", b.deko, col, location=orig, material=deko_materialien(), uv=False)
            d.parent = ob
            d.location = (0, 0, 0)
            d.visible_shadow = False
        else:
            b.deko.free()
        boden_teile += [(p, art, g["id"]) for p, art in b.boden_teile]
        ergebnis.append(ob)
    bpy.app.driver_namespace["boden_teile"] = boden_teile
    print(f"GEBAEUDE2: {len(ergebnis)} Gebaeude, {len(boden_teile)} Bodenteile (Glas/Klimageraete/Buchstaben)")
    return ergebnis, boden_teile


# ------------------------------------------------------------------ Typ 2: Holzhaus mit Veranda
class Dachflaeche:
    """Geneigte Dachflaeche fuer FA.wandscheibe: s entlang Traufe, z = Weg von Traufe zum First, n = Dicke nach unten."""

    def __init__(self, p0, richtung_s, richtung_t, laenge_s, laenge_t, dicke=0.12):
        self.p0, self.es, self.et = Vector(p0), Vector(richtung_s).normalized(), Vector(richtung_t).normalized()
        self.nrm = self.es.cross(self.et).normalized()
        if self.nrm.z < 0:
            self.nrm = -self.nrm
        self.s0, self.s1, self.d = 0.0, laenge_s, dicke
        self.lt = laenge_t

    def welt(self, s, n, t):
        return self.p0 + self.es * s + self.et * t - self.nrm * n


def _dach_box(bm, dach, s0, s1, n0, n1, t0, t1, mat):
    c = [dach.welt(s, n, t) for s in (s0, s1) for n in (n0, n1) for t in (t0, t1)]
    idx = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    vs = [bm.verts.new(p) for p in c]
    for q in idx:
        try:
            f = bm.faces.new([vs[i] for i in q])
            f.material_index = mat
        except ValueError:
            pass


def typ2(b, g, rnd):
    W, D = b.r.W, b.r.D
    z0 = b.z0
    auf = rnd.uniform(*g["cfg"]["aufstaenderung_typ2"])
    n = g["geschosse"]
    ze = z0 + auf
    traufe = ze + n * 2.8
    d = 0.18
    zer = g["zerstoerung"]
    sills = [ze + k * 2.8 + 0.8 for k in range(n)]
    tuer = (W / 2 - 0.48, W / 2 + 0.48)
    ops = {}
    for seite in ("vorne", "hinten", "links", "rechts"):
        w = b.wand(seite, d)
        aus = [(tuer[0] - 0.6, tuer[1] + 0.6)] if seite in ("vorne", "hinten") else None
        ops[seite] = fenster_reihe(b, w, sills, 0.85, 1.4, 2.4 if seite == "vorne" else 2.8, 0.8, g, rnd,
                                   aus=aus, sturz=False, rahmen=S["Rahmen"], vorhaenge=0.45)
        for o in ops[seite]:  # Fensterlaeden (40 %)
            if rnd.random() < 0.4:
                for (a, c) in ((o["s0"] - 0.42, o["s0"] - 0.04), (o["s1"] + 0.04, o["s1"] + 0.42)):
                    if rnd.random() < 0.85:
                        FA.box_welt(b.bm, w, a, c, -0.04, 0.0, o["z0"], o["z1"], S["Lack"])
            FA.box_welt(b.bm, w, o["s0"] - 0.08, o["s1"] + 0.08, -0.03, 0.0, o["z1"], o["z1"] + 0.12, S["Rahmen"])
    for seite in ("vorne", "hinten"):
        w = b.wand(seite, d)
        ops[seite].append({"s0": tuer[0], "s1": tuer[1], "z0": ze, "z1": ze + 2.1})
        _tuer(b, w, tuer[0], tuer[1], ze, ze + 2.1, rnd)
    for seite, o_list in ops.items():
        FA.wandscheibe(b.bm, b.wand(seite, d), ze - 0.12, traufe, o_list, rnd, S["Fassade"], S["InnenWand"], unebenheit=0.012)
    for k in range(n):
        b.box(d, d, W - d, D - d, ze + k * 2.8 - 0.2, ze + k * 2.8, S["InnenDecke"], top=rnd.choice([S["InnenBoden"], S["Teppich"]]))
    b.box(d, d, W - d, D - d, traufe - 0.2, traufe, S["InnenDecke"], top=S["InnenDecke"])
    # Kriechraum: Pfeiler + Lattengitter
    for (u, v) in [(0.15, 0.15), (W - 0.45, 0.15), (0.15, D - 0.45), (W - 0.45, D - 0.45), (W / 2, 0.15), (W / 2, D - 0.45)]:
        b.box(u, v, u + 0.3, v + 0.3, g["zg"], ze - 0.12, S["Schutt"])
    for seite in ("vorne", "hinten", "links", "rechts"):
        w = b.wand(seite, d)
        L = w.s1 - w.s0
        k = 0
        x = w.s0 - auf
        while x < w.s1:
            for richt in (1, -1):
                if rnd.random() < (0.08 if zer == "leicht" else 0.25):
                    continue
                a0 = x if richt > 0 else x + auf
                pts0 = [(a0, z0 + 0.02), (a0 + richt * auf, ze - 0.14)]
                (sa, za), (sb, zb) = pts0
                sa_c, sb_c = max(w.s0, min(w.s1, sa)), max(w.s0, min(w.s1, sb))
                if abs(sb_c - sa_c) < 0.05:
                    continue
                za_c = za + (zb - za) * ((sa_c - sa) / (sb - sa))
                zb_c = za + (zb - za) * ((sb_c - sa) / (sb - sa))
                vs = [w.welt(sa_c, -0.03, za_c), w.welt(sb_c, -0.03, zb_c), w.welt(sb_c, -0.03, zb_c + 0.04), w.welt(sa_c, -0.03, za_c + 0.04)]
                f = b.bm.faces.new([b.bm.verts.new(p) for p in vs])
                f.material_index = S["Holz"]
            x += 0.32
    # Dach: Satteldach 30-40 Grad, Ueberstand 40-60 cm, Schindeln, Loecher mit sichtbaren Sparren
    neig = math.radians(rnd.uniform(30, 40))
    ov = rnd.uniform(0.4, 0.6)
    first_u = rnd.random() < 0.5  # First parallel zur Strasse
    loch_p = {"leicht": 0.0, "mittel": 0.6, "schwer": 1.0}[zer]
    if first_u:
        halb, laenge = D / 2, W
        hoch = halb * math.tan(neig)
        b.prisma(0, W, 0, D, traufe, traufe + hoch, True, S["Fassade"])
        seiten = [((-ov, -ov), (1, 0), (0, 1)), ((W + ov, D + ov), (-1, 0), (0, -1))]
    else:
        halb, laenge = W / 2, D
        hoch = halb * math.tan(neig)
        b.prisma(0, W, 0, D, traufe, traufe + hoch, False, S["Fassade"])
        seiten = [((W + ov, -ov), (0, 1), (-1, 0)), ((-ov, D + ov), (0, -1), (1, 0))]
    lt = (halb + ov) / math.cos(neig)
    for (pu, pv), (su, sv), (tu, tv) in seiten:
        p0 = Vector((*b.r.p(pu, pv), traufe - ov * math.tan(neig) + 0.12))
        e_s = Vector((*b.r.p(pu + su, pv + sv), 0)) - Vector((*b.r.p(pu, pv), 0))
        e_t_h = Vector((*b.r.p(pu + tu, pv + tv), 0)) - Vector((*b.r.p(pu, pv), 0))
        e_t = e_t_h.normalized() * math.cos(neig) + Vector((0, 0, math.sin(neig)))
        dach = Dachflaeche(p0, e_s, e_t, laenge + 2 * ov, lt + 0.05)
        loecher = []
        if rnd.random() < loch_p:
            for k in range(1 if zer == "mittel" else rnd.randint(1, 2)):
                sa = rnd.uniform(1.0, laenge - 2.0)
                ta = rnd.uniform(0.8, lt - 2.0)
                loecher.append({"s0": sa, "s1": sa + rnd.uniform(1.0, 2.4), "z0": ta, "z1": ta + rnd.uniform(0.8, 1.8)})
        FA.wandscheibe(b.bm, dach, 0.0, lt, loecher, rnd, S["Dach"], S["Holz"], unebenheit=0.03 if zer != "leicht" else 0.012,
                       zacken=range(len(loecher)))
        for o in loecher:  # Sparren unter dem Loch
            sc = o["s0"] - 0.2
            while sc < o["s1"] + 0.2:
                _dach_box(b.bm, dach, sc - 0.025, sc + 0.025, 0.12, 0.26, 0.0, lt, S["Holz"])
                sc += 0.6
        # Dachrinne an der Traufe (teils abgerissen)
        hangt = rnd.random() < (0.15 if zer == "leicht" else 0.5)
        n_seg = 3
        for k in range(n_seg):
            sa, sb = (laenge + 2 * ov) * k / n_seg, (laenge + 2 * ov) * (k + 1) / n_seg
            if hangt and k == n_seg - 1:
                pa, pb = dach.welt(sa, 0.05, -0.05), dach.welt(sb, 0.05, -0.05) + Vector((0, 0, -1.8))
            else:
                pa, pb = dach.welt(sa, 0.05, -0.05), dach.welt(sb, 0.05, -0.05)
            _rohr(b, pa, pb, 0.06, S["Metall"], seg=6)
    # Fallrohre (D 10 cm) an zwei Ecken
    for (u, v) in ((-0.1, -0.1), (W + 0.1, -0.1)):
        x, y = b.r.p(u, v)
        oben = traufe - 0.1
        _rohr(b, Vector((x, y, z0 + 0.2)), Vector((x, y, oben)), 0.05, S["Metall"], seg=8)
    b.box(W * 0.7, D * 0.6, W * 0.7 + 0.6, D * 0.6 + 0.6, ze, traufe + hoch + 0.9, S["Schutt"], top=S["Beton"])  # Schornstein
    _veranda(b, g, rnd, ze, auf)
    _grundstueck2(b, g, rnd)


def _rohr(b, pa, pb, r, mat, seg=8):
    d = pb - pa
    if d.length < 1e-3:
        return
    bm2 = bmesh.new()
    m = Matrix.Translation((pa + pb) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.create_cone(bm2, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length, matrix=m)
    b.mesh_einfuegen(bm2, mat)


def _veranda(b, g, rnd, ze, auf):
    """Veranda ueber die ganze Front: Dielen, Pfosten alle ~2,5 m, Gelaender 0,9 m mit Staeben, Dach durchhaengend,
    Treppe, Fliegengittertuer (zerrissen), Hollywoodschaukel."""
    W = b.r.W
    zer = g["zerstoerung"]
    b.box(0, -2.4, W, 0, ze - 0.2, ze - 0.05, S["Holz"])
    for k in range(int(W / 0.14)):  # Dielen
        u = k * 0.14
        if zer != "leicht" and rnd.random() < 0.04:
            continue
        b.box(u + 0.005, -2.4, u + 0.135, 0, ze - 0.05, ze, S["InnenBoden"])
    npf = max(2, int(round(W / 2.5)) + 1)
    sack = {"leicht": 0.1, "mittel": 0.3, "schwer": 0.55}[zer]
    pf = [0.1 + (W - 0.2) * k / (npf - 1) for k in range(npf)]
    fehlt = rnd.randrange(npf) if zer == "schwer" else -1
    for k, u in enumerate(pf):
        if k == fehlt:
            b.schiefe_platte(u - 0.07, u + 0.07, -2.3, ze + 0.1, -4.6, ze - auf + 0.15, 0.12, S["Holz"])
            continue
        b.box(u - 0.07, -2.32, u + 0.07, -2.18, ze, ze + 2.55 - (sack if 0 < k < npf - 1 else 0) * 0.6, S["Rahmen"])
    for k in range(npf - 1):
        a, c = pf[k] + 0.07, pf[k + 1] - 0.07
        if abs((a + c) / 2 - W / 2) < 1.0:
            continue
        b.box(a, -2.28, c, -2.22, ze + 0.86, ze + 0.92, S["Rahmen"])
        b.box(a, -2.28, c, -2.22, ze + 0.1, ze + 0.14, S["Rahmen"])
        x = a + 0.06
        while x < c - 0.04:
            if not (zer != "leicht" and rnd.random() < 0.12):
                b.box(x, -2.26, x + 0.035, -2.235, ze + 0.14, ze + 0.86, S["Rahmen"])
            x += 0.12
    b.schiefe_platte(-0.2, W + 0.2, 0, ze + 2.95, -2.65, ze + 2.6 - sack, 0.1, S["Dach"])
    stufen = max(3, int(round(auf / 0.18)))
    for k in range(stufen):
        b.box(W / 2 - 0.7, -2.4 - 0.28 * (stufen - k), W / 2 + 0.7, -2.4, b.z0 - 0.1, b.z0 + (auf / stufen) * (k + 1), S["Holz"])
    # Fliegengittertuer vor der Haustuer, Gitter zerrissen (Teilflaechen)
    w = b.wand("vorne", 0.18)
    t0, t1 = W / 2 - 0.48, W / 2 + 0.48
    for (a, c, d1, e) in [(t0, t0 + 0.05, ze, ze + 2.1), (t1 - 0.05, t1, ze, ze + 2.1), (t0, t1, ze + 2.05, ze + 2.1), (t0, t1, ze + 1.0, ze + 1.05)]:
        FA.box_welt(b.bm, w, a, c, -0.12, -0.09, d1, e, S["Rahmen"])
    for (zu, zo) in ((ze + 0.05, ze + 1.0), (ze + 1.05, ze + 2.05)):
        if rnd.random() < 0.5:
            vs = [b.bm.verts.new(w.welt(s, -0.105, z)) for s, z in ((t0 + 0.05, zu), (t1 - 0.05, zu), (t1 - 0.05, zo - rnd.uniform(0, 0.5)), (t0 + 0.05, zo))]
            f = b.bm.faces.new(vs)
            f.material_index = S["Metall"]
    # Hollywoodschaukel (an Ketten unter dem Verandadach)
    if rnd.random() < 0.6:
        u0 = rnd.choice([0.6, W - 2.4])
        zs = ze + 0.45
        b.box(u0, -1.2, u0 + 1.6, -0.7, zs, zs + 0.06, S["Holz"])
        b.box(u0, -0.75, u0 + 1.6, -0.7, zs, zs + 0.5, S["Holz"])
        for u in (u0 + 0.05, u0 + 1.55):
            b.box(u - 0.006, -0.96, u + 0.006, -0.95, zs, ze + 2.8 - sack * 0.5, S["Rost"])


# ------------------------------------------------------------------ Typ 5: Buerogebaeude
def typ5(b, g, rnd):
    W, D = b.r.W, b.r.D
    n = g["geschosse"]
    z0 = b.z0
    top = z0 + n * 3.8
    glas = g.get("variante") == "glas"
    geschosse = [z0 + k * 3.8 for k in range(n)]
    ops = {}
    for seite in ("vorne", "hinten", "links", "rechts"):
        w = b.wand(seite)
        L = w.s1 - w.s0
        o_list = []
        for k, zf in enumerate(geschosse):
            if k == 0:
                o = {"s0": w.s0 + 1.0, "s1": w.s1 - 1.0, "z0": zf + 0.3, "z1": zf + 3.4}
            elif glas:
                o = {"s0": w.s0 + 0.15, "s1": w.s1 - 0.15, "z0": zf + 0.05, "z1": zf + 3.45}
            else:
                o = {"s0": w.s0 + 0.6, "s1": w.s1 - 0.6, "z0": zf + 1.0, "z1": zf + 2.7}
            o_list.append(o)
            _modulfassade(b, w, o, g, rnd, k, n)
        ops[seite] = o_list
    huelle(b, g, geschosse, top, ops, kern=True,
           boden=[S["Fliesen"]] + [S["Schutt"] if (g.get("brand") and k >= n - 3) else S["Teppich"] for k in range(1, n)])
    for k in range(1, n):  # Deckenstirn/Bruestungsband
        zf = z0 + k * 3.8
        b.box(-0.03, -0.03, W + 0.03, 0.0, zf - 0.3, zf + (0.05 if glas else 0.95), S["Metall"] if glas else S["Beton"])
        b.box(-0.03, D, W + 0.03, D + 0.03, zf - 0.3, zf + (0.05 if glas else 0.95), S["Metall"] if glas else S["Beton"])
    dach_flach(b, g, top, 1.1)
    b.box(W / 2 - 4, -3.5, W / 2 + 4, 0, z0 + 4.0, z0 + 4.35, S["Beton"])
    for uu in (W / 2 - 3.6, W / 2 + 3.6):
        b.box(uu - 0.12, -3.3, uu + 0.12, -3.06, z0, z0 + 4.0, S["Metall"])
    bm2 = bmesh.new()  # Drehtuer-Gehaeuse
    x, y = b.r.p(W / 2, -0.2)
    bmesh.ops.create_cone(bm2, cap_ends=True, segments=20, radius1=1.2, radius2=1.2, depth=2.5, matrix=Matrix.Translation((x, y, z0 + 1.25)))
    b.mesh_einfuegen(bm2, S["Glas"])
    if not g.get("kamera_dach"):
        b.box(W * 0.35, D * 0.35, W * 0.65, D * 0.65, top, top + 3.2, S["Beton"], top=S["Dach"])
    dachtechnik(b, top, rnd, anzahl=3)
    if g.get("brand"):  # Russ ueber mehrere Etagen
        for seite in ("vorne", "rechts"):
            w = b.wand(seite)
            for k in range(n - 3, n):
                zf = z0 + k * 3.8
                for j in range(rnd.randint(2, 4)):
                    sc = rnd.uniform(w.s0 + 2, w.s1 - 2)
                    b.decal(w, sc - rnd.uniform(1.2, 2.5), sc + rnd.uniform(1.2, 2.5), zf + 1.6, zf + 1.6 + rnd.uniform(2.5, 4.5), 0)


def _modulfassade(b, w, o, g, rnd, k, n):
    """Raster 1,5 m: Pfosten, Scheiben (viele fehlend), Jalousien haengen heraus."""
    s0, s1, z0, z1 = o["s0"], o["s1"], o["z0"], o["z1"]
    mods = max(1, round((s1 - s0) / 1.5))
    xs = [s0 + (s1 - s0) * i / mods for i in range(mods + 1)]
    n0 = 0.12
    for x in xs:
        FA.box_welt(b.bm, w, x - 0.03, x + 0.03, n0, n0 + 0.1, z0, z1, S["Metall"])
    FA.box_welt(b.bm, w, s0, s1, n0, n0 + 0.1, z0, z0 + 0.06, S["Metall"])
    FA.box_welt(b.bm, w, s0, s1, n0, n0 + 0.1, z1 - 0.06, z1, S["Metall"])
    fehl = {"leicht": 0.25, "mittel": 0.45, "schwer": 0.65}[g["zerstoerung"]]
    if g.get("brand") and k >= n - 3:
        fehl = 0.85
    for i in range(mods):
        a, c = xs[i] + 0.03, xs[i + 1] - 0.03
        x = rnd.random()
        if x < fehl:
            if rnd.random() < 0.12:  # Jalousie haengt heraus
                vs = [w.welt(a + 0.1, n0 - 0.05, z1 - 0.1), w.welt(c - 0.1, n0 - 0.05, z1 - 0.1),
                      w.welt(c - 0.15, -rnd.uniform(0.3, 0.8), z1 - rnd.uniform(1.2, 2.2)), w.welt(a + 0.1, -rnd.uniform(0.2, 0.6), z1 - rnd.uniform(1.0, 2.0))]
                f = b.bm.faces.new([b.bm.verts.new(p) for p in vs])
                f.material_index = S["Lack"]
            b.boden_teile.append((w.welt((a + c) / 2, -rnd.uniform(0.5, 3.0), 0), "glas"))
        elif x < fehl + 0.12:
            for (cs, cz, ds, dz) in [(a, z0 + 0.06, 1, 1), (c, z1 - 0.06, -1, -1)]:
                vs = [b.bm.verts.new(w.welt(s, n0 + 0.05, z)) for s, z in ((cs, cz), (cs + ds * rnd.uniform(0.2, 0.9), cz), (cs, cz + dz * rnd.uniform(0.3, 1.5)))]
                f = b.bm.faces.new(vs)
                f.material_index = S["Glas"]
        else:
            _glas(b, w, a, c, z0 + 0.06, z1 - 0.06, n0 + 0.05)
            if rnd.random() < 0.35:  # Jalousie innen, schief
                vs = [w.welt(a, 0.35, z1 - 0.1), w.welt(c, 0.35, z1 - 0.1), w.welt(c, 0.38, z1 - rnd.uniform(0.5, 2.0)), w.welt(a, 0.38, z1 - rnd.uniform(0.3, 1.5))]
                f = b.bm.faces.new([b.bm.verts.new(p) for p in vs])
                f.material_index = S["Lack"]


# ------------------------------------------------------------------ Typ 6 / 8 / 4 / 7 (Erweiterungen)
def typ6(b, g, rnd):
    W, D = b.r.W, b.r.D
    n = g["geschosse"]
    z0 = b.z0
    top = z0 + n * 4.0
    geschosse = [z0 + k * 4.0 for k in range(n)]
    ops = {}
    for seite in ("vorne", "hinten", "links", "rechts"):
        w = b.wand(seite)
        ops[seite] = fenster_reihe(b, w, [z + 1.0 for z in geschosse], 1.6, 1.6, 3.2, 1.2, g, rnd, sturz=False,
                                   aus=[(6, 22)] if seite == "vorne" else None, vorhaenge=0.5)
    w = b.wand("vorne")
    ops["vorne"].append({"s0": 9.0, "s1": 19.0, "z0": z0 + 0.1, "z1": z0 + 3.2})  # Notaufnahme-Eingang
    huelle(b, g, geschosse, top, ops)
    dach_flach(b, g, top, 1.0)
    for k in range(1, n):
        b.box(-0.03, -0.03, W + 0.03, 0, z0 + k * 4.0 - 0.25, z0 + k * 4.0 + 0.1, S["Beton"])
    b.box(6, -9, 22, 0, z0 + 4.5, z0 + 5.1, S["Beton"])
    for uu in (6.5, 21.5):
        for vv in (-8.5, -3):
            b.box(uu - 0.2, vv - 0.2, uu + 0.2, vv + 0.2, z0, z0 + 4.5, S["Metall"])
    m = Matrix.Translation((*b.r.p(14.0, -9.06), z0 + 4.8)) @ _richtung_matrix(b, "vorne")
    V.text_mesh(b.bm, "EMERGENCY", 0.6, m, S["Lack"], extrude=0.02)
    # Landeplatz-Markierung (verblasst)
    x, y = b.r.p(W * 0.7, D * 0.5)
    bm2 = bmesh.new()
    bmesh.ops.create_circle(bm2, cap_ends=False, segments=48, radius=7.0)
    ring = bmesh.ops.extrude_edge_only(bm2, edges=list(bm2.edges))
    for v in [e for e in ring["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co *= 7.5 / 7.0
    bmesh.ops.translate(bm2, verts=bm2.verts, vec=(x, y, top + 0.02))
    b.mesh_einfuegen(bm2, S["Lack"])
    V.text_mesh(b.bm, "H", 6.0, Matrix.Translation((x, y, top + 0.025)), S["Lack"], extrude=0.0)
    for k, uu in enumerate((26, 33, 40)):  # Zelte mit durchhaengender Plane
        b.box(uu, -14, uu + 5, -9, z0, z0 + 1.6, S["Stoff"])
        b.prisma(uu, uu + 5, -14, -9, z0 + 1.6, z0 + 3.0 - rnd.uniform(0, 0.4), False, S["Stoff"])
    for k in range(6):  # Absperrgitter
        uu = 4 + k * 2.6
        b.box(uu, -16.0, uu + 2.4, -15.95, z0, z0 + 1.1, S["Metall"])
    dachtechnik(b, top, rnd, anzahl=4)


def _richtung_matrix(b, seite):
    """Rotation fuer Texte, die von der Strassenseite lesbar sind."""
    w = b.wand(seite)
    p = w.welt(0, 0, 0)
    ex = (w.welt(1, 0, 0) - p).normalized()
    ez = (w.welt(0, -1, 0) - p).normalized()
    return Matrix((ex, Vector((0, 0, 1)), ez)).transposed().to_4x4()


def typ8(b, g, rnd):
    art = g.get("art")
    if art in ("schule", "feuerwache"):
        W, D = b.r.W, b.r.D
        z0 = b.z0
        top = z0 + 7.0
        geschosse = [z0, z0 + 3.5]
        ops = {}
        for seite in ("vorne", "hinten", "links", "rechts"):
            w = b.wand(seite)
            if art == "feuerwache" and seite == "vorne":
                ops[seite] = fenster_reihe(b, w, [z0 + 4.5], 1.0, 1.4, 2.6, 1.0, g, rnd)
                for k in range(3):
                    uu = 2.0 + k * 4.8
                    ops[seite].append({"s0": uu, "s1": uu + 3.6, "z0": z0, "z1": z0 + 4.2})
                    offen = rnd.random() < 0.45
                    zt = z0 + (4.2 if offen else rnd.uniform(0.0, 2.5))
                    FA.box_welt(b.bm, w, uu, uu + 3.6, 0.1, 0.16, zt, z0 + 4.2, S["Lack"])
            else:
                ops[seite] = fenster_reihe(b, w, [z0 + 0.9, z0 + 4.4], 1.4, 1.6, 2.4, 1.2, g, rnd,
                                           aus=[(W / 2 - 2.5, W / 2 + 2.5)] if seite == "vorne" else None)
        if art == "schule":
            w = b.wand("vorne")
            ops["vorne"].append({"s0": W / 2 - 1.2, "s1": W / 2 + 1.2, "z0": z0, "z1": z0 + 2.6})
        huelle(b, g, geschosse, top, ops)
        dach_flach(b, g, top, 0.8)
        b.box(-0.03, -0.03, W + 0.03, 0, z0 + 3.35, z0 + 3.6, S["Beton"])
        if art == "schule":
            b.box(W / 2 - 3, -2.5, W / 2 + 3, 0, z0 + 3.0, z0 + 3.3, S["Beton"])
            V.text_mesh(b.bm, "SCHOOL", 0.55, Matrix.Translation((*b.r.p(W / 2, -0.04), z0 + 6.2)) @ _richtung_matrix(b, "vorne"), S["Lack"], extrude=0.015)
        else:
            b.box(W - 4.5, D - 4.5, W - 0.5, D - 0.5, g["zg"], z0 + 14.0, S["Fassade"], top=S["Dach"])
        dachtechnik(b, top, rnd, anzahl=2)
    else:
        P1.typ8_sonstiges(b, g, rnd)


def typ4(b, g, rnd):
    P1.typ4_tankstelle(b, g, rnd)
    W, D = b.r.W, b.r.D
    z0 = b.z0
    u0 = (W - 30) / 2
    m = Matrix.Translation((*b.r.p(u0 + 15, 4.95), z0 + 5.75)) @ _richtung_matrix(b, "vorne")
    V.text_mesh(b.bm, "HARLAN FUEL", 0.7, m, S["Lack"], extrude=0.02)
    m = Matrix.Translation((*b.r.p(1.5, 1.25), z0 + 8.4)) @ _richtung_matrix(b, "vorne")
    V.text_mesh(b.bm, "HARLAN", 0.45, m, S["Lack"], extrude=0.02)
    m = Matrix.Translation((*b.r.p(1.5, 1.25), z0 + 6.9)) @ _richtung_matrix(b, "vorne")
    V.text_mesh(b.bm, "3.4  ", 0.6, m, S["Rost"], extrude=0.02)
    for k in range(4):  # Zapfschlaeuche, zwei Zapfpistolen am Boden
        uu = u0 + 4.5 + k * 7.0
        pa = Vector((*b.r.p(uu + 0.45, 5.0 + 6.0), z0 + 1.5))
        pb = Vector((*b.r.p(uu + 0.9 + rnd.uniform(0, 1.2), 5.0 + 6.0 + rnd.uniform(-1.5, 1.5)), z0 + 0.05))
        _rohr(b, pa, (pa + pb) / 2 + Vector((0, 0, -0.4)), 0.02, S["Lack"], seg=6)
        _rohr(b, (pa + pb) / 2 + Vector((0, 0, -0.4)), pb, 0.02, S["Lack"], seg=6)


def typ7(b, g, rnd):
    P1.typ7_parkhaus(b, g, rnd)
    W = b.r.W
    m = Matrix.Translation((*b.r.p(8.0, -0.25), b.z0 + 3.9)) @ _richtung_matrix(b, "vorne")
    V.text_mesh(b.bm, "PARKING", 0.8, m, S["Lack"], extrude=0.03)
    # Bewehrung an den Bruchkanten der eingestuerzten Ecke
    eu0, ev1 = W - 12.0, 11.0
    for k in range(1, g["geschosse"]):
        zd = b.z0 + k * 3.0 - 0.15
        for i in range(14):
            if rnd.random() < 0.5:
                u = eu0 + rnd.uniform(-0.05, 0.05)
                v = rnd.uniform(0.3, ev1)
                pa = Vector((*b.r.p(u, v), zd))
                pb = Vector((*b.r.p(u + rnd.uniform(0.4, 1.2), v + rnd.uniform(-0.2, 0.2)), zd - rnd.uniform(0.1, 0.8)))
            else:
                u = rnd.uniform(eu0, W)
                v = ev1
                pa = Vector((*b.r.p(u, v), zd))
                pb = Vector((*b.r.p(u + rnd.uniform(-0.2, 0.2), v - rnd.uniform(0.4, 1.2)), zd - rnd.uniform(0.1, 0.8)))
            _rohr(b, pa, pb, 0.0125, S["Rost"], seg=5)


NEU.update({2: typ2, 4: typ4, 5: typ5, 6: typ6, 7: typ7, 8: typ8})



def _zaun_latten(b, w_frame, ua, va, ub, vb, z, rnd, umgedrueckt=False):
    """Lattenzaun 1,0 m: Pfosten alle 2,4 m, 2 Riegel, Latten 9 cm alle 14 cm (teils fehlend/schief)."""
    a, c = Vector((ua, va)), Vector((ub, vb))
    L = (c - a).length
    if L < 0.2:
        return
    d = (c - a) / L
    def P(t, off=0.0):
        q = a + d * t + Vector((-d.y, d.x)) * off
        return q
    def box_t(t0, t1, o0, o1, z0, z1, mat, kipp=0.0):
        tmp = bmesh.new()
        V.box(tmp, t0, o0, z0, t1, o1, z1)
        if kipp:
            bmesh.ops.rotate(tmp, verts=tmp.verts, cent=((t0 + t1) / 2, o0, z0), matrix=Matrix.Rotation(kipp, 3, "X"))
        pts = []
        for f in tmp.faces:
            pts.append([Vector((*b.r.p(*P(v.co.x, v.co.y)), v.co.z)) for v in f.verts])
        tmp.free()
        for vs in pts:
            f = b.bm.faces.new([b.bm.verts.new(p) for p in vs])
            f.material_index = mat
    kipp = math.radians(rnd.uniform(55, 80)) if umgedrueckt else 0.0
    t = 0.0
    while t <= L:
        box_t(t - 0.045, t + 0.045, -0.045, 0.045, z - 0.3, z + 1.1, S["Holz"], kipp)
        t += 2.4
    for zz in (z + 0.25, z + 0.8):
        box_t(0, L, 0.045, 0.09, zz, zz + 0.07, S["Holz"], kipp)
    t = 0.05
    while t < L - 0.05:
        if rnd.random() > 0.1:
            box_t(t, t + 0.09, 0.09, 0.11, z + 0.03, z + rnd.uniform(0.95, 1.02), S["Rahmen"], kipp + rnd.uniform(-0.05, 0.05))
        t += 0.14


def _zaun_draht(b, ua, va, ub, vb, z, rnd, hoehe=1.2):
    """Maschendrahtzaun: Rohrpfosten alle 3 m, Oberrohr, Geflecht (Alpha), teils eingedrueckt."""
    pa, pb = Vector((*b.r.p(ua, va), z)), Vector((*b.r.p(ub, vb), z))
    L = (pb - pa).length
    if L < 0.2:
        return
    n = max(1, int(L / 3.0))
    for k in range(n + 1):
        p = pa.lerp(pb, k / n)
        _rohr(b, p - Vector((0, 0, 0.3)), p + Vector((0, 0, hoehe + 0.05)), 0.025, S["Metall"], seg=6)
    _rohr(b, pa + Vector((0, 0, hoehe)), pb + Vector((0, 0, hoehe)), 0.017, S["Metall"], seg=6)
    for k in range(n):
        p0, p1 = pa.lerp(pb, k / n), pa.lerp(pb, (k + 1) / n)
        beul = rnd.uniform(0, 0.35) if rnd.random() < 0.3 else 0.0
        nrm = Vector((-(p1 - p0).y, (p1 - p0).x, 0)).normalized() * beul
        mid = (p0 + p1) / 2 + nrm
        for (q0, q1) in ((p0, mid), (mid, p1)):
            vs = [q0 + Vector((0, 0, 0.03)), q1 + Vector((0, 0, 0.03)), q1 + Vector((0, 0, hoehe - 0.02)), q0 + Vector((0, 0, hoehe - 0.02))]
            f = b.bm.faces.new([b.bm.verts.new(p) for p in vs])
            f.material_index = S["Draht"]


def _grundstueck2(b, g, rnd):
    """Vorgarten-Lattenzaun mit Tor, Seiten/Rueckseite Maschendraht, Einfahrt, Briefkasten am Strassenrand."""
    W, D = b.r.W, b.r.D
    z = b.z0
    vorne = -5.7
    lu0, lu1 = -1.5, W + 4.0
    ein = (W + 0.6, W + 3.6)
    tor = (W / 2 - 0.6, W / 2 + 0.6)
    druck = g["zerstoerung"] != "leicht" and rnd.random() < 0.6
    _zaun_latten(b, None, lu0, vorne, tor[0], vorne, z, rnd, umgedrueckt=druck)
    _zaun_latten(b, None, tor[1], vorne, ein[0], vorne, z, rnd)
    _zaun_draht(b, lu0, vorne, lu0, D + 6.0, z, rnd)
    _zaun_draht(b, lu1, vorne, lu1, D + 6.0, z, rnd)
    _zaun_draht(b, lu0, D + 6.0, lu1, D + 6.0, z, rnd)
    b.box(ein[0], vorne - 0.3, ein[1], D + 2.0, z - 0.05, z + 0.03, S["Beton"])  # Einfahrt
    b.box(W + 3.75, vorne - 0.45, W + 3.85, vorne - 0.35, z, z + 1.05, S["Holz"])  # Briefkasten-Pfosten
    bm2 = bmesh.new()
    x, y = b.r.p(W + 3.8, vorne - 0.4)
    bmesh.ops.create_cone(bm2, cap_ends=True, segments=12, radius1=0.12, radius2=0.12, depth=0.45,
                          matrix=Matrix.Translation((x, y, z + 1.17)) @ _richtung_matrix(b, "links") @ Matrix.Rotation(math.pi / 2, 4, "X"))
    b.mesh_einfuegen(bm2, S["Lack"])
