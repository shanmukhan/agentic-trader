"""Net-of-cost metrics from the fill ledger; unfinished holdings are never closed by fiat."""

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.corporate_actions.accounting import steps
from trading_agent.persistence.database import Database

D = Decimal


def code_digest() -> str:
    root = Path(__file__).resolve().parent.parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


@dataclass
class Performance:
    initial_cash: Decimal
    peak: Decimal = field(init=False)
    drawdown: Decimal = D(0)
    drawdown_pct: Decimal = D(0)
    observations: int = 0
    stale_valuations: int = 0

    def __post_init__(self) -> None:
        self.peak = self.initial_cash

    def observe(self, snapshot: dict[str, Any]) -> None:
        equity = D(snapshot["equity"])
        self.peak = max(self.peak, equity)
        loss = self.peak - equity
        self.drawdown = max(self.drawdown, loss)
        self.drawdown_pct = max(self.drawdown_pct, loss / self.peak * 100)
        self.observations += 1
        self.stale_valuations += int(not snapshot["valuation_fresh"])


def ledger_results(db: Database) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    trades: list[dict[str, Any]] = []
    active: dict[str, dict[str, Any]] = {}
    with db.transaction() as tx:
        for kind, row in steps(tx):
            if kind == "corporate_cash_receipt":
                continue  # Separate investment-income/fraction results appear in the LT report.
            if kind == "corporate_action_batch":
                result = json.loads(row["payload"])["result"]
                trade = active.get(row["symbol"])
                if trade:
                    trade["corporate_share_delta"] = trade.get("corporate_share_delta", 0) + (
                        result["after"]["quantity"] - result["before"]["quantity"]
                    )
                    trade["remaining"] = result["after"]["quantity"]
                    trade["_remaining_basis"] = D(result["after"]["cost"])
                    trade["fraction_basis_transferred"] = trade.get(
                        "fraction_basis_transferred", D(0)
                    ) + sum((D(claim["basis"]) for claim in result["claims"]), D(0))
                continue
            symbol, qty = row["symbol"], row["quantity"]
            notional, fee = D(row["price"]) * qty, D(row["fees"])
            if row["side"] == "BUY":
                trade = active.setdefault(
                    symbol,
                    {
                        "symbol": symbol,
                        "entry_time": row["time"],
                        "quantity": 0,
                        "remaining": 0,
                        "buy_notional": D(0),
                        "sell_notional": D(0),
                        "fees": D(0),
                        "entry_intent": row["order_id"],
                        "_remaining_basis": D(0),
                        "_capital_realized": D(0),
                    },
                )
                trade["quantity"] += qty
                trade["remaining"] += qty
                trade["buy_notional"] += notional
                trade["_remaining_basis"] += notional + fee
            else:
                if symbol not in active or qty > active[symbol]["remaining"]:
                    raise RuntimeError("report sell exceeds filled position")
                trade = active[symbol]
                basis = (
                    trade["_remaining_basis"]
                    if qty == trade["remaining"]
                    else trade["_remaining_basis"] * D(qty) / trade["remaining"]
                )
                trade["_remaining_basis"] -= basis
                trade["_capital_realized"] += notional - fee - basis
                trade["remaining"] -= qty
                trade["sell_notional"] += notional
                trade["exit_time"], trade["exit_reason"] = row["time"], row["reason"]
            trade["fees"] += fee
            if trade["remaining"] == 0:
                trade["net_pnl"] = (
                    trade["sell_notional"]
                    - trade["buy_notional"]
                    - trade["fees"]
                    + trade.get("fraction_basis_transferred", D(0))
                )
                if "corporate_share_delta" in trade:
                    trade["net_pnl"] = trade["_capital_realized"]
                trade.pop("_remaining_basis")
                trade.pop("_capital_realized")
                trades.append(trade)
                del active[symbol]
        orders = tx.execute("SELECT * FROM orders ORDER BY created,id").fetchall()
    winners = sum((t["net_pnl"] for t in trades if t["net_pnl"] > 0), D(0))
    losers = -sum((t["net_pnl"] for t in trades if t["net_pnl"] < 0), D(0))
    count = len(trades)
    metrics = {
        "completed_trades": count,
        "winning_trades": sum(t["net_pnl"] > 0 for t in trades),
        "losing_trades": sum(t["net_pnl"] < 0 for t in trades),
        "win_rate_pct": D(sum(t["net_pnl"] > 0 for t in trades)) / count * 100 if count else None,
        "expectancy_per_completed_trade": (winners - losers) / count if count else None,
        "profit_factor": winners / losers if losers else None,
        "profit_factor_status": "defined" if losers else "no_completed_losses",
        "order_states": dict(Counter(r["state"] for r in orders)),
        "pending_orders": sum(r["state"] in ("ACCEPTED", "PARTIAL") for r in orders),
        "rejection_reasons": dict(
            Counter(
                code
                for r in orders
                if r["state"] == "REJECTED"
                for code in r["reason"].split(",")
                if code
            )
        ),
        "uncompleted_trades": len(active),
    }
    return trades, metrics


def journal_digest(db: Database) -> str:
    digest = hashlib.sha256()
    with db.transaction() as tx:
        for row in tx.execute("SELECT * FROM events ORDER BY seq"):
            digest.update((json.dumps(dict(row), sort_keys=True) + "\n").encode())
    return digest.hexdigest()


def write_report(directory: Path, report: dict[str, Any], trades: list[dict[str, Any]]) -> None:
    (directory / "report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, default=str) + "\n"
    )
    with (directory / "trades.jsonl").open("x") as file:
        for trade in trades:
            file.write(json.dumps(trade, sort_keys=True, default=str) + "\n")
    metrics = report["metrics"]
    lines = [
        "# Strategy research report",
        "",
        f"Status: **{report['status']}**. PAPER ONLY.",
        "",
        f"Hypothesis: `{report['strategy']['hypothesis']}`.",
        f"Model: `{report.get('model_sha256') or 'rule-only'}`.",
        "",
        f"Synthetic data: **{report['dataset']['synthetic']}**. "
        "This run does not establish strategy profitability or live readiness.",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Net liquidation P&L | {metrics['net_pnl']} |",
        f"| Realized P&L | {report['final_snapshot']['realized_pnl']} |",
        f"| Charged simulated fees | {report['final_snapshot']['fees']} |",
        f"| Completed trades | {metrics['completed_trades']} |",
        f"| Win rate (%) | {metrics['win_rate_pct']} |",
        f"| Profit factor | {metrics['profit_factor']} ({metrics['profit_factor_status']}) |",
        f"| Maximum observed drawdown | {metrics['max_drawdown']} |",
        f"| Open positions / pending orders | {len(report['final_snapshot']['positions'])} / "
        f"{metrics['pending_orders']} |",
        "",
        "## Research limitations",
        "",
        "- Completed five-minute candles create signals; only later observed bid/ask quotes fill.",
        "- Network, queue position, price impact and missed intratick moves are not reconstructed.",
        "- Unfinished positions remain open; stale valuations and gaps are disclosed.",
        "- No parameter search, annualized Sharpe or live trading approval is produced.",
        "- Optional offline ML identity and availability are recorded in report.json.",
        "",
        "See `report.json` for exact input, configuration, code and journal hashes, "
        "data-quality counters, timestamps, gates and all financial values.",
        "",
    ]
    (directory / "report.md").write_text("\n".join(lines))
