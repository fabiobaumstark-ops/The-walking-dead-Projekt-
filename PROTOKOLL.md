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

## Phase 2b – Detail-Ausbau (Feedback 2026-11-04)
- Nutzer: „zu wenig Details, Moos fehlt“, „viel zu wenig Details“.
- Entscheidung des Nutzers: 1C + Moos jetzt, 2 alle Bereiche, 3B mehr Details am Checkpoint.
- Annahme (dem Nutzer mitgeteilt): „Moos und so“ = Moos, Flechten, Laub und kleine Grasbüschel in Rissen und Fugen. Bäume, Büsche, Ranken und Kudzu bleiben in Phase 4.
- Referenzbild vom Nutzer: Konzeptkunst einer überwucherten Stadt (Signatur unten links, vermutlich aus einem Videospiel – unsicher).
  Wird nur als Stimmungsreferenz genutzt, nicht nachgebaut und nicht gespeichert.
- Entscheidungen: 1A Zeitspanne 10–15 Jahre und stark überwuchert (AUFTRAG A14, LOOK_BIBLE v1.1), 2A große Vegetation in Phase 4, 3 Flair + Boden übernehmen.
- Folgen:
  - Boden jetzt: Erdschichten, Matsch, Moos auf dem Asphalt, aufgebrochene Platten, ausgetretener Pfad
  - stärkere Verwitterung (verw_master 0,85 → 1,0, mehr Rost/Moos)
  - in Phase 3 stärker verrostete Fahrzeuge
- Boden (scripts/phase2/boden.py + scripts/configs/boden.json):
  - Erdschicht und Moosflächen über Fahrbahn, Gehweg und Gasse, mit weichen Rändern über das Attribut „deckung“
  - in der Fahrbahnmitte ein geschwungener Trampelpfad (1,8 m) frei
  - 5 Felder mit aufgebrochenen Asphaltschollen
  - Erste Abdeckung war zu niedrig (kaum sichtbar) → Grundwerte auf ~1,0 erhöht, Alpha-Schwelle 0,16–0,4. Erde dunkler, Moos kräftiger.
- Nutzer-Wunsch „vor allem soll die Stadt so eine Dichte haben“ → Rückfrage gestellt (A Innenstadt verdichten + Skyline / B nur Skyline / C nur Viertel).
- Dichte (Nutzer: Antwort C, keine Skyline):
  - Typ 3 jetzt mit 3–5 Geschossen; Typ 1 höher (B11 4, B12 5, B14 4, B17 5, B20 4, B21 4 – Hubschrauber bleibt im 2. OG, B24 5, B30 5, B38 3)
  - neue Gebäude B39 (Typ 3 zwischen Feuerwache und Büro_1), B40 und B41 (Typ 1, je 5 Geschosse an den Ostenden)
  - Lagerhalle B18 durch Typ-3-Geschäftshaus ersetzt (Typ 8 jetzt 3×: Kirche, Feuerwache, Schule)
  - B22 bis x = 45,5 verbreitert; schmale Durchgänge bleiben bewusst
  - Hauptstraßen-Achse West/Ost im Mittelgrund als geschlossene Innenstadt-Zeilen (3–6 Geschosse) statt Flachbauten

## Phase 2b – Abschluss (2026-11-04)
- viertel_v03.blend (30,6 MB), Aufbau aus Skripten in 69 s.
- Inhalt: 41 Gebäude, 4 718 Schuttteile, 526 Sandsäcke, 3 567 Grasbüschel, 1 875 Moospolster, 90 Laubhaufen.
  Dazu Erdschicht, Moosflächen, Asphaltschollen, Fassaden-Details, Innenraum-Möbel, Hausanschlüsse.
- Renders (CPU, 960 × 540, 48 Samples): CAM 1: 287 s, CAM 2: 234 s, CAM 3: 301 s, CAM 4: 279 s, Draufsicht 117 s.
  Mehr als doppelt so lang wie in Phase 2 (mehr Instanzen und Shader-Ebenen), aber unter der 10-min-Grenze.
  → renders/test/phase2b_cam1–4.png, phase2b_draufsicht.png, phase2b_lageplan(_variante_A).png

