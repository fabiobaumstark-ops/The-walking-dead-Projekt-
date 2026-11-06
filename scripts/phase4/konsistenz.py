"""Phase 4.3 – Konsistenz-Test (A10.6): selbst gebaute Objekte an heruntergeladene angleichen.

Befund der Nah-Renders: Matratzen/Kartons wirkten wie weisse Bloecke (keine brauchbaren UVs -> Textur einfarbig,
zu hell), Panzer zu kantig (keine Fasen). Massnahmen (vegetation.json -> konsistenz):
- Box-UV fuer selbst gebaute Meshes ohne nutzbare UVs (Praefixe)
- Fasen-Modifier fuer harte Kanten (Praefixe)
- Helligkeit (HSV-Value) einzelner Materialien senken, Flechten auf Fahrzeugen reduzieren
"""
import os
import sys

import bmesh
import bpy

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import veg_basis as VB  # noqa: E402


def _uv_flaeche(me):
    if not me.uv_layers:
        return 0.0
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active
    a = 0.0
    for f in bm.faces:
        p = [l[uv].uv for l in f.loops]
        a += abs(sum(p[i].x * p[i - 1].y - p[i - 1].x * p[i].y for i in range(len(p)))) / 2
    bm.free()
    return a


def box_uv(me, skala):
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.active or bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = [(1, 2), (0, 2), (0, 1)][ax]
        for l in f.loops:
            l[uv].uv = (l.vert.co[a] * skala, l.vert.co[b] * skala)
    bm.to_mesh(me)
    bm.free()


def bauen():
    C = VB.cfg()["konsistenz"]
    meshes = {o.data for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(tuple(C["uv_praefixe"]))}
    neu_uv = 0
    for me in meshes:
        if me.library is None and _uv_flaeche(me) < 1e-4 * max(1, len(me.polygons)):
            box_uv(me, C["uv_skala"])
            neu_uv += 1
    fasen = 0
    for o in bpy.data.objects:
        if o.type == "MESH" and o.library is None and o.name.startswith(tuple(C["fasen_praefixe"])) and "Fase" not in o.modifiers:
            m = o.modifiers.new("Fase", "BEVEL")
            m.width, m.segments, m.limit_method = C["fasen_breite_m"], 2, "ANGLE"
            m.angle_limit = 0.6
            m.harden_normals = False
            fasen += 1
    for name, wert in C["hsv_value"].items():
        n = bpy.data.materials[name].node_tree.nodes.get("HSV_Basis")
        n.inputs["Value"].default_value = wert
    fl = 0
    for m in bpy.data.materials:
        if m.name.startswith(tuple(C["flechten_praefixe"])) and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == "GROUP" and n.node_tree and n.node_tree.name == "MAT_Verwitterung" and "Flechten" in n.inputs:
                    n.inputs["Flechten"].default_value = min(n.inputs["Flechten"].default_value, C["flechten_fahrzeuge"])
                    fl += 1
    print("KONSISTENZ", {"box_uv": neu_uv, "fasen": fasen, "flechten": fl}, flush=True)
