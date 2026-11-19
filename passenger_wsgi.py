"""
cPanel (Passenger/LiteSpeed) entry point for the Guitarineh web admin panel.

cPanel → Setup Python App:
  - Application root:         guitarine-bot
  - Application URL:          telegram-guitarineh.ir   (no path)
  - Application startup file: passenger_wsgi.py
  - Application entry point:  application

Two things this file has to work around:

1. Passenger speaks WSGI, FastAPI speaks ASGI. a2wsgi bridges them, but it
   only forwards HTTP requests -- it never runs the ASGI *lifespan* protocol.
   `web.main`'s startup hook (which opens the database and builds the Telegram
   bot) therefore has to be driven by hand, on the same event loop a2wsgi
   uses for requests. Without it every request 500s: `app.state.db` is unset.

2. LiteSpeed loads this module once and then *forks* worker processes.
   Threads do not survive fork, so a loop thread started at import time is
   dead in the worker and every request blocks forever waiting on it (the
   symptom is a 120s "Request Timeout" with no traceback). So the loop, the
   lifespan and the WSGI wrapper are built lazily on the first request in
   each process, keyed by PID.

Requires: pip install -r requirements-web.txt
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import sys
import threading

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from a2wsgi import ASGIMiddleware

from web.main import app

logger = logging.getLogger("guitarine.passenger")

STARTUP_TIMEOUT = float(os.getenv("WEB_STARTUP_TIMEOUT", "60"))

# LiteSpeed's LSAPI swallows whatever the app writes to stderr, so an
# unhandled exception reaches the browser as a bare "Internal Server Error"
# with no trace anywhere. Log to a file we control instead.
ERROR_LOG = os.path.join(ROOT, "data", "panel-error.log")


def _install_file_logging() -> None:
    root = logging.getLogger()
    if any(getattr(h, "_guitarine", False) for h in root.handlers):
        return
    os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)
    handler = logging.FileHandler(ERROR_LOG, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    handler._guitarine = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    if root.level > logging.INFO or root.level == logging.NOTSET:
        root.setLevel(logging.INFO)


_install_file_logging()


class LifespanRunner:
    """Run an ASGI app's lifespan on `loop` and keep it running."""

    def __init__(self, asgi_app, loop):
        self._app = asgi_app
        self._loop = loop
        self._ready = threading.Event()
        self._future = None
        self.error = None

    async def _run(self):
        queue = asyncio.Queue()
        await queue.put({"type": "lifespan.startup"})

        async def receive():
            return await queue.get()

        async def send(message):
            kind = message["type"]
            if kind == "lifespan.startup.complete":
                self._ready.set()
            elif kind == "lifespan.startup.failed":
                self.error = message.get("message") or "startup failed"
                self._ready.set()

        scope = {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.0"}}
        try:
            # Blocks until shutdown — the app stays "inside" its lifespan here.
            await self._app(scope, receive, send)
        except Exception as exc:
            self.error = "%s: %s" % (type(exc).__name__, exc)
            logger.exception("lifespan crashed")
        finally:
            self._ready.set()

    def start(self, timeout):
        self._future = asyncio.run_coroutine_threadsafe(self._run(), self._loop)
        if not self._ready.wait(timeout):
            raise RuntimeError("web app did not start within %.0fs" % timeout)
        if self.error:
            raise RuntimeError("web app startup failed: %s" % self.error)


_init_lock = threading.Lock()
_state = {"pid": None, "wsgi": None, "lifespan": None}


def _build():
    loop = asyncio.new_event_loop()
    threading.Thread(
        target=loop.run_forever, name="guitarine-asgi", daemon=True
    ).start()
    runner = LifespanRunner(app, loop)
    runner.start(STARTUP_TIMEOUT)
    logger.info("Guitarineh admin panel ready in pid %s", os.getpid())
    return ASGIMiddleware(app, loop=loop), runner


def _wsgi():
    pid = os.getpid()
    if _state["wsgi"] is not None and _state["pid"] == pid:
        return _state["wsgi"]
    with _init_lock:
        if _state["wsgi"] is None or _state["pid"] != pid:
            _state["wsgi"], _state["lifespan"] = _build()
            _state["pid"] = pid
    return _state["wsgi"]


_BODYLESS_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def _buffer_body(environ):
    """Give a2wsgi a body it can measure.

    LiteSpeed hands HTTP/2 requests to LSAPI without CONTENT_LENGTH. a2wsgi
    sizes the request body purely from that header, so it forwards an *empty*
    body to the ASGI app: a file upload from a browser (HTTP/2) died with a
    500 while the identical request over HTTP/1.1 worked. Read the stream once
    and set the header ourselves.
    """
    if environ.get("CONTENT_LENGTH"):
        return environ
    if environ.get("REQUEST_METHOD", "GET").upper() in _BODYLESS_METHODS:
        return environ
    stream = environ.get("wsgi.input")
    if stream is None:
        return environ
    body = stream.read()
    environ["wsgi.input"] = io.BytesIO(body)
    environ["CONTENT_LENGTH"] = str(len(body))
    return environ


def application(environ, start_response):
    # A generator, so failures raised while the response is being iterated
    # are caught here too — that is where ASGI errors actually surface.
    try:
        for chunk in _wsgi()(_buffer_body(environ), start_response):
            yield chunk
    except Exception:
        logger.exception(
            "request failed: %s %s (proto=%s, len=%s, type=%s)",
            environ.get("REQUEST_METHOD"),
            environ.get("PATH_INFO"),
            environ.get("SERVER_PROTOCOL"),
            environ.get("CONTENT_LENGTH"),
            environ.get("CONTENT_TYPE"),
        )
        raise
