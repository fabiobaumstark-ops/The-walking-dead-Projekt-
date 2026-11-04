# LOOK BIBLE – verbindlicher Stil-Leitfaden

**Status: v1.1 (2026-11-04)** – v1.0 bestätigt. Änderung laut Nutzer: Zeitspanne 10–15 Jahre, stark überwuchert, Flair und Boden wie Referenz (siehe AUFTRAG A14).

## Freigegebene Grundentscheidungen
| # | Thema | Entscheidung |
|---|---|---|
| 1 | Region/Baustil | US-Süden: Ziegel-Main-Street + Holzhäuser mit Veranden |
| 2 | Jahreszeit | Spätsommer (Ende August): grün, dicht, heiß |
| 3 | Tageszeit & Wetter | Spätnachmittag, Sonne bricht durch Dunst und Wolken |
| 4 | Zerstörung | gemischt: überwiegend verfallen, Zerstörung nur an bestimmten Stellen (Verteilung 30 % leicht / 40 % mittel / 30 % schwer); nach 10–15 Jahren mehr Dacheinstürze und starker Rost |
| 5 | Vegetation | **stark überwuchert** (Änderung v1.1): Fassaden voller Ranken, Straßen großteils mit Erde und Grün bedeckt, ausgetretener Weg in der Mitte |
| 6 | Farbstimmung | warm-staubig mit leichtem Gelb-Grün-Stich |
| 7 | Militär-Epoche | generisch modern (keine Kopie eines realen Modells) |
| 8 | Figuren | einzelne Gruppen (3–4 Gruppen + Einzelne, 25–40 gesamt) |
| 9 | Figuren-Methode | MPFB 2 + CC0-System-Assets |
| 10 | Hero-Shots | bleiben wie im Auftrag (5.3) |
| 11 | Animation | später entscheiden |

## Stimmung (3 Sätze)
Eine Südstaaten-Kleinstadt gut zehn Jahre nach dem Zusammenbruch: still, schwül und schwer, als hätte die Zeit die Luft angehalten. Das Grün ist zurück und überzieht die Spuren einer überstürzten Flucht: offene Autotüren, Sperren, die nichts aufgehalten haben, ein abgestürzter Hubschrauber. Alles wirkt wie ein echtes, leicht ausgebleichtes Filmstandbild, nicht wie ein Spiel: entsättigt, staubig, ehrlich.

## Farbpalette (sRGB-Hex, Basisfarben vor dem Licht)
| Element | Hex | Änderung zum Auftrag |
|---|---|---|
| Himmel/Dunst | `#A7ADB0` | – |
| Asphalt trocken (gealtert) | `#5E5C58` | **heller als `#3A3A38`**: gealterter Asphalt hat eine Albedo von ca. 0,12 (LBNL), `#3A3A38` entspricht frischem Asphalt |
| Asphalt nass | `#2A2A29` | etwas heller als `#1F2020`, damit er nicht schwarz absäuft [E] |
| Beton | `#8A877F` | – (Albedo ca. 0,25, passt zu 0,18–0,35) |
| Ziegel verblasst | `#8C5A45` | – |
| Holz verwittert | `#8B8478` | – |
| Rost hell / dunkel | `#A0522D` / `#4A2A18` | – |
| Moos | `#4F5A2A` | – |
| Trockenes Gras | `#9C8F5E` | – |
| Grünes Unkraut | `#5E6B34` | – |
| Kudzu/Laub sattgrün (neu) | `#4A5A2C` | neu, für üppiges Süd-Grün, bleibt entsättigt |
| Tarnfarbe verblasst | `#5C5F45` | – |
| Staub | `#9A9284` | – |
| Feuerlicht | `#FF9A4D` | – |
Regel: Keine Fläche ist gesättigter als das grüne Unkraut. Reines Weiß und reines Schwarz gibt es nicht.

