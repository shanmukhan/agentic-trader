"""Expanding whole-session splits with label-interval purge and time embargo."""

from dataclasses import dataclass
from datetime import date, timedelta

from trading_agent.market_data.calendar import IST
from trading_agent.ml.schema import Sample, TrainingSettings


@dataclass(frozen=True)
class Split:
    name: str
    train: tuple[Sample, ...]
    calibration: tuple[Sample, ...]
    evaluation: tuple[Sample, ...]
    purged_train: int
    purged_calibration: int


def chronological_splits(
    rows: list[Sample], sessions: tuple[date, ...], settings: TrainingSettings
) -> list[Split]:
    if tuple(sorted(set(sessions))) != sessions:
        raise ValueError("sessions must be strictly chronological")
    cfg = settings
    development = len(sessions) - cfg.holdout_sessions
    first_train = (
        development - cfg.calibration_sessions - cfg.validation_sessions * cfg.walk_forward_folds
    )
    if first_train < cfg.min_train_sessions:
        raise ValueError("insufficient chronological sessions for the predeclared split policy")
    result = []
    for fold in range(cfg.walk_forward_folds + 1):
        final = fold == cfg.walk_forward_folds
        train_end = (
            development - cfg.calibration_sessions
            if final
            else first_train + fold * cfg.validation_sessions
        )
        calibration_end = train_end + cfg.calibration_sessions
        evaluation_end = len(sessions) if final else calibration_end + cfg.validation_sessions
        blocks = []
        for a, b in (
            (0, train_end),
            (train_end, calibration_end),
            (calibration_end, evaluation_end),
        ):
            days = set(sessions[a:b])
            blocks.append(
                tuple(row for row in rows if row.features.time.astimezone(IST).date() in days)
            )
        train, calibration, evaluation = blocks
        if not all(blocks):
            raise ValueError("empty chronological train/calibration/evaluation block")
        embargo = timedelta(minutes=cfg.embargo_minutes)
        cal_start = min(row.features.time for row in calibration)
        eval_start = min(row.features.time for row in evaluation)
        kept_train = tuple(row for row in train if row.label_end + embargo < cal_start)
        kept_cal = tuple(row for row in calibration if row.label_end + embargo < eval_start)
        result.append(
            Split(
                "holdout" if final else f"fold_{fold + 1}",
                kept_train,
                kept_cal,
                evaluation,
                len(train) - len(kept_train),
                len(calibration) - len(kept_cal),
            )
        )
    return result
