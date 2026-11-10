# UEBERGABE – aktueller Stand

- **Aktuelle Phase:** 5.8 Qualitätsrunde, Teil 1 fertig (2026-11-10) – wartet auf Rückmeldung; danach Teil 2 und Animation 5.6
- **Blender-Version:** 5.2.3 LTS (Linux: /opt/blender-5.2.3-linux-x64, Befehl `blender`)
- **.blend-Version:** `viertel_v10.blend` (5.8 Teil 1, 89,7 MB – Ziel unter 90 MB fast ausgeschöpft); Vorversion `viertel_v09.blend`
- **Branch:** `claude/zealous-ride-c12e2z` (neu ab 2026-11-10; gleicher Stand wie zuvor `claude/zen-meitner-53hxe1`)
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
1. Rückmeldung abwarten: Öffnet `viertel_v10.blend` auf dem Mac flüssig? Passt der stärkere Nebel, passt die neue CAM 4?
2. 5.8 Teil 2 (offen): Matratzen/Kartons (Scans cardboard_box_01 und trashbag liegen in assets/models), Sandsack-Material, Flachdächer, Lichtstrahlen, CAM 4 aufhellen. Danach 5.6 Animation (freigegeben mit Antwort 4B).
3. Ausgangsdatei: `viertel_v10.blend`. Reihenfolge nach einem Neubau älterer Phasen: nacharbeit_militaer.py → build_phase4.py --nur Konsistenz → build_phase5.py → qualitaet.py (macht Bäume zu Instanzen, Pfade relativ, Fenster leicht).
4. Vorschau in der Cloud (16 GB RAM): `render_vorschau.py -- --cpu --sparsam --nur <Nr>`, jede Kamera in einem eigenen Blender-Aufruf. Zwei Blender-Prozesse gleichzeitig sprengen den Speicher.
5. Speicher: Render-Szene braucht ohne Texturen ca. 11,7 GB (gemessen), mit Texturen geschätzt 13–16 GB. Auf dem Mac (24 GB) beim finalen Render andere Programme schließen.
6. MPFB-Paket: Server sehr langsam; bei Bedarf in Teilstücken parallel laden (Range-Anfragen), Zielgröße 280.737.770 Byte.

## Offene Fragen an den Nutzer
- Öffnet v10 auf dem Mac? (falls nein: was passiert genau)
- 5.8 Teil 1: Nebelstärke, neue CAM 4, Panzerturm in Ordnung?

## Bisherige Antworten/Freigaben
- Phase 5 (2026-11-10): 1A CAM 1 am besten, CAM 4 am schwächsten (neu komponieren), 2C Nebel zu schwach → mehr Dunst in der Tiefe, 3A final 1080p, 4B Animation ja, aber erst nach der Qualitätsrunde
- Phase 4 (2026-11-09): 1B Vegetation genau richtig, 2A Panzer-Form in der Qualitätsrunde überarbeiten, 3A Farben passen (Grading in Phase 5), 4B fast aus einem Guss
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
- Phase-3-Fragen (2026-11-05): alle Empfehlungen – 1A Flotte ok, 2B Panzerturm aus der Nähe weniger glatt (Dellen, Abplatzer, Schmutz), 3B Hubschrauberrumpf detaillierter (Nieten, Blechstöße, Dellen, Klappen), 4A Geschichte ok, 5A Figuren ok, 6A Look ok (Ausreißer über 2B/3B)
- Phase 4 „weiter“ (2026-11-05), Ansatz: 1A Bäume = Poly-Haven-CC0 (island_tree_01, island_tree_02, tree_small_02; keine Kiefern – zu schwer), 2A Efeu/Wein = eigener Generator mit ambientCG-Blattfotos (CC0), 3A Straßen 60–70 % bewachsen, Trampelpfad 2–3 m in der Mitte

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
17. Nacharbeit 2B/3B: `blender -b viertel_v04.blend --python scripts/phase3/nacharbeit_militaer.py -- --version 05` (baut nur 05_Militaer neu; Parameter militaer.json → "detail") → viertel_v05.blend
18. `blender -b viertel_v05.blend --python scripts/phase3/render_nah.py -- --prefix phase3b` und `blender -b viertel_v05.blend --python scripts/phase1/render_blockout.py -- --prefix phase3b --nur CAM_Hero_01,CAM_Hero_02,CAM_Hero_03,CAM_Hero_04`
19. Phase 4: `blender -b viertel_v05.blend --python scripts/phase4/build_phase4.py -- --version 06 [--nur Baeume,Ranken,Boden]` → viertel_v06.blend (Bäume sind aus assets/models VERLINKT, assets/ muss vorhanden sein)
20. `blender -b viertel_v06.blend --python scripts/phase4/build_phase4.py -- --version 07 --nur Konsistenz` → viertel_v07.blend
21. `blender -b viertel_v07.blend --python scripts/phase3/render_nah.py -- --prefix phase4 --nur konsistenz_auto,konsistenz_panzer,konsistenz_baum_fassade,konsistenz_wandfuss`; Hero-Kameras: `render_blockout.py -- --prefix phase4 --nur CAM_Hero_01,CAM_Hero_02,CAM_Hero_03,CAM_Hero_04,draufsicht` (aus v06, Konsistenz-Änderungen dort nur minimal)
22. Phase 5: `blender -b viertel_v07.blend --python scripts/phase5/build_phase5.py -- --version 08` → viertel_v08.blend (Parameter licht.json)
23. `blender -b viertel_v08.blend --python scripts/phase5/render_vorschau.py -- --prefix phase5 --samples 64 --prozent 50 --cpu` → renders/test/phase5_cam1–4.png
24. 5.8: `blender -b viertel_v08.blend --python scripts/phase5/qualitaet.py -- --version 09` (Instanzen, Pfade), dann `build_phase5.py -- --version 09 --nur Licht,Atmosphaere,Compositor` und `--nur Kameras,Atmosphaere`, `qualitaet.py -- --version 09 --nur Ansicht,Pfade`
25. Panzer: `blender -b viertel_v09.blend --python scripts/phase3/nacharbeit_militaer.py -- --version 10`, dann auf v10: `build_phase4.py -- --version 10 --nur Konsistenz`, `build_phase5.py -- --version 10 --nur Kameras,Atmosphaere`, `qualitaet.py -- --version 10`
26. Vorschau: je Kamera `blender -b viertel_v10.blend --python scripts/phase5/render_vorschau.py -- --prefix phase58 --samples 64 --prozent 50 --cpu --sparsam --nur <1-4>` (CAM 2 und 3 stammen aus v09, dort identisch bis auf den Panzer)
