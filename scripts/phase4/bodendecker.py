"""Phase 4.1 – Bodenbewuchs (Freigabe 3A: Strassen 60-70 % bewachsen, Trampelpfad 2-3 m in der Mitte frei).

Gras (Phase-2b-Prototypen), hohe Graeser, Kraeuter (Brennnessel, Unkraut, Sauerampfer), Farne im Schatten,
Blumen (Loewenzahn, Schoellkraut, Immergruen, Gazanie) und Straeucher – alles Poly-Haven-Modelle (CC0).
Dichte = Erd-Bedeckung aus Phase 2b (boden.deckung_funktion, gleicher Trampelpfad) x Oberflaechenklasse x Flecken.
Arten wachsen in Gruppen (Noise je Art). Jeder Punkt per Strahl: nur auf Boden, nie in/unter Fahrzeugen oder Haeusern.
Parameter: vegetation.json -> "boden".
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector, noise

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import veg_basis as VB  # noqa: E402
from veg_basis import V  # noqa: E402


def _normieren(o, name):
    """Ursprung unten-mittig, ECHTE Groesse bleibt (flache Rosetten wuerden beim Normieren auf 1 m Hoehe riesig)."""
    o.data = o.data.copy()
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix()
    vs = o.data.vertices
    xs, ys, zs = [v.co.x for v in vs], [v.co.y for v in vs], [v.co.z for v in vs]
    o.data.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs))))
    o.name = name
    return max(max(xs) - min(xs), max(ys) - min(ys)), max(zs) - min(zs)


def _eigenes_teil(o, aid):
    """Nur Teile des Modells selbst (manche Poly-Haven-Dateien enthalten Scan-Reste mit fremden, fehlenden Texturen)."""
    mats = [m for m in o.data.materials if m]
    return bool(mats) and all(m.name.split(".")[0].startswith(aid.split("_")[0]) for m in mats)


def _ist_kugel(o):
    """Hilfskugeln (GN-Platzhalter) in manchen Modellen: alle Punkte ~gleich weit vom Mittelpunkt."""
    vs = [v.co for v in o.data.vertices]
    if len(vs) < 50:
        return False
    m = sum(vs, Vector()) / len(vs)
    d = [(v - m).length for v in vs]
    mittel = sum(d) / len(d)
    return mittel > 0 and (sum((x - mittel) ** 2 for x in d) / len(d)) ** 0.5 / mittel < 0.04


def prototypen(C):
    """Je Gruppe eine Liste (name, collection, skala): eine Collection je Modell, damit Groesse je Modell stimmt."""
    out = {}
    for gname, g in C["gruppen"].items():
        if "quelle" in g:  # Gras aus Phase 2b, getrennt nach gruen / trocken
            col = V.prototypen(f"Bodendecker_{gname}")
            for o in bpy.data.collections[g["quelle"]].objects:
                if g.get("filter") == "trocken" and o.name.endswith("_trocken") or \
                   g.get("filter") == "gruen" and not o.name.endswith("_trocken") or "filter" not in g:
                    col.objects.link(o)
            out[gname] = [(gname, col, None)]
            continue
        out[gname] = []
        for aid in g["modelle"]:
            col = V.prototypen(f"Bodendecker_{gname}_{aid}")
            obs = [o for o in V.modell_laden(aid, col) if o.type == "MESH"]
            bpy.context.view_layer.update()
            basis = {}
            for o in obs:  # je Variante die mittlere Detailstufe (LOD1), sonst die feinste vorhandene
                nm = o.name
                stamm, lod = (nm.rsplit("_LOD", 1) + ["0"])[:2] if "_LOD" in nm else (nm, "0")
                lod = int(lod) if lod.isdigit() else 0
                if stamm not in basis or abs(lod - 1) < abs(basis[stamm][0] - 1):
                    basis[stamm] = (lod, o)
            behalten = {o for _l, o in basis.values() if _eigenes_teil(o, aid) and not _ist_kugel(o)}
            k = 0
            for o in obs:
                if o in behalten:
                    breite, hoehe = _normieren(o, f"VEG_Boden_{gname}_{aid}_{k:02d}")
                    if hoehe < 0.01 or breite > 3.0 or hoehe > g.get("max_hoehe_m", 9.0):  # Reste/Bodenplatten
                        bpy.data.objects.remove(o)
                        continue
                    k += 1
                else:
                    bpy.data.objects.remove(o)
            if k:
                out[gname].append((aid, col, g.get("skala_modell", {}).get(aid, g["skala"])))
    return out


def grasnarbe(C, quelle_col, col):
    """Grasnarbe als Geometry Nodes direkt auf der Erdschicht (Phase 2b): Dichte = Attribut 'deckung' x Noise-Maske.
    Punkte entstehen erst beim Auswerten -> keine gespeicherten Punkte, .blend bleibt klein (AUFTRAG 4.1 Technik)."""
    G = C["grasnarbe"]
    ng = bpy.data.node_groups.get("GN_Grasnarbe") or bpy.data.node_groups.new("GN_Grasnarbe", "GeometryNodeTree")
    ng.nodes.clear()
    if not ng.interface.items_tree:
        ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    deck = N.new("GeometryNodeInputNamedAttribute")
    deck.data_type = "FLOAT"
    deck.inputs["Name"].default_value = "deckung"
    pw = N.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = G["deckung_exponent"]
    L.new(deck.outputs["Attribute"], pw.inputs[0])
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = G["noise_skala"]
    mr = N.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.35, 0.65
    mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 0.25, 1.0
    L.new(nz.outputs["Fac"], mr.inputs["Value"])
    mul = N.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    L.new(pw.outputs[0], mul.inputs[0])
    L.new(mr.outputs["Result"], mul.inputs[1])
    dist = N.new("GeometryNodeDistributePointsOnFaces")
    dist.distribute_method = "RANDOM"
    dist.inputs["Seed"].default_value = G["seed"]
    L.new(gi.outputs["Geometry"], dist.inputs["Mesh"])
    dm = N.new("ShaderNodeMath")  # Blender 5.2: im Modus RANDOM nimmt 'Density' direkt ein Feld
    dm.operation = "MULTIPLY"
    L.new(mul.outputs[0], dm.inputs[0])
    dm.inputs[1].default_value = G["dichte_pro_m2"]
    L.new(dm.outputs[0], dist.inputs["Density"])
    ci = N.new("GeometryNodeCollectionInfo")
    ci.transform_space = "ORIGINAL"
    ci.inputs["Collection"].default_value = quelle_col
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    iop = N.new("GeometryNodeInstanceOnPoints")
    iop.inputs["Pick Instance"].default_value = True
    ri = N.new("FunctionNodeRandomValue")
    ri.data_type = "INT"
    ri.inputs["Min"].default_value = 0
    ri.inputs["Max"].default_value = max(0, len(quelle_col.objects) - 1)
    rr = N.new("FunctionNodeRandomValue")
    rr.data_type = "FLOAT_VECTOR"
    rr.inputs["Min"].default_value = (-0.12, -0.12, 0.0)
    rr.inputs["Max"].default_value = (0.12, 0.12, 6.283)
    e2r = N.new("FunctionNodeEulerToRotation")
    L.new(rr.outputs["Value"], e2r.inputs[0])
    rs = N.new("FunctionNodeRandomValue")
    rs.data_type = "FLOAT"
    rs.inputs["Min"].default_value, rs.inputs["Max"].default_value = G["hoehe_m"]
    hs = N.new("ShaderNodeMath")  # duenner Boden -> niedriger
    hs.operation = "MULTIPLY_ADD"
    L.new(deck.outputs["Attribute"], hs.inputs[0])
    hs.inputs[1].default_value, hs.inputs[2].default_value = 0.5, 0.5
    sm = N.new("ShaderNodeMath")
    sm.operation = "MULTIPLY"
    L.new(rs.outputs["Value"], sm.inputs[0])
    L.new(hs.outputs[0], sm.inputs[1])
    cx = N.new("ShaderNodeCombineXYZ")
    sw = N.new("ShaderNodeMath")
    sw.operation = "MULTIPLY"
    L.new(sm.outputs[0], sw.inputs[0])
    sw.inputs[1].default_value = 1.15
    L.new(sw.outputs[0], cx.inputs["X"])
    L.new(sw.outputs[0], cx.inputs["Y"])
    L.new(sm.outputs[0], cx.inputs["Z"])
    L.new(dist.outputs["Points"], iop.inputs["Points"])
    L.new(ci.outputs[0], iop.inputs["Instance"])
    L.new(ri.outputs["Value"], iop.inputs["Instance Index"])
    L.new(e2r.outputs[0], iop.inputs["Rotation"])
    L.new(cx.outputs[0], iop.inputs["Scale"])
    L.new(iop.outputs["Instances"], go.inputs["Geometry"])
    obs = []
    for quelle in G["flaechen"]:
        q = bpy.data.objects.get(quelle)
        if q is None:
            continue
        ob = bpy.data.objects.new(f"VEG_Grasnarbe_{quelle[4:]}", q.data)  # gleiches Mesh, nur Instanzen als Ausgabe
        col.objects.link(ob)
        ob.matrix_world = q.matrix_world.copy()
        mod = ob.modifiers.new("GN_Grasnarbe", "NODES")
        mod.node_group = ng
        obs.append(ob)
    return obs


def sichtkegel():
    """Hero-Kameras: (Position 2D, Blickrichtung 2D, halber Bildwinkel). Nahe Pflanzen im Bild bleiben niedrig."""
    out = []
    for o in bpy.data.objects:
        if o.name.startswith("CAM_Hero_") and o.type == "CAMERA":
            f = (o.matrix_world.to_3x3() @ Vector((0, 0, -1)))
            f2 = Vector((f.x, f.y)).normalized()
            halb = math.atan(18.0 / o.data.lens) + math.radians(6)
            out.append((Vector((o.matrix_world.translation.x, o.matrix_world.translation.y)), f2, halb))
    return out


def _klasse(C, name):
    for praefix, f in C["klassen"]:
        if name.startswith(praefix):
            return f
    return 0.0


def bauen():
    import boden as BO
    from baeume import _strassen_state
    C = VB.cfg()["boden"]
    r = VB.rnd(21)
    _strassen_state()
    deckung = BO.deckung_funktion(V.config("boden.json"))
    protos = prototypen(C)
    aus = VB.vegetation_ausblenden(("Baeume", "Baeume_Hintergrund", "Ranken"))  # schnellere Strahlen
    S = VB.Strahl()
    col = V.collection("08_Vegetation/Bodendecker")
    kams = [Vector((c.x, c.y)) for c in VB.kameras()]
    kegel = sichtkegel()
    gruppen = list(C["gruppen"].items())
    punkte = {}
    wind = math.radians(C["wind_neigung_grad"])
    wx, wy = math.cos(math.radians(C["wind_richtung_grad"])), math.sin(math.radians(C["wind_richtung_grad"]))
    st = C["raster_m"]
    kandidaten = 0
    for (x0, y0, x1, y1, faktor) in C["bereiche"]:
        y = y0
        while y < y1:
            x = x0
            while x < x1:
                px, py = x + r.uniform(0, st), y + r.uniform(0, st)
                x += st
                kandidaten += 1
                if any((Vector((px, py)) - k).length < C["kamera_frei_m"] for k in kams):
                    continue
                d = deckung(px, py)
                if d < 0:  # im Gebaeude
                    continue
                flecken = 0.5 + 0.5 * noise.noise(Vector((px / C["flecken_m"], py / C["flecken_m"], 9.1)))
                p_basis = faktor * (C["grundwert"] + max(0.0, d) ** 0.7) * (0.55 + 0.9 * flecken)
                if r.random() > p_basis:
                    continue
                b = S.boden(px, py)
                if b is None:
                    continue
                kl = _klasse(C, b[2])
                if r.random() > kl:
                    continue
                # Art waehlen: Gewicht x Gruppen-Noise (Arten wachsen in Gruppen)
                ws = []
                for i, (gname, g) in enumerate(gruppen):
                    gn = 0.5 + 0.5 * noise.noise(Vector((px / C["gruppen_noise_m"], py / C["gruppen_noise_m"], 3.0 + 7.0 * i)))
                    ws.append(g["gewicht"] * (gn ** g.get("gruppierung", 1.5)))
                gname = r.choices([g for g, _ in gruppen], weights=ws)[0]
                g = C["gruppen"][gname]
                if not protos[gname]:
                    continue
                aid, pcol, skala = r.choice(protos[gname])
                h_max = None  # im Sichtkegel nah vor einer Hero-Kamera nur niedriges Gras
                for kp, kf, halb in kegel:
                    v = Vector((px, py)) - kp
                    dk = v.length
                    if dk < C["sichtkegel_m"] and dk > 0.01 and kf.angle(v / dk) < halb:
                        hm = max(0.12, C["sichtkegel_steigung"] * dk - 0.1)
                        h_max = hm if h_max is None else min(h_max, hm)
                if h_max is not None:
                    if skala is not None or gname == "hochgras":
                        continue
                mager = 0.45 + 0.55 * max(0.0, d)  # magerer Boden / Pfadrand -> niedriger
                if skala is None:  # Gras-Prototypen sind 1 m hoch normiert
                    h = r.uniform(*g["hoehe_m"]) * mager
                    if h_max is not None:
                        h = min(h, h_max)
                    sk = (h * r.uniform(0.85, 1.3), h * r.uniform(0.85, 1.3), h)
                else:  # Modelle in echter Groesse x Skala je Modell
                    s = r.uniform(*skala) * (0.6 + 0.4 * mager)
                    sk = (s, s, s * r.uniform(0.9, 1.15))
                k = r.uniform(0.2, 1.0) * wind
                punkte.setdefault((gname, aid), (pcol, []))[1].append(
                    ((px, py, b[0] - 0.015), (-wy * k + r.uniform(-0.08, 0.08), wx * k + r.uniform(-0.08, 0.08),
                                              r.uniform(0, 6.28)), sk, r.randrange(len(pcol.objects))))
            y += st
    VB.vegetation_einblenden(aus)
    narbe = grasnarbe(C, protos["gras_gruen"][0][1], col)
    n = 0
    je = {}
    for (gname, aid), (pcol, pk) in punkte.items():
        V.instanzen(f"VEG_Boden_{gname}_{aid}", pk, pcol, col)
        n += len(pk)
        je[f"{gname}/{aid}"] = len(pk)
    print("BODEN", {"kandidaten": kandidaten, "pflanzen": n, "grasnarbe": [o.name for o in narbe], "je_modell": je,
                    "strahlen": S.n}, flush=True)