### D1-Checkliste Phase 2b
- Maßstab ok
- Nichts schwebt: Schuttkegel aus Einzelteilen liegen auf dem Fuß, Gras/Moos auf der Oberfläche, Erdschicht folgt dem Boden
- Keine Bordstein-Überbrückung durch die Erdschicht
- Keine echten Marken/Orte. Zettel, Plakate und Such-Markierungen nur mit erfundenen allgemeinen Texten
- Offen: Fahrzeuge (Phase 3), große Vegetation (Phase 4), Licht/Dunst (Phase 5)

### D2-Qualitätsbewertung Phase 2b (ehrlich)
| Kriterium | Note | Was verrät CGI / was hilft |
|---|---|---|
| Realismus Geometrie | 7 | Dicht, viele Kleinteile, Schutt aus Einzelteilen. Kugel-Bäume und Auto-Platzhalter fallen auf → Phase 3/4 |
| Realismus Materialien | 6 | Verwitterung jetzt sichtbar (Moos, Flechten, Feuchte, Fahnen). Einige gestrichene Ziegelfassaden wirken blass (B30), die Erde ist noch zu gleichförmig → Phase 4: Gras/Laub auf der Erde, Farbvariation |
| Einheitlicher Look | 6 | Alles läuft über die Bibliothek und MAT_Verwitterung; nur die Platzhalter stechen heraus |
| Licht & Stimmung | 4 | Ohne warmes Gegenlicht, Dunst und Grading noch flach (Phase 5) |
| Komposition | 6 | Die Straßenschluchten wirken jetzt (CAM 1/3). Hauptmotive (Panzer, Hubschrauber, Stau) fehlen noch |
| Glaubwürdigkeit der Geschichte | 7 | Checkpoint mit Lager-Spuren, Barrikaden, Plünderung, Zettel „MISSING“, Such-Markierungen |

## Phase 3 – Start (2026-11-04)
- Phase 2/2b freigegeben („Gut weiter“). AUFTRAG ergänzt um 5.8 Qualitätsrunde nach Phase 5.
- Arbeitsweise Phase 3: allein (kostensparend, einheitlicher Look).
- 3.1.0/3.2 Recherche: recherche/fahrzeuge.md (Maß-Spannen A–H, Sonderfahrzeuge, Epochen, Farben, Alterung), recherche/militaer.md (Kampfpanzer, Hubschrauber, Militär-Lkw).
  - Korrekturen am Auftrag:
    - unbunte Farben ca. 75–80 % statt 60 % (gewählt 70 %)
    - Kastenwagen klassisch 2,15 m statt 2,50 m
    - Militär-Lkw 7,3 m statt 6,7 m
- Neue CC0-Texturen (Poly Haven): poly_wool_herringbone (Sitzstoff), brown_leather (Leder/Kunststoff-Narbung), rusty_metal_04 (Rostblech), rusty_metal_sheet (Rostflecken-Maske).
- Fahrzeug-Baukasten v1 (scripts/phase3/):
  - Karosserie als Loft aus Querschnitt-Ringen (Profile in fahrzeuge.json)
  - Flächen werden per Regel Bauteilen zugeordnet
  - 5-mm-Spalte zwischen verschiedenen Bauteilen
  - Scheiben 5 mm, Türen mit Scharnier-Drehpunkt
  - Leuchten/Grill per Raycast-Patch auf der Oberfläche
  - Testläufe: Kappen-Normalen waren invertiert (schwarze Front), Scheinwerfer-Oberkante falsch, Spiegel innen → behoben
- Vorschau-Iteration 2–3 (Testläufe in niedriger Auflösung):
  - F (Kleinwagen) wirkte wie ein Mini-Van → neues Profil: abfallendes Dach, schrägere Heckklappe, H 1,50 m
  - B (Kompakt-SUV) wirkte wie ein Kombi → Gürtellinie +4–5 cm (kleinere Fenster), Radlauf-Leisten statt treppiger Verkleidung
  - Pickup: Kabinen-Heckfenster ergänzt, Rücklichter an den Bordwand-Enden, Kennzeichen-Ausrichtung korrigiert
  - Kastenwagen: Fenster in den Hecktüren
  - Stoßstangen und Seitenleisten als durchgehende Profile (vorher sichtbare Segmente)
  - Sitze als Polster mit Seitenwangen; Vorzeichenfehler behoben (Lehnen neigten nach vorne)
  - Armaturenbrett mit Seitenprofil
  - Kantenverschleiß am Lack = Grundierung statt Rost (Rost nur über eigene Maske unten); Innenraum ohne Moos/Flechten
  - Je Typ 2–3 Front-/Heck-Varianten in fahrzeuge.json (für die Flotte)

