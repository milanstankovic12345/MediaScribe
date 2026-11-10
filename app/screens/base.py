import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app import downloader
from app.screens.done_dialog import DoneDialog, done_payload
from app.screens.playlist_dialog import PlaylistDialog


class Screen(ctk.CTkFrame):
    """One self-contained page: URL, options, output folder, progress bar, log.

    Subclasses add their own option widgets in `_build_options` (row 1), set `button_text`,
    `dir_key`, and implement `_validate`, `_args` (main thread) and `_run` (worker thread).
    """
    button_text = "Start"
    dir_key = "output_dir"
    show_url_clear = True
    supports_playlist = False  # Audio/Video override: a playlist URL downloads each item separately

    def __init__(self, master, cfg: dict):
        super().__init__(master, fg_color="transparent")
        self.cfg = cfg
        self.q: queue.Queue = queue.Queue()
        self.busy = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(6, weight=1)

        url_row = ctk.CTkFrame(self, fg_color="transparent")
        url_row.grid(row=0, column=0, padx=16, pady=(16, 4), sticky="ew")
        url_row.columnconfigure(0, weight=1)
        self.url = ctk.CTkEntry(url_row, placeholder_text="Paste YouTube URL...")
        self.url.grid(row=0, column=0, sticky="ew")
        if self.show_url_clear:
            ctk.CTkButton(url_row, text="Clear", width=60, fg_color="gray", command=self._clear).grid(
                row=0, column=1, padx=(4, 0))

        opts = ctk.CTkFrame(self, fg_color="transparent")
        opts.grid(row=1, column=0, padx=16, pady=4, sticky="ew")
        self._build_options(opts)

        out = ctk.CTkFrame(self, fg_color="transparent")
        out.grid(row=2, column=0, padx=16, pady=4, sticky="ew")
        out.columnconfigure(0, weight=1)
        self.out_entry = ctk.CTkEntry(out)
        self.out_entry.insert(0, cfg[self.dir_key])
        self.out_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(out, text="Output folder", width=110, command=self._pick_dir).grid(row=0, column=1, padx=(4, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, padx=16, pady=8, sticky="ew")
        self.action_buttons = self._build_actions(actions)
        self.bar = ctk.CTkProgressBar(self)
        self.bar.set(0)
        self.bar.grid(row=4, column=0, padx=16, pady=4, sticky="ew")
        self.logbox = ctk.CTkTextbox(self, state="disabled")
        self.logbox.grid(row=6, column=0, padx=16, pady=(4, 16), sticky="nsew")
        self.after(100, self._poll)

    # ---- hooks for subclasses
    def _build_options(self, parent):
        pass

    def _build_actions(self, parent) -> list:
        """Create the action button(s) in `parent`; return them (all disabled while busy)."""
        parent.columnconfigure(0, weight=1)
        self.button = ctk.CTkButton(parent, text=self.button_text, height=40, command=self._start)
        self.button.grid(row=0, column=0, sticky="ew")
        return [self.button]

    def _validate(self, url: str) -> str | None:
        """Return a warning message if input is invalid, else None."""
        return None if url else "Paste a YouTube URL first."

    def _args(self) -> tuple:
        """Snapshot of widget values for the worker (main thread)."""
        return ()

    def _run(self, url: str, out: Path, *args) -> str:
        raise NotImplementedError

    def _run_item(self, url: str, out: Path, args: tuple, prefix: str, cb) -> Path:
        """Download one playlist item; return the saved file path (worker thread)."""
        raise NotImplementedError

    def collect_cfg(self) -> dict:
        return {self.dir_key: self.out_entry.get().strip() or self.cfg[self.dir_key]}

    # ---- helpers
    def _clear(self):
        self.url.delete(0, "end")

    def _pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.out_entry.get() or None)
        if d:
            self.out_entry.delete(0, "end")
            self.out_entry.insert(0, d)

    def _log(self, msg: str):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def _set_busy(self, busy: bool):
        self.busy = busy
        for b in self.action_buttons:
            b.configure(state="disabled" if busy else "normal")
        if busy:
            self.bar.set(0)

    # ---- threading
    def _start(self):
        if self.busy:
            return
        url = self.url.get().strip()
        problem = self._validate(url)
        if problem:
            messagebox.showwarning("Check input", problem)
            return
        if self.supports_playlist and downloader.is_playlist_url(url):
            self._set_busy(True)
            self._log("Fetching playlist...")
            threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()
            return
        self.cfg.update(self.collect_cfg())
        out = Path(self.cfg[self.dir_key])
        self._set_busy(True)
        threading.Thread(target=self._worker, args=(url, out, self._args()), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            self.q.put(("playlist", downloader.fetch_playlist(url)))
        except Exception as e:
            self.q.put(("error", str(e)))

    def _on_playlist(self, title, entries):
        self._set_busy(False)
        if not entries:
            self._log("ERROR: playlist has no available videos.")
            messagebox.showerror("Error", "The playlist has no available videos.")
            return
        self._log(f"Playlist '{title}': {len(entries)} videos.")
        PlaylistDialog(self, title, entries, lambda sel: self._start_playlist(title, sel))

    def _start_playlist(self, title, entries):
        if self.busy or not entries:
            return
        self.cfg.update(self.collect_cfg())
        out = Path(self.cfg[self.dir_key]) / downloader.safe_name(title)
        self._set_busy(True)
        threading.Thread(target=self._playlist_worker, args=(entries, out, self._args()), daemon=True).start()

    def _playlist_worker(self, entries, out, args):
        n, failed = len(entries), []
        try:
            for i, e in enumerate(entries):
                self._say(f"[{i + 1}/{n}] {e.title}")
                try:
                    self._run_item(e.url, out, args, downloader.item_prefix(e.index, entries[-1].index),
                                   lambda f, i=i: self._prog((i + f) / n))
                except Exception as ex:  # skip this item, keep going
                    failed.append(e.title)
                    self._say(f"  FAILED: {ex}")
                self._prog((i + 1) / n)
            msg = f"Playlist saved ({n - len(failed)}/{n} ok):\n{out}"
            if failed:
                msg += "\n\nFailed:\n" + "\n".join(failed)
            self.q.put(("done", (msg, out)))
        except Exception as ex:
            self.q.put(("error", str(ex)))

    def _worker(self, url, out, args):
        try:
            self.q.put(("done", self._run(url, out, *args)))
        except Exception as e:  # show any failure readably
            self.q.put(("error", str(e)))

    def _poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "progress":
                    self.bar.set(val)
                elif kind == "log":
                    self._log(val)
                elif kind == "playlist":
                    self._on_playlist(*val)
                elif kind == "done":
                    self._set_busy(False)
                    self.bar.set(1)
                    self._log("Done.")
                    message, path = done_payload(val)
                    DoneDialog(self, message, path)
                elif kind == "error":
                    self._set_busy(False)
                    self._log(f"ERROR: {val}")
                    messagebox.showerror("Error", val)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _prog(self, v: float):
        self.q.put(("progress", v))

    def _say(self, msg: str):
        self.q.put(("log", msg))
