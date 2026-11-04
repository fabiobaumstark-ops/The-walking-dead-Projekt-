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

## Phase 2.3 – Straßenraum (2026-11-04)
- Bibliotheks-Materialien ersetzen das Blockout-Grau an Gelände, Blöcken, Platz, Gasse und Hochstraße.
- Kachel-Vermeidung (zweite gedrehte Abtastung, Noise-Mischung) bei Asphalt, Erde, Gras, Beton, Kies, Laub, Bordstein und Bitumen.
- Feine Fahrbahn (0,25 m) in den Kamerazonen:
  - Absenkungen mit Pfützen (2 mit Öl-Schlieren über Thin Film), nasser Rand
  - 10 Schlaglöcher (Ø 0,4–0,9 m, mit Wasser oder Erde gefüllt), 6 Flickstellen
  - ca. 300 Längs- und Querrisse + Netzriss-Felder; Rissverläufe sind für die Vegetation in Phase 4 gemerkt
- Markierungen: gelbe Doppellinie, Spurlinien gestrichelt 3/9 m, Randlinien, Zebrastreifen mit 0,6-m-Balken, Haltelinien.
  Abplatzer über eine Fotomaske. Gullideckel Ø 60 cm.
- Gehweg: Betonplatten 1,5 × 1,5 m als GN-Instanzen (3 Varianten, gedreht). Neben den Baumscheiben angehoben (2–6 cm) und gekippt.
- Strommasten (10,4 m sichtbar, alle ~35 m):
  - Querträger, Porzellan-Isolatoren, Trafos an jedem 3. Mast, Abspannseile
  - 6 Leitungen je Feld mit Durchhang, 12 % gerissen bis zum Boden; Mast bei x = −25,7 umgeknickt
- Laternen 8 m mit 2-m-Ausleger alle 25 m, 30 % umgeknickt.
- Ampeln: Spannseile diagonal an 4 Masten, Signalgeber mit Unterkante 5,3 m (TDOT-Recherche), einer heruntergefallen.
- Schilder generisch mit erfundenen Straßennamen (MAIN ST, CEDAR ST, BELL ST), teils verbogen: Stop, Tempo 30, Einbahn, Parkverbot, Bus.
- Stadtmöbel:
  - 6 Hydranten (einer umgefahren, mit Kalkspur)
  - Parkuhren, 2 Briefkästen (dunkelgrün, ohne Logo)
  - Zeitungsautomaten mit erfundener Schlagzeile, Bushaltestelle, Fahrradständer mit Rädern
- Korrekturen nach Test:
  - Asphalt dunkler (Wert 0,56–0,58, Verwitterung „Lokal“ 0,25), Staub global auf max. 45 % Deckung
  - Markierungen weniger verwittert, Nassrand rauer (0,28–0,5)
- Renderzeit CAM_Hero_01 (480 × 270, 12 Samples): ~16 s.

## Phase 2.4 – Schutt-Streuung (2026-11-04)
- GN_Schutt_Streuung mit ~1 570 Instanzen. Vorlagen:
  - selbst gebaut: Betonbrocken 5–95 cm (kantig), Ziegel (ganz/halb/gebrochen), Ziegelhaufen, Glasscherben-Felder, Bretter, Papier/Zeitungen (zerknittert), Kleidung, Schuhe, Koffer, Rucksack, Matratzen, Einkaufswagen, Flaschen, heruntergefallene Klimageräte
  - Poly Haven: Karton, rostige Dose, alter Reifen, Müllsack, Mülltonne, 2 Stühle, 2 Kanister
- Verteilung:
  - dichter an Wänden (bis 1,6 m), in Rinnsteinen, in der Gasse und im Kamerabereich (×1,6), außerhalb ×0,35
  - Glas an den gemerkten kaputten Fenstern, 60 Teile je schwer beschädigter Fassade
  - Papier/Plastik zum Wind ausgerichtet (aus SW) und vor windzugewandten Wänden gehäuft
- Kollision: Mindestabstand je Objekt, nichts in Gebäuden, nichts Großes auf der Bordsteinkante, Höhe immer auf der Oberfläche (−6 mm eingebettet).
- Fehler gefunden und behoben: Vorlagen- und Ziel-Collection hießen gleich („Schutt“) → Abhängigkeits-Zyklus, 0 Instanzen. Vorlagen heißen jetzt PROTO_*.
- 18 abgefallene Schildbuchstaben liegen auf dem Gehweg.

