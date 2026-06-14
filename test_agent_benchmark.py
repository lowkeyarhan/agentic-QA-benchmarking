from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import agents
from benchmark_deterministic import build_deterministic_grade
from deepeval.test_case import LLMTestCase

from agents import (
    AgentRunResult,
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
    select_eval_ids,
    selected_eval_ids,
    window_eval_ids,
)
from qa_bench import (
    QA_BENCH_CAPABILITIES,
    QA_BENCH_METRICS,
    available_suite_names,
    difficulty_for_tier,
    eval_metadata,
)
from qa_bench.rubrics import (
    HIGH_DIFFICULTY_EVAL_IDS,
    LOW_DIFFICULTY_EVAL_IDS,
    MAX_DIFFICULTY_EVAL_IDS,
    MEDIUM_DIFFICULTY_EVAL_IDS,
    ULTRA_DIFFICULTY_EVAL_IDS,
)
import run_benchmark
from run_benchmark import (
    BatchJudgeCaseScore,
    BatchJudgeResponse,
    JudgeMetricScore,
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


def test_supatest_agent_environment_enables_eval_telemetry_by_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv("BENCHMARK_SUPATEST_EVAL_TELEMETRY", raising=False)
    monkeypatch.delenv("SUPATEST_EVAL_TELEMETRY", raising=False)

    env = agent_environment("supatest")

    assert env["SUPATEST_EVAL_TELEMETRY"] == "1"


def test_supatest_agent_environment_can_disable_eval_telemetry(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_SUPATEST_EVAL_TELEMETRY", "0")

    env = agent_environment("supatest")

    assert env["SUPATEST_EVAL_TELEMETRY"] == "0"


def test_run_agent_records_monotonic_elapsed_duration(tmp_path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    output_dir = tmp_path / "run"
    fixture = SimpleNamespace(
        eval_id="E-clock",
        task="Measure elapsed time",
        mode="build",
        logs_file=None,
    )

    class FakeProcess:
        returncode = 0

        def communicate(self, input=None, timeout=None):
            return "done\n", None

    monotonic_values = iter([10.0, 12.5])
    monkeypatch.setenv("BENCHMARK_FAKE_CMD", "fake-agent {task}")
    monkeypatch.setattr(agents.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(
        agents.subprocess, "Popen", lambda *args, **kwargs: FakeProcess()
    )

    result = agents.run_agent("fake", fixture, project_dir, output_dir)

    assert result.duration_ms == 2500
    assert result.transcript_path.read_text() == "done\n"


def test_run_one_case_checkpoints_pending_result(tmp_path, monkeypatch) -> None:
    runs_dir = tmp_path / "runs"

    def fake_run_agent(agent, fixture, project_dir, output_dir):
        test_path = project_dir / "tests" / "checkpoint.spec.ts"
        test_path.parent.mkdir(exist_ok=True)
        test_path.write_text("import { test } from '@playwright/test';\n")
        transcript_path = output_dir / "transcript.log"
        transcript_path.write_text("finished\n")
        return AgentRunResult(
            agent=agent,
            eval_id=fixture.eval_id,
            project_dir=project_dir,
            transcript_path=transcript_path,
            exit_code=0,
            duration_ms=1234,
            timed_out=False,
            changed_files=["tests/checkpoint.spec.ts"],
            changed_file_excerpt="--- tests/checkpoint.spec.ts ---\nimport { test }",
        )

    monkeypatch.setattr(run_benchmark, "run_agent", fake_run_agent)

    pending = run_benchmark.run_one_case(
        "checkpoint-run", runs_dir, "E1", "supatest", "case-001"
    )
    pending_path = (
        runs_dir
        / "case-001"
        / agent_run_dir_name("supatest")
        / run_benchmark.PENDING_RESULT_FILE
    )
    saved = json.loads(pending_path.read_text())

    assert pending.result["durationMs"] == 1234
    assert saved["evalId"] == "E1"
    assert saved["agent"] == "supatest"
    assert saved["changedFiles"] == ["tests/checkpoint.spec.ts"]


def test_score_existing_run_id_from_args(monkeypatch) -> None:
    monkeypatch.delenv("BENCHMARK_SCORE_EXISTING_RUN_ID", raising=False)
    monkeypatch.setattr(
        run_benchmark.sys,
        "argv",
        ["run_benchmark.py", "--score-existing", "20260613-235343"],
    )

    assert run_benchmark.score_existing_run_id_from_args() == "20260613-235343"


def test_run_benchmark_exposes_judge_batch_size_helper(monkeypatch) -> None:
    monkeypatch.delenv("BENCHMARK_JUDGE_BATCH_SIZE", raising=False)

    assert run_benchmark.configured_judge_batch_size(3) == 0


def test_infer_duration_ms_from_structured_transcript() -> None:
    transcript = "\n".join(
        [
            "plain text",
            json.dumps({"type": "result", "duration_ms": 43935}),
            json.dumps({"type": "result", "stats": {"duration_ms": 1234}}),
        ]
    )

    assert run_benchmark.infer_duration_ms_from_transcript(transcript) == 1234


def test_local_mobile_tool_paths_are_added_when_present(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    maestro_bin = home / ".maestro" / "bin"
    maestro_bin.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    path = with_local_tool_paths(os.pathsep.join(["/usr/bin", "/bin"]))

    assert path.split(os.pathsep)[0] == str(maestro_bin)


def write_executable(path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)


def test_agent_environment_hides_host_rtk_without_hiding_neighbor_tools(
    tmp_path, monkeypatch
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_executable(bin_dir / "rtk")
    write_executable(bin_dir / "codex")
    write_executable(bin_dir / "npm")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.delenv("BENCHMARK_HIDE_HOST_TOOLS", raising=False)

    env = agent_environment("codex")

    assert shutil.which("rtk", path=env["PATH"]) is None
    assert (
        Path(shutil.which("codex", path=env["PATH"]) or "").resolve()
        == (bin_dir / "codex").resolve()
    )
    assert (
        Path(shutil.which("npm", path=env["PATH"]) or "").resolve()
        == (bin_dir / "npm").resolve()
    )


def test_agent_environment_can_disable_host_tool_hiding_for_local_debugging(
    tmp_path, monkeypatch
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_executable(bin_dir / "rtk")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("BENCHMARK_HIDE_HOST_TOOLS", "none")

    env = agent_environment("cursor")

    assert shutil.which("rtk", path=env["PATH"]) == str(bin_dir / "rtk")


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
    monkeypatch.delenv("BENCHMARK_GEMINI_MODEL", raising=False)
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


def test_resolve_eval_ids_supports_named_qa_bench_suites() -> None:
    eval_ids = resolve_eval_ids("suite:qa-smoke")

    assert eval_ids == ["E25", "E31", "E43", "E48", "E50", "E65", "E101", "E118"]


def test_resolve_eval_ids_supports_low_qa_bench_suite() -> None:
    eval_ids = resolve_eval_ids("suite:qa-low")

    assert eval_ids == LOW_DIFFICULTY_EVAL_IDS
    assert all(
        difficulty_for_tier(load_fixture(eval_id).tier) == "low" for eval_id in eval_ids
    )


def test_resolve_eval_ids_supports_medium_and_high_qa_bench_suites() -> None:
    medium_eval_ids = resolve_eval_ids("suite:qa-medium")
    high_eval_ids = resolve_eval_ids("suite:qa-high")

    assert medium_eval_ids == MEDIUM_DIFFICULTY_EVAL_IDS
    assert high_eval_ids == HIGH_DIFFICULTY_EVAL_IDS
    assert all(
        difficulty_for_tier(load_fixture(eval_id).tier) == "medium"
        for eval_id in medium_eval_ids
    )
    assert all(
        difficulty_for_tier(load_fixture(eval_id).tier) == "high"
        for eval_id in high_eval_ids
    )


def test_resolve_eval_ids_supports_ultra_and_max_qa_bench_suites() -> None:
    ultra_eval_ids = resolve_eval_ids("suite:qa-ultra")
    max_eval_ids = resolve_eval_ids("suite:qa-max")

    assert ultra_eval_ids == ULTRA_DIFFICULTY_EVAL_IDS
    assert max_eval_ids == MAX_DIFFICULTY_EVAL_IDS
    assert all(
        difficulty_for_tier(load_fixture(eval_id).tier) == "ultra"
        for eval_id in ultra_eval_ids
    )
    assert all(
        difficulty_for_tier(load_fixture(eval_id).tier) == "max"
        for eval_id in max_eval_ids
    )


def test_select_eval_ids_appends_extra_eval_ids_after_windowing() -> None:
    eval_ids = select_eval_ids("E1,E2,E3", "E4,E2", "2", "1")

    assert eval_ids == ["E2", "E3", "E4"]


def test_selected_eval_ids_reads_extra_eval_ids_from_env(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_EVAL_IDS", "E1")
    monkeypatch.setenv("BENCHMARK_EXTRA_EVAL_IDS", "E2,E1")
    monkeypatch.setenv("BENCHMARK_EVAL_LIMIT", "all")
    monkeypatch.setenv("BENCHMARK_EVAL_OFFSET", "0")

    assert selected_eval_ids() == ["E1", "E2"]


def test_reproducibility_metadata_records_extra_eval_ids(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_EVAL_IDS", "suite:qa-smoke")
    monkeypatch.setenv("BENCHMARK_EXTRA_EVAL_IDS", "E2,E6")

    metadata = run_benchmark.build_reproducibility_metadata(
        "extra-evals",
        ["E25", "E31", "E2", "E6"],
        ["supatest"],
        1,
        600,
    )

    assert metadata["evalRunner"]["baseEvalIds"] == "suite:qa-smoke"
    assert metadata["evalRunner"]["extraEvalIds"] == "E2,E6"
    assert metadata["evalRunner"]["benchmarkSuite"]["id"] == "custom-qa"


def test_qa_bench_suite_names_are_vendor_neutral() -> None:
    assert "qa-high" in available_suite_names()
    assert "qa-low" in available_suite_names()
    assert "qa-max" in available_suite_names()
    assert "qa-medium" in available_suite_names()
    assert "qa-ultra" in available_suite_names()
    assert "qa-lifecycle-extended" in available_suite_names()
    assert all("supatest" not in suite for suite in available_suite_names())


def test_documented_tier_difficulty_mapping() -> None:
    assert difficulty_for_tier(1) == "low"
    assert difficulty_for_tier(2) == "low"
    assert difficulty_for_tier(3) == "medium"
    assert difficulty_for_tier(4) == "medium"
    assert difficulty_for_tier(5) == "high"
    assert difficulty_for_tier(6) == "high"
    assert difficulty_for_tier(7) == "ultra"
    assert difficulty_for_tier(9) == "ultra"
    assert difficulty_for_tier(10) == "max"
    assert difficulty_for_tier(11) == "max"


def test_all_fixtures_have_explicit_qa_bench_metadata() -> None:
    fixtures = [load_fixture(eval_id) for eval_id in available_eval_ids()]

    assert len(fixtures) == 100
    for fixture in fixtures:
        eval_id = fixture.eval_id
        explicit = fixture.qa_bench
        metadata = eval_metadata(fixture)

        assert explicit is not None, eval_id
        assert explicit["difficulty"] == difficulty_for_tier(fixture.tier), eval_id
        assert explicit["capability"] in QA_BENCH_CAPABILITIES, eval_id
        assert explicit["metricIds"], eval_id
        assert set(explicit["metricIds"]) <= set(QA_BENCH_METRICS), eval_id
        assert metadata["metadataSource"] == "fixture", eval_id
        assert metadata["difficulty"] == explicit["difficulty"], eval_id
        assert metadata["capability"] == explicit["capability"], eval_id
        assert metadata["metricIds"] == explicit["metricIds"], eval_id
        assert metadata["judgeGuidance"], eval_id
        assert metadata["qualitySignals"], eval_id
        assert metadata["expectedSignals"], eval_id
        assert metadata["antiPatterns"], eval_id
        assert metadata["scoringNotes"], eval_id
        if metadata["difficulty"] == "low":
            assert "baseline QA competency" in metadata["judgeGuidance"][0], eval_id


def test_low_difficulty_evals_have_explicit_expected_signals_and_antipatterns() -> None:
    assert len(LOW_DIFFICULTY_EVAL_IDS) == 20

    for eval_id in LOW_DIFFICULTY_EVAL_IDS:
        metadata = eval_metadata(load_fixture(eval_id))

        assert metadata["difficulty"] == "low", eval_id
        assert metadata["expectedSignals"], eval_id
        assert metadata["antiPatterns"], eval_id
        assert metadata["scoringNotes"], eval_id


def test_medium_and_high_difficulty_evals_have_expected_signals_and_antipatterns() -> (
    None
):
    assert len(MEDIUM_DIFFICULTY_EVAL_IDS) == 20
    assert len(HIGH_DIFFICULTY_EVAL_IDS) == 20

    for difficulty, eval_ids in [
        ("medium", MEDIUM_DIFFICULTY_EVAL_IDS),
        ("high", HIGH_DIFFICULTY_EVAL_IDS),
    ]:
        for eval_id in eval_ids:
            metadata = eval_metadata(load_fixture(eval_id))

            assert metadata["difficulty"] == difficulty, eval_id
            assert metadata["expectedSignals"], eval_id
            assert metadata["antiPatterns"], eval_id
            assert metadata["scoringNotes"], eval_id


def test_ultra_and_max_difficulty_evals_have_expected_signals_and_antipatterns() -> (
    None
):
    assert len(ULTRA_DIFFICULTY_EVAL_IDS) == 20
    assert len(MAX_DIFFICULTY_EVAL_IDS) == 20

    for difficulty, eval_ids in [
        ("ultra", ULTRA_DIFFICULTY_EVAL_IDS),
        ("max", MAX_DIFFICULTY_EVAL_IDS),
    ]:
        for eval_id in eval_ids:
            metadata = eval_metadata(load_fixture(eval_id))

            assert metadata["difficulty"] == difficulty, eval_id
            assert metadata["expectedSignals"], eval_id
            assert metadata["antiPatterns"], eval_id
            assert metadata["scoringNotes"], eval_id


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


def test_deterministic_grader_flags_fixed_waits_and_skips() -> None:
    result = {
        "mode": "build",
        "changedDiff": (
            "--- a/tests/example.spec.ts\n"
            "+++ b/tests/example.spec.ts\n"
            "+test.skip('flaky test', async ({ page }) => {})\n"
            "+await page.waitForTimeout(500)\n"
            "+expect(true).toBe(true)\n"
        ),
        "artifactChecks": {"warnings": [], "ranVerificationCommand": True},
    }

    grade = build_deterministic_grade(result)

    assert "no-fixed-waits" in grade["failedCheckIds"]
    assert "no-skip-or-only" in grade["failedCheckIds"]
    assert "no-trivial-assertions" in grade["failedCheckIds"]
    assert grade["cap"] == 0.49


def test_deterministic_grader_flags_missing_required_implementation_change() -> None:
    result = {
        "mode": "fix",
        "changedFiles": ["tests/cart.spec.ts"],
        "changedDiff": "+expect(total).toBe(85)\n",
        "artifactChecks": {
            "changedImplementationFiles": [],
            "changedTestFiles": ["tests/cart.spec.ts"],
            "warnings": [],
        },
        "passCriteria": ["At least one non-test file is modified"],
        "failCriteria": ["No implementation file changes"],
    }

    grade = build_deterministic_grade(result)

    assert "implementation-change-required" in grade["failedCheckIds"]
    assert grade["cap"] == 0.39


def test_deterministic_grader_flags_plan_mode_writes() -> None:
    result = {
        "mode": "plan",
        "changedFiles": ["tests/new.spec.ts"],
        "artifactChecks": {"warnings": [], "changedTestFiles": ["tests/new.spec.ts"]},
    }

    grade = build_deterministic_grade(result)

    assert "plan-read-only" in grade["failedCheckIds"]
    assert "no-spec-files-when-forbidden" in grade["failedCheckIds"]
    assert grade["cap"] == 0.39


def test_deterministic_grader_flags_missing_mobile_inspect() -> None:
    result = {
        "mode": "build",
        "changedDiff": "",
        "artifactChecks": {"warnings": []},
        "task": "Call inspect_view_hierarchy to discover selectors from the live device.",
        "evidence": "Final answer guessed selectors without tool use.",
        "telemetry": {"toolCounts": {}},
    }

    grade = build_deterministic_grade(result)

    assert "maestro-inspect-required" in grade["failedCheckIds"]
    assert grade["cap"] == 0.69


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
                            "cache_creation_input_tokens": 50,
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
    assert usage["cacheCreationInputTokens"] == 50
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


def test_eval_telemetry_parser_reads_stream_json_tools_and_usage(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("BENCHMARK_SUPATEST_MODEL", "premium")
    transcript = tmp_path / "transcript.log"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "system",
                        "subtype": "init",
                        "model": "premium",
                        "provider": "anthropic",
                        "taskKind": "qa-code-verification",
                        "harnessProfile": "qa-code-verification:premium",
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "git diff --name-only"},
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "npx playwright test tests/cart.spec.ts"},
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "tests/cart.spec.ts"},
                    }
                ),
                json.dumps({"type": "policy_denial", "reason": "Write denied"}),
                json.dumps(
                    {
                        "type": "result",
                        "duration_ms": 1234,
                        "num_turns": 3,
                        "total_cost_usd": 0.01,
                        "usage": {
                            "input_tokens": 1000,
                            "output_tokens": 250,
                            "cache_read_input_tokens": 400,
                            "cache_creation_input_tokens": 50,
                            "total_tokens": 1250,
                        },
                    }
                ),
                "{not json",
            ]
        )
    )

    telemetry = run_benchmark.build_eval_telemetry(
        "supatest", transcript, tmp_path, duration_ms=1500
    )

    assert telemetry["taskKind"] == "qa-code-verification"
    assert telemetry["harnessProfile"] == "qa-code-verification:premium"
    assert telemetry["selectedModel"] == "premium"
    assert telemetry["provider"] == "anthropic"
    assert telemetry["turns"] == 3
    assert telemetry["sdkDurationMs"] == 1234
    assert telemetry["wallDurationMs"] == 1500
    assert telemetry["costUsd"] == 0.01
    assert telemetry["inputTokens"] == 1000
    assert telemetry["outputTokens"] == 250
    assert telemetry["cacheReadTokens"] == 400
    assert telemetry["cacheCreationTokens"] == 50
    assert telemetry["totalTokens"] == 1250
    assert telemetry["toolCounts"] == {"Bash": 2, "Edit": 1}
    assert telemetry["commandCategories"] == {"git-read": 1, "test": 1}
    assert telemetry["firstTool"] == "Bash"
    assert telemetry["firstShellCommand"] == "git diff --name-only"
    assert telemetry["didRunTests"] is True
    assert telemetry["didWrite"] is True
    assert telemetry["deniedPolicyCount"] == 1
    assert telemetry["malformedJsonLines"] == 1


def test_eval_telemetry_parser_reads_nested_supatest_and_cursor_tool_shapes(
    tmp_path,
) -> None:
    transcript = tmp_path / "transcript.log"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "name": "Read",
                                    "input": {"file_path": "tests/toast.spec.ts"},
                                },
                                {
                                    "type": "tool_use",
                                    "name": "Bash",
                                    "input": {
                                        "command": "npm test -- tests/toast.spec.ts"
                                    },
                                },
                            ],
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_call",
                        "subtype": "started",
                        "tool_call": {
                            "shellToolCall": {
                                "args": {"command": "rg waitForTimeout pages tests"}
                            }
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "tool_call",
                        "subtype": "completed",
                        "tool_call": {
                            "editToolCall": {"args": {"path": "pages/InventoryPage.ts"}}
                        },
                    }
                ),
            ]
        )
    )

    telemetry = run_benchmark.build_eval_telemetry("supatest", transcript, tmp_path)

    assert telemetry["toolCounts"] == {"Read": 1, "Bash": 2, "Edit": 1}
    assert telemetry["firstTool"] == "Read"
    assert telemetry["firstShellCommand"] == "npm test -- tests/toast.spec.ts"
    assert telemetry["commandCategories"] == {"search": 1, "test": 1}
    assert telemetry["didRunTests"] is True
    assert telemetry["didWrite"] is True


