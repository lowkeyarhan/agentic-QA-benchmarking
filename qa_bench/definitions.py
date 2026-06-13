from __future__ import annotations


QA_BENCH_VERSION = "qa-bench-v1"

QA_BENCH_METRICS = {
    "relevance": {
        "label": "Relevance",
        "description": "The work targets the requested QA problem instead of generic coding changes.",
    },
    "coverage": {
        "label": "Coverage",
        "description": "Critical user flows, states, roles, and regressions are covered.",
    },
    "assertion_quality": {
        "label": "Assertion quality",
        "description": "Assertions verify meaningful product behavior without trivial or weak checks.",
    },
    "test_integrity": {
        "label": "Test integrity",
        "description": "The agent preserves intent and does not weaken, skip, or fake tests.",
    },
    "maintainability": {
        "label": "Maintainability",
        "description": "Changes follow local test structure, page objects, tags, and naming conventions.",
    },
    "selector_strategy": {
        "label": "Selector strategy",
        "description": "Selectors are stable, user-facing when appropriate, and consistent with the project.",
    },
    "state_timing_reliability": {
        "label": "State and timing reliability",
        "description": "The solution uses state-based waits and robust setup instead of brittle sleeps.",
    },
    "root_cause_accuracy": {
        "label": "Root-cause accuracy",
        "description": "Failure diagnosis distinguishes test bugs, app bugs, data drift, selectors, and timing.",
    },
    "evidence_quality": {
        "label": "Evidence quality",
        "description": "The agent uses logs, reporters, traces, screenshots, videos, or browser/device evidence correctly.",
    },
    "reporting_quality": {
        "label": "Reporting quality",
        "description": "The output summarizes findings, risks, failures, and next actions clearly for QA teams.",
    },
    "metadata_quality": {
        "label": "Metadata quality",
        "description": "Stable IDs, retries, ownership, priority, feature tags, and manual tags are preserved or added when required.",
    },
    "framework_adaptation": {
        "label": "Framework adaptation",
        "description": "The agent adapts to Playwright, Cypress, WDIO, Appium, Maestro, JUnit, or TestNG conventions.",
    },
    "manual_workflow": {
        "label": "Manual workflow",
        "description": "Manual-test requirements are preserved, tagged, and reported without being converted incorrectly.",
    },
    "ci_log_analysis": {
        "label": "CI log analysis",
        "description": "The agent extracts actionable diagnosis from CI logs, stdout, stderr, and reporter output.",
    },
    "mobile_context": {
        "label": "Mobile context",
        "description": "The agent handles mobile hierarchy, Appium, Maestro, simulator, or device-specific evidence.",
    },
}

QA_BENCH_CAPABILITIES = {
    "test-authoring": {
        "label": "Test authoring",
        "description": "Create useful automated tests from natural-language QA requests.",
    },
    "test-repair": {
        "label": "Test repair",
        "description": "Fix failing tests while preserving assertion intent and local conventions.",
    },
    "root-cause-debugging": {
        "label": "Root-cause debugging",
        "description": "Classify failures into selector, timing, state, data, environment, or app-bug causes.",
    },
    "feature-validation": {
        "label": "Feature validation",
        "description": "Validate a feature end to end with runtime evidence and an actionable report.",
    },
    "risk-planning": {
        "label": "Risk planning",
        "description": "Produce read-only QA plans, coverage matrices, and regression scope.",
    },
    "reporting-and-evidence": {
        "label": "Reporting and evidence",
        "description": "Summarize test health, logs, artifacts, failures, and next steps.",
    },
    "project-discovery": {
        "label": "Project discovery",
        "description": "Infer framework, selectors, setup, page objects, and project conventions.",
    },
    "metadata-governance": {
        "label": "Metadata governance",
        "description": "Manage tags, stable IDs, ownership, priority, retries, flaky status, and manual markers.",
    },
    "mobile-qa": {
        "label": "Mobile QA",
        "description": "Handle mobile app, WDIO/Appium, Maestro, simulator, and view-hierarchy tasks.",
    },
    "browser-context": {
        "label": "Browser context",
        "description": "Use browser or runtime context to inspect UI state and choose robust QA actions.",
    },
}
