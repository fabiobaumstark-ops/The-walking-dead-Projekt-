"""Phase 2.5 – Militaerischer Checkpoint (Variante A: Ortsausgang Ost). Parameter: scripts/configs/checkpoint.json

Sandsaecke (einzeln verformt, im Verband, aufgeplatzt), Gabionen, Jersey-Barrieren (Schikane), Concertina-Draht
(Pyramide 2+1), 2 Container (einer offen mit Feldbetten), 2 Zelte, Wachturm 5 m, Schranke, Absperrgitter,
Scheinwerfer, Generator, Kabeltrommeln, Kisten, Kanister, Warnschilder mit erfundenen allgemeinen Texten.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import strassenraum as SR  # noqa: E402
import viertel_lib as V  # noqa: E402

RND = None


def boden(x, y):
    return SR.fahrbahn_z(x, y) if SR.ist_fahrbahn(x, y) else SR.gehweg_z(x, y)


# ------------------------------------------------------------------ Sandsaecke
def sandsack_prototypen():
    col = V.prototypen("Sandsaecke")
    rnd = random.Random(5)
    mats = [V.material("MAT_Sackleinen"), V.material("MAT_Sandsack_Oliv")]
    for k in range(6):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=4, use_grid_fill=True)
        geplatzt = k == 5
        for v in bm.verts:
            x, y, z = v.co
            # gefuellter Sack: abgerundet, oben gewoelbt, Enden zusammengezogen
            r = (abs(x) * 2) ** 3
            v.co.y *= 1 - 0.25 * r
            v.co.z *= 1 - 0.35 * r
            v.co.x *= 0.5
            v.co.y *= 0.3
            v.co.z = (v.co.z + 0.5) * (0.15 if not geplatzt else 0.09)
            v.co.z += 0.02 * math.cos(v.co.x * 6) * (1 if z > 0 else 0)
            v.co += Vector((rnd.uniform(-0.008, 0.008), rnd.uniform(-0.008, 0.008), rnd.uniform(-0.006, 0.006)))
        for f in bm.faces:
            f.smooth = True
        zmin = min(v.co.z for v in bm.verts)
        for v in bm.verts:
            v.co.z -= zmin
        ob = V.objekt_aus_bmesh(f"CHK_Sandsack_V{k + 1}", bm, col, material=mats[k % 2])
    return col


def sandsackwand(punkte, start, richtung, laenge, lagen=8, reihen=2, rnd=None, luecke=None):
    """Sandsackwand im Verband: Lagen 15 cm, Saecke 50 x 30 cm, versetzt wie Mauerwerk; leicht nach hinten geneigt."""
    d = Vector(richtung).normalized()
    n = Vector((-d.y, d.x))
    for lage in range(lagen):
        versatz = 0.25 if lage % 2 else 0.0
        for reihe in range(reihen):
            s = -versatz
            while s < laenge - 0.2:
                if luecke and luecke[0] < s < luecke[1]:
                    s += 0.5
                    continue
                if rnd.random() < 0.03 and lage > lagen - 3:  # fehlende Saecke oben
                    s += 0.5
                    continue
                p = Vector(start) + d * (s + 0.25) + n * (reihe * 0.3 + 0.15 - lage * 0.012)
                z = boden(p.x, p.y) + lage * 0.135 + rnd.uniform(-0.01, 0.01)
                idx = 5 if (rnd.random() < 0.04 and lage < 3) else rnd.randrange(5)
                yaw = math.atan2(d.y, d.x) + rnd.uniform(-0.07, 0.07)
                punkte.append(((p.x, p.y, z), (rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), yaw),
                               (rnd.uniform(0.93, 1.07), rnd.uniform(0.93, 1.07), rnd.uniform(0.9, 1.05)), idx))
                s += 0.5


def sandkegel(bm, x, y, r, h):
    z = boden(x, y)
    bmesh.ops.create_cone(bm, cap_ends=False, segments=14, radius1=r, radius2=0.02, depth=h,
                          matrix=Matrix.Translation((x, y, z + h / 2 - 0.02)) @ Matrix.Diagonal((1, 0.7, 1, 1)))


# ------------------------------------------------------------------ Jersey-Barriere
def jersey(bm, mitte, yaw, laenge, rnd, mat=0):
    """New-Jersey-Profil: Fuss 0,61 m, Hoehe 0,81 m (Recherche), abgeplatzte Kanten, Hebeoesen."""
    prof = [(-0.305, 0.0), (-0.305, 0.076), (-0.229, 0.33), (-0.08, 0.81), (0.08, 0.81), (0.229, 0.33), (0.305, 0.076), (0.305, 0.0)]
    tmp = bmesh.new()
    n_seg = 8
    ringe = []
    for k in range(n_seg + 1):
        x = -laenge / 2 + laenge * k / n_seg
        ring = []
        for (y, z) in prof:
            dy = dz = 0.0
            if k in (0, n_seg) or (z > 0.7 and rnd.random() < 0.25):
                dy, dz = rnd.uniform(-0.03, 0.03), -rnd.uniform(0, 0.05) if z > 0.3 else 0
            ring.append(tmp.verts.new((x + (rnd.uniform(-0.04, 0.04) if k in (0, n_seg) else 0), y + dy, z + dz)))
        ringe.append(ring)
    for k in range(n_seg):
        a, b = ringe[k], ringe[k + 1]
        for i in range(len(prof) - 1):
            tmp.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
        tmp.faces.new((a[-1], b[-1], b[0], a[0]))
    tmp.faces.new(ringe[0][::-1])
    tmp.faces.new(ringe[-1])
    bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
    for s in (-laenge / 3, laenge / 3):  # Hebeoesen
        SR.rohr(tmp, (s - 0.06, 0, 0.81), (s - 0.06, 0, 0.9), 0.012, seg=5, mat=1)
        SR.rohr(tmp, (s + 0.06, 0, 0.81), (s + 0.06, 0, 0.9), 0.012, seg=5, mat=1)
        SR.rohr(tmp, (s - 0.06, 0, 0.9), (s + 0.06, 0, 0.9), 0.012, seg=5, mat=1)
    z = boden(*mitte)
    bmesh.ops.transform(tmp, matrix=Matrix.Translation((mitte[0], mitte[1], z - 0.01)) @ Matrix.Rotation(yaw, 4, "Z"), verts=tmp.verts)
    SR.einfuegen(bm, tmp, None)


# ------------------------------------------------------------------ Gabionen
def gabione(bm, mitte, yaw, rnd, mat_draht=1, mat_vlies=2, mat_sand=3):
    """Drahtkorb 1,37 x 1,06 x 1,0 m (MIL1-aehnlich) mit Vlies und Fuellung; Vlies teils zerrissen."""
    gx, gy, gz = 1.37, 1.06, 1.0
    z = boden(*mitte)
    m = Matrix.Translation((mitte[0], mitte[1], z)) @ Matrix.Rotation(yaw, 4, "Z")
    t = bmesh.new()
    V.box(t, -gx / 2, -gy / 2, 0, gx / 2, gy / 2, gz)
    for f in t.faces:
        f.material_index = mat_draht
    bmesh.ops.transform(t, matrix=m, verts=t.verts)
    SR.einfuegen(bm, t, mat_draht)
    t = bmesh.new()  # Vlies (leicht ausgebeult), teils fehlend
    bmesh.ops.create_cube(t, size=1.0)
    bmesh.ops.subdivide_edges(t, edges=list(t.edges), cuts=3, use_grid_fill=True)
    for v in t.verts:
        v.co.x *= gx - 0.03
        v.co.y *= gy - 0.03
        v.co.z = (v.co.z + 0.5) * (gz - 0.05)
        if 0.05 < v.co.z < gz - 0.1:
            v.co.x *= 1 + 0.03 * (1 - abs(v.co.z - gz / 2) * 2)
            v.co.y *= 1 + 0.03 * (1 - abs(v.co.z - gz / 2) * 2)
    loecher = [f for f in t.faces if rnd.random() < 0.12 and f.calc_center_median().z < gz - 0.2 and abs(f.normal.z) < 0.5]
    bmesh.ops.delete(t, geom=loecher, context="FACES")
    bmesh.ops.transform(t, matrix=m, verts=t.verts)
    SR.einfuegen(bm, t, mat_vlies)
    if loecher:  # rieselnde Fuellung
        p = m @ Vector((gx / 2 + 0.25, 0, 0))
        sandkegel_bm = bmesh.new()
        sandkegel(sandkegel_bm, p.x, p.y, 0.45, 0.25)
        SR.einfuegen(bm, sandkegel_bm, mat_sand)


# ------------------------------------------------------------------ Concertina
def concertina(cu, a, b, rnd, hoehe_mitte=0.475, radius=0.475, riss=None):
    """Spirale (Ø 0,95 m, ~0,27 m je Windung) entlang a->b."""
    a, b = Vector(a), Vector(b)
    d = (b - a)
    L = d.length
    d.normalize()
    n = Vector((-d.y, d.x, 0))
    windungen = L / 0.27
    steps = int(windungen * 12)
    sp = None
    for k in range(steps + 1):
        s = L * k / steps
        if riss and riss[0] < s < riss[1]:
            sp = None
            continue
        if sp is None:
            sp = cu.splines.new("POLY")
            first = True
        th = 2 * math.pi * windungen * k / steps
        sack = 1.0 - 0.25 * max(0, noise.noise(Vector((s * 0.3, a.x * 0.1, 3.1))))
        r = radius * sack
        p = a + d * s + n * (r * math.cos(th))
        zb = boden(p.x, p.y)
        p.z = zb + hoehe_mitte * sack + r * math.sin(th)
        p.z = max(p.z, zb + 0.01)
        if first:
            sp.points[0].co = (*p, 1)
            first = False
        else:
            sp.points.add(1)
            sp.points[-1].co = (*p, 1)


# ------------------------------------------------------------------ Container, Zelt, Turm, Kleinteile
def container(bm, mitte, yaw, offen, rnd, mats):
    """20-Fuss-Container 6,06 x 2,44 x 2,59 m: Wellwaende, Eckbeschlaege, Tueren mit Verriegelungsstangen."""
    L, B, H = 6.06, 2.44, 2.59
    z = boden(*mitte)
    m = Matrix.Translation((mitte[0], mitte[1], z)) @ Matrix.Rotation(yaw, 4, "Z")
    def kb(x0, y0, z0, x1, y1, z1, mat):
        t = bmesh.new()
        V.box(t, x0, y0, z0, x1, y1, z1)
        bmesh.ops.transform(t, matrix=m, verts=t.verts)
        SR.einfuegen(bm, t, mat)
    w = 0.04
    kb(-L / 2, -B / 2, 0, L / 2, -B / 2 + w, H, mats["wand"])
    kb(-L / 2, B / 2 - w, 0, L / 2, B / 2, H, mats["wand"])
    kb(-L / 2, -B / 2, H - w, L / 2, B / 2, H, mats["wand"])
    kb(-L / 2, -B / 2, 0, L / 2, B / 2, 0.16, mats["rahmen"])
    kb(-L / 2, -B / 2, 0, -L / 2 + w, B / 2, H, mats["wand"])
    for (x, y) in ((-L / 2, -B / 2), (L / 2, -B / 2), (-L / 2, B / 2), (L / 2, B / 2)):
        for zz in (0, H - 0.12):
            kb(x - 0.09 * (1 if x > 0 else -1) * 0 - 0.09, y - 0.09, zz, x + 0.09, y + 0.09, zz + 0.12, mats["rahmen"])
    for zz in (0.0, H - 0.18):
        kb(L / 2 - 0.15, -B / 2, zz, L / 2, B / 2, zz + 0.18, mats["rahmen"])
    for (y0, y1, sgn) in ((-B / 2, 0.0, -1), (0.0, B / 2, 1)):  # Tueren
        if offen:
            t = bmesh.new()
            V.box(t, 0, 0, 0.18, 0.05, (y1 - y0), H - 0.2)
            ang = sgn * math.radians(rnd.uniform(95, 160))
            piv = Vector((L / 2, y0 if sgn < 0 else y1, 0))
            bmesh.ops.translate(t, verts=t.verts, vec=(0, -(y1 - y0) if sgn > 0 else 0, 0))
            bmesh.ops.rotate(t, verts=t.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-ang, 3, "Z"))
            bmesh.ops.translate(t, verts=t.verts, vec=piv)
            bmesh.ops.transform(t, matrix=m, verts=t.verts)
            SR.einfuegen(bm, t, mats["wand"])
        else:
            kb(L / 2 - 0.02, y0 + 0.01, 0.18, L / 2 + 0.03, y1 - 0.01, H - 0.2, mats["wand"])
            for yy in (y0 + 0.25, y1 - 0.25):
                kb(L / 2 + 0.03, yy - 0.02, 0.2, L / 2 + 0.07, yy + 0.02, H - 0.22, mats["rost"])
    if offen:  # Feldbetten + Kisten innen
        for k in range(2):
            y = -0.6 + k * 1.2
            kb(-2.4, y - 0.33, 0.55, -0.4, y + 0.33, 0.6, mats["stoff"])
            for xx in (-2.35, -0.45):
                kb(xx - 0.02, y - 0.33, 0.16, xx + 0.02, y + 0.33, 0.55, mats["rahmen"])
        for k in range(3):
            kb(1.0 + k * 0.55, -0.9, 0.16, 1.5 + k * 0.55, -0.4, 0.16 + rnd.uniform(0.3, 0.5), mats["holz"])


def zelt(bm, mitte, yaw, rnd, mats):
    """Militaerzelt 6 x 5 m: Plane durchhaengend, Risse, Abspannseile, Heringe; Feldbetten und Tisch innen."""
    L, B, wand, first = 6.0, 5.0, 1.7, 3.0
    z0 = boden(*mitte)
    m = Matrix.Translation((mitte[0], mitte[1], z0)) @ Matrix.Rotation(yaw, 4, "Z")
    t = bmesh.new()
    nx, ny = 12, 10
    grid = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = -L / 2 + L * i / nx
            v = j / ny  # 0..1 ueber den Querschnitt: Wand - Dach - Wand
            if v < 0.2:
                y, z = -B / 2, wand * (v / 0.2)
            elif v > 0.8:
                y, z = B / 2, wand * ((1 - v) / 0.2)
            else:
                q = (v - 0.2) / 0.6
                y = -B / 2 + B * q
                z = wand + (first - wand) * (1 - abs(q - 0.5) * 2)
                sack = 0.25 * math.sin(math.pi * q * 2) ** 2 * math.sin(math.pi * (i % 4) / 4) ** 2
                z -= sack + rnd.uniform(0, 0.04)
            grid[i, j] = t.verts.new((x, y, max(z, 0.02)))
    for i in range(nx):
        for j in range(ny):
            if rnd.random() < 0.07 and 1 < j < ny - 1:
                continue  # Riss
            t.faces.new((grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]))
    bmesh.ops.transform(t, matrix=m, verts=t.verts)
    SR.einfuegen(bm, t, mats["plane"])
    for sx in (-L / 2, 0, L / 2):  # Stangen + Abspannseile
        a = m @ Vector((sx, 0, 0))
        SR.rohr(bm, a, m @ Vector((sx, 0, first)), 0.03, seg=6, mat=mats["rahmen"])
        for sy in (-1, 1):
            p = m @ Vector((sx, sy * B / 2, wand))
            q = m @ Vector((sx, sy * (B / 2 + 1.6), 0))
            q.z = boden(q.x, q.y)
            SR.rohr(bm, p, q, 0.005, seg=4, mat=mats["seil"])
            SR.rohr(bm, q - Vector((0, 0, 0.2)), q + Vector((0, 0, 0.1)), 0.012, seg=4, mat=mats["rahmen"])
    for k in range(3):
        y = -1.6 + k * 1.6
        t = bmesh.new()
        V.box(t, -1.0, y - 0.33, 0.4, 1.0, y + 0.33, 0.45)
        bmesh.ops.transform(t, matrix=m, verts=t.verts)
        SR.einfuegen(bm, t, mats["stoff"])
    t = bmesh.new()
    V.box(t, 1.6, -0.6, 0.72, 2.4, 0.6, 0.76)
    bmesh.ops.transform(t, matrix=m, verts=t.verts)
    SR.einfuegen(bm, t, mats["holz"])


def wachturm(bm, x, y, rnd, mats, punkte_sack):
    """Gerüstrohr-Turm 5 m, Plattform 2,5 x 2,5 m mit Sandsaecken, Leiter, zerrissenes Tarnnetz."""
    z0 = boden(x, y)
    hz = 5.0
    ecken = [(x + dx, y + dy) for dx in (0, 2.5) for dy in (0, 2.5)]
    for (cx, cy) in ecken:
        SR.rohr(bm, (cx, cy, z0), (cx, cy, z0 + hz + 1.1), 0.024, seg=8, mat=mats["rohr"])
    for zz in (z0 + 1.6, z0 + 3.3, z0 + hz):
        for (a, b) in ((0, 1), (1, 3), (3, 2), (2, 0)):
            SR.rohr(bm, (*ecken[a], zz), (*ecken[b], zz), 0.024, seg=8, mat=mats["rohr"])
    for (a, b) in ((0, 1), (2, 3)):  # Diagonalen
        SR.rohr(bm, (*ecken[a], z0 + 0.1), (*ecken[b], z0 + 1.6), 0.024, seg=6, mat=mats["rohr"])
        SR.rohr(bm, (*ecken[b], z0 + 1.6), (*ecken[a], z0 + 3.3), 0.024, seg=6, mat=mats["rohr"])
    for k in range(10):  # Plattform-Bohlen
        V.box(bm, x + k * 0.25, y, z0 + hz, x + k * 0.25 + 0.23, y + 2.5, z0 + hz + 0.05)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[-6:]:
            f.material_index = mats["holz"]
    for k in range(int(hz / 0.3)):  # Leiter
        zz = z0 + 0.3 + k * 0.3
        SR.rohr(bm, (x + 2.5, y + 1.0, zz), (x + 2.5, y + 1.5, zz), 0.015, seg=5, mat=mats["rohr"])
    SR.rohr(bm, (x + 2.55, y + 1.0, z0), (x + 2.55, y + 1.0, z0 + hz + 1.0), 0.02, seg=5, mat=mats["rohr"])
    SR.rohr(bm, (x + 2.55, y + 1.5, z0), (x + 2.55, y + 1.5, z0 + hz + 1.0), 0.02, seg=5, mat=mats["rohr"])
    for (sx, sy, dx, dy, L) in ((x, y, 1, 0, 2.5), (x, y + 2.5, 1, 0, 2.5), (x, y, 0, 1, 2.5)):  # Saecke auf der Plattform
        for lage in range(4):
            s = 0.0 if lage % 2 == 0 else 0.25
            while s < L - 0.3:
                p = Vector((sx, sy)) + Vector((dx, dy)) * (s + 0.25)
                punkte_sack.append(((p.x, p.y, z0 + hz + 0.05 + lage * 0.135), (0, 0, math.atan2(dy, dx) + rnd.uniform(-0.08, 0.08)), (1, 1, 1), rnd.randrange(5)))
                s += 0.5
    t = bmesh.new()  # Tarnnetz (zerrissen, haengt)
    for i in range(8):
        for j in range(8):
            if rnd.random() < 0.3:
                continue
            u0, u1, v0, v1 = i / 8 * 3.0 - 0.25, (i + 1) / 8 * 3.0 - 0.25, j / 8 * 3.0 - 0.25, (j + 1) / 8 * 3.0 - 0.25
            pts = [(x + u, y + v, z0 + hz + 2.0 - 0.4 * math.sin(math.pi * u / 2.5) * math.sin(math.pi * v / 2.5) - (1.5 if (u > 2.0 and v < 0.6) else 0)) for (u, v) in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]
            t.faces.new([t.verts.new(p) for p in pts])
    SR.einfuegen(bm, t, mats["netz"])


def kleinkram(bm, cfg, rnd, mats):
    k = cfg["kleinteile"]
    # Schranke (rot-weiss verblasst): Pfosten + Schlagbaum, gesenkt / abgeknickt
    sx, sy = k["schranke"]
    z = boden(sx, sy)
    SR.rohr(bm, (sx, sy, z), (sx, sy, z + 1.0), 0.06, seg=10, mat=mats["rot"])
    for i in range(8):
        a = Vector((sx, sy + 0.5 * i, z + 0.95 - 0.02 * i))
        b = Vector((sx, sy + 0.5 * (i + 1), z + 0.95 - 0.02 * (i + 1)))
        SR.rohr(bm, a, b, 0.045, seg=8, mat=mats["rot"] if i % 2 == 0 else mats["weiss"])
    # Absperrgitter
    for (x, y, yaw) in k["absperrgitter"]:
        z = boden(x, y)
        d = Vector((math.cos(yaw), math.sin(yaw), 0))
        a, b = Vector((x, y, z)) - d * 1.1, Vector((x, y, z)) + d * 1.1
        for q in (a, b):
            SR.rohr(bm, q, q + Vector((0, 0, 1.05)), 0.02, seg=6, mat=mats["rohr"])
        SR.rohr(bm, a + Vector((0, 0, 1.05)), b + Vector((0, 0, 1.05)), 0.02, seg=6, mat=mats["rohr"])
        SR.rohr(bm, a + Vector((0, 0, 0.2)), b + Vector((0, 0, 0.2)), 0.02, seg=6, mat=mats["rohr"])
        for i in range(12):
            q = a.lerp(b, (i + 0.5) / 12)
            SR.rohr(bm, q + Vector((0, 0, 0.2)), q + Vector((0, 0, 1.05)), 0.008, seg=4, mat=mats["rohr"])
    # Scheinwerfer auf Stativ (kaputt)
    x, y = k["scheinwerfer"]
    z = boden(x, y)
    for a in (0, 2.1, 4.2):
        SR.rohr(bm, (x + math.cos(a) * 0.6, y + math.sin(a) * 0.6, z), (x, y, z + 1.8), 0.02, seg=5, mat=mats["rohr"])
    SR.rohr(bm, (x, y, z + 1.8), (x, y, z + 2.6), 0.03, seg=6, mat=mats["rohr"])
    SR.kasten(bm, (x, y, z + 2.75), (0.55, 0.3, 0.45), rot=(0.3, 0, 2.6), mat=mats["oliv"])
    # Generator, Kabeltrommeln, Kisten, Kanister
    x, y = k["generator"]
    z = boden(x, y)
    SR.kasten(bm, (x, y, z + 0.5), (1.3, 0.8, 0.9), mat=mats["oliv"])
    SR.rohr(bm, (x + 0.5, y, z + 0.95), (x + 0.5, y, z + 1.4), 0.03, seg=6, mat=mats["rost"])
    for (x, y) in k["kabeltrommeln"]:
        z = boden(x, y)
        for dz in (0.0, 0.62):
            SR.rohr(bm, (x, y - 0.32 + dz, z + 0.5), (x, y - 0.27 + dz, z + 0.5), 0.5, seg=18, mat=mats["holz"])
        SR.rohr(bm, (x, y - 0.27, z + 0.5), (x, y + 0.3, z + 0.5), 0.3, seg=14, mat=mats["gummi"])


def schilder(bm, cfg, rnd, mats):
    """Warnschilder (Sperrholz) mit erfundenen allgemeinen Texten."""
    for s in cfg["schilder"]:
        x, y = s["pos"]
        z = boden(x, y)
        yaw = math.radians(s["richtung"])
        w, hh = s["groesse"]
        m = Matrix.Translation((x, y, z + s.get("hoehe", 1.4))) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(math.radians(s.get("kipp", 0)), 4, "Y") @ Matrix.Rotation(math.pi / 2, 4, "X")
        t = bmesh.new()
        V.box(t, -w / 2, -hh / 2, -0.01, w / 2, hh / 2, 0.01)
        SR.einfuegen_m(bm, t, m, mats["sperrholz"])
        V.text_mesh(bm, s["text"], s.get("schrift", 0.22), m @ Matrix.Translation((0, 0, 0.012)), mats["schrift_rot"] if s.get("rot") else mats["schrift"], extrude=0.0)
        if s.get("pfosten", True):
            for dx in (-w / 2 + 0.1, w / 2 - 0.1):
                p = m @ Vector((dx, -hh / 2, 0))
                SR.rohr(bm, (p.x, p.y, z - 0.3), (p.x, p.y, p.z + hh), 0.04, seg=6, mat=mats["holz"])


def extras(bm, cu_kabel, cfg, rnd, mats, punkte_sack):
    """3B: Spuren von Menschen - Kistenstapel, Munitions-/Rationskisten, Schlafsaecke, Feldbett draussen,
    Feuerstelle, Waescheleine, Plane als Unterstand, Kabel am Boden, Helme, Stiefel, Schablonen-Texte."""
    E = cfg["extras"]
    for w in E["sandsackwaende"]:
        sandsackwand(punkte_sack, w["start"], w["richtung"], w["laenge"], w.get("lagen", 6), w.get("reihen", 2), rnd)
    for (x, y, n, yaw) in E["kistenstapel"]:
        z = boden(x, y)
        for k in range(n):
            gr = (0.9, 0.5, 0.45) if k % 2 == 0 else (0.6, 0.4, 0.35)
            SR.kasten(bm, (x + rnd.uniform(-0.05, 0.05), y + rnd.uniform(-0.05, 0.05), z + 0.25 + k * 0.45), gr, rot=(0, 0, yaw + rnd.uniform(-0.15, 0.15)), mat=mats["oliv"])
    m_txt = mats["schrift"]
    for (x, y, yaw, text) in E["kisten_text"]:
        z = boden(x, y)
        SR.kasten(bm, (x, y, z + 0.2), (0.7, 0.4, 0.4), rot=(0, 0, yaw), mat=mats["holz"])
        m = Matrix.Translation((x, y, z + 0.41)) @ Matrix.Rotation(yaw, 4, "Z")
        V.text_mesh(bm, text, 0.09, m, m_txt, extrude=0.0)
    for (x, y, yaw) in E["schlafsaecke"]:
        z = boden(x, y)
        SR.rohr(bm, Vector((x, y, z + 0.13)) - Vector((math.cos(yaw), math.sin(yaw), 0)) * 0.3,
                Vector((x, y, z + 0.13)) + Vector((math.cos(yaw), math.sin(yaw), 0)) * 0.3, 0.13, seg=12, mat=mats["vlies"])
    for (x, y, yaw) in E["feldbetten"]:
        z = boden(x, y)
        mk = Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, "Z")
        t = bmesh.new()
        V.box(t, -1.0, -0.33, 0.42, 1.0, 0.33, 0.46)
        SR.einfuegen_m(bm, t, mk, mats["stoff"])
        for (a_, b_) in ((-0.95, -0.33), (0.95, -0.33), (-0.95, 0.33), (0.95, 0.33)):
            t = bmesh.new()
            V.box(t, a_ - 0.02, b_ - 0.02, 0, a_ + 0.02, b_ + 0.02, 0.42)
            SR.einfuegen_m(bm, t, mk, mats["rohr"])
    fx, fy = E["feuerstelle"]  # Steinring, Asche, verkohlte Hoelzer
    z = boden(fx, fy)
    for k in range(10):
        a_ = 2 * math.pi * k / 10
        SR.kasten(bm, (fx + math.cos(a_) * 0.55, fy + math.sin(a_) * 0.55, z + 0.07), (0.2, 0.16, 0.14), rot=(rnd.uniform(-0.3, 0.3), 0, a_), mat=mats["beton"])
    for k in range(5):
        a_ = rnd.uniform(0, 6.28)
        SR.rohr(bm, (fx + math.cos(a_) * 0.4, fy + math.sin(a_) * 0.4, z + 0.05), (fx - math.cos(a_) * 0.2, fy - math.sin(a_) * 0.2, z + 0.1), 0.04, seg=6, mat=mats["rost"])
    SR.rohr(bm, (fx, fy, z - 0.01), (fx, fy, z + 0.015), 0.42, seg=16, mat=mats["asche"])
    (ax, ay), (bx, by) = E["waescheleine"]
    za, zb = boden(ax, ay) + 1.8, boden(bx, by) + 1.8
    sp = cu_kabel.splines.new("POLY")
    sp.points.add(10)
    for k in range(11):
        t = k / 10
        p = Vector((ax, ay, za)).lerp(Vector((bx, by, zb)), t)
        p.z -= 0.25 * 4 * t * (1 - t)
        sp.points[k].co = (*p, 1)
    for k in range(4):  # Kleidung an der Leine
        t = 0.2 + k * 0.18
        p = Vector((ax, ay, za)).lerp(Vector((bx, by, zb)), t)
        p.z -= 0.25 * 4 * t * (1 - t)
        d = (Vector((bx, by, 0)) - Vector((ax, ay, 0))).normalized()
        vs = [p - d * 0.25, p + d * 0.25, p + d * 0.22 - Vector((0, 0, 0.6)), p - d * 0.22 - Vector((0, 0, 0.55))]
        f = bm.faces.new([bm.verts.new(v) for v in vs])
        f.material_index = mats["stoff"] if k % 2 else mats["vlies"]
    px, py, pyaw = E["plane_unterstand"]  # Plane schraeg zwischen Container und zwei Stangen
    z = boden(px, py)
    mk = Matrix.Translation((px, py, z)) @ Matrix.Rotation(pyaw, 4, "Z")
    for dx in (-1.4, 1.4):
        p0 = mk @ Vector((dx, -1.8, 0))
        SR.rohr(bm, p0, p0 + Vector((0, 0, 1.5)), 0.025, seg=6, mat=mats["rohr"])
    vs = [mk @ Vector((-1.6, 0, 2.3)), mk @ Vector((1.6, 0, 2.25)), mk @ Vector((1.5, -1.85, 1.5)), mk @ Vector((-1.5, -1.85, 1.45))]
    f = bm.faces.new([bm.verts.new(v) for v in vs])
    f.material_index = mats["plane"]
    for (pa, pb) in E["kabel"]:  # Kabel am Boden (vom Generator)
        a_, b_ = Vector(pa + [0]), Vector(pb + [0])
        sp = cu_kabel.splines.new("POLY")
        n = 14
        sp.points.add(n)
        for k in range(n + 1):
            t = k / n
            p = a_.lerp(b_, t) + Vector((math.sin(t * 7 + a_.x) * 0.35, math.cos(t * 5) * 0.3, 0))
            p.z = boden(p.x, p.y) + 0.02
            sp.points[k].co = (*p, 1)
    for (x, y) in E["helme"]:
        z = boden(x, y)
        t = bmesh.new()
        bmesh.ops.create_uvsphere(t, u_segments=14, v_segments=7, radius=0.15)
        for v in t.verts:
            v.co.z = max(v.co.z, 0) * 0.9
        bmesh.ops.transform(t, matrix=Matrix.Translation((x, y, z)) @ Matrix.Rotation(rnd.uniform(-2.5, 2.5), 4, "X"), verts=t.verts)
        SR.einfuegen(bm, t, mats["oliv"])
    for (x, y, yaw, text, gr) in E["schablonen"]:  # Schablonen-/Spruehtexte auf Container/Jersey
        z = boden(x, y)
        m = Matrix.Translation((x, y, z + gr[1])) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
        V.text_mesh(bm, text, gr[0], m, mats["schrift_rot"] if "TURN" in text else m_txt, extrude=0.0)


def moos_punkte(punkte_sack, cfg):
    """Moos auf den obersten Sandsack-Lagen und Jersey-Barrieren (fuer vegetation_klein)."""
    out = bpy.app.driver_namespace.setdefault("moos_punkte", [])
    top = {}
    for (p, rot, sk, idx) in punkte_sack:
        k = (round(p[0], 1), round(p[1], 1))
        if k not in top or p[2] > top[k][2]:
            top[k] = p
    for p in top.values():
        out.append((p[0], p[1], p[2] + 0.14, RND.uniform(0.06, 0.16)))
    for j in cfg["jersey"]:
        x, y = j["mitte"]
        for k in range(3):
            d = math.radians(j["richtung"])
            o = RND.uniform(-1.6, 1.6)
            out.append((x + math.cos(d) * o, y + math.sin(d) * o, boden(x, y) + 0.8, RND.uniform(0.05, 0.12)))


def bauen():
    global RND
    cfg = V.config("checkpoint.json")
    RND = rnd = random.Random(cfg["seed"])
    col = V.collection("06_Checkpoint_Barrikaden/Checkpoint")
    proto = sandsack_prototypen()
    punkte = []
    for w in cfg["sandsackwaende"]:
        sandsackwand(punkte, w["start"], w["richtung"], w["laenge"], w.get("lagen", 8), w.get("reihen", 2), rnd, w.get("luecke"))
    mats = {"beton": 0, "rost": 1, "vlies": 2, "sand": 3, "draht": 4, "wand": 5, "rahmen": 6, "stoff": 7, "holz": 8,
            "plane": 9, "seil": 10, "rohr": 11, "netz": 12, "rot": 13, "weiss": 14, "oliv": 15, "gummi": 16,
            "sperrholz": 17, "schrift": 18, "schrift_rot": 19, "asche": 20}
    matlist = [V.material("MAT_Beton_Grob"), V.material("MAT_Rost_Dunkel"), V.material("MAT_Plane_Oliv"), V.material("MAT_Sand"),
               V.mat_maschendraht("MAT_Gabionen_Gitter"), V.material("MAT_Container"), V.material("MAT_Lack_Oliv"),
               V.material("MAT_Stoff_Plane"), V.material("MAT_Holz_Bretter_Alt"), V.material("MAT_Plane_Oliv"),
               V.material("MAT_Gummi"), V.material("MAT_Stahl_Verzinkt"), V.material("MAT_Plane_Oliv"),
               V.material("MAT_Lack_Rot"), V.material("MAT_Lack_Weiss"), V.material("MAT_Lack_Oliv"), V.material("MAT_Gummi"),
               V.material("MAT_Sperrholz"), V.mat_farbe("MAT_Schablone_Schwarz", "#151515", 0.35, "MAT_Beton_Grob", lokal=0.5),
               V.mat_farbe("MAT_Schablone_Rot", "#7A1E18", 0.35, "MAT_Beton_Grob", lokal=0.5),
               V.mat_farbe("MAT_Asche", "#3A3734", 0.1, "MAT_Beton_Grob", rau=0.95, lokal=0.3)]
    bm = bmesh.new()
    for j in cfg["jersey"]:
        jersey(bm, j["mitte"], math.radians(j["richtung"]), j.get("laenge", 3.65), rnd)
    for g in cfg["gabionen"]:
        gabione(bm, g["mitte"], math.radians(g["richtung"]), rnd, mats["draht"], mats["vlies"], mats["sand"])
    for (x, y, r, h) in cfg["sandkegel"]:
        sandkegel(bm, x, y, r, h)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[-14:]:
            f.material_index = mats["sand"]
    for c in cfg["container"]:
        container(bm, c["mitte"], math.radians(c["richtung"]), c.get("offen", False), rnd, mats)
    for z in cfg["zelte"]:
        zelt(bm, z["mitte"], math.radians(z["richtung"]), rnd, mats)
    wachturm(bm, *cfg["wachturm"], rnd, mats, punkte)
    kleinkram(bm, cfg, rnd, mats)
    schilder(bm, cfg, rnd, mats)
    cu_k = bpy.data.curves.new("CHK_Kabel_Leine", "CURVE")
    cu_k.dimensions = "3D"
    cu_k.bevel_depth = 0.012
    extras(bm, cu_k, cfg, rnd, mats, punkte)
    ok = bpy.data.objects.new("CHK_Kabel_Leine", cu_k)
    cu_k.materials.append(V.material("MAT_Gummi"))
    col.objects.link(ok)
    moos_punkte(punkte, cfg)
    ob = V.objekt_aus_bmesh("CHK_Checkpoint", bm, col, material=matlist)
    V.fase(ob, 0.01, 1, winkel=40)
    sack = V.instanzen("CHK_Sandsaecke", punkte, proto, col)
    # Concertina-Draht: Pyramide 2 unten + 1 oben, teils eingerissen
    cu = bpy.data.curves.new("CHK_Concertina", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0035
    for c in cfg["concertina"]:
        a, b = Vector(c["von"] + [0]), Vector(c["bis"] + [0])
        d = (b - a).normalized()
        n = Vector((-d.y, d.x, 0))
        concertina(cu, a - n * 0.48, b - n * 0.48, rnd, riss=c.get("riss"))
        concertina(cu, a + n * 0.48, b + n * 0.48, rnd)
        concertina(cu, a, b, rnd, hoehe_mitte=0.475 + 0.82, riss=c.get("riss_oben"))
        L = (b - a).length
        bm2 = bmesh.new()
        s = 0.0
        while s <= L:
            p = a + d * s
            zz = boden(p.x, p.y)
            SR.rohr(bm2, (p.x, p.y, zz - 0.3), (p.x, p.y, zz + 1.5), 0.02, seg=6, mat=0)
            s += 3.0
        V.objekt_aus_bmesh(f"CHK_Pfosten_{c['name']}", bm2, col, material=V.material("MAT_Rost_Dunkel"))
    obc = bpy.data.objects.new("CHK_Concertina", cu)
    cu.materials.append(V.material("MAT_Stahl_Verzinkt"))
    col.objects.link(obc)
    # Kisten, Kanister, Fass (Poly Haven) als Kopien
    pcol = V.collection("06_Checkpoint_Barrikaden/Checkpoint_Props")
    for (aid, x, y, yaw) in cfg["polyhaven"]:
        for o in V.modell_laden(aid, pcol):
            if o.parent is None and o.type == "MESH":
                o.data = o.data.copy()
                o.data.transform(Matrix.Rotation(math.radians(yaw), 4, "Z") @ o.matrix_basis)  # Rotation anwenden (A5)
                o.matrix_basis = Matrix()
                zmin = min(v.co.z for v in o.data.vertices)
                o.location = (x, y, boden(x, y) - zmin)
    print(f"CHECKPOINT: {len(punkte)} Sandsaecke, {len(cfg['jersey'])} Jersey, {len(cfg['gabionen'])} Gabionen")
