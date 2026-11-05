"""Nah-Vorschau einzelner Objekte (Pruefung der Nacharbeit), lokal mit Metal-GPU falls vorhanden.

Aufruf:  blender -b viertel_v05.blend --python scripts/phase3/render_nah.py -- --prefix phase3b [--samples 64]
Ansichten: (Name, Ziel-Objekt, Kamera-Versatz zum Ziel, Ziel-Versatz, Brennweite)
"""
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import viertel_lib as V  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
praefix = args[args.index("--prefix") + 1] if "--prefix" in args else "phase3b"
samples = int(args[args.index("--samples") + 1]) if "--samples" in args else 64
nur = args[args.index("--nur") + 1].split(",") if "--nur" in args else None

ANSICHTEN = [
    ("panzer_turm_nah", "MIL_Panzer_A_Turm_Koerper", (-5.0, -2.5, 1.0), (0, 0, 0.4), 50),
    ("panzer_a_nah", "MIL_Panzer_A", (6.5, -7.5, 1.7), (0, 0, 1.4), 35),
    ("hubschrauber_rumpf", "MIL_Hubschrauber_Rumpf", (-6.0, 7.0, -3.0), (0, 0, 1.0), 35),
    ("hubschrauber_nah", "MIL_Hubschrauber_Rumpf", (3.0, 6.0, -1.0), (0, 0, 1.6), 28),
]


def gpu():
    try:
        p = bpy.context.preferences.addons["cycles"].preferences
        p.compute_device_type = "METAL"
        p.get_devices()
        for d in p.devices:
            d.use = True
        return any(d.type == "METAL" for d in p.devices)
    except Exception:
        return False


def licht():
    """Gleiches Vorschau-Licht wie scripts/phase1/render_blockout.py (Szene speichert bis Phase 5 kein Licht)."""
    if "LGT_Sonne" in bpy.data.objects:
        return
    hdr = os.path.join(V.ASSETS, "hdri", "kloofendal_28d_misty_puresky_4k.hdr")
    img = bpy.data.images.load(hdr, check_existing=True)
    rot, el = V.hdri_rotation_fuer(img, 265)
    V.hdri_welt(hdr, 1.0, rot)
    V.sonne(265, el, staerke=2.5, kelvin=5000, winkel_grad=2.0, col=V.collection("10_Licht_Atmosphaere"))


sc = bpy.context.scene
licht()
metal = gpu()
cam_data = bpy.data.cameras.new("CAM_Nah_tmp")
cam = bpy.data.objects.new("CAM_Nah_tmp", cam_data)
sc.collection.objects.link(cam)
for name, ziel, versatz, zv, f in ANSICHTEN:
    if nur and name not in nur:
        continue
    ob = bpy.data.objects[ziel]
    z = ob.matrix_world.translation + Vector(zv)
    cam.location = z + Vector(versatz)
    cam.rotation_euler = (z - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = f
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU" if metal else "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(V.ROOT, "renders", "test", f"{praefix}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDER", name, "GPU" if metal else "CPU", flush=True)
