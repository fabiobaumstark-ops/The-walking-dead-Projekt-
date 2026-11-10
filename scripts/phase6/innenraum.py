"""Phase 6.4 – Begehbare Gebaeude: Treppenhaeuser, Deckenoeffnungen, hohler Kern mit Tueren, Dachausstieg.

Aufruf:
    blender -b viertel_v10.blend --python scripts/phase6/innenraum.py -- --pruefen         # Neubau OHNE Aenderung, Vergleich mit der .blend
    blender -b viertel_v10.blend --python scripts/phase6/innenraum.py -- --version 11 [--nur B01,B09]

Prinzip: Die Gebaeude werden mit dem freigegebenen Generator (scripts/phase2/gebaeude2.py) und denselben Seeds neu
erzeugt; nur die Mesh-Daten der vorhandenen BLD_-Objekte werden ersetzt (Objekte, Modifier, Eigenschaften bleiben).
Eingegriffen wird an EINER Stelle: Bau.box() - dort werden Geschossdecken/Dachplatten um das Treppenloch herum gebaut
und der massive Kern grosser Gebaeude durch Waende mit Tueren ersetzt. Der Zufall des Generators bleibt unberuehrt
(eigener Seed fuer alles Neue), deshalb sehen Fassaden, Fenster und Schaeden exakt aus wie vorher.
Parameter: scripts/configs/innenraum.json
"""
import hashlib
import json
import math
import os
import random
import sys
import time

import bmesh
import bpy
from mathutils import Vector

HIER = os.path.dirname(os.path.abspath(__file__))
for p in ("lib", "phase1", "phase2", "phase4"):
    sys.path.insert(0, os.path.join(HIER, "..", p))
sys.path.insert(0, HIER)
import viertel_lib as V  # noqa: E402
import blockout_gebaeude as P1  # noqa: E402
import gebaeude2 as G2  # noqa: E402
import fassaden_details as FD  # noqa: E402
import veg_basis as VB  # noqa: E402
import innenausbau as IA  # noqa: E402

S = G2.S
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PRUEFEN = "--pruefen" in args
version = args[args.index("--version") + 1] if "--version" in args else "11"
NUR = args[args.index("--nur") + 1].split(",") if "--nur" in args else None
C = json.load(open(os.path.join(HIER, "..", "configs", "innenraum.json")))


# ------------------------------------------------------------------ Gebaeude neu erzeugen (wie gebaeude2.bauen)
class Bau3(G2.Bau2):
    """Bau2 mit abfangbarem box(): plan = None -> unveraendert (Pruefung)."""

    def __init__(self, rahmen, z0, rnd, plan=None):
        super().__init__(rahmen, z0, rnd)
        self.plan = plan
        self.log = {"decken_geloch": 0, "kern_hohl": 0}
        self.tueren = []
        self.oeffnungen = []
        self.moebel = []
        self.ladentuer = None

    def schiefe_platte(self, u0, u1, v0, z_v0, v1, z_v1, dicke, mat):
        p = self.plan
        if p is not None and p.get("parkhaus") and (u0, u1, v0, v1) == tuple(C["parkhaus"]["rampe"]):
            z_v1 += C["parkhaus"]["rampe_hoeher"]  # Rampe endet auf der Deckenoberkante statt 30 cm darunter
            p.setdefault("rampen", []).append((z_v0, z_v1))
        return super().schiefe_platte(u0, u1, v0, z_v0, v1, z_v1, dicke, mat)

    def box(self, u0, v0, u1, v1, za, zb, mat=P1.F, top=None):
        p = self.plan
        if p is not None and p.get("parkhaus"):
            ru0, rv0, ru1, rv1 = C["parkhaus"]["rampe"][0], C["parkhaus"]["rampe"][2], C["parkhaus"]["rampe"][1], C["parkhaus"]["rampe"][3]
            if abs((zb - za) - 0.3) < 1e-6 and mat == top and min(u0, u1) <= ru0 and max(u0, u1) >= ru1 \
                    and min(v0, v1) <= rv0 and max(v0, v1) >= rv1:
                p.setdefault("decken", []).append(zb)
                fs = []
                for (a, c, d_, e_) in ((u0, v0, ru0, v1), (ru1, v0, u1, v1), (ru0, v0, ru1, rv0), (ru0, rv1, ru1, v1)):
                    if d_ - a > 0.01 and e_ - c > 0.01:
                        fs += G2.Bau2.box(self, a, c, d_, e_, za, zb, mat, top)
                return fs
            return super().box(u0, v0, u1, v1, za, zb, mat, top)
        if p is not None:
            if p.get("kern") and _ist_kern(self, p, u0, v0, u1, v1, za, zb, mat, top):
                return kern_hohl(self, p, u0, v0, u1, v1, za, zb)
            if _ist_dachraum(self, p, u0, v0, u1, v1, za, zb, mat):
                p["dachraum"] = (min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1), za, zb)
                return []  # wird in treppenhaus() hohl gebaut (Treppe endet darin)
            if p.get("loch") and _ist_decke(self, p, u0, v0, u1, v1, za, zb, mat):
                return decke_mit_loch(self, p, u0, v0, u1, v1, za, zb, mat, top)
        return super().box(u0, v0, u1, v1, za, zb, mat, top)


def gebaeude_liste():
    cfg = V.config("gebaeude.json")
    geb = P1.planen(cfg)
    for g in geb:  # Nachbarn fuer Brandwaende (wie gebaeude2.bauen)
        x0, y0, x1, y1 = g["rechteck"]
        for o in geb:
            if o is g:
                continue
            a = o["rechteck"]
            ueberlapp_y = a[1] < y1 - 1 and a[3] > y0 + 1
            if ueberlapp_y and abs(a[2] - x0) < 0.6:
                g["nachbar_links" if g["front"] == "S" else "nachbar_rechts"] = True
            if ueberlapp_y and abs(a[0] - x1) < 0.6:
                g["nachbar_rechts" if g["front"] == "S" else "nachbar_links"] = True
    return cfg, geb


def erzeugen(cfg, g, plan_fn=None, masten=None):
    """Ein Gebaeude wie in gebaeude2.bauen() erzeugen. plan_fn(b, g) -> plan (vor dem Bau, aus Massen/Typ)."""
    rnd = random.Random(cfg["seed"] * 1000 + int(g["id"][1:]))
    g["cfg"] = cfg
    rahmen = P1.Rahmen(g["rechteck"], g["front"])
    x0, y0, x1, y1 = g["rechteck"]
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), ((x0 + x1) / 2, (y0 + y1) / 2)]
    z0 = V.h_max(pts) + 0.15
    g["zg"] = V.h_min(pts) - 0.3
    b = Bau3(rahmen, z0, rnd)
    b.g = g
    if plan_fn:
        b.plan = plan_fn(b, g)
        G2._tuer = _tuer_getrennt
        G2._schaufenster = _schaufenster_getrennt
    try:
        if g["typ"] in G2.NEU:
            G2.NEU[g["typ"]](b, g, rnd)
        else:
            P1.BAUER[g["typ"]](b, g, rnd)
    finally:
        G2._tuer = _TUER_ORIG
        G2._schaufenster = _SCHAUFENSTER_ORIG
    if b.plan is not None and g["typ"] == 1 and C.get("hinterausgang_typ1", True):
        b.plan["hinterausgang"] = hinterausgang_typ1(b)
    if b.plan is not None and g["typ"] == 2:
        b.plan["eingang"] = eingang_typ2(b)
    if b.plan is not None and g["typ"] == 5:
        b.plan["eingang"] = eingang_typ5(b)
    if b.plan is not None and getattr(b, "ladentuer", None):
        w_, ta, tc, sfz = b.ladentuer
        b.plan["ladentuer_geschnitten"] = eingang_schneiden(b, w_, ta, tc, b.z0, sfz + 0.07)
    FD.fassade(b, g, rnd, masten if masten is not None else G2._mastpunkte())
    FD.innenraum(b, g, rnd)
    if b.plan and b.plan.get("parkhaus"):
        b.plan["ebenen"] = sorted(b.plan.get("decken", []))
    if b.plan and b.plan.get("achse"):
        treppenhaus(b, b.plan)
        if g["id"] in C.get("innenausbau", {}).get("gebaeude", []):
            b.plan["ausbau"] = IA.ausbauen(b, b.plan, C, S, G2, V, VB)
        b.plan["durchgang_weg"] = durchgaenge_frei(b)
        b.plan["stufen_neu"] = stufen_ergaenzen(b)
    orig = Vector((x0, y0, z0))
    bmesh.ops.translate(b.bm, verts=b.bm.verts, vec=-orig)
    bmesh.ops.remove_doubles(b.bm, verts=b.bm.verts, dist=0.0005)
    return b, orig


