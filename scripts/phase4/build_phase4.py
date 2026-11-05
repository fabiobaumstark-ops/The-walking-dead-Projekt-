"""Phase 4 – Aufbau: viertel_v05.blend + grosse Vegetation -> viertel_v06.blend.

Aufruf:  blender -b viertel_v05.blend --python scripts/phase4/build_phase4.py -- --version 06 [--nur Baeume,Ranken,Boden] [--ohne-speichern]
Jeder Teil entfernt vorher seinen alten Stand (wiederholbar). Parameter: scripts/configs/vegetation.json.
"""
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import bpy  # noqa: E402
import veg_basis as VB  # noqa: E402
from veg_basis import V  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
version = args[args.index("--version") + 1] if "--version" in args else "06"
nur = args[args.index("--nur") + 1].split(",") if "--nur" in args else ["Baeume", "Ranken", "Boden"]

TEILE = {
    "Baeume": (["08_Vegetation/Baeume", "08_Vegetation/Baeume_Hintergrund"], ["PROTO_Baeume"]),
    "Ranken": (["08_Vegetation/Ranken"], ["PROTO_Ranken"]),
    "Boden": (["08_Vegetation/Bodendecker"], ["PROTO_Bodendecker"]),
}


def leeren(teil):
    cols, protos = TEILE[teil]
    for pfad in cols + protos:
        c = bpy.data.collections.get(pfad.split("/")[-1])
        if c is None:
            continue
        for o in list(c.all_objects):
            bpy.data.objects.remove(o)
    bpy.data.orphans_purge(do_recursive=True)


if __name__ == "__main__":
    t0 = time.time()
    V.regler_setzen(bpy.context.scene)
    for teil in nur:
        leeren(teil)
        if teil == "Baeume":
            import baeume
            baeume.bauen()
        elif teil == "Ranken":
            import ranken
            ranken.bauen()
        elif teil == "Boden":
            import bodendecker
            bodendecker.bauen()
        print("ZEIT", teil, round(time.time() - t0, 1), "s", flush=True)
    if "--ohne-speichern" not in args:
        pfad = os.path.join(V.ROOT, f"viertel_v{version}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=pfad, compress=True, relative_remap=True)
        print("GESPEICHERT", pfad, round(os.path.getsize(pfad) / 1e6, 1), "MB")