def test_failure_taxonomy_flags_plan_overtooling_and_missing_artifact() -> None:
    fixture = SimpleNamespace(
        mode="plan",
        task="Create a read-only QA plan.",
        pass_criteria=["Plan includes affected flows"],
        fail_criteria=[],
    )
    result = {
        "mode": "plan",
        "result": "fail",
        "exitCode": 1,
        "scoreSource": "batch-judge",
        "failedChecks": 1,
        "artifactWarnings": ["expected-artifact-change-missing"],
        "tokenUsage": run_benchmark.empty_token_usage(),
        "telemetry": {
            **run_benchmark.empty_eval_telemetry(),
            "didRunTests": True,
            "didUseBrowser": True,
            "didWrite": True,
        },
    }

    taxonomy = run_benchmark.failure_taxonomy_for_result(result, fixture)

    assert "agent-error" in taxonomy
    assert "grader-fail" in taxonomy
    assert "missing-artifact" in taxonomy
    assert "missing-token-usage" in taxonomy
    assert "over-tooling" in taxonomy
    assert "wrong-route" in taxonomy


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


def test_write_summary_emits_only_three_result_files(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BENCHMARK_EVAL_IDS", raising=False)
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
    assert "QA Bench Capability Scores" in scores
    assert "QA Bench Metric Scores" in scores
    assert summary["agentModels"]["supatest"] == "premium"
    assert summary["toolPolicy"]["hiddenHostTools"] == ["rtk"]
    assert run["toolPolicy"] == summary["toolPolicy"]
    assert summary["qaBench"]["version"] == "qa-bench-v1"
    assert summary["qaBench"]["evals"]["E25"]["capability"] == "test-authoring"
    assert "coverage" in summary["qaBench"]["evals"]["E25"]["metricIds"]
    assert "byMetric" in summary["qaBench"]["summary"]["byAgent"]["supatest"]
    assert summary["reproducibility"]["benchmarkRunId"] == "verify"
    assert (
        summary["reproducibility"]["evalRunner"]["benchmarkSuite"]["id"]
        == "qa-production"
    )
    assert summary["reproducibility"]["evalRunner"]["fixtureHashes"]["E25"]
    assert summary["diagnostics"]["failureTaxonomy"]["missing-token-usage"] == 1
    assert run["diagnostics"] == summary["diagnostics"]
    assert summary["summary"]["byAgent"]["supatest"]["pass"] == 1
    assert (
        summary["summary"]["byAgent"]["supatest"]["tokenUsage"]["scorePercent"] == 0.0
    )
    assert summary["summary"]["byAgent"]["supatest"]["time"]["scorePercent"] == 100.0
    assert summary["summary"]["byAgent"]["supatest"]["overallScorePercent"] == 70.0
    assert run["runsByEval"]["E25"]["supatest"]["caseId"] == "case-001"
    assert run["runsByEval"]["E25"]["supatest"]["tokenUsage"]["scorePercent"] == 0.0
    assert run["runsByEval"]["E25"]["supatest"]["time"]["scorePercent"] == 100.0
    assert run["runsByEval"]["E25"]["supatest"]["overallScorePercent"] == 70.0
    assert (
        run["runsByEval"]["E25"]["supatest"]["qaBench"]["capability"]
        == "test-authoring"
    )
    assert run["runsByEval"]["E25"]["supatest"]["failureTaxonomy"] == [
        "missing-token-usage"
    ]


def test_write_summary_creates_missing_results_dir(tmp_path) -> None:
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
        "changedFiles": [],
        "tokenUsage": run_benchmark.empty_token_usage(),
        "passCriteria": [],
        "failCriteria": [],
    }
    results_dir = tmp_path / "nested" / "results"

    write_summary(results_dir, "verify", ["E25"], ["supatest"], 1, 600, [result])

    assert (results_dir / "scores.md").is_file()
    assert (results_dir / "summary.json").is_file()
    assert (results_dir / "run.json").is_file()


