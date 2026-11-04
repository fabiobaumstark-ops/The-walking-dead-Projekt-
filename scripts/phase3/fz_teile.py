"""Phase 3 – Fahrzeug-Baukasten, Teil 2: Raeder, Leuchten, Grill, Anbauteile, Innenraum, Unterboden, Pritsche."""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import viertel_lib as V  # noqa: E402
import fz_karosserie as K  # noqa: E402


# ---------------------------------------------------------------- Grundformen
def objekt(name, bm, col, mats, parent=None, loc=(0, 0, 0), uv=True, glatt=False):
    if glatt:
        for f in bm.faces:
            f.smooth = True
    ob = V.objekt_aus_bmesh(name, bm, col, location=loc, material=mats, uv=uv)
    if parent is not None:
        ob.parent = parent
    return ob


def quader(bm, c, s, mat=0, rot=None):
    """Quader mit Mittelpunkt c, Kantenlaengen s, optional gedreht (Matrix 3x3)."""
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    ecken = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
             (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    c = Vector(c)
    vs = []
    for e in ecken:
        v = Vector(e)
        if rot is not None:
            v = rot @ v
        vs.append(bm.verts.new(c + v))
    fl = []
    for q in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        f = bm.faces.new([vs[i] for i in q])
        f.material_index = mat
        fl.append(f)
    return fl


def zylinder(bm, p0, p1, r, seg=16, mat=0, deckel=True, r1=None):
    p0, p1 = Vector(p0), Vector(p1)
    ax = (p1 - p0).normalized()
    hilf = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
    u = ax.cross(hilf).normalized()
    w = ax.cross(u)
    r1 = r if r1 is None else r1
    a, b = [], []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        d = u * math.cos(t) + w * math.sin(t)
        a.append(bm.verts.new(p0 + d * r))
        b.append(bm.verts.new(p1 + d * r1))
    fl = []
    for i in range(seg):
        j = (i + 1) % seg
        f = bm.faces.new((a[i], a[j], b[j], b[i]))
        f.material_index = mat
        f.smooth = True
        fl.append(f)
    if deckel:
        for ring, rev in ((a, True), (b, False)):
            f = bm.faces.new(list(reversed(ring)) if rev else ring)
            f.material_index = mat
            fl.append(f)
    return fl


def rotation_um_y(profil, seg, mat=0, bm=None, winkel=(0, 2 * math.pi)):
    """Dreht ein Profil [(r, y), ...] um die y-Achse (Radachse)."""
    bm = bm or bmesh.new()
    voll = abs(winkel[1] - winkel[0] - 2 * math.pi) < 1e-6
    n = seg if voll else seg + 1
    ringe = []
    for i in range(n):
        t = winkel[0] + (winkel[1] - winkel[0]) * i / seg
        ringe.append([bm.verts.new((r * math.cos(t), y, r * math.sin(t))) for r, y in profil])
    for i in range(seg):
        i1 = (i + 1) % n if voll else i + 1
        for k in range(len(profil) - 1):
            f = bm.faces.new((ringe[i][k], ringe[i][k + 1], ringe[i1][k + 1], ringe[i1][k]))
            f.material_index = mat
            f.smooth = True
    return bm


def _normalen_nach_aussen(bm, faces, mitte_fn):
    for f in faces:
        if f.normal.dot(f.calc_center_median() - mitte_fn(f)) < 0:
            f.normal_flip()


# ---------------------------------------------------------------- Raeder
REIFEN_NAME = {"A": "ORVANE TOURING", "B": "ORVANE TERRA AT", "C": "KELDRA HT", "D": "KELDRA TRAIL AT",
               "E": "MARLOW 70", "F": "ORVANE CITY", "G": "MARLOW TOURING", "H": "KELDRA CARGO LT"}


def rad_mesh(typ, T, felge, mats):
    """Ein Rad (Reifen + Felge + Bremse) als Mesh, lokal: Achse = y, Aussenseite = +y."""
    name = f"FZ_Rad_{typ}_{felge}"
    if name in bpy.data.meshes:
        return bpy.data.meshes[name]
    R = K.reifen_radius(T["reifen"])
    rr = T["reifen"][0] * 0.0127
    w = T["reifen"][1] / 1000.0
    h = R - rr
    slots = ["reifen", "felge", "bremse", "chrom", "dunkel"]
    fm = {"alu5": "felge_alu", "alu6": "felge_alu", "stahl": "felge_stahl", "stahl_kappe": "felge_stahl"}[felge]
    # Reifen
    pr = [(rr - 0.004, -w * 0.40), (rr + 0.22 * h, -w * 0.47), (rr + 0.55 * h, -w * 0.50), (R - 0.16 * h, -w * 0.48),
          (R - 0.025, -w * 0.44), (R, -w * 0.38)]
    for a, b in ((-0.235, -0.205), (-0.015, 0.015), (0.205, 0.235)):
        pr += [(R, (a - 0.005) * w), (R - 0.008, a * w), (R - 0.008, b * w), (R, (b + 0.005) * w)]
    pr += [(R, w * 0.38), (R - 0.025, w * 0.44), (R - 0.16 * h, w * 0.48), (R - 0.0 * h - 0.45 * h, w * 0.50),
           (rr + 0.22 * h, w * 0.47), (rr - 0.004, w * 0.40)]
    bm = rotation_um_y(pr, 72, 0)
    # Flankenbeschriftung (erfundener Name + Groesse), erhaben
    txt = f"{REIFEN_NAME.get(typ, 'ORVANE')}   P{T['reifen'][1]}/{T['reifen'][2]}R{T['reifen'][0]}   M+S   "
    gr = min(0.026, h * 0.22)
    rt = rr + 0.55 * h
    for seite in (1, -1):
        winkel_zeichen = gr * 0.72 / rt
        a0 = math.radians(80) if seite > 0 else math.radians(100)
        for i, ch in enumerate(txt):
            if ch == " ":
                continue
            a = a0 - seite * i * winkel_zeichen
            pos = Vector((rt * math.cos(a), seite * w * 0.505, rt * math.sin(a)))
            tang = Vector((-math.sin(a), 0, math.cos(a))) * (-seite)
            radial = Vector((math.cos(a), 0, math.sin(a)))
            normal = Vector((0, seite, 0))
            mx = Matrix((tang, radial, normal)).transposed().to_4x4()
            mx.translation = pos
            V.text_mesh(bm, ch, gr, mx, 0, extrude=0.0012)
    # Felge: Bett + Horn
    pf = [(rr + 0.010, -w * 0.47), (rr - 0.006, -w * 0.45), (rr - 0.014, -w * 0.38), (rr - 0.014, w * 0.30),
          (rr - 0.006, w * 0.44), (rr + 0.010, w * 0.465), (rr + 0.004, w * 0.495), (rr - 0.012, w * 0.49)]
    rotation_um_y(pf, 48, 1, bm)
    yf = w * 0.26
    nabe = 0.075 if R < 0.39 else 0.09
    if felge in ("alu5", "alu6"):
        n = 5 if felge == "alu5" else 6
        rin = rr - 0.016
        ringe_r = [0.035, nabe, nabe + 0.02] + [nabe + 0.02 + (rin - nabe - 0.02) * k / 6 for k in range(1, 7)]
        seg = n * 12
        vs = []
        for ri, r in enumerate(ringe_r):
            schuessel = 0.035 * (1 - (r / rin) ** 1.5)
            vs.append([bm.verts.new((r * math.cos(2 * math.pi * s / seg), yf - schuessel + w * 0.18 * (r / rin) ** 3,
                                      r * math.sin(2 * math.pi * s / seg))) for s in range(seg)])
        neue = []
        for ri in range(len(ringe_r) - 1):
            for s in range(seg):
                s1 = (s + 1) % seg
                ang = ((s + 0.5) / seg * n) % 1.0
                rm = (ringe_r[ri] + ringe_r[ri + 1]) / 2
                halb = 0.13 + 0.10 * (rm - nabe) / (rin - nabe)  # Speichen werden nach aussen breiter
                fenster = ri >= 2 and ri < len(ringe_r) - 2 and abs(ang - 0.5) < 0.5 - halb
                if fenster:
                    continue
                f = bm.faces.new((vs[ri][s], vs[ri][s1], vs[ri + 1][s1], vs[ri + 1][s]))
                f.material_index = 1
                f.smooth = True
                neue.append(f)
        ext = bmesh.ops.extrude_face_region(bm, geom=neue)
        for v in [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]:
            v.co.y -= 0.028
        for f in neue:
            f.normal_update()
        # Mittelkappe
        zylinder(bm, (0, yf + 0.004, 0), (0, yf + 0.016, 0), 0.032, 20, 3)
        loch_r = 0.058 if R < 0.39 else 0.072
        for i in range(n if n != 6 else 6):
            a = 2 * math.pi * (i + 0.5) / (n if n != 6 else 6)
            p = Vector((loch_r * math.cos(a), yf - 0.025, loch_r * math.sin(a)))
            zylinder(bm, p, p + Vector((0, 0.022, 0)), 0.0095, 6, 3)
    else:
        # Stahlfelge: Schuessel mit Lueftungsloechern
        rin = rr - 0.016
        ringe_r = [0.035, nabe, rin * 0.52, rin * 0.62, rin * 0.72, rin]
        seg = 60
        vs = []
        for r in ringe_r:
            yy = yf - 0.045 + 0.06 * (r / rin) ** 2
            vs.append([bm.verts.new((r * math.cos(2 * math.pi * s / seg), yy, r * math.sin(2 * math.pi * s / seg))) for s in range(seg)])
        for ri in range(len(ringe_r) - 1):
            for s in range(seg):
                s1 = (s + 1) % seg
                if ri == 2 and (s % 10) in (3, 4, 5):
                    continue  # Lueftungsloecher
                f = bm.faces.new((vs[ri][s], vs[ri][s1], vs[ri + 1][s1], vs[ri + 1][s]))
                f.material_index = 1
                f.smooth = True
        loch_r = 0.058 if R < 0.39 else 0.08
        anz = 5 if R < 0.39 else 8
        for i in range(anz):
            a = 2 * math.pi * i / anz
            p = Vector((loch_r * math.cos(a), yf - 0.044, loch_r * math.sin(a)))
            zylinder(bm, p, p + Vector((0, 0.03, 0)), 0.011, 6, 3)
        if felge == "stahl_kappe":
            # Radkappe: flache Kuppel mit 10 Schlitzen (Kunststoff, silbern lackiert)
            seg2 = 80
            rk = [0.0, 0.05, rr * 0.55, rr * 0.75, rr * 0.92, rr - 0.004]
            vk = []
            for r in rk:
                yy = yf + 0.030 - 0.02 * (r / rr) ** 2
                if r == 0.0:
                    vk.append([bm.verts.new((0, yy, 0))])
                else:
                    vk.append([bm.verts.new((r * math.cos(2 * math.pi * s / seg2), yy, r * math.sin(2 * math.pi * s / seg2))) for s in range(seg2)])
            for ri in range(len(rk) - 1):
                for s in range(seg2):
                    s1 = (s + 1) % seg2
                    if ri == 3 and (s % 8) in (2, 3, 4):
                        continue
                    if ri == 0:
                        f = bm.faces.new((vk[0][0], vk[1][s], vk[1][s1]))
                    else:
                        f = bm.faces.new((vk[ri][s], vk[ri + 1][s], vk[ri + 1][s1], vk[ri][s1]))
                    f.material_index = 3
                    f.smooth = True
    # Bremsscheibe + Sattel
    rs = rr - 0.05
    zylinder(bm, (0, -w * 0.10, 0), (0, -w * 0.10 + 0.026, 0), rs, 36, 2)
    zylinder(bm, (0, -w * 0.12, 0), (0, yf - 0.04, 0), 0.07, 16, 2)
    sat = Matrix.Rotation(math.radians(-35), 3, "Y")
    quader(bm, sat @ Vector((rs - 0.035, -w * 0.10 + 0.013, 0)), (0.07, 0.07, 0.16), 4, sat)
    bm.normal_update()
    # Normalen pruefen: Reifen-Lauffl. muss nach aussen zeigen
    for f in bm.faces:
        c = f.calc_center_median()
        radial = Vector((c.x, 0, c.z))
        if f.material_index == 0 and radial.length > R - 0.01 and f.normal.dot(radial) < 0:
            f.normal_flip()
    me = bpy.data.meshes.new(name)
    V.uv_welt(bm, 1.0)
    bm.to_mesh(me)
    bm.free()
    mm = {"felge": mats[fm], "chrom": mats["felge_kappe"] if felge == "stahl_kappe" else mats["chrom"]}
    for s in slots:
        me.materials.append(mm.get(s) or mats[s])
    return me


# ---------------------------------------------------------------- Flaechen-Patches (Leuchten, Grill, Kennzeichen)
def _innen(pt, poly):
    x, y = pt
    inn = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inn = not inn
    return inn


def _naechster_rand(pt, poly):
    best, bd = None, 1e9
    p = Vector((pt[0], pt[1]))
    n = len(poly)
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
        q = a + ab * t
        if (q - p).length < bd:
            best, bd = q, (q - p).length
    return (best.x, best.y)


def patch(bvh, poly, achse, richtung, ursprung, versatz, zelle=0.012, muster=None, mat=0, bm=None):
    """Flaeche auf der Karosserie: Polygon in der Projektionsebene, per Raycast auf die Oberflaeche gelegt.
    achse 'x': poly in (y, z), Strahl entlang richtung*(1,0,0); achse 'y': poly in (x, z)."""
    bm = bm or bmesh.new()
    us = [p[0] for p in poly]
    vs = [p[1] for p in poly]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    nu = max(2, int(math.ceil((u1 - u0) / zelle)))
    nv = max(2, int(math.ceil((v1 - v0) / zelle)))
    gitter = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            u, v = u0 + (u1 - u0) * i / nu, v0 + (v1 - v0) * j / nv
            if not _innen((u, v), poly):
                q = _naechster_rand((u, v), poly)
                if math.hypot(q[0] - u, q[1] - v) > zelle * 0.75:
                    continue
                u, v = q
                rand = True
            else:
                rand = False
            if achse == "x":
                o = Vector((ursprung, u, v))
                dvec = Vector((richtung, 0, 0))
            else:
                o = Vector((u, ursprung, v))
                dvec = Vector((0, richtung, 0))
            hit = bvh.ray_cast(o, dvec, 5.0)
            if hit[0] is None or abs(hit[1].dot(dvec)) < 0.15:
                continue
            nrm = hit[1] if hit[1].dot(dvec) < 0 else -hit[1]
            gitter[(i, j)] = (hit[0] + nrm * versatz, rand)
    verts = {k: bm.verts.new(p) for k, (p, r) in gitter.items()}
    fl = []
    for i in range(nu):
        for j in range(nv):
            ks = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if not all(k in verts for k in ks):
                continue
            if all(gitter[k][1] for k in ks):
                continue
            if muster and not muster(i, j, nu, nv):
                continue
            f = bm.faces.new([verts[k] for k in ks])
            f.material_index = mat
            f.smooth = True
            fl.append(f)
    bm.normal_update()
    if fl and fl[0].normal.dot(Vector((-richtung, 0, 0)) if achse == "x" else Vector((0, -richtung, 0))) < 0:
        for f in fl:
            f.normal_flip()
    return bm, fl


def _verdicken(ob, dicke, versatz=-1.0, rand=True):
    m = ob.modifiers.new("Dicke", "SOLIDIFY")
    m.thickness = dicke
    m.offset = versatz
    m.use_rim = rand
    m.use_even_offset = True
    return m


def _rund(rechteck, r=0.02, n=3):
    """Rechteck (u0, v0, u1, v1) -> Polygon mit abgerundeten Ecken."""
    u0, v0, u1, v1 = rechteck
    r = min(r, (u1 - u0) / 2.2, (v1 - v0) / 2.2)
    pts = []
    for cu, cv, a0 in ((u1 - r, v0 + r, -90), (u1 - r, v1 - r, 0), (u0 + r, v1 - r, 90), (u0 + r, v0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return pts


def leuchten(lo, T, mats, col, root, cid, bvh_heck=None):
    """Scheinwerfer, Blinker, Ruecklichter, Grill (alle frei gestaltet, keine realen Formen)."""
    P = lo.P
    L = P.L
    xf, xr = L / 2 + 1.0, -L / 2 - 1.0
    bl = T["stossf_linie"]
    obs = []
    # Hoehe der Vorderkante an den Ecken
    hw_f = P.hw(0.10)
    lv = T["licht_v"]
    y_out = hw_f * 0.965
    y_in = y_out - lv["b"]
    # Oberkante knapp unter der Haubenvorderkante (an der Ecke), Unterkante darf etwas unter die Stossfaengerlinie
    hit = lo.strahl((P.x(T["haube"][0] + 0.02), (y_in + y_out) / 2, 5.0), (0, 0, -1))
    z1 = (hit[0].z if hit else P.top(T["haube"][0])) - 0.012
    h = lv["h"]
    z0 = max(z1 - h, bl - 0.05)
    st = lv["stil"]
    if st == "schmal":
        poly = [(y_in, z1 - (z1 - z0) * 0.55), (y_out - 0.05, z0), (y_out, z0 + (z1 - z0) * 0.35), (y_out, z1), (y_in + 0.03, z1)]
    elif st == "keil":
        poly = [(y_in, z1 - (z1 - z0) * 0.3), (y_out - 0.04, z0), (y_out, z0 + 0.02), (y_out - 0.01, z1), (y_in + 0.01, z1)]
    else:
        poly = _rund((y_in, z0, y_out, z1), 0.018 if st == "rechteck" else 0.03)
    for s in (1, -1):
        pl = [(u * s, v) for u, v in poly]
        if s < 0:
            pl = list(reversed(pl))
        bm, _ = patch(lo.bvh, pl, "x", -1, xf, 0.0015, 0.01)
        ob = objekt(f"{cid}_Scheinwerfer_Gehaeuse_{'l' if s > 0 else 'r'}", bm, col, [mats["reflektor"]], root, glatt=True)
        bm2, _ = patch(lo.bvh, pl, "x", -1, xf, 0.008, 0.01)
        ob2 = objekt(f"{cid}_Scheinwerfer_Glas_{'l' if s > 0 else 'r'}", bm2, col, [mats["scheinwerfer"]], root, glatt=True)
        _verdicken(ob2, 0.004)
        # Reflektor-Schalen + Blinker
        bm3 = bmesh.new()
        cu = s * (y_in + y_out) / 2
        hitc = lo.strahl((xf, cu, (z0 + z1) / 2), (-1, 0, 0))
        if hitc:
            for k, du in enumerate((-0.07, 0.05) if lv["b"] > 0.3 else (0.0,)):
                hk = lo.strahl((xf, cu + s * du, (z0 + z1) / 2), (-1, 0, 0))
                if hk is None:
                    continue
                c, nrm = hk
                rr = min(0.032, (z1 - z0) * 0.30)
                zylinder(bm3, c + nrm * 0.002, c + nrm * 0.0055, rr, 20, 0)
                zylinder(bm3, c + nrm * 0.0055, c + nrm * 0.0065, rr * 0.7, 20, 1)
        if len(bm3.verts):
            objekt(f"{cid}_Scheinwerfer_Linse_{'l' if s > 0 else 'r'}", bm3, col, [mats["reflektor"], mats["scheinwerfer"]], root, glatt=True)
        else:
            bm3.free()
        # Blinker unter/aussen
        bp = _rund((y_out - 0.10, z0 - 0.045, y_out - 0.01, z0 - 0.012), 0.01)
        bp = [(u * s, v) for u, v in bp]
        if s < 0:
            bp = list(reversed(bp))
        bm4, fl4 = patch(lo.bvh, bp, "x", -1, xf, 0.004, 0.008)
        if fl4:
            ob4 = objekt(f"{cid}_Blinker_v{'l' if s > 0 else 'r'}", bm4, col, [mats["blinker"]], root, glatt=True)
            _verdicken(ob4, 0.004)
        else:
            bm4.free()
        obs += [ob, ob2]
    # Grill
    gr = T["grill"]
    gy = max(y_in - 0.02, 0.2)
    gz1 = z1 - 0.01
    gz0 = max(gz1 - gr["h"], bl + 0.015) if gr["stil"] != "quer_gross" else max(gz1 - gr["h"], bl - 0.02)
    if gr["stil"] == "gitter":
        gpoly = [(-gy, gz0), (gy, gz0), (gy - 0.04, gz1), (-gy + 0.04, gz1)]
    else:
        gpoly = _rund((-gy, gz0, gy, gz1), 0.03)
    bmg, _ = patch(lo.bvh, gpoly, "x", -1, xf, 0.001, 0.012)
    gmat = mats["chrom"] if gr["stil"] == "quer_gross" else mats["schwarz"]
    objekt(f"{cid}_Grill_Grund", bmg, col, [mats["dunkel"]], root)
    if gr["stil"] == "gitter":
        muster = lambda i, j, nu, nv: (i + j) % 2 == 0  # noqa: E731
    elif gr["stil"] == "quer_gross":
        muster = lambda i, j, nu, nv: (j % 4) < 2 or i in (0, nu - 1) or i == nu // 2  # noqa: E731
    else:
        muster = lambda i, j, nu, nv: (j % 3) == 0 or i in (0, nu - 1)  # noqa: E731
    bmb, flb = patch(lo.bvh, gpoly, "x", -1, xf, 0.014, 0.012, muster)
    obg = objekt(f"{cid}_Grill", bmb, col, [gmat], root)
    _verdicken(obg, 0.014)
    if gr.get("unten"):
        zu0 = P.bot(0.0) + 0.08
        zu1 = bl - 0.05
        if zu1 - zu0 > 0.05:
            up = _rund((-hw_f * 0.5, zu0, hw_f * 0.5, zu1), 0.03)
            bmu, _ = patch(lo.bvh, up, "x", -1, xf, 0.001, 0.012)
            objekt(f"{cid}_Lufteinlass_Grund", bmu, col, [mats["dunkel"]], root)
            bmu2, _ = patch(lo.bvh, up, "x", -1, xf, 0.01, 0.012, lambda i, j, nu, nv: (i + j) % 2 == 0)
            o = objekt(f"{cid}_Lufteinlass", bmu2, col, [mats["schwarz"]], root)
            _verdicken(o, 0.01)
    # Ruecklichter
    lh = T["licht_h"]
    hw_r = P.hw(L - 0.10) if T["heck"] != "pritsche" else P.B / 2
    bvh = bvh_heck or lo.bvh
    if lh["stil"] == "quer":
        ry_out, ry_in = hw_r * 0.97, hw_r * 0.97 - lh["b"]
        hitr = lo.strahl((-L / 2 + 0.06, (ry_in + ry_out) / 2, 5.0), (0, 0, -1))
        rz1 = (hitr[0].z if hitr else P.top(L - 0.05)) - 0.025
        rz0 = max(rz1 - lh["h"], bl + 0.03)
        rpoly = [(ry_in, rz0 + 0.02), (ry_out, rz0), (ry_out, rz1), (ry_in + 0.03, rz1)]
    elif lh["stil"] == "pritsche":
        ry_out = hw_r - 0.012
        ry_in = ry_out - lh["b"]
        rz0 = bl + 0.03
        rz1 = rz0 + lh["h"]
        rpoly = _rund((ry_in, rz0, ry_out, rz1), 0.01)
    else:
        ry_out = hw_r * (0.99 if lh["stil"] == "kasten" else 0.975)
        ry_in = ry_out - lh["b"]
        rz0 = bl + (0.10 if lh["stil"] == "kasten" else 0.05)
        rz1 = rz0 + lh["h"]
        rpoly = _rund((ry_in, rz0, ry_out, rz1), 0.02)
    for s in (1, -1):
        pl = [(u * s, v) for u, v in rpoly]
        if s > 0:
            pl = list(reversed(pl))
        bm, fl = patch(bvh, pl, "x", 1, xr, 0.0015, 0.01)
        if not fl:
            bm.free()
            continue
        objekt(f"{cid}_Ruecklicht_Gehaeuse_{'l' if s > 0 else 'r'}", bm, col, [mats["reflektor"]], root, glatt=True)
        bm2, _ = patch(bvh, pl, "x", 1, xr, 0.007, 0.01)
        o = objekt(f"{cid}_Ruecklicht_{'l' if s > 0 else 'r'}", bm2, col, [mats["ruecklicht"]], root, glatt=True)
        _verdicken(o, 0.004)
        # Rueckfahrlicht (weiss) als kleiner Einsatz
        if lh["stil"] in ("quer", "senkrecht"):
            if lh["stil"] == "quer":
                wp = _rund((ry_in + 0.01, rz0 + 0.025, ry_in + 0.09, rz1 - 0.02), 0.01)
            else:
                wp = _rund((ry_in + 0.015, rz0 + 0.015, ry_out - 0.015, rz0 + 0.07), 0.01)
            wp = [(u * s, v) for u, v in wp]
            if s > 0:
                wp = list(reversed(wp))
            bm5, fl5 = patch(bvh, wp, "x", 1, xr, 0.0095, 0.008)
            if fl5:
                o5 = objekt(f"{cid}_Rueckfahrlicht_{'l' if s > 0 else 'r'}", bm5, col, [mats["scheinwerfer"]], root, glatt=True)
                _verdicken(o5, 0.002)
            else:
                bm5.free()
    return obs


# ---------------------------------------------------------------- Kennzeichen (erfundene Nummer, neutrales Design)
def kennzeichen(lo, T, mats, col, root, cid, rnd, bvh=None):
    P = lo.P
    L = P.L
    kz = T["kennzeichen"]
    z = kz["z"]
    bvh = bvh or lo.bvh
    hit = bvh.ray_cast(Vector((-L / 2 - 1, 0, z)), Vector((1, 0, 0)), 5.0)
    if hit[0] is None:
        return None
    pos, n = hit[0], hit[1]
    bm = bmesh.new()
    rot = Vector((0, 0, 1)).rotation_difference(n).to_matrix()
    # Tafel 30,5 x 15,2 cm, leicht schraeg wie die Flaeche
    basis = Matrix((Vector((0, -1, 0)) if n.x < 0 else Vector((0, 1, 0)), Vector((0, 0, 1)), n)).transposed()
    c = pos + n * 0.004
    quader(bm, c, (0.0, 0.0, 0.0), 0)  # Platzhalter fuer Indizes
    bm.clear()
    qr = basis
    for f in quader(bm, Vector((0, 0, 0)), (0.305, 0.152, 0.003), 0):
        pass
    bmesh.ops.transform(bm, matrix=qr.to_4x4(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=c, verts=bm.verts)
    buch = "".join(rnd.choice("ABCDEFGHJKLMNPRSTVWXYZ") for _ in range(3))
    nummer = f"{buch} {rnd.randint(1000, 9999)}"
    mx = qr.to_4x4()
    mx.translation = c + n * 0.0016 + qr @ Vector((0, -0.008, 0))
    V.text_mesh(bm, nummer, 0.07, mx, 1, extrude=0.0012)
    # schmaler Rand oben/unten
    for dv in (0.064, -0.064):
        mx2 = qr.to_4x4()
        mx2.translation = c + n * 0.0016 + qr @ Vector((0, dv, 0))
        bm2 = bmesh.new()
        quader(bm2, Vector((0, 0, 0)), (0.29, 0.005, 0.001), 1)
        bmesh.ops.transform(bm2, matrix=mx2, verts=bm2.verts)
        me = bpy.data.meshes.new("tmp")
        bm2.to_mesh(me)
        bm2.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    # Halter (dunkel)
    mxh = qr.to_4x4()
    mxh.translation = c - n * 0.003
    bm3 = bmesh.new()
    quader(bm3, Vector((0, 0, 0)), (0.33, 0.175, 0.006), 2)
    bmesh.ops.transform(bm3, matrix=mxh, verts=bm3.verts)
    me = bpy.data.meshes.new("tmp")
    bm3.to_mesh(me)
    bm3.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    ob = objekt(f"{cid}_Kennzeichen_h", bm, col, [mats["kennzeichen"], mats["schrift"], mats["schwarz"]], root)
    ob["nummer"] = nummer
    return ob


# ---------------------------------------------------------------- Anbauteile
def oberflaeche_seite(lo, d, z, s, abstand=0.0):
    """Punkt auf der Seitenwand (Strahl von aussen nach innen)."""
    P = lo.P
    x = P.x(d)
    hit = lo.strahl((x, s * 3.0, z), (0, -s, 0))
    if hit is None:
        return None, None
    return hit[0] + hit[1] * abstand, hit[1]


def spiegel(lo, T, mats, col, tuer_obs, cid):
    P = lo.P
    t0 = T["tueren"][0][0]
    d = t0 + 0.05
    while d < t0 + 0.6 and (P.top(d) - T["woelbung"] - T["dachradius"] - P.belt(d)) < 0.16:
        d += 0.01
    d += 0.04
    z = P.belt(d) + 0.06
    mat = mats["lack"] if T["spiegel"] == "lack" else mats["schwarz"]
    gross = 1.25 if T["H"] > 1.8 else 1.0
    out = []
    for s in ("l", "r"):
        sg = 1 if s == "l" else -1
        p = Vector((P.x(d), sg * P.hw(d) * 0.955, z))
        tuer = tuer_obs.get(f"Tuer_v{s}")
        bm = bmesh.new()
        # Gehaeuse: gerundeter Kasten (Bevel), hinten das Spiegelglas
        c = p + Vector((0.0, sg * 0.125 * gross, 0.03))
        quader(bm, c, (0.075, 0.20 * gross, 0.125 * gross), 0)
        quader(bm, c + Vector((-0.0385, 0, 0)), (0.002, 0.18 * gross, 0.105 * gross), 1)
        # Fuss
        quader(bm, p + Vector((0.005, sg * 0.03, -0.005)), (0.10, 0.07, 0.045), 0)
        loc = Vector((0, 0, 0))
        if tuer is not None:
            loc = tuer.location.copy()
            bmesh.ops.translate(bm, vec=-loc, verts=bm.verts)
        ob = objekt(f"{cid}_Spiegel_{s}", bm, col, [mat, mats["reflektor"]], tuer)
        fb = ob.modifiers.new("Rund", "BEVEL")
        fb.width = 0.025
        fb.segments = 4
        fb.limit_method = "ANGLE"
        for pl in ob.data.polygons:
            pl.use_smooth = True
        out.append(ob)
    return out


def griffe(lo, T, mats, col, tuer_obs, cid):
    P = lo.P
    mat = {"lack": mats["lack"], "chrom": mats["chrom"], "schwarz": mats["schwarz"]}[T["griffe"]]
    for k, t in enumerate(T["tueren"]):
        for s in K.tuer_seiten(t):
            sg = 1 if s == "l" else -1
            d = t[1] - 0.16 if not (len(t) > 2 and t[2] == "schiebe") else t[0] + 0.16
            z = P.belt(d) - 0.10
            p, n = oberflaeche_seite(lo, d, z, sg, 0.012)
            if p is None:
                continue
            tuer = tuer_obs.get(K.tuer_name(k, s))
            bm = bmesh.new()
            quader(bm, p, (0.17, 0.022, 0.032), 0)
            quader(bm, p - Vector((0, sg * 0.011, 0)), (0.19, 0.004, 0.05), 1)
            for f in bm.faces:
                f.smooth = True
            if tuer is not None:
                bmesh.ops.translate(bm, vec=-tuer.location, verts=bm.verts)
            ob = objekt(f"{cid}_Griff_{K.tuer_name(k, s)[5:]}", bm, col, [mat, mats["dunkel"]], tuer)
            m = ob.modifiers.new("Fase", "BEVEL")
            m.width = 0.007
            m.segments = 2


def wischer(lo, T, mats, col, root, cid):
    P = lo.P
    fs0 = T["frontscheibe"][0]
    d = fs0 + 0.04
    bm = bmesh.new()
    for k, y0 in enumerate((0.33, -0.12)):
        x = P.x(d)
        hit = lo.strahl((x, y0, 5), (0, 0, -1))
        if hit is None:
            continue
        p = hit[0] + Vector((0, 0, 0.012))
        laenge = 0.55 if k == 0 else 0.48
        # Arm liegt entlang der Scheibenunterkante, leicht schraeg nach oben
        steig = (P.top(fs0 + 0.3) - P.top(fs0)) / 0.3
        richt = Vector((-0.18, 1.0, 0.0)).normalized()
        ende = p + richt * laenge
        hit2 = lo.strahl((ende.x, ende.y, 5), (0, 0, -1))
        if hit2:
            ende = hit2[0] + Vector((0, 0, 0.012))
        zylinder(bm, p, ende, 0.007, 6, 0)
        zylinder(bm, p - Vector((0, 0, 0.012)), p + Vector((0, 0, 0.01)), 0.015, 10, 0)
        mitte = (p + ende) / 2
        zylinder(bm, mitte + richt * -0.22 + Vector((0, 0, -0.006)), mitte + richt * 0.22 + Vector((0, 0, -0.006)), 0.006, 6, 1)
        _ = steig
    objekt(f"{cid}_Wischer", bm, col, [mats["schwarz"], mats["reifen"]], root, glatt=True)


def antenne(lo, T, mats, col, root, cid):
    P = lo.P
    art = T.get("antenne")
    bm = bmesh.new()
    if art == "kotfluegel":
        d = T["haube"][1] - 0.15
        y = -(P.hw(d) - 0.06)
        hit = lo.strahl((P.x(d), y, 5), (0, 0, -1))
        if hit is None:
            return
        p = hit[0]
        zylinder(bm, p, p + Vector((-0.12, 0, 0.78)), 0.0025, 6, 0, r1=0.0015)
        zylinder(bm, p - Vector((0, 0, 0.01)), p + Vector((0, 0, 0.02)), 0.01, 10, 1)
    elif art == "flosse":
        d = T["dach_hinten"] - 0.18
        hit = lo.strahl((P.x(d), 0, 5), (0, 0, -1))
        if hit is None:
            return
        p = hit[0]
        prof = [(0.0, 0.0), (0.16, 0.0), (0.03, 0.06), (0.0, 0.055)]
        for sy in (-0.028, 0.028):
            pass
        vs0 = [bm.verts.new(p + Vector((-u, -0.028, v))) for u, v in prof]
        vs1 = [bm.verts.new(p + Vector((-u, 0.028, v))) for u, v in prof]
        bm.faces.new(vs0[::-1])
        bm.faces.new(vs1)
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((vs0[i], vs0[j], vs1[j], vs1[i]))
    elif art == "dach_stab":
        d = T["frontscheibe"][1] + 0.25
        hit = lo.strahl((P.x(d), 0.25, 5), (0, 0, -1))
        if hit is None:
            return
        p = hit[0]
        zylinder(bm, p, p + Vector((-0.18, 0, 0.32)), 0.004, 6, 1, r1=0.002)
        zylinder(bm, p - Vector((0, 0, 0.01)), p + Vector((0, 0, 0.025)), 0.014, 10, 1)
    else:
        bm.free()
        return
    bm.normal_update()
    ob = objekt(f"{cid}_Antenne", bm, col, [mats["chrom"], mats["schwarz"]], root, glatt=True)
    if art == "flosse":
        ob.data.materials[0] = mats["lack"]
        m = ob.modifiers.new("Rund", "SUBSURF")
        m.levels = m.render_levels = 2


def dachreling(lo, T, mats, col, root, cid):
    if not T.get("dachreling"):
        return
    P = lo.P
    d0, d1 = T["frontscheibe"][1] + 0.15, T["dach_hinten"] - 0.12
    bm = bmesh.new()
    for s in (1, -1):
        y = s * (P.dachbreite - 0.09)
        pts = []
        n = 14
        for k in range(n + 1):
            d = d0 + (d1 - d0) * k / n
            hit = lo.strahl((P.x(d), y, 5), (0, 0, -1))
            if hit:
                pts.append(hit[0] + Vector((0, 0, 0.055)))
        for a, b in zip(pts, pts[1:]):
            c = (a + b) / 2
            rot = Vector((1, 0, 0)).rotation_difference((b - a).normalized()).to_matrix()
            quader(bm, c, ((b - a).length + 0.004, 0.028, 0.032), 0, rot)
        for p in (pts[0], pts[-1]):
            quader(bm, p - Vector((0, 0, 0.03)), (0.09, 0.034, 0.06), 0)
    ob = objekt(f"{cid}_Dachreling", bm, col, [mats["schwarz"]], root)
    m = ob.modifiers.new("Fase", "BEVEL")
    m.width = 0.006
    m.segments = 2


def seitenleiste(lo, T, mats, col, root, cid):
    """Seitliche Schutzleiste (Kombi 1990er)."""
    z = T.get("seitenleiste")
    if not z:
        return
    P = lo.P
    bm = bmesh.new()
    for s in (1, -1):
        pts = []
        for k in range(40):
            d = 0.55 + (P.L - 1.0) * k / 39
            p, n = oberflaeche_seite(lo, d, z, s, 0.004)
            if p is not None:
                pts.append(p)
        for a, b in zip(pts, pts[1:]):
            c = (a + b) / 2
            rot = Vector((1, 0, 0)).rotation_difference((b - a).normalized()).to_matrix()
            quader(bm, c, ((b - a).length + 0.002, 0.012, 0.045), 0, rot)
    objekt(f"{cid}_Seitenleiste", bm, col, [mats["grau"]], root)


def stossfaenger_extra(lo, T, mats, col, root, cid):
    """Separate Stossstangen (Chrom beim Pickup, grauer Kunststoff beim alten Kombi)."""
    art = T["stossf"]
    if art not in ("chrom", "grau"):
        return
    P = lo.P
    L = P.L
    mat = mats["chrom"] if art == "chrom" else mats["grau"]
    bm = bmesh.new()
    bl = T["stossf_linie"]
    if art == "chrom":
        z0, z1 = P.bot(0.05) + 0.03, bl + 0.01
    else:
        z0, z1 = bl - 0.14, bl + 0.01
    # vorne: Strahlen ueber die Breite, Leiste davor
    for seite, x_start, richt in (("v", L / 2 + 1, -1), ("h", -L / 2 - 1, 1)):
        if seite == "h" and T["heck"] == "pritsche":
            continue
        pts = []
        hw = P.hw(0.15) if seite == "v" else P.hw(L - 0.15)
        for k in range(25):
            y = -hw * 0.98 + 2 * hw * 0.98 * k / 24
            hit = lo.bvh.ray_cast(Vector((x_start, y, (z0 + z1) / 2)), Vector((richt, 0, 0)), 5.0)
            if hit[0] is not None:
                pts.append(hit[0] + Vector((-richt * 0.035, 0, 0)))
        for a, b in zip(pts, pts[1:]):
            c = (a + b) / 2
            c.z = (z0 + z1) / 2
            rot = Vector((0, 1, 0)).rotation_difference(Vector(((b - a).x, (b - a).y, 0)).normalized()).to_matrix()
            quader(bm, c, (0.075, (b - a).length + 0.003, z1 - z0), 0, rot)
    ob = objekt(f"{cid}_Stossstange", bm, col, [mat], root)
    m = ob.modifiers.new("Fase", "BEVEL")
    m.width = 0.015
    m.segments = 3


def schiebetuer_schiene(lo, T, mats, col, root, cid):
    for k, t in enumerate(T["tueren"]):
        if len(t) > 2 and t[2] == "schiebe":
            P = lo.P
            bm = bmesh.new()
            for s in K.tuer_seiten(t):
                sg = 1 if s == "l" else -1
                pts = []
                for i in range(12):
                    d = t[1] + 0.03 + (min(P.L - 0.45, t[1] + 1.1) - t[1] - 0.03) * i / 11
                    p, n = oberflaeche_seite(lo, d, P.belt(d) - 0.015, sg, 0.002)
                    if p is not None:
                        pts.append(p)
                for a, b in zip(pts, pts[1:]):
                    c = (a + b) / 2
                    rot = Vector((1, 0, 0)).rotation_difference((b - a).normalized()).to_matrix()
                    quader(bm, c, ((b - a).length + 0.002, 0.008, 0.022), 0, rot)
            objekt(f"{cid}_Schiebetuer_Schiene", bm, col, [mats["dunkel"]], root)


# ---------------------------------------------------------------- Innenraum
def innenraum(lo, T, mats, col, root, cid, rnd):
    P = lo.P
    I = T["innen"]
    sitzm = V.material(rnd.choice(["MAT_Sitzstoff_Grau", "MAT_Sitzstoff_Beige", "MAT_Sitzstoff_Schwarz",
                                   "MAT_Leder_Schwarz", "MAT_Leder_Beige", "MAT_Leder_Grau"]))
    obs = []
    boden = I["boden"]
    dv0 = I["armaturen"][0]
    d_ende = (I["sitz_h"] or I["sitz_v"]) + 0.55
    if I.get("reihe3"):
        d_ende = I["reihe3"] + 0.55
    if T["heck"] in ("klappe", "kasten"):
        d_ende = P.L - 0.25
    if T["heck"] == "pritsche":
        d_ende = P.ende - 0.05
    # Teppich-Boden (folgt der Breite)
    bm = bmesh.new()
    n = 16
    for k in range(n):
        a, b = dv0 + (d_ende - dv0) * k / n, dv0 + (d_ende - dv0) * (k + 1) / n
        w = min(P.hw(a), P.hw(b)) - P.bw - 0.10 if (P.radlauf(a) or P.radlauf(b)) else min(P.hw(a), P.hw(b)) - 0.10
        quader(bm, (P.x((a + b) / 2), 0, boden - 0.02), (b - a + 0.002, 2 * max(w, 0.3), 0.04), 0)
    obs.append(objekt(f"{cid}_Innen_Boden", bm, col, [mats["teppich"]], root))
    # Spritzwand
    bm = bmesh.new()
    quader(bm, (P.x(dv0 - 0.03), 0, (boden + P.belt(dv0)) / 2), (0.03, 2 * (P.hw(dv0) - 0.08), P.belt(dv0) - boden), 0)
    objekt(f"{cid}_Spritzwand", bm, col, [mats["dunkel"]], root)

    def sitz(name, d, y, breite, hoehe_sitz, lehne_h=0.62, kopf=True, neigung=18):
        bm = bmesh.new()
        x = P.x(d)
        quader(bm, (x + 0.15, y, hoehe_sitz - 0.065), (0.50, breite, 0.13), 0)
        quader(bm, (x + 0.15, y, (boden + hoehe_sitz - 0.13) / 2), (0.36, breite * 0.7, max(hoehe_sitz - 0.13 - boden, 0.02)), 1)
        rot = Matrix.Rotation(math.radians(neigung), 3, "Y")
        lc = Vector((x - 0.06, y, hoehe_sitz - 0.05)) + rot @ Vector((0, 0, lehne_h / 2))
        quader(bm, lc, (0.11, breite, lehne_h), 0, rot)
        if breite < 0.7:  # Seitenwangen an Sitzflaeche und Lehne (Einzelsitze)
            for sy in (-1, 1):
                quader(bm, (x + 0.13, y + sy * (breite / 2 - 0.045), hoehe_sitz - 0.045), (0.46, 0.09, 0.15), 0)
                wc = Vector((x - 0.06, y + sy * (breite / 2 - 0.045), hoehe_sitz - 0.05)) + rot @ Vector((0.045, 0, lehne_h * 0.42))
                quader(bm, wc, (0.13, 0.09, lehne_h * 0.75), 0, rot)
        if kopf:
            kc = Vector((x - 0.06, y, hoehe_sitz - 0.05)) + rot @ Vector((0, 0, lehne_h + 0.13))
            for yy in (-0.06, 0.06):
                zylinder(bm, Vector((x - 0.06, y + yy, hoehe_sitz - 0.05)) + rot @ Vector((0, 0, lehne_h - 0.02)),
                         Vector((x - 0.06, y + yy, hoehe_sitz - 0.05)) + rot @ Vector((0, 0, lehne_h + 0.07)), 0.006, 6, 2)
            quader(bm, kc, (0.09, min(0.27, breite * 0.55), 0.17), 0, rot)
        ob = objekt(name, bm, col, [sitzm, mats["dunkel"], mats["chrom"]], root)
        m = ob.modifiers.new("Polster", "BEVEL")
        m.width = 0.035
        m.segments = 3
        m.limit_method = "ANGLE"
        sub = ob.modifiers.new("Rund", "SUBSURF")
        sub.levels = sub.render_levels = 1
        for f in ob.data.polygons:
            f.use_smooth = True
        return ob

    hz = I["sitz"]
    for s in (1, -1):
        obs.append(sitz(f"{cid}_Sitz_v{'l' if s > 0 else 'r'}", I["sitz_v"], s * 0.37, 0.52, hz))
    if I.get("sitz_h"):
        bw = 2 * (P.hw(I["sitz_h"]) - 0.12)
        obs.append(sitz(f"{cid}_Rueckbank", I["sitz_h"], 0, bw, hz - 0.03, 0.60, False, 22))
        bmk = bmesh.new()
        for yy in (-bw * 0.33, bw * 0.33):
            rot = Matrix.Rotation(math.radians(22), 3, "Y")
            c = Vector((P.x(I["sitz_h"]) - 0.06, yy, hz - 0.08)) + rot @ Vector((0, 0, 0.73))
            quader(bmk, c, (0.09, 0.26, 0.16), 0, rot)
        o = objekt(f"{cid}_Rueckbank_Kopfst", bmk, col, [sitzm], root)
        m = o.modifiers.new("Polster", "BEVEL")
        m.width = 0.03
        m.segments = 3
    if I.get("reihe3"):
        bw = 2 * (P.hw(I["reihe3"]) - P.bw - 0.12)
        obs.append(sitz(f"{cid}_Reihe3", I["reihe3"], 0, bw, hz - 0.06, 0.55, False, 20))
    # Armaturenbrett: Keil unter der Frontscheibe
    d0, d1 = I["armaturen"]
    bm = bmesh.new()
    n = 10
    for k in range(n):
        a, b = d0 + (d1 - d0) * k / n, d0 + (d1 - d0) * (k + 1) / n
        dm = (a + b) / 2
        zt = min(P.belt(dm) + 0.05, P.top(dm) - T["woelbung"] - 0.05)
        zb = boden + 0.25 if k < n - 3 else boden + 0.38
        w = P.hw(dm) - 0.07
        quader(bm, (P.x(dm), 0, (zt + zb) / 2), (b - a + 0.002, 2 * w, zt - zb), 0)
    lz = I["lenkrad"]
    # Instrumententraeger vor dem Fahrer
    quader(bm, (P.x(d1 - 0.12), 0.37, P.belt(d1) + 0.035), (0.2, 0.36, 0.08), 0)
    # Mittelkonsole oben (Radio/Display) + unten
    quader(bm, (P.x(d1 - 0.02), 0, boden + 0.42), (0.06, 0.34, 0.30), 0)
    quader(bm, (P.x(d1 + 0.001), 0, boden + 0.50), (0.004, 0.22, 0.12), 1)
    sv = I["sitz_v"]
    quader(bm, (P.x((d1 + sv + 0.1) / 2), 0, boden + 0.14), (sv + 0.1 - d1, 0.24, 0.28), 0)
    # Lueftungsduesen
    for yy in (-0.6, -0.08, 0.08, 0.6):
        quader(bm, (P.x(d1 + 0.001), yy * (P.hw(d1) - 0.1) / 0.6 if abs(yy) > 0.5 else yy, P.belt(d1) - 0.02), (0.004, 0.11, 0.05), 1)
    o = objekt(f"{cid}_Armaturen", bm, col, [mats["armaturen"], mats["dunkel"]], root)
    m = o.modifiers.new("Fase", "BEVEL")
    m.width = 0.02
    m.segments = 3
    obs.append(o)
    # Lenkrad (US: links = +y)
    bm = bmesh.new()
    c = Vector((P.x(lz[0]), 0.37, lz[1]))
    neig = Matrix.Rotation(math.radians(-25), 3, "Y")
    achse = neig @ Vector((1, 0, 0))
    bmesh.ops.create_circle(bm, cap_ends=False, segments=32, radius=0.185)
    ring = list(bm.verts)
    tor = bmesh.new()
    seg, segk = 36, 8
    vv = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        mitte = Vector((0, 0.185 * math.cos(a), 0.185 * math.sin(a)))
        rr = []
        for k in range(segk):
            b = 2 * math.pi * k / segk
            radial = Vector((0, math.cos(a), math.sin(a)))
            p = mitte + (radial * math.cos(b) + Vector((1, 0, 0)) * math.sin(b)) * 0.017
            rr.append(tor.verts.new(neig @ p + c))
        vv.append(rr)
    for i in range(seg):
        for k in range(segk):
            f = tor.faces.new((vv[i][k], vv[(i + 1) % seg][k], vv[(i + 1) % seg][(k + 1) % segk], vv[i][(k + 1) % segk]))
            f.smooth = True
    bm.free()
    for a in (0, 120, 240):
        w = math.radians(a - 90)
        p1 = c + neig @ Vector((0, 0.17 * math.cos(w), 0.17 * math.sin(w)))
        zylinder(tor, c, p1, 0.012, 8, 0)
    zylinder(tor, c - achse * 0.02, c + achse * 0.05, 0.06, 20, 0)
    zylinder(tor, c + achse * 0.05, c + achse * 0.42 + Vector((0, 0, -0.10)), 0.035, 12, 0)
    objekt(f"{cid}_Lenkrad", tor, col, [mats["armaturen"]], root)
    # Schalthebel
    bm = bmesh.new()
    p = Vector((P.x(sv - 0.32), 0, boden + 0.28))
    zylinder(bm, p, p + Vector((0, 0, 0.12)), 0.008, 8, 0)
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.025, matrix=Matrix.Translation(p + Vector((0, 0, 0.13))))
    objekt(f"{cid}_Schalthebel", bm, col, [mats["armaturen"]], root, glatt=True)
    # Sonnenblenden + Innenspiegel
    fs1 = T["frontscheibe"][1]
    zt = P.top(fs1 + 0.05) - T["woelbung"] - 0.045
    bm = bmesh.new()
    for yy in (0.33, -0.33):
        quader(bm, (P.x(fs1 + 0.12), yy, zt - 0.01), (0.17, 0.36, 0.018), 0)
    quader(bm, (P.x(fs1 - 0.01), 0, zt - 0.08), (0.03, 0.24, 0.065), 1)
    zylinder(bm, (P.x(fs1 - 0.005), 0, zt - 0.05), (P.x(fs1 + 0.01), 0, zt), 0.006, 6, 1)
    o = objekt(f"{cid}_Sonnenblenden", bm, col, [mats["dachhimmel"], mats["armaturen"]], root)
    m = o.modifiers.new("Fase", "BEVEL")
    m.width = 0.006
    m.segments = 2
    # Gurte an der B-Saeule
    if len(T["tueren"]) > 1:
        db = T["tueren"][1][0]
        bm = bmesh.new()
        for s in (1, -1):
            oben = Vector((P.x(db + 0.02), s * (P.hw(db) - 0.13), P.belt(db) + 0.32))
            unten = Vector((P.x(db + 0.02), s * (P.hw(db) - 0.11), boden + 0.18))
            c = (oben + unten) / 2
            rot = Vector((0, 0, 1)).rotation_difference((oben - unten).normalized()).to_matrix()
            quader(bm, c, (0.004, 0.046, (oben - unten).length), 0, rot)
        objekt(f"{cid}_Gurte", bm, col, [mats["dunkel"]], root)
    # Hutablage (Limousine)
    if I.get("ablage"):
        a0, a1 = I["ablage"]
        bm = bmesh.new()
        quader(bm, (P.x((a0 + a1) / 2), 0, P.belt(a0) + 0.01), (a1 - a0, 2 * (P.hw(a0) - 0.10), 0.015), 0)
        objekt(f"{cid}_Hutablage", bm, col, [mats["armaturen"]], root)
    # Kastenwagen: Trennwand + Laderaumboden (Sperrholz)
    if I.get("trennwand"):
        dt = I["trennwand"]
        bm = bmesh.new()
        quader(bm, (P.x(dt), 0, (boden + P.top(dt) - 0.1) / 2), (0.02, 2 * (P.hw(dt) - 0.06), P.top(dt) - 0.1 - boden), 0)
        o = objekt(f"{cid}_Trennwand", bm, col, [mats["grau"]], root)
        bm = bmesh.new()
        quader(bm, (P.x((dt + P.L - 0.2) / 2), 0, boden + 0.01), (P.L - 0.2 - dt, 2 * (P.hw(3.0) - 0.12), 0.018), 0)
        objekt(f"{cid}_Laderaumboden", bm, col, [V.material("MAT_Sperrholz")], root)
    return obs


# ---------------------------------------------------------------- Unterboden + Motorraum
def unterboden(lo, T, mats, col, root, cid):
    P = lo.P
    bm = bmesh.new()
    za = P.T.get("innen", {}).get("boden", 0.25) - 0.08
    xv, xh = P.x(P.achsen[0]), P.x(P.achsen[1])
    spur = P.hw(P.achsen[0]) - P.bw / 2 - 0.03
    # Achsen
    zylinder(bm, (xv, -spur + 0.12, P.R), (xv, spur - 0.12, P.R), 0.025, 10, 0)
    zylinder(bm, (xh, -spur + 0.12, P.R), (xh, spur - 0.12, P.R), 0.04 if P.T["heck"] in ("pritsche", "kasten") else 0.025, 10, 0)
    # Federn/Daempfer
    for x in (xv, xh):
        for s in (1, -1):
            zylinder(bm, (x - 0.06, s * (spur - 0.18), P.R), (x - 0.06, s * (spur - 0.18), za + 0.06), 0.045, 10, 0)
    # Auspuff rechts, Schalldaempfer, Tank
    ze = P.bot(P.L / 2) + 0.05
    zylinder(bm, (P.x(0.7), -0.30, ze + 0.05), (P.x(P.achsen[1] - 0.3), -0.36, ze), 0.028, 10, 0)
    zylinder(bm, (P.x(P.achsen[1] + 0.35), -0.40, ze + 0.02), (P.x(P.L - 0.05), -0.45, ze + 0.02), 0.03, 10, 0)
    quader(bm, (P.x(P.achsen[1] + 0.15), -0.40, ze + 0.06), (0.42, 0.26, 0.15), 0)
    quader(bm, (P.x(P.achsen[1] - 0.55), 0.25, ze + 0.10), (0.6, 0.55, 0.18), 0)
    # Laengstraeger
    for s in (1, -1):
        quader(bm, (P.x((P.achsen[0] + P.achsen[1]) / 2), s * 0.45, ze + 0.06), (P.achsen[1] - P.achsen[0] + 0.6, 0.07, 0.1), 0)
    ob = objekt(f"{cid}_Unterboden_Teile", bm, col, [mats["unterboden"]], root)
    # Motorraum (sichtbar bei offener Haube)
    h0, h1 = T["haube"]
    bm = bmesh.new()
    zm = P.bot((h0 + h1) / 2) + 0.12
    zo = P.top((h0 + h1) / 2) - 0.14
    quader(bm, (P.x(h1 - 0.45), 0, (zm + zo) / 2), (0.55, 0.62, zo - zm), 0)
    quader(bm, (P.x(h0 + 0.12), 0, (zm + zo) / 2 + 0.03), (0.05, 2 * (P.hw(h0) - 0.2), zo - zm - 0.04), 1)
    quader(bm, (P.x(h1 - 0.28), 0.52, zo - 0.12), (0.25, 0.18, 0.2), 1)
    objekt(f"{cid}_Motorraum", bm, col, [mats["unterboden"], mats["dunkel"]], root)
    return ob


# ---------------------------------------------------------------- Pickup-Pritsche
def pritsche(lo, T, mats, col, root, cid):
    """Ladeflaeche: Aussenhaut (Profil-Loft der Seite), Innenwand, Boden mit Sicken, Stirnwand, Heckklappe."""
    P = lo.P
    pr = T["pritsche"]
    d0, d1 = pr["d"]
    zr, zboden, zunten = pr["rand_z"], pr["boden_z"], pr["unten_z"]
    bi = pr["innen_b"]
    n = 60
    ds = sorted(set([d0 + (d1 - d0) * k / n for k in range(n + 1)] +
                    [P.achsen[1] + s * (P.Ra + e) for s in (-1, 1) for e in (-0.0015, 0.0015)]))
    ds = [d for d in ds if d0 <= d <= d1]
    bm = bmesh.new()
    seiten = {}
    fu, fb, fs, bs = T["flanke"]
    for s in (1, -1):
        reihen = []
        for d in ds:
            hw = P.B / 2 * (0.985 if d > d1 - 0.04 else 1.0)
            za = P.radlauf(d)
            pts = []
            zs = za if (za is not None and za > zunten) else zunten
            if za is not None and za > zunten:
                pts.append((hw - P.bw - 0.07, zunten))
                pts.append((hw - P.bw - 0.07, za))
            else:
                pts.append((hw - P.bw - 0.07, zunten - 0.001))
                pts.append((hw - P.bw - 0.07, zunten))
            pts.append((hw - 0.03, zs))
            for k in range(8):
                z = zs + 0.02 + (zr - 0.02 - zs - 0.02) * k / 7
                t = (z - zunten) / (zr - zunten)
                v = fb + (fs - fb) * _glatt2(t) if t > bs else fu + (fb - fu) * _glatt2(t / bs)
                pts.append((hw * v, z))
            pts += [(hw * fs - 0.005, zr), (hw * fs - 0.04, zr + 0.012), (bi + 0.03, zr + 0.012), (bi, zr - 0.01),
                    (bi, (zr + zboden) / 2), (bi, zboden)]
            reihen.append([bm.verts.new((P.x(d), s * y, z)) for y, z in pts])
        for a, b in zip(reihen, reihen[1:]):
            for k in range(len(a) - 1):
                f = bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]) if s > 0 else (a[k], b[k], b[k + 1], a[k + 1]))
                f.smooth = True
                f.material_index = 1 if k >= len(a) - 4 else 0
        for rr in (reihen[0], reihen[-1]):
            for k in range(len(rr) - 1):
                pass
        # Endkappen (vorne/hinten) als schmale Flaechen zwischen Aussen- und Innenhaut
        for rr, vorne in ((reihen[0], True), (reihen[-1], False)):
            aussen = rr[2:len(rr) - 4]
            innen_v = rr[len(rr) - 4:]
            zx = rr[0].co.x
            ring = aussen + list(innen_v)
            try:
                f = bm.faces.new(ring if (s > 0) != vorne else list(reversed(ring)))
                f.material_index = 0
            except ValueError:
                pass
        seiten[s] = reihen
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        if f.material_index == 0 and abs(c.y) > bi + 0.05 and f.normal.y * c.y < 0 and abs(f.normal.y) > 0.5:
            f.normal_flip()
    ob = objekt(f"{cid}_Pritsche_Seiten", bm, col, [mats["lack"], V.material("MAT_Kunststoff_Schwarz")], root)
    _verdicken(ob, 0.012)
    # Boden mit Sicken, Stirnwand, Radkaesten innen
    bm = bmesh.new()
    xa, xb = P.x(d1), P.x(d0 + 0.05)
    quader(bm, ((xa + xb) / 2, 0, zboden - 0.02), (xb - xa, 2 * bi, 0.04), 0)
    for k in range(9):
        y = -bi + 0.1 + (2 * bi - 0.2) * k / 8
        quader(bm, ((xa + xb) / 2, y, zboden + 0.008), (xb - xa - 0.04, 0.05, 0.016), 0)
    quader(bm, (P.x(d0 + 0.025), 0, (zboden + zr) / 2), (0.05, 2 * bi + 0.06, zr - zboden + 0.04), 0)
    xa_r = P.x(P.achsen[1])
    for s in (1, -1):
        quader(bm, (xa_r, s * (bi - (bi - pr["radkasten_b"]) / 2), zboden + (P.radlauf(P.achsen[1]) + 0.06 - zboden) / 2),
               (2 * P.Ra + 0.06, bi - pr["radkasten_b"], P.radlauf(P.achsen[1]) + 0.06 - zboden), 0)
    o = objekt(f"{cid}_Pritsche_Boden", bm, col, [V.material("MAT_Kunststoff_Schwarz")], root)
    m = o.modifiers.new("Fase", "BEVEL")
    m.width = 0.012
    m.segments = 2
    # Heckklappe (Drehpunkt unten)
    bm = bmesh.new()
    hx = P.x(d1) + 0.03
    piv = Vector((hx, 0, zboden - 0.03))
    quader(bm, Vector((0, 0, (zr - zboden) / 2 + 0.01)), (0.055, 2 * bi + 0.05, zr - zboden + 0.02), 0)
    quader(bm, Vector((-0.028, 0, zr - zboden - 0.06)), (0.006, 0.26, 0.07), 1)
    ok = objekt(f"{cid}_Heckklappe", bm, col, [mats["lack"], mats["dunkel"]], root, loc=piv)
    m = ok.modifiers.new("Fase", "BEVEL")
    m.width = 0.012
    m.segments = 3
    # Stufen-Stossstange hinten + Rahmen + Ersatzrad
    bm = bmesh.new()
    quader(bm, (P.x(P.L - 0.06), 0, 0.56), (0.12, P.B - 0.12, 0.17), 0)
    o = objekt(f"{cid}_Stossstange_h", bm, col, [mats["chrom"]], root)
    m = o.modifiers.new("Fase", "BEVEL")
    m.width = 0.02
    m.segments = 3
    bm = bmesh.new()
    for s in (1, -1):
        quader(bm, (P.x((P.ende + P.L) / 2), s * 0.45, 0.52), (P.L - P.ende, 0.08, 0.14), 0)
    quader(bm, (P.x(P.L - 0.03), 0, 0.42), (0.18, 0.06, 0.06), 0)
    objekt(f"{cid}_Rahmen_h", bm, col, [mats["unterboden"]], root)
    # BVH fuer Ruecklichter/Kennzeichen am Heck
    bm_all = bmesh.new()
    for o in (ob,):
        bm_all.from_mesh(o.data)
    quader(bm_all, (P.x(P.L - 0.06), 0, 0.56), (0.12, P.B - 0.12, 0.17), 0)
    return BVHTree.FromBMesh(bm_all)


