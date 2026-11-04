"""Phase 3 – Fahrzeug-Karosserie (Baukasten, Teil 1).

Prinzip:
- Die Aussenhaut entsteht als "Loft": Querschnitts-Ringe entlang der Fahrzeuglaenge (Stationen d).
- Jeder Ring wird aus den Profilen in fahrzeuge.json berechnet:
  Dachlinie, Unterkante, Guertellinie, Grundriss-Breite, Radlaeufe, Flanken-Woelbung, Dachwoelbung.
- Jede Flaeche bekommt (Station, Ring-Abschnitt, Seite).
  Regeln ordnen sie einem Bauteil zu: Tuer, Haube, Kotfluegel, Karosserie, Scheibe ...
- Spaltmasse (5 mm): Zwischen zwei verschiedenen Bauteilen liegt ein schmaler Streifen, der entfernt wird.
- Scheiben werden eigene Objekte: 5 mm dick, leicht nach innen versetzt.

Koordinaten: x nach vorne (Front bei +L/2), y nach links, z nach oben, Boden z = 0.
"""
import math

import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

M = {"mitte_u": 0, "boden_e": 2, "radhaus_e": 4, "schweller": 6, "sw0": 7, "sw1": 8, "bl0": 10, "bl1": 11,
     "guertel": 15, "glas0": 16, "glas1": 20, "sch0": 21, "sch1": 22, "saeule0": 25, "saeule1": 26, "mitte": 30}
HALB = 30                       # Punkte je Ringhaelfte (0 = unten Mitte ... 30 = oben Mitte)
SPALT_PAARE = {M["sw0"], M["bl0"], M["sch0"], M["saeule0"]}


# ---------------------------------------------------------------- Interpolation
def pchip(pts):
    """Monotone kubische Interpolation (Fritsch-Carlson): keine Ueberschwinger zwischen den Stuetzpunkten."""
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    n = len(xs)
    if n == 1:
        return lambda x: ys[0]
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    dl = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = dl[0], dl[-1]
    for i in range(1, n - 1):
        if dl[i - 1] * dl[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        lo, hi = 0, n - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= x:
                lo = mid
            else:
                hi = mid
        t = (x - xs[lo]) / h[lo]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[lo] + (t3 - 2 * t2 + t) * h[lo] * m[lo]
                + (-2 * t3 + 3 * t2) * ys[lo + 1] + (t3 - t2) * h[lo] * m[lo + 1])
    return f


