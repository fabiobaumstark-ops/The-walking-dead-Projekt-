"""Phase 2.4 – Schutt und Streuobjekte (GN_Schutt_Streuung). Parameter: scripts/configs/schutt.json

Verteilung: dichter an Hauswaenden, Bordsteinen, Ecken, unter zerstoerten Fassaden (Schuttkegel), in der Gasse,
locker auf Fahrbahnen. Glas unter kaputten Fenstern, heruntergefallene Klimageraete und Buchstaben an den
gemerkten Stellen (gebaeude2.boden_teile). Papier/Plastik nach Hauptwind (aus SW) an Hindernissen zusammengeweht.
Kollision: Mindestabstaende je Kategorie, Hoehe immer auf der Oberflaeche (Gehweg/Fahrbahn), nichts in Gebaeuden.
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
import strassenraum as SR  # noqa: E402
import viertel_lib as V  # noqa: E402

RND = None
GEB = []


def _proto_objekt(name, bm, col, mat):
    bm.normal_update()
    # Ursprung an der Unterseite (A5: Props Unterseite)
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
    ob = V.objekt_aus_bmesh(name, bm, col, material=mat)
    return ob


def _stein(rnd, groesse, flach=0.6, subdiv=1):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=0.5)
    seed = rnd.random() * 10
    for v in bm.verts:
        n = noise.noise(v.co * 2.1 + Vector((seed, 0, 0)))
        v.co *= (1 + 0.35 * n)
        v.co.z *= flach
        v.co.x *= rnd.uniform(0.8, 1.3)
    bmesh.ops.scale(bm, vec=(groesse, groesse, groesse), verts=bm.verts)
    return bm


def _ziegel(rnd, bruch=0.0):
    bm = bmesh.new()
    lx = 0.2 * (1 - bruch * rnd.uniform(0.3, 0.6))
    V.box(bm, -lx / 2, -0.0475, 0, lx / 2, 0.0475, 0.057)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.004, segments=1, affect="EDGES", clamp_overlap=True)
    for v in bm.verts:
        v.co += Vector((rnd.uniform(-0.003, 0.003), rnd.uniform(-0.003, 0.003), rnd.uniform(-0.002, 0.002)))
    return bm


def _platte_knautsch(rnd, sx, sy, knick=0.3, aufl=6):
    """Zerknitterte Flaeche (Papier, Kleidung, Karton)."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=aufl, y_segments=aufl, size=0.5)
    seed = rnd.random() * 10
    for v in bm.verts:
        v.co.x *= sx * 2
        v.co.y *= sy * 2
        v.co.z = knick * min(sx, sy) * (0.5 + noise.noise(Vector((v.co.x * 6 / max(sx, 0.05), v.co.y * 6 / max(sy, 0.05), seed))))
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.003)
    return bm


