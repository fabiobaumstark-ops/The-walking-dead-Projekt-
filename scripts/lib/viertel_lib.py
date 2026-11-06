"""Gemeinsame Hilfsfunktionen fuer alle Blender-Skripte des Projekts (Blender 5.2.3 LTS).

Einbinden in einem Skript:
    import sys, os; sys.path.insert(0, os.path.join(<repo>, "scripts", "lib")); import viertel_lib as V
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Vector, noise

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIGS = os.path.join(ROOT, "scripts", "configs")
ASSETS = os.path.join(ROOT, "assets")

COLLECTIONS = ["01_Gelaende", "02_Strassen", "03_Gebaeude", "04_Fahrzeuge", "05_Militaer",
               "06_Checkpoint_Barrikaden", "07_Props_Schutt", "08_Vegetation", "09_Figuren",
               "10_Licht_Atmosphaere", "11_Kameras", "99_Blockout_Archiv"]


# ---------------------------------------------------------------- allgemein
def config(name):
    with open(os.path.join(CONFIGS, name), encoding="utf-8") as f:
        return json.load(f)


def manifest():
    with open(os.path.join(ROOT, "assets_manifest.json"), encoding="utf-8") as f:
        return json.load(f)


def hex_lin(h, a=1.0):
    """'#RRGGBB' (sRGB) -> lineares RGBA-Tupel fuer Blender."""
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], a)


def leere_szene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def collection(name, parent=None):
    """Holt/erzeugt eine Collection (auch Unter-Collections, z.B. '03_Gebaeude/Typ3')."""
    teile = name.split("/")
    eltern = parent or bpy.context.scene.collection
    col = None
    for t in teile:
        col = bpy.data.collections.get(t)
        if col is None:
            col = bpy.data.collections.new(t)
        if col.name not in [c.name for c in eltern.children]:
            eltern.children.link(col)
        eltern = col
    return col


def alle_collections():
    for n in COLLECTIONS:
        collection(n)


def objekt_aus_bmesh(name, bm, col, location=(0, 0, 0), material=None, uv=True):
    """Erzeugt ein Mesh-Objekt; Koordinaten im bmesh sind relativ zum Ursprung 'location'."""
    me = bpy.data.meshes.new(name)
    if uv:
        uv_welt(bm)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    col.objects.link(ob)
    if material is not None:
        mats = material if isinstance(material, (list, tuple)) else [material]
        for m in mats:
            me.materials.append(m)
    return ob


def uv_welt(bm, skala=1.0):
    """Box-Projektion pro Flaeche in Metern (UV 1.0 = 1 m). Material skaliert auf reale Kachelgroesse."""
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            c = lp.vert.co
            if ax == 2:
                u, v = (c.x, c.y) if n.z >= 0 else (-c.x, c.y)
            elif ax == 0:
                u, v = (c.y, c.z) if n.x >= 0 else (-c.y, c.z)
            else:
                u, v = (-c.x, c.z) if n.y >= 0 else (c.x, c.z)
            lp[uvl].uv = (u * skala, v * skala)


def box(bm, x0, y0, z0, x1, y1, z1):
    """Quader in ein bmesh einfuegen (Koordinaten relativ)."""
    vs = [bm.verts.new(p) for p in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                     (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]]
    idx = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return [bm.faces.new([vs[i] for i in q]) for q in idx]


def fase(ob, breite=0.02, segmente=2, winkel=30.0):
    """Kantenfase als Modifier (A10: 1-3 cm, 2-3 Segmente)."""
    m = ob.modifiers.new("Fase", "BEVEL")
    m.width = breite
    m.segments = segmente
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(winkel)
    m.harden_normals = False
    m.use_clamp_overlap = True
    return m


# ---------------------------------------------------------------- Gelaende-Hoehe
_GEL = None


def gelaende_cfg():
    global _GEL
    if _GEL is None:
        _GEL = config("gelaende.json")
    return _GEL


def h(x, y):
    """Gelaendehoehe (m) an Weltposition x,y. Gleiche Formel fuer Gelaende, Strassen und Gebaeude."""
    g = gelaende_cfg()
    z = g["gefaelle_x"] * x + g["gefaelle_y"] * y
    s = g["noise_skala_m"]
    z += g["noise_amp_m"] * noise.noise(Vector((x / s + 13.1, y / s + 7.7, g["seed"] * 0.37)))
    # Randbereiche: Boeschungen / Wellen ausserhalb des Hauptbereichs
    for b in g.get("boeschungen", []):
        if b["achse"] == "y":
            d = (y - b["von"]) * (1 if b["richtung"] > 0 else -1)
        else:
            d = (x - b["von"]) * (1 if b["richtung"] > 0 else -1)
        if d > 0:
            t = min(d / b["breite"], 1.0)
            t = t * t * (3 - 2 * t)
            z += b["hoehe"] * t
    return z


def h_max(pts):
    return max(h(x, y) for x, y in pts)


def h_min(pts):
    return min(h(x, y) for x, y in pts)


# ---------------------------------------------------------------- Material-Hilfen
def _sock(sockets, ident):
    for s in sockets:
        if s.identifier == ident:
            return s
    raise KeyError(ident)


def _mix_rgb(nt, fac, a, b, blend="MIX"):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    n.blend_type = blend
    n.clamp_result = True
    _link(nt, fac, _sock(n.inputs, "Factor_Float"))
    _link(nt, a, _sock(n.inputs, "A_Color"))
    _link(nt, b, _sock(n.inputs, "B_Color"))
    return _sock(n.outputs, "Result_Color")


def _link(nt, src, dst):
    if src is None:
        return
    if isinstance(src, (int, float)):
        dst.default_value = src
    elif isinstance(src, tuple):
        dst.default_value = src
    else:
        nt.links.new(src, dst)


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    _link(nt, a, n.inputs[0])
    if b is not None:
        _link(nt, b, n.inputs[1])
    return n.outputs[0]


def _maprange(nt, val, a0, a1, b0=0.0, b1=1.0, smooth=True):
    n = nt.nodes.new("ShaderNodeMapRange")
    n.interpolation_type = "SMOOTHSTEP" if smooth else "LINEAR"
    n.clamp = True
    _link(nt, val, n.inputs["Value"])
    for i, v in zip(("From Min", "From Max", "To Min", "To Max"), (a0, a1, b0, b1)):
        _link(nt, v, n.inputs[i])
    return n.outputs["Result"]


def _noise(nt, vec, scale, detail=6.0, rough=0.6, dist=0.0):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.noise_dimensions = "3D"
    _link(nt, vec, n.inputs["Vector"])
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = dist
    return n.outputs["Fac"]


def _attr(nt, name, typ="VIEW_LAYER"):
    n = nt.nodes.new("ShaderNodeAttribute")
    n.attribute_type = typ
    n.attribute_name = name
    return n.outputs["Fac"]


def verwitterung_gruppe():
    """Shader-Gruppe MAT_Verwitterung (Teil A10, Punkt 2). Durchlaeuft JEDES Material."""
    if "MAT_Verwitterung" in bpy.data.node_groups:
        return flechten_eingang(bpy.data.node_groups["MAT_Verwitterung"])
    vc = config("materialien.json")["verwitterung"]
    ng = bpy.data.node_groups.new("MAT_Verwitterung", "ShaderNodeTree")
    itf = ng.interface
    def sin(name, typ, default=None, mn=None, mx=None):
        s = itf.new_socket(name, in_out="INPUT", socket_type=typ)
        if default is not None:
            s.default_value = default
        if mn is not None:
            s.min_value, s.max_value = mn, mx
        return s
    sin("Farbe", "NodeSocketColor", (0.5, 0.5, 0.5, 1))
    sin("Rauheit", "NodeSocketFloat", 0.7, 0.0, 1.0)
    sin("Normale", "NodeSocketVector")
    sin("Kantenfarbe", "NodeSocketColor", hex_lin("#A9A398"))
    sin("Lokal", "NodeSocketFloat", 1.0, 0.0, 2.0)
    for n, t in (("Farbe", "NodeSocketColor"), ("Rauheit", "NodeSocketFloat"), ("Normale", "NodeSocketVector")):
        itf.new_socket(n, in_out="OUTPUT", socket_type=t)
    nt = ng
    gi = nt.nodes.new("NodeGroupInput")
    go = nt.nodes.new("NodeGroupOutput")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    P, N = geo.outputs["Position"], geo.outputs["Normal"]
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(N, sep.inputs[0])
    Nz = sep.outputs["Z"]
    sepP = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(P, sepP.inputs[0])

    # Master: verw_master * Lokal * (1 + Objekt-Eigenschaft verw_korrektur)
    korr = _math(nt, "ADD", _attr(nt, "verw_korrektur", "OBJECT"), 1.0)
    M = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _attr(nt, "verw_master"), gi.outputs["Lokal"]), korr, clamp=True)
    def staerke(prop):
        return _math(nt, "MULTIPLY", _attr(nt, prop), M, clamp=True)

    farbe = gi.outputs["Farbe"]
    rau = gi.outputs["Rauheit"]

    # f) Ausbleichen/Entsaettigung, Sonnenseite staerker
    az, el = math.radians(vc["sonne_azimut_grad"]), math.radians(vc["sonne_hoehe_grad"])
    sdir = (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(N, dot.inputs[0])
    dot.inputs[1].default_value = sdir
    sonne = _maprange(nt, dot.outputs["Value"], -0.2, 0.8, 0.35, 1.0)
    bleich = _math(nt, "MULTIPLY", staerke("verw_bleich"), sonne, clamp=True)
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    _link(nt, farbe, hsv.inputs["Color"])
    _link(nt, _maprange(nt, bleich, 0, 1, 1.0, 0.55, smooth=False), hsv.inputs["Saturation"])
    _link(nt, _maprange(nt, bleich, 0, 1, 1.0, 1.18, smooth=False), hsv.inputs["Value"])
    farbe = hsv.outputs["Color"]

    # d) Wasserlaufspuren: vertikal gestreckter Noise auf senkrechten Flaechen, von oben beginnend
    st = nt.nodes.new("ShaderNodeVectorMath")
    st.operation = "MULTIPLY"
    nt.links.new(P, st.inputs[0])
    st.inputs[1].default_value = (1.0, 1.0, 0.06)
    streif = _maprange(nt, _noise(nt, st.outputs[0], 3.5, 4.0, 0.5), 0.48, 0.66)
    senkrecht = _maprange(nt, _math(nt, "ABSOLUTE", Nz), 0.35, 0.1)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sepG = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sepG.inputs[0])
    oben = _maprange(nt, sepG.outputs["Z"], 0.0, 1.0, 0.35, 1.0)
    wasser = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", streif, senkrecht), oben)
    wasser = _math(nt, "MULTIPLY", wasser, _math(nt, "MULTIPLY", staerke("verw_wasser"), 1.0), clamp=True)
    dunkel = _mix_rgb(nt, 1.0, farbe, (0.5, 0.47, 0.42, 1.0), "MULTIPLY")
    farbe = _mix_rgb(nt, wasser, farbe, dunkel)

    # b) Schmutz von unten (0-80 cm ueber Gelaende) + Schmutz in Vertiefungen (AO)
    g = gelaende_cfg() if os.path.exists(os.path.join(CONFIGS, "gelaende.json")) else {"gefaelle_x": 0, "gefaelle_y": 0}
    boden = _math(nt, "ADD", _math(nt, "MULTIPLY", sepP.outputs["X"], _attr(nt, "verw_boden_gx")),
                  _math(nt, "MULTIPLY", sepP.outputs["Y"], _attr(nt, "verw_boden_gy")))
    hoehe = _math(nt, "SUBTRACT", sepP.outputs["Z"], _math(nt, "ADD", boden, _attr(nt, "verw_boden_z0")))
    hoehe = _math(nt, "ADD", hoehe, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, P, 1.8, 3.0), 0.5), 0.35))
    unten = _maprange(nt, hoehe, 0.8, 0.0)
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 4
    ao.only_local = True
    ao.inputs["Distance"].default_value = 0.25
    hohl = _maprange(nt, ao.outputs["AO"], 0.85, 0.35)
    schmutz = _math(nt, "MAXIMUM", unten, _math(nt, "MULTIPLY", hohl, 0.6))
    schmutz = _math(nt, "MULTIPLY", schmutz, _maprange(nt, _noise(nt, P, 4.0, 6.0, 0.65), 0.3, 0.7, 0.45, 1.0))
    schmutz = _math(nt, "MULTIPLY", schmutz, _math(nt, "MULTIPLY", staerke("verw_schmutz"), 1.0), clamp=True)
    farbe = _mix_rgb(nt, schmutz, farbe, hex_lin(vc["schmutzfarbe"]))
    rau = _math(nt, "ADD", rau, _math(nt, "MULTIPLY", schmutz, 0.25), clamp=True)

    # c) Kantenabnutzung: Bevel-Normale vs. Flaechennormale
    bev = nt.nodes.new("ShaderNodeBevel")
    bev.samples = 4
    bev.inputs["Radius"].default_value = 0.05
    d2 = nt.nodes.new("ShaderNodeVectorMath")
    d2.operation = "DOT_PRODUCT"
    nt.links.new(bev.outputs["Normal"], d2.inputs[0])
    nt.links.new(N, d2.inputs[1])
    kante = _maprange(nt, _math(nt, "SUBTRACT", 1.0, d2.outputs["Value"]), 0.002, 0.03)
    kante = _math(nt, "MULTIPLY", kante, _maprange(nt, _noise(nt, P, 22.0, 8.0, 0.7), 0.38, 0.6))
    kante = _math(nt, "MULTIPLY", kante, staerke("verw_kanten"), clamp=True)
    farbe = _mix_rgb(nt, kante, farbe, gi.outputs["Kantenfarbe"])

    # a) Staub von oben
    oben_n = _maprange(nt, Nz, 0.25, 0.9)
    staub = _math(nt, "MULTIPLY", oben_n, _maprange(nt, _noise(nt, P, 2.5, 8.0, 0.6), 0.38, 0.72, 0.1, 1.0))
    staub = _math(nt, "MULTIPLY", staub, _math(nt, "MULTIPLY", staerke("verw_staub"), 0.45), clamp=True)
    farbe = _mix_rgb(nt, staub, farbe, hex_lin(vc["staubfarbe"]))
    rau = _math(nt, "ADD", rau, _math(nt, "MULTIPLY", staub, 0.35), clamp=True)

    # e) Moos (Fototextur Moss002): oben auf schattigen Flaechen, in Vertiefungen, am feuchten Wandfuss
    ao2 = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao2.samples = 4
    ao2.inputs["Distance"].default_value = 1.5
    schatten = _maprange(nt, ao2.outputs["AO"], 0.95, 0.5, 0.55, 1.0)
    flecken = _maprange(nt, _noise(nt, P, 0.7, 6.0, 0.7, 0.3), 0.42, 0.58)
    feinflecken = _maprange(nt, _noise(nt, P, 6.0, 4.0, 0.6), 0.35, 0.65, 0.4, 1.0)
    oben_m = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _maprange(nt, Nz, 0.45, 0.9), schatten), flecken)
    nord = _maprange(nt, _math(nt, "MULTIPLY", sep.outputs["Y"], -1.0), -0.2, 0.7, 0.35, 1.0)  # Wand zeigt nach Norden = feucht
    fuss_m = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _maprange(nt, hoehe, 0.5, 0.05), senkrecht), _math(nt, "MULTIPLY", nord, flecken))
    hohl_m = _math(nt, "MULTIPLY", _maprange(nt, ao.outputs["AO"], 0.75, 0.3), _maprange(nt, Nz, 0.1, 0.6))
    moos = _math(nt, "MAXIMUM", _math(nt, "MAXIMUM", oben_m, _math(nt, "MULTIPLY", fuss_m, 0.8)), _math(nt, "MULTIPLY", hohl_m, 0.7))
    moos = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", moos, feinflecken), _math(nt, "MULTIPLY", staerke("verw_moos"), 1.15), clamp=True)
    eintrag_m = next(a for a in manifest()["assets"] if a["name"] == "MAT_Moos")
    mt = nt.nodes.new("ShaderNodeTexImage")
    mt.image = _bild(_karte(os.path.join(ROOT, eintrag_m["zielpfad"]), "_color"), False)
    uvm = nt.nodes.new("ShaderNodeUVMap")
    mpm = nt.nodes.new("ShaderNodeMapping")
    mpm.inputs["Scale"].default_value = (0.8, 0.8, 1)
    nt.links.new(uvm.outputs["UV"], mpm.inputs["Vector"])
    nt.links.new(mpm.outputs["Vector"], mt.inputs["Vector"])
    mhsv = nt.nodes.new("ShaderNodeHueSaturation")
    mhsv.inputs["Saturation"].default_value = 0.75
    mhsv.inputs["Value"].default_value = 0.8
    nt.links.new(mt.outputs["Color"], mhsv.inputs["Color"])
    mfarbe = _mix_rgb(nt, _noise(nt, P, 3.0, 4.0), mhsv.outputs["Color"], hex_lin("#5A5A2E"), "MULTIPLY")
    mfarbe = _mix_rgb(nt, 0.5, mhsv.outputs["Color"], mfarbe)
    farbe = _mix_rgb(nt, moos, farbe, mfarbe)
    rau = _math(nt, "MAXIMUM", rau, _math(nt, "MULTIPLY", moos, 0.95))

    # g) Flechten: kleine hellgrau-gruene Flecken auf Stein/Beton (Lokal steuert pro Material)
    fl = _maprange(nt, _noise(nt, P, 7.5, 3.0, 0.5, 0.2), 0.62, 0.68)
    fl = _math(nt, "MULTIPLY", fl, _maprange(nt, _noise(nt, P, 0.6, 2.0), 0.45, 0.6))
    fl = _math(nt, "MULTIPLY", fl, _math(nt, "MULTIPLY", _attr(nt, "verw_flechten"), M), clamp=True)
    farbe = _mix_rgb(nt, _math(nt, "MULTIPLY", fl, 0.75), farbe, hex_lin("#A3A88E"))

    # h) Feuchte am Wandfuss: dunkler, unregelmaessiger Rand (zusaetzlich zum Schmutz)
    feucht = _math(nt, "MULTIPLY", _maprange(nt, _math(nt, "ADD", hoehe, _math(nt, "MULTIPLY", _noise(nt, P, 1.2, 4.0), 0.3)), 0.75, 0.25), senkrecht)
    feucht = _math(nt, "MULTIPLY", feucht, _math(nt, "MULTIPLY", staerke("verw_schmutz"), 0.55), clamp=True)
    farbe = _mix_rgb(nt, feucht, farbe, _mix_rgb(nt, 1.0, farbe, (0.62, 0.6, 0.55, 1), "MULTIPLY"))

    nt.links.new(farbe, go.inputs["Farbe"])
    nt.links.new(rau, go.inputs["Rauheit"])
    nt.links.new(gi.outputs["Normale"], go.inputs["Normale"])
    return flechten_eingang(ng)


def flechten_eingang(ng):
    """Eingang 'Flechten' (Standard 1.0 = unveraendert) fuer MAT_Verwitterung nachruesten: schwaecht die Flechten-Ebene
    pro Material ab (z. B. Militaerlack). Ruestet auch Gruppen aelterer .blend-Dateien nach."""
    if "Flechten" in ng.interface.items_tree:
        return ng
    s = ng.interface.new_socket("Flechten", in_out="INPUT", socket_type="NodeSocketFloat")
    s.default_value, s.min_value, s.max_value = 1.0, 0.0, 2.0
    gi = next(n for n in ng.nodes if n.type == "GROUP_INPUT")
    ziel = hex_lin("#A3A88E")
    for n in ng.nodes:
        if n.bl_idname != "ShaderNodeMix" or n.data_type != "RGBA":
            continue
        b = _sock(n.inputs, "B_Color")
        if b.is_linked or any(abs(b.default_value[i] - ziel[i]) > 1e-4 for i in range(3)):
            continue
        f = _sock(n.inputs, "Factor_Float")
        quelle = f.links[0].from_socket
        mul = _math(ng, "MULTIPLY", quelle, gi.outputs["Flechten"], clamp=True)
        ng.links.new(mul, f)
        break
    return ng


def regler_setzen(sc=None):
    """Zentrale Verwitterungs-Regler als Szenen-Eigenschaften anlegen (falls noch nicht da)."""
    sc = sc or bpy.context.scene
    vc = config("materialien.json")["verwitterung"]
    for k, v in vc.items():
        if k.startswith("verw_") and k not in sc.keys():
            sc[k] = float(v)
    g = gelaende_cfg() if os.path.exists(os.path.join(CONFIGS, "gelaende.json")) else None
    if "verw_boden_gx" not in sc.keys():
        sc["verw_boden_gx"] = float(g["gefaelle_x"]) if g else 0.0
        sc["verw_boden_gy"] = float(g["gefaelle_y"]) if g else 0.0
        sc["verw_boden_z0"] = 0.0


def _karte(ordner, *muster):
    for f in sorted(os.listdir(ordner)):
        low = f.lower()
        if any(m in low for m in muster) and not low.endswith(".zip"):
            return os.path.join(ordner, f)
    return None


def _bild(pfad, nicht_farbe):
    img = bpy.data.images.load(pfad, check_existing=True)
    if nicht_farbe:
        img.colorspace_settings.name = "Non-Color"
    return img


def material(name):
    """Baut (oder holt) ein MAT_ aus der Bibliothek (scripts/configs/materialien.json)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    cfg = config("materialien.json")
    std = dict(cfg["standard"])
    eigen = cfg["materialien"].get(name) or cfg.get("abgeleitet", {}).get(name, {})
    basis = eigen.get("basis")
    if basis:
        std.update(cfg["materialien"].get(basis, {}))
    std.update(eigen)
    eintrag = next(a for a in manifest()["assets"] if a["name"] == (basis or name))
    ordner = os.path.join(ROOT, eintrag["zielpfad"])
    groesse = std.get("groesse_m") or eintrag.get("masse_m") or [2, 2]

    m = bpy.data.materials.new(name)
    m.use_fake_user = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])

    uv = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / groesse[0], 1.0 / groesse[1], 1.0)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    vec = mp.outputs["Vector"]

    anti = std.get("antitiling")
    if anti:  # zweite, gedrehte und verschobene Abtastung, gemischt ueber grossen Noise (keine Kachelwiederholung)
        mp2 = nt.nodes.new("ShaderNodeMapping")
        mp2.inputs["Scale"].default_value = (0.93 / groesse[0], 0.93 / groesse[1], 1.0)
        mp2.inputs["Rotation"].default_value = (0, 0, 0.73)
        mp2.inputs["Location"].default_value = (0.37, 0.61, 0)
        nt.links.new(uv.outputs["UV"], mp2.inputs["Vector"])
        geo0 = nt.nodes.new("ShaderNodeNewGeometry")
        maske = _maprange(nt, _noise(nt, geo0.outputs["Position"], 0.09, 3.0, 0.55), 0.42, 0.58)

    def tex(pfad, nicht_farbe):
        if not pfad:
            return None
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _bild(pfad, nicht_farbe)
        t.interpolation = "Cubic" if nicht_farbe else "Linear"
        nt.links.new(vec, t.inputs["Vector"])
        if not anti:
            return t.outputs["Color"]
        t2 = nt.nodes.new("ShaderNodeTexImage")
        t2.image = t.image
        t2.interpolation = t.interpolation
        nt.links.new(mp2.outputs["Vector"], t2.inputs["Vector"])
        return _mix_rgb(nt, maske, t.outputs["Color"], t2.outputs["Color"])

    col = tex(_karte(ordner, "_diff_", "_color", "_albedo_"), False)
    rough = tex(_karte(ordner, "_rough_", "_roughness"), True)
    nor = tex(_karte(ordner, "_nor_gl_", "_normalgl"), True)
    disp = tex(_karte(ordner, "_disp_", "_displacement"), True)

    # Ebene 1+2: Fototextur, Farbanpassung an Look-Bible, grossflaechige Variation
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.name = "HSV_Basis"
    for i, k in enumerate(("Hue", "Saturation", "Value")):
        hsv.inputs[k].default_value = std["hsv"][i]
    _link(nt, col, hsv.inputs["Color"])
    hsv_out = hsv.outputs["Color"]
    if std.get("farbe"):  # Umfaerben: Helligkeit der Fototextur x Zielfarbe (Lack, Schilder, Planen ...)
        hsv.inputs["Saturation"].default_value = 0.0
        hsv.inputs["Value"].default_value = std.get("farbe_gain", 2.2)
        hsv_out = _mix_rgb(nt, 1.0, hsv.outputs["Color"], hex_lin(std["farbe"]), "MULTIPLY")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    var = _maprange(nt, _noise(nt, geo.outputs["Position"], 0.12, 3.0, 0.5), 0.3, 0.7,
                    1.0 - std["variation"], 1.0 + std["variation"])
    farbe = hsv_out
    vmul = nt.nodes.new("ShaderNodeMix")
    vmul.data_type = "RGBA"
    vmul.blend_type = "MULTIPLY"
    _sock(vmul.inputs, "Factor_Float").default_value = 1.0
    nt.links.new(farbe, _sock(vmul.inputs, "A_Color"))
    cmb = nt.nodes.new("ShaderNodeCombineColor")
    for i in range(3):
        nt.links.new(var, cmb.inputs[i])
    nt.links.new(cmb.outputs[0], _sock(vmul.inputs, "B_Color"))
    farbe = _sock(vmul.outputs, "Result_Color")

    # Fugen fuer Gehweg-Platten (1,5 m Raster)
    if std.get("fugen_m"):
        fug = _fugen(nt, geo.outputs["Position"], std["fugen_m"])
        farbe = _mix_rgb(nt, _math(nt, "MULTIPLY", fug, 0.85), farbe, hex_lin("#3A3631"))

    # Ebene 3: Rauheitsvariation
    rau = _maprange(nt, rough if rough else 0.7, 0.0, 1.0, std["rauheit_min"], std["rauheit_max"], smooth=False)
    rau = _math(nt, "MULTIPLY", rau, _maprange(nt, _noise(nt, geo.outputs["Position"], 0.5, 2.0), 0.3, 0.7, 0.9, 1.1),
                clamp=True)

    normal = None
    if nor:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = std["normal"]
        nt.links.new(nor, nm.inputs["Color"])
        normal = nm.outputs["Normal"]
    if disp:
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = std["bump"]
        bump.inputs["Distance"].default_value = 0.01
        nt.links.new(disp, bump.inputs["Height"])
        if normal:
            nt.links.new(normal, bump.inputs["Normal"])
        normal = bump.outputs["Normal"]
    if normal is None:
        normal = geo.outputs["Normal"]

    # Ebene 4: MAT_Verwitterung
    grp = nt.nodes.new("ShaderNodeGroup")
    grp.node_tree = verwitterung_gruppe()
    grp.label = "MAT_Verwitterung"
    nt.links.new(farbe, grp.inputs["Farbe"])
    _link(nt, rau, grp.inputs["Rauheit"])
    nt.links.new(normal, grp.inputs["Normale"])
    grp.inputs["Kantenfarbe"].default_value = hex_lin(std["kantenfarbe"])
    grp.inputs["Lokal"].default_value = std["lokal"]
    nt.links.new(grp.outputs["Farbe"], bsdf.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], bsdf.inputs["Roughness"])
    nt.links.new(grp.outputs["Normale"], bsdf.inputs["Normal"])
    m["textur_quelle"] = eintrag["seite"]
    return m


