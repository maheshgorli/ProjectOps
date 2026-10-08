# ProjectOps Coding Standards

## 1. Python Standards
- **Python Version**: Python 3.12+ (strictly typed using Python 3.12 syntax, e.g., `list[str]`, `str | None`).
- **Formatting & Linting**: Ruff format and ruff check with a max line length of 100 characters.
- **Typing**: Strict type annotations on all function signatures, dataclasses, and domain models. Avoid `Any`.

## 2. Domain Purity Rules
- Under `backend/app/domain`:
  - Never import external I/O libraries (`fastapi`, `sqlalchemy`, `httpx`, `requests`, `openai`, `anthropic`, etc.).
  - Never instantiate system time directly (`datetime.now()`); always use an injected `Clock` instance.
  - No side effects: domain functions must be pure transformations or return immutable data.

## 3. Testing Requirements
- **Framework**: `pytest`, `pytest-asyncio`, and `Hypothesis`.
- **Unit Testing**: Every module must have comprehensive unit tests for standard and edge cases.
- **Property-Based Testing**: Use Hypothesis for invariants (e.g., topological order, schedule monotonicity, working-day boundary enforcement).
- **Architectural Testing**: Automated AST inspection tests that enforce zero external dependencies in the domain engine.
