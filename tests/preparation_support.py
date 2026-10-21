"""INVENTED provider responses for isolated workflow tests, never market acceptance."""

import csv
import io
import json
from datetime import datetime, timedelta
from decimal import Decimal as D
from types import SimpleNamespace

from conftest import NOW

from trading_agent.api.setup import SetupService
from trading_agent.desk import sources
from trading_agent.desk.preparation import DownloadRequest, InstallRequest, Preparation
from trading_agent.desk.service import TradingDesk
from trading_agent.market_data.calendar import IST
from trading_agent.models import Instrument, stamp

TEST_NOW = NOW + timedelta(days=1)


def make_preparation(tmp_path, monkeypatch, factory):
    e = factory(stream_tokens=(257,))
    e.calendar.sources = {day: "INVENTED prior account review" for day in e.calendar.sessions}
    e.register(
        [
            Instrument(symbol=f"NSE:A{i:03}", token=257 + i * 256, tick_size=D(".05"))
            for i in range(99)
        ]
    )
    config = tmp_path / "account.toml"
    values = e.settings.model_dump(mode="json", exclude={"operator_token"})
    # The setup writer validates the real Settings contract, including unchanged financial policy.
    config.write_text("\n".join(k + " = " + json.dumps(v) for k, v in values.items()) + "\n")
    clock = [TEST_NOW]
    setup = SetupService(e, config, lambda: clock[0])
    setup.values = {
        "api_key": "INVENTED-key",
        "api_secret": "INVENTED-secret",
        "access_token": "INVENTED-token",
    }
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(("Company Name", "Industry", "Symbol", "Series", "ISIN Code"))
    for i in range(100):
        writer.writerow((f"INVENTED {i}", "TEST", f"A{i:03}", "EQ", f"INE{i:09}"))
    holidays = json.dumps(
        {
            "CM": [
                {"tradingDate": d}
                for d in ["26-Jan-2026", "01-May-2026", "15-Aug-2026", "02-Oct-2026", "20-Oct-2026"]
            ]
        }
    ).encode()
    calendar = sources.proposed_sessions(holidays, TEST_NOW.astimezone(IST).date())
    days = [s.day for s in calendar if datetime.combine(s.day, s.close, IST) <= TEST_NOW][-60:]
    requests = []

    def read(url, params=None):
        requests.append((url, params))
        if url in sources.UNIVERSES.values():
            return output.getvalue().encode()
        if url == sources.HOLIDAYS:
            return holidays
        return json.dumps(
            [
                {
                    "symbol": "A001",
                    "exDate": days[2].strftime("%d-%b-%Y"),
                    "subject": "INVENTED dividend",
                }
            ]
        ).encode()

    class Broker:
        def __init__(self):
            self.calls = []

        def get_profile(self):
            return {"authenticated": True}

        def get_daily_history(self, instrument, start, end, as_of):
            self.calls.append(instrument.symbol)
            rows = []
            for i, day in enumerate(days):
                price = D(500) - D(59 - i) / 2
                rows.append(
                    dict(
                        symbol=instrument.symbol,
                        session=day.isoformat(),
                        open=str(price),
                        high=str(price + 1),
                        low=str(price - 1),
                        close=str(price),
                        volume=1_000_000,
                        price_available_at=stamp(as_of),
                        basis_reviewed_at=stamp(as_of),
                        basis_reference="INVENTED unreviewed observation",
                        share_numerator=1,
                        share_denominator=1,
                        cash_per_previous_share="0",
                    )
                )
            return rows[:-1] if instrument.symbol == "NSE:A002" else rows

    broker = Broker()
    monkeypatch.setattr(sources, "public_read", read)
    monkeypatch.setattr(setup, "broker", lambda: broker)
    desk = TradingDesk(e, TEST_NOW, clock=lambda: clock[0])
    prep = Preparation(desk, setup, lambda: clock[0])
    return SimpleNamespace(
        engine=e,
        desk=desk,
        setup=setup,
        prep=prep,
        clock=clock,
        requests=requests,
        broker=broker,
        days=days,
    )


def download(s):
    request = DownloadRequest(
        universe="nifty100", request_id="b" * 32, revision=s.desk.revision, acknowledged=True
    )
    s.prep.start(request)
    s.prep.thread.join(timeout=5)
    assert not s.prep.thread.is_alive()
    assert s.prep.state["state"] == "ready_for_review", s.prep.state
    return request


def installation(s, **updates):
    state = s.prep.state
    return InstallRequest.model_validate(
        {
            "preview_sha256": state["preview_sha256"],
            "revision": s.desk.revision,
            "strategy_mode": "rules",
            "calendar_csv": state["calendar_csv"],
            "reference": "INVENTED test source review",
            "calendar_reviewed": True,
            "basis_reviewed": True,
            "policy_reviewed": True,
            **updates,
        }
    )
