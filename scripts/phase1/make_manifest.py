#!/usr/bin/env python3
"""Erzeugt assets_manifest.json aus scripts/configs/assets_auswahl.json.

Fragt die offiziellen APIs von Poly Haven und ambientCG ab (nur Python-Standardbibliothek)
und schreibt fuer jedes Asset: Name, Quelle, Seiten-URL, Aufloesung, Lizenz, Zielpfad,
reale Masse und alle Einzeldateien (URL, Groesse, MD5).

Aufruf (im Repo-Hauptordner):  python3 scripts/phase1/make_manifest.py
"""
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AUSWAHL = os.path.join(ROOT, "scripts", "configs", "assets_auswahl.json")
MANIFEST = os.path.join(ROOT, "assets_manifest.json")
UA = {"User-Agent": "viertel-projekt-manifest/1.0"}


def get_json(url):
    for versuch in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # Netzwerkfehler -> kurz warten, erneut
            if versuch == 3:
                raise
            time.sleep(2 ** (versuch + 1))


def ph_info(asset_id):
    return get_json(f"https://api.polyhaven.com/info/{asset_id}")


def ph_files(asset_id):
    return get_json(f"https://api.polyhaven.com/files/{asset_id}")


def datei(url, ziel, size=None, md5=None):
    return {"url": url, "ziel": ziel, "size": size, "md5": md5}


def textur_polyhaven(e):
    aid, res = e["id"], e["res"]
    info, files = ph_info(aid), ph_files(aid)
    ziel = f"assets/textures/{aid}"
    out = []
    karten = [("Diffuse", "jpg"), ("Rough", "jpg"), ("nor_gl", "jpg"), ("Displacement", "png"), ("AO", "jpg")]
    for key, fmt in karten:
        if key in files and res in files[key] and fmt in files[key][res]:
            f = files[key][res][fmt]
            out.append(datei(f["url"], f"{ziel}/{os.path.basename(f['url'])}", f["size"], f["md5"]))
    dims = info.get("dimensions") or [2000, 2000]
    return {
        "name": e["mat"], "typ": "textur", "quelle": "Poly Haven", "asset_id": aid,
        "seite": f"https://polyhaven.com/a/{aid}", "aufloesung": res, "lizenz": "CC0 1.0",
        "autoren": list((info.get("authors") or {}).keys()), "zielpfad": ziel,
        "masse_m": [round(dims[0] / 1000.0, 3), round(dims[1] / 1000.0, 3)], "gruppe": "basis",
        "dateien": out,
    }


def textur_ambientcg(e):
    aid, res = e["id"], e["res"]
    d = get_json(f"https://ambientcg.com/api/v2/full_json?id={aid}&include=downloadData,dimensionsData")
    a = d["foundAssets"][0]
    attr = f"{res.upper()}-JPG"
    dl = [x for x in a["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"]
          if x["attribute"] == attr][0]
    ziel = f"assets/textures/{aid}"
    dx = a.get("dimensionX") or 200  # cm
    dy = a.get("dimensionY") or dx
    return {
        "name": e["mat"], "typ": "textur", "quelle": "ambientCG", "asset_id": aid,
        "seite": f"https://ambientcg.com/view?id={aid}", "aufloesung": res, "lizenz": "CC0 1.0",
        "autoren": ["ambientCG (Lennart Demes)"], "zielpfad": ziel,
        "masse_m": [round(dx / 100.0, 3), round(dy / 100.0, 3)], "gruppe": "basis",
        "dateien": [dict(datei(dl["fullDownloadPath"], f"{ziel}/{aid}_{attr}.zip", dl["size"], None), entpacken=True)],
    }


def hdri(e):
    aid, res = e["id"], e["res"]
    info, files = ph_info(aid), ph_files(aid)
    f = files["hdri"][res]["hdr"]
    ziel = "assets/hdri"
    return {
        "name": e["name"], "typ": "hdri", "quelle": "Poly Haven", "asset_id": aid,
        "seite": f"https://polyhaven.com/a/{aid}", "aufloesung": res, "lizenz": "CC0 1.0",
        "autoren": list((info.get("authors") or {}).keys()), "zielpfad": ziel, "gruppe": e.get("gruppe", "basis"),
        "dateien": [datei(f["url"], f"{ziel}/{os.path.basename(f['url'])}", f["size"], f["md5"])],
    }


def modell(aid, res="2k"):
    info, files = ph_info(aid), ph_files(aid)
    b = files["blend"][res]["blend"]
    ziel = f"assets/models/{aid}"
    out = [datei(b["url"], f"{ziel}/{os.path.basename(b['url'])}", b["size"], b["md5"])]
    for rel, inc in (b.get("include") or {}).items():
        out.append(datei(inc["url"], f"{ziel}/{rel}", inc["size"], inc["md5"]))
    return {
        "name": aid, "typ": "modell", "quelle": "Poly Haven", "asset_id": aid,
        "seite": f"https://polyhaven.com/a/{aid}", "aufloesung": res, "lizenz": "CC0 1.0",
        "autoren": list((info.get("authors") or {}).keys()), "zielpfad": ziel, "gruppe": "basis",
        "dateien": out,
    }


def main():
    sel = json.load(open(AUSWAHL, encoding="utf-8"))
    assets = []
    for e in sel["texturen"]:
        print("Textur", e["id"], flush=True)
        assets.append(textur_polyhaven(e) if e["quelle"] == "polyhaven" else textur_ambientcg(e))
    for e in sel["hdris"]:
        print("HDRI", e["id"], e["res"], flush=True)
        assets.append(hdri(e))
    for aid in sel["modelle"]:
        print("Modell", aid, flush=True)
        assets.append(modell(aid))
    total = sum((f["size"] or 0) for a in assets for f in a["dateien"])
    basis = sum((f["size"] or 0) for a in assets if a["gruppe"] == "basis" for f in a["dateien"])
    man = {
        "_info": "Liste aller externen Assets. Laden mit: python3 download_assets.py",
        "erstellt": time.strftime("%Y-%m-%d"),
        "groesse_gesamt_mb": round(total / 1e6), "groesse_basis_mb": round(basis / 1e6),
        "selbst_gebaut": sel.get("selbst_bauen", []),
        "assets": assets,
    }
    json.dump(man, open(MANIFEST, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"Manifest geschrieben: {len(assets)} Assets, gesamt {total/1e6:.0f} MB (basis {basis/1e6:.0f} MB)")


if __name__ == "__main__":
    sys.exit(main())
