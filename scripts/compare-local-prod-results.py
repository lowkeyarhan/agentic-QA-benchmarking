#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_summary(path: Path) -> dict:
    return json.loads((path / "summary.json").read_text())


def load_runs(path: Path) -> list[dict]:
    payload = json.loads((path / "run.json").read_text())
    runs: list[dict] = []
    for eval_runs in payload.get("runsByEval", {}).values():
        if isinstance(eval_runs, dict):
            runs.extend(eval_runs.values())
        elif isinstance(eval_runs, list):
            runs.extend(eval_runs)
    return runs


def agent_summary(summary: dict) -> dict:
    rows = summary.get("summary", {}).get("agentScoreSummary", [])
    return rows[0] if rows else {}


def difficulty_scores(summary: dict) -> dict[str, float | None]:
    qa = summary.get("qaBench", {}).get("aggregates", {}).get("byDifficulty", {})
    return {key: value.get("averageScorePercent") for key, value in qa.items()}


def score_percent(run: dict) -> float | None:
    overall = run.get("overall") or {}
    value = overall.get("scorePercent")
    if isinstance(value, (int, float)):
        return float(value)
    judge = run.get("judge") or {}
    value = judge.get("scorePercent")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def top_issue(run: dict) -> str:
    taxonomy = run.get("failureTaxonomy") or []
    if taxonomy:
        first = taxonomy[0]
        if isinstance(first, dict):
            return str(first.get("label") or first.get("id") or "unknown")
        return str(first)
    judge = run.get("judge") or {}
    failed = [
        item.get("criterion") or item.get("name")
        for item in judge.get("criteria", [])
        if item.get("passed") is False
    ]
    if failed:
        return str(failed[0])
    return str(run.get("result") or "unknown")


def fmt(value: object, *, signed: bool = False) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        text = f"{value:.1f}"
        if signed and value > 0:
            return f"+{text}"
        return text
    return str(value)


