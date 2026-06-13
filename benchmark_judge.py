from __future__ import annotations

import json
import os
from typing import Literal

from pydantic import BaseModel

from scoring import (
    configured_token_baseline_threshold_percent,
    make_judge_model,
    qa_score_percent,
    result_label,
)


DEFAULT_OVERALL_QA_WEIGHT = 0.7


class BatchJudgeCaseScore(BaseModel):
    resultId: str
    score: float
    result: Literal["pass", "partial", "fail"]
    passedChecks: int
    failedChecks: int
    reason: str
    metricScores: list["JudgeMetricScore"] | None = None
    criterionScores: list["JudgeCriterionScore"] | None = None
    failureTaxonomy: list[str] | None = None
    evidence: list[str] | None = None
    confidence: float | None = None
    auditNotes: str | None = None


class JudgeMetricScore(BaseModel):
    metricId: str
    score: float
    reason: str | None = None


class JudgeCriterionScore(BaseModel):
    criterion: str
    status: Literal["satisfied", "partial", "failed", "not_applicable"]
    reason: str


class BatchJudgeResponse(BaseModel):
    results: list[BatchJudgeCaseScore]


def empty_time_score(duration_ms: int | None = None) -> dict:
    return {
        "durationMs": duration_ms,
        "score": None,
        "scorePercent": None,
        "scoreBasis": None,
    }


def apply_time_efficiency_scores(results: list[dict]) -> None:
    """Score runtime with a QA-protected per-eval fastest-run baseline."""

    threshold = configured_token_baseline_threshold_percent()
    by_eval: dict[str, list[dict]] = {}
    for result in results:
        result["time"] = empty_time_score(duration_ms(result))
        by_eval.setdefault(result.get("evalId", ""), []).append(result)

    for eval_results in by_eval.values():
        baseline_candidates = [
            duration
            for result in eval_results
            if qa_score_percent(result) >= threshold
            for duration in [duration_ms(result)]
            if duration is not None and duration > 0
        ]
        best_duration = min(baseline_candidates) if baseline_candidates else None

        for result in eval_results:
            time_score = result["time"]
            qa_score = result.get("scorePercent")
            duration = duration_ms(result)
            if qa_score is None:
                continue
            if duration is None or duration <= 0:
                time_score["score"] = 0.0
                time_score["scorePercent"] = 0.0
                time_score["scoreBasis"] = "missing-time-zero-efficiency"
                continue
            if best_duration is None:
                time_score["score"] = 0.0
                time_score["scorePercent"] = 0.0
                time_score["scoreBasis"] = "no-passing-time-baseline"
                continue

            raw_score = min(100.0, (best_duration / duration) * 100)
            basis = "relative-passing-time-baseline"
            if float(qa_score) < threshold:
                raw_score = min(raw_score, float(qa_score))
                basis = "qa-capped-relative-passing-time-baseline"

            time_score["scorePercent"] = round(raw_score, 1)
            time_score["score"] = round(raw_score / 100, 4)
            time_score["scoreBasis"] = basis


def duration_ms(result: dict) -> int | None:
    duration = result.get("durationMs")
    return int(duration) if duration is not None else None


def apply_overall_scores(results: list[dict]) -> None:
    weights = overall_score_weights()
    for result in results:
        qa_score = result.get("scorePercent")
        token_score = (result.get("tokenUsage") or {}).get("scorePercent")
        if qa_score is None or token_score is None:
            result["overallScore"] = None
            result["overallScorePercent"] = None
            result["overallScoreSource"] = None
            continue

        overall_percent = (
            float(qa_score) * weights["qa"] + float(token_score) * weights["tokenUsage"]
        )
        result["overallScorePercent"] = round(overall_percent, 1)
        result["overallScore"] = round(overall_percent / 100, 4)
        result["overallScoreSource"] = "weighted-qa-token"


def overall_score_weights() -> dict[str, float]:
    qa_weight = configured_overall_qa_weight()
    token_weight = round(1.0 - qa_weight, 4)
    if token_weight < 0:
        raise ValueError("BENCHMARK_OVERALL_QA_WEIGHT must be <= 1.")
    return {
        "qa": qa_weight,
        "tokenUsage": token_weight,
    }