def test_write_summary_includes_relative_token_efficiency_and_overall_score(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("BENCHMARK_OVERALL_QA_WEIGHT", "0.7")
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

    assert (
        "| Agent | QA | Tok | Used | Cache R | Cache W | Time | Overall | P | Part | F |"
        in scores
    )
    assert (
        "| supatest [premium] | 100.0 | 100.0 | 1.0k | 0 | 0 | 123ms | 100.0 | 1 | 0 | 0 |"
        in scores
    )
    assert (
        "| cursor [auto] | 100.0 | 50.0 | 2.0k | 0 | 0 | 123ms | 85.0 | 1 | 0 | 0 |"
        in scores
    )
    assert "Checks Pass" not in scores
    assert "Checks Fail" not in scores
    assert "| Used |" in scores
    assert "| Cache R |" in scores
    assert "| Cache W |" in scores
    assert "| Time |" in scores
    assert "Cost USD" not in scores
    assert "$0.0100" not in scores
    assert summary["overallScoring"]["qaWeight"] == 0.7
    assert summary["overallScoring"]["tokenUsageWeight"] == 0.3
    assert "timeWeight" not in summary["overallScoring"]
    assert summary["summary"]["byAgent"]["supatest"]["overallScorePercent"] == 100.0
    assert summary["summary"]["byAgent"]["cursor"]["overallScorePercent"] == 85.0
    assert (
        summary["summary"]["byAgent"]["supatest"]["tokenUsage"]["scorePercent"] == 100.0
    )
    assert summary["summary"]["byAgent"]["cursor"]["tokenUsage"]["scorePercent"] == 50.0
    assert summary["summary"]["byAgent"]["cursor"]["time"]["scorePercent"] == 100.0
    assert run["runsByEval"]["E25"]["cursor"]["tokenUsage"]["scorePercent"] == 50
    assert run["runsByEval"]["E25"]["cursor"]["time"]["scorePercent"] == 100.0
    assert run["runsByEval"]["E25"]["cursor"]["overallScorePercent"] == 85.0


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


def test_time_efficiency_baseline_ignores_fast_failed_runs(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARK_TOKEN_BASELINE_QA_THRESHOLD", "0.8")
    results = [
        {"evalId": "E25", "scorePercent": 100, "durationMs": 1000},
        {"evalId": "E25", "scorePercent": 0, "durationMs": 1},
        {"evalId": "E25", "scorePercent": 100, "durationMs": 2000},
    ]

    run_benchmark.apply_time_efficiency_scores(results)

    assert results[0]["time"]["scorePercent"] == 100.0
    assert results[1]["time"]["scorePercent"] == 0.0
    assert (
        results[1]["time"]["scoreBasis"] == "qa-capped-relative-passing-time-baseline"
    )
    assert results[2]["time"]["scorePercent"] == 50.0


def test_supatest_eval_dashboard_payload_uses_agent_summary_scores() -> None:
    supatest_result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E25",
        "evalName": "Batch Tests Before Running",
        "agent": "supatest:premium",
        "mode": "build",
        "score": 1.0,
        "scorePercent": 100,
        "overallScore": 0.985,
        "overallScorePercent": 98.5,
        "result": "pass",
        "reason": "ok",
        "scoreSource": "judge",
        "overallScoreSource": "weighted-qa-token",
        "passedChecks": 2,
        "failedChecks": 0,
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 1234,
        "projectDir": "runs/verify/case-001/supatest/project",
        "transcriptPath": "runs/verify/case-001/supatest/transcript.log",
        "changedFiles": ["tests/error-users.spec.ts"],
        "artifactWarnings": [],
        "tokenUsage": {
            **run_benchmark.empty_token_usage(),
            "inputTokens": 800,
            "outputTokens": 200,
            "totalTokens": 1000,
            "score": 0.95,
            "scorePercent": 95.0,
            "scoreBasis": "relative-passing-token-baseline",
            "estimatedCostUsd": 0.0123,
            "source": "transcript",
        },
        "time": {
            **run_benchmark.empty_time_score(1234),
            "score": 0.9,
            "scorePercent": 90.0,
            "scoreBasis": "relative-passing-time-baseline",
        },
    }
    cursor_result = {
        **supatest_result,
        "agent": "cursor:auto",
        "overallScorePercent": 90,
        "durationMs": 5000,
    }

    payload = run_benchmark.build_supatest_eval_dashboard_payload(
        "verify",
        ["E25"],
        ["supatest:premium", "cursor:auto"],
        1,
        600,
        [cursor_result, supatest_result],
    )

    assert payload["runName"] == "Benchmark verify"
    assert payload["durationMs"] == 6234
    assert payload["runMetadata"]["benchmarkRunId"] == "verify"
    assert payload["runMetadata"]["agents"] == ["supatest:premium", "cursor:auto"]
    assert payload["runMetadata"]["benchmarkAgents"] == [
        "supatest:premium",
        "cursor:auto",
    ]
    assert payload["runMetadata"]["reproducibility"]["benchmarkRunId"] == "verify"
    assert "diagnostics" in payload["runMetadata"]
    assert payload["runMetadata"]["qaBench"]["version"] == "qa-bench-v1"
    assert payload["runMetadata"]["qaBench"]["evals"]["E25"]["capability"] == (
        "test-authoring"
    )
    assert (
        "byCapability"
        in payload["runMetadata"]["qaBench"]["summary"]["byAgent"]["supatest:premium"]
    )
    assert "Agent | QA | Tok" in payload["runMetadata"]["scoreSummaryMarkdown"]
    assert "Time" in payload["runMetadata"]["scoreSummary"]["columns"]
    assert payload["runMetadata"]["scoreSummary"]["rows"][0]["overallScore"] == 98.5
    assert payload["runMetadata"]["scoreSummary"]["rows"][0]["totalTimeText"] == "1.2s"
    assert payload["runMetadata"]["scoreSummary"]["rows"][1]["agent"] == "cursor:auto"
    assert len(payload["results"]) == 2
    by_eval_id = {result["evalId"]: result for result in payload["results"]}
    uploaded = by_eval_id["summary:supatest-premium"]
    assert uploaded["evalId"] == "summary:supatest-premium"
    assert uploaded["evalName"] == "supatest [premium]"
    assert uploaded["evalCategory"] == "Agent Summary"
    assert uploaded["score"] == 98.5
    assert uploaded["durationMs"] == 1234
    assert (
        "| supatest [premium] | 100.0 | 95.0 | 1.0k | 0 | 0 | 1.2s | 98.5 | 1 | 0 | 0 |"
        in uploaded["logs"]
    )
    assert (
        "| cursor [auto] | 100.0 | 95.0 | 1.0k | 0 | 0 | 5.0s | 90.0 | 1 | 0 | 0 |"
        in uploaded["logs"]
    )
    assert uploaded["metadata"]["scoreSummary"]["agent"] == "supatest:premium"
    assert uploaded["metadata"]["scoreSummary"]["overallScore"] == 98.5
    assert uploaded["metadata"]["scoreSummary"]["tokenUsageText"] == "1.0k"
    assert uploaded["metadata"]["scoreSummary"]["cacheReadTokensText"] == "0"
    assert uploaded["metadata"]["scoreSummary"]["cacheCreationTokensText"] == "0"
    assert uploaded["metadata"]["scoreSummary"]["totalTimeText"] == "1.2s"
    assert by_eval_id["summary:cursor-auto"]["evalCategory"] == "Agent Summary"
    assert by_eval_id["summary:cursor-auto"]["score"] == 90.0


def test_supatest_eval_dashboard_payload_backfills_overall_score(
    monkeypatch,
) -> None:
    monkeypatch.setenv("BENCHMARK_OVERALL_QA_WEIGHT", "0.7")
    result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E25",
        "evalName": "Batch Tests Before Running",
        "agent": "supatest:premium",
        "mode": "build",
        "scorePercent": 100,
        "result": "pass",
        "reason": "ok",
        "scoreSource": "judge",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 1234,
        "changedFiles": [],
    }

    payload = run_benchmark.build_supatest_eval_dashboard_payload(
        "verify",
        ["E25"],
        ["supatest:premium"],
        1,
        600,
        [result],
    )

    uploaded = payload["results"][0]
    assert uploaded["metadata"]["scoreSummary"]["qaAvg"] == 100.0
    assert uploaded["metadata"]["scoreSummary"]["overallScore"] == 70.0
    assert uploaded["score"] == 70.0


