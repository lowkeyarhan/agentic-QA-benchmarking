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
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from fixtures import BENCHMARK_ROOT, EvalFixture
from qa_bench import difficulty_for_tier


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

DEFAULT_AGENT_MODELS = {
    "cursor": "auto",
    "gemini": "gemini-3.1-flash-lite",
    "supatest": "premium",
}

DEFAULT_AGENT_COMMANDS = {
    "cursor": (
        "cursor-agent --print --force --output-format stream-json "
        "--model {model} {prompt}"
    ),
    "codex": (
        "codex exec -C {cwd} --skip-git-repo-check "
        "--dangerously-bypass-approvals-and-sandbox {model_arg} {prompt}"
    ),
    "gemini": (
        "gemini --model {model} --prompt {prompt} --yolo --skip-trust "
        "--output-format stream-json"
    ),
}

PROMPT_PROFILES = {"qa", "minimal", "raw"}
DEFAULT_HIDDEN_HOST_TOOLS = "rtk"
DEFAULT_MAX_ITERATIONS_BY_DIFFICULTY = {
    "unknown": 75,
    "low": 75,
    "medium": 95,
    "high": 120,
    "ultra": 150,
    "max": 180,
}


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
    stdin_input = agent_stdin_input(agent, fixture)
    start = time.monotonic()
    timed_out = False

    proc = subprocess.Popen(
        command,
        cwd=cwd,
        shell=use_shell,
        text=True,
        stdin=subprocess.PIPE if stdin_input is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=agent_environment(agent),
        start_new_session=True,
    )

    try:
        output, _ = proc.communicate(input=stdin_input, timeout=timeout_seconds)
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

    duration_ms = int((time.monotonic() - start) * 1000)
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
    family = agent_family(agent)
    if family == "supatest":
        custom_template = os.getenv("BENCHMARK_SUPATEST_CMD")
        if custom_template:
            return (
                render_command_template(custom_template, fixture, project_dir, agent),
                project_dir,
                True,
            )

        max_iterations = str(max_iterations_for_fixture(fixture))
        model = agent_model(agent) or DEFAULT_AGENT_MODELS["supatest"]
        binary = os.getenv("BENCHMARK_SUPATEST_BINARY") or "supatest"
        if supatest_machine_mode_enabled():
            args = [
                binary,
                "--output-format",
                "stream-json",
                "--input-format",
                "stream-json",
                "--mode",
                fixture.mode,
                "--model",
                model,
                "--cwd",
                str(project_dir),
                "--max-iterations",
                max_iterations,
            ]
        else:
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

        api_key = os.getenv("BENCHMARK_SUPATEST_API_KEY") or os.getenv(
            "SUPATEST_API_KEY"
        )
        if api_key:
            args.extend(["--supatest-api-key", api_key])

        cwd = project_dir

        project_id = resolve_supatest_project_id()
        if not project_id:
            raise RuntimeError(
                "Supatest runs require BENCHMARK_SUPATEST_PROJECT_ID or "
                "benchmark/.supatest/settings.json projectId."
            )
        args.extend(["--project-id", project_id])

        if fixture.logs_file:
            args.extend(["--logs", str(fixture.logs_file)])
        return args, cwd, False

    template_name, template = agent_command_template(agent)
    if not template:
        raise RuntimeError(f"{template_name} is required to run agent '{agent}'")

    return (
        render_command_template(template, fixture, project_dir, agent),
        project_dir,
        True,
    )


def agent_stdin_input(agent: str, fixture: EvalFixture) -> str | None:
    if (
        agent_family(agent) == "supatest"
        and not os.getenv("BENCHMARK_SUPATEST_CMD")
        and supatest_machine_mode_enabled()
    ):
        return (
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": build_prompt(fixture)},
                        ],
                    },
                }
            )
            + "\n"
        )
    return None


