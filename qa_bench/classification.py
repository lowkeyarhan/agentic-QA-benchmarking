from __future__ import annotations

import re
from collections import Counter

from .definitions import QA_BENCH_CAPABILITIES, QA_BENCH_METRICS, QA_BENCH_VERSION


DIFFICULTY_WEIGHTS = {
    "low": 1.0,
    "medium": 1.15,
    "high": 1.3,
    "ultra": 1.5,
    "max": 1.75,
}
VALID_DIFFICULTIES = {*DIFFICULTY_WEIGHTS, "unknown"}


def eval_metadata(fixture) -> dict:
    explicit = explicit_qa_bench_metadata(fixture)
    capability = str(explicit.get("capability") or capability_for_fixture(fixture))
    validate_capability(capability, fixture)
    metric_ids = explicit_metric_ids(explicit, fixture) or metric_ids_for_fixture(
        fixture, capability
    )
    tier = getattr(fixture, "tier", None)
    difficulty = str(explicit.get("difficulty") or difficulty_for_tier(tier))
    validate_difficulty(difficulty, fixture)
    return {
        "version": QA_BENCH_VERSION,
        "evalId": getattr(fixture, "eval_id", None),
        "mode": getattr(fixture, "mode", None),
        "difficulty": difficulty,
        "tier": tier,
        "capability": capability,
        "capabilityLabel": QA_BENCH_CAPABILITIES[capability]["label"],
        "metricIds": metric_ids,
        "metrics": [
            {
                "id": metric_id,
                "label": QA_BENCH_METRICS[metric_id]["label"],
                "description": QA_BENCH_METRICS[metric_id]["description"],
            }
            for metric_id in metric_ids
        ],
        "weight": eval_weight_for_fixture(fixture),
        "metadataSource": "fixture" if explicit else "inferred",
    }


def catalog_for_fixtures(fixtures: list) -> dict:
    evals = {fixture.eval_id: eval_metadata(fixture) for fixture in fixtures}
    capability_counts = Counter(item["capability"] for item in evals.values())
    metric_counts: Counter[str] = Counter()
    difficulty_counts = Counter(item["difficulty"] for item in evals.values())
    mode_counts = Counter(item["mode"] for item in evals.values())
    for item in evals.values():
        metric_counts.update(item["metricIds"])
    return {
        "version": QA_BENCH_VERSION,
        "evals": evals,
        "capabilityDefinitions": QA_BENCH_CAPABILITIES,
        "metricDefinitions": QA_BENCH_METRICS,
        "coverage": {
            "capabilities": dict(sorted(capability_counts.items())),
            "metrics": dict(sorted(metric_counts.items())),
            "difficulties": dict(sorted(difficulty_counts.items())),
            "modes": dict(sorted(mode_counts.items())),
        },
    }


def capability_for_fixture(fixture) -> str:
    mode = str(getattr(fixture, "mode", "") or "").lower()
    text = fixture_search_text(fixture)

    if mode == "test-feature":
        return "feature-validation"
    if mode == "plan":
        return "risk-planning"
    if mode == "report":
        return "reporting-and-evidence"
    if contains_any(text, ["maestro", "appium", "wdio", "android", "ios", "mobile"]):
        return "mobile-qa"
    if contains_any(
        text,
        [
            "root cause",
            "classify",
            "failure category",
            "bug rather than",
            "application bug",
        ],
    ):
        return "root-cause-debugging"
    if contains_any(
        text,
        [
            "@manual",
            "manual test",
            "stable id",
            "owner",
            "priority",
            "metadata",
            "flaky",
        ],
    ):
        return "metadata-governance"
    if contains_any(
        text,
        [
            "supatest.md",
            "project convention",
            "page object",
            "selector strategy",
            "discover",
        ],
    ):
        return "project-discovery"
    if contains_any(
        text, ["browser", "screenshot", "video", "trace", "visual evidence"]
    ):
        return "browser-context"
    if mode == "fix":
        return "test-repair"
    return "test-authoring"


