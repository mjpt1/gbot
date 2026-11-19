from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "products"

SAMPLES = [
    ("beginner-chords.pdf", "Guitarine — Beginner Chords"),
    ("advanced-chords.pdf", "Guitarine — Advanced Chords"),
    ("iranian-pop.pdf", "Guitarine — Iranian Pop Chords"),
]


def make_pdf(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 80, title)
    c.setFont("Helvetica", 12)
    c.drawCentredString(
        width / 2,
        height - 120,
        "Sample product PDF for Guitarine offline bot.",
    )
    c.drawCentredString(
        width / 2,
        height - 150,
        "Replace this file with your real chord sheet.",
    )
    c.showPage()
    c.setFont("Helvetica", 14)
    c.drawString(72, height - 100, "Page 2 — practice notes")
    c.showPage()
    c.save()
    print(f"wrote {path}")


def main() -> None:
    for name, title in SAMPLES:
        make_pdf(OUT / name, title)


if __name__ == "__main__":
    main()
