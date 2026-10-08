"""Strict architectural test enforcing pure Python and ZERO I/O in the domain engine."""

import ast
from pathlib import Path

FORBIDDEN_MODULES = {
    "fastapi",
    "sqlalchemy",
    "httpx",
    "requests",
    "aiohttp",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "aiosqlite",
    "sqlite3",
    "openai",
    "anthropic",
    "socket",
    "http",
}


def test_domain_has_zero_io_or_external_imports():
    """Scan all Python files in backend/app/domain using AST.

    Assert that no forbidden I/O, database, network, or AI packages are imported.
    """
    domain_dir = Path(__file__).resolve().parents[4] / "backend" / "app" / "domain"
    assert domain_dir.exists(), f"Domain directory not found at {domain_dir}"

    domain_files = list(domain_dir.rglob("*.py"))
    assert len(domain_files) > 0, "No domain files found to inspect"

    violations: list[str] = []

    for file_path in domain_files:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in FORBIDDEN_MODULES:
                        violations.append(
                            f"{file_path.name}:{node.lineno} imports forbidden module '{root_pkg}'"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_pkg = node.module.split(".")[0]
                if root_pkg in FORBIDDEN_MODULES:
                    violations.append(
                        f"{file_path.name}:{node.lineno} imports from forbidden '{root_pkg}'"
                    )

    assert not violations, (
        "Domain engine purity violated! Found forbidden I/O imports:\n" + "\n".join(violations)
    )
