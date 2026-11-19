"""
Run the web admin panel only (no Telegram bot polling).

Use on VPS for testing, or when the bot runs elsewhere.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn

from bot.config import load_config

if __name__ == "__main__":
    config = load_config()
    for d in (
        config.branding_dir,
        config.products_dir,
        config.receipts_dir,
        config.protected_dir,
    ):
        d.mkdir(parents=True, exist_ok=True)

    uvicorn.run(
        "web.main:app",
        host=config.web_host,
        port=config.web_port,
        log_level="info",
    )
