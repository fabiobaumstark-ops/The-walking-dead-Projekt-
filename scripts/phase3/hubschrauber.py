"""Phase 3.5 – Mehrzweck-Hubschrauber (generisch, eigenes Design) mit Absturzszenario in B21 (2. OG).

Masse nach recherche/militaer.md: Rumpf ~15,5 m, Hauptrotor Ø 16,3 m (4 Blaetter je ~7,6 m), Hoehe ~5,1 m.
Lokale Koordinaten: x nach vorne (Bug), y nach links, z nach oben, Rumpfboden-Unterkante z = 0.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, HIER)
import viertel_lib as V  # noqa: E402
import fz_karosserie as K  # noqa: E402
import fz_material as FM  # noqa: E402
import fz_schaden as FS  # noqa: E402
import fz_teile as FT  # noqa: E402
import mil_detail as MD  # noqa: E402

Q, ZY, OB = FT.quader, FT.zylinder, FT.objekt

# Querschnitte: x, halbe Breite, Unterkante, Oberkante, Eckradius
SCHNITTE = [(6.30, 0.18, 0.80, 1.05, 0.15), (6.10, 0.50, 0.40, 1.55, 0.30), (5.60, 0.82, 0.18, 1.90, 0.42),
            (4.80, 1.00, 0.06, 2.04, 0.40), (3.60, 1.12, 0.0, 2.14, 0.34), (2.00, 1.16, 0.0, 2.20, 0.30),
            (0.00, 1.16, 0.0, 2.20, 0.30), (-1.40, 1.07, 0.12, 2.16, 0.30), (-2.30, 0.80, 0.50, 2.04, 0.27),
            (-3.00, 0.48, 0.92, 1.96, 0.20), (-6.00, 0.33, 1.20, 1.92, 0.14), (-9.20, 0.22, 1.46, 1.90, 0.10)]
BRUCH_X = -4.1


def mats():
    return {
        "lack": MD.lack_veredeln(MD.blech_naehte(FM.lack("Heli_Oliv", "#474B39", 0.0, matt=True))),  # 3B
        "dunkel": FM.dunkel(),
        "glas": FM.autoglas(),
        "russ": V.mat_russ() if hasattr(V, "mat_russ") else FM.dunkel(),
        "verbrannt": FS.mat_verbrannt(),
        "rost": V.material("MAT_Rost_Dunkel"),
        "gummi": V.material("MAT_Gummi"),
        "stoff": V.material("MAT_Plane_Oliv"),
        "sitz": V.material("MAT_Leder_Schwarz"),
        "armaturen": V.material("MAT_Armaturen"),
        "schrift": FM.text_mat("Heli", "#22231E", 0.8),
        "chrom": FM.chrom(),
    }


def _interp(x):
    s = SCHNITTE
    for a, b in zip(s, s[1:]):
        if b[0] <= x <= a[0]:
            t = (a[0] - x) / (a[0] - b[0])
            t = t * t * (3 - 2 * t) if (a[0] > 5 or b[0] < -2.5) else t
            return tuple(a[i] + (b[i] - a[i]) * t for i in range(1, 5))
    return s[0][1:] if x > s[0][0] else s[-1][1:]


def _ring(x, n=28):
    hw, zu, zo, r = _interp(x)
    r = min(r, hw * 0.95, (zo - zu) / 2.05)
    pts = []
    ecken = [(hw - r, zu + r, -90), (hw - r, zo - r, 0), (-hw + r, zo - r, 90), (-hw + r, zu + r, 180)]
    per = n // 4
    for cy, cz, a0 in ecken:
        for k in range(per):
            a = math.radians(a0 + 90 * k / (per - 1)) if per > 1 else math.radians(a0)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def rumpf_bm(x0, x1, schritt=0.12):
    """Rumpf-Loft zwischen x1 (vorne) und x0 (hinten), mit Kappen."""
    bm = bmesh.new()
    xs = [x1 - k * schritt for k in range(int((x1 - x0) / schritt) + 1)] + [x0]
    reihen = []
    for x in xs:
        reihen.append([bm.verts.new((x, y, z)) for y, z in _ring(x)])
    n = len(reihen[0])
    for a, b in zip(reihen, reihen[1:]):
        for k in range(n):
            k1 = (k + 1) % n
            f = bm.faces.new((a[k], a[k1], b[k1], b[k]))
            f.smooth = True
    for r, rev in ((reihen[0], False), (reihen[-1], True)):
        bm.faces.new(list(reversed(r)) if rev else r)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def klassifizieren(bm):
    """Material je Flaeche: Lack, Cockpitglas, Kinnfenster, Tuerfenster."""
    for f in bm.faces:
        c = f.calc_center_median()
        f.material_index = 0
        # Cockpitscheiben oben/seitlich vorne (Rahmen-Steg in der Mitte)
        zg = 1.02 + (6.15 - c.x) * 0.20
        if 4.15 < c.x < 6.18 and c.z > zg and abs(c.y) > 0.05 and not (5.0 < c.x < 5.15):
            f.material_index = 1
        # Kinnfenster unten vorne
        if 5.25 < c.x < 6.05 and 0.28 < c.z < 0.85 and 0.22 < abs(c.y) < 0.75:
            f.material_index = 1
        # Fenster in den Schiebetueren
        if 0.35 < c.x < 1.45 and 1.22 < c.z < 1.78 and abs(c.y) > 0.9:
            f.material_index = 1


def bauen(name, col, rnd, opt):
    M = mats()
    root = bpy.data.objects.new(name, None)
    col.objects.link(root)
    root.empty_display_size = 4
    root["typ"] = "Mehrzweck-Hubschrauber (generisch)"
    # Rumpf (Kabine + vorderer Heckausleger bis zur Bruchstelle)
    bm = rumpf_bm(BRUCH_X, 6.30)
    klassifizieren(bm)
    # Schiebetuer-Oeffnung rechts (Tuer abgerissen), links Tuer offen (nach hinten geschoben, separates Teil)
    weg = [f for f in bm.faces if -0.55 < f.calc_center_median().x < 2.15 and 0.18 < f.calc_center_median().z < 1.92
           and f.calc_center_median().y < -0.9]
    bmesh.ops.delete(bm, geom=weg, context="FACES")
    weg = [f for f in bm.faces if -0.55 < f.calc_center_median().x < 2.15 and 0.18 < f.calc_center_median().z < 1.92
           and f.calc_center_median().y > 0.9]
    tuer_fl = [f for f in weg]
    tuer_bm = bmesh.new()
    karte = {}
    for f in tuer_fl:
        vs = []
        for v in f.verts:
            if v not in karte:
                karte[v] = tuer_bm.verts.new(v.co + Vector((-1.9, 0.10, 0)))
            vs.append(karte[v])
        nf = tuer_bm.faces.new(vs)
        nf.material_index = f.material_index
        nf.smooth = True
    bmesh.ops.delete(bm, geom=weg, context="FACES")
    # Cockpit-Glas als eigenes Objekt (teils zerbrochen -> fehlt)
    glas = [f for f in bm.faces if f.material_index == 1]
    gbm = bmesh.new()
    karte = {}

    def scheibe_id(c):  # ganze Scheiben (nicht einzelne Flaechen) zerbrechen
        if c.z < 0.9:
            return ("kinn", c.y > 0)
        if c.x > 5.07:
            return ("front", c.y > 0, c.z > 1.45)
        if c.x > 4.15:
            return ("seite_v", c.y > 0)
        return ("tuer", c.y > 0)
    kaputt = {}
    for f in glas:
        sid = scheibe_id(f.calc_center_median())
        if sid not in kaputt:
            kaputt[sid] = rnd.random() < 0.5
        if kaputt[sid]:
            continue
        vs = []
        for v in f.verts:
            if v not in karte:
                karte[v] = gbm.verts.new(v.co - v.normal * 0.01)
            vs.append(karte[v])
        gbm.faces.new(vs)
    bmesh.ops.delete(bm, geom=glas, context="FACES")
    # 3B: Dellen im Rumpfblech (nicht an Fenster-/Tuerkanten und Kappen, damit Glas und Tuer passen)
    rand = {v for v in bm.verts if v.is_boundary or any(len(f.verts) > 4 for f in v.link_faces)}
    rand |= {e.other_vert(v) for v in list(rand) for e in v.link_edges}
    MD.dellen(bm, list(bm.verts), MD.rnd(3), MD.cfg()["rumpf_dellen"], fest=rand)
    rumpf = OB(f"{name}_Rumpf", bm, col, [M["lack"], M["dunkel"]], root)
    d = rumpf.modifiers.new("Blech", "SOLIDIFY")
    d.thickness = 0.02
    d.offset = -1
    d.material_offset = 1
    rumpf.modifiers.new("Normalen", "WEIGHTED_NORMAL").keep_sharp = True
    og = OB(f"{name}_Cockpitglas", gbm, col, [M["glas"]], root, glatt=True)
    og.modifiers.new("Dicke", "SOLIDIFY").thickness = 0.01
    tuer = OB(f"{name}_Schiebetuer_l", tuer_bm, col, [M["lack"], M["glas"]], root)
    tuer.modifiers.new("Dicke", "SOLIDIFY").thickness = 0.02
    # Fensterrahmen-Stege des Cockpits
    bm = bmesh.new()
    for x in (5.07, 4.15):
        pts = [Vector((x, y, z + 0.01)) for y, z in _ring(x) if z > 1.0 + (6.15 - x) * 0.2]
        if len(pts) > 2:
            FT.profil_zug(bm, pts, FT.rrechteck(0.05, 0.04, 0.01, 1), mat=0, kappen=True)
    OB(f"{name}_Cockpitrahmen", bm, col, [M["lack"]], root, glatt=True)
    # Triebwerksverkleidungen, Getriebe, Rotormast (Triebwerke ausgebrannt)
    bm = bmesh.new()
    for s in (1, -1):
        FT.polster(bm, (0.15, s * 0.48, 2.42), (2.9, 0.62, 0.46), None, "z", 0.0, 0.0, mat=1, cuts=3)
        Q(bm, (1.62, s * 0.48, 2.42), (0.05, 0.42, 0.30), 2)  # Lufteinlass-Gitter
        ZY(bm, (-1.3, s * 0.52, 2.40), (-1.75, s * 0.95, 2.30), 0.16, 14, 1)  # Abgasaustritt
    FT.polster(bm, (0.35, 0, 2.48), (1.4, 0.70, 0.55), None, "z", 0.0, 0.0, mat=0, cuts=3)
    ZY(bm, (0.35, 0, 2.6), (0.35, 0, 3.25), 0.16, 16, 3)
    ZY(bm, (0.35, 0, 3.10), (0.35, 0, 3.30), 0.36, 20, 3)
    for k in range(4):  # Blattanschluesse
        a = math.radians(45 + 90 * k)
        ZY(bm, (0.35, 0, 3.2), (0.35 + 0.62 * math.cos(a), 0.62 * math.sin(a), 3.2), 0.07, 10, 3)
    ob = OB(f"{name}_Triebwerke_Rotorkopf", bm, col, [M["lack"], M["verbrannt"], M["dunkel"], M["rost"]], root)
    ob.modifiers.new("Rund", "SUBSURF").levels = 1
    # 3B: offene Wartungsklappe rechts an der Triebwerksverkleidung
    MD.klappe(f"{name}_Wartungsklappe", col, root, M["lack"], M["dunkel"], (0.55, -0.79, 2.42), (0.85, 0.30), -1)
    # Fahrwerk (feste Raeder), Trittstufen, Haltegriffe, Antennen, Rettungswinde
    bm = bmesh.new()
    for s in (1, -1):
        ZY(bm, (-0.4, s * 1.10, 0.55), (-0.4, s * 1.35, 0.25), 0.05, 8, 0)
        ZY(bm, (-0.4, s * 1.30, 0.22), (-0.4, s * 1.46, 0.22), 0.21, 18, 1)
        Q(bm, (2.6, s * 1.17, 0.30), (0.35, 0.10, 0.03), 0)
        for x in (2.3, -0.8):
            ZY(bm, (x, s * 1.18, 1.0), (x, s * 1.18, 1.5), 0.015, 6, 2)
    ZY(bm, (-7.6, 0, 1.30), (-7.6, 0, 1.05), 0.03, 6, 0)
    Q(bm, (-1.0, 0, 2.25), (0.05, 0.30, 0.25), 0)
    Q(bm, (2.5, 0, 2.24), (0.30, 0.04, 0.10), 0)
    ZY(bm, (1.8, -1.0, 2.0), (1.8, -1.6, 2.15), 0.04, 8, 0)  # Windenarm rechts
    ZY(bm, (1.8, -1.6, 2.15), (1.8, -1.6, 1.85), 0.10, 12, 0)
    OB(f"{name}_Fahrwerk_Anbau", bm, col, [M["lack"], M["gummi"], M["chrom"]], root, glatt=True)
    # Innenraum: 2 Cockpitsitze, Instrumententafel, Bankreihe (Stoff), herabhaengende Kabel
    bm = bmesh.new()
    for s in (1, -1):
        FT.polster(bm, (4.35, s * 0.48, 0.65), (0.50, 0.50, 0.12), None, "z", 0.03, 0.01, 0)
        FT.polster(bm, Vector((4.05, s * 0.48, 1.05)), (0.10, 0.50, 0.70), Matrix.Rotation(math.radians(-12), 3, "Y"), "x", 0.03, 0.01, 0)
    Q(bm, (5.30, 0, 1.12), (0.30, 1.4, 0.40), 1)
    Q(bm, (5.15, 0, 1.36), (0.40, 1.3, 0.04), 1)
    for k in range(6):
        Q(bm, (-1.2 + k * 0.55, 0.65, 0.55), (0.45, 0.45, 0.06), 2)
        Q(bm, (-1.2 + k * 0.55, 0.92, 0.95), (0.45, 0.04, 0.75), 2)
    for k in range(9):
        a = Vector((rnd.uniform(-1.5, 3.0), rnd.uniform(-0.8, 0.8), 2.05))
        b = a + Vector((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), -rnd.uniform(0.4, 1.3)))
        ZY(bm, a, b, 0.008, 5, 1)
    Q(bm, (1.0, 0, 0.05), (6.0, 2.1, 0.06), 1)
    OB(f"{name}_Innenraum", bm, col, [M["sitz"], M["armaturen"], M["stoff"]], root)
    # Heckausleger-Endstueck (abgeknickt): eigenes Teil mit Drehpunkt an der Bruchstelle
    hinten = bpy.data.objects.new(f"{name}_Heckausleger", None)
    col.objects.link(hinten)
    hinten.parent = root
    hinten.location = (BRUCH_X, 0, 1.55)
    bm = rumpf_bm(-9.2, BRUCH_X - 0.04)
    for v in bm.verts:
        v.co -= Vector((BRUCH_X, 0, 1.55))
    ob = OB(f"{name}_Heckausleger_Rohr", bm, col, [M["lack"]], hinten)
    ob.modifiers.new("Dicke", "SOLIDIFY").thickness = 0.015
    bm = bmesh.new()
    # Seitenleitwerk + Hoehenleitwerk (am Ende)
    xe = -9.2 - BRUCH_X
    flosse = [(xe + 0.05, 0.25), (xe - 0.55, 0.30), (xe - 0.95, 2.05), (xe - 0.35, 2.0), (xe + 0.55, 0.4)]
    vs0 = [bm.verts.new((x, -0.05, z)) for x, z in flosse]
    vs1 = [bm.verts.new((x, 0.05, z)) for x, z in flosse]
    bm.faces.new(vs0[::-1])
    bm.faces.new(vs1)
    for i in range(len(flosse)):
        j = (i + 1) % len(flosse)
        bm.faces.new((vs0[i], vs0[j], vs1[j], vs1[i]))
    for s in (1, -1):
        Q(bm, (xe + 0.4, s * 1.0, 0.15), (0.65, 2.0, 0.05), 0)
    Q(bm, (xe - 0.45, 0.10, 1.75), (0.3, 0.12, 0.3), 0)  # Heckrotor-Getriebe (Rotor liegt am Boden)
    txt = bmesh.new()
    mx = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0))).transposed().to_4x4()
    mx.translation = Vector((-1.8, 0.34, 0.18))
    V.text_mesh(bm, opt.get("nummer", "4K-2207"), 0.26, mx, 1, extrude=0.001, aufloesung=3)
    txt.free()
    ob = OB(f"{name}_Leitwerk", bm, col, [M["lack"], M["schrift"]], hinten)
    FT._verdicken(ob, 0.01) if False else None
    hinten.rotation_euler = (math.radians(opt.get("heck_roll", 8)), math.radians(opt.get("heck_knick", -72)), math.radians(opt.get("heck_gier", -10)))
    for o in root.children_recursive:
        o["lack_alter"] = 1.0
        o["verw_korrektur"] = 0.3
    return root


def rotorblatt(name, col, M, laenge=7.6, sehne=0.53, biegung=0.0, parent=None):
    """Rotorblatt (flaches Profil), optional nach unten gebogen (biegung in m an der Spitze)."""
    bm = bmesh.new()
    n = 26
    reihen = []
    for i in range(n + 1):
        t = i / n
        x = t * laenge
        z = -biegung * t ** 2
        c = sehne * (0.6 if t > 0.96 else 1.0)
        prof = [(-c * 0.3, 0.0), (0.0, 0.03), (c * 0.7, 0.01), (c * 0.72, 0.0), (c * 0.7, -0.01), (0.0, -0.02)]
        reihen.append([bm.verts.new((x, y, z + dz)) for y, dz in prof])
    for a, b in zip(reihen, reihen[1:]):
        for k in range(6):
            k1 = (k + 1) % 6
            f = bm.faces.new((a[k], a[k1], b[k1], b[k]))
            f.smooth = True
    bm.faces.new(reihen[0][::-1])
    bm.faces.new(reihen[-1])
    ob = OB(name, bm, col, [M["lack"]], parent)
    ob["lack_alter"] = 1.0
    return ob


def heckrotor(name, col, M):
    bm = bmesh.new()
    ZY(bm, (0, -0.1, 0), (0, 0.1, 0), 0.12, 12, 0)
    for k in range(4):
        a = math.radians(90 * k + 20)
        r = Matrix.Rotation(a, 3, "Y")
        Q(bm, r @ Vector((0.85, 0, 0)), (1.55, 0.03, 0.20), 0, r)
    ob = OB(name, bm, col, [M["lack"]])
    ob["lack_alter"] = 1.0
    return ob


def absturz(boden, col, cfg):
    """Hubschrauber in B21 (2. OG, Nordfassade y = -11,35), Blaetter verstreut, Truemmerfeld darunter."""
    import militaer as MI
    rnd = random.Random(cfg.get("seed", 73))
    M = mats()
    h = bauen("MIL_Hubschrauber", col, rnd, cfg)
    x, y = cfg["pos_xy"]
    z = boden.z(x, -11.0) + cfg["z_ueber_boden"]
    h.location = (x, y, z)
    h.rotation_euler = Euler([math.radians(a) for a in cfg["rot"]], "XYZ")
    bpy.context.view_layer.update()
    # Blatt 1 am Rotorkopf (verbogen, haengt herab)
    kopf = h.matrix_world @ Vector((0.35, 0, 3.2))
    b1 = rotorblatt("MIL_Rotorblatt_1", col, M, 7.4, biegung=2.2)
    b1.location = kopf
    b1.rotation_euler = Euler((math.radians(4), math.radians(cfg.get("blatt1_nick", 14)), math.radians(cfg["blatt1_gier"])), "XYZ")
    # Russfahne an der Fassade ueber dem Einschlagloch (Brand der Triebwerke)
    if cfg.get("russ"):
        r = cfg["russ"]
        z0 = boden.z(x, -11.0) + cfg["z_ueber_boden"] + 2.4 + r["z_ueber_loch"]
        me = bpy.data.meshes.new("MIL_Hubschrauber_Russ")
        me.from_pydata([(r["x"][0], -11.33, z0 - 1.2), (r["x"][1], -11.33, z0 - 1.2), (r["x"][1], -11.33, z0 + r["hoehe"]),
                        (r["x"][0], -11.33, z0 + r["hoehe"])], [], [(0, 1, 2, 3)])
        uvl = me.uv_layers.new(name="UVMap")
        for i, uv in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
            uvl.data[i].uv = uv
        me.materials.append(V.mat_russ())
        ob = bpy.data.objects.new("MIL_Hubschrauber_Russ", me)
        col.objects.link(ob)
    # Blatt 2 + 3 verstreut (Strasse / Vordergrund fuer CAM_Hero_04), Blatt 4 steckt in der Fassade gegenueber
    for k, (p, rot) in enumerate(cfg["blaetter"]):
        b = rotorblatt(f"MIL_Rotorblatt_{k + 2}", col, M, 7.2 if k < 2 else 4.8, biegung=0.15 * k)
        zz = boden.z(p[0], p[1]) + 0.04 if len(p) == 2 else p[2]
        b.location = (p[0], p[1], zz)
        b.rotation_euler = Euler([math.radians(a) for a in rot], "XYZ")
    tr = heckrotor("MIL_Heckrotor", col, M)
    p = cfg["heckrotor"]
    tr.location = (p[0], p[1], boden.z(p[0], p[1]) + 0.12)
    tr.rotation_euler = (math.radians(84), 0, math.radians(p[2]))
    # Truemmerfeld: Schutt-Instanzen + Rumpfbleche + Kisten
    MI.schutthaufen("MIL_Hubschrauber_Truemmer", cfg["truemmer"]["mitte"], cfg["truemmer"]["radius"], 0.45,
                    cfg["truemmer"]["teile"], col, boden, rnd, laengs=1.4)
    bm = bmesh.new()
    for k in range(24):
        cx, cy = cfg["truemmer"]["mitte"][:2]
        px, py = cx + rnd.uniform(-4, 4), cy + rnd.uniform(-2.5, 3.0)
        r = Matrix.Rotation(rnd.uniform(0, 6.28), 3, "Z") @ Matrix.Rotation(rnd.uniform(-0.4, 0.4), 3, "X")
        Q(bm, (px, py, boden.z(px, py) + 0.03), (rnd.uniform(0.3, 1.2), rnd.uniform(0.2, 0.8), 0.008), 0, r)
    ob = OB("MIL_Hubschrauber_Bleche", bm, col, [M["lack"]])
    ob["lack_alter"] = 1.0
    import flotte as FL
    for k, (px, py, rz) in enumerate(cfg.get("kisten", [])):
        FL.kopie("wooden_military_crate", col, (px, py, boden.z(px, py)), math.radians(rz))
    return h
