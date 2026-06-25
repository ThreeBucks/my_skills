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
  `codex` CLI 时执行 `codex plugin add <plugin>@personal` 做正式注册。

如果 `codex` CLI 不在 `PATH`，脚本会继续尝试这些位置：

- `CODEX_CLI_PATH`
- `VSCODE_AGENT_FOLDER/extensions/openai.chatgpt-*/bin/**/codex`
- `VSCODE_EXTENSIONS/openai.chatgpt-*/bin/**/codex`
- `~/.vscode/extensions/openai.chatgpt-*/bin/**/codex`
- `~/.vscode-server/extensions/openai.chatgpt-*/bin/**/codex`
- `~/.vscode-server-insiders/extensions/openai.chatgpt-*/bin/**/codex`
- `~/.vscode-remote/extensions/openai.chatgpt-*/bin/**/codex`
- macOS 的 `/Applications/Codex.app/Contents/Resources/codex`

仍找不到时，脚本不会失败：它会继续完成 skills、plugin 文件和 marketplace 元数据同步，并跳过 `codex plugin add`。这种情况下独立 skills 会安装好，但 plugin bundles 不会完成 Codex 正式注册。远端安装 plugin 时建议使用 `--require-codex-cli`，这样找不到 VSCode 里的 `codex` 会直接报错，避免误以为 plugin 已注册。

如果远端确实有 `codex` CLI 但脚本没找到，可以显式指定：

```bash
CODEX_CLI_PATH=/path/to/codex ./install-codex.sh
```

如果你希望找不到 `codex` CLI 时直接失败，使用：

```bash
./install-codex.sh --require-codex-cli
```

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

如果 `codex` CLI 不在 `PATH`，可以通过 `CODEX_CLI_PATH=/path/to/codex ./uninstall-codex.sh` 显式指定；仍找不到时脚本不会失败，会继续删除本地文件和 marketplace 元数据，并跳过 `codex plugin remove`。

如果你希望找不到 `codex` CLI 时直接失败，使用：

```bash
./uninstall-codex.sh --require-codex-cli
```

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

## Picode 安装

在当前仓库中执行下面的命令，即可安装或更新所有适配 Picode 的 skills：

```bash
./install-picode.sh
```

只预览安装动作，不写入任何文件：

```bash
./install-picode.sh --dry-run
```

安装脚本会做两类同步：

- 将根目录下的独立 skills 复制到 `${PICODE_HOME:-~/.picode}/skills`。
- 将 Codex plugin bundles 中的 `skills/*` 展开为 Picode 单个 skills，并复制到 `${PICODE_HOME:-~/.picode}/skills`。

Picode 没有 Codex plugin 注册概念，所以 `superpowers`、`ok-skills` 这类 bundle 不会作为整体 plugin 安装；其中每个 `SKILL.md` 会作为独立 Picode skill 安装。

安装脚本会更新 `${PICODE_HOME:-~/.picode}/picode.md` 中由当前仓库维护的默认加载 block，让 Picode 新会话默认加载：

- `dev-baseline`
- `karpathy-guidelines`
- `rtk`

如果不想改 `picode.md`，使用：

```bash
./install-picode.sh --no-defaults
```

安装脚本会给每个安装目标写入 `.my-skills-install.json` 标记。再次安装时，只有带有当前仓库标记的同名目录会被自动更新；如果目标位置已经存在同名 skill，但没有当前仓库标记，脚本会拒绝覆盖，避免误伤你手工安装或其他来源安装的内容。

如果确认要接管并覆盖这些同名目标，使用：

```bash
./install-picode.sh --force
```

安装完成后，开启一个新的 Picode 会话，让新安装的 skills 被加载。

## Picode 卸载

卸载由当前仓库安装到 Picode 的 skills：

```bash
./uninstall-picode.sh
```

只预览卸载动作，不删除任何文件：

```bash
./uninstall-picode.sh --dry-run
```

卸载脚本会删除 `${PICODE_HOME:-~/.picode}/skills` 下由当前仓库安装的 skills，并移除 `picode.md` 中由当前仓库维护的默认加载 block。没有 `.my-skills-install.json` 标记的同名 skill 会被跳过。

如果确认要强制删除同名目标，使用：

```bash
./uninstall-picode.sh --force
```

卸载完成后，开启一个新的 Picode 会话，让已移除的 skills 不再被加载。

## 清单

- `dev-baseline`：开发任务默认初始化规则。
- `rtk`：默认 shell 命令包装规则，要求优先使用 `rtk` 和 `rtk proxy`。
- `doc-coauthoring`：文档协作与共创工作流。
- `karpathy-guidelines`：务实、外科式修改导向的编码准则。
- `adadnn-dev-workflow`：AdaDnn 开发任务中的个人协作流程，要求先方案、方案写入上级 `develop_plan/`，并按项目 skill 工作。
- `superpowers`：来自 `obra/superpowers` 的上游 Superpowers 整体 bundle。
- `ok-skills`：从 `mxyhi/ok-skills` 中筛选出的 Codex plugin bundle。
- `agent-skill-creator`：来自 `FrancyJGLisboa/agent-skill-creator` 的 skill 生成工具。
- `systems-code-research-doc`：复杂系统源码调研到学习/分享文档的工作流。
