# ============================================================================
# File:       system/managers/file_manager.py
# Purpose:    API sloj sa klasom FileManager — klasni pristup
# Author:     Aleksandar Popović
# Created:    2025-08-07
# Updated:    2025-08-07
# ============================================================================

from system.handlers.file_handler import (
    write_file,
    read_file,
    update_file,
    delete_file,
    file_exists,
    rename_file,
    copy_file,
    move_file,
    zip_file,
    unzip_file,
    list_files,
    list_dirs,
    create_directory_if_missing
)
from system.helpers.core_helper import safe_call
from system.managers.event_manager import EventManager


class FileManager:
    @staticmethod
    def create(path, content):
        result = safe_call(write_file, path, content)
        if result:
            EventManager.emit("file_created", {"path": path})
        else:
            EventManager.emit("file_create_failed", {"path": path})
        return result

    @staticmethod
    def read(path):
        result = safe_call(read_file, path)
        if result is not None:
            EventManager.emit("file_read", {"path": path})
        else:
            EventManager.emit("file_read_failed", {"path": path})
        return result

    @staticmethod
    def update(path, content):
        result = safe_call(update_file, path, content)
        if result:
            EventManager.emit("file_updated", {"path": path})
        else:
            EventManager.emit("file_update_failed", {"path": path})
        return result

    @staticmethod
    def delete(path):
        result = safe_call(delete_file, path)
        if result:
            EventManager.emit("file_deleted", {"path": path})
        else:
            EventManager.emit("file_delete_failed", {"path": path})
        return result

    @staticmethod
    def exists(path):
        result = safe_call(file_exists, path)
        EventManager.emit("file_checked", {"path": path, "exists": result})
        return result

    @staticmethod
    def rename(old_path, new_path):
        result = safe_call(rename_file, old_path, new_path)
        if result:
            EventManager.emit("file_renamed", {"from": old_path, "to": new_path})
        else:
            EventManager.emit("file_rename_failed", {"from": old_path, "to": new_path})
        return result

    @staticmethod
    def copy(src, dest):
        result = safe_call(copy_file, src, dest)
        if result:
            EventManager.emit("file_copied", {"from": src, "to": dest})
        else:
            EventManager.emit("file_copy_failed", {"from": src, "to": dest})
        return result

    @staticmethod
    def move(src, dest):
        result = safe_call(move_file, src, dest)
        if result:
            EventManager.emit("file_moved", {"from": src, "to": dest})
        else:
            EventManager.emit("file_move_failed", {"from": src, "to": dest})
        return result

    @staticmethod
    def zip(src, zip_path):
        result = safe_call(zip_file, src, zip_path)
        if result:
            EventManager.emit("file_zipped", {"src": src, "zip": zip_path})
        else:
            EventManager.emit("file_zip_failed", {"src": src, "zip": zip_path})
        return result

    @staticmethod
    def unzip(zip_path, dest_dir):
        result = safe_call(unzip_file, zip_path, dest_dir)
        if result:
            EventManager.emit("file_unzipped", {"zip": zip_path, "dest": dest_dir})
        else:
            EventManager.emit("file_unzip_failed", {"zip": zip_path, "dest": dest_dir})
        return result

    @staticmethod
    def list_all_files(directory):
        result = safe_call(list_files, directory)
        if result is not None:
            EventManager.emit("files_listed", {"directory": directory, "count": len(result)})
        else:
            EventManager.emit("files_list_failed", {"directory": directory})
        return result

    @staticmethod
    def list_all_dirs(directory):
        result = safe_call(list_dirs, directory)
        if result is not None:
            EventManager.emit("dirs_listed", {"directory": directory, "count": len(result)})
        else:
            EventManager.emit("dirs_list_failed", {"directory": directory})
        return result

    @staticmethod
    def ensure_dir(path):
        result = safe_call(create_directory_if_missing, path)
        if result:
            EventManager.emit("directory_ensured", {"path": path})
        else:
            EventManager.emit("directory_ensure_failed", {"path": path})
        return result
