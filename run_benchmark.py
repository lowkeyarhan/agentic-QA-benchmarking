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
from typing import Literal

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

load_dotenv(BENCHMARK_ROOT / ".env", override=False)

from agents import (  # noqa: E402
    agent_display_name,
    agent_model_label,
    agent_run_dir_name,
    run_agent,
)
from fixtures import copy_project, load_fixture, resolve_eval_ids  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from scoring import (
    make_judge_model,
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
    test_case: object | None = None


@dataclass(frozen=True)
class PreflightIssue:
    kind: str
    platform: str
    reason: str


class BatchJudgeCaseScore(BaseModel):
    resultId: str
    score: float
    result: Literal["pass", "partial", "fail"]
    passedChecks: int
    failedChecks: int
    reason: str


class BatchJudgeResponse(BaseModel):
    results: list[BatchJudgeCaseScore]


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
    print(f"Agents: {', '.join(agent_display_name(agent) for agent in agents)}")
    print(f"Parallelism: {parallelism}")
    print(f"Timeout: {os.environ['BENCHMARK_TIMEOUT_SECONDS']}s per agent run")
    print()

    case_ids = {
        eval_id: f"case-{index + 1:03d}" for index, eval_id in enumerate(eval_ids)
    }
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
    print()
    print(f"Results: {results_dir}")
    print(f"Summary: {results_dir / 'scores.md'}")
    print(f"Combined JSON: {results_dir / 'run.json'}")
    return 0


def preflight_fixture(
    fixture, device_cache: dict[str, PreflightIssue | None]
) -> PreflightIssue | None:
    platform = required_live_device_platform(fixture)
    if not platform:
        return None

    if platform not in device_cache:
        device_cache[platform] = preflight_maestro_device(platform)
    return device_cache[platform]


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
    return None


def redact_configured_secrets(text: str) -> str:
    for name in (
        "GOOGLE_API_KEY",
        "CONFIDENT_API_KEY",
        "OPENAI_API_KEY",
        "SUPATEST_API_KEY",
        "BENCHMARK_SUPATEST_API_KEY",
    ):
        value = os.getenv(name)
        if value and len(value) >= 6:
            text = text.replace(value, "<redacted>")
    return text


def required_live_device_platform(fixture) -> str | None:
    text = "\n".join(
        [
            fixture.task,
            "\n".join(fixture.pass_criteria),
            "\n".join(fixture.fail_criteria),
        ]
    ).lower()

    if "authoring only" in text or "do not inspect a live device" in text:
        return None

    requires_actual_inspection = (
        "calls mcp__maestro__inspect_view_hierarchy" in text
        or "calls mcp__maestro__inspect_screen" in text
        or "inspect the live device" in text
    )
    if not requires_actual_inspection:
        return None

    if "android" in text or "emulator" in text:
        return "android"
    if "ios" in text or "simulator" in text:
        return "ios"
    return None


def preflight_maestro_device(platform: str) -> PreflightIssue | None:
    maestro = shutil.which("maestro")
    local_maestro = Path.home() / ".maestro" / "bin" / "maestro"
    if not maestro and local_maestro.exists():
        maestro = str(local_maestro)
    if not maestro:
        return PreflightIssue(
            kind="missing-maestro",
            platform=platform,
            reason="Maestro CLI was not found on PATH or at ~/.maestro/bin/maestro.",
        )

    try:
        completed = subprocess.run(
            [maestro, "--no-ansi", "list-devices", "--platform", platform],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            env={**os.environ, "MAESTRO_CLI_NO_ANALYTICS": "true"},
        )
    except subprocess.TimeoutExpired:
        return PreflightIssue(
            kind="maestro-timeout",
            platform=platform,
            reason=f"Timed out while listing {platform} devices with Maestro.",
        )
    except OSError as error:
        return PreflightIssue(
            kind="maestro-error",
            platform=platform,
            reason=f"Failed to list {platform} devices with Maestro: {error}",
        )

    output = completed.stdout or ""
    if completed.returncode != 0:
        return PreflightIssue(
            kind="maestro-error",
            platform=platform,
            reason=(
                f"Maestro list-devices --platform {platform} exited "
                f"{completed.returncode}: {compact_output(output)}"
            ),
        )
    if not maestro_output_has_devices(output, platform):
        return PreflightIssue(
            kind="missing-device",
            platform=platform,
            reason=f"No local {platform} device is visible to Maestro.",
        )
    return None


def maestro_output_has_devices(output: str, platform: str) -> bool:
    platform_headings = {"android", "ios", "web"}
    for raw_line in output.splitlines():
        if not raw_line.startswith("  "):
            continue
        stripped = raw_line.strip()
        if not stripped or stripped.lower() in platform_headings:
            continue
        if stripped.lower() == "no devices found":
            return False
        return True
    return False


def compact_output(output: str, max_chars: int = 500) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    text = " ".join(lines)
    return text[:max_chars] if text else "no output"


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
    run_id: str,
    pending_results: list[PendingResult],
    run_eval_ids: list[str] | None = None,
    run_agents: list[str] | None = None,
) -> list[dict]:
    results = [dict(item.result) for item in pending_results]
    scoring_jobs = []
    for index, item in enumerate(pending_results):
        result = results[index]
        if result.get("scoreSource"):
            continue
        if item.test_case is None:
            mark_unscored(
                result, "No judge evidence was produced for this case.", "harness"
            )
            continue
        if result.get("timedOut"):
            apply_score(
                result,
                0.0,
                "Timed out before the agent completed the task.",
                "timeout",
                passed_checks=0,
                failed_checks=max(1, len(result.get("passCriteria") or [])),
            )
            continue
        scoring_jobs.append((index, item.test_case))

    if not scoring_jobs:
        return results

    batch_size = configured_judge_batch_size(len(scoring_jobs))
    scoring_batches = (
        list(chunked(scoring_jobs, batch_size)) if batch_size else [scoring_jobs]
    )
    for scoring_batch in scoring_batches:
        try:
            judge_response = batch_judge_results(
                run_id,
                results,
                scoring_batch,
                run_eval_ids=run_eval_ids,
                run_agents=run_agents,
            )
        except Exception as error:
            reason = redact_configured_secrets(f"{type(error).__name__}: {error}")
            for result_index, _ in scoring_batch:
                mark_unscored(results[result_index], reason, "judge-error")
            for result in results:
                result.pop("_judgeResultId", None)
            continue

        apply_batch_judgement(results, scoring_batch, judge_response)
    return results


