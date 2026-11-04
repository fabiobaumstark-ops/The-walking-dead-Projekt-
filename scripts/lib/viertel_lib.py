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
        return bpy.data.node_groups["MAT_Verwitterung"]
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
    staub = _math(nt, "MULTIPLY", staub, _math(nt, "MULTIPLY", staerke("verw_staub"), 0.55), clamp=True)
    farbe = _mix_rgb(nt, staub, farbe, hex_lin(vc["staubfarbe"]))
    rau = _math(nt, "ADD", rau, _math(nt, "MULTIPLY", staub, 0.35), clamp=True)

    # e) Moos auf waagerechten, schattigen Flaechen (AO als Schatten-Naeherung)
    ao2 = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao2.samples = 4
    ao2.inputs["Distance"].default_value = 1.5
    schatten = _maprange(nt, ao2.outputs["AO"], 0.95, 0.55, 0.45, 1.0)
    flecken = _maprange(nt, _noise(nt, P, 0.9, 6.0, 0.7, 0.3), 0.48, 0.62)
    moos = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", _maprange(nt, Nz, 0.55, 0.95), schatten), flecken)
    moos = _math(nt, "MULTIPLY", moos, _math(nt, "MULTIPLY", staerke("verw_moos"), 0.9), clamp=True)
    mfarbe = _mix_rgb(nt, _noise(nt, P, 9.0, 4.0), hex_lin(vc["moosfarbe"]), hex_lin("#3B4720"))
    farbe = _mix_rgb(nt, moos, farbe, mfarbe)
    rau = _math(nt, "MAXIMUM", rau, _math(nt, "MULTIPLY", moos, 0.95))

    nt.links.new(farbe, go.inputs["Farbe"])
    nt.links.new(rau, go.inputs["Rauheit"])
    nt.links.new(gi.outputs["Normale"], go.inputs["Normale"])
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
    std.update(cfg["materialien"].get(name, {}))
    eintrag = next(a for a in manifest()["assets"] if a["name"] == name)
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

    def tex(pfad, nicht_farbe):
        if not pfad:
            return None
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _bild(pfad, nicht_farbe)
        t.interpolation = "Cubic" if nicht_farbe else "Linear"
        nt.links.new(vec, t.inputs["Vector"])
        return t.outputs["Color"]

    col = tex(_karte(ordner, "_diff_", "_color"), False)
    rough = tex(_karte(ordner, "_rough_", "_roughness"), True)
    nor = tex(_karte(ordner, "_nor_gl_", "_normalgl"), True)
    disp = tex(_karte(ordner, "_disp_", "_displacement"), True)

    # Ebene 1+2: Fototextur, Farbanpassung an Look-Bible, grossflaechige Variation
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    for i, k in enumerate(("Hue", "Saturation", "Value")):
        hsv.inputs[k].default_value = std["hsv"][i]
    _link(nt, col, hsv.inputs["Color"])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    var = _maprange(nt, _noise(nt, geo.outputs["Position"], 0.12, 3.0, 0.5), 0.3, 0.7,
                    1.0 - std["variation"], 1.0 + std["variation"])
    farbe = _mix_rgb(nt, 1.0, hsv.outputs["Color"], (1, 1, 1, 1), "MULTIPLY")
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
    return {n: material(n) for n in cfg["materialien"]}


def material_einfaerben(mat, hsv=None):
    """Heruntergeladenes Material an Look-Bible angleichen + MAT_Verwitterung einschleifen (A10, Punkt 3)."""
    if mat is None or mat.get("verwittert"):
        return mat
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return mat
    hsv = hsv or config("materialien.json")["verwitterung"]["heruntergeladen_hsv"]
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
