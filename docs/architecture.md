# ProjectOps Layered Architecture

## 1. Architectural Layers

ProjectOps follows a strict layered architecture with dependency direction flowing inward toward the pure domain engine:

```text
[ Presentation / Client ] (React / Vite / Tailwind UI)
          │
          ▼
[ API Layer ] (/api/v1 - FastAPI, OpenAPI schemas, Pydantic validation)
          │
          ▼
[ Workflow / Engine Layer ] (Multi-agent loop: PLAN -> EXECUTE -> OBSERVE -> ...)
          │
          ▼
[ Infrastructure / Persistence ] (SQLAlchemy, Alembic, GitHub webhooks)
          │
          ▼
[ PURE DOMAIN ENGINE ] (backend/app/domain - Zero I/O, pure Python)
```

## 2. Inversion of Control & Zero I/O in Domain

The core domain (`backend/app/domain`) is isolated from all side-effects:
- **No Database Imports**: No SQLAlchemy, no SQL queries, no ORM references.
- **No Network / HTTP Imports**: No `fastapi`, `httpx`, `requests`, or sockets.
- **No LLM SDKs**: No `anthropic`, `openai`, or AI dependencies.
- **Injectable Clock**: All temporal operations take an injectable `Clock` protocol (`SystemClock` or `FixedClock`).

This guarantees:
1. **Strict Determinism**: Running scheduling, graph validation, or impact analysis on identical inputs yields bit-for-bit identical results on every platform.
2. **Infinite Simulation Speed**: Thousand-iteration what-if simulations run in milliseconds in memory with zero database transaction overhead.
3. **Property-Based Testability**: Hypothesis can generate thousands of synthetic DAGs and calendars without mocking or database cleanup.
