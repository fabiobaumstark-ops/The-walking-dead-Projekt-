"""Phase 1.3 + 1.4 – Gelaende, Strassen (Bloecke mit Bordstein/Gehweg), Platz, Gasse, Hochstrasse, Hintergrund.

Wird von build_blockout.py aufgerufen. Alle Masse aus scripts/configs/layout.json und gelaende.json.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

import viertel_lib as V


# ------------------------------------------------------------------ Gelaende 1.3
def _strassen_zone(x, y, L):
    """Liefert (ist_fahrbahn, woelbung_m) fuer einen Punkt."""
    best = None
    for s in L["strassen"]:
        half = s["fahrbahn"] / 2.0
        if s["achse"] == "x":
            d, t = abs(y - s["lage"]), x
        else:
            d, t = abs(x - s["lage"]), y
        if d <= half and s["von"] <= t <= s["bis"]:
            w = 0.012 * (half - d)  # Querneigung 1,2 % (Daechprofil) zur Rinne hin
            best = w if best is None else max(best, w)
    return (best is not None), (best or 0.0)


def gelaende():
    G, L = V.gelaende_cfg(), V.config("layout.json")
    col = V.collection("01_Gelaende")
    n = int(G["groesse_m"] / G["raster_m"])
    half = G["groesse_m"] / 2.0
    bm = bmesh.new()
    vs = []
    for j in range(n + 1):
        y = -half + j * G["raster_m"]
        row = []
        for i in range(n + 1):
            x = -half + i * G["raster_m"]
            fb, w = _strassen_zone(x, y, L)
            row.append(bm.verts.new((x, y, V.h(x, y) + w)))
        vs.append(row)
    for j in range(n):
        for i in range(n):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            c = f.calc_center_median()
            f.material_index = 0 if _strassen_zone(c.x, c.y, L)[0] else 1
    ob = V.objekt_aus_bmesh("GEO_Gelaende", bm, col, material=[V.blockout_mat("Fahrbahn"), V.blockout_mat("Brache")])
    ob["info"] = "Fahrbahn (Slot 0) und Brache (Slot 1); Hoehe = viertel_lib.h(x,y) + Fahrbahnwoelbung"

    # Aussenring bis 350 m (Horizont), unter dem Kerngelaende abgesenkt
    bm = bmesh.new()
    R, st = 350, 10
    k = int(2 * R / st)
    rows = []
    for j in range(k + 1):
        y = -R + j * st
        row = []
        for i in range(k + 1):
            x = -R + i * st
            z = V.h(max(-half, min(half, x)), max(-half, min(half, y)))
            dd = max(abs(x), abs(y)) - half
            if dd > 0:
                z += 4.0 * noise.noise(Vector((x / 140.0, y / 140.0, 3.3))) * V.smooth(dd / 60.0)
            if abs(x) < half and abs(y) < half:
                z -= 1.0
            row.append(bm.verts.new((x, y, z)))
        rows.append(row)
    for j in range(k):
        for i in range(k):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    V.objekt_aus_bmesh("GEO_Aussengelaende", bm, col, material=V.blockout_mat("Brache"))


# ------------------------------------------------------------------ Strassenbloecke 1.4
def _street(L, name):
    return next(s for s in L["strassen"] if s["name"] == name)


def _offsets(L, block):
    bo = L["bordstein"]["breite"]
    out = set()
    for side, sname in block["seiten"].items():
        s = _street(L, sname)
        out |= {bo, bo + s["gruenstreifen"], bo + s["gruenstreifen"] + s["gehweg"]}
    return sorted(o for o in out if o > 0)


def _interval_cuts(a, b, von_a, von_b, offs, maxstep=1.5):
    """Schnitte im Intervall [a,b]; Offsets gemessen von a (falls von_a) bzw. b (falls von_b)."""
    pts = {a, b}
    for o in offs:
        if von_a and a + o < b:
            pts.add(a + o)
        if von_b and b - o > a:
            pts.add(b - o)
    pts = sorted(pts)
    out = [pts[0]]
    for p in pts[1:]:
        n = max(1, int(math.ceil((p - out[-1]) / maxstep - 1e-6)))
        start = out[-1]
        for k in range(1, n + 1):
            out.append(start + (p - start) * k / n)
    return out


def _sym_corner_cuts(r, offs, maxstep=1.5):
    """Abstaende 0..r vom Aussenrand einer Eckzelle (symmetrisch fuer beide Achsen)."""
    return _interval_cuts(0.0, r, True, False, offs, maxstep)


def block_mesh(L, block):
    bo = L["bordstein"]
    r = bo["eckradius"]
    x0, y0, x1, y1 = block["rechteck"]
    S = block["seiten"]
    offs = _offsets(L, block)
    corner_d = _sym_corner_cuts(r, offs)  # Abstaende vom Aussenrand (0 = Kante)

    def axis_cuts(lo, hi, side_lo, side_hi):
        c_lo = [lo + d for d in corner_d] if side_lo in S else _interval_cuts(lo, lo + r, False, False, [])
        c_hi = [hi - d for d in corner_d][::-1] if side_hi in S else _interval_cuts(hi - r, hi, False, False, [])
        mid = _interval_cuts(lo + r, hi - r, False, False, [])
        return [c_lo, mid, c_hi]

    xc = axis_cuts(x0, x1, "W", "O")
    yc = axis_cuts(y0, y1, "S", "N")
    corners = {"SW": (0, 0), "SO": (2, 0), "NW": (0, 2), "NO": (2, 2)}
    arc = {corners[c]: c for c in block.get("ecken", [])}

    bm = bmesh.new()
    for i in range(3):
        for j in range(3):
            xs, ys = sorted(xc[i]), sorted(yc[j])
            if (i, j) in arc:
                name = arc[(i, j)]
                cx = x0 + r if "W" in name else x1 - r
                cy = y0 + r if "S" in name else y1 - r
                da = Vector((-1 if "W" in name else 1, 0))
                db = Vector((0, -1 if "S" in name else 1))
                radii = sorted(set(round(d, 6) for d in [r - d for d in corner_d]))
                m = 16
                center = bm.verts.new((cx, cy, 0))
                rings = []
                for rad in radii:
                    if rad <= 1e-6:
                        continue
                    ring = []
                    for k in range(m + 1):
                        t = k / m
                        if k == 0:
                            d = da
                        elif k == m:
                            d = db
                        else:
                            ang = t * math.pi / 2
                            d = da * math.cos(ang) + db * math.sin(ang)
                        ring.append(bm.verts.new((cx + d.x * rad, cy + d.y * rad, 0)))
                    rings.append(ring)
                for k in range(m):
                    bm.faces.new((center, rings[0][k], rings[0][k + 1]))
                for q in range(len(rings) - 1):
                    a, b = rings[q], rings[q + 1]
                    for k in range(m):
                        bm.faces.new((a[k], b[k], b[k + 1], a[k + 1]))
            else:
                grid = [[bm.verts.new((x, y, 0)) for x in xs] for y in ys]
                for jj in range(len(ys) - 1):
                    for ii in range(len(xs) - 1):
                        bm.faces.new((grid[jj][ii], grid[jj][ii + 1], grid[jj + 1][ii + 1], grid[jj + 1][ii]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)
    for f in bm.faces:
        f.normal_update()
        if f.normal.z < 0:
            f.normal_flip()

    # Hoehen + Rampen (abgesenkte Bordsteine) an den Kreuzungsecken
    ramps = []
    for name in block.get("ecken", []):
        cx = x0 + r if "W" in name else x1 - r
        cy = y0 + r if "S" in name else y1 - r
        ramps.append((Vector((cx, cy)), (-1 if "W" in name else 1, -1 if "S" in name else 1)))
    for v in bm.verts:
        z = V.h(v.co.x, v.co.y) + bo["hoehe"]
        for c, (sx, sy) in ramps:
            p = Vector((v.co.x, v.co.y)) - c
            if p.x * sx < 0 or p.y * sy < 0:
                continue
            dd = r - p.length
            apex = Vector((sx, sy)).normalized()
            ang = math.acos(max(-1, min(1, p.normalized().dot(apex)))) if p.length > 0 else 0
            arcd = ang * r
            f = (1 - V.smooth(dd / 1.6)) * (1 - V.smooth((arcd - bo["rampe_breite"] / 2) / 0.5))
            z -= (bo["hoehe"] - 0.01) * f
        v.co.z = z

    # Zonen -> Material-Slots: 0 Bordstein, 1 Gehweg, 2 Gruenstreifen, 3 Grundstueck
    def zone(px, py):
        best = (1e9, 3)
        for side, sname in S.items():
            s = _street(L, sname)
            d = {"S": py - y0, "N": y1 - py, "W": px - x0, "O": x1 - px}[side]
            in_arc = None
            for c, (sx, sy) in ramps:
                p = Vector((px, py)) - c
                if p.x * sx >= 0 and p.y * sy >= 0:
                    in_arc = r - p.length
            if in_arc is not None:
                zz = 0 if in_arc < bo["breite"] else (1 if in_arc < bo["breite"] + 4.2 else 3)
                return zz
            if d < best[0]:
                g, w = s["gruenstreifen"], s["gehweg"]
                zz = 0 if d < bo["breite"] else 2 if d < bo["breite"] + g else 1 if d < bo["breite"] + g + w else 3
                best = (d, zz)
        return best[1]

    for f in bm.faces:
        c = f.calc_center_median()
        f.material_index = zone(c.x, c.y)
    # Bordstein-Seitenflaechen: Randkanten nach unten extrudieren
    rand = [e for e in bm.edges if e.is_boundary]
    res = bmesh.ops.extrude_edge_only(bm, edges=rand)
    for v in [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]:
        v.co.z = V.h(v.co.x, v.co.y) - 0.25
    for f in [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]:
        f.material_index = 0
    mats = [V.blockout_mat(z) for z in ("Bordstein", "Gehweg", "Gruenstreifen", "Grundstueck")]
    ob = V.objekt_aus_bmesh(f"STR_Block_{block['name']}", bm, V.collection("02_Strassen/Bloecke"), material=mats)
    ob["info"] = "Slots: 0 Bordstein, 1 Gehweg, 2 Gruenstreifen, 3 Grundstueck"
    return ob


def baumscheiben(L):
    col = V.collection("02_Strassen/Baumscheiben")
    bs = L["baumscheiben"]
    s = _street(L, "STR_Hauptstrasse")
    bo = L["bordstein"]["breite"]
    bm = bmesh.new()
    anzahl = 0
    kreuz = [st["lage"] for st in L["strassen"] if st["achse"] == "y"]
    for blk in L["bloecke"]:
        x0, y0, x1, y1 = blk["rechteck"]
        for side in ("S", "N"):
            if blk["seiten"].get(side) != "STR_Hauptstrasse":
                continue
            yc = (y0 + bo + s["gruenstreifen"] / 2) if side == "S" else (y1 - bo - s["gruenstreifen"] / 2)
            x = x0 + bs["abstand_zur_ecke"]
            while x < x1 - bs["abstand_zur_ecke"]:
                if all(abs(x - k) > 12 for k in kreuz):
                    a, b = bs["groesse"][0] / 2, s["gruenstreifen"] / 2 - 0.02
                    z = V.h(x, yc) + L["bordstein"]["hoehe"]
                    V.box(bm, x - a, yc - b, z - 0.03, x + a, yc + b, z + 0.005)
                    anzahl += 1
                x += bs["abstand"]
    ob = V.objekt_aus_bmesh("STR_Baumscheiben", bm, col, material=V.blockout_mat("Brache"))
    ob["anzahl"] = anzahl
    return ob


def platz(L):
    """Zentraler Platz 40x40 m: Wege, Rasen (Grundstueckszone), Brunnen mit Saeule (eigenes Design), Baenke."""
    P = L["platz"]
    col = V.collection("02_Strassen/Platz")
    x0, y0, x1, y1 = P["rechteck"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    zb = lambda x, y: V.h(x, y) + L["bordstein"]["hoehe"]
    bm = bmesh.new()
    t = 0.04
    def slab(ax0, ay0, ax1, ay1):
        z = zb((ax0 + ax1) / 2, (ay0 + ay1) / 2)
        V.box(bm, ax0, ay0, z - 0.05, ax1, ay1, z + t)
    w = 3.0
    slab(x0, y0, x1, y0 + w); slab(x0, y1 - w, x1, y1); slab(x0, y0, x0 + w, y1); slab(x1 - w, y0, x1, y1)
    slab(cx - 2, y0, cx + 2, y1); slab(x0, cy - 2, x1, cy + 2)
    V.objekt_aus_bmesh("STR_Platz_Wege", bm, col, material=V.blockout_mat("Gehweg"))
    # Brunnen: achteckiges Becken, Sockel, Saeule mit Kugelaufsatz (eigenes Design "Siedlerbrunnen")
    bm = bmesh.new()
    z = zb(cx, cy)
    R = P["brunnen_durchmesser"] / 2
    # Becken aus 8 Wandstuecken (0,55 m hoch, 0,4 m dick) + Beckenboden
    seite = 2 * R * math.sin(math.pi / 8)
    for k in range(8):
        a8 = k * math.pi / 4
        wb = bmesh.new()
        V.box(wb, -seite / 2 - 0.08, -0.2, 0, seite / 2 + 0.08, 0.2, 0.55)
        bmesh.ops.rotate(wb, verts=wb.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(a8 + math.pi / 2, 3, "Z"))
        rr = R * math.cos(math.pi / 8) - 0.2
        bmesh.ops.translate(wb, verts=wb.verts, vec=(cx + math.cos(a8) * rr, cy + math.sin(a8) * rr, z - 0.05))
        me = bpy.data.meshes.new("tmp")
        wb.to_mesh(me)
        wb.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=R - 0.3, radius2=R - 0.3, depth=0.2,
                          matrix=Matrix.Translation((cx, cy, z + 0.02)) @ Matrix.Rotation(math.pi / 8, 4, "Z"))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.9, radius2=0.8, depth=1.0,
                          matrix=Matrix.Translation((cx, cy, z + 0.5)))
    V.box(bm, cx - 0.35, cy - 0.35, z + 1.0, cx + 0.35, cy + 0.35, z + 4.2)
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.45,
                              matrix=Matrix.Translation((cx, cy, z + 4.6)))
    ob = V.objekt_aus_bmesh("STR_Platz_Brunnen", bm, col, material=V.blockout_mat("Beton"))
    V.fase(ob, 0.02, 2)
    # Baenke um den Brunnen (8 Stueck)
    bm = bmesh.new()
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        bx, by = cx + math.cos(a) * 7.5, cy + math.sin(a) * 7.5
        zz = zb(bx, by)
        bb = bmesh.new()
        V.box(bb, -0.9, -0.25, zz + 0.0, 0.9, 0.25, zz + 0.45)
        V.box(bb, -0.9, 0.2, zz + 0.45, 0.9, 0.28, zz + 0.85)
        bmesh.ops.rotate(bb, verts=bb.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(a + math.pi / 2, 3, "Z"))
        bmesh.ops.translate(bb, verts=bb.verts, vec=(bx, by, 0))
        me = bpy.data.meshes.new("tmp")
        bb.to_mesh(me)
        bb.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    V.objekt_aus_bmesh("PRP_Platz_Baenke", bm, col, material=V.blockout_mat("Holz"))


def gasse(L):
    G = L["gasse"]
    col = V.collection("02_Strassen/Gasse")
    x0, y0, x1, y1 = G["rechteck"]
    bm = bmesh.new()
    n = int((x1 - x0) / 1.5)
    verts = []
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        verts.append([bm.verts.new((x, y, V.h(x, y) + L["bordstein"]["hoehe"] + 0.03)) for y in (y0, (y0 + y1) / 2, y1)])
    for i in range(n):
        for k in range(2):
            bm.faces.new((verts[i][k], verts[i + 1][k], verts[i + 1][k + 1], verts[i][k + 1]))
    V.objekt_aus_bmesh("STR_Gasse_Belag", bm, col, material=V.blockout_mat("Fahrbahn"))
    # Muellcontainer (1,8 x 1,1 x 1,25 m) an der Gasse
    bm = bmesh.new()
    rnd = random.Random(5)
    for x in (-40.0, -27.5, -9.0, 6.0):
        yy = y0 + 0.75
        z = V.h(x, yy) + L["bordstein"]["hoehe"] + 0.03
        V.box(bm, x - 0.9, yy - 0.55, z, x + 0.9, yy + 0.55, z + 1.25)
    ob = V.objekt_aus_bmesh("PRP_Gasse_Muellcontainer", bm, col, material=V.blockout_mat("Metall"))
    V.fase(ob, 0.02, 2)


def hochstrasse(L):
    H = L["hochstrasse"]
    col = V.collection("02_Strassen/Hochstrasse")
    rnd = random.Random(11)
    X, B, D = H["achse_x"], H["breite"], H["dicke"]
    ztop = V.h(X, 0) + H["oberkante_ueber_boden"]
    zbot = ztop - D
    a, b = H["eingestuerzt_von"], H["eingestuerzt_bis"]

    def jagged_end(bm, y_end, richtung, z0, z1):
        """Bruchkante: unregelmaessiges Ende einer Platte (richtung +1 = Platte liegt bei y>y_end)."""
        n = 10
        pts = []
        for i in range(n + 1):
            x = X - B / 2 + B * i / n
            pts.append((x, y_end + richtung * rnd.uniform(0.0, 0.9)))
        return pts

    bm = bmesh.new()
    y = H["von"]
    segs = []
    p = H["pfeiler_start"]
    stuetzen = []
    while p <= H["bis"]:
        stuetzen.append(p)
        p += H["pfeiler_abstand"]
    # Fahrbahnplatten zwischen den Stuetzen (Ausnahme: eingestuerztes Feld)
    kanten = [H["von"]] + stuetzen + [H["bis"]]
    for y0, y1 in zip(kanten[:-1], kanten[1:]):
        if y0 >= a - 0.1 and y1 <= b + 0.1:
            continue
        if abs(y1 - a) < 0.1:  # Bruchkante Sued-Teil (Platte endet bei a, gezackt)
            prof = jagged_end(bm, a, -1, zbot, ztop)
            _platte_profil(bm, X, B, y0, prof, zbot, ztop, "hi", rnd)
        elif abs(y0 - b) < 0.1:
            prof = jagged_end(bm, b, 1, zbot, ztop)
            _platte_profil(bm, X, B, y1, prof, zbot, ztop, "lo", rnd)
        else:
            V.box(bm, X - B / 2, y0, zbot, X + B / 2, y1, ztop)
    ob = V.objekt_aus_bmesh("STR_Hochstrasse_Fahrbahn", bm, col, material=V.blockout_mat("Beton"))
    V.fase(ob, 0.02, 2)
    # Pfeiler + Querriegel
    bm = bmesh.new()
    for sy in stuetzen:
        zg = V.h(X, sy) - 0.5
        hh = (zbot - 1.2) - zg
        for dx in (-3.5, 3.5):
            bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=H["pfeiler_durchmesser"] / 2,
                                  radius2=H["pfeiler_durchmesser"] / 2, depth=hh,
                                  matrix=Matrix.Translation((X + dx, sy, zg + hh / 2)))
        V.box(bm, X - B / 2 + 0.5, sy - 0.9, zbot - 1.2, X + B / 2 - 0.5, sy + 0.9, zbot)
    ob = V.objekt_aus_bmesh("STR_Hochstrasse_Pfeiler", bm, col, material=V.blockout_mat("Beton"))
    # Abgestuerztes Feld: Nordende lehnt auf ca. 4,5 m am Pfeiler, Suedende liegt auf der Strasse
    bm = bmesh.new()
    L_seg = b - a - 0.6
    V.box(bm, -B / 2, -L_seg / 2, -D / 2, B / 2, L_seg / 2, D / 2)
    z_n = V.h(X, b) + 4.5
    z_s = V.h(X, a) + 0.75
    ang = math.atan2(z_n - z_s, L_seg)
    rot = Matrix.Rotation(math.radians(4), 3, "Z") @ Matrix.Rotation(math.radians(-2.5), 3, "Y") @ Matrix.Rotation(ang, 3, "X")
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=rot)
    mid = Vector((X + 0.6, (a + b) / 2 - 0.4, (z_n + z_s) / 2))
    ob = V.objekt_aus_bmesh("STR_Hochstrasse_Abgestuerzt", bm, col, location=mid, material=V.blockout_mat("Beton"))
    _bewehrung(col, X, B, ztop, zbot, a, b, ob, rnd)
    _leitplanken(col, X, B, ztop, kanten, a, b, rnd)
    return ob


def _platte_profil(bm, X, B, y_fest, prof, zbot, ztop, ende, rnd):
    """Platte von y_fest bis zum gezackten Profil (Liste (x,y))."""
    unten, oben = [], []
    for (x, y) in prof:
        unten.append(bm.verts.new((x, y, zbot)))
        oben.append(bm.verts.new((x, y + (0.15 if ende == "hi" else -0.15) * rnd.random(), ztop)))
    f0 = [bm.verts.new((X - B / 2, y_fest, zbot)), bm.verts.new((X + B / 2, y_fest, zbot))]
    f1 = [bm.verts.new((X - B / 2, y_fest, ztop)), bm.verts.new((X + B / 2, y_fest, ztop))]
    bm.faces.new(f0[::-1] + unten if ende == "hi" else f0 + unten[::-1])
    bm.faces.new(f1 + oben[::-1] if ende == "hi" else f1[::-1] + oben)
    for i in range(len(prof) - 1):
        bm.faces.new((unten[i], unten[i + 1], oben[i + 1], oben[i]))
    bm.faces.new((f0[0], f1[0], oben[0], unten[0]))
    bm.faces.new((f0[1], unten[-1], oben[-1], f1[1]))
    bm.faces.new((f0[0], f0[1], f1[1], f1[0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def _bewehrung(col, X, B, ztop, zbot, a, b, gefallen, rnd):
    """Bewehrungsstaebe (Ø 2,5 cm) an den Bruchkanten, teils verbogen."""
    bm = bmesh.new()
    for y_end, s in ((a, 1), (b, -1)):
        for i in range(38):
            x = X - B / 2 + 0.3 + (B - 0.6) * rnd.random()
            z = rnd.choice([zbot + 0.12, ztop - 0.12])
            lng = rnd.uniform(0.3, 1.4)
            d = Vector((rnd.uniform(-0.15, 0.15), s, rnd.uniform(-0.5, 0.1))).normalized()
            start = Vector((x, y_end - s * 0.5, z))
            m = Matrix.Translation(start + d * lng / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
            bmesh.ops.create_cone(bm, cap_ends=False, segments=5, radius1=0.0125, radius2=0.0125, depth=lng, matrix=m)
    V.objekt_aus_bmesh("STR_Hochstrasse_Bewehrung", bm, col, material=V.blockout_mat("Metall"), uv=False)


def _leitplanken(col, X, B, ztop, kanten, a, b, rnd):
    """Stahl-Leitplanken auf beiden Plattenraendern; an der Bruchstelle herabhaengend."""
    bm = bmesh.new()
    for sx in (-1, 1):
        xr = X + sx * (B / 2 - 0.35)
        y = kanten[0]
        while y < kanten[-1]:
            if a - 0.2 < y < b + 0.2:
                y += 2.0
                continue
            V.box(bm, xr - 0.08, y - 0.08, ztop, xr + 0.08, y + 0.08, ztop + 0.75)
            y += 2.0
        for (y0, y1) in ((kanten[0], a), (b, kanten[-1])):
            V.box(bm, xr - 0.04 * sx - 0.03, y0, ztop + 0.45, xr - 0.04 * sx + 0.03, y1, ztop + 0.78)
        # herabhaengende Stuecke an beiden Bruchkanten
        for (y_end, s) in ((a, 1), (b, -1)):
            hb = bmesh.new()
            V.box(hb, -0.03, 0, -0.16, 0.03, 4.0, 0.16)
            rot = Matrix.Rotation(-math.radians(rnd.uniform(55, 80)) * s, 3, "X")
            bmesh.ops.rotate(hb, verts=hb.verts, cent=(0, 0, 0), matrix=rot @ Matrix.Rotation(math.radians(180 if s < 0 else 0), 3, "Z"))
            bmesh.ops.translate(hb, verts=hb.verts, vec=(xr, y_end, ztop + 0.6))
            me = bpy.data.meshes.new("tmp")
            hb.to_mesh(me)
            hb.free()
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
    V.objekt_aus_bmesh("STR_Hochstrasse_Leitplanken", bm, col, material=V.blockout_mat("Metall"))


def hintergrund(L):
    """Silhouetten gegen leere Horizonte: Baumgruppen + ferne Gebaeude (nur grobe Formen)."""
    H = L["hintergrund"]
    rnd = random.Random(H["seed"])
    col = V.collection("01_Gelaende/Hintergrund")
    bm = bmesh.new()
    for i in range(H["baumgruppen"]):
        a = rnd.uniform(0, 2 * math.pi)
        rad = rnd.uniform(H["radius_min"], H["radius_max"])
        x, y = math.cos(a) * rad, math.sin(a) * rad
        zg = _aussen_h(x, y)
        for k in range(rnd.randint(3, 7)):
            dx, dy = rnd.uniform(-14, 14), rnd.uniform(-14, 14)
            w, hgt = rnd.uniform(6, 13), rnd.uniform(9, 20)
            m = Matrix.Translation((x + dx, y + dy, zg + hgt * 0.55)) @ Matrix.Diagonal((w, w * rnd.uniform(0.8, 1.2), hgt * 0.55, 1))
            bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0, matrix=m)
    ob = V.objekt_aus_bmesh("VEG_Hintergrund_Baumgruppen", bm, col, material=V.blockout_mat("Baum"))
    for pg in ob.data.polygons:
        pg.use_smooth = True
    bm = bmesh.new()
    for i in range(H["ferne_gebaeude"]):
        a = rnd.uniform(-0.2 * math.pi, 1.1 * math.pi)  # vor allem Norden/Osten (Kamera-Blickrichtungen)
        rad = rnd.uniform(220, H["radius_max"])
        x, y = math.cos(a) * rad, math.sin(a) * rad
        w, d, hgt = rnd.uniform(12, 35), rnd.uniform(12, 30), rnd.choice([9, 12, 16, 24, 32, 45])
        zg = _aussen_h(x, y) - 0.5
        V.box(bm, x - w / 2, y - d / 2, zg, x + w / 2, y + d / 2, zg + hgt)
    V.objekt_aus_bmesh("BLD_Hintergrund_Silhouetten", bm, col, material=V.blockout_mat("Hintergrund"))
    # Rauchsaeulen-Positionen (Phase 5) als Empties merken
    for i, (x, y) in enumerate([(240, 160), (-180, 230)]):
        e = bpy.data.objects.new(f"FX_Rauchsaeule_Position_{i + 1}", None)
        e.location = (x, y, _aussen_h(x, y))
        V.collection("10_Licht_Atmosphaere").objects.link(e)


def _aussen_h(x, y):
    half = V.gelaende_cfg()["groesse_m"] / 2
    z = V.h(max(-half, min(half, x)), max(-half, min(half, y)))
    dd = max(abs(x), abs(y)) - half
    if dd > 0:
        z += 4.0 * noise.noise(Vector((x / 140.0, y / 140.0, 3.3))) * V.smooth(dd / 60.0)
    return z


def bauen():
    L = V.config("layout.json")
    gelaende()
    for blk in L["bloecke"]:
        block_mesh(L, blk)
    baumscheiben(L)
    platz(L)
    gasse(L)
    hochstrasse(L)
    hintergrund(L)
