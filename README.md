# my_skills

面向 PiCode 的通用工程工作流集合：规定如何调研、设计、实施、评审和交付，不承载项目知识、领域排障手册或平台工具实现。正式集合从 24 个入口收敛为 **8 个**，默认只加载 **dev-baseline**。

## 八个入口

| Skill | 职责 |
|---|---|
| [dev-baseline](skills/dev-baseline/SKILL.md) | 上下文、授权、最小路由、工具选择与证据纪律；唯一默认 |
| [design-workflow](skills/design-workflow/SKILL.md) | 需求澄清、方案比较、架构评估、范围与验收、会话内分解 |
| [execute-work](skills/execute-work/SKILL.md) | 按批准范围实施，管理依赖，按需委派、并行和隔离 |
| [systematic-debugging](skills/systematic-debugging/SKILL.md) | 通用诊断方法，不包含领域知识 |
| [test-driven-development](skills/test-driven-development/SKILL.md) | 适用行为变更的 RED → GREEN → REFACTOR |
| [code-review-workflow](skills/code-review-workflow/SKILL.md) | 发起/执行/接收评审，覆盖未提交变更与反馈核实 |
| [doc-coauthoring](skills/doc-coauthoring/SKILL.md) | 通用取证、技术文档、直接成稿或迭代共创、配图与读者检查 |
| [verification-before-completion](skills/verification-before-completion/SKILL.md) | 当前状态的验收证据、准确声明结果、已授权交付与清理 |

每个任务选一个主流程，按需补充方法，不串联全部技能。设计决定方案，写作表达方案；TDD、代码评审和最终验证互不替代。

## 默认约定

- 规划在会话与宿主任务列表中进行，不自动创建本地 plan/spec/progress/findings 文件。
- 正式设计文档、配图及必要构建产物仍按用户指定目标交付，不附带另一套过程材料。
- 复用已有审批，仅为新增范围确认；仅暂停依赖阻塞的部分。
- 专用文件工具优先；RTK 不再是默认依赖，软件不被卸载，可以按需摘要输出。
- worktree、子代理、依赖安装、提交、推送和发布不是默认必经步骤。
- 通用方法留在此仓库；领域技能和环境规则由目标项目提供。
- 飞书等平台的鉴权、执行与交付门交给平台能力；不复制实现、不绕过质量要求。

## PiCode 安装与更新

需要 Python 3.9+。安装是独立部署动作，先预览：

```bash
./install-picode.sh --dry-run
```

确认目标与变更后安装全部八项：

```bash
./install-picode.sh
```

精选安装或排除技能：

```bash
./install-picode.sh --only dev-baseline,doc-coauthoring
./install-picode.sh --exclude systematic-debugging --dry-run
```

`--only`、`--exclude` 接受逗号列表，可重复。仅选择文档技能不会自动安装底座或写入指向不存在底座的默认项；只安装部分技能时，其他未安装能力需由宿主已有技能提供，不能假装可用。

默认目标是 `${PICODE_HOME:-~/.picode}/skills`。`--picode-home` 可指定隔离 home，`--skills-dir` 可指定该 home 下相对目录或专用绝对目录。拒绝路径穿越、符号链接、根目录和与源码重叠的目标。

安装器只读取正式 `skills/*/SKILL.md`，校验入口名称与目录一致；来源目录缺入口或格式不符合约定时先报错，不将来源损坏当成退役。不展开 legacy/plugin bundles。

每个安装目录写 `.my-skills-install.json`。新版 manifest v2 记录文件内容摘要和常规权限位（含技能根目录及子目录）；不记录 ACL 或所有者。普通更新只替换来源一致且本地内容、文件集合和权限均未修改的受管目录。来源与已安装状态一致时输出 `unchanged`，不重写目录。

预览和执行使用同一份内存操作清单，列出目标、状态、动作、原因与汇总。有多项冲突时一次报告，不只显示第一项；任何预检冲突都不修改安装项和默认配置。无关第三方链接或坏 marker 只提示并保留，但选中的同名目标仍严格拒绝处理。

### 默认加载

