from app.evaluation.knowledge_coverage_runner import analyze_coverage


def test_knowledge_coverage_contains_all_three_domains():
    result = analyze_coverage()

    assert result["total_chunks"] >= 1700
    assert set(result["domains"]) == {"tire", "brake", "composite"}
    assert all(len(item["categories"]) == 8 for item in result["domains"].values())


def test_coverage_report_exposes_team_experiment_gap():
    result = analyze_coverage()

    assert result["domains"]["tire"]["team_experiment_source_count"] > 0
    assert result["domains"]["brake"]["team_experiment_source_count"] == 0
    assert result["domains"]["composite"]["team_experiment_source_count"] == 0
    assert any("授权实验" in item for item in result["domains"]["brake"]["priorities"])