def _fugen(nt, P, raster):
    """Maske fuer Plattenfugen im Raster (m) in XY."""
    res = []
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(P, sep.inputs[0])
    for ach in ("X", "Y"):
        w = _math(nt, "PINGPONG", sep.outputs[ach], raster / 2.0)  # 0 an Fuge
        res.append(_maprange(nt, w, 0.012, 0.004))
    return _math(nt, "MAXIMUM", res[0], res[1])


def bibliothek():
    """Alle Bibliotheks-Materialien erzeugen (mit Fake-User, damit sie in der .blend bleiben)."""
    cfg = config("materialien.json")
    out = {n: material(n) for n in cfg["materialien"]}
    out.update({n: material(n) for n in cfg.get("abgeleitet", {}) if not n.startswith("_")})
    return out


def material_einfaerben(mat, hsv=None):
    """Heruntergeladenes Material an Look-Bible angleichen + MAT_Verwitterung einschleifen (A10, Punkt 3)."""
    if mat is None or mat.get("verwittert"):
        return mat
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    hsv = hsv or config("materialien.json")["verwitterung"]["heruntergeladen_hsv"]
    if bsdf is None:
        return _einfaerben_gruppe(mat, hsv)
    def quelle(inp):
        return inp.links[0].from_socket if inp.is_linked else None
    c_src, r_src, n_src = quelle(bsdf.inputs["Base Color"]), quelle(bsdf.inputs["Roughness"]), quelle(bsdf.inputs["Normal"])
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    for i, k in enumerate(("Hue", "Saturation", "Value")):
        hs.inputs[k].default_value = hsv[i]
    if c_src:
        nt.links.new(c_src, hs.inputs["Color"])
    else:
        hs.inputs["Color"].default_value = bsdf.inputs["Base Color"].default_value
    grp = nt.nodes.new("ShaderNodeGroup")
    grp.node_tree = verwitterung_gruppe()
    nt.links.new(hs.outputs["Color"], grp.inputs["Farbe"])
    if r_src:
        nt.links.new(r_src, grp.inputs["Rauheit"])
    else:
        grp.inputs["Rauheit"].default_value = max(bsdf.inputs["Roughness"].default_value, 0.35)
    if n_src:
        nt.links.new(n_src, grp.inputs["Normale"])
    else:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        nt.links.new(geo.outputs["Normal"], grp.inputs["Normale"])
    nt.links.new(grp.outputs["Farbe"], bsdf.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], bsdf.inputs["Roughness"])
    nt.links.new(grp.outputs["Normale"], bsdf.inputs["Normal"])
    mat["verwittert"] = True
    return mat


