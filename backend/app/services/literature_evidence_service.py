from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RECORDS_PATH = PROJECT_ROOT / "knowledge_corpus" / "literature_evidence" / "experiment_records.json"


def list_literature_experiments(domain: str | None = None) -> dict:
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8")) if RECORDS_PATH.exists() else []
    if domain:
        records = [record for record in records if record.get("domain") == domain]
    reviewed_count = sum(record.get("review_status") == "expert_reviewed" for record in records)
    return {
        "count": len(records),
        "evidence_type": "published_literature_experiment",
        "reviewed_count": reviewed_count,
        "review_status": "expert_reviewed" if records and reviewed_count == len(records) else "partially_reviewed",
        "review_note": "实验参数由公开论文或官方报告提取，已完成人工复核；复核确认转录、来源定位和适用边界，不代表重复开展原论文试验。",
        "records": records,
    }
