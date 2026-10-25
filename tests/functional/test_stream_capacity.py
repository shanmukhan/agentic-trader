"""Synthetic expanded-feed lifecycle: config, initialization, transport and durable account."""

import sqlite3
import struct
from contextlib import closing, nullcontext
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock

from conftest import TOKEN

from trading_agent.main import execute, open_automated, parser
from trading_agent.models import Instrument
from trading_agent.paper.demo import WARM, warmup
from trading_agent.paper.service import PaperService
from trading_agent.settings import Settings


def test_fifty_symbol_paper_account_receives_reviewed_full_depth_feed(tmp_path, monkeypatch):
    import websockets.sync.client

    catalog = [
        Instrument(symbol=f"NSE:DEMO{index}", token=256 * index + 1, tick_size=Decimal(".05"))
        for index in range(50)
    ]
    calendar = tmp_path / "sessions.csv"
    calendar.write_text("date,open,close,source\n2026-10-20,09:15,15:30,synthetic test\n")
    database = tmp_path / "account.sqlite3"
    config = tmp_path / "paper.toml"
    config.write_text(
        f'database="{database}"\ncalendar="{calendar}"\n'
        f"stream_limit=50\nstream_tokens={[item.token for item in catalog]}\n"
    )
    broker = Mock()
    broker.get_instruments.return_value = catalog
    monkeypatch.setenv("TRADING_OPERATOR_TOKEN", TOKEN)
    monkeypatch.setenv("KITE_API_KEY", "synthetic-key")
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "synthetic-session")
    monkeypatch.setattr("trading_agent.main.ReadOnlyKite.from_environment", lambda: broker)
    monkeypatch.setattr("trading_agent.main.clock", lambda: WARM)
    initialized = execute(
        parser().parse_args(["--config", str(config), "paper-init", "--rule-only"])
    )
    assert Decimal(initialized["cash"]) == Decimal("25000.00") and not initialized["armed"]

    packets = []
    for item in catalog:
        packet = bytearray(184)
        for offset, value in (
            (0, item.token),
            (4, 50000),
            (16, 1000),
            (60, int(WARM.timestamp())),
            (64, 100),
            (68, 49995),
            (124, 100),
            (128, 50000),
        ):
            struct.pack_into(">I", packet, offset, value)
        packets.append(struct.pack(">H", 184) + packet)
    socket = Mock()
    socket.recv.return_value = struct.pack(">H", 50) + b"".join(packets)
    monkeypatch.setattr(websockets.sync.client, "connect", lambda *a, **k: nullcontext(socket))
    serving = parser().parse_args(["serve", "--stream", "--automate", "--rule-only"])
    db, engine, feed = open_automated(Settings.load(config), serving)
    current = [WARM]
    service = PaperService(feed, broker, lambda: current[0])
    original = service.stream._on_quote
    accepted = []

    def received(quote):
        original(quote)
        accepted.append(quote.symbol)
        if len(accepted) == 50:
            service.stream._stop.set()

    service.stream._on_quote = received
    try:
        assert service.stream.stream_limit == 50
        service.stream._run()
        assert len(accepted) == 50 and feed.counts["quotes_accepted"] == 50
        assert not engine.faulted and not feed.armed and not engine.orders()
        template = warmup()[0]
        history = [
            template.model_copy(
                update={"symbol": item.symbol, "start": template.start + timedelta(minutes=5 * i)}
            )
            for item in catalog
            for i in range(30)
        ]
        # A reviewed expanded universe must not hit the former fixed 1,000-bar ceiling.
        current[0] = template.start + timedelta(minutes=150)
        feed.on_candles(history, current[0])
        assert not engine.faulted and len(feed.last_bar) == 50
        service.close()
    finally:
        db.close()
    # Read persisted data independently of the application account/snapshot accessors.
    with closing(sqlite3.connect(database)) as persisted:
        assert persisted.execute("SELECT COUNT(*) FROM instruments").fetchone()[0] == 50
        assert persisted.execute("SELECT COUNT(*) FROM quotes").fetchone()[0] == 50
        assert persisted.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 1500
        assert persisted.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
        assert persisted.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