def _einfaerben_gruppe(mat, hsv):
    """Fallback fuer Materialien ohne Principled BSDF (z. B. Poly-Haven-Pflanzen mit eigener Shader-Gruppe):
    Farbe und Rauheit, die in die Shader-Gruppe laufen, durch HSV + MAT_Verwitterung leiten."""
    nt = mat.node_tree
    farb_namen = ("Base Color", "Color", "Diffuse", "Diffuse Dead", "Albedo")
    rau_namen = ("Roughness", "Rough")
    ziele = [n for n in nt.nodes if n.type == "GROUP" and n.node_tree and n.node_tree.name != "MAT_Verwitterung"
             and any(s.name in farb_namen for s in n.inputs)]
    if not ziele:
        return mat
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    for z in ziele:
        rau_in = next((s for s in z.inputs if s.name in rau_namen), None)
        rau_src = rau_in.links[0].from_socket if rau_in is not None and rau_in.is_linked else None
        for s in [s for s in z.inputs if s.name in farb_namen]:
            if not s.is_linked:
                continue
            hs = nt.nodes.new("ShaderNodeHueSaturation")
            for i, k in enumerate(("Hue", "Saturation", "Value")):
                hs.inputs[k].default_value = hsv[i]
            nt.links.new(s.links[0].from_socket, hs.inputs["Color"])
            grp = nt.nodes.new("ShaderNodeGroup")
            grp.node_tree = verwitterung_gruppe()
            nt.links.new(hs.outputs["Color"], grp.inputs["Farbe"])
            if rau_src is not None:
                nt.links.new(rau_src, grp.inputs["Rauheit"])
            nt.links.new(geo.outputs["Normal"], grp.inputs["Normale"])
            nt.links.new(grp.outputs["Farbe"], s)
            if rau_in is not None and rau_src is not None and s.name in ("Base Color", "Color", "Diffuse"):
                nt.links.new(grp.outputs["Rauheit"], rau_in)
    mat["verwittert"] = True
    return mat


