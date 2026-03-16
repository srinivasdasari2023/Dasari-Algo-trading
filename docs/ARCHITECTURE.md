# Architecture: CapitalGuard Algo Trader

**C4 + Event Model | Event-Driven | Risk-First**

---

## 1. Context Diagram (C4 Level 1)

```mermaid
C4Context
    title System Context - CapitalGuard Algo Trader

    Person(trader, "Risk-Conscious Trader", "Uses signals and execution modes")
    Person(admin, "System Admin", "Manages risk, schedules, audit")

    System(capitalguard, "CapitalGuard Algo Trader", "Capital-preserving index options algo trading")

    System_Ext(upstox, "Upstox", "Broker: OAuth, market data, orders")

    Rel(trader, capitalguard, "Uses")
    Rel(admin, capitalguard, "Manages")
    Rel(capitalguard, upstox, "Market data, orders, OAuth")
```

---

## 2. Container Diagram (C4 Level 2)

```mermaid
C4Container
    title Container Diagram

    Person(trader, "Trader / Admin")

    Container_Boundary(platform, "CapitalGuard Platform") {
        Container(web, "Web App", "React (Next.js)", "Dashboard, signals, positions")
        Container(mobile, "Mobile App", "React Native", "Same views as web")
        Container(api, "Backend API", "Python FastAPI", "REST + WebSocket")
        Container(market_svc, "Market Service", "Python", "Candles, EMAs, CPR")
        Container(signal_svc, "Signal Service", "Python", "Bias, pattern, entry logic")
        Container(risk_svc, "Risk Service", "Python", "Limits, daily loss, square-off")
        Container(order_svc, "Order Service", "Python", "Upstox orders, idempotency")
    }

    ContainerDb(postgres, "PostgreSQL", "Trades, signals, audits, users")
    ContainerDb(redis, "Redis", "Live state, locks, session")
    System_Ext(upstox, "Upstox API")

    Rel(trader, web, "Uses")
    Rel(trader, mobile, "Uses")
    Rel(web, api, "REST/WS")
    Rel(mobile, api, "REST/WS")
    Rel(api, market_svc, "Commands/Queries")
    Rel(api, signal_svc, "Commands/Queries")
    Rel(api, risk_svc, "Commands/Queries")
    Rel(api, order_svc, "Commands/Queries")
    Rel(market_svc, postgres, "Read/Write")
    Rel(market_svc, redis, "Cache/State")
    Rel(signal_svc, redis, "State")
    Rel(risk_svc, postgres, "Read/Write")
    Rel(risk_svc, redis, "Locks/State")
    Rel(order_svc, postgres, "Read/Write")
    Rel(order_svc, redis, "Idempotency keys")
    Rel(order_svc, upstox, "HTTPS")
```

---

## 3. Component Diagram – Backend (Signal & Risk Flow)

```mermaid
C4Component
    title Signal & Risk Flow (simplified)

    Container_Boundary(api, "Backend API") {
        Component(api_gw, "API Gateway", "FastAPI", "REST + WebSocket routes")
        Component(cmd_handler, "Command Handler", "Python", "Orchestrates commands")
        Component(evt_bus, "Event Bus", "In-process / Redis Streams", "Commands vs Events")
    }

    Container_Boundary(market_svc, "Market Service") {
        Component(candle_store, "Candle Store", "Python", "Fetch & persist candles")
        Component(ema_calc, "EMA Calculator", "Python", "15/5/2 min EMAs")
        Component(cpr_calc, "CPR Calculator", "Python", "CPR levels")
    }

    Container_Boundary(signal_svc, "Signal Service") {
        Component(bias_check, "Bias Check", "Python", "EMA20 vs EMA200")
        Component(engulf_detect, "Engulfing Detector", "Python", "Bull/Bear engulfing only")
        Component(entry_seq, "Entry Sequence", "Python", "Pullback + close above/below")
        Component(opt_filter, "Option Filter", "Python", "Premium, ATM, spread, volume")
    }

    Container_Boundary(risk_svc, "Risk Service") {
        Component(daily_limits, "Daily Limits", "Python", "Max 3 trades, 1-loss stop")
        Component(time_filter, "Time Filter", "Python", "09:20-14:45 IST")
        Component(square_off, "Square-Off", "Python", "15:15 auto close")
    }

    Rel(api_gw, cmd_handler, "Command")
    Rel(cmd_handler, evt_bus, "Publish event")
    Rel(evt_bus, candle_store, "On market update")
    Rel(candle_store, ema_calc, "Candles")
    Rel(candle_store, cpr_calc, "OHLC")
    Rel(ema_calc, bias_check, "EMAs")
    Rel(cpr_calc, bias_check, "CPR")
    Rel(bias_check, engulf_detect, "Bias")
    Rel(engulf_detect, entry_seq, "Pattern")
    Rel(entry_seq, opt_filter, "Entry")
    Rel(opt_filter, daily_limits, "Candidate signal")
    Rel(daily_limits, time_filter, "Allowed")
    Rel(time_filter, square_off, "Position lifecycle")
```