## Phase 3 – Fahrzeuge, Militär & Figuren (2026-11-04)
### Ablauf
- Recherche: recherche/fahrzeuge.md, recherche/militaer.md
- Zwischen-Stopp: 8 Grundmodelle, freigegeben („das passt“). Vorschau: renders/test/phase3_grund_*
- Flotte: 38 Fahrzeuge + 5 Sonderfahrzeuge (scripts/configs/flotte.json)
  - Stau: 12 + 1 auf dem Gehweg
  - Unfallkette: 6, davon 1 ausgebrannt, 1 auf der Seite, 1 auf dem Dach
  - SUV am Strommast: 1
  - geparkt: 8
  - Plünderung: 2 (Kombi mit Kartons, Limousine auf Ziegeln)
  - Tankstelle: 3
  - Polizeisperre: 2 (schwarz-weiß, Lichtbalken, generisch „POLICE“)
  - Barrikade 1: 2 (ersetzen die Platzhalter)
  - Sonderfahrzeuge: Schulbus, Sattelzug (Auflieger umgekippt, Ladung verstreut), Rettungswagen mit Trage, 2 Militär-Lkw
- Schäden per Seed (fz_schaden.py):
  - platte Reifen, fehlende Räder, Glas (gesprungen/zerbrochen/fehlt)
  - Türen, Hauben und Klappen offen, Dellen, ausgebrannt
- Detailstufen: nah (< 20 m) voll; mittel (20–60 m) ohne Unterboden; fern (> 60 m) zu einem Mesh zusammengefasst
- Panzer A: Hauptstraße, Turm 22°, rechte Kette abgesprungen, Schürzen teils fehlend/verbogen, Staukorb mit Ladung und Busch, Pfütze
- Panzer B: in B17 gefahren
  - vorne 7° angehoben, Rohr 24° hoch, Front unter Schutt
  - Mauerdurchbruch als Boolean-Modifier am Phase-2-Gebäude B17 (nicht zerstörend, Modifier „Panzer_B_Durchbruch“)
- Hubschrauber: im 2. OG von B21 (Loch aus Phase 2)
  - Heckausleger abgeknickt, Heckrotor am Boden
  - Blätter: eines am Kopf, zwei auf der Straße, eines in der Parkhaus-Fassade
  - Trümmerfeld, Ruß an der Fassade
- Figuren: 27 aus 12 Vorlagen (MPFB 2 + MakeHuman-Systemassets CC0)
  - 8 Posen, kein Blut
  - Abstand ≥ 12 m zu allen Hero-Kameras
- Dateigröße: viertel_v04.blend 70,7 MB (Freigabe B: eine große Datei). v02 entfernt.

### Gefundene und behobene Fehler
- Scheinwerfer-Oberkante falsch, Kappen-Normalen invertiert (schwarze Front)
- Spiegel innen, Rückenlehnen nach vorne geneigt
- Fern-LOD-Absturz: Materialien der ausgewerteten Kopien übernommen → Originale verwenden
- Barrikaden-Neubau brauchte den Zustand des Straßenmoduls
- Schulbus verdeckte CAM_Hero_04 → nach Osten verschoben
- Hubschrauber zu tief im Gebäude → 4,5 m herausgezogen
- Glas brach flächenweise (Schachbrett) → scheibenweise
- Figuren zu hell → dunkler
- Posen: Achsen per Testreihe kalibriert

### Renderzeiten (CPU, 960×540, 48 Samples)
- CAM_Hero_01 236 s, CAM_Hero_02 193 s, CAM_Hero_03 263 s, CAM_Hero_04 245 s, Draufsicht 94 s
- Bau der Szene: ca. 14 min (Flotte 5 min, Militär < 1 min, Figuren 8 min)

### D1-Checkliste Phase 3
- [x] Maßstab: Autos 4,1–5,9 m, Figuren 1,55–1,90 m, Bus 11,8 m
- [x] Nichts schwebt: Fahrzeuge stehen auf den 4 Radpunkten (Ebene durch die Radhöhen), Figuren mit tiefstem Punkt auf dem Boden
  - [ ] Einzelfälle prüfe ich in Phase 4 mit Vegetation
