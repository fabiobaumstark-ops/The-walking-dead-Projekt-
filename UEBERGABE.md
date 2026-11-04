# UEBERGABE – aktueller Stand

- **Aktuelle Phase:** Phase 0 – Recherche fertig, warte auf Antworten zu den 11 Freigabe-Fragen (STOPP)
- **Blender-Version:** 5.2.3 LTS (Linux, /opt/blender-5.2.3-linux-x64, Befehl `blender`)
- **.blend-Version:** noch keine
- **Branch:** `claude/zen-meitner-53hxe1`
- **Netzwerk:** FULL (siehe AUFTRAG.md, A1b)

## Fertig
- AUFTRAG.md (Version 8, A1b Netzwerk FULL ergänzt)
- PROTOKOLL.md (Umgebungsprüfung, Blender-Installation)
- .gitignore
- Blender 5.2.3 LTS installiert + Testrender ok
- recherche/RECHERCHE.md, architektur.md, vegetation.md, moodboard.html
- recherche/LOOK_BIBLE.md (ENTWURF v0.1, auf Basis meiner Empfehlungen)
- MPFB 2.0.18 Installationstest in Blender 5.2.3: ok

## Halb fertig / fehlt
- LOOK_BIBLE.md an Antworten anpassen, dann zweite Bestätigung durch Nutzer
- fahrzeuge.md / militaer.md: erst vor Phase 3 (laut Auftrag)

## Nächster konkreter Schritt
- In einer neuen Sitzung: Blender ist im Container NICHT dauerhaft. Neu installieren:
  `curl -O https://download.blender.org/release/Blender5.2/blender-5.2.3-linux-x64.tar.xz`
  und nach /opt entpacken (Symlink /usr/local/bin/blender).
- Antworten des Nutzers auf die 11 Phase-0-Fragen in LOOK_BIBLE.md einarbeiten
  (Region, Jahreszeit, Licht, Zerstörung, Vegetation, Farbe, Militär-Epoche,
  Figuren, Hero-Shots, Animation), Status auf v1.0 setzen, Bestätigung einholen.
- Danach Phase 1 (AUFTRAG.md Phase 1 lesen).

## Offene Fragen an den Nutzer
- Phase-0-Freigabe-Fragen 1–11 (gestellt am 2026-11-04) – Empfehlungen:
  1 US-Süden · 2 Spätsommer · 3 Spätnachmittag, Sonne durch Dunst/Wolken ·
  4 gemischt (überwiegend verfallen) · 5 mittel bis stark · 6 warm-staubig mit
  gelb-grünem Stich · 7 eher modern · 8 einzelne Gruppen · 9 MPFB ·
  10 Hero-Shots so lassen · 11 später entscheiden

## Bisherige Antworten/Freigaben
- Netzwerk: FULL (alle Domains erreichbar)
- Blender: normale Linux-Version (nicht bpy von PyPI)
- Branch: weiter in `claude/zen-meitner-53hxe1`
- Recherche Phase 0 starten: ja

## Ausgeführte Skripte (Reihenfolge)
- keine Projektskripte bisher
