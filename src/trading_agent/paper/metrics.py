"""O(1) observation with bounded recent-window percentile calculation on demand."""

import math
from collections import Counter, deque
from typing import Any


class Timings:
    def __init__(self, budget_ms: int):
        self.budget_ms = budget_ms
        self.values: dict[str, deque[float]] = {}
        self.counts: Counter[str] = Counter()
        self.over_budget: Counter[str] = Counter()
        self.maxima: dict[str, float] = {}

    def observe(self, stage: str, milliseconds: float) -> None:
        if not math.isfinite(milliseconds) or milliseconds < 0:
            raise ValueError("invalid duration")
        self.values.setdefault(stage, deque(maxlen=512)).append(milliseconds)
        self.counts[stage] += 1
        self.over_budget[stage] += int(milliseconds > self.budget_ms)
        self.maxima[stage] = max(milliseconds, self.maxima.get(stage, 0.0))

    def snapshot(self) -> dict[str, Any]:
        result = {}
        for name, values in self.values.items():
            ordered = sorted(values)
            result[name] = {
                "total_count": self.counts[name],
                "window_count": len(ordered),
                "over_budget_count": self.over_budget[name],
                "maximum_ms": self.maxima[name],
                **{
                    f"p{p}_ms": ordered[
                        min(len(ordered) - 1, math.ceil(len(ordered) * p / 100) - 1)
                    ]
                    for p in (50, 95, 99)
                },
            }
        return result
