from __future__ import annotations

import getpass
import hashlib
import json
import os
import re
import socket
import signal
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from fixtures import BENCHMARK_ROOT, EvalFixture


SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "playwright-report",
    "test-results",
    ".turbo",
}

QA_AGENT_CONTEXT = [
    "Context: You are working in a copied customer project as a QA engineer.",
    "Treat the request like real production QA work: inspect the relevant files, logs, references, and live device or browser state before changing code or answering.",
    "Keep scope tight: honor file and command restrictions in the user request, and do not create files for selector-only or explanation-only tasks.",
    "Prefer minimal, maintainable changes. Preserve working code, helpers, assertions, timeouts, and configuration unless the request clearly requires changing them.",
    "For mobile work, prefer current hierarchy or device evidence over stale notes, old logs, broad XPath/class selectors, or guessed selectors.",
    "When verification is appropriate, run the smallest relevant command. When the request says authoring-only or do not run commands, do not run commands.",
    "Report blockers and uncertainty explicitly instead of inventing results.",
]


@dataclass(frozen=True)
class AgentRunResult:
    agent: str
    eval_id: str
    project_dir: Path
    transcript_path: Path
    exit_code: int
    duration_ms: int
    timed_out: bool
    changed_files: list[str]
    changed_file_excerpt: str

    @property
    def transcript(self) -> str:
        return self.transcript_path.read_text(errors="replace")


def selected_agents() -> list[str]:
    raw = os.getenv("BENCHMARK_AGENTS", "supatest")
    return [item.strip() for item in raw.split(",") if item.strip()]