def metric_ids_for_fixture(fixture, capability: str) -> list[str]:
    mode = str(getattr(fixture, "mode", "") or "").lower()
    text = fixture_search_text(fixture)
    metrics = ["relevance", "coverage"]

    if mode in {"build", "fix"}:
        metrics.extend(["assertion_quality", "test_integrity", "maintainability"])
    if mode == "fix":
        metrics.extend(["root_cause_accuracy", "state_timing_reliability"])
    if mode in {"plan", "report", "test-feature"}:
        metrics.append("reporting_quality")
    if capability in {
        "browser-context",
        "feature-validation",
        "reporting-and-evidence",
    }:
        metrics.append("evidence_quality")
    if capability in {"project-discovery", "test-repair", "test-authoring"}:
        metrics.append("selector_strategy")
    if capability == "metadata-governance":
        metrics.extend(["metadata_quality", "manual_workflow"])
    if capability == "mobile-qa":
        metrics.extend(["framework_adaptation", "mobile_context", "evidence_quality"])
    if contains_any(text, ["ci", "stdout", "stderr", "log", "reporter"]):
        metrics.append("ci_log_analysis")
    if contains_any(text, ["waitfortimeout", "timeout", "race", "flaky", "retry"]):
        metrics.append("state_timing_reliability")
    if contains_any(text, ["@manual", "manual"]):
        metrics.append("manual_workflow")
    if contains_any(
        text, ["tag", "metadata", "stable id", "owner", "priority", "flaky"]
    ):
        metrics.append("metadata_quality")

    return sorted(dict.fromkeys(metrics))


def difficulty_for_tier(tier: int | None) -> str:
    if tier is None:
        return "unknown"
    if tier <= 2:
        return "low"
    if tier <= 4:
        return "medium"
    if tier <= 6:
        return "high"
    if tier <= 9:
        return "ultra"
    return "max"


def eval_weight_for_fixture(fixture) -> float:
    explicit = explicit_qa_bench_metadata(fixture)
    if explicit.get("weight") is not None:
        return float(explicit["weight"])
    difficulty = str(
        explicit.get("difficulty")
        or difficulty_for_tier(getattr(fixture, "tier", None))
    )
    return DIFFICULTY_WEIGHTS.get(difficulty, 1.0)


def fixture_search_text(fixture) -> str:
    parts = [
        str(getattr(fixture, "name", "") or ""),
        str(getattr(fixture, "mode", "") or ""),
        str(getattr(fixture, "task", "") or ""),
        "\n".join(getattr(fixture, "pass_criteria", []) or []),
        "\n".join(getattr(fixture, "fail_criteria", []) or []),
    ]
    return re.sub(r"\s+", " ", "\n".join(parts).lower())


def contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def explicit_qa_bench_metadata(fixture) -> dict:
    raw = getattr(fixture, "qa_bench", None) or {}
    if not isinstance(raw, dict):
        raise ValueError(
            f"Fixture {getattr(fixture, 'eval_id', '<unknown>')} qaBench metadata "
            "must be an object."
        )
    return raw


def explicit_metric_ids(explicit: dict, fixture) -> list[str] | None:
    raw = explicit.get("metricIds")
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(
            f"Fixture {getattr(fixture, 'eval_id', '<unknown>')} qaBench.metricIds "
            "must be a list of metric id strings."
        )
    metric_ids = list(dict.fromkeys(raw))
    unknown = sorted(set(metric_ids) - set(QA_BENCH_METRICS))
    if unknown:
        raise ValueError(
            f"Fixture {getattr(fixture, 'eval_id', '<unknown>')} has unknown "
            f"QA Bench metric id(s): {', '.join(unknown)}"
        )
    return metric_ids


def validate_capability(capability: str, fixture) -> None:
    if capability not in QA_BENCH_CAPABILITIES:
        raise ValueError(
            f"Fixture {getattr(fixture, 'eval_id', '<unknown>')} has unknown "
            f"QA Bench capability: {capability}"
        )


def validate_difficulty(difficulty: str, fixture) -> None:
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"Fixture {getattr(fixture, 'eval_id', '<unknown>')} has unknown "
            f"QA Bench difficulty: {difficulty}"
        )
