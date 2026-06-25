---
name: rtk
description: 在 Codex 中运行 shell 命令时使用，尤其是该用户的工作区；默认给命令加 rtk，需要原始输出、shell 条件、管道或重定向时使用 rtk proxy。
---

# RTK

RTK 是该用户默认的 shell 命令包装器。

## 规则

默认给 shell 命令加 `rtk`：

```bash
rtk git status
rtk pytest -q
rtk npm test
rtk cargo test
```

需要原始命令行为、未过滤输出、shell 条件、管道、重定向、通配或 shell builtin 时，用 `rtk proxy`。复杂命令优先用 `bash -lc` 包住：

```bash
rtk proxy sed -n '1,120p' README.md
rtk proxy jq . package.json
rtk proxy bash -lc 'find . -maxdepth 2 -type f | sort'
```

不要把 `test`、`&&`、`|`、`>` 这类 shell 语法直接挂在 `rtk` 后面；它们属于 shell，需要走 `rtk proxy bash -lc '<cmd>'`。

## 验证

如果不确定 RTK 是否可用，检查：

```bash
rtk --version
which rtk
rtk gain
```

如果 `rtk` 不可用，直接说明，并使用当前环境里最合适的 fallback。
