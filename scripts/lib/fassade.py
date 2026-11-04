"""Fassaden-Baukasten (Phase 2): Wandscheiben mit echten Oeffnungen, Laibungen, Fenstern, Innenraeumen.

Lokale Wandkoordinaten: s = entlang der Wand (von aussen gesehen nach rechts), z = Hoehe (absolut),
n = Tiefe in die Wand (0 = Aussenflaeche, dicke = Innenflaeche).
"""
import math
import random

import bmesh
from mathutils import Matrix, Vector, noise

# Material-Slots aller Phase-2-Gebaeude
SLOT = {k: i for i, k in enumerate([
    "Fassade", "Glas", "Dach", "Beton", "Holz", "Metall", "Schutt", "InnenWand", "InnenBoden", "InnenDecke",
    "Rahmen", "Sperrholz", "Stoff", "Teppich", "Fliesen", "Rost", "Lack", "Gelaender", "Draht"])}


class Wand:
    """Abbildung (s, n) -> (u, v) fuer die vier Seiten eines Rahmens (u = Front, v = Tiefe)."""

    def __init__(self, bau, seite, dicke):
        self.b, self.seite, self.d = bau, seite, dicke
        W, D = bau.r.W, bau.r.D
        self.W, self.D = W, D
        if seite in ("vorne", "hinten"):
            self.s0, self.s1 = 0.0, W
        else:
            self.s0, self.s1 = dicke, D - dicke

    def uv(self, s, n):
        W, D = self.W, self.D
        return {"vorne": (s, n), "hinten": (W - s, D - n), "links": (n, D - s), "rechts": (W - n, s)}[self.seite]

    def welt(self, s, n, z):
        u, v = self.uv(s, n)
        x, y = self.b.r.p(u, v)
        return Vector((x, y, z))

    def laenge(self):
        return self.W if self.seite in ("vorne", "hinten") else self.D


