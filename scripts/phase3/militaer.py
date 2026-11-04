"""Phase 3.3–3.5 – Militaer in der Szene: Panzer A (Hauptstrasse), Panzer B (in Hauswand B17), Hubschrauber (B21).

Aufruf ueber build_phase3.py (Funktion bauen()).
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, HIER)
import viertel_lib as V  # noqa: E402
import panzer as PZ  # noqa: E402
import fz_teile as FT  # noqa: E402


def schutthaufen(name, mitte_welt, radius, hoehe, teile, col, boden, rnd, yaw=0.0, laengs=1.6):
    """Schuttkegel aus den Phase-2-Bruchstuecken (PROTO_Schutt) als Instanzen."""
    proto = bpy.data.collections.get("PROTO_Schutt")
    if proto is None or not proto.objects:
        return None
    n_proto = len([o for o in proto.objects])
    punkte = []
    rz = Matrix.Rotation(yaw, 3, "Z")
    for _ in range(teile):
        r = radius * math.sqrt(rnd.random())
        a = rnd.uniform(0, 2 * math.pi)
        lp = Vector((r * math.cos(a) * laengs, r * math.sin(a), 0))
        w = rz @ lp + Vector(mitte_welt)
        h = hoehe * max(0.0, 1 - (r / radius) ** 1.6) * rnd.uniform(0.55, 1.0)
        z = boden.z(w.x, w.y) + h
        s = rnd.uniform(0.7, 1.7)
        punkte.append((Vector((w.x, w.y, z)), (rnd.uniform(0, 3.1), rnd.uniform(0, 3.1), rnd.uniform(0, 6.28)), (s, s, s),
                       rnd.randrange(n_proto)))
    return V.instanzen(name, punkte, proto, col)


def wandloch(cfg_loch):
    """Durchbruch in der Hauswand (Boolean, zerstoerungsfrei) fuer Panzer B."""
    zielname = cfg_loch["objekt"]
    me = bpy.data.meshes.new(f"MIL_Wandloch_{zielname}")
    bm = bmesh.new()
    rnd = random.Random(5)
    mx, my, mz = cfg_loch["mitte"]
    gx, gy, gz = cfg_loch["groesse"]
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
    for v in bm.verts:  # unregelmaessige Bruchkante
        v.co = Vector((v.co.x * gx * (1 + 0.18 * rnd.uniform(-1, 1)), v.co.y * gy, v.co.z * gz * (1 + 0.15 * rnd.uniform(-1, 1))))
    bmesh.ops.translate(bm, vec=(mx, my, mz), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    cut = bpy.data.objects.new(f"MIL_Wandloch_{zielname}", me)
    V.collection("05_Militaer").objects.link(cut)
    cut.hide_render = True
    cut.display_type = "WIRE"
    for n in (zielname, f"{zielname}_Decals"):
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        m = ob.modifiers.new("Panzer_B_Durchbruch", "BOOLEAN")
        m.object = cut
        m.operation = "DIFFERENCE"
        m.solver = "EXACT"
    return cut


def panzer_setzen(boden, col):
    import flotte as FL
    C = PZ.cfg()
    out = []
    # Panzer A
    oa = C["panzer_a"]
    a = PZ.bauen("MIL_Panzer_A", C, col, random.Random(37), oa)
    PZ.setzen(a, boden, oa)
    bpy.context.view_layer.update()
    if oa.get("pfuetze"):
        PZ.pfuetze(a, col, boden)
    out.append(a)
    # Panzer B: in die Wand gefahren, vorne angehoben, Front unter Schutt
    ob = C["panzer_b"]
    b = PZ.bauen("MIL_Panzer_B", C, col, random.Random(41), ob)
    PZ.setzen(b, boden, ob)
    bpy.context.view_layer.update()
    sc = ob["schutt"]
    mw = b.matrix_world
    mitte = mw @ Vector((sc["mitte_lokal"][0], sc["mitte_lokal"][1], 0))
    schutthaufen("MIL_Panzer_B_Schutt", (mitte.x, mitte.y, 0), sc["radius"], sc["hoehe"], sc["teile"], col, boden,
                 random.Random(9), yaw=math.radians(ob["richtung"]))
    if ob.get("wand_loch"):
        wandloch(ob["wand_loch"])
    out.append(b)
    _ = FL
    return out


def bauen(boden=None):
    import flotte as FL
    boden = boden or FL.Boden()
    col = V.collection("05_Militaer")
    return panzer_setzen(boden, col)
