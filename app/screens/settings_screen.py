import queue
import threading
import webbrowser

import customtkinter as ctk

from app import gemini, settings

STATUS_TEXT = {"invalid_key": "Invalid key", "network": "No internet", "rate_limited": "Rate limited"}

GUIDE = ("How to connect (free):\n"
         "1) Open Google AI Studio (button below).\n"
         "2) Sign in with a Google account.\n"
         "3) Click \"Create API key\".\n"
         "4) Paste the key above and click Save.")
PRIVACY = ("Privacy: with Gemini, transcript text is sent to Google. Free-tier data may be used by Google "
           "to improve its products, so do not use it for confidential recordings.")


def status_for_error(err: Exception) -> str:
    """Short status-line text for a failed connection test (never contains the key)."""
    return STATUS_TEXT.get(getattr(err, "kind", ""), "Error: " + str(err))


class SettingsScreen(ctk.CTkFrame):
    """App settings. Currently only the optional Gemini API key (not a `Screen` subclass)."""

    def __init__(self, master, cfg: dict):
        super().__init__(master, fg_color="transparent")
        self.cfg = cfg
        self.q: queue.Queue = queue.Queue()
        self.columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Gemini API (optional)", font=ctk.CTkFont(size=16, weight="bold"),
                     anchor="w").grid(row=0, column=0, padx=16, pady=(16, 4), sticky="ew")
        ctk.CTkLabel(self, text=GUIDE, anchor="w", justify="left").grid(
            row=1, column=0, padx=16, pady=4, sticky="ew")
        ctk.CTkButton(self, text="Get a free API key", width=160, command=self._open_key_page).grid(
            row=2, column=0, padx=16, pady=4, sticky="w")

        key_row = ctk.CTkFrame(self, fg_color="transparent")
        key_row.grid(row=3, column=0, padx=16, pady=8, sticky="ew")
        key_row.columnconfigure(0, weight=1)
        self.key_entry = ctk.CTkEntry(key_row, show="*", placeholder_text="Gemini API key")
        self.key_entry.grid(row=0, column=0, sticky="ew")
        if cfg.get("gemini_api_key"):
            self.key_entry.insert(0, cfg["gemini_api_key"])
        self.show_btn = ctk.CTkButton(key_row, text="Show", width=70, fg_color="gray", command=self._toggle_show)
        self.show_btn.grid(row=0, column=1, padx=(4, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=4, column=0, padx=16, pady=4, sticky="w")
        ctk.CTkButton(btns, text="Save", width=90, command=self._save).pack(side="left")
        self.test_btn = ctk.CTkButton(btns, text="Test connection", width=130, command=self._test)
        self.test_btn.pack(side="left", padx=8)
        ctk.CTkButton(btns, text="Disconnect", width=100, fg_color="gray", command=self._disconnect).pack(side="left")

        self.status = ctk.CTkLabel(self, text="", anchor="w")
        self.status.grid(row=5, column=0, padx=16, pady=8, sticky="ew")
        ctk.CTkLabel(self, text=PRIVACY, anchor="w", justify="left", wraplength=620).grid(
            row=6, column=0, padx=16, pady=8, sticky="ew")
        self._refresh_status()
        self.after(100, self._poll)

    def collect_cfg(self) -> dict:
        return {}  # the key is written to cfg only by Save / Disconnect

    # ---- actions (main thread)
    def _open_key_page(self):
        webbrowser.open(gemini.API_KEY_URL)

    def _toggle_show(self):
        hidden = self.key_entry.cget("show") == "*"
        self.key_entry.configure(show="" if hidden else "*")
        self.show_btn.configure(text="Hide" if hidden else "Show")

    def _persist(self):
        try:
            settings.save(self.cfg)
        except OSError:
            self.status.configure(text="Could not write the settings file.")

    def _save(self):
        self.cfg["gemini_api_key"] = self.key_entry.get().strip()
        self._persist()
        self._refresh_status()

    def _disconnect(self):
        self.cfg["gemini_api_key"] = ""
        self.key_entry.delete(0, "end")
        self._persist()
        self._refresh_status()

    def _refresh_status(self):
        if settings.get_gemini_key({}):
            text = "Using GEMINI_API_KEY from environment"
        elif self.cfg.get("gemini_api_key"):
            text = "Connected (key saved)"
        else:
            text = "Not connected"
        self.status.configure(text=text)

    def _test(self):
        env_key = settings.get_gemini_key({})
        key = env_key or self.key_entry.get().strip() or settings.get_gemini_key(self.cfg)
        if not key:
            self.status.configure(text="Enter a key first.")
            return
        self.test_btn.configure(state="disabled")
        self.status.configure(text="Testing GEMINI_API_KEY from environment..." if env_key else "Testing...")
        threading.Thread(target=self._test_worker, args=(key, self.cfg.get("gemini_model") or None),
                         daemon=True).start()

    def _test_worker(self, key, model):
        try:
            gemini.check_key(key, model)
            self.q.put(("ok", "Connected"))
        except Exception as e:
            self.q.put(("err", status_for_error(e)))

    def _poll(self):
        try:
            while True:
                kind, text = self.q.get_nowait()
                self.test_btn.configure(state="normal")
                self.status.configure(text=text)
        except queue.Empty:
            pass
        self.after(100, self._poll)
