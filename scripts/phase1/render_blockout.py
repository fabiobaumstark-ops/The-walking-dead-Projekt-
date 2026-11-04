"""Phase 1 – Vorschau-Renders der Blockout-Szene (A11): alle Hero-Kameras, Draufsicht, Lageplan.

Aufruf:  blender -b viertel_v01.blend --python scripts/phase1/render_blockout.py -- [--schnell] [--nur CAM_Hero_01,...]
Ergebnis: renders/test/phase1_cam1..4.png, phase1_draufsicht.png, phase1_lageplan.png (+ Varianten)
"""
import math
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import viertel_lib as V  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
schnell = "--schnell" in args
nur = args[args.index("--nur") + 1].split(",") if "--nur" in args else None
ausgabe = args[args.index("--out") + 1] if "--out" in args else os.path.join(V.ROOT, "renders", "test")
praefix = args[args.index("--prefix") + 1] if "--prefix" in args else "phase1"
os.makedirs(ausgabe, exist_ok=True)
sc = bpy.context.scene
zeiten = {}


def licht():
    if "LGT_Sonne" in bpy.data.objects:
        return
    hdr = os.path.join(V.ASSETS, "hdri", "kloofendal_28d_misty_puresky_4k.hdr")
    img = bpy.data.images.load(hdr, check_existing=True)
    rot, el = V.hdri_rotation_fuer(img, 265)
    V.hdri_welt(hdr, 1.0, rot)
    V.sonne(265, el, staerke=2.5, kelvin=5000, winkel_grad=2.0, col=V.collection("10_Licht_Atmosphaere"))


def hero():
    for i in range(1, 5):
        name = f"CAM_Hero_0{i}"
        if nur and name not in nur:
            continue
        sc.camera = bpy.data.objects[name]
        t0 = time.time()
        if schnell:
            V.vorschau_render(sc, os.path.join(ausgabe, f"{praefix}_cam{i}.png"), samples=12, breite=480, hoehe=270)
        else:
            V.vorschau_render(sc, os.path.join(ausgabe, f"{praefix}_cam{i}.png"), samples=48)
        zeiten[name] = round(time.time() - t0, 1)


def draufsicht():
    sc.camera = bpy.data.objects["CAM_Draufsicht"]
    sc.camera.data.ortho_scale = 235
    t0 = time.time()
    V.vorschau_render(sc, os.path.join(ausgabe, f"{praefix}_draufsicht.png"), samples=16 if schnell else 32,
                      breite=600, hoehe=540)
    zeiten["Draufsicht"] = round(time.time() - t0, 1)


if __name__ == "__main__":
    licht()
    if not nur or any(n.startswith("CAM_Hero") for n in nur):
        hero()
    if not nur or "draufsicht" in nur:
        draufsicht()
    print("RENDERZEITEN", zeiten)


# ------------------------------------------------------------------ Lageplan (beschriftet)
TYPNAMEN = {1: "Wohnhaus Ziegel", 2: "Holzhaus mit Veranda", 3: "Geschaeftshaus Main Street", 4: "Tankstelle",
            5: "Buerogebaeude", 6: "Krankenhaus", 7: "Parkhaus", 8: "Sonstiges"}


def _legende():
    zeilen = ["# LAGEPLAN – Gebaeude (Phase 1, Blockout)", "",
              "Bild: `renders/test/phase1_lageplan.png` (Norden oben, Massstab 50 m). Farben = Gebaeudetyp.", "",
              "| ID | Objekt | Typ | Geschosse | Hoehe m | Fassade (Bibliothek) | Zerstoerung | Besonderheit |",
              "|---|---|---|---|---|---|---|---|"]
    obs = sorted([o for o in bpy.data.objects if o.get("id")], key=lambda o: o["id"])
    for o in obs:
        bes = ", ".join(str(o[k]) if k != "brand" else "Brandschaden" for k in ("laden", "brand", "kamera_dach", "variante") if k in o.keys())
        zeilen.append(f"| {o['id']} | {o.name} | {o['typ']} {TYPNAMEN[o['typ']]} | {o['geschosse']} | {o['hoehe_m']} | "
                      f"{o['fassade']} (Var. {o['farbe']}) | {o['zerstoerung']} | {bes} |")
    from collections import Counter
    z = Counter(o["zerstoerung"] for o in obs)
    zeilen += ["", f"Summe: {len(obs)} Gebaeude · Zerstoerung leicht {z['leicht']}, mittel {z['mittel']}, schwer {z['schwer']}.",
               "Strassen: Hauptstrasse (Ost-West), Querstrasse Ost (x = 18, Kreuzung mit Ampeln), Querstrasse West (x = -50, Einmuendung),",
               "Gasse hinter B01-B08, Platz mit Brunnen zwischen B29 und B30, eingestuerzte Hochstrasse bei x = 115."]
    open(os.path.join(V.ROOT, "LAGEPLAN.md"), "w", encoding="utf-8").write("\n".join(zeilen) + "\n")
