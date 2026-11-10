"""Phase 6.4 – Begehbarkeits-Test: Kommt eine Spielfigur von der Strasse in jedes Geschoss und aufs Dach?

Aufruf:  blender -b viertel_v11.blend --python scripts/phase6/begehbar.py -- [--nur B05,B09] [--raster 0.2]
Figur wie der Unreal-Standard-Charakter (Annahme): Hoehe 1,76 m, Radius 0,30 m (Test etwas schmaler als 0,34 m,
weil das Raster die Tuermitte nicht genau trifft), Stufenhoehe 0,45 m. Optional Sprung: bis 0,9 m nach oben.
Verfahren: Raster ueber Grundriss + 3 m Rand; je Rasterpunkt alle begehbaren Flaechen (Strahl nach unten, Normale
nach oben, genug Kopfhoehe, Abstand zu Waenden); Nachbarn verbunden, wenn Hoehenunterschied klein und kein
Hindernis dazwischen. Breitensuche ab der Strasse vor dem Gebaeude.
"""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
import viertel_lib as V  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NUR = args[args.index("--nur") + 1].split(",") if "--nur" in args else None
R = float(args[args.index("--raster") + 1]) if "--raster" in args else 0.2
HOEHE, RADIUS, STUFE, SPRUNG = 1.76, 0.30, 0.45, 0.9
RAND = 6.0  # Veranden, Treppen und Vordaecher ragen bis ca. 4 m vor