安装器仅更新 `picode.md` 中自己维护的标记块，默认只有实际已安装的 `dev-baseline`。用户手写内容保持不变；旧默认引用会提示人工检查。

```bash
./install-picode.sh --no-defaults
```

该选项完全不更新默认配置。安装后启动新 PiCode 会话并核对实际解析路径；本仓库不会删除 Hub 同名技能，也不保证整个宿主只显示八个技能。

### 旧版本迁移

旧版本 marker 无摘要或仅有 manifest v1 内容摘要，不能证明权限未被修改，预览会列出旧格式并说明需要确认。先检查来源、差异并保存需要的修改，再显式确认；`--force` 不是自动迁移前置。

```bash
# 先列出完整迁移状态与冲突，不写入
./install-picode.sh --prune --dry-run
# 核对旧版本/本地修改后，可预览显式确认后的动作
./install-picode.sh --prune --force --dry-run
```

- `--prune` 仅清理明确退役名单内、且标记属于本仓库的安装项；不会删除因 `--only` 未选中的现役技能。未知的来源缺失项保留并提示，不自动退役。
- `--force` 仅确认覆盖/删除本仓库受管项的本地修改或旧 marker。**不同于旧版，它不能接管无标记或其他来源目录。**
- 预览命令没有授权真实删除；确认后移除 `--dry-run` 才会执行。不要让 agent 自动追加 `--force`。
- 卸载和退役清理枚举安装标记，不依赖旧源码目录仍存在。
- 所有目标和配置先预检；发现冲突不会先安装一半。单项更新在切换成功前保留旧目录，切换失败时尝试恢复；恢复失败会保留备份并报告路径，不能把失败备份当临时文件清掉。
- 这不是完整批次事务：先完成的项目不因后续失败自动回滚，也不承诺断电、磁盘损坏或外部并发修改下的恢复。默认配置最后更新，失败后应先检查实际状态再重试。
- 来源身份仍包含仓库绝对路径。搬迁仓库后，工具会报告来源不匹配而不是自动认领；尤其不能把“未识别到归属”当作卸载成功并清除默认块。需要恢复原路径或另行核对迁移，不要手改 marker 来绕过检查。
- 领域规则退出此集合，不在迁移中自动写入领域项目。

## PiCode 卸载

```bash
./uninstall-picode.sh --dry-run
./uninstall-picode.sh --only doc-coauthoring --dry-run
```

确认后去掉 `--dry-run`。只卸载匹配本仓库标记的项；内容修改、权限修改、旧 marker 和符号链接同样受保护。已知现役/退役名称已不存在时输出 `already absent` 并成功返回，未知名称仍报错，同名第三方目标仍拒绝处理。默认块根据剩余受管底座调整，保留手写内容与原始换行；末尾无换行时也与新维护块分开。

## Codex 兼容

```bash
./install-codex.sh --dry-run
./uninstall-codex.sh --dry-run
```

Codex 只安装相同的八项到 `${CODEX_HOME:-~/.codex}/skills`，支持同样的精选、摘要保护和退役项清理。不会调用 Codex CLI、同步 bundle、修改 `~/plugins` 或 marketplace，也不自动配置 Codex 的默认加载规则。

旧参数 `--agents-home`、`--plugin-home`、`--no-plugin-add` / `--no-plugin-remove`、`--require-codex-cli` 仅兼容解析，不再产生插件动作。**已存在的旧插件/注册不会自动清理**；如需退役，另行确认来源和授权。

## 来源、归档与维护

- [SOURCES.md](SOURCES.md)：来源、许可证位置、24 项迁移映射和更新纪律。
- [MAINTAINING.md](MAINTAINING.md)：维护方法、结构测试和行为评估说明。
- `legacy/`：保留旧材料和许可证；入口改名 `SKILL.retired.md`，不用于运行或安装。
- `skills/`：唯一正式分发来源；内部参考文件保持自包含。

验证：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

安装测试只在临时目录执行。`tests/workflow_cases.py` 提供十八个行为回归场景；结构断言、行为模拟和实际工具执行是不同验证层级，不互相冒充。