def modell_laden(asset_id, col):
    """Haengt alle Objekte eines Poly-Haven-Modells an (assets/models/<id>/<id>_2k.blend)."""
    pfad = os.path.join(ASSETS, "models", asset_id, f"{asset_id}_2k.blend")
    with bpy.data.libraries.load(pfad, link=False) as (src, dst):
        dst.objects = list(src.objects)
    obs = []
    for ob in dst.objects:
        if ob is None or ob.type not in {"MESH", "EMPTY"}:
            continue
        col.objects.link(ob)
        obs.append(ob)
        if ob.type == "MESH":
            for slot in ob.material_slots:
                material_einfaerben(slot.material)
    return obs


def hdri_welt(pfad, staerke=1.0, rotation_grad=0.0):
    w = bpy.data.worlds.new("LGT_Welt_HDRI")
    bpy.context.scene.world = w
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(pfad, check_existing=True)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rotation_grad))
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = staerke
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return w


def sonne(azimut_grad, hoehe_grad, staerke=3.0, kelvin=4800, winkel_grad=2.0, col=None):
    d = bpy.data.lights.new("LGT_Sonne", "SUN")
    d.energy = staerke
    d.angle = math.radians(winkel_grad)
    d.use_temperature = True
    d.temperature = kelvin
    ob = bpy.data.objects.new("LGT_Sonne", d)
    (col or bpy.context.scene.collection).objects.link(ob)
    az, el = math.radians(azimut_grad), math.radians(hoehe_grad)
    # Licht zeigt entlang -Z des Objekts: Richtung ZUR Sonne = (sin az cos el, cos az cos el, sin el)
    to_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    ob.rotation_euler = to_sun.to_track_quat("Z", "Y").to_euler()
    return ob


