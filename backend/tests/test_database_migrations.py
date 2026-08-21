from sqlalchemy import create_engine, inspect, text

from app.db.migrate import upgrade_database
from app.db.models import Base


def _sqlite_url(path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_empty_database_upgrades_to_alembic_head(tmp_path):
    database_path = tmp_path / "empty.db"
    url = _sqlite_url(database_path)

    result = upgrade_database(url)
    engine = create_engine(url)

    assert result["bootstrapped_existing_schema"] is False
    assert result["revision"] == "20260812_0002"
    assert result["async_tasks_ready"] is True
    assert "async_tasks" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "20260812_0002"


def test_existing_create_all_schema_is_bootstrapped_without_data_loss(tmp_path):
    database_path = tmp_path / "legacy.db"
    url = _sqlite_url(database_path)
    engine = create_engine(url)
    legacy_tables = [table for table in Base.metadata.sorted_tables if table.name != "async_tasks"]
    Base.metadata.create_all(engine, tables=legacy_tables)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO learners "
                "(profile_id, name, profile_type, background, characteristics, learning_goal, level, recommended_domains, created_at) "
                "VALUES ('legacy', 'Legacy', 'student', 'materials', '', 'training', 'low', '[]', CURRENT_TIMESTAMP)"
            )
        )

    result = upgrade_database(url)

    assert result["bootstrapped_existing_schema"] is True
    assert result["async_tasks_ready"] is True
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM learners")).scalar() == 1
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "20260812_0002"
