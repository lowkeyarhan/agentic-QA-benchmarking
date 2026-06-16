from __future__ import annotations

import re


def build_deterministic_grade(result: dict) -> dict:
    checks: list[dict] = []
    caps: list[dict] = []
    diff = str(result.get("changedDiff") or "")
    evidence = str(result.get("evidence") or "")
    mode = str(result.get("mode") or "")
    artifact_checks = result.get("artifactChecks") or {}
    warnings = result.get("artifactWarnings") or artifact_checks.get("warnings") or []
    changed_files = result.get("changedFiles") or []
    telemetry = result.get("telemetry") or {}
    task_text = benchmark_text(result)

    if "expected-artifact-change-missing" in warnings:
        add_failed_check(
            checks,
            caps,
            "expected-artifact-change",
            "expected artifact change missing",
            0.39,
        )
    if "only-noisy-files-changed" in warnings:
        add_failed_check(
            checks,
            caps,
            "no-noisy-artifacts-only",
            "only noisy files changed",
            0.39,
        )
    if "verification-command-not-observed" in warnings:
        add_failed_check(
            checks,
            caps,
            "verification-observed",
            "verification command not observed",
            0.69,
        )

    if added_fixed_wait_violations(diff, task_text):
        add_failed_check(
            checks,
            caps,
            "no-fixed-waits",
            "Changed diff adds fixed waits or arbitrary sleeps.",
            0.59,
        )
    if added_line_matches(diff, only_pattern()):
        add_failed_check(
            checks,
            caps,
            "no-skip-or-only",
            "Changed diff adds only markers.",
            0.49,
        )
    if added_line_matches(diff, skip_pattern()) and not allows_documented_skip(task_text):
        add_failed_check(
            checks,
            caps,
            "no-skip-or-only",
            "Changed diff adds skip markers without an explicit documented-skip contract.",
            0.49,
        )
    if added_line_matches(diff, trivial_assertion_pattern()):
        add_failed_check(
            checks,
            caps,
            "no-trivial-assertions",
            "Changed diff adds trivial assertions.",
            0.49,
        )
    if added_line_matches(diff, swallowed_failure_pattern()):
        add_failed_check(
            checks,
            caps,
            "no-swallowed-failures",
            "Changed diff adds try/catch or guard patterns that can swallow test failures.",
            0.59,
        )

    if mode == "plan" and changed_files:
        add_failed_check(
            checks,
            caps,
            "plan-read-only",
            "Plan mode changed project files.",
            0.39,
        )
    if mode == "plan" and telemetry.get("didRunTests"):
        add_failed_check(
            checks,
            caps,
            "plan-no-test-run",
            "Plan mode ran tests.",
            0.39,
        )

    if expects_no_spec_files(task_text, mode) and (
        artifact_checks.get("changedTestFiles") or []
    ):
        add_failed_check(
            checks,
            caps,
            "no-spec-files-when-forbidden",
            "Task forbids automation/spec files but test files changed.",
            0.39,
        )
    if expects_no_test_run(task_text, mode) and (
        artifact_checks.get("ranVerificationCommand") or telemetry.get("didRunTests")
    ):
        add_failed_check(
            checks,
            caps,
            "no-test-run-when-forbidden",
            "Task forbids test execution but a test command was observed.",
            0.39,
        )
    if expects_implementation_change(task_text) and not (
        artifact_checks.get("changedImplementationFiles") or []
    ):
        add_failed_check(
            checks,
            caps,
            "implementation-change-required",
            "Task requires implementation/root-cause file changes, but no implementation file changed.",
            0.39,
        )

    if requires_report_artifact(task_text, mode) and not has_report_artifact(
        changed_files
    ):
        add_failed_check(
            checks,
            caps,
            "report-artifact-required",
            "Task requires a report artifact, but no report artifact changed.",
            0.49,
        )

    if forbids_adb_bash(task_text) and command_text_contains(
        telemetry, evidence, ("adb ", "xcrun ", "simctl")
    ):
        add_failed_check(
            checks,
            caps,
            "mobile-no-adb-bash",
            "Task forbids adb/xcrun-style inspection, but command evidence indicates it was used.",
            0.39,
        )
    if requires_maestro_inspect(task_text) and not command_text_contains(
        telemetry,
        evidence,
        (
            "mcp__maestro__inspect_view_hierarchy",
            "inspect_view_hierarchy",
            "inspect_screen",
        ),
    ):
        add_failed_check(
            checks,
            caps,
            "maestro-inspect-required",
            "Task requires mobile hierarchy inspection, but no inspect call was observed.",
            0.69,
        )

    passed_checks = infer_passed_checks(checks, result, diff, artifact_checks)
    checks.extend(passed_checks)
    return {
        "checks": checks,
        "caps": caps,
        "cap": min((item["cap"] for item in caps), default=None),
        "failedCheckIds": [item["id"] for item in checks if item["status"] == "failed"],
    }


