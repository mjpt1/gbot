from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CheckoutStates(StatesGroup):
    waiting_receipt = State()


class AdminStates(StatesGroup):
    product_title = State()
    product_price = State()
    product_pdf = State()
    batch_collect = State()
    batch_title = State()
    batch_price = State()
    add_admin_id = State()
    settings_welcome = State()
    settings_menu = State()
    settings_logo = State()