def objektname(cfg, g, zaehler):
    tname = cfg["typnamen"][str(g["typ"])]
    zaehler[tname] = zaehler.get(tname, 0) + 1
    return f"BLD_{g['name']}" if g.get("name") else f"BLD_{tname}_{zaehler[tname]:02d}"


def uv_abdruck(me_or_bm):
    """Hash der sortierten UV-Koordinaten (Texturen sitzen gleich)."""
    if isinstance(me_or_bm, bmesh.types.BMesh):
        uvl = me_or_bm.loops.layers.uv.active
        uv = sorted((round(l[uvl].uv.x, 3), round(l[uvl].uv.y, 3)) for f in me_or_bm.faces for l in f.loops) if uvl else []
    else:
        lay = me_or_bm.uv_layers.active
        uv = sorted((round(d.uv[0], 3), round(d.uv[1], 3)) for d in lay.data) if lay else []
    return (hashlib.md5(str(uv).encode()).hexdigest()[:10],)


def fingerabdruck(me_or_bm):
    """Reihenfolge-unabhaengiger Vergleich: Anzahl + gerundete, sortierte Koordinaten (Hash)."""
    vs = me_or_bm.verts if isinstance(me_or_bm, bmesh.types.BMesh) else me_or_bm.vertices
    co = sorted((round(v.co.x, 3), round(v.co.y, 3), round(v.co.z, 3)) for v in vs)
    return len(co), hashlib.md5(str(co).encode()).hexdigest()[:10]


# ------------------------------------------------------------------ Tueren als eigene Objekte
_TUER_ORIG = G2._tuer


def _tuer_getrennt(b, w, s0, s1, z0, z1, rnd, offen=None):
    """Wie gebaeude2._tuer (gleiche Zufallszahlen!), aber das Tuerblatt kommt nicht ins Gebaeude-Mesh,
    sondern wird gemerkt und spaeter als eigenes, drehbares Objekt gebaut (Spiel: Tueren oeffnen)."""
    for (a, c, d, e) in [(s0, s0 + 0.08, z0, z1), (s1 - 0.08, s1, z0, z1), (s0, s1, z1 - 0.08, z1)]:
        G2.FA.box_welt(b.bm, w, a, c, 0.12, 0.2, d, e, S["Rahmen"])
    G2.FA.box_welt(b.bm, w, s0, s1, -0.06, w.d + 0.02, z0 - 0.2, z0, S["Beton"])  # Schwelle (Boden in der Wanddicke)
    en = (w.welt(0, 1, 0) - w.welt(0, 0, 0)).normalized()
    b.oeffnungen.append((w.welt((s0 + s1) / 2, 0, z0), -en, s1 - s0))  # auch ohne Tuerblatt ein Zugang
    zust = offen or rnd.choice(["zu", "offen", "offen", "fehlt"])
    if zust == "fehlt":
        return
    ang = 0 if zust == "zu" else rnd.uniform(0.4, 1.3)
    p0 = w.welt(s0 + 0.08, 0.16, z0)
    ex = (w.welt(s0 + 1.08, 0.16, z0) - p0).normalized()
    ey = (w.welt(s0 + 0.08, 1.16, z0) - p0).normalized()  # n waechst nach innen
    b.tueren.append({"p0": p0, "ex": ex, "ey": ey, "breite": (s1 - s0) - 0.16, "z0": z0, "z1": z1,
                     "zustand": zust, "winkel": ang, "richtung": 1.0, "mat": "Holz", "dicke": 0.045})


_SCHAUFENSTER_ORIG = G2._schaufenster


def _schaufenster_getrennt(b, w, o, g, rnd):
    """Kopie von gebaeude2._schaufenster mit GLEICHEN Zufallszahlen. Aenderungen: Riegel und Sockelpaneel laufen nicht
    durch das Tuerfeld, die Glastuer wird ein eigenes Objekt, das Tuerfeld wird spaeter bis zum Boden geoeffnet."""
    import math as _m
    from mathutils import Matrix as _M
    FA = G2.FA
    s0, s1, z0, z1 = o["s0"], o["s1"], o["z0"], o["z1"]
    n0, t = 0.2, 0.07
    zk = z0 + 2.5
    felder = max(2, round((s1 - s0) / 1.6))
    xs = [s0 + (s1 - s0) * k / felder for k in range(felder + 1)]
    for x in xs:
        FA.box_welt(b.bm, w, x - 0.04, x + 0.04, n0, n0 + t, z0, z1, S["Metall"])
    tuer_i = rnd.randrange(felder)
    ta, tc = xs[tuer_i] + 0.04, xs[tuer_i + 1] - 0.04
    for z in (z0, zk, z1 - 0.04):
        if z == z0:  # unterer Riegel: Tuerfeld frei
            for (aa, cc) in ((s0, ta), (tc, s1)):
                if cc - aa > 0.01:
                    FA.box_welt(b.bm, w, aa, cc, n0, n0 + t, z, z + 0.06, S["Metall"])
        else:
            FA.box_welt(b.bm, w, s0, s1, n0, n0 + t, z, z + 0.06, S["Metall"])
    for (aa, cc) in ((s0 - 0.05, ta), (tc, s1 + 0.05)):  # Sockelpaneel ohne Tuerfeld
        if cc - aa > 0.01:
            FA.box_welt(b.bm, w, aa, cc, -0.04, 0.0, z0 - 0.5 + 0.05, z0, S["Holz"])
    geplndert = g["zerstoerung"] != "leicht" or rnd.random() < 0.6
    vernagelt = g["zerstoerung"] == "mittel" and rnd.random() < 0.35
    for k in range(felder):
        a, c = xs[k] + 0.04, xs[k + 1] - 0.04
        for (zu, zo) in ((z0 + 0.06, zk), (zk + 0.06, z1 - 0.04)):
            if k == tuer_i and zo <= zk + 0.01:
                continue
            zust = "fehlt" if (geplndert and rnd.random() < 0.6) else ("zerbrochen" if rnd.random() < 0.5 else "intakt")
            if zust == "intakt":
                G2._glas(b, w, a, c, zu, zo, n0 + t / 2)
            elif zust == "zerbrochen":
                for (cs, cz, ds, dz) in [(a, zu, 1, 1), (c, zu, -1, 1), (a, zo, 1, -1), (c, zo, -1, -1)]:
                    if rnd.random() < 0.6:
                        vs = [b.bm.verts.new(w.welt(s_, n0 + t / 2, z_)) for s_, z_ in ((cs, cz), (cs + ds * rnd.uniform(0.1, 0.5), cz), (cs, cz + dz * rnd.uniform(0.15, 0.9)))]
                        f = b.bm.faces.new(vs)
                        f.material_index = S["Glas"]
                b.boden_teile.append((w.welt((a + c) / 2, -0.5, 0), "glas"))
            else:
                b.boden_teile.append((w.welt((a + c) / 2, -0.6, 0), "glas"))
    if vernagelt:
        x = s0 - 0.05
        while x < s1:
            if rnd.random() < 0.8:
                FA.schiefe_box(b.bm, w, x, min(x + 1.22, s1 + 0.05), -0.05, -0.03, z0 - 0.2, z0 + 2.3, S["Sperrholz"],
                               winkel=_m.radians(rnd.uniform(-2.5, 2.5)))
            x += 1.24
    b.ladentuer = (w, ta, tc, z0)
    if rnd.random() < 0.6:  # Glastuer (Metallrahmen), nach aussen offen -> eigenes Objekt
        ang = rnd.uniform(0.5, 1.4)
        p0 = w.welt(ta, n0, z0 - 0.45 - 0.02)
        ex = (w.welt(ta + 1.0, n0, 0) - w.welt(ta, n0, 0)).normalized()
        ey = (w.welt(ta, n0 + 1.0, 0) - w.welt(ta, n0, 0)).normalized()
        b.tueren.append({"p0": p0, "ex": ex, "ey": ey, "breite": tc - ta, "z0": z0 - 0.45 - 0.02, "z1": zk - 0.05 + 0.1,
                         "zustand": "offen", "winkel": ang, "richtung": -1.0, "mat": "Metall", "dicke": 0.05})
    _ = _M


