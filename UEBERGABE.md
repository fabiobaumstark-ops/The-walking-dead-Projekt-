# UEBERGABE – aktueller Stand

- **Aktuelle Phase:** Phase 1 abgeschlossen → **wartet auf Freigabe (Fragen 1–5, STOPP)**
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
- Nichts halb fertig. Phase 2 beginnt erst nach Freigabe.

## Nächster konkreter Schritt
1. Neue Sitzung:
   - Blender 5.2.3 installieren (`curl -O https://download.blender.org/release/Blender5.2/blender-5.2.3-linux-x64.tar.xz`, nach /opt entpacken, Symlink /usr/local/bin/blender)
   - dann `python3 download_assets.py --nur-basis`
2. Antworten des Nutzers auf die Phase-1-Fragen einarbeiten:
   - Layout/Höhen: scripts/configs/layout.json + gebaeude.json
   - Kameras: kameras.json
   - Platzierung: gewählte Variante aus platzierung_varianten.json festschreiben
   - Verwitterung: materialien.json → verwitterung
3. Neu bauen (Befehle unten), Version hochzählen (v02), dann Phase 2 laut AUFTRAG.md.

## Offene Fragen an den Nutzer (gestellt am 2026-11-04)
Phase-1-Freigabe:
1. Layout
2. Höhen/Dichte
3. Kameraausschnitte
4. Platzierungsvariante A/B/C (Empfehlung A)
5. Materialien/Verwitterung (Empfehlung: Standard stärker, 0,85)

## Bisherige Antworten/Freigaben
- Netzwerk: FULL
- Blender: normale Linux-Version
- Branch: claude/zen-meitner-53hxe1
- Phase-0-Fragen 1–11: alle Empfehlungen angenommen
- Look-Bible v1.0 bestätigt, Phase 1 freigegeben

## Ausgeführte Skripte (Reihenfolge, alle im Repo-Hauptordner)
1. `python3 scripts/phase1/make_manifest.py`
2. `python3 download_assets.py --nur-basis`
3. `python3 scripts/phase1/make_lizenzen.py`
4. `blender -b --factory-startup --python scripts/phase1/materialtest.py`
5. `blender -b --factory-startup --python scripts/phase1/build_blockout.py -- --version 01`
6. `blender -b viertel_v01.blend --python scripts/phase1/render_blockout.py`
