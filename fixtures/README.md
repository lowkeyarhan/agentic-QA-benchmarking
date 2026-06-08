# Fixture Source

The benchmark uses a copied fixture tree in this folder:

```text
agent-eval-fixtures/fixtures
```

At runtime, each selected fixture project is copied into:

```text
runs/<run-id>/<eval-id>/<agent>/project
```

That keeps benchmark mutations and generated files out of the source fixture folders.

The copy was sourced from the repo's `agent-eval-fixtures/` directory, excluding generated dependency/output folders such as `node_modules`, `dist`, `coverage`, `playwright-report`, and `test-results`.
