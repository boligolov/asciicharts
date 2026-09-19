"""Stats store: the disabled path and bucketing. (Postgres itself is exercised
by the docker-compose smoke test, not here.)"""

import asyncio

import pytest

from asciicharts_server.store import ChartEvent, Store, bucket


@pytest.mark.parametrize("n,expected", [(0, "<10"), (9, "<10"), (10, "10-100"), (99, "10-100"),
                                        (100, "100-1000"), (999, "100-1000"), (1000, "1000+"), (10 ** 6, "1000+")])
def test_bucket(n, expected):
    assert bucket(n, 10, 100, 1000) == expected


def test_disabled_store_is_a_safe_noop():
    async def run():
        s = await Store.open(None)
        assert not s.enabled
        await s.record_chart_event(ChartEvent(chart_type="line"))
        await s.close()
    asyncio.run(run())


def test_unreachable_database_degrades_to_disabled():
    async def run():
        s = await Store.open("postgres://nobody:x@127.0.0.1:1/none")
        assert not s.enabled
    asyncio.run(run())


# --- opt-in via the environment -------------------------------------------

import logging

import asciicharts_server.app as app
from asciicharts_server.app import open_stats, stats_enabled

DSN = "postgres://u:p@localhost:5432/db"


@pytest.mark.parametrize("value,expected", [
    (None, False), ("", False), ("0", False), ("off", False), ("false", False), ("no", False), ("maybe", False),
    ("1", True), ("on", True), ("ON", True), ("true", True), ("True", True), ("yes", True), (" on ", True),
])
def test_stats_flag_parsing(value, expected):
    env = {} if value is None else {"ASCIICHARTS_STATS": value}
    assert stats_enabled(env) is expected


class FakePool:
    async def execute(self, *args):
        pass

    async def close(self):
        pass


@pytest.fixture
def spy_open(monkeypatch):
    """Replace Store.open with a spy that records calls and returns an 'enabled' store."""
    calls = []

    async def fake_open(dsn, version=""):
        calls.append(dsn)
        return Store(pool=FakePool(), version=version)

    monkeypatch.setattr(app.Store, "open", staticmethod(fake_open))
    return calls


def test_statistics_are_off_by_default_even_when_a_database_is_configured(spy_open):
    s = asyncio.run(open_stats({"DATABASE_URL": DSN}))
    assert not s.enabled and spy_open == []  # never even tried to connect


def test_flag_off_values_keep_statistics_off(spy_open):
    for v in ("", "0", "off", "false"):
        assert not asyncio.run(open_stats({"ASCIICHARTS_STATS": v, "DATABASE_URL": DSN})).enabled
    assert spy_open == []


def test_flag_on_with_a_database_enables_statistics(spy_open):
    s = asyncio.run(open_stats({"ASCIICHARTS_STATS": "on", "DATABASE_URL": DSN}))
    assert s.enabled and spy_open == [DSN]


def test_flag_on_without_a_database_stays_off_and_warns(spy_open, caplog):
    for env in ({"ASCIICHARTS_STATS": "on"}, {"ASCIICHARTS_STATS": "on", "DATABASE_URL": "  "}):
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="asciicharts"):
            s = asyncio.run(open_stats(env))
        assert not s.enabled and spy_open == []
        assert "DATABASE_URL is not set" in caplog.text


def test_flag_on_with_unreachable_database_still_starts():
    s = asyncio.run(open_stats({"ASCIICHARTS_STATS": "on", "DATABASE_URL": "postgres://nobody:x@127.0.0.1:1/none"}))
    assert not s.enabled


def test_server_lifespan_reads_the_environment(monkeypatch, spy_open):
    """build_server() with no injected store follows ASCIICHARTS_STATS at startup."""
    from mcp import Client
    from asciicharts_server.app import build_server

    async def run():
        async with Client(build_server()) as c:
            await c.call_tool("render_chart", {"chartType": "sparkline", "series": [{"values": [1, 2]}]})

    monkeypatch.delenv("ASCIICHARTS_STATS", raising=False)
    monkeypatch.setenv("DATABASE_URL", DSN)
    asyncio.run(run())
    assert spy_open == []            # off by default
    monkeypatch.setenv("ASCIICHARTS_STATS", "1")
    asyncio.run(run())
    assert spy_open == [DSN]         # on when asked
