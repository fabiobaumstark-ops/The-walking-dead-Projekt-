"""Phase 5 – Vorschau der Hero-Shots mit den finalen Einstellungen (Licht, Dunst, Compositor), nur kleiner/weniger Samples.

Aufruf:  blender -b viertel_v09.blend --python scripts/phase5/render_vorschau.py -- --prefix phase5 [--samples 128] [--prozent 50] [--nur 1,3] [--cpu] [--sparsam]
--sparsam (Cloud, 16 GB RAM): Texturen max. 1024 px, Objekte ausserhalb des Kamerabilds weglassen (nicht Gebaeude/Gelaende), Compositor auf der CPU.
Nur fuer Vorschauen - die .blend wird nicht veraendert.
"""
import os
import sys
import time

import bpy

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
praefix = args[args.index("--prefix") + 1] if "--prefix" in args else "phase5"
samples = int(args[args.index("--samples") + 1]) if "--samples" in args else 128
prozent = int(args[args.index("--prozent") + 1]) if "--prozent" in args else 50
nur = [int(x) for x in args[args.index("--nur") + 1].split(",")] if "--nur" in args else [1, 2, 3, 4]

sc = bpy.context.scene
if "--cpu" in args:  # Metal kompiliert die Szenen-Kernel bei jedem Start neu -> fuer kleine Vorschauen ist die CPU schneller
    sc.cycles.device = "CPU"
else:
    p = bpy.context.preferences.addons["cycles"].preferences
    p.compute_device_type = "METAL"
    p.get_devices()
    for d in p.devices:
        d.use = True
if "--sparsam" in args:
    sc.cycles.texture_limit_render = "1024"
    sc.cycles.use_camera_cull, sc.cycles.camera_cull_margin = True, 0.25
    for o in bpy.data.objects:
        if not o.name.startswith(("BLD_", "GEO_", "FX_", "LGT_", "BOD_", "STR_")):
            o.cycles.use_camera_cull = True
    sc.render.compositor_device = "CPU"
    sc.render.use_persistent_data = False
sc.cycles.samples = samples
sc.cycles.adaptive_threshold = 0.03
sc.render.resolution_percentage = prozent
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "8"
ziel = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "renders", "test")
zeiten = {}
for i in nur:
    sc.frame_set(i)
    sc.camera = bpy.data.objects[f"CAM_Hero_{i:02d}"]
    sc.render.filepath = os.path.abspath(os.path.join(ziel, f"{praefix}_cam{i}.png"))
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    zeiten[i] = round(time.time() - t0, 1)
print("RENDERZEITEN", zeiten, flush=True)
