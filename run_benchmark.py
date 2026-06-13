#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from collections import Counter
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

load_dotenv(
    BENCHMARK_ROOT / ".env",
    override=os.getenv("BENCHMARK_ENV_FILE_OVERRIDE", "1") != "0",
)

from agents import (  # noqa: E402
    AgentRunResult,
    agent_display_name,
    agent_family,
    agent_model_label,
    agent_run_dir_name,
    changed_file_excerpt,
    diff_snapshots,
    run_agent,
    snapshot_files,
    tool_policy_metadata,
)
import benchmark_judge as benchmark_judge_module  # noqa: E402
from benchmark_artifacts import (  # noqa: E402
    build_artifact_checks,
    build_changed_diff,
    expects_artifact_change,
    expects_verification,
    is_implementation_file,
    is_noise_file,
    is_test_file,
)
from benchmark_judge import (  # noqa: E402
    BatchJudgeCaseScore,
    BatchJudgeResponse,
    JudgeCriterionScore,
    JudgeMetricScore,
    apply_overall_scores,
    apply_score,
    apply_time_efficiency_scores,
    build_batch_judge_prompt,
    batch_judge_results as _batch_judge_results,
    configured_judge_batch_size,
    empty_time_score,
    mark_unscored,
    overall_score_weights,
    parse_batch_judge_response,
    redact_configured_secrets,
    score_pending_results as _score_pending_results,
    duration_ms,
)
from benchmark_telemetry import (  # noqa: E402
    build_eval_telemetry,
    empty_eval_telemetry,
)
from benchmark_preflight import (  # noqa: E402
    PreflightIssue,
    compact_output,
    maestro_output_has_devices,
    preflight_fixture,
    preflight_maestro_device,
    required_live_device_platform,
)
from benchmark_tokens import (  # noqa: E402
    build_token_usage,
    empty_token_usage,
    parse_token_usage_json,
    parse_token_usage_text,
    token_total,
)
from fixtures import (
    copy_project,
    load_fixture,
    selected_eval_ids,
)  # noqa: E402
from qa_bench import (  # noqa: E402
    build_metadata as build_qa_bench_metadata,
    ensure_result_metadata as ensure_qa_bench_result_metadata,
    eval_metadata as qa_bench_eval_metadata,
    format_score_tables as format_qa_bench_score_tables,
    suite_metadata as qa_bench_suite_metadata,
)
from scoring import (
    apply_token_efficiency_scores,
    configured_token_baseline_threshold_percent,
    make_judge_model,
    make_test_case,
    result_label,
)  # noqa: E402


# Edit these defaults directly, or override with benchmark/.env.
DEFAULT_EVAL_IDS = "suite:qa-production"
DEFAULT_AGENTS = ["supatest", "cursor", "codex", "gemini"]
DEFAULT_PARALLELISM = 3
DEFAULT_AGENT_TIMEOUT_SECONDS = 600
PENDING_RESULT_FILE = "pending-result.json"
FIXTURE_HASH_SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "playwright-report",
    "test-results",
    ".turbo",
}


@dataclass(frozen=True)
class PendingResult:
    result: dict
    test_case: object | None = None