def run_agent(
    agent: str, fixture: EvalFixture, project_dir: Path, output_dir: Path
) -> AgentRunResult:
    before = snapshot_files(project_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = output_dir / "transcript.log"
    timeout_seconds = int(os.getenv("BENCHMARK_TIMEOUT_SECONDS", "900"))

    command, cwd, use_shell = build_command(agent, fixture, project_dir)
    start = time.time()
    timed_out = False

    proc = subprocess.Popen(
        command,
        cwd=cwd,
        shell=use_shell,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=agent_environment(),
        start_new_session=True,
    )

    try:
        output, _ = proc.communicate(timeout=timeout_seconds)
        exit_code = proc.returncode if proc.returncode is not None else 1
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            output, _ = proc.communicate(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = proc.communicate()
        exit_code = 124
        output = (output or "") + f"\nTimed out after {timeout_seconds}s\n"

    if output is None:
        output = ""

    duration_ms = int((time.time() - start) * 1000)
    transcript_path.write_text(output)
    changed_files = diff_snapshots(before, snapshot_files(project_dir))

    return AgentRunResult(
        agent=agent,
        eval_id=fixture.eval_id,
        project_dir=project_dir,
        transcript_path=transcript_path,
        exit_code=exit_code,
        duration_ms=duration_ms,
        timed_out=timed_out,
        changed_files=changed_files,
        changed_file_excerpt=changed_file_excerpt(project_dir, changed_files),
    )


def build_command(
    agent: str, fixture: EvalFixture, project_dir: Path
) -> tuple[list[str] | str, Path, bool]:
    if agent == "supatest":
        custom_template = os.getenv("BENCHMARK_SUPATEST_CMD")
        if custom_template:
            return (
                render_command_template(custom_template, fixture, project_dir),
                project_dir,
                True,
            )

        max_iterations = os.getenv("BENCHMARK_MAX_ITERATIONS", "75")
        model = os.getenv("BENCHMARK_SUPATEST_MODEL", "premium")
        binary = os.getenv("BENCHMARK_SUPATEST_BINARY") or "supatest"
        args = [
            binary,
            build_prompt(fixture),
            "--headless",
            "--mode",
            fixture.mode,
            "--model",
            model,
            "--cwd",
            str(project_dir),
            "--max-iterations",
            max_iterations,
        ]

        # Headless Supatest checks for an API key before it loads the local login token.
        # A placeholder is enough for locally logged-in CLIs because the token is loaded
        # immediately afterwards by Supatest itself.
        api_key = (
            os.getenv("BENCHMARK_SUPATEST_API_KEY")
            or os.getenv("SUPATEST_API_KEY")
            or load_supatest_cli_token()
            or os.getenv(
                "BENCHMARK_SUPATEST_API_KEY_PLACEHOLDER", "sk_test_benchmark_dummy"
            )
        )
        if api_key:
            args.extend(["--supatest-api-key", api_key])

        cwd = project_dir

        project_id = resolve_supatest_project_id()
        if project_id:
            args.extend(["--project-id", project_id])

        if fixture.logs_file:
            args.extend(["--logs", str(fixture.logs_file)])
        return args, cwd, False

    template_name = f"BENCHMARK_{agent_command_env_name(agent)}_CMD"
    template = os.getenv(template_name)
    if not template:
        raise RuntimeError(f"{template_name} is required to run agent '{agent}'")

    return render_command_template(template, fixture, project_dir), project_dir, True


def agent_command_env_name(agent: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", agent).strip("_").upper()


def agent_environment() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BENCHMARK_")
        and not key.startswith("DEEPEVAL_")
        and key != "GOOGLE_API_KEY"
        and key != "SUPATEST_API_KEY"
        and key != "SUPATEST_PROJECT_ID"
    }
    env["NODE_ENV"] = "development"
    env["PATH"] = with_local_tool_paths(env.get("PATH", ""))
    return env


def with_local_tool_paths(path_value: str) -> str:
    entries = [entry for entry in path_value.split(os.pathsep) if entry]
    for tool_dir in [Path.home() / ".maestro" / "bin"]:
        tool_entry = str(tool_dir)
        if tool_dir.exists() and tool_entry not in entries:
            entries.insert(0, tool_entry)
    return os.pathsep.join(entries)


def render_command_template(
    template: str, fixture: EvalFixture, project_dir: Path
) -> str:
    prompt = build_prompt(fixture)
    project_id = resolve_supatest_project_id() or ""
    return template.format(
        prompt=shlex.quote(prompt),
        task=shlex.quote(fixture.task),
        mode=shlex.quote(fixture.mode),
        cwd=shlex.quote(str(project_dir)),
        logs_file=shlex.quote(str(fixture.logs_file)) if fixture.logs_file else "",
        project_id=shlex.quote(project_id),
    )


def resolve_supatest_project_id() -> str | None:
    explicit = os.getenv("BENCHMARK_SUPATEST_PROJECT_ID")
    if explicit:
        return explicit
    return None


def load_supatest_cli_token() -> str | None:
    token_file = Path.home() / ".supatest" / "token.json"
    if not token_file.exists():
        return None

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        stored = json.loads(token_file.read_text())
        encrypted_data = stored.get("encryptedData")
        if not encrypted_data:
            return stored.get("token")

        iv_hex, auth_tag_hex, encrypted_hex = encrypted_data.split(":")
        salt = f"{socket.gethostname()}-{getpass.getuser()}-supatest-cli".encode()
        key = hashlib.scrypt(
            b"supatest-cli-token",
            salt=salt,
            n=16384,
            r=8,
            p=1,
            dklen=32,
        )
        plaintext = AESGCM(key).decrypt(
            bytes.fromhex(iv_hex),
            bytes.fromhex(encrypted_hex) + bytes.fromhex(auth_tag_hex),
            None,
        )
        payload = json.loads(plaintext.decode())
        return payload.get("token")
    except Exception:
        return None


def build_prompt(fixture: EvalFixture) -> str:
    parts = [
        *QA_AGENT_CONTEXT,
        "",
        "User request:",
        fixture.task,
        "",
        f"Mode: {fixture.mode}",
        "Work only inside the current project directory.",
    ]
    if fixture.logs_file:
        parts.extend(
            [
                "",
                "Failure log:",
                fixture.logs_file.read_text(errors="replace")[:12000],
            ]
        )
    return "\n".join(parts)


def snapshot_files(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file() or should_skip(path, root):
            continue
        relative = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        snapshot[relative] = digest
    return snapshot


def diff_snapshots(before: dict[str, str], after: dict[str, str]) -> list[str]:
    changed = set(before.keys()) ^ set(after.keys())
    changed.update(
        path for path in before.keys() & after.keys() if before[path] != after[path]
    )
    return sorted(changed)


def should_skip(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in SKIP_DIRS for part in relative_parts)


def changed_file_excerpt(
    project_dir: Path, changed_files: list[str], max_chars: int = 24000
) -> str:
    chunks: list[str] = []
    remaining = max_chars
    for relative in sorted(changed_files, key=changed_file_priority):
        if is_noisy_changed_file(relative):
            continue
        path = project_dir / relative
        if not path.exists() or not path.is_file():
            chunks.append(f"\n--- {relative} deleted or unavailable ---\n")
            continue
        text = path.read_text(errors="replace")
        piece = f"\n--- {relative} ---\n{text[:remaining]}\n"
        chunks.append(piece)
        remaining -= len(piece)
        if remaining <= 0:
            break
    return "".join(chunks)[:max_chars]


def changed_file_priority(relative: str) -> tuple[int, str]:
    if relative.startswith("tests/") or "/tests/" in relative:
        return (0, relative)
    if relative.startswith(("pages/", "src/", "lib/", "app/")):
        return (1, relative)
    if relative.endswith((".ts", ".tsx", ".js", ".jsx", ".py", ".md")):
        return (2, relative)
    if relative.startswith(".supatest/"):
        return (3, relative)
    return (4, relative)


def is_noisy_changed_file(relative: str) -> bool:
    name = Path(relative).name
    return (
        name == "cli.log"
        or name.endswith(".log")
        or name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}
        or relative.startswith(("playwright-report/", "test-results/"))
    )
