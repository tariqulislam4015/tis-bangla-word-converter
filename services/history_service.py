"""Conversion history stored in a local SQLite database."""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAX_TEXT = 50_000      # characters of text kept per text-mode entry
MAX_ENTRIES = 500


@dataclass
class HistoryEntry:
    id: int
    timestamp: str
    mode: str          # "text" | "docx" | "batch" | "txt"
    direction: str     # "U2B" | "B2U"
    source: str        # file path or text preview
    output: str        # file path or text preview
    chars: int
    status: str        # "ok" | "error" | "cancelled"
    detail: str
    input_text: str = ""
    output_text: str = ""


class HistoryService:
    def __init__(self, path: Path | str):
        self.path = str(path)
        self._lock = threading.Lock()
        try:
            self._conn = sqlite3.connect(self.path, check_same_thread=False)
            self._init()
        except sqlite3.DatabaseError:
            # corrupted database: start fresh in memory rather than crash
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._init()

    def _init(self) -> None:
        with self._conn:
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, mode TEXT NOT NULL, direction TEXT NOT NULL,
                    source TEXT, output TEXT, chars INTEGER, status TEXT, detail TEXT,
                    input_text TEXT, output_text TEXT)""")

    def add(self, mode: str, direction: str, source: str, output: str, chars: int,
            status: str = "ok", detail: str = "", input_text: str = "",
            output_text: str = "") -> int:
        ts = datetime.now().isoformat(timespec="seconds")
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO history (ts, mode, direction, source, output, chars, status, detail,"
                " input_text, output_text) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (ts, mode, direction, source[:1000], output[:1000], int(chars), status, detail[:4000],
                 input_text[:MAX_TEXT], output_text[:MAX_TEXT]))
            self._conn.execute(
                "DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)",
                (MAX_ENTRIES,))
            return int(cur.lastrowid)

    def list(self, limit: int = 200) -> list[HistoryEntry]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, ts, mode, direction, source, output, chars, status, detail,"
                " input_text, output_text FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [HistoryEntry(*[r if r is not None else "" for r in row]) for row in rows]

    def get(self, entry_id: int) -> HistoryEntry | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, ts, mode, direction, source, output, chars, status, detail,"
                " input_text, output_text FROM history WHERE id=?", (entry_id,)).fetchone()
        return HistoryEntry(*[r if r is not None else "" for r in row]) if row else None

    def clear(self) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM history")

    def stats(self) -> dict[str, int]:
        with self._lock:
            total, chars = self._conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(chars),0) FROM history WHERE status='ok'").fetchone()
        return {"conversions": int(total), "characters": int(chars)}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
