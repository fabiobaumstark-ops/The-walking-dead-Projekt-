"""Phase 2.6 – Drei Barrikaden mit eigener Geschichte (glaubwuerdig von Menschen gebaut). Parameter: scripts/configs/barrikaden.json

1 Hauptstrasse West: quergestellte Autos (Platzhalter bis Phase 3), Bus-Seitenteil, Wellblech, Paletten,
  mit Ketten verbunden, Durchgang mit Maschendraht-Tor.
2 Querstrasse West: Moebel, Tueren, Matratzen, Reifen, Bretter, Stacheldraht - improvisiert, teils eingestuerzt.
3 Gasse: Holzpalisade aus Brettern mit Stuetzbalken und Keilen, davor angespitzte Pfaehle.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import checkpoint as CP  # noqa: E402
import strassenraum as SR  # noqa: E402
import viertel_lib as V  # noqa: E402

M = {k: i for i, k in enumerate(["lack", "glas", "gummi", "rost", "wellblech", "holz", "palette", "draht", "stoff", "sperrholz", "metall", "bus", "lack2"])}


def mats():
    return [V.material("MAT_Lack_Blau"), V.mat_glas(), V.material("MAT_Gummi"), V.material("MAT_Rost_Dunkel"),
            V.material("MAT_Wellblech"), V.material("MAT_Holz_Bretter_Alt"), V.material("MAT_Holz_Planken"), V.mat_maschendraht(),
            V.material("MAT_Stoff_Plane"), V.material("MAT_Sperrholz"), V.material("MAT_Stahl_Verzinkt"), V.material("MAT_Lack_Gelb"),
            V.material("MAT_Lack_Rot")]


def boden(x, y):
    return CP.boden(x, y)


def kb(bm, m, x0, y0, z0, x1, y1, z1, mat):
    t = bmesh.new()
    V.box(t, x0, y0, z0, x1, y1, z1)
    bmesh.ops.transform(t, matrix=m, verts=t.verts)
    SR.einfuegen(bm, t, mat)


def auto_platzhalter(bm, mitte, yaw, L=4.85, B=1.85, H=1.45, mat=0, kipp=0.0):
    """Grobes Auto mit richtigen Massen (Typ A Limousine) - wird in Phase 3 durch echte Fahrzeuge ersetzt."""
    z = boden(*mitte)
    m = Matrix.Translation((mitte[0], mitte[1], z)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(kipp, 4, "X")
    kb(bm, m, -L / 2, -B / 2, 0.3, L / 2, B / 2, 0.85, mat)
    kb(bm, m, -L * 0.28, -B / 2 + 0.08, 0.85, L * 0.2, B / 2 - 0.08, H - 0.02, M["glas"])
    kb(bm, m, -L * 0.26, -B / 2 + 0.1, H - 0.06, L * 0.18, B / 2 - 0.1, H, mat)
    for sx in (-L * 0.32, L * 0.3):
        for sy in (-B / 2 + 0.12, B / 2 - 0.12):
            p = m @ Vector((sx, sy, 0.32))
            q = m @ Vector((sx, sy + (0.22 if sy > 0 else -0.22) * 0 + 0.0, 0.32))
            d = (m.to_3x3() @ Vector((0, 1, 0))) * 0.11
            SR.rohr(bm, p - d, p + d, 0.32, seg=14, mat=M["gummi"])


def palette(bm, m, rnd):
    """Europaletten-aehnlich 1,2 x 0,8 x 0,14 m (Bretter + Kloetze)."""
    for k in range(5):
        y = -0.4 + 0.05 + k * 0.175
        kb(bm, m, -0.6, y - 0.05, 0.12, 0.6, y + 0.05, 0.14, M["palette"])
    for x in (-0.55, 0, 0.55):
        for y in (-0.35, 0, 0.35):
            kb(bm, m, x - 0.05, y - 0.05, 0.02, x + 0.05, y + 0.05, 0.12, M["palette"])
    for x in (-0.55, 0, 0.55):
        kb(bm, m, x - 0.06, -0.4, 0.0, x + 0.06, 0.4, 0.02, M["palette"])


def kette(cu, a, b, sack=0.15):
    sp = cu.splines.new("POLY")
    n = 16
    sp.points.add(n)
    for k in range(n + 1):
        t = k / n
        p = Vector(a).lerp(Vector(b), t)
        p.z -= sack * 4 * t * (1 - t)
        sp.points[k].co = (*p, 1)


def barrikade1(bm, cu, cfg, rnd):
    c = cfg["hauptstrasse"]
    x = c["x"]
    for a in c["autos"]:
        auto_platzhalter(bm, (x + a["dx"], a["y"]), math.radians(a["richtung"]), mat=a.get("farbe", 0))
    # Bus-Seitenteil (gelb verblasst) auf dem suedlichen Gehweg
    bx, by = x - 1.2, -9.3
    z = boden(bx, by)
    m = Matrix.Translation((bx, by, z)) @ Matrix.Rotation(math.radians(88), 4, "Z") @ Matrix.Rotation(math.radians(-7), 4, "Y")
    kb(bm, m, -3.2, -0.04, 0.3, 3.2, 0.04, 1.2, M["bus"])
    for k in range(5):
        kb(bm, m, -2.9 + k * 1.2, -0.05, 1.2, -2.2 + k * 1.2, 0.05, 1.9, M["glas"] if k % 2 else M["bus"])
    kb(bm, m, -3.2, -0.04, 1.9, 3.2, 0.04, 2.2, M["bus"])
    # Wellblech-Tafeln zwischen den Autos (angelehnt, verschraubt)
    for (y0, y1) in c["wellblech"]:
        for k in range(int((y1 - y0) / 0.9)):
            y = y0 + k * 0.9 + 0.45
            z = boden(x, y)
            m = Matrix.Translation((x + 0.6, y, z)) @ Matrix.Rotation(math.radians(rnd.uniform(-8, 8)), 4, "Z") @ Matrix.Rotation(math.radians(rnd.uniform(8, 16)), 4, "Y")
            kb(bm, m, -0.02, -0.47, 0.0, 0.02, 0.47, rnd.uniform(1.7, 2.1), M["wellblech"])
    # Paletten gestapelt und hochkant
    for (dx, y, n, hoch) in c["paletten"]:
        for k in range(n):
            z = boden(x + dx, y)
            if hoch:
                m = Matrix.Translation((x + dx + k * 0.16, y, z)) @ Matrix.Rotation(math.pi / 2, 4, "Y") @ Matrix.Translation((-0.6, 0, 0))
            else:
                m = Matrix.Translation((x + dx, y, z + k * 0.145)) @ Matrix.Rotation(rnd.uniform(-0.15, 0.15), 4, "Z")
            palette(bm, m, rnd)
    # Tor aus Maschendraht im Durchgang (halb offen)
    g0, g1 = c["tor"]
    z = boden(x, g0)
    for y in (g0, g1):
        SR.rohr(bm, (x, y, z - 0.3), (x, y, z + 2.2), 0.04, seg=8, mat=M["metall"])
    ang = math.radians(35)
    p0 = Vector((x, g0, z))
    d = Vector((math.sin(ang), math.cos(ang), 0)) * (g1 - g0 - 0.1)
    for (a, b) in ((p0 + Vector((0, 0.05, 0.1)), p0 + d + Vector((0, 0, 0.1))), (p0 + Vector((0, 0.05, 2.0)), p0 + d + Vector((0, 0, 2.0))),
                   (p0 + d + Vector((0, 0, 0.1)), p0 + d + Vector((0, 0, 2.0)))):
        SR.rohr(bm, a, b, 0.02, seg=6, mat=M["metall"])
    vs = [p0 + Vector((0, 0.05, 0.12)), p0 + d + Vector((0, 0, 0.12)), p0 + d + Vector((0, 0, 1.98)), p0 + Vector((0, 0.05, 1.98))]
    f = bm.faces.new([bm.verts.new(v) for v in vs])
    f.material_index = M["draht"]
    # Ketten zwischen den Autos
    for (ya, yb) in c["ketten"]:
        kette(cu, (x, ya, boden(x, ya) + 0.6), (x, yb, boden(x, yb) + 0.6))


def barrikade2(bm, cu, cfg, rnd):
    """Improvisiert aus Moebeln, Tueren, Matratzen, Reifen, Brettern - teils eingestuerzt."""
    c = cfg["querstrasse"]
    y = c["y"]
    for k in range(c["teile"]):
        x = rnd.uniform(c["x0"], c["x1"])
        art = rnd.random()
        z = boden(x, y)
        stack = rnd.uniform(0, 0.9)
        m = Matrix.Translation((x, y + rnd.uniform(-0.8, 0.8), z + stack * rnd.random())) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z") @ Matrix.Rotation(rnd.uniform(-0.5, 0.5), 4, "X")
        if art < 0.2:  # Schrank
            kb(bm, m, -0.5, -0.3, 0, 0.5, 0.3, 1.9, M["holz"])
        elif art < 0.38:  # Tuer
            kb(bm, m, -0.45, -0.025, 0, 0.45, 0.025, 2.05, M["sperrholz"] if rnd.random() < 0.5 else M["holz"])
        elif art < 0.52:  # Matratze
            kb(bm, m, -0.95, -0.7, 0, 0.95, 0.7, 0.2, M["stoff"])
        elif art < 0.66:  # Reifenstapel
            for j in range(rnd.randint(2, 4)):
                p = m @ Vector((0, 0, 0.12 + j * 0.24))
                SR.rohr(bm, p - Vector((0, 0, 0.11)), p + Vector((0, 0, 0.11)), 0.33, seg=14, mat=M["gummi"])
        elif art < 0.8:  # Bretter
            kb(bm, m, -1.2, -0.1, 0, 1.2, 0.1, 0.025, M["holz"])
        elif art < 0.9:  # Tisch
            kb(bm, m, -0.7, -0.45, 0.72, 0.7, 0.45, 0.76, M["holz"])
            for (a, b) in ((-0.65, -0.4), (0.65, -0.4), (-0.65, 0.4), (0.65, 0.4)):
                kb(bm, m, a - 0.03, b - 0.03, 0, a + 0.03, b + 0.03, 0.72, M["holz"])
        else:  # Sofa
            kb(bm, m, -0.9, -0.45, 0, 0.9, 0.45, 0.45, M["stoff"])
            kb(bm, m, -0.9, 0.3, 0.45, 0.9, 0.45, 0.85, M["stoff"])
    # Stacheldraht ueber der Barrikade (Spirale, flach)
    CP.concertina(cu, Vector((c["x0"], y + 0.3, 0)), Vector((c["x1"], y + 0.3, 0)), rnd, hoehe_mitte=1.3, radius=0.3, riss=[2.0, 3.5])


def barrikade3(bm, cfg, rnd):
    """Palisade in der Gasse: Bretter 2,2 m mit Spitzen, 2 Riegel, Stuetzbalken mit Keilen, Pfaehle davor."""
    c = cfg["gasse"]
    x = c["x"]
    y0, y1 = c["y0"], c["y1"]
    y = y0
    while y < y1 - 0.05:
        w = rnd.uniform(0.18, 0.26)
        z = boden(x, y + w / 2)
        h = rnd.uniform(2.05, 2.35)
        m = Matrix.Translation((x, y + w / 2, z)) @ Matrix.Rotation(math.radians(rnd.uniform(-2, 2)), 4, "X")
        kb(bm, m, -0.012, -w / 2 + 0.005, 0, 0.012, w / 2 - 0.005, h, M["holz"])
        t = bmesh.new()  # Spitze
        vs = [t.verts.new(p) for p in ((-0.012, -w / 2 + 0.005, h), (0.012, -w / 2 + 0.005, h), (0.012, w / 2 - 0.005, h), (-0.012, w / 2 - 0.005, h), (0, 0, h + 0.18))]
        t.faces.new(vs[:4][::-1])
        for i in range(4):
            t.faces.new((vs[i], vs[(i + 1) % 4], vs[4]))
        bmesh.ops.transform(t, matrix=m, verts=t.verts)
        SR.einfuegen(bm, t, M["holz"])
        y += w
    for zz in (0.5, 1.6):  # Riegel hinten (Gassenseite Ost)
        z = boden(x, y0)
        kb(bm, Matrix.Translation((x + 0.06, 0, z)), -0.04, y0, zz, 0.04, y1, zz + 0.12, M["holz"])
    for yy in (y0 + 0.8, (y0 + y1) / 2, y1 - 0.8):  # Stuetzbalken schraeg mit Keil am Boden
        z = boden(x, yy)
        a = Vector((x + 0.12, yy, z + 1.7))
        b = Vector((x + 1.6, yy, boden(x + 1.6, yy) + 0.05))
        SR.rohr(bm, a, b, 0.055, seg=6, mat=M["holz"])
        kb(bm, Matrix.Translation((x + 1.75, yy, boden(x + 1.75, yy))), -0.12, -0.08, 0, 0.12, 0.08, 0.1, M["holz"])
    for k in range(c["pfaehle"]):  # angespitzte Pfaehle davor (Westseite)
        yy = y0 + 0.3 + (y1 - y0 - 0.6) * k / max(1, c["pfaehle"] - 1)
        z = boden(x - 1.0, yy)
        a = Vector((x - 0.6, yy, z - 0.2))
        b = Vector((x - 1.9, yy + rnd.uniform(-0.2, 0.2), z + 0.9))
        SR.rohr(bm, a, b, 0.05, seg=6, mat=M["holz"], r2=0.005)


def bauen():
    cfg = V.config("barrikaden.json")
    rnd = random.Random(cfg["seed"])
    col = V.collection("06_Checkpoint_Barrikaden/Barrikaden")
    cu = bpy.data.curves.new("CHK_Barrikaden_Ketten_Draht", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.006
    for nr, fn in ((1, barrikade1), (2, barrikade2), (3, barrikade3)):
        bm = bmesh.new()
        if nr == 3:
            fn(bm, cfg, rnd)
        else:
            fn(bm, cu, cfg, rnd)
        ob = V.objekt_aus_bmesh(f"CHK_Barrikade_{nr}", bm, col, material=mats())
        V.fase(ob, 0.008, 1, winkel=40)
        if nr == 1:
            ob["info"] = "Autos = Platzhalter (Typ A/E/F), werden in Phase 3 ersetzt"
    ob = bpy.data.objects.new("CHK_Barrikaden_Ketten_Draht", cu)
    cu.materials.append(V.material("MAT_Rost_Dunkel"))
    col.objects.link(ob)
