import pytest

from app.core.config import settings
from app.db.database import reset_engine_cache
from app.search.es_client import reset_es_client_cache
from app.services.task_manager import task_manager


@pytest.fixture(autouse=True)
def default_mock_modes(monkeypatch):
    """Keep unit tests independent from local Docker services by default."""
    monkeypatch.setattr(settings, "data_backend", "json")
    monkeypatch.setattr(settings, "database_enabled", False)
    monkeypatch.setattr(settings, "es_enabled", False)
    monkeypatch.setattr(settings, "llm_enabled", False)
    reset_engine_cache()
    reset_es_client_cache()
    task_manager.clear()
    yield
    task_manager.clear()
    reset_engine_cache()
    reset_es_client_cache()
