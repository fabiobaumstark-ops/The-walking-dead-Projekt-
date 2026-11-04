# UEBERGABE – aktueller Stand

- **Aktuelle Phase:** Phase 2 läuft (allein, ohne parallele Agenten). 2.1/2.2 Gebäude fertig, als Nächstes 2.3 Straßenraum
- **Blender-Version:** 5.2.3 LTS (Linux: /opt/blender-5.2.3-linux-x64, Befehl `blender`)
- **.blend-Version:** `viertel_v01.blend` (Blockout, 7,6 MB, Texturpfade relativ)
- **Branch:** `claude/zen-meitner-53hxe1`
- **Netzwerk:** FULL (siehe AUFTRAG.md, A1b)

## Fertig
- Phase 0: AUFTRAG.md, PROTOKOLL.md, recherche/ (RECHERCHE.md, architektur.md, vegetation.md, moodboard.html, LOOK_BIBLE.md v1.0 – bestätigt)
- Phase 1.1 Assets:
  - Auswahl: scripts/configs/assets_auswahl.json
  - scripts/phase1/make_manifest.py → assets_manifest.json (70 Assets, 1,36 GB, CC0)
  - download_assets.py (getestet)
  - scripts/phase1/make_lizenzen.py → LIZENZEN.txt
- Phase 1.2 Material-Bibliothek:
  - scripts/lib/viertel_lib.py: 35 MAT_-Materialien + Shader-Gruppe MAT_Verwitterung, zentrale Regler verw_* als Szenen-Eigenschaften
  - scripts/configs/materialien.json
  - Testreihe: scripts/phase1/materialtest.py → renders/test/phase1_materialtest_000/050/100.png
- Phase 1.3/1.4: scripts/phase1/blockout_umgebung.py
  - Konfiguration: scripts/configs/gelaende.json, layout.json
  - Inhalt: Gelände, 5 Straßenblöcke, Kreuzung, Platz, Gasse, Hochstraße, Hintergrund
- Phase 1.5: scripts/phase1/blockout_gebaeude.py + scripts/configs/gebaeude.json
  - 38 Gebäude, alle 8 Typen, Seed 42
  - Zerstörung: 11 leicht / 16 mittel / 11 schwer
  - Legende: LAGEPLAN.md
- Phase 1.6: scripts/phase1/blockout_kameras.py + scripts/configs/kameras.json (4 Hero-Kameras + Draufsicht)
- Renders: scripts/phase1/render_blockout.py → renders/test/
  - phase1_cam1–4, phase1_draufsicht
  - phase1_lageplan, phase1_lageplan_variante_A/B/C
- Varianten für Frage 4: scripts/configs/platzierung_varianten.json

## Halb fertig / fehlt
- Phase 2:
  - fertig: 2.1/2.2 Gebäude (scripts/phase2/gebaeude2.py, Baukasten scripts/lib/fassade.py)
  - offen: 2.3 Straßenraum (scripts/phase2/strassenraum.py), 2.4 Schutt (schutt.py), 2.5 Checkpoint (checkpoint.py), 2.6 Barrikaden (barrikaden.py), A13 Hintergrund-Ring (hintergrund_ring.py)
  - build_phase2.py lädt diese Module automatisch, sobald die Datei existiert

## Nächster konkreter Schritt
1. Neue Sitzung:
   - Blender 5.2.3 installieren (`curl -O https://download.blender.org/release/Blender5.2/blender-5.2.3-linux-x64.tar.xz`, nach /opt entpacken, Symlink /usr/local/bin/blender)
   - dann `python3 download_assets.py --nur-basis`
2. Phase 2 starten (AUFTRAG.md Phase 2 + A13 lesen). Phase-1-Antworten sind schon in den Configs.
3. Neu bauen (Befehle unten), Version hochzählen (v02), dann Phase 2 laut AUFTRAG.md.

## Offene Fragen an den Nutzer
- keine (Phase 2 läuft)

## Bisherige Antworten/Freigaben
- Netzwerk: FULL
- Blender: normale Linux-Version
- Branch: claude/zen-meitner-53hxe1
- Phase-0-Fragen 1–11: alle Empfehlungen angenommen
- Look-Bible v1.0 bestätigt, Phase 1 freigegeben
- Phase-1-Fragen (2026-11-04): 1A Layout ok, 2A Höhen/Dichte ok, 3A Kameras ok,
  4A Platzierung Variante A (platzierung_varianten.json → "gewaehlt": "A"),
  5B Verwitterung stärker (verw_master 0,85, verw_kanten 1,3 in materialien.json)
- Bäume (Phase 4): freie Baum-Modelle aus anderen Quellen, nur eindeutig freie Lizenz, echte Modelle vor selbst erzeugten
- Phase 2 gestartet: Option A (allein, keine parallelen Agenten)
- Neu: A13 Hintergrund-Ring (AUFTRAG.md). Silhouetten und Gelände in Phase 2, Bäume in Phase 4, Dunst in Phase 5.
  Nach Phase 2 mit CAM_Hero_02 auf leere Horizontstellen prüfen

## Ausgeführte Skripte (Reihenfolge, alle im Repo-Hauptordner)
1. `python3 scripts/phase1/make_manifest.py`
2. `python3 download_assets.py --nur-basis`
3. `python3 scripts/phase1/make_lizenzen.py`
4. `blender -b --factory-startup --python scripts/phase1/materialtest.py`
5. `blender -b --factory-startup --python scripts/phase1/build_blockout.py -- --version 01`
6. `blender -b viertel_v01.blend --python scripts/phase1/render_blockout.py`
7. Phase 2: `blender -b --factory-startup --python scripts/phase2/build_phase2.py -- --version 02` (Test: --version 02test, Datei danach löschen)
