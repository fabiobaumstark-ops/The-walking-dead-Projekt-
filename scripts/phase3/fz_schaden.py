"""Phase 3.1.4/3.1.5 – Schaeden an einem gebauten Fahrzeug (Seed-gesteuert, Anteile laut Auftrag).

    zustand = wuerfeln(rnd, typ)          # Dict mit allen Schaeden
    anwenden(root, zustand)               # veraendert Teile, Materialien, Lage

Alle Winkel in Grad. Tueren links (+y) oeffnen mit negativem Winkel um z, rechts mit positivem.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, HIER)
import viertel_lib as V  # noqa: E402
import fz_material as FM  # noqa: E402

RAEDER = ("vl", "vr", "hl", "hr")


# ---------------------------------------------------------------- Zufall nach Auftrag (3.1.4)
def wuerfeln(rnd, typ, ausgebrannt=None):
    z = {"platt": [], "rad_fehlt": [], "glas": {}, "tueren": {}, "haube": 0.0, "klappe": 0.0,
         "front": 0.0, "heck": 0.0, "seite": None, "ausgebrannt": False, "tuer_weg": None}
    if rnd.random() < 0.70:
        z["platt"] = rnd.sample(RAEDER, rnd.choice((1, 1, 2, 2, 3, 4)))
    if rnd.random() < 0.15:
        z["rad_fehlt"] = rnd.sample(RAEDER, rnd.choice((1, 2, 4)))
    r = rnd.random()
    z["glas"]["Frontscheibe"] = "fehlt" if r < 0.15 else ("gesprungen" if r < 0.55 else "intakt")
    z["glas"]["seiten_bruch"] = 0.5
    z["glas"]["Heck"] = "zerbrochen" if rnd.random() < 0.30 else "intakt"
    if rnd.random() < 0.30:
        for _ in range(rnd.choice((1, 1, 2))):
            z["tueren"][rnd.choice(("Tuer_vl", "Tuer_vr", "Tuer_hl", "Tuer_hr"))] = rnd.uniform(30, 70)
    if rnd.random() < 0.10:
        z["tuer_weg"] = rnd.choice(("Tuer_vl", "Tuer_vr", "Tuer_hl", "Tuer_hr"))
    if rnd.random() < 0.15:
        z["haube"] = rnd.uniform(35, 70)
    if rnd.random() < 0.20:
        z["klappe"] = rnd.uniform(40, 85)
    if rnd.random() < 0.25:
        z["front"] = rnd.uniform(0.3, 1.0)
    if rnd.random() < 0.15:
        z["heck"] = rnd.uniform(0.3, 0.9)
    if rnd.random() < 0.10:
        z["seite"] = (rnd.choice((1, -1)), rnd.uniform(0.3, 0.9))
    z["ausgebrannt"] = (rnd.random() < 0.30) if ausgebrannt is None else ausgebrannt
    if z["ausgebrannt"]:
        z["glas"] = {"alle": "fehlt"}
        z["platt"] = list(RAEDER)
    return z


# ---------------------------------------------------------------- Hilfen
def teile(root):
    out = {}

    def lauf(o):
        for c in o.children:
            out[c.get("bauteil") or c.name.split(root.name + "_", 1)[-1]] = c
            lauf(c)
    lauf(root)
    return out


def tuer_auf(ob, grad, durchhaengen=0.0):
    if ob is None:
        return
    s = -1 if ob.name.endswith("l") else 1
    if ob.get("drehachse") == "schiebe":
        ob.location.x -= min(grad, 70) / 70 * 0.75
        ob.location.y += s * -0.12
        return
    ob.rotation_euler = (0, -math.radians(durchhaengen), math.radians(grad) * s)


def haube_auf(ob, grad):
    if ob is not None:
        ob.rotation_euler.y = -math.radians(grad)


def klappe_auf(ob, grad):
    if ob is not None:
        ob.rotation_euler.y = math.radians(grad)


def _mesh_kopie(ob, suffix):
    me = ob.data.copy()
    me.name = f"{ob.data.name}_{suffix}"
    ob.data = me
    return me


def reifen_platt(rad, staerke=1.0):
    """Reifen unten eingedrueckt, Flanke gewoelbt (eigene Mesh-Kopie)."""
    R = rad["reifen_r"]
    me = _mesh_kopie(rad, "platt")
    bm = bmesh.new()
    bm.from_mesh(me)
    flach = R * (1 - 0.22 * staerke)
    for v in bm.verts:
        if v.co.z < -flach:
            t = (-flach - v.co.z) / (R - flach + 1e-6)
            v.co.z = -flach - (R - flach) * 0.12 * t
            v.co.y *= 1 + 0.10 * staerke * min(1, t * 2)
            v.co.x *= 1 + 0.05 * staerke
    bm.to_mesh(me)
    bm.free()
    rad["platt"] = staerke
    return R - flach - (R - flach) * 0.12


def glas_weg(ob, kruemel_col=None):
    if ob is None:
        return
    ob.hide_render = True
    ob.hide_viewport = True
    ob["zustand"] = "fehlt"


def glas_gesprungen(ob):
    if ob is None:
        return
    m = mat_glas_gesprungen()
    for i in range(len(ob.data.materials)):
        ob.data.materials[i] = m
    ob["zustand"] = "gesprungen"


def mat_glas_gesprungen(name="MAT_Autoglas_Gesprungen"):
    """Spinnennetz-Risse um einen Einschlag (Voronoi-Kanten + radiale Linien), sonst wie MAT_Autoglas."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    basis = FM.autoglas()
    m = basis.copy()
    m.name = name
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 9.0
    nt.links.new(geo.outputs["Position"], vor.inputs["Vector"])
    riss = V._maprange(nt, vor.outputs["Distance"], 0.012, 0.0)
    nah = V._maprange(nt, V._noise(nt, geo.outputs["Position"], 0.8, 2.0), 0.45, 0.6)
    riss = V._math(nt, "MULTIPLY", riss, nah)
    alt = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].links else None
    if alt is not None:
        nt.links.new(V._mix_rgb(nt, riss, alt, V.hex_lin("#E8E8E2")), b.inputs["Base Color"])
    rau_alt = b.inputs["Roughness"].links[0].from_socket if b.inputs["Roughness"].links else None
    if rau_alt is not None:
        nt.links.new(V._math(nt, "MAXIMUM", rau_alt, V._math(nt, "MULTIPLY", riss, 0.8)), b.inputs["Roughness"])
    tw = V._math(nt, "SUBTRACT", 1.0, V._math(nt, "MULTIPLY", riss, 0.7))
    nt.links.new(tw, b.inputs["Transmission Weight"])
    return m


