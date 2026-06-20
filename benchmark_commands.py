from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from benchmark_telemetry import (
    categorize_shell_command,
    extract_shell_command,
    extract_tool_name,
    is_tool_use_event,
    nested_tool_use_events,
    normalized_event_type,
    parse_structured_events,
    safe_command_excerpt,
)

RUN_COMMANDS_SCHEMA_VERSION = 2


def empty_commands_report(
    agent: str, source: str = "benchmark-transcript-parser"
) -> dict:
    return {
        "schemaVersion": RUN_COMMANDS_SCHEMA_VERSION,
        "generatedAt": datetime.now(UTC).isoformat(),
        "agent": agent,
        "source": source,
        "summary": {
            "totalInvocations": 0,
            "allowedInvocations": 0,
            "deniedInvocations": 0,
            "shellCommands": 0,
            "toolCounts": {},
            "commandCategories": {},
            "supatestFeatures": {},
        },
        "loadedMcpServers": [],
        "loadedBundledTools": [],
        "invocations": [],
    }


def detect_supatest_features(tool_name: str | None, command: str | None) -> list[str]:
    features: list[str] = []
    lower_tool = (tool_name or "").lower()
    lower_command = (command or "").lower()

    if "graphify" in lower_tool or "graphify" in lower_command:
        features.append("graphify")
    if lower_tool.startswith("mcp__graphify__"):
        features.append("graphify-mcp")
    if "supatest graphify" in lower_command:
        features.append("graphify-cli")
    if " rtk" in f" {lower_command}" or lower_tool.endswith("rtk"):
        features.append("rtk")
    if lower_tool.startswith("mcp__lean-ctx__") or "ctx_" in lower_command:
        features.append("lean-ctx")
    if lower_tool.startswith("mcp__agora-memory__"):
        features.append("agora-memory")
    if lower_tool.startswith("mcp__morph-mcp__"):
        features.append("morph-mcp")
    if lower_tool.startswith("mcp__headroom__"):
        features.append("headroom-mcp")
    if "headroom" in lower_command:
        features.append("headroom")
    if lower_tool.startswith("mcp__playwright__browser"):
        features.append("playwright-mcp")
    if lower_tool.startswith("mcp__maestro__"):
        features.append("maestro-mcp")
    if "verify-fix.mjs" in lower_command:
        features.append("verify-fix")

    return list(dict.fromkeys(features))


def is_policy_denial_event(event: dict, event_type: str | None) -> bool:
    haystack = " ".join(
        str(value)
        for key, value in event.items()
        if key.lower() in {"type", "event", "kind", "message", "reason", "code"}
    ).lower()
    return bool(
        (event_type and "policy" in event_type and "den" in event_type)
        or ("policy" in haystack and ("denied" in haystack or "denial" in haystack))
        or ("denied" in haystack and "tool" in haystack)
    )


def summarize_invocations(invocations: list[dict]) -> dict:
    tool_counts: dict[str, int] = {}
    command_categories: dict[str, int] = {}
    supatest_features: dict[str, int] = {}
    shell_commands = 0
    allowed_invocations = 0
    denied_invocations = 0

    for invocation in invocations:
        tool = str(invocation.get("tool") or "unknown")
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
        if invocation.get("allowed"):
            allowed_invocations += 1
        else:
            denied_invocations += 1
        command = invocation.get("command")
        if isinstance(command, str) and command.strip():
            shell_commands += 1
            category = invocation.get("category")
            if isinstance(category, str) and category:
                command_categories[category] = command_categories.get(category, 0) + 1
        for feature in invocation.get("supatestFeatures") or []:
            if isinstance(feature, str) and feature:
                supatest_features[feature] = supatest_features.get(feature, 0) + 1

    return {
        "totalInvocations": len(invocations),
        "allowedInvocations": allowed_invocations,
        "deniedInvocations": denied_invocations,
        "shellCommands": shell_commands,
        "toolCounts": dict(sorted(tool_counts.items())),
        "commandCategories": dict(sorted(command_categories.items())),
        "supatestFeatures": dict(sorted(supatest_features.items())),
    }


def build_command_invocation(
    index: int,
    turn: int,
    tool_name: str,
    event: dict,
    allowed: bool,
    denied_reason: str | None = None,
) -> dict:
    command = extract_shell_command(event)
    invocation: dict = {
        "index": index,
        "turn": turn,
        "tool": tool_name,
        "allowed": allowed,
        "supatestFeatures": detect_supatest_features(tool_name, command),
    }
    if command:
        invocation["command"] = safe_command_excerpt(command, 2000)
        category = categorize_shell_command(command)
        if category:
            invocation["category"] = category
    target = first_nested_string(event, "file_path", "path", "pattern")
    if target and target != command:
        invocation["target"] = safe_command_excerpt(target, 240)
    if denied_reason:
        invocation["deniedReason"] = denied_reason
    return invocation


