import random
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.models import Instrument


def test_seeded_partial_buy_sell_cancel_reissue_sequences(engine_factory):
    """Real balances stay reconcilable after many independent partial round trips."""
    engine = engine_factory(daily_loss_limit=D(5000), max_consecutive_losses=100)
    randomizer = random.Random(42)
    second = 0
    for number in range(30):
        second += 1
        now = NOW + timedelta(seconds=second)
        engine.ingest(quote(second), now)
        assert engine.submit(candidate(f"round-{number}", now=now), now)["state"] == "ACCEPTED"
        second += 1
        now = NOW + timedelta(seconds=second)
        engine.ingest(quote(second, ask_size=3), now)
        engine.flatten(now)  # cancels residual entry and queues sale of the three actual shares
        bid = D(500) + D(randomizer.randint(-30, 30)) / 10
        second += 1
        now = NOW + timedelta(seconds=second)
        engine.ingest(quote(second, bid=str(bid), ask=str(bid + D(".05")), bid_size=2), now)
        sell = engine.orders()[-1]
        assert sell["side"] == "SELL" and sell["state"] == "PARTIAL"
        engine.cancel(sell["id"], now)
        # Same timestamp reissue must have a new durable ID and preserve trade P&L.
        engine.poll(now)
        assert engine.orders()[-1]["id"] != sell["id"]
        second += 1
        now = NOW + timedelta(seconds=second)
        engine.ingest(quote(second, bid=str(bid), ask=str(bid + D(".05"))), now)
        state = engine.snapshot(now)
        assert not state["positions"]
        assert D(state["cash"]) == D(25000) + D(state["realized_pnl"])
        with engine.db.transaction() as tx:
            engine.db.reconcile(tx)
        engine.reset_kill(now)


def test_changed_instrument_mapping_rejected(engine):
    with pytest.raises(ValueError, match="mapping changed"):
        engine.register([Instrument(symbol="NSE:DEMO", token=99, tick_size=D(".05"))])


def test_spread_and_liquidity_fail_closed(engine):
    now = NOW + timedelta(seconds=1)
    engine.ingest(quote(1, bid="495", ask="500"), now)
    assert (
        "SPREAD_TOO_WIDE" in engine.submit(candidate("spread", now=now, stop="490"), now)["reason"]
    )
    now += timedelta(seconds=1)
    engine.ingest(quote(2, ask_size=0), now)
    assert "NO_LIQUIDITY" in engine.submit(candidate("empty-book", now=now), now)["reason"]