def eingang_schneiden(b, w, s_a, s_c, z_a, z_b, z_laibung=None, kaempfer=False):
    """Bruestung unter einer Tuer bis zum Boden entfernen (Wand nachtraeglich aufschneiden), Laibungen + Schwelle."""
    o = w.welt(0, 0, 0)
    es = (w.welt(1, 0, 0) - o).normalized()
    en = (w.welt(0, 1, 0) - o).normalized()

    def sn(p):
        d = p - o
        return d.dot(es), d.dot(en)

    def kandidaten(nur_unten=True):
        out = []
        for f in b.bm.faces:
            ok, irgendwo = True, False
            for v in f.verts:
                s_, n_ = sn(v.co)
                if not (-0.15 <= n_ <= w.d + 0.15 and s_a - 3 <= s_ <= s_c + 3) or (nur_unten and v.co.z > z_b + 0.01):
                    ok = False
                    break
                irgendwo |= z_a - 0.3 <= v.co.z <= z_b + 0.01
            if ok and irgendwo:
                out.append(f)
        return out
    # zuerst waagerecht bei z_b schneiden (Pfosten/Scheiben, die hoeher reichen), dann senkrecht und unten
    fs = kandidaten(False)
    if fs:
        geom = list({v for f in fs for v in f.verts}) + list({e for f in fs for e in f.edges}) + fs
        bmesh.ops.bisect_plane(b.bm, geom=geom, plane_co=Vector((0, 0, z_b)), plane_no=Vector((0, 0, 1)), dist=1e-5)
    for (pc, pn) in ((o + es * s_a, es), (o + es * s_c, es), (Vector((0, 0, z_a)), Vector((0, 0, 1)))):
        fs = kandidaten()
        if not fs:
            return 0
        geom = list({v for f in fs for v in f.verts}) + list({e for f in fs for e in f.edges}) + fs
        bmesh.ops.bisect_plane(b.bm, geom=geom, plane_co=pc, plane_no=pn, dist=1e-5)
    weg = []
    for f in kandidaten():
        c = f.calc_center_median()
        s_, n_ = sn(c)
        if s_a + 1e-4 < s_ < s_c - 1e-4 and z_a + 1e-4 < c.z < z_b:
            weg.append(f)
    bmesh.ops.delete(b.bm, geom=weg, context="FACES")
    FA = G2.FA
    zl = z_b if z_laibung is None else z_laibung
    for s_ in (s_a, s_c):  # Laibungen (nur so hoch, wie dort Wand war)
        vs = [b.bm.verts.new(w.welt(s_, n_, z_)) for n_, z_ in ((0.0, z_a), (w.d, z_a), (w.d, zl), (0.0, zl))]
        f = b.bm.faces.new(vs)
        f.material_index = S["Fassade"]
    FA.box_welt(b.bm, w, s_a, s_c, -0.06, w.d + 0.02, z_a - 0.2, z_a, S["Beton"])  # Schwelle
    if kaempfer:  # Querriegel ueber der Tuer (Pfosten enden dort)
        FA.box_welt(b.bm, w, s_a - 0.03, s_c + 0.03, 0.12, 0.22, z_b, z_b + 0.08, S["Metall"])
    return len(weg)


def teil_entfernen(b, mitte, radius, mat):
    """Zusammenhaengendes Teil eines Materials (z. B. Drehtuer-Zylinder) nahe 'mitte' (x, y) entfernen."""
    gesehen, weg = set(), []
    for f in b.bm.faces:
        if f in gesehen or f.material_index != mat:
            continue
        teil, stapel = [], [f]
        gesehen.add(f)
        while stapel:
            ff = stapel.pop()
            teil.append(ff)
            for e in ff.edges:
                for nf in e.link_faces:
                    if nf not in gesehen and nf.material_index == mat:
                        gesehen.add(nf)
                        stapel.append(nf)
        if all(math.hypot(v.co.x - mitte[0], v.co.y - mitte[1]) <= radius for ff in teil for v in ff.verts):
            weg += teil
    bmesh.ops.delete(b.bm, geom=weg, context="FACES")
    return len(weg)


def bereich_loeschen(b, w, s_a, s_c, n_a, n_b, z_a, z_b):
    """Alle Flaechen, die ganz in einem Quader (Wandkoordinaten) liegen, loeschen."""
    o = w.welt(0, 0, 0)
    es = (w.welt(1, 0, 0) - o).normalized()
    en = (w.welt(0, 1, 0) - o).normalized()
    weg = []
    for f in b.bm.faces:
        if all(s_a - 1e-4 <= (v.co - o).dot(es) <= s_c + 1e-4 and n_a - 1e-4 <= (v.co - o).dot(en) <= n_b + 1e-4
               and z_a - 1e-4 <= v.co.z <= z_b + 1e-4 for v in f.verts):
            weg.append(f)
    bmesh.ops.delete(b.bm, geom=weg, context="FACES")
    return len(weg)


def box_ausschneiden(b, w, s_a, s_c, n_a, n_b, z_a, z_b):
    """Alles in einem Quader (Wandkoordinaten) herausschneiden: Flaechen an s_a/s_c auftrennen, Inneres loeschen."""
    o = w.welt(0, 0, 0)
    es = (w.welt(1, 0, 0) - o).normalized()
    en = (w.welt(0, 1, 0) - o).normalized()

    def kand():
        out = []
        for f in b.bm.faces:
            cs = [((v.co - o).dot(es), (v.co - o).dot(en), v.co.z) for v in f.verts]
            if all(n_a - 1e-4 <= n_ <= n_b + 1e-4 and z_a - 1e-4 <= z_ <= z_b + 1e-4 for _, n_, z_ in cs) and \
                    min(c[0] for c in cs) < s_c and max(c[0] for c in cs) > s_a:
                out.append(f)
        return out
    for sp in (s_a, s_c):
        fs = kand()
        if fs:
            geom = list({v for f in fs for v in f.verts}) + list({e for f in fs for e in f.edges}) + fs
            bmesh.ops.bisect_plane(b.bm, geom=geom, plane_co=o + es * sp, plane_no=es, dist=1e-5)
    weg = [f for f in kand() if s_a + 1e-4 < (f.calc_center_median() - o).dot(es) < s_c - 1e-4]
    bmesh.ops.delete(b.bm, geom=weg, context="FACES")
    return len(weg)


