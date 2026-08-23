# Codex 项目级结构检查

本文在 2026-08-23 按 OpenAI 官方文档和本机 `codex-cli 0.146.0` 核验。

## 结构结论

| 能力 | 正确落点 | 模板策略 |
| --- | --- | --- |
| 持久项目规则 | 根或子目录 `AGENTS.md` / `AGENTS.override.md` | 根文件保持精简，专题规则放 `docs/agents/` |
| 仓库共享 skills | `.agents/skills/<name>/SKILL.md` | 仅用于项目固定版本或覆盖 |
| 项目配置 | `.codex/config.toml` | 只在可信项目加载，禁止机器绝对路径和凭据 |
| 可分发工作流 | `.codex-plugin/plugin.json` + Plugin 根级 `skills/` | 本仓库的主要交付形态 |
| Skill 定义 | `SKILL.md` YAML frontmatter | `name` 与目录一致，`description` 写明触发条件 |
| Skill UI 策略 | `agents/openai.yaml` | 显式流程可关闭 implicit invocation |
| 显式调用 | `$skill-name` | 不把自定义 skill 写成 slash command |

`AGENTS.md` 会按目录层级叠加，更接近当前工作目录的规则优先。根文件应保存可执行规则、项目事实和验证入口，避免把长篇背景全部塞进指令上下文。

Plugin 和项目本地 skill 是两套分发边界：Plugin 内使用 `skills/`；业务仓库共享 skill 使用 `.agents/skills/`。`.codex/skills/` 不是当前官方仓库级 skill 位置。

项目 `.codex/config.toml` 只有在项目被信任后才加载。通用模板不能写用户目录、工作区绝对路径或降低 sandbox/approval 边界；没有具体设置需求时，保持空配置或仅保留说明最稳妥。

## 本仓库发布门禁

- 官方 Plugin validator 通过。
- JSON、TOML、YAML frontmatter 与 `agents/openai.yaml` 可解析。
- 每个 `$skill-name` 路由都指向实际发布的 skill。
- fresh、dry-run、repeat、upgrade、conflict 初始化场景通过。
- 发布包不含用户绝对路径、凭据、旧 `.codex/skills/` 或来源项目领域词。
- 每个上游派生 skill 都有 commit、路径、许可证和本地修改记录。

## 官方资料

- [Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Build skills](https://developers.openai.com/plugins/build/skills)
- [Build plugins](https://developers.openai.com/plugins/build/plugins)
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Permissions](https://learn.chatgpt.com/docs/permissions)
- [Plugins](https://learn.chatgpt.com/docs/plugins)

官方能力和 surface 支持会变化；每次发布都应重新核验，不把本文当作永久兼容承诺。
