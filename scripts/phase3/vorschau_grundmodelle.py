"""Phase 3.1.11 – Vorschau der 8 Grundmodelle (ZWISCHEN-STOPP): je 3 Winkel + Innenraum, dazu eine Reihe aller Typen.

Aufruf:  blender -b --factory-startup --python scripts/phase3/vorschau_grundmodelle.py -- [--nur A,B] [--schnell] [--ohne-reihe]
Ergebnis: renders/test/phase3_grund_<Typ>_{vorne,seite,hinten,innen}.png, phase3_grund_reihe.png, scripts/../viertel_fz_grundmodelle.blend (nicht im Repo)
"""
import math
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "..", "lib"))
sys.path.insert(0, HIER)
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import viertel_lib as V  # noqa: E402
import fahrzeug as FZ  # noqa: E402
import fz_karosserie as K  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
nur = args[args.index("--nur") + 1].split(",") if "--nur" in args else list("ABCDEFGH")
schnell = "--schnell" in args
ausgabe = os.path.join(V.ROOT, "renders", "test")
os.makedirs(ausgabe, exist_ok=True)

FARBE = {"A": "Silber", "B": "Dunkelblau", "C": "Schwarz", "D": "Weiss", "E": "Braun_Metallic", "F": "Rot",
         "G": "Grau", "H": "Weiss"}


def studio():
    sc = V.leere_szene()
    V.regler_setzen(sc)
    sc["verw_boden_gx"] = sc["verw_boden_gy"] = sc["verw_boden_z0"] = 0.0
    hdr = os.path.join(V.ASSETS, "hdri", "kloofendal_28d_misty_puresky_4k.hdr")
    img = bpy.data.images.load(hdr, check_existing=True)
    rot, el = V.hdri_rotation_fuer(img, 60)
    V.hdri_welt(hdr, 1.0, rot)
    V.sonne(60, el, staerke=2.5, kelvin=5000, winkel_grad=2.0)
    bm = bmesh.new()
    V.box(bm, -120, -120, -0.05, 120, 120, 0.0)
    V.objekt_aus_bmesh("Boden_Asphalt", bm, sc.collection, material=V.material("MAT_Asphalt_Rissig"))
    return sc


def kamera(name, pos, ziel, lens=35, sc=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = pos
    ob.rotation_euler = (Vector(ziel) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    return ob


def sichtbar(roots, nur_root):
    for r in roots:
        an = r is nur_root or nur_root is None
        for ob in [r] + FZ._kinder(r):
            ob.hide_render = not an


if __name__ == "__main__":
    sc = studio()
    C = FZ.cfg()
    roots = {}
    zeiten = {}
    abstand = 0.0
    for t in nur:
        T = C["typen"][t]
        t0 = time.time()
        r = FZ.bauen(t, farbe=FARBE[t], seed=11, alter=0.8)
        r.location = (0, abstand, 0)
        roots[t] = r
        zeiten[f"bau_{t}"] = round(time.time() - t0, 1)
        abstand += 7.0
    bpy.context.view_layer.update()
    breite, hoehe, samples = (480, 270, 16) if schnell else (960, 540, int(args[args.index("--samples") + 1]) if "--samples" in args else 28)
    for t, r in roots.items():
        T = C["typen"][t]
        P = K.Profil(T)
        L, Hh = T["L"], T["H"]
        c = r.location
        sichtbar(roots.values(), r)
        I = T["innen"]
        di = (I["sitz_h"] or I["sitz_v"] + 0.55) + 0.05
        if I.get("trennwand"):
            di = I["trennwand"] - 0.06
        ansichten = {
            "vorne": (c + Vector((L / 2 + 3.4, 3.9, 1.3 + Hh * 0.15)), c + Vector((0.35, 0, Hh * 0.45)), 35),
            "seite": (c + Vector((0, L * 1.62, 1.05)), c + Vector((0, 0, Hh * 0.47)), 50),
            "hinten": (c + Vector((-(L / 2 + 3.2), 3.8, 1.45 + Hh * 0.15)), c + Vector((-0.35, 0, Hh * 0.45)), 35),
            "innen": (c + Vector((P.x(I["sitz_v"] + 0.45), P.hw(I["sitz_v"]) + 0.85, I["sitz"] + 0.70)),
                      c + Vector((P.x(I["lenkrad"][0] - 0.25), 0.15, I["lenkrad"][1] - 0.05)), 20),
        }
        tuer = bpy.data.objects.get(f"{r.name}_Tuer_vl")
        for n, (pos, ziel, lens) in ansichten.items():
            cam = kamera(f"CAM_{t}_{n}", pos, ziel, lens)
            sc.camera = cam
            sc.view_settings.exposure = 0.7 if n == "innen" else 0.0
            if tuer is not None:
                tuer.rotation_euler.z = math.radians(-75) if n == "innen" else 0.0
            t0 = time.time()
            V.vorschau_render(sc, os.path.join(ausgabe, f"phase3_grund_{t}_{n}.png"), samples=int(samples * (1.7 if n == "innen" else 1)),
                              breite=breite, hoehe=hoehe)
            zeiten[f"{t}_{n}"] = round(time.time() - t0, 1)
    if "--ohne-reihe" not in args and len(roots) > 1:
        # Alle Typen nebeneinander (Seitenansicht, orthografisch) + 1,75-m-Figur als Massstab
        sichtbar(roots.values(), None)
        sc.view_settings.exposure = 0.0
        x = 0.0
        for t in nur:
            r = roots[t]
            L = C["typen"][t]["L"]
            r.location = (x + L / 2, 0, 0)
            x += L + 0.9
        bm = bmesh.new()
        V.box(bm, x, -0.2, 0, x + 0.45, 0.2, 1.75)
        V.objekt_aus_bmesh("Massstab_175cm", bm, sc.collection, material=V.material("MAT_Kunststoff_Grau"))
        cd = bpy.data.cameras.new("CAM_Reihe")
        cd.type = "ORTHO"
        cd.ortho_scale = x + 1.4
        cam = bpy.data.objects.new("CAM_Reihe", cd)
        sc.collection.objects.link(cam)
        cam.location = ((x + 0.45) / 2, -40, 1.2)
        cam.rotation_euler = (math.radians(90), 0, 0)
        sc.camera = cam
        t0 = time.time()
        V.vorschau_render(sc, os.path.join(ausgabe, "phase3_grund_reihe.png"), samples=24 if not schnell else 12,
                          breite=2400 if not schnell else 1200, hoehe=420 if not schnell else 210)
        zeiten["reihe"] = round(time.time() - t0, 1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(V.ROOT, "viertel_fz_grundmodelle_test.blend"), compress=True)
    print("ZEITEN", zeiten)