def add_failed_check(
    checks: list[dict], caps: list[dict], check_id: str, evidence: str, cap: float
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": "failed",
            "evidence": evidence,
            "cap": cap,
        }
    )
    caps.append({"checkId": check_id, "cap": cap, "reason": evidence})


def infer_passed_checks(
    checks: list[dict], result: dict, diff: str, artifact_checks: dict
) -> list[dict]:
    failed_ids = {check["id"] for check in checks if check.get("status") == "failed"}
    passed: list[dict] = []
    if "no-fixed-waits" not in failed_ids and diff:
        passed.append({"id": "no-fixed-waits", "status": "passed"})
    if "no-skip-or-only" not in failed_ids and diff:
        passed.append({"id": "no-skip-or-only", "status": "passed"})
    if "no-trivial-assertions" not in failed_ids and diff:
        passed.append({"id": "no-trivial-assertions", "status": "passed"})
    if artifact_checks.get("ranVerificationCommand"):
        passed.append({"id": "verification-observed", "status": "passed"})
    if result.get("mode") == "plan" and not (result.get("changedFiles") or []):
        passed.append({"id": "plan-read-only", "status": "passed"})
    return passed


def benchmark_text(result: dict) -> str:
    return "\n".join(
        [
            str(result.get("task") or ""),
            "\n".join(result.get("passCriteria") or []),
            "\n".join(result.get("failCriteria") or []),
        ]
    ).lower()


