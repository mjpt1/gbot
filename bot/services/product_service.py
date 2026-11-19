from __future__ import annotations

import re
import secrets
import shutil
from pathlib import Path

from bot.config import Config
from bot.db.database import Database


def _safe_filename(original: str) -> str:
    """ASCII-only name.

    `\\w` matches Persian letters, so the old pattern let non-ASCII names
    through — and the panel runs without a UTF-8 filesystem encoding, where
    creating such a file raises UnicodeEncodeError.
    """
    stem = Path(original).stem
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", stem)[:40].strip("_") or "product"
    return f"{safe}_{secrets.token_hex(4)}.pdf"


async def save_product_pdf(
    db: Database,
    config: Config,
    *,
    title: str,
    price: int,
    source: Path,
) -> int:
    config.products_dir.mkdir(parents=True, exist_ok=True)
    dest = config.products_dir / _safe_filename(source.name)
    shutil.copy2(source, dest)
    return await db.create_product(title, price, str(dest.resolve()))
