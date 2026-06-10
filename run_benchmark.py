#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
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

load_dotenv(
    BENCHMARK_ROOT / ".env",
    override=os.getenv("BENCHMARK_ENV_FILE_OVERRIDE", "1") != "0",
)

from agents import (  # noqa: E402
    agent_command_env_name,
    agent_display_name,
    agent_family,
    agent_model_label,
    agent_run_dir_name,
    run_agent,
)
from fixtures import (
    copy_project,
    load_fixture,
    resolve_eval_ids,
    window_eval_ids,
)  # noqa: E402
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
DEFAULT_OVERALL_QA_WEIGHT = 0.8


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
    requested_eval_ids = os.getenv("BENCHMARK_EVAL_IDS", DEFAULT_EVAL_IDS)
    eval_ids = window_eval_ids(
        resolve_eval_ids(requested_eval_ids),
        os.getenv("BENCHMARK_EVAL_LIMIT"),
        os.getenv("BENCHMARK_EVAL_OFFSET"),
    )
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
    artifact_checks = build_artifact_checks(fixture, run)
    token_usage = build_token_usage(agent, run.transcript_path, case_run_dir)
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
        "artifactChecks": artifact_checks,
        "artifactWarnings": artifact_checks["warnings"],
        "tokenUsage": token_usage,
        "passCriteria": fixture.pass_criteria,
        "failCriteria": fixture.fail_criteria,
    }

    return PendingResult(result, make_test_case(fixture, run))


def build_artifact_checks(fixture, run) -> dict:
    changed_files = list(run.changed_files)
    transcript = run.transcript.lower()
    changed_test_files = [path for path in changed_files if is_test_file(path)]
    changed_implementation_files = [
        path for path in changed_files if is_implementation_file(path)
    ]
    changed_markdown_files = [
        path for path in changed_files if path.lower().endswith(".md")
    ]
    changed_noise_files = [path for path in changed_files if is_noise_file(path)]
    changed_relevant_files = [
        path for path in changed_files if path not in set(changed_noise_files)
    ]
    ran_verification = bool(
        re.search(
            r"\b(npx\s+playwright|playwright\s+test|npm\s+(test|run)|pnpm\s+(test|run)|yarn\s+(test|run)|vitest|cypress|wdio|maestro\s+test|pytest)\b",
            transcript,
        )
    )
    rate_limited = "rate limit" in transcript or "resource exhausted" in transcript

    warnings: list[str] = []
    if not changed_relevant_files and expects_artifact_change(fixture):
        warnings.append("expected-artifact-change-missing")
    if changed_files and not changed_relevant_files:
        warnings.append("only-noisy-files-changed")
    if fixture.mode in {"build", "fix", "test-feature"} and not ran_verification:
        if expects_verification(fixture):
            warnings.append("verification-command-not-observed")
    if rate_limited:
        warnings.append("rate-limit-observed")

    return {
        "changedFileCount": len(changed_files),
        "changedRelevantFiles": changed_relevant_files,
        "changedTestFiles": changed_test_files,
        "changedImplementationFiles": changed_implementation_files,
        "changedMarkdownFiles": changed_markdown_files,
        "changedNoiseFiles": changed_noise_files,
        "createdOrChangedSupatestMemory": ".supatest/SUPATEST.md" in changed_files,
        "ranVerificationCommand": ran_verification,
        "rateLimited": rate_limited,
        "warnings": warnings,
    }


def empty_token_usage() -> dict:
    return {
        "inputTokens": None,
        "outputTokens": None,
        "cachedInputTokens": None,
        "totalTokens": None,
        "estimatedCostUsd": None,
        "score": None,
        "scorePercent": None,
        "scoreBasis": None,
        "source": None,
        "warnings": [],
    }


def build_token_usage(agent: str, transcript_path: Path, case_run_dir: Path) -> dict:
    usage = empty_token_usage()
    sources: list[str] = []
    for source_name, path in token_usage_candidate_paths(transcript_path, case_run_dir):
        parsed = parse_token_usage_file(path)
        if not parsed:
            continue
        merge_token_usage(usage, parsed)
        sources.append(source_name)

    if usage["totalTokens"] is None:
        input_tokens = usage.get("inputTokens")
        output_tokens = usage.get("outputTokens")
        if input_tokens is not None or output_tokens is not None:
            usage["totalTokens"] = int(input_tokens or 0) + int(output_tokens or 0)

    estimated_cost = estimate_token_cost_usd(agent, usage)
    if estimated_cost is not None:
        usage["estimatedCostUsd"] = round(estimated_cost, 6)

    if sources:
        usage["source"] = ", ".join(dict.fromkeys(sources))
    if usage["totalTokens"] is None and not sources:
        usage["warnings"].append("token-usage-not-found")
    return usage


