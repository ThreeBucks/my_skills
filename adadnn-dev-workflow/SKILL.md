---
name: adadnn-dev-workflow
description: 当用户在 AdaDnn 相关仓库中做开发、重构、调试、测试、方案设计或 review，尤其需要遵守该用户个人开发流程时使用。
---

# AdaDnn 开发流程

这个 skill 记录该用户在 AdaDnn 开发中的个人协作习惯，不承载 CCL、AdaEP、Kernel 等技术细节；具体技术判断回到目标仓库的项目级 skill 执行。

## 默认流程

- 开始任务先检查目标仓库的 `.picode/skills/`，按任务类型加载更具体的项目 skill。
- 开发、重构、接口变更、调试方案、测试方案默认先沟通方案，不直接实现。
- 方案确认后写入 AdaDnn 上级目录的 `develop_plan/`，也就是 `../develop_plan/`；不要写在 AdaDnn 仓库根目录。
- 实现过程按方案推进；如果当前代码事实、测试结果或用户新要求与方案不一致，先更新方案或说明偏差，再继续实现。
- 纯阅读、定位、解释、review 可以直接做；发现需要改代码时再回到方案流程。

## 常用项目 skill

- CCL、ACCL、communicator、comm slot、rank_info、comm_id、AdaLink：`.picode/skills/adadnn-ccl-dev`。
- AdaEP 调试、hang、mismatch、notify、dispatch、CI：`.picode/skills/adaep-debugging`。
- AdaEP 测试设计、quick、full、golden、case 粒度：`.picode/skills/adaep-ut-design`。
- ADAS kernel、PE、DMA、同步、tiling、编译：`.picode/skills/ada-kernel-agent-skills`。
