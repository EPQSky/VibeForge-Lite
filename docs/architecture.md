# 架构说明

## 两个边界

本仓库把“可分发工作流”和“目标项目配置”建模为两个边界：

- Plugin 边界：`.codex-plugin/plugin.json` 与 `skills/`，由 Codex 安装和发现。
- Project 边界：`templates/project/` 与 `$vibe-init`，向目标仓库写入 project-local skills、来源元数据、持久规则、文档约定和状态。

Project 是默认安装边界：团队可以随仓库共享、审查和固定 workflow，不依赖某个用户目录。显式 `--skills plugin` 时只写项目配置，由已安装 Plugin 提供 skills。

## 初始化模型

`skills/vibe-init/scripts/vibe_init.py` 是零第三方依赖的确定性执行层。`$vibe-init` 负责理解仓库、解释计划和取得确认，再调用脚本落盘。

初始化器把目标文件分成三类：

- `AGENTS.md`：只管理 `<!-- vibeforge-lite:start -->` 与 `<!-- vibeforge-lite:end -->` 之间的区块。
- 独立文档：通过 `.vibecoding/state.json` 保存上次写入哈希。只有文件未被用户修改时才自动升级，否则报告冲突。
- Vendored distribution：把完整 `skills/` 映射到 `.agents/skills/`，把版本、来源锁和许可证映射到 `.agents/vibeforge-lite/`；每个文件独立记录哈希，不整目录覆盖。

默认调用是 dry-run。`--apply` 也不会覆盖冲突文件，因此脚本可以安全地重复运行。

当脚本从源码或 Plugin 运行时，从 distribution 根读取 skills 与元数据；当脚本从目标项目的 `.agents/skills/` 运行时，从相邻的 `.agents/vibeforge-lite/` 读取相同元数据，因此项目级安装可以自举升级。

## 工作流状态

产品访谈和 triage 标签与实现任务状态是不同维度：

- triage：`needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human`、`wontfix`；
- 本地实现：`ready-for-agent`、`in-progress`、`done`。

`$to-tickets` 直接产生 `ready-for-agent` 任务卡；`$triage` 面向尚未整理的外部输入，不重复 triage 已拆分任务。

## 上游维护

上游 skill 固定在 `UPSTREAM.lock` 的 commit，不动态跟随 `HEAD`。升级时逐项比较行为、重新应用本地 Codex 适配、更新许可证记录，并执行完整验证矩阵。

CI 从 OpenAI `codex` 仓库的固定 commit 下载 Plugin validator 及其同目录依赖，不追踪浮动分支。升级 validator 时先在本地验证新 commit，再更新 workflow 中的固定值。
