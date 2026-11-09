"""Phase 5 – Licht, Atmosphaere, Kameras, Render-Setup, Compositor (AUFTRAG 5.1-5.5).

Aufruf:  blender -b viertel_v07.blend --python scripts/phase5/build_phase5.py -- --version 08 [--nur Licht,Atmosphaere,Kameras,Render,Compositor]
Parameter: scripts/configs/licht.json. Jeder Teil entfernt vorher seinen alten Stand (wiederholbar).
Hero-Shots: Bild 1-4 der Zeitleiste = CAM_Hero_01-04 (Marker binden die Kamera) -> Render > Animation rendert alle vier.
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "phase4"))
import veg_basis as VB  # noqa: E402
from veg_basis import V  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
version = args[args.index("--version") + 1] if "--version" in args else "08"
nur = args[args.index("--nur") + 1].split(",") if "--nur" in args else ["Licht", "Atmosphaere", "Kameras", "Render", "Compositor"]
C = json.load(open(os.path.join(HIER, "..", "configs", "licht.json")))
sc = bpy.context.scene
COL = "10_Licht_Atmosphaere"


def col():
    return V.collection(COL)


def weg(praefixe):
    for o in [o for o in bpy.data.objects if o.name.startswith(tuple(praefixe)) and "_Position" not in o.name]:
        bpy.data.objects.remove(o)


def mat_neu(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, m.node_tree


def lin(h):
    return V.hex_lin(h)


# ---------------------------------------------------------------- 5.1 Licht
def licht():
    L = C["licht"]
    weg(["LGT_Sonne", "LGT_Feuer", "FX_Feuertonne", "FX_Flamme", "FX_Rauch_Tonne"])
    for w in [w for w in bpy.data.worlds if w.name.startswith("LGT_Welt")]:
        bpy.data.worlds.remove(w)
    hdr = os.path.join(V.ASSETS, "hdri", L["hdri"])
    img = bpy.data.images.load(hdr, check_existing=True)
    rot, _ = V.hdri_rotation_fuer(img, L["sonne_azimut"])
    V.hdri_welt(hdr, L["hdri_staerke"], rot)
    img.filepath = bpy.path.relpath(img.filepath)
    V.sonne(L["sonne_azimut"], L["sonne_hoehe"], staerke=L["sonne_staerke"], kelvin=L["sonne_kelvin"],
            winkel_grad=L["sonne_winkel"], col=col())
    feuertonne()


def _volumen_mat(name, dichte, farbe, emission=0.0, kelvin=2000, noise=1.5, radial=True, oben=0.15):
    """Volumen mit Noise; radial: Dichte faellt zum Rand des (Einheits-)Objekts ab, nach oben duenner."""
    m, nt = mat_neu(name)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = lin(farbe)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = noise
    nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    # r = Laenge(x, y) im Objektraum (Objekt: Radius 1, z 0..1)
    vm = nt.nodes.new("ShaderNodeVectorMath")
    vm.operation = "MULTIPLY"
    vm.inputs[1].default_value = (1, 1, 0)
    nt.links.new(tc.outputs["Object"], vm.inputs[0])
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    nt.links.new(vm.outputs[0], ln.inputs[0])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["From Min"].default_value, rr.inputs["From Max"].default_value = 0.2, 1.0
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = 1.0, 0.0
    nt.links.new(ln.outputs["Value"], rr.inputs["Value"])
    zz = nt.nodes.new("ShaderNodeMapRange")
    zz.inputs["From Min"].default_value, zz.inputs["From Max"].default_value = 0.0, 1.0
    zz.inputs["To Min"].default_value, zz.inputs["To Max"].default_value = 1.0, oben
    nt.links.new(sep.outputs["Z"], zz.inputs["Value"])
    nm = nt.nodes.new("ShaderNodeMapRange")
    nm.inputs["From Min"].default_value, nm.inputs["From Max"].default_value = 0.42, 0.75
    nt.links.new(nz.outputs["Fac"], nm.inputs["Value"])
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    nt.links.new(nm.outputs[0], m1.inputs[0])
    nt.links.new((rr if radial else zz).outputs[0], m1.inputs[1])
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    nt.links.new(m1.outputs[0], m2.inputs[0])
    nt.links.new(zz.outputs[0], m2.inputs[1])
    m3 = nt.nodes.new("ShaderNodeMath")
    m3.operation = "MULTIPLY"
    m3.inputs[1].default_value = dichte
    nt.links.new(m2.outputs[0], m3.inputs[0])
    nt.links.new(m3.outputs[0], pv.inputs["Density"])
    if emission:
        em = nt.nodes.new("ShaderNodeMath")
        em.operation = "MULTIPLY"
        em.inputs[1].default_value = emission
        nt.links.new(m2.outputs[0], em.inputs[0])
        nt.links.new(em.outputs[0], pv.inputs["Blackbody Intensity"])
        pv.inputs["Temperature"].default_value = kelvin
    nt.links.new(pv.outputs[0], out.inputs["Volume"])
    return m


def _zylinder(name, r, h, mat, pos, neigung=None):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=1.0, radius2=1.0, depth=1.0)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.5))
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.scale = (r, r, h)
    ob.location = pos
    if neigung:
        ob.rotation_euler = neigung
    col().objects.link(ob)
    return ob


def feuertonne():
    F = C["feuertonne"]
    s = VB.Strahl()
    b = s.boden(*F["pos"])
    print("FEUERTONNE Boden", b and b[2], b and round(b[0], 2))
    p = Vector((*F["pos"], b[0] if b else 0.0))
    # Tonne: oben offener Zylinder mit Wandstaerke, rostig
    import bmesh
    me = bpy.data.meshes.new("FX_Feuertonne")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=F["radius"], radius2=F["radius"], depth=F["hoehe"])
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, F["hoehe"] / 2))
    oben = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.delete(bm, geom=oben, context="FACES_ONLY")
    V.uv_welt(bm)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(V.material("MAT_Rost_Dunkel"))
    tonne = bpy.data.objects.new("FX_Feuertonne", me)
    tonne.location = p
    col().objects.link(tonne)
    m = tonne.modifiers.new("Wand", "SOLIDIFY")
    m.thickness = 0.012
    # Flamme (Volumen-Emission) und Rauchfahne
    fl = _zylinder("FX_Flamme", F["radius"] * 0.8, 0.5, _volumen_mat("MAT_FX_Flamme", 1.2, "#2E2A27", emission=14.0, oben=0.0,
                                                                       kelvin=F["kelvin"], noise=3.5), p + Vector((0, 0, F["hoehe"] - 0.12)))
    fl.visible_shadow = False
    _zylinder("FX_Rauch_Tonne", 0.9, 9.0, _volumen_mat("MAT_FX_Rauch_Tonne", 0.35, "#4E4B48", noise=1.2),
              p + Vector((0, 0, F["hoehe"] + 0.3)), neigung=(math.radians(12), 0, math.radians(-135)))
    # Punktlicht mit Flackern (Noise auf der Staerke, nur fuer Animation relevant)
    d = bpy.data.lights.new("LGT_Feuer", "POINT")
    d.energy = F["licht_w"]
    d.use_temperature, d.temperature = True, F["kelvin"]
    d.shadow_soft_size = 0.18
    lo = bpy.data.objects.new("LGT_Feuer", d)
    lo.location = p + Vector((0, 0, F["hoehe"] + 0.2))
    col().objects.link(lo)
    d.keyframe_insert("energy", frame=1)
    fc = d.animation_data.action.fcurves[0] if hasattr(d.animation_data.action, "fcurves") else None
    if fc:
        n = fc.modifiers.new("NOISE")
        n.scale, n.strength = 2.0, F["licht_w"] * F["flackern"]


# ---------------------------------------------------------------- 5.2 Atmosphaere
def atmosphaere():
    weg(["FX_Dunst", "FX_Rauchsaeule_", "FX_Vogel"])
    D = C["dunst"]
    m, nt = mat_neu("MAT_FX_Dunst")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = lin(D["farbe"])
    pv.inputs["Anisotropy"].default_value = D["anisotropie"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    # Tiefe: Abstand zur Viertel-Mitte (xy) -> 1 .. 1+tiefe_faktor
    vm = nt.nodes.new("ShaderNodeVectorMath")
    vm.operation = "DISTANCE"
    vm.inputs[1].default_value = (*D["mitte"], 0)
    mul = nt.nodes.new("ShaderNodeVectorMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = (1, 1, 0)
    nt.links.new(geo.outputs["Position"], mul.inputs[0])
    nt.links.new(mul.outputs[0], vm.inputs[0])
    tiefe = nt.nodes.new("ShaderNodeMapRange")
    tiefe.inputs["From Min"].default_value, tiefe.inputs["From Max"].default_value = 0.0, D["tiefe_m"]
    tiefe.inputs["To Min"].default_value, tiefe.inputs["To Max"].default_value = 1.0, 1.0 + D["tiefe_faktor"]
    nt.links.new(vm.outputs["Value"], tiefe.inputs["Value"])
    # Hoehe: exp(-z / abfall)
    hz = nt.nodes.new("ShaderNodeMath")
    hz.operation = "MULTIPLY"
    hz.inputs[1].default_value = -1.0 / D["hoehe_abfall_m"]
    nt.links.new(sep.outputs["Z"], hz.inputs[0])
    ex = nt.nodes.new("ShaderNodeMath")
    ex.operation = "EXPONENT"
    nt.links.new(hz.outputs[0], ex.inputs[0])
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    nt.links.new(tiefe.outputs[0], m1.inputs[0])
    nt.links.new(ex.outputs[0], m1.inputs[1])
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    m2.inputs[1].default_value = D["dichte"]
    nt.links.new(m1.outputs[0], m2.inputs[0])
    nt.links.new(m2.outputs[0], pv.inputs["Density"])
    nt.links.new(pv.outputs[0], out.inputs["Volume"])
    gx, gy, gz = D["groesse"]
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(*D["mitte"], gz / 2 - 20))
    w = bpy.context.active_object
    w.name = "FX_Dunst"
    w.scale = (gx, gy, gz)
    w.data.materials.append(m)
    for c in w.users_collection:
        c.objects.unlink(w)
    col().objects.link(w)
    w.visible_shadow = True
    # Rauchsaeulen an den Positionen aus Phase 1, vom Wind nach NO geneigt
    R = C["rauch"]
    rm = _volumen_mat("MAT_FX_Rauchsaeule", R["dichte"], R["farbe"], noise=R["noise"])
    az = math.radians(R["wind_azimut"])
    for i, e in enumerate(sorted((o for o in bpy.data.objects if o.name.startswith("FX_Rauchsaeule_Position")), key=lambda o: o.name)):
        if i < len(R.get("positionen", [])):  # Positionen aus Phase 1 hier ueberschreibbar (Horizont von CAM 2)
            e.location.x, e.location.y = R["positionen"][i]
        p = e.location.copy()  # Empty ohne Eltern; matrix_world waere hier noch nicht aktualisiert
        b = VB.Strahl().boden(p.x, p.y)
        p.z = b[0] if b else p.z
        z = _zylinder(f"FX_Rauchsaeule_{i + 1}", R["radius"], R["hoehe"], rm, p)
        z.rotation_mode = "XYZ"
        n = math.radians(R["neigung_grad"])
        z.rotation_euler = (-n * math.cos(az), n * math.sin(az), 0)
    voegel()


def _vogel_mesh():
    import bmesh
    me = bpy.data.meshes.new("FX_Vogel")
    bm = bmesh.new()
    s = C["voegel"]["spannweite_m"] / 2
    pts = [(-s, -0.02, 0.06), (-s * 0.45, 0.05, 0.03), (0, 0.12, 0), (s * 0.45, 0.05, 0.03), (s, -0.02, 0.06),
           (s * 0.4, -0.06, 0.0), (0.05, -0.2, 0), (0, -0.28, 0), (-0.05, -0.2, 0), (-s * 0.4, -0.06, 0.0)]
    bm.faces.new([bm.verts.new(p) for p in pts])
    bm.to_mesh(me)
    bm.free()
    m, nt = mat_neu("MAT_FX_Vogel")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = lin("#1C1B1A")
    b.inputs["Roughness"].default_value = 0.7
    nt.links.new(b.outputs[0], out.inputs[0])
    me.materials.append(m)
    return me


def voegel():
    W = C["voegel"]
    rnd = random.Random(W["seed"])
    me = _vogel_mesh()
    n = 0
    for cname in W["kamera"]:
        cam = bpy.data.objects[cname]
        mw = cam.matrix_world
        vor = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
        rechts = (mw.to_3x3() @ Vector((1, 0, 0))).normalized()
        hoch = (mw.to_3x3() @ Vector((0, 1, 0))).normalized()
        for k in range(W["anzahl_himmel"] if cname == W["kamera"][0] else 2):
            d = rnd.uniform(*W["abstand_m"])
            p = mw.translation + vor * d + rechts * rnd.uniform(-0.35, 0.35) * d + hoch * rnd.uniform(0.18, 0.3) * d
            o = bpy.data.objects.new(f"FX_Vogel_{n + 1:02d}", me)
            o.location = p
            o.rotation_euler = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.4, 0.4), rnd.uniform(0, 6.28))
            sk = rnd.uniform(0.85, 1.15)
            o.scale = (sk, sk, sk)
            col().objects.link(o)
            n += 1
    print("VOEGEL", n)


# ---------------------------------------------------------------- 5.3 Kameras
def kameras():
    for cname, ziel in C["kamera_fokus"].items():
        bpy.data.objects[cname].data.dof.focus_object = bpy.data.objects[ziel]
    dg = bpy.context.evaluated_depsgraph_get()
    for cname, hoehe in C["fokus_strahl"].items():
        if cname.startswith("_"):
            continue
        cam = bpy.data.objects[cname]
        fr = [cam.matrix_world @ v for v in cam.data.view_frame(scene=sc)]  # oben rechts, unten rechts, unten links, oben links
        start = cam.matrix_world.translation
        naechster = None  # naechster Treffer in einem Band bis zur angegebenen Bildhoehe (vorderste Sandsaecke)
        for u in (0.2, 0.35, 0.5, 0.65, 0.8):
            for k in range(1, 5):
                v = hoehe * k / 4
                unten = fr[2] + (fr[1] - fr[2]) * u
                ziel = unten + ((fr[3] + (fr[0] - fr[3]) * u) - unten) * v
                treffer, ort, _, _, o, _ = sc.ray_cast(dg, start, (ziel - start).normalized(), distance=200)
                if treffer and (naechster is None or (ort - start).length < naechster[0]):
                    naechster = ((ort - start).length, o.name)
        if naechster:
            cam.data.dof.focus_object = None
            cam.data.dof.focus_distance = naechster[0] + 0.25
            print("FOKUS", cname, naechster[1], round(naechster[0] + 0.25, 2))
    for c in [o for o in bpy.data.objects if o.name.startswith("CAM_Hero")]:
        c.data.sensor_width, c.data.sensor_fit = 36.0, "HORIZONTAL"
    for m in list(sc.timeline_markers):
        sc.timeline_markers.remove(m)
    for i in range(1, 5):
        mk = sc.timeline_markers.new(f"Hero_{i:02d}", frame=i)
        mk.camera = bpy.data.objects[f"CAM_Hero_{i:02d}"]
    sc.frame_start, sc.frame_end, sc.frame_current = 1, 4, 1
    sc.camera = bpy.data.objects["CAM_Hero_01"]


# ---------------------------------------------------------------- 5.4 Render
def render():
    R = C["render"]
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    sc.cycles.samples = R["samples"]
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = R["rauschschwelle"]
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = R["bounces"]
    sc.cycles.volume_bounces = R["volumen_bounces"]
    sc.cycles.sample_clamp_indirect = R["clamp_indirekt"]
    sc.cycles.texture_limit_render = "OFF"
    sc.render.resolution_x, sc.render.resolution_y = R["aufloesung"]
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = R["look"]
    vl = sc.view_layers[0]
    vl.use_pass_mist = True
    vl.use_pass_ambient_occlusion = True
    vl.cycles.denoising_store_passes = True
    sc.world.mist_settings.start = R["nebel_start"]
    sc.world.mist_settings.depth = R["nebel_tiefe"]
    sc.world.mist_settings.falloff = "QUADRATIC"
    sc.render.image_settings.media_type = "MULTI_LAYER_IMAGE"  # Blender 5: Multilayer-EXR
    sc.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    sc.render.image_settings.color_depth = "16"
    sc.render.filepath = "//renders/final/hero_##_"
    sc.render.use_file_extension = True


# ---------------------------------------------------------------- 5.5 Compositor
def kornbild():
    """Feines Filmkorn als Bild (960x540, Mittelwert 0.5), wird 2x skaliert -> grobkoerniger wie Film."""
    import numpy as np
    img = bpy.data.images.get("FX_Filmkorn") or bpy.data.images.new("FX_Filmkorn", 960, 540, float_buffer=False)
    rng = np.random.default_rng(3)
    g = np.clip(rng.normal(0.5, 0.17, (540, 960)), 0, 1).astype(np.float32)
    px = np.repeat(g[:, :, None], 4, axis=2)
    px[:, :, 3] = 1.0
    img.pixels.foreach_set(px.ravel())
    img.colorspace_settings.name = "Non-Color"
    img.pack()
    return img


def compositor():
    K = C["compositor"]
    alt = bpy.data.node_groups.get("CMP_Look")
    if alt:
        bpy.data.node_groups.remove(alt)
    ng = bpy.data.node_groups.new("CMP_Look", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = ng.nodes, ng.links
    rl = N.new("CompositorNodeRLayers")
    rl.scene = sc

    def mix(a, b, fac, art="MIX"):
        m = N.new("ShaderNodeMix")
        m.data_type, m.blend_type = "RGBA", art
        if isinstance(fac, float):
            m.inputs[0].default_value = fac
        else:
            L.new(fac, m.inputs[0])
        L.new(a, m.inputs[6]) if not isinstance(a, tuple) else setattr(m.inputs[6], "default_value", a)
        L.new(b, m.inputs[7]) if not isinstance(b, tuple) else setattr(m.inputs[7], "default_value", b)
        return m.outputs[2]

    # Tiefendunst ueber den Mist-Pass
    nebel_fak = N.new("ShaderNodeMath")
    nebel_fak.operation = "MULTIPLY"
    nebel_fak.inputs[1].default_value = K["nebel_mix"]
    L.new(rl.outputs["Mist"], nebel_fak.inputs[0])
    bild = mix(rl.outputs["Image"], tuple(lin(K["nebel_farbe"])), nebel_fak.outputs[0])
    # Farbkorrektur: Schatten kuehl, Lichter warm, leichter Gelb-Gruen-Stich
    cb = N.new("CompositorNodeColorBalance")
    cb.inputs["Type"].default_value = "Lift/Gamma/Gain"
    for name, wert in (("Lift", K["lift"]), ("Gamma", K["gamma"]), ("Gain", K["gain"])):
        [s for s in cb.inputs if s.name == name and s.type == "RGBA"][0].default_value = (*wert, 1.0)
    L.new(bild, cb.inputs["Image"])
    hs = N.new("CompositorNodeHueSat")
    hs.inputs["Saturation"].default_value = K["saettigung"]
    L.new(cb.outputs[0], hs.inputs["Image"])
    gl = N.new("CompositorNodeGlare")
    for wert in ("FOG_GLOW", "Fog Glow", "BLOOM", "Bloom"):
        try:
            gl.inputs["Type"].default_value = wert
            break
        except Exception:  # noqa: BLE001 - Menue-Namen je nach Blender-Version
            continue
    print("GLARE", gl.inputs["Type"].default_value)
    gl.inputs["Threshold"].default_value = K["glare_schwelle"]
    gl.inputs["Strength"].default_value = K["glare_staerke"]
    L.new(hs.outputs[0], gl.inputs["Image"])
    ld = N.new("CompositorNodeLensdist")
    ld.inputs["Dispersion"].default_value = K["dispersion"]
    ld.inputs["Fit"].default_value = True
    L.new(gl.outputs["Image"], ld.inputs["Image"])
    # Vignette: weiche Ellipse, Raender abdunkeln
    el = N.new("CompositorNodeEllipseMask")
    el.inputs["Size"].default_value = (0.95, 0.95)
    bl = N.new("CompositorNodeBlur")
    bl.inputs["Size"].default_value = (300, 300)
    L.new(el.outputs["Mask"], bl.inputs["Image"])
    vig = N.new("ShaderNodeMapRange")
    vig.inputs["To Min"].default_value = 1.0 - K["vignette"]
    L.new(bl.outputs[0], vig.inputs["Value"])
    vm = N.new("ShaderNodeMix")
    vm.data_type, vm.blend_type = "RGBA", "MULTIPLY"
    vm.inputs[0].default_value = 1.0
    L.new(ld.outputs[0], vm.inputs[6])
    L.new(vig.outputs[0], vm.inputs[7])
    # Filmkorn (Overlay)
    ki = N.new("CompositorNodeImage")
    ki.image = kornbild()
    ks = N.new("CompositorNodeScale")
    ks.inputs["Type"].default_value = "Render Size"
    L.new(ki.outputs["Image"], ks.inputs["Image"])
    bild = mix(vm.outputs[2], ks.outputs[0], K["korn"], "OVERLAY")
    go = N.new("NodeGroupOutput")
    L.new(bild, go.inputs[0])
    # zusaetzlich bearbeitetes PNG nach renders/final/
    fo = N.new("CompositorNodeOutputFile")
    fo.directory = "//renders/final/"
    fo.file_name = "hero_##"
    if hasattr(fo, "use_custom_format"):
        fo.use_custom_format = True
    fo.format.media_type = "IMAGE"
    fo.format.file_format = "PNG"
    try:
        fo.file_output_items.new("RGBA", "_bearbeitet")
    except Exception as e:  # noqa: BLE001
        print("COMPOSITOR file_output_items", e)
    L.new(bild, fo.inputs[0])
    sc.compositing_node_group = ng
    sc.render.use_compositing = True
    print("COMPOSITOR", len(N), "Knoten", flush=True)


if __name__ == "__main__":
    V.regler_setzen(sc)
    for teil in nur:
        {"Licht": licht, "Atmosphaere": atmosphaere, "Kameras": kameras, "Render": render, "Compositor": compositor}[teil]()
        print("TEIL", teil, "fertig", flush=True)
    if "--ohne-speichern" not in args:
        pfad = os.path.join(V.ROOT, f"viertel_v{version}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=pfad, compress=True, relative_remap=True)
        print("GESPEICHERT", pfad, round(os.path.getsize(pfad) / 1e6, 1), "MB")
