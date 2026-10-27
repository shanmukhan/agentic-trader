# Backend Architecture Roadmap: Scaling from Paper Engine to Autonomous Live Trading Platform

**Target System:** Agentic Trader Backend Engine  
**Scope:** Architectural Redesign, Live Broker Execution OMS, High-Throughput Tick Pipeline, Multi-Mode State Machine & Persistence  
**Modes Supported:** Manual, Semi-Autonomous (Approval Flow), Fully Autonomous  
**Status:** Architecture Blueprint & Implementation Roadmap (Zero Code Modified)

---

## 1. Current Backend Technical Debt & Architectural Bottlenecks

A rigorous code-level audit of `src/trading_agent/` reveals key bottlenecks that prevent the current backend from supporting production workloads and live capital execution:

```
+----------------------------------------------------------------------------------------------------+
|                               CURRENT BACKEND BOTTLENECK PROFILE                                   |
+----------------------------------------------------------------------------------------------------+
| [ Incoming WebSocket Ticks ]                                                                       |
|             │                                                                                      |
|             ▼                                                                                      |
|   PaperBroker.ingest(quote)  ───► ACQUIRES GLOBAL RE-ENTRANT LOCK (PaperBroker.lock)              |
|             │                                                                                      |
|             ├──► SQLite BEGIN IMMEDIATE (Database.lock)                                            |
|             ├──► INSERT/UPDATE into `quotes` table (Disk I/O)                                      |
|             ├──► INSERT into `events` table (Disk I/O)                                              |
|             ├──► _watch() / _process() / _fill() (Order evaluation)                                |
|             └──► Transaction COMMIT                                                                |
|                                                                                                    |
|   * RESULT: REST API requests (/api/console, /api/desk) hang waiting for the SQLite lock!          |
|   * Write Amplification: 100 ticks/sec = 200 disk writes/sec in SQLite WAL!                         |
|   * Hardcoded Constraints: Hard ceiling of 10 symbols (stream_tokens) across settings & parser!    |
|   * Live Execution: ZERO code paths exist to place real broker orders.                             |
+----------------------------------------------------------------------------------------------------+
```

### 1.1 Summary of Specific Code Bottlenecks

1. **Zero Live Order Execution Capability:**
   - In `src/trading_agent/broker/readonly_kite.py`, `RestrictedKiteHTTP` allows only three HTTP paths: `user.profile`, `market.instruments`, and `market.historical`.
   - The official Kite SDK's order methods are intentionally missing. To trade real money, the system must build an enterprise Order Management System (OMS) with rate limiting, error handling, order state reconciliation, and postback processing.

2. **Database Write Amplification on Tick Ingestion:**
   - In `PaperBroker.ingest()`, every incoming tick performs a database transaction:
     ```python
     # src/trading_agent/execution/paper_broker.py:747-751
     tx.execute(
         "INSERT INTO quotes VALUES (?,?,?) ON CONFLICT(symbol) DO UPDATE SET "
         "time=excluded.time,payload=excluded.payload",
         ...,
     )
     self.db.event(tx, stamp(now), "quote", quote.symbol, quote.model_dump(mode="json"))
     ```
   - In a volatile market, liquid stocks generate tens of thousands of ticks per hour. Writing every tick to SQLite disk storage creates extreme WAL write amplification, disk thrashing, and high latency.

3. **Global Lock Contention:**
   - `PaperBroker.lock` wraps tick ingestion, the risk watchdog, order submission, cancellation, and position snapshots.
   - When REST clients poll `/api/console` or `/api/desk`, they acquire this same lock (`engine.lock`). During market bursts, read endpoints lag, causing browser timeouts.

4. **Hardcoded 10-Symbol Streaming Limit:**
   - `Settings.stream_tokens` enforces `len <= 10`.
   - `QuoteStream` enforces `1 <= len(self.instruments) <= 10`.
   - `_parse_binary` asserts `count <= 10`.
   - This prevents the platform from streaming quotes for broader market universes (e.g., Nifty 50, Nifty 100, sectoral baskets).

5. **Fragile In-Place TOML Rewriting:**
   - In `SetupService._persist_config()`, account configuration changes are saved by running regex text substitutions (`re.subn`) on `config/paper.toml`. This is prone to syntax corruption, loss of comments, and race conditions.

---

## 2. Target Architecture: Modular Event-Driven Architecture (EDA)

To support sub-millisecond execution, multiple asset classes, and high-concurrency operations, the backend must transition to a decoupled, event-driven design:

