from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qa_bench import (
    available_suite_names,
    is_suite_token,
    resolve_suite_eval_ids,
)


BENCHMARK_ROOT = Path(__file__).resolve().parent


def benchmark_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value).expanduser()
    return path if path.is_absolute() else BENCHMARK_ROOT / path


FIXTURES_ROOT = benchmark_path(
    os.getenv("BENCHMARK_FIXTURES_ROOT"),
    BENCHMARK_ROOT / "agent-eval-fixtures" / "fixtures",
)
BASE_TEMPLATES_ROOT = benchmark_path(
    os.getenv("BENCHMARK_BASE_TEMPLATES_ROOT"),
    BENCHMARK_ROOT / "agent-eval-fixtures" / "base-templates",
)
PROJECT_COPY_IGNORE = shutil.ignore_patterns(
    "node_modules",
    ".git",
    "dist",
    "build",
    "coverage",
    "playwright-report",
    "test-results",
    ".turbo",
)


@dataclass(frozen=True)
class EvalFixture:
    eval_id: str
    name: str
    mode: str
    task: str
    pass_criteria: list[str]
    fail_criteria: list[str]
    tier: int | None
    fixture_dir: Path
    project_dir: Path
    logs_file: Path | None
    qa_bench: dict | None = None
    base_template: str | None = None
    modifications: list[Any] | None = None


def available_eval_ids(fixtures_root: Path = FIXTURES_ROOT) -> list[str]:
    eval_ids = []
    fixture_dirs = fixtures_root.iterdir() if fixtures_root.exists() else []
    for path in fixture_dirs:
        if (path / "fixture.json").exists():
            eval_ids.append(path.name)
    return sorted(eval_ids, key=eval_id_sort_key)


def selected_eval_ids() -> list[str]:
    return select_eval_ids(
        os.getenv("BENCHMARK_EVAL_IDS", "suite:qa-production"),
        os.getenv("BENCHMARK_EXTRA_EVAL_IDS"),
        os.getenv("BENCHMARK_EVAL_LIMIT"),
        os.getenv("BENCHMARK_EVAL_OFFSET"),
    )


def select_eval_ids(
    raw_eval_ids: str | list[str],
    raw_extra_eval_ids: str | list[str] | None = None,
    raw_limit: str | None = None,
    raw_offset: str | None = None,
) -> list[str]:
    base_eval_ids = window_eval_ids(
        resolve_eval_ids(raw_eval_ids),
        raw_limit,
        raw_offset,
    )
    extra_eval_ids = resolve_optional_eval_ids(raw_extra_eval_ids)
    return list(dict.fromkeys([*base_eval_ids, *extra_eval_ids]))


def resolve_optional_eval_ids(raw: str | list[str] | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str) and not raw.strip():
        return []
    return resolve_eval_ids(raw)


def resolve_eval_ids(raw: str | list[str]) -> list[str]:
    values = raw if isinstance(raw, list) else [item.strip() for item in raw.split(",")]
    requested = [item for item in values if item]
    if not requested or any(item.lower() == "all" for item in requested):
        return available_eval_ids()

    available_list = available_eval_ids()
    resolved: list[str] = []
    for item in requested:
        if is_suite_token(item):
            resolved.extend(resolve_suite_eval_ids(item, available_list))
        else:
            resolved.append(item)

    available = set(available_list)
    missing = [eval_id for eval_id in resolved if eval_id not in available]
    if missing:
        raise ValueError(
            "Unknown eval id(s): "
            + ", ".join(missing)
            + ". Use BENCHMARK_EVAL_IDS=all to run every available fixture, "
            + "or BENCHMARK_EVAL_IDS=suite:<name>. Available suites: "
            + ", ".join(available_suite_names())
        )
    return list(dict.fromkeys(resolved))


def window_eval_ids(
    eval_ids: list[str],
    raw_limit: str | None = None,
    raw_offset: str | None = None,
) -> list[str]:
    offset = parse_non_negative_int(raw_offset, "BENCHMARK_EVAL_OFFSET")
    limit = parse_eval_limit(raw_limit)
    selected = eval_ids[offset:]
    if limit is not None:
        selected = selected[:limit]
    if eval_ids and not selected:
        raise ValueError(
            "BENCHMARK_EVAL_OFFSET skips every selected eval. "
            f"Selected {len(eval_ids)} eval(s), offset was {offset}."
        )
    return selected


def parse_eval_limit(raw: str | None) -> int | None:
    if raw is None or not raw.strip() or raw.strip().lower() == "all":
        return None
    value = parse_non_negative_int(raw, "BENCHMARK_EVAL_LIMIT")
    if value <= 0:
        raise ValueError("BENCHMARK_EVAL_LIMIT must be a positive integer or 'all'.")
    return value


def parse_non_negative_int(raw: str | None, name: str) -> int:
    if raw is None or not raw.strip():
        return 0
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a non-negative integer.") from error
    if value < 0:
        raise ValueError(f"{name} must be a non-negative integer.")
    return value


