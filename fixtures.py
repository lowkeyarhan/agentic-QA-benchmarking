from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


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


def available_eval_ids(fixtures_root: Path = FIXTURES_ROOT) -> list[str]:
    eval_ids = []
    fixture_dirs = fixtures_root.iterdir() if fixtures_root.exists() else []
    for path in fixture_dirs:
        if (path / "fixture.json").exists():
            eval_ids.append(path.name)
    return sorted(eval_ids, key=eval_id_sort_key)


def selected_eval_ids() -> list[str]:
    return resolve_eval_ids(os.getenv("BENCHMARK_EVAL_IDS", "all"))


def resolve_eval_ids(raw: str | list[str]) -> list[str]:
    values = raw if isinstance(raw, list) else [item.strip() for item in raw.split(",")]
    requested = [item for item in values if item]
    if not requested or any(item.lower() == "all" for item in requested):
        return available_eval_ids()

    available = set(available_eval_ids())
    missing = [eval_id for eval_id in requested if eval_id not in available]
    if missing:
        raise ValueError(
            "Unknown eval id(s): "
            + ", ".join(missing)
            + ". Use BENCHMARK_EVAL_IDS=all to run every available fixture."
        )
    return requested


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
    )


def copy_project(fixture: EvalFixture, destination: Path) -> Path:
    project_destination = destination / "project"
    if project_destination.exists():
        shutil.rmtree(project_destination)
    shutil.copytree(
        fixture.project_dir,
        project_destination,
        ignore=shutil.ignore_patterns(
            "node_modules",
            ".git",
            "dist",
            "build",
            "coverage",
            "playwright-report",
            "test-results",
            ".turbo",
        ),
    )
    return project_destination