def eingang_typ2(b):
    """Holzhaus: geschlossene Fliegengittertuer vor der Haustuer -> eigenes Objekt (halb offen, nach aussen)."""
    W = b.r.W
    ze = b.info["geschosse"][0]
    w = b.wand("vorne", 0.18)
    t0, t1 = W / 2 - 0.48, W / 2 + 0.48
    n = bereich_loeschen(b, w, t0, t1, -0.125, -0.085, ze - 0.01, ze + 2.11)
    # Veranda: Gelaender/Pfosten vor der Treppe (Treppe W/2 +- 0,7) herausschneiden, neue Pfosten an der Oeffnung
    ze_ = ze
    n += box_ausschneiden(b, w, W / 2 - 0.72, W / 2 + 0.72, -2.33, -2.17, ze_ - 0.01, ze_ + 2.6)
    for uu in (W / 2 - 0.79, W / 2 + 0.79):
        G2.Bau2.box(b, uu - 0.07, -2.32, uu + 0.07, -2.18, ze_, ze_ + 2.4, S["Rahmen"])
    p0 = w.welt(t0, -0.12, ze - 0.02)
    ex = (w.welt(t0 + 1.0, -0.12, 0) - w.welt(t0, -0.12, 0)).normalized()
    ey = (w.welt(t0, 0.88, 0) - w.welt(t0, -0.12, 0)).normalized()
    b.tueren.append({"p0": p0, "ex": ex, "ey": ey, "breite": t1 - t0, "z0": ze - 0.02, "z1": ze + 2.1 + 0.08,
                     "zustand": "offen", "winkel": math.radians(70), "richtung": -1.0, "mat": "Rahmen", "dicke": 0.03,
                     "art": "fliegengitter"})
    return {"fliegengitter_flaechen": n}


def zugaenge(b):
    """Aussentueren als (Mitte, Richtung nach aussen, Breite, Schwellenhoehe)."""
    out = list(b.oeffnungen)
    if getattr(b, "ladentuer", None):
        w, ta, tc, _ = b.ladentuer
        o, en = w.welt(0, 0, 0), (w.welt(0, 1, 0) - w.welt(0, 0, 0)).normalized()
        m = w.welt((ta + tc) / 2, 0, b.z0)
        out.append((m, -en, tc - ta))
    if b.g["typ"] == 5:
        w = b.wand("vorne")
        en = (w.welt(0, 1, 0) - w.welt(0, 0, 0)).normalized()
        out.append((w.welt(b.r.W / 2, 0, b.z0), -en, 2.4))
    return out


def durchgaenge_frei(b):
    """Kleine Anbauteile (Kaesten, Schilder), die in einen Tuerdurchgang ragen, entfernen."""
    weg, gesehen = [], set()
    bereiche = []
    for mitte, d, breite in zugaenge(b):
        d = Vector((d.x, d.y, 0)).normalized()
        bereiche.append((mitte, d, Vector((-d.y, d.x, 0)), breite))
    for f in b.bm.faces:
        if f in gesehen:
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
        if len(teil) > 30:
            continue
        for mitte, d, q, breite in bereiche:
            if any(abs((v.co - mitte).dot(q)) < breite / 2 - 0.1 and -0.45 <= (v.co - mitte).dot(d) <= 0.6
                   and mitte.z + 0.1 <= v.co.z <= mitte.z + 2.05 for ff in teil for v in ff.verts):
                weg += teil
                break
    bmesh.ops.delete(b.bm, geom=weg, context="FACES")
    return len(weg)


def stufen_ergaenzen(b):
    """Vor jeder Aussentuer nach aussen laufen bis zum Fuss der vorhandenen Treppe; liegt der Fuss hoeher als
    das Gelaende, Stufen ergaenzen (Steigung <= 0,17 m, Auftritt 0,30 m) bis auf das Gelaende."""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromBMesh(b.bm)
    T = C["aussentreppe"]
    neu = 0
    for mitte, d, breite in zugaenge(b):
        d = Vector((d.x, d.y, 0)).normalized()
        q = Vector((-d.y, d.x, 0))
        z = mitte.z
        p = mitte.copy()
        a = 0.0
        while a < 8.0:  # vorhandene Flaechen (Schwelle, Podest, Veranda, Stufen) entlang gehen
            a += 0.1
            pp = mitte + d * a
            h = bvh.ray_cast(Vector((pp.x, pp.y, z + 0.3)), Vector((0, 0, -1)), 0.3 + T["steigung"] + 0.03)
            if h[0] is None or h[1].z < 0.7:
                break
            z, p = h[0].z, pp
        boden = V.h(p.x, p.y)
        if z - boden <= T["steigung"] + 0.02:
            continue
        n = math.ceil((z - boden) / T["steigung"])
        st = (z - boden) / n
        fuss = p + d * 0.05  # Kante der letzten vorhandenen Flaeche
        for i in range(1, n):
            a0, a1 = (i - 1) * T["auftritt"], i * T["auftritt"]
            ecken = [fuss + d * aa + q * qq for aa in (a0, a1) for qq in (-breite / 2 - 0.2, breite / 2 + 0.2)]
            xs, ys = [e.x for e in ecken], [e.y for e in ecken]
            zb = z - i * st
            zg = min(V.h(e.x, e.y) for e in ecken) - 0.25
            fs = V.box(b.bm, min(xs), min(ys), zg, max(xs), max(ys), zb)
            for f in fs:
                f.material_index = S["Beton"]
            neu += 1
    return neu


def hinterausgang_typ1(b):
    """Wohnhaus: Hintertuer zum Hof (Erdgeschoss), dort wo in der Rueckwand kein Fenster ist."""
    info = b.info or {}
    eg = info.get("geschosse", [b.z0])[0]
    w = b.wand("hinten")
    fenster = sorted((o["s0"], o["s1"]) for o in info.get("ops", {}).get("hinten", []) if o["z0"] < eg + 2.3 and o["z1"] > eg)
    breite, rand = 1.0, 0.9
    kandidaten = []
    a = w.s0 + rand
    for (f0, f1) in fenster + [(w.s1 - rand, w.s1)]:
        if f0 - 0.25 - a >= breite:
            kandidaten.append((a + (f0 - 0.25 - a - breite) / 2))
        a = max(a, f1 + 0.25)
    if not kandidaten:
        return None
    mitte = (w.s0 + w.s1) / 2
    s0 = min(kandidaten, key=lambda k: abs(k + breite / 2 - mitte))
    s1 = s0 + breite
    eingang_schneiden(b, w, s0, s1, eg, eg + 2.2, z_laibung=eg + 2.2)
    for (aa, cc, d, e) in [(s0, s0 + 0.08, eg, eg + 2.2), (s1 - 0.08, s1, eg, eg + 2.2), (s0, s1, eg + 2.12, eg + 2.2)]:
        G2.FA.box_welt(b.bm, w, aa, cc, 0.12, 0.2, d, e, S["Rahmen"])  # Zarge
    G2.FA.box_welt(b.bm, w, s0 - 0.05, s1 + 0.05, -0.02, w.d + 0.02, eg + 2.2, eg + 2.45, S["Beton"])  # Sturz
    en = (w.welt(0, 1, 0) - w.welt(0, 0, 0)).normalized()
    b.oeffnungen.append((w.welt((s0 + s1) / 2, 0, eg), -en, breite))
    rnd = b.plan["rnd"]
    p0 = w.welt(s0 + 0.08, 0.16, eg)
    ex = (w.welt(s0 + 1.08, 0.16, eg) - p0).normalized()
    ey = (w.welt(s0 + 0.08, 1.16, eg) - p0).normalized()
    zust = rnd.choice(["zu", "offen", "offen"])
    b.tueren.append({"p0": p0, "ex": ex, "ey": ey, "breite": breite - 0.16, "z0": eg, "z1": eg + 2.2,
                     "zustand": zust, "winkel": 0.0 if zust == "zu" else rnd.uniform(0.4, 1.3), "richtung": 1.0,
                     "mat": "Holz", "dicke": 0.045})
    return round(s0, 2)