def delle(ob, zentrum_welt, radius, tiefe, richtung):
    """Vertices im Radius entlang 'richtung' verschieben (weicher Abfall + etwas Noise)."""
    if ob is None or ob.type != "MESH":
        return
    from mathutils import noise
    mw = ob.matrix_world
    inv = mw.inverted()
    rl = (inv.to_3x3() @ Vector(richtung)).normalized()
    for v in ob.data.vertices:
        w = mw @ v.co
        d = (w - Vector(zentrum_welt)).length
        if d < radius:
            f = (1 - d / radius) ** 1.6
            f *= 0.75 + 0.5 * noise.noise(w * 7.0)
            v.co += rl * tiefe * f


def ausbrennen(root, T):
    """Ausgebranntes Fahrzeug: Lack -> verbranntes Blech, Kunststoff/Glas/Reifen weg, Innenraum Gerippe."""
    mb = mat_verbrannt()
    for ob in [o for o in root.children_recursive if o.type == "MESH"]:
        n = ob.name
        if "GLAS" in n or "Scheinwerfer_Glas" in n or "Ruecklicht" in n or "Blinker" in n or "Grill" in n \
                or "Lufteinlass" in n or "Spiegel" in n or "Kennzeichen" in n or "Radlaufleisten" in n:
            ob.hide_render = ob.hide_viewport = True
            continue
        if n.endswith(("Sitz_vl", "Sitz_vr", "Rueckbank", "Reihe3", "Rueckbank_Kopfst", "Armaturen", "Lenkrad",
                       "Innen_Boden", "Sonnenblenden", "Gurte", "Hutablage")):
            for i in range(len(ob.data.materials)):
                ob.data.materials[i] = mb
            if "Sitz" in n or "Rueckbank" in n or "Reihe3" in n:
                for mod in list(ob.modifiers):
                    ob.modifiers.remove(mod)
                w = ob.modifiers.new("Gerippe", "WIREFRAME")
                w.thickness = 0.012
            continue
        if "_Rad_" in n:
            _rad_ohne_reifen(ob)
            continue
        for i, m in enumerate(ob.data.materials):
            if m and not m.name.startswith("MAT_Fahrzeug_Dunkel"):
                ob.data.materials[i] = mb
    root["ausgebrannt"] = True


def _rad_ohne_reifen(rad):
    me = _mesh_kopie(rad, "verbrannt")
    bm = bmesh.new()
    bm.from_mesh(me)
    weg = [f for f in bm.faces if f.material_index == 0]
    bmesh.ops.delete(bm, geom=weg, context="FACES")
    bm.to_mesh(me)
    bm.free()
    mb = mat_verbrannt()
    for i in range(len(me.materials)):
        me.materials[i] = mb
    rad["platt"] = 1.0
    rad["ohne_reifen"] = True


