# Unreal-Anleitung (Mac) – Phase 6.1 Pipeline-Test

Ziel dieses Schritts: Ein kleines Stück des Viertels (30 m um den Panzer) kommt nach Unreal. Du prüfst, ob alles richtig herum liegt, und schickst mir das Ergebnis. Erst danach exportiere ich das ganze Viertel.

Alle Befehle im **Terminal** im Ordner `twd`. Jeden Befehl einzeln kopieren und Enter drücken.

## 1. Neuesten Stand holen

```bash
git fetch origin claude/zealous-ride-c12e2z
```

```bash
git checkout claude/zealous-ride-c12e2z
```

```bash
git pull
```

## 2. Unreal Engine 5.8 installieren

1. Den **Epic Games Launcher** von epicgames.com herunterladen und installieren. Dafür brauchst du ein kostenloses Epic-Konto.
2. Im Launcher links **Unreal Engine** → oben **Bibliothek** → beim Plus-Symbol die Version **5.8** auswählen → **Installieren**.
3. Laut Epic braucht Unreal 5.8 mindestens **macOS Sonoma 14.5**. Du hast macOS 27, das passt.
4. Unreal braucht viel Speicherplatz. Meine Schätzung: mehrere zehn GB. Den genauen Wert zeigt dir der Launcher beim Installieren.

Xcode brauchst du erst später (Phase 6.5, wenn das Spiel in C++ programmiert wird).

## 3. Projekt anlegen

1. Unreal 5.8 starten → **Games** → **First Person**.
2. Rechts: **Blueprint**, Ziel **Desktop**, Qualität **Maximum**, **Starter Content aus**.
3. Speicherort: **nicht** im Ordner `twd`, z. B. `~/Unreal/Viertel`. Name: `Viertel` → **Create**.
4. Menü **Edit → Plugins** → nach **Python** suchen → **Python Editor Script Plugin** anhaken. Falls es angeboten wird, auch **Editor Scripting Utilities** anhaken. Danach Unreal neu starten.

## 4. Testpaket aus Blender exportieren

Dauert in der Cloud etwa 1 Minute und belegt etwa 0,7 GB in `twd/export/unreal_test`:

```bash
/Applications/Blender-5.2.3.app/Contents/MacOS/Blender -b viertel_v12.blend --python scripts/phase6/export_unreal.py -- --test
```

Am Ende muss eine Zeile beginnend mit `EXPORT {'formen': ...` stehen (etwa 1000 Formen).

## 5. In Unreal importieren

1. In Unreal: Menü **Tools → Execute Python Script…** → `twd/scripts/phase6/ue_import.py` auswählen.
2. Es erscheinen Fortschrittsbalken (Materialien, Meshes, Platzieren). Das kann einige Minuten dauern. Wie lange genau, weiß ich nicht.
3. Danach ist das Level `Content/Viertel/Karten/L_Viertel_Test` offen.

## 6. Prüfen (wichtig!)

**A) Liegt alles richtig herum?**
1. Im großen Fenster oben links auf **Perspective** klicken → **Top** wählen. Mit dem Mausrad herauszoomen.
2. Vergleiche mit meinem Referenzbild `renders/test/phase6_referenz_draufsicht.png`: Häuserreihe oben, Straße in der Mitte, Panzer, rotes Testobjekt rechts unter dem Panzer.
3. **Drehen ist in Ordnung, Spiegeln nicht.** Das Unreal-Bild darf gedreht sein. Wenn es sich aber nur durch Spiegeln mit meinem Bild zur Deckung bringen lässt, stimmt etwas nicht.
4. Das Testobjekt ist ein Pfeil (2 m lang) mit einem kurzen Stab (1 m) zur Seite und einem Würfel (0,5 m). Prüfe: Zeigt die Pfeilspitze wie im Referenzbild weg vom Panzer, und sitzt der Stab auf derselben Seite?

**B) Durchlaufen:** **Play** drücken (grünes Dreieck oben). Mit WASD und der Maus laufen. Mit Esc beendest du.
- Bildrate anzeigen: während des Spielens die Taste `^` bzw. `` ` `` drücken (öffnet die Konsole), `stat fps` tippen und Enter drücken.

## 7. Das schickst du mir

1. Screenshot der Draufsicht (Top) und einen Screenshot beim Spielen (Cmd+Shift+4).
2. Die fps-Zahl beim Spielen.
3. Fehlermeldungen: Menü **Window → Output Log**, oben im Suchfeld `VIERTEL` eingeben, alle gelben/roten Zeilen kopieren.
4. Was komisch aussieht (z. B. pinke/schwarze Flächen, schwebende Dinge, falsche Größe).

## Wenn etwas schiefgeht

- **"No module named unreal" / Menüpunkt fehlt:** Das Python-Plugin ist nicht aktiv (Schritt 3.4).
- **Unreal stürzt ab oder hängt:** In `ue_import.py` ganz oben `NANITE = False` setzen. Nanite ist auf dem Mac bei Epic noch als „Beta“ markiert.
- **Alles ist schwarz:** Im Level fehlt Licht. Schick mir das Output Log.
- **Nochmal von vorn:** Im Content Browser den Ordner `Viertel` löschen und Schritt 5 wiederholen.
