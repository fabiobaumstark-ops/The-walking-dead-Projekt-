"""Phase 2b – kleine Vegetation (auf Wunsch aus Phase 4 vorgezogen): Moospolster, Grasbueschel in Rissen und Fugen,
Laub und Erde (Decals + Laubhaufen). Baeume, Bueche, Ranken, Kudzu bleiben in Phase 4.
Parameter: scripts/configs/vegetation_klein.json. Grasbueschel = Poly-Haven-Modelle (CC0), angepasst und verwittert.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import schutt as SCH  # noqa: E402
import strassenraum as SR  # noqa: E402
import viertel_lib as V  # noqa: E402


def boden(x, y):
    return SR.fahrbahn_z(x, y) if SR.ist_fahrbahn(x, y) else SR.gehweg_z(x, y)


# ------------------------------------------------------------------ Prototypen
def gras_prototypen(cfg):
    """Einzelne Grasbueschel aus Poly-Haven-Modellen: Transform in die Mesh-Daten, Ursprung unten-mittig."""
    col = V.prototypen("Gras")
    for aid, max_n in cfg["gras_modelle"]:
        obs = [o for o in V.modell_laden(aid, col) if o.type == "MESH"][:max_n]
        bpy.context.view_layer.update()
        for o in list(col.objects):
            if o.type != "MESH" or o in obs:
                continue
        for o in obs:
            o.data = o.data.copy()
            o.data.transform(o.matrix_world)
            o.matrix_world = Matrix()
            xs = [v.co.x for v in o.data.vertices]
            ys = [v.co.y for v in o.data.vertices]
            zs = [v.co.z for v in o.data.vertices]
            o.data.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs))))
            h = max(zs) - min(zs)
            if h > 0:  # auf 1 m Hoehe normieren, Skalierung erfolgt pro Instanz
                o.data.transform(Matrix.Scale(1.0 / h, 4))
            o.name = f"VEG_Gras_{aid}_{obs.index(o):02d}"
    # ueberzaehlige Objekte (Kinder ohne Mesh / Rest) entfernen
    for o in list(col.objects):
        if not o.name.startswith("VEG_Gras_"):
            bpy.data.objects.remove(o)
    # Farben an die Look-Bible anpassen (Unkraut #5E6B34 gedaempft) + trockene Varianten (#9C8F5E)
    rnd = random.Random(2)
    def hsv_setzen(mat, wert):
        for n in mat.node_tree.nodes:
            if n.type == "HUE_SAT":
                for i, k in enumerate(("Hue", "Saturation", "Value")):
                    n.inputs[k].default_value = wert[i]
                return
    for o in list(col.objects):
        for slot in o.material_slots:
            if slot.material:
                hsv_setzen(slot.material, cfg["gras_hsv"])
        if rnd.random() < cfg["trocken_anteil"]:
            t = o.copy()
            t.data = o.data.copy()
            t.name = o.name + "_trocken"
            col.objects.link(t)
            for slot in t.material_slots:
                if slot.material:
                    m = slot.material.copy()
                    m.name = slot.material.name + "_trocken"
                    hsv_setzen(m, cfg["gras_hsv_trocken"])
                    slot.material = m
    return col


def moos_prototypen():
    col = V.prototypen("Moos")
    rnd = random.Random(4)
    for k in range(5):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.5)
        seed = rnd.random() * 10
        for v in bm.verts:
            n = noise.noise(v.co * 3.0 + Vector((seed, 0, 0)))
            v.co *= 1 + 0.35 * n
            v.co.z = max(v.co.z, -0.05) * 0.22 * (1 + 0.5 * noise.noise(v.co * 9.0))
            v.co.x *= rnd.uniform(0.9, 1.6)
        for f in bm.faces:
            f.smooth = True
        zmin = min(v.co.z for v in bm.verts)
        for v in bm.verts:
            v.co.z -= zmin
        V.objekt_aus_bmesh(f"VEG_Moospolster_{k + 1}", bm, col, material=V.material("MAT_Moos"))
    return col


def laub_prototypen():
    col = V.prototypen("Laub")
    rnd = random.Random(6)
    for k in range(4):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.5)
        seed = rnd.random() * 10
        for v in bm.verts:
            v.co *= 1 + 0.25 * noise.noise(v.co * 2.0 + Vector((seed, 1, 0)))
            v.co.z = max(v.co.z, -0.02) * rnd.uniform(0.12, 0.25)
            v.co.x *= rnd.uniform(1.0, 2.2)
        for f in bm.faces:
            f.smooth = True
        zmin = min(v.co.z for v in bm.verts)
        for v in bm.verts:
            v.co.z -= zmin
        V.objekt_aus_bmesh(f"VEG_Laubhaufen_{k + 1}", bm, col, material=V.material("MAT_Laub_Boden"))
    return col


# ------------------------------------------------------------------ Decals (Laub, Erde, Oel)
def decal_material(name, basis):
    """Kopie eines Bibliotheks-Materials mit weichem, unregelmaessigem Rand (UV-Layer 'Maske')."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = V.material(basis).copy()
    m.name = name
    m.use_fake_user = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "Maske"
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs[0])
    dx = V._math(nt, "SUBTRACT", sep.outputs["X"], 0.5)
    dy = V._math(nt, "SUBTRACT", sep.outputs["Y"], 0.5)
    r = V._math(nt, "SQRT", V._math(nt, "ADD", V._math(nt, "MULTIPLY", dx, dx), V._math(nt, "MULTIPLY", dy, dy)))
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    r = V._math(nt, "ADD", r, V._math(nt, "MULTIPLY", V._math(nt, "SUBTRACT", V._noise(nt, geo.outputs["Position"], 2.5, 5.0, 0.6), 0.5), 0.35))
    alpha = V._maprange(nt, r, 0.5, 0.3)
    nt.links.new(alpha, bsdf.inputs["Alpha"])
    return m


