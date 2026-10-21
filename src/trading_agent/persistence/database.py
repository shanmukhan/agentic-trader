"""SQLite single-writer transactions, durable WAL and consistent online backups."""

import fcntl
import json
import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL,
    kind TEXT NOT NULL, entity TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS instruments (
    symbol TEXT PRIMARY KEY, token INTEGER NOT NULL UNIQUE, tick TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quotes (
    symbol TEXT PRIMARY KEY, time TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candles (
    symbol TEXT NOT NULL, start TEXT NOT NULL, minutes INTEGER NOT NULL,
    payload TEXT NOT NULL, PRIMARY KEY(symbol,start,minutes)
);
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
    state TEXT NOT NULL CHECK(state IN
        ('CREATED','ACCEPTED','PARTIAL','FILLED','CANCELLED','REJECTED')),
    quantity INTEGER NOT NULL CHECK(quantity >= 0), filled INTEGER NOT NULL DEFAULT 0,
    cap TEXT NOT NULL, stop TEXT NOT NULL, target TEXT NOT NULL,
    reserved_cash TEXT NOT NULL, reserved_risk TEXT NOT NULL,
    turnover TEXT NOT NULL DEFAULT '0', fees TEXT NOT NULL DEFAULT '0',
    created TEXT NOT NULL, reason TEXT NOT NULL,
    CHECK(filled >= 0 AND filled <= quantity)
);
CREATE INDEX IF NOT EXISTS pending_orders ON orders(state,symbol);
CREATE TABLE IF NOT EXISTS fills (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT NOT NULL REFERENCES orders(id),
    time TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity > 0),
    price TEXT NOT NULL, fees TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY, quantity INTEGER NOT NULL CHECK(quantity > 0),
    cost TEXT NOT NULL, stop TEXT NOT NULL, target TEXT NOT NULL,
    opened TEXT NOT NULL
);
PRAGMA user_version=1;
"""


CORPORATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS corporate_batches (
    id TEXT PRIMARY KEY, time TEXT NOT NULL, symbol TEXT NOT NULL,
    request TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS corporate_payments (
    id TEXT PRIMARY KEY, time TEXT NOT NULL, claim_id TEXT NOT NULL UNIQUE,
    request TEXT NOT NULL, payload TEXT NOT NULL
);
"""