def main() -> int:
    score_existing_run_id = score_existing_run_id_from_args()
    run_id = score_existing_run_id or os.getenv(
        "BENCHMARK_RUN_ID", time.strftime("%Y%m%d-%H%M%S")
    )
    eval_ids = selected_eval_ids()
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
    print(f"Agents: {', '.join(agent_display_name(agent) for agent in agents)}")
    print(f"Parallelism: {parallelism}")
    print(f"Timeout: {os.environ['BENCHMARK_TIMEOUT_SECONDS']}s per agent run")
    print()

    case_ids = {
        eval_id: f"case-{index + 1:03d}" for index, eval_id in enumerate(eval_ids)
    }
    if score_existing_run_id:
        print(f"Recovery mode: scoring existing artifacts from {runs_dir}")
        print()
        if os.getenv("BENCHMARK_DISABLE_JUDGE_PREFLIGHT") != "1":
            judge_issue = preflight_judge_model()
            if judge_issue:
                print(f"Judge preflight failed: {judge_issue}")
                print(
                    "Fix DEEPEVAL_JUDGE_PROVIDER and the matching judge API key, or set "
                    "BENCHMARK_DISABLE_JUDGE_PREFLIGHT=1 to bypass this guard."
                )
                return 2
        if results_dir.exists():
            shutil.rmtree(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        return score_existing_run(
            run_id,
            runs_dir,
            results_dir,
            eval_ids,
            agents,
            case_ids,
            parallelism,
            int(os.environ["BENCHMARK_TIMEOUT_SECONDS"]),
        )

    preflight_issues: dict[str, PreflightIssue] = {}
    if not is_dry_run and os.getenv("BENCHMARK_DISABLE_PREFLIGHT") != "1":
        device_cache: dict[str, PreflightIssue | None] = {}
        for eval_id in eval_ids:
            issue = preflight_fixture(load_fixture(eval_id), device_cache)
            if issue:
                preflight_issues[eval_id] = issue
    if not is_dry_run and os.getenv("BENCHMARK_DISABLE_JUDGE_PREFLIGHT") != "1":
        judge_issue = preflight_judge_model()
        if judge_issue:
            print(f"Judge preflight failed: {judge_issue}")
            print(
                "Fix DEEPEVAL_JUDGE_PROVIDER and the matching judge API key, or set "
                "BENCHMARK_DISABLE_JUDGE_PREFLIGHT=1 to bypass this guard."
            )
            return 2

    jobs = [
        (eval_id, agent, case_ids[eval_id])
        for eval_id in eval_ids
        for agent in agents
        if eval_id not in preflight_issues
    ]
    if is_dry_run:
        print("Cases:")
        for eval_id, agent, case_id in [
            (eval_id, agent, case_ids[eval_id])
            for eval_id in eval_ids
            for agent in agents
        ]:
            print(f"  {case_id} / {agent_display_name(agent)} ({eval_id})")
        print()
        print(f"Runs dir: {runs_dir}")
        print(f"Results dir: {results_dir}")
        return 0

    results: list[dict] = []
    for eval_id, issue in preflight_issues.items():
        fixture = load_fixture(eval_id)
        for agent in agents:
            result = write_blocked_result(
                run_id,
                fixture,
                agent,
                case_ids[eval_id],
                issue,
            )
            results.append(result)
            print(format_score_line(result))

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
            if pending_result.result.get("scoreSource"):
                print(format_score_line(pending_result.result))
            else:
                print(format_pending_line(pending_result.result))

    if pending_results:
        print()
        batch_size = configured_judge_batch_size(len(pending_results))
        if batch_size:
            print(
                f"Scoring {len(pending_results)} completed runs with judge batches "
                f"of {batch_size}..."
            )
        else:
            print(
                f"Scoring {len(pending_results)} completed runs with one judge call..."
            )
        results.extend(
            score_pending_results(
                run_id,
                pending_results,
                run_eval_ids=eval_ids,
                run_agents=agents,
            )
        )
        print()
        print("Scores:")
        for result in order_results(eval_ids, agents, results):
            print(format_score_line(result))
    elif os.getenv("BENCHMARK_PRINT_FINAL_TABLE") == "1":
        print()
        print("Scores:")
        for result in order_results(eval_ids, agents, results):
            print(format_score_line(result))

    timeout_seconds = int(os.environ["BENCHMARK_TIMEOUT_SECONDS"])
    write_summary(
        results_dir, run_id, eval_ids, agents, parallelism, timeout_seconds, results
    )
    dashboard_issue = upload_supatest_eval_dashboard(
        run_id, eval_ids, agents, parallelism, timeout_seconds, results
    )
    print()
    print(f"Results: {results_dir}")
    print(f"Summary: {results_dir / 'scores.md'}")
    print(f"Combined JSON: {results_dir / 'run.json'}")
    if dashboard_issue:
        print(f"Supatest eval dashboard upload failed: {dashboard_issue}")
        if os.getenv("BENCHMARK_SUPATEST_EVAL_DASHBOARD_STRICT") == "1":
            return 3
    return 0


def preflight_judge_model() -> str | None:
    try:
        judge_model = make_judge_model()
    except Exception as error:
        return redact_configured_secrets(f"{type(error).__name__}: {error}")

    if judge_model is None:
        return (
            "No judge model is configured. Set DEEPEVAL_JUDGE_PROVIDER and the "
            "matching GOOGLE_API_KEY or OPENAI_API_KEY."
        )

    try:
        generated = judge_model.generate(
            judge_preflight_prompt(),
            schema=BatchJudgeResponse,
        )
        response = generated[0] if isinstance(generated, tuple) else generated
        judge_response = parse_batch_judge_response(response)
        if len(judge_response.results) != 1:
            return (
                "Judge API preflight failed: expected exactly one structured "
                f"result, got {len(judge_response.results)}."
            )
        scored = judge_response.results[0]
        if scored.resultId != "preflight" or scored.result != "pass":
            return (
                "Judge API preflight failed: structured response did not match "
                "the expected preflight result."
            )
    except Exception as error:
        return redact_configured_secrets(
            f"Judge API preflight failed: {type(error).__name__}: {error}"
        )
    return None


def judge_preflight_prompt() -> str:
    return (
        "This is a connectivity and structured-output preflight for a benchmark "
        "judge. Return exactly one result with resultId 'preflight', score 1.0, "
        "result 'pass', passedChecks 1, failedChecks 0, and a short reason. "
        "Do not include any extra resultIds."
    )


def score_pending_results(
    run_id: str,
    pending_results: list[PendingResult],
    run_eval_ids: list[str] | None = None,
    run_agents: list[str] | None = None,
) -> list[dict]:
    benchmark_judge_module.make_judge_model = make_judge_model
    return _score_pending_results(
        run_id,
        pending_results,
        run_eval_ids=run_eval_ids,
        run_agents=run_agents,
    )


def batch_judge_results(
    run_id: str,
    results: list[dict],
    scoring_jobs: list[tuple[int, object]],
    run_eval_ids: list[str] | None = None,
    run_agents: list[str] | None = None,
) -> BatchJudgeResponse:
    benchmark_judge_module.make_judge_model = make_judge_model
    return _batch_judge_results(
        run_id,
        results,
        scoring_jobs,
        run_eval_ids=run_eval_ids,
        run_agents=run_agents,
    )


def run_one_case(
    run_id: str, runs_dir: Path, eval_id: str, agent: str, case_id: str
) -> PendingResult:
    fixture = load_fixture(eval_id)
    case_run_dir = runs_dir / case_id / agent_run_dir_name(agent)
    case_run_dir.mkdir(parents=True, exist_ok=True)
    if fixture.logs_file:
        neutral_logs_file = case_run_dir / "failure.log"
        shutil.copyfile(fixture.logs_file, neutral_logs_file)
        fixture = replace(fixture, logs_file=neutral_logs_file)
    project_dir = copy_project(fixture, case_run_dir)

    run = run_agent(agent, fixture, project_dir, case_run_dir)
    result, changed_diff = result_from_agent_run(
        run_id,
        fixture,
        agent,
        case_id,
        run,
        case_run_dir,
    )
    write_pending_result(case_run_dir, result)
    return PendingResult(result, make_test_case(fixture, run, changed_diff))


def result_from_agent_run(
    run_id: str,
    fixture,
    agent: str,
    case_id: str,
    run: AgentRunResult,
    case_run_dir: Path,
    recovery: dict | None = None,
) -> tuple[dict, str]:
    artifact_checks = build_artifact_checks(fixture, run)
    token_usage = build_token_usage(agent, run.transcript_path, case_run_dir)
    telemetry = build_eval_telemetry(
        agent, run.transcript_path, case_run_dir, run.duration_ms
    )
    changed_diff = build_changed_diff(
        fixture.project_dir, run.project_dir, run.changed_files
    )
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
        "changedDiff": changed_diff,
        "artifactChecks": artifact_checks,
        "artifactWarnings": artifact_checks["warnings"],
        "tokenUsage": token_usage,
        "telemetry": telemetry,
        "fixtureHash": fixture_content_hash(fixture.eval_id),
        "qaBench": qa_bench_eval_metadata(fixture),
        "passCriteria": fixture.pass_criteria,
        "failCriteria": fixture.fail_criteria,
    }
    if recovery:
        result["recovery"] = recovery

    return result, changed_diff


def write_pending_result(case_run_dir: Path, result: dict) -> None:
    pending_path = case_run_dir / PENDING_RESULT_FILE
    pending_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


def score_existing_run(
    run_id: str,
    runs_dir: Path,
    results_dir: Path,
    eval_ids: list[str],
    agents: list[str],
    case_ids: dict[str, str],
    parallelism: int,
    timeout_seconds: int,
) -> int:
    pending_results: list[PendingResult] = []
    missing: list[str] = []
    for eval_id in eval_ids:
        fixture = load_fixture(eval_id)
        case_id = case_ids[eval_id]
        for agent in agents:
            case_run_dir = runs_dir / case_id / agent_run_dir_name(agent)
            if not case_run_dir.exists():
                missing.append(f"{case_id}/{agent_run_dir_name(agent)}")
                continue
            try:
                pending_results.append(
                    recover_pending_result(run_id, fixture, agent, case_id, case_run_dir)
                )
            except FileNotFoundError:
                missing.append(f"{case_id}/{agent_run_dir_name(agent)}")

    if missing:
        print("Cannot recover run; missing artifact directories/files:")
        for item in missing:
            print(f"  {item}")
        return 2

    if not pending_results:
        print("Cannot recover run; no completed agent artifacts were found.")
        return 2

    batch_size = configured_judge_batch_size(len(pending_results))
    if batch_size:
        print(
            f"Scoring {len(pending_results)} recovered runs with judge batches "
            f"of {batch_size}..."
        )
    else:
        print(f"Scoring {len(pending_results)} recovered runs with one judge call...")
    results = score_pending_results(
        run_id,
        pending_results,
        run_eval_ids=eval_ids,
        run_agents=agents,
    )
    print()
    print("Scores:")
    for result in order_results(eval_ids, agents, results):
        print(format_score_line(result))

    write_summary(
        results_dir, run_id, eval_ids, agents, parallelism, timeout_seconds, results
    )
    dashboard_issue = upload_supatest_eval_dashboard(
        run_id, eval_ids, agents, parallelism, timeout_seconds, results
    )
    print()
    print(f"Results: {results_dir}")
    print(f"Summary: {results_dir / 'scores.md'}")
    print(f"Combined JSON: {results_dir / 'run.json'}")
    if dashboard_issue:
        print(f"Supatest eval dashboard upload failed: {dashboard_issue}")
        if os.getenv("BENCHMARK_SUPATEST_EVAL_DASHBOARD_STRICT") == "1":
            return 3
    return 0