def configured_judge_batch_size(job_count: int) -> int:
    raw = os.getenv("BENCHMARK_JUDGE_BATCH_SIZE", "").strip()
    if not raw:
        return 0
    value = int(raw)
    if value <= 0 or job_count <= 0:
        return 0
    return min(value, job_count)


def chunked(items: list[tuple[int, object]], chunk_size: int):
    for index in range(0, len(items), chunk_size):
        yield items[index : index + chunk_size]


def batch_judge_results(
    run_id: str,
    results: list[dict],
    scoring_jobs: list[tuple[int, object]],
    run_eval_ids: list[str] | None = None,
    run_agents: list[str] | None = None,
) -> BatchJudgeResponse:
    judge_model = make_judge_model()
    if judge_model is None:
        raise RuntimeError(
            "No judge model is configured. Set DEEPEVAL_JUDGE_PROVIDER and the "
            "matching GOOGLE_API_KEY or OPENAI_API_KEY."
        )

    prompt = build_batch_judge_prompt(
        run_id,
        results,
        scoring_jobs,
        run_eval_ids=run_eval_ids,
        run_agents=run_agents,
    )
    response, _ = judge_model.generate(prompt, schema=BatchJudgeResponse)
    if isinstance(response, BatchJudgeResponse):
        return response
    if isinstance(response, dict):
        return BatchJudgeResponse.model_validate(response)
    return BatchJudgeResponse.model_validate_json(str(response))


