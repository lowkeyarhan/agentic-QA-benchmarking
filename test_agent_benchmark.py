from __future__ import annotations

import json
import os
from types import SimpleNamespace

from deepeval.test_case import LLMTestCase

from agents import (
    agent_command_env_name,
    agent_display_name,
    agent_environment,
    agent_model_label,
    build_command,
    build_prompt,
    changed_file_excerpt,
    resolve_supatest_project_id,
    with_local_tool_paths,
)
from fixtures import available_eval_ids, load_fixture, resolve_eval_ids
import run_benchmark
from run_benchmark import (
    PreflightIssue,
    evaluate_quietly,
    format_score_line,
    maestro_output_has_devices,
    required_live_device_platform,
    write_blocked_result,
    write_summary,
)
from scoring import cleaned_transcript, make_metric, make_test_case


def test_agent_environment_hides_benchmark_and_judge_vars(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_EVAL_IDS", "E25")
    monkeypatch.setenv("DEEPEVAL_GEMINI_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("GOOGLE_API_KEY", "secret")
    monkeypatch.setenv("SUPATEST_API_KEY", "supatest-secret")
    monkeypatch.setenv("SUPATEST_PROJECT_ID", "aiden")

    env = agent_environment()

    assert "BENCHMARK_EVAL_IDS" not in env
    assert "DEEPEVAL_GEMINI_MODEL" not in env
    assert "GOOGLE_API_KEY" not in env
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


def test_supatest_project_id_uses_explicit_or_benchmark_settings(monkeypatch) -> None:
    monkeypatch.delenv("BENCHMARK_SUPATEST_PROJECT_ID", raising=False)
    monkeypatch.setenv("SUPATEST_PROJECT_ID", "global-env-should-not-leak")

    assert resolve_supatest_project_id() == "aiden"

    monkeypatch.setenv("BENCHMARK_SUPATEST_PROJECT_ID", "benchmark-project")

    assert resolve_supatest_project_id() == "benchmark-project"


def test_benchmark_prompt_frames_real_qa_without_exposing_rubric() -> None:
    fixture = load_fixture("E25")

    prompt = build_prompt(fixture)

    assert "real production QA work" in prompt
    assert "User request:" in prompt
    assert fixture.task in prompt
    assert "passCriteria" not in prompt
    assert "failCriteria" not in prompt


def test_supatest_receives_same_benchmark_prompt(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_SUPATEST_PROJECT_ID", "benchmark-project")
    monkeypatch.delenv("BENCHMARK_SUPATEST_API_KEY", raising=False)
    monkeypatch.delenv("SUPATEST_API_KEY", raising=False)
    monkeypatch.delenv("BENCHMARK_SUPATEST_MODEL", raising=False)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    fixture = load_fixture("E25")

    command, cwd, use_shell = build_command("supatest", fixture, project_dir)

    assert use_shell is False
    assert cwd == project_dir
    assert command[1] == build_prompt(fixture)
    assert "real production QA work" in command[1]
    assert command[command.index("--model") + 1] == "premium"
    assert command[command.index("--project-id") + 1] == "benchmark-project"
    assert "--supatest-api-key" not in command


def test_resolve_eval_ids_all_uses_every_available_fixture() -> None:
    eval_ids = resolve_eval_ids("all")

    assert eval_ids == available_eval_ids()
    assert "E18" in eval_ids
    assert "E101" in eval_ids


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

    test_case = make_test_case(load_fixture("E25"), run)

    assert "Agent:" not in test_case.actual_output
    assert "supatest" not in test_case.actual_output.lower()
    assert str(tmp_path) not in test_case.actual_output
    assert "cli_1234567890abcdefghijklmnop" not in test_case.actual_output
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
    assert run["runsByEval"]["E25"]["supatest"]["caseId"] == "case-001"


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

    assert line == "  E1 cursor [auto]                    100 pass    35790ms"
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


def test_judge_error_is_unscored_not_agent_failure(monkeypatch) -> None:
    def failing_evaluate(**_kwargs):
        raise RuntimeError("judge quota exhausted")

    monkeypatch.setattr(run_benchmark, "evaluate_quietly", failing_evaluate)
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
    assert "judge quota exhausted" in scored["reason"]


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
    assert "Unscored" in scores


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


def test_deepeval_console_output_is_suppressed_by_default(monkeypatch, capsys) -> None:
    def noisy_evaluate(**_kwargs):
        print("deepeval banner")
        return "ok"

    monkeypatch.delenv("BENCHMARK_DEEPEVAL_VERBOSE", raising=False)
    monkeypatch.setattr(run_benchmark, "evaluate", noisy_evaluate)

    assert evaluate_quietly(test_cases=[], metrics=[]) == "ok"

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_deepeval_console_output_can_be_enabled(monkeypatch, capsys) -> None:
    def noisy_evaluate(**_kwargs):
        print("deepeval banner")
        return "ok"

    monkeypatch.setenv("BENCHMARK_DEEPEVAL_VERBOSE", "1")
    monkeypatch.setattr(run_benchmark, "evaluate", noisy_evaluate)

    assert evaluate_quietly(test_cases=[], metrics=[]) == "ok"

    captured = capsys.readouterr()
    assert "deepeval banner" in captured.out
