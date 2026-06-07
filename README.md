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

如果 `codex` CLI 不在 `PATH`，脚本会尝试常见的 Codex.app 和 VSCode extension 路径；仍找不到时会报错。可以通过 `CODEX_CLI_PATH=/path/to/codex ./install-codex.sh` 显式指定。

如果只想同步文件和 marketplace 元数据，不执行 `codex plugin add`，使用：

```bash
./install-codex.sh --no-plugin-add
```

安装脚本会给每个安装目标写入 `.my-skills-install.json` 标记。再次安装时，只有带有当前仓库标记的同名目录会被自动更新；如果目标位置已经存在同名 skill 或 plugin，但没有当前仓库标记，脚本会拒绝覆盖，避免误伤你手工安装或其他来源安装的内容。

如果确认要接管并覆盖这些同名目标，使用：

```bash
./install-codex.sh --force
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

如果 `codex` CLI 不在 `PATH`，可以通过 `CODEX_CLI_PATH=/path/to/codex ./uninstall-codex.sh` 显式指定；仍找不到时脚本会报错，避免只删文件但留下 Codex registration。

如果只想删除文件和 marketplace 元数据，不执行 `codex plugin remove`，使用：

```bash
./uninstall-codex.sh --no-plugin-remove
```

卸载脚本默认只删除带有当前仓库 `.my-skills-install.json` 标记的目录；没有标记的同名 skill 或 plugin 会被跳过。这样可以避免误删同名但来源不同的内容。

如果确认要强制删除同名目标，使用：

```bash
./uninstall-codex.sh --force
```

卸载完成后，开启一个新的 Codex thread，让已移除的 skills 和 plugins 不再被加载。

## 清单

- `engineering-workflow-baseline`：个人工程工作流底座。
- `doc-coauthoring`：文档协作与共创工作流。
- `karpathy-guidelines`：务实、外科式修改导向的编码准则。
- `superpowers`：来自 `obra/superpowers` 的上游 Superpowers 整体 bundle。
- `ok-skills`：从 `mxyhi/ok-skills` 中筛选出的 Codex plugin bundle。
- `agent-skill-creator`：来自 `FrancyJGLisboa/agent-skill-creator` 的 skill 生成工具。
