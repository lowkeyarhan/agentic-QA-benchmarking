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
            r"\b(npx\s+playwright|playwright\s+test|node\s+(?:\./)?verify-fix\.mjs|npm\s+(test|run)|pnpm\s+(test|run)|yarn\s+(test|run)|vitest|cypress|wdio|maestro\s+test|pytest)\b",
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

    playwright_metadata = build_playwright_metadata_checks(
        fixture, run, changed_test_files
    )

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
        "playwrightMetadata": playwright_metadata,
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
    if explicitly_allows_no_artifact_change(text):
        return False
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


def explicitly_allows_no_artifact_change(text: str) -> bool:
    no_change_phrases = (
        "no cosmetic diff",
        "without making a cosmetic edit",
        "without a cosmetic edit",
        "does not rewrite identical",
        "do not rewrite identical",
        "current source already satisfies",
        "current files already satisfy",
        "failure log as stale",
        "failure log is stale",
        "stale evidence",
    )
    return any(phrase in text for phrase in no_change_phrases)


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


REQUIRED_PLAYWRIGHT_METADATA_TAGS = ("@feature:", "@priority:", "@test_type:")


def build_playwright_metadata_checks(
    fixture, run, changed_test_files: list[str]
) -> dict:
    required_tags = list(REQUIRED_PLAYWRIGHT_METADATA_TAGS)
    required = requires_playwright_metadata_tags(fixture)
    check = {
        "required": required,
        "passed": None,
        "requiredTags": required_tags,
        "files": [],
        "totalTests": 0,
        "taggedTests": 0,
        "missing": [],
    }
    if not required:
        return check

    project_dir = getattr(run, "project_dir", None)
    if not project_dir:
        check["passed"] = False
        check["missing"].append(
            {
                "file": None,
                "test": None,
                "missingTags": required_tags,
                "reason": "project directory unavailable",
            }
        )
        return check

    playwright_files = [
        path
        for path in changed_test_files
        if path.lower().endswith((".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx"))
    ]
    if not playwright_files:
        check["passed"] = False
        check["missing"].append(
            {
                "file": None,
                "test": None,
                "missingTags": required_tags,
                "reason": "no changed Playwright spec files",
            }
        )
        return check

    root = Path(project_dir)
    for relative in playwright_files:
        path = root / relative
        if not path.exists() or not path.is_file():
            file_check = {
                "file": relative,
                "totalTests": 0,
                "taggedTests": 0,
                "missing": [
                    {
                        "file": relative,
                        "test": None,
                        "missingTags": required_tags,
                        "reason": "changed spec file unavailable",
                    }
                ],
            }
        else:
            file_check = analyze_playwright_metadata_file(relative, path.read_text())
        check["files"].append(file_check)
        check["totalTests"] += file_check["totalTests"]
        check["taggedTests"] += file_check["taggedTests"]
        check["missing"].extend(file_check["missing"])

    check["passed"] = check["totalTests"] > 0 and not check["missing"]
    return check


def requires_playwright_metadata_tags(fixture) -> bool:
    text = fixture_expectation_text(fixture)
    qa_bench = getattr(fixture, "qa_bench", None)
    qa_bench = qa_bench if isinstance(qa_bench, dict) else {}
    if qa_bench.get("capability") == "metadata-governance":
        return True
    metadata_terms = (
        "metadata object",
        "tag:",
        "@feature:",
        "@priority:",
        "@test_type:",
    )
    return (
        "playwright" in text
        and "every test" in text
        and any(term in text for term in metadata_terms)
    )


def analyze_playwright_metadata_file(relative: str, text: str) -> dict:
    resolvers = build_metadata_resolvers(text)
    missing = []
    total_tests = 0
    tagged_tests = 0

    for call in iter_playwright_test_calls(text):
        total_tests += 1
        args = split_top_level_args(call["args"])
        title = first_string_literal(args[0]) if args else f"line {call['line']}"
        metadata_arg = args[1].strip() if len(args) >= 3 else ""
        tags = extract_metadata_tags(metadata_arg, resolvers)
        missing_tags = [
            tag for tag in REQUIRED_PLAYWRIGHT_METADATA_TAGS if not has_tag(tags, tag)
        ]
        if missing_tags:
            missing.append(
                {
                    "file": relative,
                    "line": call["line"],
                    "test": title,
                    "missingTags": missing_tags,
                }
            )
        else:
            tagged_tests += 1

    return {
        "file": relative,
        "totalTests": total_tests,
        "taggedTests": tagged_tests,
        "missing": missing,
    }