def test_supatest_eval_dashboard_upload_posts_bearer_payload(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"id":"run"}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["content_type"] = request.get_header("Content-type")
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse()

    result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E25",
        "evalName": "Batch Tests Before Running",
        "agent": "supatest:premium",
        "mode": "build",
        "scorePercent": 100,
        "overallScorePercent": 90,
        "result": "pass",
        "reason": "ok",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 2000,
        "changedFiles": [],
    }
    cursor_result = {**result, "agent": "cursor:auto", "durationMs": 3000}
    monkeypatch.setenv("BENCHMARK_SUPATEST_EVAL_DASHBOARD_API_KEY", "sk_test_123")
    monkeypatch.setenv(
        "BENCHMARK_SUPATEST_EVAL_DASHBOARD_URL", "https://evals.example.com"
    )
    monkeypatch.setenv("BENCHMARK_SUPATEST_EVAL_DASHBOARD_RUN_NAME", "Run {run_id}")
    monkeypatch.setenv("BENCHMARK_SUPATEST_EVAL_DASHBOARD_TIMEOUT_SECONDS", "7")
    monkeypatch.setattr(run_benchmark.urllib.request, "urlopen", fake_urlopen)

    issue = run_benchmark.upload_supatest_eval_dashboard(
        "verify",
        ["E25"],
        ["cursor:auto", "supatest:premium"],
        1,
        600,
        [cursor_result, result],
    )

    assert issue is None
    assert captured["url"] == "https://evals.example.com/api/v1/ingest"
    assert captured["authorization"] == "Bearer sk_test_123"
    assert captured["content_type"] == "application/json"
    assert captured["timeout"] == 7
    assert captured["payload"]["runName"] == "Run verify"
    assert len(captured["payload"]["results"]) == 2
    assert {result["evalId"] for result in captured["payload"]["results"]} == {
        "summary:cursor-auto",
        "summary:supatest-premium",
    }


