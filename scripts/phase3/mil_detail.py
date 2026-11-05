"""Phase-3-Nacharbeit 2B/3B: Panzerturm und Hubschrauberrumpf weniger glatt.

- dellen(): echte Dellen + leichte Welligkeit in der Geometrie (bmesh, eigener Seed)
- lack_veredeln(): Abplatzer an Kanten (Bevel-Maske, unabhaengig von der Polygondichte), vereinzelte Flaechen-Abplatzer,
  Schmutz in Ecken/Fugen (AO), Dellen-Bump. Wird VOR MAT_Verwitterung eingehaengt, die weiter alles durchlaeuft.
- blech_naehte(): Blechstoesse mit Nietreihen (Hubschrauber), ebenfalls vor MAT_Verwitterung.
Parameter: scripts/configs/militaer.json -> "detail".
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector, noise

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
import viertel_lib as V  # noqa: E402

_m, _n, _mr, _l, _mix = V._math, V._noise, V._maprange, V._link, V._mix_rgb


def cfg():
    return V.config("militaer.json")["detail"]


def rnd(salz):
    return random.Random(cfg()["seed"] * 1000 + salz)


# ---------------------------------------------------------------- Geometrie
def unterteilen(bm, faces, cuts):
    """Grosse Flaechen in ein Raster teilen, damit Dellen Geometrie haben."""
    kanten = list({e for f in faces for e in f.edges})
    bmesh.ops.subdivide_edges(bm, edges=kanten, cuts=cuts, use_grid_fill=True)


def dellen(bm, verts, r, p, fest=()):
    """Dellen nach innen (entlang der Vertex-Normale) + leichte Welligkeit. fest: Vertices, die bleiben."""
    fest = set(fest)
    vs = [v for v in verts if v not in fest]
    if not vs:
        return
    bm.normal_update()
    normalen = {v: v.normal.copy() for v in vs}
    zentren = []
    for _ in range(p["anzahl"]):
        v = r.choice(vs)
        zentren.append((v.co.copy(), normalen[v], r.uniform(*p["radius_m"]), r.uniform(*p["tiefe_m"])))
    w = p["welle_m"]
    for v in vs:
        n = normalen[v]
        off = noise.noise(v.co * 2.2) * w
        for c, nc, rad, tiefe in zentren:
            d = (v.co - c).length
            if d < 2.2 * rad and n.dot(nc) > 0.3:
                off -= tiefe * math.exp(-2.0 * (d / rad) ** 2)
        v.co += n * off


# ---------------------------------------------------------------- Shader
def _verw_knoten(mat):
    return next((n for n in mat.node_tree.nodes if n.type == "GROUP" and n.node_tree
                 and n.node_tree.name == "MAT_Verwitterung"), None)


def _quelle(nt, sock):
    """Was gerade in den Eingang laeuft (Link oder fester Wert)."""
    if sock.is_linked:
        lk = sock.links[0]
        src = lk.from_socket
        nt.links.remove(lk)
        return src
    dv = sock.default_value
    return tuple(dv) if hasattr(dv, "__len__") else float(dv)


def _pos(nt):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return tc.outputs["Object"]


def lack_veredeln(mat):
    """Abplatzer, Schmutz in Ecken und Dellen-Bump fuer Militaerlack (einmal pro Material)."""
    if mat is None or mat.get("veredelt_2b3b"):
        return mat
    V.verwitterung_gruppe()  # Eingang "Flechten" nachruesten
    grp = _verw_knoten(mat)
    if grp is None:
        return mat
    p = cfg()["lack"]
    grp.inputs["Flechten"].default_value = p["flechten"]  # Flechten nur angedeutet: auf Lack wirkten sie wie weisse Flecken
    nt = mat.node_tree
    farbe = _quelle(nt, grp.inputs["Farbe"])
    rau = _quelle(nt, grp.inputs["Rauheit"])
    normal = _quelle(nt, grp.inputs["Normale"])
    P = _pos(nt)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    # Kantenmaske ueber den Bevel-Knoten (funktioniert auch auf grossen, flachen Polygonen)
    bev = nt.nodes.new("ShaderNodeBevel")
    bev.samples = 8
    bev.inputs["Radius"].default_value = p["kante_radius_m"]
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(bev.outputs["Normal"], dot.inputs[0])
    nt.links.new(geo.outputs["Normal"], dot.inputs[1])
    kante = _mr(nt, dot.outputs["Value"], 0.998, 0.97)
    rauschen = _n(nt, P, 9.0, 8.0, 0.72)
    chips_k = _m(nt, "MULTIPLY", kante, _mr(nt, rauschen, 0.40, 0.47))
    chips_f = _m(nt, "MULTIPLY", _mr(nt, _n(nt, P, 14.0, 10.0, 0.75), 0.60, 0.62), p["flaechen_abplatzer"])
    chips = _m(nt, "MULTIPLY", _m(nt, "MAXIMUM", chips_k, chips_f), p["abplatzer"], clamp=True)
    # Unter dem Lack: Grundierung -> blankes Metall -> Rost (innen)
    tief = _mr(nt, _n(nt, P, 30.0, 4.0, 0.6), 0.45, 0.6)
    unter = _mix(nt, tief, V.hex_lin(p["primer"]), _mix(nt, _mr(nt, rauschen, 0.5, 0.62), V.hex_lin(p["metall"]),
                                                       V.hex_lin(p["rost"])))
    # Schmutz in Ecken und Fugen (AO), fleckig
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 8
    ao.only_local = True
    ao.inputs["Distance"].default_value = 0.25
    dreck = _m(nt, "MULTIPLY", _mr(nt, ao.outputs["AO"], 0.9, 0.45), _mr(nt, _n(nt, P, 4.0, 6.0, 0.65), 0.3, 0.6))
    dreck = _m(nt, "MULTIPLY", dreck, p["schmutz_ecken"], clamp=True)
    # Tonvariation: grossflaechig heller/dunkler (Ausbleichen ungleichmaessig), senkrechte Schlieren
    ton = _mr(nt, _n(nt, P, 0.9, 3.0, 0.5), 0.3, 0.7, 1.0 - p["tonvariation"], 1.0 + p["tonvariation"])
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    _l(nt, farbe, hsv.inputs["Color"])
    _l(nt, ton, hsv.inputs["Value"])
    farbe = hsv.outputs["Color"]
    f2 = _mix(nt, dreck, farbe, V.hex_lin(p["schmutz"]))
    f2 = _mix(nt, chips, f2, unter)
    r2 = _m(nt, "ADD", rau, _m(nt, "MULTIPLY", dreck, 0.2), clamp=True)
    r2 = _mix_f(nt, chips, r2, 0.62)
    # Dellen-Bump (grossflaechig) + Abplatzer leicht vertieft
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = p["dellen_bump"]
    bump.inputs["Distance"].default_value = 0.02
    struktur = _m(nt, "MULTIPLY", _n(nt, P, 55.0, 6.0, 0.7), p["struktur"])  # Guss-/Walzhaut, Kratzer
    hoehe = _m(nt, "SUBTRACT", _m(nt, "ADD", _n(nt, P, 1.6, 2.0, 0.5), struktur), _m(nt, "MULTIPLY", chips, 0.15))
    nt.links.new(hoehe, bump.inputs["Height"])
    _l(nt, normal if not isinstance(normal, (float, tuple)) else None, bump.inputs["Normal"])
    _l(nt, f2, grp.inputs["Farbe"])
    _l(nt, r2, grp.inputs["Rauheit"])
    nt.links.new(bump.outputs["Normal"], grp.inputs["Normale"])
    mat["veredelt_2b3b"] = True
    return mat


def _mix_f(nt, fac, a, b):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "FLOAT"
    n.clamp_factor = True
    _l(nt, fac, n.inputs["Factor"])
    _l(nt, a, n.inputs["A"])
    _l(nt, b, n.inputs["B"])
    return n.outputs["Result"]


def _naht(nt, abstand_quer, entlang, fuge, niet_abstand, versatz, radius):
    """Fugen- und Nietmaske fuer eine Naht. abstand_quer: Abstand zur Nahtlinie (Socket), entlang: Koordinate laengs."""
    a = _m(nt, "ABSOLUTE", abstand_quer)
    fuge_m = _mr(nt, a, fuge, fuge * 0.4)
    # Nietreihen in +-versatz neben der Fuge
    q = _m(nt, "ABSOLUTE", _m(nt, "SUBTRACT", a, versatz))
    l = _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", _m(nt, "FRACT", _m(nt, "DIVIDE", entlang, niet_abstand)), 0.5), niet_abstand)
    d = nt.nodes.new("ShaderNodeVectorMath")
    d.operation = "LENGTH"
    c = nt.nodes.new("ShaderNodeCombineXYZ")
    _l(nt, q, c.inputs["X"])
    _l(nt, l, c.inputs["Y"])
    nt.links.new(c.outputs[0], d.inputs[0])
    niet = _mr(nt, d.outputs["Value"], radius, radius * 0.5)
    return fuge_m, niet


def blech_naehte(mat):
    """Blechstoesse (quer, alle stoss_abstand_m) und Laengsnaehte (naehte_z_m) mit Nietreihen. Objektkoordinaten."""
    if mat is None or mat.get("blech_2b3b"):
        return mat
    grp = _verw_knoten(mat)
    if grp is None:
        return mat
    p = cfg()["blech"]
    nt = mat.node_tree
    farbe = _quelle(nt, grp.inputs["Farbe"])
    rau = _quelle(nt, grp.inputs["Rauheit"])
    normal = _quelle(nt, grp.inputs["Normale"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(_pos(nt), sep.inputs[0])
    x, z = sep.outputs["X"], sep.outputs["Z"]
    s = p["stoss_abstand_m"]
    # Abstand zum naechsten Querstoss
    quer = _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", _m(nt, "FRACT", _m(nt, "DIVIDE", x, s)), 0.5), s)
    quer = _m(nt, "SUBTRACT", _m(nt, "ABSOLUTE", quer), s / 2)
    fuge, niet = _naht(nt, quer, z, p["fuge_m"], p["niet_abstand_m"], p["niet_versatz_m"], p["niet_radius_m"])
    for zn in p["naehte_z_m"]:
        fz, nz = _naht(nt, _m(nt, "SUBTRACT", z, zn), x, p["fuge_m"], p["niet_abstand_m"], p["niet_versatz_m"],
                       p["niet_radius_m"])
        fuge = _m(nt, "MAXIMUM", fuge, fz)
        niet = _m(nt, "MAXIMUM", niet, nz)
    f2 = _mix(nt, _m(nt, "MULTIPLY", fuge, 0.7), farbe, V.hex_lin("#2C2A24"))
    f2 = _mix(nt, _m(nt, "MULTIPLY", niet, 0.35), f2, V.hex_lin("#6B6555"))
    r2 = _m(nt, "ADD", rau, _m(nt, "MULTIPLY", fuge, 0.15), clamp=True)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.003
    nt.links.new(_m(nt, "SUBTRACT", niet, fuge), bump.inputs["Height"])
    _l(nt, normal if not isinstance(normal, (float, tuple)) else None, bump.inputs["Normal"])
    _l(nt, f2, grp.inputs["Farbe"])
    _l(nt, r2, grp.inputs["Rauheit"])
    nt.links.new(bump.outputs["Normal"], grp.inputs["Normale"])
    mat["blech_2b3b"] = True
    return mat


def klappe(name, col, parent, mat_lack, mat_dunkel, mitte, groesse, seite):
    """Offene Wartungsklappe an der Triebwerksverkleidung: dunkle Oeffnung + aufgeklapptes Blech (Scharnier oben)."""
    import fz_teile as FT
    gx, gz = groesse
    x, y, z = mitte
    bm = bmesh.new()
    FT.quader(bm, (x, y + seite * 0.004, z), (gx, 0.006, gz), 1)  # Oeffnung (dunkel)
    oeffn = FT.objekt(f"{name}_Oeffnung", bm, col, [mat_lack, mat_dunkel], parent)
    bm = bmesh.new()
    FT.quader(bm, (0, seite * 0.006, -gz / 2), (gx, 0.012, gz), 0)
    kl = FT.objekt(f"{name}", bm, col, [mat_lack], parent)
    kl.location = (x, y + seite * 0.01, z + gz / 2)
    kl.rotation_euler = (seite * math.radians(cfg()["klappe"]["offen_grad"]), 0, 0)
    return oeffn, kl
