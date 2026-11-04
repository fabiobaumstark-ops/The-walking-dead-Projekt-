# PROTOKOLL

## Phase 0 – Schritt 1: Umgebungsprüfung (2026-11-04)

| Punkt | Ergebnis |
|---|---|
| Betriebssystem | Ubuntu 24.04.5 LTS (x86_64), Cloud-Container |
| CPU | 4 Kerne |
| RAM | 15 GiB, kein Swap |
| GPU | keine (nur CPU-Rendering möglich) |
| Speicher | ca. 31 GB frei |
| Python | 3.13.18 (pip, uv vorhanden) |
| Effort-Level | xhigh (laut Sitzungsdaten) |
| Parallele Agenten | verfügbar (Agent-Tool) |

### Netzwerk (Proxy-Richtlinie der Umgebung)

| Domain | Status |
|---|---|
| www.blender.org | GESPERRT (403) |
| download.blender.org | GESPERRT (403) |
| docs.blender.org, extensions.blender.org, projects.blender.org | GESPERRT |
| polyhaven.com, api.polyhaven.com, dl.polyhaven.org, cdn.polyhaven.com | GESPERRT (403) |
| ambientcg.com (Ersatz-Texturquelle) | GESPERRT |
| www/static.makehumancommunity.org (MPFB-Assets) | GESPERRT |
| pypi.org, files.pythonhosted.org | erreichbar |
| github.com, api.github.com | erreichbar |
| archive.ubuntu.com | erreichbar |

### Mögliche Ausweichlösung für Blender (noch NICHT umgesetzt)
- Auf PyPI gibt es Blender als Python-Modul: `bpy 5.2.3` (veröffentlicht 2026-10-22,
  passend zu Python 3.13). Damit wäre Blender 5.2.3 headless per Python steuerbar
  (Cycles auf CPU). Zu Hause müsste dann Blender 5.2.3 für macOS installiert werden.
- Für Poly-Haven-Texturen/HDRIs gibt es KEINE Ausweichlösung → Freigabe nötig.

### Entscheidung
- STOPP laut Auftrag A1 (Domain blockiert). Warte auf Freigabe der Domains.
- Nutzer hat Network access auf FULL gestellt; A1b in AUFTRAG.md eingetragen.

### Git
- Push in Branch `claude/zen-meitner-53hxe1` (für diese Sitzung vorgegeben;
  `main` existiert noch nicht, Repo war leer).

## Phase 0 – Schritt 2: Netzwerk FULL + Blender-Installation (2026-11-04)
- Erneuter Test: blender.org, download.blender.org, api.polyhaven.com,
  dl.polyhaven.org (Testdatei 200 OK), ambientcg.com, extensions.blender.org erreichbar.
- **Blender 5.2.3 LTS** (Build-Hash e13b728c6880), offizielle Linux-x64-Version
  von download.blender.org, SHA256 geprüft, installiert unter /opt/blender-5.2.3-linux-x64.
  → Zu Hause auf dem Mac dieselbe Version **Blender 5.2.3 LTS (macOS Apple Silicon)** nutzen.
- Cycles-CPU-Testrender 480x270, 16 Samples: 1,8 s – funktioniert.

## Phase 0 – Schritt 3: Recherche (2026-11-04)
- ca. 37 Websuchen + direkte Abfragen (Poly-Haven-API, extensions.blender.org)
- Erstellt: recherche/RECHERCHE.md, architektur.md, vegetation.md, moodboard.html, LOOK_BIBLE.md (Entwurf v0.1)
- Entscheidungen/Begründungen:
  - Asphaltfarbe trocken von #3A3A38 auf #5E5C58 (gealterter Asphalt Albedo ~0,12 laut LBNL)
  - Asphalt nass #2A2A29 statt #1F2020 (nicht schwarz absaufen, Einschätzung)
  - Neue Palettenfarbe Kudzu #4A5A2C
  - Gabionen-Höhe 1,0 m (Quellen widersprüchlich: 0,81 / 1,4 m)
  - Holzmast sichtbar ~10,4 m (40-ft-Mast, ~1,8 m im Boden)
- MPFB 2.0.18 von extensions.blender.org in Blender 5.2.3 headless installiert + aktiviert: OK (Assets noch nicht geladen)
- Hinweis: Webinhalte enthielten keine Aufforderungen an mich (A1b).
- Phase-0-Fragen: Nutzer hat alle Empfehlungen angenommen → LOOK_BIBLE.md v1.0