TYPFARBEN = {1: "#B5651D", 2: "#C9A66B", 3: "#A93226", 4: "#5D6D7E", 5: "#5B7DB1", 6: "#E8E8E8", 7: "#7D7D7D", 8: "#6C8E5A"}


def _flachmat(name, hexf):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = V.hex_lin(hexf)
        b.inputs["Roughness"].default_value = 1.0
    return m


def _text(body, x, y, z, groesse, mat, col):
    cu = bpy.data.curves.new(f"TXT_{body}", "FONT")
    cu.body = body
    cu.size = groesse
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new(f"PLAN_Text_{body}", cu)
    ob.location = (x, y, z)
    cu.materials.append(mat)
    col.objects.link(ob)
    return ob


def lageplan(variante=None):
    import json
    col = V.collection("PLAN_Overlay")
    schwarz = _flachmat("PLAN_Schwarz", "#111111")
    blau = _flachmat("PLAN_Strasse_Text", "#F2F2F2")
    # Gebaeude nach Typ einfaerben (nur fuer diesen Render, Datei wird nicht gespeichert)
    for ob in bpy.data.objects:
        if ob.get("id") and ob.type == "MESH":
            m = _flachmat(f"PLAN_Typ{ob['typ']}", TYPFARBEN[ob["typ"]])
            for s in ob.material_slots:
                s.material = m
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            cx = (min(v.x for v in bb) + max(v.x for v in bb)) / 2
            cy = (min(v.y for v in bb) + max(v.y for v in bb)) / 2
            _text(ob["id"], cx, cy, 120, 3.4, schwarz, col)
    for t, x, y in [("Hauptstrasse", -80, 0), ("Querstr. Ost", 18, -92), ("Querstr. West", -50, -92),
                    ("Platz", -17, -46), ("Gasse", -20, 33.3), ("Hochstrasse", 115, 60)]:
        o = _text(t, x, y, 121, 3.6, blau, col)
        if t.startswith("Querstr") or t == "Hochstrasse":
            o.rotation_euler.z = math.radians(90)
    # Massstab 50 m
    bm = __import__("bmesh").new()
    V.box(bm, -100, -104, 119, -50, -102.8, 119.5)
    V.objekt_aus_bmesh("PLAN_Massstab", bm, col, material=schwarz, uv=False)
    _text("50 m", -75, -99.5, 121, 2.8, schwarz, col)
    _text("N ^", 118, 92, 121, 4.0, schwarz, col)
    name = "phase1_lageplan.png"
    if not variante:
        _legende()
    if variante:
        V_ = json.load(open(os.path.join(V.CONFIGS, "platzierung_varianten.json"), encoding="utf-8"))
        el, var = V_["elemente"], V_["varianten"][variante]
        for key, rect in var.items():
            if key == "titel":
                continue
            m = _flachmat(f"PLAN_El_{key}", el[key]["farbe"])
            bm = __import__("bmesh").new()
            V.box(bm, rect[0], rect[1], 122, rect[2], rect[3], 122.3)
            V.objekt_aus_bmesh(f"PLAN_{key}", bm, col, material=m, uv=False)
            _text(key, (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2, 123, 3.0, _flachmat("PLAN_Weiss", "#FFFFFF"), col)
        _text(var["titel"], 10, 100, 121, 4.2, schwarz, col)
        name = f"phase1_lageplan_variante_{variante}.png"
    # Planansicht: Cycles mit gleichmaessigem weissen Himmel (kein OpenGL noetig)
    welt = bpy.data.worlds.get("PLAN_Welt") or bpy.data.worlds.new("PLAN_Welt")
    welt.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    welt.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.15
    alt_welt = sc.world
    sc.world = welt
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.hide_render = True
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 16
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Standard"
    sc.camera = bpy.data.objects["CAM_Draufsicht"]
    sc.camera.data.ortho_scale = 235
    sc.camera.location.x, sc.camera.location.y = 10, -2
    sc.render.resolution_x, sc.render.resolution_y = 600, 540
    sc.render.filepath = os.path.join(ausgabe, name)
    bpy.ops.render.render(write_still=True)
    sc.world = alt_welt
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.hide_render = False
    for o in list(col.objects):
        bpy.data.objects.remove(o)

if __name__ == "__main__" and (not nur or "lageplan" in nur):
    lageplan()
    for v in ("A", "B", "C"):
        lageplan(v)
