"""Anonymous usage statistics, persisted to Postgres.

Nothing here ever sees or stores the data a caller charts (values, labels,
titles) — only the shape of the request: chart type, style, size buckets,
success/failure.

Everything is best-effort and optional. ``Store.open(None)`` returns a
``Store`` with no database behind it, and every method on it is a no-op, so
the server behaves identically whether or not ``DATABASE_URL`` is set. A
failed insert is logged and swallowed — stats must never affect a tool result.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("asciicharts.store")

SCHEMA = """
CREATE TABLE IF NOT EXISTS chart_events (
    id                 BIGSERIAL PRIMARY KEY,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    chart_type         TEXT NOT NULL,
    style              TEXT NOT NULL DEFAULT '',
    mode               TEXT NOT NULL DEFAULT '',
    border             TEXT NOT NULL DEFAULT '',
    use_color          BOOLEAN NOT NULL DEFAULT false,
    series_count       INT NOT NULL DEFAULT 0,
    point_count_bucket TEXT NOT NULL DEFAULT '',
    output_size_bucket TEXT NOT NULL DEFAULT '',
    success            BOOLEAN NOT NULL,
    error_message      TEXT NOT NULL DEFAULT '',
    server_version     TEXT NOT NULL DEFAULT ''
);
"""


@dataclass
class ChartEvent:
    """The anonymous shape of one render_chart call — never the caller's data."""

    chart_type: str
    style: str = ""
    mode: str = ""
    border: str = ""
    use_color: bool = False
    series_count: int = 0
    point_count_bucket: str = ""
    output_size_bucket: str = ""
    success: bool = True
    error_message: str = ""


def bucket(n: int, *thresholds: int) -> str:
    """Label n against ascending thresholds: bucket(n, 10, 100, 1000) -> "<10", "10-100", "100-1000" or "1000+"."""
    for i, t in enumerate(thresholds):
        if n < t:
            return f"<{t}" if i == 0 else f"{thresholds[i - 1]}-{t}"
    return f"{thresholds[-1]}+"


class Store:
    def __init__(self, pool: Any = None, version: str = ""):
        self._pool = pool
        self._version = version

    @property
    def enabled(self) -> bool:
        return self._pool is not None

    @classmethod
    async def open(cls, dsn: str | None, version: str = "") -> "Store":
        """Connect and migrate. Returns a disabled Store if dsn is empty or the
        database is unreachable (logged, never raised)."""
        if not dsn:
            return cls()
        try:
            import asyncpg  # optional dependency: pip install asciicharts[stats]

            pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5, command_timeout=5)
            async with pool.acquire() as conn:
                await conn.execute(SCHEMA)
        except Exception as e:  # noqa: BLE001 - stats are optional by design
            log.warning("stats: %s — continuing without usage statistics", e)
            return cls()
        return cls(pool, version)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def record_chart_event(self, e: ChartEvent) -> None:
        if self._pool is None:
            return
        try:
            await self._pool.execute(
                """INSERT INTO chart_events
                   (chart_type, style, mode, border, use_color, series_count,
                    point_count_bucket, output_size_bucket, success, error_message, server_version)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                e.chart_type, e.style, e.mode, e.border, e.use_color, e.series_count,
                e.point_count_bucket, e.output_size_bucket, e.success, e.error_message, self._version,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("store: record chart event: %s", exc)
