# Changelog

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