def first_nested_string(value, *keys: str) -> str | None:
    normalized_keys = {key.replace("_", "").lower() for key in keys}

    if isinstance(value, dict):
        for raw_key, raw_value in value.items():
            if str(raw_key).replace("_", "").lower() in normalized_keys:
                if isinstance(raw_value, str) and raw_value.strip():
                    return raw_value.strip()
            nested = first_nested_string(raw_value, *keys)
            if nested:
                return nested
    elif isinstance(value, list):
        for item in value:
            nested = first_nested_string(item, *keys)
            if nested:
                return nested
    return None


def extract_denial_reason(event: dict) -> str | None:
    for key in (
        "reason",
        "message",
        "permissionDecisionReason",
        "permission_decision_reason",
    ):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return first_nested_string(event, "reason", "message", "permissionDecisionReason")


def build_commands_report_from_transcript(agent: str, transcript_path: Path) -> dict:
    if not transcript_path.exists():
        return empty_commands_report(agent)

    text = transcript_path.read_text(errors="replace")
    events, _malformed = parse_structured_events(text)
    invocations: list[dict] = []
    turn = 0

    for event in events:
        if not isinstance(event, dict):
            continue

        event_type = normalized_event_type(event)
        if event_type and event_type.startswith("assistant"):
            turn += 1

        if is_policy_denial_event(event, event_type):
            tool_name = extract_tool_name(event) or "unknown"
            invocations.append(
                build_command_invocation(
                    len(invocations) + 1,
                    max(turn, 1),
                    tool_name,
                    event,
                    allowed=False,
                    denied_reason=extract_denial_reason(event),
                )
            )
            continue

        tool_events = nested_tool_use_events(event)
        if not tool_events and is_tool_use_event(event, event_type):
            tool_events = [event]

        for tool_event in tool_events:
            if not isinstance(tool_event, dict):
                continue
            tool_name = extract_tool_name(tool_event) or "unknown"
            invocations.append(
                build_command_invocation(
                    len(invocations) + 1,
                    max(turn, 1),
                    tool_name,
                    tool_event,
                    allowed=True,
                )
            )

    report = empty_commands_report(agent)
    report["invocations"] = invocations
    report["summary"] = summarize_invocations(invocations)
    return report


def load_commands_report(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def resolve_commands_report(
    agent: str, transcript_path: Path, case_run_dir: Path
) -> dict:
    for candidate in (
        case_run_dir / "commands.json",
        case_run_dir / ".supatest" / "commands.json",
        case_run_dir / "project" / ".supatest" / "commands.json",
        case_run_dir / "project" / "commands.json",
    ):
        existing = load_commands_report(candidate)
        if existing:
            existing.setdefault("agent", agent)
            return existing
    return build_commands_report_from_transcript(agent, transcript_path)


def write_commands_json(case_run_dir: Path, report: dict) -> Path:
    output_path = case_run_dir / "commands.json"
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return output_path


def write_run_commands_bundle(
    run_id: str,
    runs_dir: Path,
    results_dir: Path,
    results: list[dict],
) -> Path:
    entries: list[dict] = []
    reports: dict[str, dict] = {}

    for result in results:
        commands_path_raw = result.get("commandsPath")
        if not isinstance(commands_path_raw, str) or not commands_path_raw.strip():
            continue

        commands_path = Path(commands_path_raw)
        if not commands_path.is_absolute():
            commands_path = runs_dir / commands_path
        if not commands_path.exists():
            continue

        report = load_commands_report(commands_path)
        if not report:
            continue

        case_id = str(result.get("caseId") or "unknown-case")
        agent = str(result.get("agent") or "unknown-agent")
        eval_id = str(result.get("evalId") or "unknown-eval")
        key = f"{case_id}/{agent}"

        try:
            relative_path = str(commands_path.relative_to(runs_dir))
        except ValueError:
            relative_path = str(commands_path)

        entry = {
            "caseId": case_id,
            "evalId": eval_id,
            "agent": agent,
            "commandsPath": relative_path,
            "summary": report.get("summary") or result.get("commandsSummary") or {},
            "loadedMcpServers": report.get("loadedMcpServers")
            or report.get("mcpServers")
            or [],
            "loadedBundledTools": report.get("loadedBundledTools") or [],
        }
        entries.append(entry)
        reports[key] = report

    bundle = {
        "schemaVersion": RUN_COMMANDS_SCHEMA_VERSION,
        "runId": run_id,
        "generatedAt": datetime.now(UTC).isoformat(),
        "entryCount": len(entries),
        "entries": entries,
        "reports": reports,
    }

    runs_bundle_path = runs_dir / "commands.json"
    results_bundle_path = results_dir / "commands.json"
    payload = json.dumps(bundle, indent=2, sort_keys=True) + "\n"
    runs_bundle_path.write_text(payload)
    results_bundle_path.write_text(payload)

    commands_dir = results_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        source_path = runs_dir / entry["commandsPath"]
        if not source_path.exists():
            continue
        target_name = f"{entry['caseId']}__{entry['agent'].replace(':', '_')}.json"
        target_path = commands_dir / target_name
        target_path.write_text(source_path.read_text())

    return runs_bundle_path