def oel_material():
    name = "MAT_Oelfleck"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = V.mat_farbe(name, "#14120E", 0.15, "MAT_Asphalt_Rissig", rau=0.35, lokal=0.1)
    return m


def decals(cfg, rnd, col, gebaeude_rechtecke):
    """Laub/Erde an Bordsteinen, Waenden, Ecken; Oelflecken auf der Fahrbahn."""
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")   # Haupt-UV (Meter, Fototextur) - zuerst, damit uv_welt() sie nutzt
    uvm = bm.loops.layers.uv.new("Maske")
    def quad(x, y, sx, sy, yaw, mat, off=0.004):
        c, s = math.cos(yaw), math.sin(yaw)
        n = 4
        vs = {}
        for i in range(n + 1):
            for j in range(n + 1):
                lx, ly = (i / n - 0.5) * sx, (j / n - 0.5) * sy
                px, py = x + lx * c - ly * s, y + lx * s + ly * c
                vs[i, j] = bm.verts.new((px, py, boden(px, py) + off))
        for i in range(n):
            for j in range(n):
                f = bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
                f.material_index = mat
                for lp, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    lp[uvm].uv = (a / n, b / n)
    # entlang der Rinnsteine (beide Seiten der Fahrbahnen) im Kamerabereich
    for (x0, x1, y) in cfg["rinnen"]:
        x = x0
        while x < x1:
            if rnd.random() < cfg["rinne_anteil"]:
                l = rnd.uniform(0.8, 3.0)
                off = -0.35 if y > 0 else 0.35
                quad(x + l / 2, y + off, l, rnd.uniform(0.35, 0.8), rnd.uniform(-0.05, 0.05), 0 if rnd.random() < 0.65 else 1, off=0.004)
            x += rnd.uniform(1.0, 4.0)
    # am Wandfuss (Gehwegseite) und in Ecken
    for (x0, y0, x1, y1) in gebaeude_rechtecke:
        for (ax, ay, bx, by, nx, ny) in ((x0, y0, x1, y0, 0, -1), (x0, y1, x1, y1, 0, 1), (x0, y0, x0, y1, -1, 0), (x1, y0, x1, y1, 1, 0)):
            L = math.hypot(bx - ax, by - ay)
            t = 0.0
            while t < L:
                if rnd.random() < cfg["wand_anteil"]:
                    x, y = ax + (bx - ax) * t / L + nx * 0.35, ay + (by - ay) * t / L + ny * 0.35
                    if not SCH._abstand_gebaeude(x, y)[2] and abs(x) < 110 and abs(y) < 110:
                        yaw = math.atan2(by - ay, bx - ax)
                        quad(x, y, rnd.uniform(0.8, 2.4), rnd.uniform(0.4, 0.9), yaw, 0 if rnd.random() < 0.5 else 1, off=0.006)
                t += rnd.uniform(1.5, 4.0)
    # Oelflecken (Fahrbahn, Kamerabereich)
    for k in range(cfg["oelflecken"]):
        x, y = rnd.uniform(-45, 82), rnd.uniform(-6.5, 6.5)
        quad(x, y, rnd.uniform(0.4, 1.4), rnd.uniform(0.3, 1.0), rnd.uniform(0, 3.14), 2, off=0.003)
    mats = [decal_material("MAT_Laub_Decal", "MAT_Laub_Boden"), decal_material("MAT_Erde_Decal", "MAT_Erde"), oel_material()]
    V.uv_welt(bm)  # Haupt-UV (Meter) fuer die Fototextur; 'Maske' bleibt fuer den Rand
    me = bpy.data.meshes.new("VEG_Laub_Erde_Decals")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("VEG_Laub_Erde_Decals", me)
    for mm in mats:
        me.materials.append(mm)
    me.uv_layers.active = me.uv_layers["UVMap"]
    me.uv_layers["UVMap"].active_render = True
    ob.visible_shadow = False
    col.objects.link(ob)


