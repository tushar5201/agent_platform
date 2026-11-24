"""SQLite store for the per-user daily cap and the tool-call audit log."""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
  user_id TEXT NOT NULL, day TEXT NOT NULL, count INTEGER NOT NULL,
  PRIMARY KEY (user_id, day)
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, user_id TEXT NOT NULL,
  thread_id TEXT NOT NULL, tool TEXT NOT NULL, args TEXT NOT NULL,
  ok INTEGER NOT NULL, flagged INTEGER NOT NULL, ms INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_user ON audit (user_id, ts);
"""


class Store:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def open(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def hit_daily(self, user_id: str, cap: int) -> bool:
        """Count one chat for today (UTC). Returns False when the cap is already used up."""
        assert self.conn
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        cur = await self.conn.execute(
            "INSERT INTO usage (user_id, day, count) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, day) DO UPDATE SET count = count + 1 RETURNING count",
            (user_id, day),
        )
        (count,) = await cur.fetchone()
        await self.conn.commit()
        return count <= cap

    async def audit(self, *, user_id, thread_id, tool, args, ok, flagged, ms) -> None:
        assert self.conn
        await self.conn.execute(
            "INSERT INTO audit (ts, user_id, thread_id, tool, args, ok, flagged, ms) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (time.time(), user_id, thread_id, tool, json.dumps(args)[:500], int(ok),
             int(flagged), ms),
        )
        await self.conn.commit()

    async def recent_audit(self, user_id: str, limit: int = 20) -> list[dict]:
        assert self.conn
        cur = await self.conn.execute(
            "SELECT tool, args, ok, flagged, ms FROM audit WHERE user_id=? "
            "ORDER BY id DESC LIMIT ?", (user_id, limit))
        cols = ["tool", "args", "ok", "flagged", "ms"]
        return [dict(zip(cols, r, strict=True)) for r in await cur.fetchall()]
