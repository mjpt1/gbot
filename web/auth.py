from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse

from bot.services.admin_credentials import get_password_hash, session_fingerprint

SESSION_KEY = "admin_logged_in"
SESSION_FINGERPRINT = "pw"


def url_prefix(request: Request) -> str:
    """Mount prefix, e.g. "/panel" when Passenger serves the app under a sub-path."""
    return request.scope.get("root_path", "").rstrip("/")


def redirect(request: Request, path: str, status_code: int = 303) -> RedirectResponse:
    """Redirect to an app-relative path, keeping the mount prefix intact."""
    return RedirectResponse(f"{url_prefix(request)}{path}", status_code=status_code)


def is_logged_in(request: Request) -> bool:
    return bool(request.session.get(SESSION_KEY))


async def current_fingerprint(request: Request) -> str:
    return session_fingerprint(
        await get_password_hash(request.app.state.db, request.app.state.config)
    )


async def require_login(request: Request) -> RedirectResponse | None:
    """Guard for every protected route.

    Besides the session flag it checks a fingerprint of the current password
    hash, so changing the password immediately invalidates sessions on other
    devices (and any session issued before this check existed).
    """
    if not is_logged_in(request):
        return redirect(request, "/login")
    if request.session.get(SESSION_FINGERPRINT) != await current_fingerprint(request):
        request.session.clear()
        return redirect(request, "/login?expired=1")
    return None
