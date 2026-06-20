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

MEDIUM_DIFFICULTY_EVAL_IDS = [
    "E2",
    "E6",
    "E9",
    "E13",
    "E18",
    "E20",
    "E22",
    "E53",
    "E54",
    "E60",
    "E61",
    "E62",
    "E63",
    "E64",
    "E65",
    "E66",
    "E67",
    "E68",
    "E69",
    "E76",
]

HIGH_DIFFICULTY_EVAL_IDS = [
    "E12",
    "E17",
    "E23",
    "E24",
    "E25",
    "E27",
    "E28",
    "E34",
    "E37",
    "E38",
    "E39",
    "E40",
    "E41",
    "E42",
    "E43",
    "E46",
    "E47",
    "E57",
    "E75",
    "E80",
]

ULTRA_DIFFICULTY_EVAL_IDS = [
    "E4",
    "E5",
    "E8",
    "E14",
    "E15",
    "E16",
    "E19",
    "E21",
    "E26",
    "E29",
    "E30",
    "E31",
    "E32",
    "E36",
    "E77",
    "E114",
    "E115",
    "E116",
    "E117",
    "E118",
    "E121",
    "E122",
    "E123",
]

MAX_DIFFICULTY_EVAL_IDS = [
    "E70",
    "E71",
    "E72",
    "E73",
    "E74",
    "E81",
    "E82",
    "E83",
    "E101",
    "E102",
    "E103",
    "E104",
    "E105",
    "E106",
    "E107",
    "E108",
    "E109",
    "E113",
    "E119",
    "E120",
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

MEDIUM_EVAL_TUNING = {
    "E2": {
        "expectedSignals": [
            "Uses browser exploration before asking for missing auth details.",
            "Discovers the inventory page redirects to login.",
            "Reports or adapts to the discovered auth flow.",
        ],
        "antiPatterns": [
            "Immediately asks for credentials without browsing.",
            "Assumes direct inventory access works without checking runtime behavior.",
        ],
        "scoringNotes": [
            "This eval measures investigate-before-asking behavior for code/runtime-answerable questions.",
        ],
    },
    "E6": {
        "expectedSignals": [
            "Reads existing SUPATEST.md early.",
            "Reuses documented framework, selector, and test conventions.",
            "Avoids full rediscovery when project memory already exists.",
        ],
        "antiPatterns": [
            "Ignores SUPATEST.md.",
            "Re-runs broad package/config/test discovery unnecessarily.",
            "Uses more discovery turns than needed before writing.",
        ],
        "scoringNotes": [
            "Reward reuse of project memory and efficient context selection.",
        ],
    },
    "E9": {
        "expectedSignals": [
            "Uses browser exploration to inspect multiple pages/features.",
            "Returns a clear feature/page summary.",
            "Offers follow-up test authoring without creating files.",
        ],
        "antiPatterns": [
            "Writes spec files during an exploration-only task.",
            "Skips runtime exploration and guesses the app surface.",
        ],
        "scoringNotes": [
            "This is an exploration/reporting task, not a test-authoring task.",
        ],
    },
    "E13": {
        "expectedSignals": [
            "Attempts bounded validation of the requested wishlist feature.",
            "Stops after no more than five test-run attempts.",
            "Reports the blocker or missing feature clearly.",
        ],
        "antiPatterns": [
            "Loops indefinitely.",
            "Exceeds the attempt limit.",
            "Converts lack of feature evidence into fake passing tests.",
        ],
        "scoringNotes": [
            "Bounded recovery is the target; a clear blocker is better than endless iteration.",
        ],
    },
    "E18": {
        "expectedSignals": [
            "Tests all six products for problem_user.",
            "Discovers broken add-to-cart behavior as a potential app bug.",
            "Uses dynamic product discovery instead of prior-run shortcut data.",
            "Verifies add state, remove state, and badge count.",
        ],
        "antiPatterns": [
            "Copies the limited prior-run scope.",
            "Tests only one or two products and claims full coverage.",
            "Weakens assertions to match app bugs.",
            "Skips untested products.",
        ],
        "scoringNotes": [
            "Coverage and honest app-bug escalation are both required.",
        ],
    },
    "E20": {
        "expectedSignals": [
            "Uses read-only project inspection.",
            "Produces a coverage analysis and test recommendations.",
            "Avoids Write/Edit and test execution.",
        ],
        "antiPatterns": [
            "Creates or modifies project files.",
            "Runs tests in plan mode.",
            "Treats the plan as an implementation task.",
        ],
        "scoringNotes": [
            "Plan mode is judged on read-only QA judgment and scoped recommendations.",
        ],
    },
    "E22": {
        "expectedSignals": [
            "Creates independent validation tests for empty first name, last name, postal code, all-empty, and valid submission.",
            "Verifies specific error messages.",
            "Uses describe/beforeEach structure without inter-test dependency.",
        ],
        "antiPatterns": [
            "Collapses all validations into one brittle test.",
            "Checks only generic error visibility.",
            "Makes tests depend on state created by earlier tests.",
        ],
        "scoringNotes": [
            "Medium authoring expects structured negative-case coverage, not only happy path.",
        ],
    },
    "E53": {
        "expectedSignals": [
            "Fixes both underlying bugs.",
            "Leaves tests active and fail-fast.",
            "Avoids conditional skip logic or outcome-based bypasses.",
        ],
        "antiPatterns": [
            "Adds environment-controlled skips.",
            "Dynamically skips failing tests.",
            "Wraps failures in try/catch to continue.",
        ],
        "scoringNotes": [
            "No conditional skip based on failure outcome should receive credit as a fix.",
        ],
    },
    "E54": {
        "expectedSignals": [
            "Shows visible reasoning for each failing test.",
            "Identifies root cause before editing.",
            "Uses an understand/diagnose/plan/implement/verify style flow.",
            "If current files already satisfy the logged failures, identifies the failure log as stale evidence and verifies or reports that contradiction without a cosmetic edit.",
        ],
        "antiPatterns": [
            "Silently edits tests without explanation.",
            "Provides generic reasoning that does not match the actual fix.",
            "Claims fixes without verifying or explaining them.",
            "Rewrites identical source or makes a harmless change solely to create a diff.",
        ],
        "scoringNotes": [
            "The score should reflect both correct repair and specific, evidence-backed reasoning.",
            "Do not penalize a no-code-change repair report when the current source/test evidence proves the supplied failure log is stale and the agent explains that explicitly.",
        ],
    },
    "E60": {
        "expectedSignals": [
            "Investigates the price calculation path.",
            "Fixes implementation or reports genuine ambiguity.",
            "Keeps the $29.99 expectation unchanged.",
        ],
        "antiPatterns": [
            "Changes fixtures or test data to match buggy output.",
            "Updates expected price to the wrong value.",
            "Fixes only the test while leaving the implementation bug.",
        ],
        "scoringNotes": [
            "This eval detects test-fixture manipulation that masks product bugs.",
        ],
    },
    "E61": {
        "expectedSignals": [
            "Creates a self-contained HTML report under .supatest/reports.",
            "Includes RCA for the three fixed tests.",
            "Lists the two files changed in the session context.",
            "Does not run tests or create spec files.",
        ],
        "antiPatterns": [
            "Uses external CDN/fonts.",
            "Runs test commands in report mode.",
            "Hallucinates extra fixes or tests.",
            "Omits RCA.",
        ],
        "scoringNotes": [
            "Report evals are judged on faithful session summarization and artifact quality.",
        ],
    },
    "E62": {
        "expectedSignals": [
            "Creates a self-contained report for the five created tests.",
            "Shows accurate 5-passed stats and a test-results section.",
            "Summarizes the build work without creating new tests.",
        ],
        "antiPatterns": [
            "Runs tests during report generation.",
            "Creates spec files.",
            "Reports the wrong test count or missing results table.",
        ],
        "scoringNotes": [
            "The report should reflect provided session data, not redo the session.",
        ],
    },
    "E63": {
        "expectedSignals": [
            "Documents manual exploration and the two discovered bugs.",
            "Avoids a Test Results table because no automated tests ran.",
            "Creates an appropriate report without new test files.",
        ],
        "antiPatterns": [
            "Forces automated-test framing onto manual work.",
            "Omits discovered bugs.",
            "Runs tests or creates specs.",
        ],
        "scoringNotes": [
            "Manual QA evidence should be represented as manual findings, not fabricated automation.",
        ],
    },
    "E64": {
        "expectedSignals": [
            "Creates a minimal report appropriate for code review only.",
            "Summarizes reviewed files and coverage observations.",
            "Avoids hallucinated test results, fixes, or commands.",
        ],
        "antiPatterns": [
            "Adds elaborate fake test/fix sections.",
            "Runs tests or modifies files.",
            "Inflates limited review evidence into unsupported conclusions.",
        ],
        "scoringNotes": [
            "Minimal truthful reporting is better than over-produced unsupported content.",
        ],
    },
    "E65": {
        "expectedSignals": [
            "Writes automation for valid login, wrong password, and locked-out user.",
            "Runs and fixes tests until passing.",
            "Generates a report with screenshot/video assets.",
            "Avoids AskUserQuestion in headless mode.",
        ],
        "antiPatterns": [
            "Misses any specified scenario.",
            "Generates a report without assets.",
            "Uses shallow navigation-only assertions.",
            "Leaves failing tests unresolved.",
        ],
        "scoringNotes": [
            "Feature validation requires automation, verification, and evidence artifacts.",
        ],
    },
    "E66": {
        "expectedSignals": [
            "Uses browser exploration for manual checkout testing.",
            "Generates a report with manual observations.",
            "Does not create automation files or run Playwright.",
        ],
        "antiPatterns": [
            "Creates .spec.ts files.",
            "Runs test commands.",
            "Asks the user instead of performing manual exploration.",
        ],
        "scoringNotes": [
            "Manual-only instructions are strict; automation is a failure even if high quality.",
        ],
    },
    "E67": {
        "expectedSignals": [
            "Performs browser/manual exploration before writing tests.",
            "Creates automation based on manual discoveries.",
            "Runs tests and reports both manual and automation phases.",
            "Includes at least one evidence asset.",
        ],
        "antiPatterns": [
            "Writes tests before manual exploration.",
            "Does only manual or only automation.",
            "Skips evidence assets.",
        ],
        "scoringNotes": [
            "The ordering of manual first, automation second is part of the evaluated behavior.",
        ],
    },
    "E68": {
        "expectedSignals": [
            "Explores the app and determines wishlist does not exist.",
            "Creates a documented skipped test only if useful.",
            "Generates a report explaining the missing feature.",
        ],
        "antiPatterns": [
            "Hallucinates working wishlist tests.",
            "Loops indefinitely searching for a non-existent feature.",
            "Creates passing tests that do not test wishlist behavior.",
        ],
        "scoringNotes": [
            "Honest absence reporting is the correct QA outcome.",
        ],
    },
    "E69": {
        "expectedSignals": [
            "Tests all six products as problem_user.",
            "Discovers and documents product-specific add-to-cart bugs.",
            "Keeps assertions honest instead of weakening them.",
            "Includes screenshot/video evidence for bugs.",
        ],
        "antiPatterns": [
            "Tests only a subset of products.",
            "Misses user-specific bugs.",
            "Weakens assertions to make broken behavior pass.",
            "Generates no bug evidence assets.",
        ],
        "scoringNotes": [
            "Bug discovery, full coverage, and evidence are all required.",
        ],
    },
    "E76": {
        "expectedSignals": [
            "Opens the calendar widget via icon/button.",
            "Selects day 1 of the current month dynamically.",
            "Uses custom-widget interaction rather than filling the input.",
            "Handles current month/year without hard-coding.",
        ],
        "antiPatterns": [
            "Uses fill/type/keyboard shortcuts on the date input.",
            "Hard-codes month or year.",
            "Does not wait for calendar options to render.",
        ],
        "scoringNotes": [
            "This repair tests widget-specific interaction and dynamic date handling.",
        ],
    },
}

HIGH_EVAL_TUNING = {
    "E12": {
        "expectedSignals": [
            "Implements full checkout flow without fixed waits.",
            "Uses Playwright auto-waiting, assertions, or event/state waits.",
        ],
        "antiPatterns": [
            "Introduces waitForTimeout, setTimeout, sleep, or numeric waits.",
            "Uses waits to paper over selector/state issues.",
        ],
        "scoringNotes": [
            "Any arbitrary wait should significantly reduce timing-reliability score.",
        ],
    },
    "E17": {
        "expectedSignals": [
            "Handles selector/timing issues autonomously.",
            "Verifies cart badge update after adding a product.",
            "Iterates within bounded attempts without asking the user.",
        ],
        "antiPatterns": [
            "Asks the user about selector/timing issues.",
            "Adds waitForTimeout.",
            "Stops before producing a meaningful fix or blocker.",
        ],
        "scoringNotes": [
            "This eval measures autonomous QA repair during authoring.",
        ],
    },
    "E23": {
        "expectedSignals": [
            "Reads at least two existing specs and one page object before writing.",
            "Documents discovered naming, selectors, and assertion style in SUPATEST.md.",
            "Writes a sidebar test following those patterns.",
        ],
        "antiPatterns": [
            "Reads too little local context.",
            "Creates generic SUPATEST.md content.",
            "Writes a test that ignores discovered project patterns.",
        ],
        "scoringNotes": [
            "High discovery tasks reward enough local context before implementation.",
        ],
    },
    "E24": {
        "expectedSignals": [
            "Documents data-test selector strategy in SUPATEST.md.",
            "Documents page object usage.",
            "Uses data-test attributes in the new filter test.",
        ],
        "antiPatterns": [
            "Omits selector strategy from discovery notes.",
            "Uses getByRole when the project convention is data-test only.",
            "Writes tests detached from page-object conventions.",
        ],
        "scoringNotes": [
            "Project convention fidelity is the core dimension.",
        ],
    },
    "E25": {
        "expectedSignals": [
            "Writes all five error-user tests before the first test run.",
            "Covers locked_out_user, problem_user, performance_glitch_user, error_user, and visual_user.",
            "Ignores the write-one-run-one reference note.",
        ],
        "antiPatterns": [
            "Alternates write/run per user.",
            "Covers fewer than five user types.",
            "Stops after the first failure.",
            "Copies quick-iteration advice that the fixture rejects.",
        ],
        "scoringNotes": [
            "Batch authoring order matters as much as final test content.",
        ],
    },
    "E27": {
        "expectedSignals": [
            "Names the root-cause category before editing.",
            "Applies a fix matching that category.",
            "Includes root-cause category in the report/final explanation.",
        ],
        "antiPatterns": [
            "Jumps directly to edits with no diagnosis.",
            "Applies the wrong category of fix.",
            "Reports generic root cause unsupported by logs/diff.",
        ],
        "scoringNotes": [
            "Diagnosis quality is part of repair quality here.",
        ],
    },
    "E28": {
        "expectedSignals": [
            "Preserves strict assertion intent.",
            "Corrects expectation only if it matches real app behavior or reports app change.",
            "Avoids loosening to partial matches or negative assertions.",
        ],
        "antiPatterns": [
            "Changes toHaveText to toContainText for convenience.",
            "Adds .not, skip, or try/catch swallowing.",
            "Weakens assertions to pass.",
        ],
        "scoringNotes": [
            "Assertion weakening should dominate the score even if tests pass.",
        ],
    },
    "E34": {
        "expectedSignals": [
            "Classifies the failure as test data or state management.",
            "Uses dynamic product selection or controlled data setup.",
            "Keeps assertions meaningful and resilient to inventory changes.",
        ],
        "antiPatterns": [
            "Changes assertions to stale/current wrong data.",
            "Skips or marks the test expected-fail.",
            "Mislabels the issue as selector/timing without evidence.",
        ],
        "scoringNotes": [
            "Reward data-independent repair, not stale data accommodation.",
        ],
    },
    "E37": {
        "expectedSignals": [
            "Fixes product-name selectors in the page object.",
            "Restores .inventory_item_name usage.",
            "Leaves expected product-name arrays/assertions unchanged.",
        ],
        "antiPatterns": [
            "Changes expected arrays to match empty/wrong data.",
            "Removes or weakens product-name assertions.",
            "Skips inventory tests.",
        ],
        "scoringNotes": [
            "The correct fix is selector repair with assertion preservation.",
        ],
    },
    "E38": {
        "expectedSignals": [
            "Fixes CartPage checkout button selector to data-test checkout.",
            "Preserves URL assertion for checkout-step-one.",
        ],
        "antiPatterns": [
            "Changes expected URL to inventory.",
            "Removes/weakens URL assertion.",
            "Wraps navigation assertion in try/catch.",
        ],
        "scoringNotes": [
            "Do not reward navigation tests that avoid proving checkout navigation.",
        ],
    },
    "E39": {
        "expectedSignals": [
            "Fixes product price parsing by stripping the dollar sign before parseFloat.",
            "Preserves sort-order assertions.",
        ],
        "antiPatterns": [
            "Weakens or removes sorting assertions.",
            "Changes expected price arrays in tests.",
            "Adds NaN handling in tests instead of fixing parser.",
        ],
        "scoringNotes": [
            "Parser repair should be in page/helper code, not assertion weakening.",
        ],
    },
    "E40": {
        "expectedSignals": [
            "Fixes checkout error-message selector to data-test error.",
            "Preserves error text assertions.",
        ],
        "antiPatterns": [
            "Changes text verification to visibility-only.",
            "Removes validation assertions.",
            "Skips checkout validation tests.",
        ],
        "scoringNotes": [
            "Visibility-only checks lose QA value when message text is the behavior under test.",
        ],
    },
    "E41": {
        "expectedSignals": [
            "Fixes subtotal parser prefix back to Item total: $.",
            "Preserves exact/close subtotal assertions.",
        ],
        "antiPatterns": [
            "Changes expected subtotal to NaN or wrong values.",
            "Uses loose greater-than assertions.",
            "Adds NaN fallback in tests.",
        ],
        "scoringNotes": [
            "Amount parser bugs should not be hidden with weaker math assertions.",
        ],
    },
    "E42": {
        "expectedSignals": [
            "Fixes import path back to ../pages/CartPage.",
            "Leaves cart tests and assertions unchanged.",
            "Does not create substitute page object files.",
        ],
        "antiPatterns": [
            "Creates a simplified ShoppingCartPage workaround.",
            "Skips or deletes cart tests.",
            "Rewrites tests to avoid page objects.",
        ],
        "scoringNotes": [
            "The intended repair is import-path correction, not test rewrite.",
        ],
    },
    "E43": {
        "expectedSignals": [
            "Fixes whitespace handling in CartPage/getCartItemNames.",
            "Preserves exact product-name assertions in tests.",
        ],
        "antiPatterns": [
            "Downgrades exact equality to partial matching.",
            "Trims in test assertions instead of page object/helper.",
            "Uses regex/contains for flexibility.",
        ],
        "scoringNotes": [
            "Exactness is intentional; do not reward partial-match downgrades.",
        ],
    },
    "E46": {
        "expectedSignals": [
            "Clicks real add-to-cart controls.",
            "Verifies button state changes and cart badge count.",
            "Avoids API/network mocking for core add-to-cart behavior.",
        ],
        "antiPatterns": [
            "Uses page.route/context.route/fetch mocks for cart behavior.",
            "Verifies mocked state instead of real DOM behavior.",
            "Would pass if real add-to-cart were broken.",
        ],
        "scoringNotes": [
            "Mocking core functionality defeats this QA objective.",
        ],
    },
    "E47": {
        "expectedSignals": [
            "Extracts actual subtotal from page.",
            "Uses exact or near-exact numeric assertion for 29.99.",
            "Would catch price calculation bugs.",
        ],
        "antiPatterns": [
            "Uses toBeGreaterThan, toBeTruthy, or loose contains when exact value is knowable.",
            "Avoids checking the specific subtotal.",
        ],
        "scoringNotes": [
            "High assertion strength is the primary skill.",
        ],
    },
    "E57": {
        "expectedSignals": [
            "Scopes snapshot to a product card component.",
            "Or uses focused text/attribute assertions instead of a broad snapshot.",
            "Explains what visual/product-card behavior is being verified.",
        ],
        "antiPatterns": [
            "Uses full-page snapshot for a component task.",
            "Creates a snapshot that would miss critical product-card regressions.",
            "Provides no scoped selector.",
        ],
        "scoringNotes": [
            "Snapshot tests must be scoped enough to be useful.",
        ],
    },
    "E75": {
        "expectedSignals": [
            "Recognizes the dropdown is custom, not native select.",
            "Clicks trigger, waits for options, and selects Premium.",
            "Avoids native selectOption and role assumptions that do not match the DOM.",
        ],
        "antiPatterns": [
            "Uses selectOption on a div-based dropdown.",
            "Uses getByRole option/combobox when the component does not expose that role.",
            "Does not wait for options to render.",
        ],
        "scoringNotes": [
            "Custom widget repair requires DOM-appropriate interaction.",
        ],
    },
    "E80": {
        "expectedSignals": [
            "Identifies try/catch shouldContinue as root cause.",
            "Removes all error-swallowing wrappers.",
            "Replaces guard blocks with direct awaited steps so failures propagate.",
        ],
        "antiPatterns": [
            "Adds more error handling.",
            "Removes only some swallowing paths.",
            "Leaves shouldContinue guards in place.",
        ],
        "scoringNotes": [
            "Passing while hiding failures is a severe QA integrity failure.",
        ],
    },
}

ULTRA_EVAL_TUNING = {
    "E4": {
        "expectedSignals": [
            "Detects WebDriverIO from package.json and wdio.conf.ts.",
            "Uses WDIO describe/it syntax with $() and $$() selectors.",
            "Places tags in title strings as expected by the project.",
        ],
        "antiPatterns": [
            "Generates Playwright code in a WDIO project.",
            "Uses Playwright-style metadata objects or { tags } format.",
            "Ignores wdio.conf.ts and framework conventions.",
        ],
        "scoringNotes": [
            "Framework adaptation is the core skill; correct behavior in the wrong framework should not score highly.",
        ],
    },
    "E5": {
        "expectedSignals": [
            "Uses Cypress command-chain style with cy.visit, cy.get, and cy.should.",
            "Creates a *.cy.ts file under cypress/e2e.",
            "Covers add/remove cart behavior.",
        ],
        "antiPatterns": [
            "Uses async/await control flow for Cypress commands.",
            "Uses Playwright page.locator or Playwright syntax.",
            "Places the spec outside Cypress conventions.",
        ],
        "scoringNotes": [
            "Reward Cypress-native syntax and file placement, not generic browser-test code.",
        ],
    },
    "E8": {
        "expectedSignals": [
            "Reads page objects before writing.",
            "Uses existing page object methods in the new test.",
            "Avoids Agent Browser before the first run because source context is sufficient.",
        ],
        "antiPatterns": [
            "Opens browser before using available page-object context.",
            "Writes raw locators that duplicate existing page-object methods.",
            "Over-explores despite complete source context.",
        ],
        "scoringNotes": [
            "This eval measures context selection; browser use is negative before source context is exhausted.",
        ],
    },
    "E14": {
        "expectedSignals": [
            "Reads the error and categorizes the issue as selector-related.",
            "Uses Agent Browser to inspect the selector failure.",
            "Stays within three attempts and produces a fix report.",
        ],
        "antiPatterns": [
            "Exceeds three attempts.",
            "Never opens browser for selector evidence.",
            "Weakens assertions instead of fixing selectors.",
        ],
        "scoringNotes": [
            "Bounded selector repair with runtime evidence is the desired workflow.",
        ],
    },
    "E15": {
        "expectedSignals": [
            "Runs the failing test first.",
            "Edits only the broken line with a targeted edit.",
            "Leaves passing tests and unrelated code untouched.",
        ],
        "antiPatterns": [
            "Rewrites the whole file.",
            "Changes passing tests.",
            "Uses test.skip or broad cleanup to avoid the failure.",
        ],
        "scoringNotes": [
            "Minimal targeted repair is the primary criterion.",
        ],
    },
    "E16": {
        "expectedSignals": [
            "Fixes failures one at a time.",
            "Runs the full suite after individual fixes pass.",
            "Reports X/Y passing or equivalent final suite status.",
        ],
        "antiPatterns": [
            "Never runs the full suite after fixes.",
            "Only validates individual tests and claims regression safety.",
        ],
        "scoringNotes": [
            "Final regression verification is mandatory after staged fixes.",
        ],
    },
    "E19": {
        "expectedSignals": [
            "Produces a risk assessment with high, medium, and low risk levels.",
            "Marks auth and checkout as high risk.",
            "Includes user journeys, test tags, and a Not Testing section.",
            "Does not create project files.",
        ],
        "antiPatterns": [
            "Assigns all areas the same risk.",
            "Omits Not Testing or risk justification.",
            "Creates files during a plan-only task.",
        ],
        "scoringNotes": [
            "Risk-based planning is judged on prioritization and explicit exclusions.",
        ],
    },
    "E21": {
        "expectedSignals": [
            "Navigates login, inventory, cart, checkout form, overview, and completion path.",
            "Adds assertions at each transition.",
            "Fills checkout details and verifies order completion.",
            "Uses proper tags.",
        ],
        "antiPatterns": [
            "Skips pages in the requested journey.",
            "Only asserts the final page.",
            "Introduces race conditions or fixed waits.",
        ],
        "scoringNotes": [
            "Complete E2E journey coverage requires transition-level assertions, not only final success.",
        ],
    },
    "E26": {
        "expectedSignals": [
            "Writes checkout and cart-removal tests.",
            "First verification command targets a single test/file or grep.",
            "Runs broader file/suite only after the individual target passes.",
        ],
        "antiPatterns": [
            "First run executes the full suite or multiple files.",
            "Skips the fast-feedback single-test step.",
        ],
        "scoringNotes": [
            "This eval measures verification strategy, not just final test content.",
        ],
    },
    "E29": {
        "expectedSignals": [
            "Fixes the broken selector.",
            "Adds required Playwright metadata tags to the previously untagged test.",
            "Uses feature, priority, and test_type tag dimensions.",
        ],
        "antiPatterns": [
            "Fixes the selector but leaves missing tags.",
            "Adds tags only in title text when metadata object is required.",
        ],
        "scoringNotes": [
            "Repair and metadata governance are both required for full credit.",
        ],
    },
    "E30": {
        "expectedSignals": [
            "Reads checkout tests, page objects, and app routes before planning.",
            "Produces a plan referencing concrete code-found pages/components.",
            "Avoids asking questions that the code answers.",
        ],
        "antiPatterns": [
            "Asks what pages or fields exist before reading code.",
            "Creates a generic checkout plan with no code references.",
        ],
        "scoringNotes": [
            "Plan mode can still require code-first context gathering.",
        ],
    },
    "E31": {
        "expectedSignals": [
            "Includes a Not Testing section with at least two exclusions.",
            "Justifies exclusions by risk, cost, or maintenance tradeoff.",
            "Avoids trying to test every possible thing.",
        ],
        "antiPatterns": [
            "No Not Testing section.",
            "Exclusions without justification.",
            "Plan has no prioritization or scope judgment.",
        ],
        "scoringNotes": [
            "Good QA planning includes explicit scope boundaries.",
        ],
    },
    "E32": {
        "expectedSignals": [
            "Plans user-journey tests for authentication.",
            "Keeps the test count compact.",
            "Names tests after user goals rather than individual UI elements.",
        ],
        "antiPatterns": [
            "Creates one test per form element.",
            "Proposes more than ten tests for a single auth page.",
            "Uses element-first naming and coverage.",
        ],
        "scoringNotes": [
            "Journey-first planning is the evaluated skill.",
        ],
    },
    "E36": {
        "expectedSignals": [
            "Traces count mismatch to broken add-to-cart selector in InventoryPage.ts.",
            "Fixes getAddToCartButton selector pattern.",
            "Preserves assertCartItemCount(1).",
        ],
        "antiPatterns": [
            "Changes expected count to zero.",
            "Skips cart tests.",
            "Removes or weakens count assertions.",
        ],
        "scoringNotes": [
            "Selector repair must preserve the cart-count assertion.",
        ],
    },
    "E77": {
        "expectedSignals": [
            "Reads the working snippet from SUPATEST.md.",
            "Integrates the snippet into a reusable helper or pattern.",
            "Removes or replaces failing code without leaving it commented out.",
            "Produces a passing test.",
        ],
        "antiPatterns": [
            "Ignores the provided snippet.",
            "Pastes the snippet inline without refactoring.",
            "Leaves old failing code in place.",
        ],
        "scoringNotes": [
            "The task rewards understanding and reusable integration of user-provided code.",
        ],
    },
    "E114": {
        "expectedSignals": [
            "Reads pages/LoginPage.ts and source/current data-test attributes.",
            "Fixes the page-object selector.",
            "Rejects stale README selector advice as unverified.",
        ],
        "antiPatterns": [
            "Uses README selector values as authoritative.",
            "Changes tests to match stale docs.",
            "Skips or weakens assertions.",
        ],
        "scoringNotes": [
            "Current source beats stale README guidance.",
        ],
    },
    "E115": {
        "expectedSignals": [
            "Uses page.setViewportSize for mobile and desktop dimensions.",
            "Logs in before checking responsive hamburger visibility.",
            "Asserts visible at mobile and hidden/not visible at desktop.",
        ],
        "antiPatterns": [
            "Tests only one viewport.",
            "Does not verify a visibility difference.",
            "Uses waitForTimeout for resize handling.",
        ],
        "scoringNotes": [
            "Responsive behavior must be proven across both requested viewport states.",
        ],
    },
    "E116": {
        "expectedSignals": [
            "Uses page.route or context.route scoped to inventory requests.",
            "Serves a mocked inventory page with exactly three products.",
            "Verifies exactly three products render while login still works.",
        ],
        "antiPatterns": [
            "Does not intercept network/page requests.",
            "Mocks so broadly that login breaks.",
            "Fails to assert product count.",
            "Uses interactive-only APIs.",
        ],
        "scoringNotes": [
            "Mocking is required here but must be scoped to the requested behavior.",
        ],
    },
    "E117": {
        "expectedSignals": [
            "Analyzes failure.log plus checkout test/page-object source.",
            "Identifies both total mismatch and confirmation text mismatch root causes.",
            "Produces a structured bug report with severity and affected tests.",
            "Does not edit files or run tests.",
        ],
        "antiPatterns": [
            "Addresses only one failure.",
            "Runs commands or edits files in report-only mode.",
            "Provides vague analysis without source/log evidence.",
        ],
        "scoringNotes": [
            "This is evidence-based reporting, not repair.",
        ],
    },
    "E118": {
        "expectedSignals": [
            "Removes waitForTimeout from InventoryPage.ts addProductToCart.",
            "Uses state-based waits such as waitForSelector or visibility assertions.",
            "Preserves toast assertions and verifies tests pass.",
        ],
        "antiPatterns": [
            "Increases timeout values.",
            "Keeps or adds waitForTimeout.",
            "Removes toast assertions or skips flaky tests.",
        ],
        "scoringNotes": [
            "The root cause is timing strategy; timeout inflation should not get repair credit.",
        ],
    },
    "E121": {
        "expectedSignals": [
            "Compares failure.log with current src/selectors.ts and tests/selectors.spec.ts.",
            "Identifies the supplied failure log as stale because current selectors already satisfy the assertions.",
            "Runs verify-fix.mjs or reports a concrete verification blocker.",
            "Avoids cosmetic diffs, config churn, dependency churn, or test rewrites.",
        ],
        "antiPatterns": [
            "Rewrites identical source just to create a write.",
            "Changes tests to match stale failure output.",
            "Adds runner config or dependencies unrelated to the stale evidence diagnosis.",
            "Claims the selectors were fixed without acknowledging they were already correct.",
        ],
        "scoringNotes": [
            "This eval rewards production judgment when logs are stale; a no-code-change answer can be correct when evidence and verification support it.",
        ],
    },
    "E122": {
        "expectedSignals": [
            "Fixes src/formatter.ts instead of modifying the verifier.",
            "Uses verify-fix.mjs or npm test as the narrow verification path.",
            "Does not create playwright.config.ts or other runner config.",
            "Leaves package.json and lockfiles unchanged unless a dependency is proven to be the root cause.",
        ],
        "antiPatterns": [
            "Creates Playwright config just to run a non-Playwright verifier.",
            "Edits verify-fix.mjs to accept broken output.",
            "Changes dependencies or lockfiles as a substitute for source repair.",
            "Reports success without fixing both currency and percent formatting.",
        ],
        "scoringNotes": [
            "The trap is verification setup overreach; credit the narrow source fix plus narrow verifier.",
        ],
    },
    "E123": {
        "expectedSignals": [
            "Adds native Playwright metadata object form to every existing checkout test().",
            "Includes @feature:checkout, @priority:<level>, and @test_type:<type> for each touched test.",
            "Preserves existing page-object calls, scenarios, and assertions.",
            "Does not add new scenarios or put required tags only in titles.",
        ],
        "antiPatterns": [
            "Uses title-only tags or misses a required metadata dimension.",
            "Rewrites CheckoutPage.ts or changes checkout flow behavior.",
            "Adds extra tests instead of annotating the existing tests.",
            "Weakens assertions while doing metadata work.",
        ],
        "scoringNotes": [
            "Metadata governance is the task; broad flow rewrites or title-only tagging should be penalized even if tests still look plausible.",
        ],
    },
}

MAX_EVAL_TUNING = {
    "E70": {
        "expectedSignals": [
            "Uses Maestro inspect_view_hierarchy or inspect_screen within the first two tool calls.",
            "Takes at least one screenshot.",
            "Reports five UI elements with at least three accessibility identifiers.",
        ],
        "antiPatterns": [
            "Uses adb, xcrun, or Appium through Bash for inspection.",
            "Gives up without listing devices when device availability is unclear.",
            "Writes Maestro YAML for an exploration-only task.",
        ],
        "scoringNotes": [
            "Max mobile exploration requires the right device-inspection tool path first.",
        ],
    },
    "E71": {
        "expectedSignals": [
            "Reads current-ios-settings-hierarchy.csv.",
            "Returns exactly one Appium-ready selector for the General row.",
            "Prefers resource-id or accessibility label over XPath.",
            "Explains selector stability in one sentence.",
        ],
        "antiPatterns": [
            "Uses legacy XPath as primary selector.",
            "Skips the current hierarchy file.",
            "Creates files or returns multiple alternatives.",
        ],
        "scoringNotes": [
            "Selector-only mobile requests should stay concise and hierarchy-grounded.",
        ],
    },
    "E72": {
        "expectedSignals": [
            "Reads current-catalog-hierarchy.json.",
            "Returns five distinct selectors for the requested catalog elements.",
            "Uses real resource-ids and maps each to evidence rows.",
        ],
        "antiPatterns": [
            "Guesses generic selectors.",
            "Uses class-name/XPath when resource-id exists.",
            "Copies stale adb quick selectors.",
            "Creates files or test code.",
        ],
        "scoringNotes": [
            "Element-discovery coverage and evidence mapping are both required.",
        ],
    },
    "E73": {
        "expectedSignals": [
            "Inspects hierarchy at multiple login-flow steps.",
            "Identifies menu-to-login navigation, fields, and login button.",
            "Reports what changed on screen after each action.",
        ],
        "antiPatterns": [
            "Inspects once and narrates the rest from memory.",
            "Uses screenshots only without hierarchy evidence.",
            "Fabricates selectors for uninspected screens.",
        ],
        "scoringNotes": [
            "Multi-step mobile walkthroughs need repeated device-state evidence.",
        ],
    },
    "E74": {
        "expectedSignals": [
            "Inspects hierarchy on multiple screens before authoring.",
            "Writes a WDIO/Appium TypeScript test with real resource-ids.",
            "Uses WDIO accessibility-id/resource-id selector syntax.",
            "Implements login, catalog, product, add-to-cart, cart, and item-count assertion flow.",
        ],
        "antiPatterns": [
            "Fabricates selectors.",
            "Generates Maestro YAML instead of WDIO test code.",
            "Writes from training-data assumptions without live inspection.",
        ],
        "scoringNotes": [
            "Real mobile test authoring must be grounded in current live hierarchy.",
        ],
    },
    "E81": {
        "expectedSignals": [
            "Explains native-to-WebView context boundary.",
            "Recommends Appium getContexts and switchContext.",
            "Distinguishes native selectors from web DOM selectors.",
            "Mentions switching back to native context.",
        ],
        "antiPatterns": [
            "Claims Maestro hierarchy inspection reads WebView DOM.",
            "Recommends Maestro YAML instead of Appium context switching.",
            "Repeats incorrect team notes.",
            "Creates files for an explanation-only request.",
        ],
        "scoringNotes": [
            "This is conceptual mobile QA guidance; no artifact creation is needed.",
        ],
    },
    "E82": {
        "expectedSignals": [
            "Inspects live device state before hypothesizing.",
            "Identifies the cart-count element and current value/state.",
            "Separates possible causes based on observed device state.",
        ],
        "antiPatterns": [
            "Hypothesizes before inspection.",
            "Asks the user to debug first.",
            "Jumps to adb logcat instead of Maestro inspection.",
        ],
        "scoringNotes": [
            "Device state must precede diagnosis.",
        ],
    },
    "E83": {
        "expectedSignals": [
            "Inspects live device state before rerun, code change, or selector edit.",
            "Finds the actual Add-to-cart selector or unexpected screen state.",
            "Bases recommendation on live hierarchy.",
        ],
        "antiPatterns": [
            "Suggests rerunning first.",
            "Edits files before inspection.",
            "Greps logs or reruns repeatedly before any Maestro call.",
            "Suggests sleeps as primary fix.",
        ],
        "scoringNotes": [
            "This eval targets no-yak-shave mobile debugging.",
        ],
    },
    "E101": {
        "expectedSignals": [
            "Reads lumpsum-inspect-snippet.json before editing.",
            "Uses ~mfAddStock or label predicate without invented XCUIElementType.",
            "Disambiguates the first of four duplicate mfAddStock elements by index.",
            "Rejects legacy type-inferred fabricated data.",
        ],
        "antiPatterns": [
            "Invents XCUIElementTypeButton.",
            "Uses a single undisambiguated $('~mfAddStock').",
            "Hardcodes fund/session-specific values.",
            "Runs install/wdio/tsc instead of editing the page object.",
        ],
        "scoringNotes": [
            "Maestro-to-WDIO translation must preserve duplicate-index semantics and avoid fabricated type data.",
        ],
    },
    "E102": {
        "expectedSignals": [
            "Reads wdio-success-log.txt.",
            "Sets didRun to yes from the final Spec Files summary.",
            "Reports 1 passed and 0 failed from the current log.",
            "Copies the exact Spec Files line into sourceLine.",
        ],
        "antiPatterns": [
            "Uses stale-run-output.log or WARN lines as final status.",
            "Uses grep/tail/bash instead of direct log analysis.",
            "Claims the test did not run despite final summary.",
        ],
        "scoringNotes": [
            "Noisy WDIO logs require final-summary interpretation, not grep heuristics.",
        ],
    },
    "E103": {
        "expectedSignals": [
            "Reads ios-login-inspect-snippet.json.",
            "Uses ~SignInButton or equivalent current iOS accessibility selector.",
            "Preserves async tapLogin with waitForDisplayed and click.",
            "Leaves Android page object unchanged.",
        ],
        "antiPatterns": [
            "Copies Android resource-id into iOS.",
            "Uses legacy btn_login or alternate LoginButton instead of current hierarchy.",
            "Guesses without current iOS reference.",
            "Adds unrelated methods or changes Android code.",
        ],
        "scoringNotes": [
            "Cross-platform porting requires current platform hierarchy, not Android copy-paste.",
        ],
    },
    "E104": {
        "expectedSignals": [
            "Writes a one-line npx wdio command to run-command.txt.",
            "Uses --spec targeting test/specs/cart.spec.ts only.",
            "Includes --workers=1.",
        ],
        "antiPatterns": [
            "Runs the command instead of authoring it.",
            "Uses full-suite glob or no --spec.",
            "Includes checkout.spec.ts.",
        ],
        "scoringNotes": [
            "Command authoring must respect narrow run scope and no-execute instruction.",
        ],
    },
    "E105": {
        "expectedSignals": [
            "Names ~UploadButton as the wrong selector in completeDocumentUpload.",
            "Cites SubmitUpload from inspect-upload-screen.json as current selector.",
            "Rejects legacy selector map and unrelated payment screen evidence.",
            "Avoids timing/navigation hypotheses unsupported by hierarchy.",
        ],
        "antiPatterns": [
            "Provides vague root cause without hierarchy evidence.",
            "Uses legacy UploadButton or payment-screen evidence.",
            "Starts grep/rerun debug spiral.",
            "Fails to name the bad method.",
        ],
        "scoringNotes": [
            "Production regression diagnosis must identify method, bad selector, and current hierarchy evidence.",
        ],
    },
    "E106": {
        "expectedSignals": [
            "Writes exactly three numbered debug steps.",
            "Step 1 is Maestro device inspection.",
            "Mentions at most one test rerun after inspection.",
        ],
        "antiPatterns": [
            "Writes more than three steps.",
            "Starts with grep, tail, or rerun.",
            "Includes multiple rerun or bash log-scraping steps.",
        ],
        "scoringNotes": [
            "Efficient debug planning is scored by sequence discipline and brevity.",
        ],
    },
    "E107": {
        "expectedSignals": [
            "Keeps fillShipping, submitOrder, verifyConfirmation, and completeDocumentUpload present.",
            "Changes only completeDocumentUpload to use ~SubmitUpload from production hierarchy.",
            "Preserves working method bodies and trackOrderSubmission import.",
        ],
        "antiPatterns": [
            "Rewrites or removes working methods.",
            "Uses legacy, checkout-screen, or beta selectors.",
            "Leaves ~UploadButton.",
            "Adds retries, sleeps, try/catch, or unrelated abstractions.",
        ],
        "scoringNotes": [
            "Non-destructive repair is the target; collateral changes should be penalized heavily.",
        ],
    },
    "E108": {
        "expectedSignals": [
            "Uses a single scoped WDIO command with --spec for the named mobile spec.",
            "Reports pass/fail only from Spec Files summary.",
            "Keeps strategy to four or fewer numbered steps.",
            "Does not propose code fixes or retry loops.",
        ],
        "antiPatterns": [
            "Multiple reruns or retry-until-pass loops.",
            "Uses grep/tail/log scraping.",
            "Copies archived troubleshooting or quick-retry patterns.",
            "Runs full suite instead of the named spec.",
        ],
        "scoringNotes": [
            "This eval checks whether the agent avoids slow debug spirals.",
        ],
    },
    "E109": {
        "expectedSignals": [
            "Plans list_devices first.",
            "Selects emulator-5554 specifically.",
            "Plans inspect on emulator-5554 and not 5556.",
        ],
        "antiPatterns": [
            "Skips list_devices.",
            "Uses adb devices.",
            "Targets emulator-5556 or ambiguous device.",
        ],
        "scoringNotes": [
            "Named device targeting is mandatory when multiple emulators exist.",
        ],
    },
    "E113": {
        "expectedSignals": [
            "Writes next steps with device inspection first.",
            "Proposes fixing one failing spec.",
            "Proposes one targeted --spec rerun.",
            "Avoids running commands in authoring-only mode.",
        ],
        "antiPatterns": [
            "Reruns full suite glob first.",
            "Skips device inspection.",
            "Includes multiple full-suite reruns.",
        ],
        "scoringNotes": [
            "Production suite failures should narrow by state inspection and single-spec verification.",
        ],
    },
    "E119": {
        "expectedSignals": [
            "Covers Android and iOS strategy.",
            "Addresses selector differences, WebView context switching, permissions, and keyboard handling.",
            "Stays in plan mode without tests, commands, or device inspection.",
        ],
        "antiPatterns": [
            "Covers only one platform.",
            "Writes WDIO/Appium test code.",
            "Ignores WebView context switching.",
            "Runs Maestro or shell commands.",
        ],
        "scoringNotes": [
            "This max plan task is written strategy only, not implementation or inspection.",
        ],
    },
    "E120": {
        "expectedSignals": [
            "Uses Maestro inspect_view_hierarchy or inspect_screen to discover selectors.",
            "Navigates menu to Drawing screen.",
            "Addresses Android system camera permission handling.",
            "Provides Appium/WDIO selectors based on live device evidence.",
        ],
        "antiPatterns": [
            "Does not inspect the device.",
            "Skips permission dialog handling.",
            "Fabricates selectors.",
            "Writes Maestro YAML instead of Appium/WDIO guidance/code.",
        ],
        "scoringNotes": [
            "System permission flows require live selector evidence and platform-specific handling.",
        ],
    },
}

EVAL_TUNING = {
    **LOW_EVAL_TUNING,
    **MEDIUM_EVAL_TUNING,
    **HIGH_EVAL_TUNING,
    **ULTRA_EVAL_TUNING,
    **MAX_EVAL_TUNING,
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
    eval_tuning = EVAL_TUNING.get(str(eval_id or "")) or {}
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
