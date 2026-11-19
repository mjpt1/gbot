from __future__ import annotations

import json
from typing import TypedDict

from bot.db.database import Database
from bot.keyboards.labels import BTN_CART, BTN_CHECKOUT, BTN_HELP, BTN_PRODUCTS

SETTING_MENU_ITEMS = "main_menu_items"

ACTION_PRODUCTS = "products"
ACTION_CART = "cart"
ACTION_CHECKOUT = "checkout"
ACTION_HELP = "help"
ACTION_MESSAGE = "message"

ACTION_LABELS = {
    ACTION_PRODUCTS: "محصولات",
    ACTION_CART: "سبد خرید",
    ACTION_CHECKOUT: "تسویه حساب",
    ACTION_HELP: "راهنما",
    ACTION_MESSAGE: "پیام سفارشی",
}


class MenuItem(TypedDict):
    id: str
    label: str
    action: str
    response_text: str


DEFAULT_MENU_ITEMS: tuple[MenuItem, ...] = (
    {"id": "products", "label": BTN_PRODUCTS, "action": ACTION_PRODUCTS, "response_text": ""},
    {"id": "cart", "label": BTN_CART, "action": ACTION_CART, "response_text": ""},
    {"id": "checkout", "label": BTN_CHECKOUT, "action": ACTION_CHECKOUT, "response_text": ""},
    {"id": "help", "label": BTN_HELP, "action": ACTION_HELP, "response_text": ""},
)


def default_menu_items() -> list[MenuItem]:
    return [item.copy() for item in DEFAULT_MENU_ITEMS]


def _clean_item(value: object) -> MenuItem | None:
    if not isinstance(value, dict):
        return None
    item_id = str(value.get("id", "")).strip()
    label = str(value.get("label", "")).strip()
    action = str(value.get("action", "")).strip()
    response_text = str(value.get("response_text", "")).strip()
    if not item_id or not label or action not in ACTION_LABELS:
        return None
    if action == ACTION_MESSAGE and not response_text:
        return None
    return {
        "id": item_id[:40],
        "label": label[:64],
        "action": action,
        "response_text": response_text[:4000],
    }


def parse_menu_items(raw: str) -> list[MenuItem]:
    if not raw:
        return default_menu_items()
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default_menu_items()
    if not isinstance(payload, list):
        return default_menu_items()

    items: list[MenuItem] = []
    seen_ids: set[str] = set()
    seen_labels: set[str] = set()
    for value in payload:
        item = _clean_item(value)
        if not item or item["id"] in seen_ids or item["label"] in seen_labels:
            continue
        seen_ids.add(item["id"])
        seen_labels.add(item["label"])
        items.append(item)
    return items


async def get_menu_items(db: Database) -> list[MenuItem]:
    raw = await db.get_setting(SETTING_MENU_ITEMS, "")
    return parse_menu_items(raw)


async def save_menu_items(db: Database, items: list[MenuItem]) -> None:
    cleaned = parse_menu_items(json.dumps(items, ensure_ascii=False))
    await db.set_setting(
        SETTING_MENU_ITEMS,
        json.dumps(cleaned, ensure_ascii=False, separators=(",", ":")),
    )