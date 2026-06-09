#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from pathlib import Path

BENCHMARK_ROOT = Path(__file__).resolve().parent

VENV_PYTHON = BENCHMARK_ROOT / ".venv" / "bin" / "python"
VENV_DIR = BENCHMARK_ROOT / ".venv"
VENV_MARKER = VENV_DIR / ".benchmark-root"
REQUIREMENTS = BENCHMARK_ROOT / "requirements.txt"

if (
    VENV_DIR.exists()
    and VENV_PYTHON.exists()
    and os.getenv("BENCHMARK_SKIP_BOOTSTRAP") != "1"
    and (not VENV_MARKER.exists() or VENV_MARKER.read_text() != str(BENCHMARK_ROOT))
):
    print("Benchmark folder moved or virtualenv is unverified; rebuilding .venv...")
    shutil.rmtree(VENV_DIR)

if not VENV_PYTHON.exists() and os.getenv("BENCHMARK_SKIP_BOOTSTRAP") != "1":
    print("Creating benchmark virtualenv...")
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    print("Installing benchmark Python dependencies...")
    subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS)], check=True
    )
    VENV_MARKER.write_text(str(BENCHMARK_ROOT))

if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != VENV_DIR.resolve():
    os.execv(
        str(VENV_PYTHON),
        [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
    )

sys.path.insert(0, str(BENCHMARK_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    print(
        "Missing Python dependencies. If you moved this folder, run: rm -rf .venv && ./run_benchmark.py --dry-run"
    )
    raise

load_dotenv(BENCHMARK_ROOT / ".env")

from agents import run_agent  # noqa: E402
from deepeval import evaluate  # noqa: E402
from deepeval.evaluate.configs import (  # noqa: E402
    AsyncConfig,
    CacheConfig,
    DisplayConfig,
    ErrorConfig,
)
from deepeval.test_case import LLMTestCase  # noqa: E402
from fixtures import copy_project, load_fixture, resolve_eval_ids  # noqa: E402
from scoring import (
    make_metric,
    make_test_case,
    result_label,
)  # noqa: E402


# Edit these defaults directly, or override with benchmark/.env.
DEFAULT_EVAL_IDS = "all"
DEFAULT_AGENTS = ["supatest", "cursor", "codex", "gemini"]
DEFAULT_PARALLELISM = 3
DEFAULT_AGENT_TIMEOUT_SECONDS = 600


@dataclass(frozen=True)
class PendingResult:
    result: dict
    test_case: LLMTestCase | None = None


def main() -> int:
    run_id = os.getenv("BENCHMARK_RUN_ID", time.strftime("%Y%m%d-%H%M%S"))
    eval_ids = resolve_eval_ids(os.getenv("BENCHMARK_EVAL_IDS", DEFAULT_EVAL_IDS))
    agents = csv_env("BENCHMARK_AGENTS", DEFAULT_AGENTS)
    parallelism = int(os.getenv("BENCHMARK_PARALLELISM", str(DEFAULT_PARALLELISM)))
    os.environ.setdefault(
        "BENCHMARK_TIMEOUT_SECONDS", str(DEFAULT_AGENT_TIMEOUT_SECONDS)
    )

    runs_dir = (
        benchmark_path(os.getenv("BENCHMARK_RUNS_DIR"), BENCHMARK_ROOT / "runs")
        / run_id
    )
    results_dir = (
        benchmark_path(os.getenv("BENCHMARK_RESULTS_DIR"), BENCHMARK_ROOT / "results")
        / run_id
    )
    is_dry_run = "--dry-run" in sys.argv
    if not is_dry_run:
        if results_dir.exists():
            shutil.rmtree(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)

    print(f"Run ID: {run_id}")
    print(f"Evals: {', '.join(eval_ids)}")
    print(f"Agents: {', '.join(agents)}")
    print(f"Parallelism: {parallelism}")
    print(f"Timeout: {os.environ['BENCHMARK_TIMEOUT_SECONDS']}s per agent run")
    print()

    case_ids = {
        eval_id: f"case-{index + 1:03d}" for index, eval_id in enumerate(eval_ids)
    }
    jobs = [
        (eval_id, agent, case_ids[eval_id]) for eval_id in eval_ids for agent in agents
    ]
    if is_dry_run:
        print("Cases:")
        for eval_id, agent, case_id in jobs:
            print(f"  {case_id} / {agent} ({eval_id})")
        print()
        print(f"Runs dir: {runs_dir}")
        print(f"Results dir: {results_dir}")
        return 0

    pending_results: list[PendingResult] = []

    with ThreadPoolExecutor(max_workers=parallelism) as executor:
        futures = {
            executor.submit(run_one_case, run_id, runs_dir, eval_id, agent, case_id): (
                eval_id,
                agent,
                case_id,
            )
            for eval_id, agent, case_id in jobs
        }
        for future in as_completed(futures):
            eval_id, agent, case_id = futures[future]
            try:
                pending_result = future.result()
            except Exception as error:
                pending_result = PendingResult(
                    write_error_result(run_id, eval_id, agent, case_id, error)
                )
            pending_results.append(pending_result)
            print(
                f"{eval_id:>4} {agent:<9} finished {pending_result.result['durationMs']}ms"
            )

    results = score_pending_results(run_id, pending_results)
    print()
    print("Scores:")
    for result in order_results(eval_ids, agents, results):
        print(
            f"{result['evalId']:>4} {result['agent']:<9} {result['scorePercent']:>3} {result['result']:<7} {result['durationMs']}ms"
        )

    timeout_seconds = int(os.environ["BENCHMARK_TIMEOUT_SECONDS"])
    write_summary(
        results_dir, run_id, eval_ids, agents, parallelism, timeout_seconds, results
    )
    print()
    print(f"Results: {results_dir}")
    print(f"Summary: {results_dir / 'scores.md'}")
    print(f"Combined JSON: {results_dir / 'run.json'}")
    return 0


def run_one_case(
    run_id: str, runs_dir: Path, eval_id: str, agent: str, case_id: str
) -> PendingResult:
    fixture = load_fixture(eval_id)
    case_run_dir = runs_dir / case_id / agent
    case_run_dir.mkdir(parents=True, exist_ok=True)
    if fixture.logs_file:
        neutral_logs_file = case_run_dir / "failure.log"
        shutil.copyfile(fixture.logs_file, neutral_logs_file)
        fixture = replace(fixture, logs_file=neutral_logs_file)
    project_dir = copy_project(fixture, case_run_dir)

    run = run_agent(agent, fixture, project_dir, case_run_dir)
    result = {
        "runId": run_id,
        "caseId": case_id,
        "evalId": fixture.eval_id,
        "evalName": fixture.name,
        "agent": agent,
        "mode": fixture.mode,
        "exitCode": run.exit_code,
        "timedOut": run.timed_out,
        "durationMs": run.duration_ms,
        "projectDir": str(run.project_dir),
        "transcriptPath": str(run.transcript_path),
        "changedFiles": run.changed_files,
        "passCriteria": fixture.pass_criteria,
        "failCriteria": fixture.fail_criteria,
    }

    return PendingResult(result, make_test_case(fixture, run))


def score_pending_results(
    run_id: str, pending_results: list[PendingResult]
) -> list[dict]:
    results = [dict(item.result) for item in pending_results]
    scoring_jobs = [
        (index, item.test_case)
        for index, item in enumerate(pending_results)
        if item.test_case is not None
    ]
    if not scoring_jobs:
        return results

    test_cases = [test_case for _, test_case in scoring_jobs if test_case is not None]
    try:
        evaluation = evaluate(
            test_cases=test_cases,
            metrics=[make_metric()],
            identifier=run_id,
            hyperparameters=build_deepeval_hyperparameters(results),
            async_config=AsyncConfig(run_async=False),
            display_config=DisplayConfig(
                show_indicator=False,
                print_results=False,
                inspect_after_run=False,
                truncate_passing_cases=False,
            ),
            cache_config=CacheConfig(write_cache=False, use_cache=False),
            error_config=ErrorConfig(ignore_errors=False),
        )
    except Exception as error:
        reason = f"{type(error).__name__}: {error}"
        for result_index, _ in scoring_jobs:
            apply_score(results[result_index], 0.0, reason, "judge-error")
        return results

    scored_result_indexes: set[int] = set()
    for test_result in evaluation.test_results:
        if test_result.index is None or test_result.index >= len(scoring_jobs):
            continue
        result_index = scoring_jobs[test_result.index][0]
        scored_result_indexes.add(result_index)
        metric_data = test_result.metrics_data[0] if test_result.metrics_data else None
        if metric_data is None:
            apply_score(
                results[result_index],
                0.0,
                "DeepEval returned no metric data for this case.",
                "judge-error",
            )
            continue

        score = float(metric_data.score or 0.0)
        reason = metric_data.reason or metric_data.error or ""
        source = "timeout" if results[result_index].get("timedOut") else "judge"
        apply_score(results[result_index], score, reason, source)

    for result_index, _ in scoring_jobs:
        if result_index not in scored_result_indexes:
            apply_score(
                results[result_index],
                0.0,
                "DeepEval did not return a score for this case.",
                "judge-error",
            )

    return results


def apply_score(result: dict, score: float, reason: str, score_source: str) -> None:
    result["score"] = score
    result["scorePercent"] = round(score * 100)
    result["result"] = result_label(score, bool(result.get("timedOut")))
    result["reason"] = reason
    result["scoreSource"] = score_source


def build_deepeval_hyperparameters(results: list[dict]) -> dict:
    eval_ids = sorted(
        {str(item.get("evalId")) for item in results if item.get("evalId")}
    )
    agents = sorted({str(item.get("agent")) for item in results if item.get("agent")})
    return {
        "benchmark_run_id": results[0].get("runId", "") if results else "",
        "eval_ids": ",".join(eval_ids),
        "agents": ",".join(agents),
        "parallelism": int(
            os.getenv("BENCHMARK_PARALLELISM", str(DEFAULT_PARALLELISM))
        ),
        "timeout_seconds": int(
            os.getenv("BENCHMARK_TIMEOUT_SECONDS", str(DEFAULT_AGENT_TIMEOUT_SECONDS))
        ),
    }


def write_error_result(
    run_id: str, eval_id: str, agent: str, case_id: str, error: Exception
) -> dict:
    return {
        "runId": run_id,
        "caseId": case_id,
        "evalId": eval_id,
        "agent": agent,
        "score": 0.0,
        "scorePercent": 0,
        "result": "fail",
        "reason": f"{type(error).__name__}: {error}",
        "scoreSource": "harness-error",
        "exitCode": 1,
        "timedOut": False,
        "durationMs": 0,
        "traceback": traceback.format_exc(),
    }


def write_summary(
    results_dir: Path,
    run_id: str,
    eval_ids: list[str],
    agents: list[str],
    parallelism: int,
    timeout_seconds: int,
    results: list[dict],
) -> None:
    by_key = {(item["evalId"], item["agent"]): item for item in results}
    lines = [
        "| Eval | " + " | ".join(agents) + " |",
        "| --- | " + " | ".join(["---"] * len(agents)) + " |",
    ]

    for eval_id in eval_ids:
        cells = [eval_id]
        for agent in agents:
            result = by_key.get((eval_id, agent))
            cells.append(format_cell(result))
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")
    lines.append("| Agent | Average | Pass | Partial | Fail |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for agent in agents:
        agent_results = [item for item in results if item["agent"] == agent]
        if agent_results:
            average = round(
                sum(item["scorePercent"] for item in agent_results)
                / len(agent_results),
                1,
            )
        else:
            average = 0
        pass_count = sum(1 for item in agent_results if item["result"] == "pass")
        partial_count = sum(1 for item in agent_results if item["result"] == "partial")
        fail_count = sum(1 for item in agent_results if item["result"] == "fail")
        lines.append(
            f"| {agent} | {average} | {pass_count} | {partial_count} | {fail_count} |"
        )

    (results_dir / "scores.md").write_text("\n".join(lines) + "\n")
    ordered_results = order_results(eval_ids, agents, results)
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    metadata = {
        "runId": run_id,
        "generatedAt": generated_at,
        "evalIds": eval_ids,
        "agents": agents,
        "parallelism": parallelism,
        "timeoutSeconds": timeout_seconds,
    }
    (results_dir / "summary.json").write_text(
        json.dumps(
            {
                **metadata,
                "summary": build_run_summary(eval_ids, agents, ordered_results),
            },
            indent=2,
        )
    )
    (results_dir / "run.json").write_text(
        json.dumps(
            {
                **metadata,
                "runsByEval": build_runs_by_eval(eval_ids, agents, ordered_results),
            },
            indent=2,
        )
    )


def order_results(
    eval_ids: list[str], agents: list[str], results: list[dict]
) -> list[dict]:
    eval_order = {eval_id: index for index, eval_id in enumerate(eval_ids)}
    agent_order = {agent: index for index, agent in enumerate(agents)}
    return sorted(
        results,
        key=lambda item: (
            eval_order.get(item.get("evalId"), len(eval_order)),
            agent_order.get(item.get("agent"), len(agent_order)),
            item.get("evalId", ""),
            item.get("agent", ""),
        ),
    )


def build_run_summary(
    eval_ids: list[str], agents: list[str], results: list[dict]
) -> dict:
    by_key = {(item["evalId"], item["agent"]): item for item in results}
    by_eval = {
        eval_id: {
            agent: summarize_result(by_key.get((eval_id, agent))) for agent in agents
        }
        for eval_id in eval_ids
    }

    by_agent = {}
    for agent in agents:
        agent_results = [item for item in results if item.get("agent") == agent]
        by_agent[agent] = summarize_group(agent_results)

    return {
        "overall": summarize_group(results),
        "byAgent": by_agent,
        "byEval": by_eval,
    }


def build_runs_by_eval(
    eval_ids: list[str], agents: list[str], results: list[dict]
) -> dict:
    by_key = {(item["evalId"], item["agent"]): item for item in results}
    return {
        eval_id: {agent: by_key.get((eval_id, agent)) for agent in agents}
        for eval_id in eval_ids
    }


def summarize_group(results: list[dict]) -> dict:
    total = len(results)
    average = (
        round(sum(item.get("scorePercent", 0) for item in results) / total, 1)
        if total
        else 0
    )
    return {
        "total": total,
        "averageScorePercent": average,
        "pass": sum(1 for item in results if item.get("result") == "pass"),
        "partial": sum(1 for item in results if item.get("result") == "partial"),
        "fail": sum(1 for item in results if item.get("result") == "fail"),
        "timedOut": sum(1 for item in results if item.get("timedOut")),
        "durationMs": sum(item.get("durationMs", 0) for item in results),
    }


def summarize_result(result: dict | None) -> dict | None:
    if not result:
        return None
    return {
        "scorePercent": result.get("scorePercent"),
        "result": result.get("result"),
        "durationMs": result.get("durationMs"),
        "timedOut": result.get("timedOut"),
        "exitCode": result.get("exitCode"),
    }


def format_cell(result: dict | None) -> str:
    if not result:
        return "-"
    return f"{result['scorePercent']} {result['result']}"


def csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def benchmark_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else BENCHMARK_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