def eval_id_sort_key(eval_id: str) -> tuple[str, int, str]:
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", eval_id)
    if not match:
        return (eval_id, -1, eval_id)
    prefix, number = match.groups()
    return (prefix, int(number), eval_id)


def load_fixture(eval_id: str) -> EvalFixture:
    fixture_dir = FIXTURES_ROOT / eval_id
    fixture_json = fixture_dir / "fixture.json"
    if not fixture_json.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_json}")

    data = json.loads(fixture_json.read_text())
    project_dir = fixture_dir / "project"
    if not project_dir.exists():
        raise FileNotFoundError(f"Fixture project not found: {project_dir}")

    logs_value = data.get("logsFile")
    logs_file = fixture_dir / logs_value if logs_value else fixture_dir / "failure.log"
    if not logs_file.exists():
        logs_file = None

    qa_bench = data.get("qaBench")
    if qa_bench is not None and not isinstance(qa_bench, dict):
        raise ValueError(f"Fixture {eval_id} qaBench metadata must be an object.")

    return EvalFixture(
        eval_id=data["evalId"],
        name=data["name"],
        mode=data["mode"],
        task=data["task"],
        pass_criteria=list(data.get("passCriteria", [])),
        fail_criteria=list(data.get("failCriteria", [])),
        tier=data.get("tier"),
        fixture_dir=fixture_dir,
        project_dir=project_dir,
        logs_file=logs_file,
        qa_bench=dict(qa_bench) if qa_bench is not None else None,
        base_template=data.get("baseTemplate"),
        modifications=list(data.get("modifications") or []),
    )


def copy_project(fixture: EvalFixture, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    project_destination = destination / "project"
    if project_destination.exists():
        shutil.rmtree(project_destination)
    base_template_dir = base_template_project_dir(fixture)
    if base_template_dir:
        shutil.copytree(
            base_template_dir,
            project_destination,
            ignore=PROJECT_COPY_IGNORE,
        )
        shutil.copytree(
            fixture.project_dir,
            project_destination,
            dirs_exist_ok=True,
            ignore=PROJECT_COPY_IGNORE,
        )
    else:
        shutil.copytree(
            fixture.project_dir,
            project_destination,
            ignore=PROJECT_COPY_IGNORE,
        )
    apply_fixture_modifications(fixture, project_destination)
    prepare_bundled_context_tools(project_destination)
    return project_destination


def resolve_supatest_binary() -> str | None:
    explicit = (os.getenv("BENCHMARK_SUPATEST_BINARY") or "").strip()
    if explicit:
        return explicit
    return shutil.which("supatest")


def prepare_bundled_context_tools(project_dir: Path) -> None:
    raw = os.getenv("BENCHMARK_SUPATEST_PREPARE_GRAPHIFY", "1").strip().lower()
    if raw in {"", "0", "false", "no", "off", "none"}:
        return

    graph_path = project_dir / "graphify-out" / "graph.json"
    if graph_path.exists():
        return

    binary = resolve_supatest_binary()
    if not binary:
        return

    timeout_raw = os.getenv("BENCHMARK_SUPATEST_GRAPHIFY_TIMEOUT_SECONDS", "120").strip()
    try:
        timeout_seconds = max(1, int(timeout_raw))
    except ValueError:
        timeout_seconds = 120

    try:
        subprocess.run(
            [binary, "graphify", "update", ".", "--no-cluster"],
            cwd=project_dir,
            check=False,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired):
        return


def base_template_project_dir(fixture: EvalFixture) -> Path | None:
    if not fixture.base_template:
        return None
    candidate = BASE_TEMPLATES_ROOT / fixture.base_template
    return candidate if candidate.exists() else None


def apply_fixture_modifications(fixture: EvalFixture, project_dir: Path) -> None:
    for modification in fixture.modifications or []:
        if not isinstance(modification, dict):
            continue
        modification_type = modification.get("type")
        if modification_type == "delete":
            apply_delete_modification(project_dir, modification)
        elif modification_type == "replace":
            apply_replace_modification(fixture, project_dir, modification)


def apply_delete_modification(project_dir: Path, modification: dict) -> None:
    pattern = modification.get("pattern") or modification.get("file")
    if not pattern:
        return

    matches = list(project_dir.glob(str(pattern)))
    direct = project_dir / str(pattern)
    if direct.exists() and direct not in matches:
        matches.append(direct)

    for path in matches:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def apply_replace_modification(
    fixture: EvalFixture, project_dir: Path, modification: dict
) -> None:
    relative_file = modification.get("file")
    find_text = modification.get("find")
    replace_text = modification.get("replace")
    if not relative_file or find_text is None or replace_text is None:
        return

    path = project_dir / str(relative_file)
    if not path.exists():
        raise FileNotFoundError(
            f"Fixture {fixture.eval_id} replace target is missing: {relative_file}"
        )

    text = path.read_text()
    if str(find_text) in text:
        path.write_text(text.replace(str(find_text), str(replace_text), 1))
        return
    if str(replace_text) in text:
        return
    raise ValueError(
        f"Fixture {fixture.eval_id} replace target did not contain find or replacement text: {relative_file}"
    )
