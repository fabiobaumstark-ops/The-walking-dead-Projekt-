# Auf dem Mac weitermachen (mit Claude Code)

Stand: 11.11.2026. Hier steht, wie du genau dort weitermachst, wo die Cloud-Sitzung aufgehört hat.
Auf dem Mac kann Claude Code selbst Befehle ausführen (git, Blender, Export). In der Cloud ging das nicht.

## 1. Einmalig: Projekt auf den neuesten Stand bringen

Terminal öffnen, diese Zeile kopieren, Enter:

```bash
cd ~/Claude/twd && git fetch origin claude/zealous-ride-c12e2z && git checkout claude/zealous-ride-c12e2z && git pull
```

- Falls dein Projektordner woanders liegt: `~/Claude/twd` durch deinen Pfad ersetzen.
- Kommt „Your local changes … would be overwritten“: nichts löschen. Claude Code (Schritt 2) fragen, es löst das sicher.

## 2. Claude Code im Projektordner starten

Im Terminal im Ordner `twd`:

```bash
claude
```

Dann diesen Satz schreiben:

> Lies AUFTRAG.md, UEBERGABE.md und WEITERMACHEN_MAC.md und mach weiter. Ich bin auf dem Mac, Unreal 5.8 ist installiert und das Projekt „Viertel“ (Blueprint, First Person) ist angelegt.

## 3. Wo wir gerade stehen

| Bereich | Stand |
|---|---|
| Blender-Datei | `viertel_v12.blend` (aktuell), `viertel_v10.blend` = Bau-Basis für alle Umbauten |
| Begehbar | 39 von 41 Gebäuden in allen Geschossen (Kirche und Tankstellen-Shop fehlen noch) |
| Dach | über Dachluke + Steigleiter (deine Entscheidung) |
| Innenräume | Muster in B11 (Wohnhaus) und B05 (Laden + Wohnungen): Räume, Tapete/Putz/Dielen, Möbel-Scans |
| Unreal | 5.8 installiert, Metal-Toolchain nachinstalliert, Projekt „Viertel“ angelegt; **erster Import noch nicht gemacht** |

## 4. Nächste Schritte (in dieser Reihenfolge)

**A) Unreal-Test (Phase 6.1)** – das kann Claude Code auf dem Mac teilweise selbst:
1. Neue Texturen/Möbel laden: `python3 download_assets.py --nur-basis`
2. Testpaket exportieren:
   `/Applications/Blender-5.2.3.app/Contents/MacOS/Blender -b viertel_v12.blend --python scripts/phase6/export_unreal.py -- --test`
3. In Unreal (das machst du): Edit → Plugins → „Python Editor Script Plugin“ an, Neustart, dann
   Tools → Execute Python Script… → `twd/scripts/phase6/ue_import.py`
4. Prüfen wie in `UNREAL_ANLEITUNG.md` Schritt 6 (Draufsicht mit `renders/test/phase6_referenz_draufsicht.png`
   vergleichen, Play drücken, Output Log nach „VIERTEL“ filtern) und das Ergebnis Claude Code zeigen.

**B) Innenräume verbessern (Phase 6.4 Teil 2)** – deine Rückmeldung: „Texturen innen schlecht“, wurde überarbeitet. Offen:
- Moos auf dem Ladenboden (Korrektur ist eingetragen, neu rendern)
- Räume zu leer: Kleinkram, Schutt, Papier, Scherben, Laub
- Küche/Bad einrichten (Küchenzeile, Waschbecken, WC – selbst modellieren, keine freien Scans)
- Licht in fensterlosen Räumen
- dann auf alle Gebäude übertragen, Kirche und Tankstelle neu bauen

## 5. Wichtig für Claude Code auf dem Mac

- Gebäude immer aus `viertel_v10.blend` neu bauen: `scripts/phase6/innenraum.py -- --version NN`
- Danach immer `scripts/phase6/begehbar.py` laufen lassen (Begehbarkeit) und bei Änderungen am Generator
  `innenraum.py -- --pruefen` und `-- --pruefen-zufall` (Fassaden dürfen sich nicht ändern)
- Innen-Vorschau: `scripts/phase6/innen_vorschau.py -- --ansichten B11_wohnen,B05_laden --belichtung 6.0`
- Auf dem Mac (24 GB RAM) reicht der Speicher für Innen-Renders; die GPU (Metal) kompiliert beim ersten Start lange,
  für kleine Vorschauen `--cpu` bzw. die Cloud-Einstellungen nutzen
- Alles Weitere: `UEBERGABE.md` (Skriptliste, Antworten), `PROTOKOLL.md` (was wann warum), `AUFTRAG.md` (Regeln, Phasen)