- [x] Keine sichtbar gekachelten Texturen
- [x] Keine sauberen Flächen mehr: Autolack mit Schmutzfilm, Dellen, Klarlack-Schäden, Rost
- [x] Kanten gefast (Bevel/Solidify-Ränder)
- [x] Keine falschen Normalen (Kappen korrigiert)
- [ ] Himmel/Schatten: unverändert bis Phase 5
- [x] Komposition: Hauptmotive jetzt vorhanden (Panzer A links, Stau in die Tiefe, Hubschrauber oben rechts in CAM 1)
- [x] Look-Bible: Farben ausgeblichen, Rost, Moos auf waagerechten Flächen
- [~] Selbst gebaut vs. heruntergeladen: nach der Korrektur meist nicht mehr auffällig; der Panzerturm wirkt aus der Nähe noch etwas glatt (Einschätzung)
- [x] Kein reales Modell erkennbar, keine Marken/Logos; Reifen, Kennzeichen und Nummern sind erfunden
- [x] Nichts aus Filmen/Serien, kein Blut

### Konsistenz-Test (A10.6): renders/test/phase3_konsistenz_1–4
1. Kombi ↔ Kartons (Scan):
   - vorher auffällig, weil der Lack zu sauber war
   - jetzt mit Schmutzfilm, Schlieren und stärkeren Dellen
2. Militär-Lkw ↔ Kisten und Kanister (Scan): kaum Unterschied.
3. Panzer-Staukorb ↔ Kanister und Busch (Scan):
   - vorher auffällig, weil die Flächen zu glatt waren
   - jetzt mit Zusatzpanzerung, Schrauben, Schweißnähten und feinerer Lackstruktur
4. Figur ↔ geparktes Auto: kaum Unterschied.

### D2-Qualitätsbewertung Phase 3 (ehrlich)
| Kriterium | Note | Was verrät CGI / was hilft |
|---|---|---|
| Realismus Geometrie | 7 | Fahrzeuge mit Spaltmaßen, Leuchten, Innenraum; Panzer mit Laufwerk und Einzelgliedern. Hubschrauber-Rumpf noch recht glatt und einfach; Bäume weiter Kugeln → Phase 4 |
| Realismus Materialien | 6 | Lack, Rost, Glas, Reifen gealtert. Aus der Nähe wirken Karosserien noch etwas „glatt“ (keine echten Beulen), Figurenkleidung von Nahem zu einheitlich → Qualitätsrunde: Beulen per Displacement, mehr Schmutz in Fugen |
| Einheitlicher Look | 7 | Alles läuft über MAT_Verwitterung; der Konsistenz-Test ist nach den Korrekturen weitgehend unauffällig |
| Licht & Stimmung | 4 | Unverändert flach (Phase 5: Gegenlicht, Dunst, Grading) |
| Komposition | 7 | CAM 1 erfüllt die Look-Bible (Panzer links, Stau, Hubschrauber oben rechts). CAM 4 ist durch den hängenden Heckausleger unruhig |
| Glaubwürdigkeit der Geschichte | 8 | Flucht-Stau mit offenen Türen, Unfallkette, Plünderung, verlassene Polizeisperre, Absturz mit Trümmerfeld |

## Lokale Einrichtung Mac (2026-11-05)
- Apple M4 Pro, 12 Kerne, 24 GB RAM, macOS 27.0; Metal-GPU (16 Kerne) erkannt
- Blender 5.2.3 LTS installiert (neben vorhandenem 5.1.0), SHA256 geprüft
- `python3 download_assets.py --nur-basis`: 356 Dateien, 0 Fehler
- Fehler gefunden: 13 Bilder in viertel_v04.blend hatten absolute Cloud-Pfade (Leder, Sitzstoff, Rostblech; Verstoß gegen A3) → auf relativ umgestellt, 0 fehlende Texturen

## Phase 3 – Freigabe und Nacharbeit 2B/3B (2026-11-05, lokal auf dem Mac)
- Freigabe: alle Empfehlungen (1A 2B 3B 4A 5A 6A)
- Neu: scripts/phase3/mil_detail.py, nacharbeit_militaer.py, render_nah.py; Parameter in militaer.json → "detail" (eigener Seed 73, Bau-Seeds unverändert)
- 2B Panzer (Turm + Lack):
  - Turmschale in ein Raster geteilt, 14 Dellen (1,2–3,5 cm) + leichte Welligkeit
  - Lack: dunkle Abplatzer an Kanten und Flächen (Grundierung → Metall → Rost), Schmutz in Ecken, ungleichmäßiges Ausbleichen (±12 %), feine Oberflächenstruktur
