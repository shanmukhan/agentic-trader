"""Measure loaded JSON inference and ten-candidate ranking, without training or I/O."""

import argparse
import json
import platform
from datetime import timedelta
from pathlib import Path
from time import perf_counter_ns

from trading_agent.execution.costs import Charges
from trading_agent.ml.features import FEATURE_NAMES, FeatureVector
from trading_agent.ml.inference import ResearchModel, load_model
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings
from trading_agent.strategy.rules import StrategySettings


def benchmark(model: ResearchModel, samples: int) -> dict:
    now = model.artifact.available_after + timedelta(days=1)
    vector = FeatureVector(
        symbol="NSE:DEMO",
        time=now,
        candle_end=now,
        values=model.artifact.coefficients.means,
        candidate_sha256="0" * 64,
    )
    batch = [vector.model_copy(update={"symbol": f"NSE:TEST{i}"}) for i in range(10)]
    results = {}
    for name, size in (("inference", 1), ("rank_ten", 10)):
        elapsed = []
        for _ in range(samples):
            before = perf_counter_ns()
            if size == 1:
                model.score(vector)
            else:
                sorted(
                    ((model.score(item), item.symbol) for item in batch),
                    key=lambda item: (-item[0], item[1]),
                )
            elapsed.append(perf_counter_ns() - before)
        elapsed.sort()
        results[name] = {
            "samples": samples,
            **{
                f"p{p}_ms": elapsed[min(len(elapsed) - 1, int(len(elapsed) * p / 100))] / 1e6
                for p in (50, 95, 99)
            },
        }
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "model_sha256": model.version,
        "features": len(FEATURE_NAMES),
        "timings": results,
        "limitations": "Loaded coefficient math and sorting only; excludes feature construction, "
        "artifact loading, input decoding, training, risk/execution, disk and network. "
        "Not a Pi measurement.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/paper.toml"))
    parser.add_argument("--strategy", type=Path, default=Path("config/strategy.toml"))
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--allow-synthetic-model", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 100 <= args.samples <= 100000:
        parser.error("use 100 to 100000 samples")
    loaded = load_model(
        args.model,
        strategy_sha256=StrategySettings.load(args.strategy).digest(),
        policy_sha256=policy_fingerprint(Settings.load(args.config)),
        charges_version=Charges().version,
        allow_synthetic=args.allow_synthetic_model,
    )
    serialized = json.dumps(benchmark(loaded, args.samples), indent=2) + "\n"
    print(serialized, end="")
    if args.output:
        args.output.write_text(serialized)