## Licht (freigegeben: Spätnachmittag, Sonne durch Dunst/Wolken)
- **Tageszeit:** später Nachmittag (ca. 17–18 Uhr Ende August)
- **Wetter:** schwül-dunstig, aufgelockerte Haufenwolken, im Hintergrund Gewittertürme. Die Sonne bricht stellenweise durch.
- **Sonne:** 20–30° über dem Horizont, Winkel 1,5–2,5° (weiche Schattenkante), ca. 4800 K
- **HDRI-Kandidaten (Poly Haven, CC0):** `abandoned_tank_farm_01/02` (urban, nachmittags, 16K), `abandoned_parking` (urban, 16K), `quarry_cloudy` (20K, geringer Kontrast)
- **Dunst:** zunehmend mit der Tiefe. Ab ca. 150 m werden die Silhouetten deutlich blasser, der Horizont versinkt im Dunst.

## Zustand nach 10–15 Jahren (v1.1)
- **Verrostet:**
  - Autos an Schwellern, Radläufen und Kanten
  - Ketten und Laufrollen der Panzer
  - Blech, Geländer, Feuertreppen, Schrauben
  - verbrannte Fahrzeuge komplett
- **Verblasst:**
  - Autolack, besonders Dach und Haube; Rot am stärksten
  - Markisen, Schilder, Tarnfarbe, Plastik (kreidig)
- **Bewachsen:**
  - Fugen und Risse
  - Grünstreifen und Vorgärten (hüfthoch)
  - ca. 40 % der Fassaden mit Ranken
  - Pioniergehölze 2–5 m
  - Kudzu-Decken am Stadtrand
- **Eingestürzt:**
  - Dächer einzelner Holzhäuser
  - die Parkhaus-Ecke
  - Teile schwer beschädigter Häuser
  - das Brückensegment
  - **nicht** flächendeckend: das meiste steht noch.
- **Glas:** Viele Scheiben fehlen. Intakte Scheiben sind staubig und milchig.
- **Holz:** grau, Farbe in Schollen abgeblättert, an Unterkanten faul.

## Einheitlicher Look – Projektregeln (zu Teil A10)
1. Jede Oberfläche bekommt eine Poly-Haven- oder ambientCG-Fototextur (CC0) **+ `MAT_Verwitterung`**. Selbst gebaute Objekte haben keine Farbe ohne Fotobasis.
2. Master-Verwitterung Standard = 0,7. Die Ebenen Staub, Schmutz unten, Kanten, Wasserläufer, Moos und Ausbleichen sind einzeln regelbar.
3. Staubfarbe = `#9A9284` auf allen nach oben zeigenden Flächen. Schmutz unten 0–80 cm in Erdbraun.
4. Texeldichte: 1024 px/m im Nahbereich, 512 px/m im Mittelbereich. Kantenfase 1–3 cm bei allem Harten.
5. Alles steht im Boden: Kontaktschatten (AO), Laub und Erde am Fuß, Gras drumherum.
6. Ein Licht, ein Nebel, ein Grading für alles. Keine Extra-Lichter für einzelne Objekte.
7. Heruntergeladene Modelle werden in Farbe an die Palette angeglichen und gealtert.

## So sieht es aus (10)
1. Schwüler Dunst, der die Tiefe schluckt
2. Gras in jeder Fuge, Laub in jeder Ecke
3. Lack ausgeblichen und fleckig matt
4. Rostläufer unter Blech und Schrauben
5. Offene Autotüren, Gepäck auf der Straße
6. Ranken an Masten, Leitungen und Fassaden
7. Dunkle Fensterhöhlen, dahinter erkennbare Räume
8. Weiche Schatten, die nie schwarz sind
9. Feines Filmkorn, leicht gelb-grünes, entsättigtes Grading
10. Figuren klein in der Ferne, halb im Dunst

## So sieht es NICHT aus (10)
1. Kein knalliges, gesättigtes Grün und kein blauer Himmel wie auf einer Postkarte
2. Keine perfekt sauberen oder gleichfarbigen Flächen
3. Keine identischen Autos oder Häuser nebeneinander
4. Kein Kriegsgebiet mit Bombenkratern überall
5. Kein geschlossener Wald mitten auf der Fahrbahn (Bäume nur an Rändern, Rissen und im Schutt; die Mitte bleibt als Trampelpfad offen)
6. Kein Nebel wie eine Wand, keine übertriebenen Lichtstrahlen
7. Kein Blut, keine Wunden, keine Leichen
8. Keine echten Marken, Logos, Kennzeichen oder Hoheitszeichen
9. Nichts aus Filmen, Serien oder Spielen
10. Kein Spiel- oder Comic-Look (keine überzeichneten Kanten, kein Bloom-Glühen)

