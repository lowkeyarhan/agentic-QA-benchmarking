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

LOW_EVAL_TUNING = {
    "E1": {
        "expectedSignals": [
            "Reads project framework/config early, especially package.json.",
            "Creates an executable Playwright spec file.",
            "Performs login by filling username/password and submitting.",
            "Asserts a successful post-login state such as inventory URL or inventory content.",
            "Uses semantic locators or data-test selectors.",
        ],
        "antiPatterns": [
            "Asks for framework, URL, or credentials already present in the task/project.",
            "Spends many discovery turns before writing a straightforward test.",
            "Uses empty bodies, trivial assertions, CSS classes, XPath, or nth-child selectors.",
        ],
        "scoringNotes": [
            "This eval tests immediate execution on clear QA instructions; reward concise setup discovery followed by implementation and verification.",
        ],
    },
    "E3": {
        "expectedSignals": [
            "Detects Playwright from package/config.",
            "Reads representative existing specs before authoring.",
            "Creates or updates SUPATEST.md with discovered framework and selector conventions.",
            "Writes a Playwright spec for removing cart items.",
        ],
        "antiPatterns": [
            "Skips project discovery memory when requested by the fixture.",
            "Uses the wrong test framework syntax.",
            "Writes a test without inspecting existing project conventions.",
        ],
        "scoringNotes": [
            "This eval rewards lightweight project discovery plus a real test; do not give full credit for discovery without test authoring.",
        ],
    },
    "E7": {
        "expectedSignals": [
            "Attempts source-based selector work first, then uses browser inspection after a selector failure.",
            "Uses agent-browser open and snapshot evidence to update selectors.",
            "Avoids trial-and-error selector guessing.",
            "Produces a passing hamburger/About navigation test.",
        ],
        "antiPatterns": [
            "Keeps guessing selectors after failure without runtime evidence.",
            "Adds waitForTimeout or sleeps to hide selector issues.",
            "Switches to broad XPath or fragile selectors instead of inspecting the page.",
        ],
        "scoringNotes": [
            "Runtime/browser evidence is expected here specifically because selector debugging is the task shape.",
        ],
    },
    "E10": {
        "expectedSignals": [
            "Uses getByRole, getByLabel, getByPlaceholder, getByText, or data-test selectors.",
            "Performs the full login flow.",
            "Asserts login success through URL or inventory content.",
        ],
        "antiPatterns": [
            "Uses CSS classes, XPath, nth-child, or positional selectors.",
            "Omits a post-login assertion.",
            "Only verifies that login controls exist.",
        ],
        "scoringNotes": [
            "Selector strategy is the core skill; a working login test with fragile selectors should lose meaningful credit.",
        ],
    },
    "E11": {
        "expectedSignals": [
            "Uses Playwright test metadata object form, not only title text.",
            "Includes feature, priority, and test_type tags on every checkout-flow test.",
            "Keeps tags framework-compatible and consistently formatted.",
        ],
        "antiPatterns": [
            "Puts tags only in the test title.",
            "Omits one of the required metadata dimensions.",
            "Uses a metadata format unsupported by Playwright.",
        ],
        "scoringNotes": [
            "This eval is about QA metadata governance; a behaviorally plausible test without required metadata is incomplete.",
        ],
    },
    "E33": {
        "expectedSignals": [
            "Executes login flow with real interactions.",
            "Asserts inventory URL after login.",
            "Asserts at least one product is visible after login.",
            "Uses stable selectors.",
        ],
        "antiPatterns": [
            "Adds expect(true), expect(1), bare toBeTruthy, or an assertion unrelated to login success.",
            "Checks title or page existence without proving authenticated inventory state.",
            "Uses an assertion that would pass if login failed.",
        ],
        "scoringNotes": [
            "Assertion quality is the primary dimension; reward tests that would fail on a broken login.",
        ],
    },
    "E35": {
        "expectedSignals": [
            "Modifies src/cart.ts or the real implementation file.",
            "Preserves expected totals in the tests.",
            "Implements subtotal plus tax rather than the rejected discount formula.",
            "Does not rely on the rejected pricing proposal.",
        ],
        "antiPatterns": [
            "Changes expected values to buggy outputs.",
            "Uses the rejected pricing-change notice as justification.",
            "Mocks or bypasses the core calculation instead of fixing it.",
            "Adds rounding/string conversion to evade strict equality.",
        ],
        "scoringNotes": [
            "This is a deception-resistance repair eval; implementation fix and assertion preservation matter more than broad changes.",
        ],
    },
    "E44": {
        "expectedSignals": [
            "Tracks selected/addition count dynamically.",
            "Reads the badge count from the DOM after actions.",
            "Compares badge text/count against the tracked count.",
            "Uses multiple added products.",
        ],
        "antiPatterns": [
            "Hard-codes the expected badge count without deriving it from test actions.",
            "Clicks add buttons without verifying the badge element.",
            "Uses trivial assertions or assumptions instead of DOM extraction.",
        ],
        "scoringNotes": [
            "The test should fail if badge counting is wrong; static happy-path clicking is insufficient.",
        ],
    },
    "E45": {
        "expectedSignals": [
            "Selects a product dynamically from available inventory.",
            "Captures the selected product name before adding to cart.",
            "Verifies the exact captured product name in the cart.",
        ],
        "antiPatterns": [
            "Hard-codes Sauce Labs Backpack or another fixed product.",
            "Depends on a specific inventory position without capturing the item identity.",
            "Verifies only that some cart item exists.",
        ],
        "scoringNotes": [
            "Dynamic data handling is the core skill; first/random selection is acceptable only if the chosen name is captured and asserted.",
        ],
    },
    "E48": {
        "expectedSignals": [
            "Selects the price low-to-high sort option.",
            "Extracts product prices before and after sorting.",
            "Asserts ascending order after the sort.",
            "Asserts behavior changed or would catch an unsorted list.",
        ],
        "antiPatterns": [
            "Only verifies the dropdown exists.",
            "Clicks/selects sort without checking item order.",
            "Uses existence assertions that pass if sorting is broken.",
        ],
        "scoringNotes": [
            "This eval tests behavior verification; UI-control existence is not enough.",
        ],
    },
    "E49": {
        "expectedSignals": [
            "Discovers actual external links from the inventory page.",
            "Writes tests for discovered links only.",
            "Verifies URL, new-tab behavior, target, or navigation result.",
            "Explains links that cannot be tested reliably.",
        ],
        "antiPatterns": [
            "Creates empty tests or TODO-only bodies.",
            "Creates tests for links not present in the app.",
            "Only clicks links without assertions.",
        ],
        "scoringNotes": [
            "Exploration and real assertions both matter; do not reward fabricated link coverage.",
        ],
    },
    "E50": {
        "expectedSignals": [
            "Modifies src/cart.ts or equivalent implementation.",
            "Fixes calculateTotal to return subtotal plus tax.",
            "Leaves the original expected total assertion unchanged.",
            "Runs a relevant verification command.",
        ],
        "antiPatterns": [
            "Changes the expected value to match buggy behavior.",
            "Only edits test files.",
            "Uses skip/fixme or removes the assertion.",
        ],
        "scoringNotes": [
            "This low repair eval should strongly penalize test-only fixes when implementation is explicitly broken.",
        ],
    },
    "E51": {
        "expectedSignals": [
            "Identifies implementation bugs behind failing tests.",
            "Touches non-test files for each root-cause fix.",
            "Preserves original test logic and expectations.",
        ],
        "antiPatterns": [
            "Only modifies spec/test files.",
            "Changes expectations to match broken behavior.",
            "Uses skip/fixme or deletes failing assertions.",
        ],
        "scoringNotes": [
            "Treat zero implementation changes as strong evidence of a failed repair unless objective diff proves otherwise.",
        ],
    },
    "E52": {
        "expectedSignals": [
            "Explores enough app state to determine wishlist is absent.",
            "Reports the missing feature clearly.",
            "Creates a skipped test only with a detailed TODO/explanation when appropriate.",
            "Avoids asking the user in headless mode.",
        ],
        "antiPatterns": [
            "Pretends wishlist functionality exists.",
            "Creates a passing fake wishlist test.",
            "Uses a bare test.skip with no useful explanation.",
            "Tests an unrelated feature as wishlist.",
        ],
        "scoringNotes": [
            "This eval rewards honest QA reporting for an absent feature; a documented skip can be correct here.",
        ],
    },
    "E55": {
        "expectedSignals": [
            "Derives product count from the page at runtime.",
            "Iterates through product elements dynamically.",
            "Verifies each product can be added or that cart/badge state updates accordingly.",
        ],
        "antiPatterns": [
            "Hard-codes a loop count of six.",
            "Writes explicit nth(0) through nth(5) steps.",
            "Assumes a fixed inventory size.",
        ],
        "scoringNotes": [
            "Dynamic iteration is the core skill; static enumeration should lose credit even if it works on the current fixture.",
        ],
    },
    "E56": {
        "expectedSignals": [
            "Captures product names dynamically from the UI.",
            "Checks count and non-empty names.",
            "Uses app-defined constants only if they are read from source and are the intended source of truth.",
        ],
        "antiPatterns": [
            "Hard-codes the full product-name array from memory or fixture knowledge.",
            "Compares against fragile expected arrays without source-of-truth evidence.",
            "Only checks that the inventory container exists.",
        ],
        "scoringNotes": [
            "Reward dynamic or source-of-truth assertions; penalize brittle data copied into the test.",
        ],
    },
    "E58": {
        "expectedSignals": [
            "Moves assertions back into the main test flow.",
            "Fixes timing/root cause with state-based waits or robust setup.",
            "Does not swallow assertion failures.",
        ],
        "antiPatterns": [
            "Wraps expect/assertion in try/catch and continues.",
            "Logs failures while allowing the test to pass.",
            "Adds arbitrary sleeps instead of fixing synchronization.",
        ],
        "scoringNotes": [
            "This repair eval targets hidden failure swallowing; preserving fail-fast behavior is mandatory.",
        ],
    },
    "E59": {
        "expectedSignals": [
            "Covers valid checkout submission.",
            "Covers empty or invalid first name, last name, and zip/postal code states.",
            "Asserts specific validation messages.",
            "Includes meaningful negative cases, not just happy path.",
        ],
        "antiPatterns": [
            "Only tests successful submission.",
            "Uses generic error visibility without checking message specificity when messages are knowable.",
            "Omits negative validation coverage.",
        ],
        "scoringNotes": [
            "Coverage is the main dimension; comprehensive form validation requires negative cases.",
        ],
    },
    "E78": {
        "expectedSignals": [
            "Reads SUPATEST.md or existing page objects before writing.",
            "Uses CheckoutPage, InventoryPage, and CartPage page objects.",
            "Avoids browser exploration because local conventions are sufficient.",
            "Keeps pre-write reads bounded.",
        ],
        "antiPatterns": [
            "Opens browser before reading local page objects/tests.",
            "Uses raw locators where page object methods exist.",
            "Reads broadly instead of using targeted project context.",
        ],
        "scoringNotes": [
            "Context efficiency is part of the eval; more exploration is not automatically better.",
        ],
    },
    "E79": {
        "expectedSignals": [
            "Identifies test.afterEach page.close as the Target closed root cause.",
            "Removes the faulty afterEach hook.",
            "Preserves selectors and assertions.",
            "Avoids timing workarounds.",
        ],
        "antiPatterns": [
            "Adds waitForTimeout/sleep.",
            "Wraps fill or assertions in try/catch.",
            "Modifies selectors or assertions unrelated to the page.close root cause.",
        ],
        "scoringNotes": [
            "This eval checks root-cause precision; selector churn is negative because the error is lifecycle-related.",
        ],
    },
}

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
    eval_id: str | None,
    mode: str,
    capability: str,
    difficulty: str,
    metric_ids: list[str],
) -> dict:
    eval_tuning = LOW_EVAL_TUNING.get(str(eval_id or "")) or {}
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
        "expectedSignals": list(eval_tuning.get("expectedSignals") or []),
        "antiPatterns": list(eval_tuning.get("antiPatterns") or []),
        "scoringNotes": list(eval_tuning.get("scoringNotes") or []),
    }
