from __future__ import annotations

GLASS_LINE = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"
MUSIC_NOTES = ("🎸", "🎵", "🎶", "🎼", "🎹", "🥁")


def brand_banner(subtitle: str = "") -> str:
    lines = [
        "🎸 <b>گیتارینه</b> · Guitarineh 🎵",
        f"<i>{subtitle or 'آکوردها · پکیج‌ها · موسیقی'}</i>",
        GLASS_LINE,
    ]
    return "\n".join(lines)


def glass_card(title: str, body: str, icon: str = "✦") -> str:
    return (
        f"{icon} <b>{title}</b>\n"
        f"<blockquote>{body}</blockquote>"
    )


def music_icon(index: int) -> str:
    return MUSIC_NOTES[index % len(MUSIC_NOTES)]