def test_supatest_eval_dashboard_upload_includes_non_supatest_results(
    monkeypatch,
) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"id":"run"}'

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode())
        captured["timeout"] = timeout
        return FakeResponse()

    result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E25",
        "evalName": "Batch Tests Before Running",
        "agent": "cursor:auto",
        "mode": "build",
        "scorePercent": 100,
        "overallScorePercent": 90,
        "result": "pass",
        "reason": "ok",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 2000,
        "changedFiles": [],
    }
    monkeypatch.setenv("BENCHMARK_SUPATEST_EVAL_DASHBOARD_API_KEY", "sk_test_123")
    monkeypatch.setattr(run_benchmark.urllib.request, "urlopen", fake_urlopen)

    issue = run_benchmark.upload_supatest_eval_dashboard(
        "verify",
        ["E25"],
        ["cursor:auto"],
        1,
        600,
        [result],
    )

    assert issue is None
    assert captured["payload"]["runMetadata"]["agents"] == ["cursor:auto"]
    assert captured["payload"]["results"][0]["evalId"] == "summary:cursor-auto"


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
            assert "expect(page.locator" in prompt
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
                            metricScores=[
                                JudgeMetricScore(
                                    metricId="relevance",
                                    score=1.0,
                                    reason="Specific to the requested behavior.",
                                ),
                                JudgeMetricScore(
                                    metricId="coverage",
                                    score=0.8,
                                    reason="Covers the main path.",
                                ),
                            ],
                            confidence=0.91,
                            evidence=["changedDiff shows a test edit"],
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
            "+expect(page.locator('[data-testid=\"checkout-button\"]')).toBeVisible()\n"
        ),
        "qaBench": {
            "metricIds": ["relevance", "coverage"],
            "weight": 1.0,
        },
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
    assert scored["qaBench"]["metricScores"] == {"relevance": 1.0, "coverage": 0.8}
    assert scored["qaBench"]["metricScoreSource"] == "batch-judge"
    assert scored["qaBench"]["metricReasons"]["coverage"] == "Covers the main path."
    assert scored["judgeDiagnostics"]["confidence"] == 0.91
    assert scored["judgeDiagnostics"]["evidence"] == ["changedDiff shows a test edit"]
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
    assert "enterprise QA benchmark judge" in prompt
    assert "objective evidence" in prompt