```
+----------------------------------------------------------------------------------------------------+
|                               MODULAR EVENT-DRIVEN ARCHITECTURE (EDA)                              |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|   [ Zerodha Kite / Market Feed ]                      [ REST / WebSocket Client (Browser) ]        |
|                 │                                                       ▲                          |
|                 ▼                                                       │                          |
|   +───────────────────────────+                         +───────────────────────────────+          |
|   | Market Data Service (MDS) |                         |  Real-Time Gateway (FastAPI)  |          |
|   | - WebSocket connection    |                         |  - WebSocket Push (/ws/stream)|          |
|   | - Binary tick parser      |                         |  - Auth & Session Manager     |          |
|   +─────────────┬─────────────+                         +───────────────▲───────────────+          |
|                 │                                                       │                          |
|                 ▼                                                       │                          |
|   +───────────────────────────+                         +───────────────┴───────────────+          |
|   | In-Memory Tick Cache      | ──────────────────────► | Notification & Alerting Bus   |          |
|   | (Ring Buffer / LMAX-style)|                         | (WebPush, Telegram, Audio)    |          |
|   +─────────────┬─────────────+                         +───────────────▲───────────────+          |
|                 │                                                       │                          |
|                 ▼                                                       │                          |
|   +───────────────────────────+    Proposals / Orders   +───────────────┴───────────────+          |
|   | Strategy & ML Engine      | ──────────────────────► | Risk Management Engine (RMS)  |          |
|   | - 5m ORB / VWAP Rules     |                         | - Pre-trade margin validation |          |
|   | - Causal Daily Screener   |                         | - Daily drawdown guard        |          |
|   | - Real-time ML Inference  |                         | - Consecutive loss limiter    |          |
|   +───────────────────────────+                         +───────────────┬───────────────+          |
|                                                                         │ Approved Orders          |
|                                                                         ▼                          |
|                                                         +───────────────────────────────+          |
|                                                         | Order Management System (OMS) |          |
|                                                         +───────────────┬───────────────+          |
|                                                                         │                          |
|                                                   ┌─────────────────────┴─────────────────────┐    |
|                                                   ▼                                           ▼    |
|                                      +─────────────────────────+                 +─────────────────+
|                                      |   Paper Broker Adapter  |                 | Zerodha Live OMS|
|                                      |   (Simulated Matching)  |                 | (Real Execution)|
|                                      +─────────────────────────+                 +─────────────────+
|                                                   │                                           │    |
|                                                   └─────────────────────┬─────────────────────┘    |
|                                                                         ▼                          |
|                                                         +───────────────────────────────+          |
|                                                         | Persistence & Ledger (PAL)    |          |
|                                                         | - Append-only Event Journal   |          |
|                                                         | - Exact Decimal Accounting    |          |
|                                                         | - SQLite / PostgreSQL Store   |          |
|                                                         +───────────────────────────────+          |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Transitioning from Paper Trading to Live Broker Execution

### 3.1 The `BrokerGateway` Abstraction
We define a unified broker interface that cleanly decouples strategy logic and risk rules from order execution:

```python
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any
from trading_agent.models import Instrument, Order, OrderRequest, Quote


