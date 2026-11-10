# OK Skills Selected

This directory integrates a selected subset of
[`mxyhi/ok-skills`](https://github.com/mxyhi/ok-skills) as a single local
Codex plugin-style bundle.

## Included Skills

- `diagnose`: disciplined diagnosis loop for hard bugs and performance regressions.
- `planning-with-files`: persistent file-backed planning with templates and helper scripts.
- `improve-codebase-architecture`: architecture review workflow for deeper modules,
  clearer seams, and better testability.

## Layout

```text
ok-skills/
  .codex-plugin/plugin.json
  skills/
    diagnose/
    planning-with-files/
    improve-codebase-architecture/
```

The Codex plugin manifest exposes `./skills/` so the three selected skills stay
grouped under one source directory instead of being flattened into the repo root.

## Source

See `SOURCE.md` for upstream commit and integration notes.
