"""Phase 5.8 – Qualitaetsrunde: technische Korrekturen an der fertigen Szene (wiederholbar).

Aufruf:  blender -b viertel_v08.blend --python scripts/phase5/qualitaet.py -- --version 09 [--nur Instanzen,Pfade]
Teile:
- Instanzen: Baeume (verlinktes Mesh + Material am Objekt) werden von Cycles NICHT als Instanzen geteilt, sondern je
  Objekt einzeln geladen (36 Baeume = ca. 24 Mio. Flaechen statt 3,7 Mio., > 4 GB RAM). Loesung: je Baum-Variante
  eine Vorlage in 00_Prototypen/PROTO_Baum_Instanzen_*, die Baeume selbst werden Collection-Instanzen (Empties,
  gleicher Name, gleiche Lage).
- Pfade: absolute Bild-/Bibliothekspfade relativ machen (AUFTRAG A3).
- Ansicht: Datei laesst sich auf dem Mac kaum oeffnen -> Pflanzen-Generatoren (Gras, Efeu, Wald) nur noch im Render
  berechnen, Baeume im Fenster als Kaesten, Simplify fuers Fenster. Der Render bleibt unveraendert.
"""
import os
import sys

import bpy

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "phase4"))
import veg_basis as VB  # noqa: E402
from veg_basis import V  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
version = args[args.index("--version") + 1] if "--version" in args else "09"
nur = args[args.index("--nur") + 1].split(",") if "--nur" in args else ["Instanzen", "Pfade", "Ansicht"]


def instanzen(sammlungen=("Baeume",), min_flaechen=20000):
    """Objekte mit geteiltem Mesh und Material am Objekt -> Collection-Instanzen."""
    gruppen = {}
    for cn in sammlungen:
        for ob in list(bpy.data.collections[cn].objects):
            if ob.type != "MESH" or ob.modifiers or len(ob.data.polygons) < min_flaechen:
                continue
            if not any(s.link == "OBJECT" for s in ob.material_slots):
                continue
            key = (ob.data.name, tuple(s.material.name if s.material else "" for s in ob.material_slots))
            gruppen.setdefault(key, []).append(ob)
    n_proto = n_inst = gespart = 0
    for i, (key, obs) in enumerate(sorted(gruppen.items())):
        erstes = obs[0]
        pc = V.prototypen(f"Baum_Instanzen_{i + 1:02d}")
        for alt in list(pc.objects):
            bpy.data.objects.remove(alt)
        p = bpy.data.objects.new(f"PROTO_Baum_Instanz_{i + 1:02d}", erstes.data)
        pc.objects.link(p)
        for k, s in enumerate(erstes.material_slots):
            p.material_slots[k].link = s.link
            p.material_slots[k].material = s.material
        n_proto += 1
        gespart += len(erstes.data.polygons) * (len(obs) - 1)
        for ob in obs:
            name, mw = ob.name, ob.matrix_world.copy()
            cols = list(ob.users_collection)
            eig = {k: ob[k] for k in ob.keys()}
            ob.name = name + "_alt"
            e = bpy.data.objects.new(name, None)
            e.empty_display_type, e.empty_display_size = "SINGLE_ARROW", 2.0
            e.instance_type, e.instance_collection = "COLLECTION", pc
            for c in cols:
                c.objects.link(e)
            e.matrix_world = mw
            for k, v in eig.items():
                e[k] = v
            bpy.data.objects.remove(ob)
            n_inst += 1
    print("INSTANZEN", {"vorlagen": n_proto, "baeume": n_inst, "flaechen_gespart": gespart}, flush=True)


def pfade():
    """Alle absoluten Pfade relativ zur .blend machen (Mac-Pfade /Users/.../assets/... -> //assets/...)."""
    V.pfade_relativ()


def ansicht():
    """Fenster-Anzeige entlasten (nur Viewport, Render unveraendert)."""
    sc = bpy.context.scene
    veg = set(bpy.data.collections["08_Vegetation"].all_objects)
    n_mod = n_box = 0
    for ob in veg:
        for m in ob.modifiers:
            if m.type == "NODES" and m.show_viewport:
                m.show_viewport = False  # Gras, Efeu, Wald: erst beim Rendern erzeugen
                n_mod += 1
        if ob.instance_type == "COLLECTION" or (ob.type == "MESH" and len(ob.data.polygons) > 50000):
            ob.display_type = "BOUNDS"
            n_box += 1
    for ob in bpy.data.objects:  # sonstige sehr schwere Meshes als Kasten
        if ob not in veg and ob.type == "MESH" and len(ob.data.polygons) > 400000:
            ob.display_type = "BOUNDS"
            n_box += 1
    sc.render.use_simplify = True
    sc.render.simplify_subdivision = 0          # Fenster: keine Unterteilung
    sc.render.simplify_subdivision_render = 6   # Render: unveraendert
    if hasattr(sc.render, "simplify_volumes"):
        sc.render.simplify_volumes = 0.25
    sc.render.use_persistent_data = False
    print("ANSICHT", {"generatoren_nur_render": n_mod, "kaesten": n_box}, flush=True)


if __name__ == "__main__":
    for teil in nur:
        {"Instanzen": instanzen, "Pfade": pfade, "Ansicht": ansicht}[teil]()
    if "--ohne-speichern" not in args:
        pfad = os.path.join(V.ROOT, f"viertel_v{version}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=pfad, compress=True, relative_remap=True)
        print("GESPEICHERT", pfad, round(os.path.getsize(pfad) / 1e6, 1), "MB")
    _ = VB