- 3B Hubschrauber: 22 Dellen im Rumpfblech (nicht an Fenster-/Türkanten), Blechstöße alle 0,95 m + 3 Längsnähte mit Nietreihen, offene Wartungsklappe an der Triebwerksverkleidung, gleiche Lack-Veredelung
- Hauptbefund: Die hellen Flecken auf Panzer und Hubschrauber kamen aus der Flechten-Ebene von MAT_Verwitterung (auf Lack wirkten sie wie weiße Farbkleckse). Gruppe hat jetzt den Eingang „Flechten“ (Standard 1,0 = alle anderen Materialien unverändert); Militärlack 0,15
- Vorher/Nachher: renders/test/phase3a_* / phase3b_*; Hero-Kameras: phase3b_cam1–4
- Renderzeiten Mac (CPU, 960×540, 48 Samples): CAM 1 38 s, CAM 2 31 s, CAM 3 43 s, CAM 4 45 s; Nahansichten (Metal-GPU, 64 Samples) ca. 50 s
- Dateien: viertel_v05.blend 72,7 MB; viertel_v03.blend aus dem Repo entfernt (A3: aktuelle + letzte Version)
- D2 neu: Realismus Materialien 6 → 7 (keine Farbkleckse mehr, Lack mit Tiefe); Einheitlicher Look 7 → 8. Rest unverändert. Dellen sieht man nur im Streiflicht – wirkt in Phase 5 mit tieferer Sonne stärker

## Phase 4 – Vegetation & Material-Feinschliff (2026-11-06, lokal auf dem Mac)
- Freigabe: 1A Bäume Poly Haven (island_tree_01/02, tree_small_02), 2A eigener Efeu-/Wein-Generator mit ambientCG-Blattfotos, 3A Straßen 60–70 % überwuchert, Pfad 2–3 m frei
- Skripte: scripts/phase4/ (veg_basis, baeume, ranken, bodendecker, material_feinschliff, konsistenz, build_phase4); Parameter in scripts/configs/vegetation.json
- 4.1:
  - Straßen-, Garten-, Platz-, Pionierbäume, ein umgestürzter Baum
  - Hintergrundwald mit ca. 14.800 Instanzen
  - ca. 107.000 Efeu-/Wein-/Kudzu-Büschel
  - Bodendecker mit GN-Grasnarbe; Sichtkegel vor den Hero-Kameras bleibt frei
- 4.2: 37 Pflanzen-Materialien ohne MAT_Verwitterung nachgerüstet, danach 0 ohne
- 4.3 Konsistenz (renders/test/phase4_konsistenz_*):
  - Befund 1: In 2 Nahansichten stand die Kamera im Efeu, das Bild war schwarz. Lösung: render_nah.py dreht die Kamera jetzt, bis die Sicht frei ist.
  - Befund 2: Matratzen und Kartons wirkten wie weiße Klötze. Sie sind jetzt dunkler und gefast; die Klotzform bleibt sichtbar → Qualitätsrunde: durch Scans ersetzen oder neu modellieren.
  - Befund 3: Panzer A wirkt neben Scan-Pflanzen und Figuren kastenförmig. Fasen (3 cm) helfen kaum, das Grundproblem ist die Form → Qualitätsrunde.
  - Flechten auf Fahrzeuglack auf 0,3 gesenkt (17 Materialien)
  - Bäume, Efeu und Gras passen gut zu Gebäuden und Autos.
- Renderzeiten (CPU, 960×540, 48 Samples): CAM 1 86 s, CAM 2 65 s, CAM 3 85 s, CAM 4 72 s, Draufsicht 33 s; Nahansichten Metal-GPU ca. 60–90 s
- Datei: viertel_v07.blend 88,1 MB (Bäume aus assets/models verlinkt); viertel_v05.blend entfernt

