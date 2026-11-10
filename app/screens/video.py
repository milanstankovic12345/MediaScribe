import customtkinter as ctk

from app import downloader
from app.screens.base import Screen


class VideoScreen(Screen):
    button_text = "Download video (MP4)"
    supports_playlist = True
    dir_key = "video_dir"

    def _build_options(self, parent):
        ctk.CTkLabel(parent, text="Video quality:").pack(side="left")
        self.quality = ctk.CTkOptionMenu(parent, values=downloader.VIDEO_QUALITIES, width=110)
        q = self.cfg["video_quality"]
        self.quality.set(q if q in downloader.VIDEO_QUALITIES else downloader.VIDEO_QUALITIES[0])
        self.quality.pack(side="left", padx=8)

    def _args(self):
        return (self.quality.get(),)

    def collect_cfg(self):
        return {**super().collect_cfg(), "video_quality": self.quality.get()}

    def _run(self, url, out, quality):
        self._say("Downloading video...")
        path, _title = downloader.download_video(url, out, self._prog, quality)
        self._say(f"Saved: {path}")
        return f"Video saved:\n{path}", path

    def _run_item(self, url, out, args, prefix, cb):
        path, _title = downloader.download_video(url, out, cb, args[0], prefix)
        return path