def prototypen_bauen(cfg):
    rnd = random.Random(cfg["seed"] + 1)
    col = V.prototypen("Schutt")
    eintraege = []  # (kategorie, objekt)
    ziegel_mat = V.material("MAT_Ziegelstein") if "MAT_Ziegelstein" in V.config("materialien.json")["abgeleitet"] else V.material("MAT_Ziegel_Verblasst")
    for i, g in enumerate([0.06, 0.1, 0.16, 0.24, 0.34, 0.45, 0.7, 0.95]):
        bm = _stein(rnd, g, rnd.uniform(0.35, 0.6), 1)
        for v in bm.verts:  # kantig: Ecken zufaellig versetzen
            v.co += Vector((rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), rnd.uniform(-0.06, 0.06))) * g
        kat_b = "beton" if i < 6 else "beton_gross"
        eintraege.append((kat_b, _proto_objekt(f"DEB_Betonbrocken_{i + 1:02d}", bm, col, V.material("MAT_Beton_Grob"))))
    for i in range(3):
        eintraege.append(("ziegel", _proto_objekt(f"DEB_Ziegel_{i + 1:02d}", _ziegel(rnd, [0, 0.5, 0.8][i]), col, ziegel_mat)))
    for i in range(2):  # Ziegelhaufen
        bm = bmesh.new()
        for k in range(rnd.randint(18, 34)):
            t = _ziegel(rnd, rnd.choice([0, 0, 0.5]))
            r = rnd.uniform(0, 0.55) ** 0.7
            a = rnd.uniform(0, 6.28)
            z = max(0, 0.32 * (1 - r / 0.6)) * rnd.uniform(0.3, 1.0)
            m = Matrix.Translation((math.cos(a) * r, math.sin(a) * r, z)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z") @ Matrix.Rotation(rnd.uniform(-0.6, 0.6), 4, "X")
            bmesh.ops.transform(t, matrix=m, verts=t.verts)
            SR.einfuegen(bm, t, 0)
        eintraege.append(("ziegelhaufen", _proto_objekt(f"DEB_Ziegelhaufen_{i + 1:02d}", bm, col, ziegel_mat)))
    for i in range(3):  # Glasscherben-Felder
        bm = bmesh.new()
        for k in range(rnd.randint(10, 22)):
            cx, cy = rnd.gauss(0, 0.25), rnd.gauss(0, 0.25)
            s = rnd.uniform(0.02, 0.12)
            vs = [bm.verts.new((cx + rnd.uniform(-s, s), cy + rnd.uniform(-s, s), rnd.uniform(0.001, 0.004))) for _ in range(3)]
            try:
                bm.faces.new(vs)
            except ValueError:
                pass
        eintraege.append(("glas", _proto_objekt(f"DEB_Glasscherben_{i + 1:02d}", bm, col, V.mat_glas("MAT_Glas_Scherben", 1.4))))
    for i in range(3):  # Bretter
        bm = bmesh.new()
        l = rnd.uniform(0.6, 2.0)
        V.box(bm, -l / 2, -rnd.uniform(0.05, 0.1), 0, l / 2, rnd.uniform(0.05, 0.1), 0.022)
        eintraege.append(("holz", _proto_objekt(f"DEB_Brett_{i + 1:02d}", bm, col, V.material("MAT_Holz_Bretter_Alt"))))
    for i in range(4):  # Papier/Zeitungen
        sx, sy = [(0.1, 0.15), (0.15, 0.29), (0.21, 0.15), (0.08, 0.1)][i]  # gefaltete/zerrissene Zeitungsseiten
        eintraege.append(("papier", _proto_objekt(f"DEB_Papier_{i + 1:02d}", _platte_knautsch(rnd, sx, sy, 0.25, 5), col, V.material("MAT_Papier"))))
    for i in range(3):  # Kleidung
        mat = V.material(["MAT_Plane_Oliv", "MAT_Markise_Rot", "MAT_Lack_Blau"][i]) if i < 2 else V.material("MAT_Stoff_Plane")
        eintraege.append(("kleidung", _proto_objekt(f"DEB_Kleidung_{i + 1:02d}", _platte_knautsch(rnd, rnd.uniform(0.3, 0.5), rnd.uniform(0.25, 0.4), 0.6, 8), col, mat)))
    for i in range(2):  # Schuhe
        bm = bmesh.new()
        V.box(bm, -0.14, -0.05, 0, 0.14, 0.05, 0.03)
        V.box(bm, -0.13, -0.045, 0.03, 0.02, 0.045, 0.1)
        V.box(bm, 0.02, -0.04, 0.03, 0.13, 0.04, 0.06)
        eintraege.append(("schuh", _proto_objekt(f"DEB_Schuh_{i + 1:02d}", bm, col, V.material("MAT_Gummi"))))
    for i in range(2):  # Koffer
        bm = bmesh.new()
        w, d, hh = rnd.uniform(0.45, 0.7), 0.22, rnd.uniform(0.35, 0.5)
        V.box(bm, -w / 2, -d / 2, 0, w / 2, d / 2, hh)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.03, segments=2, affect="EDGES", clamp_overlap=True)
        V.box(bm, -0.1, -0.02, hh, 0.1, 0.02, hh + 0.04)
        eintraege.append(("koffer", _proto_objekt(f"PRP_Koffer_{i + 1:02d}", bm, col, V.material(["MAT_Lack_Schwarz", "MAT_Markise_Rot"][i]))))
    bm = bmesh.new()  # Rucksack
    V.box(bm, -0.16, -0.1, 0, 0.16, 0.1, 0.45)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.05, segments=3, affect="EDGES", clamp_overlap=True)
    eintraege.append(("rucksack", _proto_objekt("PRP_Rucksack_01", bm, col, V.material("MAT_Plane_Oliv"))))
    for i in range(2):  # Matratzen (durchgebogen, fleckig)
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=8, y_segments=4, size=0.5)
        for v in bm.verts:
            v.co.x *= 1.9
            v.co.y *= 0.95
            v.co.z = 0.06 * math.sin(v.co.x * 1.6 + i) + 0.04 * noise.noise(v.co * 3)
        bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.18)
        eintraege.append(("matratze", _proto_objekt(f"PRP_Matratze_{i + 1:02d}", bm, col, V.material("MAT_Stoff_Plane"))))
    bm = bmesh.new()  # Einkaufswagen (vereinfacht: Korb aus Drahtflaechen, Rahmen, Raeder)
    for (a, b) in [((-0.45, -0.28, 0.45), (0.45, -0.28, 0.45)), ((-0.45, 0.28, 0.45), (0.45, 0.28, 0.45)),
                   ((-0.45, -0.28, 0.45), (-0.5, -0.22, 0.1)), ((0.45, -0.28, 0.45), (0.4, -0.22, 0.1)),
                   ((-0.45, 0.28, 0.45), (-0.5, 0.22, 0.1)), ((0.45, 0.28, 0.45), (0.4, 0.22, 0.1)),
                   ((0.45, -0.28, 1.0), (0.45, 0.28, 1.0)), ((0.45, -0.28, 0.45), (0.5, -0.28, 1.0)), ((0.45, 0.28, 0.45), (0.5, 0.28, 1.0))]:
        SR.rohr(bm, a, b, 0.01, seg=5, mat=0)
    for (q) in ([(-0.45, -0.28, 0.45), (0.45, -0.28, 0.45), (0.5, -0.3, 0.95), (-0.5, -0.3, 0.95)],
              [(-0.45, 0.28, 0.45), (-0.5, 0.3, 0.95), (0.5, 0.3, 0.95), (0.45, 0.28, 0.45)],
              [(-0.45, -0.28, 0.45), (-0.5, -0.3, 0.95), (-0.5, 0.3, 0.95), (-0.45, 0.28, 0.45)],
              [(-0.45, -0.28, 0.45), (-0.45, 0.28, 0.45), (0.45, 0.28, 0.45), (0.45, -0.28, 0.45)]):
        f = bm.faces.new([bm.verts.new(p) for p in q])
        f.material_index = 1
    for (x, y) in ((-0.5, -0.22), (0.4, -0.22), (-0.5, 0.22), (0.4, 0.22)):
        SR.rohr(bm, (x, y - 0.02, 0.05), (x, y + 0.02, 0.05), 0.05, seg=10, mat=2)
    eintraege.append(("wagen", _proto_objekt("PRP_Einkaufswagen_01", bm, col, [V.material("MAT_Stahl_Verzinkt"), V.mat_maschendraht(), V.material("MAT_Gummi")])))
    for i in range(2):  # Flaschen
        bm = bmesh.new()
        SR.rohr(bm, (0, 0, 0), (0, 0, 0.2), 0.035, seg=10)
        SR.rohr(bm, (0, 0, 0.2), (0, 0, 0.27), 0.035, seg=10, r2=0.012)
        SR.rohr(bm, (0, 0, 0.27), (0, 0, 0.31), 0.012, seg=8)
        m = Matrix.Rotation(math.pi / 2, 4, "Y") if i == 1 else Matrix()
        bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
        eintraege.append(("flasche", _proto_objekt(f"DEB_Flasche_{i + 1:02d}", bm, col, V.mat_glas("MAT_Glas_Flasche", 2.0))))
    bm = bmesh.new()  # heruntergefallenes Klimageraet
    V.box(bm, -0.33, -0.3, 0, 0.33, 0.3, 0.4)
    V.box(bm, -0.3, -0.31, 0.05, 0.3, -0.3, 0.35)
    eintraege.append(("klimageraet", _proto_objekt("DEB_Klimageraet_01", bm, col, V.material("MAT_Metall_Rahmen"))))
    # Poly-Haven-Modelle als zusaetzliche Prototypen (Farben angeglichen, verwittert)
    for kat, aid in cfg["polyhaven"]:
        obs = [o for o in V.modell_laden(aid, col) if o.type == "MESH"]
        if not obs:
            continue
        haupt = obs[0]
        if len(obs) > 1:  # Teile zu einem Objekt zusammenfuehren
            with bpy.context.temp_override(active_object=haupt, selected_editable_objects=obs, selected_objects=obs):
                bpy.ops.object.join()
        haupt.location = (0, 0, 0)
        bpy.context.view_layer.update()
        haupt.data.transform(haupt.matrix_world)  # Rotation/Skalierung anwenden (A5)
        haupt.matrix_world = Matrix()
        zmin = min(v.co.z for v in haupt.data.vertices)
        haupt.data.transform(Matrix.Translation((0, 0, -zmin)))  # Ursprung an der Unterseite
        haupt.name = f"PRP_{aid}"
        eintraege.append((kat, haupt))
    return col, eintraege


