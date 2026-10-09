"""Database migration runner using Alembic."""

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


def run_migrations(target_revision: str = "head") -> None:
    """Run Alembic database migrations up to the target revision."""
    repo_root = Path(__file__).resolve().parent.parent
    ini_path = repo_root / "alembic.ini"

    if not ini_path.exists():
        ini_path = repo_root / "backend" / "alembic.ini"

    print(f"Applying database migrations using config: {ini_path}")
    cfg = Config(str(ini_path))

    # Apply database URL from environment or settings if provided
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        command.upgrade(cfg, target_revision)
        print(f"Successfully migrated database schema to '{target_revision}'.")
    except Exception as exc:
        print(f"Migration error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    rev = sys.argv[1] if len(sys.argv) > 1 else "head"
    run_migrations(rev)
