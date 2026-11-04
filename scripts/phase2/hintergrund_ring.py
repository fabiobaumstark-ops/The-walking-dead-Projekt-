"""Phase 2 – Hintergrund-Ring (AUFTRAG A13). Parameter: scripts/configs/hintergrund.json

Mittelgrund 80-150 m: weitere Haeuser + Strassenzuege (vereinfacht, Fototexturen, keine Innenraeume).
Hintergrund 150-300 m: Silhouetten (Haeuser, Hallen, Geschaeftsbloecke).
Horizont 300 m+: Huegel/Gelaendewellen bis 1,6 km.
Landmarken (eigenes Design): Wasserturm, Kirchturm, Getreidesilo, Funkmast, Hochspannungsleitung, Werbetafel.
Hochstrasse laeuft in die Ferne weiter, mit Autowracks. Baeume folgen in Phase 4, Dunst in Phase 5.
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
sys.path.insert(0, os.path.join(HIER, "..", "phase1"))
import blockout_umgebung as BU  # noqa: E402
import strassenraum as SR  # noqa: E402
import viertel_lib as V  # noqa: E402

H = None


def gz(x, y):
    """Gelaendehoehe ueberall (Kern, Aussenring, Fernring)."""
    r = math.hypot(x, y)
    z = BU._aussen_h(x, y)
    if r > 340:
        t = V.smooth((r - 340) / 500)
        grob = 0.5 + 0.5 * noise.noise(Vector((x / 520.0, y / 520.0, 5.5)))
        kamm = 1.0 - abs(noise.noise(Vector((x / 240.0, y / 240.0, 8.1))))  # Kuppen und Taeler
        z += H["fern"]["huegel_m"] * t * (0.25 + 0.55 * grob + 0.45 * kamm * kamm)
        z += 5.0 * t * noise.noise(Vector((x / 80.0, y / 80.0, 2.2)))
    return z


# ------------------------------------------------------------------ Horizont
def fernring(col):
    F = H["fern"]
    bm = bmesh.new()
    ringe = []
    radien = [330 + (F["radius_max"] - 330) * (k / F["ringe"]) ** 1.6 for k in range(F["ringe"] + 1)]
    seg = F["segmente"]
    for r in radien:
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            x, y = math.cos(a) * r, math.sin(a) * r
            z = gz(x, y) - (0.8 if r < 500 else 0.0)
            ring.append(bm.verts.new((x, y, z)))
        ringe.append(ring)
    for k in range(len(ringe) - 1):
        a, b = ringe[k], ringe[k + 1]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    ob = V.objekt_aus_bmesh("GEO_Fernring_Huegel", bm, col, material=V.material("MAT_Gras_Boden"))
    for p in ob.data.polygons:
        p.use_smooth = True


# ------------------------------------------------------------------ einfache Haeuser (Mittel-/Hintergrund)
def einfaches_haus(bm, x, y, yaw, w, d, geschosse, dach, rnd, fassade_slot, fenster=True, kaputt=False):
    z0 = gz(x, y)
    m = Matrix.Translation((x, y, z0)) @ Matrix.Rotation(yaw, 4, "Z")
    hh = geschosse * (2.8 if dach == "sattel" else 3.4)
    def kb(x0, y0, z0_, x1, y1, z1, mat):
        t = bmesh.new()
        V.box(t, x0, y0, z0_, x1, y1, z1)
        bmesh.ops.transform(t, matrix=m, verts=t.verts)
        SR.einfuegen(bm, t, mat)
    kb(-w / 2, -d / 2, -0.6, w / 2, d / 2, hh + 0.5, fassade_slot)
    if dach == "sattel":
        neig = math.radians(rnd.uniform(28, 38))
        first = (d / 2 + 0.5) * math.tan(neig)
        t = bmesh.new()
        prof = [(-d / 2 - 0.5, hh + 0.5), (0, hh + 0.5 + first), (d / 2 + 0.5, hh + 0.5)]
        a = [t.verts.new((-w / 2 - 0.3, py, pz)) for py, pz in prof]
        b = [t.verts.new((w / 2 + 0.3, py, pz)) for py, pz in prof]
        t.faces.new(a)
        t.faces.new(b[::-1])
        for i in range(3):
            j = (i + 1) % 3
            t.faces.new((a[i], b[i], b[j], a[j]))
        if kaputt:  # eingesunkener Dachteil
            for v in t.verts:
                if v.co.x > w * 0.1 and v.co.z > hh + 1.0:
                    v.co.z -= first * 0.6
        bmesh.ops.recalc_face_normals(t, faces=t.faces)
        bmesh.ops.transform(t, matrix=m, verts=t.verts)
        SR.einfuegen(bm, t, 2)
    else:
        kb(-w / 2, -d / 2, hh + 0.5, w / 2, d / 2, hh + 1.2, fassade_slot)
        kb(-w / 2 + 0.3, -d / 2 + 0.3, hh + 0.5, w / 2 - 0.3, d / 2 - 0.3, hh + 0.55, 3)
    if fenster:  # dunkle Fensterflaechen als einfache Platten (kein Innenraum, Fernbereich)
        for g in range(geschosse):
            zf = 0.9 + g * (hh / geschosse) + 0.5
            for seite in (-1, 1):
                n = max(1, int(w / 2.6))
                for k in range(n):
                    sx = -w / 2 + (k + 0.5) * w / n
                    if rnd.random() < 0.12:
                        continue
                    kb(sx - 0.45, seite * (d / 2) - 0.02 * (1 if seite > 0 else -1) * -1, zf, sx + 0.45, seite * (d / 2 + 0.02), zf + 1.4, 1)


def mittelgrund(col):
    """Weitere Haeuser + Strassen im Ring 80-150 m (ausserhalb der Bloecke)."""
    M = H["mittelgrund"]
    rnd = random.Random(M["seed"])
    bm = bmesh.new()
    bm_str = bmesh.new()
    belegt = []
    def frei(x, y, r):
        if abs(x) < 101 and abs(y) < 101:
            return False
        if abs(x - 115) < 10:
            return False
        for s in L["strassen"]:
            half = s["fahrbahn"] / 2 + 1.5
            if s["achse"] == "x" and abs(y - s["lage"]) < half + r and s["von"] - 20 <= x <= s["bis"] + 20:
                return False
            if s["achse"] == "y" and abs(x - s["lage"]) < half + r and s["von"] - 20 <= y <= s["bis"] + 20:
                return False
        return all((x - a) ** 2 + (y - b) ** 2 > (r + c) ** 2 for a, b, c in belegt)
    for st in M["strassen"]:
        (xa, ya), (xb, yb) = st["von"], st["bis"]
        Ls = math.hypot(xb - xa, yb - ya)
        d = Vector(((xb - xa) / Ls, (yb - ya) / Ls))
        n = Vector((-d.y, d.x))
        k = 0 if st.get("asphalt", True) else 10 ** 9
        while k * 2.0 < Ls:  # Fahrbahnstreifen (Asphalt) auf dem Gelaende
            p0 = Vector((xa, ya)) + d * (k * 2.0)
            p1 = Vector((xa, ya)) + d * min(Ls, (k + 1) * 2.0)
            q = [p0 - n * st["breite"] / 2, p1 - n * st["breite"] / 2, p1 + n * st["breite"] / 2, p0 + n * st["breite"] / 2]
            bm_str.faces.new([bm_str.verts.new((v.x, v.y, gz(v.x, v.y) + 0.04)) for v in q])
            k += 1
        s = rnd.uniform(4, 10)
        while s < Ls - 6:
            for seite in (-1, 1):
                if rnd.random() < st.get("luecken", 0.15):
                    continue
                w, dd = rnd.uniform(7.5, 12), rnd.uniform(8.5, 13)
                abst = st["breite"] / 2 + rnd.uniform(5, 9) + dd / 2
                p = Vector((xa, ya)) + d * s + n * seite * abst
                if not frei(p.x, p.y, max(w, dd) / 2 + 1):
                    continue
                yaw = math.atan2(d.y, d.x) + (0 if seite > 0 else math.pi)
                typ = st.get("typ", "wohnen")
                if typ == "gewerbe":
                    w, dd = rnd.uniform(12, 30), rnd.uniform(12, 25)
                    einfaches_haus(bm, p.x, p.y, yaw, w, dd, rnd.randint(1, 2), "flach", rnd, rnd.choice([0, 4, 6]))
                else:
                    einfaches_haus(bm, p.x, p.y, yaw, w, dd, rnd.choice([1, 1, 2]), "sattel", rnd, rnd.choice([5, 7, 5]), kaputt=rnd.random() < 0.25)
                belegt.append((p.x, p.y, max(w, dd) / 2 + 2))
            s += rnd.uniform(15, 24)
    mats = [V.material("MAT_Ziegel_Rot"), V.mat_glas("MAT_Glas_Dunkel", 2.0), V.mat_schindeln(), V.material("MAT_Flachdach_Bitumen"),
            V.material("MAT_Ziegel_Verblasst"), V.mat_variante("MAT_Holz_Verkleidung", 2, "#C9D0D0"), V.material("MAT_Beton_Grob"),
            V.mat_variante("MAT_Holz_Verkleidung", 1, "#E4DCC6")]
    ob = V.objekt_aus_bmesh("BLD_Mittelgrund_Haeuser", bm, col, material=mats)
    ob["detailstufe"] = "mittel/fern: einfache Geometrie, keine Innenraeume"
    V.objekt_aus_bmesh("STR_Mittelgrund_Strassen", bm_str, V.collection("02_Strassen/Mittelgrund"), material=V.material("MAT_Asphalt_Alt"))
    return belegt


def hintergrund(col, belegt):
    B = H["hintergrund"]
    rnd = random.Random(B["seed"])
    alt = bpy.data.objects.get("BLD_Hintergrund_Silhouetten")
    if alt:
        bpy.data.objects.remove(alt)
    bm = bmesh.new()
    n_ok = 0
    versuche = 0
    while n_ok < B["anzahl"] and versuche < B["anzahl"] * 20:
        versuche += 1
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(B["r_min"], B["r_max"])
        x, y = math.cos(a) * r, math.sin(a) * r
        if abs(x - 115) < 14 or any((x - p) ** 2 + (y - q) ** 2 < (c + 10) ** 2 for p, q, c in belegt):
            continue
        typ = rnd.random()
        yaw = rnd.choice([0, math.pi / 2]) + rnd.uniform(-0.1, 0.1)
        if typ < 0.6:
            einfaches_haus(bm, x, y, yaw, rnd.uniform(8, 13), rnd.uniform(9, 13), rnd.choice([1, 2]), "sattel", rnd, rnd.choice([5, 7]), fenster=False, kaputt=rnd.random() < 0.3)
            rr = 9
        elif typ < 0.85:
            einfaches_haus(bm, x, y, yaw, rnd.uniform(25, 60), rnd.uniform(20, 40), 1, "flach", rnd, 6, fenster=False)
            rr = 30
        else:
            einfaches_haus(bm, x, y, yaw, rnd.uniform(15, 30), rnd.uniform(15, 25), rnd.randint(3, 8), "flach", rnd, rnd.choice([0, 4]), fenster=True)
            rr = 20
        belegt.append((x, y, rr))
        n_ok += 1
    # Horizont: verstreute Hoefe, Scheunen, Hallen bis ~700 m (auf den Huegeln, durchbrechen die Linie)
    for k in range(B.get("fern_anzahl", 0)):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(340, 720)
        x, y = math.cos(a) * r, math.sin(a) * r
        if rnd.random() < 0.65:
            einfaches_haus(bm, x, y, rnd.uniform(0, 3.14), rnd.uniform(9, 16), rnd.uniform(10, 18), rnd.choice([1, 2]), "sattel", rnd, rnd.choice([5, 6, 7]), fenster=False)
        else:
            einfaches_haus(bm, x, y, rnd.uniform(0, 3.14), rnd.uniform(20, 45), rnd.uniform(15, 30), rnd.choice([1, 2, 3]), "flach", rnd, 6, fenster=False)
    mats = [V.material("MAT_Ziegel_Rot"), V.mat_glas("MAT_Glas_Dunkel", 2.0), V.mat_schindeln(), V.material("MAT_Flachdach_Bitumen"),
            V.material("MAT_Ziegel_Verblasst"), V.mat_variante("MAT_Holz_Verkleidung", 2, "#C9D0D0"), V.material("MAT_Wellblech"),
            V.mat_variante("MAT_Holz_Verkleidung", 1, "#E4DCC6")]
    V.objekt_aus_bmesh("BLD_Hintergrund_Silhouetten", bm, col, material=mats)


# ------------------------------------------------------------------ Landmarken (eigenes Design)
def wasserturm(bm, x, y, rnd):
    z0 = gz(x, y)
    hz = 28.0
    beine = 6
    for k in range(beine):
        a = 2 * math.pi * k / beine
        p0 = Vector((x + math.cos(a) * 6.5, y + math.sin(a) * 6.5, z0))
        p1 = Vector((x + math.cos(a) * 4.5, y + math.sin(a) * 4.5, z0 + hz))
        SR.rohr(bm, p0, p1, 0.35, seg=10, mat=0)
        b = 2 * math.pi * (k + 1) / beine
        for t in (0.33, 0.66):
            q0 = p0.lerp(p1, t)
            q1 = Vector((x + math.cos(b) * 6.5, y + math.sin(b) * 6.5, z0)).lerp(Vector((x + math.cos(b) * 4.5, y + math.sin(b) * 4.5, z0 + hz)), t)
            SR.rohr(bm, q0, q1, 0.12, seg=6, mat=0)
    SR.rohr(bm, (x, y, z0), (x, y, z0 + hz), 0.6, seg=12, mat=0)  # Steigrohr
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=12, radius=6.0, matrix=Matrix.Translation((x, y, z0 + hz + 4.5)) @ Matrix.Diagonal((1, 1, 0.75, 1)))
    bm.faces.ensure_lookup_table()
    SR.rohr(bm, (x, y, z0 + hz + 4.5), (x, y, z0 + hz + 10.5), 6.0, seg=32, mat=1)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=6.3, radius2=0.3, depth=3.0, matrix=Matrix.Translation((x, y, z0 + hz + 12.0)))
    SR.rohr(bm, (x, y, z0 + hz + 4.3), (x, y, z0 + hz + 4.5), 7.2, seg=32, mat=0)  # Laufsteg
    SR.rohr(bm, (x, y, z0 + hz + 7.0), (x, y, z0 + hz + 8.2), 6.03, seg=32, mat=2)  # verblasstes Farbband (ohne Ortsnamen)


def kirchturm(bm_ziel, x, y):
    bm = bmesh.new()
    _kirchturm(bm, x, y)
    SR.einfuegen(bm_ziel, bm, 1)


def _kirchturm(bm, x, y):
    z0 = gz(x, y)
    V.box(bm, x - 2.5, y - 2.5, z0, x + 2.5, y + 2.5, z0 + 14)
    V.box(bm, x - 1.8, y - 1.8, z0 + 14, x + 1.8, y + 1.8, z0 + 18.5)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=2.0, radius2=0.08, depth=9.0, matrix=Matrix.Translation((x, y, z0 + 23.0)))
    SR.rohr(bm, (x, y, z0 + 27.5), (x, y, z0 + 29.0), 0.05, seg=4, mat=0)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=7.5, radius2=0.1, depth=6.0, matrix=Matrix.Translation((x + 9, y, z0 + 10)) @ Matrix.Rotation(math.pi / 4, 4, "Z"))
    V.box(bm, x + 3.5, y - 5, z0, x + 15, y + 5, z0 + 7)


def silo(bm, x, y):
    z0 = gz(x, y)
    for k in range(3):
        cx = x + k * 8.5
        SR.rohr(bm, (cx, y, z0), (cx, y, z0 + 24), 4.0, seg=24, mat=1)
        bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=4.1, radius2=0.5, depth=2.5, matrix=Matrix.Translation((cx, y, z0 + 25.2)))
    V.box(bm, x + 24, y - 3, z0, x + 30, y + 3, z0 + 36)
    SR.rohr(bm, (x + 24, y, z0 + 33), (x + 17, y, z0 + 27), 0.6, seg=8, mat=0)
    V.box(bm, x - 6, y - 12, z0, x + 30, y - 6, z0 + 6)


def funkmast(bm, cu, x, y):
    z0 = gz(x, y)
    hz = 72.0
    pts = [Vector((math.cos(a) * 1.2, math.sin(a) * 1.2, 0)) for a in (0, 2.09, 4.19)]
    for p in pts:
        SR.rohr(bm, Vector((x, y, z0)) + p, Vector((x, y, z0 + hz)) + p * 0.6, 0.08, seg=6, mat=3)
    k = 0
    while k * 3.0 < hz:
        z = z0 + k * 3.0
        for i in range(3):
            a, b = pts[i], pts[(i + 1) % 3]
            f = 1 - 0.4 * (k * 3.0 / hz)
            SR.rohr(bm, Vector((x, y, z)) + a * f, Vector((x, y, z + 3.0)) + b * f, 0.03, seg=4, mat=3 if (k // 4) % 2 else 4)
        k += 1
    for (h, r) in ((0.35, 45), (0.7, 60)):  # Abspannseile
        for a in (0, 2.09, 4.19):
            sp = cu.splines.new("POLY")
            sp.points.add(1)
            sp.points[0].co = (x, y, z0 + hz * h, 1)
            ax, ay = x + math.cos(a) * r, y + math.sin(a) * r
            sp.points[1].co = (ax, ay, gz(ax, ay), 1)


def hochspannung(bm, cu, linie):
    (xa, ya), (xb, yb) = linie["von"], linie["bis"]
    Lg = math.hypot(xb - xa, yb - ya)
    n = max(1, int(Lg / linie["abstand"]))
    d = Vector(((xb - xa) / Lg, (yb - ya) / Lg, 0))
    q = Vector((-d.y, d.x, 0))
    masten = []
    for k in range(n + 1):
        p = Vector((xa, ya, 0)) + d * (Lg * k / n)
        p.z = gz(p.x, p.y)
        hz = 34.0
        fuss = [p + q * sx * 3.5 + d * sy * 3.5 for sx in (-1, 1) for sy in (-1, 1)]
        for f in fuss:
            SR.rohr(bm, f, p + Vector((0, 0, hz)) + (f - p) * 0.15, 0.12, seg=5, mat=3)
        for z in (12, 20, 27):
            for (i, j) in ((0, 1), (1, 3), (3, 2), (2, 0)):
                t = z / hz
                a = fuss[i].lerp(p + Vector((0, 0, hz)) + (fuss[i] - p) * 0.15, t)
                b = fuss[j].lerp(p + Vector((0, 0, hz)) + (fuss[j] - p) * 0.15, t)
                SR.rohr(bm, a, b, 0.06, seg=4, mat=3)
        for z, br in ((22, 9.0), (28, 7.0)):
            SR.rohr(bm, p + Vector((0, 0, z)) - q * br, p + Vector((0, 0, z)) + q * br, 0.12, seg=4, mat=3)
        masten.append([p + Vector((0, 0, z - 1.5)) + q * s for z, br in ((22, 9.0), (28, 7.0)) for s in (-br + 0.5, br - 0.5)])
    for k in range(len(masten) - 1):
        for w in range(4):
            sp = cu.splines.new("POLY")
            sp.points.add(20)
            a, b = masten[k][w], masten[k + 1][w]
            for i in range(21):
                t = i / 20
                p = a.lerp(b, t)
                p.z -= 7.0 * 4 * t * (1 - t)
                sp.points[i].co = (*p, 1)


def werbetafel(bm, w, rnd):
    x, y = w["pos"]
    z0 = gz(x, y)
    yaw = math.radians(w["richtung"])
    for dx in (-3.5, 3.5):
        p = Vector((x, y, z0)) + Vector((math.cos(yaw), math.sin(yaw), 0)) * dx
        SR.rohr(bm, p, p + Vector((0, 0, 10.0)), 0.25, seg=10, mat=3)
    m = Matrix.Translation((x, y, z0 + 12.0)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
    t = bmesh.new()
    for i in range(10):  # Tafel aus Paneelen, einige fehlen (zerrissen)
        if rnd.random() < 0.15:
            continue
        V.box(t, -7.3 + i * 1.46, -2.15, -0.05, -7.3 + (i + 1) * 1.46 - 0.02, 2.15, 0.05)
    SR.einfuegen_m(bm, t, m, 5)
    V.text_mesh(bm, w["text"], 0.75, m @ Matrix.Translation((0, 0, -0.06)) @ Matrix.Rotation(math.pi, 4, "Y"), 6, extrude=0.0)
    V.box(bm, x - 7.3, y - 0.8, z0 + 9.6, x + 7.3, y + 0.8, z0 + 9.75)  # Laufsteg


def hochstrasse_weiter(col):
    """Hochstrasse ueber das Kerngelaende hinaus (bis ~520 m) mit Autowracks auf der Fahrbahn."""
    Hs = L["hochstrasse"]
    X, Bd, D = Hs["achse_x"], Hs["breite"], Hs["dicke"]
    ztop = V.h(X, 0) + Hs["oberkante_ueber_boden"]
    rnd = random.Random(8)
    bm = bmesh.new()
    for sgn in (1, -1):
        y = Hs["bis"] if sgn > 0 else Hs["von"]
        ziel = H["hochstrasse_bis"]
        while abs(y) < ziel:
            y2 = y + sgn * 30
            zt = max(ztop, gz(X, y2) + 6.5)
            a, b = sorted((y, y2))
            V.box(bm, X - Bd / 2, a, zt - D, X + Bd / 2, b, zt)
            zg = gz(X, y2) - 0.5
            for dx in (-3.5, 3.5):
                SR.rohr(bm, (X + dx, y2, zg), (X + dx, y2, zt - D - 1.2), 0.75, seg=14, mat=0)
            V.box(bm, X - Bd / 2 + 0.5, y2 - 0.9, zt - D - 1.2, X + Bd / 2 - 0.5, y2 + 0.9, zt - D)
            for sx in (-1, 1):
                V.box(bm, X + sx * (Bd / 2 - 0.3) - 0.03, a, zt + 0.45, X + sx * (Bd / 2 - 0.3) + 0.03, b, zt + 0.78)
            # Autowracks (Platzhalter, quer/schraeg, teils ausgebrannt)
            if rnd.random() < H["wracks_pro_feld"]:
                for k in range(rnd.randint(1, 3)):
                    cx = X + rnd.uniform(-4.5, 4.5)
                    cy = rnd.uniform(a + 3, b - 3)
                    yaw = rnd.uniform(-0.6, 0.6) + (math.pi / 2)
                    t = bmesh.new()
                    V.box(t, -2.4, -0.92, 0.3, 2.4, 0.92, 0.9)
                    V.box(t, -1.3, -0.85, 0.9, 1.0, 0.85, 1.42)
                    bmesh.ops.transform(t, matrix=Matrix.Translation((cx, cy, zt)) @ Matrix.Rotation(yaw, 4, "Z"), verts=t.verts)
                    SR.einfuegen(bm, t, 1 if rnd.random() < 0.5 else 2)
            y = y2
    ob = V.objekt_aus_bmesh("STR_Hochstrasse_Fernteil", bm, col,
                            material=[V.material("MAT_Beton_Grob"), V.material("MAT_Rost_Dunkel"), V.material("MAT_Lack_Weiss")])
    ob["info"] = "Autowracks = Platzhalter (Phase 3)"


L = None


def bauen():
    global H, L
    H = V.config("hintergrund.json")
    L = V.config("layout.json")
    col = V.collection("01_Gelaende/Hintergrund")
    fernring(col)
    belegt = mittelgrund(V.collection("03_Gebaeude/Mittelgrund"))
    hintergrund(V.collection("03_Gebaeude/Hintergrund"), belegt)
    bm = bmesh.new()
    cu = bpy.data.curves.new("BLD_Landmarken_Seile", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.03
    rnd = random.Random(H["seed"])
    lm = H["landmarken"]
    wasserturm(bm, *lm["wasserturm"], rnd)
    kirchturm(bm, *lm["kirchturm"])
    silo(bm, *lm["silo"])
    funkmast(bm, cu, *lm["funkmast"])
    for linie in lm["hochspannung"]:
        hochspannung(bm, cu, linie)
    werbetafel(bm, lm["werbetafel"], rnd)
    mats = [V.material("MAT_Stahl_Verzinkt"), V.material("MAT_Lack_Weiss"), V.material("MAT_Lack_Schwarz"), V.material("MAT_Rost_Hell"),
            V.material("MAT_Lack_Rot"), V.material("MAT_Sperrholz"), V.mat_farbe("MAT_Werbung_Farbe", "#7A2E22", 0.55, "MAT_Beton_Grob", lokal=0.6)]
    ob = V.objekt_aus_bmesh("BLD_Landmarken", bm, V.collection("03_Gebaeude/Landmarken"), material=mats)
    ob = bpy.data.objects.new("BLD_Landmarken_Seile", cu)
    cu.materials.append(V.material("MAT_Gummi"))
    V.collection("03_Gebaeude/Landmarken").objects.link(ob)
    hochstrasse_weiter(V.collection("02_Strassen/Hochstrasse"))
