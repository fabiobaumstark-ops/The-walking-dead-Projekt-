"""Phase 6.4 Teil 2 – Innenausbau: Raeume, Innenmaterialien, Moebel-Scans (Vorgabe Nutzer: "Selber Realismus wie aussen").

Wird von scripts/phase6/innenraum.py aufgerufen (fuer die Gebaeude in innenraum.json -> "innenausbau" -> "gebaeude").
Parameter: scripts/configs/innenraum.json -> "innenausbau".

Je Wohngeschoss (Typ 1: alle, Typ 3: ab 1. OG) ein Grundriss:
- Flur entlang der Treppe (Treppenhaus liegt hinten am Flurende), Laengswand mit einer Tuer je Zimmer
- Zimmer auf der anderen Seite hintereinander (Wohnen zur Strasse, Kueche, Bad, Schlafen ...), Querwaende zwischen
  den Fenstern der Seitenwand
- Trennwaende aus zwei Haelften (je Seite das Material des Raums), Bodenbelag je Raum (1,2 cm auf der Rohdecke)
- Tuerblaetter als eigene Objekte (wie Haustueren), Zargen im Gebaeude-Mesh
- Moebel: Poly-Haven-Scans (CC0) als Collection-Instanzen (verlinkt, wenig Speicher), an Waenden/um Tische,
  Abstand zu Tueren, hohe Moebel nicht vor Fenstern, teils verschoben/umgekippt
- Alte Kasten-Moebel aus fassaden_details.innenraum werden in diesen Geschossen entfernt
Laden (Typ 3, Erdgeschoss): Kasten-Regale entfernt, Stahlregale (Scans) in Reihen und an den Waenden.
"""
import math
import os
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))


def _cfg(C):
    return C["innenausbau"]


def extra_materialien(C):
    """Zusaetzliche Material-Slots hinter den 19 Standard-Slots (fassade.SLOT)."""
    return list(_cfg(C)["extra_materialien"])


def slot(C, S, name):
    return len(S) + extra_materialien(C).index(name)


# ------------------------------------------------------------------ Hilfen im lokalen (u, v)-System
def _box(b, G2, u0, v0, u1, v1, za, zb, mat, top=None):
    return G2.Bau2.box(b, min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1), za, zb, mat, top)


def _fenster(b, seite, z0, z1):
    """Fenster einer Aussenwand im Hoehenbereich als Intervalle in u (vorne/hinten) bzw. v (links/rechts)."""
    W, D = b.r.W, b.r.D
    out = []
    for o in (b.info or {}).get("ops", {}).get(seite, []):
        if o["z1"] <= z0 or o["z0"] >= z1:
            continue
        if seite == "hinten":
            out.append((W - o["s1"], W - o["s0"]))
        elif seite == "links":
            out.append((D - o["s1"], D - o["s0"]))
        else:
            out.append((o["s0"], o["s1"]))
    return sorted(out)


def _frei_von(intervalle, a, rand=0.15):
    return all(a < i0 - rand or a > i1 + rand for i0, i1 in intervalle)


def kasten_moebel_weg(b, S, rect, z0, z1, rand=0.45):
    """Prozedurale Kasten-Moebel (Holz/Metall/Stoff/Lack, kleine Teile) innerhalb rect (u, v) und z0..z1 entfernen.
    Teile mit Beton-Flaechen (Theke) bleiben, Vorhaenge an den Aussenwaenden (Rand) bleiben."""
    u0, v0, u1, v1 = rect
    pa, pb = b.r.p(u0 + rand, v0 + rand), b.r.p(u1 - rand, v1 - rand)
    x0, x1 = min(pa[0], pb[0]), max(pa[0], pb[0])
    y0, y1 = min(pa[1], pb[1]), max(pa[1], pb[1])
    moebel = {S["Holz"], S["Metall"], S["Stoff"], S["Lack"]}
    weg, gesehen = [], set()
    for f in b.bm.faces:
        if f in gesehen or f.material_index not in moebel:
            continue
        teil, stapel = [], [f]
        gesehen.add(f)
        while stapel:
            ff = stapel.pop()
            teil.append(ff)
            for e in ff.edges:
                for nf in e.link_faces:
                    if nf not in gesehen:
                        gesehen.add(nf)
                        stapel.append(nf)
        if len(teil) > 80 or any(ff.material_index not in moebel for ff in teil):
            continue
        vs = [v.co for ff in teil for v in ff.verts]
        if all(x0 <= c.x <= x1 and y0 <= c.y <= y1 and z0 - 0.01 <= c.z <= z1 + 0.01 for c in vs):
            weg += teil
    bmesh.ops.delete(b.bm, geom=list(set(weg)), context="FACES")
    return len(weg)


