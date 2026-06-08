from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from agents import run_agent, selected_agents
from fixtures import (
    BENCHMARK_ROOT,
    benchmark_path,
    copy_project,
    load_fixture,
    selected_eval_ids,
)
from scoring import make_metric, make_test_case, result_label


RUN_ID = os.getenv("BENCHMARK_RUN_ID", time.strftime("%Y%m%d-%H%M%S"))
RUNS_DIR = (
    benchmark_path(os.getenv("BENCHMARK_RUNS_DIR"), BENCHMARK_ROOT / "runs") / RUN_ID
)
RESULTS_DIR = (
    benchmark_path(os.getenv("BENCHMARK_RESULTS_DIR"), BENCHMARK_ROOT / "results")
    / RUN_ID
)


CASES = [
    (eval_id, agent) for eval_id in selected_eval_ids() for agent in selected_agents()
]


@pytest.mark.parametrize(("eval_id", "agent"), CASES)
def test_agent_fixture(eval_id: str, agent: str) -> None:
    fixture = load_fixture(eval_id)
    case_run_dir = RUNS_DIR / eval_id / agent
    case_result_dir = RESULTS_DIR / eval_id
    project_dir = copy_project(fixture, case_run_dir)

    run = run_agent(agent, fixture, project_dir, case_run_dir)
    test_case = make_test_case(fixture, run)
    metric = make_metric(fixture)
    metric.measure(test_case)

    score = 0.0 if run.timed_out else float(metric.score or 0.0)
    label = result_label(score, run.timed_out)

    case_result_dir.mkdir(parents=True, exist_ok=True)
    result_path = case_result_dir / f"{agent}.json"
    result_path.write_text(
        json.dumps(
            {
                "runId": RUN_ID,
                "evalId": fixture.eval_id,
                "evalName": fixture.name,
                "agent": agent,
                "mode": fixture.mode,
                "score": score,
                "scorePercent": round(score * 100),
                "result": label,
                "reason": metric.reason,
                "exitCode": run.exit_code,
                "timedOut": run.timed_out,
                "durationMs": run.duration_ms,
                "projectDir": str(run.project_dir),
                "transcriptPath": str(run.transcript_path),
                "changedFiles": run.changed_files,
                "passCriteria": fixture.pass_criteria,
                "failCriteria": fixture.fail_criteria,
            },
            indent=2,
        )
    )

    if os.getenv("BENCHMARK_ASSERT_PASS") == "1":
        assert score >= 0.7, metric.reason