def recover_pending_result(
    run_id: str,
    fixture,
    agent: str,
    case_id: str,
    case_run_dir: Path,
) -> PendingResult:
    pending_path = case_run_dir / PENDING_RESULT_FILE
    if pending_path.exists():
        result = json.loads(pending_path.read_text())
        run = agent_run_from_result(fixture, agent, case_run_dir, result)
        result.setdefault(
            "recovery",
            {
                "source": PENDING_RESULT_FILE,
                "missingWallDuration": False,
            },
        )
        return PendingResult(
            result,
            make_test_case(fixture, run, str(result.get("changedDiff") or "")),
        )

    run = reconstruct_agent_run_from_artifacts(fixture, agent, case_run_dir)
    result, changed_diff = result_from_agent_run(
        run_id,
        fixture,
        agent,
        case_id,
        run,
        case_run_dir,
        recovery={
            "source": "run-artifacts",
            "missingWallDuration": run.duration_ms <= 0,
            "missingExitCode": run.exit_code == 0 and not run.timed_out,
        },
    )
    return PendingResult(result, make_test_case(fixture, run, changed_diff))


def agent_run_from_result(
    fixture,
    agent: str,
    case_run_dir: Path,
    result: dict,
) -> AgentRunResult:
    project_dir = Path(result.get("projectDir") or case_run_dir / "project")
    transcript_path = Path(
        result.get("transcriptPath") or case_run_dir / "transcript.log"
    )
    changed_files = list(result.get("changedFiles") or [])
    return AgentRunResult(
        agent=agent,
        eval_id=fixture.eval_id,
        project_dir=project_dir,
        transcript_path=transcript_path,
        exit_code=int(result.get("exitCode") or 0),
        duration_ms=int(result.get("durationMs") or 0),
        timed_out=bool(result.get("timedOut")),
        changed_files=changed_files,
        changed_file_excerpt=changed_file_excerpt(project_dir, changed_files),
    )


def reconstruct_agent_run_from_artifacts(
    fixture,
    agent: str,
    case_run_dir: Path,
) -> AgentRunResult:
    project_dir = case_run_dir / "project"
    transcript_path = case_run_dir / "transcript.log"
    if not project_dir.exists() or not transcript_path.exists():
        raise FileNotFoundError(str(case_run_dir))

    changed_files = diff_snapshots(
        snapshot_files(fixture.project_dir),
        snapshot_files(project_dir),
    )
    transcript = transcript_path.read_text(errors="replace")
    timeout_match = re.search(r"Timed out after\s+(\d+)s", transcript)
    timed_out = timeout_match is not None
    duration_ms = (
        int(timeout_match.group(1)) * 1000
        if timeout_match
        else infer_duration_ms_from_transcript(transcript)
    )
    exit_code = 124 if timed_out else 0
    return AgentRunResult(
        agent=agent,
        eval_id=fixture.eval_id,
        project_dir=project_dir,
        transcript_path=transcript_path,
        exit_code=exit_code,
        duration_ms=duration_ms,
        timed_out=timed_out,
        changed_files=changed_files,
        changed_file_excerpt=changed_file_excerpt(project_dir, changed_files),
    )


def infer_duration_ms_from_transcript(transcript: str) -> int:
    durations: list[int] = []
    for line in transcript.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        for value in possible_duration_values(event):
            if value is not None:
                durations.append(value)
    return durations[-1] if durations else 0


def possible_duration_values(event: dict) -> list[int | None]:
    values = [
        duration_value(event.get("duration_ms")),
        duration_value(event.get("durationMs")),
    ]
    stats = event.get("stats")
    if isinstance(stats, dict):
        values.append(duration_value(stats.get("duration_ms")))
        values.append(duration_value(stats.get("durationMs")))
    return values


def duration_value(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def write_error_result(
    run_id: str, eval_id: str, agent: str, case_id: str, error: Exception
) -> dict:
    qa_bench = None
    try:
        qa_bench = qa_bench_eval_metadata(load_fixture(eval_id))
    except Exception:
        qa_bench = None
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
        "passedChecks": 0,
        "failedChecks": 1,
        "exitCode": 1,
        "timedOut": False,
        "durationMs": 0,
        "tokenUsage": empty_token_usage(),
        "telemetry": empty_eval_telemetry(),
        "qaBench": qa_bench,
        "failureTaxonomy": ["agent-error"],
        "traceback": traceback.format_exc(),
    }


def write_blocked_result(
    run_id: str,
    fixture,
    agent: str,
    case_id: str,
    issue: PreflightIssue,
) -> dict:
    return {
        "runId": run_id,
        "caseId": case_id,
        "evalId": fixture.eval_id,
        "evalName": fixture.name,
        "agent": agent,
        "mode": fixture.mode,
        "score": None,
        "scorePercent": None,
        "result": "blocked",
        "reason": issue.reason,
        "scoreSource": "preflight",
        "passedChecks": None,
        "failedChecks": None,
        "preflight": {
            "kind": issue.kind,
            "platform": issue.platform,
            "reason": issue.reason,
        },
        "exitCode": None,
        "timedOut": False,
        "durationMs": 0,
        "tokenUsage": empty_token_usage(),
        "telemetry": empty_eval_telemetry(),
        "fixtureHash": fixture_content_hash(fixture.eval_id),
        "qaBench": qa_bench_eval_metadata(fixture),
        "projectDir": None,
        "transcriptPath": None,
        "changedFiles": [],
        "passCriteria": fixture.pass_criteria,
        "failCriteria": fixture.fail_criteria,
    }


def apply_failure_taxonomies(results: list[dict]) -> None:
    for result in results:
        try:
            fixture = load_fixture(result["evalId"])
        except Exception:
            fixture = None
        result["failureTaxonomy"] = failure_taxonomy_for_result(result, fixture)


