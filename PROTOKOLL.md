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
