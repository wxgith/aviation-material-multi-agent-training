from app.core.config import settings
from app.search.es_client import es_connected, get_es_client
from app.services.data_loader import load_knowledge_base


def ensure_index() -> None:
    client = get_es_client()
    index = settings.es_index_knowledge
    if client.indices.exists(index=index):
        return
    client.indices.create(
        index=index,
        mappings={
            "properties": {
                "id": {"type": "keyword"},
                "domain": {"type": "keyword"},
                "title": {"type": "text"},
                "tags": {"type": "keyword"},
                "difficulty": {"type": "keyword"},
                "content": {"type": "text"},
                "source_type": {"type": "keyword"},
                "source_id": {"type": "keyword"},
                "source_locator": {"type": "keyword"},
                "source_url": {"type": "keyword", "index": False},
                "source_authority": {"type": "keyword"},
                "applicable_learners": {"type": "keyword"},
                "common_misconceptions": {"type": "text"},
            }
        },
    )


def index_knowledge() -> int:
    ensure_index()
    client = get_es_client()
    index = settings.es_index_knowledge
    count = 0
    for knowledge in load_knowledge_base().values():
        for chunk in knowledge.get("chunks", []):
            client.index(index=index, id=chunk["id"], document=chunk)
            count += 1
    client.indices.refresh(index=index)
    return count


def main() -> None:
    if not settings.es_enabled:
        print("elasticsearch disabled; set ES_ENABLED=true before indexing.")
        return
    if not es_connected():
        print(f"elasticsearch unavailable at {settings.es_url}; check ES_URL/ES_USERNAME/ES_PASSWORD.")
        return
    count = index_knowledge()
    print(f"indexed knowledge chunks={count} into {settings.es_index_knowledge}")


if __name__ == "__main__":
    main()