def added_line_matches(diff: str, pattern: re.Pattern) -> bool:
    return any(
        pattern.search(line[1:])
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def added_fixed_wait_violations(diff: str, task_text: str) -> list[str]:
    pattern = fixed_wait_pattern()
    violations: list[str] = []
    for file_path, section in diff_file_sections(diff).items():
        for line in section["added"]:
            if not pattern.search(line):
                continue
            if is_existing_async_implementation_timer(file_path, section, line, task_text):
                continue
            violations.append(f"{file_path}:{line.strip()}")
    return violations


def diff_file_sections(diff: str) -> dict[str, dict[str, list[str]]]:
    sections: dict[str, dict[str, list[str]]] = {}
    current_file = ""

    def current_section() -> dict[str, list[str]]:
        if current_file not in sections:
            sections[current_file] = {"added": [], "removed": []}
        return sections[current_file]

    for raw_line in diff.splitlines():
        if raw_line.startswith("+++ "):
            current_file = normalize_diff_path(raw_line[4:].strip())
            current_section()
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            current_section()["added"].append(raw_line[1:])
            continue
        if raw_line.startswith("-") and not raw_line.startswith("---"):
            current_section()["removed"].append(raw_line[1:])

    return sections


def normalize_diff_path(path: str) -> str:
    if path == "/dev/null":
        return ""
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def is_existing_async_implementation_timer(
    file_path: str, section: dict[str, list[str]], line: str, task_text: str
) -> bool:
    if "settimeout" not in line.lower():
        return False
    if not file_path or is_test_path(file_path):
        return False
    added_text = "\n".join(section["added"]).lower()
    removed_text = "\n".join(section["removed"]).lower()
    return (
        "settimeout" in removed_text
        and "new promise" in added_text
        and "resolve" in added_text
        and task_suggests_async_timing_fix(task_text)
    )


def is_test_path(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    parts = normalized.split("/")
    return (
        "tests" in parts
        or "test" in parts
        or "e2e" in parts
        or normalized.endswith(
            (
                ".spec.ts",
                ".spec.tsx",
                ".spec.js",
                ".spec.jsx",
                ".test.ts",
                ".test.tsx",
                ".test.js",
                ".test.jsx",
            )
        )
    )


def task_suggests_async_timing_fix(task_text: str) -> bool:
    return any(
        needle in task_text
        for needle in (
            "async",
            "await",
            "delayed",
            "eventual",
            "flaky",
            "load",
            "loader",
            "promise",
            "race",
            "timing",
            "timeout",
            "wait",
        )
    )


def fixed_wait_pattern() -> re.Pattern:
    return re.compile(r"\b(waitForTimeout|sleep|setTimeout|cy\.wait)\s*\(", re.I)


def skip_pattern() -> re.Pattern:
    return re.compile(r"\b(test|it|describe)\.skip\s*\(|\.skip\s*\(")


def only_pattern() -> re.Pattern:
    return re.compile(r"\b(test|it|describe)\.only\s*\(|\.only\s*\(")


def allows_documented_skip(task_text: str) -> bool:
    has_skip_contract = (
        "test.skip" in task_text
        or "skipped test" in task_text
        or "skip with" in task_text
        or "skipped todo" in task_text
    )
    has_documentation_contract = (
        "todo" in task_text
        or "detailed" in task_text
        or "explanation" in task_text
        or "explaining" in task_text
    )
    return has_skip_contract and has_documentation_contract


def trivial_assertion_pattern() -> re.Pattern:
    return re.compile(
        r"expect\s*\(\s*(true|1)\s*\)|assert\s*\(\s*true\s*\)|toBe\s*\(\s*true\s*\)",
        re.I,
    )


def swallowed_failure_pattern() -> re.Pattern:
    return re.compile(r"\btry\s*\{|catch\s*\(|shouldContinue|continueOnFailure", re.I)


def expects_no_spec_files(task_text: str, mode: str) -> bool:
    return (
        "do not write any automation" in task_text
        or "no .spec.ts" in task_text
        or "does not create test files" in task_text
        or "do not create files" in task_text
        or "do not create or edit files" in task_text
        or mode in {"plan"}
    )


def expects_no_test_run(task_text: str, mode: str) -> bool:
    return (
        "do not run" in task_text
        or "does not run" in task_text
        or "authoring only" in task_text
        or "do not execute" in task_text
        or mode in {"plan", "report"}
    )


def expects_implementation_change(task_text: str) -> bool:
    return (
        "implementation file" in task_text
        or "bug is in src/" in task_text
        or "at least one non-test file" in task_text
        or "no implementation file changes" in task_text
        or "git diff shows zero implementation file changes" in task_text
    )


def requires_report_artifact(task_text: str, mode: str) -> bool:
    return (
        mode == "report"
        or "generates html report" in task_text
        or "generates report" in task_text
        or ".supatest/reports" in task_text
    )


def has_report_artifact(changed_files: list[str]) -> bool:
    return any(
        "/reports/" in path.lower()
        or path.lower().startswith((".supatest/reports/", "reports/"))
        or path.lower().endswith(".html")
        and "report" in path.lower()
        for path in changed_files
    )


def forbids_adb_bash(task_text: str) -> bool:
    return "adb" in task_text or "xcrun" in task_text


def requires_maestro_inspect(task_text: str) -> bool:
    return (
        "inspect_view_hierarchy" in task_text
        or "inspect_screen" in task_text
        or "live app's view hierarchy" in task_text
        or "live device" in task_text
    )


def command_text_contains(
    telemetry: dict, evidence: str, needles: tuple[str, ...]
) -> bool:
    text = "\n".join(
        [
            str(evidence or ""),
            str(telemetry.get("firstTool") or ""),
            str(telemetry.get("firstShellCommand") or ""),
            str(telemetry.get("lastCommandCategory") or ""),
            " ".join((telemetry.get("toolCounts") or {}).keys()),
        ]
    ).lower()
    return any(needle.lower() in text for needle in needles)
