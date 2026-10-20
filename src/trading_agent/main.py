"""Operator commands. Broker secrets are read from environment or hidden prompts only."""

import argparse
import getpass
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_agent.broker.readonly_kite import (
    QuoteStream,
    ReadOnlyKite,
    exchange_token,
    login_url,
)
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import SessionCalendar
from trading_agent.market_data.candles import CandleBuilder
from trading_agent.market_data.repository import store_candles
from trading_agent.models import Instrument, Quote
from trading_agent.observability.logging import configure_logging
from trading_agent.persistence.database import Database
from trading_agent.replay import demo, run_events
from trading_agent.settings import Settings


def clock() -> datetime:
    return datetime.now(UTC)


def open_engine(settings: Settings) -> tuple[Database, PaperBroker]:
    calendar = SessionCalendar.load(settings.calendar)
    database = Database(settings.database, settings.starting_cash)
    try:
        return database, PaperBroker(database, settings, calendar)
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
    serve.add_argument(
        "--stream", action="store_true", help="enable authenticated read-only Kite feed"
    )
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
            stream = None
            if args.stream:
                ReadOnlyKite.from_environment().get_profile()
                with db.transaction() as tx:
                    catalog = [
                        Instrument(symbol=r["symbol"], token=r["token"], tick_size=r["tick"])
                        for r in tx.execute("SELECT * FROM instruments")
                        if r["token"] in settings.stream_tokens
                    ]
                if len(catalog) != len(settings.stream_tokens):
                    raise ValueError("configured tokens missing from reviewed catalog")
                builders = (CandleBuilder(1), CandleBuilder(5))

                def ingest(quote: Quote) -> None:
                    now = clock()
                    if engine.ingest(quote, now):
                        try:
                            for builder in builders:
                                store_candles(db, builder.update(quote), now)
                        except Exception:
                            engine.faulted = True
                            engine.set_connected(False)
                            raise

                def connection_changed(connected: bool) -> None:
                    engine.set_connected(connected)
                    if not connected:
                        for builder in builders:
                            builder.active.clear()
                            builder.previous.clear()

                stream = QuoteStream(catalog, ingest, connection_changed, clock)
            app = create_app(engine, stream=stream)
            uvicorn.run(
                app,
                host=settings.host,
                port=settings.port,
                workers=1,
                access_log=False,
                proxy_headers=False,
                log_config=None,
            )
            return None
        raise ValueError("unknown command")
    finally:
        db.close()


def main() -> None:
    os.umask(0o077)
    args = parser().parse_args()
    try:
        result = execute(args)
        if result is not None:
            print(json.dumps(result, indent=2, default=str))
    except Exception as exc:
        # No exception repr/tracebacks: third-party errors can contain credentials.
        print(
            f"Command failed ({type(exc).__name__}); check configuration and operator runbook.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