### D1-Checkliste Phase 4
- [x] Maßstab: Bäume 7–19 m, Gras 0,3–1,9 m, Büsche in echter Poly-Haven-Größe
- [x] Nichts schwebt: alles per Strahl auf den Boden gesetzt, Ranken auf die Wand
- [x] Keine gekachelten Texturen, Pflanzen mit Farbstreuung je Objekt
- [x] Alle Materialien über MAT_Verwitterung (Ausnahmen: Decals, Wasser)
- [ ] Himmel/Dunst: Hügel über 750 m kahl → Dunst in Phase 5
- [~] Selbst gebaut vs. heruntergeladen: Panzer und Kartons/Matratzen fallen noch auf
- [x] Keine Marken, nichts aus Filmen/Serien

### D2-Qualitätsbewertung Phase 4 (ehrlich)
| Kriterium | Note | Begründung |
|---|---|---|
| Realismus Geometrie | 7 | Bäume/Pflanzen fotoreal; Panzer und Kleinkram zu kastig |
| Realismus Materialien | 7 | Pflanzen-Scans + Verwitterung; Kartons zu flach |
| Einheitlicher Look | 7 | Vegetation verbindet alles; Panzer sticht heraus |
| Licht & Stimmung | 4 | Vorschau-Licht flach, Phase 5 |
| Komposition | 7 | Bewuchs rahmt die Hero-Kameras, Pfad frei |
| Glaubwürdigkeit der Geschichte | 8 | 10–15 Jahre Verwilderung gut lesbar |
- Freigabe (2026-11-09): alle Empfehlungen – 1B Vegetation genau richtig, 2A Panzer-Form → Qualitätsrunde, 3A Farben passen, 4B fast aus einem Guss

## Phase 5 – Licht, Atmosphäre, Kameras, Render-Setup (2026-11-09, lokal auf dem Mac)
- Skripte: scripts/phase5/build_phase5.py (Teile Licht, Atmosphaere, Kameras, Render, Compositor), render_vorschau.py; Parameter scripts/configs/licht.json
- 5.1 Licht:
  - HDRI kloofendal_28d_misty (Stärke 0,9), auf die Sonne ausgerichtet
  - Sonne: Azimut 215° (Südwest), 30° hoch, 4800 K, Winkel 2°, Stärke 4,5
  - Befund: Bei 265° lag die Straße von CAM 1 komplett im Schatten des Bürohauses B09 (Test „nur Sonne“). Mit 215° liegt Licht in der Straße und CAM 3 bekommt Gegenlicht.
  - Feuertonne am Checkpoint: Rostfass, Flamme als Volumen-Emission (2000 K), Punktlicht 260 W mit Flacker-Noise, Rauchfahne
- 5.2 Atmosphäre:
  - Dunst-Volumen 1700 × 1700 × 180 m, Dichte 0,0013 × Höhenabfall (70 m) × Tiefenfaktor (bis 2,4 × in 450 m)
  - Erster Versuch zu dicht (0,0026), „Nebelwand“ in CAM 2 → halbiert
  - 2 Rauchsäulen am Horizont (420/120, 380/−170), vom Wind nach NO geneigt
  - 9 Krähen-Silhouetten am Himmel (CAM 1, 2, 4)
  - Positions-Empties der Rauchsäulen wurden beim ersten Bau mitgelöscht (Präfix) → Aufräumen schließt „_Position“ jetzt aus
- 5.3 Kameras: CAM 1 fokussiert auf Panzer A; CAM 3 auf die vordersten Sandsäcke (Strahl, 2,3 m); Marker Hero_01–04 auf Bild 1–4 binden die Kameras
- 5.4 Render (in der .blend):
  - Cycles GPU, 1920 × 1080, 1024 Samples, Rauschschwelle 0,01, OIDN
  - Bounces 12, Volumen 2, Clamp indirekt 10
  - AgX „Medium High Contrast“
  - Passes Mist, AO, Denoising
  - Ausgabe: EXR-Multilayer `renders/final/hero_##_` + PNG `hero_##_bearbeitet.png`
- 5.5 Compositor (CMP_Look): Mist-Dunst 5 %, Lift kühl / Gain warm, Sättigung 0,96, Fog Glow, Dispersion 0,006, Vignette 22 %, Filmkorn (gepacktes Rauschbild 960 × 540)
- Blender-5.2-Details: Multilayer-EXR über `media_type = MULTI_LAYER_IMAGE`; Compositor als Node-Gruppe (`scene.compositing_node_group`)
- Leistung:
  - Metal-GPU kompiliert die Szenen-Kernel bei jedem Start neu: Mini-Bild GPU 142 s, CPU 20 s → Vorschauen auf CPU (`--cpu`)
  - Für die finalen Bilder bleibt die GPU eingestellt (die Kompilierzeit fällt dann pro Bild kaum ins Gewicht)
  - Ein Vorschau-Render mit GPU und 64 Samples hing über 30 min → abgebrochen