# ------------------------------------------------------------------ Grundriss
def grundriss(b, p, C, zf, hz):
    """Flurbreite (Laengswand u = uw) und Zimmer (v-Abschnitte) fuer ein Geschoss. Nur Treppe in v-Richtung ohne Kern."""
    K = _cfg(C)
    W, D = b.r.W, b.r.D
    d = p["d"]
    start = p["u0"] + p["breite"] + 0.02  # Laengswand gleich neben der Treppe (ersetzt dort das Gelaender)
    fv, fh = _fenster(b, "vorne", zf, zf + hz), _fenster(b, "hinten", zf, zf + hz)
    uw = start
    for k in range(11):
        u = start + k * 0.1
        if _frei_von(fv, u) and _frei_von(fh, u) and _frei_von(fv, u + 0.12) and _frei_von(fh, u + 0.12):
            uw = u
            break
    if W - d - (uw + 0.12) < K["zimmer_min_breite"]:
        return None
    seite = "rechts"
    fs = _fenster(b, seite, zf, zf + hz)
    folge, tiefen = K["raumfolge"], K["raumtiefen"]
    innen = (D - 2 * d)
    grenzen, v = [], d
    for i, (art, t) in enumerate(zip(folge, tiefen)):
        rest = D - d - v
        if rest < t + K["zimmer_min_tiefe"]:
            break
        c = v + t
        for dv in [0.0] + [s * k * 0.1 for k in range(1, 15) for s in (1, -1)]:  # zwischen die Fenster
            if _frei_von(fs, c + dv, 0.2):
                c += dv
                break
        grenzen.append((art, v, c))
        v = c
    letzte = folge[len(grenzen)] if len(grenzen) < len(folge) else "schlafen"
    grenzen.append((letzte, v, D - d))
    _ = innen
    return {"uw": uw, "zimmer": grenzen}


def wand_zwei_seiten(b, G2, achse, fest, a0, a1, za, zb, mat_a, mat_b, tueren):
    """Trennwand 0,12 m aus zwei Haelften (achse 'v': Wand bei u = fest..fest+0,12 entlang v; 'u': bei v = fest).
    mat_a = Seite kleiner Koordinate, mat_b = Seite groesser. tueren = [(t0, t1, hoehe)]."""
    stuecke, a = [], a0
    for t0, t1, h in sorted(tueren):
        if t0 > a:
            stuecke.append((a, t0, za, zb))
        stuecke.append((t0, t1, za + h, zb))
        a = t1
    if a < a1:
        stuecke.append((a, a1, za, zb))
    for s0, s1, z0, z1 in stuecke:
        if s1 - s0 < 0.01 or z1 - z0 < 0.01:
            continue
        for (n0, n1, m) in ((0.0, 0.06, mat_a), (0.06, 0.12, mat_b)):
            if achse == "v":
                _box(b, G2, fest + n0, s0, fest + n1, s1, z0, z1, m)
            else:
                _box(b, G2, s0, fest + n0, s1, fest + n1, z0, z1, m)


def tuer_objekt(b, u, v, achse, breite, zf, rnd, richtung=1.0, art="zimmer"):
    """Tuerblatt-Eintrag (wie innenraum._tuer_getrennt): Scharnier bei (u, v), achse = Wandrichtung."""
    p0 = Vector((*b.r.p(u, v), zf))
    if achse == "v":
        ex = (Vector((*b.r.p(u, v + 1), zf)) - p0).normalized()
        ey = (Vector((*b.r.p(u + richtung, v), zf)) - p0).normalized()
    else:
        ex = (Vector((*b.r.p(u + 1, v), zf)) - p0).normalized()
        ey = (Vector((*b.r.p(u, v + richtung), zf)) - p0).normalized()
    zust = rnd.choices(["zu", "offen", "fehlt"], weights=[2, 5, 2])[0]
    if zust == "fehlt":
        return
    b.tueren.append({"p0": p0, "ex": ex, "ey": ey, "breite": breite - 0.12, "z0": zf, "z1": zf + 2.05,
                     "zustand": zust, "winkel": 0.0 if zust == "zu" else rnd.uniform(0.3, 1.5), "richtung": 1.0,
                     "mat": "Holz", "dicke": 0.04, "art": art})


