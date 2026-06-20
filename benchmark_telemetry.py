from __future__ import annotations

import json
import os
import re
from pathlib import Path

from agents import agent_model_label
from benchmark_tokens import (
    normalize_usage_key,
    parse_numeric_value,
    parse_token_usage_json,
    set_max_usage_value,
)


def empty_eval_telemetry() -> dict:
    return {
        "taskKind": None,
        "harnessProfile": None,
        "selectedModel": None,
        "resolvedModel": None,
        "provider": None,
        "turns": None,
        "sdkDurationMs": None,
        "costUsd": None,
        "inputTokens": None,
        "outputTokens": None,
        "cacheReadTokens": None,
        "cacheCreationTokens": None,
        "totalTokens": None,
        "toolCounts": {},
        "commandCategories": {},
        "firstTool": None,
        "firstShellCommand": None,
        "didWrite": False,
        "didRunTests": False,
        "didUseBrowser": False,
        "didAskUser": False,
        "deniedPolicyCount": 0,
        "eventCount": 0,
        "eventTypes": {},
        "malformedJsonLines": 0,
    }


def build_eval_telemetry(
    agent: str,
    transcript_path: Path,
    case_run_dir: Path,
    duration_ms: int | None = None,
) -> dict:
    telemetry = empty_eval_telemetry()
    telemetry["selectedModel"] = agent_model_label(agent)
    if duration_ms is not None:
        telemetry["wallDurationMs"] = duration_ms

    parsed_sources = []
    for source_name, path in telemetry_candidate_paths(transcript_path, case_run_dir):
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if len(text) > 2_000_000:
            text = text[-2_000_000:]
        events, malformed_count = parse_structured_events(text)
        if not events and malformed_count == 0:
            continue
        parsed_sources.append(source_name)
        telemetry["malformedJsonLines"] += malformed_count
        for event in events:
            merge_telemetry_event(telemetry, event)

    if parsed_sources:
        telemetry["source"] = ", ".join(dict.fromkeys(parsed_sources))
    else:
        telemetry["source"] = None
    return telemetry


def telemetry_candidate_paths(
    transcript_path: Path, case_run_dir: Path
) -> list[tuple[str, Path]]:
    return [
        ("transcript", transcript_path),
        ("run-telemetry-json", case_run_dir / "telemetry.json"),
        ("run-telemetry-jsonl", case_run_dir / "telemetry.jsonl"),
        ("run-usage-jsonl", case_run_dir / "usage.jsonl"),
        ("run-commands-json", case_run_dir / "commands.json"),
        ("run-supatest-commands-json", case_run_dir / ".supatest" / "commands.json"),
        ("project-supatest-commands-json", case_run_dir / "project" / ".supatest" / "commands.json"),
        ("run-supatest-telemetry-json", case_run_dir / ".supatest" / "telemetry.json"),
        (
            "run-supatest-telemetry-jsonl",
            case_run_dir / ".supatest" / "telemetry.jsonl",
        ),
        ("project-telemetry-json", case_run_dir / "project" / "telemetry.json"),
        ("project-telemetry-jsonl", case_run_dir / "project" / "telemetry.jsonl"),
        (
            "project-supatest-telemetry-json",
            case_run_dir / "project" / ".supatest" / "telemetry.json",
        ),
        (
            "project-supatest-telemetry-jsonl",
            case_run_dir / "project" / ".supatest" / "telemetry.jsonl",
        ),
    ]


def parse_structured_events(text: str) -> tuple[list[object], int]:
    stripped = text.strip()
    if not stripped:
        return [], 0

    if stripped.startswith(("{", "[")):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            pass
        else:
            return normalize_event_container(parsed), 0

    events: list[object] = []
    malformed = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith(("{", "[")):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        events.extend(normalize_event_container(parsed))
    return events, malformed


