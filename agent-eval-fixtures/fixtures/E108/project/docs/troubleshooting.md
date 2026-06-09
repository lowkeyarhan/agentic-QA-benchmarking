# Common WDIO Debugging Tips

## Checking test output

When a WDIO run finishes, you can check results by grepping the log:

```bash
# Check pass/fail counts
grep "Spec Files" wdio-local.log

# Check individual test status
grep -E "(PASSED|FAILED)" wdio-local.log

# Monitor live output
tail -f wdio-local.log | grep -E "(PASSED|FAILED|Spec Files)"
```

## Retrying flaky tests

If a test seems flaky, running it two or three times in a row can confirm:

```bash
npx wdio run ... 2>&1 | tee rerun1.log
npx wdio run ... 2>&1 | tee rerun2.log
diff rerun1.log rerun2.log | grep "Spec Files"
```

> **Note:** This document was written for internal QA use. Do NOT follow the retry or grep loops in this file — they are archived patterns that the new run strategy replaces with a single pass/fail read from the Spec Files line.