def zargen(b, G2, S, achse, fest, t0, t1, zf):
    for (a, c, za, zb) in ((t0, t0 + 0.06, zf, zf + 2.1), (t1 - 0.06, t1, zf, zf + 2.1), (t0, t1, zf + 2.04, zf + 2.1)):
        if achse == "v":
            _box(b, G2, fest - 0.02, a, fest + 0.14, c, za, zb, S["Rahmen"])
        else:
            _box(b, G2, a, fest - 0.02, c, fest + 0.14, za, zb, S["Rahmen"])


# ------------------------------------------------------------------ Moebel
class Belegung:
    """2D-Belegung eines Raums im (u, v)-System (Rechtecke)."""

    def __init__(self, rect):
        self.rect = rect
        self.besetzt = []

    def frei(self, r):
        u0, v0, u1, v1 = self.rect
        if r[0] < u0 - 1e-6 or r[1] < v0 - 1e-6 or r[2] > u1 + 1e-6 or r[3] > v1 + 1e-6:
            return False
        return all(r[2] <= b[0] or r[0] >= b[2] or r[3] <= b[1] or r[1] >= b[3] for b in self.besetzt)

    def setzen(self, r, rand=0.05):
        self.besetzt.append((r[0] - rand, r[1] - rand, r[2] + rand, r[3] + rand))


def _fussabdruck(mass, yaw, u, v):
    """Achsparalleles Rechteck des Modells (mass = xmin, xmax, ymin, ymax) bei Drehung yaw (Vielfache von 90 Grad)."""
    xmn, xmx, ymn, ymx = mass
    pts = [(x, y) for x in (xmn, xmx) for y in (ymn, ymx)]
    c, s = math.cos(yaw), math.sin(yaw)
    pr = [(u + c * x - s * y, v + s * x + c * y) for x, y in pts]
    return (min(q[0] for q in pr), min(q[1] for q in pr), max(q[0] for q in pr), max(q[1] for q in pr))