def normalize_event_container(value) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("events", "messages", "items"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
        return [value]
    return []


def merge_telemetry_event(telemetry: dict, event) -> None:
    if not isinstance(event, dict):
        return

    telemetry["eventCount"] += 1
    event_type = normalized_event_type(event)
    if event_type:
        event_types = telemetry.setdefault("eventTypes", {})
        event_types[event_type] = int(event_types.get(event_type, 0)) + 1

    assign_first_string(
        telemetry, "taskKind", first_nested_string(event, "taskKind", "task_kind")
    )
    assign_first_string(
        telemetry,
        "harnessProfile",
        first_nested_string(event, "harnessProfile", "harness_profile"),
    )
    assign_first_string(telemetry, "provider", first_nested_string(event, "provider"))
    assign_model_fields(telemetry, event, event_type)
    assign_numeric_telemetry_fields(telemetry, event)

    for nested_event in nested_tool_use_events(event):
        merge_telemetry_event(telemetry, nested_event)

    if is_policy_denial_event(event, event_type):
        telemetry["deniedPolicyCount"] = (
            int(telemetry.get("deniedPolicyCount") or 0) + 1
        )

    if is_ask_user_event(event, event_type):
        telemetry["didAskUser"] = True

    if not is_tool_use_event(event, event_type):
        return

    tool_name = extract_tool_name(event) or "unknown"
    tool_counts = telemetry.setdefault("toolCounts", {})
    tool_counts[tool_name] = int(tool_counts.get(tool_name, 0)) + 1
    if not telemetry.get("firstTool"):
        telemetry["firstTool"] = tool_name

    normalized_tool = normalize_usage_key(tool_name)
    if normalized_tool in {
        "write",
        "edit",
        "multiedit",
        "applypatch",
        "strreplaceeditor",
    }:
        telemetry["didWrite"] = True
    if "browser" in normalized_tool or "playwright" in normalized_tool:
        telemetry["didUseBrowser"] = True
    if "ask" in normalized_tool and "user" in normalized_tool:
        telemetry["didAskUser"] = True

    command = extract_shell_command(event)
    if command:
        if not telemetry.get("firstShellCommand"):
            telemetry["firstShellCommand"] = safe_command_excerpt(command)
        category = categorize_shell_command(command)
        if category:
            command_categories = telemetry.setdefault("commandCategories", {})
            command_categories[category] = int(command_categories.get(category, 0)) + 1
        if command_runs_tests(command):
            telemetry["didRunTests"] = True
        if command_uses_browser(command):
            telemetry["didUseBrowser"] = True
        if command_writes_files(command):
            telemetry["didWrite"] = True


def nested_tool_use_events(event: dict) -> list[dict]:
    message = event.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [
        item
        for item in content
        if isinstance(item, dict)
        and str(item.get("type") or "").lower()
        in {"tool_use", "tool-call", "tool_call"}
    ]


def normalized_event_type(event: dict) -> str | None:
    for key in ("type", "event", "kind"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            subtype = event.get("subtype")
            if isinstance(subtype, str) and subtype.strip():
                return f"{value.strip()}/{subtype.strip()}".lower()
            return value.strip().lower()
    return None


def assign_first_string(telemetry: dict, key: str, value: str | None) -> None:
    if value and not telemetry.get(key):
        telemetry[key] = value


def assign_model_fields(telemetry: dict, event: dict, event_type: str | None) -> None:
    selected = first_nested_string(event, "selectedModel", "selected_model")
    resolved = first_nested_string(event, "resolvedModel", "resolved_model")
    model = first_nested_string(event, "model")

    if selected and not telemetry.get("selectedModel"):
        telemetry["selectedModel"] = selected
    if resolved and not telemetry.get("resolvedModel"):
        telemetry["resolvedModel"] = resolved
    if model:
        if event_type and ("result" in event_type or "final" in event_type):
            assign_first_string(telemetry, "resolvedModel", model)
        else:
            assign_first_string(telemetry, "selectedModel", model)


def assign_numeric_telemetry_fields(telemetry: dict, event: dict) -> None:
    numeric_mappings = {
        "turns": ("turns", "numTurns", "num_turns", "turnCount", "turn_count"),
        "sdkDurationMs": (
            "durationMs",
            "duration_ms",
            "sdkDurationMs",
            "sdk_duration_ms",
        ),
        "costUsd": ("costUsd", "cost_usd", "totalCostUsd", "total_cost_usd"),
        "cacheReadTokens": ("cacheReadInputTokens", "cache_read_input_tokens"),
        "cacheCreationTokens": (
            "cacheCreationInputTokens",
            "cache_creation_input_tokens",
        ),
        "contextSeedBytes": ("contextSeedBytes", "context_seed_bytes"),
        "filesModifiedCount": ("filesModifiedCount", "files_modified_count"),
    }
    for target, keys in numeric_mappings.items():
        value = first_nested_number(event, *keys)
        if value is None:
            continue
        set_max_usage_value(
            telemetry, target, int(value) if float(value).is_integer() else float(value)
        )

    usage = parse_token_usage_json(event)
    token_mappings = {
        "inputTokens": "inputTokens",
        "outputTokens": "outputTokens",
        "totalTokens": "totalTokens",
    }
    for telemetry_key, usage_key in token_mappings.items():
        value = usage.get(usage_key)
        if value is not None:
            set_max_usage_value(telemetry, telemetry_key, value)


def first_nested_string(value, *keys: str) -> str | None:
    normalized_keys = {normalize_usage_key(key) for key in keys}
    for found in walk_nested_values(value, normalized_keys):
        if isinstance(found, str) and found.strip():
            return found.strip()
    return None


def first_nested_number(value, *keys: str) -> float | None:
    normalized_keys = {normalize_usage_key(key) for key in keys}
    for found in walk_nested_values(value, normalized_keys):
        number = parse_numeric_value(found)
        if number is not None:
            return number
    return None


def walk_nested_values(value, normalized_keys: set[str]):
    if isinstance(value, dict):
        for raw_key, raw_value in value.items():
            if normalize_usage_key(str(raw_key)) in normalized_keys:
                yield raw_value
            yield from walk_nested_values(raw_value, normalized_keys)
    elif isinstance(value, list):
        for item in value:
            yield from walk_nested_values(item, normalized_keys)


def is_policy_denial_event(event: dict, event_type: str | None) -> bool:
    haystack = " ".join(
        str(value)
        for key, value in event.items()
        if key.lower() in {"type", "event", "kind", "message", "reason", "code"}
    ).lower()
    return bool(
        (event_type and "policy" in event_type and "den" in event_type)
        or ("policy" in haystack and ("denied" in haystack or "denial" in haystack))
    )


def is_ask_user_event(event: dict, event_type: str | None) -> bool:
    if event_type and ("ask" in event_type or "question" in event_type):
        return True
    tool_name = extract_tool_name(event)
    return bool(tool_name and "ask" in normalize_usage_key(tool_name))


def is_tool_use_event(event: dict, event_type: str | None) -> bool:
    if event_type and any(
        marker in event_type
        for marker in ("tool_use", "tool-call", "toolcall", "tool_call")
    ):
        return True
    if (
        event_type
        and "tool" in event_type
        and not any(marker in event_type for marker in ("result", "response", "output"))
    ):
        return True
    return extract_tool_name(event) is not None and (
        "input" in event or "arguments" in event or "args" in event
    )


def extract_tool_name(event: dict) -> str | None:
    for key in ("toolName", "tool_name", "name", "tool"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key, tool_name in (
        ("shellToolCall", "Bash"),
        ("editToolCall", "Edit"),
        ("readFileToolCall", "Read"),
        ("readLintsToolCall", "ReadLints"),
        ("listDirToolCall", "LS"),
        ("grepToolCall", "Grep"),
    ):
        if key in event:
            return tool_name
    for key in ("toolCall", "tool_call", "call"):
        value = event.get(key)
        if isinstance(value, dict):
            nested = extract_tool_name(value)
            if nested:
                return nested
    for value in event.values():
        if isinstance(value, dict):
            nested = extract_tool_name(value)
            if nested:
                return nested
    return None


def extract_shell_command(event: dict) -> str | None:
    tool_name = normalize_usage_key(extract_tool_name(event) or "")
    command = first_nested_string(event, "command", "cmd")
    if command and (
        tool_name in {"bash", "shell", "terminal", "command", "runcommand"}
        or "bash" in tool_name
        or "shell" in tool_name
    ):
        return command
    return command if looks_like_shell_command(command or "") else None


def looks_like_shell_command(command: str) -> bool:
    return bool(
        re.match(
            r"^\s*(git|rg|grep|find|ls|pwd|cat|sed|awk|npm|pnpm|yarn|npx|pytest|python|tsx|node|maestro|wdio|playwright|cypress)\b",
            command,
        )
    )


def safe_command_excerpt(command: str, max_chars: int = 240) -> str:
    redacted = redact_configured_secrets(command)
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>", redacted)
    redacted = re.sub(r"\bcli_[A-Za-z0-9._~+/=-]{16,}", "<redacted-token>", redacted)
    redacted = re.sub(r"\bsk[-_][A-Za-z0-9._~+/=-]{16,}", "<redacted-token>", redacted)
    return truncate_text(redacted.strip(), max_chars).replace("\n", " ")


def categorize_shell_command(command: str) -> str | None:
    lower = command.strip().lower()
    if command_runs_tests(command):
        return "test"
    if re.match(r"^(git\s+diff|git\s+show|git\s+status)\b", lower):
        return "git-read"
    if re.match(r"^(rg|grep|find)\b", lower):
        return "search"
    if re.match(r"^(ls|pwd|cat|sed|awk)\b", lower):
        return "read"
    if re.match(r"^(npm|pnpm|yarn)\s+(install|add|i)\b", lower):
        return "dependency-install"
    if "graphify" in lower:
        return "graphify"
    if "maestro" in lower:
        return "mobile-runtime"
    return "other"


def command_runs_tests(command: str) -> bool:
    return bool(
        re.search(
            r"\b(npx\s+playwright|playwright\s+test|npm\s+(test|run)|pnpm\s+(test|run)|yarn\s+(test|run)|vitest|cypress|wdio|maestro\s+test|pytest)\b",
            command.lower(),
        )
    )


def command_uses_browser(command: str) -> bool:
    lower = command.lower()
    return "browser" in lower or "playwright open" in lower or "cypress open" in lower


def command_writes_files(command: str) -> bool:
    lower = command.lower()
    return bool(
        re.search(
            r"(^|\s)(touch|tee|apply_patch|mv|cp|npm\s+install|pnpm\s+add)\b", lower
        )
        or re.search(r"(^|\s)(>|>>)\s*[^&\s]", command)
    )


def redact_configured_secrets(text: str) -> str:
    for name in (
        "GOOGLE_API_KEY",
        "CONFIDENT_API_KEY",
        "OPENAI_API_KEY",
        "SUPATEST_API_KEY",
        "BENCHMARK_SUPATEST_API_KEY",
        "BENCHMARK_SUPATEST_EVAL_DASHBOARD_API_KEY",
    ):
        value = os.getenv(name)
        if value and len(value) >= 6:
            text = text.replace(value, "<redacted>")
    return text


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
