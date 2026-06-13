from __future__ import annotations

import json
import os
import re
from pathlib import Path

from agents import agent_command_env_name, agent_family


def empty_token_usage() -> dict:
    return {
        "inputTokens": None,
        "outputTokens": None,
        "cachedInputTokens": None,
        "cacheCreationInputTokens": None,
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
            # Provider cached-token counters are not consistently additive.
            usage["totalTokens"] = int(input_tokens or 0) + int(output_tokens or 0)

    if usage["totalTokens"] is None:
        fallback_tokens = token_usage_fallback_tokens(agent)
        if fallback_tokens is not None:
            usage["totalTokens"] = fallback_tokens
            sources.append("configured-fallback")
            usage["warnings"].append("token-usage-fallback")

    estimated_cost = estimate_token_cost_usd(agent, usage)
    if estimated_cost is not None:
        usage["estimatedCostUsd"] = round(estimated_cost, 6)

    if sources:
        usage["source"] = ", ".join(dict.fromkeys(sources))
    if usage["totalTokens"] is None:
        if sources:
            usage["warnings"].append("token-total-not-found")
        else:
            usage["warnings"].append("token-usage-not-found")
    return usage


def token_usage_candidate_paths(
    transcript_path: Path, case_run_dir: Path
) -> list[tuple[str, Path]]:
    return [
        ("transcript", transcript_path),
        ("run-usage-json", case_run_dir / "usage.json"),
        ("run-usage-jsonl", case_run_dir / "usage.jsonl"),
        ("run-token-usage-json", case_run_dir / "token-usage.json"),
        ("run-token-usage-jsonl", case_run_dir / "token-usage.jsonl"),
        ("run-telemetry-json", case_run_dir / "telemetry.json"),
        ("run-telemetry-jsonl", case_run_dir / "telemetry.jsonl"),
        ("run-supatest-usage-json", case_run_dir / ".supatest" / "usage.json"),
        ("run-supatest-usage-jsonl", case_run_dir / ".supatest" / "usage.jsonl"),
        (
            "run-supatest-token-usage-json",
            case_run_dir / ".supatest" / "token-usage.json",
        ),
        (
            "run-supatest-token-usage-jsonl",
            case_run_dir / ".supatest" / "token-usage.jsonl",
        ),
        ("run-supatest-telemetry-json", case_run_dir / ".supatest" / "telemetry.json"),
        (
            "run-supatest-telemetry-jsonl",
            case_run_dir / ".supatest" / "telemetry.jsonl",
        ),
        ("project-usage-json", case_run_dir / "project" / "usage.json"),
        ("project-usage-jsonl", case_run_dir / "project" / "usage.jsonl"),
        ("project-token-usage-json", case_run_dir / "project" / "token-usage.json"),
        (
            "project-token-usage-jsonl",
            case_run_dir / "project" / "token-usage.jsonl",
        ),
        ("project-telemetry-json", case_run_dir / "project" / "telemetry.json"),
        ("project-telemetry-jsonl", case_run_dir / "project" / "telemetry.jsonl"),
        (
            "project-supatest-usage-json",
            case_run_dir / "project" / ".supatest" / "usage.json",
        ),
        (
            "project-supatest-usage-jsonl",
            case_run_dir / "project" / ".supatest" / "usage.jsonl",
        ),
        (
            "project-supatest-token-usage-json",
            case_run_dir / "project" / ".supatest" / "token-usage.json",
        ),
        (
            "project-supatest-token-usage-jsonl",
            case_run_dir / "project" / ".supatest" / "token-usage.jsonl",
        ),
        (
            "project-supatest-telemetry-json",
            case_run_dir / "project" / ".supatest" / "telemetry.json",
        ),
        (
            "project-supatest-telemetry-jsonl",
            case_run_dir / "project" / ".supatest" / "telemetry.jsonl",
        ),
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

    for parsed_json in parse_json_lines(text):
        parsed_any = (
            merge_token_usage(usage, parse_token_usage_json(parsed_json)) or parsed_any
        )

    parsed_any = merge_token_usage(usage, parse_token_usage_text(text)) or parsed_any
    return usage if parsed_any else None


def parse_json_lines(text: str) -> list[object]:
    parsed: list[object] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        try:
            parsed.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return parsed


def parse_token_usage_json(value) -> dict:
    usage = empty_token_usage()

    def walk(item, in_usage: bool = False) -> None:
        if isinstance(item, dict):
            for raw_key, raw_value in item.items():
                key = normalize_usage_key(str(raw_key))
                next_in_usage = in_usage or key in {
                    "usage",
                    "usagemetadata",
                    "tokenusage",
                    "tokens",
                }
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
        "prompttokencount",
        "inputtokencount",
    } or (in_usage and key in {"prompt", "input"}):
        set_max_usage_value(usage, "inputTokens", int(number))
    elif key in {
        "completiontokens",
        "completiontoken",
        "outputtokens",
        "outputtoken",
        "responsetokens",
        "candidatetokens",
        "candidatetokencount",
        "candidatestokens",
        "candidatestokencount",
        "completiontokencount",
        "outputtokencount",
        "responsetokencount",
    } or (in_usage and key in {"completion", "output", "response"}):
        set_max_usage_value(usage, "outputTokens", int(number))
    elif key in {
        "cachereadinputtokens",
        "cachereadinputtoken",
        "cache_read_input_tokens",
    }:
        set_max_usage_value(usage, "cachedInputTokens", int(number))
    elif key in {
        "cachecreationinputtokens",
        "cachecreationinputtoken",
        "cache_creation_input_tokens",
    }:
        set_max_usage_value(usage, "cacheCreationInputTokens", int(number))
    elif key in {
        "cachedtokens",
        "cachedinputtokens",
        "cacheinputtokens",
        "cachedprompttokens",
        "cachedcontenttokens",
        "cachedcontenttokencount",
    }:
        set_max_usage_value(usage, "cachedInputTokens", int(number))
    elif key in {
        "totaltokens",
        "totaltoken",
        "tokensused",
        "tokencount",
        "totaltokencount",
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

    for match in re.finditer(
        r"(?i)\b(?:tokens\s+used|total\s+tokens?|total\s+token\s+count|token\s+usage|usage\s+tokens)\b\s*[:=]\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
        text,
    ):
        set_max_usage_value(usage, "totalTokens", int(parse_usage_number(match[1])))

    labeled_patterns = [
        (
            r"(?i)\b(prompt|input|completion|output|response|candidate|candidates|total|cached|cached\s+input|cached\s+content|cache\s+read\s+input|cache\s+creation\s+input)\s+(?:tokens?|token\s+count)\s*[:=]\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            1,
            2,
        ),
        (
            r"(?i)[\"']?\b(prompt_tokens|input_tokens|completion_tokens|output_tokens|response_tokens|candidate_tokens|candidates_tokens|total_tokens|prompt_token_count|candidates_token_count|candidate_token_count|total_token_count|cached_tokens|cached_input_tokens|cached_content_token_count|cache_read_input_tokens|cache_creation_input_tokens)\b[\"']?\s*[:=]\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            1,
            2,
        ),
        (
            r"(?i)\b([0-9][0-9,]*(?:\.[0-9]+)?)\s+(prompt|input|completion|output|response|candidate|candidates|total|cached|cached\s+input|cached\s+content)\s+(?:tokens?|token\s+count)\b",
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
        r"(?i)\b(?:estimated\s+)?(?:total\s+)?cost(?:\s+usd|\s*\(usd\))?\s*[:=]\s*\$?\s*([0-9]+(?:\.[0-9]+)?)|\btotal_cost_usd\b[\"']?\s*[:=]\s*\$?\s*([0-9]+(?:\.[0-9]+)?)",
        text,
    ):
        set_max_usage_value(
            usage,
            "estimatedCostUsd",
            float(next(group for group in match.groups() if group is not None)),
        )

    return usage


def token_usage_field_for_label(label: str) -> str | None:
    normalized = normalize_usage_key(label)
    if normalized in {
        "prompt",
        "prompttokens",
        "prompttokencount",
        "input",
        "inputtokens",
        "inputtokencount",
    }:
        return "inputTokens"
    if normalized in {
        "completion",
        "completiontokens",
        "completiontokencount",
        "output",
        "outputtokens",
        "outputtokencount",
        "response",
        "responsetokens",
        "responsetokencount",
        "candidate",
        "candidatetokens",
        "candidatetokencount",
        "candidates",
        "candidatestokens",
        "candidatestokencount",
    }:
        return "outputTokens"
    if normalized in {
        "cachecreationinput",
        "cachecreationinputtokens",
    }:
        return "cacheCreationInputTokens"
    if normalized in {
        "cached",
        "cachedtokens",
        "cachedinput",
        "cachedinputtokens",
        "cachedcontent",
        "cachereadinput",
        "cachereadinputtokens",
        "cachedcontenttokencount",
    }:
        return "cachedInputTokens"
    if normalized in {"total", "totaltokens", "totaltokencount"}:
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
        "cacheCreationInputTokens",
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
        ("cacheCreationInputTokens", "CACHE_CREATION_INPUT"),
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


def token_usage_fallback_tokens(agent: str) -> int | None:
    env_names = [agent_command_env_name(agent)]
    family_env = agent_command_env_name(agent_family(agent))
    if family_env not in env_names:
        env_names.append(family_env)

    for env_name in env_names:
        raw = os.getenv(f"BENCHMARK_TOKEN_USAGE_FALLBACK_{env_name}_TOKENS")
        if raw and raw.strip():
            return int(raw.strip())
    raw = os.getenv("BENCHMARK_TOKEN_USAGE_FALLBACK_TOKENS")
    return int(raw.strip()) if raw and raw.strip() else None


def token_total(usage: dict | None) -> int | None:
    if not usage:
        return None
    total = usage.get("totalTokens")
    return int(total) if total is not None else None
