"""Phase 4.2 – Material-Feinschliff: Pruefung aller verwendeten Materialien (A10/4.2) und Nachruesten.

- Jedes verwendete Material muss durch MAT_Verwitterung laufen. Fehlt die Gruppe (z. B. Poly-Haven-Pflanzen mit
  eigener Shader-Gruppe), wird sie ueber viertel_lib.material_einfaerben nachgeruestet.
- Ausnahmen (vegetation.json -> material.ausnahmen): Overlay-Decals, die auf bereits verwitterten Flaechen liegen,
  Wasser und unsichtbare Hilfsmaterialien.
- Prueft: Rauheit 0 ausserhalb von Wasser, fehlende Bilddateien.
"""
import os
import sys

import bpy

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import veg_basis as VB  # noqa: E402
from veg_basis import V  # noqa: E402


def _hat_gruppe(nt, tiefe=0):
    for n in nt.nodes:
        if n.type == "GROUP" and n.node_tree:
            if n.node_tree.name == "MAT_Verwitterung" or (tiefe < 2 and _hat_gruppe(n.node_tree, tiefe + 1)):
                return True
    return False


def benutzte_materialien():
    out = set()
    for o in bpy.data.objects:
        if o.type == "MESH":
            for s in o.material_slots:
                if s.material:
                    out.add(s.material)
    return out


def pruefen():
    C = VB.cfg()["material"]
    ohne, glatt, fehlt = [], [], set()
    for m in benutzte_materialien():
        if m.name.startswith(tuple(C["ausnahmen"])) or not m.node_tree:
            continue
        if not _hat_gruppe(m.node_tree):
            ohne.append(m.name)
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED" and not n.inputs["Roughness"].is_linked and n.inputs["Roughness"].default_value < 0.05:
                glatt.append(m.name)
            if n.type == "TEX_IMAGE" and n.image and n.image.source == "FILE":
                if not os.path.exists(bpy.path.abspath(n.image.filepath, library=n.image.library)):
                    fehlt.add(n.image.filepath)
    return ohne, glatt, sorted(fehlt)


def bauen():
    vorher, _, _ = pruefen()
    for name in vorher:
        V.material_einfaerben(bpy.data.materials[name], VB.cfg()["material"]["hsv"].get(name.split(".")[0]))
    ohne, glatt, fehlt = pruefen()
    print("MATERIAL", {"nachgeruestet": len(vorher) - len(ohne), "weiter_ohne_verwitterung": ohne[:20],
                       "rauheit_0": glatt[:20], "fehlende_bilder": fehlt[:10]}, flush=True)