- Renderzeiten Vorschau (CPU, 960 × 540, 64 Samples, mit Dunst): CAM 1 113 s, CAM 2 81 s, CAM 3 106 s, CAM 4 94 s
- Speicher (Teil C): Blender-Prozess ca. 5,5 GB beim Render (Texturen ohne Limit) → passt in einen M4 Pro mit 24 GB
- Datei: viertel_v08.blend 88,2 MB; viertel_v06.blend entfernt (A3)

### D1-Checkliste Phase 5
- [x] Himmel: misty HDRI, brennt nicht aus (AgX)
- [x] Schatten weich, nicht schwarz; Sonne 30°, 4800 K
- [x] Dunst nimmt mit der Tiefe zu, keine Wand mehr
- [~] Rauchsäulen: am Horizont, aber nur schwach sichtbar
- [~] Feuertonne: warmer Lichtakzent da, Flamme selbst zu schwach
- [x] Vertikalen senkrecht (Shift), Brennweiten/Blenden laut 5.3
- [ ] CAM 4: Hubschrauber vor der Fassade statt vor dem Himmel, im Schatten → Komposition offen
- [x] Grading dezent: Schatten kühl, Lichter warm, Korn, Vignette

### D2-Qualitätsbewertung Phase 5 (ehrlich)
| Kriterium | Note | Begründung |
|---|---|---|
| Realismus Geometrie | 7 | unverändert; Panzer/Kleinkram → Qualitätsrunde |
| Realismus Materialien | 7 | unverändert |
| Einheitlicher Look | 8 | ein Licht, ein Dunst, ein Grading verbindet alles |
| Licht & Stimmung | 7 | warme Südwestsonne, Tiefendunst; es fehlen noch Lichtstrahlen |
| Komposition | 6 | CAM 1–3 gut, CAM 4 schwach |
| Glaubwürdigkeit der Geschichte | 8 | Feuertonne, Rauch, Krähen ergänzen die Erzählung |
- Freigabe (2026-11-10): 1A CAM 1 am besten / CAM 4 am schwächsten, 2C Nebel zu schwach, 3A final 1080p, 4B Animation ja, nach der Qualitätsrunde

## Phase 5.8 – Qualitätsrunde, Teil 1 (2026-11-10, Cloud-Sitzung)
- Umgebung: Linux, 4 Kerne, 16 GB RAM, keine GPU; Blender 5.2.3 LTS; Assets neu geladen (MakeHuman-Server sehr langsam, ca. 15 KB/s je Verbindung → in 28 Teilstücken parallel geladen, Größe geprüft)
- Skripte: scripts/phase5/qualitaet.py (Teile Instanzen, Pfade, Ansicht); build_phase5.py erweitert (Bodennebel, Flamme aus licht.json, Kameras mit `neu_setzen`); render_vorschau.py `--sparsam`; viertel_lib.pfade_relativ()
- Befund 1 – Speicher (wichtigster Fund):
  - Die 36 Bäume teilten sich zwar das verlinkte Mesh, Cycles lud sie aber je Objekt einzeln (Material am Objekt statt am Mesh): ca. 24 Mio. Flächen statt 3,7 Mio.
  - Messung (Render ohne Texturen, Spitzenwert): mit allen Bäumen > 14 GB (Abbruch), mit je einem Baum pro Mesh 10,6 GB
  - Lösung: 7 Vorlagen in 00_Prototypen/PROTO_Baum_Instanzen_*, die 36 Bäume sind jetzt Collection-Instanzen (gleicher Name, gleiche Lage) → 19,2 Mio. Flächen weniger, Spitzenwert 11,7 GB
  - Die Angabe „ca. 5,5 GB“ aus Phase 5 (Mac) war zu niedrig; realistisch sind mit Texturen etwa 13–16 GB (Schätzung, auf dem Mac nicht nachgemessen)