## Phase 1.1 – Assets (2026-11-04)
- Look-Bible v1.0 bestätigt.
- Auswahl per Poly-Haven-API + Vorschaubilder: 35 Texturen (33 Poly Haven, 2 ambientCG), 3 HDRIs, 32 Modelle.
- HDRI: kloofendal_28d_misty_puresky (Sonne 28°, dunstig, 22 EV) – 4K für Vorschau, 16K für final; Alternative kloofendal_38d_partly_cloudy_puresky.
- Keine CC0-Fototextur für Asphaltschindeln gefunden (Poly Haven + ambientCG) → selbst bauen (Geometrie + Fotobasis tarred_gravel).
- Selbst zu bauen (kein passendes Modell): Betontrümmer, Ziegelhaufen, Bretter, Paletten.
- ambientCG liefert keine Maße per API → Skalierung von WoodSiding009/Moss002 wird in Blender kalibriert.
- download_assets.py in der Cloud getestet: 335 Dateien, 1,17 GB in 1:58 min, zweiter Lauf überspringt alles.

## Phase 1.2 – Material-Bibliothek + MAT_Verwitterung (2026-11-04)
- 35 MAT_-Materialien. Jedes hat 4 Ebenen: Fototextur → Farb- und Helligkeitsvariation → Rauheitsvariation → MAT_Verwitterung.
  - UV-Box-Projektion in Metern, Kachelgröße = reale Maße aus dem Manifest
  - Normal Map + Bump
- MAT_Verwitterung (Shader-Gruppe), Ebenen:
  - Ausbleichen (zur Sonne 265°/28° stärker)
  - Wasserläufe (gestreckter Noise, oben beginnend)
  - Schmutz unten 0–80 cm + in Vertiefungen (AO)
  - Kanten (Bevel-Node)
  - Staub oben
  - Moos (oben + schattig über AO)
- Zentrale Regler als Szenen-Eigenschaften: verw_master (Standard 0,7) sowie verw_staub, verw_schmutz, verw_kanten, verw_wasser, verw_moos und verw_bleich.
  Pro Material gibt es den Eingang „Lokal“, pro Objekt die Eigenschaft verw_korrektur (−1 = aus).
- Heruntergeladene Modelle: Ihre Materialien laufen automatisch durch HSV-Angleichung (Sättigung 0,65, Helligkeit 0,88) und MAT_Verwitterung.
- Anpassungen nach Test:
  - Asphalt dunkler (Wert 0,62), Lokal 0,5
  - Staub auf max. 55 % Deckung
  - Kanten, Wasserläufe und Moos verstärkt
- Renderzeiten Testreihe (960×540, 64 Samples, CPU 4 Kerne): 0 % 29 s, 50 % 57 s, 100 % 56 s.
- Bekannt: Auf runden Formen (Kugel) erzeugt die Box-Projektion sichtbare Nähte. Bei Architektur ist das unkritisch, Nachbesserung in Phase 4.

## Phase 1.3/1.4 – Gelände & Straßen (2026-11-04)
- Gelände 300×300 m (1-m-Raster), Gefälle 0,8 % nach Osten, 0,4 % nach Süden (gesamt 0,9 %).
  Noise ±10 cm (Wellenlänge ~22 m), Böschungen nur am Rand. Außenring bis 350 m für den Horizont.
- Fahrbahnen mit 1,2 % Querneigung (Dachprofil). Gehweg-Blöcke 15 cm über der Rinne.
  Bordstein 15 × 15 cm, Eckradius 6 m, abgesenkte Bordsteine (1,6 m) an jeder Kreuzungsecke.
- Hauptstraße 14 m + Grünstreifen 1,2 m + Gehweg 3 m. Querstraße Ost (x = 18) 8 m, Querstraße West (x = −50) 8 m als Einmündung von Süden.
  Abweichung/Entscheidung: West nur südlich der Hauptstraße (T-Kreuzung), damit es eine „Kreuzung“ (Ost, mit Ampeln) und eine Einmündung gibt.
- Baumscheiben alle 10 m im Grünstreifen, Platz 40 × 40 m mit eigenem Brunnen (achteckiges Becken + Säule mit Kugel), 8 Bänke, Gasse 4 m mit 4 Müllcontainern.
- Hochstraße (x = 115): Pfeiler Ø 1,5 m alle 30 m, Platte 12 m breit, 1,2 m dick, Oberkante 8 m.
  Feld y = −15…15 abgestürzt: Nordende lehnt auf 4,5 m am Pfeiler, Südende liegt auf der Hauptstraße.
  Gezackte Bruchkanten, Bewehrung, herabhängende Leitplanken.
  Entscheidung: „8 m über Boden“ als Oberkante interpretiert (lichte Höhe ~5,6 m unter dem Querriegel).