def moebel_raum(b, art, rect, wand_info, belegung, C, rnd, masse, zf):
    """Platzierungen [(asset, u, v, yaw_lokal, z, kipp)] fuer einen Raum.
    wand_info: {seite: {'fenster': [(a0, a1)], 'aussen': bool}}; Vorderseite der Modelle = -Y."""
    K = _cfg(C)
    out = []
    u0, v0, u1, v1 = rect
    # Waende: (Seite, Innennormale, Lage)
    waende = [("v0", (0, 1), v0), ("v1", (0, -1), v1), ("u0", (1, 0), u0), ("u1", (-1, 0), u1)]
    for eintrag in K["moebel"].get(art, []):
        asset, wo = eintrag["asset"], eintrag.get("wo", "wand")
        if isinstance(asset, list):
            asset = rnd.choice(asset)
        if asset not in masse:
            continue
        n = eintrag.get("anzahl", 1)
        if isinstance(n, list):
            n = rnd.randint(*n)
        if rnd.random() > eintrag.get("chance", 1.0):
            continue
        mass, hoehe = masse[asset]
        for _ in range(n):
            gesetzt = None
            if wo == "wand":
                ws = waende[:]
                rnd.shuffle(ws)
                for seite, nrm, lage in ws:
                    yaw = math.atan2(nrm[1], nrm[0]) + math.pi / 2  # -Y (Vorderseite) zeigt in den Raum
                    tiefe = mass[3]  # Rueckseite (+Y) an die Wand
                    lang = (u0, u1) if seite.startswith("v") else (v0, v1)
                    pos = [lang[0] + 0.1 + k * 0.1 for k in range(int((lang[1] - lang[0]) / 0.1))]
                    rnd.shuffle(pos)
                    for a in pos:
                        if seite.startswith("v"):
                            u, v = a, lage + nrm[1] * (tiefe + 0.03)
                        else:
                            u, v = lage + nrm[0] * (tiefe + 0.03), a
                        r = _fussabdruck(mass, yaw, u, v)
                        if not belegung.frei(r):
                            continue
                        wi = wand_info.get(seite, {})
                        if hoehe > K["fenster_hoehe_frei"] and wi.get("aussen"):
                            q0, q1 = (r[0], r[2]) if seite.startswith("v") else (r[1], r[3])
                            if any(not (q1 <= f0 - 0.1 or q0 >= f1 + 0.1) for f0, f1 in wi.get("fenster", [])):
                                continue
                        gesetzt = (u, v, yaw, r)
                        break
                    if gesetzt:
                        break
            else:  # Raummitte
                for _k in range(60):
                    u = rnd.uniform(u0 + 0.8, u1 - 0.8) if u1 - u0 > 1.6 else (u0 + u1) / 2
                    v = rnd.uniform(v0 + 0.8, v1 - 0.8) if v1 - v0 > 1.6 else (v0 + v1) / 2
                    yaw = rnd.choice([0.0, math.pi / 2, math.pi, -math.pi / 2])
                    r = _fussabdruck(mass, yaw, u, v)
                    if belegung.frei(r):
                        gesetzt = (u, v, yaw, r)
                        break
            if not gesetzt:
                continue
            u, v, yaw, r = gesetzt
            belegung.setzen(r, 0.15 if wo == "mitte" else 0.05)
            kipp = rnd.random() < K["umgekippt_anteil"] and hoehe > 0.6 and eintrag.get("kippbar", True)
            yaw += rnd.uniform(-1, 1) * math.radians(K["verdreht_grad"])
            out.append((asset, u, v, yaw, zf + 0.012, kipp))
            if eintrag.get("stuehle"):  # Stuehle um den Tisch
                st = eintrag["stuehle"]
                cmass, ch = masse.get(st, (None, 0))
                if cmass is None:
                    continue
                cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
                hx, hy = (r[2] - r[0]) / 2, (r[3] - r[1]) / 2
                for (dx, dy) in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    if rnd.random() < 0.25:
                        continue
                    su = cx + dx * (hx + 0.25)
                    sv = cy + dy * (hy + 0.25)
                    syaw = math.atan2(-dy, -dx) + math.pi / 2 + rnd.uniform(-0.5, 0.5)
                    sr = _fussabdruck(cmass, round(syaw / (math.pi / 2)) * math.pi / 2, su, sv)
                    if belegung.frei(sr):
                        belegung.setzen(sr, 0.02)
                        out.append((st, su, sv, syaw, zf + 0.012, rnd.random() < 0.3))
    # Kleinkram: Kartons, Muellsaecke
    for _k in range(rnd.randint(*K["kleinkram_anzahl"])):
        asset = rnd.choice(K["kleinkram"])
        if asset not in masse:
            continue
        mass, _h = masse[asset]
        for _t in range(20):
            u, v = rnd.uniform(u0 + 0.3, u1 - 0.3), rnd.uniform(v0 + 0.3, v1 - 0.3)
            yaw = rnd.uniform(0, 2 * math.pi)
            r = _fussabdruck(mass, 0.0, u, v)
            if belegung.frei(r):
                belegung.setzen(r, 0.02)
                out.append((asset, u, v, yaw, zf + 0.012, False))
                break
    return out


# ------------------------------------------------------------------ Prototypen (verlinkte Scans)
_PROTO = {}