def configured_overall_qa_weight() -> float:
    raw = os.getenv(
        "BENCHMARK_OVERALL_QA_WEIGHT", str(DEFAULT_OVERALL_QA_WEIGHT)
    ).strip()
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError(
            "BENCHMARK_OVERALL_QA_WEIGHT must be between 0 and 1."
        ) from error
    if value < 0 or value > 1:
        raise ValueError("BENCHMARK_OVERALL_QA_WEIGHT must be between 0 and 1.")
    return value


def score_pending_results(
    run_id: str,
    pending_results: list,
    run_eval_ids: list[str] | None = None,
    run_agents: list[str] | None = None,
) -> list[dict]:
    results = [dict(item.result) for item in pending_results]
    scoring_jobs = []
    for index, item in enumerate(pending_results):
        result = results[index]
        if result.get("scoreSource"):
            continue
        if item.test_case is None:
            mark_unscored(
                result, "No judge evidence was produced for this case.", "harness"
            )
            continue
        if result.get("timedOut"):
            apply_score(
                result,
                0.0,
                "Timed out before the agent completed the task.",
                "timeout",
                passed_checks=0,
                failed_checks=max(1, len(result.get("passCriteria") or [])),
            )
            continue
        scoring_jobs.append((index, item.test_case))

    if not scoring_jobs:
        return results

    batch_size = configured_judge_batch_size(len(scoring_jobs))
    scoring_batches = (
        list(chunked(scoring_jobs, batch_size)) if batch_size else [scoring_jobs]
    )
    for scoring_batch in scoring_batches:
        try:
            judge_response = batch_judge_results(
                run_id,
                results,
                scoring_batch,
                run_eval_ids=run_eval_ids,
                run_agents=run_agents,
            )
        except Exception as error:
            reason = redact_configured_secrets(f"{type(error).__name__}: {error}")
            for result_index, _ in scoring_batch:
                mark_unscored(results[result_index], reason, "judge-error")
            for result in results:
                result.pop("_judgeResultId", None)
            continue

        apply_batch_judgement(results, scoring_batch, judge_response)
    return results


def configured_judge_batch_size(job_count: int) -> int:
    raw = os.getenv("BENCHMARK_JUDGE_BATCH_SIZE", "").strip()
    if not raw:
        return 0
    value = int(raw)
    if value <= 0 or job_count <= 0:
        return 0
    return min(value, job_count)


def chunked(items: list[tuple[int, object]], chunk_size: int):
    for index in range(0, len(items), chunk_size):
        yield items[index : index + chunk_size]


def batch_judge_results(
    run_id: str,
    results: list[dict],
    scoring_jobs: list[tuple[int, object]],
    run_eval_ids: list[str] | None = None,
    run_agents: list[str] | None = None,
) -> BatchJudgeResponse:
    judge_model = make_judge_model()
    if judge_model is None:
        raise RuntimeError(
            "No judge model is configured. Set DEEPEVAL_JUDGE_PROVIDER and the "
            "matching GOOGLE_API_KEY or OPENAI_API_KEY."
        )

    prompt = build_batch_judge_prompt(
        run_id,
        results,
        scoring_jobs,
        run_eval_ids=run_eval_ids,
        run_agents=run_agents,
    )
    response, _ = judge_model.generate(prompt, schema=BatchJudgeResponse)
    return parse_batch_judge_response(response)


def parse_batch_judge_response(response) -> BatchJudgeResponse:
    if isinstance(response, BatchJudgeResponse):
        return response
    if isinstance(response, dict):
        return BatchJudgeResponse.model_validate(normalize_batch_response_payload(response))
    parsed = json.loads(str(response))
    return BatchJudgeResponse.model_validate(normalize_batch_response_payload(parsed))


