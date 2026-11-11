import customtkinter as ctk

from app import settings
from app.screens.audio import AudioScreen
from app.screens.settings_screen import SettingsScreen
from app.screens.transcribe import TranscribeScreen
from app.screens.video import VideoScreen

NAV = [("audio", "Audio (MP3)", AudioScreen),
       ("video", "Video (MP4)", VideoScreen),
       ("transcribe", "Transcribe", TranscribeScreen),
       ("settings", "Settings", SettingsScreen)]


class App(ctk.CTk):
    """Main window: sidebar navigation plus the Audio / Video / Transcribe screens."""

    def __init__(self):
        super().__init__()
        self.title("MediaScribe")
        self.geometry("880x620")
        ctk.set_appearance_mode("system")
        self.cfg = settings.load()
        self._build()
        self.show("audio")
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        side = ctk.CTkFrame(self, width=160, corner_radius=0)
        side.grid(row=0, column=0, sticky="ns")
        self.screens, self.nav_buttons = {}, {}
        for i, (key, label, cls) in enumerate(NAV):
            btn = ctk.CTkButton(side, text=label, height=40, anchor="w", fg_color="transparent",
                                text_color=("gray10", "gray90"), command=lambda k=key: self.show(k))
            btn.grid(row=i, column=0, padx=8, pady=(16 if i == 0 else 4, 0), sticky="ew")
            self.nav_buttons[key] = btn
            screen = cls(self, self.cfg)
            screen.grid(row=0, column=1, sticky="nsew")
            self.screens[key] = screen

    def show(self, key: str):
        """Raise the screen for `key` and highlight its sidebar button."""
        screen = self.screens[key]
        screen.tkraise()
        if hasattr(screen, "on_show"):
            screen.on_show()
        for k, btn in self.nav_buttons.items():
            btn.configure(fg_color=("gray75", "gray25") if k == key else "transparent")

    def _close(self):
        for s in self.screens.values():
            self.cfg.update(s.collect_cfg())
        try:
            settings.save(self.cfg)
        except OSError:
            pass
        self.destroy()
