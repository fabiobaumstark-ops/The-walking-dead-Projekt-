# Anleitung für zu Hause (Mac)

So renderst du das Viertel auf deinem Mac. Alle Befehle tippst du im **Terminal** ein (Programme → Dienstprogramme → Terminal). Kopiere jeden Befehl einzeln und drücke danach Enter.

## 1. Projekt herunterladen

Einmalig das Projekt holen:

```bash
git clone -b claude/zen-meitner-53hxe1 https://github.com/fabiobaumstark-ops/The-walking-dead-Projekt-.git twd
```

```bash
cd twd
```

Hast du das Projekt schon, holst du den neuesten Stand so:

```bash
git pull
```

## 2. Blender installieren

- **Genau Blender 5.2.3 LTS** von blender.org → Download → „Previous versions“ bzw. „LTS“ (macOS, Apple Silicon).
- In den Ordner Programme ziehen. Andere Versionen können die Datei falsch öffnen.

## 3. Texturen und Modelle laden

Die Bilder liegen nicht im Repo (zu groß). Im Ordner `twd` ausführen:

```bash
python3 download_assets.py --nur-basis
```

Das lädt etwa 1,7 GB nach `assets/`. Mit `python3 download_assets.py --pruefen` kannst du danach kontrollieren, ob alles heil angekommen ist.

## 4. Datei öffnen und GPU einschalten

1. Blender starten → Datei → Öffnen → `twd/viertel_v08.blend` (immer die höchste Nummer nehmen).
2. Bearbeiten → Einstellungen → System → Cycles Render Devices → **Metal** wählen und deinen Mac (M4 Pro) anhaken.
3. Rechts im Eigenschaften-Fenster, Reiter Render (Kamera-Symbol): **Device = GPU Compute** muss eingestellt sein (ist schon gespeichert).

## 5. Die 4 Hero-Shots rendern

Die Zeitleiste ist schon vorbereitet: **Bild 1 = CAM_Hero_01**, Bild 2 = CAM_Hero_02, Bild 3 = CAM_Hero_03, Bild 4 = CAM_Hero_04. Die Marker „Hero_01“ bis „Hero_04“ schalten die Kamera automatisch um.

- **Alle vier auf einmal:** Menü Render → **Render Animation** (Strg+F12 bzw. Cmd+F12).
- **Nur einen Shot:** in der Zeitleiste unten das Bild (1–4) einstellen, dann Render → **Render Image** (F12). Speichern im Renderfenster mit Bild → Speichern unter.

Die Bilder landen in `twd/renders/final/`:
- `hero_01_.exr` … – EXR mit allen Ebenen (Mist, AO …) zum Nachbearbeiten
- `hero_png_0001.png` … – fertig bearbeitetes PNG (Farbe, Dunst, Vignette, Korn)

Auflösung: 1920×1080, bis zu 1024 Samples, Rauschfilter an.

## 6. Wie lange dauert das? (Schätzung!)

Vorschau mit 128 Samples und halber Größe dauerte auf dem M4 Pro etwa 1–3 Minuten pro Bild. Für das finale Bild (vierfache Pixel, mehr Samples, Dunst) schätze ich **etwa 15–40 Minuten pro Hero-Shot**. Das ist nur eine Schätzung – Dunst und viele Pflanzen machen es langsamer. Den Mac dabei am Strom lassen.

## 7. Wenn etwas schiefgeht

- **Rosa/pinke Flächen (Textur fehlt):** Datei → Externe Daten → **Fehlende Dateien suchen** → den Ordner `twd/assets` wählen. Oder Schritt 3 nochmal ausführen.
- **Blender stürzt ab:** Mac neu starten, nur Blender offen lassen. Unter Render → Leistung → „Persistent Data“ ausschalten. Hilft das nicht, unter Render → Light Paths die Volume Bounces auf 1 senken.
- **Speicher voll:** Andere Programme schließen. Im Outliner die Collection `Baeume_Hintergrund` für den Render ausschalten (Kamera-Symbol) – die Hero-Objekte nie.
- **Render zu langsam:** Render → Sampling → Max Samples auf 512 senken oder Noise Threshold auf 0.02. Für einen Test die Auflösung auf 50 % stellen (Ausgabe-Reiter).

## 8. Figuren durch fertige Charaktere ersetzen

Die Figuren liegen in der Collection **09_Figuren**:
- Namen: `FIG_<Gruppe>_<Nr>` bzw. `FIG_Einzeln_<Name>`
- Es sind verlinkte Kopien von 12 Vorlagen in `00_Prototypen/PROTO_Figuren_Vorlagen` (gebackene Meshes ohne Rig).

Eine einzelne Figur tauschen:
1. Den eigenen Charakter importieren (Datei → Importieren, z. B. FBX). Ursprung zwischen die Füße setzen, Blickrichtung −Y.
2. Die alte Figur auswählen, Position und Drehung im N-Panel (Taste N) ablesen und beim neuen Charakter eintragen.
   - Oder in der Python-Konsole: `neu.matrix_world = alt.matrix_world.copy()`
3. Die alte Figur löschen, die neue in die Collection 09_Figuren legen.

Eine ganze Vorlage für alle ihre Kopien tauschen: im Objekt-Datenreiter das Mesh der Vorlage durch das neue Mesh ersetzen – alle Kopien übernehmen es automatisch.

Damit der Charakter zum Look passt: im Material die Gruppe **MAT_Verwitterung** (Shift+A → Gruppe) zwischen Farbe und Principled BSDF einhängen.

Figuren neu erzeugen: in `scripts/configs/figuren.json` Vorlagen, Gruppen und Positionen ändern, dann Phase 3 neu bauen (`scripts/phase3/build_phase3.py`). Dafür müssen das Blender-Add-on MPFB 2 und die MakeHuman-Systemassets installiert sein (lädt `download_assets.py`).

## 9. Verwitterung zentral stärker oder schwächer machen

Eigenschaften-Fenster → Reiter **Szene** → unten „Benutzerdefinierte Eigenschaften“:
- `verw_master` – alles zusammen (1,0 = normal, 0 = neu, 2 = sehr alt)
- `verw_staub`, `verw_schmutz`, `verw_kanten`, `verw_wasser`, `verw_moos`, `verw_bleich`, `verw_flechten` – einzelne Ebenen

Die Werte wirken sofort auf alle Materialien.

## 10. Generator-Werte ändern und neu erzeugen

Alle Zahlen stehen in `scripts/configs/` (JSON-Dateien, mit jedem Texteditor bearbeitbar), z. B.:
- `vegetation.json` – Bäume, Efeu, Gras
- `licht.json` – Sonne, Dunst, Rauch, Compositor
- `kameras.json` – Hero-Kameras

Danach den passenden Teil neu bauen, z. B. Licht und Dunst:

```bash
/Applications/Blender-5.2.3.app/Contents/MacOS/Blender -b viertel_v08.blend --python scripts/phase5/build_phase5.py -- --version 09 --nur Licht,Atmosphaere
```

Die Reihenfolge aller Skripte steht in `UEBERGABE.md` unter „Ausgeführte Skripte“.

## 11. Mit Claude Code weitermachen

Im Ordner `twd` Claude Code starten und schreiben:

> Lies AUFTRAG.md und UEBERGABE.md und mach weiter.
