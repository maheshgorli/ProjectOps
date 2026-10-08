# ADR 0001: Domain Engine is Pure and I/O-Free

## Status
Accepted

## Context
ProjectOps is an autonomous project execution and risk management system. Core operations include:
- Graph cycle checks and topological ordering
- Critical path method (CPM) forward and backward scheduling passes
- Multi-factor assignment scoring
- Workload and utilization calculations
- What-if delay impact simulation

If the domain engine were coupled to external frameworks (such as database ORMs, HTTP clients, or LLM SDKs), running what-if replan simulations would require database transactions, mocking, or network calls. Furthermore, non-deterministic behaviors (like unmocked system clocks) make verification fragile.

## Decision
We enforce that `backend/app/domain` is written in **pure Python** with **zero I/O imports**:
1. No database frameworks (e.g., SQLAlchemy, psycopg).
2. No HTTP/API frameworks (e.g., FastAPI, httpx, requests).
3. No AI/LLM SDKs (e.g., Anthropic, OpenAI).
4. Time operations require an injectable `Clock` protocol (`SystemClock` or `FixedClock`).

## Consequences
- **Positive**:
  - Deterministic simulations can run thousands of candidate schedules in milliseconds in memory.
  - Test suites run in seconds without spinning up databases.
  - Property-based testing with Hypothesis can generate and test thousands of arbitrary valid and invalid graphs.
  - The domain engine can be reused across CLI, API, workers, or edge environments without alteration.
- **Negative / Trade-offs**:
  - Requires explicit mapper functions between database ORM models and pure domain dataclasses/models in the repository layer.