def bvh_fuer(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    mw = ob.matrix_world
    vs = [mw @ v.co for v in me.vertices]
    fs = [tuple(p.vertices) for p in me.polygons]
    oe.to_mesh_clear()
    return BVHTree.FromPolygons(vs, fs, epsilon=0.0)


def flaechen(bvh, x, y, ztop, zmin):
    """Alle nach oben zeigenden Flaechen unter (x, y), von oben nach unten."""
    out, z = [], ztop
    while z > zmin:
        loc, n, _, _ = bvh.ray_cast(Vector((x, y, z)), Vector((0, 0, -1)), z - zmin)
        if loc is None:
            break
        if n.z > 0.7:
            out.append(loc.z)
        z = loc.z - 0.02
    return out


def frei(bvh, p, z):
    """Kopfhoehe und Abstand zu Waenden an der Stelle (Stehen moeglich?)."""
    loc, _, _, _ = bvh.ray_cast(Vector((p[0], p[1], z + 0.05)), Vector((0, 0, 1)), HOEHE)
    if loc is not None:
        return False
    for k in range(8):
        a = k * math.pi / 4
        d = Vector((math.cos(a), math.sin(a), 0))
        for hz in (STUFE + 0.05, 1.0, HOEHE - 0.1):
            if bvh.ray_cast(Vector((p[0], p[1], z + hz)), d, RADIUS)[0] is not None:
                return False
    return True


def durchgang(bvh, a, b, za, zb):
    d = Vector((b[0] - a[0], b[1] - a[1], 0))
    L = d.length
    d.normalize()
    z = max(za, zb)
    for hz in (STUFE + 0.05, 1.0, HOEHE - 0.1):
        if bvh.ray_cast(Vector((a[0], a[1], z + hz)), d, L)[0] is not None:
            return False
    return True


def pruefen(ob, g):
    t0 = time.time()
    bvh = bvh_fuer(ob)
    rahmen_x0, rahmen_y0, rahmen_x1, rahmen_y1 = g["rechteck"]
    # Raster leicht versetzt: Punkte genau auf Kanten (Stufenkante = Lochkante) lassen Strahlen durchrutschen
    x0, y0, x1, y1 = rahmen_x0 - RAND + 0.0137, rahmen_y0 - RAND + 0.0113, rahmen_x1 + RAND, rahmen_y1 + RAND
    ztop = ob.matrix_world.translation.z + max(v.co.z for v in ob.data.vertices) + 1.0
    zmin = ob.matrix_world.translation.z - 3.0
    nx, ny = int((x1 - x0) / R) + 1, int((y1 - y0) / R) + 1
    knoten = {}  # (i, j) -> [z, ...]
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + i * R, y0 + j * R
            innen = rahmen_x0 < x < rahmen_x1 and rahmen_y0 < y < rahmen_y1
            zs = flaechen(bvh, x, y, ztop, zmin)
            if not innen:
                zs.append(V.h(x, y))  # Gelaende ausserhalb (nicht im Gebaeude-Mesh)
            zs = [z for z in zs if frei(bvh, (x, y), z)]
            if zs:
                knoten[(i, j)] = zs
    # Start: jeder Gelaendepunkt rund ums Gebaeude (die Figur kann ums Haus laufen)
    starts = []
    for (i, j), zs in knoten.items():
        x, y = x0 + i * R, y0 + j * R
        if rahmen_x0 < x < rahmen_x1 and rahmen_y0 < y < rahmen_y1:
            continue
        hz = V.h(x, y)
        for z in zs:
            if abs(z - hz) < 0.3:
                starts.append(((i, j), z))
    start = starts[0] if starts else None
    ergebnis = {}
    for modus, hoch in (("laufen", STUFE), ("springen", SPRUNG)):
        if start is None:
            ergebnis[modus] = None
            continue
        gesehen = set(starts)
        stapel = list(starts)
        while stapel:
            (i, j), z = stapel.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                k = (i + di, j + dj)
                for z2 in knoten.get(k, ()):
                    if (k, z2) in gesehen:
                        continue
                    dz = z2 - z
                    if dz > hoch or dz < -2.5:
                        continue
                    a = (x0 + i * R, y0 + j * R)
                    b = (x0 + k[0] * R, y0 + k[1] * R)
                    if not durchgang(bvh, a, b, z, z2):
                        continue
                    gesehen.add((k, z2))
                    stapel.append((k, z2))
        innen = [z for (k, z) in gesehen
                 if rahmen_x0 < x0 + k[0] * R < rahmen_x1 and rahmen_y0 < y0 + k[1] * R < rahmen_y1]
        ergebnis[modus] = innen
        if "--punkte" in args and modus == "laufen":
            for pt in args[args.index("--punkte") + 1].split(";"):
                px, py = (float(c) for c in pt.split(","))
                k = (round((px - x0) / R), round((py - y0) / R))
                print("PKT", pt, "knoten", [round(z, 2) for z in knoten.get(k, [])],
                      "erreicht", [round(z, 2) for (kk, z) in gesehen if kk == k], flush=True)
        if "--karte" in args and modus == "laufen":
            zk = float(args[args.index("--karte") + 1])
            erreicht_k = {k for (k, z) in gesehen if abs(z - zk) < 0.3}
            da = {k for k, zs in knoten.items() if any(abs(z - zk) < 0.3 for z in zs)}
            for j in range(ny - 1, -1, -2):
                print("K " + "".join("o" if (i, j) in erreicht_k else ("." if (i, j) in da else " ") for i in range(0, nx, 1)), flush=True)
        if "--debug" in args and innen:
            top = sorted(((z, k) for (k, z) in gesehen), reverse=True)[:3]
            print("DBG hoechste", [(round(z, 2), round(x0 + k[0] * R, 2), round(y0 + k[1] * R, 2)) for z, k in top], flush=True)
        if "--debug" in args:
            print("DBG", g["id"], modus, "start", start, "gesehen", len(gesehen), "innen", len(innen),
                  "z_innen", sorted({round(z, 1) for z in innen})[:12], flush=True)
    return ergebnis, round(time.time() - t0, 1), len(knoten)


def geschosse_von(ob):
    """Geschoss-Oberkanten aus grossen, nach oben zeigenden Flaechen (wie schnitt_vorschau.py)."""
    fl = {}
    for f in ob.data.polygons:
        if f.normal.z > 0.99 and f.area > 2.0:
            z = round((ob.matrix_world @ f.center).z, 2)
            fl[z] = fl.get(z, 0) + f.area
    out = []
    for z in sorted(z for z, a in fl.items() if a > 15):
        if not out or z - out[-1] > 2.0:
            out.append(z)
    return out


def main():
    cfg = V.config("gebaeude.json")
    geb = {g["id"]: g for g in cfg["gebaeude"]}
    zeilen = []
    for ob in sorted((o for o in bpy.data.objects if o.name.startswith("BLD_") and o.get("id") and not o.name.endswith("_Decals")),
                     key=lambda o: o["id"]):
        gid = ob["id"]
        if NUR and gid not in NUR or gid not in geb:
            continue
        res, dt, nk = pruefen(ob, geb[gid])
        ebenen = list(ob.get("ebenen_z", [])) or geschosse_von(ob)

        def erreicht(liste):
            if liste is None:
                return []
            return [e for e in ebenen if any(abs(z - e) < 0.15 for z in liste)]
        lauf, sprung = erreicht(res["laufen"]), erreicht(res["springen"])
        if "--debug" in args:
            print("DBG ebenen", gid, ebenen, flush=True)
        zeilen.append({"id": gid, "name": ob.name, "ebenen": len(ebenen), "laufen": len(lauf), "springen": len(sprung),
                       "dach": bool(ebenen) and abs(lauf[-1] - ebenen[-1]) < 0.15 if lauf else False, "zeit_s": dt})
        print("BEGEHBAR", json.dumps(zeilen[-1]), flush=True)
    voll = sum(1 for z in zeilen if z["ebenen"] and z["laufen"] == z["ebenen"])
    print("ZUSAMMEN", voll, "von", len(zeilen), "Gebaeuden in allen Ebenen begehbar", flush=True)
    with open(os.path.join(V.ROOT, "renders", "test", "phase6_begehbar.json"), "w") as f:
        json.dump(zeilen, f, indent=1)


main()
