"""Phase 4 – gemeinsame Werkzeuge: Strahlen gegen die Szene, Pflanzen-Prototypen, Abstand zu Hero-Kameras.

Platzierung per Strahl (ray_cast) statt Formeln: Pflanzen sitzen damit genau auf Boden, Schutt, Daechern und Fassaden,
auch an zerstoerten Stellen. Vegetation (VEG_) und unsichtbare Hilfsobjekte werden vom Strahl durchdrungen.
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, os.path.join(HIER, "..", "phase2"))
import viertel_lib as V  # noqa: E402

BODEN = ("BOD_", "STR_", "GEO_")
DURCH = ("VEG_", "FX_", "LGT_", "CAM_")


def cfg():
    return V.config("vegetation.json")


def kameras():
    return [o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("CAM_Hero_")]


def abstand_kamera(p, _cache={}):
    if "k" not in _cache:
        _cache["k"] = kameras()
    p = Vector(p)
    return min((p - c).length for c in _cache["k"])


def im_ausschluss(x, y):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in cfg()["ausschluss_rechtecke"])


class Strahl:
    def __init__(self):
        self.dg = bpy.context.evaluated_depsgraph_get()
        self.sc = bpy.context.scene
        self.n = 0

    def treffer(self, start, richtung, weite=1.0e4):
        """Erster sichtbarer Treffer (ohne Vegetation/Hilfsobjekte): (Punkt, Normale, Objekt) oder (None, None, None)."""
        p = Vector(start)
        d = Vector(richtung).normalized()
        rest = weite
        for _ in range(12):
            self.n += 1
            ok, loc, nor, _i, ob, _m = self.sc.ray_cast(self.dg, p, d, distance=rest)
            if not ok:
                return None, None, None
            org = ob.original if hasattr(ob, "original") else ob
            if org.hide_render or org.name.startswith(DURCH):
                schritt = (loc - p).length + 0.002
                p = loc + d * 0.002
                rest -= schritt
                if rest <= 0:
                    return None, None, None
                continue
            return loc, nor, org
        return None, None, None

    def boden(self, x, y, z0=90.0):
        """Bodenpunkt (z, normale, name) wenn von oben zuerst Boden getroffen wird, sonst None (Hindernis)."""
        loc, nor, ob = self.treffer((x, y, z0), (0, 0, -1))
        if loc is None or not ob.name.startswith(BODEN):
            return None
        return loc.z, nor, ob.name

    def oben(self, x, y, z0=90.0):
        """Oberster Treffer beliebiger Art (fuer Daecher, Schutt)."""
        loc, nor, ob = self.treffer((x, y, z0), (0, 0, -1))
        return (loc, nor, ob) if loc is not None else None


# ------------------------------------------------------------------ Prototypen
# Grosse Modelle (Baeume) werden aus assets/models/ VERLINKT (nicht kopiert), damit die .blend klein bleibt.
# Farbanpassung/Verwitterung (A10) ueber lokale Material-Kopien, die pro Objekt zugewiesen werden (slot.link = OBJECT).
_MATS = {}


def lokales_material(m):
    if m is None:
        return None
    if m.name not in _MATS:
        k = m.copy()
        k.name = f"VEG_{m.name}"
        V.material_einfaerben(k)
        _MATS[m.name] = k
    return _MATS[m.name]


def unsichtbar():
    m = bpy.data.materials.get("VEG_Unsichtbar")
    if m is None:
        m = bpy.data.materials.new("VEG_Unsichtbar")
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        nt.links.new(tr.outputs[0], out.inputs["Surface"])
    return m


def link_prototyp(aid, objname, col, name):
    """Verlinkt ein Objekt aus assets/models/<aid>/<aid>_2k.blend. Lokales Objekt mit dem verlinkten Mesh;
    matrix_world = Versatz auf Stammfuss (Mittel der untersten Punkte) und z min = 0. Masse als Eigenschaften."""
    pfad = os.path.join(V.ASSETS, "models", aid, f"{aid}_2k.blend")
    with bpy.data.libraries.load(pfad, link=True, relative=True) as (src, dst):
        dst.objects = [objname]
    lo = dst.objects[0]
    me = lo.data
    M = lo.matrix_world.copy()
    co = [M @ v.co for v in me.vertices]
    zmin = min(c.z for c in co)
    unten = [c for c in co if c.z < zmin + 0.12]
    cx = sum(c.x for c in unten) / len(unten)
    cy = sum(c.y for c in unten) / len(unten)
    p = bpy.data.objects.new(name, me)
    col.objects.link(p)
    p.matrix_world = Matrix.Translation((-cx, -cy, -zmin)) @ M
    h = max(c.z for c in co) - zmin
    oben = sorted(math.hypot(c.x - cx, c.y - cy) for c in co if c.z - zmin > 0.35 * h)
    p["h"], p["r"], p["zb"] = h, (oben[int(0.95 * (len(oben) - 1))] if oben else 1.0), 0.35 * h
    for s in p.material_slots:
        m = s.material
        s.link = "OBJECT"
        s.material = lokales_material(m)
    return p


def variante(p, name, col, unsichtbar_woerter=()):
    """Weitere Variante mit gleichem (verlinktem) Mesh, z. B. tot = Laub/Zweige unsichtbar."""
    k = bpy.data.objects.new(name, p.data)
    col.objects.link(k)
    k.matrix_world = p.matrix_world.copy()
    for key in ("h", "r", "zb"):
        k[key] = p[key]
    for i, s in enumerate(p.data.materials):
        sl = k.material_slots[i]
        sl.link = "OBJECT"
        sl.material = unsichtbar() if (s and any(w in s.name for w in unsichtbar_woerter)) else p.material_slots[i].material
    return k


def dezimiert(p, ratio, name, col):
    """Lokale, stark vereinfachte Kopie (Hintergrund) – klein genug fuer die .blend."""
    tmp = bpy.data.objects.new("tmp_dez", p.data)
    bpy.context.scene.collection.objects.link(tmp)  # Prototypen-Collection ist ausgeschlossen -> sonst kein Modifier
    m = tmp.modifiers.new("LOD", "DECIMATE")
    m.ratio = ratio
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    me.name = name
    for i in range(len(me.materials)):
        me.materials[i] = p.material_slots[i].material
    me.transform(p.matrix_world)  # Versatz einbacken: GN-Instanzen setzen die Objekt-Transformation zurueck
    k = bpy.data.objects.new(name, me)
    col.objects.link(k)
    for key in ("h", "r", "zb"):
        k[key] = p[key]
    return k


def kopie(proto, name, col, pos=None, rot_z=0.0, skal=1.0, kipp=(0.0, 0.0), matrix=None):
    """Instanz des Prototyps (gleiches Mesh, gleiche Material-Zuweisung). matrix ersetzt pos/rot/skal."""
    ob = bpy.data.objects.new(name, proto.data)
    col.objects.link(ob)
    if matrix is None:
        from mathutils import Euler
        matrix = (Matrix.Translation(pos) @ Euler((kipp[0], kipp[1], rot_z)).to_matrix().to_4x4()
                  @ Matrix.Diagonal((skal, skal, skal, 1)))
    ob.matrix_world = matrix @ proto.matrix_world
    for i, s in enumerate(proto.material_slots):
        if s.link == "OBJECT":
            ob.material_slots[i].link = "OBJECT"
            ob.material_slots[i].material = s.material
    return ob


def rnd(salz):
    return random.Random(cfg()["seed"] * 1000 + salz)
