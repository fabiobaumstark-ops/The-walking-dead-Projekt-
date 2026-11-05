"""Phase-3-Nacharbeit 2B/3B: nur das Militaer (05_Militaer) neu bauen, Rest der Szene bleibt unveraendert.

Aufruf:  blender -b viertel_v04.blend --python scripts/phase3/nacharbeit_militaer.py -- --version 05 [--ohne-speichern]
1. Alle Objekte in 05_Militaer entfernen, Wanddurchbruch-Modifier von Panzer B am Gebaeude entfernen
2. militaer.bauen() mit den Details aus militaer.json -> "detail" (gleiche Bau-Seeds wie vorher)
"""
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, os.path.join(HIER, "..", "phase2"))
sys.path.insert(0, HIER)
import bpy  # noqa: E402
import viertel_lib as V  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
version = args[args.index("--version") + 1] if "--version" in args else "05"


def militaer_entfernen():
    col = bpy.data.collections["05_Militaer"]
    for ob in bpy.data.objects:
        for m in [m for m in ob.modifiers if m.name == "Panzer_B_Durchbruch"]:
            ob.modifiers.remove(m)
    obs = list(col.all_objects)
    for ob in obs:
        bpy.data.objects.remove(ob)
    for ch in list(col.children_recursive):
        bpy.data.collections.remove(ch)
    bpy.data.orphans_purge(do_recursive=True)
    return len(obs)


if __name__ == "__main__":
    t0 = time.time()
    V.regler_setzen(bpy.context.scene)
    print("ENTFERNT", militaer_entfernen(), "Objekte", flush=True)
    import militaer as MI
    MI.bauen()
    print("ZEIT Militaer", round(time.time() - t0, 1), "s", flush=True)
    if "--ohne-speichern" not in args:
        pfad = os.path.join(V.ROOT, f"viertel_v{version}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=pfad, compress=True, relative_remap=True)
        print("GESPEICHERT", pfad, round(os.path.getsize(pfad) / 1e6, 1), "MB")