def failure_taxonomy_for_result(result: dict, fixture=None) -> list[str]:
    taxonomy: list[str] = []
    telemetry = result.get("telemetry") or {}
    judge_diagnostics = result.get("judgeDiagnostics") or {}
    artifact_checks = result.get("artifactChecks") or {}
    artifact_warnings = (
        result.get("artifactWarnings") or artifact_checks.get("warnings") or []
    )
    reason = str(result.get("reason") or "").lower()
    score_source = str(result.get("scoreSource") or "")
    mode = str(result.get("mode") or getattr(fixture, "mode", "") or "")

    if result.get("timedOut"):
        taxonomy.append("timeout")
        if (result.get("changedFiles") or []) or (
            artifact_checks.get("changedRelevantFiles") or []
        ):
            taxonomy.append("timeout-with-artifacts")
        else:
            taxonomy.append("timeout-no-artifacts")
        if token_total(result.get("tokenUsage")) is not None:
            taxonomy.append("timeout-with-token-usage")
    if score_source in {"harness-error"}:
        taxonomy.append("agent-error")
    if score_source in {"judge-error"}:
        taxonomy.append("judge-error")
    if score_source == "preflight":
        taxonomy.append("env-preflight")
    if result.get("exitCode") not in {None, 0} and result.get("result") == "fail":
        taxonomy.append("agent-error")
    if "rate-limit-observed" in artifact_warnings or "rate limit" in reason:
        taxonomy.append("env-auth")
    if "verification-command-not-observed" in artifact_warnings:
        taxonomy.append("missing-verification")
    if "expected-artifact-change-missing" in artifact_warnings:
        taxonomy.append("missing-artifact")
    if "only-noisy-files-changed" in artifact_warnings:
        taxonomy.append("noisy-artifacts-only")
    if result.get("failedChecks"):
        taxonomy.append("grader-fail")
    if (result.get("tokenUsage") or {}).get("source") is None:
        taxonomy.append("missing-token-usage")
    taxonomy.extend(judge_diagnostics.get("failureTaxonomy") or [])
    if judge_diagnostics.get("deterministicCaps"):
        taxonomy.append("deterministic-cap")

    if telemetry.get("deniedPolicyCount"):
        taxonomy.append("policy-denial")
    if telemetry.get("didAskUser"):
        taxonomy.append("asked-user")

    over_tooling = bool(
        telemetry.get("didUseBrowser")
        or (mode == "plan" and telemetry.get("didRunTests"))
        or (mode == "plan" and telemetry.get("didWrite"))
    )
    if over_tooling:
        taxonomy.append("over-tooling")
    if mode == "plan" and (
        telemetry.get("didRunTests")
        or telemetry.get("didUseBrowser")
        or telemetry.get("didWrite")
    ):
        taxonomy.append("wrong-route")

    if fixture is not None and expects_artifact_change(fixture):
        changed_relevant = artifact_checks.get("changedRelevantFiles") or []
        if result.get("result") == "fail" and not changed_relevant:
            taxonomy.append("missed-artifact")

    return sorted(dict.fromkeys(taxonomy))


def build_reproducibility_metadata(
    run_id: str,
    eval_ids: list[str],
    agents: list[str],
    parallelism: int,
    timeout_seconds: int,
) -> dict:
    return {
        "benchmarkRunId": run_id,
        "benchmarkRoot": str(BENCHMARK_ROOT),
        "generatedBy": "run_benchmark.py",
        "git": git_metadata(BENCHMARK_ROOT),
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
        "evalRunner": {
            "benchmarkSuite": qa_bench_suite_metadata(
                requested_eval_ids_label(), eval_ids
            ),
            "evalIds": eval_ids,
            "baseEvalIds": os.getenv("BENCHMARK_EVAL_IDS", DEFAULT_EVAL_IDS),
            "extraEvalIds": os.getenv("BENCHMARK_EXTRA_EVAL_IDS", "") or None,
            "fixtureHashes": {
                eval_id: fixture_content_hash(eval_id) for eval_id in eval_ids
            },
            "parallelism": parallelism,
            "timeoutSeconds": timeout_seconds,
            "maxIterations": os.getenv("BENCHMARK_MAX_ITERATIONS"),
            "judgeBatchSize": os.getenv("BENCHMARK_JUDGE_BATCH_SIZE", "") or None,
            "promptProfile": os.getenv("BENCHMARK_PROMPT_PROFILE", "qa"),
            "environmentMode": benchmark_environment_mode(),
            "telemetryExpected": supatest_eval_telemetry_enabled(),
            "supatestMachineMode": os.getenv("BENCHMARK_SUPATEST_MACHINE_MODE", "1"),
        },
        "agents": {
            agent: {
                "family": agent_family(agent),
                "selectedModel": agent_model_label(agent),
            }
            for agent in agents
        },
    }


def git_metadata(root: Path) -> dict:
    return {
        "sha": git_output(root, "rev-parse", "HEAD"),
        "shortSha": git_output(root, "rev-parse", "--short", "HEAD"),
        "branch": git_output(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git_output(root, "status", "--porcelain")),
    }