def _glatt2(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def radlaufleisten(lo, T, mats, col, root, cid):
    """Kunststoff-Leisten entlang der Radlaeufe (SUV/Pickup), folgen der Karosserie-Oberflaeche."""
    if not T.get("radlaufleiste"):
        return
    P = lo.P
    bm = bmesh.new()
    rm = P.Ra + 0.032
    for ai, a in enumerate(P.achsen):
        if T["heck"] == "pritsche" and ai == 1:
            continue
        for s in (1, -1):
            pts = []
            winkel = [math.radians(-12 + k * (204 / 30)) for k in range(31)]
            for w in winkel:
                d = a + rm * math.cos(w)
                z = P.R + rm * math.sin(w)
                if z > P.belt(d) - 0.05:
                    continue
                p, n = oberflaeche_seite(lo, d, z, s, 0.006)
                if p is not None:
                    pts.append((p, n))
            for (p0, n0), (p1, n1) in zip(pts, pts[1:]):
                t = (p1 - p0)
                if t.length < 1e-4 or t.length > 0.2:
                    continue
                nn = (n0 + n1).normalized()
                x = t.normalized()
                zb = x.cross(nn).normalized()
                rot = Matrix((x, nn, zb)).transposed()
                quader(bm, (p0 + p1) / 2, (t.length + 0.004, 0.014, 0.062), 0, rot)
    if len(bm.verts):
        ob = objekt(f"{cid}_Radlaufleisten", bm, col, [mats["schwarz"]], root)
        m = ob.modifiers.new("Fase", "BEVEL")
        m.width = 0.005
        m.segments = 2
    else:
        bm.free()


def fenster_patch(bvh, poly, richtung, ursprung, mats, col, eltern, name, versatz_eltern=None):
    """Scheibe + schwarzer Gummirahmen als Flaechen-Patch (Kabinen-Rueckwand, Hecktueren)."""
    u0 = min(p[0] for p in poly)
    u1 = max(p[0] for p in poly)
    v0 = min(p[1] for p in poly)
    v1 = max(p[1] for p in poly)
    rahmen = _rund((u0 - 0.025, v0 - 0.025, u1 + 0.025, v1 + 0.025), 0.05)
    out = []
    for nm, pl, vs, mat, dicke in (("Rahmen", rahmen, 0.003, mats["schwarz"], 0.004), ("Glas", poly, 0.006, mats["glas"], 0.004)):
        bm, fl = patch(bvh, pl, "x", richtung, ursprung, vs, 0.02)
        if not fl:
            bm.free()
            continue
        if versatz_eltern is not None:
            bmesh.ops.translate(bm, vec=-versatz_eltern, verts=bm.verts)
        ob = objekt(f"{name}_{nm}", bm, col, [mat], eltern, glatt=True)
        _verdicken(ob, dicke)
        out.append(ob)
    return out
