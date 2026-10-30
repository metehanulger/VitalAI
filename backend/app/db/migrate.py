"""Run Alembic migrations from application code (used on startup and in tests)."""

from pathlib import Path

from alembic import command
from alembic.config import Config

_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def upgrade_to_head() -> None:
    """Bring the PostgreSQL schema up to the latest migration."""
    config = Config(str(_ALEMBIC_INI))
    config.attributes["skip_logging_config"] = True
    command.upgrade(config, "head")
