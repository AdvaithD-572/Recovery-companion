from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text


def _upgrade(connection):
    backend = Path(__file__).resolve().parents[2]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic").replace("%", "%%"))
    cfg.attributes["connection"] = connection
    if connection.dialect.name == "postgresql":
        connection.execute(text("select pg_advisory_xact_lock(725953011)"))
    command.upgrade(cfg, "head")


async def migrate(engine):
    async with engine.begin() as connection:
        await connection.run_sync(_upgrade)