class BrokerGateway(ABC):
    """Abstract gateway implemented by PaperBroker and LiveBroker."""

    @abstractmethod
    async def get_profile(self) -> dict[str, Any]: ...

    @abstractmethod
    async def get_funds(self) -> dict[str, Decimal]: ...

    @abstractmethod
    async def get_positions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_orders(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def place_order(self, request: OrderRequest) -> str:
        """Submit an order to the execution engine. Returns broker order_id."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str, reason: str) -> bool: ...

    @abstractmethod
    async def modify_order(
        self, order_id: str, price: Decimal | None, quantity: int | None
    ) -> bool: ...
```

### 3.2 Live Order Lifecycle & State Machine
In live markets, orders transition through states that do not exist in paper trading (e.g. `TRIGGER_PENDING`, `UPDATE_PENDING`, `OPEN`, `REJECTED_BY_EXCHANGE`).

```
                    ┌─────────────────────────┐
                    │       CREATED (OMS)     │
                    └────────────┬────────────┘
                                 │ Dispatched to Broker
                                 ▼
                    ┌─────────────────────────┐
                    │      SUBMITTED (Kite)   │
                    └────────────┬────────────┘
         ┌───────────────────────┼────────────────────────┐
         │ Rejected by RMS       │ Accepted by Exchange   │ Network Timeout / Unconfirmed
         ▼                       ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  REJECTED        │    │  OPEN / PENDING  │    │ UNKNOWN (Probe)  │
│  (Margin/Limits) │    └────────┬─────────┘    └────────┬─────────┘
└──────────────────┘             │                       │
                    ┌────────────┴────────────┐          │ Reconciled
                    │ Partial Fill            │          │
                    ▼                         ▼          ▼
           ┌──────────────────┐      ┌─────────────────────────┐
           │     PARTIAL      │      │     COMPLETED (FILLED)  │
           └────────┬─────────┘      └─────────────────────────┘
                    │ Remainder Cancelled
                    ▼
           ┌──────────────────┐
           │    CANCELLED     │
           └──────────────────┘
```

#### Zerodha Live Execution Features:
1. **Postback Webhook Server (`/api/v1/broker/postback`):**  
   Zerodha Kite Connect pushes real-time order status updates via HTTP POST webhooks. The backend verifies the HMAC SHA256 checksum and immediately transitions order state in the OMS without waiting for polling.
2. **Periodic Order Book Reconciliation:**  
   A background task polls `/orders` from Kite Connect every 10 seconds to detect orders modified or cancelled directly by the operator in Zerodha's native mobile/web app.
3. **Smart Bracket / Stop-Loss Order Routing:**  
   In Indian markets, intraday bracket orders with automatic SL/Target can be routed as Zerodha **GTT (Good Till Triggered)** or synthetic server-managed stop limit orders.

---

## 4. Multi-Mode State Machine (Manual, Semi-Autonomous, Fully Autonomous)

The trading engine enforces a strict formal Finite State Machine (FSM) governing operational authority:

```
                            ┌────────────────────────┐
                            │      SYSTEM INIT       │
                            └───────────┬────────────┘
                                        │ Health checks pass
                                        ▼
                  ┌────────────────────────────────────────────┐
                  │                 MANUAL MODE                │ ◄──────────┐
                  │   - Operator initiates every trade         │            │
                  │   - Algorithm emits no orders              │            │
                  └───────────────┬────────────────────────────┘            │
                                  │                                         │
                 Operator arms    │   Operator arms                         │ Fail-Safe Demotion:
                 with approval    │   with autonomous                       │ - WebSocket disconnected
                 confirmation     │   acknowledgement                       │ - Stale quotes (>5s)
                                  │                                         │ - Drawdown breach
                                  ▼                                         │ - Consecutive loss streak
                 ┌─────────────────────────────────┐                        │ - Emergency Kill Switch
                 │      APPROVAL (SEMI-AUTO)       │                        │ - Operator manual pause
                 │   - Strategy emits proposals    │ ───────────────────────┤
                 │   - Requires operator signature │                        │
                 │   - 120s countdown window       │                        │
                 └────────────────┬────────────────┘                        │
                                  │ Operator toggles                        │
                                  │ full automation                         │
                                  ▼                                         │
                 ┌─────────────────────────────────┐                        │
                 │       FULLY AUTONOMOUS          │                        │
                 │   - Strategy signals execute    │ ───────────────────────┘
                 │   - Automated sizing & orders   │
                 │   - Full risk guards active     │
                 └─────────────────────────────────┘
```

### 4.1 Transition Safeguards
- **Zero-Latency Demotion:** If the market data connection drops for > 2 seconds, the system instantly pauses trading, disarms automation, cancels unfilled buy orders, and demotes mode to `MANUAL`.
- **Approval Signature Security:** In Semi-Autonomous mode, every proposal generates a cryptographically signed payload (`preview_sha256 = HMAC_SHA256(proposal_id + price_cap + max_qty + secret)`). When the user clicks approve, this signature is verified to ensure prices have not slipped past the allowed threshold.

---

## 5. High-Throughput Market Data & Streaming Architecture

### 5.1 Decoupling Tick Ingestion from Disk I/O (In-Memory Ring Buffer)
Instead of executing an SQLite write on every tick, incoming WebSocket ticks are written to a fixed-size lockless in-memory circular ring buffer:

```python
from collections import deque
from dataclasses import dataclass
from decimal import Decimal
import time


@dataclass(slots=True)
class FastQuote:
    symbol: str
    token: int
    last: Decimal
    bid: Decimal
    ask: Decimal
    bid_size: int
    ask_size: int
    volume: int
    timestamp_ns: int


class InMemoryTickCache:
    """Zero-allocation in-memory quote store for sub-millisecond evaluation."""

    def __init__(self, symbols: list[str], max_history: int = 1000):
        self._quotes: dict[str, FastQuote] = {}
        self._history: dict[str, deque[FastQuote]] = {s: deque(maxlen=max_history) for s in symbols}

    def update(self, quote: FastQuote) -> None:
        self._quotes[quote.symbol] = quote
        self._history[quote.symbol].append(quote)

    def get_latest(self, symbol: str) -> FastQuote | None:
        return self._quotes.get(symbol)
```

- **Async Flush Worker:** A dedicated background thread batches quotes and flushes candle aggregates to the database once every 1 second, reducing database write operations by **98%**.
- **Expanded Universe Support:** By decoupling from disk I/O, the engine can easily process streams for **100+ instruments** simultaneously (covering the entire Nifty 100).

### 5.2 Server-to-Client Real-Time WebSocket Gateway
Replaces HTTP polling with an asynchronous WebSocket server in FastAPI:

```python
# Route: /ws/stream
# Protocols: JSON-RPC or lightweight typed messages
{
    "type": "tick",
    "symbol": "NSE:RELIANCE",
    "last": "2940.50",
    "bid": "2940.20",
    "ask": "2940.50",
    "age_ms": 14,
}
{
    "type": "proposal_created",
    "id": "prop-8f92a",
    "symbol": "NSE:RELIANCE",
    "side": "BUY",
    "price_cap": "2942.00",
    "expires_in_seconds": 120,
}
{
    "type": "order_fill",
    "order_id": "ord-1029",
    "symbol": "NSE:RELIANCE",
    "filled_qty": 2,
    "fill_price": "2940.50",
}
```

---

## 6. Enterprise Risk Management System (RMS 2.0)

The Risk Engine operates as an independent gatekeeper between the Strategy Engine and Order Routing. No order can reach the broker without passing all 5 layers:

```
+───────────────────────────────────────────────────────────────────────────────────+
|                           5-LAYER RISK DEFENSE PIPELINE                           |
+───────────────────────────────────────────────────────────────────────────────────+
| 1. Account & Session Guard:  Market calendar open, entry window active, kill switch|
| 2. Market Data Guard:        Quote age < 2s, spread < 30 bps, volume regression ok|
| 3. Pre-Trade Sizing Guard:   Max trade risk (₹62.50), cash debit, slippage buffer |
| 4. Portfolio Drawdown Guard: Daily loss limit (₹250), peak equity drawdown limit  |
| 5. Broker Exposure Guard:    Zerodha margin buffer, position limit (max 2-5 open) |
+───────────────────────────────────────────────────────────────────────────────────+
```

### Dynamic Circuit Breaker & Automatic Flattener:
- **Max Loss Streak:** After 3 consecutive losing trades in a session, trading pauses automatically until the next day.
- **Intraday Flattening Clock:** At exactly 15:15 IST, all pending intraday buy orders are cancelled, and open positions are systematically closed using limit-on-close or market orders with rate-limiting.

---

## 7. Push Notifications & External Alerting

In Semi-Autonomous mode, operators cannot be expected to stare at a desktop screen for 6 consecutive market hours. An asynchronous alerting dispatcher will broadcast proposals via:
1. **HTML5 Web Push API:** Browser notifications with action buttons ("Approve", "Decline") directly from the OS notification banner.
2. **Telegram Bot Dispatcher:** Sends proposal cards with inline buttons to the operator's private Telegram chat. Tapping "Approve" sends an authenticated webhook back to the server.
3. **Local Audio Synthesizer:** Plays synthesized high/low tones in the browser tab on signal arrival and order completion.

---

## 8. Technology Stack & Database Evolution Roadmap

| Component | Current Stack | Proposed Production Upgrade | Rationale |
| :--- | :--- | :--- | :--- |
| **Language & Runtime** | Python 3.13 | Python 3.13 (AsyncIO / uvloop) | High-performance asynchronous event handling. |
| **API Framework** | FastAPI + Uvicorn | FastAPI + Uvicorn + WebSockets | Native async WebSocket pub/sub streaming. |
| **Local / Edge Database** | SQLite (WAL mode) | SQLite (WAL mode, optimized PRAGMAs) | Retained for lightweight, zero-dependency local paper trading. |
| **Production Database** | None | PostgreSQL 16 + TimescaleDB | Hypertable partitioning for millisecond candle & tick queries. |
| **In-Memory Cache** | In-process dicts | Redis 7 or In-Memory Ring Buffer | Lockless inter-process communication and pub/sub. |
| **Broker Integration** | Read-Only Kite HTTP | `BrokerGateway` (Paper + Zerodha Live) | Full order placement, modification, and postback webhooks. |
| **Telemetry & Metrics** | None | Prometheus + Grafana + OpenTelemetry | Live monitoring of tick processing latency, slip, and memory. |
