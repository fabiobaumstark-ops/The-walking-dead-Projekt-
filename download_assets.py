#!/usr/bin/env python3
"""Laedt alle Assets (Texturen, HDRIs, Modelle) aus assets_manifest.json in den Ordner assets/.

Nur Python-Standardbibliothek. Bereits vorhandene Dateien (richtige Groesse) werden uebersprungen.

Aufruf im Projektordner (Terminal):
    python3 download_assets.py              # alles (auch 16K-HDRI fuer finale Renders)
    python3 download_assets.py --nur-basis  # ohne die grossen "final"-Dateien
    python3 download_assets.py --pruefen    # zusaetzlich MD5-Pruefsummen kontrollieren
"""
import argparse
import hashlib
import json
import os
import shutil
import ssl
import sys
import time
import urllib.error
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "assets_manifest.json")
UA = {"User-Agent": "viertel-projekt-download/1.0"}


def mb(n):
    return f"{(n or 0) / 1e6:7.1f} MB"


def md5_von(pfad):
    h = hashlib.md5()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fortschritt(text, done, total, start):
    breite = 28
    anteil = done / total if total else 0
    balken = "#" * int(breite * anteil) + "-" * (breite - int(breite * anteil))
    tempo = done / max(time.time() - start, 0.001) / 1e6
    sys.stdout.write(f"\r  [{balken}] {anteil*100:5.1f}% {mb(done)} von {mb(total)}  {tempo:5.1f} MB/s  {text[:38]:<38}")
    sys.stdout.flush()


def lade(url, ziel, groesse, text):
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    tmp = ziel + ".teil"
    letzter_fehler = None
    for versuch in range(4):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as out:
                total = groesse or int(r.headers.get("Content-Length") or 0)
                done, start = 0, time.time()
                while True:
                    block = r.read(1 << 16)
                    if not block:
                        break
                    out.write(block)
                    done += len(block)
                    fortschritt(text, done, total, start)
            os.replace(tmp, ziel)
            sys.stdout.write("\n")
            return True
        except urllib.error.URLError as e:
            letzter_fehler = e
            if isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
                break  # Wiederholen hilft hier nicht
        except Exception as e:  # noqa: BLE001
            letzter_fehler = e
        time.sleep(2 ** (versuch + 1))
    sys.stdout.write("\n")
    if os.path.exists(tmp):
        os.remove(tmp)
    erklaere_fehler(url, letzter_fehler)
    return False


def erklaere_fehler(url, e):
    print(f"  FEHLER bei {url}")
    print(f"    Grund: {e}")
    reason = getattr(e, "reason", None)
    if isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(e):
        print("    -> Dein Python hat keine SSL-Zertifikate. Auf dem Mac im Finder:")
        print("       Programme > Python 3.x > 'Install Certificates.command' doppelklicken, dann erneut starten.")
    elif isinstance(e, urllib.error.HTTPError) and e.code == 404:
        print("    -> Datei gibt es auf dem Server nicht mehr. Bitte Claude Bescheid sagen (Manifest erneuern).")
    else:
        print("    -> Internetverbindung pruefen und das Skript einfach noch einmal starten.")
        print("       Bereits geladene Dateien werden dann uebersprungen.")


def entpacken(zip_pfad, ziel_ordner):
    with zipfile.ZipFile(zip_pfad) as z:
        for name in z.namelist():
            # nur Bilddateien, keine Unterordner/Skripte, gegen Pfad-Tricks abgesichert
            base = os.path.basename(name)
            if not base or not base.lower().endswith((".jpg", ".jpeg", ".png", ".exr", ".tif")):
                continue
            with z.open(name) as src, open(os.path.join(ziel_ordner, base), "wb") as dst:
                shutil.copyfileobj(src, dst)


def entpacken_struktur(zip_pfad, ziel_ordner):
    """Nur Bilddateien, Ordnerstruktur bleibt (fuer die Figuren-Texturen); unsichere Pfade werden uebersprungen."""
    with zipfile.ZipFile(zip_pfad) as z:
        for name in z.namelist():
            if name.startswith("/") or ".." in name.split("/") or not name.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            ziel = os.path.join(ziel_ordner, *name.split("/"))
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            if os.path.exists(ziel):
                continue
            with z.open(name) as src, open(ziel, "wb") as dst:
                shutil.copyfileobj(src, dst)


def main():
    ap = argparse.ArgumentParser(description="Assets laden")
    ap.add_argument("--nur-basis", action="store_true", help="grosse 'final'-Dateien (16K-HDRI) weglassen")
    ap.add_argument("--pruefen", action="store_true", help="MD5-Pruefsummen kontrollieren")
    args = ap.parse_args()

    if not os.path.exists(MANIFEST):
        print("assets_manifest.json nicht gefunden. Bitte das Skript im Projektordner starten.")
        return 1
    man = json.load(open(MANIFEST, encoding="utf-8"))
    assets = [a for a in man["assets"] if not (args.nur_basis and a.get("gruppe") == "final")]
    dateien = [(a, f) for a in assets for f in a["dateien"]]
    gesamt = sum(f.get("size") or 0 for _, f in dateien)
    print(f"{len(assets)} Assets, {len(dateien)} Dateien, ca. {gesamt/1e9:.2f} GB")

    ok = uebersprungen = fehler = 0
    for i, (a, f) in enumerate(dateien, 1):
        ziel = os.path.join(ROOT, f["ziel"])
        text = f"{i}/{len(dateien)} {a['name']}"
        vorhanden = os.path.exists(ziel) and (not f.get("size") or os.path.getsize(ziel) == f["size"])
        if vorhanden and args.pruefen and f.get("md5") and md5_von(ziel) != f["md5"]:
            print(f"  {text}: Pruefsumme falsch -> neu laden")
            vorhanden = False
        if vorhanden:
            uebersprungen += 1
            print(f"  {text}: schon da")
        else:
            print(f"  {text}: {os.path.basename(ziel)}")
            if not lade(f["url"], ziel, f.get("size"), text):
                fehler += 1
                continue
            if args.pruefen and f.get("md5") and md5_von(ziel) != f["md5"]:
                print("    WARNUNG: Pruefsumme stimmt nach dem Laden nicht. Bitte erneut starten.")
                fehler += 1
                continue
            ok += 1
        if f.get("entpacken"):
            entpacken(ziel, os.path.dirname(ziel))
        if f.get("entpacken_nach"):
            entpacken_struktur(ziel, os.path.join(ROOT, f["entpacken_nach"]))

    print(f"\nFertig: {ok} geladen, {uebersprungen} schon vorhanden, {fehler} Fehler.")
    if fehler:
        print("Einfach noch einmal starten - fertige Dateien werden uebersprungen.")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