def token_usage_candidate_paths(
    transcript_path: Path, case_run_dir: Path
) -> list[tuple[str, Path]]:
    return [
        ("transcript", transcript_path),
        ("run-usage-json", case_run_dir / "usage.json"),
        ("run-token-usage-json", case_run_dir / "token-usage.json"),
        ("run-telemetry-json", case_run_dir / "telemetry.json"),
        ("project-usage-json", case_run_dir / "project" / "usage.json"),
        ("project-token-usage-json", case_run_dir / "project" / "token-usage.json"),
        ("project-telemetry-json", case_run_dir / "project" / "telemetry.json"),
        ("project-cli-log", case_run_dir / "project" / "cli.log"),
    ]


def parse_token_usage_file(path: Path) -> dict | None:
    if not path.exists() or not path.is_file():
        return None

    text = path.read_text(errors="replace")
    if len(text) > 2_000_000:
        text = text[-2_000_000:]

    usage = empty_token_usage()
    parsed_any = False

    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        try:
            parsed_json = json.loads(stripped)
        except json.JSONDecodeError:
            parsed_json = None
        if parsed_json is not None:
            parsed_any = merge_token_usage(usage, parse_token_usage_json(parsed_json))

    parsed_any = merge_token_usage(usage, parse_token_usage_text(text)) or parsed_any
    return usage if parsed_any else None


def parse_token_usage_json(value) -> dict:
    usage = empty_token_usage()

    def walk(item, in_usage: bool = False) -> None:
        if isinstance(item, dict):
            for raw_key, raw_value in item.items():
                key = normalize_usage_key(str(raw_key))
                next_in_usage = in_usage or key in {"usage", "tokenusage", "tokens"}
                assign_json_usage_value(usage, key, raw_value, next_in_usage)
                walk(raw_value, next_in_usage)
        elif isinstance(item, list):
            for child in item:
                walk(child, in_usage)

    walk(value)
    return usage


def assign_json_usage_value(
    usage: dict, key: str, raw_value, in_usage: bool = False
) -> None:
    number = parse_numeric_value(raw_value)
    if number is None:
        return

    if key in {
        "prompttokens",
        "prompttoken",
        "inputtokens",
        "inputtoken",
    } or (in_usage and key in {"prompt", "input"}):
        set_max_usage_value(usage, "inputTokens", int(number))
    elif key in {
        "completiontokens",
        "completiontoken",
        "outputtokens",
        "outputtoken",
        "responsetokens",
    } or (in_usage and key in {"completion", "output", "response"}):
        set_max_usage_value(usage, "outputTokens", int(number))
    elif key in {
        "cachedtokens",
        "cachedinputtokens",
        "cacheinputtokens",
        "cachereadinputtokens",
        "cachecreationinputtokens",
        "cachedprompttokens",
    }:
        set_max_usage_value(usage, "cachedInputTokens", int(number))
    elif key in {
        "totaltokens",
        "totaltoken",
        "tokensused",
        "tokencount",
    } or (in_usage and key == "total"):
        set_max_usage_value(usage, "totalTokens", int(number))
    elif key in {
        "costusd",
        "estimatedcostusd",
        "totalcostusd",
        "totalcost",
        "evaluationcost",
    }:
        set_max_usage_value(usage, "estimatedCostUsd", float(number))


