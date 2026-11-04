"""Phase 3.1.7/3.1.8 – Fahrzeugflotte in die Szene setzen (Konfiguration: scripts/configs/flotte.json).

- Bodenhoehe per Raycast auf Gelaende, Fahrbahn, Bloecke (Gehwege)
- Fahrzeug folgt den 4 Radhoehen (Gefaelle, Bordstein, platte Reifen) -> Ebene durch die Radmitten
- Detailstufe nach Abstand zur naechsten Hero-Kamera (nah/mittel/fern)
- Lagen: normal, "dach" (auf dem Dach, Dach eingedrueckt), "seite"
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, HIER)
import viertel_lib as V  # noqa: E402
import fahrzeug as FZ  # noqa: E402
import fz_karosserie as K  # noqa: E402
import fz_material as FM  # noqa: E402
import fz_schaden as FS  # noqa: E402
import fz_teile as FT  # noqa: E402

BODEN_OBJEKTE = ("GEO_Gelaende", "STR_Fahrbahn_Detail", "STR_Block_", "STR_Platz_Wege", "STR_Gasse_Belag")


# ---------------------------------------------------------------- Boden
class Boden:
    def __init__(self):
        dg = bpy.context.evaluated_depsgraph_get()
        bm = bmesh.new()
        for ob in bpy.data.objects:
            if ob.type == "MESH" and ob.name.startswith(BODEN_OBJEKTE):
                ev = ob.evaluated_get(dg)
                me = ev.to_mesh()
                tmp = bmesh.new()
                tmp.from_mesh(me)
                tmp.transform(ob.matrix_world)
                me2 = bpy.data.meshes.new("tmp_boden")
                tmp.to_mesh(me2)
                tmp.free()
                bm.from_mesh(me2)
                bpy.data.meshes.remove(me2)
                ev.to_mesh_clear()
        self.bvh = BVHTree.FromBMesh(bm)
        bm.free()

    def z(self, x, y):
        hit = self.bvh.ray_cast(Vector((x, y, 200.0)), Vector((0, 0, -1)), 400.0)
        return hit[0].z if hit[0] is not None else V.h(x, y)


# ---------------------------------------------------------------- Auswahl
def farbe_waehlen(rnd, C, verboten=()):
    namen = list(C["farb_anteile"].keys())
    gew = [C["farb_anteile"][n] for n in namen]
    for _ in range(20):
        f = rnd.choices(namen, gew)[0]
        if f not in verboten:
            return f
    return f


def kameras():
    return [o.matrix_world.translation.copy() for o in bpy.data.objects if o.name.startswith("CAM_Hero_")]


def lod_fuer(pos, cams, grenzen):
    d = min((Vector((pos[0], pos[1], 0)) - Vector((c.x, c.y, 0))).length for c in cams) if cams else 99
    return ("nah" if d < grenzen[0] else "mittel" if d < grenzen[1] else "fern"), d


# ---------------------------------------------------------------- Lage
def radpunkte(root, T):
    P = K.Profil(T)
    out = {}
    n = len(P.achsen)
    for ai, a in enumerate(P.achsen):
        an = "v" if ai == 0 else ("h" if ai == n - 1 else "m")
        for s in (1, -1):
            out[an + ("l" if s > 0 else "r")] = Vector((P.x(a), s * (P.hw(a) - P.bw / 2 - 0.035), 0.0))
    return out, P


def hinsetzen(root, T, boden, pos, richtung_grad, senk, lage="normal"):
    """Fahrzeug in die Ebene durch die 4 Radaufstandspunkte legen."""
    yaw = math.radians(richtung_grad)
    rp, P = radpunkte(root, T)
    rz = Matrix.Rotation(yaw, 3, "Z")
    if lage == "dach":
        z0 = boden.z(*pos)
        root.location = (pos[0], pos[1], z0 + T["H"] - 0.12)
        root.rotation_euler = Euler((math.pi, math.radians(3), yaw), "XYZ")
        return
    if lage == "seite":
        z0 = boden.z(*pos)
        root.location = (pos[0], pos[1], z0 + T["B"] / 2 + 0.02)
        root.rotation_euler = Euler((math.radians(-88), 0, yaw), "XYZ")
        return
    # Ebene z = a + b*x + c*y (lokal) durch (Boden - Absenkung) der 4 Raeder, kleinste Quadrate
    pts = []
    for k, lp in rp.items():
        w = rz @ lp + Vector((pos[0], pos[1], 0))
        pts.append((lp.x, lp.y, boden.z(w.x, w.y) - senk.get(k, 0.0)))
    n = len(pts)
    sx = sum(p[0] for p in pts) / n
    sy = sum(p[1] for p in pts) / n
    sz = sum(p[2] for p in pts) / n
    sxx = sum((p[0] - sx) ** 2 for p in pts)
    syy = sum((p[1] - sy) ** 2 for p in pts)
    b = sum((p[0] - sx) * (p[2] - sz) for p in pts) / max(sxx, 1e-6)
    c = sum((p[1] - sy) * (p[2] - sz) for p in pts) / max(syy, 1e-6)
    a = sz - b * sx - c * sy
    pitch = -math.asin(max(-0.5, min(0.5, b)))
    roll = math.asin(max(-0.5, min(0.5, c)))
    root.location = (pos[0], pos[1], a)
    root.rotation_euler = Euler((roll, pitch, yaw), "XYZ")


def dach_eindruecken(root, T):
    """Dach und Saeulen eingedrueckt (Fahrzeug liegt auf dem Dach)."""
    P = K.Profil(T)
    for ob in root.children_recursive:
        if ob.type != "MESH" or "_Rad_" in ob.name:
            continue
        mw = ob.matrix_local if ob.parent == root else root.matrix_world.inverted() @ ob.matrix_world
        inv = mw.inverted()
        for v in ob.data.vertices:
            p = mw @ v.co
            d = P.L / 2 - p.x
            zb = P.belt(d)
            if p.z > zb:
                p.z = zb + (p.z - zb) * 0.62
                v.co = inv @ p


# ---------------------------------------------------------------- Zusatzteile
def polizei(root, T, cfgp, col, rnd):
    """Schwarz-weisse Lackierung (Tueren weiss), Lichtbalken, generische Aufschrift, Rammschutz."""
    C = FZ.cfg()
    weiss = FM.lack(cfgp["tueren_farbe"], C["farben"][cfgp["tueren_farbe"]][0], 0.0)
    tl = FS.teile(root)
    for n, ob in tl.items():
        if n.startswith("Tuer_") and ob.type == "MESH":
            for i, m in enumerate(ob.data.materials):
                if m and m.name.startswith("MAT_Autolack_"):
                    ob.data.materials[i] = weiss
    P = K.Profil(T)
    mats = FM.satz(root["farbe"], C["farben"])
    bm = bmesh.new()
    d = T["tueren"][1][0] - 0.1
    zt = P.top(d) + 0.015
    FT.quader(bm, (P.x(d), 0, zt + 0.05), (0.30, 1.20, 0.10), 0)
    for k, y in enumerate((-0.45, -0.15, 0.15, 0.45)):
        FT.quader(bm, (P.x(d), y, zt + 0.065), (0.31, 0.28, 0.07), 1 if y < 0 else 2)
    for y in (-0.45, 0.45):
        FT.quader(bm, (P.x(d), y, zt + 0.005), (0.12, 0.05, 0.03), 0)
    blau = FM.streuscheibe("Blau", "#1D3E8C", False)
    ob = FT.objekt(f"{root.name}_Lichtbalken", bm, col, [mats["schwarz"], mats["ruecklicht"], blau], root)
    m = ob.modifiers.new("Fase", "BEVEL")
    m.width = 0.012
    m.segments = 2
    # Rammschutz vorne
    bm = bmesh.new()
    xf = P.L / 2 + 0.06
    zb = T["stossf_linie"]
    for y in (-0.28, 0.28):
        FT.zylinder(bm, (xf, y, 0.32), (xf, y, zb + 0.18), 0.025, 8, 0)
    for z in (0.40, zb + 0.12):
        FT.zylinder(bm, (xf + 0.01, -0.36, z), (xf + 0.01, 0.36, z), 0.022, 8, 0)
    FT.objekt(f"{root.name}_Rammschutz", bm, col, [mats["schwarz"]], root, glatt=True)
    # Aufschrift auf den Vordertueren (erfunden/generisch: keine Behoerde, keine Stadt)
    schrift = FM.text_mat("Polizei", "#151515", 0.5)
    nr = f"{cfgp['nummer_praefix']} {rnd.randint(11, 48)}"
    lo_bvh = None
    for s in (1, -1):
        tuer = tl.get(f"Tuer_v{'l' if s > 0 else 'r'}")
        if tuer is None:
            continue
        t0, t1 = T["tueren"][0]
        dm = (t0 + t1) / 2
        z = (T["schweller_z"] + P.belt(dm)) / 2 + 0.05
        y = s * (P.hw(dm) + 0.004)
        bm = bmesh.new()
        lese = Vector((1, 0, 0)) if s < 0 else Vector((-1, 0, 0))
        nrm = Vector((0, s, 0))
        mx = Matrix((lese, Vector((0, 0, 1)), nrm)).transposed().to_4x4()
        mx.translation = Vector((P.x(dm), y, z)) - tuer.location
        V.text_mesh(bm, cfgp["aufschrift"], 0.14, mx, 0, extrude=0.0015, aufloesung=3)
        mx2 = mx.copy()
        mx2.translation = Vector((P.x(dm), y, z - 0.13)) - tuer.location
        V.text_mesh(bm, nr, 0.06, mx2, 0, extrude=0.0015, aufloesung=2)
        FT.objekt(f"{root.name}_Aufschrift_{'l' if s > 0 else 'r'}", bm, col, [schrift], tuer)
    _ = lo_bvh
    root["polizei"] = True


_PROTO = {}


def _proto(asset):
    if asset not in _PROTO:
        col = V.prototypen("Fahrzeug_Props")
        obs = V.modell_laden(asset, col)
        _PROTO[asset] = [o for o in obs if o.type == "MESH"]
    return _PROTO[asset]


def kopie(asset, col, pos, rot_z=0.0, skal=1.0, kipp=(0, 0)):
    out = []
    for p in _proto(asset):
        o = p.copy()
        o.location = (pos[0] + p.location.x * skal, pos[1] + p.location.y * skal, pos[2] + p.location.z * skal)
        o.rotation_euler = (kipp[0], kipp[1], rot_z)
        o.scale = (skal, skal, skal)
        col.objects.link(o)
        out.append(o)
    return out


def ziegel_unterlage(root, T, col, senk, boden):
    """Ziegelstapel unter den Radnaben (Auto ohne Raeder)."""
    rp, P = radpunkte(root, T)
    m = V.material("MAT_Ziegelstein")
    mw = root.matrix_world
    bm = bmesh.new()
    rnd = random.Random(root.get("seed", 0))
    for k, lp in rp.items():
        nabe = mw @ Vector((lp.x, lp.y * 0.92, P.R - senk.get(k, 0.0)))
        bz = boden.z(nabe.x, nabe.y)
        hoehe = max(nabe.z - 0.075 - bz, 0.065)
        n = max(1, int(round(hoehe / 0.066)))
        for i in range(n):
            rot = Matrix.Rotation(root.rotation_euler.z + rnd.uniform(-0.25, 0.25) + (math.pi / 2 if i % 2 else 0), 3, "Z")
            FT.quader(bm, (nabe.x + rnd.uniform(-0.02, 0.02), nabe.y, bz + 0.0325 + i * 0.066), (0.20, 0.10, 0.065), 0, rot)
    ob = FT.objekt(f"{root.name}_Ziegel", bm, col, [m])
    V.fase(ob, 0.006, 1)
    return ob


def zusammenfassen(root, col):
    """Ferne Fahrzeuge: alle sichtbaren Teile zu EINEM Mesh (ohne Blech-Dicke, ohne Innenraum)."""
    dg = bpy.context.evaluated_depsgraph_get()
    teile = [o for o in root.children_recursive if o.type == "MESH" and not o.hide_render]
    for o in teile:
        for m in o.modifiers:
            if m.type in ("SOLIDIFY", "SUBSURF", "BEVEL"):
                m.show_render = m.show_viewport = False
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    mats = []
    inv = root.matrix_world.inverted()
    for o in teile:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        tmp = bmesh.new()
        tmp.from_mesh(me)
        tmp.transform(inv @ o.matrix_world)
        karte = []
        for m in [sl.material for sl in o.material_slots]:  # Originale, NICHT die ausgewerteten Kopien
            if m not in mats:
                mats.append(m)
            karte.append(mats.index(m))
        for f in tmp.faces:
            f.material_index = karte[min(f.material_index, len(karte) - 1)] if karte else 0
        me2 = bpy.data.meshes.new("tmp_lod")
        tmp.to_mesh(me2)
        tmp.free()
        bm.from_mesh(me2)
        bpy.data.meshes.remove(me2)
        ev.to_mesh_clear()
    # Originale entfernen (gesammelt, Meshes bleiben als verwaiste Daten und werden beim Speichern verworfen)
    weg = [o for o in root.children_recursive if o.type == "MESH"]
    bpy.data.batch_remove(weg)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new(f"{root.name}_Fern")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(f"{root.name}_Fern", me)
    col.objects.link(ob)
    ob.parent = root
    ob["lack_alter"] = root.get("lack_alter", 0.8)
    ob["verw_korrektur"] = 0.0
    root["lod"] = "fern"
    return ob


# ---------------------------------------------------------------- Ein Fahrzeug
def fahrzeug(e, gruppe, C, F, boden, cams, col, rnd, nachbar_farben):
    typ = e["typ"]
    T0 = C["typen"].get(typ) or C["sondertypen"][typ]
    pos = e["pos"]
    lod, dist = lod_fuer(pos, cams, F["lod_m"])
    seed = rnd.randint(1, 99999)
    r2 = random.Random(seed)
    farbe = e.get("farbe") or (F["polizei"]["farbe"] if e.get("polizei") else
                               farbe_waehlen(r2, C, [f for t, f in nachbar_farben if t == typ]))
    felge = e.get("felge") or ("stahl_kappe" if e.get("polizei") else r2.choice(T0["felgen"]))
    variante = e.get("variante", 0 if e.get("polizei") else r2.randrange(len(T0.get("varianten", [{}]))))
    cid = f"FZ_{gruppe}_{len([o for o in bpy.data.objects if o.name.startswith('FZ_' + gruppe + '_') and o.type == 'EMPTY']) + 1:02d}"
    root = FZ.bauen(typ, farbe=farbe, felge=felge, seed=seed, alter=r2.uniform(0.7, 1.0), col=col, cid=cid,
                    innen=(lod != "fern"), variante=variante)
    T = dict(T0)
    T.update((T0.get("varianten") or [{}])[variante % len(T0.get("varianten") or [{}])])
    root["gruppe"] = gruppe
    root["lod"] = lod
    root["abstand_kamera_m"] = round(dist, 1)
    if e.get("info"):
        root["info"] = e["info"]
    G = F["gruppen"][gruppe]
    z = FS.wuerfeln(r2, typ, ausgebrannt=(r2.random() < G.get("brand_anteil", 0.0)))
    if "zustand" in G:
        z.update({k: v for k, v in G["zustand"].items() if k != "platt_alle"})
        if G["zustand"].get("platt_alle"):
            z["platt"] = list(FS.RAEDER)
    if gruppe == "Stau" and r2.random() < G.get("tueren_offen_anteil", 0):
        for _ in range(r2.choice((1, 1, 2))):
            z["tueren"][r2.choice(("Tuer_vl", "Tuer_vr", "Tuer_hl", "Tuer_hr"))] = r2.uniform(35, 70)
    if "zustand" in e:
        z.update(e["zustand"])
    if e.get("polizei"):
        polizei(root, T, F["polizei"], col, r2)
    if e.get("unterlage") == "ziegel":
        z["rad_fehlt"] = list(FS.RAEDER)
    if z.get("platt_alle"):
        z["platt"] = list(FS.RAEDER)
    senk = FS.anwenden(root, z, T)
    if "hecktuer" in z:
        FS.tuer_auf(FS.teile(root).get("Hecktuer_m"), z["hecktuer"])
    for k in ("ml", "mr"):
        if k not in senk and ("hl" in senk or "vl" in senk):
            senk[k] = (senk.get("h" + k[1], 0) + senk.get("v" + k[1], 0)) / 2
    if e.get("unterlage") == "ziegel":
        P = K.Profil(T)
        senk = {k: P.R - 0.30 for k in FS.RAEDER}
    lage = e.get("lage", "normal")
    if lage == "dach":
        dach_eindruecken(root, T)
    hinsetzen(root, T, boden, pos, e.get("richtung", 0), senk, lage)
    bpy.context.view_layer.update()
    if e.get("unterlage") == "ziegel":
        ziegel_unterlage(root, T, col, senk, boden)
    if e.get("kartons"):
        mw = root.matrix_world
        P = K.Profil(T)
        for k in range(e["kartons"]):
            lp = Vector((-P.L / 2 - 0.4 - 0.45 * (k % 2), r2.uniform(-0.6, 0.6), 0))
            w = mw @ lp
            kopie("cardboard_box_01", col, (w.x, w.y, boden.z(w.x, w.y) + (0.32 if k >= 2 else 0.0)),
                  r2.uniform(0, 6.28), 1.0)
    if e.get("auflieger"):
        auflieger_setzen(root, e["auflieger"], col, boden, r2)
    if e.get("trage"):
        trage(root, T, col)
    if lod == "mittel":  # Unterboden weg, Polster einfacher
        for o in list(root.children_recursive):
            if o.name.endswith(("Unterboden_Teile", "Motorraum")):
                bpy.data.objects.remove(o)
            elif o.type == "MESH":
                for m in o.modifiers:
                    if m.type == "SUBSURF":
                        m.levels = m.render_levels = 1
    if lod == "fern":
        zusammenfassen(root, col)
    for o in root.children_recursive:
        if "lack_alter" not in o.keys():
            o["lack_alter"] = root.get("lack_alter", 0.8)
            o["verw_korrektur"] = 0.0
    root["zustand"] = str({k: v for k, v in z.items() if v})
    return root, (typ, farbe)


def flotte_bauen(col=None, nur_gruppen=None):
    C = FZ.cfg()
    F = V.config("flotte.json")
    rnd = random.Random(F["seed"])
    boden = Boden()
    cams = kameras()
    col = col or V.collection("04_Fahrzeuge/Flotte")
    out = []
    for gname, G in F["gruppen"].items():
        if nur_gruppen and gname not in nur_gruppen:
            continue
        gcol = V.collection(f"04_Fahrzeuge/{gname}")
        nachbarn = []
        liste = []
        for reihe in G.get("reihen", []):
            x = reihe["x_vorne"]
            for t in reihe["typen"]:
                Lt = C["typen"][t]["L"]
                xm = x - Lt / 2
                liste.append({"typ": t, "pos": [xm, reihe["y"] + rnd.uniform(-G["quer_m"], G["quer_m"])],
                              "richtung": reihe["richtung"] + rnd.uniform(-G["schraeg_grad"], G["schraeg_grad"])})
                x -= Lt + rnd.uniform(*G["luecke"])
        liste += G.get("einzeln", []) + G.get("fahrzeuge", [])
        for e in liste:
            root, tf = fahrzeug(e, gname, C, F, boden, cams, gcol, rnd, nachbarn[-3:])
            nachbarn.append(tf)
            out.append(root)
            print(f"FZ {root.name}: {e['typ']} {tf[1]} lod={root['lod']} ({root['abstand_kamera_m']} m)", flush=True)
    return out


def auflieger_setzen(zug, a, col, boden, rnd):
    """Umgekippter Auflieger (eingeknickter Sattelzug) mit verstreuter Ladung (Kartons, Paletten)."""
    import fz_sonder as SO
    C = FZ.cfg()
    T = C["sondertypen"]["Z"]
    mats = FM.satz(zug["farbe"], C["farben"])
    rad_me = FT.rad_mesh("Z", T, "stahl", mats)
    R = K.reifen_radius(T["reifen"])
    tr = SO.auflieger(col, f"{zug.name}_Auflieger", rnd, mats, rad_me, R)
    x, y = a["pos"]
    tr.location = (x, y, boden.z(x, y) + SO.B / 2 + 0.03)
    tr.rotation_euler = Euler((math.radians(a.get("kipp", -90)), 0, math.radians(a["richtung"])), "XYZ")
    bpy.context.view_layer.update()
    mw = tr.matrix_world
    # Ladung: Paletten + Kartons aus dem Riss und hinter den Hecktueren
    bm = bmesh.new()
    holz = V.material("MAT_Holz_Bretter_Alt")
    n = a.get("ladung", 20)
    for k in range(n):
        if k % 3 == 0:
            lp = Vector((rnd.uniform(-8.0, -1.5), -SO.B / 2 - rnd.uniform(0.3, 3.0), 0))
        else:
            lp = Vector((-SO.L / 2 - rnd.uniform(0.5, 4.0), rnd.uniform(-2.5, 2.5), 0))
        w = mw @ Vector((lp.x, 0, 0))
        w2 = mw @ Vector((lp.x, 0, 0)) + (mw.to_3x3() @ Vector((0, 0, -lp.y)))
        gx, gy = (w2.x, w2.y) if k % 3 == 0 else ((mw @ Vector((lp.x, lp.y, SO.B / 2))).x, (mw @ Vector((lp.x, lp.y, SO.B / 2))).y)
        gz = boden.z(gx, gy)
        if k % 4 == 0:
            m = Matrix.Translation((gx, gy, gz)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, "Z")
            SO.palette(bm, m)
            kopie("cardboard_box_01", col, (gx, gy, gz + 0.15), rnd.uniform(0, 6.28))
        else:
            kopie("cardboard_box_01", col, (gx, gy, gz), rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.2),
                  (rnd.choice((0, 0, 1.57)), 0))
        _ = w
    if len(bm.verts):
        o = FT.objekt(f"{zug.name}_Paletten", bm, col, [holz])
        o["lack_alter"] = 0.9
    return tr


def trage(root, T, col):
    """Leere Krankentrage, halb aus dem Rettungswagen gezogen (Hecktueren offen)."""
    P = K.Profil(T)
    C = FZ.cfg()
    mats = FM.satz(root["farbe"], C["farben"])
    bm = bmesh.new()
    x = -P.L / 2 - 0.55
    z = 0.62 + 0.12
    FT.polster(bm, (x, 0.2, z + 0.06), (1.95, 0.56, 0.08), None, "z", 0.0, 0.0, cuts=2)
    for xx in (x - 0.85, x + 0.85):
        for yy in (0.0, 0.4):
            FT.zylinder(bm, (xx, yy, z), (xx - 0.05 if xx < x else xx, yy, 0.12 if xx < x else z), 0.018, 8, 1)
    FT.zylinder(bm, (x - 0.95, 0.2, z), (x + 0.95, 0.2, z), 0.02, 8, 1)
    o = FT.objekt(f"{root.name}_Trage", bm, col, [V.material("MAT_Leder_Schwarz"), mats["chrom"]], root)
    o["lack_alter"] = 0.9
    return o
