"""Phase 3.3/3.4 – Kampfpanzer (generisch modern, eigenes Design), Hero-Objekt.

Lokale Koordinaten: x nach vorne (Bug), y nach links, z nach oben, Boden z = 0.
Baugruppen: Wanne (Bug, Fahrerluke, Scheinwerfer, Heck, Lueftungsgitter), Laufwerk (7 Laufrollen je Seite, Leitrad,
Triebrad, Stuetzrollen, Schwingarme), Kette (einzelne Glieder als Instanzen), Schuerzen (6 Segmente),
Turm (Facetten, Blende, Rohr mit Waermeschutz + Rauchabsauger, Kommandantenkuppel, Luken offen, Optiken,
Nebelwurfbecher, Staukorb mit Ladung), Anbauteile (Werkzeug, Abschleppseile, Haken, Ersatzglieder).
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
import fz_material as FM  # noqa: E402
import mil_detail as MD  # noqa: E402
import fz_teile as FT  # noqa: E402

Q, ZY, OB = FT.quader, FT.zylinder, FT.objekt


def cfg():
    return V.config("militaer.json")


def mats():
    return {
        "tarn": MD.lack_veredeln(V.material("MAT_Panzer_Tarn")),  # 2B: Abplatzer, Schmutz, Dellen-Bump
        "rost": V.material("MAT_Rost_Dunkel"),
        "rost_hell": V.material("MAT_Rost_Hell"),
        "gummi": V.material("MAT_Gummi"),
        "dunkel": FM.dunkel(),
        "glas": FM.autoglas(),
        "draht": V.mat_maschendraht(),
        "plane": V.material("MAT_Plane_Oliv"),
        "sack": V.material("MAT_Sackleinen"),
        "holz": V.material("MAT_Holz_Bretter_Alt"),
        "schrift": FM.text_mat("Schablone", "#2B2A25", 0.8),
        "scheinwerfer": FM.streuscheibe("Klar", "#EEF0EC"),
        "reflektor": FM.reflektor(),
    }


def prisma(bm, poly, y0, y1, mat=0):
    """Seitenprofil [(x, z), ...] (gegen den Uhrzeigersinn) zwischen y0 und y1 extrudiert."""
    a = [bm.verts.new((x, y0, z)) for x, z in poly]
    b = [bm.verts.new((x, y1, z)) for x, z in poly]
    fl = [bm.faces.new(list(reversed(a))), bm.faces.new(b)]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        fl.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in fl:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=fl)
    return fl


def loft2(bm, unten, oben, z0, z1, mat=0):
    """Grundriss-Polygone (x, y) unten/oben -> geschlossener Koerper (Turm)."""
    a = [bm.verts.new((x, y, z0)) for x, y in unten]
    b = [bm.verts.new((x, y, z1)) for x, y in oben]
    fl = [bm.faces.new(list(reversed(a))), bm.faces.new(b)]
    n = len(unten)
    for i in range(n):
        j = (i + 1) % n
        fl.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in fl:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=fl)
    return fl


def _fase(ob, w=0.02, seg=2, winkel=35):
    m = ob.modifiers.new("Fase", "BEVEL")
    m.width = w
    m.segments = seg
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(winkel)
    m.use_clamp_overlap = True
    return m


def _scheibe(profil_rz, seg=32, mat=0, bm=None):
    """Rotationskoerper um die y-Achse (Rad/Rolle), Profil [(r, y)]."""
    return FT.rotation_um_y(profil_rz, seg, mat, bm)


# ---------------------------------------------------------------- Kette
def kettenglied_proto(M):
    col = V.prototypen("Kettenglied")
    if col.objects:
        return col
    bm = bmesh.new()
    t, b = 0.17, 0.63
    Q(bm, (0, 0.165, 0.0), (t - 0.025, 0.25, 0.05), 0)          # Platte links
    Q(bm, (0, -0.165, 0.0), (t - 0.025, 0.25, 0.05), 0)         # Platte rechts
    Q(bm, (0.01, 0.165, 0.033), (0.07, 0.22, 0.022), 1)          # Gummipolster
    Q(bm, (0.01, -0.165, 0.033), (0.07, 0.22, 0.022), 1)
    for y in (0.30, -0.30, 0.03, -0.03):
        Q(bm, (t / 2 - 0.005, y, 0.0), (0.05, 0.035 if abs(y) > 0.1 else 0.03, 0.065), 0)  # Endverbinder
    Q(bm, (0.0, 0.0, -0.075), (0.07, 0.05, 0.11), 0)            # Fuehrungszahn
    ZY(bm, (t / 2 - 0.005, -b / 2, 0), (t / 2 - 0.005, b / 2, 0), 0.016, 8, 0)  # Bolzen
    ob = OB("MIL_Kettenglied", bm, col, [M["rost"], M["gummi"]])
    _fase(ob, 0.006, 1, 40)
    ob["lack_alter"] = 1.0
    return col


def kettenpfad(P):
    """Mittellinie der Kette (x, z), Umlauf: oben nach hinten, Triebrad, unten nach vorne, Leitrad."""
    lx, lz, lr = P["leitrad"]
    tx, tz, tr = P["triebrad"]
    zs, rs = P["stuetzrolle"]
    rz, rr = P["laufrolle_z"], P["laufrolle_r"]
    d = 0.04
    pts = []
    oben_v, oben_h = zs + rs + d, zs + rs + d
    # oberes Trum (leicht durchhaengend zwischen den Stuetzrollen)
    for k in range(41):
        x = lx - (lx - tx) * k / 40
        sx = sorted([lx, tx] + P["stuetzrollen_x"], reverse=True)
        sack = 0.0
        for a, b in zip(sx, sx[1:]):
            if b <= x <= a:
                u = (x - b) / max(a - b, 1e-6)
                sack = 0.035 * math.sin(math.pi * u)
        zt = (lz + lr + d) + ((tz + tr + d) - (lz + lr + d)) * k / 40
        pts.append(Vector((x, 0, max(zt, oben_v) - sack)))
    # Triebrad hinten (Halbkreis nach unten)
    for k in range(1, 18):
        a = math.pi / 2 + math.pi * k / 18 * 0.95
        pts.append(Vector((tx + (tr + d) * math.cos(a), 0, tz + (tr + d) * math.sin(a))))
    # unteres Trum
    zb = rz - rr - d
    x0 = P["laufrollen_x"][-1] - 0.2
    x1 = P["laufrollen_x"][0] + 0.2
    pts.append(Vector((x0, 0, zb)))
    pts.append(Vector((x1, 0, zb)))
    # Leitrad vorne (von unten nach oben)
    for k in range(0, 18):
        a = -math.pi / 2 + math.pi * 0.35 + math.pi * 0.65 * k / 17
        pts.append(Vector((lx + (lr + d) * math.cos(a), 0, lz + (lr + d) * math.sin(a))))
    return pts


def glieder_auf_pfad(pts, teilung, geschlossen=True):
    """Gleichmaessige Teilung entlang des Pfades -> (pos, euler) je Glied."""
    seg = list(zip(pts, pts[1:] + ([pts[0]] if geschlossen else [])))
    laengen = [(b - a).length for a, b in seg]
    gesamt = sum(laengen)
    n = int(gesamt / teilung)
    schritt = gesamt / n
    out = []
    for i in range(n):
        s = i * schritt
        k = 0
        while k < len(laengen) - 1 and s > laengen[k]:
            s -= laengen[k]
            k += 1
        a, b = seg[k]
        p = a.lerp(b, s / max(laengen[k], 1e-6))
        t = (b - a).normalized()
        nrm = Vector((0, 1, 0)).cross(t)  # aussen: oben auf dem oberen Trum, unten auf dem unteren
        bb = nrm.cross(t)
        mx = Matrix((t, bb, nrm)).transposed()
        out.append((p, mx.to_euler()))
    return out


# ---------------------------------------------------------------- Panzer
def bauen(name, C, col, rnd, opt):
    P = C["panzer_masse"]
    M = mats()
    root = bpy.data.objects.new(name, None)
    col.objects.link(root)
    root.empty_display_size = 3
    root["typ"] = "Kampfpanzer (generisch)"
    deck = P["deck_z"]
    spz = 1.12  # Unterkante Kettenabdeckung
    # Wanne
    bm = bmesh.new()
    prisma(bm, [(3.70, 0.95), (3.40, 0.48), (-3.55, 0.48), (-3.82, 0.82), (-3.82, spz), (3.70, spz)], -1.10, 1.10, 0)
    prisma(bm, [(3.88, spz), (2.15, deck), (-3.82, deck), (-3.90, deck - 0.12), (-3.90, spz)], -1.75, 1.75, 0)
    # Lueftungsgitter auf dem Motordeck, Rahmen
    for k in range(26):
        x = -3.55 + k * 0.095
        Q(bm, (x, 0.62, deck + 0.012), (0.035, 0.95, 0.024), 2)
        Q(bm, (x, -0.62, deck + 0.012), (0.035, 0.95, 0.024), 2)
    for x in (-3.62, -1.08):
        Q(bm, (x, 0, deck + 0.02), (0.06, 2.6, 0.04), 0)
    # Auspuffgitter am Heck
    for k in range(10):
        Q(bm, (-3.92, 0, spz + 0.05 + k * 0.035), (0.03, 2.2, 0.018), 2)
    # Kotfluegel vorne, Haken, Heckleuchten-Schutz
    for s in (1, -1):
        Q(bm, (3.75, s * 1.43, spz + 0.02), (0.45, 0.70, 0.03), 0)
        for x, z in ((3.86, 0.72), (-3.93, 0.98)):
            ZY(bm, (x, s * 0.9 - 0.06, z), (x, s * 0.9 + 0.06, z), 0.06, 10, 2)
            Q(bm, (x - 0.06 * (1 if x > 0 else -1), s * 0.9, z + 0.06), (0.12, 0.16, 0.06), 0)
        Q(bm, (-3.93, s * 1.45, deck - 0.2), (0.06, 0.25, 0.18), 0)
    # Schweissnaehte an Bug und Seiten, Schraubenreihe auf der Schuerzenoberkante, Deckel/Klappen auf dem Motordeck
    for s in (1, -1):
        ZY(bm, (3.88, s * 1.74, spz), (2.15, s * 1.74, deck), 0.014, 5, 0)
        ZY(bm, (2.15, s * 1.74, deck), (-3.82, s * 1.74, deck), 0.012, 5, 0)
        ZY(bm, (3.70, s * 1.09, 0.95), (3.40, s * 1.09, 0.48), 0.014, 5, 0)
        for k in range(26):
            x = 3.55 - k * 0.265
            ZY(bm, (x, s * 1.755, spz - 0.02), (x, s * 1.79, spz - 0.02), 0.018, 6, 0)
    for x0_, y0_ in ((-0.6, 0.85), (-0.6, -0.85), (1.4, 1.2), (1.4, -1.2)):
        Q(bm, (x0_, y0_, deck + 0.012), (0.75, 0.55, 0.025), 0)
        for dx in (-0.33, 0.33):
            for dy in (-0.23, 0.23):
                ZY(bm, (x0_ + dx, y0_ + dy, deck + 0.02), (x0_ + dx, y0_ + dy, deck + 0.04), 0.016, 6, 0)
    hull = OB(f"{name}_Wanne", bm, col, [M["tarn"], M["dunkel"], M["rost"]], root)
    _fase(hull, 0.025, 2)
    # Fahrerluke, Winkelspiegel, Scheinwerfer mit Schutzgitter
    bm = bmesh.new()
    neig = math.atan2(deck - spz, 3.88 - 2.15)
    rot = Matrix.Rotation(-neig, 3, "Y")
    zg = spz + (3.88 - 2.62) * math.tan(neig)
    ZY(bm, Vector((2.62, 0, zg)), Vector((2.62, 0, zg)) + rot @ Vector((0, 0, 0.06)), 0.34, 20, 0)
    for dy in (-0.16, 0, 0.16):
        Q(bm, Vector((2.95, dy, spz + (3.88 - 2.95) * math.tan(neig) + 0.05)), (0.08, 0.12, 0.08), 0, rot)
        Q(bm, Vector((2.99, dy, spz + (3.88 - 2.99) * math.tan(neig) + 0.06)), (0.005, 0.10, 0.05), 1, rot)
    for s in (1, -1):
        c = Vector((3.62, s * 1.38, spz + 0.17))
        ZY(bm, c - Vector((0.08, 0, 0)), c + Vector((0.06, 0, 0)), 0.08, 14, 0)
        ZY(bm, c + Vector((0.06, 0, 0)), c + Vector((0.065, 0, 0)), 0.065, 14, 3)
        for dz in (-0.07, 0.07):
            ZY(bm, c + Vector((0.12, -0.1, dz)), c + Vector((0.12, 0.1, dz)), 0.008, 6, 2)
        for dy in (-0.1, 0.1):
            ZY(bm, c + Vector((0.12, dy, -0.07)), c + Vector((0.12, dy, 0.07)), 0.008, 6, 2)
            ZY(bm, c + Vector((0.12, dy, -0.07)), c + Vector((-0.05, dy, -0.09)), 0.008, 6, 2)
    OB(f"{name}_Bug_Details", bm, col, [M["tarn"], M["glas"], M["rost"], M["scheinwerfer"]], root)
    # Werkzeug, Abschleppseile, Ersatzglieder
    bm = bmesh.new()
    fehlt = opt.get("werkzeug_fehlt", [])
    yw = -1.55
    if "schaufel" not in fehlt:
        ZY(bm, (-1.2, yw, deck + 0.04), (0.1, yw, deck + 0.04), 0.018, 8, 1)
        Q(bm, (-1.42, yw, deck + 0.03), (0.36, 0.25, 0.012), 2)
    if "axt" not in fehlt:
        ZY(bm, (0.4, yw, deck + 0.04), (1.25, yw, deck + 0.04), 0.02, 8, 1)
        Q(bm, (1.3, yw, deck + 0.04), (0.14, 0.03, 0.16), 2)
    if "brechstange" not in fehlt:
        ZY(bm, (-2.9, yw + 0.12, deck + 0.03), (-1.5, yw + 0.12, deck + 0.03), 0.015, 6, 2)
    for k in range(6):  # Halterungen
        Q(bm, (-2.8 + k * 0.75, yw, deck + 0.02), (0.04, 0.3, 0.04), 0)
    for dz, dy in ((0.04, 1.52), (0.04, 1.62)):
        pts = []
        for k in range(21):
            x = -2.8 + 4.0 * k / 20
            pts.append(Vector((x, dy, deck + dz + 0.02 - 0.04 * math.sin(math.pi * ((k % 5) / 5)))))
        FT.profil_zug(bm, pts, [(0.016 * math.cos(a), 0.016 * math.sin(a)) for a in [i * math.pi / 4 for i in range(8)]], mat=2)
    OB(f"{name}_Werkzeug_Seile", bm, col, [M["tarn"], M["holz"], M["rost"]], root, glatt=True)
    # Laufwerk
    proto = kettenglied_proto(M)
    rr, rz = P["laufrolle_r"], P["laufrolle_z"]
    rolle = bpy.data.meshes.get("MIL_Laufrolle")
    if rolle is None:
        bmr = bmesh.new()
        for off in (-0.1, 0.1):
            pr = [(0.06, off - 0.06), (0.29, off - 0.06), (0.29, off + 0.06), (0.06, off + 0.06)]
            _scheibe([(r, y) for r, y in pr], 28, 0, bmr)
            _scheibe([(0.29, off - 0.065), (rr, off - 0.065), (rr, off + 0.065), (0.29, off + 0.065)], 28, 1, bmr)
            for k in range(4):
                a = 2 * math.pi * k / 4 + 0.4
                c = Vector((0.18 * math.cos(a), off + 0.063 * (1 if off > 0 else -1), 0.18 * math.sin(a)))
                ZY(bmr, c, c + Vector((0, 0.004 * (1 if off > 0 else -1), 0)), 0.055, 12, 2)
        ZY(bmr, (0, -0.2, 0), (0, 0.2, 0), 0.06, 12, 0)
        rolle = bpy.data.meshes.new("MIL_Laufrolle")
        bmr.to_mesh(rolle)
        bmr.free()
        for m in (M["rost"], M["gummi"], M["dunkel"]):
            rolle.materials.append(m)
    bm_arm = bmesh.new()
    seiten = {"l": 1, "r": -1}
    ab = opt.get("kette_ab")
    for sn, s in seiten.items():
        yt = s * P["kette_y"]
        ohne = (ab == sn)
        zr = rz if not ohne else rr  # ohne Kette stehen die Rollen direkt auf dem Boden
        for k, x in enumerate(P["laufrollen_x"]):
            o = bpy.data.objects.new(f"{name}_Laufrolle_{sn}{k}", rolle)
            o.location = (x, yt, zr)
            o.parent = root
            col.objects.link(o)
            Q(bm_arm, ((x + 0.32 + x) / 2, s * 1.16, (zr + 0.62) / 2 + 0.05), (0.42, 0.08, 0.10), 0,
              Matrix.Rotation(math.radians(-18), 3, "Y"))
        lx, lz, lr = P["leitrad"]
        tx, tz, tr = P["triebrad"]
        dz = 0.0 if not ohne else -(rz - rr)
        b2 = bmesh.new()
        _scheibe([(0.05, -0.17), (lr, -0.17), (lr, -0.04), (0.08, -0.04)], 28, 0, b2)
        _scheibe([(0.08, 0.04), (lr, 0.04), (lr, 0.17), (0.05, 0.17)], 28, 0, b2)
        bmesh.ops.translate(b2, vec=(lx, yt, lz + dz), verts=b2.verts)
        _einfuegen(bm_arm, b2)
        b3 = bmesh.new()
        _scheibe([(0.06, -0.16), (tr - 0.03, -0.16), (tr - 0.03, 0.16), (0.06, 0.16)], 28, 0, b3)
        for k in range(12):  # Zahnkranz
            a = 2 * math.pi * k / 12
            for yy in (-0.11, 0.11):
                Q(b3, (tr * math.cos(a), yy, tr * math.sin(a)), (0.07, 0.05, 0.07), 0, Matrix.Rotation(-a, 3, "Y"))
        bmesh.ops.translate(b3, vec=(tx, yt, tz + dz), verts=b3.verts)
        _einfuegen(bm_arm, b3)
        zs, rs = P["stuetzrolle"]
        for x in P["stuetzrollen_x"]:
            ZY(bm_arm, (x, yt - 0.13, zs + dz), (x, yt + 0.13, zs + dz), rs, 16, 0)
            ZY(bm_arm, (x, s * 1.12, zs + dz), (x, yt, zs + dz), 0.03, 8, 0)
        # Kette
        if not ohne:
            punkte = []
            for p, e in glieder_auf_pfad(kettenpfad(P), P["kette_teilung"]):
                punkte.append((Vector((p.x, yt, p.z)), tuple(e), (1, 1, 1), 0))
            V.instanzen(f"{name}_Kette_{sn}", punkte, proto, col).parent = root
        else:
            # abgesprungene Kette: gestreckt vor/neben dem Panzer auf dem Boden, Ende aufgefaltet
            punkte = []
            Lk = opt.get("kette_ab_laenge", 6.0)
            n = int(Lk / P["kette_teilung"])
            for i in range(n):
                t = i / n
                x = 3.2 + i * P["kette_teilung"] * 0.98
                y = yt + s * (0.35 * t * t) + 0.04 * math.sin(i * 0.7)
                z = 0.04
                rot_z = s * 0.35 * t
                kipp = 0.0
                if i > n - 7:  # umgeschlagenes Ende
                    z = 0.04 + 0.07 * (i - (n - 7))
                    kipp = -0.5
                punkte.append((Vector((x, y, z)), (math.pi, kipp, rot_z), (1, 1, 1), 0))
            for i in range(14):  # Rest unter den Rollen hervor
                x = 3.2 - i * P["kette_teilung"]
                punkte.append((Vector((x, yt + s * 0.55, 0.04)), (math.pi, 0.0, s * 0.08), (1, 1, 1), 0))
            V.instanzen(f"{name}_Kette_{sn}_abgesprungen", punkte, proto, col).parent = root
    arm = OB(f"{name}_Laufwerk", bm_arm, col, [M["rost"]], root, glatt=True)
    # Schuerzen (6 Segmente je Seite), einige fehlen/verbogen
    fehlen = {(a, b) for a, b in opt.get("schuerzen_fehlen", [])}
    biegen = {(a, b): w for a, b, w in opt.get("schuerzen_verbogen", [])}
    bm = bmesh.new()
    x0, x1 = 3.62, -3.30
    for sn, s in seiten.items():
        for k in range(6):
            if (sn, k) in fehlen:
                continue
            a = x0 + (x1 - x0) * k / 6
            b = x0 + (x1 - x0) * (k + 1) / 6
            dicke = 0.08 if k == 0 else 0.035
            c = Vector(((a + b) / 2, s * (P["schuerze_b"] / 2 + dicke / 2), 0.80))
            w = biegen.get((sn, k), 0)
            rot = Matrix.Rotation(math.radians(w) * s, 3, "X")
            hoehe = 0.66 if k else 0.62
            Q(bm, c + rot @ Vector((0, 0, 0.0)), (abs(b - a) - 0.012, dicke, hoehe), 0, rot)
            if k == 0:  # vorderes Segment unten abgeschraegt
                Q(bm, c + Vector((0.12, 0, -0.36)), (abs(b - a) - 0.25, dicke, 0.12), 0, rot)
    sch = OB(f"{name}_Schuerzen", bm, col, [M["tarn"]], root)
    _fase(sch, 0.012, 2)
    # Turm
    turm = turm_bauen(name, C, col, M, opt, rnd)
    turm.parent = root
    turm.location = (P["turm_x"], 0, deck)
    turm.rotation_euler = (0, 0, math.radians(opt.get("turm_grad", 0)))
    # Ersatz-Kettenglieder auf dem Bug
    for k, y in enumerate((-0.75, -0.55, 0.55, 0.75)):
        o = proto.objects[0].copy()
        o.location = (3.25, y, spz + (3.88 - 3.25) * math.tan(neig) + 0.06)
        o.rotation_euler = (0, -neig, math.pi / 2)
        o.parent = root
        col.objects.link(o)
    # Innenraum (durch die offenen Luken nur angedeutet)
    bm = bmesh.new()
    Q(bm, (0.25, 0, deck - 0.45), (2.2, 2.0, 0.04), 0)
    Q(bm, (2.55, 0, deck - 0.35), (0.5, 0.45, 0.4), 0)
    OB(f"{name}_Innen", bm, col, [M["dunkel"]], root)
    for o in root.children_recursive:
        o["lack_alter"] = 1.0
        o["verw_korrektur"] = 0.25
    return root


def _einfuegen(bm, tmp):
    me = bpy.data.meshes.new("tmp_ein")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def turm_bauen(name, C, col, M, opt, rnd):
    P = C["panzer_masse"]
    h = P["turm_dach_z"] - P["deck_z"]
    # 5.8 Qualitaetsrunde: Keilform statt Kasten - Front 42 Grad geneigt, Seiten 15 Grad, Heck 8 Grad
    # (vorher fast senkrechte Waende: unten 1.95/1.68, oben 1.80/1.55)
    unten = [(2.05, 0.0), (1.98, 0.70), (1.28, 1.52), (-0.6, 1.68), (-2.12, 1.50), (-2.42, 1.10), (-2.42, -1.10),
             (-2.12, -1.50), (-0.6, -1.68), (1.28, -1.52), (1.98, -0.70)]
    oben = [(1.30, 0.0), (1.25, 0.55), (0.82, 1.20), (-0.6, 1.45), (-2.00, 1.30), (-2.30, 0.98), (-2.30, -0.98),
            (-2.00, -1.30), (-0.6, -1.45), (0.82, -1.20), (1.25, -0.55)]
    nseite = math.atan2(1.68 - 1.45, h)  # Seitenneigung

    def ywand(z, x=-0.6):
        """y der Seitenwand in Hoehe z (bei x), fuer Anbauten, die an der schraegen Wand sitzen."""
        yu = 1.68 if x <= -0.6 else 1.68 - (x + 0.6) * (1.68 - 1.52) / 1.88
        yo = 1.45 if x <= -0.6 else 1.45 - (x + 0.6) * (1.45 - 1.20) / 1.42
        return yu + (yo - yu) * z / h
    tr = bpy.data.objects.new(f"{name}_Turm", None)
    col.objects.link(tr)
    bm = bmesh.new()
    schale = loft2(bm, unten, oben, 0.0, h, 0)
    # 2B: Turmschale unterteilen und verbeulen (Rand unten/oben bleibt, eigener Seed -> Bau-Zufall unveraendert)
    pd = MD.cfg()["turm_dellen"]
    MD.unterteilen(bm, schale[2:], pd["unterteilung"])
    sv = list(bm.verts)
    MD.dellen(bm, sv, MD.rnd(1 if name.endswith("_A") else 2), pd,
              fest=[v for v in sv if v.co.z < 0.03 or v.co.z > h - 0.03])
    # Turmring-Kragen unten
    ZY(bm, (0, 0, -0.06), (0, 0, 0.02), 1.15, 40, 0)
    # Staukaesten an den Seiten
    for s in (1, -1):
        Q(bm, (-1.15, s * (ywand(0.45) + 0.07), 0.45), (1.1, 0.16, 0.36), 0, Matrix.Rotation(s * nseite, 3, "X"))
        for x in (0.3, -0.9, -1.9):
            ZY(bm, (x, s * 1.22, h + 0.0), (x, s * 1.22, h + 0.07), 0.035, 8, 0)  # Haken
    # Zusatzpanzerung an den Turmseiten (Module mit Schraubenreihen), Schweissnaehte an der Turmkante
    for s in (1, -1):
        for k, (x0_, x1_) in enumerate(((1.30, 0.45), (0.40, -0.45))):
            xm = (x0_ + x1_) / 2
            rs = Matrix.Rotation(s * nseite, 3, "X")
            yy = s * (ywand(0.42, xm) + 0.05)
            Q(bm, (xm, yy, 0.42), (abs(x1_ - x0_) - 0.04, 0.07, 0.62), 0, rs)
            for i in range(5):
                for zz in (0.16, 0.68):
                    xb = x1_ + (x0_ - x1_) * (i + 0.5) / 5
                    c = Vector((xb, s * (ywand(zz, xm) + 0.05), zz))
                    ZY(bm, c + rs @ Vector((0, s * 0.035, 0)), c + rs @ Vector((0, s * 0.05, 0)), 0.018, 6, 0)
        # Keil-Zusatzpanzerung an den Turmwangen links/rechts der Kanone (schraeg nach hinten-aussen)
        wu = [(2.16, s * 0.58), (2.40, s * 0.66), (1.52, s * 1.70), (1.24, s * 1.56)]
        wo = [(1.62, s * 0.50), (1.84, s * 0.56), (1.10, s * 1.40), (0.86, s * 1.26)]
        if s < 0:
            wu, wo = wu[::-1], wo[::-1]
        loft2(bm, wu, wo, 0.05, 0.76, 0)
    for (xa_, ya_), (xb_, yb_) in zip(oben + oben[:1], oben[1:] + oben[:1]):
        ZY(bm, (xa_, ya_, h + 0.004), (xb_, yb_, h + 0.004), 0.012, 5, 0)
    for k in range(18):  # Schrauben am Dachrand
        t = k / 18
        i = int(t * len(oben))
        xa_, ya_ = oben[i]
        xb_, yb_ = oben[(i + 1) % len(oben)]
        u = t * len(oben) - i
        x_, y_ = xa_ + (xb_ - xa_) * u, ya_ + (yb_ - ya_) * u
        ZY(bm, (x_ * 0.95, y_ * 0.95, h), (x_ * 0.95, y_ * 0.95, h + 0.02), 0.02, 6, 0)
    body = OB(f"{name}_Turm_Koerper", bm, col, [M["tarn"], M["dunkel"]], tr)
    _fase(body, 0.03, 2, 30)
    # Luken-Ausschnitte (Bool) -> man sieht durch die offenen Luken ins dunkle Innere
    cut = bpy.data.objects.new(f"{name}_Lukenschnitt", None)
    bmc = bmesh.new()
    ZY(bmc, (-0.35, -0.62, h - 0.2), (-0.35, -0.62, h + 0.6), 0.30, 24, 0)
    Q(bmc, (-0.25, 0.62, h), (0.52, 0.46, 0.5), 0)
    mec = bpy.data.meshes.new(f"{name}_Lukenschnitt")
    bmc.to_mesh(mec)
    bmc.free()
    cut = bpy.data.objects.new(f"{name}_Lukenschnitt", mec)
    col.objects.link(cut)
    cut.parent = tr
    cut.hide_render = True
    cut.display_type = "WIRE"
    bo = body.modifiers.new("Luken", "BOOLEAN")
    bo.object = cut
    bo.operation = "DIFFERENCE"
    bo.solver = "EXACT"
    body.modifiers.move(len(body.modifiers) - 1, 0)
    # Blende + Rohr (Waermeschutzhuelle in Segmenten, Rauchabsauger, Muendung, Muendungsreferenz)
    bm = bmesh.new()
    prisma(bm, [(1.50, 0.12), (2.26, 0.24), (2.32, 0.42), (2.26, 0.60), (1.42, 0.78)], -0.46, 0.46, 0)  # Keilblende
    L = P["rohr_l"]
    x0 = 2.25
    ZY(bm, (x0, 0, 0.42), (x0 + L, 0, 0.42), 0.075, 20, 0)
    segm = [(x0 + 0.15, x0 + 1.75), (x0 + 1.82, x0 + 2.05)]
    ZY(bm, (x0 + 0.1, 0, 0.42), (x0 + 1.0, 0, 0.42), 0.10, 20, 0)
    ZY(bm, (x0 + 1.06, 0, 0.42), (x0 + 1.95, 0, 0.42), 0.10, 20, 0)
    ZY(bm, (x0 + 2.0, 0, 0.42), (x0 + 2.55, 0, 0.42), 0.135, 24, 0)  # Rauchabsauger
    ZY(bm, (x0 + 2.6, 0, 0.42), (x0 + 3.5, 0, 0.42), 0.10, 20, 0)
    ZY(bm, (x0 + 3.56, 0, 0.42), (x0 + 4.6, 0, 0.42), 0.10, 20, 0)
    ZY(bm, (x0 + L - 0.12, 0, 0.42), (x0 + L, 0, 0.42), 0.088, 20, 0)
    ZY(bm, (x0 + L - 0.02, 0, 0.42), (x0 + L + 0.001, 0, 0.42), 0.055, 16, 1)
    Q(bm, (x0 + L - 0.1, 0, 0.52), (0.12, 0.06, 0.05), 0)
    _ = segm
    rohr = OB(f"{name}_Rohr", bm, col, [M["tarn"], M["dunkel"]], tr, glatt=True)
    for v in rohr.data.vertices:
        v.co.x -= 1.95
        v.co.z -= 0.40
    rohr.location = (1.95, 0, 0.40)
    rohr.rotation_euler = (0, -math.radians(opt.get("rohr_grad", 0)), 0)
    _fase(rohr, 0.01, 2, 40)
    # Kommandantenkuppel, Winkelspiegel, Luken (offen), Optiken
    bm = bmesh.new()
    cx, cy = -0.35, -0.62
    ZY(bm, (cx, cy, h), (cx, cy, h + 0.22), 0.40, 28, 0)
    for k in range(7):
        a = 2 * math.pi * k / 7
        p = Vector((cx + 0.41 * math.cos(a), cy + 0.41 * math.sin(a), h + 0.16))
        Q(bm, p, (0.06, 0.13, 0.08), 0, Matrix.Rotation(a, 3, "Z"))
        Q(bm, p + Vector((0.032 * math.cos(a), 0.032 * math.sin(a), 0)), (0.004, 0.10, 0.05), 1, Matrix.Rotation(a, 3, "Z"))
    # Ladeschuetzenluke (Platte) und Kommandantenluke (Deckel) offen
    pl = Matrix.Rotation(math.radians(-100), 3, "Y")
    Q(bm, Vector((-0.25 - 0.26, 0.62, h + 0.03)) + pl @ Vector((0.26, 0, 0.0)), (0.52, 0.46, 0.04), 0, pl)
    dk = Matrix.Rotation(math.radians(-105), 3, "Y")
    c0 = Vector((cx - 0.32, cy, h + 0.24))
    tmp = bmesh.new()
    ZY(tmp, (0, 0, 0), (0, 0, 0.045), 0.33, 24, 0)
    for v in tmp.verts:
        v.co = c0 + dk @ (v.co + Vector((0.32, 0, 0)))
    _einfuegen(bm, tmp)
    # Richtschuetzen-Optik (Glas zerbrochen) + Kommandanten-Rundblickoptik
    Q(bm, (0.62, -0.72, h + 0.16), (0.46, 0.36, 0.32), 0)
    Q(bm, (0.86, -0.72, h + 0.20), (0.02, 0.26, 0.16), 2)
    ZY(bm, (0.15, -0.05, h), (0.15, -0.05, h + 0.32), 0.06, 12, 0)
    Q(bm, (0.15, -0.05, h + 0.45), (0.30, 0.26, 0.26), 0)
    Q(bm, (0.30, -0.05, h + 0.47), (0.02, 0.18, 0.12), 2)
    # Antennenfuesse (Antennen abgebrochen)
    for y, l in ((0.95, 0.38), (-0.95, 0.06)):
        ZY(bm, (-1.65, y, h), (-1.65, y, h + 0.12), 0.05, 12, 0)
        ZY(bm, (-1.65, y, h + 0.12), (-1.65, y, h + 0.12 + l), 0.008, 6, 3)
    # Nebelwurfbecher: 2 Gruppen x 6, schraeg nach vorne/aussen/oben
    for s in (1, -1):
        for k in range(6):
            r = Matrix.Rotation(math.radians(55), 3, "Y") @ Matrix.Rotation(math.radians(s * (20 + k * 9)), 3, "X")
            xk, zk = 0.55 - (k % 3) * 0.14, 0.56 + (k // 3) * 0.11
            p = Vector((xk, s * (ywand(zk, xk) + 0.04), zk))
            ZY(bm, p, p + r @ Vector((0, 0, 0.24)), 0.042, 10, 0)
            ZY(bm, p + r @ Vector((0, 0, 0.235)), p + r @ Vector((0, 0, 0.245)), 0.032, 10, 1)
    OB(f"{name}_Turm_Aufbauten", bm, col, [M["tarn"], M["dunkel"], M["glas"], M["rost"]], tr, glatt=False)
    # Staukorb rund um das Turmheck (Gitter + Rahmen) mit verrotteter Ladung
    bm = bmesh.new()
    xa, xb, yk, za, zb = -1.0, -2.80, 1.66, 0.30, 0.85
    rahmen = [(xa, yk), (xb + 0.25, yk), (xb, yk - 0.25), (xb, -yk + 0.25), (xb + 0.25, -yk), (xa, -yk)]
    for z in (za, zb):
        pts = [Vector((x, y, z)) for x, y in rahmen]
        for a, b in zip(pts, pts[1:]):
            ZY(bm, a, b, 0.014, 6, 0)
    for x, y in rahmen:
        ZY(bm, (x, y, za), (x, y, zb), 0.014, 6, 0)
    korb = OB(f"{name}_Staukorb", bm, col, [M["rost"]], tr, glatt=True)
    bm = bmesh.new()
    for (x0_, y0_), (x1_, y1_) in zip(rahmen, rahmen[1:]):
        v = [bm.verts.new((x0_, y0_, za)), bm.verts.new((x1_, y1_, za)), bm.verts.new((x1_, y1_, zb)), bm.verts.new((x0_, y0_, zb))]
        bm.faces.new(v)
    netz = OB(f"{name}_Staukorb_Gitter", bm, col, [M["draht"]], tr)
    bm = bmesh.new()
    for k in range(5):
        x = -1.25 - k * 0.32 + rnd.uniform(-0.05, 0.05)
        y = rnd.uniform(-1.2, 1.2)
        FT.polster(bm, (x, y, za + 0.17), (0.38, 0.55, 0.30), Matrix.Rotation(rnd.uniform(-0.4, 0.4), 3, "Z"), "z",
                   0.0, -0.03, k % 2)
    ZY(bm, (-2.55, -1.3, za + 0.2), (-2.55, 1.2, za + 0.22), 0.17, 16, 1)
    lad = OB(f"{name}_Staukorb_Ladung", bm, col, [M["sack"], M["plane"]], tr)
    m = lad.modifiers.new("Rund", "SUBSURF")
    m.levels = m.render_levels = 1
    # Kanister + Busch (Fotoscan-Modelle)
    for k, (x, y) in enumerate(((-2.45, -0.9), (-2.45, -0.55))):
        for o in _kopie("metal_jerrycan", col, (x, y, za + 0.02), 0.3 * k):
            o.parent = tr
    if opt.get("busch_staukorb"):
        for o in _kopie("shrub_02", col, (-1.9, 0.6, za + 0.28), 0.8, 0.42):
            o.parent = tr
    # Schablonen-Nummer (erfunden), verblasst
    bm = bmesh.new()
    for s in (1, -1):
        n = Vector((0.0, s, math.tan(nseite))).normalized()
        up = Vector((0, 0, 1))
        lese = up.cross(n).normalized()
        mx = Matrix((lese, up, n)).transposed().to_4x4()
        mx.translation = Vector((-0.02, s * (ywand(0.42, -0.025) + 0.089), 0.42))  # auf dem hinteren Zusatzmodul
        V.text_mesh(bm, opt.get("nummer", "K-00"), 0.22, mx, 0, extrude=0.001, aufloesung=3)
    OB(f"{name}_Nummer", bm, col, [M["schrift"]], tr)
    _ = (korb, netz)
    return tr


def _kopie(asset, col, pos, rot_z=0.0, skal=1.0):
    import flotte as FL
    out = FL.kopie(asset, col, pos, rot_z, skal)
    return out


def pfuetze(root, col, boden, radius=2.2):
    """Unregelmaessige Pfuetze unter der Wanne."""
    bm = bmesh.new()
    mw = root.matrix_world
    n = 28
    rnd = random.Random(7)
    c = mw @ Vector((-0.5, 0.2, 0))
    ring = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = radius * (0.75 + 0.35 * rnd.random())
        x, y = c.x + r * 1.5 * math.cos(a), c.y + r * 0.8 * math.sin(a)
        ring.append(bm.verts.new((x, y, boden.z(x, y) + 0.006)))
    bm.faces.new(ring)
    ob = OB(f"{root.name}_Pfuetze", bm, col, [V.mat_wasser()])
    return ob


def setzen(root, boden, opt, schief_seite=None):
    """Auf den Boden stellen: Ebene durch die 4 Laufwerks-Ecken, ohne Kette 8 cm tiefer auf einer Seite."""
    x, y = opt["pos"]
    yaw = math.radians(opt["richtung"])
    rz = Matrix.Rotation(yaw, 3, "Z")
    pts = []
    for lx in (2.9, -2.9):
        for s, sn in ((1, "l"), (-1, "r")):
            w = rz @ Vector((lx, s * 1.43, 0)) + Vector((x, y, 0))
            pts.append((lx, s * 1.43, boden.z(w.x, w.y) - (0.08 if opt.get("kette_ab") == sn else 0.0)))
    sx = sum(p[0] for p in pts) / 4
    sy = sum(p[1] for p in pts) / 4
    sz = sum(p[2] for p in pts) / 4
    b = sum((p[0] - sx) * (p[2] - sz) for p in pts) / sum((p[0] - sx) ** 2 for p in pts)
    c = sum((p[1] - sy) * (p[2] - sz) for p in pts) / sum((p[1] - sy) ** 2 for p in pts)
    root.location = (x, y, sz - b * sx - c * sy)
    root.rotation_euler = Euler((math.asin(c), -math.asin(b) - math.radians(opt.get("nick_grad", 0)), yaw), "XYZ")
