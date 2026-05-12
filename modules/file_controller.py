"""
modules/file_controller.py — File system operations for Ghost-141
"""

import os
import shutil
import subprocess
import platform


class FileController:
    def __init__(self, settings):
        self.settings = settings
        self.os = platform.system()

    def open(self, path: str):
        path = os.path.expanduser(path)
        if self.os == "Linux":
            subprocess.Popen(["xdg-open", path])
        elif self.os == "Darwin":
            subprocess.Popen(["open", path])
        elif self.os == "Windows":
            os.startfile(path)
        print(f"[FILE] Opened: {path}")

    def list_dir(self, directory: str = "~") -> list[str]:
        path = os.path.expanduser(directory)
        try:
            return os.listdir(path)
        except Exception as e:
            return [f"Error: {e}"]

    def create(self, path: str, content: str = ""):
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        print(f"[FILE] Created: {path}")

    def read(self, path: str) -> str:
        path = os.path.expanduser(path)
        try:
            with open(path) as f:
                return f.read()
        except Exception as e:
            return f"Read error: {e}"

    def delete(self, path: str):
        path = os.path.expanduser(path)
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        print(f"[FILE] Deleted: {path}")

    def move(self, src: str, dst: str):
        shutil.move(os.path.expanduser(src), os.path.expanduser(dst))
        print(f"[FILE] Moved: {src} → {dst}")

    def rename(self, path: str, new_name: str):
        old = os.path.expanduser(path)
        new = os.path.join(os.path.dirname(old), new_name)
        os.rename(old, new)
        print(f"[FILE] Renamed: {old} → {new}")
