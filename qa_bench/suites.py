from __future__ import annotations

from .rubrics import LOW_DIFFICULTY_EVAL_IDS


SUITE_PREFIX = "suite:"

QA_BENCH_SUITES = {
    "qa-production": {
        "label": "QA Bench Production",
        "description": "All available QA lifecycle fixtures, with metadata slices by capability, metric, mode, and difficulty.",
        "evalIds": ["all"],
    },
    "qa-low": {
        "label": "QA Bench Low Difficulty",
        "description": "Baseline QA competency suite covering simple but real test authoring, repair, selector, metadata, and discovery tasks.",
        "evalIds": LOW_DIFFICULTY_EVAL_IDS,
    },
    "qa-core": {
        "label": "QA Bench Core",
        "description": "Balanced representative suite for vendor comparisons without running every fixture.",
        "evalIds": [
            "E1",
            "E3",
            "E10",
            "E11",
            "E18",
            "E19",
            "E25",
            "E29",
            "E31",
            "E43",
            "E48",
            "E50",
            "E58",
            "E61",
            "E63",
            "E65",
            "E66",
            "E67",
            "E70",
            "E71",
            "E73",
            "E80",
            "E101",
            "E105",
            "E118",
        ],
    },
    "qa-smoke": {
        "label": "QA Bench Smoke",
        "description": "Fast sanity suite spanning authoring, repair, planning, feature validation, and mobile QA.",
        "evalIds": ["E25", "E31", "E43", "E48", "E50", "E65", "E101", "E118"],
    },
    "qa-lifecycle-extended": {
        "label": "QA Bench Lifecycle Extended",
        "description": "Broad lifecycle suite covering advanced QA tasks across web, mobile, repair, reporting, evidence, and metadata workflows.",
        "evalIds": [
            "E3",
            "E7",
            "E10",
            "E11",
            "E18",
            "E19",
            "E23",
            "E24",
            "E25",
            "E27",
            "E28",
            "E31",
            "E32",
            "E43",
            "E48",
            "E50",
            "E58",
            "E61",
            "E62",
            "E63",
            "E65",
            "E66",
            "E67",
            "E69",
            "E70",
            "E71",
            "E73",
            "E74",
            "E80",
            "E101",
            "E103",
            "E105",
            "E107",
            "E108",
            "E109",
            "E113",
            "E118",
            "E119",
            "E120",
        ],
    },
}


def normalize_suite_name(raw: str) -> str:
    value = raw.strip().lower()
    if value.startswith(SUITE_PREFIX):
        value = value[len(SUITE_PREFIX) :]
    return value


def is_suite_token(raw: str) -> bool:
    return normalize_suite_name(
        raw
    ) in QA_BENCH_SUITES or raw.strip().lower().startswith(SUITE_PREFIX)


def available_suite_names() -> list[str]:
    return sorted(QA_BENCH_SUITES)


def resolve_suite_eval_ids(raw: str, available_eval_ids: list[str]) -> list[str]:
    suite_name = normalize_suite_name(raw)
    suite = QA_BENCH_SUITES.get(suite_name)
    if not suite:
        raise ValueError(
            f"Unknown QA Bench suite: {raw}. Available suites: "
            + ", ".join(available_suite_names())
        )

    eval_ids = list(suite["evalIds"])
    if eval_ids == ["all"]:
        return list(available_eval_ids)

    available = set(available_eval_ids)
    missing = [eval_id for eval_id in eval_ids if eval_id not in available]
    if missing:
        raise ValueError(
            f"QA Bench suite {suite_name} references missing eval id(s): "
            + ", ".join(missing)
        )
    return eval_ids


def configured_suite_name(
    raw_eval_ids: str | None, selected_eval_ids: list[str]
) -> str:
    raw_suite = normalize_suite_name(raw_eval_ids or "")
    if raw_suite in QA_BENCH_SUITES:
        return raw_suite

    for suite_name, suite in QA_BENCH_SUITES.items():
        suite_eval_ids = suite["evalIds"]
        if suite_eval_ids == ["all"]:
            continue
        if list(selected_eval_ids) == list(suite_eval_ids):
            return suite_name
    return "custom-qa"


def suite_metadata(raw_eval_ids: str | None, selected_eval_ids: list[str]) -> dict:
    suite_name = configured_suite_name(raw_eval_ids, selected_eval_ids)
    suite = QA_BENCH_SUITES.get(suite_name)
    if suite:
        return {
            "id": suite_name,
            "label": suite["label"],
            "description": suite["description"],
            "evalCount": len(selected_eval_ids),
        }
    return {
        "id": suite_name,
        "label": "Custom QA Bench Selection",
        "description": "Custom subset of QA Bench fixtures selected by eval id.",
        "evalCount": len(selected_eval_ids),
    }
