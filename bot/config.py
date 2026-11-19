from __future__ import annotations



import os

from dataclasses import dataclass

from pathlib import Path



from dotenv import load_dotenv



BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")





def _parse_admin_ids(raw: str) -> frozenset[int]:

    ids: set[int] = set()

    for part in raw.replace(";", ",").split(","):

        part = part.strip()

        if part:

            ids.add(int(part))

    return frozenset(ids)





@dataclass(frozen=True, slots=True)

class Config:

    bot_token: str

    admin_ids: frozenset[int]

    bank_card: str

    bank_card_holder: str

    owner_pdf_password: str

    db_path: Path

    products_dir: Path

    receipts_dir: Path

    protected_dir: Path

    branding_dir: Path

    web_admin_user: str

    web_admin_password: str

    web_secret_key: str

    web_host: str

    web_port: int

    web_base_url: str

    telegram_proxy: str





def load_config() -> Config:

    token = os.getenv("BOT_TOKEN", "").strip()

    if not token:

        raise RuntimeError("BOT_TOKEN is required in .env")



    admin_raw = os.getenv("ADMIN_IDS", "").strip()

    if not admin_raw:

        raise RuntimeError("ADMIN_IDS is required in .env")



    bank_card = os.getenv("BANK_CARD", "").strip()

    if not bank_card:

        raise RuntimeError("BANK_CARD is required in .env")



    web_user = os.getenv("WEB_ADMIN_USER", "").strip()

    web_pass = os.getenv("WEB_ADMIN_PASSWORD", "").strip()

    if not web_user or not web_pass:

        raise RuntimeError("WEB_ADMIN_USER and WEB_ADMIN_PASSWORD are required in .env")



    web_secret = os.getenv("WEB_SECRET_KEY", "").strip() or secrets_fallback()

    web_host = os.getenv("WEB_HOST", "127.0.0.1").strip() or "127.0.0.1"

    web_port = int(os.getenv("WEB_PORT", "8080").strip() or "8080")

    web_base = os.getenv("WEB_BASE_URL", f"http://{web_host}:{web_port}").strip()



    data_dir = BASE_DIR / "data"

    return Config(

        bot_token=token,

        admin_ids=_parse_admin_ids(admin_raw),

        bank_card=bank_card,

        bank_card_holder=os.getenv("BANK_CARD_HOLDER", "").strip(),

        owner_pdf_password=os.getenv("OWNER_PDF_PASSWORD", "guitarine-owner").strip()

        or "guitarine-owner",

        db_path=data_dir / "guitarine.db",

        products_dir=data_dir / "products",

        receipts_dir=data_dir / "receipts",

        protected_dir=data_dir / "protected",

        branding_dir=data_dir / "branding",

        web_admin_user=web_user,

        web_admin_password=web_pass,

        web_secret_key=web_secret,

        web_host=web_host,

        web_port=web_port,

        web_base_url=web_base.rstrip("/"),

        telegram_proxy=os.getenv("TELEGRAM_PROXY", "").strip(),

    )





def secrets_fallback() -> str:

    import secrets



    return secrets.token_hex(32)


