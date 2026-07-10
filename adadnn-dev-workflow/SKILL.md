---
name: adadnn-dev-workflow
description: 当用户在 AdaDnn 相关仓库中做开发、重构、调试、测试、运行命令、代码格式、方案设计或 review，尤其需要遵守该用户个人流程和 runtime 环境前置检查时使用。
---

# AdaDnn 开发流程

这个 skill 记录该用户在 AdaDnn 开发中的个人协作习惯，不承载 CCL、AdaEP、Kernel 等技术细节；具体技术判断回到目标仓库的项目级 skill 执行。

## 默认流程

- 开始任务先检查目标仓库的 `.picode/skills/`，按任务类型加载更具体的项目 skill。
- 开发、重构、接口变更、调试方案、测试方案默认先沟通方案，不直接实现。
- 方案确认后写入 AdaDnn 上级目录的 `develop_plan/`，也就是 `../develop_plan/`；不要写在 AdaDnn 仓库根目录。
- 实现过程按方案推进；如果当前代码事实、测试结果或用户新要求与方案不一致，先更新方案或说明偏差，再继续实现。
- 在 AdaDnn 中写完或改完代码后，使用仓库内 `scripts/clang-tidy.sh` 脚本处理代码 format；不要只依赖通用 editor format。
- 纯阅读、定位、解释、review 可以直接做；发现需要改代码时再回到方案流程。

## 运行前置环境

- 在 AdaDnn 仓库里跑 build、gtest、pytest、mpirun 或任何 runtime/TSIM/CCL/AdaEP 命令前，先在同一个 shell 执行 `source scripts/env.sh`。
- agent 跑命令时不要把 `source` 和测试拆成两次 shell 调用；用 `bash -lc 'source scripts/env.sh && ...'` 包住。
- TSIM、CCL、pytest ccl、mpirun、集群 case 默认先显式准备：

```bash
export ADAVM_CLIENT_PATH="${ADAVM_CLIENT_PATH:-/usr/bin/adavm_client}"
export ADAX_RT_USE_TSIM_MODE="${ADAX_RT_USE_TSIM_MODE:-1}"
export SIM_LOG_MIN_LEVEL="${SIM_LOG_MIN_LEVEL:-INFO}"
export CCL_FORK_TEST="${CCL_FORK_TEST:-1}"
```

- `ADAX_RT_USE_TSIM_MODE=1` 是 adavm perf 默认；`2` 是 tsim_lite，必要时再设 `TSIM_LITE_THREADS=<0-66>`；真卡运行才用 `0`。
- 需要本地 dump/printf 时再加 `export ADAX_TSIM_WITH_HACK_PRINTF=1`。
- 不确定环境是否已生效时，先查 `env | rg 'ADAVM_CLIENT_PATH|ADAX_RT_USE_TSIM_MODE|SIM_LOG_MIN_LEVEL|CCL_FORK_TEST|TSIM_LITE_THREADS'`，不要等测试失败后再补。

## 常用项目 skill

- CCL、ACCL、communicator、comm slot、rank_info、comm_id、AdaLink：`.picode/skills/adadnn-ccl-dev`。
- AdaEP 调试、hang、mismatch、notify、dispatch、CI：`.picode/skills/adaep-debugging`。
- AdaEP 测试设计、quick、full、golden、case 粒度：`.picode/skills/adaep-ut-design`。
- ADAS kernel、PE、DMA、同步、tiling、编译：`.picode/skills/ada-kernel-agent-skills`。
