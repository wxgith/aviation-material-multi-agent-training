from functools import lru_cache

from elasticsearch import Elasticsearch

from app.core.config import settings


@lru_cache
def get_es_client() -> Elasticsearch:
    kwargs = {}
    if settings.es_username:
        kwargs["basic_auth"] = (settings.es_username, settings.es_password or "")
    return Elasticsearch(
        settings.es_url,
        request_timeout=3,
        max_retries=0,
        retry_on_timeout=False,
        **kwargs,
    )


def es_connected() -> bool:
    if not settings.es_enabled:
        return False
    try:
        return bool(get_es_client().ping())
    except Exception:
        return False


def reset_es_client_cache() -> None:
    get_es_client.cache_clear()
