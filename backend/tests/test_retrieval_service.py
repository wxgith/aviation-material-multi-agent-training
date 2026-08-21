from app.services.data_loader import get_profile
from app.services.retrieval_service import retrieve_knowledge


def test_retrieval_prioritizes_weak_points_and_goal():
    profile = get_profile("undergrad_basic")
    chunks = retrieve_knowledge(
        domain="tire",
        weak_points=["热氧老化", "滑动磨损"],
        learning_goal=profile["default_goal"],
        learner_type=profile["learner_type"],
        top_k=3,
    )

    assert len(chunks) == 3
    evidence_ids = {chunk["id"] for chunk in chunks}
    assert {"tire-k01", "tire-k02"} & evidence_ids
    assert all(chunk["domain"] == "tire" for chunk in chunks)


def test_retrieval_prioritizes_composite_ndt_methods():
    chunks = retrieve_knowledge(
        domain="composite",
        weak_points=["综合迁移应用"],
        learning_goal="用无损检测区分分层、基体开裂和纤维断裂",
        learner_type="材料方向研究生",
        top_k=3,
    )

    assert "composite-k03" in {chunk["id"] for chunk in chunks}