def supatest_machine_mode_enabled() -> bool:
    raw = os.getenv("BENCHMARK_SUPATEST_MACHINE_MODE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def fixture_difficulty(fixture: EvalFixture) -> str:
    raw_qa_bench = getattr(fixture, "qa_bench", None)
    qa_bench = raw_qa_bench if isinstance(raw_qa_bench, dict) else {}
    difficulty = str(
        qa_bench.get("difficulty")
        or difficulty_for_tier(getattr(fixture, "tier", None))
    )
    return difficulty if difficulty in DEFAULT_MAX_ITERATIONS_BY_DIFFICULTY else "unknown"


def parse_positive_int(raw: str, name: str) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be a positive integer.") from error
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def max_iterations_policy_mode() -> str:
    raw = os.getenv("BENCHMARK_MAX_ITERATIONS_POLICY", "difficulty").strip().lower()
    if raw in {"difficulty", "difficulty-based", "by-difficulty"}:
        return "difficulty"
    if raw in {"static", "fixed", "global"}:
        return "static"
    raise ValueError(
        "BENCHMARK_MAX_ITERATIONS_POLICY must be 'difficulty' or 'static'."
    )


def max_iterations_for_fixture(fixture: EvalFixture) -> int:
    difficulty = fixture_difficulty(fixture)
    difficulty_env_name = f"BENCHMARK_MAX_ITERATIONS_{difficulty.upper()}"
    difficulty_override = os.getenv(difficulty_env_name)
    if difficulty_override:
        return parse_positive_int(difficulty_override, difficulty_env_name)

    global_override = (
        os.getenv("BENCHMARK_MAX_ITERATIONS")
        if max_iterations_policy_mode() == "static"
        else None
    )
    if global_override:
        return parse_positive_int(global_override, "BENCHMARK_MAX_ITERATIONS")

    return DEFAULT_MAX_ITERATIONS_BY_DIFFICULTY[difficulty]


def max_iterations_policy_metadata() -> dict[str, object]:
    overrides = {
        difficulty: os.getenv(f"BENCHMARK_MAX_ITERATIONS_{difficulty.upper()}")
        for difficulty in DEFAULT_MAX_ITERATIONS_BY_DIFFICULTY
        if os.getenv(f"BENCHMARK_MAX_ITERATIONS_{difficulty.upper()}")
    }
    return {
        "policy": "static" if max_iterations_policy_mode() == "static" else "difficulty-based",
        "byDifficulty": DEFAULT_MAX_ITERATIONS_BY_DIFFICULTY,
        "staticOverride": os.getenv("BENCHMARK_MAX_ITERATIONS")
        if max_iterations_policy_mode() == "static"
        else None,
        "difficultyOverrides": overrides,
    }


def agent_family(agent: str) -> str:
    return agent.split(":", 1)[0].strip()


def agent_inline_model(agent: str) -> str | None:
    if ":" not in agent:
        return None
    model = agent.split(":", 1)[1].strip()
    return model or None


def agent_run_dir_name(agent: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", agent).strip("-") or "agent"


def agent_command_env_name(agent: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", agent).strip("_").upper()


def agent_model(agent: str) -> str | None:
    id_env_name = agent_command_env_name(agent)
    explicit = os.getenv(f"BENCHMARK_{id_env_name}_MODEL")
    if explicit:
        return explicit.strip()

    inline_model = agent_inline_model(agent)
    if inline_model:
        return inline_model

    family = agent_family(agent)
    family_env_name = agent_command_env_name(family)
    explicit = os.getenv(f"BENCHMARK_{family_env_name}_MODEL")
    return explicit.strip() if explicit else None


def agent_model_label(agent: str) -> str:
    env_names = [agent_command_env_name(agent)]
    family = agent_family(agent)
    family_env_name = agent_command_env_name(family)
    if family_env_name not in env_names:
        env_names.append(family_env_name)

    for env_name in env_names:
        explicit = os.getenv(f"BENCHMARK_{env_name}_MODEL_LABEL")
        if explicit:
            return explicit

    configured_model = agent_model(agent)
    if configured_model:
        return configured_model

    if family == "supatest":
        return DEFAULT_AGENT_MODELS["supatest"]

    _, template = agent_command_template(agent)
    return model_from_command_template(template) or "default"


def agent_display_name(agent: str) -> str:
    return f"{agent_family(agent)} [{agent_model_label(agent)}]"


def agent_command_template(agent: str) -> tuple[str, str | None]:
    env_names = [agent_command_env_name(agent)]
    family = agent_family(agent)
    family_env_name = agent_command_env_name(family)
    if family_env_name not in env_names:
        env_names.append(family_env_name)

    for env_name in env_names:
        template_name = f"BENCHMARK_{env_name}_CMD"
        template = os.getenv(template_name)
        if template:
            return template_name, template

    template = DEFAULT_AGENT_COMMANDS.get(family)
    if template:
        return f"built-in {family} command", template

    return f"BENCHMARK_{family_env_name}_CMD", None


def model_from_command_template(template: str | None) -> str | None:
    if not template:
        return None
    try:
        parts = shlex.split(template)
    except ValueError:
        return None

    for index, part in enumerate(parts):
        if part in {"--model", "-m"} and index + 1 < len(parts):
            return parts[index + 1]
        if part.startswith("--model="):
            return part.split("=", 1)[1]
    return None


def agent_environment(agent: str | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("BENCHMARK_")
        and not key.startswith("DEEPEVAL_")
        and key != "GOOGLE_API_KEY"
        and key != "OPENAI_API_KEY"
        and key != "SUPATEST_API_KEY"
        and key != "SUPATEST_PROJECT_ID"
    }
    env["NODE_ENV"] = "development"
    env["PATH"] = with_hidden_host_tools(
        with_local_tool_paths(env.get("PATH", "")),
        hidden_host_tools(),
    )
    if agent and agent_family(agent) == "supatest":
        env["SUPATEST_EVAL_TELEMETRY"] = (
            "1" if benchmark_supatest_eval_telemetry_enabled() else "0"
        )
    return env


def benchmark_supatest_eval_telemetry_enabled() -> bool:
    raw = os.getenv(
        "BENCHMARK_SUPATEST_EVAL_TELEMETRY",
        os.getenv("SUPATEST_EVAL_TELEMETRY", "1"),
    ).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def with_local_tool_paths(path_value: str) -> str:
    entries = [entry for entry in path_value.split(os.pathsep) if entry]
    for tool_dir in [Path.home() / ".maestro" / "bin"]:
        tool_entry = str(tool_dir)
        if tool_dir.exists() and tool_entry not in entries:
            entries.insert(0, tool_entry)
    return os.pathsep.join(entries)


def hidden_host_tools() -> list[str]:
    raw = os.getenv("BENCHMARK_HIDE_HOST_TOOLS", DEFAULT_HIDDEN_HOST_TOOLS).strip()
    if raw.lower() in {"", "0", "false", "no", "off", "none"}:
        return []
    return [tool.strip() for tool in raw.split(",") if tool.strip()]


def with_hidden_host_tools(path_value: str, tools: list[str]) -> str:
    if not tools:
        return path_value

    hidden = set(tools)
    entries = [entry for entry in path_value.split(os.pathsep) if entry]
    sanitized_entries = []
    for entry in entries:
        path = Path(entry)
        if path_contains_hidden_tool(path, hidden):
            sanitized_entries.append(str(sanitized_path_dir(path, hidden)))
        else:
            sanitized_entries.append(entry)
    return os.pathsep.join(sanitized_entries)


def path_contains_hidden_tool(path: Path, hidden: set[str]) -> bool:
    try:
        return any((path / tool).exists() for tool in hidden)
    except OSError:
        return False


def sanitized_path_dir(source_dir: Path, hidden: set[str]) -> Path:
    source_key = str(source_dir.resolve(strict=False))
    hidden_key = ",".join(sorted(hidden))
    digest = hashlib.sha256(f"{source_key}\0{hidden_key}".encode()).hexdigest()[:16]
    sanitized_dir = (
        Path(tempfile.gettempdir()) / "agent-benchmark-sanitized-path" / digest
    )
    sanitized_dir.mkdir(parents=True, exist_ok=True)

    try:
        children = list(source_dir.iterdir())
    except OSError:
        return sanitized_dir

    for child in children:
        if child.name in hidden:
            continue
        if not child.is_file() and not child.is_symlink():
            continue
        if not os.access(child, os.X_OK):
            continue

        target = sanitized_dir / child.name
        if target.exists() or target.is_symlink():
            continue
        try:
            target.symlink_to(child)
        except OSError:
            continue
    return sanitized_dir


def tool_policy_metadata() -> dict[str, object]:
    hidden = hidden_host_tools()
    return {
        "hiddenHostTools": hidden,
        "hiddenFromAgentPath": hidden,
        "rtkPolicy": (
            "Host-level rtk is hidden from benchmark-launched agent PATH by "
            "default. Supatest may use RTK only when provided by its own "
            "compiled runtime/toolchain."
        ),
    }


def render_command_template(
    template: str, fixture: EvalFixture, project_dir: Path, agent: str
) -> str:
    prompt = build_prompt(fixture)
    project_id = resolve_supatest_project_id() or ""
    model = agent_model(agent) or DEFAULT_AGENT_MODELS.get(agent_family(agent), "")
    model_arg = f"--model {shlex.quote(model)}" if model else ""
    difficulty = fixture_difficulty(fixture)
    return template.format(
        agent=shlex.quote(agent_family(agent)),
        prompt=shlex.quote(prompt),
        task=shlex.quote(fixture.task),
        mode=shlex.quote(fixture.mode),
        cwd=shlex.quote(str(project_dir)),
        logs_file=shlex.quote(str(fixture.logs_file)) if fixture.logs_file else "",
        model=shlex.quote(model) if model else "",
        model_arg=model_arg,
        project_id=shlex.quote(project_id),
        difficulty=shlex.quote(difficulty),
        max_iterations=str(max_iterations_for_fixture(fixture)),
    )


def resolve_supatest_project_id() -> str | None:
    explicit = (os.getenv("BENCHMARK_SUPATEST_PROJECT_ID") or "").strip()
    if explicit:
        return explicit

    settings_path = BENCHMARK_ROOT / ".supatest" / "settings.json"
    if settings_path.exists():
        try:
            project_id = json.loads(settings_path.read_text()).get("projectId")
        except Exception:
            project_id = None
        if project_id:
            return str(project_id).strip() or None
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
    profile = os.getenv("BENCHMARK_PROMPT_PROFILE", "qa").strip().lower() or "qa"
    if profile not in PROMPT_PROFILES:
        raise ValueError(
            "BENCHMARK_PROMPT_PROFILE must be one of: "
            + ", ".join(sorted(PROMPT_PROFILES))
        )

    if profile == "raw":
        parts = [fixture.task]
    elif profile == "minimal":
        parts = [
            "User request:",
            fixture.task,
            "",
            f"Mode: {fixture.mode}",
            "Work only inside the current project directory.",
        ]
    else:
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
