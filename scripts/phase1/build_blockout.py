"""Phase 1 – baut die komplette Blockout-Szene aus den Konfigurationen und speichert viertel_vXX.blend.

Aufruf (Repo-Hauptordner):
    blender -b --factory-startup --python scripts/phase1/build_blockout.py -- [--nur umgebung]
"""
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, HIER)
import bpy  # noqa: E402
import viertel_lib as V  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
nur = args[args.index("--nur") + 1] if "--nur" in args else "alles"
version = args[args.index("--version") + 1] if "--version" in args else "01"

t0 = time.time()
sc = V.leere_szene()
sc.name = "Viertel"
V.alle_collections()
V.regler_setzen(sc)
V.bibliothek()  # Material-Bibliothek (Fake-User) fuer spaetere Phasen
import blockout_umgebung  # noqa: E402
blockout_umgebung.bauen()
print(f"Umgebung fertig nach {time.time() - t0:.1f} s")
if nur in ("alles", "gebaeude"):
    import blockout_gebaeude  # noqa: E402
    blockout_gebaeude.bauen()
    print(f"Gebaeude fertig nach {time.time() - t0:.1f} s")
if nur in ("alles", "gebaeude", "kameras"):
    import blockout_kameras  # noqa: E402
    blockout_kameras.bauen()

ziel = os.path.join(V.ROOT, f"viertel_v{version}.blend")
bpy.ops.wm.save_as_mainfile(filepath=ziel, compress=True)
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_mainfile(compress=True)
print(f"GESPEICHERT {ziel} ({os.path.getsize(ziel) / 1e6:.1f} MB) nach {time.time() - t0:.1f} s")
