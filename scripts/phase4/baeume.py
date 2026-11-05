"""Phase 4.1 – Baeume: Strassenbaeume (Baumscheiben), Garten- und Platzbaeume, tote und ein umgestuerzter Baum,
Pionierbaeume (Mauerfuss, Dach/Dachrinne, Schutt, Gehwegfugen) und Waldraender im Hintergrund-Ring.
Modelle: Poly Haven CC0 (island_tree_01, island_tree_02, tree_small_02) als verlinkte Kopien.
Parameter: scripts/configs/vegetation.json -> "baeume".
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import veg_basis as VB  # noqa: E402
from veg_basis import V  # noqa: E402

PROTO = {}   # (art, stufe) -> Objekt; stufe: nah / mittel / fern / tot
MASSE = {}   # art -> (hoehe, kronenradius, kronen_unterkante) in Modellgroesse


def prototypen():
    C = VB.cfg()["baeume"]
    col = V.prototypen("Baeume")
    for art, aid in C["modelle"].items():
        nah = VB.link_prototyp(aid, f"{aid}_LOD0", col, f"VEG_Baum_{art}_nah")
        mittel = VB.link_prototyp(aid, f"{aid}_LOD1", col, f"VEG_Baum_{art}_mittel")
        PROTO[(art, "nah")] = nah
        PROTO[(art, "mittel")] = mittel
        PROTO[(art, "fern")] = VB.dezimiert(mittel, C["hintergrund"]["dezimieren"], f"VEG_Baum_{art}_fern", col)
        PROTO[(art, "tot")] = VB.variante(nah, f"VEG_Baum_{art}_tot", col, ("leaves", "branches"))
        MASSE[art] = (nah["h"], nah["r"], nah["zb"])
    return col


def _stufe(p):
    return "nah" if VB.abstand_kamera(p) < VB.cfg()["lod_nah_m"] else "mittel"


def krone_frei(S, x, y, zg, h, r, zb, bld_erlaubt=False):
    """Kein Hindernis (Laterne, Fahrzeug, Wand ...) ragt in die Krone; Stammfuss frei."""
    proben = [(0.0, 0.0)] + [(f * r * math.cos(a), f * r * math.sin(a))
                             for f in (0.4, 0.78) for a in [k * math.pi / 5 for k in range(10)]]
    for dx, dy in proben:
        loc, _n, ob = S.treffer((x + dx, y + dy, zg + h + 6), (0, 0, -1))
        if loc is None or ob.name.startswith(VB.BODEN):
            continue
        grenze = zg + (0.4 if dx == dy == 0.0 else zb)
        if loc.z > grenze and not (bld_erlaubt and ob.name.startswith("BLD_")):
            return False
    return True


def setzen(S, col, art, x, y, hoehe, r, name, stufe=None, tot=False, bld_erlaubt=False, zg=None, mindest=0.6):
    """Baum mit Zielhoehe; bei Hindernis in der Krone schrittweise kleiner (bis mindest * Zielhoehe)."""
    if VB.im_ausschluss(x, y):
        return None
    if zg is None:
        b = S.boden(x, y)
        if b is None:
            return None
        zg = b[0]
    h0, r0, zb0 = MASSE[art]
    for f in (1.0, 0.85, 0.72, mindest):
        s = hoehe * f / h0
        if krone_frei(S, x, y, zg, h0 * s, r0 * s, zb0 * s, bld_erlaubt):
            st = "tot" if tot else (stufe or _stufe((x, y, zg)))
            ob = VB.kopie(PROTO[(art, st)], name, col, (x, y, zg - 0.03), r.uniform(0, 2 * math.pi), s,
                          (r.uniform(-0.04, 0.04), r.uniform(-0.04, 0.04)))
            ob["hoehe_m"] = round(h0 * s, 2)
            return ob
    return None


def _strassen_state():
    import schutt as SCH
    import strassenraum as SR
    SR.L = V.config("layout.json")
    SR.C = V.config("strassenraum.json")
    SR.DETAIL[:] = [tuple(z) for z in SR.C["detail_zonen"]]
    if not SCH.GEB:
        SCH.GEB = [tuple(g["rechteck"]) for g in V.config("gebaeude.json")["gebaeude"]]
    return SR, SCH


def strassenbaeume(S, col, r):
    C = VB.cfg()["baeume"]["strassen"]
    SR, _ = _strassen_state()
    pos = [p for p in SR.baumscheiben_positionen() if -70 < p[0] < 110]
    r.shuffle(pos)
    n = 0
    for (x, y) in pos:
        if n >= C["max_anzahl"] or r.random() > C["anteil_baumscheiben"]:
            continue
        art = "gross" if r.random() < 0.7 else "jung"
        tot = r.random() < C["tot_anteil"]
        if setzen(S, col, art, x, y, r.uniform(*C["hoehe_m"]), r, f"VEG_Baum_Strasse_{n + 1:02d}", tot=tot):
            n += 1
    return n


def _gebaeude(typen=None):
    out = []
    for o in bpy.data.objects:
        if o.name.startswith("BLD_") and "id" in o.keys() and o.visible_get():
            if typen is None or o["typ"] in typen:
                out.append(o)
    rects = {g["id"]: g["rechteck"] for g in V.config("gebaeude.json")["gebaeude"]}
    return [(o, rects[o["id"]]) for o in out if o["id"] in rects]


SEITE = {"S": (0, -1), "N": (0, 1), "W": (-1, 0), "O": (1, 0)}


def gartenbaeume(S, col, r):
    C = VB.cfg()["baeume"]["garten"]
    hs = _gebaeude({2})
    r.shuffle(hs)
    n, kandidaten = 0, []
    for o, (x0, y0, x1, y1) in hs:
        fx, fy = SEITE.get(o.get("front", "S"), (0, -1))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        tief = abs(x1 - x0) / 2 if fx else abs(y1 - y0) / 2
        for seite in (-1, 1):  # Hinterhof, dann Vorgarten
            d = tief + r.uniform(*C["abstand_m"])
            x, y = cx + seite * fx * d + r.uniform(-2, 2) * (1 - abs(fx)), cy + seite * fy * d + r.uniform(-2, 2) * (1 - abs(fy))
            kandidaten.append((x, y, seite, (fx, fy)))
    frei = []
    for kand in kandidaten:
        x, y = kand[0], kand[1]
        if n >= C["anzahl"]:
            frei.append(kand)
            continue
        art = "gross" if r.random() < 0.55 else "knorrig"
        ob = setzen(S, col, art, x, y, r.uniform(*C["hoehe_m"]) * (0.55 if art == "knorrig" else 1.0), r,
                    f"VEG_Baum_Garten_{n + 1:02d}", tot=r.random() < 0.12)
        if ob:
            n += 1
        else:
            frei.append(kand)
    return n, frei


def umgestuerzt(S, col, r, kandidaten):
    """Ein Baum im Vorgarten umgestuerzt, Krone Richtung Strasse ueber dem Zaun."""
    C = VB.cfg()["baeume"]["umgestuerzt"]
    n = 0
    for x, y, seite, (fx, fy) in kandidaten:
        if n >= C["anzahl"] or seite != 1:
            continue
        b = S.boden(x, y)
        if b is None or VB.im_ausschluss(x, y):
            continue
        art = "gross"
        h0, _r0, _zb = MASSE[art]
        s = r.uniform(7.5, 9.0) / h0
        d = Vector((fx, fy, 0)).normalized()
        achse = Vector((-d.y, d.x, 0))
        m = (Matrix.Translation((x, y, b[0] + 0.12 * s)) @ Matrix.Rotation(math.radians(C["kippen_grad"]), 4, achse)
             @ Matrix.Rotation(r.uniform(0, 6.28), 4, "Z") @ Matrix.Diagonal((s, s, s, 1)))
        ob = VB.kopie(PROTO[(art, _stufe((x, y, b[0])))], f"VEG_Baum_Umgestuerzt_{n + 1:02d}", col, matrix=m)
        ob["info"] = "umgestuerzt, Wurzelteller am Boden, Krone Richtung Strasse"
        n += 1
    return n


def platzbaeume(S, col, r):
    C = VB.cfg()["baeume"]["platz"]
    x0, y0, x1, y1 = V.config("layout.json")["platz"]["rechteck"]
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    n = 0
    for _ in range(60):
        if n >= C["anzahl"]:
            break
        x, y = r.uniform(x0 + 3, x1 - 3), r.uniform(y0 + 3, y1 - 3)
        if math.hypot(x - mx, y - my) < 9:  # Brunnen frei
            continue
        if setzen(S, col, "gross", x, y, r.uniform(*C["hoehe_m"]), r, f"VEG_Baum_Platz_{n + 1:02d}"):
            n += 1
    return n


def pionierbaeume(S, col, r):
    """Pioniergehoelze (A14: deutlich hoeher): Mauerfuss, Dachrand/Dachrinne, Schuttkegel, Gehwegfugen."""
    C = VB.cfg()["baeume"]["pionier"]
    n = 0

    def neu(art, x, y, h, zg=None, bld=False, mindest=0.5):
        nonlocal n
        ob = setzen(S, col, art, x, y, h, r, f"VEG_Baum_Pionier_{n + 1:02d}", bld_erlaubt=bld, zg=zg, mindest=mindest)
        if ob:
            n += 1
        return ob

    geb = [g for g in _gebaeude() if -60 < (g[1][0] + g[1][2]) / 2 < 100 and abs((g[1][1] + g[1][3]) / 2) < 70]
    # Mauerfuss
    k = 0
    for _ in range(80):
        if k >= C["mauerfuss"]:
            break
        o, (x0, y0, x1, y1) = r.choice(geb)
        s = r.choice("SNWO")
        fx, fy = SEITE[s]
        t = r.uniform(0.15, 0.85)
        x = x0 + (x1 - x0) * t if fy else (x0 if fx < 0 else x1)
        y = y0 + (y1 - y0) * t if fx else (y0 if fy < 0 else y1)
        d = r.uniform(0.6, 1.3)
        if neu("jung" if r.random() < 0.7 else "knorrig", x + fx * d, y + fy * d, r.uniform(*C["hoehe_m"]), bld=True):
            k += 1
    # Dach / Dachrinne (Flachdaecher beschaedigter Haeuser)
    k = 0
    dach = [g for g in geb if g[0]["typ"] in (1, 3, 5) and g[0].get("zerstoerung") in ("mittel", "schwer")]
    for _ in range(60):
        if k >= C["dach"] or not dach:
            break
        o, (x0, y0, x1, y1) = r.choice(dach)
        x, y = r.uniform(x0 + 0.5, x1 - 0.5), r.choice([y0 + 0.7, y1 - 0.7])
        if r.random() < 0.5:
            x, y = r.choice([x0 + 0.7, x1 - 0.7]), r.uniform(y0 + 0.5, y1 - 0.5)
        tr = S.oben(x, y)
        if tr is None or tr[2] != o or tr[0].z < 5 or tr[1].z < 0.8:
            continue
        if neu("knorrig" if r.random() < 0.5 else "jung", x, y, r.uniform(*C["dach_hoehe_m"]), zg=tr[0].z, bld=True,
               mindest=0.6):
            k += 1
    # Schuttkegel
    k = 0
    schutt = [o for o in bpy.data.objects if o.visible_get() and (o.name.startswith("DEB_Schutt") or o.name.endswith("_Schutt"))]
    r.shuffle(schutt)
    for o in schutt:
        if k >= C["schutt"]:
            break
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        x = sum(v.x for v in bb) / 8 + r.uniform(-1, 1)
        y = sum(v.y for v in bb) / 8 + r.uniform(-1, 1)
        tr = S.oben(x, y)
        if tr is None or tr[2].name.startswith("BLD_"):
            continue
        if neu("jung", x, y, r.uniform(*C["hoehe_m"]) * 0.8, zg=tr[0].z, bld=True):
            k += 1
    # Gehwegfugen (Hauptstrasse)
    k = 0
    for _ in range(80):
        if k >= C["gehweg"]:
            break
        x, y = r.uniform(-60, 100), r.choice([r.uniform(7.6, 9.8), r.uniform(-9.8, -7.6)])
        if neu("jung", x, y, r.uniform(*C["hoehe_m"]) * 0.75):
            k += 1
    return n


def hintergrund(S, col, r):
    """Waldraender und Baumreihen im Hintergrund-Ring (A13) statt der Blockout-Kugeln: Waldflecken per Noise-Maske,
    nur auf freiem Gelaende (Strahl trifft GEO_), als GN-Punkt-Instanzen der vereinfachten Baeume (eine je Art)."""
    from mathutils import noise
    C = VB.cfg()["baeume"]["hintergrund"]
    punkte = {art: [] for art in C["arten_anteil"]}
    arten = list(C["arten_anteil"].items())
    for _ in range(C["kandidaten"]):
        a = r.uniform(0, 2 * math.pi)
        rad = math.sqrt(r.uniform(C["radius_m"][0] ** 2, C["radius_m"][1] ** 2))
        x, y = math.cos(a) * rad, math.sin(a) * rad
        wald = noise.noise(Vector((x / C["flecken_m"], y / C["flecken_m"], 1.7)))
        reihe = noise.noise(Vector((x / 40.0, y / 40.0, 5.1)))
        if wald < C["wald_schwelle"] and abs(reihe) > 0.05:  # ausserhalb Wald: nur schmale Baumreihen/Hecken
            continue
        tr = S.oben(x, y, 500.0)
        if tr is None or not tr[2].name.startswith("GEO_"):
            continue
        z = r.random() * sum(v for _k, v in arten)
        for art, v in arten:
            z -= v
            if z <= 0:
                break
        h0 = MASSE[art][0]
        s = r.uniform(*C["hoehe_m"]) / h0 * (0.6 if art == "knorrig" else 1.0)
        punkte[art].append(((x, y, tr[0].z - 0.15), (r.uniform(-0.05, 0.05), r.uniform(-0.05, 0.05), r.uniform(0, 6.28)),
                            (s, s, s * r.uniform(0.85, 1.15)), 0))
    n = 0
    for art, pk in punkte.items():
        qc = V.prototypen(f"Wald_{art}")
        ob = PROTO[(art, "fern")]
        if ob.name not in qc.objects:
            qc.objects.link(ob)
        V.instanzen(f"VEG_Wald_{art}", pk, qc, col)
        n += len(pk)
    alt = bpy.data.objects.get("VEG_Hintergrund_Baumgruppen")
    if alt:
        bpy.data.objects.remove(alt)
    return n


def bauen():
    r = VB.rnd(1)
    prototypen()
    S = VB.Strahl()
    col = V.collection("08_Vegetation/Baeume")
    col_h = V.collection("08_Vegetation/Baeume_Hintergrund")
    erg = {"strasse": strassenbaeume(S, col, r)}
    erg["garten"], kand = gartenbaeume(S, col, r)
    erg["umgestuerzt"] = umgestuerzt(S, col, r, kand)
    erg["platz"] = platzbaeume(S, col, r)
    erg["pionier"] = pionierbaeume(S, col, r)
    erg["wald"] = hintergrund(S, col_h, r)
    print("BAEUME", erg, "Strahlen", S.n, flush=True)
    return erg