def normalize_batch_response_payload(value):
    if not isinstance(value, dict):
        return value
    results = value.get("results")
    if not isinstance(results, list):
        return value
    normalized_results = []
    for item in results:
        if not isinstance(item, dict):
            normalized_results.append(item)
            continue
        normalized = dict(item)
        metric_scores = normalized.get("metricScores")
        if isinstance(metric_scores, dict):
            normalized["metricScores"] = [
                {"metricId": metric_id, "score": score}
                for metric_id, score in metric_scores.items()
            ]
        normalized_results.append(normalized)
    return {**value, "results": normalized_results}


def build_batch_judge_prompt(
    run_id: str,
    results: list[dict],
    scoring_jobs: list[tuple[int, object]],
    run_eval_ids: list[str] | None = None,
    run_agents: list[str] | None = None,
) -> str:
    cases = []
    char_budget = batch_case_char_budget(len(scoring_jobs))
    for ordinal, (result_index, test_case) in enumerate(scoring_jobs, start=1):
        result = results[result_index]
        result_id = f"r{ordinal:03d}"
        result["_judgeResultId"] = result_id
        cases.append(batch_case_payload(result_id, result, test_case, char_budget))

    payload = {
        "runId": run_id,
        "evalIds": run_eval_ids or [],
        "agentCount": len(run_agents or []),
        "scoringPolicy": {
            "scoreRange": "0.0 to 1.0",
            "pass": "score >= 0.70",
            "partial": "0.40 <= score < 0.70",
            "fail": "score < 0.40",
            "passedChecks": "Number of pass criteria materially satisfied.",
            "failedChecks": "Number of fail criteria triggered. Use 0 when no fail criterion was triggered.",
            "metricScores": (
                "When qaBench.metricIds are present, return one metricScores array "
                "item per metric id using {metricId, score, reason}. These are "
                "diagnostic QA dimension scores, not replacements for the overall score."
            ),
            "criterionScores": (
                "Return criterionScores for the most important pass/fail criteria "
                "using status satisfied, partial, failed, or not_applicable."
            ),
            "confidence": "0.0 to 1.0 confidence in the score based on available evidence.",
            "failureTaxonomy": (
                "Optional diagnostic labels such as missing-artifact, missing-verification, "
                "weak-assertion, irrelevant-change, assertion-weakened, fabricated-evidence, "
                "wrong-route, env-auth, timeout, or app-bug."
            ),
        },
        "cases": cases,
    }

    return (
        "You are an impartial enterprise QA benchmark judge. Score every case in the JSON payload. "
        "Use only the task, criteria, changed files, excerpts, and transcript evidence. "
        "Do not reward or penalize any agent name, vendor, model, speed, or cost. "
        "Prefer objective evidence over claims. If the transcript claims success but changedDiff, "
        "artifactChecks, or evidence contradict it, score the objective evidence. "
        "A non-zero wrapper exit code is not automatic failure if evidence proves completion. "
        "Plan-mode cases are read-only: do not require changed files, and judge the "
        "delivered plan or recommendation from transcript evidence unless the criteria "
        "explicitly require a file. "
        "Build/fix/test-feature cases generally require relevant artifacts and verification "
        "unless criteria explicitly say authoring-only or no-run. "
        "Penalize missing evidence, fabricated selectors, stale evidence, forbidden commands, "
        "irrelevant edits, destructive rewrites, trivial assertions such as expect(true), "
        "assertion weakening, over-mocking the behavior under test, and unsupported claims. "
        "Reward QA-specific strengths only when evidenced: strong assertions, preserved intent, "
        "stable selectors, state-based waits, root-cause diagnosis, framework conventions, "
        "manual-test preservation, and useful evidence/reporting. "
        "For each case, return metricScores for the provided qaBench.metricIds when present. "
        "Metric scores must be based on the same evidence and criteria as the overall score. "
        "Return concise evidence snippets or references in evidence, not long quotes. "
        "Return criterionScores and confidence whenever possible. "
        "Return exactly one result for every case resultId and no extra resultIds. "
        "Use result labels consistent with the score thresholds. "
        "Keep reasons short and evidence-based.\n\n" + json.dumps(payload, indent=2)
    )


