# Changelog

## 0.3.2 - 2026-08-28

- 将 `$execute-spec-tickets` 的单票修复上限从五轮提高到九轮；第九轮后的第十次独立复审仍阻断时，才进入修复耗尽流程。
- 同步更新状态契约、`skip` 硬门禁和自动化测试，确保九轮上限由校验脚本强制执行。

## 0.3.1 - 2026-08-28

- 将 `$execute-spec-tickets` 的单票修复上限从三轮提高到五轮；第五轮后的第六次独立复审仍阻断时，才进入修复耗尽流程。
- 同步更新状态契约、`skip` 硬门禁和自动化测试，确保五轮上限由校验脚本强制执行。

## 0.3.0 - 2026-08-26

- 新增 `$execute-spec-tickets`，按依赖顺序串行实施已批准 Tickets，并为每票执行独立复审、最多三轮修复、失败隔离和范围受控的 Commit。
- 新增 `validate_ticket_gate.py`，校验 Tracker 完成状态、验收证据、评审历史、提交范围、提交后快照和修复耗尽后的跳票条件。

## 0.2.1 - 2026-08-26

- 将 `mattpocock/skills v1.2.3`（commit `6acc160e4e0cd062dbbbd7a1b26ae92855edf07e`）设为派生 skills 的权威上游基线。
- 吸收该 release 的 phase-boundary 路由、grilling 问题格式、事实调查规则与 spec 术语更新，同时保留 VibeForge Lite 的 Codex 调用、安全边界和顺序访谈适配。
- 明确记录 `v1.2.3` 中未导入的 skills，以及该 release 已移除但本项目继续维护的 legacy `batch-grill-me`。

## 0.2.0 - 2026-08-26

- `$vibe-init` 默认把完整 workflow vendoring 到目标项目的 `.agents/skills/`，不依赖用户级安装。
- 项目级安装同步保存版本、上游锁与第三方许可证，并通过状态哈希安全升级。
- 新增 clone 仓库后的 `scripts/install_project.py` 入口，支持对话驱动的指定目录安装。
- 保留 `--skills plugin`，供明确希望复用已安装 Plugin 的项目选择轻量初始化。

## 0.1.0 - 2026-08-23

- 首次打包 Codex Plugin 与通用项目模板。
- 提供 `$vibe-init` dry-run、幂等更新、受管区块、状态哈希与冲突保护。
- 固定并记录 `mattpocock/skills` 来源、许可证与本地 Codex 适配。
- 建立 `grill -> spec -> tickets -> implement -> review` 主流程及验证矩阵。
- 评审覆盖 committed、staged、unstaged 与 untracked 工作，外部 tracker 内容按不可信数据处理。
- 发布包使用 Git 跟踪文件白名单并生成可复现归档；初始化器拒绝受管路径中的符号链接。
