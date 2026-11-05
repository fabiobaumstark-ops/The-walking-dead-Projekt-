# UEBERGABE – aktueller Stand

- **Aktuelle Phase:** Phase 3 abgeschlossen → wartet auf Freigabe (Fragen 1–6 unten)
- **Blender-Version:** 5.2.3 LTS (Linux: /opt/blender-5.2.3-linux-x64, Befehl `blender`)
- **.blend-Version:** `viertel_v04.blend` (Phase 3, 70,7 MB, Freigabe B: eine große Datei); Vorversion `viertel_v03.blend`
- **Branch:** `claude/zen-meitner-53hxe1`
- **Netzwerk:** FULL (siehe AUFTRAG.md, A1b)
- **Lokal (Mac, 2026-11-05):** Blender 5.2.3 LTS unter /Applications/Blender-5.2.3.app, Metal-GPU (M4 Pro, 16 Kerne) erkannt, Assets geladen (356 Dateien, 1,7 GB)

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
- Phase 3 (läuft):
  - fertig: 3.1.0 Recherche → recherche/fahrzeuge.md, 3.2 → recherche/militaer.md
  - fertig: 4 neue CC0-Texturen (Sitzstoff, Leder, Rostblech, Blech mit Rostflecken)
  - Baukasten, Grundmodelle A–H (Profile + Maße in scripts/configs/fahrzeuge.json):
    - scripts/phase3/fz_karosserie.py: Loft, Bauteile, 5-mm-Spalte, Scheiben
    - fz_teile.py: Räder, Leuchten, Grill, Spiegel, Griffe, Innenraum, Unterboden, Pritsche
    - fz_material.py: Lack mit Alterung, Chrom, Glas, Reifen …
    - fahrzeug.py: Generator `bauen(typ, farbe, felge, seed, alter)`
    - vorschau_grundmodelle.py: Vorschau-Renders
    - kontaktbogen.py: Übersicht (braucht Pillow)
  - offen nach Zwischen-Stopp: Front-/Heck-Varianten (2–3 je Typ), Schadenskatalog, ausgebrannte Fahrzeuge, LOD, Flotte + Anordnung, Sonderfahrzeuge, Panzer A/B, Hubschrauber, Figuren, Konsistenz-Test
- Phase 2 komplett:
  - 2.1/2.2 Gebäude: scripts/phase2/gebaeude2.py
  - 2.3 Straßenraum: strassenraum.py
  - 2.4 Schutt: schutt.py
  - 2.5 Checkpoint: checkpoint.py
  - 2.6 Barrikaden: barrikaden.py
  - A13 Hintergrund: hintergrund_ring.py
  - Aufbau aller Teile: scripts/phase2/build_phase2.py
- Bewusst offen für spätere Phasen:
  - Autos der Barrikade 1 und Wracks auf der Hochstraße sind Platzhalter (Phase 3)
  - Baum-Platzhalter (Kugeln) bis Phase 4
  - Kirche und Lagerhalle noch ohne echte Fensteröffnungen

## Nächster konkreter Schritt
1. Neue Sitzung: Blender 5.2.3 installieren, `python3 download_assets.py --nur-basis`.
2. Antworten auf die Phase-2-Fragen einarbeiten (Configs in scripts/configs/, neu bauen mit
   `blender -b --factory-startup --python scripts/phase2/build_phase2.py -- --version 03`).
3. Danach Phase 3 laut AUFTRAG.md:
   - zuerst Fahrzeug-Recherche 3.1.0 → recherche/fahrzeuge.md
   - Militär-Recherche → recherche/militaer.md
   - dann 8 Grundmodelle bauen und ZWISCHEN-STOPP zur Freigabe

## Offene Fragen an den Nutzer
- Freigabe-Fragen Phase 3 (1–6): Flotte, Panzer A, Hubschrauber, Geschichte, Figuren, einheitlicher Look

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
- Phase-2-Feedback (2026-11-04):
  - Frage 1 B „zu wenig Details, Moos fehlt“, Frage 2 A „viel zu wenig Details“
  - Nachfrage beantwortet:
    - 1C: Bäume, Büsche und Ranken bleiben in Phase 4, aber Moos, Flechten, Laub und kleine Grasbüschel in Rissen und Fugen jetzt
    - 2: alle Detail-Bereiche (Fassaden, Boden, Zerstörung, Innenräume)
    - 3B: Checkpoint und Barrikaden mit mehr Details und Menschenspuren
  - Umsetzung als Phase 2b
