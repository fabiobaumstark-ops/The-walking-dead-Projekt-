"""Phase 4.1 – Kletterpflanzen (Freigabe 2A: eigener Generator, Blaetter aus ambientCG-Fotos CC0).

- Efeu / Wilder Wein an Fassaden: von unten wachsend, Schattenseite (N/O) haeufiger, teils ganze Fassaden (A14).
  Jeder Blattbueschel wird per Strahl von aussen auf die echte Fassade gesetzt (keine schwebenden Blaetter vor
  Fensterhoehlen; Gesimse, Feuertreppen und Bruchkanten werden mitbewachsen).
- Haengende Ranken an Dachkanten, Kudzu-Decken auf einzelnen Holzhaeusern.
- Ranken an Strommasten, am Heckausleger des Hubschraubers und an geparkten Autos (Flaechen-Stichproben).
Blattbueschel = kleine Meshes aus Fotoblatt-Karten, als GN-Punkt-Instanzen (A9). Parameter: vegetation.json -> "ranken".
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
import veg_basis as VB  # noqa: E402
from veg_basis import V  # noqa: E402

# Atlas-Raster: (Spalten, Zeilen, Blattspitze zeigt nach 'oben' oder 'rechts')
ATLAS = {"MAT_Blatt_Efeu_A": (2, 3, "oben"), "MAT_Blatt_Efeu_B": (3, 3, "rechts"), "MAT_Blatt_Wein": (3, 3, "oben")}


# ------------------------------------------------------------------ Material
def blatt_material(asset_mat, hsv, transluzenz=0.35):
    name = f"VEG_{asset_mat}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    eintrag = next(a for a in V.manifest()["assets"] if a["name"] == asset_mat)
    ordner = os.path.join(V.ROOT, eintrag["zielpfad"])
    m, nt, b = V._neues_mat(name)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    uv = nt.nodes.new("ShaderNodeUVMap")

    def tex(muster, nicht_farbe):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = V._bild(V._karte(ordner, muster), nicht_farbe)
        nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
        return t
    farbe_t, alpha_t = tex("_color", False), tex("_opacity", True)
    rau_t, nor_t = tex("_roughness", True), tex("_normalgl", True)
    # Look-Bible: gedaempftes Gruen; je Instanz leichte Variation (Object Info > Random)
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    nt.links.new(farbe_t.outputs["Color"], hs.inputs["Color"])
    nt.links.new(V._math(nt, "ADD", hsv[0] - 0.03, V._math(nt, "MULTIPLY", oi.outputs["Random"], 0.06)), hs.inputs["Hue"])
    hs.inputs["Saturation"].default_value = hsv[1]
    nt.links.new(V._math(nt, "ADD", hsv[2] - 0.12, V._math(nt, "MULTIPLY", oi.outputs["Random"], 0.24)), hs.inputs["Value"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.6
    nt.links.new(nor_t.outputs["Color"], nm.inputs["Color"])
    rau = V._maprange(nt, rau_t.outputs["Color"], 0.0, 1.0, 0.45, 0.8, smooth=False)
    grp = V._verw_anschluss(nt, hs.outputs["Color"], rau, nm.outputs["Normal"], lokal=0.2, kante="#6E7A3E")
    nt.links.new(grp.outputs["Farbe"], b.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], b.inputs["Roughness"])
    nt.links.new(grp.outputs["Normale"], b.inputs["Normal"])
    # duennes Blatt: etwas Licht scheint durch (wichtig fuer das Gegenlicht in Phase 5)
    tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(V._mix_rgb(nt, 1.0, grp.outputs["Farbe"], (0.95, 1.0, 0.55, 1), "MULTIPLY"), tl.inputs["Color"])
    nt.links.new(grp.outputs["Normale"], tl.inputs["Normal"])
    m1 = nt.nodes.new("ShaderNodeMixShader")
    m1.inputs["Fac"].default_value = transluzenz
    nt.links.new(b.outputs[0], m1.inputs[1])
    nt.links.new(tl.outputs[0], m1.inputs[2])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    m2 = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(alpha_t.outputs["Color"], m2.inputs["Fac"])
    nt.links.new(tr.outputs[0], m2.inputs[1])
    nt.links.new(m1.outputs[0], m2.inputs[2])
    nt.links.new(m2.outputs[0], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ Blattbueschel
def _blatt(bm, uvl, asset_mat, rnd, pos, roll, kipp, groesse, zelle=None):
    sp, ze, spitze = ATLAS[asset_mat]
    c = zelle if zelle is not None else rnd.randrange(sp * ze)
    u0, v0 = (c % sp) / sp, (c // sp) / ze
    du, dv = 1.0 / sp, 1.0 / ze
    w, h = groesse * (du / dv if spitze == "oben" else dv / du), groesse
    R = Matrix.Rotation(roll, 3, "Y") @ Matrix.Rotation(kipp, 3, "X")
    ecken = [(-w / 2, 0), (w / 2, 0), (w / 2, h), (-w / 2, h)]
    vs = [bm.verts.new(R @ Vector((s, 0, t)) + pos) for s, t in ecken]
    f = bm.faces.new(vs)
    for lp, (s, t) in zip(f.loops, ecken):
        a, b = s / w + 0.5, t / h
        lp[uvl].uv = (u0 + a * du, v0 + b * dv) if spitze == "oben" else (u0 + b * du, v0 + (1 - a) * dv)


def bueschel(name, asset_mat, rnd, n, ausdehnung, dicke, blattgroesse, art="efeu"):
    """Mesh im lokalen Raum: Wand-Normale = +Y, oben = +Z, Ursprung auf der Wand."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for _ in range(n):
        a, r = rnd.uniform(0, 2 * math.pi), ausdehnung / 2 * math.sqrt(rnd.random())
        mitte = Vector((r * math.cos(a), rnd.uniform(0.01, dicke), r * math.sin(a)))
        if art == "efeu":  # Blattspitzen meist nach unten, Blattflaeche zum Licht, vom Stiel abgestellt
            roll = rnd.uniform(math.radians(120), math.radians(240)) if rnd.random() < 0.7 else rnd.uniform(-1.6, 1.6)
            _blatt(bm, uvl, asset_mat, rnd, mitte, roll, rnd.uniform(-0.9, -0.15), blattgroesse * rnd.uniform(0.7, 1.3))
        else:  # Kudzu: 3 Teilblaetter, Wein: 5 Teilblaetter (handfoermig)
            k = 3 if art == "kudzu" else 5
            basis = rnd.uniform(0, 2 * math.pi)
            kipp = rnd.uniform(-1.1, -0.2)
            for j in range(k):
                roll = basis + (j - (k - 1) / 2) * (1.0 if k == 3 else 0.62)
                _blatt(bm, uvl, asset_mat, rnd, mitte, roll, kipp + rnd.uniform(-0.2, 0.2),
                       blattgroesse * rnd.uniform(0.75, 1.2) * (1.15 if j == (k - 1) // 2 else 0.9))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bpy.data.materials[f"VEG_{asset_mat}"])
    return me


def prototypen(C):
    for asset_mat, hsv in C["blatt_hsv"].items():
        blatt_material(asset_mat, hsv)
    r = VB.rnd(11)
    out = {}
    for typ, p in C["bueschel"].items():
        col = V.prototypen(f"Ranken_{typ}")
        for k in range(p["varianten"]):
            am = p["blatt"][k % len(p["blatt"])]
            me = bueschel(f"VEG_Ranke_{typ}_{k}", am, r, p["blaetter"], p["ausdehnung"], p["dicke"], p["blattgroesse"],
                          p.get("art", "efeu"))
            ob = bpy.data.objects.new(me.name, me)
            col.objects.link(ob)
        out[typ] = col
    return out


# ------------------------------------------------------------------ Ausrichtung
def euler_aus_normale(n, roll=0.0):
    """Rotation, die lokal +Y auf die Normale n und lokal +Z moeglichst nach oben dreht (+ Drehung um n)."""
    y = Vector(n).normalized()
    hilf = Vector((0, 0, 1)) if abs(y.z) < 0.92 else Vector((1, 0, 0))
    x = y.cross(hilf).normalized()  # rechtshaendig (x × y = z), sonst Spiegelung statt Drehung
    z = x.cross(y)
    M = Matrix((x, y, z)).transposed()
    return (Matrix.Rotation(roll, 3, y) @ M).to_euler("XYZ")


# ------------------------------------------------------------------ Fassaden
SEITEN = {"S": (0, -1), "N": (0, 1), "W": (-1, 0), "O": (1, 0)}


def _fassaden():
    rects = {g["id"]: g for g in V.config("gebaeude.json")["gebaeude"]}
    out = []
    for o in bpy.data.objects:
        if o.name.startswith("BLD_") and "id" in o.keys() and o.visible_get() and o["id"] in rects:
            out.append((o, rects[o["id"]]["rechteck"], float(o.get("hoehe_m", 10.0))))
    return out


def fassaden_bewuchs(S, C, punkte, r):
    F = C["fassaden"]
    n_fass = 0
    alle = _fassaden()
    for o, (x0, y0, x1, y1), H in alle:
        for s, (nx, ny) in SEITEN.items():
            if r.random() > F["anteil_seite"][s] + (F["front_bonus"] if o.get("front") == s else 0.0):
                continue
            n_fass += 1
            if ny:
                a, b = Vector((x0, y0 if ny < 0 else y1, 0)), Vector((x1, y0 if ny < 0 else y1, 0))
            else:
                a, b = Vector((x0 if nx < 0 else x1, y0, 0)), Vector((x0 if nx < 0 else x1, y1, 0))
            L = (b - a).length
            t = (b - a).normalized()
            n = Vector((nx, ny, 0))
            typ = r.choices(list(F["typen"]), weights=[v["gewicht"] for v in F["typen"].values()])[0]
            T = F["typen"][typ]
            art = "wein" if (s in ("S", "W") and r.random() < F["wein_anteil_sonnenseite"]) else "efeu"
            # Wuchsherde entlang der Fassade, Obergrenze mit Noise
            herde = [(r.uniform(0, L), r.uniform(*T["breite_m"]), r.uniform(*T["hoehe_anteil"]))
                     for _ in range(max(1, int(L / T["herd_abstand_m"])))]
            mitte_f = (a + b) / 2 + n * 2.0
            d_cam = VB.abstand_kamera((mitte_f.x, mitte_f.y, H / 2))
            stufe = "nah" if d_cam < F["lod_m"][0] else ("mittel" if d_cam < F["lod_m"][1] else "fern")
            raster = F["raster_m"][stufe] * T.get("raster_faktor", 1.0)
            seed_f = r.uniform(0, 100)
            andere = [rc for oo, rc, _h in alle if oo["id"] != o["id"]]
            u = r.uniform(0, raster)
            while u < L:
                pa = a + t * u + n * 0.6
                if any(rx0 < pa.x < rx1 and ry0 < pa.y < ry1 for rx0, ry0, rx1, ry1 in andere):  # Nachbarwand
                    u += raster
                    continue
                oben = H * max(f * math.exp(-((u - u0) / w) ** 2) for u0, w, f in herde)
                oben *= 1 + 0.18 * noise.noise(Vector((u / 2.5, seed_f, 0.5)))
                aussen = a + t * u + n * 2.0
                bz = S.boden(aussen.x, aussen.y)
                zg = bz[0] if bz else 0.0
                z = r.uniform(0, raster) + 0.05
                while z < oben:
                    rel = z / max(oben, 0.1)
                    loch = noise.noise(Vector((u / 1.6, z / 1.6, seed_f)))
                    if loch > -0.45 + 0.75 * rel ** 3:
                        start = aussen + Vector((0, 0, zg + z))
                        loc, nor, hit = S.treffer(start, -n, 3.2)
                        if loc is not None and hit.name.startswith("BLD_"):
                            if nor.dot(n) < 0:
                                nor = -nor
                            p = loc + nor * 0.015
                            sk = r.uniform(0.8, 1.25) * (1.0 - 0.25 * rel)
                            punkte[(art, stufe)].append(((p.x, p.y, p.z), tuple(euler_aus_normale(nor, r.uniform(-0.5, 0.5))),
                                                          (sk, sk, sk), 0))
                    z += raster * r.uniform(0.8, 1.2)
                u += raster * r.uniform(0.8, 1.2)
            # haengende Ranken von der Dachkante (vor allem bei 'voll' und 'hoch')
            if r.random() < F["haengend_anteil"].get(typ, 0.0):
                for _ in range(r.randint(*F["haengend_anzahl"])):
                    uu = r.uniform(0.3, L - 0.3)
                    laenge = r.uniform(*F["haengend_laenge_m"])
                    aussen = a + t * uu + n * 2.0
                    bz = S.boden(aussen.x, aussen.y)
                    zg = bz[0] if bz else 0.0
                    loc, nor, hit = S.treffer(aussen + Vector((0, 0, zg + H - 0.4)), -n, 3.2)
                    if loc is None:
                        continue
                    zz = 0.0
                    while zz < laenge:
                        schwung = 0.06 * math.sin(zz * 1.7 + uu)
                        p = loc + n * (0.05 + 0.04 * zz + schwung) - Vector((0, 0, zz))
                        sk = r.uniform(0.6, 0.9) * (1 - 0.4 * zz / laenge)
                        punkte[(art, stufe)].append(((p.x, p.y, p.z), tuple(euler_aus_normale(n, r.uniform(-0.6, 0.6))),
                                                      (sk, sk, sk), 0))
                        zz += F["raster_m"][stufe] * 0.8
    return n_fass


# ------------------------------------------------------------------ Kudzu-Haeuser
def kudzu_haeuser(S, C, punkte, r):
    K = C["kudzu"]
    haeuser = [(o, rect, H) for o, rect, H in _fassaden() if o.get("typ") == 2]
    haeuser.sort(key=lambda h: -VB.abstand_kamera(((h[1][0] + h[1][2]) / 2, (h[1][1] + h[1][3]) / 2, 0)))
    n = 0
    for o, (x0, y0, x1, y1), H in haeuser[:K["haeuser"]]:
        n += 1
        st = K["raster_m"]
        x = x0 - 1.0
        while x < x1 + 1.0:
            y = y0 - 1.0
            while y < y1 + 1.0:
                tr = S.oben(x + r.uniform(-0.2, 0.2), y + r.uniform(-0.2, 0.2))
                if tr is not None and (tr[2].name.startswith("BLD_") or VB.ist_boden(tr[2].name)):
                    p = tr[0] + tr[1] * 0.05
                    sk = r.uniform(0.85, 1.3)
                    punkte[("kudzu", "mittel")].append(((p.x, p.y, p.z), tuple(euler_aus_normale(tr[1], r.uniform(-3, 3))),
                                                        (sk, sk, sk), 0))
                y += st
            x += st
        # Waende ringsum
        for s, (nx, ny) in SEITEN.items():
            nvec = Vector((nx, ny, 0))
            if ny:
                a, b = Vector((x0, y0 if ny < 0 else y1, 0)), Vector((x1, y0 if ny < 0 else y1, 0))
            else:
                a, b = Vector((x0 if nx < 0 else x1, y0, 0)), Vector((x0 if nx < 0 else x1, y1, 0))
            L = (b - a).length
            t = (b - a).normalized()
            u = 0.0
            while u < L:
                z = 0.1
                while z < H * 1.05:
                    loc, nor, hit = S.treffer(a + t * u + nvec * 2.5 + Vector((0, 0, z)), -nvec, 3.5)
                    if loc is not None and not hit.name.startswith(("VEG_",)):
                        if nor.dot(nvec) < 0:
                            nor = -nor
                        p = loc + nor * 0.05
                        sk = r.uniform(0.85, 1.3)
                        punkte[("kudzu", "mittel")].append(((p.x, p.y, p.z), tuple(euler_aus_normale(nor, r.uniform(-3, 3))),
                                                            (sk, sk, sk), 0))
                    z += st
                u += st
    return n


# ------------------------------------------------------------------ Objekte (Masten, Heckausleger, Autos)
def _flaechen_punkte(obs, dichte, r, filt):
    """Zufallspunkte auf den Flaechen der Objekte (ausgewertet, Weltkoordinaten), flaechengewichtet."""
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for ob in obs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ob.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        for pg in me.polygons:
            c = mw @ pg.center
            nrm = (nm @ pg.normal).normalized()
            fl = pg.area * (mw.to_scale()[0] ** 2)
            k = fl * dichte
            while k > 0:
                if r.random() < min(k, 1.0):
                    vs = [mw @ me.vertices[i].co for i in pg.vertices]
                    w = [r.random() for _ in vs]
                    sw = sum(w)
                    p = sum((v * (wi / sw) for v, wi in zip(vs, w)), Vector())
                    if filt(ob, p, nrm):
                        out.append((p, nrm))
                k -= 1.0
        ev.to_mesh_clear()
    return out


def objekt_bewuchs(S, C, punkte, r):
    O = C["objekte"]
    n = 0
    # Strommasten: einzelne Masten (per Position gehasht) bis zu einer zufaelligen Hoehe
    masten = [o for o in bpy.data.objects if o.name.startswith("STR_Strommasten") and o.visible_get()]

    def mast_ok(ob, p, nrm):
        h = random.Random(int(round(p.x / 3.0)) * 7919 + int(round(p.y / 3.0)))
        if h.random() > O["mast_anteil"]:
            return False
        return p.z < h.uniform(*O["mast_hoehe_m"]) and abs(nrm.z) < 0.7
    for p, nrm in _flaechen_punkte(masten, O["dichte_pro_m2"], r, mast_ok):
        sk = r.uniform(0.6, 1.0)
        punkte[("efeu", "mittel")].append(((p + nrm * 0.02)[:], tuple(euler_aus_normale(nrm, r.uniform(-1, 1))), (sk, sk, sk), 0))
        n += 1
    # Heckausleger des Hubschraubers (haengt herunter, Ranken von unten)
    heck = [o for o in bpy.data.objects if o.name.startswith("MIL_Hubschrauber_Heckausleger") and o.type == "MESH"]
    zb = min((o.matrix_world @ Vector(c)).z for o in heck for c in o.bound_box) if heck else 0.0

    def heck_ok(ob, p, nrm):
        return p.z < zb + O["heck_hoehe_m"] and noise.noise(p * 1.3) > -0.2
    for p, nrm in _flaechen_punkte(heck, O["dichte_pro_m2"] * 1.5, r, heck_ok):
        sk = r.uniform(0.6, 1.0)
        punkte[("efeu", "nah")].append(((p + nrm * 0.02)[:], tuple(euler_aus_normale(nrm, r.uniform(-1, 1))), (sk, sk, sk), 0))
        n += 1
    # geparkte Autos (seit Jahren unberuehrt): Ranken an Raedern und unterer Karosserie
    autos = sorted({o.name.split("_")[1] + "_" + o.name.split("_")[2] for o in bpy.data.objects if o.name.startswith("FZ_Geparkt_")})
    gewaehlt = set(r.sample(autos, max(1, int(len(autos) * O["auto_anteil"])))) if autos else set()
    teile = [o for o in bpy.data.objects if o.type == "MESH" and o.visible_get() and o.name.startswith("FZ_Geparkt_")
             and "_".join(o.name.split("_")[1:3]) in gewaehlt and "GLAS" not in o.name and "Innen" not in o.name]
    boden_z = {}

    def auto_ok(ob, p, nrm):
        key = "_".join(ob.name.split("_")[:3])
        if key not in boden_z:  # Fahrzeug-Ursprung = Mitte Unterkante (A5) ~ Boden
            root = bpy.data.objects.get(key)
            boden_z[key] = root.matrix_world.translation.z if root else p.z - 0.5
        return p.z < boden_z[key] + O["auto_hoehe_m"] + 0.25 * noise.noise(p * 2.0) and nrm.z < 0.6
    for p, nrm in _flaechen_punkte(teile, O["dichte_pro_m2"], r, auto_ok):
        sk = r.uniform(0.5, 0.85)
        punkte[("efeu", "nah")].append(((p + nrm * 0.02)[:], tuple(euler_aus_normale(nrm, r.uniform(-1, 1))), (sk, sk, sk), 0))
        n += 1
    return n


def bauen():
    C = VB.cfg()["ranken"]
    r = VB.rnd(12)
    protos = prototypen(C)
    aus = VB.vegetation_ausblenden(("Baeume", "Baeume_Hintergrund", "Bodendecker"))  # schnellere Strahlen
    S = VB.Strahl()
    col = V.collection("08_Vegetation/Ranken")
    punkte = {k: [] for k in [("efeu", s) for s in ("nah", "mittel", "fern")] + [("wein", s) for s in ("nah", "mittel", "fern")]
              + [("kudzu", "mittel")]}
    nf = fassaden_bewuchs(S, C, punkte, r)
    nk = kudzu_haeuser(S, C, punkte, r)
    no = objekt_bewuchs(S, C, punkte, r)
    VB.vegetation_einblenden(aus)
    gesamt = 0
    for (art, stufe), pk in punkte.items():
        typ = f"{art}_{stufe}"
        if not pk or typ not in protos:
            continue
        idx_n = len(protos[typ].objects)
        pk = [(p, rot, sk, r.randrange(idx_n)) for p, rot, sk, _i in pk]
        V.instanzen(f"VEG_Ranken_{typ}", pk, protos[typ], col)
        gesamt += len(pk)
    print("RANKEN", {"fassaden": nf, "kudzu_haeuser": nk, "objekt_bueschel": no, "bueschel": gesamt,
                     "je_typ": {f"{a}_{s}": len(v) for (a, s), v in punkte.items()}, "strahlen": S.n}, flush=True)
