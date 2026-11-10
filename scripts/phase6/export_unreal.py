"""Phase 6.1 – Export des Viertels fuer Unreal Engine 5.8 (Blender-Seite).

Aufruf (im Repo-Hauptordner):
    blender -b viertel_v10.blend --python scripts/phase6/export_unreal.py -- --test
    blender -b viertel_v10.blend --python scripts/phase6/export_unreal.py -- --alles
Optionen: --mitte x,y  --radius m (Testbereich, Standard: Panzer A, 30 m)  --ziel ordner (Standard export/unreal_test bzw. export/unreal)

Prinzip (wie in Blender: Vorlage + Instanzen):
- Jede eindeutige Form wird EINMAL als FBX gespeichert (meshes/SM_*.fbx, lokale Koordinaten, Meter).
- szene.json listet je Form alle Platzierungen (schon in Unreal-Koordinaten: cm, Roll/Pitch/Yaw, Skalierung),
  die Materialien mit ihren Texturen (Pfade relativ zum Repo) sowie Licht und Startpunkt.
- scripts/phase6/ue_import.py liest szene.json im Unreal-Editor und baut daraus das Level.
Gerendert wird mit den RENDER-Einstellungen (Pflanzen-Generatoren an, Simplify aus), die .blend wird nicht veraendert.

Koordinaten (Annahme, wird mit dem Testobjekt TEST_Achsen geprueft): Blender rechtshaendig (m, Z oben),
Unreal linkshaendig (cm, Z oben): x_ue = 100 x, y_ue = -100 y, z_ue = 100 z; Roll = rx, Pitch = -ry, Yaw = -rz.
Falls das Testobjekt in Unreal falsch liegt: Werte in KONV unten anpassen und neu exportieren.
"""
import json
import math
import os
import re
import sys
import time

import bpy
import bmesh
from mathutils import Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HIER, "..", ".."))

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEST = "--alles" not in args
MITTE = [float(v) for v in args[args.index("--mitte") + 1].split(",")] if "--mitte" in args else [-3.6, 3.35]
RADIUS = float(args[args.index("--radius") + 1]) if "--radius" in args else 30.0
ZIEL = os.path.join(ROOT, args[args.index("--ziel") + 1]) if "--ziel" in args else \
    os.path.join(ROOT, "export", "unreal_test" if TEST else "unreal")

KONV = {"skala": 100.0, "spiegel_y": True, "roll": 1, "pitch": -1, "yaw": -1}
WEG = ("FX_Dunst", "FX_Rauch", "FX_Flamme", "CAM_", "LGT_")  # Volumen/Kameras/Lichter nicht als Mesh
MIN_FLAECHEN = 1


def name_ue(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)[:90]


# ------------------------------------------------------------------ Render-Zustand herstellen (nur im Speicher)
def render_zustand():
    for o in bpy.data.objects:
        o.hide_viewport = o.hide_render
        for m in o.modifiers:
            m.show_viewport = m.show_render

    def lc(l):
        l.collection.hide_viewport = l.collection.hide_render
        for k in l.children:
            lc(k)
    lc(bpy.context.view_layer.layer_collection)
    bpy.context.scene.render.use_simplify = False


# ------------------------------------------------------------------ Koordinaten
def ue_transform(mw):
    loc, rot, sk = mw.decompose()
    gespiegelt = mw.to_3x3().determinant() < 0
    e = rot.to_euler("XYZ")
    s = KONV["skala"]
    y = -loc.y if KONV["spiegel_y"] else loc.y
    return [round(loc.x * s, 2), round(y * s, 2), round(loc.z * s, 2),
            round(math.degrees(e.x) * KONV["roll"], 3), round(math.degrees(e.y) * KONV["pitch"], 3),
            round(math.degrees(e.z) * KONV["yaw"], 3),
            round(sk.x, 4), round(sk.y, 4), round(sk.z, 4)], gespiegelt


def ue_blick(mw):
    """Blickrichtung (Blender: lokale -Z-Achse von Sonne/Kamera) als Unreal-Rotator [Roll, Pitch, Yaw] in Grad.
    Unreal-Lichter und -Kameras schauen entlang ihrer +X-Achse."""
    d = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    dy = -d.y if KONV["spiegel_y"] else d.y
    return [0.0, round(math.degrees(math.asin(max(-1, min(1, d.z)))), 3), round(math.degrees(math.atan2(dy, d.x)), 3)]


