# EPQ Vibecoding Agent 指南

## 交流与交付

- 默认使用简体中文交流和编写项目文档，代码标识、命令、配置键与第三方专有名词保持原文。
- 修改前先阅读 `README.md`、`docs/architecture.md`、`UPSTREAM.lock` 和受影响 skill。
- 保持 Codex-first：显式调用使用 `$skill-name`，项目级 skill 使用 `.agents/skills/`，Plugin skill 使用根级 `skills/`。
- 不把用户名、绝对路径、凭据、私有仓库信息或示例来源项目的领域内容写入发布物。

## 变更边界

- `skills/` 是 Plugin 发布内容；`templates/project/` 是 `$vibe-init` 的目标项目模板。
- 上游派生 skill 的来源和本地修改必须同步记录在 `UPSTREAM.lock` 与 `THIRD_PARTY_NOTICES.md`。
- `$vibe-init` 必须 dry-run-first、幂等、保留用户内容，并在冲突时停止覆盖。
- `$implement` 不得默认提交；`$code-review` 必须同时覆盖 Standards 和 Spec 两个轴。
- 不手工编辑生成的 `dist/`；使用 `python3 scripts/package_release.py` 重新生成。

## 验证

完成修改前运行：

```bash
python3 scripts/validate_repo.py
python3 -m unittest discover -s tests -v
python3 scripts/package_release.py --check
python3 "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py" .
```

最后一条命令依赖本机 Codex 安装；CI 应显式提供对应 validator。