def parse_token_usage_text(text: str) -> dict:
    text = re.sub(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)
    usage = empty_token_usage()

    for match in re.finditer(
        r"(?is)\btokens\s+used\s*[\r\n]+[\s`$>]*([0-9][0-9,]*(?:\.[0-9]+)?)",
        text,
    ):
        set_max_usage_value(usage, "totalTokens", int(parse_usage_number(match[1])))

    labeled_patterns = [
        (
            r"(?i)\b(prompt|input|completion|output|response|total|cached|cached\s+input|cache\s+read\s+input|cache\s+creation\s+input)\s+tokens?\s*[:=]\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            1,
            2,
        ),
        (
            r"(?i)[\"']?\b(prompt_tokens|input_tokens|completion_tokens|output_tokens|response_tokens|total_tokens|cached_tokens|cached_input_tokens|cache_read_input_tokens|cache_creation_input_tokens)\b[\"']?\s*[:=]\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            1,
            2,
        ),
        (
            r"(?i)\b([0-9][0-9,]*(?:\.[0-9]+)?)\s+(prompt|input|completion|output|response|total|cached|cached\s+input)\s+tokens?\b",
            2,
            1,
        ),
    ]
    for pattern, label_group, value_group in labeled_patterns:
        for match in re.finditer(pattern, text):
            field = token_usage_field_for_label(match[label_group])
            if not field:
                continue
            set_max_usage_value(
                usage, field, int(parse_usage_number(match[value_group]))
            )

    for match in re.finditer(
        r"(?i)\b(?:estimated\s+)?(?:total\s+)?cost(?:\s+usd|\s*\(usd\))?\s*[:=]\s*\$?\s*([0-9]+(?:\.[0-9]+)?)",
        text,
    ):
        set_max_usage_value(usage, "estimatedCostUsd", float(match[1]))

    return usage


def token_usage_field_for_label(label: str) -> str | None:
    normalized = normalize_usage_key(label)
    if normalized in {"prompt", "prompttokens", "input", "inputtokens"}:
        return "inputTokens"
    if normalized in {
        "completion",
        "completiontokens",
        "output",
        "outputtokens",
        "response",
        "responsetokens",
    }:
        return "outputTokens"
    if normalized in {
        "cached",
        "cachedtokens",
        "cachedinput",
        "cachedinputtokens",
        "cachereadinput",
        "cachereadinputtokens",
        "cachecreationinput",
        "cachecreationinputtokens",
    }:
        return "cachedInputTokens"
    if normalized in {"total", "totaltokens"}:
        return "totalTokens"
    return None


