#!/usr/bin/env python3
"""Schreibt LIZENZEN.txt aus assets_manifest.json (Quelle, Autor, Lizenz jedes Assets)."""
import json, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
m = json.load(open(os.path.join(ROOT, "assets_manifest.json"), encoding="utf-8"))
z = ["LIZENZEN – alle externen Assets dieses Projekts", "=" * 50, "",
     "Alle Assets stehen unter CC0 1.0 (Public Domain, keine Namensnennung noetig).",
     "Poly Haven: https://polyhaven.com/license   ambientCG: https://docs.ambientcg.com/license", "",
     f"{'Name':28} {'Typ':7} {'Quelle':10} {'Lizenz':7} Autor(en) / Seite"]
gesehen = set()
for a in m["assets"]:
    key = (a["asset_id"], a["aufloesung"])
    if key in gesehen:
        continue
    gesehen.add(key)
    z.append(f"{a['name'][:28]:28} {a['typ']:7} {a['quelle'][:10]:10} {a['lizenz'][:7]:7} {', '.join(a['autoren'])} / {a['seite']}")
z += ["", "Selbst gebaut (keine externe Lizenz): " + "; ".join(m.get("selbst_gebaut", [])),
      "", "Software: Blender 5.2.3 LTS (GPL), MPFB 2 (GPLv3, Assets CC0)."]
open(os.path.join(ROOT, "LIZENZEN.txt"), "w", encoding="utf-8").write("\n".join(z) + "\n")
print("LIZENZEN.txt:", len(gesehen), "Eintraege")
