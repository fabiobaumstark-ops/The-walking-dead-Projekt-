"""Nur Sonne, Himmel, Himmelslicht, Dunst und Startpunkt im offenen Level neu setzen (ohne Neu-Import).

In Unreal: Tools -> Execute Python Script... -> diese Datei. Das Level L_Viertel_Test muss offen sein.
"""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ue_import.py"), init_globals={"NUR_UMGEBUNG": True})