def build_report(local_dir: Path, prod_dir: Path) -> str:
    local_summary = load_summary(local_dir)
    prod_summary = load_summary(prod_dir)
    local_runs = {run["evalId"]: run for run in load_runs(local_dir)}
    prod_runs = {run["evalId"]: run for run in load_runs(prod_dir)}

    local_agent = agent_summary(local_summary)
    prod_agent = agent_summary(prod_summary)
    local_diff = difficulty_scores(local_summary)
    prod_diff = difficulty_scores(prod_summary)

    lines = [
        "# Local vs Production Supatest Comparison",
        "",
        f"- Local results: `{local_dir}`",
        f"- Prod results: `{prod_dir}`",
        "",
        "## Overall",
        "",
        "| Metric | Local build | Production npm | Delta (local - prod) |",
        "| --- | ---: | ---: | ---: |",
    ]

    for key, label in [
        ("overallScorePercent", "Overall"),
        ("qaScorePercent", "QA"),
        ("tokenEfficiencyScorePercent", "Token efficiency"),
        ("timeScorePercent", "Time efficiency"),
    ]:
        local_val = local_agent.get(key)
        prod_val = prod_agent.get(key)
        delta = None
        if isinstance(local_val, (int, float)) and isinstance(prod_val, (int, float)):
            delta = round(local_val - prod_val, 1)
        lines.append(
            f"| {label} | {fmt(local_val)} | {fmt(prod_val)} | {fmt(delta, signed=True)} |"
        )

    lines.extend(
        [
            "",
            "| Result counts | Local | Production |",
            "| --- | ---: | ---: |",
        ]
    )
    for key, label in [
        ("passCount", "Pass"),
        ("partialCount", "Partial"),
        ("failCount", "Fail"),
    ]:
        lines.append(
            f"| {label} | {local_agent.get(key, 'n/a')} | {prod_agent.get(key, 'n/a')} |"
        )

    lines.extend(
        [
            "",
            "## By difficulty",
            "",
            "| Difficulty | Local QA | Prod QA | Delta |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for difficulty in ["low", "medium", "high", "ultra", "max"]:
        local_val = local_diff.get(difficulty)
        prod_val = prod_diff.get(difficulty)
        delta = None
        if isinstance(local_val, (int, float)) and isinstance(prod_val, (int, float)):
            delta = round(local_val - prod_val, 1)
        lines.append(
            f"| {difficulty} | {fmt(local_val)} | {fmt(prod_val)} | {fmt(delta, signed=True)} |"
        )

    improvements: list[tuple[str, float, float, str, str]] = []
    regressions: list[tuple[str, float, float, str, str]] = []
    for eval_id in sorted(set(local_runs) | set(prod_runs)):
        local_run = local_runs.get(eval_id, {})
        prod_run = prod_runs.get(eval_id, {})
        local_score = score_percent(local_run)
        prod_score = score_percent(prod_run)
        if local_score is None or prod_score is None:
            continue
        delta = local_score - prod_score
        if delta > 5:
            improvements.append(
                (
                    eval_id,
                    local_score,
                    prod_score,
                    str(local_run.get("result", "unknown")),
                    str(prod_run.get("result", "unknown")),
                )
            )
        elif delta < -5:
            regressions.append(
                (
                    eval_id,
                    local_score,
                    prod_score,
                    str(local_run.get("result", "unknown")),
                    str(prod_run.get("result", "unknown")),
                )
            )

    lines.extend(["", "## Biggest local improvements (>5 pts)", ""])
    if improvements:
        lines.extend(
            [
                "| Eval | Local | Prod | Local result | Prod result |",
                "| --- | ---: | ---: | --- | --- |",
            ]
        )
        for eval_id, local_score, prod_score, local_result, prod_result in sorted(
            improvements, key=lambda item: item[1] - item[2], reverse=True
        )[:15]:
            lines.append(
                f"| {eval_id} | {local_score:.1f} | {prod_score:.1f} | {local_result} | {prod_result} |"
            )
    else:
        lines.append("No eval improved by more than 5 points.")

    lines.extend(["", "## Biggest local regressions (>5 pts)", ""])
    if regressions:
        lines.extend(
            [
                "| Eval | Local | Prod | Local result | Prod result |",
                "| --- | ---: | ---: | --- | --- |",
            ]
        )
        for eval_id, local_score, prod_score, local_result, prod_result in sorted(
            regressions, key=lambda item: item[1] - item[2]
        )[:15]:
            lines.append(
                f"| {eval_id} | {local_score:.1f} | {prod_score:.1f} | {local_result} | {prod_result} |"
            )
    else:
        lines.append("No eval regressed by more than 5 points.")

    lines.extend(["", "## Still failing on local", ""])
    local_failures = [
        run for run in local_runs.values() if run.get("result") in {"fail", "partial"}
    ]
    if not local_failures:
        lines.append("Local had no fail/partial evals.")
    else:
        lines.extend(
            [
                "| Eval | Difficulty | Local | Prod | Local issue |",
                "| --- | --- | ---: | ---: | --- |",
            ]
        )
        for run in sorted(local_failures, key=lambda item: score_percent(item) or 0):
            eval_id = run["evalId"]
            prod_run = prod_runs.get(eval_id, {})
            lines.append(
                f"| {eval_id} | {run.get('difficulty', 'unknown')} | "
                f"{fmt(score_percent(run))} | {fmt(score_percent(prod_run))} | {top_issue(run)} |"
            )

    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: compare-local-prod-results.py <local-results-dir> <prod-results-dir>"
        )
        return 2

    local_dir = Path(sys.argv[1])
    prod_dir = Path(sys.argv[2])
    report = build_report(local_dir, prod_dir)
    print(report, end="")

    prefix = local_dir.name.rsplit("-local", 1)[0]
    report_path = local_dir.parent / f"{prefix}-comparison.md"
    report_path.write_text(report)
    print(f"Wrote comparison report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