def build_batch_judge_prompt(
    run_id: str,
    results: list[dict],
    scoring_jobs: list[tuple[int, object]],
    run_eval_ids: list[str] | None = None,
    run_agents: list[str] | None = None,
) -> str:
    cases = []
    char_budget = batch_case_char_budget(len(scoring_jobs))
    for ordinal, (result_index, test_case) in enumerate(scoring_jobs, start=1):
        result = results[result_index]
        result_id = f"r{ordinal:03d}"
        result["_judgeResultId"] = result_id
        cases.append(batch_case_payload(result_id, result, test_case, char_budget))

    payload = {
        "runId": run_id,
        "evalIds": run_eval_ids or [],
        "agentCount": len(run_agents or []),
        "scoringPolicy": {
            "scoreRange": "0.0 to 1.0",
            "pass": "score >= 0.70",
            "partial": "0.40 <= score < 0.70",
            "fail": "score < 0.40",
            "passedChecks": "Number of pass criteria materially satisfied.",
            "failedChecks": "Number of fail criteria triggered. Use 0 when no fail criterion was triggered.",
        },
        "cases": cases,
    }

    return (
        "You are an impartial QA benchmark judge. Score every case in the JSON payload. "
        "Use only the task, criteria, changed files, excerpts, and transcript evidence. "
        "Do not reward or penalize any agent name, vendor, model, speed, or cost. "
        "A non-zero wrapper exit code is not automatic failure if evidence proves completion. "
        "Penalize missing evidence, fabricated selectors, stale evidence, forbidden commands, "
        "irrelevant edits, destructive rewrites, and unsupported claims. "
        "Return exactly one result for every case resultId and no extra resultIds. "
        "Use result labels consistent with the score thresholds. "
        "Keep reasons short and evidence-based.\n\n" + json.dumps(payload, indent=2)
    )