# ------------------------------------------------------------------ Streuung
def streuen(cfg, rnd, gras_col, moos_col, laub_col, col, gebaeude_rechtecke):
    n_gras = len(gras_col.objects)
    n_moos = len(moos_col.objects)
    n_laub = len(laub_col.objects)
    gras, moos, laub = [], [], []
    def g(x, y, h, wind=0.15):
        if SCH._abstand_gebaeude(x, y)[2]:
            return
        z = boden(x, y)
        gras.append(((x, y, z - 0.01), (rnd.uniform(-wind, wind), rnd.uniform(-wind, wind), rnd.uniform(0, 6.28)), (h * rnd.uniform(0.8, 1.3), h * rnd.uniform(0.8, 1.3), h), rnd.randrange(n_gras)))
    def m_(x, y, s, z=None):
        if z is None:
            if SCH._abstand_gebaeude(x, y)[2]:
                return
            z = boden(x, y)
        moos.append(((x, y, z - 0.005), (0, 0, rnd.uniform(0, 6.28)), (s, s * rnd.uniform(0.6, 1.0), s), rnd.randrange(n_moos)))
    # 1) Risse in der Fahrbahn
    for pts in bpy.app.driver_namespace.get("risse", []):
        for (x, y) in pts:
            if rnd.random() < cfg["riss_anteil"]:
                g(x + rnd.uniform(-0.05, 0.05), y + rnd.uniform(-0.05, 0.05), rnd.uniform(0.08, 0.35))
            if rnd.random() < cfg["riss_moos"]:
                m_(x, y, rnd.uniform(0.03, 0.09))
    # 2) Fugen der Gehwegplatten (Raster 1,5 m) + Rinne
    for (x0, x1, y0, y1) in SR.C["gehweg_zonen"]:
        y = y0
        while y <= y1 + 0.01:
            x = x0
            while x < x1:
                if rnd.random() < cfg["fugen_anteil"]:
                    g(x + rnd.uniform(0, 1.5), y + rnd.uniform(-0.02, 0.02), rnd.uniform(0.06, 0.3))
                x += 0.5
            y += 1.5
        x = x0
        while x <= x1 + 0.01:
            yy = y0
            while yy < y1:
                if rnd.random() < cfg["fugen_anteil"]:
                    g(x + rnd.uniform(-0.02, 0.02), yy + rnd.uniform(0, 1.5), rnd.uniform(0.06, 0.3))
                yy += 0.5
            x += 1.5
    for (x0, x1, y) in cfg["rinnen"]:
        x = x0
        while x < x1:
            if rnd.random() < cfg["rinne_gras"]:
                g(x, y + (-0.08 if y > 0 else 0.08), rnd.uniform(0.1, 0.45))
            if rnd.random() < cfg["rinne_moos"]:  # Moos auf dem Bordstein
                m_(x, y + (0.05 if y > 0 else -0.05), rnd.uniform(0.05, 0.12), z=SR.gehweg_z(x, y) - 0.005 + 0.002)
            x += 0.4
    # 3) Gruenstreifen, Baumscheiben (dichter)
    for (bx, by) in bpy.app.driver_namespace.get("baumscheiben", []):
        for k in range(cfg["baumscheibe_gras"]):
            g(bx + rnd.uniform(-0.7, 0.7), by + rnd.uniform(-0.55, 0.55), rnd.uniform(0.15, 0.6))
    # 4) Wandfuss: Gras + Moos (Nordseite mehr Moos)
    for (x0, y0, x1, y1) in gebaeude_rechtecke:
        for (ax, ay, bx, by, nx, ny) in ((x0, y0, x1, y0, 0, -1), (x0, y1, x1, y1, 0, 1), (x0, y0, x0, y1, -1, 0), (x1, y0, x1, y1, 1, 0)):
            L = math.hypot(bx - ax, by - ay)
            if abs((ax + bx) / 2) > 110 or abs((ay + by) / 2) > 110:
                continue
            t = 0.0
            nord = ny > 0
            while t < L:
                x, y = ax + (bx - ax) * t / L + nx * rnd.uniform(0.04, 0.25), ay + (by - ay) * t / L + ny * rnd.uniform(0.04, 0.25)
                if rnd.random() < cfg["wand_gras"]:
                    g(x, y, rnd.uniform(0.1, 0.5))
                if rnd.random() < cfg["wand_moos"] * (2.5 if nord else 1.0):
                    m_(x, y, rnd.uniform(0.06, 0.22))
                t += 0.3
    # 5) Moos auf Checkpoint-Elementen (Sandsaecke, Jersey) und Platz-Brunnen
    for (x, y, z, s) in bpy.app.driver_namespace.get("moos_punkte", []):
        if rnd.random() < 0.6:
            m_(x, y, s, z=z)
    # 6) Laubhaufen in Ecken/Rinnen
    for k in range(cfg["laubhaufen"]):
        x, y = rnd.uniform(-48, 85), rnd.choice([rnd.uniform(-7.0, -6.3), rnd.uniform(6.3, 7.0), rnd.uniform(-11.3, -10.6), rnd.uniform(10.6, 11.3)])
        if SCH._abstand_gebaeude(x, y)[2]:
            continue
        s = rnd.uniform(0.3, 1.1)
        laub.append(((x, y, boden(x, y) - 0.01), (0, 0, rnd.uniform(-0.3, 0.3)), (s, s * rnd.uniform(0.5, 0.9), s * rnd.uniform(0.6, 1.0)), rnd.randrange(n_laub)))
    V.instanzen("VEG_Grasbueschel", gras, gras_col, col)
    V.instanzen("VEG_Moospolster", moos, moos_col, col)
    V.instanzen("VEG_Laubhaufen", laub, laub_col, col)
    return len(gras), len(moos), len(laub)


def bauen():
    cfg = V.config("vegetation_klein.json")
    rnd = random.Random(cfg["seed"])
    if SCH.GEB == []:
        SCH.GEB = [tuple(g["rechteck"]) for g in V.config("gebaeude.json")["gebaeude"]]
    col = V.collection("08_Vegetation/Klein")
    gras_col = gras_prototypen(cfg)
    moos_col = moos_prototypen()
    laub_col = laub_prototypen()
    rects = list(SCH.GEB)
    decals(cfg, rnd, col, rects)
    n = streuen(cfg, rnd, gras_col, moos_col, laub_col, col, rects)
    print(f"VEGETATION_KLEIN: {n[0]} Grasbueschel, {n[1]} Moospolster, {n[2]} Laubhaufen")