def eingang_typ5(b):
    """Buero: massiver Drehtuer-Zylinder weg, Glasfassade in der Mitte 2,4 m breit bis zum Boden offen, Kaempfer."""
    W = b.r.W
    w = b.wand("vorne")
    x, y = b.r.p(W / 2, -0.2)
    n = teil_entfernen(b, (x, y), 1.25, S["Glas"])
    z0 = b.z0
    m = eingang_schneiden(b, w, W / 2 - 1.2, W / 2 + 1.2, z0, z0 + 2.4, z_laibung=z0 + 0.3, kaempfer=True)
    return {"drehtuer_flaechen": n, "fassade_flaechen": m}


def tueren_bauen(b, gid, name, orig, ob_geb):
    """Tuerblaetter als Objekte TUER_<id>_<n>; Ursprung im Scharnier, lokale z-Drehung = Oeffnung (nach innen)."""
    from mathutils import Matrix
    col = V.collection("03_Gebaeude/Tueren")
    for alt in [o for o in col.objects if o.get("gebaeude") == gid]:
        bpy.data.objects.remove(alt)
    for k, t in enumerate(b.tueren):
        idx = S[t.get("mat", "Holz")]
        holz = ob_geb.data.materials[idx] if len(ob_geb.data.materials) > idx else None
        ex, ey = t["ex"], t["ey"]
        ez = Vector((0, 0, 1))
        innen = 1.0
        if ex.cross(ey).dot(ez) < 0:  # rechtshaendiges Objekt-System: y nach aussen drehen, Oeffnung spiegeln
            ey, innen = -ey, -1.0
        me = bpy.data.meshes.new(f"TUER_{gid}_{k + 1:02d}")
        bm = bmesh.new()
        L, H = t["breite"], t["z1"] - t["z0"]
        dk = t.get("dicke", 0.045)
        y0, y1 = (0.0, dk) if innen > 0 else (-dk, 0.0)
        if t.get("art") == "fliegengitter":  # Rahmen (5 cm) mit Mittelriegel, Gitter zerrissen (fehlt)
            for (a, c, za, zb) in ((0, 0.05, 0.02, H - 0.1), (L - 0.05, L, 0.02, H - 0.1), (0, L, H - 0.15, H - 0.1),
                                   (0, L, 0.02, 0.07), (0, L, 1.0, 1.05)):
                V.box(bm, a, y0, za, c, y1, zb)
        else:
            V.box(bm, 0.0, y0, 0.02, L, y1, H - 0.1)
        bm.to_mesh(me)
        bm.free()
        if holz:
            me.materials.append(holz)
        ob = bpy.data.objects.new(f"TUER_{gid}_{k + 1:02d}", me)
        col.objects.link(ob)
        m = Matrix((ex, ey, ez)).transposed().to_4x4()
        m.translation = t["p0"]
        ob.matrix_world = m @ Matrix.Rotation(innen * t.get("richtung", 1.0) * t["winkel"], 4, "Z")
        ob["gebaeude"], ob["zustand"], ob["oeffnung_grad"] = gid, t["zustand"], round(math.degrees(t["winkel"]), 1)
        ob["oeffnet_nach"] = "innen" if t.get("richtung", 1.0) > 0 else "aussen"
        ob["breite_m"], ob["hoehe_m"] = round(L, 3), round(H, 3)
    return len(b.tueren)


# ------------------------------------------------------------------ Planung Treppenhaus
def _treppenmass(hoehen):
    """Stufenzahl je Lauf fuer die groesste Geschosshoehe; Laenge des Treppenhauses (U-Treppe mit Zwischenpodest)."""
    T = C["treppe"]
    hmax = max(hoehen)
    n = math.ceil(hmax / T["steigung_max"])
    n1 = math.ceil(n / 2)
    lauf = (n1 - 1) * T["auftritt"]
    return lauf, T["podest"] * 2 + lauf


def plan_erstellen(b, g):
    """Lage des Treppenhauses im lokalen (u, v)-System; None = Gebaeude bleibt unveraendert."""
    if g["id"] in C.get("ausnahmen", {}):
        return None
    if g["typ"] == 7 and C.get("parkhaus"):
        return {"parkhaus": True, "loch": False, "kern": False, "tueren": [],
                "rnd": random.Random(C["seed"] * 1000 + int(g["id"][1:]))}
    if g["typ"] not in C["typen"]:
        return None
    W, D = b.r.W, b.r.D
    T = C["treppe"]
    breite = 2 * T["laufbreite"] + T["auge"]
    # Ebenen vorab aus den Typ-Regeln (die echten Werte setzt der Typ-Bauer in b.info; hier nur fuer die Masse)
    hoehen = {1: [3.2], 2: [2.8], 3: [4.6, 3.2], 5: [3.8], 6: [4.0], 8: [3.5]}[g["typ"]]
    lauf, laenge = _treppenmass(hoehen)
    d = 0.18 if g["typ"] == 2 else 0.3
    e = C["kern_einzug"]
    kern = g["typ"] in (1, 3, 5, 6, 8) and W > 11 and D > 11 and not (g["typ"] == 5 and False)
    plan = {"breite": breite, "laenge": laenge, "lauf": lauf, "kern": kern, "e": e, "d": d, "loch": True,
            "rnd": random.Random(C["seed"] * 1000 + int(g["id"][1:])), "tueren": []}
    if kern:
        ki_u, ki_v = W - 2 * e - 0.4, D - 2 * e - 0.4  # Innenmass des Kerns (Wand 0,2 m)
        if ki_v >= laenge + 0.6 and ki_u >= breite:
            plan.update(achse="v", u0=e + 0.2, v0=D - e - 0.2 - laenge)
        elif ki_u >= laenge + 0.6 and ki_v >= breite:
            plan.update(achse="u", u0=W - e - 0.2 - laenge, v0=e + 0.2)
        else:
            plan["kern"] = False
    if not plan["kern"]:
        if D - 2 * d >= laenge + 3.0:
            plan.update(achse="v", u0=d, v0=D - d - laenge)
        elif W - 2 * d >= laenge + 3.0:
            plan.update(achse="u", u0=W - d - laenge, v0=d)
        else:
            return None
    if g["typ"] == 5 and not g.get("kamera_dach"):  # Dachaufbau (Maschinenraum) aus gebaeude2.typ5
        (ru0, rv0, ru1, rv1), _ = _rechteck(plan)
        mu0, mv0, mu1, mv1 = W * 0.35, D * 0.35, W * 0.65, D * 0.65
        if mu0 < ru1 and mu1 > ru0 and mv0 < rv1 and mv1 > rv0:
            plan["dachraum_plan"] = True
    return plan


