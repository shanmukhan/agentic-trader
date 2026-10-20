"""Invented contributions/SIP/partial-fill/restart lifecycle in a separate account."""

import json
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.backtesting.report import ledger_results
from trading_agent.daily_execution.runner import finish_manifest, private_text
from trading_agent.execution.delivery import HoldingReview
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Instrument, Quote
from trading_agent.persistence.database import Database
from trading_agent.portfolio.contracts import (
    Approval,
    CancelPlan,
    Contribution,
    SIPPlan,
    occurrence_request,
)
from trading_agent.portfolio.service import cancel_plan, confirm, create_plan, preview, view
from trading_agent.risk.policy import policy_values
from trading_agent.settings import Settings

D = Decimal


def portfolio_demo(directory: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    now = datetime(2025, 10, 20, 10, tzinfo=IST)
    days = [now.date(), (now + timedelta(days=1)).date()]
    calendar = SessionCalendar(
        {day: (time(9, 15), time(15, 30)) for day in days},
        {day: "INVENTED contribution session" for day in days},
    )
    settings = Settings.load("config/long-term.toml").model_copy(
        update={"database": directory / "paper.sqlite3"}
    )
    db = Database(settings.database, settings.starting_cash)
    engine = PaperBroker(db, settings, calendar, recovery_time=now)
    engine.register([Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))])
    engine.set_connected(True)

    def market(at: datetime, *, bid: str = "500", depth: int = 100) -> None:
        engine.ingest(
            Quote(
                symbol="NSE:DEMO",
                token=1,
                exchange_time=at,
                received_time=at,
                last=D(bid),
                bid=D(bid),
                ask=D(bid) + D(".10"),
                bid_size=depth,
                ask_size=depth,
                volume=1000 + at.second * 100,
                source="replay",
            ),
            at,
        )

    def review(at: datetime) -> None:
        engine.review_holding(
            HoldingReview(
                symbol="NSE:DEMO",
                session_date=at.date(),
                no_corporate_action=True,
                reference="INVENTED clear raw basis",
            ),
            at,
        )

    def buy(request: Contribution, at: datetime) -> Approval:
        result = preview(engine, request, at)
        if not result["decision"]["allowed"]:
            raise RuntimeError("invented contribution fixture failed sizing")
        approval = Approval(request=request, preview_sha256=result["preview_sha256"])
        confirm(engine, approval, at)
        return approval

    try:
        review(now)
        market(now)
        plan = SIPPlan(
            plan_id="invented-recurring",
            symbol="NSE:DEMO",
            budget=D("1500"),
            sessions=tuple(days),
            stop_pct=D("2"),
            target_pct=D("20"),
            reference="INVENTED two reviewed recurring dates",
        )
        create_plan(engine, plan, now)
        buy(occurrence_request(plan, days[0]), now)
        market(now + timedelta(seconds=1))
        buy(
            Contribution(
                intent_id="invented-add",
                symbol="NSE:DEMO",
                budget=D("1000"),
                reference="INVENTED reviewed holding addition",
            ),
            now + timedelta(seconds=1),
        )
        market(now + timedelta(seconds=2))
        partial = buy(
            Contribution(
                intent_id="invented-partial",
                symbol="NSE:DEMO",
                budget=D("2000"),
                reference="INVENTED partial fill and crash drill",
            ),
            now + timedelta(seconds=2),
        )
        market(now + timedelta(seconds=3), depth=1)
        db.close()
        db = Database(settings.database, settings.starting_cash)
        engine = PaperBroker(db, settings, calendar, recovery_time=now + timedelta(seconds=4))
        engine.set_connected(True)
        retried = confirm(engine, partial, now + timedelta(seconds=4))
        if retried["state"] != "CANCELLED" or retried["filled"] != 1:
            raise RuntimeError("restart duplicated a contribution")
        now += timedelta(days=1)
        review(now)
        market(now)
        buy(occurrence_request(plan, days[1]), now)
        market(now + timedelta(seconds=1))
        cancel_plan(
            engine,
            CancelPlan(plan_id=plan.plan_id, reference="INVENTED operator plan completion"),
            now + timedelta(seconds=1),
        )
        held = engine.snapshot(now + timedelta(seconds=1))["positions"][0]["quantity"]
        engine.exit_holding("NSE:DEMO", now + timedelta(seconds=1))
        market(now + timedelta(seconds=2), bid="550")
        final = view(engine, now + timedelta(seconds=2))
        with db.transaction() as tx:
            db.reconcile(tx)
        trades, _ = ledger_results(db)
        if D(final["account"]["cash"]) != settings.starting_cash + sum(
            (t["net_pnl"] for t in trades), D(0)
        ):
            raise RuntimeError(
                "contribution demo cash failed independent capital P&L reconciliation"
            )
        result = {
            "synthetic": True,
            "ready_for_live": False,
            "held_before_sale": held,
            "restart_order_state": retried["state"],
            "final_cash": final["account"]["cash"],
            "fees": final["account"]["fees"],
            "acquisition_lots": len(final["lots"]),
            "net_capital_pnl": str(sum((t["net_pnl"] for t in trades), D(0))),
        }
        db.backup(directory / "preview.sqlite3")
        db.close()
        private_text(
            directory / "sessions.csv",
            "date,open,close,source\n"
            + "".join(f"{day},09:15,15:30,INVENTED contribution session\n" for day in days),
        )
        preview_values = {
            **policy_values(settings),
            "database": str((directory / "preview.sqlite3").resolve()),
            "calendar": str((directory / "sessions.csv").resolve()),
            "host": "127.0.0.1",
            "port": 8003,
        }
        private_text(
            directory / "preview.toml",
            "".join(f"{key} = {json.dumps(value)}\n" for key, value in preview_values.items()),
        )
        private_text(
            directory / "report.json",
            json.dumps({"summary": result, **final}, indent=2, sort_keys=True, default=str) + "\n",
        )
        private_text(
            directory / "report.md",
            "# Contribution and SIP lifecycle\n\n"
            "Invented paper software evidence; no market acceptance.\n\n"
            + "\n".join(f"- {k}: {v}" for k, v in result.items())
            + "\n\nFour original acquisition lots share one pooled-cost holding. "
            "Partial entry residue was cancelled on restart. Each SIP occurrence was "
            "explicitly confirmed. No cash was deposited.\n",
        )
        finish_manifest(
            directory,
            ["paper.sqlite3", "report.json", "report.md", "preview.toml", "sessions.csv"],
            kind="portfolio-contribution-demo-v1",
            synthetic=True,
        )
        return result
    finally:
        db.close()
