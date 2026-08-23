#!/usr/bin/env python3
"""Dry-run-first initializer for the EPQ Vibecoding project template."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

TEMPLATE_VERSION = "0.1.0"
START_RE = re.compile(r"<!-- epq-vibecoding:start(?: version=[^ ]+)? -->")
END_MARKER = "<!-- epq-vibecoding:end -->"
STATE_PATH = Path(".vibecoding/state.json")


@dataclass
class Action:
    kind: str
    path: str
    reason: str
    content: str | None = None

    def public(self) -> dict[str, str]:
        return {"action": self.kind, "path": self.path, "reason": self.reason}


def sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def load_state(root: Path) -> dict:
    raw = read_text(root / STATE_PATH)
    if raw is None:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"_error": f"invalid JSON: {exc}"}
    if not isinstance(value, dict):
        return {"_error": "state root is not an object"}
    return value


def managed_template(asset_root: Path) -> str:
    full = (asset_root / "AGENTS.md").read_text(encoding="utf-8")
    start = START_RE.search(full)
    end = full.find(END_MARKER)
    if start is None or end < start.end():
        raise RuntimeError("template AGENTS.md has invalid managed markers")
    return full[start.start() : end + len(END_MARKER)]


def merge_agents(existing: str | None, block: str) -> tuple[str | None, str | None]:
    if existing is None:
        return f"# Project Agent Guide\n\n{block}\n", None
    starts = list(START_RE.finditer(existing))
    ends = [match.start() for match in re.finditer(re.escape(END_MARKER), existing)]
    if not starts and not ends:
        separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
        return f"{existing}{separator}{block}\n", None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0].end():
        return None, "managed markers are missing, duplicated, or out of order"
    end = ends[0] + len(END_MARKER)
    return f"{existing[:starts[0].start()]}{block}{existing[end:]}", None


def plan(root: Path, asset_root: Path, tracker: str) -> tuple[list[Action], dict]:
    actions: list[Action] = []
    state = load_state(root)
    if "_error" in state:
        actions.append(Action("conflict", str(STATE_PATH), state["_error"]))
        prior_hashes: dict[str, str] = {}
    else:
        prior_hashes = state.get("managed_files", {}) if isinstance(state.get("managed_files", {}), dict) else {}

    block = managed_template(asset_root)
    agents_path = root / "AGENTS.md"
    existing_agents = read_text(agents_path)
    merged, error = merge_agents(existing_agents, block)
    if error:
        actions.append(Action("conflict", "AGENTS.md", error))
    elif merged == existing_agents:
        actions.append(Action("leave unchanged", "AGENTS.md", "managed block is current"))
    else:
        kind = "create" if existing_agents is None else "update managed block"
        actions.append(Action(kind, "AGENTS.md", "install the versioned workflow block", merged))

    doc_assets = {
        "docs/agents/domain.md": "docs/agents/domain.md",
        "docs/agents/issue-tracker.md": f"docs/agents/issue-tracker-{tracker}.md" if tracker != "local" else "docs/agents/issue-tracker.md",
        "docs/agents/triage-labels.md": "docs/agents/triage-labels.md",
    }
    for rel, asset_rel in doc_assets.items():
        asset = asset_root / asset_rel
        if not asset.exists():
            actions.append(Action("conflict", rel, f"tracker template is unavailable: {tracker}"))
            continue
        desired = asset.read_text(encoding="utf-8")
        current = read_text(root / rel)
        if current is None:
            actions.append(Action("create", rel, "install project workflow documentation", desired))
        elif current == desired:
            actions.append(Action("leave unchanged", rel, "content is current"))
        elif prior_hashes.get(rel) == sha256(current):
            actions.append(Action("migrate", rel, "update an unmodified managed file", desired))
        else:
            actions.append(Action("conflict", rel, "existing content is user-authored or changed since initialization"))

    for rel in (".scratch/.gitkeep", "docs/adr/.gitkeep"):
        if (root / rel).exists():
            actions.append(Action("leave unchanged", rel, "path already exists"))
        else:
            actions.append(Action("create", rel, "materialize the local workflow directory", ""))

    scans = {
        ".codex/skills": "legacy project skill path; migrate deliberately to .agents/skills",
        ".agents/skills": "project-local skills detected; Plugin skills will not be duplicated",
        "CLAUDE.md": "another agent's instructions detected; left untouched",
    }
    for rel, reason in scans.items():
        if (root / rel).exists():
            actions.append(Action("leave unchanged", rel, reason))

    next_hashes = dict(prior_hashes)
    for action in actions:
        if action.content is not None and action.path.startswith("docs/agents/"):
            next_hashes[action.path] = sha256(action.content)
        elif action.kind == "leave unchanged" and action.path.startswith("docs/agents/"):
            current = read_text(root / action.path)
            if current is not None:
                next_hashes[action.path] = sha256(current)

    next_state = {
        "schema_version": 1,
        "template_version": TEMPLATE_VERSION,
        "tracker": tracker,
        "managed_files": dict(sorted(next_hashes.items())),
    }
    desired_state = json.dumps(next_state, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    current_state = read_text(root / STATE_PATH)
    if any(action.kind == "conflict" for action in actions):
        if not any(action.path == str(STATE_PATH) and action.kind == "conflict" for action in actions):
            actions.append(Action("conflict", str(STATE_PATH), "state is not updated while unresolved conflicts remain"))
    elif current_state == desired_state:
        actions.append(Action("leave unchanged", str(STATE_PATH), "template state is current"))
    else:
        kind = "create" if current_state is None else "migrate"
        actions.append(Action(kind, str(STATE_PATH), "record applied template version and managed hashes", desired_state))
    return actions, next_state


def apply_actions(root: Path, actions: list[Action]) -> int:
    conflicts = [action for action in actions if action.kind == "conflict"]
    if conflicts:
        return 2
    for action in actions:
        if action.content is not None and action.kind in {"create", "migrate", "update managed block"}:
            atomic_write(root / action.path, action.content)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.cwd(), help="target repository (default: current directory)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="apply a conflict-free plan")
    mode.add_argument("--dry-run", action="store_true", help="show the plan without writing (default)")
    parser.add_argument("--tracker", choices=("local", "github", "gitlab"), default="local")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.target.expanduser().resolve()
    if not root.is_dir():
        print(f"target is not a directory: {root}", file=sys.stderr)
        return 2
    asset_root = Path(__file__).resolve().parents[1] / "assets" / "project"
    actions, state = plan(root, asset_root, args.tracker)
    exit_code = apply_actions(root, actions) if args.apply else (2 if any(a.kind == "conflict" for a in actions) else 0)
    payload = {
        "mode": "apply" if args.apply else "dry-run",
        "target": str(root),
        "template_version": TEMPLATE_VERSION,
        "actions": [action.public() for action in actions],
        "state": state,
        "exit_code": exit_code,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"EPQ Vibecoding {TEMPLATE_VERSION} {payload['mode']}: {root}")
        for action in actions:
            print(f"- {action.kind:20} {action.path}: {action.reason}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