def vorschau_render(sc, pfad, samples=48, breite=960, hoehe=540):
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6
    sc.cycles.texture_limit_render = "2048"
    sc.render.resolution_x, sc.render.resolution_y = breite, hoehe
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = pfad
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- HDRI-Ausrichtung
def hdri_sonne(img):
    """Hellster Punkt eines Equirect-HDRIs -> (phi_bild, hoehe) in Radiant (phi von +X gegen den Uhrzeigersinn)."""
    import numpy as np
    w, hh = img.size
    px = np.empty(w * hh * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    lum = px.reshape(hh, w, 4)[:, :, :3].sum(axis=2)
    row, colm = np.unravel_index(int(np.argmax(lum)), lum.shape)
    u, v = (colm + 0.5) / w, (row + 0.5) / hh
    return math.pi - 2 * math.pi * u, math.pi * (v - 0.5)


def hdri_rotation_fuer(img, ziel_azimut_grad):
    """Z-Rotation (Grad) fuer den Mapping-Node, damit die HDRI-Sonne aus ziel_azimut kommt (Kompass, N=+Y)."""
    phi_img, el = hdri_sonne(img)
    phi_ziel = math.radians(90.0 - ziel_azimut_grad)
    return math.degrees(phi_img - phi_ziel), math.degrees(el)


# ---------------------------------------------------------------- Blockout
BLOCKOUT_GRAU = {
    "Fahrbahn": "#3C3C3B", "Brache": "#6A6658", "Bordstein": "#9A9892", "Gehweg": "#8E8C86",
    "Gruenstreifen": "#5E6250", "Grundstueck": "#6E6B60", "Gebaeude": "#A3A19B", "Dach": "#74726D",
    "Beton": "#8A877F", "Holz": "#8B8478", "Metall": "#6E6E6E", "Glas": "#4A5055", "Schutt": "#7E7A72",
    "Baum": "#4F5545", "Hintergrund": "#8A8E8C", "Markierung": "#B0AEA6",
}


def blockout_mat(zone):
    """Graues Blockout-Material (Phase 1). Wird in Phase 2-4 durch MAT_-Bibliothek ersetzt."""
    name = f"MAT_Blockout_{zone}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_fake_user = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = hex_lin(BLOCKOUT_GRAU[zone])
    b.inputs["Roughness"].default_value = 0.85
    m.diffuse_color = hex_lin(BLOCKOUT_GRAU[zone])
    return m


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)



