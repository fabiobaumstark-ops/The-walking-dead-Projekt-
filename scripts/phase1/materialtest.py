"""Phase 1.2 – Testreihe Material-Bibliothek + MAT_Verwitterung.

Wuerfel, Zylinder, Kugel, Wandstueck mit Fenster + 3 Poly-Haven-Modelle,
jeweils mit Verwitterung 0 %, 50 %, 100 %.

Aufruf:  blender -b --factory-startup --python scripts/phase1/materialtest.py
Ergebnis: renders/test/phase1_materialtest.png (+ teile/materialtest.blend, nicht im Repo)
"""
import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import viertel_lib as V  # noqa: E402

sc = V.leere_szene()
V.alle_collections()
V.regler_setzen(sc)
sc["verw_master"] = 1.0           # Testreihe: 100 % = volle Verwitterung
sc["verw_boden_gx"] = 0.0         # Testboden ist eben
sc["verw_boden_gy"] = 0.0
sc["verw_boden_z0"] = 0.0
lib = V.bibliothek()
col = V.collection("99_Blockout_Archiv/Materialtest")


def bevel_bm(bm, w=0.02, seg=3):
    edges = [e for e in bm.edges if e.calc_face_angle(0) > math.radians(30)]
    bmesh.ops.bevel(bm, geom=edges, offset=w, segments=seg, profile=0.5, affect="EDGES", clamp_overlap=True)


def wuerfel():
    bm = bmesh.new()
    V.box(bm, -0.5, -0.5, 0, 0.5, 0.5, 1.0)
    bevel_bm(bm)
    return V.objekt_aus_bmesh("PRP_Test_Wuerfel", bm, col, material=lib["MAT_Holz_Verkleidung"])


def zylinder():
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=0.45, radius2=0.45, depth=1.2)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.6))
    bevel_bm(bm, 0.015, 2)
    ob = V.objekt_aus_bmesh("PRP_Test_Zylinder", bm, col, material=lib["MAT_Metall_Lackiert"])
    for p in ob.data.polygons:
        p.use_smooth = abs(p.normal.z) < 0.5
    return ob


def kugel():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=0.55)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.55))
    ob = V.objekt_aus_bmesh("PRP_Test_Kugel", bm, col, material=lib["MAT_Beton_Glatt"])
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def wand():
    """Wand 2,4 x 2,6 x 0,3 m, Fenster 0,9 x 1,5 m (Bruestung 0,9 m), Rahmen 7 cm, 15 cm zurueckgesetzt, Fensterbank."""
    bm = bmesh.new()
    W, H, D = 2.4, 2.6, 0.3
    fx0, fx1, fz0, fz1 = -0.45, 0.45, 0.9, 2.4
    for (x0, x1, z0, z1) in [(-W / 2, fx0, 0, H), (fx1, W / 2, 0, H), (fx0, fx1, 0, fz0), (fx0, fx1, fz1, H)]:
        V.box(bm, x0, 0, z0, x1, D, z1)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bevel_bm(bm, 0.015, 2)
    w = V.objekt_aus_bmesh("BLD_Test_Wand", bm, col, material=lib["MAT_Ziegel_Rot"])
    # Rahmen (Holz) 15 cm zurueckgesetzt, 7 cm breit, Sprosse mittig
    bm = bmesh.new()
    r, t, y0 = 0.07, 0.06, 0.15
    for (x0, x1, z0, z1) in [(fx0, fx0 + r, fz0, fz1), (fx1 - r, fx1, fz0, fz1), (fx0, fx1, fz0, fz0 + r),
                             (fx0, fx1, fz1 - r, fz1), (fx0, fx1, (fz0 + fz1) / 2 - 0.03, (fz0 + fz1) / 2 + 0.03)]:
        V.box(bm, x0, y0, z0, x1, y0 + t, z1)
    bevel_bm(bm, 0.006, 2)
    V.objekt_aus_bmesh("BLD_Test_Fensterrahmen", bm, col, material=lib["MAT_Holz_Planken"]).parent = w
    # Fensterbank: 5 cm Ueberstand, Tropfkante
    bm = bmesh.new()
    V.box(bm, fx0 - 0.04, -0.05, fz0 - 0.05, fx1 + 0.04, y0 + 0.02, fz0)
    bevel_bm(bm, 0.008, 2)
    V.objekt_aus_bmesh("BLD_Test_Fensterbank", bm, col, material=lib["MAT_Beton_Glatt"]).parent = w
    # dunkler Innenraum dahinter (Rueckwand)
    # Raum hinter dem Fenster: vorne offen, damit nur durchs Fenster Licht hineinfaellt
    bm = bmesh.new()
    fs = V.box(bm, -0.9, 0.3, 0.02, 0.9, 1.4, H - 0.2)
    bmesh.ops.delete(bm, geom=[fs[2]], context="FACES")
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    V.objekt_aus_bmesh("BLD_Test_Innenraum", bm, col, material=lib["MAT_Putz"]).parent = w
    return w


