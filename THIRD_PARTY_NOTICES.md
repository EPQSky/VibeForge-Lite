# Third-Party Notices

## mattpocock/skills

Parts of `skills/` are derived from the `mattpocock/skills` repository. The main imported snapshot is commit `9c32629965586e75a9d2206922dccec91e19f2f2`; `batch-grill-me` is traced to commit `9603c1cc8118d08bc1b3bf34cf714f62178dea3b`.

Copyright (c) 2026 Matt Pocock

Licensed under the MIT License. The complete upstream license is preserved at `licenses/MIT-mattpocock.txt`; imported paths, local names, and modifications are recorded in `UPSTREAM.lock`.

`batch-grill-with-docs`, `vibe-guide`, and the executable `vibe-init` behavior are maintained by this project. All vendored skills include local Codex compatibility changes and are not presented as unmodified upstream copies. Local adaptations also make code review cover the full working tree, add explicit trust boundaries for external tracker content, constrain spec synthesis to one testing-seam confirmation, keep parent specs out of implementation-ready state, and let TDD reuse seams already approved in a spec or ticket.

## OpenAI Codex Plugin validator

CI downloads the Plugin validator and its identifier helper from a fixed commit of the OpenAI `codex` repository and executes them without redistributing them in this project's Plugin archive. The repository, commit, and paths are recorded in `UPSTREAM.lock`; the upstream project is licensed under Apache-2.0.