def normalize_usage_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def parse_numeric_value(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and re.fullmatch(
        r"\$?\s*[0-9][0-9,]*(?:\.[0-9]+)?", value.strip()
    ):
        return parse_usage_number(value)
    return None


def parse_usage_number(value: str) -> float:
    return float(value.strip().lstrip("$").replace(",", ""))


def merge_token_usage(target: dict, source: dict | None) -> bool:
    if not source:
        return False

    changed = False
    for field in (
        "inputTokens",
        "outputTokens",
        "cachedInputTokens",
        "totalTokens",
        "estimatedCostUsd",
    ):
        value = source.get(field)
        if value is None:
            continue
        changed = set_max_usage_value(target, field, value) or changed
    return changed


def set_max_usage_value(usage: dict, field: str, value: int | float) -> bool:
    current = usage.get(field)
    if current is None or value > current:
        usage[field] = value
        return True
    return False


def estimate_token_cost_usd(agent: str, usage: dict) -> float | None:
    reported_cost = usage.get("estimatedCostUsd")
    if reported_cost is not None:
        return float(reported_cost)

    total_rate = token_price_rate(agent, "TOTAL")
    total_tokens = usage.get("totalTokens")
    if total_rate is not None and total_tokens is not None:
        return (float(total_tokens) / 1_000_000) * total_rate

    cost = 0.0
    has_rate = False
    for usage_field, rate_field in (
        ("inputTokens", "INPUT"),
        ("outputTokens", "OUTPUT"),
        ("cachedInputTokens", "CACHED_INPUT"),
    ):
        rate = token_price_rate(agent, rate_field)
        tokens = usage.get(usage_field)
        if rate is None or tokens is None:
            continue
        has_rate = True
        cost += (float(tokens) / 1_000_000) * rate
    return cost if has_rate else None


def token_price_rate(agent: str, field: str) -> float | None:
    env_names = [agent_command_env_name(agent)]
    family_env = agent_command_env_name(agent_family(agent))
    if family_env not in env_names:
        env_names.append(family_env)

    for env_name in env_names:
        raw = os.getenv(f"BENCHMARK_TOKEN_PRICE_{env_name}_{field}_PER_1M")
        if raw:
            return float(raw)
    return None


def apply_token_efficiency_scores(results: list[dict]) -> None:
    by_eval: dict[str, list[dict]] = {}
    for result in results:
        by_eval.setdefault(result.get("evalId", ""), []).append(result)

    for eval_results in by_eval.values():
        known = [
            result
            for result in eval_results
            if token_total(result.get("tokenUsage")) is not None
        ]
        if not known:
            continue

        best_total = min(token_total(result.get("tokenUsage")) for result in known)
        if not best_total or best_total <= 0:
            continue

        for result in known:
            usage = result.setdefault("tokenUsage", empty_token_usage())
            total = token_total(usage)
            if not total or total <= 0:
                continue
            score = min(1.0, best_total / total)
            usage["score"] = round(score, 4)
            usage["scorePercent"] = round(score * 100)
            usage["scoreBasis"] = "relative-total-tokens-per-eval"


def token_total(usage: dict | None) -> int | None:
    if not usage:
        return None
    total = usage.get("totalTokens")
    return int(total) if total is not None else None


def apply_overall_scores(results: list[dict]) -> None:
    weights = overall_score_weights()
    for result in results:
        qa_score = result.get("scorePercent")
        token_score = (result.get("tokenUsage") or {}).get("scorePercent")
        if qa_score is None or token_score is None:
            result["overallScore"] = None
            result["overallScorePercent"] = None
            result["overallScoreSource"] = None
            continue

        overall_percent = (
            float(qa_score) * weights["qa"]
            + float(token_score) * weights["tokenUsage"]
        )
        result["overallScorePercent"] = round(overall_percent, 1)
        result["overallScore"] = round(overall_percent / 100, 4)
        result["overallScoreSource"] = "weighted-qa-token"


def overall_score_weights() -> dict[str, float]:
    qa_weight = configured_overall_qa_weight()
    return {
        "qa": qa_weight,
        "tokenUsage": round(1.0 - qa_weight, 4),
    }


def configured_overall_qa_weight() -> float:
    raw = os.getenv(
        "BENCHMARK_OVERALL_QA_WEIGHT", str(DEFAULT_OVERALL_QA_WEIGHT)
    ).strip()
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError(
            "BENCHMARK_OVERALL_QA_WEIGHT must be between 0 and 1."
        ) from error
    if value < 0 or value > 1:
        raise ValueError("BENCHMARK_OVERALL_QA_WEIGHT must be between 0 and 1.")
    return value


def is_test_file(path: str) -> bool:
    lower = path.lower()
    return (
        lower.endswith((".spec.ts", ".spec.tsx", ".spec.js", ".cy.ts", ".cy.js"))
        or lower.startswith(("tests/", "test/", "test/specs/", "cypress/e2e/", "e2e/"))
        or "/tests/" in lower
        or "/test/specs/" in lower
    )


def is_implementation_file(path: str) -> bool:
    lower = path.lower()
    if is_test_file(path) or is_noise_file(path):
        return False
    return lower.endswith((".ts", ".tsx", ".js", ".jsx", ".py")) and lower.startswith(
        ("pages/", "src/", "lib/", "app/", "utils/", "cypress/pages/", "test/specs/")
    )


def is_noise_file(path: str) -> bool:
    lower = path.lower()
    name = Path(path).name.lower()
    return (
        name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "cli.log"}
        or lower.endswith(".log")
        or lower.startswith(("node_modules/", "playwright-report/", "test-results/"))
    )


def expects_artifact_change(fixture) -> bool:
    text = fixture_expectation_text(fixture)
    if any(
        phrase in text
        for phrase in (
            "do not create files",
            "does not create files",
            "before answering",
            "selector table",
            "root cause",
            "read-only",
        )
    ):
        return False
    if fixture.mode in {"build", "fix", "plan", "report", "test-feature"}:
        return True
    return any(
        phrase in text
        for phrase in (
            "write tests",
            "writes",
            "produces",
            "fix ",
            "fixes",
            "edit ",
            "create ",
            "adds ",
        )
    )


def expects_verification(fixture) -> bool:
    text = fixture_expectation_text(fixture)
    if "do not run" in text or "does not run" in text or "authoring only" in text:
        return False
    if fixture.mode in {"plan", "report"}:
        return False
    return True


def fixture_expectation_text(fixture) -> str:
    return "\n".join(
        [
            fixture.task,
            "\n".join(fixture.pass_criteria),
            "\n".join(fixture.fail_criteria),
        ]
    ).lower()


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
    return parse_batch_judge_response(response)


