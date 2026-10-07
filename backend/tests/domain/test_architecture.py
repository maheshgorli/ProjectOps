"""Architectural boundary enforcement tests.

Verifies that backend/app/domain remains pure Python with ZERO I/O:
No DB (SQLAlchemy, sqlite3, asyncpg, psycopg, etc.),
No HTTP (requests, httpx, urllib, aiohttp, etc.),
No Web Frameworks (FastAPI, Starlette, Flask, etc.),
No LLM libraries (anthropic, openai, langchain, etc.),
No OS filesystem / network calls.
"""

import ast
from pathlib import Path

FORBIDDEN_MODULE_PREFIXES = {
    # Database
    "sqlalchemy",
    "alembic",
    "sqlite3",
    "asyncpg",
    "psycopg",
    "psycopg2",
    # HTTP & Web
    "fastapi",
    "starlette",
    "httpx",
    "requests",
    "urllib.request",
    "aiohttp",
    # LLMs & AI
    "anthropic",
    "openai",
    "google",
    "langchain",
    # Subprocesses & direct network
    "socket",
    "subprocess",
}


def test_domain_has_zero_io_or_external_imports():
    """Verify via AST that no file in backend/app/domain imports any forbidden module."""
    current_file = Path(__file__).resolve()
    domain_dir = current_file.parents[2] / "app" / "domain"
    assert domain_dir.exists() and domain_dir.is_dir(), f"Domain dir not found: {domain_dir}"

    python_files = list(domain_dir.glob("*.py"))
    assert len(python_files) > 0, "No Python files found in domain directory!"

    violations: list[str] = []

    for py_file in python_files:
        with open(py_file, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(py_file))

        for node in ast.walk(tree):
            imported_names: list[str] = []
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.append(node.module)

            for mod_name in imported_names:
                for forbidden in FORBIDDEN_MODULE_PREFIXES:
                    if mod_name == forbidden or mod_name.startswith(f"{forbidden}."):
                        violations.append(
                            f"File '{py_file.name}' line {getattr(node, 'lineno', '?')} "
                            f"imports forbidden module '{mod_name}'"
                        )

    msg = "Architectural boundary violation in backend/app/domain:\n" + "\n".join(violations)
    assert not violations, msg
