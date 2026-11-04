"""Phase 1.5 – Gebaeude-Blockout-Generator (fester Seed, Parameter in scripts/configs/gebaeude.json).

Grobe Volumen mit korrekten Massen: Koerper, Daecher, Attika, Gesimse, Fensterraster, Schaufenster,
Veranden, Feuertreppen, Vordaecher, Grundstuecke (Zaeune, Einfahrten, Briefkaesten), Schadensbilder
(schwer: Teil-Einsturz + Schuttkegel). Ursprung jedes Gebaeudes = Ecke Erdgeschoss (x0, y0, EG-Niveau).
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

import viertel_lib as V

SLOTS = ["Fassade", "Glas", "Dach", "Beton", "Holz", "Metall", "Schutt"]
F, GL, DA, BE, HO, ME, SC = range(7)


class Rahmen:
    """Lokales Koordinatensystem eines Gebaeudes: u entlang der Strassenfront, v = Tiefe (0 = Front)."""

    def __init__(self, rect, front):
        self.x0, self.y0, self.x1, self.y1 = rect
        self.front = front
        if front in ("S", "N"):
            self.W, self.D = self.x1 - self.x0, self.y1 - self.y0
        else:
            self.W, self.D = self.y1 - self.y0, self.x1 - self.x0

    def p(self, u, v):
        f = self.front
        if f == "S":
            return self.x0 + u, self.y0 + v
        if f == "N":
            return self.x1 - u, self.y1 - v
        if f == "W":
            return self.x0 + v, self.y1 - u
        return self.x1 - v, self.y0 + u  # "O"


class Bau:
    def __init__(self, rahmen, z0):
        self.r = rahmen
        self.z0 = z0
        self.bm = bmesh.new()

    def box(self, u0, v0, u1, v1, za, zb, mat=F, top=None):
        (xa, ya), (xb, yb) = self.r.p(u0, v0), self.r.p(u1, v1)
        fs = V.box(self.bm, min(xa, xb), min(ya, yb), za, max(xa, xb), max(ya, yb), zb)
        for f in fs:
            f.material_index = mat
        if top is not None:
            fs[1].material_index = top
        return fs

    def mesh_einfuegen(self, bm2, mat):
        me = bpy.data.meshes.new("tmp")
        bm2.to_mesh(me)
        bm2.free()
        n0 = len(self.bm.faces)
        self.bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        self.bm.faces.ensure_lookup_table()
        for f in list(self.bm.faces)[n0:]:
            f.material_index = mat

    def prisma(self, u0, u1, v0, v1, z_unten, z_first, ridge_along_u, mat):
        """Satteldach-Prisma: First in der Mitte (entlang u oder v)."""
        bm2 = bmesh.new()
        pts = []
        if ridge_along_u:
            vm = (v0 + v1) / 2
            prof = [(v0, z_unten), (vm, z_first), (v1, z_unten)]
            ends = (u0, u1)
            for e in ends:
                pts.append([bm2.verts.new((*self.r.p(e, vv), zz)) for vv, zz in prof])
        else:
            um = (u0 + u1) / 2
            prof = [(u0, z_unten), (um, z_first), (u1, z_unten)]
            for e in (v0, v1):
                pts.append([bm2.verts.new((*self.r.p(uu, e), zz)) for uu, zz in prof])
        a, b = pts
        bm2.faces.new(a)
        bm2.faces.new(b[::-1])
        for i in range(3):
            j = (i + 1) % 3
            bm2.faces.new((a[i], b[i], b[j], a[j]))
        bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
        self.mesh_einfuegen(bm2, mat)

    def schiefe_platte(self, u0, u1, v0, z_v0, v1, z_v1, dicke, mat):
        bm2 = bmesh.new()
        top = [(u0, v0, z_v0), (u1, v0, z_v0), (u1, v1, z_v1), (u0, v1, z_v1)]
        vs = [bm2.verts.new((*self.r.p(u, v), z)) for u, v, z in top] + \
             [bm2.verts.new((*self.r.p(u, v), z - dicke)) for u, v, z in top]
        for q in [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]:
            bm2.faces.new([vs[i] for i in q])
        bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
        self.mesh_einfuegen(bm2, mat)

    def fenster(self, seite, z_bruestungen, w=0.9, hh=1.5, abstand=2.6, rand=0.9, mat=GL, aus=None, tiefe=0.03):
        L = self.r.W if seite in ("vorne", "hinten") else self.r.D
        n = max(1, int((L - 2 * rand + (abstand - w)) // abstand))
        start = (L - (n - 1) * abstand) / 2
        for zb in z_bruestungen:
            for k in range(n):
                c = start + k * abstand
                if aus and any(a <= c <= b for a, b in aus):
                    continue
                if seite == "vorne":
                    self.box(c - w / 2, -tiefe, c + w / 2, 0.0, zb, zb + hh, mat)
                elif seite == "hinten":
                    self.box(c - w / 2, self.r.D, c + w / 2, self.r.D + tiefe, zb, zb + hh, mat)
                elif seite == "links":
                    self.box(-tiefe, c - w / 2, 0.0, c + w / 2, zb, zb + hh, mat)
                else:
                    self.box(self.r.W, c - w / 2, self.r.W + tiefe, c + w / 2, zb, zb + hh, mat)
        return n

    def attika(self, z_dach, hoehe, dicke=0.3, mat=F):
        W, D = self.r.W, self.r.D
        self.box(0, 0, W, dicke, z_dach, z_dach + hoehe, mat, top=BE)
        self.box(0, D - dicke, W, D, z_dach, z_dach + hoehe, mat, top=BE)
        self.box(0, dicke, dicke, D - dicke, z_dach, z_dach + hoehe, mat, top=BE)
        self.box(W - dicke, dicke, W, D - dicke, z_dach, z_dach + hoehe, mat, top=BE)

    def schuttkegel(self, u, v, radius, hoehe, rnd):
        x, y = self.r.p(u, v)
        bm2 = bmesh.new()
        m = Matrix.Translation((x, y, V.h(x, y) + 0.15 + hoehe * 0.35)) @ Matrix.Diagonal((radius, radius * rnd.uniform(0.7, 1.0), hoehe, 1))
        bmesh.ops.create_icosphere(bm2, subdivisions=2, radius=1.0, matrix=m)
        for vv in bm2.verts:  # unregelmaessiger, flacher Kegel statt glattem Felsbrocken
            vv.co += Vector((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.35, 0.35), rnd.uniform(-0.25, 0.25)))
            vv.co.z = max(vv.co.z, V.h(vv.co.x, vv.co.y) + 0.05)
        self.mesh_einfuegen(bm2, SC)


# ------------------------------------------------------------------ Gebaeudetypen
def typ1_wohnhaus(b, g, rnd):
    r, z0 = b.r, b.z0
    W, D = r.W, r.D
    n = g["geschosse"]
    stufen = rnd.randint(3, 5)
    eg = z0 + stufen * 0.17
    H = n * 3.2
    top = eg + H
    b.box(0, 0, W, D, g["zg"], top, F, top=DA)
    b.attika(top, g["attika"])
    b.box(-0.35, -0.35, W + 0.35, 0.3, top - 0.45, top - 0.05, BE)  # Abschlussgesims vorne
    for k in range(1, n):  # Gurtgesimse
        b.box(-0.04, -0.04, W + 0.04, 0.0, eg + k * 3.2 - 0.08, eg + k * 3.2 + 0.08, BE)
    sills = [eg + k * 3.2 + 0.9 for k in range(n)]
    tuer = W / 2
    b.fenster("vorne", sills[:1], aus=[(tuer - 1.3, tuer + 1.3)])
    b.fenster("vorne", sills[1:])
    for s in ("links", "rechts", "hinten"):
        b.fenster(s, sills)
    # Eingang: Treppe, Tuer, Vordach, Briefkastenanlage
    for k in range(stufen):
        b.box(tuer - 1.0, -0.3 * (stufen - k), tuer + 1.0, 0.0, z0 - 0.1, z0 + 0.17 * (k + 1), BE)
    b.box(tuer - 0.6, -0.04, tuer + 0.6, 0.0, eg, eg + 2.3, HO)
    b.box(tuer - 1.2, -1.3, tuer + 1.2, 0.0, eg + 2.6, eg + 2.75, BE)
    b.box(tuer + 0.8, -0.18, tuer + 1.4, -0.03, eg + 0.9, eg + 1.7, ME)
    # Feuertreppe (Front oder Seite): Podest je OG, Gelaender, Leitern
    seite = rnd.choice(["vorne", "rechts"])
    for k in range(1, n):
        zf = eg + k * 3.2
        hang = g["zerstoerung"] == "schwer" and k == n - 1
        if seite == "vorne":
            u0 = W * 0.2
            if hang:
                b.schiefe_platte(u0, u0 + 3.2, -1.1, zf - 1.6, 0, zf, 0.06, ME)
            else:
                b.box(u0, -1.15, u0 + 3.2, 0, zf - 0.06, zf, ME)
                b.box(u0, -1.15, u0 + 3.2, -1.1, zf, zf + 0.95, ME)
            b.box(u0 + 2.6, -1.0, u0 + 2.75, -0.6, zf - 3.2, zf, ME)
        else:
            v0 = D * 0.35
            b.box(W, v0, W + 1.15, v0 + 3.2, zf - 0.06, zf, ME)
            b.box(W + 1.1, v0, W + 1.15, v0 + 3.2, zf, zf + 0.95, ME)
            b.box(W + 0.6, v0 + 2.6, W + 1.0, v0 + 2.75, zf - 3.2, zf, ME)
    _dachtechnik(b, top, rnd)
    if g["zerstoerung"] == "schwer" and not g.get("name") == "Wohnhaus_Hubschrauber":
        _teileinsturz(b, top, 3.2, rnd)
    if g.get("name") == "Wohnhaus_Hubschrauber":
        # Loch in der Front im 2. OG fuer den Hubschrauber (Phase 3), Schutt davor
        b.box(W * 0.25, -0.05, W * 0.75, 0.01, eg + 2 * 3.2 - 0.2, eg + 3 * 3.2 - 0.4, GL)
        b.schuttkegel(W * 0.5, -2.5, 3.2, 1.4, rnd)


def typ2_holzhaus(b, g, rnd):
    r, z0 = b.r, b.z0
    W, D = r.W, r.D
    auf = rnd.uniform(*g["cfg"]["aufstaenderung_typ2"])
    n = g["geschosse"]
    ze = z0 + auf
    traufe = ze + n * 2.8
    b.box(0.25, 0.25, W - 0.25, D - 0.25, g["zg"], ze, HO)       # Kriechraum (Lattengitter)
    b.box(0, 0, W, D, ze, traufe, F, top=DA)
    neig = math.radians(rnd.uniform(30, 40))
    ov = rnd.uniform(0.4, 0.6)
    giebel_vorne = rnd.random() < 0.5
    schwer = g["zerstoerung"] == "schwer"
    if giebel_vorne:  # First entlang v
        hoch = (W / 2) * math.tan(neig)
        b.prisma(0, W, 0, D, traufe, traufe + hoch, False, F)
        if schwer:
            b.schiefe_platte(-ov, W / 2, -ov, traufe + hoch * 0.2, D * 0.55, traufe - 0.6, 0.15, DA)
            b.prisma(-ov, W + ov, D * 0.55, D + ov, traufe - 0.05, traufe + hoch + 0.2, False, DA)
        else:
            b.prisma(-ov, W + ov, -ov, D + ov, traufe - 0.05, traufe + (W / 2 + ov) * math.tan(neig) - ov * math.tan(neig) + 0.2, False, DA)
    else:  # First entlang u
        hoch = (D / 2) * math.tan(neig)
        b.prisma(0, W, 0, D, traufe, traufe + hoch, True, F)
        if schwer:
            b.prisma(-ov, W * 0.5, -ov, D + ov, traufe - 0.05, traufe + hoch + 0.2, True, DA)
            b.schiefe_platte(W * 0.5, W + ov, -ov, traufe - 1.2, D / 2, traufe + hoch * 0.3, 0.15, DA)
        else:
            b.prisma(-ov, W + ov, -ov, D + ov, traufe - 0.05, traufe + hoch + 0.2, True, DA)
    b.box(W * 0.7, D * 0.6, W * 0.7 + 0.6, D * 0.6 + 0.6, traufe, traufe + max(hoch, 2.5) + 0.8, BE)  # Schornstein
    # Veranda ueber die ganze Front: 2,4 m tief, Pfosten alle ~2,5 m, Gelaender 0,9 m, Dach durchhaengend
    b.box(0, -2.4, W, 0, ze - 0.15, ze, HO, top=HO)
    npf = max(2, int(round(W / 2.5)) + 1)
    sack = 0.35 if g["zerstoerung"] != "leicht" else 0.12
    for k in range(npf):
        u = 0.1 + (W - 0.2) * k / (npf - 1)
        b.box(u - 0.07, -2.32, u + 0.07, -2.18, ze, ze + 2.55, HO)
        if k < npf - 1:
            u2 = 0.1 + (W - 0.2) * (k + 1) / (npf - 1)
            if abs((u + u2) / 2 - W / 2) > 0.8:
                b.box(u + 0.07, -2.27, u2 - 0.07, -2.23, ze + 0.85, ze + 0.92, HO)
    b.schiefe_platte(-0.2, W + 0.2, 0, ze + 2.95, -2.65, ze + 2.6 - sack, 0.1, DA)
    stufen = max(3, int(round(auf / 0.18)))
    for k in range(stufen):
        b.box(W / 2 - 0.7, -2.4 - 0.28 * (stufen - k), W / 2 + 0.7, -2.4, z0 - 0.1, z0 + (auf / stufen) * (k + 1), HO)
    # Fenster und Tuer
    sills = [ze + k * 2.8 + 0.8 for k in range(n)]
    b.fenster("vorne", sills[:1], w=0.85, hh=1.4, abstand=2.4, aus=[(W / 2 - 0.9, W / 2 + 0.9)])
    b.fenster("vorne", sills[1:], w=0.85, hh=1.4, abstand=2.4)
    b.box(W / 2 - 0.48, -0.04, W / 2 + 0.48, 0, ze, ze + 2.1, HO)
    for s in ("links", "rechts", "hinten"):
        b.fenster(s, sills, w=0.85, hh=1.4, abstand=2.8)
    _grundstueck(b, g, rnd)


def typ3_laden(b, g, rnd):
    r, z0 = b.r, b.z0
    W, D = r.W, r.D
    n = g["geschosse"]
    eg = rnd.uniform(*g["cfg"]["eg_hoehe_typ3"])
    top = z0 + eg + (n - 1) * 3.2
    b.box(0, 0, W, D, g["zg"], top, F, top=DA)
    b.attika(top, g["attika"])
    b.box(-0.05, -0.4, W + 0.05, 0.2, top + g["attika"] - 0.45, top + g["attika"], BE)  # Ziergesims oben
    # Erdgeschoss: Sockel 0,45, Schaufenster bis 3 m, Oberlicht, Schildband
    p = 0.4
    b.box(p, -0.08, W - p, 0, z0 - 0.05, z0 + 0.45, BE)
    b.box(p, -0.03, W - p, 0, z0 + 0.45, z0 + 3.0, GL)
    b.box(p, -0.03, W - p, 0, z0 + 3.1, z0 + 3.6, GL)
    b.box(p - 0.1, -0.15, W - p + 0.1, 0, z0 + 3.7, z0 + eg - 0.15, HO)
    if rnd.random() < 0.6:  # Markise
        b.schiefe_platte(p, W - p, 0, z0 + 3.65, -1.6, z0 + 2.85 + (0.3 if g["zerstoerung"] != "leicht" else 0), 0.05, ME)
    sills = [z0 + eg + k * 3.2 + 0.9 for k in range(n - 1)]
    b.fenster("vorne", sills, w=0.9, hh=1.55, abstand=2.2 if W < 8 else 2.5, rand=0.8)
    for k in range(1, n):
        b.box(-0.04, -0.06, W + 0.04, 0, z0 + eg + (k - 1) * 3.2 - 0.12, z0 + eg + (k - 1) * 3.2 + 0.05, BE)
    b.fenster("hinten", sills, w=0.9, hh=1.4, abstand=2.6)
    b.box(W / 2 - 0.5, D, W / 2 + 0.5, D + 0.04, z0, z0 + 2.2, HO)  # Hintereingang (Gasse)
    if rnd.random() < 0.55 and n >= 2:  # Feuertreppe an der Rueckseite
        for k in range(1, n):
            zf = z0 + eg + (k - 1) * 3.2
            b.box(W * 0.2, D, W * 0.2 + 3.0, D + 1.1, zf - 0.06, zf, ME)
            b.box(W * 0.2, D + 1.05, W * 0.2 + 3.0, D + 1.1, zf, zf + 0.95, ME)
            b.box(W * 0.2 + 2.5, D + 0.6, W * 0.2 + 2.65, D + 1.0, zf - 2.9, zf, ME)
    _dachtechnik(b, top, rnd)
    if g["zerstoerung"] == "schwer":
        _teileinsturz(b, top, 3.2, rnd)


def typ4_tankstelle(b, g, rnd):
    r, z0 = b.r, b.z0
    W, D = r.W, r.D
    b.box(0, 0, W, D, z0 - 0.1, z0 + 0.03, BE, top=BE)  # Betonflaeche
    u0, v0 = (W - 30) / 2, 5.0
    zc = z0 + 5.25
    b.box(u0, v0, u0 + 30, v0 + 12, zc, zc + 1.0, ME, top=DA)  # Dach mit Blende
    b.box(u0 + 0.5, v0 + 0.5, u0 + 29.5, v0 + 11.5, zc - 0.05, zc, GL)  # Leuchten-Unterseite
    for uu in (u0 + 4, u0 + 15, u0 + 26):
        for vv in (v0 + 2.5, v0 + 9.5):
            b.box(uu - 0.25, vv - 0.25, uu + 0.25, vv + 0.25, z0, zc, ME)
    for k in range(4):  # Zapfsaeuleninseln: Sockel 15 cm, Zapfsaeule, Anfahrschutz-Poller
        uu = u0 + 4.5 + k * 7.0
        b.box(uu - 0.6, v0 + 3, uu + 0.6, v0 + 9, z0, z0 + 0.18, BE)
        b.box(uu - 0.45, v0 + 5.5, uu + 0.45, v0 + 6.5, z0 + 0.18, z0 + 2.0, ME)
        for vv in (v0 + 3.15, v0 + 8.85):
            b.box(uu - 0.08, vv - 0.08, uu + 0.08, vv + 0.08, z0 + 0.18, z0 + 1.2, ME)
    # Shop 15 x 12 m, Glasfront zum Dach hin
    su, sv = (W - 15) / 2, D - 12.5
    b.box(su, sv, su + 15, sv + 12, g["zg"], z0 + 4.2, F, top=DA)
    b.box(su + 0.5, sv - 0.03, su + 14.5, sv, z0 + 0.4, z0 + 3.0, GL)
    b.box(su - 0.5, sv - 2.0, su + 15.5, sv, z0 + 3.4, z0 + 3.6, ME)
    b.box(su + 1, sv - 1.2, su + 3, sv - 0.4, z0, z0 + 1.0, ME)  # Eistruhe
    b.box(su + 13.5, sv - 1.0, su + 14.2, sv - 0.4, z0, z0 + 1.3, ME)  # Luft/Wasser
    # Preismast 9,5 m mit Schild (erfundene Marke, Phase 2)
    b.box(1.3, 1.3, 1.7, 1.7, z0, z0 + 9.5, ME)
    b.box(0.3, 1.3, 2.7, 1.7, z0 + 6.0, z0 + 9.3, ME)


def typ5_buero(b, g, rnd):
    r, z0 = b.r, b.z0
    W, D = r.W, r.D
    n = g["geschosse"]
    top = z0 + n * 3.8
    glas = g.get("variante") == "glas"
    b.box(0, 0, W, D, g["zg"], top, GL if glas else F, top=DA)
    b.attika(top, 1.1, mat=BE if glas else F)
    if glas:  # Vorhangfassade: Geschossdecken-Linien
        for k in range(1, n + 1):
            zf = z0 + k * 3.8
            for (a, c, d_, e) in ((0, -0.05, W, 0), (0, D, W, D + 0.05)):
                b.box(a, c, d_, e, zf - 0.25, zf + 0.05, ME)
            b.box(-0.05, 0, 0, D, zf - 0.25, zf + 0.05, ME)
            b.box(W, 0, W + 0.05, D, zf - 0.25, zf + 0.05, ME)
    else:  # Bandfassade: Fensterbaender je Geschoss
        for k in range(1, n):
            zb = z0 + k * 3.8 + 1.0
            b.box(0.6, -0.03, W - 0.6, 0, zb, zb + 1.7, GL)
            b.box(0.6, D, W - 0.6, D + 0.03, zb, zb + 1.7, GL)
            b.box(-0.03, 0.6, 0, D - 0.6, zb, zb + 1.7, GL)
            b.box(W, 0.6, W + 0.03, D - 0.6, zb, zb + 1.7, GL)
        b.box(1.0, -0.03, W - 1.0, 0, z0 + 0.3, z0 + 3.4, GL)  # Lobby
    b.box(W / 2 - 4, -3.5, W / 2 + 4, 0, z0 + 4.0, z0 + 4.35, BE)  # Vordach
    for uu in (W / 2 - 3.6, W / 2 + 3.6):
        b.box(uu - 0.12, -3.3, uu + 0.12, -3.06, z0, z0 + 4.0, ME)
    b.box(W / 2 - 1.2, -0.6, W / 2 + 1.2, 0, z0, z0 + 2.6, GL)  # Drehtuer-Gehaeuse
    if not g.get("kamera_dach"):
        b.box(W * 0.35, D * 0.35, W * 0.65, D * 0.65, top, top + 3.2, BE, top=DA)  # Technikaufbau
    _dachtechnik(b, top, rnd, anzahl=3)
    if g["zerstoerung"] == "schwer" and not glas:
        _teileinsturz(b, top, 3.8, rnd)


def typ6_krankenhaus(b, g, rnd):
    r, z0 = b.r, b.z0
    W, D = r.W, r.D
    n = g["geschosse"]
    top = z0 + n * 4.0
    b.box(0, 0, W, D, g["zg"], top, F, top=DA)
    b.attika(top, 1.0)
    for k in range(n):
        zb = z0 + k * 4.0 + 1.0
        for s in ("vorne", "hinten", "links", "rechts"):
            b.fenster(s, [zb], w=1.6, hh=1.6, abstand=3.2, rand=1.2)
    # Notaufnahme-Vordach mit Zufahrt
    b.box(6, -9, 22, 0, z0 + 4.5, z0 + 5.1, BE)
    for uu in (6.5, 21.5):
        for vv in (-8.5, -3):
            b.box(uu - 0.2, vv - 0.2, uu + 0.2, vv + 0.2, z0, z0 + 4.5, ME)
    # Hubschrauber-Landeplatz (verblasste Markierung Phase 2): flache Scheibe
    bm2 = bmesh.new()
    x, y = r.p(W * 0.7, D * 0.5)
    bmesh.ops.create_cone(bm2, cap_ends=True, segments=32, radius1=7.5, radius2=7.5, depth=0.06,
                          matrix=Matrix.Translation((x, y, top + 0.03)))
    b.mesh_einfuegen(bm2, BE)
    # Improvisierte Zelte vor dem Eingang (6 x 5 m)
    for k, uu in enumerate((26, 33, 40)):
        b.box(uu, -14, uu + 5, -9, z0, z0 + 1.6, HO)
        b.prisma(uu, uu + 5, -14, -9, z0 + 1.6, z0 + 3.0, False, HO)


def typ7_parkhaus(b, g, rnd):
    r, z0 = b.r, b.z0
    W, D = r.W, r.D
    ebenen = g["geschosse"]
    eu0, ev1 = W - 12.0, 11.0  # eingestuerzte Ecke (Front rechts)
    eck = g.get("einsturz_ecke")
    for k in range(1, ebenen):
        zd = z0 + k * 3.0
        if eck:
            b.box(0, 0, eu0, D, zd - 0.3, zd, BE, top=BE)
            b.box(eu0, ev1, W, D, zd - 0.3, zd, BE, top=BE)
            # abgesackte Decke in der Ecke (Pfannkuchen), schraeg
            zz = z0 + 0.4 + 0.75 * (k - 1)
            b.schiefe_platte(eu0 + 0.3, W + 0.4 * k, -0.6, zz + 0.2 * k, ev1 - 0.2, zz + 0.9 + 0.5 * k, 0.3, BE)
        else:
            b.box(0, 0, W, D, zd - 0.3, zd, BE, top=BE)
        for (u0, v0, u1, v1) in ((0, 0, W, 0.2), (0, D - 0.2, W, D), (0, 0, 0.2, D), (W - 0.2, 0, W, D)):
            if eck and u1 > eu0 and v0 < ev1:
                if v1 - v0 < 1:  # Front-Bruestung nur bis zur Einsturzecke
                    b.box(u0, v0, eu0, v1, zd, zd + 1.1, BE)
                else:
                    b.box(u0, ev1, u1, v1, zd, zd + 1.1, BE)
                continue
            b.box(u0, v0, u1, v1, zd, zd + 1.1, BE)
    for uu in [0.3 + 7.85 * i for i in range(5)]:
        for vv in [0.3 + 7.35 * j for j in range(5)]:
            if eck and uu > eu0 - 0.5 and vv < ev1 + 0.5:
                continue
            b.box(uu - 0.3, vv - 0.3, uu + 0.3, vv + 0.3, g["zg"], z0 + (ebenen - 1) * 3.0 - 0.3, BE)
    for k in range(ebenen - 1):  # Rampen
        b.schiefe_platte(10.5, 15.5, 8.0, z0 + k * 3.0 + 0.05, 22.0, z0 + (k + 1) * 3.0 - 0.3, 0.25, BE)
    b.box(0.2, D - 4.5, 4.5, D - 0.2, g["zg"], z0 + ebenen * 3.0 + 1.0, F, top=DA)  # Treppenhaus
    if eck:
        b.schuttkegel(W - 5, 2, 4.0, 1.6, rnd)


def typ8_sonstiges(b, g, rnd):
    r, z0 = b.r, b.z0
    W, D = r.W, r.D
    art = g.get("art")
    if art == "kirche":
        b.box(2, 6, 14, 22, g["zg"], z0 + 7.0, F, top=DA)
        b.prisma(2, 14, 6, 22, z0 + 7.0, z0 + 7.0 + 6 * math.tan(math.radians(40)), False, F)
        b.prisma(1.6, 14.4, 5.6, 22.4, z0 + 6.95, z0 + 7.2 + 6.4 * math.tan(math.radians(40)), False, DA)
        b.box(5.5, 0.5, 10.5, 5.5, g["zg"], z0 + 16.0, F, top=DA)
        bm2 = bmesh.new()
        x, y = r.p(8.0, 3.0)
        bmesh.ops.create_cone(bm2, cap_ends=True, segments=4, radius1=3.6, radius2=0.05, depth=5.5,
                              matrix=Matrix.Translation((x, y, z0 + 18.75)) @ Matrix.Rotation(math.pi / 4, 4, "Z"))
        b.mesh_einfuegen(bm2, DA)
        for k in range(3):
            b.box(6.2, 0.5 - 0.35 * (3 - k), 9.8, 0.5, z0 - 0.1, z0 + 0.17 * (k + 1), BE)
        b.box(7.2, 0.47, 8.8, 0.5, z0 + 0.5, z0 + 3.2, HO)
        for vv in (8, 11, 14, 17, 20):
            for uu in (2, 14):
                b.box(uu - 0.03, vv - 0.45, uu + 0.03, vv + 0.45, z0 + 2.0, z0 + 5.5, GL)
    elif art == "feuerwache":
        top = z0 + 7.0
        b.box(0, 0, W, D, g["zg"], top, F, top=DA)
        b.attika(top, 0.8)
        for k in range(3):
            uu = 2.0 + k * 4.8
            b.box(uu, -0.03, uu + 3.6, 0, z0, z0 + 4.2, ME)
        b.fenster("vorne", [z0 + 3.5 + 1.0], w=1.0, hh=1.4, abstand=2.6)
        b.box(W - 4.5, D - 4.5, W - 0.5, D - 0.5, g["zg"], z0 + 14.0, F, top=DA)  # Schlauchturm
    elif art == "schule":
        top = z0 + 7.0
        b.box(0, 0, W, D, g["zg"], top, F, top=DA)
        b.attika(top, 0.8)
        b.fenster("vorne", [z0 + 0.9, z0 + 4.4], w=1.4, hh=1.6, abstand=2.4, aus=[(W / 2 - 2.5, W / 2 + 2.5)])
        b.fenster("hinten", [z0 + 0.9, z0 + 4.4], w=1.4, hh=1.6, abstand=2.4)
        b.box(W / 2 - 3, -2.5, W / 2 + 3, 0, z0 + 3.2, z0 + 3.5, BE)
        b.box(W / 2 - 1.2, -0.03, W / 2 + 1.2, 0, z0, z0 + 2.5, GL)
    else:  # Lagerhalle
        top = z0 + 7.5
        b.box(0, 0, W, D, g["zg"], top, F, top=DA)
        b.prisma(-0.3, W + 0.3, -0.3, D + 0.3, top, top + (W / 2) * math.tan(math.radians(8)), False, DA)
        for k in range(3):
            uu = 2.5 + k * 6.5
            b.box(uu, -0.04, uu + 4.0, 0, z0, z0 + 4.5, ME)
        b.fenster("vorne", [z0 + 5.6], w=1.6, hh=0.9, abstand=3.5)


# ------------------------------------------------------------------ Details
def _dachtechnik(b, top, rnd, anzahl=None):
    W, D = b.r.W, b.r.D
    for k in range(anzahl or rnd.randint(1, 2)):
        uu, vv = rnd.uniform(1.5, W - 2.5), rnd.uniform(2.0, D - 3.0)
        b.box(uu, vv, uu + 1.2, vv + 0.9, top, top + 1.0, ME)
    uu, vv = rnd.uniform(1, W - 1.5), rnd.uniform(1, D - 1.5)
    b.box(uu, vv, uu + 0.15, vv + 0.15, top, top + 1.2, ME)  # Lueftungsrohr


def _teileinsturz(b, top, gh, rnd):
    """Schwerer Schaden: Ecke der oberen Geschosse eingestuerzt (als Hohlraum-Andeutung) + Schuttkegel."""
    W, D = b.r.W, b.r.D
    links = rnd.random() < 0.5
    bw = W * rnd.uniform(0.3, 0.45)
    u0, u1 = (0, bw) if links else (W - bw, W)
    tiefe = rnd.uniform(1.5, gh * 1.2)
    # dunkler Einbruch (Hohlraum) in der Fassade und herabhaengende Deckenplatte
    b.box(u0 + 0.3, -0.05, u1 - 0.3, 0.01, top - tiefe - gh * 0.6, top - 0.1, GL)
    b.schiefe_platte(u0 + 0.4, u1 - 0.4, 0.2, top - gh * 0.7, -1.4, top - gh * 1.6, 0.25, BE)
    b.schuttkegel((u0 + u1) / 2, -1.6, rnd.uniform(2.0, 3.2), rnd.uniform(0.8, 1.4), rnd)


def _grundstueck(b, g, rnd):
    """Vorgarten-Zaun, Seitenzaeune, Einfahrt, Briefkasten (Typ 2)."""
    W, D = b.r.W, b.r.D
    z = b.z0
    vorne = -6.0 + 0.3
    lu0, lu1 = -1.5, W + 4.0
    ein = (W + 0.6, W + 3.6)
    tor = (W / 2 - 0.6, W / 2 + 0.6)
    latten = rnd.random() < 0.6
    hz = 1.0 if latten else 1.2
    m = HO if latten else ME
    def zaun(u0, v0, u1, v1, hh=hz, mat=m):
        b.box(u0, v0, u1, v1, z, z + hh, mat)
    zaun(lu0, vorne, tor[0], vorne + 0.05)
    zaun(tor[1], vorne, ein[0], vorne + 0.05)
    zaun(lu0, vorne, lu0 + 0.05, D + 6.0, 1.2, ME)
    zaun(lu1 - 0.05, vorne, lu1, D + 6.0, 1.2, ME)
    zaun(lu0, D + 5.95, lu1, D + 6.0, 1.2, ME)
    if g["zerstoerung"] != "leicht":  # umgedrueckter Zaunabschnitt
        b.schiefe_platte(lu0, lu0 + 0.05, vorne + 1, z + 0.1, vorne + 4, z + 0.7, 0.05, ME)
    b.box(ein[0], vorne - 0.3, ein[1], D + 2.0, z - 0.05, z + 0.03, BE)  # Einfahrt
    b.box(W + 3.75, vorne - 0.45, W + 3.85, vorne - 0.35, z, z + 1.05, HO)  # Briefkasten-Pfosten
    b.box(W + 3.6, vorne - 0.55, W + 4.0, vorne - 0.25, z + 1.05, z + 1.3, ME)


BAUER = {1: typ1_wohnhaus, 2: typ2_holzhaus, 3: typ3_laden, 4: typ4_tankstelle, 5: typ5_buero,
         6: typ6_krankenhaus, 7: typ7_parkhaus, 8: typ8_sonstiges}


# ------------------------------------------------------------------ Generator
def _nachbarn(a, b, abstand=3.0):
    ax0, ay0, ax1, ay1 = a["rechteck"]
    bx0, by0, bx1, by1 = b["rechteck"]
    return ax0 - abstand < bx1 and bx0 - abstand < ax1 and ay0 - abstand < by1 and by0 - abstand < ay1


def _hoehe(g):
    t = g["typ"]
    n = g["geschosse"]
    gh = {1: 3.2, 2: 2.8, 3: 3.2, 5: 3.8, 6: 4.0, 7: 3.0, 8: 3.5}[t]
    return n * gh + g.get("attika", 0) + (g.get("eg_extra", 0))


def planen(cfg):
    """Legt per Seed Geschosse, Fassade, Farbe, Attika und Zerstoerung fest (reproduzierbar)."""
    rnd = random.Random(cfg["seed"])
    geb = [dict(g) for g in cfg["gebaeude"]]
    # Zerstoerungsgrade nach Anteilen verteilen (feste Vorgaben zaehlen mit)
    n = len(geb)
    ziel = {k: round(v * n) for k, v in cfg["zerstoerung_anteile"].items()}
    for g in geb:
        if g.get("zerstoerung"):
            ziel[g["zerstoerung"]] -= 1
    pool = [k for k, c in ziel.items() for _ in range(max(c, 0))]
    while len(pool) < sum(1 for g in geb if not g.get("zerstoerung")):
        pool.append("mittel")
    rnd.shuffle(pool)
    for g in geb:
        if not g.get("zerstoerung"):
            g["zerstoerung"] = pool.pop()
    fertig = []
    for g in geb:
        for versuch in range(60):
            if isinstance(g.get("geschosse_cfg", g["geschosse"]), list):
                g.setdefault("geschosse_cfg", g["geschosse"])
                g["geschosse"] = rnd.randint(*g["geschosse_cfg"])
            g["attika"] = round(rnd.uniform(*cfg["attika"]), 2) if g["typ"] in (1, 3, 5, 6) else 0.0
            g["fassade"] = rnd.choice(cfg["fassaden"][str(g["typ"])])
            g["farbe"] = rnd.randrange(cfg["farbvarianten"])
            ok = True
            for o in fertig:
                if _nachbarn(g, o):
                    if abs(_hoehe(g) - _hoehe(o)) < 0.4 or (g["fassade"] == o["fassade"] and g["farbe"] == o["farbe"]):
                        ok = False
                        break
            if ok:
                break
        g["versuche"] = versuch + 1
        fertig.append(g)
    return geb


def bauen():
    cfg = V.config("gebaeude.json")
    geb = planen(cfg)
    zaehler = {}
    ergebnis = []
    for g in geb:
        rnd = random.Random(cfg["seed"] * 1000 + int(g["id"][1:]))
        g["cfg"] = cfg
        rahmen = Rahmen(g["rechteck"], g["front"])
        x0, y0, x1, y1 = g["rechteck"]
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), ((x0 + x1) / 2, (y0 + y1) / 2)]
        z0 = V.h_max(pts) + 0.15
        g["zg"] = V.h_min(pts) - 0.3
        b = Bau(rahmen, z0)
        BAUER[g["typ"]](b, g, rnd)
        tname = cfg["typnamen"][str(g["typ"])]
        zaehler[tname] = zaehler.get(tname, 0) + 1
        name = f"BLD_{g.get('name') or tname}_{zaehler[tname]:02d}" if not g.get("name") else f"BLD_{g['name']}"
        col = V.collection(f"03_Gebaeude/Typ{g['typ']}_{tname}")
        # Ursprung = Ecke Erdgeschoss
        orig = Vector((x0, y0, z0))
        bmesh.ops.translate(b.bm, verts=b.bm.verts, vec=-orig)
        bmesh.ops.remove_doubles(b.bm, verts=b.bm.verts, dist=0.0005)
        mats = [_fassaden_mat(g), V.blockout_mat("Glas"), V.blockout_mat("Dach"), V.blockout_mat("Beton"),
                V.blockout_mat("Holz"), V.blockout_mat("Metall"), V.blockout_mat("Schutt")]
        ob = V.objekt_aus_bmesh(name, b.bm, col, location=orig, material=mats)
        V.fase(ob, 0.02, 2)
        for k in ("id", "typ", "geschosse", "zerstoerung", "fassade", "farbe", "attika", "front"):
            ob[k] = g[k]
        for k in ("laden", "brand", "kamera_dach", "variante"):
            if k in g:
                ob[k] = g[k]
        ob["hoehe_m"] = round(max(v.co.z for v in ob.data.vertices), 2)
        ergebnis.append(ob)
    print(f"GEBAEUDE: {len(ergebnis)} erzeugt; Zerstoerung:",
          {k: sum(1 for o in ergebnis if o['zerstoerung'] == k) for k in ('leicht', 'mittel', 'schwer')},
          "max. Versuche:", max(g["versuche"] for g in geb))
    return ergebnis


def _fassaden_mat(g):
    """Blockout: leicht unterschiedliche Grautoene je Fassadenmaterial/Farbvariante (Lesbarkeit der Vielfalt)."""
    name = f"MAT_Blockout_Fassade_{g['fassade'].replace('MAT_', '')}_{g['farbe']}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    basis = {"Ziegel": (0.40, 0.33, 0.30), "Putz": (0.52, 0.50, 0.46), "Holz": (0.50, 0.48, 0.44),
             "Beton": (0.47, 0.47, 0.45), "Wellblech": (0.42, 0.43, 0.43)}
    key = next((k for k in basis if k in g["fassade"]), "Beton")
    c = [x * (0.82 + 0.09 * g["farbe"]) for x in basis[key]]
    m = bpy.data.materials.new(name)
    m.use_fake_user = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*c, 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    m.diffuse_color = (*c, 1)
    m["bibliothek_material"] = g["fassade"]
    return m
