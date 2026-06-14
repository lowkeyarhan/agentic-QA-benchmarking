from __future__ import annotations


LOW_DIFFICULTY_EVAL_IDS = [
    "E1",
    "E3",
    "E7",
    "E10",
    "E11",
    "E33",
    "E35",
    "E44",
    "E45",
    "E48",
    "E49",
    "E50",
    "E51",
    "E52",
    "E55",
    "E56",
    "E58",
    "E59",
    "E78",
    "E79",
]

DIFFICULTY_GUIDANCE = {
    "low": (
        "Low difficulty means baseline QA competency, not relaxed correctness. "
        "A strong answer should complete the requested simple task with a real "
        "test or targeted fix, meaningful assertions, stable selectors, tight "
        "scope, and appropriate verification. Penalize missing basics heavily."
    ),
    "medium": (
        "Medium difficulty expects the same baseline QA quality plus context "
        "selection across more files, stronger coverage judgment, and fewer "
        "unnecessary tool turns."
    ),
    "high": (
        "High difficulty expects robust root-cause judgment, assertion "
        "preservation, state-based timing, and careful handling of competing "
        "evidence."
    ),
    "ultra": (
        "Ultra difficulty expects production-grade judgment under stale context, "
        "multiple plausible wrong paths, framework variation, or scoped runtime "
        "evidence requirements."
    ),
    "max": (
        "Max difficulty expects enterprise QA behavior on mobile, CI, device, "
        "or production-regression scenarios with precise evidence use and no "
        "destructive shortcuts."
    ),
}

MODE_GUIDANCE = {
    "build": (
        "For build tasks, inspect generated tests directly. Reward requested "
        "flow coverage, executable framework syntax, meaningful assertions, "
        "stable selectors, local conventions, and the smallest useful "
        "verification command."
    ),
    "fix": (
        "For fix tasks, identify whether the actual change repairs test code, "
        "page objects, app code, data setup, or config. Reward root-cause fixes "
        "and assertion preservation; penalize test-only workarounds, skips, "
        "weakened expectations, and unrelated edits."
    ),
    "plan": (
        "For plan tasks, judge the delivered QA analysis, affected flows, risk "
        "tradeoffs, and Not Testing rationale. Do not require file edits unless "
        "the criteria explicitly require artifacts."
    ),
    "report": (
        "For report tasks, judge whether logs/artifacts are summarized into "
        "actionable failure categories, evidence, risks, and next steps."
    ),
    "test-feature": (
        "For test-feature tasks, judge end-to-end feature validation, runtime "
        "evidence, bug discovery, coverage, and report quality."
    ),
}

CAPABILITY_GUIDANCE = {
    "test-authoring": (
        "Generated tests must exercise the requested behavior and contain "
        "assertions that would fail if the behavior regressed."
    ),
    "test-repair": (
        "Repairs must preserve the existing test's intent and fix the real "
        "root cause instead of making the test easier to pass."
    ),
    "project-discovery": (
        "Project discovery should be targeted: read enough conventions to write "
        "consistent tests, then stop exploring and implement."
    ),
    "browser-context": (
        "Browser or device context is valuable when source code is insufficient "
        "or a selector/runtime failure needs inspection; unnecessary runtime "
        "exploration should not be rewarded."
    ),
    "metadata-governance": (
        "Metadata work must use the framework's supported tag/annotation format "
        "and preserve manual, priority, ownership, or feature semantics."
    ),
    "root-cause-debugging": (
        "Root-cause debugging should classify selector, timing, state, data, "
        "environment, and app-bug causes from evidence, not guesses."
    ),
    "feature-validation": (
        "Feature validation should cover user-visible flows, important states, "
        "and evidence that supports the final QA report."
    ),
    "reporting-and-evidence": (
        "Reporting should connect logs/artifacts to concrete findings, impact, "
        "and recommended follow-up."
    ),
    "mobile-qa": (
        "Mobile QA should use current hierarchy/device evidence and stable "
        "accessibility/resource identifiers instead of stale or broad selectors."
    ),
}

METRIC_QUALITY_SIGNALS = {
    "relevance": "Changes target the exact requested QA behavior or failure.",
    "coverage": "Important path, state, or regression coverage is present.",
    "assertion_quality": "Assertions verify product behavior, not implementation trivia.",
    "test_integrity": "No skips, only markers, trivial assertions, weakened expectations, or swallowed failures.",
    "maintainability": "Changes follow local file structure, helpers, page objects, and naming patterns.",
    "selector_strategy": "Selectors are stable and consistent with project conventions.",
    "state_timing_reliability": "State-based waits are used instead of fixed sleeps or timing guesses.",
    "root_cause_accuracy": "The fix or report names the actual root cause supported by evidence.",
    "evidence_quality": "Runtime/log/reporter evidence is used when needed and not fabricated.",
    "reporting_quality": "Output is concise, actionable, and clear about risks or blockers.",
    "metadata_quality": "Required tags, IDs, owner, priority, retry, flaky, or manual metadata are correct.",
    "framework_adaptation": "The solution uses the target framework's syntax and execution conventions.",
    "manual_workflow": "Manual tests are preserved or reported without accidental automation conversion.",
    "ci_log_analysis": "Logs/stdout/stderr are distilled into actionable diagnosis.",
    "mobile_context": "Mobile hierarchy, platform, simulator, or device-specific context is handled correctly.",
}


def guidance_for_eval(
    mode: str,
    capability: str,
    difficulty: str,
    metric_ids: list[str],
) -> dict:
    guidance = [
        text
        for text in [
            DIFFICULTY_GUIDANCE.get(difficulty),
            MODE_GUIDANCE.get(mode),
            CAPABILITY_GUIDANCE.get(capability),
        ]
        if text
    ]
    signals = [
        METRIC_QUALITY_SIGNALS[metric_id]
        for metric_id in metric_ids
        if metric_id in METRIC_QUALITY_SIGNALS
    ]
    return {
        "judgeGuidance": guidance,
        "qualitySignals": signals,
    }
