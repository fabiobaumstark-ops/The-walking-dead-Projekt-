"""Phase 3 – Fahrzeug-Generator: baut ein Fahrzeug aus Grundmodell (fahrzeuge.json) + Farbe + Felge + Seed.

    import fahrzeug as FZ
    root = FZ.bauen("A", farbe="Silber", felge="alu5", seed=3, alter=0.8)

Ergebnis: Empty FZ_<id> (Ursprung = Boden, Mitte zwischen Front und Heck) mit allen Teilen als Kinder.
Tueren/Hauben/Klappen haben ihren Drehpunkt als Ursprung (spaeter: offen/abgesackt per Winkel).
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
import fz_karosserie as K  # noqa: E402
import fz_material as FM  # noqa: E402
import fz_teile as FT  # noqa: E402

INNEN = {"Tuer": "innen_tuer", "Karosserie": "dachhimmel", "Boden": "teppich"}


def cfg():
    return V.config("fahrzeuge.json")


def _drehpunkt(name, P, T):
    """Ursprung (Scharnier) fuer bewegliche Teile in Fahrzeugkoordinaten."""
    if name.startswith("Tuer_"):
        k = 0 if name[5] == "v" else 1
        t = T["tueren"][k]
        s = 1 if name.endswith("l") else -1
        schiebe = len(t) > 2 and t[2] == "schiebe"
        d = t[0] + 0.015
        z = (T["schweller_z"] + P.belt(d)) / 2
        return Vector((P.x(d), s * P.hw(d) * 0.985, z)), ("schiebe" if schiebe else "z")
    if name == "Haube":
        d = T["haube"][1] - 0.02
        return Vector((P.x(d), 0, P.top(d) - 0.01)), "y"
    if name == "Kofferraum":
        d = T["kofferraum"][0] + 0.02
        return Vector((P.x(d), 0, P.top(d) - 0.01)), "y"
    if name == "Heckklappe":
        d = T["heckklappe"] + 0.01
        return Vector((P.x(d), 0, P.top(d) - 0.01)), "y"
    if name == "Hecktuer_m":
        hb = T.get("hecktuer_b", 0.45)
        return Vector((-P.L / 2, hb, (T["stossf_linie"] + P.top(P.L)) / 2)), "z"
    if name.startswith("Hecktuer_"):
        s = 1 if name.endswith("l") else -1
        return Vector((-P.L / 2, s * P.hw(P.L) * 0.98, 1.0)), "z"
    return Vector((0, 0, 0)), None


def _gewichte_tuer(ob, P, piv):
    """Vertex-Gruppe 'dick': unterhalb der Guertellinie volle Tuerdicke, darueber (Fensterrahmen) schmal."""
    vg = ob.vertex_groups.new(name="dick")
    voll = []
    for v in ob.data.vertices:
        w = v.co + piv
        d = P.L / 2 - w.x
        if w.z < P.belt(d) - 0.004:
            voll.append(v.index)
    vg.add(voll, 1.0, "REPLACE")
    return vg


def bauen(typ, farbe="Silber", felge=None, seed=1, alter=0.8, col=None, cid=None, innen=True, variante=0):
    C = cfg()
    T = dict(C["typen"].get(typ) or C["sondertypen"][typ])
    vs = T.get("varianten") or [{}]
    T.update(vs[variante % len(vs)])  # Front-/Heck-Variante (Leuchten, Grill, Stossstange)
    rnd = random.Random(seed)
    felge = felge or T["felgen"][0]
    P = K.Profil(T, C["spalt_m"])
    lo = K.Loft(P)
    kl = lo.zuordnen()
    mats = FM.satz(farbe, C["farben"])
    cid = cid or f"FZ_{typ}_{seed:03d}"
    col = col or V.collection("04_Fahrzeuge")
    root = bpy.data.objects.new(cid, None)
    root.empty_display_size = 1.0
    col.objects.link(root)
    for k, v in (("typ", typ), ("typ_name", T["name"]), ("farbe", farbe), ("felge", felge), ("seed", seed),
                 ("lack_alter", alter), ("variante", variante)):
        root[k] = v

    gruppen = {}
    for f, n in kl.items():
        if n != "SPALT":
            gruppen.setdefault(n, []).append(f)
    teil_obs = {}
    glas_gr = {}
    for n, fl in sorted(gruppen.items()):
        if n.startswith("GLAS_"):
            glas_gr[n] = fl
            continue
        piv, art = _drehpunkt(n, P, T)
        flaechen = [(f, lo.slot(f, n)) for f in fl]
        bm, slots = K.teil_bmesh(lo, flaechen, versatz=piv)
        aussen = [mats[s] for s in slots]
        key = "Tuer" if n.startswith(("Tuer", "Hecktuer")) else n
        innen_m = mats[INNEN.get(key, "dunkel")]
        nslot = len(slots)
        matliste = aussen + [innen_m] * nslot + [mats["dunkel"]] * nslot
        ob = FT.objekt(f"{cid}_{n}", bm, col, matliste, root, loc=piv)
        ob["bauteil"] = n
        if art:
            ob["drehachse"] = art
        dick = ob.modifiers.new("Blech", "SOLIDIFY")
        dick.offset = -1.0
        dick.use_rim = True
        dick.use_even_offset = True
        dick.material_offset = nslot
        dick.material_offset_rim = 2 * nslot
        if key == "Tuer":
            dick.thickness = 0.055
            _gewichte_tuer(ob, P, piv)
            dick.vertex_group = "dick"
            dick.thickness_vertex_group = 0.35
        elif n == "Boden":
            dick.thickness = 0.03
        else:
            dick.thickness = 0.012
        wn = ob.modifiers.new("Normalen", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.mode = "FACE_AREA"
        teil_obs[n] = ob

    # Scheiben (Eltern: Tuer/Klappe, sonst Fahrzeug)
    for n, fl in glas_gr.items():
        teil = n[5:]
        eltern = teil_obs.get(teil)
        if n == "GLAS_Heckfenster":
            eltern = teil_obs.get("Heckklappe")
        piv = eltern.location.copy() if eltern is not None else Vector((0, 0, 0))
        bm = K.glas_bmesh(lo, fl, versatz=piv)
        tl = bm.verts.layers.float.new("tint")
        if n == "GLAS_Frontscheibe":
            zmax = max(v[bm.verts.layers.float["fz_z"]] for v in bm.verts)
            for v in bm.verts:
                v[tl] = 1.0 if v[bm.verts.layers.float["fz_z"]] > zmax - 0.12 else 0.0
        ob = FT.objekt(f"{cid}_{n}", bm, col, [mats["glas"]], eltern if eltern is not None else root)
        g = ob.modifiers.new("Glas", "SOLIDIFY")
        g.thickness = 0.005
        g.offset = -1.0
        ob["bauteil"] = n
        teil_obs[n] = ob

    # Raeder
    me = FT.rad_mesh(typ, T, felge, mats)
    spur = {}
    n_ach = len(P.achsen)
    for ai, a in enumerate(P.achsen):
        an = "v" if ai == 0 else ("h" if ai == 1 and n_ach == 2 else ("h" if ai == n_ach - 1 else f"m{ai}"))
        if n_ach == 3 and ai == 1:
            an = "m"
        for s in (1, -1):
            y = s * (P.hw(a) - P.bw / 2 - 0.035)
            lagen = [(y, "")]
            if P.zwilling and ai > 0:
                lagen.append((y - s * (P.bw + 0.025), "i"))
            for yy, zus in lagen:
                ob = bpy.data.objects.new(f"{cid}_Rad_{an}{'l' if s > 0 else 'r'}{zus}", me)
                ob.location = (P.x(a), yy, P.R)
                ob.rotation_euler = (0, 0, 0 if s > 0 else math.pi)
                ob.parent = root
                col.objects.link(ob)
                ob["reifen_r"] = P.R
                spur[(ai, s, zus)] = ob
    # Anbauteile
    bvh_heck = None
    if T.get("pritsche"):
        bvh_heck = FT.pritsche(lo, T, mats, col, root, cid)
    FT.leuchten(lo, T, mats, col, root, cid, bvh_heck)
    if T.get("kennzeichen"):
        FT.kennzeichen(lo, T, mats, col, root, cid, rnd, bvh_heck)
    tueren = {n: o for n, o in teil_obs.items() if n.startswith("Tuer_")}
    FT.spiegel(lo, T, mats, col, tueren, cid)
    FT.griffe(lo, T, mats, col, tueren, cid)
    FT.wischer(lo, T, mats, col, root, cid)
    FT.antenne(lo, T, mats, col, root, cid)
    FT.dachreling(lo, T, mats, col, root, cid)
    FT.seitenleiste(lo, T, mats, col, root, cid)
    FT.stossfaenger_extra(lo, T, mats, col, root, cid)
    FT.schiebetuer_schiene(lo, T, mats, col, root, cid)
    FT.radlaufleisten(lo, T, mats, col, root, cid)
    FT.leisten_streifen_schrift(lo, T, mats, col, root, cid, rnd, teil_obs)
    if T.get("sattel"):
        FT.sattel_rahmen(lo, T, mats, col, root, cid)
    if T.get("pritsche", {}).get("plane"):
        FT.plane(lo, T, mats, col, root, cid, rnd)
    if T.get("lichtbalken_box"):
        FT.lichter_kasten(lo, T, mats, col, root, cid)
    if T.get("kabinenfenster"):
        de = P.ende
        z0, z1 = P.belt(de) + 0.10, P.top(de) - T["woelbung"] - 0.13
        FT.fenster_patch(lo.bvh, FT._rund((-0.55, z0, 0.55, z1), 0.05), 1, P.x(de) - 1.0, mats, col, root, f"{cid}_Kabinenfenster")
    if T.get("hecktuer_fenster"):
        for s, n in ((1, "Hecktuer_l"), (-1, "Hecktuer_r")):
            tuer = teil_obs.get(n)
            hwr = P.hw(P.L)
            z0, z1 = P.belt(P.L) + 0.05, P.top(P.L) - T["woelbung"] - 0.20
            u0, u1 = sorted((s * 0.08, s * hwr * 0.80))
            FT.fenster_patch(lo.bvh, FT._rund((u0, z0, u1, z1), 0.04), 1, -P.L / 2 - 1.0, mats, col, tuer or root,
                             f"{cid}_{n}_Fenster", tuer.location if tuer else None)
    FT.unterboden(lo, T, mats, col, root, cid)
    if innen:
        FT.innenraum(lo, T, mats, col, root, cid, rnd)
    # Alter/Verwitterung an alle Teile weitergeben
    innen_teile = ("Sitz_", "Rueckbank", "Reihe3", "Armaturen", "Lenkrad", "Innen_Boden", "Sonnenblenden", "Gurte",
                   "Hutablage", "Spritzwand", "Trennwand", "Laderaumboden", "Schalthebel")
    for ob in _kinder(root):
        ob["lack_alter"] = alter
        # Innenraum: geschuetzt -> kaum Moos/Flechten/Staub (bis Scheiben zerbrechen, dann im Schadensmodul hoeher)
        ob["verw_korrektur"] = -0.75 if any(k in ob.name for k in innen_teile) else 0.0
    lo.bm.free()
    return root


def _kinder(root):
    out = []
    for ob in root.children:
        out.append(ob)
        out += _kinder(ob)
    return out
