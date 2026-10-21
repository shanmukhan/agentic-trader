"""Decision materialization must match its journal, including authorization and recovery."""

import json
import sqlite3

STATES = {
    "awaiting_approval",
    "authorized",
    "submitted",
    "rejected",
    "cancelled",
    "expired",
    "blocked",
}


def prepared_fingerprint(record: dict) -> str:
    from trading_agent.execution.paper_broker import intent_fingerprint
    from trading_agent.ml.features import FeatureVector
    from trading_agent.models import Candidate

    candidate = Candidate.model_validate(record["prepared_candidate"])
    if candidate.intent_id != record["intent_id"] or candidate.symbol != record["symbol"]:
        raise RuntimeError("decision instruction identity differs")
    features = (
        FeatureVector.model_validate(record["prepared_features"]) if candidate.requires_ml else None
    )
    return intent_fingerprint(candidate, features, record["review"]["maximum_quantity"])


def reconcile_desk(tx: sqlite3.Connection) -> None:
    expected = {}
    for row in tx.execute(
        "SELECT entity,payload FROM events WHERE kind='desk_decision' ORDER BY seq"
    ):
        payload = json.loads(row[1])
        if payload.get("id") != row[0] or payload.get("state") not in STATES:
            raise RuntimeError("invalid decision journal")
        expected[row[0]] = payload
    actual = {}
    for row in tx.execute("SELECT * FROM desk_decisions"):
        payload = json.loads(row["payload"])
        if (payload.get("id"), payload.get("created_at"), payload.get("state")) != (
            row["id"],
            row["time"],
            row["state"],
        ):
            raise RuntimeError("decision metadata differs from journal")
        actual[row["id"]] = payload
        if payload.get("order_id"):
            order = tx.execute(
                "SELECT symbol,side,fingerprint FROM orders WHERE id=?", (payload["order_id"],)
            ).fetchone()
            if order is None or (order[0], order[1]) != (payload["symbol"], payload["side"]):
                raise RuntimeError("decision order link differs from account")
            if payload["side"] == "BUY" and order[2] != prepared_fingerprint(payload):
                raise RuntimeError("decision authorization differs from order fingerprint")
    if expected != actual:
        raise RuntimeError("decision materialization differs from journal")
    for row in tx.execute("SELECT entity,payload FROM events WHERE kind='decision_authority'"):
        authority = json.loads(row[1])
        record = actual.get(authority["decision_id"])
        order = tx.execute("SELECT fingerprint FROM orders WHERE id=?", (row[0],)).fetchone()
        if (
            not record
            or not order
            or authority["fingerprint"] != order[0]
            or prepared_fingerprint(record) != order[0]
        ):
            raise RuntimeError("missing or invalid durable trade authorization")
