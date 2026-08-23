from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class SampleStore:
    def __init__(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS samples (
                ts REAL NOT NULL,
                iface TEXT NOT NULL,
                rx_bps INTEGER NOT NULL,
                tx_bps INTEGER NOT NULL
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_samples_iface_ts ON samples(iface, ts)"
        )
        self.conn.commit()

    def insert_many(self, ts: float, rows: list[dict[str, Any]]) -> None:
        with self._lock:
            self.conn.executemany(
                "INSERT INTO samples(ts, iface, rx_bps, tx_bps) VALUES (?,?,?,?)",
                [(ts, r["name"], r["rx_bps"], r["tx_bps"]) for r in rows],
            )
            self.conn.commit()

    def prune(self, keep_seconds: int = 6 * 3600) -> None:
        cutoff = time.time() - keep_seconds
        with self._lock:
            self.conn.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))
            self.conn.commit()

    def history(self, iface: str, since: float) -> list[dict[str, Any]]:
        with self._lock:
            cur = self.conn.execute(
                "SELECT ts, rx_bps, tx_bps FROM samples WHERE iface=? AND ts>=? ORDER BY ts",
                (iface, since),
            )
            return [{"t": t, "rx": rx, "tx": tx} for t, rx, tx in cur.fetchall()]
