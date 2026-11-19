from __future__ import annotations

import io
from pathlib import Path

import pikepdf
from pikepdf import Encryption, Permissions
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas


def _make_watermark_pdf(width: float, height: float, text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.saveState()
    c.setFillColor(Color(0.55, 0.55, 0.55, alpha=0.28))
    c.setFont("Helvetica", 14)
    # Diagonal watermark across the page
    c.translate(width / 2, height / 2)
    c.rotate(35)
    label = text[:80]
    c.drawCentredString(0, 20, label)
    c.drawCentredString(0, -20, "Guitarineh — Licensed Copy")
    c.restoreState()
    c.showPage()
    c.save()
    return buf.getvalue()


class SourcePdfLocked(Exception):
    """The product PDF is itself password-protected, so we cannot process it."""


def check_pdf(path: Path) -> str | None:
    """None when the PDF can be watermarked and re-encrypted.

    Otherwise a reason: `"locked"` (carries its own password) or `"corrupt"`
    (not a PDF we can parse). Checking at upload matters because the failure
    used to surface only when an order was approved — after the customer had
    paid — and as a misleading "product file not found".
    """
    try:
        with pikepdf.open(path):
            return None
    except pikepdf.PasswordError:
        return "locked"
    except Exception:
        return "corrupt"


def protect_pdf(
    source: Path,
    dest: Path,
    *,
    user_password: str,
    owner_password: str,
    watermark_text: str,
) -> Path:
    """Password-protect PDF, disable copy/edit, add dynamic watermark."""
    if not source.exists():
        raise FileNotFoundError(str(source))

    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        opened = pikepdf.open(source)
    except pikepdf.PasswordError as exc:
        raise SourcePdfLocked(str(source)) from exc

    with opened as pdf:
        for page in pdf.pages:
            box = page.mediabox
            width = float(box[2] - box[0])
            height = float(box[3] - box[1])
            wm_bytes = _make_watermark_pdf(width, height, watermark_text)
            with pikepdf.open(io.BytesIO(wm_bytes)) as wm_pdf:
                wm_page = wm_pdf.pages[0]
                page.add_overlay(wm_page)

        perms = Permissions(
            accessibility=True,
            extract=False,
            modify_annotation=False,
            modify_assembly=False,
            modify_form=False,
            modify_other=False,
            print_lowres=True,
            print_highres=True,
        )
        pdf.save(
            dest,
            encryption=Encryption(
                user=user_password,
                owner=owner_password,
                allow=perms,
                R=6,
            ),
        )
    return dest
