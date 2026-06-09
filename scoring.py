from __future__ import annotations

import os
import re
from collections import Counter

from deepeval.metrics import BaseMetric, GEval
from deepeval.models import GeminiModel
from deepeval.test_case import LLMTestCase, SingleTurnParams

from agents import AgentRunResult
from fixtures import BENCHMARK_ROOT, EvalFixture


ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SPINNER_RE = re.compile(r"^\s*[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s+(Thinking|Working|Processing)\.*\s*$")


def make_test_case(fixture: EvalFixture, run: AgentRunResult) -> LLMTestCase:
    transcript = sanitize_evidence(cleaned_transcript(run.transcript), run)
    changed_files = sanitize_evidence("\n".join(run.changed_files), run)
    changed_excerpt = sanitize_evidence(run.changed_file_excerpt, run)
    actual_output = "\n\n".join(
        [
            f"Exit code: {run.exit_code}",
            f"Timed out: {run.timed_out}",
            "Changed files:",
            changed_files or "No changed files",
            "Changed file excerpts:",
            changed_excerpt or "No changed file excerpts",
            "Cleaned transcript tail:",
            transcript[-16000:],
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
        name=f"{fixture.eval_id} / {run.agent}",
        input=fixture.task,
        actual_output=actual_output,
        expected_output=expected_output,
        metadata={
            "eval_id": fixture.eval_id,
            "eval_name": fixture.name,
            "agent": run.agent,
            "mode": fixture.mode,
            "timed_out": run.timed_out,
            "exit_code": run.exit_code,
        },
        tags=[fixture.eval_id, run.agent, fixture.mode],
    )


def cleaned_transcript(text: str) -> str:
    text = text.replace("\r", "\n")
    text = ANSI_RE.sub("", text)
    text = CONTROL_RE.sub("", text)
    lines = []
    previous = None
    repeat_count = 0

    def flush_previous() -> None:
        nonlocal previous, repeat_count
        if previous is None:
            return
        lines.append(previous)
        if repeat_count > 1:
            lines.append(f"[previous line repeated {repeat_count - 1} times]")
        previous = None
        repeat_count = 0

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or SPINNER_RE.match(stripped) or "ctrl+o to expand" in stripped:
            continue
        if line == previous:
            repeat_count += 1
            continue
        flush_previous()
        previous = line
        repeat_count = 1

    flush_previous()
    return "\n".join(collapse_repeated_status_lines(lines))


def collapse_repeated_status_lines(lines: list[str]) -> list[str]:
    collapsed = []
    counts: Counter[str] = Counter()
    suppressed: Counter[str] = Counter()
    for line in lines:
        key = status_line_key(line)
        if key:
            counts[key] += 1
            if counts[key] > 1:
                suppressed[key] += 1
                continue
        collapsed.append(line)

    for key, count in suppressed.items():
        collapsed.append(
            f"[suppressed {count} repeated terminal status lines for {key}]"
        )
    return collapsed


def status_line_key(line: str) -> str | None:
    stripped = line.strip()
    match = re.search(r"Command\(([^)]*)", stripped)
    if not match:
        return None
    command = match.group(1).replace("...", "").strip()
    if command.startswith("npx playwright test"):
        return "Command(npx playwright test)"
    if command.startswith("npm install"):
        return "Command(npm install)"
    return f"Command({command})"


def sanitize_evidence(text: str, run: AgentRunResult) -> str:
    if not text:
        return ""

    replacements = [
        (str(run.project_dir), "<project>"),
        (str(run.project_dir.parent), "<case>"),
        (str(run.transcript_path), "<transcript>"),
        (str(BENCHMARK_ROOT), "<benchmark>"),
    ]
    for source, replacement in sorted(
        replacements, key=lambda item: len(item[0]), reverse=True
    ):
        if source:
            text = text.replace(source, replacement)

    if run.agent:
        text = re.sub(re.escape(run.agent), "<agent>", text, flags=re.IGNORECASE)

    secret_patterns = [
        (r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>"),
        (r"\bcli_[A-Za-z0-9._~+/=-]{16,}", "<redacted-token>"),
        (r"\bsk[-_][A-Za-z0-9._~+/=-]{16,}", "<redacted-token>"),
    ]
    for pattern, replacement in secret_patterns:
        text = re.sub(pattern, replacement, text)
    return text


class BenchmarkQATaskCompletionMetric(BaseMetric):
    def __init__(self) -> None:
        self.name = "QA Task Completion"
        self.threshold = 0.7
        self.score = None
        self.reason = None
        self.success = None
        self.strict_mode = False
        self.async_mode = False
        self.verbose_mode = False
        self.include_reason = True
        self.error = None
        self.evaluation_cost = None
        self.verbose_logs = None
        self._judge = make_geval_metric()
        self.evaluation_model = getattr(self._judge, "evaluation_model", None)
        self.model = getattr(self._judge, "model", None)
        self.using_native_model = getattr(self._judge, "using_native_model", None)

    def measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        if "Timed out: True" in (test_case.actual_output or ""):
            self.score = 0.0
            self.reason = "Timed out before the agent completed the task."
            self.success = False
            self.error = None
            self.evaluation_cost = None
            self.verbose_logs = None
            return self.score

        self._judge.measure(test_case, *args, **kwargs)
        self.score = float(self._judge.score or 0.0)
        self.reason = self._judge.reason
        self.success = self.score >= self.threshold
        self.error = getattr(self._judge, "error", None)
        self.evaluation_cost = getattr(self._judge, "evaluation_cost", None)
        self.verbose_logs = getattr(self._judge, "verbose_logs", None)
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case, *args, **kwargs)

    def is_successful(self) -> bool:
        return bool(self.success)

    @property
    def __name__(self) -> str:
        return self.name


def make_metric(fixture: EvalFixture | None = None) -> BenchmarkQATaskCompletionMetric:
    return BenchmarkQATaskCompletionMetric()


def make_geval_metric() -> GEval:
    model = make_judge_model()
    return GEval(
        name="QA Task Completion",
        model=model,
        criteria=(
            "Judge whether the anonymous candidate completed the task for this software testing fixture. "
            "Give high scores only when the result satisfies the pass criteria, avoids the fail criteria, "
            "makes relevant project changes when needed, and does not merely claim success without evidence. "
            "Do not reward or penalize any specific CLI, product, company, model, brand, cost profile, or agent type. "
            "Use only the task, pass/fail criteria, changed files, and transcript evidence. "
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