def git_output(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def fixture_content_hash(eval_id: str) -> str | None:
    fixture_dir = BENCHMARK_ROOT / "agent-eval-fixtures" / "fixtures" / eval_id
    if not fixture_dir.exists():
        return None

    digest = hashlib.sha256()
    for path in sorted(fixture_dir.rglob("*")):
        if not path.is_file() or should_skip_fixture_hash(path, fixture_dir):
            continue
        relative = path.relative_to(fixture_dir).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def should_skip_fixture_hash(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in FIXTURE_HASH_SKIP_DIRS for part in relative_parts)


def benchmark_environment_mode() -> str:
    if os.getenv("BENCHMARK_OFFLINE") == "1":
        return "offline"
    if os.getenv("CI"):
        return "ci"
    return "local"


def supatest_eval_telemetry_enabled() -> bool:
    raw = (
        os.getenv(
            "BENCHMARK_SUPATEST_EVAL_TELEMETRY",
            os.getenv("SUPATEST_EVAL_TELEMETRY", "1"),
        )
        .strip()
        .lower()
    )
    return raw not in {"0", "false", "no", "off"}


def build_diagnostics_summary(results: list[dict]) -> dict:
    taxonomy = Counter(
        item for result in results for item in (result.get("failureTaxonomy") or [])
    )
    by_agent = {}
    for agent in sorted(
        {str(result.get("agent")) for result in results if result.get("agent")}
    ):
        agent_results = [result for result in results if result.get("agent") == agent]
        by_agent[agent] = summarize_agent_diagnostics(agent_results)

    return {
        "failureTaxonomy": dict(sorted(taxonomy.items())),
        "byAgent": by_agent,
    }


def summarize_agent_diagnostics(results: list[dict]) -> dict:
    tool_counts: Counter[str] = Counter()
    command_categories: Counter[str] = Counter()
    first_tools: Counter[str] = Counter()
    turns: list[int] = []
    for result in results:
        telemetry = result.get("telemetry") or {}
        tool_counts.update(telemetry.get("toolCounts") or {})
        command_categories.update(telemetry.get("commandCategories") or {})
        if telemetry.get("firstTool"):
            first_tools[str(telemetry["firstTool"])] += 1
        if telemetry.get("turns") is not None:
            turns.append(int(telemetry["turns"]))

    return {
        "toolCounts": dict(sorted(tool_counts.items())),
        "commandCategories": dict(sorted(command_categories.items())),
        "firstTools": dict(sorted(first_tools.items())),
        "averageTurns": round(sum(turns) / len(turns), 1) if turns else None,
        "didWrite": sum(
            1 for result in results if (result.get("telemetry") or {}).get("didWrite")
        ),
        "didRunTests": sum(
            1
            for result in results
            if (result.get("telemetry") or {}).get("didRunTests")
        ),
        "didUseBrowser": sum(
            1
            for result in results
            if (result.get("telemetry") or {}).get("didUseBrowser")
        ),
        "didAskUser": sum(
            1 for result in results if (result.get("telemetry") or {}).get("didAskUser")
        ),
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
    results_dir.mkdir(parents=True, exist_ok=True)
    apply_token_efficiency_scores(results)
    apply_time_efficiency_scores(results)
    apply_overall_scores(results)
    apply_failure_taxonomies(results)
    ensure_qa_bench_result_metadata(results, load_fixture)
    by_key = {(item["evalId"], item["agent"]): item for item in results}
    lines = [
        "| Eval | " + " | ".join(agent_display_name(agent) for agent in agents) + " |",
        "| --- | " + " | ".join(["---"] * len(agents)) + " |",
    ]

    for eval_id in eval_ids:
        cells = [eval_id]
        for agent in agents:
            result = by_key.get((eval_id, agent))
            cells.append(format_cell(result))
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")
    lines.extend(
        format_agent_score_summary_table(
            build_agent_score_summary_rows(agents, results)
        ).splitlines()
    )
    lines.append("")
    lines.append(format_qa_bench_score_tables(agents, results, agent_display_name))

    (results_dir / "scores.md").write_text("\n".join(lines) + "\n")
    ordered_results = order_results(eval_ids, agents, results)
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    weights = overall_score_weights()
    requested_eval_ids = requested_eval_ids_label()
    reproducibility = build_reproducibility_metadata(
        run_id, eval_ids, agents, parallelism, timeout_seconds
    )
    diagnostics = build_diagnostics_summary(ordered_results)
    qa_bench_metadata = build_qa_bench_metadata(
        requested_eval_ids,
        eval_ids,
        agents,
        ordered_results,
        [load_fixture(eval_id) for eval_id in eval_ids],
    )
    metadata = {
        "runId": run_id,
        "generatedAt": generated_at,
        "evalIds": eval_ids,
        "evalSelection": eval_selection_metadata(),
        "agents": agents,
        "agentModels": {agent: agent_model_label(agent) for agent in agents},
        "toolPolicy": tool_policy_metadata(),
        "reproducibility": reproducibility,
        "diagnostics": diagnostics,
        "qaBench": qa_bench_metadata,
        "parallelism": parallelism,
        "timeoutSeconds": timeout_seconds,
        "tokenScoring": {
            "scoreRange": "0 to 100",
            "baselineQaThresholdPercent": configured_token_baseline_threshold_percent(),
            "basis": "relative total tokens per eval; lowest known token total among QA-passing runs gets 100",
            "formula": "bestPassingTokens / agentTokens * 100",
            "failureCap": "runs below the QA baseline threshold cannot score above their QA percent for token efficiency",
            "unknownUsage": "scorePercent is 0 when token usage is unavailable",
            "cost": "reported by agent logs or estimated only when BENCHMARK_TOKEN_PRICE_* env vars are set",
            "fallback": "optional BENCHMARK_TOKEN_USAGE_FALLBACK_<AGENT>_TOKENS env vars can provide explicit totals for opaque agents",
        },
        "overallScoring": {
            "scoreRange": "0 to 100",
            "qaWeight": weights["qa"],
            "tokenUsageWeight": weights["tokenUsage"],
            "formula": "qaScorePercent * qaWeight + tokenUsage.scorePercent * tokenUsageWeight",
            "unknownTokenUsage": "missing token usage contributes 0 to the weighted token component",
        },
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


def upload_supatest_eval_dashboard(
    run_id: str,
    eval_ids: list[str],
    agents: list[str],
    parallelism: int,
    timeout_seconds: int,
    results: list[dict],
) -> str | None:
    api_key = os.getenv("BENCHMARK_SUPATEST_EVAL_DASHBOARD_API_KEY", "").strip()
    if not api_key:
        return None

    payload = build_supatest_eval_dashboard_payload(
        run_id, eval_ids, agents, parallelism, timeout_seconds, results
    )
    if not payload["results"]:
        print("Supatest eval dashboard: no benchmark results to upload")
        return None

    request = urllib.request.Request(
        supatest_eval_dashboard_ingest_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    timeout = int(
        os.getenv("BENCHMARK_SUPATEST_EVAL_DASHBOARD_TIMEOUT_SECONDS", "30") or "30"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")[:500]
        return redact_configured_secrets(
            f"HTTP {error.code} from {request.full_url}: {body or error.reason}"
        )
    except Exception as error:
        return redact_configured_secrets(f"{type(error).__name__}: {error}")

    print(
        "Supatest eval dashboard: uploaded "
        f"{len(payload['results'])} results to {request.full_url}"
    )
    return None


def build_supatest_eval_dashboard_payload(
    run_id: str,
    eval_ids: list[str],
    agents: list[str],
    parallelism: int,
    timeout_seconds: int,
    results: list[dict],
) -> dict:
    ensure_supatest_dashboard_overall_scores(results)
    apply_failure_taxonomies(results)
    ensure_qa_bench_result_metadata(results, load_fixture)
    ordered_results = order_results(eval_ids, agents, results)
    summary_rows = build_agent_score_summary_rows(agents, ordered_results)
    uploaded_rows = [row for row in summary_rows if row["total"] > row["blocked"]]
    uploaded_agents = [row["agent"] for row in uploaded_rows]
    score_summary_markdown = format_agent_score_summary_table(summary_rows)
    weights = overall_score_weights()
    reproducibility = build_reproducibility_metadata(
        run_id, eval_ids, agents, parallelism, timeout_seconds
    )
    diagnostics = build_diagnostics_summary(ordered_results)
    requested_eval_ids = requested_eval_ids_label()
    qa_bench_metadata = build_qa_bench_metadata(
        requested_eval_ids,
        eval_ids,
        agents,
        ordered_results,
        [load_fixture(eval_id) for eval_id in eval_ids],
    )
    return {
        "runName": supatest_eval_dashboard_run_name(run_id),
        "runMetadata": {
            "benchmarkRunId": run_id,
            "evalIds": eval_ids,
            "evalSelection": eval_selection_metadata(),
            "agents": uploaded_agents,
            "benchmarkAgents": agents,
            "agentModels": {
                agent: agent_model_label(agent) for agent in uploaded_agents
            },
            "toolPolicy": tool_policy_metadata(),
            "reproducibility": reproducibility,
            "diagnostics": diagnostics,
            "qaBench": qa_bench_metadata,
            "parallelism": parallelism,
            "timeoutSeconds": timeout_seconds,
            "overallScoring": {
                "qaWeight": weights["qa"],
                "tokenUsageWeight": weights["tokenUsage"],
            },
            "scoreSummaryMarkdown": score_summary_markdown,
            "scoreSummary": {
                "columns": [
                    "Agent",
                    "QA",
                    "Tok",
                    "Used",
                    "Cache R",
                    "Cache W",
                    "Time",
                    "Overall",
                    "P",
                    "Part",
                    "F",
                ],
                "rows": summary_rows,
            },
        },
        "results": [
            supatest_eval_dashboard_agent_summary_payload(
                run_id, row, score_summary_markdown
            )
            for row in uploaded_rows
        ],
        "durationMs": sum(
            int(result.get("durationMs") or 0)
            for result in ordered_results
            if result.get("result") != "blocked"
        ),
    }


def ensure_supatest_dashboard_overall_scores(results: list[dict]) -> None:
    needs_overall_score = any(
        result.get("result") != "blocked" and result.get("overallScorePercent") is None
        for result in results
    )
    if not needs_overall_score:
        return

    apply_token_efficiency_scores(results)
    apply_time_efficiency_scores(results)
    apply_overall_scores(results)


def build_agent_score_summary_rows(
    agents: list[str], results: list[dict]
) -> list[dict]:
    rows = []
    for agent in agents:
        agent_results = [item for item in results if item.get("agent") == agent]
        scored_results = scored_only(agent_results)
        token_summary = summarize_token_usage(agent_results)
        time_summary = summarize_time(agent_results)
        overall_summary = summarize_overall_score(agent_results)
        qa_avg = (
            round(
                sum(item["scorePercent"] for item in scored_results)
                / len(scored_results),
                1,
            )
            if scored_results
            else None
        )
        pass_count = sum(1 for item in agent_results if item.get("result") == "pass")
        partial_count = sum(
            1 for item in agent_results if item.get("result") == "partial"
        )
        fail_count = sum(1 for item in agent_results if item.get("result") == "fail")
        blocked_count = sum(
            1 for item in agent_results if item.get("result") == "blocked"
        )
        rows.append(
            {
                "agent": agent,
                "agentDisplayName": agent_display_name(agent),
                "agentModel": agent_model_label(agent),
                "total": len(agent_results),
                "scored": len(scored_results),
                "qaAvg": qa_avg,
                "tokenAvg": token_summary["scorePercent"],
                "tokenUsage": token_summary["totalTokens"],
                "tokenUsageText": format_token_count(token_summary["totalTokens"]),
                "cacheReadTokens": token_summary["cachedInputTokens"],
                "cacheReadTokensText": format_token_count(
                    token_summary["cachedInputTokens"]
                ),
                "cacheCreationTokens": token_summary["cacheCreationInputTokens"],
                "cacheCreationTokensText": format_token_count(
                    token_summary["cacheCreationInputTokens"]
                ),
                "timeMs": time_summary["averageDurationMs"],
                "timeText": format_duration_ms(time_summary["averageDurationMs"]),
                "totalTimeMs": time_summary["totalDurationMs"],
                "totalTimeText": format_duration_ms(time_summary["totalDurationMs"]),
                "overallScore": overall_summary["scorePercent"],
                "pass": pass_count,
                "partial": partial_count,
                "fail": fail_count,
                "blocked": blocked_count,
            }
        )
    return rows


def format_agent_score_summary_table(rows: list[dict]) -> str:
    lines = [
        "| Agent | QA | Tok | Used | Cache R | Cache W | Time | Overall | P | Part | F |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['agentDisplayName']} | "
            f"{format_optional_number(row['qaAvg'])} | "
            f"{format_optional_number(row['tokenAvg'])} | "
            f"{row['tokenUsageText']} | "
            f"{row['cacheReadTokensText']} | "
            f"{row['cacheCreationTokensText']} | "
            f"{row['totalTimeText']} | "
            f"{format_optional_number(row['overallScore'])} | "
            f"{row['pass']} | {row['partial']} | {row['fail']} |"
        )
    return "\n".join(lines)


def supatest_eval_dashboard_agent_summary_payload(
    run_id: str, row: dict, score_summary_markdown: str
) -> dict:
    agent = row["agent"]
    display_name = row["agentDisplayName"]
    score = dashboard_summary_score(row)
    return {
        "evalId": f"summary:{agent_run_dir_name(agent)}",
        "evalName": display_name,
        "evalCategory": "Agent Summary",
        "evalDescription": agent_score_summary_description(row),
        "evalMetadata": {
            "type": "agent-score-summary",
            "agent": agent,
            "agentDisplayName": display_name,
            "agentModel": row["agentModel"],
        },
        "result": dashboard_summary_result_label(score),
        "score": score,
        "durationMs": int(row.get("timeMs") or 0),
        "logs": score_summary_markdown[:4000],
        "metadata": {
            "benchmarkRunId": run_id,
            "type": "agent-score-summary",
            "scoreSummary": row,
            "scoreSummaryMarkdown": score_summary_markdown,
        },
    }


def agent_score_summary_description(row: dict) -> str:
    return (
        f"QA {format_optional_number(row['qaAvg'])} | "
        f"Tok {format_optional_number(row['tokenAvg'])} | "
        f"Used {row['tokenUsageText']} | "
        f"Cache R {row['cacheReadTokensText']} | "
        f"Cache W {row['cacheCreationTokensText']} | "
        f"Time {row['totalTimeText']} | "
        f"Overall {format_optional_number(row['overallScore'])} | "
        f"P {row['pass']} | Part {row['partial']} | F {row['fail']}"
    )


def dashboard_summary_score(row: dict) -> float:
    value = row.get("overallScore")
    if value is None:
        return 0.0
    return round(max(0.0, min(100.0, float(value))), 1)


def dashboard_summary_result_label(score: float) -> str:
    return result_label(score / 100.0, False)


def supatest_eval_dashboard_result_payload(result: dict) -> dict:
    agent = result.get("agent", "")
    eval_id = result.get("evalId", "")
    display_name = agent_display_name(agent)
    score = dashboard_result_score(result)
    score_details = supatest_eval_dashboard_score_details(result)
    return {
        "evalId": f"{eval_id}:{agent_run_dir_name(agent)}",
        "evalName": f"{eval_id} / {display_name}",
        "evalCategory": agent_family(agent) or "Agent",
        "evalDescription": str(result.get("evalName") or eval_id),
        "evalMetadata": {
            "baseEvalId": eval_id,
            "agent": agent,
            "agentDisplayName": display_name,
            "agentModel": agent_model_label(agent),
            "mode": result.get("mode"),
            "qaBench": result.get("qaBench") or {},
        },
        "result": dashboard_result_label(result),
        "score": score,
        "durationMs": int(result.get("durationMs") or 0),
        "logs": supatest_eval_dashboard_logs(result, score_details)[:4000],
        "metadata": {
            "benchmarkRunId": result.get("runId"),
            "caseId": result.get("caseId"),
            "baseEvalId": eval_id,
            "agent": agent,
            "agentDisplayName": display_name,
            "scorePercent": result.get("scorePercent"),
            "overallScorePercent": result.get("overallScorePercent"),
            "scoreSource": result.get("scoreSource"),
            "overallScoreSource": result.get("overallScoreSource"),
            "scoreDetails": score_details,
            "tokenUsage": result.get("tokenUsage") or empty_token_usage(),
            "time": result.get("time") or empty_time_score(result.get("durationMs")),
            "telemetry": result.get("telemetry") or empty_eval_telemetry(),
            "qaBench": result.get("qaBench") or {},
            "judgeDiagnostics": result.get("judgeDiagnostics") or {},
            "failureTaxonomy": result.get("failureTaxonomy") or [],
            "fixtureHash": result.get("fixtureHash"),
            "exitCode": result.get("exitCode"),
            "timedOut": result.get("timedOut"),
            "changedFiles": result.get("changedFiles") or [],
            "artifactWarnings": result.get("artifactWarnings") or [],
            "projectDir": result.get("projectDir"),
            "transcriptPath": result.get("transcriptPath"),
        },
    }


def supatest_eval_dashboard_score_details(result: dict) -> dict:
    token_usage = result.get("tokenUsage") or empty_token_usage()
    time_score = result.get("time") or empty_time_score(result.get("durationMs"))
    weights = overall_score_weights()
    return {
        "overall": {
            "score": result.get("overallScore"),
            "scorePercent": result.get("overallScorePercent"),
            "source": result.get("overallScoreSource"),
        },
        "qa": {
            "score": result.get("score"),
            "scorePercent": result.get("scorePercent"),
            "result": result.get("result"),
            "source": result.get("scoreSource"),
            "passedChecks": result.get("passedChecks"),
            "failedChecks": result.get("failedChecks"),
        },
        "tokenUsage": {
            "score": token_usage.get("score"),
            "scorePercent": token_usage.get("scorePercent"),
            "scoreBasis": token_usage.get("scoreBasis"),
            "totalTokens": token_usage.get("totalTokens"),
            "inputTokens": token_usage.get("inputTokens"),
            "outputTokens": token_usage.get("outputTokens"),
            "cachedInputTokens": token_usage.get("cachedInputTokens"),
            "cacheCreationInputTokens": token_usage.get("cacheCreationInputTokens"),
            "estimatedCostUsd": token_usage.get("estimatedCostUsd"),
            "source": token_usage.get("source"),
            "warnings": token_usage.get("warnings") or [],
        },
        "time": {
            "score": time_score.get("score"),
            "scorePercent": time_score.get("scorePercent"),
            "scoreBasis": time_score.get("scoreBasis"),
            "durationMs": time_score.get("durationMs") or result.get("durationMs"),
        },
        "qaBench": result.get("qaBench") or {},
        "judgeDiagnostics": result.get("judgeDiagnostics") or {},
        "weights": {
            "qa": weights["qa"],
            "tokenUsage": weights["tokenUsage"],
        },
    }


def supatest_eval_dashboard_logs(result: dict, score_details: dict) -> str:
    overall = score_details["overall"]
    qa = score_details["qa"]
    token_usage = score_details["tokenUsage"]
    time_score = score_details["time"]
    qa_bench = score_details.get("qaBench") or {}
    judge_diagnostics = score_details.get("judgeDiagnostics") or {}
    weights = score_details["weights"]
    passed = format_optional_number(qa.get("passedChecks"))
    failed = format_optional_number(qa.get("failedChecks"))
    lines = [
        "Detailed score",
        (
            "QA Bench: "
            f"{qa_bench.get('capabilityLabel') or qa_bench.get('capability') or 'n/a'} "
            f"({', '.join(qa_bench.get('metricIds') or []) or 'no metrics'})"
        ),
        (
            "Overall: "
            f"{format_percent(overall.get('scorePercent'))} "
            f"(source: {overall.get('source') or 'n/a'})"
        ),
        (
            "QA: "
            f"{format_percent(qa.get('scorePercent'))} "
            f"{qa.get('result') or 'n/a'} "
            f"({passed}p/{failed}f, source: {qa.get('source') or 'n/a'})"
        ),
        (
            "Token: "
            f"{format_percent(token_usage.get('scorePercent'))} "
            f"({format_token_count(token_usage.get('totalTokens'))} total tokens, "
            f"input {format_token_count(token_usage.get('inputTokens'))}, "
            f"output {format_token_count(token_usage.get('outputTokens'))}, "
            f"cache read {format_token_count(token_usage.get('cachedInputTokens'))}, "
            f"cache create {format_token_count(token_usage.get('cacheCreationInputTokens'))}, "
            f"cost {format_cost_usd(token_usage.get('estimatedCostUsd'))}, "
            f"basis: {token_usage.get('scoreBasis') or 'n/a'})"
        ),
        (
            "Time: "
            f"{format_percent(time_score.get('scorePercent'))} "
            f"({format_duration_ms(time_score.get('durationMs'))}, "
            f"basis: {time_score.get('scoreBasis') or 'n/a'})"
        ),
        (
            "Weights: "
            f"QA {format_weight(weights['qa'])}, "
            f"token {format_weight(weights['tokenUsage'])}"
        ),
    ]
    if judge_diagnostics:
        confidence = judge_diagnostics.get("confidence")
        taxonomy = ", ".join(judge_diagnostics.get("failureTaxonomy") or [])
        cap = judge_diagnostics.get("deterministicCaps") or {}
        lines.append(
            "Judge diagnostics: "
            f"confidence {format_optional_number(round(confidence, 2) if confidence is not None else None)}, "
            f"taxonomy {taxonomy or 'n/a'}"
        )
        if cap:
            lines.append(
                "Deterministic cap: "
                f"{format_optional_number(cap.get('originalScore'))} -> "
                f"{format_optional_number(cap.get('cappedScore'))} "
                f"({', '.join(cap.get('reasons') or [])})"
            )
    reason = str(result.get("reason") or "").strip()
    if reason:
        lines.extend(["", "Judge reason", reason])
    return "\n".join(lines)


def format_percent(value) -> str:
    if value is None:
        return "n/a"
    return f"{format_compact_number(value)}%"


def format_weight(value) -> str:
    return f"{format_compact_number(float(value) * 100)}%"


def format_compact_number(value) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}".rstrip("0").rstrip(".")


def dashboard_result_score(result: dict) -> float:
    value = result.get("overallScorePercent")
    if value is None:
        return 0.0
    return round(max(0.0, min(100.0, float(value))), 1)


def dashboard_result_label(result: dict) -> str:
    label = str(result.get("result") or "").lower()
    return label if label in {"pass", "partial", "fail"} else "fail"


def supatest_eval_dashboard_run_name(run_id: str) -> str:
    raw = os.getenv("BENCHMARK_SUPATEST_EVAL_DASHBOARD_RUN_NAME", "").strip()
    if not raw:
        return f"Benchmark {run_id}"
    return raw.format(run_id=run_id)


def supatest_eval_dashboard_ingest_url() -> str:
    raw = os.getenv(
        "BENCHMARK_SUPATEST_EVAL_DASHBOARD_URL",
        "https://evals-dashboard.supatest.ai",
    ).strip()
    if not raw:
        raw = "https://evals-dashboard.supatest.ai"
    base = raw.rstrip("/")
    if base.endswith("/api/v1/ingest"):
        return base
    if base.endswith("/api/v1"):
        return f"{base}/ingest"
    return f"{base}/api/v1/ingest"


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
    scored_results = scored_only(results)
    average = (
        round(
            sum(item.get("scorePercent", 0) for item in scored_results)
            / len(scored_results),
            1,
        )
        if scored_results
        else None
    )
    token_usage = summarize_token_usage(results)
    time_summary = summarize_time(results)
    overall_score = summarize_overall_score(results)
    return {
        "total": total,
        "scored": len(scored_results),
        "averageScorePercent": average,
        "overallScorePercent": overall_score["scorePercent"],
        "overallScored": overall_score["scored"],
        "tokenUsage": token_usage,
        "time": time_summary,
        "pass": sum(1 for item in results if item.get("result") == "pass"),
        "partial": sum(1 for item in results if item.get("result") == "partial"),
        "fail": sum(1 for item in results if item.get("result") == "fail"),
        "blocked": sum(1 for item in results if item.get("result") == "blocked"),
        "unscored": sum(1 for item in results if item.get("result") == "unscored"),
        "passedChecks": sum(int(item.get("passedChecks") or 0) for item in results),
        "failedChecks": sum(int(item.get("failedChecks") or 0) for item in results),
        "artifactWarnings": sum(
            len(item.get("artifactWarnings") or []) for item in results
        ),
        "timedOut": sum(1 for item in results if item.get("timedOut")),
        "durationMs": sum(item.get("durationMs", 0) for item in results),
    }


def summarize_result(result: dict | None) -> dict | None:
    if not result:
        return None
    return {
        "scorePercent": result.get("scorePercent"),
        "overallScore": result.get("overallScore"),
        "overallScorePercent": result.get("overallScorePercent"),
        "overallScoreSource": result.get("overallScoreSource"),
        "result": result.get("result"),
        "durationMs": result.get("durationMs"),
        "timedOut": result.get("timedOut"),
        "exitCode": result.get("exitCode"),
        "scoreSource": result.get("scoreSource"),
        "passedChecks": result.get("passedChecks"),
        "failedChecks": result.get("failedChecks"),
        "artifactWarnings": result.get("artifactWarnings") or [],
        "tokenUsage": result.get("tokenUsage") or empty_token_usage(),
        "time": result.get("time") or empty_time_score(result.get("durationMs")),
        "telemetry": result.get("telemetry") or empty_eval_telemetry(),
        "qaBench": result.get("qaBench") or {},
        "judgeDiagnostics": result.get("judgeDiagnostics") or {},
        "failureTaxonomy": result.get("failureTaxonomy") or [],
    }


def summarize_overall_score(results: list[dict]) -> dict:
    scored = [
        result for result in results if result.get("overallScorePercent") is not None
    ]
    return {
        "scored": len(scored),
        "scorePercent": (
            round(
                sum(float(result.get("overallScorePercent") or 0) for result in scored)
                / len(scored),
                1,
            )
            if scored
            else None
        ),
    }


def summarize_token_usage(results: list[dict]) -> dict:
    known = [
        result
        for result in results
        if token_total(result.get("tokenUsage")) is not None
    ]
    scored = [
        result
        for result in results
        if result.get("scorePercent") is not None
        and (result.get("tokenUsage") or {}).get("scorePercent") is not None
    ]
    if not known and not scored:
        return {
            "known": 0,
            "scorePercent": None,
            "totalTokens": None,
            "inputTokens": None,
            "outputTokens": None,
            "cachedInputTokens": None,
            "cacheCreationInputTokens": None,
            "estimatedCostUsd": None,
        }

    costs = [
        (result.get("tokenUsage") or {}).get("estimatedCostUsd")
        for result in known
        if (result.get("tokenUsage") or {}).get("estimatedCostUsd") is not None
    ]
    return {
        "known": len(known),
        "scorePercent": (
            round(
                sum(
                    (result.get("tokenUsage") or {}).get("scorePercent")
                    for result in scored
                )
                / len(scored),
                1,
            )
            if scored
            else None
        ),
        "totalTokens": (
            sum(
                int((result.get("tokenUsage") or {}).get("totalTokens") or 0)
                for result in known
            )
            if known
            else None
        ),
        "inputTokens": (
            sum(
                int((result.get("tokenUsage") or {}).get("inputTokens") or 0)
                for result in known
            )
            if known
            else None
        ),
        "outputTokens": (
            sum(
                int((result.get("tokenUsage") or {}).get("outputTokens") or 0)
                for result in known
            )
            if known
            else None
        ),
        "cachedInputTokens": (
            sum(
                int((result.get("tokenUsage") or {}).get("cachedInputTokens") or 0)
                for result in known
            )
            if known
            else None
        ),
        "cacheCreationInputTokens": (
            sum(
                int(
                    (result.get("tokenUsage") or {}).get("cacheCreationInputTokens")
                    or 0
                )
                for result in known
            )
            if known
            else None
        ),
        "estimatedCostUsd": (
            round(sum(float(value) for value in costs), 6) if costs else None
        ),
    }


def summarize_time(results: list[dict]) -> dict:
    known = [result for result in results if duration_ms(result) is not None]
    scored = [
        result
        for result in results
        if result.get("scorePercent") is not None
        and (result.get("time") or {}).get("scorePercent") is not None
    ]
    if not known and not scored:
        return {
            "known": 0,
            "scorePercent": None,
            "totalDurationMs": None,
            "averageDurationMs": None,
        }

    total_duration = (
        sum(int(duration_ms(result) or 0) for result in known) if known else None
    )
    return {
        "known": len(known),
        "scorePercent": (
            round(
                sum((result.get("time") or {}).get("scorePercent") for result in scored)
                / len(scored),
                1,
            )
            if scored
            else None
        ),
        "totalDurationMs": total_duration,
        "averageDurationMs": (
            round(total_duration / len(known))
            if total_duration is not None and known
            else None
        ),
    }


def format_cell(result: dict | None) -> str:
    if not result:
        return "-"
    if result.get("result") == "blocked":
        return "blocked"
    if result.get("result") == "unscored":
        return "unscored"
    if result.get("scorePercent") is None:
        return f"n/a {result['result']}"
    score = result.get("scorePercent")
    score_str = f"{score}%"
    if result.get("passedChecks") is not None or result.get("failedChecks") is not None:
        passed = int(result.get("passedChecks") or 0)
        failed = int(result.get("failedChecks") or 0)
        return f"{score_str} ({passed}p/{failed}f) {result['result']}"
    return f"{score_str} {result['result']}"


def format_optional_number(value) -> str:
    return "n/a" if value is None else str(value)


def format_token_count(value) -> str:
    if value is None:
        return "n/a"
    value = int(value)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def format_duration_ms(value) -> str:
    if value is None:
        return "n/a"
    value = int(value)
    if value < 1_000:
        return f"{value}ms"
    if value < 60_000:
        return f"{value / 1_000:.1f}s"
    minutes, remainder = divmod(value, 60_000)
    seconds = round(remainder / 1_000)
    if minutes < 60:
        return f"{minutes}m {seconds:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def format_cost_usd(value) -> str:
    return "n/a" if value is None else f"${float(value):.4f}"


def format_score_line(result: dict) -> str:
    score_text = check_score_text(result)
    return (
        f"{result['evalId']:>4} {agent_display_name(result['agent']):<32} "
        f"{score_text:>8} {result['result']:<8} "
        f"{result['durationMs']}ms"
    )


def format_pending_line(result: dict) -> str:
    pending = {**result, "scorePercent": None, "result": "pending"}
    return format_score_line(pending)


def check_score_text(result: dict) -> str:
    if result.get("passedChecks") is not None or result.get("failedChecks") is not None:
        passed = int(result.get("passedChecks") or 0)
        failed = int(result.get("failedChecks") or 0)
        return f"{passed}p/{failed}f"
    score = result.get("scorePercent")
    return "n/a" if score is None else f"{score}"


def scored_only(results: list[dict]) -> list[dict]:
    return [
        item
        for item in results
        if item.get("result") != "blocked" and item.get("scorePercent") is not None
    ]


def csv_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def score_existing_run_id_from_args() -> str | None:
    env_value = (os.getenv("BENCHMARK_SCORE_EXISTING_RUN_ID") or "").strip()
    if env_value:
        return env_value

    for index, arg in enumerate(sys.argv[1:], start=1):
        if arg == "--score-existing":
            if index + 1 >= len(sys.argv):
                raise ValueError("--score-existing requires a run id.")
            return sys.argv[index + 1]
        if arg.startswith("--score-existing="):
            value = arg.split("=", 1)[1].strip()
            if not value:
                raise ValueError("--score-existing requires a run id.")
            return value
    return None


def requested_eval_ids_label() -> str:
    base = os.getenv("BENCHMARK_EVAL_IDS", DEFAULT_EVAL_IDS)
    extra = (os.getenv("BENCHMARK_EXTRA_EVAL_IDS", "") or "").strip()
    if not extra:
        return base
    return f"{base} + {extra}"


def eval_selection_metadata() -> dict:
    return {
        "requested": requested_eval_ids_label(),
        "base": os.getenv("BENCHMARK_EVAL_IDS", DEFAULT_EVAL_IDS),
        "extra": os.getenv("BENCHMARK_EXTRA_EVAL_IDS", "") or None,
        "limit": os.getenv("BENCHMARK_EVAL_LIMIT", "all") or "all",
        "offset": int(os.getenv("BENCHMARK_EVAL_OFFSET", "0") or "0"),
    }


def benchmark_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else BENCHMARK_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
