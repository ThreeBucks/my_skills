---
name: rtk
description: Use when running shell commands in Codex, especially in this user's workspaces, to prefix commands with rtk and use rtk proxy when raw command output is needed.
---

# RTK

RTK is the default shell command wrapper for this user.

## Rule

Prefix shell commands with `rtk` by default:

```bash
rtk git status
rtk pytest -q
rtk npm test
rtk cargo test
```

Use `rtk proxy <cmd>` when the exact raw command behavior or unfiltered output is needed:

```bash
rtk proxy sed -n '1,120p' README.md
rtk proxy jq . package.json
rtk proxy find . -maxdepth 2 -type f
```

## Verification

If RTK availability is unclear, check:

```bash
rtk --version
which rtk
rtk gain
```

If `rtk` is unavailable, state that directly and use the best available fallback.
