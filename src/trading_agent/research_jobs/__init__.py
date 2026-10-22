"""Isolated legacy-offline daily backtests; never grants paper-account authority."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from trading_agent.research_jobs.jobs import BacktestJobs, JobError
    from trading_agent.research_jobs.registry import register_bundle

__all__ = ["BacktestJobs", "JobError", "register_bundle"]


def __getattr__(name: str) -> Any:
    # The worker imports isolation before applying hard limits; do not load third-party
    # parsers or account classes as an implicit package-import side effect.
    if name == "register_bundle":
        from trading_agent.research_jobs.registry import register_bundle

        return register_bundle
    if name in {"BacktestJobs", "JobError"}:
        from trading_agent.research_jobs.jobs import BacktestJobs, JobError

        return BacktestJobs if name == "BacktestJobs" else JobError
    raise AttributeError(name)
