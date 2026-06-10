from __future__ import annotations

import json
import os
from types import SimpleNamespace

from deepeval.test_case import LLMTestCase

from agents import (
    agent_command_env_name,
    agent_display_name,
    agent_environment,
    agent_family,
    agent_model,
    agent_model_label,
    agent_run_dir_name,
    agent_stdin_input,
    build_command,
    build_prompt,
    changed_file_excerpt,
    resolve_supatest_project_id,
    with_local_tool_paths,
)
from fixtures import (
    available_eval_ids,
    copy_project,
    load_fixture,
    resolve_eval_ids,
    window_eval_ids,
)
import run_benchmark
from run_benchmark import (
    BatchJudgeCaseScore,
    BatchJudgeResponse,
    PreflightIssue,
    build_token_usage,
    build_artifact_checks,
    format_score_line,
    maestro_output_has_devices,
    parse_token_usage_json,
    parse_token_usage_text,
    preflight_judge_model,
    required_live_device_platform,
    write_blocked_result,
    write_summary,
)
from scoring import (
    apply_token_efficiency_scores,
    cleaned_transcript,
    make_metric,
    make_test_case,
)
import scoring


def test_agent_environment_hides_benchmark_and_judge_vars(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_EVAL_IDS", "E25")
    monkeypatch.setenv("DEEPEVAL_GEMINI_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("GOOGLE_API_KEY", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("SUPATEST_API_KEY", "supatest-secret")
    monkeypatch.setenv("SUPATEST_PROJECT_ID", "aiden")

    env = agent_environment()

    assert "BENCHMARK_EVAL_IDS" not in env
    assert "DEEPEVAL_GEMINI_MODEL" not in env
    assert "GOOGLE_API_KEY" not in env
    assert "OPENAI_API_KEY" not in env
    assert "SUPATEST_API_KEY" not in env
    assert "SUPATEST_PROJECT_ID" not in env
    assert env["NODE_ENV"] == "development"


def test_local_mobile_tool_paths_are_added_when_present(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    maestro_bin = home / ".maestro" / "bin"
    maestro_bin.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    path = with_local_tool_paths(os.pathsep.join(["/usr/bin", "/bin"]))

    assert path.split(os.pathsep)[0] == str(maestro_bin)


def test_agent_command_env_name_supports_future_agent_names() -> None:
    assert agent_command_env_name("qa-pro") == "QA_PRO"
    assert agent_command_env_name("vendor.agent/v2") == "VENDOR_AGENT_V2"


def test_agent_family_and_run_dir_support_inline_model_variants() -> None:
    assert agent_family("codex:gpt-5") == "codex"
    assert agent_model("codex:gpt-5") == "gpt-5"
    assert agent_run_dir_name("codex:gpt-5/fast") == "codex-gpt-5-fast"
    assert agent_display_name("codex:gpt-5") == "codex [gpt-5]"


def test_agent_model_labels_use_agent_specific_config(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_SUPATEST_MODEL", "premium")
    monkeypatch.setenv(
        "BENCHMARK_CURSOR_CMD",
        "cursor-agent --print --force --model auto {prompt}",
    )
    monkeypatch.setenv(
        "BENCHMARK_GEMINI_CMD",
        "gemini --model gemini-3.1-flash-lite --prompt {prompt} --yolo",
    )

    assert agent_model_label("supatest") == "premium"
    assert agent_model_label("cursor") == "auto"
    assert agent_model_label("gemini") == "gemini-3.1-flash-lite"
    assert agent_display_name("supatest") == "supatest [premium]"


def test_inline_agent_model_overrides_family_model_default(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_CODEX_MODEL", "family-default")

    assert agent_model("codex:gpt-5") == "gpt-5"
    assert agent_model_label("codex:gpt-5") == "gpt-5"

    monkeypatch.setenv("BENCHMARK_CODEX_GPT_5_MODEL", "id-specific")

    assert agent_model("codex:gpt-5") == "id-specific"
    assert agent_model_label("codex:gpt-5") == "id-specific"


def test_gemini_agent_command_uses_configured_template(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "BENCHMARK_GEMINI_CMD",
        "gemini --model gemini-3.1-flash-lite --prompt {prompt} --yolo --skip-trust",
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    command, cwd, use_shell = build_command("gemini", load_fixture("E25"), project_dir)

    assert use_shell is True
    assert cwd == project_dir
    assert command.startswith("gemini --model gemini-3.1-flash-lite --prompt ")
    assert "--yolo --skip-trust" in command


def test_built_in_gemini_command_uses_model_env(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BENCHMARK_GEMINI_CMD", raising=False)
    monkeypatch.setenv("BENCHMARK_GEMINI_MODEL", "gemini-2.5-pro")
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    command, cwd, use_shell = build_command("gemini", load_fixture("E25"), project_dir)

    assert use_shell is True
    assert cwd == project_dir
    assert command.startswith("gemini --model gemini-2.5-pro --prompt ")
    assert "--output-format stream-json" in command


def test_built_in_cursor_command_uses_stream_json_output(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BENCHMARK_CURSOR_CMD", raising=False)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    command, cwd, use_shell = build_command("cursor", load_fixture("E25"), project_dir)

    assert use_shell is True
    assert cwd == project_dir
    assert "--output-format stream-json" in command


def test_cursor_agent_command_uses_auto_model(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "BENCHMARK_CURSOR_CMD",
        "cursor-agent --print --force --model auto {prompt}",
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    command, cwd, use_shell = build_command("cursor", load_fixture("E25"), project_dir)

    assert use_shell is True
    assert cwd == project_dir
    assert "--model auto" in command


def test_codex_model_arg_placeholder_is_empty_until_configured(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("BENCHMARK_CODEX_CMD", raising=False)
    monkeypatch.delenv("BENCHMARK_CODEX_MODEL", raising=False)
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    command, _, _ = build_command("codex", load_fixture("E25"), project_dir)

    assert "--model" not in command

    command, _, _ = build_command("codex:gpt-5", load_fixture("E25"), project_dir)

    assert "--model gpt-5" in command


def test_generic_agent_command_can_render_model_placeholders(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv(
        "BENCHMARK_QA_PRO_CMD",
        "qa-pro run --model {model} {model_arg} --cwd {cwd} {prompt}",
    )
    monkeypatch.setenv("BENCHMARK_QA_PRO_MODEL", "qa-large")
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    command, cwd, use_shell = build_command("qa-pro", load_fixture("E25"), project_dir)

    assert use_shell is True
    assert cwd == project_dir
    assert "--model qa-large --model qa-large" in command
    assert f"--cwd {project_dir}" in command


def test_supatest_project_id_uses_explicit_or_benchmark_settings(monkeypatch) -> None:
    monkeypatch.delenv("BENCHMARK_SUPATEST_PROJECT_ID", raising=False)
    monkeypatch.setenv("SUPATEST_PROJECT_ID", "global-env-should-not-leak")

    assert resolve_supatest_project_id() == "aiden"

    monkeypatch.setenv("BENCHMARK_SUPATEST_PROJECT_ID", "benchmark-project")

    assert resolve_supatest_project_id() == "benchmark-project"


def test_benchmark_prompt_frames_real_qa_without_exposing_rubric(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_PROMPT_PROFILE", "qa")
    fixture = load_fixture("E25")

    prompt = build_prompt(fixture)

    assert "real production QA work" in prompt
    assert "User request:" in prompt
    assert fixture.task in prompt
    assert "passCriteria" not in prompt
    assert "failCriteria" not in prompt


def test_prompt_profile_can_remove_shared_qa_coaching(monkeypatch) -> None:
    fixture = load_fixture("E25")
    monkeypatch.setenv("BENCHMARK_PROMPT_PROFILE", "raw")

    prompt = build_prompt(fixture)

    assert prompt.startswith(fixture.task)
    assert "real production QA work" not in prompt
    assert "User request:" not in prompt

    monkeypatch.setenv("BENCHMARK_PROMPT_PROFILE", "minimal")

    prompt = build_prompt(fixture)

    assert "User request:" in prompt
    assert "real production QA work" not in prompt
    assert f"Mode: {fixture.mode}" in prompt


def test_supatest_receives_same_benchmark_prompt(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_PROMPT_PROFILE", "qa")
    monkeypatch.setenv("BENCHMARK_SUPATEST_PROJECT_ID", "benchmark-project")
    monkeypatch.delenv("BENCHMARK_SUPATEST_API_KEY", raising=False)
    monkeypatch.delenv("SUPATEST_API_KEY", raising=False)
    monkeypatch.delenv("BENCHMARK_SUPATEST_MODEL", raising=False)
    monkeypatch.delenv("BENCHMARK_SUPATEST_MACHINE_MODE", raising=False)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    fixture = load_fixture("E25")

    command, cwd, use_shell = build_command("supatest", fixture, project_dir)
    stdin_input = agent_stdin_input("supatest", fixture)

    assert use_shell is False
    assert cwd == project_dir
    assert "--output-format" in command
    assert command[command.index("--output-format") + 1] == "stream-json"
    assert "--input-format" in command
    assert command[command.index("--input-format") + 1] == "stream-json"
    assert build_prompt(fixture) not in command
    assert stdin_input is not None
    assert "real production QA work" in stdin_input
    assert command[command.index("--model") + 1] == "premium"
    assert command[command.index("--project-id") + 1] == "benchmark-project"
    assert "--supatest-api-key" not in command


def test_resolve_eval_ids_all_uses_every_available_fixture() -> None:
    eval_ids = resolve_eval_ids("all")

    assert eval_ids == available_eval_ids()
    assert "E18" in eval_ids
    assert "E101" in eval_ids


def test_copy_project_does_not_mount_fixture_root_answer_files(tmp_path) -> None:
    fixture = load_fixture("E75")
    assert (fixture.fixture_dir / "solution.md").exists()

    copied = copy_project(fixture, tmp_path)

    assert copied == tmp_path / "project"
    assert not (copied / "solution.md").exists()


def test_window_eval_ids_supports_limit_and_offset() -> None:
    eval_ids = ["E1", "E2", "E3", "E4", "E5", "E6"]

    assert window_eval_ids(eval_ids, "5", None) == ["E1", "E2", "E3", "E4", "E5"]
    assert window_eval_ids(eval_ids, "10", None) == eval_ids
    assert window_eval_ids(eval_ids, "all", "2") == ["E3", "E4", "E5", "E6"]
    assert window_eval_ids(eval_ids, "2", "2") == ["E3", "E4"]


def test_changed_file_excerpt_prioritizes_tests_and_skips_noise(tmp_path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "pages").mkdir()
    (tmp_path / ".supatest").mkdir()
    (tmp_path / "tests" / "error-users.spec.ts").write_text("test('covers users')\n")
    (tmp_path / "pages" / "InventoryPage.ts").write_text(
        "export class InventoryPage {}\n"
    )
    (tmp_path / ".supatest" / "SUPATEST.md").write_text("local notes\n")
    (tmp_path / "cli.log").write_text("very noisy\n")
    (tmp_path / "package-lock.json").write_text("{}\n")

    excerpt = changed_file_excerpt(
        tmp_path,
        [
            ".supatest/SUPATEST.md",
            "cli.log",
            "package-lock.json",
            "pages/InventoryPage.ts",
            "tests/error-users.spec.ts",
        ],
    )

    assert excerpt.index("--- tests/error-users.spec.ts ---") < excerpt.index(
        "--- pages/InventoryPage.ts ---"
    )
    assert "cli.log" not in excerpt
    assert "package-lock.json" not in excerpt


def test_artifact_checks_detect_created_tests_and_verification() -> None:
    fixture = load_fixture("E3")
    run = SimpleNamespace(
        changed_files=[
            ".supatest/SUPATEST.md",
            "package-lock.json",
            "tests/cart-removal.spec.ts",
        ],
        transcript="npx playwright test tests/cart-removal.spec.ts --reporter=list",
    )

    checks = build_artifact_checks(fixture, run)

    assert checks["changedTestFiles"] == ["tests/cart-removal.spec.ts"]
    assert checks["createdOrChangedSupatestMemory"] is True
    assert checks["ranVerificationCommand"] is True
    assert checks["warnings"] == []


def test_artifact_checks_warn_when_build_only_changes_noise() -> None:
    fixture = load_fixture("E7")
    run = SimpleNamespace(
        changed_files=["package-lock.json"],
        transcript="Rate limit exceeded before writing files",
    )

    checks = build_artifact_checks(fixture, run)

    assert checks["changedRelevantFiles"] == []
    assert "only-noisy-files-changed" in checks["warnings"]
    assert "expected-artifact-change-missing" in checks["warnings"]
    assert "verification-command-not-observed" in checks["warnings"]
    assert "rate-limit-observed" in checks["warnings"]


def test_artifact_checks_do_not_require_files_for_plan_mode() -> None:
    fixture = load_fixture("E31")
    run = SimpleNamespace(
        changed_files=[],
        transcript="Here is the test plan.\n\n## Not Testing\n- External links: low risk.",
    )

    checks = build_artifact_checks(fixture, run)

    assert checks["changedRelevantFiles"] == []
    assert checks["warnings"] == []


def test_artifact_checks_still_require_report_artifacts() -> None:
    fixture = load_fixture("E61")
    run = SimpleNamespace(changed_files=[], transcript="Here is the report.")

    checks = build_artifact_checks(fixture, run)

    assert "expected-artifact-change-missing" in checks["warnings"]


def test_token_usage_parser_reads_codex_footer() -> None:
    usage = parse_token_usage_text(
        'done\n"input_tokens": 1000\n"output_tokens": 200\n\ntokens used\n77,461\n'
    )

    assert usage["inputTokens"] == 1000
    assert usage["outputTokens"] == 200
    assert usage["totalTokens"] == 77461


def test_token_usage_parser_reads_plain_text_supatest_counters() -> None:
    usage = parse_token_usage_text(
        "final answer\nTokens Used: 12,345\nTotal Cost USD: $0.1234\n"
    )

    assert usage["totalTokens"] == 12345
    assert usage["estimatedCostUsd"] == 0.1234


def test_token_usage_parser_reads_gemini_usage_metadata() -> None:
    usage = parse_token_usage_json(
        {
            "response": {
                "usage_metadata": {
                    "prompt_token_count": 1000,
                    "candidates_token_count": 250,
                    "total_token_count": 1250,
                }
            }
        }
    )

    assert usage["inputTokens"] == 1000
    assert usage["outputTokens"] == 250
    assert usage["totalTokens"] == 1250


def test_build_token_usage_reads_supatest_stream_json_result(tmp_path) -> None:
    transcript = tmp_path / "transcript.log"
    transcript.write_text(
        "\n".join(
            [
                "working",
                json.dumps(
                    {
                        "type": "result",
                        "total_cost_usd": 0.0123,
                        "usage": {
                            "input_tokens": 1000,
                            "output_tokens": 200,
                            "cache_read_input_tokens": 300,
                        },
                    }
                ),
            ]
        )
    )

    usage = build_token_usage("supatest", transcript, tmp_path)

    assert usage["inputTokens"] == 1000
    assert usage["outputTokens"] == 200
    assert usage["cachedInputTokens"] == 300
    assert usage["totalTokens"] == 1200
    assert usage["estimatedCostUsd"] == 0.0123
    assert usage["source"] == "transcript"


def test_build_token_usage_reads_json_and_estimates_cost(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_TOKEN_PRICE_CODEX_INPUT_PER_1M", "2")
    monkeypatch.setenv("BENCHMARK_TOKEN_PRICE_CODEX_OUTPUT_PER_1M", "10")
    transcript = tmp_path / "transcript.log"
    transcript.write_text("no usage footer\n")
    (tmp_path / "usage.json").write_text(
        json.dumps(
            {
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 200,
                    "total_tokens": 1200,
                }
            }
        )
    )

    usage = build_token_usage("codex:gpt-5.5", transcript, tmp_path)

    assert usage["inputTokens"] == 1000
    assert usage["outputTokens"] == 200
    assert usage["totalTokens"] == 1200
    assert usage["estimatedCostUsd"] == 0.004
    assert usage["source"] == "run-usage-json"


def test_make_test_case_anonymizes_agent_identity_paths_and_tokens(tmp_path) -> None:
    project_dir = tmp_path / "case-001" / "supatest" / "project"
    project_dir.mkdir(parents=True)
    transcript_path = project_dir.parent / "transcript.log"
    run = SimpleNamespace(
        agent="supatest",
        exit_code=0,
        timed_out=False,
        changed_files=["tests/error-users.spec.ts", ".supatest/SUPATEST.md"],
        changed_file_excerpt=(
            f"--- tests/error-users.spec.ts ---\n"
            f"test('locked_out_user', async () => {{}});\n"
            f"--- .supatest/SUPATEST.md ---\n"
            f"Notes from {project_dir} with cli_1234567890abcdefghijklmnop\n"
        ),
        transcript=(
            f" ● Command(npx playwright test {project_dir}/tests/error-users.spec.ts "
            f"--supatest-api-key cli_1234567890abcdefghijklmnop)"
        ),
        project_dir=project_dir,
        transcript_path=transcript_path,
    )

    test_case = make_test_case(
        load_fixture("E25"),
        run,
        f"--- a/tests/error-users.spec.ts\n+++ b/tests/error-users.spec.ts\n+// {project_dir}\n",
    )

    assert "Agent:" not in test_case.actual_output
    assert "supatest" not in test_case.actual_output.lower()
    assert str(tmp_path) not in test_case.actual_output
    assert "cli_1234567890abcdefghijklmnop" not in test_case.actual_output
    assert "Changed diff:" in test_case.actual_output
    assert "<project>/tests/error-users.spec.ts" in test_case.actual_output
    assert "<redacted-token>" in test_case.actual_output


def test_cleaned_transcript_collapses_terminal_status_redraws() -> None:
    raw = "\x1b[2K\r ⠋ Processing...\n" + "\n".join(
        [
            f"progress {index}\n"
            " ● Command(npx playwright test tests/error-users.spec.ts --reporter=list)"
            for index in range(25)
        ]
    )

    cleaned = cleaned_transcript(raw)

    retained_command_lines = [
        line for line in cleaned.splitlines() if line.strip().startswith("● Command(")
    ]
    assert len(retained_command_lines) == 1
    assert "suppressed 24 repeated terminal status lines" in cleaned
    assert "Processing" not in cleaned


def test_timeout_metric_is_a_hard_failure_without_judge_call() -> None:
    metric = make_metric()
    score = metric.measure(
        LLMTestCase(
            input="Finish the QA task",
            actual_output="Exit code: 124\nTimed out: True",
            expected_output="Pass criteria:\n- Complete the task",
        )
    )

    assert score == 0.0
    assert metric.reason == "Timed out before the agent completed the task."
    assert metric.is_successful() is False


def test_metric_uses_granular_qa_rubric() -> None:
    metric = make_metric()

    rubric = metric._judge.rubric

    assert [item.score_range for item in rubric] == [
        (0, 0),
        (1, 3),
        (4, 6),
        (7, 8),
        (9, 10),
    ]
    assert "Production-quality completion" in rubric[-1].expected_outcome
    assert metric._judge.evaluation_steps
    assert "Check the task" in metric._judge.evaluation_steps[0]


def test_judge_model_can_use_openai_provider(monkeypatch) -> None:
    created = {}

    class FakeGPTModel:
        def __init__(self, **kwargs):
            created.update(kwargs)

    monkeypatch.setenv("DEEPEVAL_JUDGE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("DEEPEVAL_OPENAI_MODEL", "gpt-5-nano")
    monkeypatch.setattr(scoring, "GPTModel", FakeGPTModel)

    judge = scoring.make_judge_model()

    assert isinstance(judge, FakeGPTModel)
    assert created["model"] == "gpt-5-nano"
    assert created["api_key"] == "openai-secret"
    assert created["temperature"] == 0


def test_write_summary_emits_only_three_result_files(tmp_path) -> None:
    result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E25",
        "evalName": "Batch Tests Before Running",
        "agent": "supatest",
        "mode": "build",
        "score": 1.0,
        "scorePercent": 100,
        "result": "pass",
        "reason": "ok",
        "scoreSource": "judge",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 123,
        "projectDir": "runs/verify/case-001/supatest/project",
        "transcriptPath": "runs/verify/case-001/supatest/transcript.log",
        "changedFiles": ["tests/error-users.spec.ts"],
        "passCriteria": [],
        "failCriteria": [],
    }

    write_summary(tmp_path, "verify", ["E25"], ["supatest"], 1, 600, [result])

    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "run.json",
        "scores.md",
        "summary.json",
    ]
    summary = json.loads((tmp_path / "summary.json").read_text())
    run = json.loads((tmp_path / "run.json").read_text())
    scores = (tmp_path / "scores.md").read_text()
    assert "supatest [premium]" in scores
    assert summary["agentModels"]["supatest"] == "premium"
    assert summary["summary"]["byAgent"]["supatest"]["pass"] == 1
    assert (
        summary["summary"]["byAgent"]["supatest"]["tokenUsage"]["scorePercent"] == 0.0
    )
    assert summary["summary"]["byAgent"]["supatest"]["overallScorePercent"] == 80.0
    assert run["runsByEval"]["E25"]["supatest"]["caseId"] == "case-001"
    assert run["runsByEval"]["E25"]["supatest"]["tokenUsage"]["scorePercent"] == 0.0
    assert run["runsByEval"]["E25"]["supatest"]["overallScorePercent"] == 80.0


def test_write_summary_includes_relative_token_efficiency_and_overall_score(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("BENCHMARK_OVERALL_QA_WEIGHT", "0.8")
    base_result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E25",
        "evalName": "Batch Tests Before Running",
        "mode": "build",
        "score": 1.0,
        "scorePercent": 100,
        "result": "pass",
        "reason": "ok",
        "scoreSource": "judge",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 123,
        "projectDir": "runs/verify/case-001/agent/project",
        "transcriptPath": "runs/verify/case-001/agent/transcript.log",
        "changedFiles": ["tests/error-users.spec.ts"],
        "passCriteria": [],
        "failCriteria": [],
    }
    supatest_result = {
        **base_result,
        "agent": "supatest",
        "tokenUsage": {
            **run_benchmark.empty_token_usage(),
            "totalTokens": 1000,
            "estimatedCostUsd": 0.01,
            "source": "transcript",
        },
    }
    cursor_result = {
        **base_result,
        "agent": "cursor",
        "tokenUsage": {
            **run_benchmark.empty_token_usage(),
            "totalTokens": 2000,
            "source": "transcript",
        },
    }

    write_summary(
        tmp_path,
        "verify",
        ["E25"],
        ["supatest", "cursor"],
        1,
        600,
        [supatest_result, cursor_result],
    )

    summary = json.loads((tmp_path / "summary.json").read_text())
    run = json.loads((tmp_path / "run.json").read_text())
    scores = (tmp_path / "scores.md").read_text()

    assert "| Agent | QA Avg | Token Avg | Token Usage | Overall Score |" in scores
    assert (
        "| supatest [premium] | 100.0 | 100.0 | 1.0k | 100.0 | 1 | 0 | 0 | 0 | 0 |"
        in scores
    )
    assert (
        "| cursor [auto] | 100.0 | 50.0 | 2.0k | 90.0 | 1 | 0 | 0 | 0 | 0 |" in scores
    )
    assert "| Token Usage |" in scores
    assert "Cost USD" not in scores
    assert "$0.0100" not in scores
    assert summary["overallScoring"]["qaWeight"] == 0.8
    assert summary["overallScoring"]["tokenUsageWeight"] == 0.2
    assert summary["summary"]["byAgent"]["supatest"]["overallScorePercent"] == 100.0
    assert summary["summary"]["byAgent"]["cursor"]["overallScorePercent"] == 90.0
    assert (
        summary["summary"]["byAgent"]["supatest"]["tokenUsage"]["scorePercent"] == 100.0
    )
    assert summary["summary"]["byAgent"]["cursor"]["tokenUsage"]["scorePercent"] == 50.0
    assert run["runsByEval"]["E25"]["cursor"]["tokenUsage"]["scorePercent"] == 50
    assert run["runsByEval"]["E25"]["cursor"]["overallScorePercent"] == 90.0


def test_token_efficiency_baseline_ignores_cheap_failed_runs(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_TOKEN_BASELINE_QA_THRESHOLD", "0.8")
    results = [
        {
            "evalId": "E25",
            "scorePercent": 100,
            "tokenUsage": {**run_benchmark.empty_token_usage(), "totalTokens": 1000},
        },
        {
            "evalId": "E25",
            "scorePercent": 0,
            "tokenUsage": {**run_benchmark.empty_token_usage(), "totalTokens": 1},
        },
        {
            "evalId": "E25",
            "scorePercent": 100,
            "tokenUsage": {**run_benchmark.empty_token_usage(), "totalTokens": 2000},
        },
        {
            "evalId": "E25",
            "scorePercent": 100,
            "tokenUsage": run_benchmark.empty_token_usage(),
        },
    ]

    apply_token_efficiency_scores(results)

    assert results[0]["tokenUsage"]["scorePercent"] == 100.0
    assert results[1]["tokenUsage"]["scorePercent"] == 0.0
    assert (
        results[1]["tokenUsage"]["scoreBasis"]
        == "qa-capped-relative-passing-token-baseline"
    )
    assert results[2]["tokenUsage"]["scorePercent"] == 50.0
    assert results[3]["tokenUsage"]["scorePercent"] == 0.0
    assert (
        results[3]["tokenUsage"]["scoreBasis"] == "missing-token-usage-zero-efficiency"
    )


def test_score_line_matches_terminal_scoreboard_shape(monkeypatch) -> None:
    monkeypatch.setenv(
        "BENCHMARK_CURSOR_CMD",
        "cursor-agent --print --force --model auto {prompt}",
    )

    line = format_score_line(
        {
            "evalId": "E1",
            "agent": "cursor",
            "scorePercent": 100,
            "result": "pass",
            "durationMs": 35790,
        }
    )

    assert line == "  E1 cursor [auto]                         100 pass     35790ms"
    assert "finished" not in line
    assert "exit=" not in line
    assert "pending" not in line


def test_blocked_score_line_uses_na_score(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_SUPATEST_MODEL", "premium")
    result = write_blocked_result(
        "verify",
        load_fixture("E72"),
        "supatest",
        "case-002",
        PreflightIssue(
            kind="missing-device",
            platform="android",
            reason="No local android device is visible to Maestro.",
        ),
    )

    line = format_score_line(result)

    assert "E72 supatest [premium]" in line
    assert "n/a blocked" in line
    assert result["scorePercent"] is None
    assert result["scoreSource"] == "preflight"


def test_judge_preflight_requires_configured_judge(monkeypatch) -> None:
    monkeypatch.setattr(run_benchmark, "make_judge_model", lambda: None)

    assert "No judge model is configured" in preflight_judge_model()


def test_judge_preflight_reports_and_redacts_model_errors(monkeypatch) -> None:
    def broken_model():
        raise RuntimeError("bad key secret-google-key")

    monkeypatch.setenv("GOOGLE_API_KEY", "secret-google-key")
    monkeypatch.setattr(run_benchmark, "make_judge_model", broken_model)

    issue = preflight_judge_model()

    assert issue is not None
    assert "RuntimeError" in issue
    assert "secret-google-key" not in issue
    assert "<redacted>" in issue


def test_judge_preflight_accepts_valid_response(monkeypatch) -> None:
    calls = {"count": 0}

    class GoodJudge:
        def generate(self, prompt, schema):
            calls["count"] += 1
            assert "preflight" in prompt
            assert schema is BatchJudgeResponse
            return (
                BatchJudgeResponse(
                    results=[
                        BatchJudgeCaseScore(
                            resultId="preflight",
                            score=1.0,
                            result="pass",
                            passedChecks=1,
                            failedChecks=0,
                            reason="Judge API is reachable.",
                        )
                    ]
                ),
                0,
            )

    monkeypatch.setattr(run_benchmark, "make_judge_model", lambda: GoodJudge())

    assert preflight_judge_model() is None
    assert calls["count"] == 1


def test_judge_preflight_rejects_malformed_response(monkeypatch) -> None:
    class BadJudge:
        def generate(self, *_args, **_kwargs):
            return BatchJudgeResponse(results=[]), 0

    monkeypatch.setattr(run_benchmark, "make_judge_model", lambda: BadJudge())

    issue = preflight_judge_model()

    assert issue is not None
    assert "expected exactly one structured result" in issue


def test_judge_preflight_reports_and_redacts_api_errors(monkeypatch) -> None:
    class BrokenJudge:
        def generate(self, *_args, **_kwargs):
            raise RuntimeError("api rejected secret-google-key")

    monkeypatch.setenv("GOOGLE_API_KEY", "secret-google-key")
    monkeypatch.setattr(run_benchmark, "make_judge_model", lambda: BrokenJudge())

    issue = preflight_judge_model()

    assert issue is not None
    assert "Judge API preflight failed" in issue
    assert "secret-google-key" not in issue
    assert "<redacted>" in issue


def test_main_stops_before_agents_when_judge_preflight_fails(
    tmp_path, monkeypatch
) -> None:
    def run_one_case_should_not_start(*_args, **_kwargs):
        raise AssertionError("agent run should not start when judge preflight fails")

    monkeypatch.setenv("BENCHMARK_RUN_ID", "judge-preflight-fails")
    monkeypatch.setenv("BENCHMARK_EVAL_IDS", "E1")
    monkeypatch.setenv("BENCHMARK_EVAL_LIMIT", "all")
    monkeypatch.setenv("BENCHMARK_EVAL_OFFSET", "0")
    monkeypatch.setenv("BENCHMARK_AGENTS", "supatest")
    monkeypatch.setenv("BENCHMARK_RESULTS_DIR", str(tmp_path / "results"))
    monkeypatch.setenv("BENCHMARK_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("BENCHMARK_DISABLE_PREFLIGHT", "1")
    monkeypatch.delenv("BENCHMARK_DISABLE_JUDGE_PREFLIGHT", raising=False)
    monkeypatch.setattr(run_benchmark, "preflight_judge_model", lambda: "judge down")
    monkeypatch.setattr(run_benchmark, "run_one_case", run_one_case_should_not_start)

    assert run_benchmark.main() == 2


def test_batch_scoring_uses_one_judge_call_and_check_counts(monkeypatch) -> None:
    calls = {"count": 0}

    class BatchJudge:
        def generate(self, prompt, schema):
            calls["count"] += 1
            assert "r001" in prompt
            assert '"changedDiff"' in prompt
            assert "expect(true)" in prompt
            assert schema is BatchJudgeResponse
            return (
                BatchJudgeResponse(
                    results=[
                        BatchJudgeCaseScore(
                            resultId="r001",
                            score=0.9,
                            result="pass",
                            passedChecks=2,
                            failedChecks=0,
                            reason="All required evidence is present.",
                        )
                    ]
                ),
                0,
            )

    monkeypatch.setattr(run_benchmark, "make_judge_model", lambda: BatchJudge())
    result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E25",
        "evalName": "Batch Tests Before Running",
        "agent": "supatest",
        "mode": "build",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 123,
        "projectDir": "runs/verify/case-001/supatest/project",
        "transcriptPath": "runs/verify/case-001/supatest/transcript.log",
        "changedFiles": ["tests/example.spec.ts"],
        "changedDiff": (
            "--- a/tests/example.spec.ts\n"
            "+++ b/tests/example.spec.ts\n"
            "-expect(locator).toBeVisible()\n"
            "+expect(true).toBe(true)\n"
        ),
        "passCriteria": ["does A", "does B"],
        "failCriteria": [],
    }
    pending = run_benchmark.PendingResult(
        result,
        LLMTestCase(
            input="Do QA work",
            actual_output="Exit code: 0\nTimed out: False\nChanged files:\nexample",
            expected_output="Pass criteria:\n- does A\n- does B",
        ),
    )

    scored = run_benchmark.score_pending_results("verify", [pending])[0]

    assert calls["count"] == 1
    assert scored["result"] == "pass"
    assert scored["scoreSource"] == "batch-judge"
    assert scored["passedChecks"] == 2
    assert scored["failedChecks"] == 0
    assert run_benchmark.format_cell(scored) == "90% (2p/0f) pass"


def test_batch_judge_prompt_treats_plan_mode_transcript_as_deliverable() -> None:
    result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E31",
        "evalName": "Planner",
        "agent": "supatest",
        "mode": "plan",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 123,
        "projectDir": "runs/verify/case-001/supatest/project",
        "transcriptPath": "runs/verify/case-001/supatest/transcript.log",
        "changedFiles": [],
        "changedDiff": "",
        "artifactChecks": {"warnings": []},
        "passCriteria": ["Plan includes a Not Testing section"],
        "failCriteria": ["No Not Testing section"],
    }
    test_case = LLMTestCase(
        input="Create a test plan",
        actual_output="Exit code: 0\nTimed out: False\nFinal answer includes a plan.",
        expected_output="Pass criteria:\n- Plan includes a Not Testing section",
    )

    prompt = run_benchmark.build_batch_judge_prompt(
        "verify",
        [result],
        [(0, test_case)],
        run_eval_ids=["E31"],
        run_agents=["supatest"],
    )

    assert "Plan-mode cases are read-only" in prompt
    assert "do not require changed files" in prompt


def test_batch_scoring_can_chunk_large_runs(monkeypatch) -> None:
    calls = {"count": 0}

    class BatchJudge:
        def generate(self, prompt, schema):
            calls["count"] += 1
            assert schema is BatchJudgeResponse
            assert "r001" in prompt
            return (
                BatchJudgeResponse(
                    results=[
                        BatchJudgeCaseScore(
                            resultId="r001",
                            score=0.8,
                            result="pass",
                            passedChecks=1,
                            failedChecks=0,
                            reason=f"Chunk {calls['count']} scored.",
                        )
                    ]
                ),
                0,
            )

    monkeypatch.setenv("BENCHMARK_JUDGE_BATCH_SIZE", "1")
    monkeypatch.setattr(run_benchmark, "make_judge_model", lambda: BatchJudge())

    pending = []
    for index, eval_id in enumerate(["E25", "E29"], start=1):
        result = {
            "runId": "verify",
            "caseId": f"case-{index:03d}",
            "evalId": eval_id,
            "evalName": "Fixture",
            "agent": "supatest",
            "mode": "build",
            "exitCode": 0,
            "timedOut": False,
            "durationMs": 123,
            "projectDir": f"runs/verify/case-{index:03d}/supatest/project",
            "transcriptPath": f"runs/verify/case-{index:03d}/supatest/transcript.log",
            "changedFiles": [],
            "passCriteria": ["does A"],
            "failCriteria": [],
        }
        pending.append(
            run_benchmark.PendingResult(
                result,
                LLMTestCase(
                    input="Do QA work",
                    actual_output="Exit code: 0\nTimed out: False\nDone",
                    expected_output="Pass criteria:\n- does A",
                ),
            )
        )

    scored = run_benchmark.score_pending_results("verify", pending)

    assert calls["count"] == 2
    assert [item["scorePercent"] for item in scored] == [80, 80]
    assert [item["reason"] for item in scored] == ["Chunk 1 scored.", "Chunk 2 scored."]


def test_missing_batch_score_is_unscored(monkeypatch) -> None:
    class EmptyJudge:
        def generate(self, *_args, **_kwargs):
            return BatchJudgeResponse(results=[]), 0

    monkeypatch.setattr(run_benchmark, "make_judge_model", lambda: EmptyJudge())
    result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E25",
        "evalName": "Batch Tests Before Running",
        "agent": "supatest",
        "mode": "build",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 123,
        "projectDir": "runs/verify/case-001/supatest/project",
        "transcriptPath": "runs/verify/case-001/supatest/transcript.log",
        "changedFiles": [],
        "passCriteria": [],
        "failCriteria": [],
    }
    pending = run_benchmark.PendingResult(
        result,
        LLMTestCase(
            input="Do QA work",
            actual_output="Exit code: 0\nTimed out: False\nCleaned transcript tail:\ndone",
            expected_output="Pass criteria:\n- Done",
        ),
    )

    scored = run_benchmark.score_pending_results("verify", [pending])[0]

    assert scored["score"] is None
    assert scored["scorePercent"] is None
    assert scored["result"] == "unscored"
    assert scored["scoreSource"] == "judge-error"
    assert "Batch judge did not return" in scored["reason"]


def test_unscored_results_are_excluded_from_summary_average(tmp_path) -> None:
    passing_result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E25",
        "evalName": "Batch Tests Before Running",
        "agent": "supatest",
        "mode": "build",
        "score": 1.0,
        "scorePercent": 100,
        "result": "pass",
        "reason": "ok",
        "scoreSource": "judge",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 123,
        "projectDir": "runs/verify/case-001/supatest/project",
        "transcriptPath": "runs/verify/case-001/supatest/transcript.log",
        "changedFiles": ["tests/error-users.spec.ts"],
        "passCriteria": [],
        "failCriteria": [],
    }
    unscored_result = {
        **passing_result,
        "caseId": "case-002",
        "evalId": "E26",
        "score": None,
        "scorePercent": None,
        "result": "unscored",
        "reason": "judge quota exhausted",
        "scoreSource": "judge-error",
    }

    write_summary(
        tmp_path,
        "verify",
        ["E25", "E26"],
        ["supatest"],
        1,
        600,
        [passing_result, unscored_result],
    )

    summary = json.loads((tmp_path / "summary.json").read_text())
    scores = (tmp_path / "scores.md").read_text()

    assert summary["summary"]["byAgent"]["supatest"]["averageScorePercent"] == 100.0
    assert summary["summary"]["byAgent"]["supatest"]["scored"] == 1
    assert summary["summary"]["byAgent"]["supatest"]["fail"] == 0
    assert summary["summary"]["byAgent"]["supatest"]["unscored"] == 1
    assert "| E26 | unscored |" in scores
    assert "Unscored" not in scores


def test_live_device_preflight_only_targets_selected_live_inspection_evals() -> None:
    assert required_live_device_platform(load_fixture("E72")) is None
    assert required_live_device_platform(load_fixture("E71")) is None
    assert required_live_device_platform(load_fixture("E81")) is None
    assert required_live_device_platform(load_fixture("E103")) is None


def test_live_device_preflight_still_detects_future_live_inspection_eval() -> None:
    fixture = SimpleNamespace(
        task="Inspect the live Android emulator before answering.",
        pass_criteria=["Calls mcp__maestro__inspect_view_hierarchy at least once"],
        fail_criteria=[],
    )

    assert required_live_device_platform(fixture) == "android"


def test_maestro_device_output_parser() -> None:
    assert maestro_output_has_devices(
        """
Local Devices
────────────────
Android
  Pixel_8_API_35   emulator-5554
""",
        "android",
    )
    assert not maestro_output_has_devices(
        """
Local Devices
────────────────
No devices found
""",
        "android",
    )