def build_metadata_resolvers(text: str) -> dict[str, set[str]]:
    resolvers: dict[str, set[str]] = {}
    for match in re.finditer(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=", text):
        name = match.group(1)
        tags = extract_assignment_tags(text, match.end())
        if tags:
            resolvers[name] = tags

    for match in re.finditer(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(", text):
        name = match.group(1)
        body_start = text.find("{", match.end())
        if body_start == -1:
            continue
        body_end = find_matching(text, body_start, "{", "}")
        if body_end is None:
            continue
        body = text[body_start : body_end + 1]
        tags = extract_returned_tags(body)
        if tags:
            resolvers[name] = tags
    return resolvers


def extract_assignment_tags(text: str, start_index: int) -> set[str]:
    statement_end = find_statement_end(text, start_index)
    statement = text[start_index:statement_end]
    arrow_index = statement.find("=>")
    if arrow_index != -1:
        tags = extract_returned_tags(statement[arrow_index + 2 :])
        if tags:
            return tags
    stripped = statement.strip()
    if stripped.startswith("{"):
        end = find_matching(stripped, 0, "{", "}")
        if end is not None:
            return literal_tags(stripped[: end + 1])
    return set()


def extract_returned_tags(text: str) -> set[str]:
    brace_index = text.find("{")
    while brace_index != -1:
        end = find_matching(text, brace_index, "{", "}")
        if end is None:
            return set()
        tags = literal_tags(text[brace_index : end + 1])
        if tags:
            return tags
        brace_index = text.find("{", end + 1)
    return set()


def iter_playwright_test_calls(text: str) -> list[dict]:
    calls = []
    pattern = re.compile(r"(?<![\w.])test(?:\.(?:only|skip|fixme))?\s*\(")
    for match in pattern.finditer(text):
        open_index = match.end() - 1
        close_index = find_matching(text, open_index, "(", ")")
        if close_index is None:
            continue
        calls.append(
            {
                "args": text[open_index + 1 : close_index],
                "line": text.count("\n", 0, match.start()) + 1,
            }
        )
    return calls


def split_top_level_args(args: str) -> list[str]:
    parts: list[str] = []
    start = 0
    stack: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(args):
        char = args[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char in "([{":
            stack.append({")": "(", "]": "[", "}": "{"}.get(char, char))
        elif char in ")]}":
            if stack:
                stack.pop()
        elif char == "," and not stack:
            parts.append(args[start:index].strip())
            start = index + 1
        index += 1
    tail = args[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def extract_metadata_tags(
    metadata_arg: str, resolvers: dict[str, set[str]]
) -> set[str]:
    stripped = metadata_arg.strip()
    if not stripped:
        return set()
    if stripped.startswith("{"):
        end = find_matching(stripped, 0, "{", "}")
        return literal_tags(stripped[: end + 1] if end is not None else stripped)

    identifier = re.match(r"^([A-Za-z_$][\w$]*)$", stripped)
    if identifier:
        return resolvers.get(identifier.group(1), set())

    call = re.match(r"^([A-Za-z_$][\w$]*)\s*\(", stripped)
    if call:
        return resolvers.get(call.group(1), set())

    return set()


def literal_tags(text: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(r"""['"`](@[A-Za-z0-9_-]+:[^'"`,\]\s}]+)""", text)
    }


def has_tag(tags: set[str], required_prefix: str) -> bool:
    return any(tag.startswith(required_prefix) for tag in tags)


def first_string_literal(text: str) -> str:
    match = re.search(r"""['"`]([^'"`]+)['"`]""", text)
    return match.group(1) if match else text.strip()[:80]


def find_statement_end(text: str, start_index: int) -> int:
    quote: str | None = None
    escaped = False
    stack: list[str] = []
    index = start_index
    while index < len(text):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char in "([{":
            stack.append(char)
        elif char in ")]}":
            if stack:
                stack.pop()
        elif char == ";" and not stack:
            return index
        index += 1
    return len(text)


def find_matching(
    text: str, open_index: int, open_char: str, close_char: str
) -> int | None:
    quote: str | None = None
    escaped = False
    depth = 0
    index = open_index
    while index < len(text):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None
