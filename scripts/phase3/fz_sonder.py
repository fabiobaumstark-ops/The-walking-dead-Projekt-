"""Phase 3.1.10 – Sattelauflieger (16,15 m Kofferaufbau) fuer den eingeknickten Sattelzug, plus Ladung.

Masse: recherche/fahrzeuge.md (53-ft-Auflieger: 16,15 x 2,59 x 4,11 m).
Lokale Koordinaten: x nach vorne (Koenigszapfen vorne), Boden z = 0, Aufbau-Unterkante 1,22 m.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, HIER)
import viertel_lib as V  # noqa: E402
import fz_material as FM  # noqa: E402
import fz_teile as FT  # noqa: E402

L, B, H, Z0 = 16.15, 2.59, 4.11, 1.22


def auflieger(col, cid, rnd, mats, rad_me, reifen_r, riss=True):
    root = bpy.data.objects.new(cid, None)
    col.objects.link(root)
    root["typ"] = "Auflieger"
    haut = V.material("MAT_Lack_Weiss")
    # Kofferaufbau: Waende als Flaechen mit Dicke, Rueckseite offen (Tueren), Dach mit Riss
    bm = bmesh.new()
    x0, x1 = -L / 2, L / 2
    h = H - Z0
    segs = 32
    riss_x = (x0 + 5.0, x0 + 9.5)
    for k in range(segs):
        a, b_ = x0 + L * k / segs, x0 + L * (k + 1) / segs
        for s in (1, -1):  # Seitenwaende
            if riss and s < 0 and riss_x[0] < a < riss_x[1]:
                # aufgerissene Seite (liegt spaeter oben): nur ausgefranste Reste oben/unten
                zt = Z0 + h * (0.12 + 0.1 * rnd.random())
                FT.quader(bm, ((a + b_) / 2, s * (B / 2 - 0.01), Z0 + (zt - Z0) / 2), (b_ - a, 0.02, zt - Z0), 0)
                zb = H - h * (0.10 + 0.12 * rnd.random())
                FT.quader(bm, ((a + b_) / 2, s * (B / 2 - 0.01), (zb + H) / 2), (b_ - a, 0.02, H - zb), 0)
                continue
            FT.quader(bm, ((a + b_) / 2, s * (B / 2 - 0.01), Z0 + h / 2), (b_ - a + 0.002, 0.02, h), 0)
        FT.quader(bm, ((a + b_) / 2, 0, H - 0.01), (b_ - a + 0.002, B, 0.02), 0)  # Dach
    FT.quader(bm, (x1 - 0.01, 0, Z0 + h / 2), (0.02, B, h), 0)  # Stirnwand
    # Pfosten aussen (alle 1,2 m), Ober-/Untergurt
    for k in range(14):
        x = x0 + 0.6 + k * 1.15
        for s in (1, -1):
            if riss and s < 0 and riss_x[0] < x < riss_x[1]:
                continue
            FT.quader(bm, (x, s * (B / 2 + 0.004), Z0 + h / 2), (0.05, 0.012, h - 0.02), 1)
    for s in (1, -1):
        for z in (Z0 + 0.06, H - 0.05):
            FT.quader(bm, (0, s * (B / 2 + 0.01), z), (L, 0.025, 0.11), 1)
    # Boden + Unterbau, Unterfahrschutz hinten
    FT.quader(bm, (0, 0, Z0 - 0.03), (L, B, 0.08), 2)
    for s in (1, -1):
        FT.quader(bm, (0, s * 0.48, Z0 - 0.20), (L - 0.4, 0.10, 0.28), 2)
    FT.quader(bm, (x0 + 0.25, 0, 0.62), (0.10, B - 0.25, 0.10), 2)
    for s in (1, -1):
        FT.quader(bm, (x0 + 0.25, s * 0.9, 0.9), (0.10, 0.08, 0.6), 2)
    # Rueckrahmen
    for s in (1, -1):
        FT.quader(bm, (x0 + 0.05, s * (B / 2 - 0.06), Z0 + h / 2), (0.1, 0.12, h), 1)
    FT.quader(bm, (x0 + 0.05, 0, H - 0.08), (0.1, B, 0.16), 1)
    ob = FT.objekt(f"{cid}_Koffer", bm, col, [haut, mats["chrom"], mats["unterboden"]], root)
    ob["lack_alter"] = 0.9
    # Hecktueren (offen, an den Seiten angeschlagen)
    for s, w in ((1, 95), (-1, 160)):
        bmt = bmesh.new()
        FT.quader(bmt, Vector((0.0, -s * (B / 4 - 0.02), 0)), (0.03, B / 2 - 0.05, h - 0.2), 0)
        for z in (-0.9, 0.0, 0.9):
            FT.quader(bmt, Vector((-0.03, -s * (B / 4), z)), (0.03, 0.05, 0.6), 1)
        t = FT.objekt(f"{cid}_Hecktuer_{'l' if s > 0 else 'r'}", bmt, col, [haut, mats["chrom"]], root,
                      loc=(x0 - 0.02, s * (B / 2 - 0.02), Z0 + h / 2))
        t.rotation_euler = (0, 0, math.radians(w) * s)
    # Stuetzbeine vorne, Koenigszapfen-Platte
    bm = bmesh.new()
    for s in (1, -1):
        FT.quader(bm, (x1 - 3.4, s * 0.75, (Z0 - 0.1) / 2 + 0.05), (0.12, 0.12, Z0 - 0.1), 0)
        FT.quader(bm, (x1 - 3.4, s * 0.75, 0.04), (0.30, 0.25, 0.04), 0)
    FT.quader(bm, (x1 - 3.4, 0, 0.55), (0.06, 1.5, 0.08), 0)
    FT.quader(bm, (x1 - 0.9, 0, Z0 - 0.08), (1.2, 1.4, 0.05), 0)
    FT.objekt(f"{cid}_Stuetzbeine", bm, col, [mats["unterboden"]], root)
    # Tandemachse mit Zwillingsreifen
    for ax in (x0 + 2.2, x0 + 3.45):
        for s in (1, -1):
            for zus, dy in (("", 0.0), ("i", 0.32)):
                r = bpy.data.objects.new(f"{cid}_Rad_{'a' if ax < x0 + 3 else 'b'}{'l' if s > 0 else 'r'}{zus}", rad_me)
                r.location = (ax, s * (B / 2 - 0.16 - dy), reifen_r)
                r.rotation_euler = (0, 0, 0 if s > 0 else math.pi)
                r.parent = root
                r["reifen_r"] = reifen_r
                r["lack_alter"] = 0.9
                col.objects.link(r)
    # Kotfluegel ueber den Achsen
    bm = bmesh.new()
    for s in (1, -1):
        FT.quader(bm, (x0 + 2.82, s * (B / 2 - 0.30), reifen_r * 2 + 0.08), (2.6, 0.62, 0.02), 0)
    FT.objekt(f"{cid}_Kotfluegel", bm, col, [mats["schwarz"]], root)
    for o in root.children:
        o["lack_alter"] = 0.9
        o["verw_korrektur"] = 0.0
    return root


def palette(bm, m_welt, mat=0):
    for k in range(5):
        y = -0.4 + 0.05 + k * 0.175
        FT.quader(bm, m_welt @ Vector((0, y, 0.13)), (1.2, 0.1, 0.022), mat, m_welt.to_3x3())
    for x in (-0.55, 0, 0.55):
        for y in (-0.35, 0, 0.35):
            FT.quader(bm, m_welt @ Vector((x, y, 0.07)), (0.1, 0.1, 0.1), mat, m_welt.to_3x3())
        FT.quader(bm, m_welt @ Vector((x, 0, 0.011)), (0.12, 0.8, 0.022), mat, m_welt.to_3x3())
