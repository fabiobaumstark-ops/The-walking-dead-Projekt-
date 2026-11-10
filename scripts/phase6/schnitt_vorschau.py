"""Phase 6.4 – Grundriss-Schnitte einzelner Gebaeude (Pruefung Treppenhaus/Tueren), je Geschoss eine Draufsicht.

Aufruf:  blender -b viertel_v11.blend --python scripts/phase6/schnitt_vorschau.py -- --nur B09,B05 [--prefix phase6_innen]
Das Gebaeude wird als Kopie in eine leere Szene gelegt und oberhalb von Geschoss + 1,4 m abgeschnitten.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HIER, "..", ".."))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NUR = args[args.index("--nur") + 1].split(",")
PREFIX = args[args.index("--prefix") + 1] if "--prefix" in args else "phase6_innen"
GROESSE = 420


def gebaeude(gid):
    return next(o for o in bpy.data.objects if o.name.startswith("BLD_") and o.get("id") == gid and not o.name.endswith("_Decals"))


def ebenen(ob):
    zs = sorted({round(v.co.z, 2) for v in ob.data.vertices})
    return zs


def schnitt(ob, z_lokal, sc):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z_lokal), plane_no=(0, 0, 1), clear_outer=True)
    me = bpy.data.meshes.new("SCHNITT")
    bm.to_mesh(me)
    bm.free()
    for m in ob.data.materials:
        me.materials.append(m)
    k = bpy.data.objects.new("SCHNITT", me)
    k.matrix_world = ob.matrix_world.copy()
    sc.collection.objects.link(k)
    return k


def main():
    src = bpy.context.scene
    sc = bpy.data.scenes.new("Schnitt")
    sc.render.engine = "CYCLES"
    sc.cycles.device, sc.cycles.samples, sc.cycles.use_denoising = "CPU", 24, True
    sc.render.resolution_x = sc.render.resolution_y = GROESSE
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    w = bpy.data.worlds.new("Schnitt_Welt")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
    sc.world = w
    sd = bpy.data.lights.new("Schnitt_Sonne", "SUN")
    sd.energy, sd.angle = 3.0, math.radians(8)
    so = bpy.data.objects.new("Schnitt_Sonne", sd)
    so.rotation_euler = (math.radians(20), math.radians(10), 0)
    sc.collection.objects.link(so)
    cd = bpy.data.cameras.new("Schnitt_Cam")
    cd.type = "ORTHO"
    cam = bpy.data.objects.new("Schnitt_Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    bilder = []
    for gid in NUR:
        ob = gebaeude(gid)
        pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        mx = sum((p for p in pts), Vector()) / 8
        cd.ortho_scale = max(max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts)) * 1.08
        cam.location = (mx.x, mx.y, max(p.z for p in pts) + 50)
        cam.rotation_euler = (0, 0, 0)
        cd.clip_end = 500
        geb = list(ob.get("geschosse_z", [])) or None
        zs_welt = sorted({round((ob.matrix_world @ v.co).z, 2) for v in ob.data.vertices})
        # Geschosse: Oberkanten der Deckenplatten = haeufige z-Werte mit grossen horizontalen Flaechen
        flaechen = {}
        for f in ob.data.polygons:
            if f.normal.z > 0.99 and f.area > 2.0:
                z = round((ob.matrix_world @ f.center).z, 2)
                flaechen[z] = flaechen.get(z, 0) + f.area
        stufen = sorted(z for z, a in flaechen.items() if a > 15)
        geschosse = []
        for z in stufen:
            if not geschosse or z - geschosse[-1] > 2.0:
                geschosse.append(z)
        for k, zf in enumerate(geschosse):
            kopie = schnitt(ob, zf + 1.4 - ob.matrix_world.translation.z, sc)
            sc.render.filepath = os.path.join(ROOT, "renders", "test", f"_tmp_{gid}_{k}.png")
            bpy.ops.render.render(write_still=True, scene=sc.name)
            bilder.append((gid, k, sc.render.filepath))
            bpy.data.objects.remove(kopie)
        _ = (geb, zs_welt)
    print("SCHNITTE", [(g, k) for g, k, _ in bilder], flush=True)
    # Kontaktbogen (ohne PIL): Bilder in ein grosses Blender-Bild kopieren
    import numpy as np
    zeilen = {}
    for gid, k, p in bilder:
        zeilen.setdefault(gid, []).append(p)
    spalten = max(len(v) for v in zeilen.values())
    H, Wd = GROESSE * len(zeilen), GROESSE * spalten
    gesamt = np.ones((H, Wd, 4), dtype=np.float32)
    for r, (gid, ps) in enumerate(zeilen.items()):
        for c, p in enumerate(ps):
            im = bpy.data.images.load(p)
            px = np.array(im.pixels[:], dtype=np.float32).reshape(GROESSE, GROESSE, 4)
            y0 = H - (r + 1) * GROESSE
            gesamt[y0:y0 + GROESSE, c * GROESSE:(c + 1) * GROESSE] = px
            bpy.data.images.remove(im)
            os.remove(p)
    out = bpy.data.images.new("Bogen", Wd, H)
    out.pixels.foreach_set(gesamt.ravel())
    out.filepath_raw = os.path.join(ROOT, "renders", "test", f"{PREFIX}_{'_'.join(NUR)}.png")
    out.file_format = "PNG"
    out.save()
    print("BOGEN", out.filepath_raw, flush=True)
    _ = src


main()
