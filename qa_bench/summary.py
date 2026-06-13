from __future__ import annotations

from collections.abc import Callable

from .classification import catalog_for_fixtures, eval_metadata
from .definitions import QA_BENCH_VERSION
from .suites import suite_metadata


def build_metadata(
    raw_eval_ids: str | None,
    eval_ids: list[str],
    agents: list[str],
    results: list[dict],
    fixtures: list,
) -> dict:
    catalog = catalog_for_fixtures(fixtures)
    return {
        "version": QA_BENCH_VERSION,
        "suite": suite_metadata(raw_eval_ids, eval_ids),
        **catalog,
        "summary": summarize_results(agents, results),
    }


def ensure_result_metadata(
    results: list[dict], fixture_loader: Callable[[str], object]
) -> None:
    for result in results:
        if result.get("qaBench") is not None:
            continue
        eval_id = result.get("evalId")
        if not eval_id:
            continue
        try:
            result["qaBench"] = eval_metadata(fixture_loader(str(eval_id)))
        except Exception:
            result["qaBench"] = None


def summarize_results(agents: list[str], results: list[dict]) -> dict:
    return {
        "byAgent": {
            agent: {
                "byCapability": summarize_dimension(
                    [result for result in results if result.get("agent") == agent],
                    "capability",
                ),
                "byMetric": summarize_metrics(
                    [result for result in results if result.get("agent") == agent]
                ),
                "byDifficulty": summarize_dimension(
                    [result for result in results if result.get("agent") == agent],
                    "difficulty",
                ),
                "byMode": summarize_dimension(
                    [result for result in results if result.get("agent") == agent],
                    "mode",
                ),
            }
            for agent in agents
        },
        "overall": {
            "byCapability": summarize_dimension(results, "capability"),
            "byMetric": summarize_metrics(results),
            "byDifficulty": summarize_dimension(results, "difficulty"),
            "byMode": summarize_dimension(results, "mode"),
        },
    }


def summarize_dimension(results: list[dict], key: str) -> dict:
    groups: dict[str, list[dict]] = {}
    for result in results:
        qa_bench = result.get("qaBench") or {}
        value = qa_bench.get(key)
        if value is None:
            continue
        groups.setdefault(str(value), []).append(result)
    return {
        group: summarize_scores(group_results)
        for group, group_results in sorted(groups.items())
    }


def summarize_metrics(results: list[dict]) -> dict:
    metric_values: dict[str, list[dict]] = {}
    for result in results:
        qa_bench = result.get("qaBench") or {}
        for metric_id in qa_bench.get("metricIds") or []:
            metric_values.setdefault(str(metric_id), []).append(result)
    return {
        metric_id: summarize_scores(metric_results, metric_id)
        for metric_id, metric_results in sorted(metric_values.items())
    }


def summarize_scores(results: list[dict], metric_id: str | None = None) -> dict:
    scored_values: list[tuple[float, float]] = []
    for result in results:
        value = score_percent(result, metric_id)
        if value is None:
            continue
        weight = float((result.get("qaBench") or {}).get("weight") or 1.0)
        scored_values.append((float(value), weight))

    weighted_total = sum(score * weight for score, weight in scored_values)
    weight_sum = sum(weight for _, weight in scored_values)
    return {
        "total": len(results),
        "scored": len(scored_values),
        "scorePercent": (
            round(sum(score for score, _ in scored_values) / len(scored_values), 1)
            if scored_values
            else None
        ),
        "weightedScorePercent": (
            round(weighted_total / weight_sum, 1) if weight_sum else None
        ),
        "pass": sum(1 for result in results if result.get("result") == "pass"),
        "partial": sum(1 for result in results if result.get("result") == "partial"),
        "fail": sum(1 for result in results if result.get("result") == "fail"),
        "blocked": sum(1 for result in results if result.get("result") == "blocked"),
        "unscored": sum(1 for result in results if result.get("result") == "unscored"),
    }


def score_percent(result: dict, metric_id: str | None = None) -> float | None:
    if metric_id:
        metric_scores = (result.get("qaBench") or {}).get("metricScores") or {}
        if metric_id in metric_scores:
            return round(float(metric_scores[metric_id]) * 100, 1)
    score = result.get("scorePercent")
    return float(score) if score is not None else None


def format_score_tables(
    agents: list[str],
    results: list[dict],
    agent_display_name: Callable[[str], str],
) -> str:
    return "\n\n".join(
        [
            "## QA Bench Capability Scores\n"
            + format_dimension_table(agents, results, "capability", agent_display_name),
            "## QA Bench Metric Scores\n"
            + format_metric_table(agents, results, agent_display_name),
            "## QA Bench Difficulty Scores\n"
            + format_dimension_table(agents, results, "difficulty", agent_display_name),
        ]
    )


def format_dimension_table(
    agents: list[str],
    results: list[dict],
    key: str,
    agent_display_name: Callable[[str], str],
) -> str:
    values = sorted(
        {
            str((result.get("qaBench") or {}).get(key))
            for result in results
            if (result.get("qaBench") or {}).get(key) is not None
        }
    )
    return format_table(
        key.title(),
        values,
        agents,
        lambda agent, value: [
            result
            for result in results
            if result.get("agent") == agent
            and str((result.get("qaBench") or {}).get(key)) == value
        ],
        agent_display_name,
    )


def format_metric_table(
    agents: list[str],
    results: list[dict],
    agent_display_name: Callable[[str], str],
) -> str:
    metric_ids = sorted(
        {
            str(metric_id)
            for result in results
            for metric_id in ((result.get("qaBench") or {}).get("metricIds") or [])
        }
    )
    return format_table(
        "Metric",
        metric_ids,
        agents,
        lambda agent, metric_id: [
            result
            for result in results
            if result.get("agent") == agent
            and metric_id in ((result.get("qaBench") or {}).get("metricIds") or [])
        ],
        agent_display_name,
        metric_mode=True,
    )


def format_table(
    first_column: str,
    values: list[str],
    agents: list[str],
    selector,
    agent_display_name: Callable[[str], str],
    metric_mode: bool = False,
) -> str:
    lines = [
        "| "
        + " | ".join([first_column, *[agent_display_name(agent) for agent in agents]])
        + " |",
        "| " + " | ".join(["---", *["---:"] * len(agents)]) + " |",
    ]
    for value in values:
        cells = [value]
        for agent in agents:
            selected_results = selector(agent, value)
            summary = summarize_scores(selected_results, value if metric_mode else None)
            cells.append(format_optional_number(summary["scorePercent"]))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def format_optional_number(value) -> str:
    return "n/a" if value is None else str(value)