PORTFOLIO_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_requests (
    id TEXT PRIMARY KEY, time TEXT NOT NULL, request TEXT NOT NULL, preview TEXT NOT NULL,
    plan_id TEXT, occurrence TEXT, UNIQUE(plan_id,occurrence)
);
CREATE TABLE IF NOT EXISTS sip_plans (
    id TEXT PRIMARY KEY, time TEXT NOT NULL, request TEXT NOT NULL, sessions TEXT NOT NULL,
    cancelled INTEGER NOT NULL CHECK(cancelled IN (0,1))
);
CREATE INDEX IF NOT EXISTS acquisition_orders ON orders(side);
"""

DESK_SCHEMA = """
CREATE TABLE IF NOT EXISTS desk_decisions (
    id TEXT PRIMARY KEY, time TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS desk_pending ON desk_decisions(state,time);
CREATE INDEX IF NOT EXISTS desk_order ON desk_decisions(json_extract(payload,'$.order_id'));
CREATE INDEX IF NOT EXISTS events_entity_kind ON events(entity,kind,seq);
CREATE INDEX IF NOT EXISTS fills_order ON fills(order_id,seq);
"""


class Database:
    def __init__(self, path: Path, starting_cash: Decimal):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = path
        self.lock = threading.RLock()
        self._owner: int | None = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self._owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self._owner)
            raise RuntimeError("account database already owned by another process") from None
        try:
            self._initialize(starting_cash)
        except BaseException:
            self.close()
            raise

    def _initialize(self, starting_cash: Decimal) -> None:
        path = self.path
        self.connection = sqlite3.connect(
            path, timeout=3, isolation_level=None, check_same_thread=False
        )
        path.chmod(0o600)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            raise RuntimeError("unsupported database schema")
        if version == 0:
            self.connection.executescript("BEGIN IMMEDIATE;" + SCHEMA + "COMMIT;")
        self.connection.executescript(CORPORATE_SCHEMA)
        self.connection.executescript(PORTFOLIO_SCHEMA)
        self.connection.executescript(DESK_SCHEMA)
        # Compatible additive index: runtime candidate lookups must not scan quote history.
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS events_kind_time ON events(kind,time,seq)"
        )
        with self.transaction() as tx:
            defaults = {
                "cash": str(starting_cash),
                "initial_cash": str(starting_cash),
                "kill": "false",
                "kill_reason": "",
                "loss_streak": "0",
                "day": "",
                "day_equity": str(starting_cash),
                "day_realized": "0",
                "total_realized": "0",
                "fees": "0",
            }
            for key, value in defaults.items():
                if version == 0:
                    tx.execute("INSERT INTO meta VALUES (?,?)", (key, value))
                else:
                    self.get(
                        tx, key
                    )  # Missing durable state must never silently reset a safeguard.
            if Decimal(self.get(tx, "initial_cash")) != starting_cash:
                raise ValueError("starting cash differs from existing account; use a new database")
            self.reconcile(tx)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self.connection
                self.connection.commit()
            except BaseException:
                self.connection.rollback()
                raise

    @staticmethod
    def get(tx: sqlite3.Connection, key: str) -> str:
        row = tx.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if row is None:
            raise RuntimeError("missing required system state")
        return str(row[0])

    @staticmethod
    def set(tx: sqlite3.Connection, key: str, value: object) -> None:
        tx.execute(
            "INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )

    @staticmethod
    def event(
        tx: sqlite3.Connection, time: str, kind: str, entity: str, payload: dict[str, Any]
    ) -> None:
        tx.execute(
            "INSERT INTO events(time,kind,entity,payload) VALUES (?,?,?,?)",
            (time, kind, entity, json.dumps(payload, sort_keys=True, default=str)),
        )

    @staticmethod
    def reconcile(tx: sqlite3.Connection) -> None:
        from trading_agent.desk.accounting import reconcile_desk

        reconcile_desk(tx)
        from trading_agent.execution.delivery import reconcile_delivery

        reconcile_delivery(tx)
        from trading_agent.corporate_actions.accounting import Ledger

        ledger = Ledger(tx)
        cash, realized, total_fees = ledger.cash, ledger.realized, ledger.fees
        turnovers, order_fees = ledger.turnovers, ledger.order_fees
        holdings = {symbol: position["quantity"] for symbol, position in ledger.positions.items()}
        costs = {symbol: Decimal(position["cost"]) for symbol, position in ledger.positions.items()}
        positions = tx.execute("SELECT * FROM positions").fetchall()
        actual = {r["symbol"]: r["quantity"] for r in positions}
        if cash != Decimal(Database.get(tx, "cash")) or actual != {
            symbol: qty for symbol, qty in holdings.items() if qty
        }:
            raise RuntimeError("portfolio reconciliation failed")
        if (
            total_fees != Decimal(Database.get(tx, "fees"))
            or realized != Decimal(Database.get(tx, "total_realized"))
            or any(Decimal(row["cost"]) != costs[row["symbol"]] for row in positions)
        ):
            raise RuntimeError("cost and P&L reconciliation failed")
        if any(
            row["opened"] != ledger.positions[row["symbol"]]["opened"]
            or any(
                Decimal(row[key]) != Decimal(ledger.positions[row["symbol"]][key])
                for key in ("stop", "target")
            )
            for row in positions
        ):
            raise RuntimeError("protective holding metadata differs from ledger")
        if Database.get(tx, "kill") not in ("true", "false"):
            raise RuntimeError("invalid durable kill state")
        reserved = sum(
            (
                Decimal(r[0])
                for r in tx.execute(
                    "SELECT reserved_cash FROM orders WHERE state IN ('ACCEPTED','PARTIAL')"
                )
            ),
            Decimal(0),
        )
        if cash < reserved or cash < 0:
            raise RuntimeError("invalid cash reservations")
        for row in tx.execute(
            "SELECT o.*,COALESCE(SUM(f.quantity),0) AS total "
            "FROM orders o LEFT JOIN fills f ON o.id=f.order_id GROUP BY o.id"
        ):
            if row["filled"] != row["total"]:
                raise RuntimeError("fill reconciliation failed")
            reservations = (Decimal(row["reserved_cash"]), Decimal(row["reserved_risk"]))
            if any(not value.is_finite() or value < 0 for value in reservations):
                raise RuntimeError("invalid durable reservation")
            pending = row["state"] in ("ACCEPTED", "PARTIAL")
            if (not pending or row["side"] == "SELL") and any(reservations):
                raise RuntimeError("terminal/exit order retains reservation")
            if pending and (row["quantity"] <= row["filled"] or row["quantity"] <= 0):
                raise RuntimeError("invalid pending order quantity")
            if Decimal(row["turnover"]) != turnovers.get(row["id"], Decimal(0)) or Decimal(
                row["fees"]
            ) != order_fees.get(row["id"], Decimal(0)):
                raise RuntimeError("order turnover reconciliation failed")
            if (
                row["state"] == "FILLED"
                and row["quantity"] != row["filled"]
                or row["state"] == "PARTIAL"
                and not 0 < row["filled"] < row["quantity"]
            ):
                raise RuntimeError("invalid durable order state")

    def backup(self, destination: Path) -> None:
        if destination.resolve() == self.path.resolve() or destination.exists():
            raise ValueError("backup must be a new file")
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        with self.lock, closing(sqlite3.connect(destination)) as target:
            self.connection.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("backup integrity check failed")
        destination.chmod(0o600)

    def close(self) -> None:
        with self.lock:
            if hasattr(self, "connection"):
                self.connection.close()
            if self._owner is not None:
                os.close(self._owner)
                self._owner = None
