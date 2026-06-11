# RTK Benchmark Fairness Policy

## Purpose

This document defines when `rtk` usage is fair in the benchmark and when it
would bias results. The benchmark should compare agents in a way that is easy to
defend: either as shipped products with their own internal tooling, or as agents
running in a deliberately standardized environment.

## Fair Benchmark Framing

The recommended framing is:

> Compare each QA agent as a shipped product/toolchain.

Under this framing, an agent may use capabilities that are part of its own
runtime, product, or framework. If the locally compiled Supatest runtime ships
with `rtk` internally, then `rtk` is part of Supatest's toolchain advantage in
the same way another agent might ship with its own planner, shell wrapper,
browser automation adapter, or test runner integration.

This is fair when it is disclosed clearly in benchmark documentation and result
reports.

## Fair Uses Of RTK

`rtk` usage is fair when:

- Supatest includes `rtk` as part of its own internal runtime or framework.
- Supatest decides to use `rtk` without benchmark prompt hints that are hidden
  from other agents.
- The benchmark report discloses that Supatest includes an RTK command proxy as
  part of its shipped runtime.
- Other agents are not artificially prevented from using their own shipped
  internal tools.
- The benchmark does not claim that every agent had an identical low-level shell
  environment if Supatest has additional product-integrated tooling.

Suggested disclosure text:

```text
Supatest includes RTK command proxy support as part of its runtime/toolchain.
Other agents were run with their default shipped command-line behavior unless
otherwise noted.
```

## Unfair Uses Of RTK

`rtk` usage is unfair when:

- The benchmark harness injects `rtk` into Supatest only, while presenting the
  run as a neutral shared environment.
- The shared prompt tells all agents to use `rtk` even though only Supatest has
  reliable access to it.
- The host machine's `PATH` accidentally exposes `rtk` to every agent, making it
  unclear whether usage came from the agent product or from the benchmark host.
- Supatest receives private benchmark-only instructions about `rtk` that are not
  part of the shipped Supatest agent behavior.
- Reports omit the fact that Supatest had integrated `rtk` support.

## Recommended Harness Policy

For clean and defensible results:

1. Do not mention `rtk` in the shared benchmark prompt.
2. Do not add benchmark-specific `rtk` instructions to fixture tasks.
3. Do not rely on the host machine's global `PATH` to provide `rtk`.
4. If Supatest should use `rtk`, make that capability part of Supatest's own
   installed runtime or internal agent framework.
5. Keep benchmark reports explicit about which agents include extra internal
   tooling.
6. Consider running an ablation when measuring the value of `rtk` itself:
   `supatest-with-rtk` versus `supatest-no-rtk`.

## Environment Isolation Guidance

The benchmark runner hides host-level `rtk` from the `PATH` inherited by
benchmark-launched agents by default:

```bash
BENCHMARK_HIDE_HOST_TOOLS=rtk
```

This avoids accidentally giving every agent access to `/opt/homebrew/bin/rtk` or
another globally installed host copy. Neighboring tools in the same directory,
such as `codex`, `gemini`, `node`, or `npm`, remain available through a
sanitized PATH directory.

This is PATH-level isolation, not a full filesystem sandbox. An agent should not
be prompted to use an absolute host `rtk` path. Supatest should get RTK only from
its own compiled runtime/toolchain if the product is meant to ship with RTK
support.

For local debugging only, host-tool hiding can be disabled:

```bash
BENCHMARK_HIDE_HOST_TOOLS=none
```

A stricter benchmark should also consider these approaches:

- Provide each agent only the tools expected in the benchmark baseline.
- Let Supatest access `rtk` only through its own packaged runtime, not through
  the benchmark harness.
- Record the effective tool environment in the run metadata.

## Recommended Result Language

Use language like this in public or internal result summaries:

```text
This benchmark compares agents as shipped toolchains, not as identical sandboxed
LLMs. Host-level RTK was hidden from benchmark-launched agent PATH. Supatest was
run from the local compiled Supatest runtime, which may include integrated RTK
command proxy support. Cursor, Codex, and Gemini were run with their configured
default CLI behavior. No shared fixture prompt instructed agents to use RTK.
```

Avoid language like:

```text
All agents had identical command execution tooling.
```

unless the harness actually enforces identical command execution tooling for
every agent.

## Practical Recommendation

Treat Supatest's internal `rtk` support as fair product differentiation, but
make the benchmark environment explicit:

- Product benchmark: Supatest may use internal `rtk`; disclose it.
- Standardized environment benchmark: either give every agent equivalent access
  or disable `rtk` for all agents.
- RTK impact study: run Supatest both with and without `rtk` and compare the
  delta.
