"""Phase 2.3 – Strassenraum: Fahrbahn-Detail (Risse, Schlagloecher, Flicken, Absenkungen, Pfuetzen), Markierungen,
Gullideckel, Gehwegplatten (angehoben), Strommasten + Leitungen, Laternen, Ampeln, Schilder, Hydranten, Stadtmoebel.
Parameter: scripts/configs/strassenraum.json
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "phase1"))
import blockout_umgebung as BU  # noqa: E402
import viertel_lib as V  # noqa: E402

L = None
C = None
RND = None
DETAIL = []  # (x0, y0, x1, y1) Zonen mit feiner Fahrbahn
SENKEN = []  # (x, y, r, tiefe)


# ------------------------------------------------------------------ Hoehenfunktionen
def woelbung(x, y):
    return BU._strassen_zone(x, y, L)[1]


def ist_fahrbahn(x, y):
    return BU._strassen_zone(x, y, L)[0]


def in_detail(x, y):
    return any(a <= x <= c and b <= y <= d for a, b, c, d in DETAIL)


def detail_hoehe(x, y):
    z = 0.0
    for (sx, sy, r, t) in SENKEN:
        d2 = (x - sx) ** 2 + (y - sy) ** 2
        if d2 < (2.2 * r) ** 2:
            z -= t * math.exp(-d2 / (r * r))
    z += 0.006 * noise.noise(Vector((x * 0.9, y * 0.9, 4.2)))
    return z


def fahrbahn_z(x, y):
    z = V.h(x, y) + woelbung(x, y)
    if in_detail(x, y):
        z += detail_hoehe(x, y)
    return z


def gehweg_z(x, y):
    return V.h(x, y) + L["bordstein"]["hoehe"]


# ------------------------------------------------------------------ Helfer
def rohr(bm, a, b, r, seg=8, mat=0, r2=None):
    a, b = Vector(a), Vector(b)
    d = b - a
    if d.length < 1e-4:
        return
    m = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    n0 = len(bm.faces)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length, matrix=m)
    bm.faces.ensure_lookup_table()
    for f in list(bm.faces)[n0:]:
        f.material_index = mat


def kasten(bm, mitte, groesse, rot=(0, 0, 0), mat=0):
    tmp = bmesh.new()
    sx, sy, sz = groesse
    V.box(tmp, -sx / 2, -sy / 2, -sz / 2, sx / 2, sy / 2, sz / 2)
    m = Matrix.Translation(mitte) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
    bmesh.ops.transform(tmp, matrix=m, verts=tmp.verts)
    einfuegen(bm, tmp, mat)


def einfuegen(bm, tmp, mat=None):
    """tmp-bmesh in bm uebernehmen; mat=None behaelt die Material-Indizes von tmp."""
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me)
    tmp.free()
    n0 = len(bm.faces)
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    if mat is not None:
        bm.faces.ensure_lookup_table()
        for f in list(bm.faces)[n0:]:
            f.material_index = mat


def obj(name, bm, col, mats, uv=True, fase=None):
    ob = V.objekt_aus_bmesh(name, bm, col, material=mats, uv=uv)
    if fase:
        V.fase(ob, fase, 2)
    return ob


def band(bm, pts, breite, z_func, mat, off=0.003, uv_laenge=True):
    """Streifen entlang einer Polylinie auf der Oberflaeche (Markierungen, Risse)."""
    uvl = bm.loops.layers.uv.verify()
    prev = None
    acc = 0.0
    for i in range(len(pts) - 1):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        d = (b - a)
        if d.length < 1e-4:
            continue
        nrm = Vector((-d.y, d.x)).normalized() * breite / 2
        q = [a - nrm, b - nrm, b + nrm, a + nrm]
        vs = [bm.verts.new((p.x, p.y, z_func(p.x, p.y) + off)) for p in q]
        f = bm.faces.new(vs)
        f.material_index = mat
        l = d.length
        for lp, uv in zip(f.loops, ((acc, 0), (acc + l, 0), (acc + l, breite), (acc, breite))):
            lp[uvl].uv = uv
        acc += l


# ------------------------------------------------------------------ Fahrbahn-Detail
def fahrbahn_detail(col):
    rnd = RND
    # Absenkungen (Pfuetzen-Mulden)
    for (x, y) in C["senken"]:
        SENKEN.append((x, y, rnd.uniform(0.9, 1.8), rnd.uniform(0.03, 0.06)))
    # Gelaende-Fahrbahn unter den Detailzonen absenken (verdeckt)
    ter = bpy.data.objects["GEO_Gelaende"]
    for v in ter.data.vertices:
        x, y = v.co.x, v.co.y
        if any(a < x < c and b < y < d for a, b, c, d in DETAIL):
            v.co.z -= 0.08
    # Feine Fahrbahn 0,25 m
    st = C["raster_m"]
    bm = bmesh.new()
    schlag = [(x, y, r) for (x, y, r) in C["schlagloecher"]]
    for (x0, y0, x1, y1) in DETAIL:
        nx, ny = int(round((x1 - x0) / st)), int(round((y1 - y0) / st))
        grid = {}
        for j in range(ny + 1):
            for i in range(nx + 1):
                x, y = x0 + i * st, y0 + j * st
                grid[i, j] = bm.verts.new((x, y, fahrbahn_z(x, y)))
        for j in range(ny):
            for i in range(nx):
                cx, cy = x0 + (i + 0.5) * st, y0 + (j + 0.5) * st
                if any((cx - sx) ** 2 + (cy - sy) ** 2 < (r + 0.1) ** 2 for sx, sy, r in schlag):
                    continue
                bm.faces.new((grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    obj("STR_Fahrbahn_Detail", bm, col, [V.material("MAT_Asphalt_Rissig")])
    # Schlagloecher: Rand (deckt Rasterkante ab), Wand, Boden (Wasser oder Erde)
    bm = bmesh.new()
    for k, (sx, sy, r) in enumerate(schlag):
        n = 18
        z0 = fahrbahn_z(sx, sy)
        tiefe = rnd.uniform(0.04, 0.09)
        aussen, innen, boden = [], [], []
        for i in range(n):
            a = 2 * math.pi * i / n
            ri = r * (1 + 0.25 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, k))))
            ro = ri + 0.35
            px, py = sx + math.cos(a) * ro, sy + math.sin(a) * ro
            aussen.append(bm.verts.new((px, py, fahrbahn_z(px, py) + 0.002)))
            qx, qy = sx + math.cos(a) * ri, sy + math.sin(a) * ri
            innen.append(bm.verts.new((qx, qy, fahrbahn_z(qx, qy) + 0.004)))
            boden.append(bm.verts.new((sx + math.cos(a) * ri * 0.8, sy + math.sin(a) * ri * 0.8, z0 - tiefe)))
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((aussen[i], aussen[j], innen[j], innen[i]))
            f.material_index = 0
            f = bm.faces.new((innen[i], innen[j], boden[j], boden[i]))
            f.material_index = 1
        f = bm.faces.new(boden)
        f.material_index = 2 if rnd.random() < 0.55 else 1
        if f.material_index == 2:  # Wasserspiegel knapp unter dem Rand
            for v in boden:
                pass
    obj("STR_Schlagloecher", bm, col, [V.material("MAT_Asphalt_Rissig"), V.material("MAT_Erde"), V.mat_wasser()])
    # Pfuetzen in den Senken (unregelmaessig), 2-3 mit Oel; nasser Rand
    bm, bmr = bmesh.new(), bmesh.new()
    for k, (x, y, r, t) in enumerate(SENKEN):
        zmin = fahrbahn_z(x, y)
        zw = zmin + t * 0.45
        n = 24
        ring, ring2 = [], []
        for i in range(n):
            a = 2 * math.pi * i / n
            rr = r * 0.8 * (1 + 0.3 * noise.noise(Vector((math.cos(a) * 1.7, math.sin(a) * 1.7, 9 + k))))
            ring.append(bm.verts.new((x + math.cos(a) * rr, y + math.sin(a) * rr, zw)))
            r2 = rr + 0.35
            px, py = x + math.cos(a) * r2, y + math.sin(a) * r2
            ring2.append((ring[-1], (px, py)))
        f = bm.faces.new(ring)
        f.material_index = 1 if k < C["oel_pfuetzen"] else 0
        outer = [bmr.verts.new((p[0], p[1], fahrbahn_z(*p) + 0.002)) for _, p in ring2]
        inner = [bmr.verts.new((v.co.x, v.co.y, max(v.co.z, fahrbahn_z(v.co.x, v.co.y)) + 0.002)) for v, _ in ring2]
        for i in range(n):
            j = (i + 1) % n
            bmr.faces.new((outer[i], outer[j], inner[j], inner[i]))
    obj("STR_Pfuetzen", bm, col, [V.mat_wasser(), V.mat_wasser("MAT_Wasser_Oel", oel=True)], uv=False)
    obj("STR_Pfuetzen_Nassrand", bmr, col, [V.material("MAT_Asphalt_Nass")])
    # Flickstellen (Rechtecke, leicht erhaben)
    bm = bmesh.new()
    for (x, y, w, l) in C["flicken"]:
        n = max(2, int(w / 0.25)), max(2, int(l / 0.25))
        vs = {}
        for i in range(n[0] + 1):
            for j in range(n[1] + 1):
                px = x + w * i / n[0] + (rnd.uniform(-0.05, 0.05) if i in (0, n[0]) else 0)
                py = y + l * j / n[1] + (rnd.uniform(-0.05, 0.05) if j in (0, n[1]) else 0)
                vs[i, j] = bm.verts.new((px, py, fahrbahn_z(px, py) + 0.006))
        for i in range(n[0]):
            for j in range(n[1]):
                bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    obj("STR_Flickstellen", bm, col, [V.material("MAT_Asphalt_Geflickt")])
    # Risse: Laengs-, Quer- und Netzrisse als dunkle Streifen (Pfade fuer Vegetation Phase 4 gemerkt)
    risse = []
    for (x0, y0, x1, y1) in DETAIL:
        for k in range(int((x1 - x0) * (y1 - y0) / C["riss_flaeche_m2"])):
            x, y = rnd.uniform(x0 + 0.5, x1 - 0.5), rnd.uniform(y0 + 0.3, y1 - 0.3)
            laengs = rnd.random() < 0.55
            ang = (0 if laengs else math.pi / 2) + rnd.uniform(-0.3, 0.3)
            pts = [(x, y)]
            for s in range(rnd.randint(6, 26)):
                ang += rnd.uniform(-0.5, 0.5)
                x += math.cos(ang) * 0.35
                y += math.sin(ang) * 0.35
                if not (x0 < x < x1 and y0 < y < y1):
                    break
                pts.append((x, y))
            if len(pts) > 2:
                risse.append(pts)
        for k in range(C["netzriss_felder"] // max(1, len(DETAIL))):  # Netzrisse (Alligator)
            cx, cy = rnd.uniform(x0 + 2, x1 - 2), rnd.uniform(y0 + 1, y1 - 1)
            for j in range(rnd.randint(7, 14)):
                x, y = cx + rnd.uniform(-1.2, 1.2), cy + rnd.uniform(-1.0, 1.0)
                ang = rnd.uniform(0, 6.28)
                pts = [(x, y)]
                for s in range(rnd.randint(2, 5)):
                    ang += rnd.uniform(-1.0, 1.0)
                    x += math.cos(ang) * 0.3
                    y += math.sin(ang) * 0.3
                    pts.append((x, y))
                risse.append(pts)
    bm = bmesh.new()
    rissmat = V.mat_farbe("MAT_Riss", "#17140F", 0.15, "MAT_Asphalt_Rissig", rau=0.9, lokal=0.2)
    for pts in risse:
        band(bm, pts, rnd.uniform(0.02, 0.045), fahrbahn_z, 0, off=0.004)
    o = obj("STR_Risse", bm, col, [rissmat], uv=False)
    o.visible_shadow = False
    bpy.context.scene["risse_pfade"] = len(risse)
    bpy.app.driver_namespace["risse"] = risse


def markierungen(col):
    """Gelbe Doppellinie, weisse Spur-/Randlinien, Zebrastreifen + Haltelinien an der Kreuzung (verblasst)."""
    gelb = V.mat_farbe("MAT_Markierung_Gelb", "#C9A640", 0.45, "MAT_Asphalt_Rissig", rau=0.55, lokal=0.25)
    weiss = V.mat_farbe("MAT_Markierung_Weiss", "#DAD6CA", 0.5, "MAT_Asphalt_Rissig", rau=0.55, lokal=0.25)
    bm = bmesh.new()
    kreuz = [(s["lage"], s["fahrbahn"] / 2) for s in L["strassen"] if s["achse"] == "y"]
    def frei(x):
        return all(abs(x - k) > h + 2.5 for k, h in kreuz)
    def linie(y, x0, x1, breite, mat, strich=None, luecke=None):
        x = x0
        while x < x1:
            xe = min(x1, x + (strich or 0.5))
            if frei(x) and frei(xe):
                pts = [(x + (xe - x) * k / 4, y) for k in range(5)]
                band(bm, pts, breite, fahrbahn_z, mat)
            x = xe + (luecke or 0.0)
    for x0, x1 in ((-150, 150),):
        for yy in (-0.125, 0.125):
            linie(yy, x0, x1, 0.1, 0)
        for yy in (-3.5, 3.5):
            linie(yy, x0, x1, 0.1, 1, strich=3.0, luecke=9.0)
        for yy in (-6.75, 6.75):
            linie(yy, x0, x1, 0.12, 1)
    # Querstrassen: gelbe Mittellinie
    for s in L["strassen"]:
        if s["achse"] != "y":
            continue
        y = s["von"]
        while y < s["bis"]:
            ye = min(s["bis"], y + 0.5)
            if abs(y) > 9 and abs(ye) > 9:
                band(bm, [(s["lage"], y + (ye - y) * k / 4) for k in range(5)], 0.1, fahrbahn_z, 0)
            y = ye
    # Zebrastreifen (Balken 0,6 m) + Haltelinien an der Kreuzung Ost
    kx = 18.0
    for (cx, cy, quer) in ((kx - 6.8, 0, True), (kx + 6.8, 0, True), (kx, 9.2, False), (kx, -9.2, False)):
        if quer:  # ueber die Hauptstrasse
            y = -6.5
            while y < 6.5:
                band(bm, [(cx - 1.5 + k * 0.75, y + 0.3) for k in range(5)], 0.6, fahrbahn_z, 1)
                y += 1.2
        else:
            x = kx - 3.6
            while x < kx + 3.6:
                band(bm, [(x + 0.3, cy - 1.5 + k * 0.75) for k in range(5)], 0.6, fahrbahn_z, 1)
                x += 1.2
    for (x, a, b) in ((kx - 9.0, 0.2, 6.8), (kx + 9.0, -6.8, -0.2)):
        band(bm, [(x, a + (b - a) * k / 6) for k in range(7)], 0.45, fahrbahn_z, 1)
    o = obj("STR_Markierungen", bm, col, [gelb, weiss], uv=False)
    o.visible_shadow = False


def gullideckel(col):
    bm = bmesh.new()
    for (x, y) in C["gullideckel"]:
        z = fahrbahn_z(x, y)
        rohr(bm, (x, y, z - 0.02), (x, y, z + 0.008), 0.33, seg=24, mat=1)
        rohr(bm, (x, y, z - 0.02), (x, y, z + 0.012), 0.3, seg=24, mat=0)
    obj("STR_Gullideckel", bm, col, [V.material("MAT_Rost_Dunkel"), V.material("MAT_Beton_Grob")])


# ------------------------------------------------------------------ Gehwegplatten
def gehwegplatten(col):
    rnd = RND
    proto = V.prototypen("Gehwegplatten")
    varianten = []
    for k in range(3):  # intakt, Ecke abgebrochen, Riss diagonal
        bm = bmesh.new()
        a = 0.744
        if k == 0:
            V.box(bm, -a, -a, -0.1, a, a, 0.0)
        elif k == 1:
            vs_t = [(-a, -a), (a, -a), (a, a - 0.35), (a - 0.4, a), (-a, a)]
            top = [bm.verts.new((x, y, 0)) for x, y in vs_t]
            bot = [bm.verts.new((x, y, -0.1)) for x, y in vs_t]
            bm.faces.new(top)
            bm.faces.new(bot[::-1])
            for i in range(len(vs_t)):
                j = (i + 1) % len(vs_t)
                bm.faces.new((bot[i], bot[j], top[j], top[i]))
        else:
            for poly in ([(-a, -a), (a, -a), (-a + 0.02, a)], [(a, -a + 0.02), (a, a), (-a + 0.04, a)]):
                top = [bm.verts.new((x, y, 0)) for x, y in poly]
                bot = [bm.verts.new((x, y, -0.1)) for x, y in poly]
                bm.faces.new(top)
                bm.faces.new(bot[::-1])
                for i in range(3):
                    j = (i + 1) % 3
                    bm.faces.new((bot[i], bot[j], top[j], top[i]))
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ob = V.objekt_aus_bmesh(f"STR_Gehwegplatte_V{k}", bm, proto, material=V.material("MAT_Gehweg_Beton"))
        for d in ob.data.uv_layers.active.data:  # jede Variante zeigt einen anderen Texturausschnitt
            d.uv = (d.uv[0] + k * 0.37, d.uv[1] + k * 0.61)
        varianten.append(ob)
    pts = []
    for (x0, x1, y0, y1) in C["gehweg_zonen"]:
        y = y0 + 0.75
        while y < y1:
            x = x0 + 0.75
            while x < x1:
                z = gehweg_z(x, y)
                tilt_x, tilt_y, dz = rnd.uniform(-0.012, 0.012), rnd.uniform(-0.012, 0.012), rnd.uniform(-0.004, 0.006)
                # Wurzeln: Platten neben Baumscheiben angehoben und gekippt
                nah_baum = any(abs(x - bx) < 1.6 and abs(y - by) < 2.4 for bx, by in BAEUME)
                if nah_baum and rnd.random() < 0.7:
                    dz += rnd.uniform(0.02, 0.06)
                    tilt_x += rnd.uniform(0.02, 0.07) * (1 if y > 0 else -1)
                    tilt_y += rnd.uniform(-0.04, 0.04)
                idx = 0 if rnd.random() < 0.75 else (1 if rnd.random() < 0.6 else 2)
                rot = (tilt_x, tilt_y, rnd.choice([0, 1.5708, 3.1416, 4.7124]))
                pts.append(((x, y, z + dz), rot, (1, 1, 1), idx))
                x += 1.5
            y += 1.5
    ob = V.instanzen("STR_Gehwegplatten", pts, proto, col)
    ob["anzahl"] = len(pts)


# ------------------------------------------------------------------ Strommasten + Leitungen
def strommasten(col):
    rnd = RND
    bm = bmesh.new()
    mats = [V.material("MAT_Mast_Holz"), V.material("MAT_Porzellan"), V.material("MAT_Stahl_Verzinkt"), V.material("MAT_Holz_Bretter_Alt")]
    masten = []
    for linie in C["strommasten"]["linien"]:
        (xa, ya), (xb, yb) = linie["von"], linie["bis"]
        L_ = math.hypot(xb - xa, yb - ya)
        n = max(1, int(round(L_ / C["strommasten"]["abstand"])))
        for k in range(n + 1):
            x, y = xa + (xb - xa) * k / n, ya + (yb - ya) * k / n
            masten.append((x, y, math.atan2(yb - ya, xb - xa), linie["name"], k))
    knick = C["strommasten"]["umgeknickt"]
    attach = {}
    for i, (x, y, rich, lname, k) in enumerate(masten):
        z0 = V.h(x, y) + 0.15
        H = 10.4
        if [x, y] == knick or (abs(x - knick[0]) < 1 and abs(y - knick[1]) < 1):
            # umgeknickt: Stumpf 2,8 m, oberer Teil liegt schraeg ueber Gehweg/Strasse
            rohr(bm, (x, y, z0 - 1.8), (x, y, z0 + 2.8), 0.15, seg=12, mat=0, r2=0.14)
            ang = math.radians(72)
            top = Vector((x, y, z0 + 2.8)) + Vector((math.cos(rich + 1.9) * math.sin(ang), math.sin(rich + 1.9) * math.sin(ang), math.cos(ang))) * (H - 2.8)
            rohr(bm, (x, y, z0 + 2.75), top, 0.14, seg=12, mat=0, r2=0.1)
            attach[i] = None
            continue
        rohr(bm, (x, y, z0 - 1.8), (x, y, z0 + H), 0.15, seg=12, mat=0, r2=0.1)
        # Quertraeger 2,4 m quer zur Leitung, Isolatoren
        q = Vector((-math.sin(rich), math.cos(rich), 0))
        zt = z0 + H - 0.6
        kasten(bm, (x, y, zt), (0.1, 2.4, 0.12), rot=(0, 0, rich), mat=3)
        pts = []
        for off in (-1.05, -0.35, 0.35, 1.05):
            p = Vector((x, y, zt + 0.06)) + q * off
            rohr(bm, p, p + Vector((0, 0, 0.18)), 0.035, seg=8, mat=1)
            pts.append(p + Vector((0, 0, 0.16)))
        pts.append(Vector((x, y, z0 + H - 2.0)) + q * 0.12)   # Neutralleiter
        pts.append(Vector((x, y, z0 + 6.0)) + q * 0.12)       # Telefonkabel
        attach[i] = pts
        if k % 3 == 1:  # Transformator
            c = Vector((x, y, z0 + H - 2.9)) + q * 0.45
            rohr(bm, c - Vector((0, 0, 0.5)), c + Vector((0, 0, 0.5)), 0.3, seg=16, mat=2)
            rohr(bm, c + Vector((0, 0, 0.5)), c + Vector((0, 0, 0.56)), 0.32, seg=16, mat=2)
            kasten(bm, Vector((x, y, z0 + H - 2.9)) + q * 0.18, (0.08, 0.3, 0.6), rot=(0, 0, rich), mat=2)
        if k == 0:  # Abspannseil am Linienende
            d = Vector((math.cos(rich), math.sin(rich), 0))
            anker = Vector((x, y, 0)) - d * 4.5
            anker.z = V.h(anker.x, anker.y)
            rohr(bm, Vector((x, y, z0 + H - 0.8)), anker, 0.008, seg=5, mat=2)
    obj("STR_Strommasten", bm, col, mats)
    # Leitungen mit Durchhang; einige gerissen und am Boden
    cu = bpy.data.curves.new("STR_Leitungen", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.008
    cu.bevel_resolution = 1
    for i in range(len(masten) - 1):
        if masten[i][3] != masten[i + 1][3]:
            continue
        a, b = attach.get(i), attach.get(i + 1)
        for w in range(6):
            if a is None and b is None:
                continue
            reisst = rnd.random() < C["strommasten"]["riss_anteil"] or a is None or b is None
            pa = a[w] if a else None
            pb = b[w] if b else None
            sp = cu.splines.new("POLY")
            n = 24
            if not reisst:
                sack = rnd.uniform(0.55, 1.0) * (1.4 if w >= 4 else 1.0)
                sp.points.add(n)
                for k in range(n + 1):
                    t = k / n
                    p = pa.lerp(pb, t)
                    p.z -= sack * 4 * t * (1 - t)
                    sp.points[k].co = (p.x, p.y, p.z, 1)
            else:  # haengt vom verbliebenen Mast herab und liegt dann auf dem Boden
                start = pa or pb
                ziel = (pb or pa).copy()
                ziel = start.lerp(ziel, rnd.uniform(0.4, 0.9)) if (pa and pb) else start + Vector((rnd.uniform(-6, 6), rnd.uniform(-3, 3), 0))
                sp.points.add(n)
                for k in range(n + 1):
                    t = k / n
                    p = start.lerp(ziel, t)
                    zb = V.h(p.x, p.y) + 0.17
                    p.z = max(zb, start.z - (start.z - zb) * min(1.0, t * 2.2) - 0.3 * math.sin(math.pi * min(1, t * 2.2)))
                    sp.points[k].co = (p.x, p.y, p.z, 1)
            if w == 5:
                sp.radius_interpolation = "LINEAR"
                for pt in sp.points:
                    pt.radius = 2.5
    ob = bpy.data.objects.new("STR_Leitungen", cu)
    cu.materials.append(V.material("MAT_Gummi"))
    col.objects.link(ob)


# ------------------------------------------------------------------ Laternen, Ampeln, Schilder, Moebel
def laternen(col):
    rnd = RND
    bm = bmesh.new()
    cfg = C["laternen"]
    for (x0, x1, y) in cfg["reihen"]:
        x = x0
        while x <= x1:
            if all(abs(x - k) > 9 for k in cfg["auslassen"]):
                z0 = gehweg_z(x, y)
                richt = -1 if y > 0 else 1
                zustand = rnd.random()
                if zustand < cfg["umgeknickt"]:
                    knick = rnd.uniform(1.5, 4.0)
                    rohr(bm, (x, y, z0 - 0.5), (x, y, z0 + knick), 0.09, seg=10, mat=0, r2=0.08)
                    ang = rnd.uniform(0.6, 1.4)
                    d = Vector((rnd.uniform(-1, 1), richt * rnd.uniform(0.2, 1), 0)).normalized()
                    top = Vector((x, y, z0 + knick)) + (d * math.sin(ang) + Vector((0, 0, math.cos(ang)))) * (8 - knick)
                    top.z = max(top.z, V.h(top.x, top.y) + 0.2)
                    rohr(bm, (x, y, z0 + knick), top, 0.075, seg=10, mat=0, r2=0.05)
                else:
                    rohr(bm, (x, y, z0 - 0.5), (x, y, z0 + 8.0), 0.09, seg=10, mat=0, r2=0.05)
                    p1 = Vector((x, y, z0 + 7.8))
                    p2 = Vector((x, y + richt * 2.0, z0 + 8.1))
                    rohr(bm, p1, p2, 0.035, seg=8, mat=0)
                    kasten(bm, p2 + Vector((0, richt * 0.25, -0.05)), (0.32, 0.7, 0.14), mat=0)
                    if rnd.random() < 0.6:
                        kasten(bm, p2 + Vector((0, richt * 0.25, -0.13)), (0.26, 0.55, 0.03), mat=1)
            x += cfg["abstand"]
    obj("STR_Laternen", bm, col, [V.material("MAT_Stahl_Verzinkt"), V.mat_glas("MAT_Glas_Leuchte", 1.5)])


def ampeln(col):
    """Spannseil-Ampeln (US-Sueden): 4 Abspannmasten, 2 Seile diagonal, 4 Signalgeber (Unterkante 5,3 m), einer am Boden."""
    rnd = RND
    bm = bmesh.new()
    mats = [V.material("MAT_Stahl_Verzinkt"), V.material("MAT_Lack_Gelb"), V.material("MAT_Lack_Schwarz"),
            V.mat_glas("MAT_Glas_Signal", 2.0), V.material("MAT_Lack_Rot")]
    pole = [Vector(p) for p in C["ampeln"]["masten"]]
    tops = []
    for p in pole:
        z0 = gehweg_z(p.x, p.y)
        rohr(bm, (p.x, p.y, z0 - 0.8), (p.x, p.y, z0 + 8.5), 0.16, seg=14, mat=0, r2=0.11)
        tops.append(Vector((p.x, p.y, z0 + 8.2)))
    cu = bpy.data.curves.new("STR_Ampel_Seile", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.01
    mitte = Vector((C["ampeln"]["mitte"][0], C["ampeln"]["mitte"][1], 0))
    for (a, b) in ((0, 3), (1, 2)):
        sp = cu.splines.new("POLY")
        sp.points.add(20)
        for k in range(21):
            t = k / 20
            q = tops[a].lerp(tops[b], t)
            q.z -= 1.2 * 4 * t * (1 - t)
            sp.points[k].co = (*q, 1)
    zmitte = tops[0].z - 1.2
    for k, ang in enumerate((0, math.pi / 2, math.pi, 1.5 * math.pi)):
        d = Vector((math.cos(ang), math.sin(ang), 0))
        c = mitte + d * 0.9
        unten = V.h(c.x, c.y) + C["ampeln"]["unterkante_m"]
        if k == C["ampeln"]["heruntergefallen"]:
            g = mitte + d * 3.5
            zg = fahrbahn_z(g.x, g.y)
            m = Matrix.Translation((g.x, g.y, zg + 0.18)) @ Matrix.Rotation(ang + 0.4, 4, "Z") @ Matrix.Rotation(math.radians(85), 4, "Y")
            _signalkopf(bm, m, broken=True)
            continue
        m = Matrix.Translation((c.x, c.y, unten + 0.55)) @ Matrix.Rotation(ang - math.pi / 2, 4, "Z")
        _signalkopf(bm, m, broken=False)
        sp = cu.splines.new("POLY")
        sp.points.add(1)
        sp.points[0].co = (c.x, c.y, unten + 1.1, 1)
        sp.points[1].co = (c.x, c.y, zmitte, 1)
    obj("STR_Ampeln", bm, col, mats)
    ob = bpy.data.objects.new("STR_Ampel_Seile", cu)
    cu.materials.append(V.material("MAT_Stahl_Verzinkt"))
    col.objects.link(ob)


def _signalkopf(bm, m, broken):
    tmp = bmesh.new()
    V.box(tmp, -0.17, -0.14, -0.55, 0.17, 0.14, 0.55)
    einfuegen_m(bm, tmp, m, 1)
    tmp = bmesh.new()
    V.box(tmp, -0.32, 0.14, -0.7, 0.32, 0.16, 0.7)
    einfuegen_m(bm, tmp, m, 2)
    for i, z in enumerate((0.36, 0.0, -0.36)):
        if broken and i == 1:
            continue
        tmp = bmesh.new()
        bmesh.ops.create_cone(tmp, cap_ends=True, segments=14, radius1=0.13, radius2=0.13, depth=0.02,
                              matrix=Matrix.Translation((0, -0.145, z)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
        einfuegen_m(bm, tmp, m, 3)
        tmp = bmesh.new()
        V.box(tmp, -0.16, -0.4, z + 0.12, 0.16, -0.14, z + 0.15)
        einfuegen_m(bm, tmp, m, 2)


def einfuegen_m(bm, tmp, m, mat):
    bmesh.ops.transform(tmp, matrix=m, verts=tmp.verts)
    einfuegen(bm, tmp, mat)


def schilder(col):
    rnd = RND
    bm = bmesh.new()
    mats = [V.material("MAT_Stahl_Verzinkt"), V.material("MAT_Lack_Rot"), V.material("MAT_Lack_Weiss"),
            V.material("MAT_Lack_Gruen"), V.material("MAT_Lack_Schwarz")]
    for s in C["schilder"]:
        x, y = s["pos"]
        z0 = gehweg_z(x, y)
        ang = math.radians(s.get("richtung", 0))
        bieg = math.radians(s.get("verbogen", 0))
        top = Vector((x, y, z0 + 2.6))
        if bieg:
            top = Vector((x, y, z0)) + Vector((math.sin(bieg) * math.cos(ang + 1.2), math.sin(bieg) * math.sin(ang + 1.2), math.cos(bieg))) * 2.6
        rohr(bm, (x, y, z0 - 0.4), top, 0.03, seg=6, mat=0)
        m = Matrix.Translation(top + Vector((0, 0, -0.35))) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(bieg, 4, "X") @ Matrix.Rotation(math.pi / 2, 4, "X")
        art = s["art"]
        tmp = bmesh.new()
        if art == "stop":
            bmesh.ops.create_cone(tmp, cap_ends=True, segments=8, radius1=0.39, radius2=0.39, depth=0.01,
                                  matrix=Matrix.Rotation(math.pi / 8, 4, "Z"))
            einfuegen_m(bm, tmp, m, 1)
            V.text_mesh(bm, "STOP", 0.2, m @ Matrix.Translation((0, 0, 0.006)), 2, extrude=0.0)
        elif art in ("tempo", "einbahn", "parken"):
            w, hh = (0.6, 0.75) if art == "tempo" else (0.9, 0.3) if art == "einbahn" else (0.3, 0.45)
            V.box(tmp, -w / 2, -hh / 2, -0.005, w / 2, hh / 2, 0.005)
            einfuegen_m(bm, tmp, m, 2 if art != "einbahn" else 4)
            txt = {"tempo": "SPEED\nLIMIT\n30", "einbahn": "ONE WAY ->", "parken": "NO\nPARKING"}[art]
            V.text_mesh(bm, txt, 0.11 if art != "tempo" else 0.14, m @ Matrix.Translation((0, 0, 0.007)), 4 if art != "einbahn" else 2, extrude=0.0)
        elif art == "strassenname":
            for k, (name, dr) in enumerate(s["namen"]):
                tmp = bmesh.new()
                V.box(tmp, -0.45, -0.075, -0.005, 0.45, 0.075, 0.005)
                mk = Matrix.Translation(top + Vector((0, 0, 0.1 + 0.18 * k))) @ Matrix.Rotation(math.radians(dr), 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
                einfuegen_m(bm, tmp, mk, 3)
                V.text_mesh(bm, name, 0.09, mk @ Matrix.Translation((0, 0, 0.007)), 2, extrude=0.0)
                V.text_mesh(bm, name, 0.09, mk @ Matrix.Translation((0, 0, -0.007)) @ Matrix.Rotation(math.pi, 4, "Y"), 2, extrude=0.0)
            continue
        elif art == "bus":
            V.box(tmp, -0.25, -0.3, -0.005, 0.25, 0.3, 0.005)
            einfuegen_m(bm, tmp, m, 3)
            V.text_mesh(bm, "BUS", 0.15, m @ Matrix.Translation((0, 0, 0.007)), 2, extrude=0.0)
    obj("STR_Schilder", bm, col, mats)


def hydranten(col):
    rnd = RND
    bm, bmd = bmesh.new(), bmesh.new()
    for i, (x, y) in enumerate(C["hydranten"]):
        z0 = gehweg_z(x, y)
        umgefahren = i == C["hydrant_umgefahren"]
        tmp = bmesh.new()
        rohr(tmp, (0, 0, 0), (0, 0, 0.06), 0.17, seg=12, mat=0)
        rohr(tmp, (0, 0, 0.06), (0, 0, 0.6), 0.11, seg=14, mat=0)
        rohr(tmp, (0, 0, 0.6), (0, 0, 0.64), 0.14, seg=14, mat=0)
        tmp2 = bmesh.new()
        bmesh.ops.create_uvsphere(tmp2, u_segments=14, v_segments=7, radius=0.12)
        for v in tmp2.verts:
            v.co.z = max(v.co.z, 0) + 0.64
        einfuegen(tmp, tmp2, 0)
        rohr(tmp, (0, 0, 0.75), (0, 0, 0.8), 0.03, seg=5, mat=0)
        for a in (0, math.pi):
            d = Vector((math.cos(a), math.sin(a), 0))
            rohr(tmp, d * 0.08 + Vector((0, 0, 0.42)), d * 0.19 + Vector((0, 0, 0.42)), 0.045, seg=10, mat=0)
        rohr(tmp, Vector((0, -0.08, 0.36)), Vector((0, -0.21, 0.36)), 0.065, seg=12, mat=0)
        if umgefahren:
            m = Matrix.Translation((x + 0.5, y, z0 + 0.13)) @ Matrix.Rotation(math.radians(80), 4, "Y") @ Matrix.Rotation(0.6, 4, "Z")
            rohr(bm, (x, y, z0 - 0.1), (x, y, z0 + 0.05), 0.12, seg=12, mat=1)  # abgerissener Stutzen
            # Kalkspuren/Wasserfleck auf dem Gehweg
            n = 20
            ring = [bmd.verts.new((x + math.cos(2 * math.pi * k / n) * r, y + math.sin(2 * math.pi * k / n) * r * 0.8, z0 + 0.003))
                    for k in range(n) for r in [1.6 * (1 + 0.3 * noise.noise(Vector((k * 0.7, 1.3, 2.2))))]]
            bmd.faces.new(ring)
        else:
            m = Matrix.Translation((x, y, z0)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z")
        bmesh.ops.transform(tmp, matrix=m, verts=tmp.verts)
        einfuegen(bm, tmp, 0)
    obj("PRP_Hydranten", bm, col, [V.material(C["hydrant_farbe"]), V.material("MAT_Rost_Dunkel")])
    obj("PRP_Hydrant_Kalkfleck", bmd, col, [V.mat_farbe("MAT_Kalkspur", "#D4CEC0", 0.7, "MAT_Beton_Grob", lokal=0.3)])


def stadtmoebel(col):
    """Parkuhren, Briefkaesten (ohne Logo), Zeitungsautomaten, Bushaltestelle, Fahrradstaender mit Raedern."""
    rnd = RND
    bm = bmesh.new()
    mats = [V.material("MAT_Stahl_Verzinkt"), V.material("MAT_Lack_Gruen"), V.material("MAT_Lack_Rot"),
            V.mat_glas(), V.material("MAT_Papier"), V.material("MAT_Lack_Schwarz"), V.material("MAT_Rost_Dunkel"), V.material("MAT_Gummi")]
    # Parkuhren
    for (x0, x1, y) in C["parkuhren"]:
        x = x0
        while x < x1:
            z0 = gehweg_z(x, y)
            if rnd.random() < 0.85:
                schief = rnd.uniform(0, 0.5) if rnd.random() < 0.2 else 0
                top = Vector((x + math.sin(schief) * 1.2, y, z0 + math.cos(schief) * 1.2))
                rohr(bm, (x, y, z0 - 0.2), top, 0.03, seg=6, mat=0)
                if rnd.random() < 0.85:
                    kasten(bm, top + Vector((0, 0, 0.15)), (0.16, 0.14, 0.3), rot=(0, schief, 0), mat=5)
                    kasten(bm, top + Vector((0, -0.075, 0.2)), (0.1, 0.01, 0.08), rot=(0, schief, 0), mat=3)
            x += 6.5
    # Briefkaesten (generisch, dunkelgruen, ohne Logo)
    for (x, y, rot) in C["briefkaesten"]:
        z0 = gehweg_z(x, y)
        for dx in (-0.2, 0.2):
            for dy in (-0.2, 0.2):
                rohr(bm, (x + dx, y + dy, z0), (x + dx, y + dy, z0 + 0.35), 0.02, seg=5, mat=1)
        kasten(bm, (x, y, z0 + 0.85), (0.5, 0.5, 1.0), rot=(0, 0, rot), mat=1)
        rohr(bm, (x - 0.25, y, z0 + 1.35), (x + 0.25, y, z0 + 1.35), 0.25, seg=16, mat=1)
    # Zeitungsautomaten (zerbrochen, vergilbte Zeitungen mit erfundener Schlagzeile)
    for (x, y, rot, farbe) in C["zeitungsautomaten"]:
        z0 = gehweg_z(x, y)
        mk = Matrix.Translation((x, y, z0)) @ Matrix.Rotation(rot, 4, "Z")
        tmp = bmesh.new()
        V.box(tmp, -0.27, -0.22, 0.3, 0.27, 0.22, 1.05)
        einfuegen_m(bm, tmp, mk, 2 if farbe == "rot" else 1)
        for dx in (-0.22, 0.22):
            tmp = bmesh.new()
            V.box(tmp, dx - 0.02, -0.18, 0.0, dx + 0.02, 0.18, 0.3)
            einfuegen_m(bm, tmp, mk, 0)
        tmp = bmesh.new()
        V.box(tmp, -0.22, -0.2, 0.62, 0.22, 0.05, 0.64)
        einfuegen_m(bm, tmp, mk, 4)
        V.text_mesh(bm, "EVACUATION\nCENTERS OPEN", 0.035, mk @ Matrix.Translation((0, -0.05, 0.645)) @ Matrix.Rotation(math.radians(-90), 4, "X") @ Matrix.Rotation(math.pi, 4, "Z"), 5, extrude=0.0)
    # Bushaltestelle: Rahmen, Dach, Glaswaende (zerbrochen), Bank
    bx, by = C["bushaltestelle"]
    z0 = gehweg_z(bx, by)
    for (dx, dy) in ((-1.8, -0.7), (1.8, -0.7), (-1.8, 0.7), (1.8, 0.7)):
        rohr(bm, (bx + dx, by + dy, z0), (bx + dx, by + dy, z0 + 2.4), 0.04, seg=8, mat=5)
    kasten(bm, (bx, by, z0 + 2.45), (3.8, 1.6, 0.08), mat=5)
    for (cx, cy, sx, sy) in ((bx, by - 0.7, 3.5, 0.02), (bx - 1.8, by, 0.02, 1.3)):
        if rnd.random() < 0.5:
            kasten(bm, (cx, cy, z0 + 1.3), (sx, sy, 1.8), mat=3)
    kasten(bm, (bx, by - 0.4, z0 + 0.45), (2.2, 0.4, 0.05), mat=0)
    for (s, f) in ((1.6, 0.7),):
        pass
    # Fahrradstaender mit verrosteten Raedern
    fx, fy = C["fahrradstaender"]
    z0 = gehweg_z(fx, fy)
    for k in range(4):
        x = fx + k * 0.8
        rohr(bm, (x, fy, z0), (x, fy, z0 + 0.8), 0.025, seg=6, mat=0)
        rohr(bm, (x + 0.5, fy, z0), (x + 0.5, fy, z0 + 0.8), 0.025, seg=6, mat=0)
        rohr(bm, (x, fy, z0 + 0.8), (x + 0.5, fy, z0 + 0.8), 0.025, seg=6, mat=0)
    for k in range(2):  # Fahrrad: zwei Raeder (Torus), Rahmen
        x = fx + 0.25 + k * 1.6
        liegt = k == 1
        for dy in (-0.55, 0.55):
            tmp = bmesh.new()
            bmesh.ops.create_circle(tmp, cap_ends=False, segments=24, radius=0.33)
            e = bmesh.ops.extrude_edge_only(tmp, edges=list(tmp.edges))
            for v in [g for g in e["geom"] if isinstance(g, bmesh.types.BMVert)]:
                v.co *= 0.9
            m = Matrix.Translation((x, fy + dy, z0 + 0.35)) @ Matrix.Rotation(math.pi / 2, 4, "Y") @ Matrix.Rotation(math.pi / 2, 4, "X")
            if liegt:
                m = Matrix.Translation((x + 0.3, fy + dy + 0.3, z0 + 0.03)) @ Matrix.Rotation(0.5, 4, "Z")
            bmesh.ops.transform(tmp, matrix=m, verts=tmp.verts)
            einfuegen(bm, tmp, 6)
        if not liegt:
            rohr(bm, (x, fy - 0.55, z0 + 0.35), (x, fy, z0 + 0.75), 0.018, seg=5, mat=6)
            rohr(bm, (x, fy, z0 + 0.75), (x, fy + 0.55, z0 + 0.35), 0.018, seg=5, mat=6)
            rohr(bm, (x, fy - 0.15, z0 + 0.4), (x, fy + 0.55, z0 + 0.35), 0.018, seg=5, mat=6)
    obj("PRP_Stadtmoebel", bm, col, mats)


def materialien_zuweisen():
    """Blockout-Grau durch Bibliotheks-Materialien ersetzen (Gelaende, Bloecke, Platz, Gasse, Hochstrasse, Hintergrund)."""
    zuord = {
        "GEO_Gelaende": ["MAT_Asphalt_Alt", "MAT_Erde"],
        "GEO_Aussengelaende": ["MAT_Gras_Boden"],
        "STR_Baumscheiben": ["MAT_Erde"],
        "STR_Platz_Wege": ["MAT_Gehweg_Beton"],
        "STR_Platz_Brunnen": ["MAT_Beton_Glatt"],
        "PRP_Platz_Baenke": ["MAT_Holz_Bretter_Alt"],
        "STR_Gasse_Belag": ["MAT_Asphalt_Geflickt"],
        "PRP_Gasse_Muellcontainer": ["MAT_Lack_Gruen"],
        "STR_Hochstrasse_Fahrbahn": ["MAT_Beton_Grob"],
        "STR_Hochstrasse_Pfeiler": ["MAT_Beton_Grob"],
        "STR_Hochstrasse_Abgestuerzt": ["MAT_Beton_Grob"],
        "STR_Hochstrasse_Bewehrung": ["MAT_Rost_Dunkel"],
        "STR_Hochstrasse_Leitplanken": ["MAT_Stahl_Verzinkt"],
    }
    for ob in bpy.data.objects:
        if ob.name.startswith("STR_Block_"):
            mats = ["MAT_Bordstein", "MAT_Gehweg_Beton", "MAT_Gras_Boden", "MAT_Gras_Boden"]
        elif ob.name in zuord:
            mats = zuord[ob.name]
        else:
            continue
        for i, s in enumerate(ob.material_slots):
            s.material = V.material(mats[min(i, len(mats) - 1)])


BAEUME = []


def baumscheiben_positionen():
    """Gleiche Logik wie blockout_umgebung.baumscheiben()."""
    bs = L["baumscheiben"]
    s = BU._street(L, "STR_Hauptstrasse")
    bo = L["bordstein"]["breite"]
    kreuz = [st["lage"] for st in L["strassen"] if st["achse"] == "y"]
    out = []
    for blk in L["bloecke"]:
        x0, y0, x1, y1 = blk["rechteck"]
        for side in ("S", "N"):
            if blk["seiten"].get(side) != "STR_Hauptstrasse":
                continue
            yc = (y0 + bo + s["gruenstreifen"] / 2) if side == "S" else (y1 - bo - s["gruenstreifen"] / 2)
            x = x0 + bs["abstand_zur_ecke"]
            while x < x1 - bs["abstand_zur_ecke"]:
                if all(abs(x - k) > 12 for k in kreuz):
                    out.append((x, yc))
                x += bs["abstand"]
    return out


def bauen():
    global L, C, RND
    L = V.config("layout.json")
    C = V.config("strassenraum.json")
    RND = random.Random(C["seed"])
    DETAIL[:] = [tuple(z) for z in C["detail_zonen"]]
    BAEUME[:] = baumscheiben_positionen()
    bpy.app.driver_namespace["baumscheiben"] = list(BAEUME)
    col = V.collection("02_Strassen/Strassenraum")
    materialien_zuweisen()
    fahrbahn_detail(V.collection("02_Strassen/Fahrbahn"))
    markierungen(V.collection("02_Strassen/Fahrbahn"))
    gullideckel(V.collection("02_Strassen/Fahrbahn"))
    gehwegplatten(V.collection("02_Strassen/Gehweg"))
    strommasten(V.collection("02_Strassen/Strommasten"))
    laternen(col)
    ampeln(col)
    schilder(col)
    hydranten(V.collection("07_Props_Schutt/Stadtmoebel"))
    stadtmoebel(V.collection("07_Props_Schutt/Stadtmoebel"))
