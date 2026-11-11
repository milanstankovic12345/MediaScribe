import os
from datetime import date
from pathlib import Path

from app.transcriber import Transcript


def fmt_time(seconds: float) -> str:
    """Format seconds as MM:SS, or H:MM:SS past one hour."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def to_markdown(t: Transcript, title: str, source: str, translated_from: str | None = None) -> str:
    """Render a transcript as Markdown with timestamped paragraphs."""
    lines = [f"# {title}", "",
             f"- Source: {source}",
             f"- Date: {date.today().isoformat()}",
             f"- Language: {t.language}"]
    if translated_from:
        lines.append(f"- Translated from: {translated_from}")
    lines.append("")
    lines += [f"**[{fmt_time(s.start)}]** {s.text}" + "\n" for s in t.segments]
    return "\n".join(lines)


def write_markdown(t: Transcript, title: str, source: str, path: Path,
                   translated_from: str | None = None) -> Path:
    """Write the transcript as a UTF-8 Markdown file and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_markdown(t, title, source, translated_from), encoding="utf-8")
    return path


def _find_font() -> str | None:
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def write_pdf(t: Transcript, title: str, source: str, path: Path,
              translated_from: str | None = None) -> Path:
    """Write the transcript as a PDF (Unicode font if available) and return its path."""
    from fpdf import FPDF

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    font = _find_font()
    if font:
        pdf.add_font("body", "", font)
        family = "body"
    else:
        family = "Helvetica"  # latin-1 only fallback

    def safe(text: str) -> str:
        return text if font else text.encode("latin-1", "replace").decode("latin-1")

    pdf.set_font(family, size=16)
    pdf.multi_cell(0, 9, safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, size=9)
    header = f"Source: {source}\nDate: {date.today().isoformat()}\nLanguage: {t.language}"
    if translated_from:
        header += f"\nTranslated from: {translated_from}"
    pdf.multi_cell(0, 5, safe(header), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font(family, size=11)
    for s in t.segments:
        pdf.multi_cell(0, 6, safe(f"[{fmt_time(s.start)}] {s.text}"),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    pdf.output(str(path))
    return path