def _rechteck(p):
    """Treppenhaus (u0, v0, u1, v1) und Deckenloch (ohne Antrittspodest)."""
    if p["achse"] == "v":
        r = (p["u0"], p["v0"], p["u0"] + p["breite"], p["v0"] + p["laenge"])
        loch = (r[0], r[1] + C["treppe"]["podest"], r[2], r[3])
    else:
        r = (p["u0"], p["v0"], p["u0"] + p["laenge"], p["v0"] + p["breite"])
        loch = (r[0], r[1], r[2] - C["treppe"]["podest"], r[3])  # Antritt liegt bei u1 (Laeufe laufen nach -u)
    return r, loch


def _luke(p):
    """Dachluke (0,8 x 0,8 m) ueber dem Antrittspodest des obersten Geschosses, an der Wand (Leiter dort)."""
    if p["achse"] == "v":
        return (p["u0"] + 0.05, p["v0"] + 0.2, p["u0"] + 0.85, p["v0"] + 1.0)
    u1 = p["u0"] + p["laenge"]
    return (u1 - 1.0, p["v0"] + 0.05, u1 - 0.2, p["v0"] + 0.85)


def _ist_dach(b, zb):
    info = b.info or {}
    return info.get("top") is not None and abs(zb - info["top"]) < 0.01


def _luke_modus(p):
    return C.get("dachzugang", "luke") == "luke" and not p.get("dachraum_plan")


# ------------------------------------------------------------------ Eingriffe in box()
def _ist_kern(b, p, u0, v0, u1, v1, za, zb, mat, top):
    e = p["e"]
    return mat == S["InnenWand"] and top == S["InnenDecke"] and abs(u0 - e) < 1e-6 and abs(v0 - e) < 1e-6 and zb - za > 2.5


def _ist_dachraum(b, p, u0, v0, u1, v1, za, zb, mat):
    """Massiver Dachaufbau (Maschinenraum), der ueber dem Treppenhaus steht."""
    info = b.info or {}
    if mat != S["Beton"] or info.get("top") is None or abs(za - info["top"]) > 0.01 or zb - za < 2.0:
        return False
    (ru0, rv0, ru1, rv1), _ = _rechteck(p)
    return min(u0, u1) < ru1 and max(u0, u1) > ru0 and min(v0, v1) < rv1 and max(v0, v1) > rv0


def _ist_decke(b, p, u0, v0, u1, v1, za, zb, mat):
    _, (lu0, lv0, lu1, lv1) = _rechteck(p)
    if _ist_dach(b, zb) and _luke_modus(p):
        lu0, lv0, lu1, lv1 = _luke(p)
    if mat != S["InnenDecke"] or not (0.12 <= zb - za <= 0.35):
        return False
    if not (min(u0, u1) <= lu0 and max(u0, u1) >= lu1 and min(v0, v1) <= lv0 and max(v0, v1) >= lv1):
        return False
    info = b.info or {}
    ge = info.get("geschosse") or [b.z0]
    if zb <= min(ge) + 0.5:  # Bodenplatte des Erdgeschosses bleibt geschlossen
        return False
    if b.g["typ"] == 2 and info.get("top") is not None and abs(zb - info["top"]) < 0.01:
        return False  # Holzhaus: Decke unter dem Spitzdach bleibt zu (kein Dachausstieg)
    return True


def decke_mit_loch(b, p, u0, v0, u1, v1, za, zb, mat, top):
    _, (lu0, lv0, lu1, lv1) = _rechteck(p)
    if _ist_dach(b, zb) and _luke_modus(p):  # Nutzer 6.4 (1B): Dachluke statt Treppenhaus-Aufbau
        lu0, lv0, lu1, lv1 = _luke(p)
        p["luke"] = True
    u0, u1, v0, v1 = min(u0, u1), max(u0, u1), min(v0, v1), max(v0, v1)
    fs = []
    for (a, c, d_, e_) in ((u0, v0, lu0, v1), (lu1, v0, u1, v1), (lu0, v0, lu1, lv0), (lu0, lv1, lu1, v1)):
        if d_ - a > 0.01 and e_ - c > 0.01:
            fs += G2.Bau2.box(b, a, c, d_, e_, za, zb, mat, top)
    p.setdefault("decken", []).append(zb)
    b.log["decken_geloch"] += 1
    return fs


def kern_hohl(b, p, u0, v0, u1, v1, za, zb):
    """Massiven Kern ersetzen: 4 Waende (0,2 m) mit Tuer je Geschoss und Seite; Aussenmass wie vorher."""
    p["kern_box"] = (u0, v0, u1, v1, za, zb)
    b.log["kern_hohl"] += 1
    return []  # Waende baut treppenhaus(), wenn die Geschosshoehen bekannt sind


# ------------------------------------------------------------------ Treppenhaus bauen
def _box(b, u0, v0, u1, v1, za, zb, mat, top=None):
    return G2.Bau2.box(b, min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1), za, zb, mat, top)


def _wand_mit_tueren(b, achse, fest, a0, a1, dicke, za, zb, tueren, mat):
    """Wand entlang u (achse='u', v = fest) oder v (achse='v', u = fest) von a0..a1, Tueren [(t0, t1, hoehe)]."""
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
        if achse == "u":
            _box(b, s0, fest, s1, fest + dicke, z0, z1, mat)
        else:
            _box(b, fest, s0, fest + dicke, s1, z0, z1, mat)


def _ebenen(b):
    info = b.info or {}
    ge = list(info.get("geschosse", []))
    top = info.get("top")
    return ge, top


def _furniture_weg(b, r, ebenen):
    """Moebel/Lampen, die im Treppenhaus stehen, entfernen (Teile, die ganz im Treppenhaus-Grundriss liegen)."""
    (u0, v0, u1, v1) = r
    pa, pb = b.r.p(u0, v0), b.r.p(u1, v1)
    rand = C["moebel_abstand"]  # Moebel, die das Treppenhaus (mit Abstand) beruehren, fallen weg
    x0, x1 = min(pa[0], pb[0]) - rand, max(pa[0], pb[0]) + rand
    y0, y1 = min(pa[1], pb[1]) - rand, max(pa[1], pb[1]) + rand
    moebel = {S["Holz"], S["Metall"], S["Stoff"], S["Lack"]}
    weg, gesehen = [], set()
    for f in b.bm.faces:
        if f in gesehen or f.material_index not in moebel:
            continue
        teil, stapel = [], [f]
        gesehen.add(f)
        while stapel:  # zusammenhaengendes Teil (BMFace-Objekte, .index ist hier nicht aktuell)
            ff = stapel.pop()
            teil.append(ff)
            for e in ff.edges:
                for nf in e.link_faces:
                    if nf not in gesehen:
                        gesehen.add(nf)
                        stapel.append(nf)
        if len(teil) > 60:
            continue
        xs = [v.co.x for ff in teil for v in ff.verts]
        ys = [v.co.y for ff in teil for v in ff.verts]
        if max(xs) > x0 and min(xs) < x1 and max(ys) > y0 and min(ys) < y1:
            weg += teil
    bmesh.ops.delete(b.bm, geom=list(set(weg)), context="FACES")
    return len(weg)