# ---------------------------------------------------------------- Phase 2: Spezial-Materialien
def _grunge(nt, asset_mat, skala=1.0):
    """Graustufen-Maske aus einer Fototextur (Rauheitskarte) – Fotobasis fuer Staub, Abplatzer usw."""
    eintrag = next(a for a in manifest()["assets"] if a["name"] == asset_mat)
    pfad = _karte(os.path.join(ROOT, eintrag["zielpfad"]), "_rough_", "_roughness")
    uv = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (skala, skala, 1)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = _bild(pfad, True)
    nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    return t.outputs["Color"]


def _verw_anschluss(nt, farbe, rau, normal, lokal=1.0, kante="#A9A398"):
    grp = nt.nodes.new("ShaderNodeGroup")
    grp.node_tree = verwitterung_gruppe()
    _link(nt, farbe, grp.inputs["Farbe"])
    _link(nt, rau, grp.inputs["Rauheit"])
    if normal is None:
        normal = nt.nodes.new("ShaderNodeNewGeometry").outputs["Normal"]
    nt.links.new(normal, grp.inputs["Normale"])
    grp.inputs["Kantenfarbe"].default_value = hex_lin(kante)
    grp.inputs["Lokal"].default_value = lokal
    return grp


def _neues_mat(name):
    m = bpy.data.materials.new(name)
    m.use_fake_user = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return m, nt, bsdf