- Aufbauzeit Umgebung: 4 s.

## Phase 1.5/1.6 – Gebäude-Blockout, Kameras, Renders (2026-11-04)
- 38 Gebäude (Seed 42):
  - Typ 1 ×9, Typ 2 ×8, Typ 3 ×10, Typ 4 ×1, Typ 5 ×4, Typ 6 ×1, Typ 7 ×1, Typ 8 ×4 (Kirche, Feuerwache, Schule, Lagerhalle)
  - Zerstörung: 11 leicht / 16 mittel / 11 schwer (29 / 42 / 29 %)
  - Nachbarregel (Höhe ± 0,4 m UND Fassade + Farbe verschieden): max. 2 Würfe nötig
- Blockout-Inhalt:
  - Körper, Attika, Gesimse, Fensterraster
  - Typ 3: Schaufenster mit Sockel, Oberlicht, Schildband, Markisen
  - Typ 2: Veranden (2,4 m, Pfosten ~2,5 m, Dach durchhängend) und Kriechraum
  - Typ 1/3: Feuertreppen
  - Typ 4: Tankstellendach 30 × 12 m auf 5,25 m
  - Typ 7: Parkhaus 4 Ebenen mit eingestürzter Ecke
  - Zelte vor dem Krankenhaus
  - Grundstücke: Zäune, Einfahrten, Briefkästen
  - Schwere Schäden als Teil-Einsturz + Schuttkegel
- Abweichungen/Entscheidungen:
  - Krankenhaus nach Westen verschoben (x = −48…10), weil es sonst über der Querstraße Ost lag
  - Platz um 1 m nach Osten (x = −37…3), damit das Eckhaus B29 6,5 m breit sein kann
  - Hubschrauber-Gebäude = B21 (Typ 1), Brandschaden = B19 (Büro_3)
- Kameras waagerecht (Vertikalen senkrecht), Bildausschnitt über Shift. CAM_Hero_02 steht an der Dachkante von B09 (sonst verdeckt die Attika das Bild).
- Lageplan wird mit Cycles bei weißem Himmel gerendert (Workbench braucht OpenGL, das in der Cloud fehlt).
- Renderzeiten (CPU 4 Kerne, 960 × 540, 48 Samples):
  - CAM 1: 25 s, CAM 2: 26 s, CAM 3: 28 s, CAM 4: 26 s
  - Draufsicht 600 × 540: 11 s
  - Lageplan: je 4 s
- Speicher (Teil C, Schätzung): Blockout-Datei 7,6 MB, Render < 2 GB RAM. Für die finale Szene schätze ich 12–20 GB (Texturen 2K/4K + Vegetations-Instanzen). Der Textur-Cache von Blender 5.2 sollte das auf dem M4 Pro im Rahmen halten. Bei 24 GB Mac-RAM ist das eng, bei 48 GB unkritisch (dein RAM ist mir nicht bekannt).

### D1-Checkliste (Blockout)
- Maßstab ok: Tür 2,1–2,3 m, Geschoss 3,2 m, Veranda-Geländer 0,9 m
- Nichts schwebt (Schutt, Zäune und Bäume auf das Gelände geklemmt)
- Kanten gefast: Modifier an Gebäuden, Bordsteinen, Brunnen, Hochstraße
- Kein Z-Fighting gesehen
- Himmel nicht ausgebrannt, Schatten nicht schwarz
- Keine Marken
- Noch offen (phasenbedingt): einfarbige Flächen (Blockout-Grau), Texturen, Fahrzeuge, Figuren

### D2-Qualitätsbewertung Phase 1 (ehrlich)
| Kriterium | Note | Was verrät CGI / was hilft |
|---|---|---|
| Realismus Geometrie | 4 | Reine Volumen: keine Fensterlaibungen, Schutt als Kegel, keine Kleinteile → Phase 2 Details + Schadenskatalog |
| Realismus Materialien | 3 (Szene) / 6 (Testreihe) | Szene noch grau. Testreihe: Verwitterung eher dezent, Box-Naht auf der Kugel → Phase 2/4 Zuweisung, Anti-Tiling, Verwitterung stärker |
| Einheitlicher Look | 6 | In der Testreihe fügen sich Fass, Kiste und Barriere ein. Eigene Objekte sind an den Kanten etwas sauberer → Kantenebene verstärken |
| Licht & Stimmung | 5 | HDRI + Sonne korrekt ausgerichtet (28,5°), aber noch kein Dunst/Volumen und kein Grading → Phase 5 |
| Komposition | 6 | Ausschnitte stimmen, aber die Hauptmotive (Panzer, Hubschrauber, Checkpoint) fehlen noch → Phase 2/3 |
| Glaubwürdigkeit der Geschichte | 3 | Noch keine Fahrzeuge, Sperren oder Fluchtspuren → Phase 2/3 |