def test_batch_judge_prompt_includes_qa_review_hints_for_tests_and_fixes() -> None:
    result = {
        "runId": "verify",
        "caseId": "case-001",
        "evalId": "E12",
        "evalName": "Fix Inventory Sorting",
        "agent": "supatest",
        "mode": "fix",
        "exitCode": 0,
        "timedOut": False,
        "durationMs": 123,
        "changedFiles": [
            "pages/InventoryPage.ts",
            "tests/inventory-sort.spec.ts",
            "playwright-report/index.html",
        ],
        "changedDiff": (
            "--- a/pages/InventoryPage.ts\n"
            "+++ b/pages/InventoryPage.ts\n"
            "-await page.waitForTimeout(500)\n"
            "+await toast.waitFor({ state: 'visible' })\n"
            "--- a/tests/inventory-sort.spec.ts\n"
            "+++ b/tests/inventory-sort.spec.ts\n"
            "+await expect(items).toHaveText(['A', 'B'])\n"
        ),
        "artifactChecks": {
            "changedTestFiles": ["tests/inventory-sort.spec.ts"],
            "changedImplementationFiles": ["pages/InventoryPage.ts"],
            "changedMarkdownFiles": [],
            "changedNoiseFiles": [],
            "changedRelevantFiles": [
                "pages/InventoryPage.ts",
                "tests/inventory-sort.spec.ts",
            ],
            "ranVerificationCommand": True,
            "warnings": [],
        },
        "qaBench": {
            "difficulty": "low",
            "judgeGuidance": [
                "Low difficulty means baseline QA competency, not relaxed correctness."
            ],
            "qualitySignals": [
                "Assertions verify product behavior, not implementation trivia."
            ],
            "expectedSignals": [
                "Removes fixed waits and adds state-based synchronization."
            ],
            "antiPatterns": ["Keeps waitForTimeout or weakens the assertion."],
            "scoringNotes": [
                "Targeted repair plus regression coverage should score well."
            ],
            "metricIds": ["relevance", "assertion_quality"],
        },
        "passCriteria": ["removes the timeout", "adds coverage for sorting"],
        "failCriteria": ["weakens the assertion"],
    }
    test_case = LLMTestCase(
        input="Fix the flaky inventory sort test and add regression coverage.",
        actual_output="Exit code: 0\nTimed out: False\nChanged files include a page object and a spec.",
        expected_output=(
            "Pass criteria:\n"
            "- removes the timeout\n"
            "- adds coverage for sorting\n"
            "Fail criteria:\n"
            "- weakens the assertion"
        ),
    )

    prompt = run_benchmark.build_batch_judge_prompt(
        "verify",
        [result],
        [(0, test_case)],
        run_eval_ids=["E12"],
        run_agents=["supatest", "cursor"],
    )
    payload = json.loads(prompt[prompt.index('{\n  "runId"') :])
    hints = payload["cases"][0]["qaReviewHints"]

    assert "Generated or updated tests are first-class QA evidence" in prompt
    assert "identify the fixes the agent actually applied" in prompt
    assert "qaReviewHints.changeSignals are deterministic hints" in prompt
    assert "qaBench.expectedSignals" in prompt
    assert "qaBench.antiPatterns" in prompt
    assert "New tests are positive when they directly prove the regression" in prompt
    assert payload["cases"][0]["qaBench"]["difficulty"] == "low"
    assert (
        "baseline QA competency" in payload["cases"][0]["qaBench"]["judgeGuidance"][0]
    )
    assert payload["cases"][0]["qaBench"]["expectedSignals"]
    assert payload["cases"][0]["qaBench"]["antiPatterns"]
    assert hints["changedTestFiles"] == ["tests/inventory-sort.spec.ts"]
    assert hints["changedImplementationFiles"] == ["pages/InventoryPage.ts"]
    assert hints["generatedOrUpdatedTests"] is True
    assert hints["implementationTouched"] is True
    assert hints["reportArtifacts"] == ["playwright-report/index.html"]
    assert hints["changeSignals"]["fixedSleepRemoved"] is True
    assert hints["changeSignals"]["stateWaitAdded"] is True
    assert hints["changeSignals"]["assertionsAdded"] == 1
    assert "targeted tests" in hints["reviewFocus"]


