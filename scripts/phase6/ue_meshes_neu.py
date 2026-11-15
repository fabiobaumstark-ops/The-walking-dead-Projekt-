"""Alle Meshes neu importieren und das Level neu aufbauen (Texturen/Materialien bleiben), z. B. nach einem neuen Export.

In Unreal: Tools -> Execute Python Script... -> diese Datei.
Ohne Fenster (Unreal geschlossen):
UnrealEditor viertel.uproject -run=pythonscript -script=<Pfad>/ue_meshes_neu.py -unattended
"""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ue_import.py"), init_globals={"NEU_MESHES": True})