def im_testbereich(mw, ob=None):
    if not TEST:
        return True
    if ob is not None and ob.type == "MESH":
        pts = [mw @ Vector(c) for c in ob.bound_box]
        x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
        y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        dx = max(x0 - MITTE[0], 0, MITTE[0] - x1)
        dy = max(y0 - MITTE[1], 0, MITTE[1] - y1)
        return math.hypot(dx, dy) <= RADIUS
    t = mw.translation
    return math.hypot(t.x - MITTE[0], t.y - MITTE[1]) <= RADIUS


# ------------------------------------------------------------------ Materialien
def _bild_stromauf(sock, tiefe=0):
    """Erstes Bild (Image Texture) stromaufwaerts eines Eingangs; durchlaeuft Gruppen, Mix, Normal Map usw."""
    if tiefe > 25 or not sock.is_linked:
        return None
    for lk in sock.links:
        n = lk.from_node
        if n.type == "TEX_IMAGE" and n.image and n.image.source == "FILE" and not n.image.packed_file:
            return n.image
        if n.type == "GROUP_INPUT":
            continue
        for e in n.inputs:
            b = _bild_stromauf(e, tiefe + 1)
            if b:
                return b
    return None


def _pfad(img):
    if img is None:
        return None
    p = os.path.abspath(bpy.path.abspath(img.filepath, library=img.library))
    try:
        return os.path.relpath(p, ROOT).replace("\\", "/")
    except ValueError:
        return p


ROLLEN = [("normal", r"nor_gl|nor_dx|normalgl|normaldx|normal|_nor_|_nor\."), ("rau", r"rough"),
          ("maske", r"alpha|opacity|_mask"), ("farbe", r"diff|color|albedo|basecolor|_col_|_col\.")]
NIE = r"disp|height|_ao_|_ao\.|ambientocclusion|metal|spec|bump"


def _bilder(nt, seen=None):
    """Alle Datei-Bilder im Material, auch in eigenen Gruppen (ohne MAT_Verwitterung)."""
    seen = seen or set()
    out = []
    for n in nt.nodes:
        if n.type == "TEX_IMAGE" and n.image and n.image.source == "FILE" and not n.image.packed_file:
            out.append(n.image)
        elif n.type == "GROUP" and n.node_tree and n.node_tree.name not in seen \
                and not n.node_tree.name.startswith("MAT_Verwitterung"):  # Moos/Schmutz-Ebenen -> spaeter Unreal-Mastermaterial
            seen.add(n.node_tree.name)
            out += _bilder(n.node_tree, seen)
    return out


def _farbe(sock, tiefe=0):
    """Grundfarbe ohne Textur: Farbe am Ende der Kette (RGB-Knoten oder unverbundener Farbeingang)."""
    if not sock.is_linked:
        v = sock.default_value
        return [round(c, 4) for c in list(v)[:3]] if hasattr(v, "__len__") and len(v) >= 3 else None
    if tiefe > 20:
        return None
    n = sock.links[0].from_node
    if n.type == "RGB":
        return [round(c, 4) for c in list(n.outputs[0].default_value)[:3]]
    for e in n.inputs:
        if e.type == "RGBA":
            f = _farbe(e, tiefe + 1)
            if f:
                return f
    return None


