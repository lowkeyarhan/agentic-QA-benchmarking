# maestro-ios-blank

Minimal mobile fixture base template for SUP-25 (device-state feedback) evals.

## What's here

- `.maestro/` — mobile-project marker (triggers SUP-25 mobile detection in the CLI)
- `.supatest/mcp.json` — Maestro MCP wired so `mcp__maestro__*` tools are available

## Prerequisites for running evals built from this template

1. **macOS** with Xcode and an iOS Simulator booted (`xcrun simctl boot ...`)
2. **Maestro CLI** installed at `~/.maestro/bin/maestro` (`supatest setup mobile` will install it)
3. **iPhone simulator with an app in the foreground** — the eval task decides which app

These evals are **macOS-only** because they exercise a live iOS simulator. They
are skipped in CI environments that don't have a booted sim, and there is no
fallback / mocked Maestro path yet. Android validation requires `adb` and a
running emulator and is not covered by this template.

## Why blank

Mobile evals validate **agent behavior under failure** — does the agent reach
for Maestro tools (`mcp__maestro__inspect_view_hierarchy`,
`mcp__maestro__take_screenshot`) instead of shelling out to `adb` / `xcrun`?
The fixture deliberately ships no test framework so the agent can't fall back
to web-style assertions; it has to interrogate the device.
