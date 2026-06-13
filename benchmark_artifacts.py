from __future__ import annotations

import difflib
import re
from pathlib import Path


def build_changed_diff(
    source_project_dir: Path,
    run_project_dir: Path,
    changed_files: list[str],
    max_chars: int = 32000,
) -> str:
    chunks: list[str] = []
    remaining = max_chars
    for relative in sorted(changed_files, key=changed_file_diff_priority):
        if is_noise_file(relative):
            continue
        before_path = source_project_dir / relative
        after_path = run_project_dir / relative
        before_lines = read_text_lines_for_diff(before_path)
        after_lines = read_text_lines_for_diff(after_path)
        if before_lines is None and after_lines is None:
            continue
        diff_lines = list(
            difflib.unified_diff(
                before_lines or [],
                after_lines or [],
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
                lineterm="",
            )
        )
        if not diff_lines:
            continue
        piece = "\n".join(diff_lines) + "\n"
        chunks.append(piece[:remaining])
        remaining -= len(piece)
        if remaining <= 0:
            chunks.append(f"\n...[diff truncated at {max_chars} chars]...\n")
            break
    return "".join(chunks)[:max_chars]


def read_text_lines_for_diff(path: Path) -> list[str] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return ["<binary file>\n"]
    return data.decode(errors="replace").splitlines()


def changed_file_diff_priority(relative: str) -> tuple[int, str]:
    if is_test_file(relative):
        return (0, relative)
    if is_implementation_file(relative):
        return (1, relative)
    if relative.lower().endswith(".md"):
        return (2, relative)
    return (3, relative)


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
    if fixture.mode == "plan":
        return False
    if fixture.mode == "report":
        return True
    if explicitly_requires_artifact_change(text):
        return True
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
    if fixture.mode in {"build", "fix", "test-feature"}:
        return True
    return explicitly_requires_artifact_change(text)


def explicitly_requires_artifact_change(text: str) -> bool:
    file_extensions = r"(?:md|ts|tsx|js|jsx|py|json|html|txt|yaml|yml)"
    patterns = [
        rf"\b(?:edit|update|modify|fix|implement)\s+[^.\n]*\.{file_extensions}\b",
        rf"\b(?:write|create|generate|produce)\s+[^.\n]*\.{file_extensions}\b",
        r"\bcreates\s+\.supatest/reports/",
        r"\b(?:write|create|add)s?\s+(?:a\s+)?(?:playwright|webdriverio|cypress|maestro\s+)?tests?\b",
        r"\b(?:write|create|add)s?\s+[^.\n]*test files?\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


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
