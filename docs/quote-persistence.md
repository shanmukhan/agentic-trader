# Quote persistence, read snapshots and recovery

The manual **Broker & Data** stream now commits one decoded nonempty quote frame in
one SQLite transaction. No new option is required: stop the owning server, update
its environment with `uv sync --extra broker --extra dev`, then restart using your
existing config (`./scripts/start_ui.sh`). Reconnect and choose any operating mode
through the normal reviewed controls. Restarting does not approve price bases or
restore trading authority.

Every accepted quote still updates the saved quote and appends its complete quote
event. Every quote runs the existing ordering, cumulative-volume, freshness,
price-basis, stop/target, portfolio-risk and fill checks in received order. The live
manual callback samples the processing clock again for each quote, including time
spent waiting for the writer or processing earlier quotes; a large frame cannot
freeze freshness. A backwards processing clock aborts the frame. Unchanged
repeats remain ignored. Ordered changed Kite books within one exchange second cannot
replenish that second's fill-depth budget. A temporary stop/target excursion inside a
frame still queues protection; fills still require eligible later observations and
latency. A successful frame is fully committed before its callback returns.

This reduces commit/fsync count when one frame carries multiple quotes. It does not
throttle, discard or invent observations. Complete quote history is required by
corporate-action reconciliation and causal replay export. Single-quote frames still
commit individually. The separate automated `PaperService` callback retains its
per-quote controller/telemetry behavior. No ring buffer, Redis, worker migration or
3,000-symbol throughput claim is introduced. Large frames still serialize engine
work, and every retained quote still consumes journal space.

The manual callback updates both one-minute and five-minute candle builders for each
accepted quote after the financial frame commits. It stores only completed candles,
in a separate transaction when any exist. Initial-volume and gap quality labels are
preserved; an empty storage batch no longer acquires the writer. Candle evidence and
financial evidence are separate commits, as before; they are not a single atomic
publication.

If a mapping/tick or storage error aborts the financial frame, its entire financial
transaction rolls back. Trust is revoked for all symbols in that frame so earlier
saved quotes cannot become usable after a partial callback. SQL/runtime failures
latch the engine fault/disconnection. A candle failure after financial commit faults
the callback, but does not undo already committed fills. Inspect saved orders, fills,
quote events and candle coverage before recovery; do not retry a failed frame to
invent liquidity or clear a fault. Preserve the account and investigate the actual
cause before a normal restart, fresh connection and explicit authorization.

## Read-only operator views

`Database.read_snapshot()` opens an independent read-only, query-only SQLite
connection with a consistent committed WAL snapshot. Status/account snapshots,
console, order lists, readiness and the proposal-alert endpoint use this boundary.
They do not reserve the writer using `BEGIN IMMEDIATE`. Orders and proposal metadata
can be read during an uncommitted writer and never expose its tentative changes.
Accidental SQL mutations through this reader fail.

Views combining persisted data with in-memory connection, quote-trust or controller
authority still take the engine lock. Other workflow/status operations retain their
existing transactions. This change is partial contention remediation; no read pool,
latency guarantee or automatic fault reset is supplied. Independent readers can pin
WAL pages until closed; each helper context promptly closes its connection.

## Local validation

Run from the prepared development environment:

```sh
.venv/bin/pytest tests/unit/test_quote_batches.py tests/unit/test_database_snapshots.py tests/long_term/test_delivery_quote_batches.py tests/functional/test_quote_frame_persistence.py -q
```

Expected results include one commit per multi-quote frame, sequential/batch persisted
state equality, exact independent cash/fees/delivery-DP checks, partial-fill and
protective-exit behavior, whole-frame rollback, completed candle preservation,
read-only mutation rejection, per-quote processing freshness/clock regression and
committed reads during an active writer. All inputs
are invented local observations. These tests do not validate real broker throughput,
market fillability, power-loss recovery or device acceptance. See the separate
[feed capacity limits](paper-feed.md), [setup recovery](ui-setup.md), and
[proposal-alert behavior](trading-desk.md).