def wandscheibe(bm, wand, z0, z1, oeffnungen, rnd, mat_aussen, mat_innen, unebenheit=0.008, zacken=()):
    """Wand mit rechteckigen Oeffnungen (Liste dicts s0,s1,z0,z1). zacken = Indizes von Oeffnungen mit Bruchkante."""
    ss = {wand.s0, wand.s1}
    zs = {z0, z1}
    for o in oeffnungen:
        ss |= {max(wand.s0, min(wand.s1, o["s0"])), max(wand.s0, min(wand.s1, o["s1"]))}
        zs |= {max(z0, min(z1, o["z0"])), max(z0, min(z1, o["z1"]))}
    ss, zs = sorted(ss), sorted(zs)
    # Zwischenschnitte fuer Unebenheit (max. ~1,6 m Raster)
    def verfeinern(vals, step):
        out = [vals[0]]
        for v in vals[1:]:
            n = max(1, int(math.ceil((v - out[-1]) / step)))
            a = out[-1]
            out += [a + (v - a) * k / n for k in range(1, n + 1)]
        return out
    ss, zs = verfeinern(ss, 1.6), verfeinern(zs, 1.6)
    ns, nz = len(ss), len(zs)

    def offen(i, j):
        sc, zc = (ss[i] + ss[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
        return any(o["s0"] < sc < o["s1"] and o["z0"] < zc < o["z1"] for o in oeffnungen)

    cell = [[offen(i, j) for j in range(nz - 1)] for i in range(ns - 1)]
    # Bruchkanten: Randpunkte von 'zacken'-Oeffnungen zufaellig verschieben
    jitter = {}
    for k in zacken:
        o = oeffnungen[k]
        for i, s in enumerate(ss):
            for j, z in enumerate(zs):
                if o["s0"] - 1e-6 <= s <= o["s1"] + 1e-6 and o["z0"] - 1e-6 <= z <= o["z1"] + 1e-6:
                    if s in (o["s0"], o["s1"]) or z in (o["z0"], o["z1"]):
                        jitter[(i, j)] = (rnd.uniform(-0.25, 0.25), rnd.uniform(-0.3, 0.3))
    va, vi = {}, {}
    seed = rnd.random() * 100
    for i, s in enumerate(ss):
        for j, z in enumerate(zs):
            ds, dz = jitter.get((i, j), (0.0, 0.0))
            if s in (wand.s0, wand.s1):
                ds = 0.0
            if z in (z0, z1):
                dz = 0.0
            bulge = 0.0 if s in (wand.s0, wand.s1) else unebenheit * noise.noise(Vector((s * 0.35, z * 0.35, seed)))
            va[i, j] = bm.verts.new(wand.welt(s + ds, -bulge, z + dz))
            vi[i, j] = bm.verts.new(wand.welt(s + ds, wand.d, z + dz))

    def face(vs, mat):
        try:
            f = bm.faces.new(vs)
            f.material_index = mat
            return f
        except ValueError:
            return None

    for i in range(ns - 1):
        for j in range(nz - 1):
            if cell[i][j]:
                continue
            face((va[i, j], va[i + 1, j], va[i + 1, j + 1], va[i, j + 1]), mat_aussen)
            face((vi[i, j + 1], vi[i + 1, j + 1], vi[i + 1, j], vi[i, j]), mat_innen)
            # Raender: Laibungen zu Oeffnungen und Aussenkanten
            if i == 0 or cell[i - 1][j]:
                face((va[i, j], va[i, j + 1], vi[i, j + 1], vi[i, j]), mat_aussen)
            if i == ns - 2 or cell[i + 1][j]:
                face((va[i + 1, j + 1], va[i + 1, j], vi[i + 1, j], vi[i + 1, j + 1]), mat_aussen)
            if j == 0 or cell[i][j - 1]:
                face((va[i + 1, j], va[i, j], vi[i, j], vi[i + 1, j]), mat_aussen)
            if j == nz - 2 or cell[i][j + 1]:
                face((va[i, j + 1], va[i + 1, j + 1], vi[i + 1, j + 1], vi[i, j + 1]), mat_aussen)


def box_welt(bm, wand, s0, s1, n0, n1, z0, z1, mat):
    """Quader in Wandkoordinaten."""
    pts = [wand.welt(s, n, 0) for s in (s0, s1) for n in (n0, n1)]
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    import viertel_lib as V
    fs = V.box(bm, min(xs), min(ys), z0, max(xs), max(ys), z1)
    for f in fs:
        f.material_index = mat
    return fs


def schiefe_box(bm, wand, s0, s1, n0, n1, z0, z1, mat, winkel=0.0, cent=None):
    """Quader in Wandkoordinaten, um die Wandnormale gedreht (schiefe Bretter)."""
    import viertel_lib as V
    tmp = bmesh.new()
    V.box(tmp, s0, n0, z0, s1, n1, z1)
    c = cent or Vector(((s0 + s1) / 2, (n0 + n1) / 2, (z0 + z1) / 2))
    bmesh.ops.rotate(tmp, verts=tmp.verts, cent=c, matrix=Matrix.Rotation(winkel, 3, "Y"))
    neu = []
    for f in tmp.faces:
        neu.append([wand.welt(v.co.x, v.co.y, v.co.z) for v in f.verts])
    tmp.free()
    for vs in neu:
        try:
            f = bm.faces.new([bm.verts.new(p) for p in vs])
            f.material_index = mat
        except ValueError:
            pass


def fenster(bm, wand, o, zustand, rnd, rahmen_mat=None, mit_bank=True, sprosse=True, ac=False):
    """Fenster in Oeffnung o: Rahmen 7 cm, 15 cm zurueckgesetzt, Glas, Fensterbank (5 cm Ueberstand).
    zustand: intakt | gesprungen | zerbrochen | fehlt | vernagelt | ausgebrannt"""
    S = SLOT
    rm = S["Rahmen"] if rahmen_mat is None else rahmen_mat
    s0, s1, z0, z1 = o["s0"], o["s1"], o["z0"], o["z1"]
    r, t, n0 = 0.07, 0.06, 0.15
    teile = []
    if zustand != "ausgebrannt":
        for (a, b, c, d) in [(s0, s0 + r, z0, z1), (s1 - r, s1, z0, z1), (s0 + r, s1 - r, z0, z0 + r), (s0 + r, s1 - r, z1 - r, z1)]:
            box_welt(bm, wand, a, b, n0, n0 + t, c, d, rm)
        if sprosse:  # Kaempfer/Schiebefenster-Riegel
            zm = (z0 + z1) / 2
            box_welt(bm, wand, s0 + r, s1 - r, n0 + 0.005, n0 + t - 0.005, zm - 0.03, zm + 0.03, rm)
    if mit_bank:
        box_welt(bm, wand, s0 - 0.05, s1 + 0.05, -0.05, n0 + 0.02, z0 - 0.06, z0, S["Beton"])
        box_welt(bm, wand, s0 - 0.04, s1 + 0.04, -0.05, -0.035, z0 - 0.09, z0 - 0.06, S["Beton"])  # Tropfkante
    ng = n0 + t / 2
    gs0, gs1, gz0, gz1 = s0 + r, s1 - r, z0 + r, z1 - r
    def glas_quad(a, b, c, d):
        vs = [bm.verts.new(wand.welt(s, ng, z)) for s, z in ((a, c), (b, c), (b, d), (a, d))]
        f = bm.faces.new(vs)
        f.material_index = S["Glas"]
    if zustand in ("intakt", "gesprungen"):
        glas_quad(gs0, gs1, gz0, gz1)
    elif zustand == "zerbrochen":  # Restsplitter in den Ecken
        for (cs, cz, ds, dz) in [(gs0, gz0, 1, 1), (gs1, gz0, -1, 1), (gs0, gz1, 1, -1), (gs1, gz1, -1, -1)]:
            if rnd.random() < 0.7:
                a = rnd.uniform(0.08, 0.35) * (gs1 - gs0)
                b = rnd.uniform(0.08, 0.4) * (gz1 - gz0)
                vs = [bm.verts.new(wand.welt(s, ng, z)) for s, z in ((cs, cz), (cs + ds * a, cz), (cs, cz + dz * b))]
                f = bm.faces.new(vs)
                f.material_index = S["Glas"]
    elif zustand == "vernagelt":  # unregelmaessige, schiefe Bretter aussen
        nbr = rnd.randint(3, 5)
        for k in range(nbr):
            zc = z0 + (z1 - z0) * (k + 0.5) / nbr + rnd.uniform(-0.08, 0.08)
            hb = rnd.uniform(0.18, 0.3)
            schiefe_box(bm, wand, s0 - 0.12, s1 + 0.12, -0.045, -0.025, zc - hb / 2, zc + hb / 2, S["Sperrholz"],
                        winkel=math.radians(rnd.uniform(-9, 9)))
    if ac:  # Fenster-Klimageraet in der unteren Haelfte
        w = min(0.66, (s1 - s0) - 0.2)
        sc = (s0 + s1) / 2
        box_welt(bm, wand, sc - w / 2, sc + w / 2, -0.3, n0 + 0.2, z0 + 0.03, z0 + 0.43, S["Metall"])
        box_welt(bm, wand, sc - w / 2 + 0.04, sc + w / 2 - 0.04, -0.31, -0.3, z0 + 0.08, z0 + 0.38, S["Rost"])
        box_welt(bm, wand, sc - 0.02, sc + 0.02, -0.3, 0.0, z0 - 0.35, z0 + 0.03, S["Metall"])  # Konsole


def vorhang(bm, wand, o, rnd, tiefe=0.32):
    """Vorhang/Jalousie innen (teilweise zugezogen, schief)."""
    s0, s1, z0, z1 = o["s0"], o["s1"], o["z0"], o["z1"]
    anteil = rnd.uniform(0.25, 0.8)
    if rnd.random() < 0.5:
        a, b = s0 + 0.05, s0 + (s1 - s0) * anteil
    else:
        a, b = s1 - (s1 - s0) * anteil, s1 - 0.05
    zt = z1 + 0.05
    zb = z0 + rnd.uniform(-0.2, 0.4)
    vs = [bm.verts.new(wand.welt(s, tiefe + rnd.uniform(0, 0.05), z)) for s, z in ((a, zb), (b, zb + rnd.uniform(-0.2, 0.2)), (b, zt), (a, zt))]
    f = bm.faces.new(vs)
    f.material_index = SLOT["Stoff"]


def fensterzustand(rnd, zerstoerung, ist_eg=False):
    """Zustand nach Schadenskatalog 2.2 (leicht 30-50 % kaputt, mittel 50-80 % kaputt/vernagelt, schwer)."""
    x = rnd.random()
    if zerstoerung == "leicht":
        return "zerbrochen" if x < 0.25 else "fehlt" if x < 0.4 else "gesprungen" if x < 0.5 else "intakt"
    if zerstoerung == "mittel":
        if ist_eg and x < 0.35:
            return "vernagelt"
        return "zerbrochen" if x < 0.4 else "fehlt" if x < 0.6 else "vernagelt" if x < 0.72 else "gesprungen" if x < 0.8 else "intakt"
    return "fehlt" if x < 0.45 else "zerbrochen" if x < 0.75 else "ausgebrannt" if x < 0.85 else "vernagelt" if x < 0.93 else "intakt"


def fensterraster(laenge, breite, abstand, rand, s_min=0.0):
    n = max(1, int((laenge - 2 * rand + (abstand - breite)) // abstand))
    start = s_min + (laenge - (n - 1) * abstand) / 2
    return [start + k * abstand for k in range(n)]