---

## 4. Event Model

### 4.1 Command vs Event Separation

- **Commands**: intent (e.g. `EvaluateSignal`, `PlaceOrder`, `SwitchTradingMode`). Request–response where applicable.
- **Events**: facts that have happened (e.g. `CandleClosed`, `SignalGenerated`, `OrderPlaced`). Consumed by downstream services.

### 4.2 Core Event Schemas (canonical)

```yaml
# CandleClosed
CandleClosed:
  event_id: uuid
  timestamp: iso8601
  source: "market-service"
  payload:
    symbol: string  # NIFTY | SENSEX
    interval: string  # 15min | 5min | 2min
    open: float
    high: float
    low: float
    close: float
    volume: int
    candle_time: iso8601

# SignalGenerated
SignalGenerated:
  event_id: uuid
  timestamp: iso8601
  source: "signal-service"
  payload:
    signal_id: uuid
    symbol: string
    direction: "BUY" | "SELL"
    reason: string
    bias: string
    time_window_ok: bool
    risk_checklist: object  # pass/fail per rule
    option_instrument_key: string | null
    rejected_reason: string | null  # if rejected by risk

# RiskChecked
RiskChecked:
  event_id: uuid
  timestamp: iso8601
  source: "risk-service"
  payload:
    signal_id: uuid
    allowed: bool
    reason: string  # e.g. "daily_loss_stop" | "max_trades" | "time_window"
    daily_trade_count: int
    daily_loss_count: int

# OrderPlaced
OrderPlaced:
  event_id: uuid
  timestamp: iso8601
  source: "order-service"
  payload:
    order_id: uuid
    broker_order_id: string
    signal_id: uuid
    idempotency_key: string
    side: "BUY" | "SELL"
    instrument_key: string
    quantity: int
    order_type: string
    status: string

# TradingModeChanged
TradingModeChanged:
  event_id: uuid
  timestamp: iso8601
  source: "api"
  payload:
    user_id: uuid
    from_mode: "MANUAL" | "SEMI_AUTO" | "FULL_AUTO"
    to_mode: string
    consent_given: bool
    ip_address: string
```

### 4.3 Event Flow (High Level)

```mermaid
sequenceDiagram
    participant Upstox
    participant Market as Market Service
    participant Signal as Signal Service
    participant Risk as Risk Service
    participant Order as Order Service
    participant Redis
    participant Postgres

    Upstox->>Market: Candle data
    Market->>Market: CandleClosed (internal/Redis)
    Market->>Signal: Evaluate (on 2min close)
    Signal->>Signal: Bias, pattern, entry sequence
    Signal->>Risk: RiskChecked (daily limits, time)
    Risk->>Redis: State update
    alt Allowed
        Risk->>Order: PlaceOrder command
        Order->>Upstox: Place order
        Order->>Postgres: OrderPlaced event stored
    else Rejected
        Risk->>Postgres: SignalRejected audit
    end
```

---

## 5. Service Responsibilities

| Service | Responsibility | Stores |
|---------|----------------|--------|
| **Market** | Fetch/store candles; compute 15/5/2 min EMAs and CPR; publish CandleClosed | Postgres (candles), Redis (latest EMAs/CPR) |
| **Signal** | Bias (EMA20 vs EMA200), time window, CPR filter, engulfing detection, entry sequence, option filter | Redis (last signal state) |
| **Risk** | Daily trade count, daily loss stop, time filter, square-off at 15:15, position limits | Postgres (trades), Redis (counters, locks) |
| **Order** | Upstox order API; idempotency; map signal → order; persist OrderPlaced | Postgres (orders), Redis (idempotency keys) |
| **API** | Auth, RBAC, WebSocket for live updates, mode switch with consent, audit log write | Postgres (audit), Redis (session) |

---

## 6. Idempotency & Replay

- **Order placement**: Every place-order command carries an `idempotency_key` (e.g. `signal_id` or `signal_id + intent`). Order service checks Redis/DB before calling Upstox; duplicate key → return existing order result.
- **Signal evaluation**: Keyed by `(symbol, interval, candle_time)`. Re-evaluation for same candle returns cached result from Redis to avoid duplicate signals.
- **Replay**: Events stored in Postgres (audit/signal/order tables). Replay for debugging or recovery is read-only; no duplicate orders due to idempotency keys.

---

## 7. Observability Strategy

- **Logging**: Structured JSON logs; correlation_id per request/flow; log level by environment.
- **Metrics**: Counters for signals generated/rejected, orders placed/failed, daily trades; gauges for open positions; latency histograms for strategy eval and order API.
- **Tracing**: Optional distributed trace (e.g. OpenTelemetry) from API → market → signal → risk → order.
- **Alerting**: Broker API failures, repeated order failures, daily loss stop triggered, square-off failures; on-call runbook for each.

---

*Document owner: Enterprise Solution Architect. Review: per major release.*
