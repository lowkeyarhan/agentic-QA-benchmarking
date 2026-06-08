from __future__ import annotations

import json
import os
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


def selected_eval_ids() -> list[str]:
    raw = os.getenv("BENCHMARK_EVAL_IDS", "E1")
    return [item.strip() for item in raw.split(",") if item.strip()]


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
