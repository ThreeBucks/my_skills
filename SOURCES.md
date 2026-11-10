# 来源与迁移记录

## 本次整理

以本仓库提交 `53f4683` 的个人定制版本为输入，重新编写通用工作流。正式安装来源仅为 `skills/`；不自动下载上游，不将旧 bundle 安装到 PiCode 或 Codex。

`legacy/` 是只读历史来源，不是备用技能集合。旧 `SKILL.md` 统一改名 `SKILL.retired.md`，防止递归发现再次暴露旧入口。旧规则中的自动落盘、安装、提交、领域环境和工具调用约定均不适用于正式集合。旧脚本、hooks、plugin manifests 只作历史材料，不运行。

## 来源

| 材料 | 来源与版本 | 处理 |
|---|---|---|
| Superpowers | https://github.com/obra/superpowers ；本次基于个人仓库 `53f4683` 的内置副本，未推断独立上游 SHA | 保留设计、实施、诊断、TDD、评审、验证方法；去除强制计划文件和平台流程；原许可证在 `legacy/superpowers/LICENSE` |
| OK Skills | https://github.com/mxyhi/ok-skills ，记录的引入版本 `f920ce42847260a7de093be2d91f40692566d5d6` | 吸收诊断和架构评估方法；不分发 Pi extension、持久化计划 hooks 或默认 HTML/CDN 流程；见 `legacy/ok-skills/SOURCE.md` 及各 LICENSE 文件 |
| Karpathy Guidelines | 个人副本注明 https://x.com/karpathy/status/2015883857489522876 ，frontmatter 声明 MIT | 将显式假设、最小修改、可验证目标合并到底座；原文保留在 `legacy/karpathy-guidelines/SKILL.retired.md` |
| Doc Coauthoring | https://github.com/anthropics/skills/tree/main/skills/doc-coauthoring 的个人定制副本；未记录独立上游 SHA | 保留直接成稿/迭代协作及读者测试的思路，正式中文入口重新整理；不推定其他子项目许可证自动适用 |
| 个人底座与源码调研 | 本仓库 `dev-baseline`、`systems-code-research-doc` | 保留证据与协作方法，移除具名领域路由 |
| Agent Skill Creator | https://github.com/FrancyJGLisboa/agent-skill-creator ，记录的引入版本 `299b62ecacf129a645d52cbfe86279fd6fa18dc8` | 完整退役，不分发其跨平台安装脚本或领域模板；历史来源与许可证保留 |

归档保留原版权声明，不以本文件替代原许可证。涉及 Superpowers 方法的正式技能随包携带 `LICENSE.superpowers.txt`；设计与诊断技能另带 `LICENSE.ok-skills.txt`。这些文件保留对应来源的原声明，不代表其他独立内容自动使用相同许可证。公开分发前应核对所复制内容的适用许可证；不能将所有目录一概宣称为同一许可证。

## 24 个旧入口的去向

| 旧入口 | 正式去向 |
|---|---|
| dev-baseline | dev-baseline |
| karpathy-guidelines | dev-baseline 的原则 |
| using-superpowers | dev-baseline 的最小路由 |
| rtk | 退役；工具可选，不卸载软件 |
| adadnn-dev-workflow | 退役；领域规则留待项目侧另行承接，不自动修改项目仓库 |
| brainstorming | design-workflow |
| writing-plans | design-workflow 的会话内分解 |
| improve-codebase-architecture | design-workflow 的架构评估参考 |
| executing-plans | execute-work |
| subagent-driven-development | execute-work 的委派参考 |
| dispatching-parallel-agents | execute-work 的并行条件 |
| using-git-worktrees | execute-work 的隔离、验证入口的授权清理 |
| systematic-debugging | systematic-debugging |
| diagnose | systematic-debugging |
| test-driven-development | test-driven-development |
| requesting-code-review | code-review-workflow |
| receiving-code-review | code-review-workflow |
| verification-before-completion | verification-before-completion |
| finishing-a-development-branch | verification-before-completion 的交付参考 |
| doc-coauthoring | doc-coauthoring |
| systems-code-research-doc | doc-coauthoring 的通用取证参考 |
| planning-with-files | 退役；仅保留显式持久化的通用约定，不保留三文件流程 |
| agent-skill-creator | 退役；按需使用宿主已有 skill 创建能力 |
| writing-skills | 退役；维护方法见 MAINTAINING.md |

## 更新纪律

- 不整包覆盖正式技能；先确认上游改变解决了什么问题，再移植必要方法。
- 一个规则只有一个权威入口；引用其他技能的职责，不复制另一套门禁。
- 更新后检查结构、链接与行为场景；来源研究、静态检查和端到端验证分开报告。
- 归档材料不自动激活，不作为当前用户授权，也不作为当前技术事实。
