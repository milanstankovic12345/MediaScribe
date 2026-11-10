import os
import subprocess
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk


def done_payload(result) -> tuple[str, Path | None]:
    """Normalise a worker result (str or (message, path)) to (message, path | None)."""
    if isinstance(result, tuple):
        msg, path = (tuple(result) + (None, None))[:2]
        return (msg or "Finished."), (Path(path) if path else None)
    return (result or "Finished."), None


def folder_of(path: Path) -> Path:
    """The folder the Open folder button targets for `path`."""
    path = Path(path)
    return path if path.is_dir() else path.parent


def open_folder(path, *, startfile=None, popen=None) -> bool:
    """Open Explorer on a directory, or on the folder of a file with the file selected.

    Returns False when the folder does not exist. Explorer's exit code is not checked.
    """
    path = Path(path)
    if path.is_file():
        (popen or subprocess.Popen)(f'explorer /select,"{path.resolve()}"')
        return True
    folder = folder_of(path)
    if not folder.is_dir():
        return False
    startfile = startfile or getattr(os, "startfile", None)
    if startfile is None:
        return False
    startfile(str(folder))
    return True


class DoneDialog(ctk.CTkToplevel):
    """Completion popup with an optional Open folder button (main thread only)."""

    def __init__(self, master, message: str, path: Path | None = None):
        super().__init__(master)
        self.title("Done")
        self.transient(master.winfo_toplevel())
        self._path = path
        ctk.CTkLabel(self, text=message, wraplength=420, justify="left").pack(padx=20, pady=(20, 10))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(padx=20, pady=(0, 16))
        if path is not None:
            ctk.CTkButton(row, text="Open folder", width=110, command=self._open).pack(side="left", padx=4)
        ok = ctk.CTkButton(row, text="OK", width=80, command=self.destroy)
        ok.pack(side="left", padx=4)
        self.bind("<Return>", lambda _e: self.destroy())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(100, self._take_focus)

    def _take_focus(self):
        try:
            self.grab_set()
            self.focus()
        except Exception:
            pass

    def _open(self):
        if not open_folder(self._path):
            messagebox.showwarning("Open folder", f"Folder not found:\n{folder_of(self._path)}")
