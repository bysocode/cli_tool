import os
import re

folder_path = "./"
for (dirpath, dirnames, filenames) in os.walk(folder_path):
    print("type dirpath", type(dirpath), "is git in dirpath", (r"*git*" in dirpath))
    if not ("*git*" in dirpath) or not ("*git*" in dirnames) or not(""): 
        print(f"Dossier actuel : {dirpath}")
        print(f"  Sous-dossiers : {dirnames}")
        print(f"  Fichiers : {filenames}")
    else:
        continue

