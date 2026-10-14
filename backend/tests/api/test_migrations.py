"""Tests for Alembic database migrations: upgrade to head, downgrade, and re-upgrade cycle."""

from pathlib import Path

from alembic.config import Config

from alembic import command


def test_alembic_upgrade_downgrade_cycle(tmp_path: Path, monkeypatch):
    """
    Verify:
    1. upgrade head on empty SQLite succeeds.
    2. downgrade -1 succeeds.
    3. upgrade head again succeeds.
    """
    db_file = tmp_path / "fresh_migration_test.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    # Use project root alembic.ini
    root_ini = Path(__file__).resolve().parents[3] / "alembic.ini"
    assert root_ini.exists(), f"Expected alembic.ini at {root_ini}"

    alembic_cfg = Config(str(root_ini))

    # 1. Upgrade from empty to head
    command.upgrade(alembic_cfg, "head")
    assert db_file.exists()

    # 2. Downgrade by 1 revision
    command.downgrade(alembic_cfg, "-1")

    # 3. Re-upgrade to head
    command.upgrade(alembic_cfg, "head")