- Referenzbild des Nutzers (Konzeptkunst, vermutlich aus einem Videospiel – nur Stimmung, nicht gespeichert):
  - 1A: so viel Grün wie im Bild → Zeitspanne 10–15 Jahre (AUFTRAG A14, LOOK_BIBLE v1.1)
  - 2A: große Vegetation in Phase 4 nach den Fahrzeugen
  - 3: Flair (Gegenlicht/Dunst → Phase 5) und Boden (Erde/Matsch/aufgebrochener Asphalt → jetzt in 2b)
  - Pflanzen müssen realistisch und detailreich sein
  - Verzierte Fassaden und hohe Hintergrundgebäude nicht ausdrücklich gewählt (angeboten)
- Dichte: Antwort C (Viertel verdichten, keine Hochhaus-Skyline) → umgesetzt in v03
- Phase 2/2b freigegeben („Gut weiter“, 2026-11-04). Qualitätsrunde nach Phase 5 vereinbart (AUFTRAG 5.8).
- Phase 3: allein (ohne parallele Agenten, wie Phase 2)
- Dateigröße (2026-11-04): Antwort B – eine große .blend erlaubt (Ziel unter 90 MB, GitHub-Grenze 100 MB)
- ZWISCHEN-STOPP 3.1.11 (Grundmodelle A–H) freigegeben: „das passt“ (2026-11-04) → weiter mit Flotte, Schäden, Sonderfahrzeugen, Militär, Figuren
- Neu: A13 Hintergrund-Ring (AUFTRAG.md). Silhouetten und Gelände in Phase 2, Bäume in Phase 4, Dunst in Phase 5.
  Nach Phase 2 mit CAM_Hero_02 auf leere Horizontstellen prüfen

## Ausgeführte Skripte (Reihenfolge, alle im Repo-Hauptordner)
1. `python3 scripts/phase1/make_manifest.py`
2. `python3 download_assets.py --nur-basis`
3. `python3 scripts/phase1/make_lizenzen.py`
4. `blender -b --factory-startup --python scripts/phase1/materialtest.py`
5. `blender -b --factory-startup --python scripts/phase1/build_blockout.py -- --version 01`
6. `blender -b viertel_v01.blend --python scripts/phase1/render_blockout.py`
7. `blender -b --factory-startup --python scripts/phase2/build_phase2.py -- --version 02` (Phase 2b: --version 03; Module: + fassaden_details (über gebaeude2), boden, vegetation_klein)
8. `blender -b viertel_v02.blend --python scripts/phase1/render_blockout.py -- --prefix phase2`
9. Phase 2b: `blender -b --factory-startup --python scripts/phase2/build_phase2.py -- --version 03`
10. `blender -b viertel_v03.blend --python scripts/phase1/render_blockout.py -- --prefix phase2b`
11. Phase 3: `python3 scripts/phase1/make_manifest.py && python3 download_assets.py --nur-basis && python3 scripts/phase1/make_lizenzen.py` (neue Fahrzeug-Texturen)
12. `blender -b --factory-startup --python scripts/phase3/vorschau_grundmodelle.py` → renders/test/phase3_grund_*.png, dann `python3 scripts/phase3/kontaktbogen.py`
13. MakeHuman-Systemassets (CC0) für MPFB: `download_assets.py` lädt sie nach assets/mpfb (Texturen entpackt nach assets/mpfb/data); für den Figuren-Neubau das Zip zusätzlich in den MPFB-Benutzerordner entpacken (…/extensions/.user/user_default/mpfb/data)
14. `blender -b viertel_v03.blend --python scripts/phase3/build_phase3.py -- --version 04` (ohne --factory-startup, MPFB muss aktiv sein) → viertel_v04.blend
15. `blender -b viertel_v04.blend --python scripts/phase1/render_blockout.py -- --prefix phase3 --nur CAM_Hero_01,CAM_Hero_02,CAM_Hero_03,CAM_Hero_04,draufsicht`
16. Mac, 2026-11-05: 13 absolute Bildpfade (/home/user/…) in viertel_v04.blend auf relativ (//assets/…) umgestellt, per Python-Einzeiler in Blender 5.2.3; danach 303 Bilder, 0 fehlend, 0 absolut
