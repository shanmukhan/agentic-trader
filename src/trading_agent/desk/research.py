"""Broad prior-daily research runs outside the quote/risk lock; no invented model scores."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any

from trading_agent.daily_execution.model import load_daily_model
from trading_agent.daily_execution.timeline import DailyTimeline
from trading_agent.daily_research.analysis import analyze
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.desk.contracts import AnalysisProfile, digest
from trading_agent.ml.inference import load_model
from trading_agent.risk.policy import policy_fingerprint


class Research:
    def __init__(self, engine: Any, path: Path, now: datetime, *, synthetic: bool = False):
        self.profile = AnalysisProfile.load(path)
        self.dataset = DailyDataset(self.profile.daily_dataset)
        if self.dataset.manifest.synthetic and not synthetic:
            raise ValueError("Synthetic daily data cannot drive a connected trading desk.")
        if any(s.reviewed_at > now for s in self.profile.shares):
            raise ValueError("Share-class reviews are not yet available.")
        symbols = {m.symbol for m in self.dataset.manifest.universe}
        shares = {s.symbol for s in self.profile.shares}
        if not shares <= symbols:
            raise ValueError("Reviewed equity shares must belong to the declared daily universe.")
        with engine.lock, engine.db.transaction() as tx:
            self.timeline_symbols = {
                r[0]
                for r in tx.execute("SELECT symbol,token FROM instruments")
                if r[1] in engine.settings.stream_tokens
            }
        self.timeline = DailyTimeline(
            self.dataset, self.timeline_symbols, self.profile.long_term.screen
        )
        self.synthetic = self.dataset.manifest.synthetic
        self.model: Any = None
        if self.profile.strategy_mode == "rules_ml":
            if self.profile.model_directory is None:
                raise ValueError(
                    "Rules + ML needs a matching independently validated model directory."
                )
            if engine.long_term:
                self.model = load_daily_model(
                    self.profile.model_directory,
                    strategy=self.profile.long_term,
                    policy=engine.settings,
                    allow_synthetic=synthetic,
                )
            else:
                self.model = load_model(
                    self.profile.model_directory,
                    strategy_sha256=self.profile.intraday.digest(),
                    policy_sha256=policy_fingerprint(engine.settings),
                    charges_version=engine.charges.version,
                    allow_synthetic=synthetic,
                )
        self.result: dict[str, Any] = {}
        self.identity = digest(
            {
                "profile": self.profile.model_dump(mode="json"),
                "data": self.dataset.hashes,
                "model": self.model.version if self.model else None,
            }
        )
        self.refresh(now)

    def ensure_symbols(self, symbols: set[str], now: datetime) -> None:
        if symbols != self.timeline_symbols:
            if self.dataset.fingerprints() != self.dataset.hashes:
                raise ValueError("Reviewed daily inputs changed.")
            timeline = DailyTimeline(self.dataset, symbols, self.profile.long_term.screen)
            self.timeline, self.timeline_symbols = timeline, symbols
        self.timeline.advance(now)

    def refresh(self, now: datetime) -> None:
        started = perf_counter()
        # analyze checks source hashes before publishing; future/incomplete data is excluded.
        result = analyze(self.dataset, self.profile.long_term.screen, now)
        reviewed = {s.symbol for s in self.profile.shares if s.reviewed_at <= now}
        for row in result["rows"]:
            if row["symbol"] not in reviewed:
                row.update(status="screened_out", rank=None)
                row["reasons"] = [*row["reasons"], "EQUITY_SHARE_CLASS_NOT_REVIEWED"]
        ranked = sorted(
            (r for r in result["rows"] if r["status"] == "research_candidate"),
            key=lambda r: (-Decimal(r["gross_total_return_pct"]), r["symbol"]),
        )
        for rank, row in enumerate(ranked, 1):
            row["rank"] = rank
        result["candidate_count"] = len(ranked)
        result["timing"] = {
            "local_screen_ms": (perf_counter() - started) * 1000,
            "network_included": False,
        }
        self.result = result
