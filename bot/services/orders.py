from __future__ import annotations

import secrets
import string
from datetime import datetime


def generate_tracking_code() -> str:
    stamp = datetime.now().strftime("%y%m%d")
    suffix = "".join(secrets.choice(string.digits) for _ in range(4))
    return f"GTR-{stamp}-{suffix}"


def normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("98") and len(digits) >= 12:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    return digits