def treppenhaus(b, p):
    T = C["treppe"]
    ebenen, top = _ebenen(b)
    if not ebenen or top is None:
        return
    r, loch = _rechteck(p)
    u0, v0, u1, v1 = r
    stufen_mat, wand_mat = S["Beton"], S["InnenWand"]
    # Dach nur, wenn die Dachplatte wirklich ein Loch bekommen hat (eingestuerzte Daecher: Platte in Teilen)
    dach = C["dachausstieg"] and b.g["typ"] != 2 and any(abs(z - top) < 0.01 for z in p.get("decken", [])) \
        and not p.get("luke")
    hoch = sorted(set([round(z, 4) for z in ebenen] + ([round(top, 4)] if dach else [])))
    if len(hoch) < 2:
        return
    p["moebel_weg"] = _furniture_weg(b, r, hoch)
    p["ebenen"] = hoch
    lb, auge, auft, pod = T["laufbreite"], T["auge"], T["auftritt"], T["podest"]
    for za, zb in zip(hoch, hoch[1:]):
        h = zb - za
        n = math.ceil(h / T["steigung_max"])
        st = h / n
        n1 = math.ceil(n / 2)
        n2 = n - n1
        zm = za + n1 * st
        # lokale Laufkoordinate t (0 = Antrittspodest-Kante), q quer (0..breite)
        def B(t0, t1, q0, q1, z0, z1, mat=stufen_mat):
            if p["achse"] == "v":
                _box(b, u0 + q0, v0 + pod + t0, u0 + q1, v0 + pod + t1, z0, z1, mat)
            else:
                _box(b, u1 - pod - t1, v0 + q0, u1 - pod - t0, v0 + q1, z0, z1, mat)
        unter = T["laufplatte"]  # Stufen als Laufplatte (schraege Unterseite) statt Vollblock -> Kopffreiheit darunter
        for k in range(1, n1):  # Lauf 1 (q 0..lb): vom Antritt weg nach oben
            B((k - 1) * auft, k * auft, 0, lb, max(za, za + k * st - st - unter), za + k * st)
        lauf1 = (n1 - 1) * auft
        B(lauf1, lauf1 + pod, 0, 2 * lb + auge, zm - 0.22, zm)  # Zwischenpodest
        auft2 = lauf1 / max(1, n2 - 1)  # ungerade Stufenzahl: Lauf 2 hat eine Stufe weniger -> Auftritt strecken (keine Luecke am Austritt)
        for j in range(1, n2):  # Lauf 2 (q lb+auge..breite): zurueck Richtung Antritt
            t1 = lauf1 - (j - 1) * auft2
            B(t1 - auft2, t1, lb + auge, 2 * lb + auge, max(za, zm + j * st - st - unter), zm + j * st)
        # Treppenauge als Bruestung zwischen den Laeufen (abgestuft)
        for k in range(1, max(n1, n2) + 1):
            hz = max(za + min(k, n1) * st, zm + min(k, n2 - 1) * st if n2 > 1 else zm)
            B((k - 1) * auft, min(k * auft, lauf1), lb, lb + auge, za, min(hz + T["gelaender"], zb - 0.3))
    # Gelaender am Deckenloch (offene Seiten), je obere Ebene
    lu0, lv0, lu1, lv1 = loch
    for z in hoch[1:]:
        if p["achse"] == "v":
            _box(b, lu1, lv0, lu1 + 0.06, lv1, z, z + T["gelaender"], S["Metall"])  # Laengsseite zum Raum
        else:
            _box(b, lu0, lv1, lu1, lv1 + 0.06, z, z + T["gelaender"], S["Metall"])
    # Kern als Waende mit Tueren
    if p.get("kern_box"):
        ku0, kv0, ku1, kv1, kza, kzb = p["kern_box"]
        dk = 0.2
        rnd = p["rnd"]
        stockw = [z for z in ebenen if kza - 0.01 <= z <= kzb]
        for k, za in enumerate(stockw):
            zb = stockw[k + 1] - 0.25 if k + 1 < len(stockw) else kzb
            for seite in ("vorne", "hinten", "links", "rechts"):
                if seite in ("vorne", "hinten"):
                    a0, a1 = ku0, ku1
                    m = rnd.uniform(a0 + 1.2, a1 - 2.2)
                    fest = kv0 if seite == "vorne" else kv1 - dk
                    _wand_mit_tueren(b, "u", fest, a0, a1, dk, za, zb, [(m, m + T["tuer_breite"], T["tuer_hoehe"])], wand_mat)
                else:
                    a0, a1 = kv0 + dk, kv1 - dk
                    m = rnd.uniform(a0 + 1.0, a1 - 2.0)
                    fest = ku0 if seite == "links" else ku1 - dk
                    _wand_mit_tueren(b, "v", fest, a0, a1, dk, za, zb, [(m, m + T["tuer_breite"], T["tuer_hoehe"])], wand_mat)
                p["tueren"].append((seite, za))
        # Kerndach wie vorher (Oberseite war InnenDecke)
    if p.get("luke"):
        leiter_und_luke(b, p, max(ebenen), top)
    # Dachausstieg: kleines Treppenhaus-Haus ueber dem Loch mit Tuer zum Dach
    if dach and p.get("dachraum"):  # Maschinenraum hohl: Huelle um Aufbau + Treppenhaus, Tuer zum Dach
        du0, dv0, du1, dv1, za, zb = p["dachraum"]
        ru0, rv0, ru1, rv1 = min(du0, u0 - 0.25), min(dv0, v0 - 0.25), max(du1, u1 + 0.25), max(dv1, v1 + 0.25)
        dk = 0.25
        m = (ru0 + ru1) / 2
        _wand_mit_tueren(b, "u", rv0, ru0, ru1, dk, za, zb, [(m - 0.5, m + 0.5, T["tuer_hoehe"])], S["Beton"])
        _box(b, ru0, rv1 - dk, ru1, rv1, za, zb, S["Beton"])
        _box(b, ru0, rv0 + dk, ru0 + dk, rv1 - dk, za, zb, S["Beton"])
        _box(b, ru1 - dk, rv0 + dk, ru1, rv1 - dk, za, zb, S["Beton"])
        _box(b, ru0, rv0, ru1, rv1, zb - 0.25, zb, S["InnenDecke"], top=S["Dach"])
        p["dachhaus"] = "maschinenraum"
    elif dach and p.get("decken") and any(abs(z - top) < 0.01 for z in p["decken"]):
        hk, dk = T["dachhaus_hoehe"], 0.2
        za, zb = top, top + hk
        if p["achse"] == "v":
            _wand_mit_tueren(b, "u", v0 - dk, u0 - dk, u1 + dk, dk, za, zb, [(u0 + 0.2, u0 + 0.2 + T["tuer_breite"], T["tuer_hoehe"])], S["Fassade"])
            _box(b, u0 - dk, v1, u1 + dk, v1 + dk, za, zb, S["Fassade"])
            _box(b, u0 - dk, v0, u0, v1, za, zb, S["Fassade"])
            _box(b, u1, v0, u1 + dk, v1, za, zb, S["Fassade"])
            _box(b, u0 - dk - 0.05, v0 - dk - 0.05, u1 + dk + 0.05, v1 + dk + 0.05, zb, zb + 0.2, S["InnenDecke"], top=S["Dach"])
        else:
            _wand_mit_tueren(b, "v", u1, v0 - dk, v1 + dk, dk, za, zb, [(v0 + 0.2, v0 + 0.2 + T["tuer_breite"], T["tuer_hoehe"])], S["Fassade"])
            _box(b, u0 - dk, v0 - dk, u0, v1 + dk, za, zb, S["Fassade"])
            _box(b, u0, v0 - dk, u1, v0, za, zb, S["Fassade"])
            _box(b, u0, v1, u1, v1 + dk, za, zb, S["Fassade"])
            _box(b, u0 - dk - 0.05, v0 - dk - 0.05, u1 + dk + 0.05, v1 + dk + 0.05, zb, zb + 0.2, S["InnenDecke"], top=S["Dach"])
        p["dachhaus"] = True


