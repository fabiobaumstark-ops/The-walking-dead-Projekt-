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
    # Name: (Gebaeude, Raumart, n-tes Vorkommen, Brennweite) - Kamera in der hinteren Ecke, Blick diagonal durch den Raum
    "B11_wohnen": ("B11", "wohnen", 1, 16),
    "B11_kueche": ("B11", "kueche", 1, 16),
    "B11_schlafen": ("B11", "schlafen", 2, 16),
    "B11_bad": ("B11", "bad", 1, 14),
    "B05_laden": ("B05", "laden", 0, 16),
    "B05_wohnen": ("B05", "wohnen", 0, 16),
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
    # Innen: kein Aussendunst/Rauch im Raum (Volumen-Wuerfel fuellt sonst die Zimmer), kein Aussen-Grading
    for o in bpy.data.objects:
        if o.name.startswith(("FX_Dunst", "FX_Rauch")):
            o.hide_render = True
    sc.render.use_compositing = "--grading" in args
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, 50
    sc.render.image_settings.media_type, sc.render.image_settings.file_format = "IMAGE", "PNG"
    sc.view_settings.exposure = float(args[args.index("--belichtung") + 1]) if "--belichtung" in args else 4.5  # Innenraum: ca. 5 Blenden dunkler als draussen
    zeiten = {}
    import json
    for name, (gid, art, k, f) in ANSICHTEN.items():
        if NUR and name not in NUR:
            continue
        ob = next(o for o in bpy.data.objects if o.name.startswith("BLD_") and o.get("id") == gid and not o.name.endswith("_Decals"))
        raeume = [rm for rm in json.loads(ob.get("raeume_json", "[]")) if rm["art"] == art]
        if len(raeume) <= k:
            print("INNEN fehlt", name, flush=True)
            continue
        rm = raeume[k]
        zf = rm["z"]
        u0, v0, u1, v1 = rm["rect"]
        r = P1.Rahmen(geb[gid]["rechteck"], geb[gid]["front"])
        p = Vector((*r.p(u1 - 0.35, v1 - 0.35), zf + 1.6))  # hintere Ecke (zur Aussenwand)
        z = Vector((*r.p(u0 + 0.3, v0 + 0.3), zf + 1.1))
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
