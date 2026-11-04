"""Phase 3 – Aufbau: viertel_v03.blend + Fahrzeuge (+ spaeter Militaer, Figuren) -> viertel_v04.blend.

Aufruf:  blender -b viertel_v03.blend --python scripts/phase3/build_phase3.py -- --version 04 [--nur Stau,Mast] [--ohne-speichern]
Schritte:
1. Platzhalter-Autos entfernen: Barrikade 1 neu bauen (identisch, nur ohne Platzhalter), Hochstrassen-Fernteil ohne Wracks
2. Flotte laut scripts/configs/flotte.json (flotte.py)
3. Wracks auf der Hochstrasse (ferne Detailstufe)
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
version = args[args.index("--version") + 1] if "--version" in args else "04"
nur = args[args.index("--nur") + 1].split(",") if "--nur" in args else None


def platzhalter_entfernen():
    import barrikaden as B
    import hintergrund_ring as HR
    import strassenraum as SR
    # Zustand des Strassenmoduls fuer die Bodenhoehe (Barrikaden liegen ausserhalb der Detailzonen -> Senken irrelevant)
    SR.L = V.config("layout.json")
    SR.C = V.config("strassenraum.json")
    SR.DETAIL[:] = [tuple(z) for z in SR.C["detail_zonen"]]
    for n in ("CHK_Barrikade_1", "CHK_Barrikade_2", "CHK_Barrikade_3", "CHK_Barrikaden_Ketten_Draht"):
        ob = bpy.data.objects.get(n)
        if ob:
            bpy.data.objects.remove(ob)
    alt = B.auto_platzhalter
    B.auto_platzhalter = lambda *a, **k: None  # gleiche Zufallsfolge, nur ohne Platzhalter-Autos
    B.bauen()
    B.auto_platzhalter = alt
    ob = bpy.data.objects.get("CHK_Barrikade_1")
    if ob:
        ob["info"] = "Autos: echte Fahrzeuge (Phase 3, 04_Fahrzeuge/Barrikade1)"
    ob = bpy.data.objects.get("STR_Hochstrasse_Fernteil")
    if ob:
        bpy.data.objects.remove(ob)
    HR.H = dict(V.config("hintergrund.json"))
    HR.H["wracks_pro_feld"] = 0.0
    HR.L = V.config("layout.json")
    HR.hochstrasse_weiter(V.collection("02_Strassen/Hochstrasse"))
    ob = bpy.data.objects.get("STR_Hochstrasse_Fernteil")
    if ob:
        ob["info"] = "Wracks: ferne Fahrzeuge (Phase 3, 04_Fahrzeuge/Hochstrasse)"


if __name__ == "__main__":
    t0 = time.time()
    V.regler_setzen(bpy.context.scene)
    if not nur:
        platzhalter_entfernen()
    import flotte as FL
    if not nur or any(g != "Militaer" for g in nur):
        FL.flotte_bauen(nur_gruppen=[g for g in nur if g != "Militaer"] if nur else None)
    print("ZEIT Flotte", round(time.time() - t0, 1), "s", flush=True)
    if not nur or "Militaer" in nur:
        import militaer as MI
        MI.bauen()
        print("ZEIT Militaer", round(time.time() - t0, 1), "s", flush=True)
    if "--ohne-speichern" not in args:
        pfad = os.path.join(V.ROOT, f"viertel_v{version}{'test' if '--test' in args else ''}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=pfad, compress=True)
        print("GESPEICHERT", pfad, round(os.path.getsize(pfad) / 1e6, 1), "MB")
