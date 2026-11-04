# ZUHAUSE_ANLEITUNG – Rendern auf dem Mac (wird in Phase 5 vervollständigt)

> Stand Phase 3. Die vollständige Anleitung (Render-Einstellungen, Metal, Kameras, Laufzeiten) folgt in Phase 5.

## Vorbereitung
1. Repo klonen bzw. aktualisieren (Branch `claude/zen-meitner-53hxe1`).
2. Im Projektordner: `python3 download_assets.py --nur-basis`
   - lädt alle Texturen, HDRIs und Modelle (CC0) nach `assets/`
   - lädt auch die MakeHuman-Systemassets (CC0) für die Figurentexturen
3. `viertel_v04.blend` in Blender 5.2 öffnen. Alle Pfade sind relativ, `assets/` muss neben der .blend liegen.

## Figuren ersetzen (Auftrag 3.6)
Die Figuren liegen in der Collection **09_Figuren**:
- Namen: `FIG_<Gruppe>_<Nr>` bzw. `FIG_Einzeln_<Name>`
- Es sind verlinkte Kopien von 12 Vorlagen in `00_Prototypen/PROTO_Figuren_Vorlagen`, also gebackene Meshes ohne Rig.

So tauschst du eine Figur gegen einen fertigen Charakter:
1. Den eigenen Charakter importieren (z. B. FBX/Blend). Ursprung zwischen die Füße setzen, Blickrichtung −Y.
2. Die zu ersetzende Figur auswählen und Position und Drehung ablesen.
   - Oder alles in einem Schritt: im Python-Konsolenfenster `neu.matrix_world = alt.matrix_world.copy()`.
3. Die alte Figur löschen und die neue in die Collection 09_Figuren legen.

Eine ganze Vorlage für alle ihre Kopien tauscht du so:
- Im Objekt-Datenreiter das Mesh der Vorlage durch das neue Mesh ersetzen.
- Alle verlinkten Kopien übernehmen es automatisch.

Neu erzeugen mit eigenen Einstellungen:
- In `scripts/configs/figuren.json` Vorlagen, Gruppen und Positionen ändern.
- Dann `blender -b viertel_v03.blend --python scripts/phase3/build_phase3.py -- --version 04` ausführen.
- Dafür müssen MPFB 2 und die MakeHuman-Systemassets installiert sein.
