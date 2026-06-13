from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class PreflightIssue:
    kind: str
    platform: str
    reason: str


def preflight_fixture(
    fixture, device_cache: dict[str, PreflightIssue | None]
) -> PreflightIssue | None:
    platform = required_live_device_platform(fixture)
    if not platform:
        return None

    if platform not in device_cache:
        device_cache[platform] = preflight_maestro_device(platform)
    return device_cache[platform]


def required_live_device_platform(fixture) -> str | None:
    text = "\n".join(
        [
            fixture.task,
            "\n".join(fixture.pass_criteria),
            "\n".join(fixture.fail_criteria),
        ]
    ).lower()

    if "authoring only" in text or "do not inspect a live device" in text:
        return None

    requires_actual_inspection = (
        "calls mcp__maestro__inspect_view_hierarchy" in text
        or "calls mcp__maestro__inspect_screen" in text
        or "inspect the live device" in text
    )
    if not requires_actual_inspection:
        return None

    if "android" in text or "emulator" in text:
        return "android"
    if "ios" in text or "simulator" in text:
        return "ios"
    return None


def preflight_maestro_device(platform: str) -> PreflightIssue | None:
    maestro = shutil.which("maestro")
    local_maestro = os.path.expanduser("~/.maestro/bin/maestro")
    if not maestro and os.path.exists(local_maestro):
        maestro = local_maestro
    if not maestro:
        return PreflightIssue(
            kind="missing-maestro",
            platform=platform,
            reason="Maestro CLI was not found on PATH or at ~/.maestro/bin/maestro.",
        )

    try:
        completed = subprocess.run(
            [maestro, "--no-ansi", "list-devices", "--platform", platform],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            env={**os.environ, "MAESTRO_CLI_NO_ANALYTICS": "true"},
        )
    except subprocess.TimeoutExpired:
        return PreflightIssue(
            kind="maestro-timeout",
            platform=platform,
            reason=f"Timed out while listing {platform} devices with Maestro.",
        )
    except OSError as error:
        return PreflightIssue(
            kind="maestro-error",
            platform=platform,
            reason=f"Failed to list {platform} devices with Maestro: {error}",
        )

    output = completed.stdout or ""
    if completed.returncode != 0:
        return PreflightIssue(
            kind="maestro-error",
            platform=platform,
            reason=(
                f"Maestro list-devices --platform {platform} exited "
                f"{completed.returncode}: {compact_output(output)}"
            ),
        )
    if not maestro_output_has_devices(output, platform):
        return PreflightIssue(
            kind="missing-device",
            platform=platform,
            reason=f"No local {platform} device is visible to Maestro.",
        )
    return None


def maestro_output_has_devices(output: str, platform: str) -> bool:
    platform_headings = {"android", "ios", "web"}
    for raw_line in output.splitlines():
        if not raw_line.startswith("  "):
            continue
        stripped = raw_line.strip()
        if not stripped or stripped.lower() in platform_headings:
            continue
        if stripped.lower() == "no devices found":
            return False
        return True
    return False


def compact_output(output: str, max_chars: int = 500) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    text = " ".join(lines)
    return text[:max_chars] if text else "no output"
