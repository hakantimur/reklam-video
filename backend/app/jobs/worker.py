"""Background worker thread: repeatedly claims and runs one job at a time.

Spec §6.2: FastAPI itself must not do long-running work; a worker executes
jobs out-of-band. `app/jobs/handlers.py` designed `run_worker_once` to be
driven by exactly this kind of loop but didn't start one — nothing was
actually consuming the queue until this module's thread is started from
`app.main`.
"""

import logging
import threading
import time

from app.core.db import SessionLocal
from app.jobs.handlers import run_worker_once

logger = logging.getLogger(__name__)

_POLL_INTERVAL_S = 1.0
_started = False
_stop_event = threading.Event()


def _worker_loop() -> None:
    while not _stop_event.is_set():
        session = SessionLocal()
        try:
            job = run_worker_once(session)
        except Exception:  # noqa: BLE001 - the worker thread must never die silently
            logger.exception("Unhandled error in job worker loop")
            job = None
        finally:
            session.close()

        if job is None:
            _stop_event.wait(_POLL_INTERVAL_S)


def start_background_worker() -> None:
    """Idempotent: safe to call more than once (e.g. across app reloads)."""
    global _started
    if _started:
        return
    _started = True
    _stop_event.clear()
    thread = threading.Thread(target=_worker_loop, name="lad-job-worker", daemon=True)
    thread.start()


def stop_background_worker() -> None:
    global _started
    _stop_event.set()
    _started = False
