"""Background ticker that runs due GEO watch queries."""
from __future__ import annotations

import threading
import time
from datetime import datetime

from core.db_manager import SharedSessionLocal
from database.models import GeoWatchQuery


_stop = threading.Event()
_thread: threading.Thread | None = None


def _due_watches(db):
    now = datetime.now()
    return (
        db.query(GeoWatchQuery)
        .filter(GeoWatchQuery.enabled == True)  # noqa: E712
        .filter((GeoWatchQuery.next_run_at == None) | (GeoWatchQuery.next_run_at <= now))  # noqa: E711
        .all()
    )


def tick_once() -> int:
    """Run every due watch once. Returns how many were dispatched."""
    from routers.branding_router import dispatch_watch

    db = SharedSessionLocal()
    count = 0
    try:
        for watch in _due_watches(db):
            try:
                dispatch_watch(db, watch)
                count += 1
            except Exception as exc:
                print(f"[GEO Scheduler] watch #{watch.id} failed: {exc}")
        db.commit()
    finally:
        db.close()
    return count


def _loop(interval_seconds: int = 60):
    print(f"[GEO Scheduler] started, tick every {interval_seconds}s")
    while not _stop.is_set():
        try:
            n = tick_once()
            if n:
                print(f"[GEO Scheduler] dispatched {n} watch(es)")
        except Exception as exc:
            print(f"[GEO Scheduler] tick error: {exc}")
        _stop.wait(interval_seconds)
    print("[GEO Scheduler] stopped")


def start(interval_seconds: int = 60):
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, args=(interval_seconds,), daemon=True, name="geo-scheduler")
    _thread.start()


def stop():
    _stop.set()