def mat_verbrannt(name="MAT_Blech_Verbrannt"):
    """Grau-schwarz verbranntes Blech mit orangebraunem Rost (Fotobasis rusty_metal_04)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = V._neues_mat(name)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    P = geo.outputs["Position"]
    rost = FM._tex(nt, "MAT_Rost_Blech", ("_diff_",), False, 0.8)
    g = FM._tex(nt, "MAT_Rost_Blech", ("_rough_",), True, 0.8)
    russ = V._maprange(nt, V._math(nt, "ADD", V._math(nt, "MULTIPLY", g, 0.5), V._math(nt, "MULTIPLY", V._noise(nt, P, 2.5, 6.0, 0.6), 0.5)), 0.45, 0.6)
    farbe = V._mix_rgb(nt, russ, rost, V.hex_lin("#2A2826"))
    farbe = V._mix_rgb(nt, V._maprange(nt, V._noise(nt, P, 0.9, 3.0), 0.55, 0.7, 0.0, 0.5), farbe, V.hex_lin("#8A8478"))
    grp = V._verw_anschluss(nt, farbe, V._maprange(nt, g, 0, 1, 0.6, 0.95), None, lokal=0.8, kante="#6E3B23")
    nt.links.new(grp.outputs["Farbe"], b.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], b.inputs["Roughness"])
    nt.links.new(grp.outputs["Normale"], b.inputs["Normal"])
    return m


# ---------------------------------------------------------------- Anwenden
def anwenden(root, z, T):
    tl = teile(root)
    # Raeder: platt / fehlt -> Absenkung je Ecke
    senk = {}
    for k in RAEDER:
        rad = next((o for n, o in tl.items() if n.endswith(f"Rad_{k}")), None)
        if rad is None:
            continue
        if k in z["rad_fehlt"]:
            rad.hide_render = rad.hide_viewport = True
            senk[k] = rad["reifen_r"] - 0.14  # steht auf Bremsscheibe/Holzklotz
        elif k in z["platt"] or z["ausgebrannt"]:
            if z["ausgebrannt"]:
                _rad_ohne_reifen(rad)
                senk[k] = rad["reifen_r"] - T["reifen"][0] * 0.0127
            else:
                senk[k] = reifen_platt(rad, 1.0)
        else:
            senk[k] = 0.0
    root["senkung"] = str({k: round(v, 3) for k, v in senk.items()})
    # Glas
    for n, ob in tl.items():
        if not n.startswith("GLAS_"):
            continue
        if z["glas"].get("alle") == "fehlt":
            glas_weg(ob)
        elif n == "GLAS_Frontscheibe":
            st = z["glas"].get("Frontscheibe")
            if st == "fehlt":
                glas_weg(ob)
            elif st == "gesprungen":
                glas_gesprungen(ob)
        elif n in ("GLAS_Heckscheibe", "GLAS_Heckfenster"):
            if z["glas"].get("Heck") == "zerbrochen":
                glas_weg(ob)
        else:
            if random.Random(hash(n) ^ root.get("seed", 0)).random() < z["glas"].get("seiten_bruch", 0.5):
                glas_weg(ob)
    # Tueren, Hauben
    for n, w in z["tueren"].items():
        tuer_auf(tl.get(n), w, durchhaengen=3.0)
    if z.get("tuer_weg") and tl.get(z["tuer_weg"]) is not None:
        ob = tl[z["tuer_weg"]]
        for o in [ob] + list(ob.children_recursive):
            o.hide_render = o.hide_viewport = True
    haube_auf(tl.get("Haube"), z["haube"])
    klappe_auf(tl.get("Kofferraum") or tl.get("Heckklappe"), z["klappe"])
    # Unfallschaeden (Dellen)
    L = T["L"]
    if z["front"] > 0:
        for n in ("Front", "Haube", "Kotfluegel_l", "Kotfluegel_r", "Grill", "Grill_Grund"):
            delle(tl.get(n), (L / 2 + 0.1, 0.25 * random.Random(root.get("seed", 0)).uniform(-1, 1), 0.6), 0.9,
                  0.28 * z["front"], (-1, 0, 0.15))
    if z["heck"] > 0:
        for n in ("Heck", "Kofferraum", "Heckklappe", "Karosserie"):
            delle(tl.get(n), (-L / 2 - 0.1, 0, 0.7), 0.7, 0.2 * z["heck"], (1, 0, 0.05))
    if z["seite"]:
        s, st = z["seite"]
        for n in tl:
            if n.startswith("Tuer_") and n.endswith("l" if s > 0 else "r"):
                delle(tl.get(n), (0, s * (T["B"] / 2 + 0.2), 0.6), 0.8, 0.16 * st, (0, -s, 0))
    if z["ausgebrannt"]:
        ausbrennen(root, T)
    return senk