def material_info(m):
    info = {"basis": [0.5, 0.5, 0.5], "rau": 0.7, "metall": 0.0, "maske": False, "zweiseitig": False, "tex": {}}
    if m is None or not m.node_tree:
        return info
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        for g in (n for n in nt.nodes if n.type == "GROUP" and n.node_tree):
            bsdf = next((n for n in g.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf:
                break
    if bsdf is not None:
        info["basis"] = _farbe(bsdf.inputs["Base Color"]) or info["basis"]
        info["rau"] = round(bsdf.inputs["Roughness"].default_value, 3)
        info["metall"] = round(bsdf.inputs["Metallic"].default_value, 3)
    em = next((n for n in nt.nodes if n.type == "EMISSION"), None)
    if em is not None:
        info["leuchten"] = [round(c, 4) for c in list(em.inputs["Color"].default_value)[:3]]
    trocken = "trocken" in m.name.lower() or "dry" in m.name.lower()
    for img in _bilder(nt):
        dn = os.path.basename(img.filepath).lower()
        if re.search(NIE, dn):
            continue
        for rolle, muster in ROLLEN:
            if re.search(muster, dn):
                if rolle == "farbe" and "farbe" in info["tex"]:
                    # Pflanzen: trockene Variante bevorzugen, wenn das Material trocken ist
                    if trocken == ("dry" in dn):
                        info["tex"]["farbe"] = _pfad(img)
                elif rolle not in info["tex"]:
                    info["tex"][rolle] = _pfad(img)
                break
    transparent = any(n.type == "BSDF_TRANSPARENT" for n in nt.nodes)
    alpha = bsdf is not None and (bsdf.inputs["Alpha"].is_linked or bsdf.inputs["Alpha"].default_value < 0.999)
    info["maske"] = bool("maske" in info["tex"] or transparent or alpha)
    info["zweiseitig"] = info["maske"]
    if "normal" in info["tex"]:
        # Poly Haven (*_nor_gl_*) und ambientCG (*_NormalGL*) liefern OpenGL-Normalen -> in Unreal Gruen kippen
        info["normal_opengl"] = bool(re.search(r"nor_gl|normalgl", os.path.basename(info["tex"]["normal"]).lower()))
    return info


# ------------------------------------------------------------------ Testobjekt fuer die Achsen
def testobjekt(dg_col):
    """Pfeil 2 m in +X, Stab 1 m in +Y, Wuerfel 0,5 m oben: zeigt in Unreal sofort, ob Achsen/Masse stimmen."""
    me = bpy.data.meshes.new("TEST_Achsen")
    bm = bmesh.new()
    for (cx, cy, cz), (sx, sy, sz) in (((1.0, 0, 0.1), (2.0, 0.2, 0.2)), ((0, 0.5, 0.1), (0.1, 1.0, 0.1)),
                                         ((0, 0, 0.45), (0.5, 0.5, 0.5)), ((2.1, 0, 0.1), (0.2, 0.5, 0.2))):
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=r["verts"])
        bmesh.ops.translate(bm, vec=(cx, cy, cz), verts=r["verts"])
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("TEST_Achsen", me)
    dg_col.objects.link(ob)
    ob.location = (MITTE[0] + 6.0, MITTE[1] - 6.0, 0.0)
    ob.rotation_euler = (0, 0, math.radians(30))  # 30 Grad gedreht: Drehrichtung pruefen
    return ob


# ------------------------------------------------------------------ Export
def fbx_schreiben(me, pfad, tmp_scene):
    ob = bpy.data.objects.new("UE_tmp", me)
    tmp_scene.collection.objects.link(ob)
    vl = tmp_scene.view_layers[0]
    for o in tmp_scene.objects:
        o.select_set(o == ob, view_layer=vl)
    with bpy.context.temp_override(scene=tmp_scene, view_layer=vl, active_object=ob, selected_objects=[ob]):
        bpy.ops.export_scene.fbx(filepath=pfad, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                                 apply_scale_options="FBX_SCALE_NONE", mesh_smooth_type="FACE", use_mesh_modifiers=False,
                                 add_leaf_bones=False, bake_anim=False, path_mode="STRIP", use_tspace=True,
                                 axis_forward="-Z", axis_up="Y")
    bpy.data.objects.remove(ob)


def main():
    t0 = time.time()
    render_zustand()
    sc = bpy.context.scene
    testobjekt(bpy.data.collections.get("11_Kameras") or sc.collection)
    dg = bpy.context.evaluated_depsgraph_get()
    os.makedirs(os.path.join(ZIEL, "meshes"), exist_ok=True)
    tmp = bpy.data.scenes.new("UE_Export_tmp")
    formen = {}      # schluessel -> {"datei", "mats", "flaechen", "quelle"}
    platz = {}       # schluessel -> [transform, ...]
    gespiegelt = 0
    mats = {}
    for i in dg.object_instances:
        o = i.object
        if o.type != "MESH":
            continue
        orig = o.original
        if orig.name.startswith(WEG):
            continue
        mw = i.matrix_world.copy()
        if not im_testbereich(mw, o):
            continue
        slots = [s.material.name if s.material else "" for s in o.material_slots]
        basis_me = o.data.original if o.data.original else o.data
        if orig.modifiers:  # Modifier veraendern die Form -> je Objekt eine eigene Form
            key = f"O_{orig.name}|{'/'.join(slots)}"
        else:  # gleiche Mesh-Daten + gleiche Materialien = gleiche Form (Instanzen, verlinkte Kopien)
            key = f"D_{basis_me.name}|{'/'.join(slots)}"
        if key not in formen:
            me = bpy.data.meshes.new_from_object(o, preserve_all_data_layers=False, depsgraph=dg)
            if len(me.polygons) < MIN_FLAECHEN:
                bpy.data.meshes.remove(me)
                formen[key] = None
                continue
            if any(len(pg.vertices) > 4 for pg in me.polygons):  # N-Gons -> Dreiecke (Tangenten fuer Normalmaps)
                bm = bmesh.new()
                bm.from_mesh(me)
                bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
                bm.to_mesh(me)
                bm.free()
            me.materials.clear()
            for s in o.material_slots:
                me.materials.append(s.material)
            nm = "SM_" + name_ue(key.split("|")[0][2:])
            basis, k = nm, 2
            while any(f and f["name"] == nm for f in formen.values()):
                nm, k = f"{basis}_{k}", k + 1
            fbx_schreiben(me, os.path.join(ZIEL, "meshes", nm + ".fbx"), tmp)
            formen[key] = {"name": nm, "datei": f"meshes/{nm}.fbx", "flaechen": len(me.polygons),
                           "mats": [name_ue(s) if s else "M_leer" for s in slots], "quelle": orig.name,
                           "kategorie": kategorie(orig)}
            for s in o.material_slots:
                if s.material and name_ue(s.material.name) not in mats:
                    mats[name_ue(s.material.name)] = material_info(s.material)
            bpy.data.meshes.remove(me)
            if len(formen) % 100 == 0:
                print("FORMEN", len(formen), round(time.time() - t0), "s", flush=True)
        if formen[key] is None:
            continue
        t, sp = ue_transform(mw)
        gespiegelt += sp
        platz.setdefault(formen[key]["name"], []).append(t)
    bpy.data.scenes.remove(tmp)
    # Licht, Startpunkt
    licht = []
    for o in bpy.data.objects:
        if o.type == "LIGHT" and not o.hide_render:
            t, _ = ue_transform(o.matrix_world)
            d = o.data
            licht.append({"name": o.name, "typ": d.type, "t": t, "staerke": d.energy, "blick": ue_blick(o.matrix_world),
                          "kelvin": d.temperature if getattr(d, "use_temperature", False) else None,
                          "farbe": list(d.color), "winkel": math.degrees(getattr(d, "angle", 0.0))})
    cam = bpy.data.objects["CAM_Hero_01"]
    start, _ = ue_transform(cam.matrix_world)
    start = {"pos": start[:3], "blick": ue_blick(cam.matrix_world)}
    szene = {
        "version": 1, "quelle": os.path.basename(bpy.data.filepath), "test": TEST, "mitte": MITTE, "radius": RADIUS,
        "konvertierung": KONV, "formen": {f["name"]: f for f in formen.values() if f},
        "platzierungen": platz, "materialien": mats, "licht": licht, "start": start,
    }
    with open(os.path.join(ZIEL, "szene.json"), "w") as f:
        json.dump(szene, f, separators=(",", ":"))
    n_inst = sum(len(v) for v in platz.values())
    print("EXPORT", {"formen": len(szene["formen"]), "platzierungen": n_inst, "materialien": len(mats),
                     "gespiegelt": gespiegelt, "zeit_s": round(time.time() - t0), "ziel": ZIEL}, flush=True)


def kategorie(o):
    """Fuer Kollision/Nanite in Unreal: gebaeude, boden, fahrzeug, pflanze, figur, sonstiges."""
    cols = {c.name for c in o.users_collection}
    alle = set()
    for c in bpy.data.collections:
        if c.name in cols or any(k.name in cols for k in c.children_recursive):
            alle.add(c.name)
    n = o.name
    if n.startswith(("VEG_", "PROTO_Baum", "PROTO_Bodendecker")) or "08_Vegetation" in alle or n.startswith("PROTO_Ranke"):
        return "pflanze"
    if n.startswith("FIG_") or "09_Figuren" in alle:
        return "figur"
    if n.startswith(("BLD_", "GEO_", "BOD_", "STR_")) or alle & {"01_Gelaende", "02_Strassen", "03_Gebaeude"}:
        return "gebaeude"
    if n.startswith(("FZ_", "MIL_")) or alle & {"04_Fahrzeuge", "05_Militaer"}:
        return "fahrzeug"
    return "sonstiges"


if __name__ == "__main__":
    main()
