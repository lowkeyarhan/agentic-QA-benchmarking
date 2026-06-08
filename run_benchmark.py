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
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS)], check=True)
    VENV_MARKER.write_text(str(BENCHMARK_ROOT))

if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != VENV_DIR.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

sys.path.insert(0, str(BENCHMARK_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    print("Missing Python dependencies. If you moved this folder, run: rm -rf .venv && ./run_benchmark.py --dry-run")
    raise

load_dotenv(BENCHMARK_ROOT / ".env")

from agents import run_agent  # noqa: E402
from fixtures import copy_project, load_fixture  # noqa: E402
from scoring import make_metric, make_test_case, result_label  # noqa: E402


# Edit these defaults directly, or override with benchmark/.env.
DEFAULT_EVAL_IDS = ["E1", "E3", "E7", "E11", "E15"]
DEFAULT_AGENTS = ["supatest", "cursor", "codex"]
DEFAULT_PARALLELISM = 3
DEFAULT_AGENT_TIMEOUT_SECONDS = 450


def main() -> int:
    run_id = os.getenv("BENCHMARK_RUN_ID", time.strftime("%Y%m%d-%H%M%S"))
    eval_ids = csv_env("BENCHMARK_EVAL_IDS", DEFAULT_EVAL_IDS)
    agents = csv_env("BENCHMARK_AGENTS", DEFAULT_AGENTS)
    parallelism = int(os.getenv("BENCHMARK_PARALLELISM", str(DEFAULT_PARALLELISM)))
    os.environ.setdefault("BENCHMARK_TIMEOUT_SECONDS", str(DEFAULT_AGENT_TIMEOUT_SECONDS))

    runs_dir = benchmark_path(os.getenv("BENCHMARK_RUNS_DIR"), BENCHMARK_ROOT / "runs") / run_id
    results_dir = benchmark_path(os.getenv("BENCHMARK_RESULTS_DIR"), BENCHMARK_ROOT / "results") / run_id
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"Run ID: {run_id}")
    print(f"Evals: {', '.join(eval_ids)}")
    print(f"Agents: {', '.join(agents)}")
    print(f"Parallelism: {parallelism}")
    print(f"Timeout: {os.environ['BENCHMARK_TIMEOUT_SECONDS']}s per agent run")
    print()

    jobs = [(eval_id, agent) for eval_id in eval_ids for agent in agents]
    if "--dry-run" in sys.argv:
        print("Cases:")
        for eval_id, agent in jobs:
            print(f"  {eval_id} / {agent}")
        print()
        print(f"Runs dir: {runs_dir}")
        print(f"Results dir: {results_dir}")
        return 0

    results: list[dict] = []

    with ThreadPoolExecutor(max_workers=parallelism) as executor:
        futures = {
            executor.submit(run_one_case, run_id, runs_dir, results_dir, eval_id, agent): (eval_id, agent)
            for eval_id, agent in jobs
        }
        for future in as_completed(futures):
            eval_id, agent = futures[future]
            try:
                result = future.result()
            except Exception as error:
                result = write_error_result(results_dir, run_id, eval_id, agent, error)
            results.append(result)
            print(f"{eval_id:>4} {agent:<9} {result['scorePercent']:>3} {result['result']:<7} {result['durationMs']}ms")

    write_summary(results_dir, eval_ids, agents, results)
    print()
    print(f"Results: {results_dir}")
    print(f"Summary: {results_dir / 'scores.md'}")
    return 0


def run_one_case(run_id: str, runs_dir: Path, results_dir: Path, eval_id: str, agent: str) -> dict:
    fixture = load_fixture(eval_id)
    case_run_dir = runs_dir / eval_id / agent
    case_result_dir = results_dir / eval_id
    project_dir = copy_project(fixture, case_run_dir)

    run = run_agent(agent, fixture, project_dir, case_run_dir)
    test_case = make_test_case(fixture, run)
    metric = make_metric(fixture)
    metric.measure(test_case)

    score = 0.0 if run.timed_out else float(metric.score or 0.0)
    label = result_label(score, run.timed_out)

    result = {
        "runId": run_id,
        "evalId": fixture.eval_id,
        "evalName": fixture.name,
        "agent": agent,
        "mode": fixture.mode,
        "score": score,
        "scorePercent": round(score * 100),
        "result": label,
        "reason": metric.reason,
        "exitCode": run.exit_code,
        "timedOut": run.timed_out,
        "durationMs": run.duration_ms,
        "projectDir": str(run.project_dir),
        "transcriptPath": str(run.transcript_path),
        "changedFiles": run.changed_files,
        "passCriteria": fixture.pass_criteria,
        "failCriteria": fixture.fail_criteria,
    }

    case_result_dir.mkdir(parents=True, exist_ok=True)
    (case_result_dir / f"{agent}.json").write_text(json.dumps(result, indent=2))
    return result


def write_error_result(results_dir: Path, run_id: str, eval_id: str, agent: str, error: Exception) -> dict:
    result = {
        "runId": run_id,
        "evalId": eval_id,
        "agent": agent,
        "score": 0.0,
        "scorePercent": 0,
        "result": "fail",
        "reason": f"{type(error).__name__}: {error}",
        "exitCode": 1,
        "timedOut": False,
        "durationMs": 0,
        "traceback": traceback.format_exc(),
    }
    case_result_dir = results_dir / eval_id
    case_result_dir.mkdir(parents=True, exist_ok=True)
    (case_result_dir / f"{agent}.json").write_text(json.dumps(result, indent=2))
    return result


def write_summary(results_dir: Path, eval_ids: list[str], agents: list[str], results: list[dict]) -> None:
    by_key = {(item["evalId"], item["agent"]): item for item in results}
    lines = ["| Eval | " + " | ".join(agents) + " |", "| --- | " + " | ".join(["---"] * len(agents)) + " |"]

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
            average = round(sum(item["scorePercent"] for item in agent_results) / len(agent_results), 1)
        else:
            average = 0
        pass_count = sum(1 for item in agent_results if item["result"] == "pass")
        partial_count = sum(1 for item in agent_results if item["result"] == "partial")
        fail_count = sum(1 for item in agent_results if item["result"] == "fail")
        lines.append(f"| {agent} | {average} | {pass_count} | {partial_count} | {fail_count} |")

    (results_dir / "scores.md").write_text("\n".join(lines) + "\n")
    (results_dir / "summary.json").write_text(json.dumps(results, indent=2))


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
