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
| 顺序执行 | `$execute-spec-tickets` | 按依赖逐票实施、独立复审、硬门禁并提交 |
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

发布版可以把 `dist/vibeforge-lite-0.3.0.tar.gz` 作为 release artifact。安装或更新 Plugin 后，新开一个 Codex task 让 skills 重新加载。

## 安装到项目

默认安装方式是把完整 workflow 固定在目标仓库，不依赖 Codex 用户目录。Clone 本仓库后运行：

```bash
python3 scripts/install_project.py --target /path/to/project
python3 scripts/install_project.py --target /path/to/project --apply
```

第一条命令只展示 dry-run；第二条只在计划无冲突时写入。用户也可以在 Clone 后直接对 Agent 说：

```text
把 VibeForge Lite 安装到 /path/to/project
```

Agent 应调用同一脚本、先展示 dry-run，再按用户的安装意图应用。安装结果包括：

- `.agents/skills/` 下完整的 project-local skills、脚本、assets 与 UI metadata；
- `.agents/vibeforge-lite/` 下版本清单、`UPSTREAM.lock`、许可证与第三方声明；
- `AGENTS.md` 中一个带版本的受管区块，区块外内容保持不变；
- `docs/agents/domain.md`、`issue-tracker.md` 与 `triage-labels.md`；
- 本地 tracker 使用的 `.scratch/` 与通用的 `docs/adr/` 目录骨架；
- `.vibecoding/state.json` 中的模板版本、skills 模式与所有受管文件哈希。

项目级 skills 与文档遵循同一安全规则：内容与当前发行版一致时 no-op；上次由 VibeForge 写入且未修改时可升级；用户修改、未知同名文件或符号链接会报告 `conflict` 并阻止本次所有写入。

## Plugin 模式

安装 Plugin 后可调用 `$vibe-init`。默认仍安装 project-local skills；只有明确希望依赖已安装 Plugin 时才选择轻量模式：

```bash
python3 /path/to/VibeForge-Lite/skills/vibe-init/scripts/vibe_init.py --target . --skills plugin
python3 /path/to/VibeForge-Lite/skills/vibe-init/scripts/vibe_init.py --target . --skills plugin --apply
```

无论哪种模式，初始化器都不会创建 `CONTEXT.md`、修改 `.codex/config.toml`、删除旧文件、降低权限或自动提交。不要使用旧的 `.codex/skills/` 路径。

`templates/project/` 展示初始化后的项目结构，其中 `.codex/config.toml` 仅包含可移植说明，不启用机器专属权限。

## 升级与卸载

升级前再次运行安装命令或 `$vibe-init` dry-run。初始化器只自动更新上次未被用户修改的受管文件；检测到用户修改时报告 `conflict`，不会覆盖。项目级安装可以直接使用仓库中已 vendoring 的 `.agents/skills/vibe-init/scripts/vibe_init.py` 自举升级。

卸载 Plugin 不会删除目标仓库内容。若要移除项目集成，先删除 `AGENTS.md` 的 `vibeforge-lite` 受管区块，再按需删除 `.agents/skills/` 中的 VibeForge skills、`.agents/vibeforge-lite/`、`.vibecoding/` 和未被项目继续使用的 `docs/agents/` 文件；不要删除团队自有的其他 project-local skills。

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

本项目使用 MIT License。部分 skills 以 `mattpocock/skills` 的 `v1.2.3` release 为权威上游，其 MIT License、固定 commit、未导入范围与本地修改说明随仓库分发。