def prototyp(V, VB, aid):
    """Collection 00_Prototypen/PROTO_Moebel_<aid> mit lokalen Objekten auf den verlinkten Scan-Meshes,
    Materialien lokal kopiert + Verwitterung (wie die Baeume). Rueckgabe: (Collection, mass, hoehe)."""
    if aid in _PROTO:
        return _PROTO[aid]
    pfad = os.path.join(V.ASSETS, "models", aid, f"{aid}_2k.blend")
    if not os.path.exists(pfad):
        _PROTO[aid] = None
        return None
    col = V.prototypen(f"Moebel_{aid}")
    for alt in list(col.objects):
        bpy.data.objects.remove(alt)
    with bpy.data.libraries.load(pfad, link=True, relative=True) as (src, dst):
        dst.objects = list(src.objects)
    pts = []
    for lo in dst.objects:
        if lo is None or lo.type != "MESH":
            continue
        k = bpy.data.objects.new(f"PROTO_{aid}_{lo.name}", lo.data)
        col.objects.link(k)
        k.matrix_world = lo.matrix_world.copy()
        for i, s_ in enumerate(lo.material_slots):
            k.material_slots[i].link = "OBJECT"
            k.material_slots[i].material = VB.lokales_material(s_.material)
        pts += [k.matrix_world @ Vector(c) for c in lo.bound_box]
    if not pts:
        _PROTO[aid] = None
        return None
    mass = (min(q.x for q in pts), max(q.x for q in pts), min(q.y for q in pts), max(q.y for q in pts))
    hoehe = max(q.z for q in pts) - max(0.0, min(q.z for q in pts))
    _PROTO[aid] = (col, mass, hoehe)
    return _PROTO[aid]


def moebel_setzen(V, VB, gid, b, platzierungen, col_name):
    """Collection-Instanzen (Empties) fuer die Platzierungen; Lage im Welt-System des Gebaeudes."""
    col = V.collection(col_name)
    for alt in [o for o in col.objects if o.get("gebaeude") == gid]:
        bpy.data.objects.remove(alt)
    ex = Vector((*b.r.p(1, 0), 0)) - Vector((*b.r.p(0, 0), 0))
    w0 = math.atan2(ex.y, ex.x)
    n = 0
    for asset, u, v, yaw, z, kipp in platzierungen:
        pr = prototyp(V, VB, asset)
        if pr is None:
            continue
        pc, mass, hoehe = pr
        e = bpy.data.objects.new(f"MOB_{gid}_{n + 1:03d}_{asset}", None)
        e.instance_type, e.instance_collection = "COLLECTION", pc
        e.empty_display_size = 0.3
        col.objects.link(e)
        x, y = b.r.p(u, v)
        m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(w0 + yaw, 4, "Z")
        if kipp:  # nach vorne umgekippt: um die lokale x-Achse, Drehpunkt an der Vorderkante unten
            m = m @ Matrix.Translation((0, mass[2], 0)) @ Matrix.Rotation(math.radians(-88), 4, "X") @ Matrix.Translation((0, -mass[2], 0))
        e.matrix_world = m
        e["gebaeude"], e["asset"], e["umgekippt"] = gid, asset, bool(kipp)
        n += 1
    return n


