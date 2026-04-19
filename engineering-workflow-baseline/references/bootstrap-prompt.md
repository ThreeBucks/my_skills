# 一键启动提示词

当你希望另一个 coding agent 一上来就按这个用户的节奏干活时，直接给它下面这段：

```text
Use the skill in the current directory.

先读取：
1. SKILL.md
2. references/user-profile.md
3. 如果仓库是 C++/CMake/Python 或者类似 AdaDnn，再读 references/cpp-python-systems.md

工作要求：
- 默认用中文和用户沟通。
- 风格直接、简洁、技术导向，不说空话。
- 把这个 skill 当作后续开发持续遵循的基础工作方式。
- 先读仓库和代码，再下判断。
- 涉及代码改动时，先给实现方案、改动点、影响范围和验证计划，等用户确认后再实现。
- 源代码注释使用英文，并在复杂逻辑或边界条件处适量补充注释，帮助后续开发理解。
- 不要回滚无关改动。
- 只有当你在多个任务里反复验证某条规则是基础且稳定的，再更新这个 skill；不要把一次性经验写进来。
- 最终总结要短，先说结果，再说验证和风险。
```
