"""Phase 3 – Fahrzeug-Materialien (alle laufen durch MAT_Verwitterung, Masken aus Fototexturen).

Pro Objekt steuern Attribute (Objekt-Eigenschaften) das Alter:
- lack_alter 0..1: Ausbleichen, Klarlack-Schaeden, Rost
- verw_korrektur: wie bei allen Objekten (MAT_Verwitterung)
Pro Vertex: fz_z = Hoehe im Fahrzeug (fuer Rost unten), tint = Toenungsstreifen der Frontscheibe.
"""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import viertel_lib as V  # noqa: E402

_m, _n, _mr, _a, _l, _mix = V._math, V._noise, V._maprange, V._attr, V._link, V._mix_rgb


def _tex(nt, asset_mat, muster, nicht_farbe, skala):
    eintrag = next(a for a in V.manifest()["assets"] if a["name"] == asset_mat)
    pfad = V._karte(os.path.join(V.ROOT, eintrag["zielpfad"]), *muster)
    uv = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (skala, skala, 1)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = V._bild(pfad, nicht_farbe)
    nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    return t.outputs["Color"]


def _geo(nt):
    g = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(g.outputs["Normal"], sep.inputs[0])
    return g, sep.outputs["Z"]


def _ende(nt, b, farbe, rau, normal, lokal, kante):
    grp = V._verw_anschluss(nt, farbe, rau, normal, lokal=lokal, kante=kante)
    nt.links.new(grp.outputs["Farbe"], b.inputs["Base Color"])
    nt.links.new(grp.outputs["Rauheit"], b.inputs["Roughness"])
    nt.links.new(grp.outputs["Normale"], b.inputs["Normal"])
    return grp


