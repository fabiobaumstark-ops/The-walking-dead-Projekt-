"""Phase 3.6 – Figuren (Zombies) mit MPFB 2 + MakeHuman-Systemassets (CC0), ohne Blut und ohne Wunden.

Ablauf je Vorlage:
- MPFB-Koerper (Geschlecht, Alter, Statur), Standard-Rig
- Proxy-Koerper, Haut (fahl, graeulich, schmutzig), Kleidung + Schuhe + Haare aus dem CC0-Paket
- Pose (eigene Knochenrotationen)
- dann zu EINEM festen Mesh gebacken (ohne Rig, ohne Shape Keys -> kleine Datei)
Danach: Platzierung (Gruppen + Einzelne, 15-40 m und > 40 m zur Hero-Kamera, min. 12 m), siehe figuren.json.
Benoetigt: MPFB 2 aktiv + Systemassets im MPFB-Benutzerordner (siehe ZUHAUSE_ANLEITUNG / UEBERGABE).
"""
import importlib
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

MP = "bl_ext.user_default.mpfb"

# Posen: Knochen -> Rotation in Grad (lokale Achsen des MakeHuman-Standard-Rigs), dazu Becken-Absenkung in m
POSEN = {
    # Achsen (kalibriert): Oberarm Z: links + = heben / rechts - = heben; X + = nach vorne. Wirbelsaeule/Kopf X + = nach vorne.
    # Oberschenkel X - = nach vorne, X + = nach hinten; Knie X + = beugen; Kopf Z = seitlich neigen.
    "schlurfen":   {"spine03": (12, 0, 0), "spine01": (6, 0, 0), "neck01": (14, 0, 4), "head": (10, 0, -6),
                    "upperarm01.L": (14, 0, -40), "upperarm01.R": (8, 0, 42), "lowerarm01.L": (10, 0, 0), "lowerarm01.R": (6, 0, 0),
                    "upperleg01.L": (-16, 0, 0), "lowerleg01.L": (14, 0, 0), "upperleg01.R": (12, 0, 0), "lowerleg01.R": (10, 0, 0),
                    "foot.R": (-8, 0, 0)},
    "gebeugt":     {"spine05": (10, 0, 0), "spine03": (22, 0, 0), "spine01": (14, 0, 0), "neck01": (18, 0, 0), "head": (-6, 0, 0),
                    "upperarm01.L": (30, 0, -36), "upperarm01.R": (26, 0, 38), "lowerarm01.L": (12, 0, 0), "lowerarm01.R": (16, 0, 0),
                    "upperleg01.L": (-12, 0, 0), "upperleg01.R": (-4, 0, 0), "lowerleg01.L": (20, 0, 0), "lowerleg01.R": (16, 0, 0)},
    "bein_ziehen": {"spine03": (8, 0, -8), "spine01": (4, 0, -6), "neck01": (8, 0, 10), "head": (6, 0, 14),
                    "upperarm01.L": (-6, 0, -42), "upperarm01.R": (22, 0, 34), "lowerarm01.R": (24, 0, 0),
                    "upperleg01.L": (-18, 0, 0), "lowerleg01.L": (10, 0, 0), "upperleg01.R": (16, 0, 0), "lowerleg01.R": (22, 0, 0),
                    "foot.R": (-26, 0, 0)},
    "kopf_schief": {"spine03": (4, 0, 6), "neck01": (6, 0, 22), "head": (2, 0, 24),
                    "upperarm01.L": (6, 0, -44), "upperarm01.R": (10, 0, 36), "lowerarm01.L": (6, 0, 0)},
    "starrend":    {"neck01": (-4, 0, 0), "head": (-6, 0, 0), "upperarm01.L": (4, 0, -42), "upperarm01.R": (4, 0, 42),
                    "lowerarm01.L": (6, 0, 0), "lowerarm01.R": (6, 0, 0)},
    "wand":        {"spine01": (-6, 0, 0), "spine03": (-6, 0, 0), "head": (8, 0, 16), "upperarm01.L": (-8, 0, -44),
                    "upperarm01.R": (-8, 0, 44), "upperleg01.R": (-28, 0, -6), "lowerleg01.R": (44, 0, 0), "foot.R": (-10, 0, 0)},
    "auto":        {"spine01": (20, 0, 0), "spine03": (20, 0, 0), "neck01": (-8, 0, 0), "head": (-10, 0, 0),
                    "upperarm01.L": (62, 0, -14), "upperarm01.R": (58, 0, 14), "lowerarm01.L": (-6, 0, 0), "lowerarm01.R": (-4, 0, 0),
                    "upperleg01.L": (-4, 0, 0), "upperleg01.R": (8, 0, 0)},
    "hockend":     {"spine01": (28, 0, 0), "spine03": (16, 0, 0), "neck01": (10, 0, 0), "head": (8, 0, 0),
                    "upperarm01.L": (34, 0, -30), "upperarm01.R": (38, 0, 30), "lowerarm01.L": (30, 0, 0), "lowerarm01.R": (26, 0, 0),
                    "upperleg01.L": (-95, 0, 4), "upperleg01.R": (-80, 0, -4), "lowerleg01.L": (120, 0, 0), "lowerleg01.R": (105, 0, 0),
                    "foot.L": (-20, 0, 0), "foot.R": (-25, 0, 0), "_absenken": 0.42},
}