def _abstand_gebaeude(x, y):
    """(Abstand zur naechsten Fassade, Aussennormale, drinnen?)"""
    best = (1e9, Vector((0, 0)), False)
    for (x0, y0, x1, y1) in GEB:
        if x0 < x < x1 and y0 < y < y1:
            return (0.0, Vector((0, 0)), True)
        dx = x0 - x if x < x0 else (x - x1 if x > x1 else 0)
        dy = y0 - y if y < y0 else (y - y1 if y > y1 else 0)
        d = math.hypot(dx, dy)
        if d < best[0]:
            n = Vector((-1 if x < x0 else (1 if x > x1 else 0), -1 if y < y0 else (1 if y > y1 else 0)))
            best = (d, n.normalized() if n.length else n, False)
    return best


def _oberflaeche(x, y):
    if SR.ist_fahrbahn(x, y):
        return SR.fahrbahn_z(x, y), "fahrbahn"
    return SR.gehweg_z(x, y), "gehweg"


def _bordstein_nah(x, y):
    """Abstand zur naechsten Bordsteinkante (gerade Strassenkanten)."""
    d = 1e9
    for s in SR.L["strassen"]:
        half = s["fahrbahn"] / 2
        if s["achse"] == "x":
            if s["von"] <= x <= s["bis"]:
                d = min(d, abs(abs(y - s["lage"]) - half))
        else:
            if s["von"] <= y <= s["bis"]:
                d = min(d, abs(abs(x - s["lage"]) - half))
    return d