- Befund 2 – Datei öffnet auf dem Mac kaum (Meldung des Nutzers): Teil „Ansicht“ – 28 Pflanzen-Generatoren (Gras, Efeu, Wald) nur noch im Render aktiv, 50 schwere Objekte im Fenster als Kästen, Simplify fürs Fenster. Render unverändert. Auf dem Mac noch nicht bestätigt.
- Befund 3 – 12 absolute Mac-Pfade (LeafSet017/024/029, Verstoß A3) → relativ; build_phase4/5 rufen jetzt vor jedem Speichern pfade_relativ() auf
- Nebel (Antwort 2C): Dichte 0,0013 → 0,0017, Tiefenfaktor 1,4 → 2,8 auf 380 m, Anisotropie 0,45 → 0,6, Mist-Anteil im Compositor 5 → 10 %; neu fleckiger Bodennebel (0,006, Abfall 7 m, Flecken 45 m) für Lichtstrahlen
- Feuertonne: Flamme 0,8 m hoch, Emission 14 → 90, Punktlicht 260 → 420 W → in CAM 3 jetzt klar sichtbar. Rauchsäulen: Dichte 0,12 → 0,3, Radius 26 m, dunkler
- CAM 4 neu: Standort (37 / −1,5), Blick nach Westen gegen das Licht auf (30,3 / −5,4), 20 mm, Shift 0,5. Rumpf, Heckausleger, Leitwerk und Rotorblätter stehen als Silhouette vor dem Himmel. 20 statt 28 mm, weil ein quer stehender Bus (x 38–48) den Abstand begrenzt (Hinderniskarte per Strahlen erstellt; 5 getestete Standorte lagen in Fahrzeugen)
- Panzer (2A aus Phase 4): Turm als Keil – Front 42° geneigt, Seiten 15°, Keil-Zusatzpanzerung an den Wangen, Keilblende, Seitenmodule und Staukästen folgen der schrägen Wand, Optik und Nebelwurfbecher versetzt. Militär neu gebaut (nacharbeit_militaer.py), danach Konsistenz (Phase 4.3) und Kameras erneut
- Vorschau in der Cloud nur mit `--sparsam` möglich (Texturen max. 1024 px, Objekte außerhalb des Bildes weggelassen), jede Kamera in einem eigenen Prozess (sonst Speicherabbruch beim Kamerawechsel)
- Renderzeiten Cloud (4 Kerne CPU, 960 × 540, 64 Samples, Dunst): CAM 1 405 s, CAM 2 300 s, CAM 3 385 s, CAM 4 194 s
- Dateien: viertel_v10.blend 89,7 MB (knapp unter dem Ziel 90 MB); v07 und v08 entfernt (A3), Vorversion v09

### D1-Checkliste 5.8 Teil 1
- [x] Dunst nimmt mit der Tiefe stärker zu, Rauchsäule in CAM 1/2 sichtbar
- [x] Feuertonne: Flamme sichtbar, warmer Akzent in CAM 3
- [x] CAM 4: Hubschrauber vor dem Himmel
- [~] CAM 4: Hubschrauber sehr dunkel (reine Silhouette), Details im Rumpf kaum erkennbar
- [~] CAM 3: Sandsäcke im Vordergrund wirken glatt (wenig Gewebestruktur)
- [~] CAM 2: Flachdächer wirken gleichförmig
- [ ] Matratzen/Kartons noch klotzig (nicht bearbeitet)
- [ ] Lichtstrahlen durch Ruinen/Baumkronen in den Vorschauen noch nicht klar erkennbar

### D2-Qualitätsbewertung 5.8 Teil 1 (ehrlich)
| Kriterium | Note | Begründung |
|---|---|---|
| Realismus Geometrie | 7 | Panzerturm besser (Keilform), Kleinkram unverändert |
| Realismus Materialien | 7 | unverändert; Sandsäcke und Dächer fallen auf |
| Einheitlicher Look | 8 | stärkerer Dunst verbindet Vorder- und Hintergrund |
| Licht & Stimmung | 7–8 | Tiefe besser, Flamme wirkt; Lichtstrahlen fehlen noch |
| Komposition | 7 | CAM 4 jetzt mit klarem Motiv vor dem Himmel, aber sehr dunkel |
| Glaubwürdigkeit der Geschichte | 8 | unverändert |
- Ziel 8–9 je Kriterium ist noch nicht erreicht.