def batch_case_payload(
    result_id: str, result: dict, test_case: object, char_budget: int
) -> dict:
    task_budget = max(300, char_budget // 5)
    criteria_budget = max(300, char_budget // 5)
    diff_budget = max(500, char_budget // 4)
    evidence_budget = max(
        400, char_budget - task_budget - criteria_budget - diff_budget
    )
    return {
        "resultId": result_id,
        "evalId": result.get("evalId"),
        "caseId": result.get("caseId"),
        "mode": result.get("mode"),
        "exitCode": result.get("exitCode"),
        "timedOut": result.get("timedOut"),
        "changedFiles": result.get("changedFiles") or [],
        "changedDiff": truncate_text(str(result.get("changedDiff") or ""), diff_budget),
        "artifactChecks": result.get("artifactChecks") or {},
        "qaBench": result.get("qaBench") or {},
        "task": truncate_text(str(getattr(test_case, "input", "")), task_budget),
        "criteria": truncate_text(
            str(getattr(test_case, "expected_output", "")), criteria_budget
        ),
        "evidence": truncate_text(
            str(getattr(test_case, "actual_output", "")), evidence_budget
        ),
    }


def batch_case_char_budget(case_count: int) -> int:
    total_budget = int(os.getenv("BENCHMARK_BATCH_TOTAL_CASE_CHARS", "180000"))
    per_case_default = int(os.getenv("BENCHMARK_BATCH_CASE_CHARS", "5000"))
    if case_count <= 0:
        return per_case_default
    return max(450, min(per_case_default, total_budget // case_count))


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


def apply_batch_judgement(
    results: list[dict],
    scoring_jobs: list[tuple[int, object]],
    judge_response: BatchJudgeResponse,
) -> None:
    expected_ids = {
        results[result_index].get("_judgeResultId"): result_index
        for result_index, _ in scoring_jobs
    }
    seen_ids: set[str] = set()
    for scored in judge_response.results:
        result_id = scored.resultId
        if result_id in seen_ids or result_id not in expected_ids:
            continue
        seen_ids.add(result_id)
        result = results[expected_ids[result_id]]
        score = max(0.0, min(1.0, float(scored.score)))
        normalized_result = result_label(score, False)
        apply_score(
            result,
            score,
            scored.reason.strip() or "Batch judge returned no reason.",
            "batch-judge",
            passed_checks=max(0, int(scored.passedChecks)),
            failed_checks=max(0, int(scored.failedChecks)),
            result_override=normalized_result,
        )
        apply_qa_bench_metric_scores(result, scored.metricScores)
        apply_judge_diagnostics(result, scored)
        apply_deterministic_score_caps(result)

    for result_id, result_index in expected_ids.items():
        if result_id not in seen_ids:
            mark_unscored(
                results[result_index],
                f"Batch judge did not return a result for {result_id}.",
                "judge-error",
            )

    for result in results:
        result.pop("_judgeResultId", None)


def apply_qa_bench_metric_scores(result: dict, raw_scores) -> None:
    qa_bench = result.get("qaBench") or {}
    metric_ids = qa_bench.get("metricIds") or []
    if not metric_ids:
        return

    raw_score_map = normalize_metric_scores(raw_scores)
    normalized = {}
    for metric_id in metric_ids:
        if raw_score_map and metric_id in raw_score_map:
            raw_value = raw_score_map[metric_id]["score"]
        else:
            raw_value = result.get("score")
        if raw_value is None:
            continue
        normalized[metric_id] = max(0.0, min(1.0, float(raw_value)))

    if normalized:
        qa_bench["metricScores"] = normalized
        qa_bench["metricScoreSource"] = (
            "batch-judge" if raw_scores else "overall-score-fallback"
        )
        if raw_score_map:
            qa_bench["metricReasons"] = {
                metric_id: item.get("reason")
                for metric_id, item in raw_score_map.items()
                if item.get("reason")
            }
        result["qaBench"] = qa_bench


def normalize_metric_scores(raw_scores) -> dict[str, dict] | None:
    if not raw_scores:
        return None
    if isinstance(raw_scores, dict):
        return {
            str(metric_id): {"score": score, "reason": None}
            for metric_id, score in raw_scores.items()
        }
    normalized: dict[str, dict] = {}
    for item in raw_scores:
        if isinstance(item, JudgeMetricScore):
            metric_id = item.metricId
            score = item.score
            reason = item.reason
        elif isinstance(item, dict):
            metric_id = item.get("metricId") or item.get("metric_id")
            score = item.get("score")
            reason = item.get("reason")
        else:
            continue
        if metric_id is None or score is None:
            continue
        normalized[str(metric_id)] = {"score": score, "reason": reason}
    return normalized or None


def apply_judge_diagnostics(result: dict, scored: BatchJudgeCaseScore) -> None:
    diagnostics = {
        "confidence": clamp_optional_score(scored.confidence),
        "failureTaxonomy": scored.failureTaxonomy or [],
        "evidence": scored.evidence or [],
        "auditNotes": scored.auditNotes,
        "criterionScores": [
            criterion.model_dump()
            if isinstance(criterion, JudgeCriterionScore)
            else dict(criterion)
            for criterion in (scored.criterionScores or [])
        ],
    }
    result["judgeDiagnostics"] = diagnostics


def apply_deterministic_score_caps(result: dict) -> None:
    cap, cap_reasons = deterministic_score_cap(result)
    if cap is None or result.get("score") is None or float(result["score"]) <= cap:
        return

    original_score = float(result["score"])
    result["score"] = cap
    result["scorePercent"] = round(cap * 100)
    result["result"] = result_label(cap, bool(result.get("timedOut")))
    result["scoreSource"] = f"{result.get('scoreSource') or 'judge'}+deterministic-cap"
    if result.get("failedChecks") is not None:
        result["failedChecks"] = max(1, int(result.get("failedChecks") or 0))

    diagnostics = result.setdefault("judgeDiagnostics", {})
    diagnostics["deterministicCaps"] = {
        "originalScore": original_score,
        "cappedScore": cap,
        "reasons": cap_reasons,
    }
    reason_suffix = " Deterministic cap applied: " + ", ".join(cap_reasons) + "."
    result["reason"] = (str(result.get("reason") or "").rstrip() + reason_suffix).strip()


def deterministic_score_cap(result: dict) -> tuple[float | None, list[str]]:
    artifact_checks = result.get("artifactChecks") or {}
    warnings = set(result.get("artifactWarnings") or artifact_checks.get("warnings") or [])
    cap = None
    reasons: list[str] = []

    if "expected-artifact-change-missing" in warnings:
        cap = min_cap(cap, 0.39)
        reasons.append("expected artifact change missing")
    if "only-noisy-files-changed" in warnings:
        cap = min_cap(cap, 0.39)
        reasons.append("only noisy files changed")
    if "verification-command-not-observed" in warnings:
        cap = min_cap(cap, 0.69)
        reasons.append("verification command not observed")

    return cap, reasons


def min_cap(current: float | None, candidate: float) -> float:
    return candidate if current is None else min(current, candidate)


def clamp_optional_score(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


def apply_score(
    result: dict,
    score: float,
    reason: str,
    score_source: str,
    passed_checks: int | None = None,
    failed_checks: int | None = None,
    result_override: str | None = None,
) -> None:
    result["score"] = score
    result["scorePercent"] = round(score * 100)
    result["result"] = result_override or result_label(
        score, bool(result.get("timedOut"))
    )
    result["reason"] = reason
    result["scoreSource"] = score_source
    if passed_checks is not None:
        result["passedChecks"] = passed_checks
    if failed_checks is not None:
        result["failedChecks"] = failed_checks


def mark_unscored(result: dict, reason: str, score_source: str) -> None:
    result["score"] = None
    result["scorePercent"] = None
    result["result"] = "unscored"
    result["reason"] = reason
    result["scoreSource"] = score_source
    result["passedChecks"] = None
    result["failedChecks"] = None


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
