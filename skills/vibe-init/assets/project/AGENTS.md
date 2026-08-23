# Project Agent Guide

<!-- epq-vibecoding:start version=0.1.0 -->
## Vibecoding workflow

- Use `$vibe-guide` when the right workflow is unclear.
- Clarify unresolved product, domain, and architecture decisions with `$grill-with-docs`; use `$batch-grill-with-docs` when a batch round is preferred.
- Turn stable decisions into `.scratch/<feature>/spec.md` with `$to-spec`, then split multi-session work into vertical tickets with `$to-tickets`.
- Implement one approved slice at a time with `$implement`; use `$tdd` when a stable behavior seam exists. Do not commit unless the user or repository policy explicitly asks.
- Before completion, review from a fixed point with `$code-review <fixed-point>` along both Standards and Spec axes.
- Use `$handoff` when another task must continue the work.

Project artifacts use `CONTEXT.md` only for stable domain language, `docs/adr/` for durable decisions, `docs/agents/` for workflow conventions, and `.scratch/` for local specs and tickets.

Local implementation ticket states are `ready-for-agent`, `in-progress`, and `done`.
<!-- epq-vibecoding:end -->
