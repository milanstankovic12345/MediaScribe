import customtkinter as ctk

from app import downloader
from app.screens.base import Screen


class AudioScreen(Screen):
    button_text = "Download audio (MP3)"
    supports_playlist = True
    dir_key = "audio_dir"

    def _build_options(self, parent):
        ctk.CTkLabel(parent, text="Audio quality:").pack(side="left")
        self.quality = ctk.CTkOptionMenu(parent, values=downloader.AUDIO_QUALITIES, width=110)
        q = self.cfg["audio_quality"]
        self.quality.set(q if q in downloader.AUDIO_QUALITIES else downloader.AUDIO_QUALITIES[0])
        self.quality.pack(side="left", padx=8)

    def _args(self):
        return (self.quality.get(),)

    def collect_cfg(self):
        return {**super().collect_cfg(), "audio_quality": self.quality.get()}

    def _run(self, url, out, quality):
        self._say("Downloading audio...")
        path, _title = downloader.download_audio(url, out, self._prog, quality)
        self._say(f"Saved: {path}")
        return f"Audio saved:\n{path}", path

    def _run_item(self, url, out, args, prefix, cb):
        path, _title = downloader.download_audio(url, out, cb, args[0], prefix)
        return path
