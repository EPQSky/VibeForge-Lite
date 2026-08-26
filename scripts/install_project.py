#!/usr/bin/env python3
"""Install VibeForge Lite into a target project using the canonical initializer."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    initializer = Path(__file__).resolve().parents[1] / "skills/vibe-init/scripts/vibe_init.py"
    runpy.run_path(str(initializer), run_name="__main__")
