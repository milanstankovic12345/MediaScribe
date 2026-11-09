import tempfile
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app import audio_prep, downloader, exporter, subtitles, translator
from app.screens.base import Screen
from app.transcriber import LANGUAGES, MODELS, transcribe

MEDIA_TYPES = [("Audio/Video", "*.mp3 *.m4a *.wav *.flac *.ogg *.opus *.mp4 *.mkv *.webm *.mov *.avi"),
               ("All files", "*.*")]
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
SRT_ONLY, EMBED, BURN = "SRT file only", "Embed into video (fast)", "Burn into video (slow)"
SUB_VIDEO_MODES = [SRT_ONLY, EMBED, BURN]
NO_FILE_TEXT = "Or use a local file: (none)"


class TranscribeScreen(Screen):
    button_text = "Transcribe"
    dir_key = "transcribe_dir"
    show_url_clear = False  # has its own Clear (URL + local file)

    def __init__(self, master, cfg):
        self.local_file: Path | None = None
        super().__init__(master, cfg)

    def _build_options(self, parent):
        parent.columnconfigure(0, weight=1)
        file_row = ctk.CTkFrame(parent, fg_color="transparent")
        file_row.grid(row=0, column=0, sticky="ew")
        file_row.columnconfigure(0, weight=1)
        self.file_lbl = ctk.CTkLabel(file_row, text=NO_FILE_TEXT, anchor="w")
        self.file_lbl.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(file_row, text="Browse file", width=100, command=self._pick_file).grid(row=0, column=1, padx=4)
        ctk.CTkButton(file_row, text="Clear", width=60, fg_color="gray", command=self._clear_file).grid(row=0, column=2)

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, pady=(8, 0), sticky="ew")
        ctk.CTkLabel(row, text="Whisper model:").pack(side="left")
        self.model = ctk.CTkOptionMenu(row, values=MODELS, width=110)
        self.model.set(self.cfg["model"] if self.cfg["model"] in MODELS else "small")
        self.model.pack(side="left", padx=8)
        ctk.CTkLabel(row, text="Language:").pack(side="left", padx=(8, 0))
        self.language = ctk.CTkOptionMenu(row, values=list(LANGUAGES), width=110)
        self.language.set(self.cfg["language"] if self.cfg["language"] in LANGUAGES else "Auto")
        self.language.pack(side="left", padx=8)
        self.md_var = ctk.BooleanVar(value=self.cfg["markdown"])
        self.pdf_var = ctk.BooleanVar(value=self.cfg["pdf"])
        ctk.CTkCheckBox(row, text="Markdown", variable=self.md_var, width=20).pack(side="left", padx=8)
        ctk.CTkCheckBox(row, text="PDF", variable=self.pdf_var, width=20).pack(side="left", padx=8)

        sub_row = ctk.CTkFrame(parent, fg_color="transparent")
        sub_row.grid(row=2, column=0, pady=(8, 0), sticky="ew")
        self.sub_var = ctk.BooleanVar(value=bool(self.cfg["subtitles"]))
        ctk.CTkCheckBox(sub_row, text="Subtitles", variable=self.sub_var, width=20,
                        command=self._toggle_subs).pack(side="left")
        ctk.CTkLabel(sub_row, text="Translate to:").pack(side="left", padx=(8, 0))
        self.sub_target = ctk.CTkOptionMenu(sub_row, values=list(translator.TARGETS), width=170)
        self.sub_target.set(self.cfg["sub_target"] if self.cfg["sub_target"] in translator.TARGETS
                            else translator.ORIGINAL)
        self.sub_target.pack(side="left", padx=8)
        ctk.CTkLabel(sub_row, text="Video:").pack(side="left", padx=(8, 0))
        self.sub_video = ctk.CTkOptionMenu(sub_row, values=SUB_VIDEO_MODES, width=180)
        self.sub_video.set(self.cfg["sub_video"] if self.cfg["sub_video"] in SUB_VIDEO_MODES else SRT_ONLY)
        self.sub_video.pack(side="left", padx=8)
        self._toggle_subs()

    def _toggle_subs(self):
        state = "normal" if self.sub_var.get() else "disabled"
        self.sub_target.configure(state=state)
        self.sub_video.configure(state=state)

    def _pick_file(self):
        p = filedialog.askopenfilename(filetypes=MEDIA_TYPES)
        if p:
            self.local_file = Path(p)
            self.file_lbl.configure(text=f"Local file: {self.local_file.name}")

    def _clear_file(self):
        self.url.delete(0, "end")
        self.local_file = None
        self.file_lbl.configure(text=NO_FILE_TEXT)

    def _validate(self, url):
        if not url and not self.local_file:
            return "Paste a URL or choose a local file."
        subs = self.sub_var.get()
        if not (self.md_var.get() or self.pdf_var.get() or subs):
            return "Tick Markdown, PDF and/or Subtitles."
        if (subs and self.sub_video.get() != SRT_ONLY and self.local_file
                and self.local_file.suffix.lower() not in VIDEO_EXTS):
            return "Embed/Burn needs a video file or a URL."
        return None

    def _args(self):
        return (self.model.get(), self.md_var.get(), self.pdf_var.get(), self.local_file,
                LANGUAGES[self.language.get()], self.sub_var.get(), self.sub_target.get(),
                self.sub_video.get())

    def collect_cfg(self):
        return {**super().collect_cfg(), "model": self.model.get(), "language": self.language.get(),
                "markdown": self.md_var.get(), "pdf": self.pdf_var.get(),
                "subtitles": self.sub_var.get(), "sub_target": self.sub_target.get(),
                "sub_video": self.sub_video.get()}

    @staticmethod
    def _lang_code(target, detected):
        if target == translator.ORIGINAL:
            return detected or "und"
        if target == translator.SERBIAN_LATIN:
            return "sr-Latn"
        nllb = translator.TARGETS[target]
        for iso, code in translator.WHISPER_TO_NLLB.items():
            if code == nllb:
                return iso
        return nllb.split("_")[0]

    def _run(self, url, out, model, md, pdf, local_file, language, subs=False,
             target=translator.ORIGINAL, sub_video=SRT_ONLY):
        saved = []
        with tempfile.TemporaryDirectory(prefix="yt-tool-") as tmp:
            tmp = Path(tmp)
            want_video = subs and sub_video != SRT_ONLY
            video_src = None
            if local_file:
                src, title, source = local_file, local_file.stem, str(local_file)
                video_src = local_file
            elif want_video:
                self._say("Downloading video for subtitles...")
                src, title = downloader.download_video(url, tmp, lambda v: self._prog(v * 0.1))
                source, video_src = url, src
            else:
                self._say("Downloading audio for transcription...")
                src, title = downloader.download_audio_raw(url, tmp, lambda v: self._prog(v * 0.1))
                source = url
            self._say("Preparing audio...")
            media = audio_prep.prepare(src, tmp, self._say)
            self._say("Transcribing...")
            t = transcribe(media, model, lambda v: self._prog(0.1 + v * 0.5), self._say, language)
            base = out / downloader.safe_name(title)
            if md:
                saved.append(exporter.write_markdown(t, title, source, base.with_suffix(".md")))
            if pdf:
                saved.append(exporter.write_pdf(t, title, source, base.with_suffix(".pdf")))
            if subs:
                segs = t.segments
                if target != translator.ORIGINAL:
                    self._say(f"Translating to {target}...")
                    segs = translator.translate_segments(segs, t.language, target,
                                                         lambda v: self._prog(0.6 + v * 0.25), self._say)
                self._prog(0.85)
                lang = self._lang_code(target, t.language)
                stem = downloader.safe_name(title) + "." + lang
                srt = subtitles.write_srt(subtitles.to_cues(segs), out / (stem + ".srt"))
                saved.append(srt)
                if sub_video == EMBED:
                    saved.append(subtitles.embed(video_src, srt, out / (stem + ".mp4"), lang.split("-")[0],
                                                 self._say))
                elif sub_video == BURN:
                    dur = max((s.end for s in t.segments), default=None)
                    saved.append(subtitles.burn(video_src, srt, out / (stem + ".burned.mp4"), dur,
                                                lambda v: self._prog(0.85 + v * 0.15), self._say))
                self._prog(1.0)
        for p in saved:
            self._say(f"Saved: {p}")
        return "Saved:" + chr(10) + chr(10).join(str(p) for p in saved)