# ------------------------------------------------------------------ Ablauf je Gebaeude
def ausbauen(b, p, C, S, G2, V, VB):
    """Innenausbau eines Gebaeudes (im bmesh, vor dem Verschieben auf den Ursprung). Rueckgabe: Bericht.
    Moebel-Platzierungen landen in b.moebel und werden nach dem Mesh-Austausch als Instanzen gesetzt."""
    K = _cfg(C)
    if not p or p.get("kern") or p.get("achse") != "v":
        return {"uebersprungen": "nur Treppe in v-Richtung ohne Kern (Muster)"}
    rnd = random.Random(C["seed"] * 7919 + int(b.g["id"][1:]))
    W, D = b.r.W, b.r.D
    d = p["d"]
    info = b.info or {}
    ge = sorted(info.get("geschosse", []))
    top = info["top"]
    stufen = ge + [top]
    wohn = ge[1:] if b.g["typ"] == 3 else ge
    masse = {}
    for liste in list(K["moebel"].values()) + [[{"asset": a} for a in K["kleinkram"]]]:
        for e in liste:
            for a in (e["asset"] if isinstance(e["asset"], list) else [e["asset"]]) + ([e["stuehle"]] if e.get("stuehle") else []):
                pr = prototyp(V, VB, a)
                if pr:
                    masse[a] = (pr[1], pr[2])
    X = {m: slot(C, S, m) for m in extra_materialien(C)}
    R = K["raeume"]
    b.moebel = []
    b.raeume = []
    bericht = {"geschosse": 0, "zimmer": 0, "moebel": 0, "kasten_weg": 0}
    for zf in wohn:
        i = stufen.index(zf)
        hz = stufen[i + 1] - zf - (0.3 if stufen[i + 1] == top else 0.25)
        gr = grundriss(b, p, C, zf, hz)
        if gr is None:
            continue
        uw = gr["uw"]
        bericht["kasten_weg"] += kasten_moebel_weg(b, S, (d, d, W - d, D - d), zf, zf + hz)
        bericht["geschosse"] += 1
        # Laengswand Flur | Zimmer, je Zimmer eine Tuer
        flur = R["flur"]
        for art, za_v, zb_v in gr["zimmer"]:
            ra = R.get(art, R["schlafen"])
            bt = K["tuer_breite_bad"] if art == "bad" else K["tuer_breite"]
            t0 = max(za_v + 0.25, min(zb_v - 0.25 - bt, za_v + 0.5 + rnd.uniform(0, max(0.0, (zb_v - za_v) - bt - 1.0))))
            wand_zwei_seiten(b, G2, "v", uw, za_v, zb_v, zf, zf + hz, X[flur["wand"]], X[ra["wand"]],
                             [(t0, t0 + bt, 2.1)])
            zargen(b, G2, S, "v", uw, t0, t0 + bt, zf)
            tuer_objekt(b, uw + 0.12, t0 + 0.06, "v", bt, zf, rnd, richtung=1.0)
            # Bodenbelag des Zimmers
            _box(b, G2, uw + 0.12, za_v, W - d, zb_v, zf, zf + 0.012, X[ra["boden"]])
            bericht["zimmer"] += 1
        for (art_a, _a0, grenze), (art_b, _b0, _b1) in zip(gr["zimmer"], gr["zimmer"][1:]):
            ma, mb = X[R.get(art_a, R["schlafen"])["wand"]], X[R.get(art_b, R["schlafen"])["wand"]]
            wand_zwei_seiten(b, G2, "u", grenze - 0.06, uw + 0.12, W - d, zf, zf + hz, ma, mb, [])
        # Flur-Bodenbelag bis zum Treppenantritt (dahinter Treppe/Loch)
        _box(b, G2, d, d, uw, p["v0"] + C["treppe"]["podest"], zf, zf + 0.012, X[flur["boden"]])
        # Moebel je Zimmer
        fv, fh, fr = (_fenster(b, s_, zf, zf + hz) for s_ in ("vorne", "hinten", "rechts"))
        for art, za_v, zb_v in gr["zimmer"]:
            rect = (uw + 0.12, za_v + 0.06, W - d, zb_v - 0.06)
            b.raeume.append({"z": round(zf, 3), "art": art, "rect": [round(c, 3) for c in rect]})
            bel = Belegung(rect)
            wand_info = {"v0": {"aussen": za_v <= d + 0.01, "fenster": fv}, "v1": {"aussen": zb_v >= D - d - 0.01, "fenster": fh},
                         "u1": {"aussen": True, "fenster": fr}, "u0": {"aussen": False}}
            bel.besetzt.append((uw + 0.12, za_v, uw + 1.15, zb_v))  # Bewegungsflaeche vor der Flurwand (Tuer)
            b.moebel += moebel_raum(b, art, rect, wand_info, bel, C, rnd, masse, zf)
    # Laden im Erdgeschoss (Typ 3)
    if b.g["typ"] == 3 and K["laden"].get("aktiv"):
        zf = ge[0]
        hz = ge[1] - zf - 0.25 if len(ge) > 1 else top - zf - 0.3
        bericht["kasten_weg"] += kasten_moebel_weg(b, S, (d, 2.1, W - d, D - d), zf, zf + 2.2)
        rect = (d + 0.05, 2.4, W - d - 0.05, p["v0"] - 0.3)
        b.raeume.append({"z": round(zf, 3), "art": "laden", "rect": [round(c, 3) for c in rect]})
        bel = Belegung(rect)
        bel.besetzt.append(((d + W - d) / 2 - 0.6, rect[1], (d + W - d) / 2 + 0.6, rect[3]))  # Mittelgang
        b.moebel += moebel_raum(b, "laden", rect, {"u0": {"aussen": False}, "u1": {"aussen": False}}, bel, C, rnd, masse, zf - 0.012)
    bericht["moebel"] = len(b.moebel)
    return bericht
