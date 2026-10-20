from datetime import timedelta
from decimal import Decimal as D

from conftest import NOW, candidate, quote

from trading_agent.backtesting.report import Performance, ledger_results


def test_drawdown_uses_running_peak_and_initial_capital():
    performance = Performance(D(100))
    for value in ("99", "110", "90", "105", "85"):
        performance.observe({"equity": value, "valuation_fresh": True})
    assert performance.drawdown == 25
    assert performance.drawdown_pct == D(25) / 110 * 100


def test_zero_trades_and_no_losses_have_defined_null_metrics(engine):
    trades, metrics = ledger_results(engine.db)
    assert not trades and metrics["completed_trades"] == 0
    assert metrics["win_rate_pct"] is metrics["profit_factor"] is None


def test_partial_exits_are_one_trade_and_open_trade_is_excluded(engine):
    engine.submit(candidate(), NOW)
    engine.ingest(quote(1, ask_size=3), NOW + timedelta(seconds=1))
    engine.kill(NOW + timedelta(seconds=1))
    engine.ingest(quote(2, bid_size=2), NOW + timedelta(seconds=2))
    trades, metrics = ledger_results(engine.db)
    assert not trades and metrics["uncompleted_trades"] == 1
    engine.ingest(quote(3), NOW + timedelta(seconds=3))
    trades, metrics = ledger_results(engine.db)
    assert len(trades) == 1 and trades[0]["quantity"] == 3
    assert metrics["completed_trades"] == metrics["losing_trades"] == 1
    assert trades[0]["net_pnl"] == D(engine.snapshot(NOW + timedelta(seconds=3))["realized_pnl"])
    assert trades[0]["fees"] == D(engine.snapshot(NOW + timedelta(seconds=3))["fees"])
