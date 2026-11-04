# UEBERGABE – aktueller Stand

- **Aktuelle Phase:** Phase 1 – Schritt 1.3/1.4 (Gelände, Straßen) fertig, als Nächstes 1.5 Gebäude-Blockout
- **Blender-Version:** 5.2.3 LTS (Linux, /opt/blender-5.2.3-linux-x64, Befehl `blender`)
- **.blend-Version:** noch keine
- **Branch:** `claude/zen-meitner-53hxe1`
- **Netzwerk:** FULL (siehe AUFTRAG.md, A1b)

## Fertig
- AUFTRAG.md (Version 8, A1b Netzwerk FULL ergänzt)
- PROTOKOLL.md (Umgebungsprüfung, Blender-Installation)
- .gitignore
- Blender 5.2.3 LTS installiert + Testrender ok
- recherche/RECHERCHE.md, architektur.md, vegetation.md, moodboard.html
- recherche/LOOK_BIBLE.md v1.0 (alle Empfehlungen angenommen)
- MPFB 2.0.18 Installationstest in Blender 5.2.3: ok
- Phase 1.1: scripts/configs/assets_auswahl.json, scripts/phase1/make_manifest.py, assets_manifest.json (70 Assets, 1,36 GB), download_assets.py (in der Cloud getestet, inkl. Überspringen), LIZENZEN.txt
- Phase 1.2: scripts/lib/viertel_lib.py (Bibliothek: MAT_-Materialien, Gruppe MAT_Verwitterung, Hilfsfunktionen), scripts/configs/materialien.json, scripts/phase1/materialtest.py → renders/test/phase1_materialtest_000/050/100.png
- Phase 1.3/1.4: scripts/configs/gelaende.json, layout.json, scripts/phase1/blockout_umgebung.py (Gelände 300x300 m + Außenring, 5 Straßenblöcke mit Bordstein/Gehweg/Grünstreifen/Rampen, Baumscheiben, Platz mit Brunnen, Gasse mit Containern, Hochstraße mit abgestürztem Feld, Hintergrund-Silhouetten), scripts/phase1/build_blockout.py (Gesamtaufbau)

## Halb fertig / fehlt
- Phase 1.5–1.6 noch offen (Gebäude-Blockout mit Generator, Kameras, Renders, Lageplan)
- fahrzeuge.md / militaer.md: erst vor Phase 3 (laut Auftrag)

## Nächster konkreter Schritt
- Neue Sitzung: Blender 5.2.3 installieren (siehe PROTOKOLL.md), dann `python3 download_assets.py --nur-basis`.
- Phase 1.5: scripts/phase1/blockout_gebaeude.py + scripts/configs/gebaeude.json schreiben (wird von build_blockout.py importiert).

## Offene Fragen an den Nutzer
- keine

## Bisherige Antworten/Freigaben
- Netzwerk: FULL (alle Domains erreichbar)
- Blender: normale Linux-Version (nicht bpy von PyPI)
- Branch: weiter in `claude/zen-meitner-53hxe1`
- Recherche Phase 0 starten: ja
- Phase-0-Fragen 1–11: alle Empfehlungen angenommen (siehe LOOK_BIBLE.md)
- Look-Bible v1.0 bestätigt, Phase 1 freigegeben (2026-11-04)

## Ausgeführte Skripte (Reihenfolge)
1. scripts/phase1/make_manifest.py (erzeugt assets_manifest.json)
2. download_assets.py --nur-basis
3. scripts/phase1/make_lizenzen.py
4. blender -b --factory-startup --python scripts/phase1/materialtest.py
5. blender -b --factory-startup --python scripts/phase1/build_blockout.py -- --version 01  (baut alles, speichert viertel_v01.blend)