def mpfb():
    try:
        HS = importlib.import_module(MP + ".services.humanservice").HumanService
        LS = importlib.import_module(MP + ".services.locationservice").LocationService
    except ImportError:
        bpy.ops.preferences.addon_enable(module=MP)
        HS = importlib.import_module(MP + ".services.humanservice").HumanService
        LS = importlib.import_module(MP + ".services.locationservice").LocationService
    return HS, LS


def _pfad(daten, art, name, endung):
    p = os.path.join(daten, art, name, f"{name}.{endung}")
    return p if os.path.exists(p) else None


def posieren(rig, pose, rnd):
    P = POSEN[pose]
    bpy.context.view_layer.objects.active = rig
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
    for bn, rot in P.items():
        if bn.startswith("_"):
            continue
        pb = rig.pose.bones.get(bn)
        if pb is None:
            continue
        j = [rnd.uniform(-4, 4) for _ in range(3)]
        pb.rotation_euler = Euler([math.radians(r + d) for r, d in zip(rot, j)], "XYZ")
    if P.get("_absenken"):
        root = rig.pose.bones.get("root")
        if root is not None:
            root.location = (0, -P["_absenken"], 0)
    bpy.context.view_layer.update()


def charakter(spec, rnd):
    """Erzeugt einen MPFB-Charakter und gibt (Objekte, Rig) zurueck."""
    HS, LS = mpfb()
    daten = LS.get_user_data()
    macro = {"gender": 0.5, "age": 0.5, "muscle": 0.5, "weight": 0.5, "proportions": 0.5, "height": 0.5,
             "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.2, "caucasian": 0.5, "african": 0.3}}
    for k, v in spec.get("macro", {}).items():
        if k == "race":
            macro["race"] = dict(v)
        else:
            macro[k] = v
    base = HS.create_human(macro_detail_dict=macro)
    rig = HS.add_builtin_rig(base, "default", import_weights=True)
    frau = spec.get("macro", {}).get("gender", 0.5) < 0.5
    proxy = HS.add_mhclo_asset(_pfad(daten, "proxymeshes", "female_generic" if frau else "male_generic", "proxy"), base,
                               asset_type="Proxymeshes", subdiv_levels=0, material_type="NONE")
    m = base.modifiers.new("Hide base mesh", "MASK")
    m.vertex_group = "body"
    m.invert_vertex_group = True
    skin = _pfad(daten, "skins", spec["haut"], "mhmat")
    if skin:
        HS.set_character_skin(skin, base, bodyproxy=proxy, skin_type="MAKESKIN")
    teile = [proxy]
    for c in spec.get("kleidung", []):
        p = _pfad(daten, "clothes", c, "mhclo")
        if p:
            teile.append(HS.add_mhclo_asset(p, base, asset_type="Clothes", subdiv_levels=0, material_type="MAKESKIN"))
    if spec.get("haar"):
        p = _pfad(daten, "hair", spec["haar"], "mhclo")
        if p:
            teile.append(HS.add_mhclo_asset(p, base, asset_type="Hair", subdiv_levels=0, material_type="MAKESKIN"))
    posieren(rig, spec["pose"], rnd)
    return base, rig, [t for t in teile if t is not None]


# ---------------------------------------------------------------- Materialien: fahl, schmutzig, zerrissen (kein Blut)
def _bsdf(mat):
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if mat and mat.node_tree else None


def material_altern(mat, art, rnd):
    """Haut: entsaettigt, grau-gruenlich, Schmutz. Kleidung: ausgeblichen, Flecken, Loecher (Alpha). Haare: stumpf."""
    if mat is None or mat.get("figur_gealtert"):
        return mat
    nt = mat.node_tree
    b = _bsdf(mat)
    if b is None:
        return mat
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    P = geo.outputs["Position"]
    quelle = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].links else None
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    if quelle is not None:
        nt.links.new(quelle, hsv.inputs["Color"])
    else:
        hsv.inputs["Color"].default_value = b.inputs["Base Color"].default_value
    if art == "haut":
        hsv.inputs["Saturation"].default_value = 0.30
        hsv.inputs["Value"].default_value = 0.55
        farbe = V._mix_rgb(nt, 0.40, hsv.outputs["Color"], V.hex_lin("#6E7366"))
        fleck = V._maprange(nt, V._noise(nt, P, 9.0, 6.0, 0.6), 0.40, 0.7, 0.0, 0.65)
        farbe = V._mix_rgb(nt, fleck, farbe, V.hex_lin("#5A5346"))
        rau = 0.62
    elif art == "haar":
        hsv.inputs["Saturation"].default_value = 0.45
        hsv.inputs["Value"].default_value = 0.65
        farbe = V._mix_rgb(nt, 0.25, hsv.outputs["Color"], V.hex_lin("#6E6A60"))
        rau = 0.8
    else:
        hsv.inputs["Saturation"].default_value = 0.45
        hsv.inputs["Value"].default_value = 0.50
        farbe = V._mix_rgb(nt, 0.30, hsv.outputs["Color"], V.hex_lin("#5E574B"))
        fleck = V._maprange(nt, V._noise(nt, P, 3.5, 6.0, 0.65), 0.45, 0.72, 0.0, 0.8)
        farbe = V._mix_rgb(nt, fleck, farbe, V.hex_lin("#3F382F"))
        # Loecher / Fetzen
        loch = V._maprange(nt, V._noise(nt, P, 6.0, 8.0, 0.7, 0.3), 0.66, 0.70, 1.0, 0.0)
        nt.links.new(loch, b.inputs["Alpha"])
        rau = 0.88
    grp = V._verw_anschluss(nt, farbe, rau, None, lokal=0.25, kante="#6E6A60")
    nt.links.new(grp.outputs["Farbe"], b.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], b.inputs["Roughness"])
    for n in ("Subsurface Weight", "Coat Weight", "Specular IOR Level"):
        if n in b.inputs and not b.inputs[n].links:
            b.inputs[n].default_value = 0.0 if n != "Specular IOR Level" else 0.35
    mat["figur_gealtert"] = True
    return mat