## Phase 2.5 – Checkpoint (Variante A, 2026-11-04)
- scripts/phase2/checkpoint.py + scripts/configs/checkpoint.json, Ortsausgang Ost (x 62–78).
- Sandsäcke: 378 Instanzen aus 6 einzeln verformten Vorlagen (1 aufgeplatzt). Im Verband (Lagen 13,5 cm, versetzt), 2 Reihen, 1,1–1,2 m hoch, leicht nach hinten geneigt, Sandkegel davor.
- 8 Jersey-Barrieren (New-Jersey-Profil 0,61/0,81 m, Länge 3,65 m, abgeplatzte Enden, Hebeösen) als Schikane.
- 5 Gabionen 1,37 × 1,06 × 1,0 m mit Gitter (Alpha), Vlies mit Rissen, rieselnde Füllung.
- Concertina Ø 0,95 m als Pyramide 2+1 quer über die Straße, eingerissen und durchhängend, Pfosten alle 3 m; kurzes Stück vor CAM_Hero_03.
- 2 Container 20 ft (einer offen mit Feldbetten und Kisten), 2 Zelte 6 × 5 m (Plane durchhängend, Risse, Abspannseile, Heringe, Betten, Tisch).
- Wachturm 5 m aus Gerüstrohren (Plattform 2,5 m, Sandsäcke, Leiter, zerrissenes Tarnnetz).
- Schranke rot-weiß, Absperrgitter, Scheinwerfer auf Stativ, Generator, Kabeltrommeln.
- Schilder „CHECKPOINT“, „STOP“, „QUARANTINE ZONE / NO ENTRY“.
- Poly Haven: Militärkiste, Holzkiste, 2 Kanister, 2 Fässer (eines als spätere Feuertonne für Phase 5).
- Hinweis für Phase 5: Der Fokus von CAM_Hero_03 sollte auf ~2,5 m (Sandsäcke) statt 4 m liegen.

## Phase 2.6 – Barrikaden (2026-11-04)
- scripts/phase2/barrikaden.py + scripts/configs/barrikaden.json.
- Barrikade 1 (Hauptstraße West, x = −59,5): 2 quergestellte Autos (Platzhalter mit Typ-A-Maßen, werden in Phase 3 ersetzt), Bus-Seitenteil, angelehnte Wellblechtafeln, Paletten, Ketten, halb offenes Maschendraht-Tor.
- Barrikade 2 (Querstraße West, y = −33,5): 45 Teile (Schränke, Türen, Matratzen, Reifenstapel, Bretter, Tische, Sofas), teils eingestürzt, Stacheldraht-Spirale mit Riss.
- Barrikade 3 (Gasse, x = −42,5): Palisade aus Brettern (2,05–2,35 m mit Spitzen), 2 Riegel, 3 Stützbalken mit Keilen, 6 angespitzte Pfähle davor.

## Phase 2 – Hintergrund-Ring A13 (2026-11-04)
- scripts/phase2/hintergrund_ring.py + scripts/configs/hintergrund.json.
- Horizont: Fernring-Gelände von 330 bis 1 600 m mit Hügeln bis 70 m (grobe Wellen + Kuppen/Täler).
  Begründung: 34 m reichten von 32 m Kamerahöhe nicht für eine sichtbar bewegte Horizontlinie (CAM_Hero_02 geprüft).
  Einschätzung: 70 m ist für das Hügelland im Südosten der USA plausibel, aber nicht recherchiert.
- Mittelgrund (80–150 m): 9 weitere Straßenzüge mit einfachen Häusern und Gewerbebauten.
  Fototexturen, dunkle Fensterflächen, 25 % mit eingesunkenen Dächern, keine Innenräume.
- Hintergrund (150–330 m): 120 Silhouetten (Häuser, Hallen, Blöcke bis 8 Geschosse). Zusätzlich 70 Höfe, Scheunen und Hallen auf den Hügeln (340–720 m).
- Landmarken (eigenes Design, ohne Ortsnamen):
  - Wasserturm 28 m + Tank auf 6 Beinen
  - weißer Kirchturm mit Spitze
  - Getreidesilo (3 Zylinder + Elevator)
  - Funkmast 72 m mit Abspannseilen
  - Hochspannungsleitung mit Gittermasten (34 m) und Durchhang
  - Werbetafel am Highway „PECAN PIES / NEXT EXIT 2 MI“ (erfunden, Paneele fehlen)
