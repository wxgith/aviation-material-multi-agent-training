from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings


BACKEND_DIR = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "20260812_0001"
EXPECTED_BASELINE_TABLES = {
    "learners",
    "diagnosis_records",
    "agent_sessions",
    "agent_steps",
    "generated_resources",
    "learning_reports",
    "feedback_records",
    "learning_interactions",
}


def alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
        config.attributes["database_url_override"] = database_url
    return config


def upgrade_database(database_url: str | None = None) -> dict:
    url = database_url or settings.database_url
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    config = alembic_config(url)
    bootstrapped = False
    if tables and "alembic_version" not in tables:
        missing = EXPECTED_BASELINE_TABLES - tables
        if missing:
            raise RuntimeError(
                "Existing database is not a recognized project schema; missing tables: "
                + ", ".join(sorted(missing))
            )
        command.stamp(config, BASELINE_REVISION)
        bootstrapped = True
    command.upgrade(config, "head")
    final_tables = set(inspect(engine).get_table_names())
    return {
        "database_url": _redact_url(url),
        "bootstrapped_existing_schema": bootstrapped,
        "revision": "20260812_0002",
        "async_tasks_ready": "async_tasks" in final_tables,
        "table_count": len(final_tables - {"alembic_version"}),
    }


def _redact_url(url: str) -> str:
    if "@" not in url or "://" not in url:
        return url
    prefix, suffix = url.split("@", 1)
    scheme, credentials = prefix.split("://", 1)
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upgrade the project SQL schema with Alembic.")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    result = upgrade_database(args.database_url)
    for key, value in result.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