def verteilen(cfg, eintraege, boden_teile):
    rnd = RND
    kat = {}
    for i, (k, ob) in enumerate(eintraege):
        kat.setdefault(k, []).append(i)
    wind = Vector(cfg["wind_nach"]).normalized()  # Wind weht nach NO
    punkte, belegt = [], {}
    zelle = 0.5

    def frei(x, y, r):
        cx, cy = int(x // zelle), int(y // zelle)
        for i in range(cx - 2, cx + 3):
            for j in range(cy - 2, cy + 3):
                for (px, py, pr) in belegt.get((i, j), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < (r + pr) ** 2:
                        return False
        return True

    def setzen(x, y, k, r, flach=False, gross=1.0, tilt=0.12, yaw=None):
        if not frei(x, y, r):
            return False
        d, n, drin = _abstand_gebaeude(x, y)
        if drin or d < r * 0.6:
            return False
        bd = _bordstein_nah(x, y)
        if bd < r and r > 0.12:  # nichts Grosses auf der Bordsteinkante
            return False
        z, art = _oberflaeche(x, y)
        idx = rnd.choice(kat[k])
        yaw = rnd.uniform(0, 6.28) if yaw is None else yaw
        t = 0.0 if flach else tilt
        s = gross * rnd.uniform(0.75, 1.25)
        punkte.append(((x, y, z - 0.006), (rnd.uniform(-t, t), rnd.uniform(-t, t), yaw), (s, s, s), idx))
        belegt.setdefault((int(x // zelle), int(y // zelle)), []).append((x, y, r * s))
        return True

    x0, y0, x1, y1 = cfg["bereich"]
    hx0, hy0, hx1, hy1 = cfg["hero_bereich"]
    # 1) gemerkte Bodenteile: Glas unter Fenstern, Klimageraete, Buchstaben
    buchstaben = {}
    for (p, art, gid) in boden_teile:
        x, y = p.x + rnd.uniform(-0.3, 0.3), p.y + rnd.uniform(-0.3, 0.3)
        if art == "glas" and rnd.random() < cfg["glas_anteil"]:
            setzen(x, y, "glas", 0.25, flach=True)
        elif art == "klimageraet":
            setzen(x, y, "klimageraet", 0.4, tilt=0.5)
        elif art.startswith("buchstabe:"):
            buchstaben.setdefault(art.split(":")[1], []).append((x, y))
    # 2) Flaechenstreuung nach Dichte
    n_versuche = int((x1 - x0) * (y1 - y0) * cfg["versuche_pro_m2"])
    for _ in range(n_versuche):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        d, n, drin = _abstand_gebaeude(x, y)
        if drin:
            continue
        bd = _bordstein_nah(x, y)
        fb = SR.ist_fahrbahn(x, y)
        hero = hx0 < x < hx1 and hy0 < y < hy1
        dichte = cfg["dichte_fahrbahn"] if fb else cfg["dichte_gehweg"]
        if d < 1.6:
            dichte += cfg["dichte_wand"] * (1 - d / 1.6)
        if fb and bd < 0.6:
            dichte += cfg["dichte_rinne"]
        if cfg["gasse"][0] < x < cfg["gasse"][2] and cfg["gasse"][1] < y < cfg["gasse"][3]:
            dichte += cfg["dichte_gasse"]
        if not hero:
            dichte *= cfg["faktor_ausserhalb"]
        else:
            dichte *= cfg.get("faktor_hero", 1.0)
        dichte *= 0.6 + 0.8 * max(0, noise.noise(Vector((x * 0.08, y * 0.08, 1.7))) + 0.5)
        if rnd.random() > dichte:
            continue
        r = rnd.random()
        luv = max(0.0, n.dot(-wind)) if d < 2.0 else 0.0  # Wand zeigt in den Wind -> Papier sammelt sich davor
        if r < 0.22 + 0.25 * luv:
            k = rnd.choice(["papier", "papier", "plastik", "karton"])
            if k not in kat:
                k = "papier"
            setzen(x, y, k, 0.15, flach=True, yaw=math.atan2(wind.y, wind.x) + rnd.uniform(-0.6, 0.6))
        elif r < 0.45:
            setzen(x, y, "beton", 0.12, gross=rnd.uniform(0.6, 1.0))
        elif r < 0.58:
            setzen(x, y, "ziegel", 0.1)
        elif r < 0.66:
            setzen(x, y, "holz", 0.3, tilt=0.05)
        elif r < 0.72:
            setzen(x, y, "glas", 0.25, flach=True)
        elif r < 0.78:
            setzen(x, y, rnd.choice(["dose", "flasche"]) if "dose" in kat else "flasche", 0.06)
        elif r < 0.83:
            setzen(x, y, "kleidung", 0.25, flach=True)
        elif r < 0.86:
            setzen(x, y, "schuh", 0.08)
        elif r < 0.88:
            setzen(x, y, rnd.choice(["koffer", "rucksack"]), 0.35, tilt=0.6)
        elif r < 0.9:
            setzen(x, y, "reifen", 0.45, tilt=0.4) if "reifen" in kat else None
        elif r < 0.92:
            setzen(x, y, "muell", 0.3) if "muell" in kat else None
        elif r < 0.93:
            setzen(x, y, "matratze", 1.0, tilt=0.08)
        elif r < 0.94:
            setzen(x, y, "moebel", 0.5, tilt=1.2) if "moebel" in kat else None
        elif r < 0.945:
            setzen(x, y, "wagen", 0.6, tilt=0.0 if rnd.random() < 0.6 else 1.4)
        else:
            setzen(x, y, "ziegelhaufen", 0.5)
    # 3) Schuttkegel vor schwer beschaedigten Gebaeuden: zusaetzliche Ziegel/Brocken
    for ob in bpy.data.objects:
        if ob.get("zerstoerung") == "schwer" and ob.get("typ") in (1, 3, 5, 7):
            bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
            cx = sum(v.x for v in bb) / 8
            cy = sum(v.y for v in bb) / 8
            fx, fy = {"S": (0, -1), "N": (0, 1), "W": (-1, 0), "O": (1, 0)}[ob["front"]]
            bx = min(v.x for v in bb) if fx < 0 else max(v.x for v in bb) if fx > 0 else cx
            by = min(v.y for v in bb) if fy < 0 else max(v.y for v in bb) if fy > 0 else cy
            for _ in range(cfg["schutt_pro_schaden"]):
                a = rnd.uniform(-1, 1) * 5
                t = rnd.uniform(0.2, 4.0)
                x = bx + fx * t + (a if fx == 0 else 0)
                y = by + fy * t + (a if fy == 0 else 0)
                setzen(x, y, rnd.choice(["ziegel", "ziegel", "beton", "beton", "beton_gross", "ziegelhaufen", "holz"]), 0.12)
    return punkte, buchstaben


def buchstaben_setzen(buchstaben, col):
    """Abgefallene Schild-Buchstaben (Text-Mesh, liegend)."""
    bm = bmesh.new()
    rnd = RND
    for ch, liste in buchstaben.items():
        for (x, y) in liste:
            z, _ = _oberflaeche(x, y)
            m = Matrix.Translation((x, y, z + 0.006)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z")
            V.text_mesh(bm, ch, 0.38, m, 0, extrude=0.006)
    ob = V.objekt_aus_bmesh("DEB_Schildbuchstaben", bm, col, material=[V.material("MAT_Lack_Weiss")])
    return ob


def bauen():
    global RND, GEB
    cfg = V.config("schutt.json")
    RND = random.Random(cfg["seed"])
    GEB = [tuple(g["rechteck"]) for g in V.config("gebaeude.json")["gebaeude"]]
    proto, eintraege = prototypen_bauen(cfg)
    boden_teile = bpy.app.driver_namespace.get("boden_teile", [])
    punkte, buchstaben = verteilen(cfg, eintraege, boden_teile)
    col = V.collection("07_Props_Schutt/Schutt")
    ob = V.instanzen("DEB_Schutt_Streuung", punkte, proto, col)
    ng = ob.modifiers[0].node_group
    ng.name = "GN_Schutt_Streuung"
    ob["anzahl"] = len(punkte)
    buchstaben_setzen(buchstaben, col)
    print(f"SCHUTT: {len(punkte)} Instanzen, {sum(len(v) for v in buchstaben.values())} Buchstaben")