def mat_glas(name="MAT_Glas_Staubig", staub=1.0):
    """Fensterglas (Thin Wall), Staub/Wasserflecken aus Fotomaske dirty_concrete, laeuft durch MAT_Verwitterung."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = _neues_mat(name)
    g = _grunge(nt, "MAT_Beton_Grob", 0.7)
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Thin Wall"].default_value = True
    b.inputs["IOR"].default_value = 1.5
    rau = _maprange(nt, g, 0.2, 0.9, 0.04, 0.12 + 0.3 * staub, smooth=False)
    farbe = _mix_rgb(nt, _maprange(nt, g, 0.3, 0.9, 0.0, 0.35 * staub), hex_lin("#D9DED9"), hex_lin("#8F8878"))
    grp = _verw_anschluss(nt, farbe, rau, None, lokal=0.6)
    nt.links.new(grp.outputs["Farbe"], b.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], b.inputs["Roughness"])
    nt.links.new(grp.outputs["Normale"], b.inputs["Normal"])
    return m


def mat_wasser(name="MAT_Wasser_Pfuetze", oel=False):
    """Pfuetzenwasser: Rauheit 0.0-0.05 (einziges Material mit ~0), optional Oel-Schlieren (Thin Film)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = _neues_mat(name)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    b.inputs["Base Color"].default_value = hex_lin("#1E1B17")
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["IOR"].default_value = 1.33
    b.inputs["Transmission Weight"].default_value = 0.0
    b.inputs["Specular IOR Level"].default_value = 0.5
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    nt.links.new(_noise(nt, geo.outputs["Position"], 6.0, 2.0), bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    if oel:
        dicke = _maprange(nt, _noise(nt, geo.outputs["Position"], 1.2, 3.0, 0.6, 2.0), 0.35, 0.75, 0.0, 650.0)
        nt.links.new(dicke, b.inputs["Thin Film Thickness"])
        b.inputs["Thin Film IOR"].default_value = 1.45
    return m


def mat_farbe(name, hexfarbe, abplatzer=0.5, unterlage="MAT_Asphalt_Rissig", rau=0.6, lokal=0.8):
    """Farbschicht (Fahrbahnmarkierung, Graffiti, Schilderlack) mit Abplatzern aus Fotomaske (Alpha)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = _neues_mat(name)
    g = _grunge(nt, unterlage, 0.5)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    wert = _math(nt, "ADD", _math(nt, "MULTIPLY", g, 0.6), _math(nt, "MULTIPLY", _noise(nt, geo.outputs["Position"], 1.4, 4.0), 0.4))
    grenze = 0.78 - 0.4 * abplatzer  # abplatzer 0 = fast intakt, 1 = fast ganz weg
    alpha = _maprange(nt, wert, grenze - 0.03, grenze + 0.03, 1.0, 0.0)
    farbe = _mix_rgb(nt, _maprange(nt, g, 0.2, 0.9, 0.0, 0.45), hex_lin(hexfarbe), hex_lin("#8A8478"))
    grp = _verw_anschluss(nt, farbe, rau, None, lokal=lokal)
    nt.links.new(grp.outputs["Farbe"], b.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], b.inputs["Roughness"])
    nt.links.new(grp.outputs["Normale"], b.inputs["Normal"])
    nt.links.new(alpha, b.inputs["Alpha"])
    return m


def mat_russ(name="MAT_Russ"):
    """Russfahne ueber Fenstern: nach oben ausfransend (Alpha aus Gradient x Noise x Fotomaske). UV: v=0 unten, v=1 oben."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = _neues_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs[0])  # Decal-UV 0..1 (u quer, v nach oben)
    g = _grunge(nt, "MAT_Beton_Grob", 0.4)
    rand = _math(nt, "MULTIPLY", _maprange(nt, sep.outputs["X"], 0.0, 0.25), _maprange(nt, sep.outputs["X"], 1.0, 0.75))
    hoch = _maprange(nt, _math(nt, "ADD", sep.outputs["Y"], _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", _noise(nt, tc.outputs["UV"], 4.0, 6.0), 0.5), 0.6)), 1.0, 0.05)
    alpha = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", hoch, rand), _maprange(nt, g, 0.1, 0.8, 0.55, 1.0), clamp=True)
    b.inputs["Base Color"].default_value = hex_lin("#141210")
    b.inputs["Roughness"].default_value = 0.95
    nt.links.new(alpha, b.inputs["Alpha"])
    return m


def mat_schindeln(name="MAT_Dachschindeln"):
    """Asphaltschindeln (selbst gebaut, keine CC0-Fototextur gefunden): Fotobasis tarred_gravel + Laschenraster."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = _neues_mat(name)
    eintrag = next(a for a in manifest()["assets"] if a["name"] == "MAT_Asphalt_Geflickt")
    ordner = os.path.join(ROOT, eintrag["zielpfad"])
    uv = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.9, 0.9, 1)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = _bild(_karte(ordner, "_diff_"), False)
    nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    br = nt.nodes.new("ShaderNodeTexBrick")  # Laschen 1,0 x 0,14 m sichtbar, versetzt
    br.offset = 0.5
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Brick Width"].default_value = 0.33
    br.inputs["Row Height"].default_value = 0.14
    br.inputs["Mortar Size"].default_value = 0.008
    br.inputs["Color1"].default_value = (1, 1, 1, 1)
    br.inputs["Color2"].default_value = (0.75, 0.75, 0.75, 1)
    br.inputs["Mortar"].default_value = (0.25, 0.25, 0.25, 1)
    nt.links.new(uv.outputs["UV"], br.inputs["Vector"])
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = 0.35
    hsv.inputs["Value"].default_value = 0.85
    nt.links.new(t.outputs["Color"], hsv.inputs["Color"])
    farbe = _mix_rgb(nt, 1.0, hsv.outputs["Color"], br.outputs["Color"], "MULTIPLY")
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    nt.links.new(br.outputs["Fac"], bump.inputs["Height"])
    grp = _verw_anschluss(nt, farbe, 0.85, bump.outputs["Normal"], lokal=1.0, kante="#6A665E")
    nt.links.new(grp.outputs["Farbe"], b.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], b.inputs["Roughness"])
    nt.links.new(grp.outputs["Normale"], b.inputs["Normal"])
    return m


# ---------------------------------------------------------------- Phase 2: Instanzen (A9)
def gn_instanzen(quelle_col):
    """GN-Gruppe GN_Instanzen_<Collection>: setzt Instanzen der Collection auf die Punkte eines Mesh (Attribute rot, skal, idx)."""
    name = f"GN_Instanzen_{quelle_col.name}"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi, go = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
    m2p = ng.nodes.new("GeometryNodeMeshToPoints")
    ci = ng.nodes.new("GeometryNodeCollectionInfo")
    ci.transform_space = "ORIGINAL"
    ci.inputs["Collection"].default_value = quelle_col
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    iop = ng.nodes.new("GeometryNodeInstanceOnPoints")
    iop.inputs["Pick Instance"].default_value = True
    def attr(name, typ):
        a = ng.nodes.new("GeometryNodeInputNamedAttribute")
        a.data_type = typ
        a.inputs["Name"].default_value = name
        return a.outputs["Attribute"]
    ng.links.new(gi.outputs["Geometry"], m2p.inputs["Mesh"])
    ng.links.new(m2p.outputs["Points"], iop.inputs["Points"])
    ng.links.new(ci.outputs[0], iop.inputs["Instance"])
    ng.links.new(attr("idx", "INT"), iop.inputs["Instance Index"])
    e2r = ng.nodes.new("FunctionNodeEulerToRotation")
    ng.links.new(attr("rot", "FLOAT_VECTOR"), e2r.inputs[0])
    ng.links.new(e2r.outputs[0], iop.inputs["Rotation"])
    ng.links.new(attr("skal", "FLOAT_VECTOR"), iop.inputs["Scale"])
    ng.links.new(iop.outputs["Instances"], go.inputs["Geometry"])
    return ng


def prototypen(name):
    """Collection fuer Vorlage-Objekte (aus der View-Layer ausgeschlossen, nur als Instanzquelle)."""
    col = collection(f"00_Prototypen/PROTO_{name}")
    def _excl(lc):
        for c in lc.children:
            if c.name == "00_Prototypen":
                c.exclude = True
            _excl(c)
    _excl(bpy.context.view_layer.layer_collection)
    return col


def instanzen(name, punkte, quelle_col, ziel_col):
    """punkte: Liste (pos, rot_euler, skal, idx). Erzeugt ein Punkt-Mesh mit GN_Instanzen_Punkte."""
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(punkte))
    me.vertices.foreach_set("co", [c for p in punkte for c in p[0]])
    for an, typ, k in (("rot", "FLOAT_VECTOR", 1), ("skal", "FLOAT_VECTOR", 2), ("idx", "INT", 3)):
        a = me.attributes.new(an, typ, "POINT")
        if typ == "INT":
            a.data.foreach_set("value", [int(p[k]) for p in punkte])
        else:
            a.data.foreach_set("vector", [c for p in punkte for c in p[k]])
    ob = bpy.data.objects.new(name, me)
    ziel_col.objects.link(ob)
    mod = ob.modifiers.new("GN_Instanzen", "NODES")
    mod.node_group = gn_instanzen(quelle_col)
    return ob



def mat_variante(basis, idx, tint=None):
    """Farbvariante eines Bibliotheks-Materials (Fassaden: keine zwei Nachbarn gleich). idx 0 = Original."""
    m0 = material(basis)
    if idx == 0 and not tint:
        return m0
    name = f"{basis}_V{idx}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = m0.copy()
    m.name = name
    m.use_fake_user = True
    nt = m.node_tree
    hsv = nt.nodes["HSV_Basis"]
    dh = [0, 0.012, -0.012, 0.025][idx % 4]
    ds = [1, 0.85, 1.1, 0.75][idx % 4]
    dv = [1, 0.9, 1.07, 0.82][idx % 4]
    hsv.inputs["Hue"].default_value = 0.5 + dh
    hsv.inputs["Saturation"].default_value *= ds
    hsv.inputs["Value"].default_value *= dv
    if tint:
        ziel = hsv.outputs["Color"].links[0].to_socket
        mx = nt.nodes.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        _sock(mx.inputs, "Factor_Float").default_value = 1.0
        nt.links.new(hsv.outputs["Color"], _sock(mx.inputs, "A_Color"))
        _sock(mx.inputs, "B_Color").default_value = hex_lin(tint)
        nt.links.new(_sock(mx.outputs, "Result_Color"), ziel)
    return m


def text_mesh(bm, text, groesse, matrix, mat, extrude=0.01, font=None, aufloesung=None):
    """Text als Mesh in ein bmesh einfuegen (lokal: x = Leserichtung, y = Hoehe, z = Dicke).
    aufloesung: Kurven-Aufloesung der Buchstaben (kleiner = weniger Punkte, z. B. 2 fuer kleine Schrift)."""
    cu = bpy.data.curves.new("tmp_txt", "FONT")
    cu.body = text
    cu.size = groesse
    cu.extrude = extrude
    if aufloesung:
        cu.resolution_u = aufloesung
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    if font:
        cu.font = font
    ob = bpy.data.objects.new("tmp_txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    n0 = len(bm.faces)
    tmp = bmesh.new()
    tmp.from_mesh(me)
    bmesh.ops.transform(tmp, matrix=matrix, verts=tmp.verts)
    me2 = bpy.data.meshes.new("tmp_txt2")
    tmp.to_mesh(me2)
    tmp.free()
    bm.from_mesh(me2)
    ob.evaluated_get(dg).to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me2)
    bm.faces.ensure_lookup_table()
    for f in list(bm.faces)[n0:]:
        f.material_index = mat



def mat_maschendraht(name="MAT_Maschendraht"):
    """Maschendrahtzaun: verzinkter Draht (Fotobasis rusty_metal_02), Rautenmuster 5 cm als Alpha."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = _neues_mat(name)
    uv = nt.nodes.new("ShaderNodeUVMap")
    alph = []
    for rot in (0.785, -0.785):
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, rot)
        nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
        wv = nt.nodes.new("ShaderNodeTexWave")
        wv.wave_profile = "SAW"
        wv.inputs["Scale"].default_value = 1.0 / 0.05 / 6.283
        wv.inputs["Distortion"].default_value = 0.0
        nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
        alph.append(_maprange(nt, wv.outputs["Fac"], 0.86, 0.93, 0.0, 1.0))
    alpha = _math(nt, "MAXIMUM", alph[0], alph[1])
    eintrag = next(a for a in manifest()["assets"] if a["name"] == "MAT_Rost_Hell")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = _bild(_karte(os.path.join(ROOT, eintrag["zielpfad"]), "_diff_"), False)
    nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    b.inputs["Metallic"].default_value = 0.6
    grp = _verw_anschluss(nt, t.outputs["Color"], 0.55, None, lokal=0.7)
    nt.links.new(grp.outputs["Farbe"], b.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], b.inputs["Roughness"])
    nt.links.new(alpha, b.inputs["Alpha"])
    return m



def mat_fahne(name, hexfarbe, staerke=0.7, unten_stark=False):
    """Decal: Schmutz-/Rostfahne (oben stark, nach unten auslaufend, streifig) bzw. Ausbluehung (unten stark).
    Decal-UV: u quer 0..1, v 0 unten .. 1 oben. Fotobasis: Rauheitskarte dirty_concrete."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = _neues_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    g = _grunge(nt, "MAT_Beton_Grob", 0.6)
    st = nt.nodes.new("ShaderNodeVectorMath")
    st.operation = "MULTIPLY"
    nt.links.new(tc.outputs["UV"], st.inputs[0])
    st.inputs[1].default_value = (9.0, 0.6, 1.0)
    streif = _maprange(nt, _noise(nt, st.outputs[0], 1.0, 3.0, 0.5), 0.35, 0.7, 0.2, 1.0)
    v = sep.outputs["Y"]
    verlauf = _maprange(nt, v, 0.6, 0.0) if unten_stark else _maprange(nt, v, 0.0, 0.95)
    rand = _math(nt, "MULTIPLY", _maprange(nt, sep.outputs["X"], 0.0, 0.3), _maprange(nt, sep.outputs["X"], 1.0, 0.7))
    alpha = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", verlauf, rand), _math(nt, "MULTIPLY", streif if not unten_stark else _maprange(nt, g, 0.2, 0.8), staerke), clamp=True)
    alpha = _math(nt, "MULTIPLY", alpha, _maprange(nt, g, 0.1, 0.9, 0.6, 1.0))
    b.inputs["Base Color"].default_value = hex_lin(hexfarbe)
    b.inputs["Roughness"].default_value = 0.9
    nt.links.new(alpha, b.inputs["Alpha"])
    return m