## Lageplan (Entwurf, ca. 300 × 300 m, Hauptbereich 120 × 120 m)
```
 N ↑                Hintergrund: Wald + Kudzu, ferne Silhouetten, Rauchsäule
   ┌───────────────────────────────────────────────────────────────┐
   │  Krankenhaus (6 Geschosse)        eingestürzte Hochstraße ════╗ │
   │      Zelte/Rettungswagen          ║ Pfeiler alle 30 m          ║ │
   │ ─────── Querstraße 1 (8 m) ───────╫──── Stau Ortsausgang ──→  ║ │
   │ Büro 1 │ Geschäftshäuser (Main St.)│ Büro 2  Parkhaus (Ecke    │ │
   │ (CAM2  │ Diner|Apotheke|Eisenw.|.. │         eingestürzt)      │ │
   │ Dach)  │══ Gasse 4 m (Barrikade 3)═│                           │ │
   │═══════ HAUPTSTRASSE 14 m (4 Spuren) ═══ Kreuzung ═══ Checkpoint ══│
   │  Barrikade 1   Panzer A   Unfallkette   Ampeln       (Container,  │
   │                                                      Sandsäcke)   │
   │ Tankstelle │ Platz 40×40 m (Brunnen) │ Geschäftshaus mit Heli    │ │
   │            │                         │ im 2. OG, Panzer B in Wand│ │
   │ ─────── Querstraße 2 (8 m), Barrikade 2 ──────────────────────── │
   │ Holzhäuser mit Veranden, Vorgärten, Kirche   Schule (Hintergr.)  │
   └───────────────────────────────────────────────────────────────┘
```
Hauptwindrichtung (Laub und Papier): aus Südwest. **[E]** Im Spätsommer im Südosten der USA plausibel, aber nicht recherchiert.
Die Positionen von Panzern, Hubschrauber, Checkpoint, Barrikaden, Stau und Unfallkette sind vorläufig und werden in Phase 1 (Frage 4) festgelegt.

## Die 4 Hero-Shots (laut Auftrag 5.3)
1. **CAM_Hero_01 „Die Straße“:**
   - 1,7 m Höhe, 35 mm, f/4
   - Panzer A im linken Drittel
   - der Stau führt in die Tiefe zum Checkpoint
   - Hubschrauber oben rechts
   - Figuren im Dunst
2. **CAM_Hero_02 „Überblick“:**
   - Dach eines Bürogebäudes (~30 m), 24 mm, f/8
   - ganzes Viertel bis zur Hochstraße
   - Rauchsäulen am Horizont
3. **CAM_Hero_03 „Checkpoint“:**
   - 1,5 m Höhe, 50 mm, f/2.8
   - Sandsäcke und Draht scharf im Vordergrund
   - Figuren unscharf im Dunst
   - Feuertonne als warmer Akzent
4. **CAM_Hero_04 „Absturz“:**
   - von unten, 28 mm, f/5.6
   - Rumpf und hängender Heckausleger vor dem Wolkenhimmel
   - Rotorblatt im Vordergrund

## Ergänzung v1.1 – Referenz-Flair des Nutzers (nur Stimmung, nichts nachbauen)
- Licht: tiefe, warme Sonne im Gegenlicht, heller Dunst schluckt die Tiefe, Lichtstrahlen zwischen den Häusern.
- Boden:
  - Asphalt großflächig unter Erde, Matsch, Moos und Gras verschwunden, aufgebrochene Platten
  - Pfützen, ein ausgetretener Pfad in der Fahrbahnmitte
- Vegetation:
  - Efeu und wilder Wein über ganze Fassaden
  - hohe Gräser, Büsche, Farne, Blumen (vereinzelt rote/gelbe Blüten), junge Bäume 6–12 m
- Qualität: Pflanzen müssen nah vor der Kamera fotoreal wirken (echte Modelle, Detail, Variation).
