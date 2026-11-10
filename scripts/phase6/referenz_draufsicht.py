"""Phase 6.1 – Referenzbild Draufsicht des Testbereichs (mit TEST_Achsen), zum Vergleich mit Unreal (Draufsicht 'Top').

Aufruf:  blender -b viertel_v10.blend --python scripts/phase6/referenz_draufsicht.py
Ausgabe: renders/test/phase6_referenz_draufsicht.png (Norden = oben im Bild, wie in Blender)
"""
import math
import os
import sys

import bpy

HIER = os.path.dirname(os.path.abspath(__file__))
sys.argv = [a for a in sys.argv]  # export_unreal liest dieselben Argumente (--mitte/--radius)
sys.path.insert(0, HIER)
import export_unreal as EX  # noqa: E402

sc = bpy.context.scene
ob = EX.testobjekt(sc.collection)
m = bpy.data.materials.new("TEST_Rot")
m.diffuse_color = (1, 0, 0, 1)
m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 0.02, 0.02, 1)
m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1, 0, 0, 1)
m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 3.0
ob.data.materials.append(m)
cd = bpy.data.cameras.new("REF_Draufsicht")
cd.type, cd.ortho_scale, cd.clip_end = "ORTHO", EX.RADIUS * 2.2, 1000
cam = bpy.data.objects.new("REF_Draufsicht", cd)
sc.collection.objects.link(cam)
cam.location = (EX.MITTE[0], EX.MITTE[1], 200)
cam.rotation_euler = (0, 0, 0)
for mk in list(sc.timeline_markers):  # Marker binden sonst CAM_Hero_01 an Bild 1
    sc.timeline_markers.remove(mk)
sc.camera = cam
for o in bpy.data.objects:
    if o.name.startswith(("FX_Dunst", "FX_Rauch")):
        o.hide_render = True
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 16
sc.cycles.use_denoising = True
sc.cycles.texture_limit_render = "512"
sc.cycles.use_camera_cull = True
for o in bpy.data.objects:
    o.cycles.use_camera_cull = True
sc.render.resolution_x = sc.render.resolution_y = 800
sc.render.resolution_percentage = 100
sc.render.use_compositing = False
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = os.path.join(EX.ROOT, "renders", "test", "phase6_referenz_draufsicht.png")
bpy.ops.render.render(write_still=True)
print("REFERENZ", sc.render.filepath, "Testobjekt bei", [round(v, 2) for v in ob.location], "Drehung 30 Grad", flush=True)
_ = math