def _glatt(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _mono(werte, lo, hi, eps=0.0015):
    """Zielhoehen -> streng steigend und innerhalb (lo, hi). Zu enge Bereiche werden gestaucht."""
    n = len(werte)
    out, prev = [], lo
    for i, v in enumerate(werte):
        v = min(max(v, prev + eps), hi - (n - i) * eps)
        if v <= prev:
            v = prev + eps * 0.5
        out.append(v)
        prev = v
    return out


def reifen_radius(r):
    felge_zoll, breite_mm, quer = r
    return (felge_zoll * 25.4 / 2 + breite_mm * quer / 100.0) / 1000.0


# ---------------------------------------------------------------- Profil
class Profil:
    def __init__(self, T, spalt=0.005):
        self.T = T
        self.g = spalt
        self.L, self.B = T["L"], T["B"]
        self.top = pchip(T["dach"])
        self.bot = pchip(T["unten"])
        self.belt = pchip(T["guertel"])
        self.wid = pchip(T["breite"])
        self.R = reifen_radius(T["reifen"])
        self.Ra = self.R + T.get("radlauf_plus", 0.04)
        self.bw = T["reifen"][1] / 1000.0
        self.achsen = [T["ueberhang_v"], T["ueberhang_v"] + T["radstand"]] + list(T.get("achsen_extra", []))
        self.zwilling = bool(T.get("zwilling_hinten"))
        self.bw_radhaus = 2 * self.bw + 0.03 if self.zwilling else self.bw
        self.dachbreite = T["dachbreite"]
        cr, rr = T["woelbung"], T["dachradius"]
        self.gh_max = max(self.top(d) - cr - rr - self.belt(d) for d in [i * self.L / 200 for i in range(201)])
        self.ende = T.get("kabine_ende", self.L)       # Pickup: Kabine endet vor der Pritsche

    def x(self, d):
        return self.L / 2 - d

    def hw(self, d):
        return self.B / 2 * self.wid(d)

    def radlauf(self, d):
        """Oberkante der Radlauf-Oeffnung an Station d (None = kein Radlauf)."""
        best = None
        for a in self.achsen:
            dx = abs(d - a)
            if dx < self.Ra:
                z = self.R + math.sqrt(self.Ra ** 2 - dx ** 2)
                best = z if best is None else max(best, z)
        if best is not None:
            best = min(best, self.belt(d) - 0.07)
        return best

    def ring(self, d):
        """Halber Querschnitt (y >= 0) als Liste von 31 Punkten (y, z), Index siehe M."""
        T, g = self.T, self.g
        zt, zb, hw = self.top(d), self.bot(d), self.hw(d)
        cr, rr = T["woelbung"], T["dachradius"]
        zte = zt - cr
        zgt = zte - rr
        zbl_line = self.belt(d)
        zg = min(zbl_line, zgt - 0.012)
        f = (zgt - zbl_line) / max(self.gh_max, 0.1)
        hw_top = hw * 0.95 + (min(self.dachbreite, hw * 0.95) - hw * 0.95) * _glatt(f * 1.15)
        fu, fb, fs, bs = T["flanke"]

        def yside(z):
            s = max(0.0, min(1.0, (z - zb) / max(zg - zb, 0.05)))
            if s < bs:
                v = fu + (fb - fu) * _glatt(s / bs)
            else:
                v = fb + (fs - fb) * _glatt((s - bs) / (1 - bs))
            return hw * v

        za = self.radlauf(d)
        y_in = max(hw - (self.bw_radhaus + 0.085), 0.12)
        P = [(0.0, zb), (y_in * 0.5, zb), (y_in, zb)]
        if za is not None and za > zb + 0.01:
            zA = zR = za
        else:
            zA, zR = zb + 0.004, zb + 0.006
        P.append((y_in, zA))
        P.append((hw - 0.04, zR))
        zc = zR + 0.012
        P.append((yside(zc) - 0.012, zc))
        zs = zR + 0.035
        P.append((yside(zs), zs))
        zsill, zbl = T["schweller_z"], T["stossf_linie"]
        ziele = [zsill - g / 2, zsill + g / 2, (zsill + zbl) / 2, zbl - g / 2, zbl + g / 2]
        ziele += [zbl + (zg - zbl) * k / 4 for k in (1, 2, 3)]
        for z in _mono(ziele, zs, zg):
            P.append((yside(z), z))
        P.append((yside(zg), zg))
        yg0 = yside(zg)
        gh = [zg + 0.015] + [zg + 0.015 + (zgt - 0.04 - zg) * k / 4 for k in (1, 2, 3)] + [zgt - 0.025]
        hgh = max(zgt - zg, 1e-4)
        for z in _mono(gh, zg, zgt):
            t = (z - zg) / hgh
            P.append((yg0 + (hw_top - yg0) * t + 0.012 * math.sin(math.pi * t) * min(1.0, hgh / 0.3), z))
        P.append((hw_top, zgt))
        for a in (math.degrees(g / rr), 50.0, 90.0):
            w = math.radians(a)
            P.append((hw_top - rr + rr * math.cos(w), zgt + rr * math.sin(w)))
        y0 = max(hw_top - rr, 0.08)

        def ztop(y):
            return zte + cr * (1 - (y / y0) ** 2)
        for yy in (y0 - 0.055, y0 - 0.055 - g, y0 * 0.62, y0 * 0.38, y0 * 0.16):
            P.append((yy, ztop(yy)))
        P.append((0.0, zt))
        assert len(P) == HALB + 1, len(P)
        return P

    def stationen(self, schnitte, kanten, ende=None):
        ende = self.ende if ende is None else ende
        g = self.g
        n = max(8, int(ende / 0.035))
        ds = [i * ende / n for i in range(n + 1)]
        gaps = []
        for c in schnitte:
            if 0.01 < c < ende - 0.01:
                ds += [c - g / 2, c + g / 2]
                gaps.append((c - g / 2, c + g / 2))
        ds += [k for k in kanten if 0.005 < k < ende - 0.005]
        for a in self.achsen:
            for s in (-1, 1):
                for e in (-0.0015, 0.0015):
                    v = a + s * self.Ra + e
                    if 0 < v < ende:
                        ds.append(v)
            for k in range(-12, 13):  # feiner im Radlauf
                v = a + k * self.Ra / 12.5
                if 0 < v < ende:
                    ds.append(v)
        ds = sorted(set(round(v, 5) for v in ds))
        sauber = [ds[0]]
        for v in ds[1:]:
            if v - sauber[-1] > 0.0009:
                sauber.append(v)
        ds = sauber
        # adaptiv verfeinern, wo sich die Form schnell aendert (z. B. steile Heckflaechen)
        for _ in range(4):
            neu = [ds[0]]
            for a, b in zip(ds, ds[1:]):
                if b - a > 0.008 and (abs(self.top(a) - self.top(b)) > 0.035 or abs(self.hw(a) - self.hw(b)) > 0.02
                                      or abs(self.bot(a) - self.bot(b)) > 0.03):
                    if not any(abs(a - g0) < 1e-6 and abs(b - g1) < 1e-6 for g0, g1 in gaps):
                        neu.append((a + b) / 2)
                neu.append(b)
            if len(neu) == len(ds):
                break
            ds = neu
        gap_i = set()
        for i, (a, b) in enumerate(zip(ds, ds[1:])):
            for g0, g1 in gaps:
                if abs(a - g0) < 2e-5 and abs(b - g1) < 2e-5:
                    gap_i.add(i)
        return ds, gap_i


# ---------------------------------------------------------------- Regeln (Flaeche -> Bauteil)
def tuer_seiten(t):
    if len(t) > 3 and t[3] in ("l", "r"):
        return [t[3]]
    if len(t) > 2 and t[2] in ("l", "r"):
        return [t[2]]
    return ["l", "r"]


def tuer_name(k, s):
    return f"Tuer_{'v' if k == 0 else 'h'}{s}"


def regeln(T, L):
    R = []

    def r(name, d0, d1, t0, t1, seite=None):
        R.append((name, d0, d1, M[t0], M[t1], seite))
    fs = T["frontscheibe"]
    r("GLAS_Frontscheibe", fs[0] + 0.025, fs[1] - 0.02, "saeule1", "mitte")
    if T["heck"] == "stufe":
        hs = T["heckscheibe"]
        r("GLAS_Heckscheibe", hs[0] + 0.02, hs[1] - 0.025, "saeule1", "mitte")
    if T["heck"] == "klappe":
        hf = T["heckfenster"]
        r("GLAS_Heckfenster", hf[0], hf[1], "saeule1", "mitte")
    for k, (t, fe) in enumerate(zip(T["tueren"], T["fenster"])):
        if fe:
            for s in tuer_seiten(t):
                r(f"GLAS_{tuer_name(k, s)}", fe[0], fe[1], "glas0", "glas1", s)
    for k, fe in enumerate(T.get("fenster_fest", [])):
        for s in (fe[2:3] or ("l", "r")):
            r(f"GLAS_Fest{k}{s}", fe[0], fe[1], "glas0", "glas1", s)
    r("Boden", 0, L, "mitte_u", "boden_e")
    r("Radhaus", 0, L, "boden_e", "radhaus_e")
    h = T["haube"]
    r("Front", 0, T["front_seite"], "radhaus_e", "bl0")
    r("Front", 0, h[0], "radhaus_e", "mitte")
    r("Haube", h[0], h[1], "sch1", "mitte")
    r("Windlauf", h[1], fs[0], "saeule1", "mitte")
    for k, t in enumerate(T["tueren"]):
        for s in tuer_seiten(t):
            r(tuer_name(k, s), t[0], t[1], "sw1", "sch0", s)
    if T["heck"] == "stufe":
        kr = T["kofferraum"]
        r("Kofferraum", kr[0], kr[1], "sch1", "mitte")
    if T["heck"] == "klappe":
        r("Heckklappe", T["heckklappe"], L + 1, "saeule1", "mitte")
    r("Heck", T["heck_seite"], L + 1, "radhaus_e", "bl0")
    for s in ("l", "r"):
        r(f"Kotfluegel_{s}", 0, T["tueren"][0][0], "radhaus_e", "sch0", s)
    r("Karosserie", 0, L + 1, "radhaus_e", "mitte")
    return R


def schnitte_kanten(T):
    h, fs = T["haube"], T["frontscheibe"]
    sch = [h[0], h[1], fs[0], T["front_seite"], T["heck_seite"]]
    kan = [fs[0] + 0.025, fs[1] - 0.02, T["dach_hinten"]]
    for t in T["tueren"]:
        sch += [t[0], t[1]]
    for fe in T["fenster"]:
        if fe:
            kan += list(fe)
    for fe in T.get("fenster_fest", []):
        kan += list(fe[:2])
    if T["heck"] == "stufe":
        sch += list(T["kofferraum"])
        kan += [T["heckscheibe"][0] + 0.02, T["heckscheibe"][1] - 0.025]
    if T["heck"] == "klappe":
        sch += [T["heckklappe"]]
        kan += list(T["heckfenster"])
    return sch, kan


# ---------------------------------------------------------------- Loft
class Loft:
    """Aussenhaut als bmesh + Zuordnung jeder Flaeche zu einem Bauteil."""

    def __init__(self, P):
        self.P = P
        T = P.T
        sch, kan = schnitte_kanten(T)
        self.ds, self.gap_i = P.stationen(sch, kan)
        self.ringe = [P.ring(d) for d in self.ds]
        self.bm = bmesh.new()
        self.V = []
        N = 2 * HALB
        for d, ring in zip(self.ds, self.ringe):
            x = P.x(d)
            reihe = []
            for k in range(N):
                if k <= HALB:
                    y, z = ring[k]
                else:
                    y, z = ring[N - k]
                    y = -y
                reihe.append(self.bm.verts.new((x, y, z)))
            self.V.append(reihe)
        self.info = {}     # face -> (i, j, seite, dmid, zmid)
        for i in range(len(self.ds) - 1):
            dmid = (self.ds[i] + self.ds[i + 1]) / 2
            for k in range(N):
                k1 = (k + 1) % N
                f = self.bm.faces.new((self.V[i][k], self.V[i][k1], self.V[i + 1][k1], self.V[i + 1][k]))
                if k < HALB:
                    j, s = k, "l"
                else:
                    j, s = N - k - 1, "r"
                zmid = (self.ringe[i][j][1] + self.ringe[i][j + 1][1]) / 2
                self.info[f] = (i, j, s, dmid, zmid)
        self.kappen = {}
        self._kappe(0, "v")
        if P.ende >= P.L - 1e-6 or T["heck"] == "pritsche":
            self._kappe(len(self.ds) - 1, "h")
        self.bm.normal_update()
        # Ausrichtung pruefen: eine Seitenflaeche links muss nach +y zeigen
        probe = next(f for f, v in self.info.items() if v[1] == M["bl1"] + 1 and v[2] == "l")
        if probe.normal.y < 0:
            bmesh.ops.reverse_faces(self.bm, faces=list(self.bm.faces))
            self.bm.normal_update()
        for f, inf in self.info.items():  # Kappen: vorne nach +x, hinten nach -x
            if inf[0] == "kappe" and f.normal.x * (1 if inf[1] == "v" else -1) < 0:
                f.normal_flip()
        self.bm.normal_update()
        self.bm.verts.ensure_lookup_table()
        self.bvh = BVHTree.FromBMesh(self.bm)

    def _kappe(self, i, art):
        """Front-/Heckflaeche: waagerechte Streifen zwischen gespiegelten Ringpunkten, mit Randspalten."""
        N, g = 2 * HALB, self.P.g
        ring = self.ringe[i]
        reihen = []
        for k in range(M["boden_e"], HALB + 1):
            L_, R_ = self.V[i][k], self.V[i][(N - k) % N]
            a = ring[k][0]
            if k == HALB or a < 4 * g:
                reihen.append([R_, L_] if k < HALB else [L_])
                continue
            x, z = L_.co.x, L_.co.z
            hb = self.P.T.get("hecktuer_b", 0.0)
            if art == "h" and self.P.T["heck"] == "bus" and a > hb + 4 * g:
                ys = [-(a - g), -(hb + g), -hb, hb, hb + g, a - g]
            else:
                ys = [-(a - g), -g / 2, g / 2, a - g]
            mitte = [self.bm.verts.new((x, y, z)) for y in ys]
            reihen.append([R_] + mitte + [L_])
        for k in range(len(reihen) - 1):
            u, o = reihen[k], reihen[k + 1]
            zmid = (u[0].co.z + o[0].co.z) / 2
            if len(o) == 1:
                f = self.bm.faces.new((u[0], u[-1], o[0]))
                self.info[f] = ("kappe", art, "haupt", zmid, 0)
                continue
            if len(u) == len(o) and len(u) in (6, 8):
                spalten = (["rand_r", "haupt_r", "mitte", "haupt_l", "rand_l"] if len(u) == 6 else
                           ["rand_r", "haupt_r", "spalt_r", "tuer", "spalt_l", "haupt_l", "rand_l"])
                for c in range(len(spalten)):
                    f = self.bm.faces.new((u[c], u[c + 1], o[c + 1], o[c]))
                    self.info[f] = ("kappe", art, spalten[c], zmid, k)
            else:
                f = self.bm.faces.new((u[0], u[-1], o[-1], o[0]))
                self.info[f] = ("kappe", art, "haupt", zmid, k)

    # -------------------------------------------------------- Zuordnung
    def zuordnen(self):
        P, T = self.P, self.P.T
        R = regeln(T, P.L)
        klasse = {}
        raster = {}
        for f, inf in self.info.items():
            if inf[0] == "kappe":
                continue
            i, j, s, dmid, zmid = inf
            raster[(i, j, s)] = f
            if j in SPALT_PAARE and i in self.gap_i:
                klasse[f] = "SPALT"
            elif j in SPALT_PAARE:
                klasse[f] = "?T"
            elif i in self.gap_i:
                klasse[f] = "?D"
            else:
                klasse[f] = next((n for n, d0, d1, t0, t1, se in R
                                  if d0 <= dmid < d1 and t0 <= j < t1 and (se is None or se == s)), "Karosserie")

        def fest(n):
            return n is not None and not n.startswith("?") and n != "SPALT"

        def aufloesen(a, b):
            if a == b:
                return a
            if a.startswith("GLAS"):
                return b
            if b.startswith("GLAS"):
                return a
            return "SPALT"
        for f, n in list(klasse.items()):
            if n in ("?T", "?D"):
                i, j, s = self.info[f][:3]
                if n == "?T":
                    na, nb = raster.get((i, j - 1, s)), raster.get((i, j + 1, s))
                else:
                    na, nb = raster.get((i - 1, j, s)), raster.get((i + 1, j, s))
                ka = klasse.get(na) if na else None
                kb = klasse.get(nb) if nb else None
                if fest(ka) and fest(kb):
                    klasse[f] = aufloesen(ka, kb)
                else:
                    klasse[f] = ka if fest(ka) else (kb if fest(kb) else "SPALT")
        # Kappen
        bl = T["stossf_linie"]
        for f, inf in self.info.items():
            if inf[0] != "kappe":
                continue
            _, art, spalte, zmid, k = inf
            if art == "v":
                n = "Front"
            elif T["heck"] == "pritsche":
                n = "Karosserie"
            elif zmid < bl - 0.0025:
                n = "Heck"
            elif abs(zmid - bl) <= 0.0026:
                if T["heck"] == "bus":
                    n = "SPALT" if spalte in ("tuer", "spalt_r", "spalt_l") else "Karosserie"
                else:
                    n = "SPALT" if T["heck"] in ("klappe", "kasten") else "Karosserie"
            elif T["heck"] == "stufe":
                n = "Karosserie"
            elif T["heck"] == "bus":
                ring_i = k + M["boden_e"]
                if ring_i >= M["sch1"]:
                    n = "Karosserie"
                elif spalte == "tuer":
                    n = "SPALT" if ring_i == M["sch0"] else "Hecktuer_m"
                elif spalte.startswith("spalt"):
                    n = "SPALT"
                else:
                    n = "Karosserie"
            elif T["heck"] == "klappe":
                n = "SPALT" if spalte.startswith("rand") else "Heckklappe"
            else:  # kasten: zwei Hecktueren
                if spalte.startswith("rand") or spalte == "mitte":
                    n = "SPALT"
                else:
                    n = "Hecktuer_l" if spalte.endswith("l") else "Hecktuer_r"
            klasse[f] = n
        self.klasse = klasse
        return klasse

    # -------------------------------------------------------- Material-Slot je Flaeche
    def slot(self, f, teil):
        T, P = self.P.T, self.P
        inf = self.info[f]
        if teil == "Boden":
            return "unterboden"
        if teil in ("Radhaus", "Windlauf"):
            return "schwarz"
        if teil in ("Front", "Heck"):
            if T["stossf"] == "schwarz":
                return "schwarz"
            if inf[0] != "kappe" and T.get("verkleidung") and inf[4] < P.bot(inf[3]) + 0.13:
                return "verkleidung"
            return "lack"
        if inf[0] == "kappe":
            return "lack"
        i, j, s, dmid, zmid = inf
        gh_hoehe = P.top(dmid) - T["woelbung"] - T["dachradius"] - P.belt(dmid)
        if M["guertel"] <= j < M["sch0"] and gh_hoehe > 0.12:
            if teil.startswith("Tuer"):
                return "rahmen" if T["rahmen"] != "lack" else "lack"
            for fe in T.get("fenster_fest", []):
                if fe[0] - 0.03 <= dmid <= fe[1] + 0.03:
                    return "rahmen" if T["rahmen"] != "lack" else "lack"
            if j == M["guertel"]:
                return "rahmen" if T["rahmen"] != "lack" else "lack"
        if T.get("verkleidung") and M["radhaus_e"] <= j < M["sw1"]:
            return "verkleidung"
        return "lack"

    def strahl(self, start, richtung, weit=6.0):
        hit = self.bvh.ray_cast(Vector(start), Vector(richtung).normalized(), weit)
        if hit[0] is None:
            return None
        return hit[0], hit[1]


# ---------------------------------------------------------------- Bauteile als bmesh
def teil_bmesh(loft, flaechen, versatz=(0, 0, 0), slot_namen=None):
    """Kopiert die Flaechen eines Bauteils in ein neues bmesh (mit Material-Index nach Slot)."""
    bm = bmesh.new()
    zl = bm.verts.layers.float.new("fz_z")
    karte = {}
    ox, oy, oz = versatz
    slots = slot_namen if slot_namen is not None else []
    for f, slot in flaechen:
        vs = []
        for v in f.verts:
            nv = karte.get(v)
            if nv is None:
                nv = bm.verts.new((v.co.x - ox, v.co.y - oy, v.co.z - oz))
                nv[zl] = v.co.z
                karte[v] = nv
            vs.append(nv)
        try:
            nf = bm.faces.new(vs)
        except ValueError:
            continue
        if slot not in slots:
            slots.append(slot)
        nf.material_index = slots.index(slot)
        nf.smooth = True
    bm.normal_update()
    for e in bm.edges:  # harte Kanten (Kappe/Seite, Radlauf-Kante) nicht glaetten
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(55):
            e.smooth = False
    return bm, slots


def glas_bmesh(loft, flaechen, versatz=(0, 0, 0), einzug=0.007):
    bm, _ = teil_bmesh(loft, [(f, "glas") for f in flaechen], versatz)
    bm.normal_update()
    for v in bm.verts:
        v.co -= v.normal * einzug
    return bm
