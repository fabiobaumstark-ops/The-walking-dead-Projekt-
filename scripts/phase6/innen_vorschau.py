"""Phase 6.4 Teil 2 – Vorschau-Renders von Innenraeumen (Kamera auf Augenhoehe, nur Tageslicht durch die Fenster).

Aufruf:  blender -b viertel_v12.blend --python scripts/phase6/innen_vorschau.py -- --ansichten B11_wohnen,B05_laden [--samples 64]
Ansichten in ANSICHTEN: Gebaeude-ID, Geschoss-Index, Kamera (u, v) und Ziel (u, v) im lokalen System des Gebaeudes
(u entlang der Strassenfront, v in die Tiefe), Brennweite. Speicher-sparend wie render_vorschau --sparsam.
"""
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, os.path.join(HIER, "..", "phase1"))
import viertel_lib as V  # noqa: E402
import blockout_gebaeude as P1  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NUR = args[args.index("--ansichten") + 1].split(",") if "--ansichten" in args else None
SAMPLES = int(args[args.index("--samples") + 1]) if "--samples" in args else 64
PREFIX = args[args.index("--prefix") + 1] if "--prefix" in args else "phase64_innen"

ANSICHTEN = {
    # Name: (Gebaeude, Geschoss-Index, Kamera (u, v), Ziel (u, v), Brennweite)
    "B11_wohnen": ("B11", 1, (9.9, 4.9), (4.0, 0.6), 18),
    "B11_kueche": ("B11", 1, (9.9, 7.9), (4.0, 5.9), 18),
    "B11_schlafen": ("B11", 2, (9.8, 15.0), (4.5, 11.5), 18),
    "B11_flur": ("B11", 1, (1.6, 1.0), (1.6, 12.0), 18),
    "B05_laden": ("B05", 0, (5.2, 1.2), (1.5, 12.0), 18),
    "B05_wohnen": ("B05", 1, (5.3, 4.8), (3.2, 0.5), 16),
}


def main():
    sc = bpy.context.scene
    cfg = V.config("gebaeude.json")
    geb = {g["id"]: g for g in cfg["gebaeude"]}
    for mk in list(sc.timeline_markers):
        sc.timeline_markers.remove(mk)
    cd = bpy.data.cameras.new("CAM_Innen")
    cd.sensor_width, cd.clip_start = 36, 0.05
    cam = bpy.data.objects.new("CAM_Innen", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.cycles.device = "CPU"
    sc.cycles.samples, sc.cycles.adaptive_threshold = SAMPLES, 0.03
    sc.cycles.texture_limit_render = "1024"
    sc.cycles.use_camera_cull, sc.cycles.camera_cull_margin = True, 0.3
    for o in bpy.data.objects:
        if not o.name.startswith(("BLD_", "GEO_", "FX_", "LGT_", "BOD_", "STR_", "TUER_", "MOB_")):
            o.cycles.use_camera_cull = True
    sc.render.compositor_device = "CPU"
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, 50
    sc.render.image_settings.media_type, sc.render.image_settings.file_format = "IMAGE", "PNG"
    sc.view_settings.exposure = 1.3  # Innenraum: wie ein Fotograf laenger belichten
    zeiten = {}
    for name, (gid, k, (cu, cv), (zu, zv), f) in ANSICHTEN.items():
        if NUR and name not in NUR:
            continue
        ob = next(o for o in bpy.data.objects if o.name.startswith("BLD_") and o.get("id") == gid and not o.name.endswith("_Decals"))
        ebenen = list(ob.get("ebenen_z", []))
        zf = ebenen[k]
        r = P1.Rahmen(geb[gid]["rechteck"], geb[gid]["front"])
        p = Vector((*r.p(cu, cv), zf + 1.6))
        z = Vector((*r.p(zu, zv), zf + 1.2))
        cam.location = p
        cam.rotation_euler = (z - p).to_track_quat("-Z", "Y").to_euler()
        cd.lens = f
        cd.dof.use_dof = False
        sc.render.filepath = os.path.join(V.ROOT, "renders", "test", f"{PREFIX}_{name}.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        zeiten[name] = round(time.time() - t0, 1)
        print("INNEN", name, zeiten[name], "s", flush=True)
    print("ZEITEN", zeiten, flush=True)
    _ = math


main()
