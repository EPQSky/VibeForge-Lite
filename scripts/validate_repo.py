#!/usr/bin/env python3
"""Validate the source repository without depending on Codex internals."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - CI installs requirements-dev.txt
    yaml = None

SKILL_REF = re.compile(r"\$([a-z0-9]+(?:-[a-z0-9]+)*)")
ABSOLUTE_HOME = re.compile(r"/(?:home|Users)/[^/\s`]+/")


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    try:
        raw = text.split("---\n", 2)[1]
    except IndexError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc
    if yaml is not None:
        value = yaml.safe_load(raw)
    else:
        value = {}
        for line in raw.splitlines():
            key, separator, item = line.partition(":")
            if separator:
                value[key.strip()] = item.strip()
    if not isinstance(value, dict):
        raise ValueError("frontmatter is not a mapping")
    return value


def portability_errors(root: Path) -> list[str]:
    errors: list[str] = []
    surfaces = [root / "templates/project", root / "skills/vibe-init/assets/project"]
    for surface in surfaces:
        if not surface.exists():
            continue
        for path in surface.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(root)
            if ABSOLUTE_HOME.search(text):
                errors.append(f"{rel}: absolute home path")
            if re.search(r"\bMinerU\b|mineru-fastapi", text, re.IGNORECASE):
                errors.append(f"{rel}: source-project term")
            if ".codex/skills/" in text:
                errors.append(f"{rel}: legacy project skill path")
            if re.search(r"(?:api[_-]?key|token|password)\s*=\s*['\"][^'\"]+", text, re.IGNORECASE):
                errors.append(f"{rel}: possible credential")
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = root / ".codex-plugin/plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"invalid plugin manifest: {exc}"]
    if manifest.get("name") != "epq-vibecoding":
        errors.append("plugin name must be epq-vibecoding")
    version = manifest.get("version", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append("plugin version must be strict SemVer")
    if manifest.get("skills") != "./skills/":
        errors.append("plugin skills path must be ./skills/")

    skills_root = root / "skills"
    skill_names = {path.parent.name for path in skills_root.glob("*/SKILL.md")}
    for name in sorted(skill_names):
        path = skills_root / name / "SKILL.md"
        try:
            frontmatter = parse_frontmatter(path)
        except ValueError as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
            continue
        if frontmatter.get("name") != name:
            errors.append(f"{path.relative_to(root)}: name does not match directory")
        if not frontmatter.get("description"):
            errors.append(f"{path.relative_to(root)}: missing description")
        metadata = path.parent / "agents/openai.yaml"
        if not metadata.exists():
            errors.append(f"{metadata.relative_to(root)}: missing")
        elif yaml is not None:
            try:
                value = yaml.safe_load(metadata.read_text(encoding="utf-8"))
                if not isinstance(value, dict) or "interface" not in value:
                    errors.append(f"{metadata.relative_to(root)}: invalid UI metadata")
            except yaml.YAMLError as exc:
                errors.append(f"{metadata.relative_to(root)}: invalid YAML: {exc}")

        for ref in SKILL_REF.findall(path.read_text(encoding="utf-8")):
            if ref not in skill_names and ref != "skill-name":
                errors.append(f"{path.relative_to(root)}: dead skill reference ${ref}")

    try:
        lock = tomllib.loads((root / "UPSTREAM.lock").read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"invalid UPSTREAM.lock: {exc}")
        lock = {}
    locked_skills = set(lock.get("skills", {}))
    if locked_skills != skill_names:
        errors.append(f"UPSTREAM.lock skill map mismatch: missing={sorted(skill_names - locked_skills)} extra={sorted(locked_skills - skill_names)}")

    required = [
        root / "LICENSE",
        root / "licenses/MIT-mattpocock.txt",
        root / "THIRD_PARTY_NOTICES.md",
        root / "templates/project/AGENTS.md",
        root / "skills/vibe-init/scripts/vibe_init.py",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(root)}")

    mirrors = {
        "AGENTS.md": "AGENTS.md",
        "docs/agents/domain.md": "docs/agents/domain.md",
        "docs/agents/issue-tracker.md": "docs/agents/issue-tracker.md",
        "docs/agents/triage-labels.md": "docs/agents/triage-labels.md",
    }
    for template_rel, asset_rel in mirrors.items():
        template = root / "templates/project" / template_rel
        asset = root / "skills/vibe-init/assets/project" / asset_rel
        if template.exists() and asset.exists() and template.read_bytes() != asset.read_bytes():
            errors.append(f"initializer asset drift: {asset.relative_to(root)}")

    if (root / ".codex/skills").exists():
        errors.append("repository must not use .codex/skills")
    errors.extend(portability_errors(root))
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: validated {len(list((root / 'skills').glob('*/SKILL.md')))} skills and project templates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
