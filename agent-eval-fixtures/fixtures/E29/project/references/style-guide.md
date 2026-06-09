# Test Tagging Conventions

## Overview

Tests in this project use inline tag strings in test names to enable Playwright's `--grep` filtering.

**Current convention (pre-v2):** Tags in test title strings:
```
test('@auth @smoke @test_type:regression Valid user can login successfully', ...)
```

**New convention (v2, preferred):** Playwright's native tag property:
```
test('Valid user can login successfully', { tag: ['@feature:auth', '@priority:high', '@test_type:smoke'] }, ...)
```

**Important:** When adding tags to a test that currently has them in the title, prefer the native `{ tag: [...] }` property format. Do NOT just prepend tags back to the title string — this does not register them for `--grep` filtering.

## Reference

Existing tests already migrated to native tag property:
- `cart.spec.ts` — uses `{ tag: ['@feature:cart', ...] }`