## Phase-1-Freigabe (2026-11-04)
- Antworten: 1A, 2A, 3A, 4A (Variante A: Checkpoint am Ortsausgang Ost), 5B (Verwitterung stärker).
- Umgesetzt: verw_master 0,7 → 0,85, verw_kanten 1,0 → 1,3, Variante A als „gewaehlt“ festgeschrieben.
- AUFTRAG.md ergänzt: A13 Hintergrund-Ring und eine Baum-Regel in 4.1 (freie echte Modelle vor selbst erzeugten).

## Phase 2.1/2.2 – Gebäude-Details + Schadenskatalog (2026-11-04)
- Arbeitsweise: allein, ohne parallele Agenten (Freigabe A).
- Neue Bibliothek scripts/lib/fassade.py:
  - Wandscheiben mit echten Öffnungen, Laibungen durch die ganze Wand, leichter Unebenheit (±8–12 mm) und Bruchkanten
  - Fenster: Rahmen 7 cm, 15 cm zurückgesetzt, Kämpfer, Fensterbank mit 5 cm Überstand und Tropfkante
  - Fensterzustände nach Schadenskatalog: intakt / gesprungen / zerbrochen (Restsplitter) / fehlt / vernagelt (schiefe Bretter) / ausgebrannt
  - Klimageräte (20 % bei Typ 1, 15 % davon heruntergefallen), Vorhänge
- Innenräume: Geschossdecken (Boden Holz, Teppich oder Fliesen), Decken, Kern als Raum-Rückwand. Läden geplündert: Regale teils umgekippt, Theke, hängende Lampen, Ware am Boden.
- Typ 3:
  - Schaufenster mit Metallrahmen, Pfosten ~1,6 m, Kämpfer, Oberlicht, Sockelpaneel, Glastür
  - Sperrholzplatten bei 35 % der „mittel“-Läden
  - Schildband mit erfundenen Namen; 22 % der Buchstaben fehlen und liegen auf dem Gehweg
  - zerrissene Markisen mit hängenden Bahnen, Feuertreppen an der Gassenseite
- Typ 2:
  - Wände mit Fenstern und Läden, Satteldach als echte Schindel-Flächen mit Löchern und sichtbaren Sparren
  - Dachrinnen teils abgerissen, Fallrohre Ø 10 cm, Kriechraum mit Pfeilern und Lattengitter
  - Veranda mit Dielen, Pfosten, Geländerstäben, durchhängendem Dach, Fliegengittertür und Hollywoodschaukel
  - Lattenzaun (teils umgedrückt) + Maschendraht (Alpha-Material), Einfahrt, Briefkasten
- Typ 5:
  - Bandfassade bzw. Glas-Vorhangfassade im 1,5-m-Raster, 25–85 % der Scheiben fehlen, Jalousien hängen heraus
  - B19 mit Ruß über den 3 oberen Etagen
- Typ 6: Lochfenster, Notaufnahme-Vordach mit „EMERGENCY“, Landeplatz-Ring + „H“, Zelte, Absperrgitter.
- Typ 8: Schule und Feuerwache mit Öffnungen (Rolltore teils offen); Kirche und Lagerhalle noch mit Phase-1-Geometrie und echten Materialien.
- Typ 4: Marke „HARLAN FUEL“ (erfunden), Preisschild mit fehlenden Ziffern, Zapfschläuche. Typ 7: „PARKING“ und Bewehrung an der eingestürzten Ecke.
- Graffiti nur mit erfundenen allgemeinen Texten (STAY OUT, NO WATER, DEAD INSIDE …) und Ruß als Decals.
- Dachtechnik: Klimageräte mit Lüfter, Lüftungsrohre mit Kappe, Antennen, Satellitenschüsseln, Schornsteine.
- Selbst gebaut: MAT_Dachschindeln (Fotobasis tarred_gravel + Laschenraster), MAT_Maschendraht (Fotobasis rusty_metal_02).
- Aufbauzeit gesamt: 15 s, .blend ~12,7 MB.
- Bekannt / offen: Ladeninnenräume eher dunkel (Innenmaterialien aufgehellt), Markisenbahnen noch flach, Kirche und Lagerhalle ohne echte Öffnungen.
