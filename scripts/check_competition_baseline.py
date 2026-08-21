from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "competition_baseline.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_equal(errors: list[str], label: str, actual, expected) -> None:
    if actual != expected:
        errors.append(f"{label}: expected {expected!r}, got {actual!r}")


def main() -> int:
    baseline = read_json(BASELINE_PATH)
    errors: list[str] = []

    manifest = read_json(ROOT / "knowledge_corpus" / "index_manifest.json")
    registry = read_json(ROOT / "knowledge_corpus" / "source_registry.json")
    catalog = read_json(ROOT / "knowledge_corpus" / "experimental_assets" / "catalog.json")
    eval_cases = read_json(ROOT / "evaluation" / "eval_cases.json")
    full = read_json(ROOT / "evaluation" / "full_case_execution_results.json")
    inquiry = read_json(ROOT / "evaluation" / "guided_inquiry_results.json")
    qwen = read_json(ROOT / "evaluation" / "qwen_quality_results.json")

    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    collected_output = f"{collected.stdout}\n{collected.stderr}"
    collected_match = re.search(r"(\d+) tests? collected", collected_output)
    if collected.returncode != 0 or not collected_match:
        errors.append("unable to collect backend pytest count")
    else:
        check_equal(
            errors,
            "backend_tests_collected",
            int(collected_match.group(1)),
            baseline["engineering"]["backend_tests_passed"],
        )

    knowledge = baseline["knowledge"]
    evaluation = baseline["evaluation"]
    check_equal(errors, "indexed_chunks", manifest["total_chunks"], knowledge["indexed_chunks"])
    check_equal(errors, "registered_sources", len(registry["sources"]), knowledge["registered_sources"])
    check_equal(errors, "experimental_topics", len(catalog["topics"]), knowledge["experimental_topics"])
    check_equal(errors, "experimental_assets", len(catalog["assets"]), knowledge["experimental_assets"])
    check_equal(errors, "eval_case_count", len(eval_cases), evaluation["core_cases"])
    check_equal(errors, "core_cases_passed", full["metrics"]["passed_cases"], evaluation["core_cases_passed"])
    check_equal(errors, "guided_inquiry_cases", inquiry["metrics"]["case_count"], evaluation["guided_inquiry_cases"])
    check_equal(errors, "guided_inquiry_passed", inquiry["metrics"]["passed_cases"], evaluation["guided_inquiry_cases_passed"])
    check_equal(errors, "qwen_cases", qwen["metrics"]["case_count"], evaluation["qwen_representative_cases"])
    check_equal(errors, "qwen_machine_passed", qwen["metrics"]["machine_passed_cases"], evaluation["qwen_machine_checks_passed"])

    authoritative_docs = [
        ROOT / "README.md",
        ROOT / "FINAL_RELEASE.md",
        ROOT / "SYSTEM_DESIGN.md",
        ROOT / "PPT_OUTLINE.md",
        ROOT / "DEMO_SCRIPT.md",
        ROOT / "SCREENSHOT_GUIDE.md",
        ROOT / "docs" / "答辩PPT文案.md",
        ROOT / "docs" / "演示视频讲稿.md",
    ]
    stale_tokens = ("56 passed", "74 passed", "107 passed", "108 passed", "110 passed")
    for path in authoritative_docs:
        if not path.exists():
            errors.append(f"missing authoritative document: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for token in stale_tokens:
            if token in text:
                errors.append(f"stale metric {token!r} in {path.relative_to(ROOT)}")

    if errors:
        print("Competition baseline check FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Competition baseline check PASSED")
    print(f"- backend tests: {baseline['engineering']['backend_tests_passed']} passed")
    print(f"- ES chunks: {knowledge['indexed_chunks']}")
    print(f"- core cases: {evaluation['core_cases_passed']}/{evaluation['core_cases']}")
    print(f"- Qwen machine checks: {evaluation['qwen_machine_checks_passed']}/{evaluation['qwen_representative_cases']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
