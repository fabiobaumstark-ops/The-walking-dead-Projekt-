"""Phase 2 – baut die Szene mit Architektur-Details, Strassenraum, Schutt, Checkpoint, Barrikaden, Hintergrund-Ring.

Aufruf (Repo-Hauptordner):
    blender -b --factory-startup --python scripts/phase2/build_phase2.py -- --version 02 [--nur gebaeude]
"""
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, os.path.join(HIER, "..", "phase1"))
sys.path.insert(0, HIER)
import bpy  # noqa: E402
import viertel_lib as V  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
version = args[args.index("--version") + 1] if "--version" in args else "02"
nur = args[args.index("--nur") + 1].split(",") if "--nur" in args else None


def an(teil):
    return nur is None or teil in nur


t0 = time.time()
sc = V.leere_szene()
sc.name = "Viertel"
V.alle_collections()
V.regler_setzen(sc)
V.bibliothek()
import blockout_umgebung  # noqa: E402
blockout_umgebung.bauen()
print(f"[{time.time() - t0:5.1f}s] Umgebung (Phase 1)")
import gebaeude2  # noqa: E402
gebaeude2.bauen()
print(f"[{time.time() - t0:5.1f}s] Gebaeude Phase 2")
for modul in ("strassenraum", "schutt", "checkpoint", "barrikaden", "boden", "vegetation_klein", "hintergrund_ring"):
    if an(modul) and os.path.exists(os.path.join(HIER, modul + ".py")):
        __import__(modul).bauen()
        print(f"[{time.time() - t0:5.1f}s] {modul}")
import blockout_kameras  # noqa: E402
blockout_kameras.bauen()
ziel = os.path.join(V.ROOT, f"viertel_v{version}.blend")
bpy.ops.wm.save_as_mainfile(filepath=ziel, compress=True)
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_mainfile(compress=True)
print(f"GESPEICHERT {ziel} ({os.path.getsize(ziel) / 1e6:.1f} MB) nach {time.time() - t0:.1f} s")