def leiter_und_luke(b, p, z_boden, top):
    """Steigleiter vom obersten Geschoss durch die Dachluke, Aufkantung (0,3 m) und aufgeklappter Deckel auf dem Dach."""
    T = C["luke"]
    lu0, lv0, lu1, lv1 = _luke(p)
    za, zb = z_boden, top + T["holm_ueber_dach"]
    sprossen = [z_boden + k * T["sprosse_abstand"] for k in range(1, int((top - z_boden) / T["sprosse_abstand"]) + 1)]
    if p["achse"] == "v":  # Leiter an der Wand u = u0, Sprossen quer (v-Richtung)
        uu = p["u0"] + 0.15
        for vv in (lv0 + 0.15, lv1 - 0.15):
            _box(b, uu - 0.025, vv - 0.025, uu + 0.025, vv + 0.025, za, zb, S["Metall"])
        for z in sprossen:
            _box(b, uu - 0.015, lv0 + 0.15, uu + 0.015, lv1 - 0.15, z - 0.015, z + 0.015, S["Metall"])
        for vv in (lv0 + 0.15, lv1 - 0.15):  # Wandhalter
            _box(b, p["u0"], vv - 0.02, uu, vv + 0.02, za + 1.0, za + 1.04, S["Metall"])
    else:  # Leiter an der Wand v = v0
        vv = p["v0"] + 0.15
        for uu in (lu0 + 0.15, lu1 - 0.15):
            _box(b, uu - 0.025, vv - 0.025, uu + 0.025, vv + 0.025, za, zb, S["Metall"])
        for z in sprossen:
            _box(b, lu0 + 0.15, vv - 0.015, lu1 - 0.15, vv + 0.015, z - 0.015, z + 0.015, S["Metall"])
        for uu in (lu0 + 0.15, lu1 - 0.15):
            _box(b, uu - 0.02, p["v0"], uu + 0.02, vv, za + 1.0, za + 1.04, S["Metall"])
    k, h = 0.1, T["aufkantung"]  # Aufkantung
    for (a, c, d_, e_) in ((lu0 - k, lv0 - k, lu1 + k, lv0), (lu0 - k, lv1, lu1 + k, lv1 + k),
                           (lu0 - k, lv0, lu0, lv1), (lu1, lv0, lu1 + k, lv1)):
        _box(b, a, c, d_, e_, top, top + h, S["Metall"])
    # Deckel aufgeklappt (steht an der Scharnierseite fast senkrecht)
    if p["achse"] == "v":
        _box(b, lu1 + k, lv0 - 0.02, lu1 + k + 0.05, lv1 + 0.02, top + h, top + h + (lu1 - lu0) + 0.1, S["Metall"])
    else:
        _box(b, lu0 - 0.02, lv1 + k, lu1 + 0.02, lv1 + k + 0.05, top + h, top + h + (lv1 - lv0) + 0.1, S["Metall"])
    p["dachhaus"] = "luke"


# ------------------------------------------------------------------ Ablauf
def main():
    t0 = time.time()
    cfg, geb = gebaeude_liste()
    masten = G2._mastpunkte()
    zaehler, ergebnis = {}, []
    for g in geb:
        name = objektname(cfg, g, zaehler)
        if NUR and g["id"] not in NUR:
            continue
        ob = bpy.data.objects.get(name)
        if ob is None:
            print("FEHLT", g["id"], name, flush=True)
            continue
        if "--pruefen-zufall" in args:  # Umbau darf den Zufall des Generators nicht verschieben
            b1, _ = erzeugen(cfg, g, None, masten)
            b2, _ = erzeugen(cfg, g, plan_erstellen, masten)
            z1, z2 = b1.rnd.random(), b2.rnd.random()
            ergebnis.append((g["id"], name, z1 == z2))
            for bb in (b1, b2):
                bb.bm.free()
                bb.deko.free()
            continue
        b, orig = erzeugen(cfg, g, None if PRUEFEN else plan_erstellen, masten)
        if PRUEFEN:
            V.uv_welt(b.bm)
            alt, neu = fingerabdruck(ob.data) + uv_abdruck(ob.data), fingerabdruck(b.bm) + uv_abdruck(b.bm)
            ergebnis.append((g["id"], name, alt == neu, alt, neu))
            b.bm.free()
            b.deko.free()
            continue
        me = bpy.data.meshes.new(ob.data.name + "_i")
        V.uv_welt(b.bm)  # wie V.objekt_aus_bmesh in gebaeude2.bauen (Box-UV in Metern) - sonst keine Texturen
        b.bm.normal_update()
        b.bm.to_mesh(me)
        b.bm.free()
        b.deko.free()
        for m in ob.data.materials:
            me.materials.append(m)
        if (b.plan or {}).get("ausbau"):  # Zusatz-Slots (Innenmaterialien) + Tausch der Innen-Slots
            for mn in IA.extra_materialien(C):
                me.materials.append(V.material(mn))
            for sl, mn in C["innenausbau"].get("slot_tausch", {}).items():
                me.materials[S[sl]] = V.material(mn)
        alt = ob.data
        ob.data = me
        if alt.users == 0:
            bpy.data.meshes.remove(alt)
        p = b.plan or {}
        n_t = tueren_bauen(b, g["id"], name, orig, ob)
        if getattr(b, "raeume", None):
            ob["raeume_json"] = json.dumps(b.raeume)  # Raumgrenzen (lokal u, v) fuer Vorschau/Spiel
        if b.moebel:
            p["moebel_gesetzt"] = IA.moebel_setzen(V, VB, g["id"], b, b.moebel, "12_Innenraum/Moebel")
        ebenen = p.get("ebenen") or list((b.info or {}).get("geschosse", []))
        if ebenen:
            ob["ebenen_z"] = [round(z, 3) for z in ebenen]  # Weltkoordinaten (Mesh ist bei orig verankert, z identisch)
        ergebnis.append((g["id"], name, bool(b.plan), b.log, p.get("achse"), p.get("moebel_weg"), p.get("dachhaus", False), "tueren", n_t,
                         "stufen", p.get("stufen_neu"), "durchgang", p.get("durchgang_weg"), "ausbau", p.get("ausbau"),
                         "moebel", p.get("moebel_gesetzt")))
    for e in ergebnis:
        print("GEB", *e, flush=True)
    if PRUEFEN or "--pruefen-zufall" in args:
        ok = sum(1 for e in ergebnis if e[2])
        print("PRUEFUNG", ok, "von", len(ergebnis), "identisch", round(time.time() - t0, 1), "s", flush=True)
        return
    V.pfade_relativ()
    pfad = os.path.join(V.ROOT, f"viertel_v{version}.blend")
    if "--ohne-speichern" not in args:
        bpy.ops.wm.save_as_mainfile(filepath=pfad, compress=True, relative_remap=True)
        print("GESPEICHERT", pfad, round(os.path.getsize(pfad) / 1e6, 1), "MB", flush=True)


if __name__ == "__main__":
    main()