- Die Hochstraße läuft bis ~520 m nach Norden und Süden weiter, mit Autowracks (Platzhalter bis Phase 3).
- Phase-1-Silhouettenkästen ersetzt. Die Baumgruppen-Platzhalter (Kugeln) bleiben bis Phase 4.
- A13-Prüfung CAM_Hero_02: Der Horizont hat jetzt Hügelwellen, Gebäude, Wasserturm und Silo; keine leeren Stellen mehr.
  Er wirkt aber noch kahl und bräunlich, solange Wälder, Baumreihen und Kudzu (Phase 4) sowie Dunst (Phase 5) fehlen.

## Phase 2 – Abschluss (2026-11-04)
- viertel_v02.blend (20 MB). Aufbau aller Teile aus Skripten in 27 s.
- Renders (CPU 4 Kerne, 960 × 540, 48 Samples): CAM 1: 130 s, CAM 2: 129 s, CAM 3: 154 s, CAM 4: 135 s, Draufsicht (600 × 540): 59 s.
  → renders/test/phase2_cam1–4.png, phase2_draufsicht.png, phase2_lageplan(_variante_A).png
- Korrektur nach Prüfung: Zeitungen kleiner (8–29 cm) und dunkler; vorher waren es zu große, zu weiße Blätter.

### D1-Checkliste Phase 2
- Maßstab ok: Tür 2,1–2,3 m, Geschoss 3,2 m, Bordstein 15 cm, Ampel-Unterkante 5,3 m, Mast 10,4 m
- Nichts schwebt: Schutt auf der Oberfläche, Gehwegplatten im Gehweg, Sandsäcke auf dem Boden
- Kachelung auf Straßen/Böden durch Anti-Tiling stark reduziert. An großen Ziegelwänden ist die Wiederholung aus der Ferne noch leicht erkennbar → Phase 4
- Kanten gefast (Modifier) an Gebäuden, Bordsteinen, Barrieren, Checkpoint
- Kein Z-Fighting gefunden (Dachplatten jetzt innerhalb der Wände)
- Keine echten Marken: Läden, Tankstelle (HARLAN FUEL), Werbetafel und Straßennamen sind erfunden; Wasserturm ohne Ortsnamen
- Nichts aus Filmen/Serien, kein Blut
- Offen: Fahrzeuge/Figuren (Phase 3), Vegetation (Phase 4), Dunst/Grading (Phase 5)

### D2-Qualitätsbewertung Phase 2 (ehrlich)
| Kriterium | Note | Was verrät CGI / was hilft |
|---|---|---|
| Realismus Geometrie | 6 | Gute Fenster, Ladenfronten, Masten, Checkpoint. Aber: Schuttkegel als glatte Hügel, Auto-Platzhalter, Kugel-Bäume, Matratzen zu sauber → Schuttkegel aus Einzelteilen, Phase 3/4 |
| Realismus Materialien | 5 | Fotobasis überall, aber Wände noch zu gleichmäßig. Einige Farbvarianten (rosa Ziegel B30) wirken pastellig, Verwitterung wirkt in Totalen zu schwach → Phase 4: mehr Ruß/Feuchte am Sockel, Ausblühungen, Laub |
| Einheitlicher Look | 6 | Bibliothek + Verwitterung auf allem, Poly-Haven-Props passen. Die Platzhalter fallen auf |
| Licht & Stimmung | 4 | Flaches Dunst-HDRI, ohne Volumen-Dunst, Lichtstrahlen und Grading wirkt das Bild „sauber“ → Phase 5 |
| Komposition | 6 | Ausschnitte tragen, aber Panzer, Hubschrauber und Stau fehlen noch als Hauptmotive → Phase 3 |
| Glaubwürdigkeit der Geschichte | 6 | Checkpoint mit Schikane, Barrikaden, Plünderung, Graffiti, Glas unter Fenstern. Fahrzeuge und Fluchtspuren folgen in Phase 3 |
