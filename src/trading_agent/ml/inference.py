class ModelUnavailable(RuntimeError):
    pass


class PhaseOneScorer:
    version = "phase1-stub"

    def score(self, features: dict[str, object]) -> float:
        raise ModelUnavailable("ML training and calibrated ranking are deferred to Phase 3")
