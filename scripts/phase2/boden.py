"""Phase 2b – Boden nach 10-15 Jahren (AUFTRAG A14): Erdschicht ueber Asphalt und Gehweg (dick an Rinnstein und
Waenden, fleckig auf der Fahrbahn, freier Trampelpfad in der Mitte), Moosflaechen, aufgebrochene Asphaltschollen.
Weiche Raender ueber das Punkt-Attribut 'deckung' (Alpha). Parameter: scripts/configs/boden.json
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


def oberflaeche(x, y):
    return SR.fahrbahn_z(x, y) if SR.ist_fahrbahn(x, y) else SR.gehweg_z(x, y)


def deckungs_material(name, basis, staerke=1.0):
    """Kopie eines Bibliotheks-Materials, Alpha = Attribut 'deckung' (mit Noise-Rand)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = V.material(basis).copy()
    m.name = name
    m.use_fake_user = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_type = "GEOMETRY"
    at.attribute_name = "deckung"
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    rand = V._math(nt, "ADD", at.outputs["Fac"], V._math(nt, "MULTIPLY", V._math(nt, "SUBTRACT", V._noise(nt, geo.outputs["Position"], 3.0, 6.0, 0.65), 0.5), 0.6))
    alpha = V._maprange(nt, rand, 0.16, 0.4, 0.0, staerke)
    nt.links.new(alpha, bsdf.inputs["Alpha"])
    return m


def deckung_funktion(cfg):
    pfad = cfg["pfad"]
    def f(x, y):
        fb = SR.ist_fahrbahn(x, y)
        d_bord = SCH._bordstein_nah(x, y)
        d_wand, _, drin = SCH._abstand_gebaeude(x, y)
        if drin:
            return -1.0
        flecken = 0.5 + 0.5 * noise.noise(Vector((x / cfg["flecken_m"], y / cfg["flecken_m"], 3.3)))
        fein = 0.5 + 0.5 * noise.noise(Vector((x / 1.3, y / 1.3, 7.7)))
        if fb:
            v = cfg["fahrbahn_basis"] * flecken
            v += cfg["rinne"] * max(0.0, 1 - d_bord / cfg["rinne_breite_m"])
            # Trampelpfad in Fahrbahnmitte (leicht geschwungen) bleibt frei
            for s in SR.L["strassen"]:
                if s["achse"] == "x" and abs(y - s["lage"]) < s["fahrbahn"] / 2:
                    mitte = s["lage"] + pfad["schwung_m"] * math.sin(x / pfad["wellenlaenge_m"])
                    v *= min(1.0, abs(y - mitte) / pfad["breite_m"]) ** 1.5
        else:
            v = cfg["gehweg_basis"] * flecken
            v += cfg["wand"] * max(0.0, 1 - d_wand / cfg["wand_breite_m"])
            v += cfg["bordstein_gehweg"] * max(0.0, 1 - d_bord / 0.8)
        return min(1.0, v * (0.75 + 0.5 * fein))
    return f


def erdschicht(cfg, col):
    f = deckung_funktion(cfg)
    st = cfg["raster_m"]
    obs = []
    for (name, basis, dicke, anteil, z_off) in (("BOD_Erdschicht", "MAT_Matsch_Laub", cfg["dicke_m"], 1.0, 0.004),
                                                ("BOD_Moosflaechen", "MAT_Moos", cfg["dicke_m"] * 0.4, cfg["moos_anteil"], 0.012)):
        bm = bmesh.new()
        dl = bm.verts.layers.float.new("deckung")
        for (x0, y0, x1, y1) in cfg["zonen"]:
            nx, ny = int(round((x1 - x0) / st)), int(round((y1 - y0) / st))
            grid = {}
            for j in range(ny + 1):
                for i in range(nx + 1):
                    x, y = x0 + i * st, y0 + j * st
                    d = f(x, y)
                    if d < 0:
                        continue
                    if name == "BOD_Moosflaechen":
                        d = d * anteil * (0.5 + 0.5 * noise.noise(Vector((x / 3.0, y / 3.0, 11.0)))) * 1.6
                    zb = oberflaeche(x, y)
                    v = bm.verts.new((x, y, zb + z_off + dicke * max(0.0, d)))
                    v[dl] = max(0.0, min(1.0, d))
                    grid[i, j] = v
            for j in range(ny):
                for i in range(nx):
                    q = [grid.get(k) for k in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))]
                    if None in q or max(v[dl] for v in q) < 0.08:
                        continue
                    # Bordsteinkante nicht ueberbruecken (Hoehensprung > 8 cm)
                    zs = [v.co.z for v in q]
                    if max(zs) - min(zs) > 0.08:
                        continue
                    bm.faces.new(q)
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        me = bpy.data.meshes.new(name)
        V.uv_welt(bm)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        me.materials.append(deckungs_material(name.replace("BOD_", "MAT_") + "_Deckung", basis))
        for p in me.polygons:
            p.use_smooth = True
        ob.visible_shadow = False if name == "BOD_Moosflaechen" else True
        col.objects.link(ob)
        obs.append(ob)
    return obs


def schollen(cfg, col, rnd):
    """Aufgebrochene Asphaltschollen (gekippt, angehoben), Erde in den Fugen liefert die Erdschicht."""
    bm = bmesh.new()
    for (cx, cy, r) in cfg["schollen_felder"]:
        n = int(r * r * 2.2)
        pts = [(cx + rnd.uniform(-r, r), cy + rnd.uniform(-r, r)) for _ in range(n)]
        for (px, py) in pts:
            if (px - cx) ** 2 + (py - cy) ** 2 > r * r or not SR.ist_fahrbahn(px, py):
                continue
            # unregelmaessiges Polygon (5-7 Ecken), 0,4-0,9 m
            k = rnd.randint(5, 7)
            gr = rnd.uniform(0.25, 0.5)
            ring = []
            for i in range(k):
                a = 2 * math.pi * i / k + rnd.uniform(-0.25, 0.25)
                rr = gr * rnd.uniform(0.7, 1.1)
                ring.append((px + math.cos(a) * rr, py + math.sin(a) * rr))
            kipp = Vector((rnd.uniform(-0.07, 0.07), rnd.uniform(-0.07, 0.07)))
            hub = rnd.uniform(0.01, 0.05)
            z0 = oberflaeche(px, py)
            top = [bm.verts.new((x, y, z0 + hub + kipp.x * (x - px) + kipp.y * (y - py))) for x, y in ring]
            bot = [bm.verts.new((x, y, z0 - 0.04)) for x, y in ring]
            bm.faces.new(top)
            bm.faces.new(bot[::-1])
            for i in range(k):
                j = (i + 1) % k
                bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    V.objekt_aus_bmesh("BOD_Asphaltschollen", bm, col, material=V.material("MAT_Asphalt_Rissig"))


def bauen():
    cfg = V.config("boden.json")
    rnd = random.Random(cfg["seed"])
    if SCH.GEB == []:
        SCH.GEB = [tuple(g["rechteck"]) for g in V.config("gebaeude.json")["gebaeude"]]
    col = V.collection("01_Gelaende/Boden")
    schollen(cfg, col, rnd)
    obs = erdschicht(cfg, col)
    print(f"BODEN: Erdschicht {len(obs[0].data.polygons)} Flaechen, Moos {len(obs[1].data.polygons)} Flaechen")
