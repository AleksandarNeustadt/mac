# ========================================================================
# File:       system/handlers/file_handler.py
# Purpose:    Niski sloj za rad sa fajlovima i direktorijumima
# Author:     Aleksandar Popovic
# Created:    2025-08-07
# Updated:    2025-08-07
# ========================================================================

import os
import shutil
import zipfile


# 📄 Rad sa fajlovima

def write_file(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def update_file(path: str, content: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fajl ne postoji: {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def delete_file(path: str):
    if os.path.exists(path):
        os.remove(path)


def file_exists(path: str) -> bool:
    return os.path.exists(path)


def rename_file(old_path: str, new_path: str):
    os.rename(old_path, new_path)


def copy_file(src: str, dest: str):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src, dest)


def move_file(src: str, dest: str):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)


# 📦 Kompresija

def zip_file(src: str, zip_path: str):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        if os.path.isdir(src):
            for root, _, files in os.walk(src):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, start=os.path.dirname(src))
                    zipf.write(full_path, arcname)
        else:
            zipf.write(src, os.path.basename(src))


def unzip_file(zip_path: str, dest_dir: str):
    with zipfile.ZipFile(zip_path, "r") as zipf:
        zipf.extractall(dest_dir)


# 📁 Direktoriijumi i listanje

def list_files(directory: str):
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]


def list_dirs(directory: str):
    return [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]


def create_directory_if_missing(path: str):
    os.makedirs(path, exist_ok=True)