def test_batch_judge_schema_avoids_metric_score_map_additional_properties() -> None:
    schema = BatchJudgeResponse.model_json_schema()
    metric_schema = schema["$defs"]["BatchJudgeCaseScore"]["properties"]["metricScores"]

    assert "additionalProperties" not in json.dumps(metric_schema)


def test_deterministic_artifact_cap_prevents_inflated_judge_score(
    monkeypatch,
) -> None:
    class InflatedJudge:
        def generate(self, _prompt, schema):
            assert schema is BatchJudgeResponse
            return (
                BatchJudgeResponse(
                    results=[
                        BatchJudgeCaseScore(
                            resultId="r001",
                            score=1.0,
                            result="pass",
                            passedChecks=2,
                            failedChecks=0,
                            reason="Looks good.",
                        )
                    ]
                ),
                0,
            )

    monkeypatch.setattr(run_benchmark, "make_judge_model", lambda: InflatedJudge())
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
        "artifactWarnings": ["expected-artifact-change-missing"],
        "artifactChecks": {"warnings": ["expected-artifact-change-missing"]},
        "passCriteria": ["adds a relevant test"],
        "failCriteria": [],
    }
    pending = run_benchmark.PendingResult(
        result,
        LLMTestCase(
            input="Add a QA test",
            actual_output="Exit code: 0\nTimed out: False\nNo changed files.",
            expected_output="Pass criteria:\n- adds a relevant test",
        ),
    )

    scored = run_benchmark.score_pending_results("verify", [pending])[0]

    assert scored["scorePercent"] == 39
    assert scored["result"] == "fail"
    assert scored["scoreSource"] == "batch-judge+deterministic-cap"
    assert scored["failedChecks"] == 1
    assert scored["judgeDiagnostics"]["deterministicCaps"]["reasons"] == [
        "expected artifact change missing"
    ]
    assert scored["deterministicGrade"]["failedCheckIds"] == [
        "expected-artifact-change"
    ]
    assert scored["judgeDiagnostics"]["deterministicChecks"][0]["id"] == (
        "expected-artifact-change"
    )


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
