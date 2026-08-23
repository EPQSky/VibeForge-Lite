# VibeForge Lite

一套 Codex-first 的通用软件开发工作流，把模糊想法稳定地推进为：

```text
grill -> spec -> tickets -> implement -> review
```

它不是某个业务项目的复制品。仓库同时交付 Codex Plugin、可审计的 skills、`$vibe-init` 初始化器和可直接检查的项目模板。

## 核心流程

| 阶段 | Skill | 产物 |
| --- | --- | --- |
| 路由 | `$vibe-guide` | 最小完整工作流建议 |
| 澄清 | `$grill-with-docs` / `$batch-grill-with-docs` | 稳定术语、ADR 与共识 |
| 规格 | `$to-spec` | 发布到配置的本地或远程 tracker |
| 拆票 | `$to-tickets` | 配置的 tracker 中可独立验收的垂直任务卡 |
| 实现 | `$implement`，适合时配合 `$tdd` | 聚焦实现与验证，不默认 commit |
| 评审 | `$code-review <review-base>` | 覆盖 commit 与工作树的 Standards + Spec 双轴发现 |
| 交接 | `$handoff` | 引用现有 artifacts 的会话交接 |

`$grill-me` 和 `$batch-grill-me` 适用于不需要同步项目文档的讨论；`$domain-modeling` 与 `$triage` 可单独使用。

## 安装

### 从源码验证

```bash
git clone https://github.com/EPQSky/VibeForge-Lite.git
cd VibeForge-Lite
python3 scripts/validate_repo.py
python3 -m unittest discover -s tests -v
```

### 本地 Marketplace 包

源仓库根目录本身是 Plugin 根。以下命令生成标准 Marketplace 布局，不修改 Codex 用户配置：

```bash
python3 scripts/package_release.py
codex plugin marketplace add ./dist/marketplace
codex plugin add vibeforge-lite@vibeforge-lite
```

发布版可以把 `dist/vibeforge-lite-0.1.0.tar.gz` 作为 release artifact。安装或更新 Plugin 后，新开一个 Codex task 让 skills 重新加载。

## 初始化项目

安装 Plugin 后，在目标仓库调用：

```text
$vibe-init
```

默认只检查并展示 dry-run。确认后让 Agent 应用，或直接运行同一实现：

```bash
python3 /path/to/VibeForge-Lite/skills/vibe-init/scripts/vibe_init.py --target .
python3 /path/to/VibeForge-Lite/skills/vibe-init/scripts/vibe_init.py --target . --apply
```

初始化器维护以下内容：

- `AGENTS.md` 中一个带版本的受管区块，区块外内容保持不变；
- `docs/agents/domain.md`、`issue-tracker.md` 与 `triage-labels.md`；
- 本地 tracker 使用的 `.scratch/` 与通用的 `docs/adr/` 惰性目录骨架；
- `.vibecoding/state.json` 中的模板版本、选择项与内容哈希。

它不会默认复制 Plugin skills、创建 `CONTEXT.md`、修改 `.codex/config.toml`、删除旧文件、降低权限或自动提交。

## 不安装 Plugin 的项目级用法

Codex 的仓库级 skill 目录是 `.agents/skills/`。需要 IDE 场景、团队内固定版本或项目覆盖时，可把所需 skill 目录 vendoring 到目标仓库的 `.agents/skills/`；不要使用旧的 `.codex/skills/` 路径。vendoring 时应同时保留 `UPSTREAM.lock` 与第三方许可。

`templates/project/` 展示初始化后的项目结构，其中 `.codex/config.toml` 仅包含可移植说明，不启用机器专属权限。

## 升级与卸载

升级前再次运行 `$vibe-init` dry-run。初始化器只自动更新上次未被用户修改的受管文件；检测到用户修改时报告 `conflict`，不会覆盖。

卸载 Plugin 不会删除目标仓库文档。若要移除项目集成，先删除 `AGENTS.md` 的 `vibeforge-lite` 受管区块，再按需删除 `.vibecoding/` 和未被项目继续使用的 `docs/agents/` 文件。

## 结构

```text
VibeForge-Lite/
├── .codex-plugin/plugin.json
├── skills/
├── templates/project/
├── scripts/
├── tests/
├── UPSTREAM.lock
├── THIRD_PARTY_NOTICES.md
└── LICENSE
```

Codex 项目级结构判断与官方资料索引见 `docs/codex-project-structure.md`。上游来源、本地差异和许可证分别记录在 `UPSTREAM.lock`、`THIRD_PARTY_NOTICES.md` 与 `licenses/`。

## 支持范围

首版只承诺 Codex CLI 与支持 Codex Plugin 的 Codex app surface。IDE 场景使用项目级 `.agents/skills/`。不同 surface 的 Plugin 支持会变化，发布前必须重新核对官方文档与当前 CLI。

## License

本项目使用 MIT License。部分 skills 派生自 `mattpocock/skills`，其 MIT License、固定 commit 与修改说明随仓库分发。
