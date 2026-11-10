import tempfile
import webbrowser
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app import audio_prep, downloader, exporter, gemini, settings, subtitles, translator
from app.screens.base import Screen
from app.transcriber import LANGUAGES, MODELS, transcribe

MEDIA_TYPES = [("Audio/Video", "*.mp3 *.m4a *.wav *.flac *.ogg *.opus *.mp4 *.mkv *.webm *.mov *.avi"),
               ("All files", "*.*")]
VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
SRT_ONLY, EMBED, BURN = "SRT file only", "Embed into video (fast)", "Burn into video (slow)"
SUB_VIDEO_MODES = [SRT_ONLY, EMBED, BURN]
GEMINI_HINT = "Gemini is not connected. Get a free API key, then paste it in Settings."
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
        self.sub_target = ctk.CTkOptionMenu(sub_row, values=list(translator.TARGETS), width=170,
                                         command=lambda _v: self._update_guidance())
        self.sub_target.set(self.cfg["sub_target"] if self.cfg["sub_target"] in translator.TARGETS
                            else translator.ORIGINAL)
        self.sub_target.pack(side="left", padx=8)
        ctk.CTkLabel(sub_row, text="Video:").pack(side="left", padx=(8, 0))
        self.sub_video = ctk.CTkOptionMenu(sub_row, values=SUB_VIDEO_MODES, width=180)
        self.sub_video.set(self.cfg["sub_video"] if self.cfg["sub_video"] in SUB_VIDEO_MODES else SRT_ONLY)
        self.sub_video.pack(side="left", padx=8)

        eng_row = ctk.CTkFrame(parent, fg_color="transparent")
        eng_row.grid(row=3, column=0, pady=(8, 0), sticky="ew")
        ctk.CTkLabel(eng_row, text="Translator:").pack(side="left")
        self.engine = ctk.CTkOptionMenu(eng_row, values=translator.ENGINES, width=230,
                                        command=lambda _v: self._update_guidance())
        self.engine.set(self.cfg["translator"] if self.cfg["translator"] in translator.ENGINES
                        else translator.LOCAL_ENGINE)
        self.engine.pack(side="left", padx=8)

        self.guidance = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(self.guidance, text=GEMINI_HINT, text_color=("#b45309", "#fbbf24")).pack(side="left")
        ctk.CTkButton(self.guidance, text="Get API key", width=100,
                      command=lambda: webbrowser.open(gemini.API_KEY_URL)).pack(side="left", padx=8)
        ctk.CTkButton(self.guidance, text="Open Settings", width=110,
                      command=lambda: self.master.show("settings")).pack(side="left")
        self.guidance.grid(row=4, column=0, pady=(8, 0), sticky="ew")
        self._toggle_subs()

    def _toggle_subs(self):
        state = "normal" if self.sub_var.get() else "disabled"
        self.sub_target.configure(state=state)
        self.sub_video.configure(state=state)
        self.engine.configure(state=state)
        self._update_guidance()

    def _gemini_missing(self) -> bool:
        return (self.sub_var.get() and self.engine.get() == translator.GEMINI_ENGINE
                and self.sub_target.get() != translator.ORIGINAL
                and not settings.get_gemini_key(self.cfg))

    def _update_guidance(self):
        if self._gemini_missing():
            self.guidance.grid()
        else:
            self.guidance.grid_remove()

    def on_show(self):
        """Called by App.show: re-check the Gemini key (it may have changed in Settings)."""
        self._update_guidance()

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
        engine = getattr(self, "engine", None)
        if (subs and engine is not None and engine.get() == translator.GEMINI_ENGINE
                and self.sub_target.get() != translator.ORIGINAL
                and not settings.get_gemini_key(self.cfg)):
            return GEMINI_HINT
        return None

    def _args(self):
        return (self.model.get(), self.md_var.get(), self.pdf_var.get(), self.local_file,
                LANGUAGES[self.language.get()], self.sub_var.get(), self.sub_target.get(),
                self.sub_video.get(), self.engine.get(), settings.get_gemini_key(self.cfg),
                self.cfg.get("gemini_model") or None)

    def collect_cfg(self):
        return {**super().collect_cfg(), "model": self.model.get(), "language": self.language.get(),
                "markdown": self.md_var.get(), "pdf": self.pdf_var.get(),
                "subtitles": self.sub_var.get(), "sub_target": self.sub_target.get(),
                "sub_video": self.sub_video.get(), "translator": self.engine.get()}

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
             target=translator.ORIGINAL, sub_video=SRT_ONLY, engine=translator.LOCAL_ENGINE,
             api_key="", gemini_model=None):
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
                    cb = lambda v: self._prog(0.6 + v * 0.25)  # noqa: E731
                    if engine == translator.GEMINI_ENGINE:
                        segs = translator.translate(segs, t.language, target, engine, api_key,
                                                    cb, self._say, gemini_model)
                    else:
                        segs = translator.translate_segments(segs, t.language, target, cb, self._say)
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