def parse_batch_judge_response(response) -> BatchJudgeResponse:
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
        "irrelevant edits, destructive rewrites, trivial assertions such as expect(true), "
        "assertion weakening, over-mocking the behavior under test, and unsupported claims. "
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
        "artifactChecks": result.get("artifactChecks") or {},
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
        "tokenUsage": empty_token_usage(),
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
    apply_token_efficiency_scores(results)
    apply_overall_scores(results)
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
        "| Agent | Overall | QA Avg | Token Avg | Scored | Overall Scored | Token Known | Pass | Partial | Fail | Blocked | Unscored | Token Usage | Cost USD | Checks Pass | Checks Fail |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    for agent in agents:
        agent_results = [item for item in results if item["agent"] == agent]
        scored_results = scored_only(agent_results)
        token_summary = summarize_token_usage(agent_results)
        overall_summary = summarize_overall_score(agent_results)
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
            f"| {agent_display_name(agent)} | "
            f"{format_optional_number(overall_summary['scorePercent'])} | "
            f"{average} | "
            f"{format_optional_number(token_summary['scorePercent'])} | "
            f"{len(scored_results)} | {overall_summary['scored']} | "
            f"{token_summary['known']} | "
            f"{pass_count} | {partial_count} | {fail_count} | {blocked_count} | "
            f"{unscored_count} | {format_token_count(token_summary['totalTokens'])} | "
            f"{format_cost_usd(token_summary['estimatedCostUsd'])} | "
            f"{passed_checks} | {failed_checks} |"
        )

    (results_dir / "scores.md").write_text("\n".join(lines) + "\n")
    ordered_results = order_results(eval_ids, agents, results)
    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    weights = overall_score_weights()
    metadata = {
        "runId": run_id,
        "generatedAt": generated_at,
        "evalIds": eval_ids,
        "evalSelection": {
            "requested": os.getenv("BENCHMARK_EVAL_IDS", DEFAULT_EVAL_IDS),
            "limit": os.getenv("BENCHMARK_EVAL_LIMIT", "all") or "all",
            "offset": int(os.getenv("BENCHMARK_EVAL_OFFSET", "0") or "0"),
        },
        "agents": agents,
        "agentModels": {agent: agent_model_label(agent) for agent in agents},
        "parallelism": parallelism,
        "timeoutSeconds": timeout_seconds,
        "tokenScoring": {
            "scoreRange": "0 to 100",
            "basis": "relative total tokens per eval; lowest known token total gets 100",
            "unknownUsage": "left unscored",
            "cost": "reported by agent logs or estimated only when BENCHMARK_TOKEN_PRICE_* env vars are set",
        },
        "overallScoring": {
            "scoreRange": "0 to 100",
            "qaWeight": weights["qa"],
            "tokenUsageWeight": weights["tokenUsage"],
            "formula": "qaScorePercent * qaWeight + tokenUsage.scorePercent * tokenUsageWeight",
            "unknownTokenUsage": "overallScorePercent is null when token usage score is unavailable",
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
    overall_score = summarize_overall_score(results)
    return {
        "total": total,
        "scored": len(scored_results),
        "averageScorePercent": average,
        "overallScorePercent": overall_score["scorePercent"],
        "overallScored": overall_score["scored"],
        "tokenUsage": token_usage,
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
    }


def summarize_overall_score(results: list[dict]) -> dict:
    scored = [
        result
        for result in results
        if result.get("overallScorePercent") is not None
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
    known = [result for result in results if token_total(result.get("tokenUsage"))]
    if not known:
        return {
            "known": 0,
            "scorePercent": None,
            "totalTokens": None,
            "inputTokens": None,
            "outputTokens": None,
            "cachedInputTokens": None,
            "estimatedCostUsd": None,
        }

    scored = [
        result
        for result in known
        if (result.get("tokenUsage") or {}).get("scorePercent") is not None
    ]
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
        "totalTokens": sum(
            int((result.get("tokenUsage") or {}).get("totalTokens") or 0)
            for result in known
        ),
        "inputTokens": sum(
            int((result.get("tokenUsage") or {}).get("inputTokens") or 0)
            for result in known
        ),
        "outputTokens": sum(
            int((result.get("tokenUsage") or {}).get("outputTokens") or 0)
            for result in known
        ),
        "cachedInputTokens": sum(
            int((result.get("tokenUsage") or {}).get("cachedInputTokens") or 0)
            for result in known
        ),
        "estimatedCostUsd": (
            round(sum(float(value) for value in costs), 6) if costs else None
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


def benchmark_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else BENCHMARK_ROOT / path


if __name__ == "__main__":
    raise SystemExit(main())
