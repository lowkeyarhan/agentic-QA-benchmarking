from __future__ import annotations

import os

from deepeval.metrics import GEval
from deepeval.models import GeminiModel
from deepeval.test_case import LLMTestCase, SingleTurnParams

from agents import AgentRunResult
from fixtures import EvalFixture


def make_test_case(fixture: EvalFixture, run: AgentRunResult) -> LLMTestCase:
    actual_output = "\n\n".join(
        [
            f"Agent: {run.agent}",
            f"Exit code: {run.exit_code}",
            f"Timed out: {run.timed_out}",
            "Changed files:",
            "\n".join(run.changed_files) or "No changed files",
            "Changed file excerpts:",
            run.changed_file_excerpt or "No changed file excerpts",
            "Transcript tail:",
            run.transcript[-16000:],
        ]
    )

    expected_output = "\n".join(
        [
            "Pass criteria:",
            *[f"- {item}" for item in fixture.pass_criteria],
            "",
            "Fail criteria:",
            *[f"- {item}" for item in fixture.fail_criteria],
        ]
    )

    return LLMTestCase(
        input=fixture.task,
        actual_output=actual_output,
        expected_output=expected_output,
    )


def make_metric(fixture: EvalFixture) -> GEval:
    model = make_judge_model()
    return GEval(
        name=f"{fixture.eval_id} Agent Task Completion",
        model=model,
        criteria=(
            "Judge whether the agent completed the task for this software testing fixture. "
            "Give high scores only when the result satisfies the pass criteria, avoids the fail criteria, "
            "makes relevant project changes when needed, and does not merely claim success without evidence. "
            "A non-zero wrapper exit code is not an automatic failure when the transcript, changed files, "
            "or test output show that the requested work was completed. Penalize timeouts, irrelevant edits, "
            "destructive test weakening, invented selectors, and missing investigation."
        ),
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=0.7,
        async_mode=False,
    )


def make_judge_model():
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        return None

    return GeminiModel(
        model=os.getenv("DEEPEVAL_GEMINI_MODEL", "gemini-2.5-pro"),
        api_key=google_api_key,
        temperature=0,
    )


def result_label(score: float, timed_out: bool) -> str:
    if timed_out:
        return "fail"
    if score >= 0.7:
        return "pass"
    if score >= 0.4:
        return "partial"
    return "fail"