def lack(name, hexf, metallic=0.0, matt=False):
    """Autolack nach ca. 12 Jahren: ausgeblichen (waagerecht staerker), Klarlack fleckig abgeloest, Rostflecken unten.
    matt=True: Tarnlack/Nutzfahrzeug ohne Klarlack (raue, kreidige Oberflaeche)."""
    mn = f"MAT_Autolack_{name}"
    if mn in bpy.data.materials:
        return bpy.data.materials[mn]
    m, nt, b = V._neues_mat(mn)
    geo, Nz = _geo(nt)
    P = geo.outputs["Position"]
    alter = _a(nt, "lack_alter", "OBJECT")
    hoch = _a(nt, "fz_z", "GEOMETRY")
    oben = _mr(nt, Nz, 0.3, 0.92)
    grunge = _tex(nt, "MAT_Blech_Rostflecken", ("_rough_",), True, 0.9)
    basis = V.hex_lin(hexf)
    # Ausbleichen: heller + entsaettigt, auf Dach/Haube/Kofferraum am staerksten
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Color"].default_value = basis
    hsv.inputs["Saturation"].default_value = 0.5
    hsv.inputs["Value"].default_value = 1.45 if sum(basis[:3]) < 0.6 else 1.12
    var = _mr(nt, _n(nt, P, 1.3, 3.0, 0.5), 0.3, 0.7, 0.7, 1.05)
    bleich = _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", alter, _m(nt, "ADD", 0.35, _m(nt, "MULTIPLY", oben, 0.65))), var, clamp=True)
    farbe = _mix(nt, bleich, basis, hsv.outputs["Color"])
    # Klarlack-Schaden: matte, kreidige Flecken (Fotomaske + Noise), fast nur oben
    wert = _m(nt, "ADD", _m(nt, "MULTIPLY", grunge, 0.45), _m(nt, "MULTIPLY", _n(nt, P, 2.2, 6.0, 0.65), 0.55))
    schwelle = _m(nt, "SUBTRACT", 0.8, _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", alter, oben), 0.33))
    kl = _mr(nt, _m(nt, "SUBTRACT", wert, schwelle), -0.02, 0.02)
    if matt:  # Tarnlack ohne Klarlack: keine kreidigen Klarlack-Flecken, nur leichte Fleckigkeit
        kl = _m(nt, "MULTIPLY", kl, 0.25)
    kreide = _mix(nt, 0.35, hsv.outputs["Color"], V.hex_lin("#BDB8AE"))
    farbe = _mix(nt, kl, farbe, kreide)
    # Rostflecken: unten (Schweller, Radlaeufe, Tuerunterkanten) + vereinzelt oben (Blasen)
    rost_t = _tex(nt, "MAT_Rost_Blech", ("_diff_",), False, 1.2)
    unten = _mr(nt, hoch, 0.62, 0.18)
    rn = _n(nt, P, 7.0, 8.0, 0.7)
    rmask = _m(nt, "MAXIMUM", _m(nt, "MULTIPLY", _mr(nt, rn, 0.62, 0.68), unten),
               _m(nt, "MULTIPLY", _mr(nt, _n(nt, P, 12.0, 6.0, 0.6), 0.73, 0.76), oben))
    rmask = _m(nt, "MULTIPLY", rmask, _mr(nt, alter, 0.3, 1.0), clamp=True)
    farbe = _mix(nt, rmask, farbe, rost_t)
    rau = _m(nt, "ADD", 0.32, _m(nt, "MULTIPLY", kl, 0.4))
    rau = _m(nt, "MAXIMUM", rau, _m(nt, "MULTIPLY", rmask, 0.9))
    # Klarlack-Schicht: weg bei Schaden und Rost, sonst stumpfer
    coat = _m(nt, "MULTIPLY", _m(nt, "SUBTRACT", 1.0, _m(nt, "MAXIMUM", kl, rmask)),
              _m(nt, "SUBTRACT", 1.0, _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", alter, oben), 0.55)), clamp=True)
    if matt:
        coat = 0.0
        rau = _m(nt, "ADD", rau, 0.38, clamp=True)
    _l(nt, coat, b.inputs["Coat Weight"])
    _l(nt, _m(nt, "ADD", 0.06, _m(nt, "MULTIPLY", alter, 0.3)), b.inputs["Coat Roughness"])
    met = _m(nt, "MULTIPLY", metallic, _m(nt, "SUBTRACT", 1.0, _m(nt, "MAXIMUM", rmask, _m(nt, "MULTIPLY", kl, 0.6))), clamp=True)
    _l(nt, met, b.inputs["Metallic"])
    # leichte Dellen/Welligkeit + erhabene Rostblasen
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.06
    bump.inputs["Distance"].default_value = 0.01
    nt.links.new(_m(nt, "ADD", _m(nt, "MULTIPLY", _n(nt, P, 3.0, 2.0), 0.5), rmask), bump.inputs["Height"])
    _ende(nt, b, farbe, rau, bump.outputs["Normal"], 0.5, "#8E8A82")  # Kanten: Grundierung statt Rost (Rost kommt aus der eigenen Maske)
    return m


def chrom(name="MAT_Chrom_Alt"):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = V._neues_mat(name)
    geo, Nz = _geo(nt)
    P = geo.outputs["Position"]
    grunge = _tex(nt, "MAT_Blech_Rostflecken", ("_rough_",), True, 1.5)
    loch = _mr(nt, _m(nt, "ADD", _m(nt, "MULTIPLY", _n(nt, P, 28.0, 6.0, 0.7), 0.6), _m(nt, "MULTIPLY", grunge, 0.4)), 0.71, 0.75)
    farbe = _mix(nt, loch, V.hex_lin("#B9BCBD"), V.hex_lin("#5B4433"))
    rau = _m(nt, "ADD", _mr(nt, grunge, 0.2, 0.9, 0.16, 0.42), _m(nt, "MULTIPLY", loch, 0.6), clamp=True)
    _l(nt, _m(nt, "SUBTRACT", 1.0, _m(nt, "MULTIPLY", loch, 0.9)), b.inputs["Metallic"])
    _ende(nt, b, farbe, rau, None, 0.6, "#6E3B23")
    return m


def felge(name, hexf, metallic, rost=0.4):
    mn = f"MAT_Felge_{name}"
    if mn in bpy.data.materials:
        return bpy.data.materials[mn]
    m, nt, b = V._neues_mat(mn)
    geo, Nz = _geo(nt)
    P = geo.outputs["Position"]
    grunge = _tex(nt, "MAT_Blech_Rostflecken", ("_rough_",), True, 3.0)
    rostm = _mr(nt, _m(nt, "ADD", _m(nt, "MULTIPLY", grunge, 0.5), _m(nt, "MULTIPLY", _n(nt, P, 15.0, 6.0), 0.5)),
                0.75 - 0.3 * rost, 0.8 - 0.3 * rost)
    if metallic > 0.7:  # Aluminium oxidiert weisslich-grau, Bremsstaub dunkelbraun
        ox = _mix(nt, _m(nt, "MULTIPLY", _mr(nt, grunge, 0.4, 0.9), 0.45), V.hex_lin("#BEBCB4"), V.hex_lin("#5E5346"))
        farbe = _mix(nt, rostm, V.hex_lin(hexf), ox)
    else:
        rost_t = _tex(nt, "MAT_Rost_Blech", ("_diff_",), False, 4.0)
        farbe = _mix(nt, rostm, V.hex_lin(hexf), rost_t)
    _l(nt, _m(nt, "MULTIPLY", metallic, _m(nt, "SUBTRACT", 1.0, rostm)), b.inputs["Metallic"])
    rau = _m(nt, "ADD", 0.35, _m(nt, "MULTIPLY", rostm, 0.55))
    _ende(nt, b, farbe, rau, None, 0.8, "#6E3B23")
    return m


def reifen(name="MAT_Reifen_Alt"):
    """Gummi: grau ausgeblichen und rissig, Profil-Bloecke als Bump (Objektkoordinaten des Rads)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = V._neues_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ang = _m(nt, "ARCTAN2", sep.outputs["Z"], sep.outputs["X"])
    rad = nt.nodes.new("ShaderNodeVectorMath")
    rad.operation = "LENGTH"
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], cmb.inputs[0])
    nt.links.new(sep.outputs["Z"], cmb.inputs[2])
    nt.links.new(cmb.outputs[0], rad.inputs[0])
    r = rad.outputs["Value"]
    rmax = _a(nt, "reifen_r", "OBJECT")
    lauf = _mr(nt, _m(nt, "SUBTRACT", r, rmax), -0.03, -0.012)
    bloecke = _m(nt, "PINGPONG", _m(nt, "ADD", _m(nt, "MULTIPLY", ang, 9.5), _m(nt, "MULTIPLY", _m(nt, "ABSOLUTE", sep.outputs["Y"]), 18.0)), 0.5)
    profil = _m(nt, "MULTIPLY", _mr(nt, bloecke, 0.12, 0.2), lauf)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    risse = _mr(nt, _n(nt, geo.outputs["Position"], 60.0, 3.0, 0.5, 1.5), 0.48, 0.52)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.006
    nt.links.new(_m(nt, "SUBTRACT", profil, _m(nt, "MULTIPLY", risse, 0.15)), bump.inputs["Height"])
    alter = _a(nt, "lack_alter", "OBJECT")
    flanke = _m(nt, "SUBTRACT", 1.0, lauf)
    grau = _m(nt, "MULTIPLY", _m(nt, "MULTIPLY", alter, flanke), _mr(nt, _n(nt, geo.outputs["Position"], 8.0, 4.0), 0.3, 0.7, 0.6, 1.0))
    farbe = _mix(nt, grau, V.hex_lin("#1D1D1C"), V.hex_lin("#4A4843"))
    farbe = _mix(nt, _m(nt, "MULTIPLY", risse, 0.4), farbe, V.hex_lin("#121211"))
    _ende(nt, b, farbe, 0.86, bump.outputs["Normal"], 0.85, "#5A5650")
    return m


def autoglas(name="MAT_Autoglas"):
    """Sicherheitsglas: Staub, Wasserflecken, Algenfilm unten, Toenungsstreifen (Attribut tint)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = V._neues_mat(name)
    geo, Nz = _geo(nt)
    P = geo.outputs["Position"]
    g = _tex(nt, "MAT_Beton_Grob", ("_rough_",), True, 0.8)
    alter = _a(nt, "lack_alter", "OBJECT")
    hoch = _a(nt, "fz_z", "GEOMETRY")
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Thin Wall"].default_value = True
    b.inputs["IOR"].default_value = 1.52
    tint = _a(nt, "tint", "GEOMETRY")
    klar = _mix(nt, tint, V.hex_lin("#C9D2CE"), V.hex_lin("#3E5A55"))
    schmutz = _m(nt, "MULTIPLY", _mr(nt, g, 0.25, 0.85, 0.05, 0.55), _m(nt, "ADD", 0.4, alter), clamp=True)
    alge = _m(nt, "MULTIPLY", _mr(nt, _m(nt, "ADD", hoch, _m(nt, "MULTIPLY", _n(nt, P, 3.0, 4.0), 0.25)), 1.2, 0.85), alter, clamp=True)
    farbe = _mix(nt, schmutz, klar, V.hex_lin("#8C8676"))
    farbe = _mix(nt, _m(nt, "MULTIPLY", alge, 0.55), farbe, V.hex_lin("#5E6A3E"))
    rau = _m(nt, "ADD", 0.05, _m(nt, "MULTIPLY", _m(nt, "MAXIMUM", schmutz, alge), 0.45), clamp=True)
    _ende(nt, b, farbe, rau, None, 0.55, "#8C8676")
    return m


def streuscheibe(name, hexf, vergilbt=True):
    mn = f"MAT_Streuscheibe_{name}"
    if mn in bpy.data.materials:
        return bpy.data.materials[mn]
    m, nt, b = V._neues_mat(mn)
    geo, Nz = _geo(nt)
    P = geo.outputs["Position"]
    alter = _a(nt, "lack_alter", "OBJECT")
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.49
    farbe = V.hex_lin(hexf)
    if vergilbt:
        farbe = _mix(nt, _m(nt, "MULTIPLY", alter, 0.6), farbe, V.hex_lin("#C9AE62"))
    trueb = _m(nt, "MULTIPLY", alter, _mr(nt, _n(nt, P, 9.0, 4.0), 0.3, 0.7, 0.18, 0.42))
    _ende(nt, b, farbe, _m(nt, "ADD", 0.08, trueb), None, 0.45, "#8C8676")
    return m


def reflektor(name="MAT_Reflektor"):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = V._neues_mat(name)
    geo, Nz = _geo(nt)
    b.inputs["Metallic"].default_value = 1.0
    fleck = _mr(nt, _n(nt, geo.outputs["Position"], 14.0, 5.0), 0.55, 0.7)
    _ende(nt, b, _mix(nt, fleck, V.hex_lin("#D4D4D2"), V.hex_lin("#6B655A")), _m(nt, "ADD", 0.12, _m(nt, "MULTIPLY", fleck, 0.5)), None, 0.3, "#6B655A")
    return m


def kennzeichen(name="MAT_Kennzeichen"):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = V._neues_mat(name)
    g = _tex(nt, "MAT_Blech_Rostflecken", ("_rough_",), True, 4.0)
    farbe = _mix(nt, _mr(nt, g, 0.3, 0.9, 0.0, 0.6), V.hex_lin("#D9D6CC"), V.hex_lin("#8C8270"))
    _ende(nt, b, farbe, _mr(nt, g, 0.0, 1.0, 0.35, 0.75), None, 0.8, "#6E3B23")
    return m


def dunkel(name="MAT_Fahrzeug_Dunkel"):
    """Fuer verdeckte Innenflaechen (Hohlraeume, Spalt-Hintergrund)."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, b = V._neues_mat(name)
    b.inputs["Base Color"].default_value = V.hex_lin("#141413")
    b.inputs["Roughness"].default_value = 0.8
    return m


def text_mat(name, hexf, rau=0.6):
    mn = f"MAT_Schrift_{name}"
    if mn in bpy.data.materials:
        return bpy.data.materials[mn]
    m, nt, b = V._neues_mat(mn)
    _ende(nt, b, V.hex_lin(hexf), rau, None, 0.7, "#6E3B23")
    return m


def satz(farbname, farben):
    """Alle Materialien eines Fahrzeugs (Name -> Material)."""
    eintrag = farben[farbname]
    hexf, met = eintrag[0], eintrag[1]
    return {
        "lack": lack(farbname, hexf, met, matt=len(eintrag) > 2 and eintrag[2] == "matt"),
        "schwarz": V.material("MAT_Kunststoff_Schwarz"),
        "verkleidung": V.material("MAT_Kunststoff_Schwarz"),
        "grau": V.material("MAT_Kunststoff_Grau"),
        "rahmen": V.material("MAT_Kunststoff_Schwarz"),
        "chrom": chrom(),
        "unterboden": V.material("MAT_Unterboden"),
        "radhaus": V.material("MAT_Kunststoff_Schwarz"),
        "glas": autoglas(),
        "scheinwerfer": streuscheibe("Klar", "#EEF0EC"),
        "ruecklicht": streuscheibe("Rot", "#A0170F", False),
        "blinker": streuscheibe("Gelb", "#D07A16", False),
        "reflektor": reflektor(),
        "reifen": reifen(),
        "felge_alu": felge("Alu", "#A3A6A8", 0.85, 0.25),
        "felge_stahl": felge("Stahl", "#2A2A2A", 0.3, 0.7),
        "felge_kappe": felge("Kappe", "#9FA2A4", 0.6, 0.15),
        "bremse": V.material("MAT_Bremsscheibe"),
        "kennzeichen": kennzeichen(),
        "schrift": text_mat("Kennzeichen", "#1F2E4A"),
        "dunkel": dunkel(),
        "innen_tuer": V.material("MAT_Tuerverkleidung"),
        "dachhimmel": V.material("MAT_Dachhimmel"),
        "armaturen": V.material("MAT_Armaturen"),
        "teppich": V.material("MAT_Teppich_Auto"),
    }
