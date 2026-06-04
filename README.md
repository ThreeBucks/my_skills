# my_skills

个人本地 skill 集合，主要面向 Codex 使用。

## Codex 安装

在当前仓库中执行下面的命令，即可安装或更新所有 skills 和 Codex plugin bundles：

```bash
./install-codex.sh
```

只预览安装动作，不写入任何文件：

```bash
./install-codex.sh --dry-run
```

安装脚本会做两类同步：

- 将根目录下的独立 skills 复制到 `${CODEX_HOME:-~/.codex}/skills`。
- 将 Codex plugin bundles 复制到 `~/plugins`，更新
  `${AGENTS_HOME:-~/.agents}/plugins/marketplace.json`，并在检测到
  `codex` CLI 时执行 `codex plugin add <plugin>@personal`。

如果只想同步文件和 marketplace 元数据，不执行 `codex plugin add`，使用：

```bash
./install-codex.sh --no-plugin-add
```

安装完成后，开启一个新的 Codex thread，让新安装的 skills 和 plugins 被加载。

## Codex 卸载

卸载由当前仓库安装到 Codex 的 skills 和 plugin bundles：

```bash
./uninstall-codex.sh
```

只预览卸载动作，不删除任何文件：

```bash
./uninstall-codex.sh --dry-run
```

卸载脚本会做三类清理：

- 删除 `${CODEX_HOME:-~/.codex}/skills` 下与当前仓库同名的独立 skills。
- 删除 `~/plugins` 下与当前仓库同名的 Codex plugin bundles。
- 从 `${AGENTS_HOME:-~/.agents}/plugins/marketplace.json` 中移除对应的本地 plugin 条目，并在检测到 `codex` CLI 时执行 `codex plugin remove <plugin>@personal`。

如果只想删除文件和 marketplace 元数据，不执行 `codex plugin remove`，使用：

```bash
./uninstall-codex.sh --no-plugin-remove
```

卸载完成后，开启一个新的 Codex thread，让已移除的 skills 和 plugins 不再被加载。

## 清单

- `engineering-workflow-baseline`：个人工程工作流底座。
- `doc-coauthoring`：文档协作与共创工作流。
- `karpathy-guidelines`：务实、外科式修改导向的编码准则。
- `superpowers`：来自 `obra/superpowers` 的上游 Superpowers 整体 bundle。
- `ok-skills`：从 `mxyhi/ok-skills` 中筛选出的 Codex plugin bundle。
- `agent-skill-creator`：来自 `FrancyJGLisboa/agent-skill-creator` 的 skill 生成工具。
