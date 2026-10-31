import pathlib
import os
import argparse

parser = argparse.ArgumentParser(
                    prog='mid_grep',
                    description='What the program does ? Nothing rn',
                    epilog='No help at all sry')



parser.add_argument('helloworld')           # positional argument
parser.add_argument('-c', '--count')      # option that takes a value
parser.add_argument('-v', '--verbose',
                    action='store_true')  # on/off flag

args=parser.parse_args()

def helloworld():
    print("Hello world")

def search_file_folder(folder_path, file_path):
    if (not folder_path.exists()):
        print("Folder does not exist")
        return None
    file_name = file_path.name
    
    for dirpath, dirnames, filenames in os.walk(folder_path):
        print(f"Dossier actuel : {dirpath}")
        print(f"  Sous-dossiers : {dirnames}")
        print(f"  Fichiers : {filenames}")
        if file_name == filenames:
            continue

def search_sequence(sequence):
    return

def img_to_hexa():
    return

def txt_to_hexa(file_path):
    if (not file_path.exists()):
        return "Text file doesn't exist."
    f = open(file_path, 'r')
    contenu = f.read()
    contenu_hexa = 0x00 #Logique txt to hexa ici.
    f.close()

    return contenu_hexa