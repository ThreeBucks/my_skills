# Source

- Upstream: https://github.com/mxyhi/ok-skills
- Commit: `f920ce42847260a7de093be2d91f40692566d5d6`
- Integrated on: 2026-06-04

## Integrated Paths

- `diagnose/` -> `skills/diagnose/`
- `planning-with-files/` -> `skills/planning-with-files/`
- `improve-codebase-architecture/` -> `skills/improve-codebase-architecture/`
- `grill-with-docs/ADR-FORMAT.md` -> `references/grill-with-docs/ADR-FORMAT.md`
- `grill-with-docs/CONTEXT-FORMAT.md` -> `references/grill-with-docs/CONTEXT-FORMAT.md`

## Local Changes

- Added `.codex-plugin/plugin.json` to expose the selected skill directories as
  one local Codex plugin-style bundle.
- Copied only the `grill-with-docs` reference files required by
  `improve-codebase-architecture` under `references/`, without exposing
  `grill-with-docs` as an additional skill.
- Added this source note and a local README.
- Did not copy the upstream `.git` directory.
