"""Regression coverage for a real, live-discovered bug: a multi-row write
(`POST .../revisions/{id}/variation`) returned a genuine HTTP 500 once
against the real Synova project, then succeeded on an immediate identical
retry with no code change — consistent with SQLite's default
`busy_timeout=0` making a writer fail instantly instead of waiting the
moment it collides with the background job worker (or any other
concurrent writer) holding the write lock. `app.core.db.make_engine` now
sets `PRAGMA busy_timeout=5000` on every connection; these tests prove
that pragma is actually applied and that it does what it's for."""

import sqlite3
import threading
import time

from app.core.db import _db_path, engine


def test_app_engine_connections_have_busy_timeout_set():
    with engine.connect() as conn:
        value = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
    assert value == 5000


def test_busy_timeout_lets_a_blocked_writer_wait_instead_of_failing_immediately():
    db_path = str(_db_path())
    errors: list[Exception] = []

    def slow_writer() -> None:
        conn = sqlite3.connect(db_path, timeout=0)
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("BEGIN IMMEDIATE")
        time.sleep(0.5)
        conn.commit()
        conn.close()

    writer_thread = threading.Thread(target=slow_writer)
    writer_thread.start()
    time.sleep(0.1)  # let slow_writer grab the write lock first

    blocked_conn = sqlite3.connect(db_path, timeout=0)
    blocked_conn.execute("PRAGMA busy_timeout=5000")
    try:
        blocked_conn.execute("BEGIN IMMEDIATE")
        blocked_conn.commit()
    except sqlite3.OperationalError as exc:
        errors.append(exc)
    finally:
        blocked_conn.close()
    writer_thread.join()

    assert not errors, f"a busy_timeout-configured writer should wait for the lock, not fail: {errors}"


def test_without_busy_timeout_a_blocked_writer_fails_immediately():
    """Sanity check that the scenario above is real: with `timeout=0` and
    no busy_timeout pragma (sqlite3's own pre-3.x-era default), the same
    collision does raise `OperationalError` — proving the fix in
    `make_engine` is what closes the gap, not some other factor."""

    db_path = str(_db_path())
    errors: list[Exception] = []

    def slow_writer() -> None:
        conn = sqlite3.connect(db_path, timeout=0)
        conn.execute("PRAGMA busy_timeout=0")
        conn.execute("BEGIN IMMEDIATE")
        time.sleep(0.5)
        conn.commit()
        conn.close()

    writer_thread = threading.Thread(target=slow_writer)
    writer_thread.start()
    time.sleep(0.1)

    blocked_conn = sqlite3.connect(db_path, timeout=0)
    blocked_conn.execute("PRAGMA busy_timeout=0")
    try:
        blocked_conn.execute("BEGIN IMMEDIATE")
        blocked_conn.commit()
    except sqlite3.OperationalError as exc:
        errors.append(exc)
    finally:
        blocked_conn.close()
    writer_thread.join()

    assert errors, "expected an immediate 'database is locked' failure with busy_timeout=0"