def backen(name, base, rig, teile, col, rnd):
    """Gepostes Ergebnis zu EINEM Mesh (Materialien = Originale, gealtert), MPFB-Objekte entfernen."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    mats = []
    for o in teile:
        ev = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=False, depsgraph=dg)
        art = "haut" if o is teile[0] else ("haar" if "hair" in o.name.lower() or o.get("mpfb_type") == "Hair" else "stoff")
        karte = []
        for sl in o.material_slots:
            m = sl.material
            if m is not None and not m.get("figur_gealtert"):
                material_altern(m, art, rnd)
            if m not in mats:
                mats.append(m)
            karte.append(mats.index(m))
        tmp = bmesh.new()
        tmp.from_mesh(me)
        tmp.transform(o.matrix_world)
        for f in tmp.faces:
            f.material_index = karte[min(f.material_index, len(karte) - 1)] if karte else 0
            f.smooth = True
        me2 = bpy.data.meshes.new("tmp_fig")
        tmp.to_mesh(me2)
        tmp.free()
        bm.from_mesh(me2)
        bpy.data.meshes.remove(me2)
        bpy.data.meshes.remove(me)
    dl = bm.verts.layers.deform.active  # Rig-Gewichte werden nach dem Backen nicht mehr gebraucht
    if dl is not None:
        bm.verts.layers.deform.remove(dl)
    zmin = min((v.co.z for v in bm.verts), default=0.0)  # tiefster Punkt (Fuss/Knie) auf den Boden
    bmesh.ops.translate(bm, vec=(0, 0, -zmin), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob["lack_alter"] = 1.0
    ob["verw_korrektur"] = -0.4
    # MPFB-Objekte entfernen (Kleidung/Proxy sind Kinder des Basismeshes)
    weg = [base, rig] + list(teile) + [c for c in base.children_recursive]
    bpy.data.batch_remove(list({o for o in weg if o is not None}))
    return ob


def vorlagen_bauen(cfg, col, rnd):
    out = {}
    for spec in cfg["vorlagen"]:
        base, rig, teile = charakter(spec, rnd)
        ob = backen(f"FIG_Vorlage_{spec['name']}", base, rig, teile, col, rnd)
        ob["pose"] = spec["pose"]
        out[spec["name"]] = ob
        print("FIGUR", spec["name"], len(ob.data.vertices), flush=True)
    return out


def frei(x, y, boden, r=0.45):
    """Kein Fahrzeug/Schutt an der Stelle (Strahlen von oben treffen den Boden)."""
    dg = bpy.context.evaluated_depsgraph_get()
    zb = boden.z(x, y)
    for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)):
        hit, loc, *_ = bpy.context.scene.ray_cast(dg, Vector((x + dx, y + dy, zb + 4.0)), Vector((0, 0, -1)), distance=6.0)
        if hit and loc.z > zb + 0.25:
            return False
    return True


def platzieren(cfg, vorlagen, col, boden, rnd):
    """Gruppen + Einzelne als verlinkte Kopien (gleiches Mesh), Abstand zu den Hero-Kameras pruefen."""
    cams = [o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("CAM_Hero_")]
    namen = list(vorlagen.keys())
    out = []
    zaehler = 0
    for g in cfg["gruppen"]:
        cx, cy = g["mitte"]
        for k in range(g["anzahl"]):
            for _ in range(40):
                x = cx + rnd.uniform(-g["radius"], g["radius"])
                y = cy + rnd.uniform(-g["radius"] * 0.6, g["radius"] * 0.6)
                dmin = min((Vector((x, y, 0)) - Vector((c.x, c.y, 0))).length for c in cams) if cams else 99
                if dmin >= cfg["min_abstand_m"] and frei(x, y, boden):
                    break
            erlaubt = g.get("vorlagen") or namen
            v = vorlagen[rnd.choice(erlaubt)]
            zaehler += 1
            o = v.copy()
            o.name = f"FIG_{g['name']}_{k + 1:02d}"
            o.location = (x, y, boden.z(x, y))
            o.rotation_euler = (0, 0, math.radians(g.get("richtung", 0) + rnd.uniform(-70, 70)))
            s = rnd.uniform(0.95, 1.05)
            o.scale = (s, s, s)
            col.objects.link(o)
            o["gruppe"] = g["name"]
            o["abstand_kamera_m"] = round(dmin, 1)
            out.append(o)
    for e in cfg.get("einzelne", []):
        v = vorlagen[e["vorlage"]]
        o = v.copy()
        o.name = f"FIG_Einzeln_{e['name']}"
        x, y = e["pos"]
        o.location = (x, y, boden.z(x, y))
        o.rotation_euler = (0, 0, math.radians(e.get("richtung", 0)))
        col.objects.link(o)
        dmin = min((Vector((x, y, 0)) - Vector((c.x, c.y, 0))).length for c in cams) if cams else 99
        o["abstand_kamera_m"] = round(dmin, 1)
        out.append(o)
    # Vorlagen selbst aus dem Bild (in Prototyp-Collection verschieben)
    proto = V.prototypen("Figuren_Vorlagen")
    for v in vorlagen.values():
        for c in list(v.users_collection):
            c.objects.unlink(v)
        proto.objects.link(v)
    return out


def texturen_umstellen():
    """Bildpfade aus dem MPFB-Benutzerordner -> //assets/mpfb/data/... (relativ, wie alle Projekt-Assets)."""
    HS, LS = mpfb()
    quelle = os.path.normpath(LS.get_user_data())
    ziel = os.path.join(V.ASSETS, "mpfb", "data")
    n = 0
    for img in bpy.data.images:
        p = os.path.normpath(bpy.path.abspath(img.filepath)) if img.filepath else ""
        if p.startswith(quelle):
            neu = os.path.join(ziel, os.path.relpath(p, quelle))
            if not os.path.exists(neu):
                os.makedirs(os.path.dirname(neu), exist_ok=True)
                import shutil
                shutil.copyfile(p, neu)
            img.filepath = bpy.path.relpath(neu)
            n += 1
    return n


def bauen(boden=None):
    import flotte as FL
    cfg = V.config("figuren.json")
    rnd = random.Random(cfg["seed"])
    col = V.collection("09_Figuren")
    vorlagen = vorlagen_bauen(cfg, col, rnd)
    print("Texturpfade umgestellt:", texturen_umstellen(), flush=True)
    boden = boden or FL.Boden()
    return platzieren(cfg, vorlagen, col, boden, rnd)