def kinder(ob):
    return [ob] + [c for c in bpy.data.objects if c.parent == ob]


# --- Poly-Haven-Modelle laden (einmal), Groesse auf Boden setzen
ph = {}
for aid in ["Barrel_01", "wooden_crate_01", "concrete_road_barrier"]:
    obs = [o for o in V.modell_laden(aid, col) if o.type == "MESH"]
    ph[aid] = obs

bpy.context.view_layer.update()
ORIG = {o: o.location.copy() for obs in ph.values() for o in obs}
ROT = {o: o.rotation_euler.z for obs in ph.values() for o in obs}
ZMIN = {aid: min((o.matrix_world @ Vector(c)).z for o in obs for c in o.bound_box) for aid, obs in ph.items()}
print("Modellgroessen:", {aid: [round(max((o.matrix_world @ Vector(c))[i] for o in obs for c in o.bound_box) - min((o.matrix_world @ Vector(c))[i] for o in obs for c in o.bound_box), 2) for i in range(3)] for aid, obs in ph.items()})

# --- Aufbau: eine Reihe mit 7 Objekten (selbst gebaut + heruntergeladen nebeneinander)
erzeuger = [wuerfel, zylinder, kugel, wand]
abst = 2.3
for i, fn in enumerate(erzeuger):
    fn().location = (i * abst, 0, 0)
for j, aid in enumerate(ph):
    for o in ph[aid]:
        o.location = ORIG[o] - Vector((0, 0, ZMIN[aid]))
        o.location.x += (len(erzeuger) + j) * abst + (0.3 if aid == "concrete_road_barrier" else 0)
        if aid == "concrete_road_barrier":
            o.rotation_euler.z = ROT[o] + math.radians(90)

# Boden
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=60, y_segments=40, size=1)
bmesh.ops.scale(bm, vec=(22, 14, 1), verts=bm.verts)
bmesh.ops.translate(bm, vec=(7, 3, 0), verts=bm.verts)
boden = V.objekt_aus_bmesh("GEO_Test_Boden", bm, col, material=lib["MAT_Asphalt_Alt"])


# Licht: HDRI (Sonne aus 265 Grad ausgerichtet) + Sonnenlampe
hdr = os.path.join(V.ASSETS, "hdri", "kloofendal_28d_misty_puresky_4k.hdr")
img = bpy.data.images.load(hdr)
rot, el = V.hdri_rotation_fuer(img, 265)
print(f"HDRI-Sonne Hoehe {el:.1f} Grad, Rotation {rot:.1f} Grad")
V.hdri_welt(hdr, 1.0, rot)
V.sonne(265, el, staerke=2.5, kelvin=5000, winkel_grad=2.0, col=V.collection("10_Licht_Atmosphaere"))

cam_d = bpy.data.cameras.new("CAM_Materialtest")
cam_d.lens = 30
cam = bpy.data.objects.new("CAM_Materialtest", cam_d)
V.collection("11_Kameras").objects.link(cam)
cam.location = (6.9, -13.8, 3.3)
cam.rotation_euler = (Vector((6.9, 0.6, 0.7)) - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam

os.makedirs(os.path.join(V.ROOT, "renders", "test"), exist_ok=True)
os.makedirs(os.path.join(V.ROOT, "teile"), exist_ok=True)
for wert, name in [(0.0, "000"), (0.5, "050"), (1.0, "100")]:
    sc["verw_master"] = wert
    t0 = time.time()
    V.vorschau_render(sc, os.path.join(V.ROOT, "renders", "test", f"phase1_materialtest_{name}.png"), samples=64)
    print(f"RENDERZEIT {name}: {time.time() - t0:.1f} s")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(V.ROOT, "teile", "materialtest.blend"))
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_mainfile()