def batch_case_payload(
    result_id: str, result: dict, test_case: object, char_budget: int
) -> dict:
    task_budget = max(300, char_budget // 4)
    criteria_budget = max(300, char_budget // 4)
    evidence_budget = max(400, char_budget - task_budget - criteria_budget)
    return {
        "resultId": result_id,
        "evalId": result.get("evalId"),
        "caseId": result.get("caseId"),
        "mode": result.get("mode"),
        "exitCode": result.get("exitCode"),
        "timedOut": result.get("timedOut"),
        "changedFiles": result.get("changedFiles") or [],
        "task": truncate_text(str(getattr(test_case, "input", "")), task_budget),
        "criteria": truncate_text(
            str(getattr(test_case, "expected_output", "")), criteria_budget
        ),
        "evidence": truncate_text(
            str(getattr(test_case, "actual_output", "")), evidence_budget
        ),
    }


def batch_case_char_budget(case_count: int) -> int:
    total_budget = int(os.getenv("BENCHMARK_BATCH_TOTAL_CASE_CHARS", "180000"))
    per_case_default = int(os.getenv("BENCHMARK_BATCH_CASE_CHARS", "5000"))
    if case_count <= 0:
        return per_case_default
    return max(450, min(per_case_default, total_budget // case_count))


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head - 80
    return (
        text[:head]
        + f"\n...[truncated {len(text) - max_chars} chars]...\n"
        + text[-max(0, tail) :]
    )


def apply_batch_judgement(
    results: list[dict],
    scoring_jobs: list[tuple[int, object]],
    judge_response: BatchJudgeResponse,
) -> None:
    expected_ids = {
        results[result_index].get("_judgeResultId"): result_index
        for result_index, _ in scoring_jobs
    }
    seen_ids: set[str] = set()
    for scored in judge_response.results:
        result_id = scored.resultId
        if result_id in seen_ids or result_id not in expected_ids:
            continue
        seen_ids.add(result_id)
        result = results[expected_ids[result_id]]
        score = max(0.0, min(1.0, float(scored.score)))
        normalized_result = result_label(score, False)
        apply_score(
            result,
            score,
            scored.reason.strip() or "Batch judge returned no reason.",
            "batch-judge",
            passed_checks=max(0, int(scored.passedChecks)),
            failed_checks=max(0, int(scored.failedChecks)),
            result_override=normalized_result,
        )

    for result_id, result_index in expected_ids.items():
        if result_id not in seen_ids:
            mark_unscored(
                results[result_index],
                f"Batch judge did not return a result for {result_id}.",
                "judge-error",
            )

    for result in results:
        result.pop("_judgeResultId", None)


def apply_score(
    result: dict,
    score: float,
    reason: str,
    score_source: str,
    passed_checks: int | None = None,
    failed_checks: int | None = None,
    result_override: str | None = None,
) -> None:
    result["score"] = score
    result["scorePercent"] = round(score * 100)
    result["result"] = result_override or result_label(
        score, bool(result.get("timedOut"))
    )
    result["reason"] = reason
    result["scoreSource"] = score_source
    if passed_checks is not None:
        result["passedChecks"] = passed_checks
    if failed_checks is not None:
        result["failedChecks"] = failed_checks


def mark_unscored(result: dict, reason: str, score_source: str) -> None:
    result["score"] = None
    result["scorePercent"] = None
    result["result"] = "unscored"
    result["reason"] = reason
    result["scoreSource"] = score_source
    result["passedChecks"] = None
    result["failedChecks"] = None


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
        "passedChecks": 0,
        "failedChecks": 1,
        "exitCode": 1,
        "timedOut": False,
        "durationMs": 0,
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
        "projectDir": None,
        "transcriptPath": None,
        "changedFiles": [],
        "passCriteria": fixture.pass_criteria,
        "failCriteria": fixture.fail_criteria,
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
    lines.append(
        "| Agent | Average | Scored | Pass | Partial | Fail | Blocked | Unscored | Checks Pass | Checks Fail |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for agent in agents:
        agent_results = [item for item in results if item["agent"] == agent]
        scored_results = scored_only(agent_results)
        if scored_results:
            average = round(
                sum(item["scorePercent"] for item in scored_results)
                / len(scored_results),
                1,
            )
        else:
            average = "n/a"
        pass_count = sum(1 for item in agent_results if item["result"] == "pass")
        partial_count = sum(1 for item in agent_results if item["result"] == "partial")
        fail_count = sum(1 for item in agent_results if item["result"] == "fail")
        blocked_count = sum(1 for item in agent_results if item["result"] == "blocked")
        unscored_count = sum(
            1 for item in agent_results if item["result"] == "unscored"
        )
        passed_checks = sum(
            int(item.get("passedChecks") or 0) for item in agent_results
        )
        failed_checks = sum(
            int(item.get("failedChecks") or 0) for item in agent_results
        )
        lines.append(
            f"| {agent_display_name(agent)} | {average} | {len(scored_results)} | "
            f"{pass_count} | {partial_count} | {fail_count} | {blocked_count} | "
            f"{unscored_count} | {passed_checks} | {failed_checks} |"
        )

    (results_dir / "scores.md").write_text("\n".join(lines) + "\n")
    ordered_results = order_results(eval_ids, agents, results)
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    metadata = {
        "runId": run_id,
        "generatedAt": generated_at,
        "evalIds": eval_ids,
        "agents": agents,
        "agentModels": {agent: agent_model_label(agent) for agent in agents},
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
    return {
        "total": total,
        "scored": len(scored_results),
        "averageScorePercent": average,
        "pass": sum(1 for item in results if item.get("result") == "pass"),
        "partial": sum(1 for item in results if item.get("result") == "partial"),
        "fail": sum(1 for item in results if item.get("result") == "fail"),
        "blocked": sum(1 for item in results if item.get("result") == "blocked"),
        "unscored": sum(1 for item in results if item.get("result") == "unscored"),
        "passedChecks": sum(int(item.get("passedChecks") or 0) for item in results),
        "failedChecks": sum(int(item.get("failedChecks") or 0) for item in results),
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
        "scoreSource": result.get("scoreSource"),
        "passedChecks": result.get("passedChecks"),
        "failedChecks": result.get("failedChecks"),
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


def benchmark_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else BENCHMARK_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
