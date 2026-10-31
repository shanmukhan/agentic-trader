"""Operator commands. Broker secrets are read from environment or hidden prompts only."""

import argparse
import getpass
import json
import os
import platform
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from trading_agent.broker.readonly_kite import (
    ReadOnlyKite,
    exchange_token,
    login_url,
)
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import SessionCalendar
from trading_agent.market_data.repository import store_candles
from trading_agent.models import Instrument
from trading_agent.observability.logging import configure_logging
from trading_agent.persistence.database import Database
from trading_agent.replay import demo, run_events
from trading_agent.settings import Settings

if TYPE_CHECKING:
    from trading_agent.ml.inference import ResearchModel
    from trading_agent.paper.config import FeedSettings
    from trading_agent.paper.runtime import PaperFeed
    from trading_agent.strategy.rules import StrategySettings


def clock() -> datetime:
    return datetime.now(UTC)


def open_engine(settings: Settings) -> tuple[Database, PaperBroker]:
    calendar = SessionCalendar.load(settings.calendar)
    database = Database(settings.database, settings.starting_cash)
    try:
        engine = PaperBroker(database, settings, calendar)
        engine.safety.enable(clock())
        return database, engine
    except BaseException:
        database.close()
        raise


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Read-only Kite data and PAPER ONLY execution")
    root.add_argument("--config", default=None, help="TOML path; defaults to TRADING_CONFIG")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("environment")
    commands.add_parser("init-db")
    commands.add_parser("status")
    commands.add_parser("verify-db")
    daily_report = commands.add_parser(
        "daily-report", help="read-only running-service daily operations audit"
    )
    daily_report.add_argument(
        "--output", type=Path, required=True, help="new private report directory"
    )
    monitor = commands.add_parser(
        "operations-watch", help="independent loopback supervisor; local alerts"
    )
    monitor.add_argument(
        "--output", type=Path, required=True, help="private durable supervisor directory"
    )
    monitor.add_argument("--interval", type=int, default=10)
    monitor.add_argument("--once", action="store_true")
    monitor.add_argument(
        "--download-universe",
        choices=("nifty100", "nifty500"),
        help="explicit opt-in to one current-day scheduled download attempt; no installation",
    )
    monitor.add_argument(
        "--after", default="08:30", help="IST acquisition start, HH:MM; default 08:30"
    )
    bundle = commands.add_parser(
        "operations-backup", help="stopped-account verified ledger and referenced artifact package"
    )
    bundle.add_argument("--output", type=Path, required=True)
    drill = commands.add_parser(
        "operations-restore-drill",
        help="verify and copy a package to a NEW isolated directory; no service start",
    )
    drill.add_argument("package", type=Path)
    drill.add_argument("--output", type=Path, required=True)
    preflight = commands.add_parser(
        "preflight", help="read-only local acceptance diagnostics; no account recovery/network"
    )
    preflight.add_argument("--output", type=Path, help="optional new private evidence directory")
    preflight.add_argument(
        "--strict", action="store_true", help="exit 2 if any required local check is blocked"
    )
    commands.add_parser("login-url")
    token = commands.add_parser("exchange-token")
    token.add_argument("--output", type=Path, required=True, help="new mode-0600 shell env file")
    commands.add_parser("profile")
    commands.add_parser("instruments")
    historical = commands.add_parser("historical")
    historical.add_argument("symbol")
    historical.add_argument("--start", required=True, type=datetime.fromisoformat)
    historical.add_argument("--end", required=True, type=datetime.fromisoformat)
    historical.add_argument("--minutes", type=int, choices=(1, 5), default=5)
    serve = commands.add_parser("serve")
    serve.add_argument("--open", action="store_true", help="open the local dashboard in a browser")
    serve.add_argument(
        "--stream", action="store_true", help="enable authenticated read-only Kite feed"
    )
    serve.add_argument(
        "--automate", action="store_true", help="supervised PAPER automation; starts disarmed"
    )
    serve.add_argument(
        "--rule-only", action="store_true", help="explicit paper rule baseline without ML"
    )
    serve.add_argument("--strategy", type=Path, default=Path("config/strategy.toml"))
    serve.add_argument("--model", type=Path, help="non-synthetic approved JSON model")
    serve.add_argument("--feed-policy", type=Path, default=Path("config/paper-feed.toml"))
    paper_init = commands.add_parser(
        "paper-init", help="new dedicated account and reviewed read-only catalog"
    )
    paper_init.add_argument("--rule-only", action="store_true")
    paper_init.add_argument("--model", type=Path)
    paper_init.add_argument("--strategy", type=Path, default=Path("config/strategy.toml"))
    paper_init.add_argument("--feed-policy", type=Path, default=Path("config/paper-feed.toml"))
    paper_demo = commands.add_parser(
        "paper-demo", help="synthetic supervised feed and outage/restart drills"
    )
    paper_demo.add_argument("--directory", type=Path, default=Path("data/paper-demo"))
    long_demo = commands.add_parser(
        "long-term-demo", help="isolated overnight paper and recovery drill"
    )
    long_demo.add_argument("--directory", type=Path, default=Path("data/long-term-demo"))
    corporate_demo = commands.add_parser(
        "corporate-actions-demo", help="invented split/bonus/dividend and receipt lifecycle"
    )
    corporate_demo.add_argument(
        "--directory", type=Path, default=Path("data/corporate-actions-demo")
    )
    daily_demo = commands.add_parser(
        "daily-research-demo", help="invented causal daily screen and offline dashboard"
    )
    daily_demo.add_argument("--directory", type=Path, default=Path("data/daily-research-demo"))
    daily = commands.add_parser(
        "daily-analyze", help="offline completed daily research; no account or orders"
    )
    daily.add_argument("dataset", type=Path)
    daily.add_argument("--as-of", required=True, type=datetime.fromisoformat)
    daily.add_argument("--policy", type=Path, default=Path("config/daily-research.toml"))
    daily.add_argument("--output", required=True, type=Path)
    investment = commands.add_parser(
        "investment-analyze", help="isolated causal price indicators; no account or orders"
    )
    investment.add_argument("dataset", type=Path)
    investment.add_argument("--symbol", required=True)
    investment.add_argument("--as-of", required=True, type=datetime.fromisoformat)
    investment.add_argument("--timeframe", choices=("1d", "1w", "1mo"), default="1d")
    investment.add_argument("--context", type=Path, help="reviewed hash-bound calendar context")
    investment.add_argument("--benchmark", type=Path, help="reviewed local benchmark JSON")
    investment.add_argument("--output", required=True, type=Path)
    registration = commands.add_parser(
        "register-backtest",
        help="register copied immutable replay inputs; no account or job starts",
    )
    registration.add_argument("daily", type=Path)
    registration.add_argument("execution", type=Path)
    registration.add_argument("--strategy", type=Path, required=True)
    registration.add_argument(
        "--policy",
        type=Path,
        required=True,
        help="reviewed isolated long-term economic policy TOML",
    )
    registration.add_argument("--label", required=True)
    registration.add_argument(
        "--registry", type=Path, help="default: configured account path with .research-jobs suffix"
    )
    policy_draft = commands.add_parser(
        "investment-policy",
        help="inspect a draft or preview reviewed-calendar dates; no account changes",
    )
    policy_draft.add_argument("draft", type=Path, help="draft JSON with label/parameters")
    policy_draft.add_argument(
        "--calendar", type=Path, help="explicit complete calendar declaration JSON"
    )
    policy_draft.add_argument(
        "--start", type=date.fromisoformat, help="inclusive horizon start YYYY-MM-DD"
    )
    policy_draft.add_argument(
        "--as-of", type=datetime.fromisoformat, help="aware calendar-availability cutoff"
    )
    for name in ("daily-backtest", "daily-labels"):
        command = commands.add_parser(name, help="isolated quote-executed daily delivery research")
        command.add_argument("daily", type=Path)
        command.add_argument("execution", type=Path)
        command.add_argument("--strategy", type=Path, default=Path("config/daily-strategy.toml"))
        command.add_argument("--output", required=True, type=Path)
        if name == "daily-backtest":
            command.add_argument("--model", type=Path)
            command.add_argument("--allow-synthetic-model", action="store_true")
    daily_train = commands.add_parser(
        "daily-train", help="separate chronological daily model validation"
    )
    daily_train.add_argument("samples", type=Path)
    daily_train.add_argument("--training", type=Path, default=Path("config/daily-ml.toml"))
    daily_train.add_argument("--output", type=Path, required=True)
    execution_demo = commands.add_parser(
        "daily-execution-demo", help="invented delivery replay/labels and optional ML workflow"
    )
    execution_demo.add_argument("--directory", type=Path, default=Path("data/daily-execution-demo"))
    execution_demo.add_argument("--with-ml", action="store_true")
    portfolio_demo = commands.add_parser(
        "portfolio-demo", help="invented reviewed purchases, SIP and partial-fill restart"
    )
    portfolio_demo.add_argument("--directory", type=Path, default=Path("data/portfolio-demo"))
    long_report = commands.add_parser(
        "long-term-report", help="preserve source delivery account work"
    )
    long_report.add_argument("--output", type=Path, required=True)
    for name, help_text in (
        ("apply-corporate-actions", "offline reviewed paper share/dividend entitlements"),
        ("record-corporate-cash", "offline reviewed paper entitlement cash receipt"),
    ):
        action = commands.add_parser(name, help=help_text)
        action.add_argument("--file", type=Path, required=True)
    paper_evidence = commands.add_parser(
        "paper-report", help="source-preserving operations evidence"
    )
    paper_evidence.add_argument("--output", type=Path, required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("destination", type=Path)
    simulation = commands.add_parser("demo")
    simulation.add_argument("--directory", type=Path, default=Path("data/demo"))
    replay = commands.add_parser("replay")
    replay.add_argument("events", type=Path)
    replay.add_argument(
        "--instruments", type=Path, required=True, help="JSON array of reviewed Instrument records"
    )
    research = commands.add_parser("backtest")
    research.add_argument(
        "dataset", type=Path, help="directory with manifest.json and events.jsonl"
    )
    research.add_argument("--strategy", type=Path, default=Path("config/strategy.toml"))
    research.add_argument("--model", type=Path, help="verified offline model artifact directory")
    research.add_argument(
        "--allow-synthetic-model",
        action="store_true",
        help="synthetic data only; does not override metric gates",
    )
    research.add_argument(
        "--output", type=Path, required=True, help="new isolated output directory"
    )
    research_demo = commands.add_parser("research-demo")
    research_demo.add_argument("--directory", type=Path, default=Path("data/research-demo"))
    research_demo.add_argument("--strategy", type=Path, default=Path("config/strategy.toml"))
    build = commands.add_parser(
        "ml-build", help="label causal candidates with isolated paper trades"
    )
    build.add_argument("dataset", type=Path)
    build.add_argument("--strategy", type=Path, default=Path("config/strategy.toml"))
    build.add_argument("--horizon-minutes", type=int, default=30)
    build.add_argument("--output", type=Path, required=True)
    train = commands.add_parser("ml-train", help="offline purged training/calibration/validation")
    train.add_argument("samples", type=Path)
    train.add_argument("--training", type=Path, default=Path("config/ml.toml"))
    train.add_argument("--output", type=Path, required=True)
    ml_demo = commands.add_parser("ml-demo", help="complete SYNTHETIC ML workflow")
    ml_demo.add_argument("--directory", type=Path, default=Path("data/ml-demo"))
    ml_demo.add_argument("--strategy", type=Path, default=Path("config/strategy.toml"))
    ml_demo.add_argument("--training", type=Path, default=Path("config/ml-demo.toml"))
    export = commands.add_parser("export-research")
    export.add_argument("--start", required=True, type=datetime.fromisoformat)
    export.add_argument("--end", required=True, type=datetime.fromisoformat)
    export.add_argument("--symbols", required=True, nargs="+")
    export.add_argument("--source", required=True, help="reviewed provenance, without credentials")
    export.add_argument("--candles", type=Path, help="optional verified 5m Candle JSONL override")
    export.add_argument("--output", required=True, type=Path)
    return root


def execute(args: argparse.Namespace) -> Any:
    if args.command == "environment":
        import shutil

        return {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
            "free_disk_gb": round(shutil.disk_usage(Path.cwd()).free / 1024**3, 2),
            "mode": "paper",
        }
    # Validate mode even for demonstrations and broker-only commands.
    settings = Settings.load(args.config)
    if args.command == "portfolio-demo":
        from trading_agent.portfolio.demo import portfolio_demo

        return portfolio_demo(args.directory)
    if args.command == "daily-execution-demo":
        from trading_agent.daily_execution.demo import execution_demo

        return execution_demo(args.directory, with_ml=args.with_ml)
    if args.command == "daily-train":
        from trading_agent.daily_execution.model import DailySamples, train_daily
        from trading_agent.ml.schema import TrainingSettings

        return train_daily(
            DailySamples(args.samples),
            settings=TrainingSettings.load(args.training),
            output=args.output,
        )
    if args.command in {"daily-backtest", "daily-labels"}:
        from trading_agent.daily_execution.contracts import DailyStrategy
        from trading_agent.daily_execution.dataset import ExecutionDataset
        from trading_agent.daily_execution.model import load_daily_model
        from trading_agent.daily_execution.runner import run_daily
        from trading_agent.daily_research.dataset import DailyDataset

        if settings.investment_horizon != "long_term":
            raise ValueError("daily execution research requires a dedicated long-term policy")
        daily_strategy = DailyStrategy.load(args.strategy)
        daily_source = ExecutionDataset(args.execution, DailyDataset(args.daily))
        daily_model = (
            load_daily_model(
                args.model,
                strategy=daily_strategy,
                policy=settings,
                allow_synthetic=args.allow_synthetic_model,
            )
            if args.command == "daily-backtest" and args.model
            else None
        )
        return run_daily(
            daily_source,
            strategy=daily_strategy,
            policy=settings,
            output=args.output,
            labels=args.command == "daily-labels",
            model=daily_model,
        )
    if args.command == "daily-research-demo":
        from trading_agent.daily_research.demo import daily_research_demo

        return daily_research_demo(args.directory)
    if args.command == "daily-analyze":
        from trading_agent.daily_research.analysis import DailyPolicy, write_analysis
        from trading_agent.daily_research.dataset import DailyDataset

        return write_analysis(
            DailyDataset(args.dataset), DailyPolicy.load(args.policy), args.as_of, args.output
        )
    if args.command == "investment-analyze":
        from trading_agent.daily_research.dataset import DailyDataset
        from trading_agent.investment_research.series import write_series_report

        return write_series_report(
            DailyDataset(args.dataset),
            args.symbol,
            args.as_of,
            args.output,
            timeframe=args.timeframe,
            context_path=args.context,
            benchmark_path=args.benchmark,
        )
    if args.command == "register-backtest":
        from trading_agent.research_jobs import register_bundle

        return register_bundle(
            args.registry or settings.database.with_suffix(".research-jobs"),
            args.daily,
            args.execution,
            args.strategy,
            args.policy,
            args.label,
        )
    if args.command == "investment-policy":
        from trading_agent.investment_research.policy_cli import inspect_policy_file

        return inspect_policy_file(args.draft, args.calendar, args.start, args.as_of)
    if args.command == "corporate-actions-demo":
        from trading_agent.corporate_actions.demo import corporate_actions_demo

        return corporate_actions_demo(args.directory)
    if args.command in {"apply-corporate-actions", "record-corporate-cash"}:
        from trading_agent.corporate_actions.contracts import ActionBatch, CashReceipt
        from trading_agent.corporate_actions.service import (
            apply_batch,
            load_request,
            record_receipt,
        )

        if settings.investment_horizon != "long_term" or not settings.database.is_file():
            raise ValueError("corporate actions require an existing long-term paper account")
        contract = ActionBatch if args.command == "apply-corporate-actions" else CashReceipt
        request = load_request(args.file, contract)
        source = Database(settings.database, settings.starting_cash)
        try:
            if isinstance(request, ActionBatch):
                return apply_batch(
                    source, settings, SessionCalendar.load(settings.calendar), request, clock()
                )
            return record_receipt(source, settings, request, clock())
        finally:
            source.close()
    if settings.investment_horizon == "long_term" and (
        args.command
        in {
            "demo",
            "replay",
            "backtest",
            "research-demo",
            "ml-build",
            "ml-train",
            "ml-demo",
            "export-research",
            "paper-init",
            "paper-report",
        }
        or args.command == "serve"
        and args.automate
    ):
        raise ValueError(
            "intraday research/automation is not approved for long-term paper accounts"
        )
    if args.command == "long-term-demo":
        from trading_agent.paper.long_term_demo import long_term_demo

        return long_term_demo(args.directory)
    if args.command == "long-term-report":
        from trading_agent.paper.long_term_report import long_term_report

        if settings.investment_horizon != "long_term" or not settings.database.is_file():
            raise ValueError("long-term report requires an existing delivery paper account")
        source = Database(settings.database, settings.starting_cash)
        try:
            return long_term_report(source, args.output)
        finally:
            source.close()
    if args.command == "daily-report":
        from trading_agent.operations.supervisor import collect, write_report

        report = collect(settings)
        write_report(report, args.output)
        return {"output": str(args.output), "checks": report["checks"], "ready_for_live": False}
    if args.command == "operations-watch":
        from datetime import time

        from trading_agent.operations.supervisor import supervise

        return supervise(
            settings,
            args.output,
            clock,
            interval=args.interval,
            after=time.fromisoformat(args.after),
            download_universe=args.download_universe,
            once=args.once,
        )
    if args.command == "operations-backup":
        from trading_agent.operations.backup import create_package

        config = Path(args.config or os.environ.get("TRADING_CONFIG", "config/paper.toml"))
        return create_package(settings, config, args.output, clock())
    if args.command == "operations-restore-drill":
        from trading_agent.operations.backup import restore_drill

        return restore_drill(settings, args.package, args.output)
    if args.command == "preflight":
        from trading_agent.observability.preflight import preflight, write_preflight

        report = preflight(settings, clock())
        if args.output:
            write_preflight(report, args.output)
        return report
    if args.command == "paper-init":
        strategy, feed_policy, model = paper_options(settings, args)
        if settings.database.exists() or not settings.stream_tokens:
            raise ValueError("paper-init requires a new database and reviewed stream tokens")
        broker = ReadOnlyKite.from_environment()
        broker.get_profile()
        catalog = [
            item for item in broker.get_instruments() if item.token in settings.stream_tokens
        ]
        if len(catalog) != len(settings.stream_tokens):
            raise ValueError("reviewed tokens are missing from the current equity catalog")
        settings.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(settings.database, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        source = Database(settings.database, settings.starting_cash)
        try:
            with source.transaction() as tx:
                for item in catalog:
                    tx.execute(
                        "INSERT INTO instruments VALUES (?,?,?)",
                        (item.symbol, item.token, str(item.tick_size)),
                    )
        finally:
            source.close()
        db, engine, runtime = attach_automation(settings, strategy, feed_policy, model)
        try:
            runtime.close(clock())
            return {
                "database": str(settings.database),
                "catalog_count": len(catalog),
                "automation_sha256": runtime.digest,
                "model_sha256": model.version if model else None,
                "armed": False,
                "cash": engine.snapshot(clock())["cash"],
                "mode": "paper",
            }
        finally:
            db.close()
    if args.command == "paper-demo":
        from trading_agent.paper.demo import run_paper_demo

        return run_paper_demo(args.directory)
    if args.command == "paper-report":
        from trading_agent.paper.report import paper_report

        if not settings.database.is_file():
            raise ValueError("paper report requires an existing account")
        source = Database(settings.database, settings.starting_cash)
        try:
            report = paper_report(source, args.output)
            return {"output": str(args.output), "gates": report["gates"], "ready_for_live": False}
        finally:
            source.close()
    if args.command == "ml-build":
        from trading_agent.backtesting.dataset import Dataset
        from trading_agent.ml.labeling import build_samples
        from trading_agent.ml.schema import LabelPolicy
        from trading_agent.strategy.rules import StrategySettings

        return build_samples(
            Dataset(args.dataset),
            strategy=StrategySettings.load(args.strategy),
            policy=settings,
            output=args.output,
            labels=LabelPolicy(horizon_minutes=args.horizon_minutes),
        )
    if args.command == "ml-train":
        from trading_agent.ml.samples import Samples
        from trading_agent.ml.schema import TrainingSettings
        from trading_agent.ml.training import train_model

        report = train_model(
            Samples(args.samples), settings=TrainingSettings.load(args.training), output=args.output
        )
        return {
            "output": str(args.output),
            "gates": report["gates"],
            "research_approved": report["research_approved"],
            "ready_for_live": False,
        }
    if args.command == "ml-demo":
        from trading_agent.ml.demo import run_ml_demo
        from trading_agent.ml.schema import TrainingSettings
        from trading_agent.strategy.rules import StrategySettings

        return run_ml_demo(
            args.directory,
            strategy=StrategySettings.load(args.strategy),
            training=TrainingSettings.load(args.training),
            policy=settings,
        )
    if args.command in ("backtest", "research-demo"):
        from trading_agent.backtesting.dataset import Dataset
        from trading_agent.backtesting.demo import create_demo_dataset
        from trading_agent.backtesting.runner import run_backtest
        from trading_agent.strategy.rules import StrategySettings

        strategy = StrategySettings.load(args.strategy)
        if args.command == "research-demo":
            args.directory.mkdir(parents=True, exist_ok=False, mode=0o700)
            dataset_path, output = args.directory / "dataset", args.directory / "run"
            create_demo_dataset(dataset_path, strategy)
        else:
            dataset_path, output = args.dataset, args.output
        model = None
        if args.command == "backtest":
            if args.allow_synthetic_model and not args.model:
                raise ValueError("synthetic model override requires --model")
            if args.model:
                from trading_agent.execution.costs import Charges
                from trading_agent.ml.inference import load_model
                from trading_agent.risk.policy import policy_fingerprint

                model = load_model(
                    args.model,
                    strategy_sha256=strategy.digest(),
                    policy_sha256=policy_fingerprint(settings),
                    charges_version=Charges().version,
                    allow_synthetic=args.allow_synthetic_model,
                )
        report = run_backtest(
            Dataset(dataset_path), strategy=strategy, policy=settings, output=output, model=model
        )
        return {
            "output": str(output),
            "status": report["status"],
            "metrics": report["metrics"],
            "research_gates": report["research_gates"],
            "ready_for_live": False,
        }
    if args.command == "export-research":
        from trading_agent.backtesting.export import export_dataset

        if not settings.database.is_file():
            raise ValueError("export requires an existing source database")
        source = Database(settings.database, settings.starting_cash)
        try:
            return export_dataset(
                source,
                SessionCalendar.load(settings.calendar),
                start=args.start,
                end=args.end,
                symbols=tuple(args.symbols),
                output=args.output,
                source=args.source,
                candle_file=args.candles,
            )
        finally:
            source.close()
    if args.command == "demo":
        return demo(args.directory)
    if args.command == "login-url":
        return {"login_url": login_url(os.environ.get("KITE_API_KEY", ""))}
    if args.command == "exchange-token":
        request_token = getpass.getpass("One-time request_token from manual Kite redirect: ")
        token = exchange_token(
            os.environ.get("KITE_API_KEY", ""), os.environ.get("KITE_API_SECRET", ""), request_token
        )
        if not token.isalnum():
            raise ValueError("invalid access token format")
        # O_EXCL avoids clobbering credentials; descriptor permissions are private from creation.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as file:
            file.write("export KITE_ACCESS_TOKEN='" + token + "'\n")
        return {"session_file": str(args.output), "next": "source file; restart stream worker"}
    if args.command == "profile":
        return ReadOnlyKite.from_environment().get_profile()
    automation = None
    if args.command == "serve" and args.automate:
        db, engine, automation = open_automated(settings, args)
    else:
        if args.command == "serve" and (args.rule_only or args.model):
            raise ValueError("automation options require --automate")
        db, engine = open_engine(settings)
    try:
        if args.command == "init-db":
            return {
                "database": str(settings.database),
                "cash": str(settings.starting_cash),
                "mode": "paper",
            }
        if args.command == "status":
            return engine.snapshot(clock())
        if args.command == "verify-db":
            with db.transaction() as tx:
                if tx.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("database integrity failure")
                db.reconcile(tx)
            return {"integrity": "ok", "accounting": "reconciled"}
        if args.command == "backup":
            db.backup(args.destination)
            return {"backup": str(args.destination)}
        if args.command == "instruments":
            instruments = ReadOnlyKite.from_environment().get_instruments()
            engine.register(instruments)
            return {"stored": len(instruments)}
        if args.command == "historical":
            with db.transaction() as tx:
                row = tx.execute(
                    "SELECT * FROM instruments WHERE symbol=?", (args.symbol,)
                ).fetchone()
            if row is None:
                raise ValueError("unknown symbol; import instruments first")
            item = Instrument(symbol=row["symbol"], token=row["token"], tick_size=row["tick"])
            now = clock()
            candles = ReadOnlyKite.from_environment().get_historical_candles(
                item, args.start, args.end, args.minutes, now
            )
            return {"stored": store_candles(db, candles, now)}
        if args.command == "replay":
            if engine.orders() or engine.snapshot(clock())["positions"]:
                raise ValueError("replay requires an unused account database")
            engine.register(
                [
                    Instrument.model_validate(item)
                    for item in json.loads(args.instruments.read_text())
                ]
            )
            with args.events.open() as file:
                return run_events(engine, (json.loads(line) for line in file if line.strip()))
        if args.command == "serve":
            import uvicorn

            from trading_agent.api.app import create_app

            configure_logging()
            stream: Any = None
            setup = None
            if not automation:
                from trading_agent.api.setup import SetupService

                setup = SetupService(
                    engine,
                    Path(args.config or os.environ.get("TRADING_CONFIG", "config/paper.toml")),
                    clock,
                )
                if args.stream:
                    setup.prepare_stream()
                stream = setup
            elif args.stream:
                broker = ReadOnlyKite.from_environment()
                broker.get_profile()
                with db.transaction() as tx:
                    catalog = [
                        Instrument(symbol=r["symbol"], token=r["token"], tick_size=r["tick"])
                        for r in tx.execute("SELECT * FROM instruments")
                        if r["token"] in settings.stream_tokens
                    ]
                if len(catalog) != len(settings.stream_tokens):
                    raise ValueError("configured tokens missing from reviewed catalog")
                from trading_agent.paper.service import PaperService

                stream = PaperService(automation, broker, clock)
            app = create_app(
                engine,
                stream=stream,
                automation=automation,
                setup=setup,
                open_browser=args.open,
                desk_profile=Path(os.environ["TRADING_ANALYSIS_PROFILE"])
                if os.environ.get("TRADING_ANALYSIS_PROFILE")
                else None,
            )
            uvicorn.run(
                app,
                host=settings.host,
                port=settings.port,
                workers=1,
                access_log=False,
                proxy_headers=bool(settings.public_origin),
                forwarded_allow_ips="127.0.0.1,::1",
                log_config=None,
            )
            return None
        raise ValueError("unknown command")
    finally:
        db.close()


def paper_options(
    settings: Settings, args: argparse.Namespace
) -> "tuple[StrategySettings, FeedSettings, ResearchModel | None]":
    from trading_agent.execution.costs import Charges
    from trading_agent.ml.inference import load_model
    from trading_agent.paper.config import FeedSettings
    from trading_agent.risk.policy import policy_fingerprint
    from trading_agent.strategy.rules import StrategySettings

    if (
        args.command == "serve" and not args.stream
    ) or not settings.operator_token.get_secret_value():
        raise ValueError("paper automation requires --stream and an operator token")
    if args.rule_only == bool(args.model):
        raise ValueError("select exactly one of --rule-only or --model")
    strategy, feed_policy = (
        StrategySettings.load(args.strategy),
        FeedSettings.load(args.feed_policy),
    )
    model = (
        load_model(
            args.model,
            strategy_sha256=strategy.digest(),
            policy_sha256=policy_fingerprint(settings),
            charges_version=Charges().version,
        )
        if args.model
        else None
    )
    return strategy, feed_policy, model


def open_automated(
    settings: Settings, args: argparse.Namespace
) -> "tuple[Database, PaperBroker, PaperFeed]":
    return attach_automation(settings, *paper_options(settings, args))


def attach_automation(
    settings: Settings,
    strategy: "StrategySettings",
    feed_policy: "FeedSettings",
    model: "ResearchModel | None",
) -> "tuple[Database, PaperBroker, PaperFeed]":
    from trading_agent.paper.config import feed_identity
    from trading_agent.paper.runtime import PaperFeed

    calendar = SessionCalendar.load(settings.calendar)
    db = Database(settings.database, settings.starting_cash)
    try:
        with db.transaction() as tx:
            catalog = [
                Instrument(symbol=row["symbol"], token=row["token"], tick_size=row["tick"])
                for row in tx.execute("SELECT * FROM instruments ORDER BY symbol")
                if row["token"] in settings.stream_tokens
            ]
        if not catalog or len(catalog) != len(settings.stream_tokens):
            raise ValueError("automation requires a reviewed registered stream catalog")
        _, signature = feed_identity(
            catalog, strategy, feed_policy, model.version if model else None, False
        )
        engine = PaperBroker(db, settings, calendar, model=model, automation=signature)
        engine.safety.enable(clock())
        runtime = PaperFeed(
            engine, instruments=catalog, strategy=strategy, settings=feed_policy, now=clock()
        )
        return db, engine, runtime
    except BaseException:
        db.close()
        raise


def main() -> None:
    os.umask(0o077)
    args = parser().parse_args()
    try:
        result = execute(args)
        if result is not None:
            print(json.dumps(result, indent=2, default=str))
            if args.command == "preflight" and args.strict and not result["local_checks_passed"]:
                sys.exit(2)
    except Exception as exc:
        # No exception repr/tracebacks: third-party errors can contain credentials.
        print(
            f"Command failed ({type(exc).__name__}); check configuration and operator runbook.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
