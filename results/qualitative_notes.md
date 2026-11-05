# Qualitative notes (Part 4)

Two runs for the Part 5 report: one strong and one weak, from different conditions.

## Strong run: `T2-B-2` (Complete, 4/4 acceptance, design_fit 3)

The agent opened with: “I'll start by reading the architecture notes in the sandbox, then implement collapsible admonitions without changing the existing `!!!` behavior.” It read `ARCHITECTURE.md` in the sandbox, then went straight to `markdown/extensions/admonition.py` and the existing admonition tests rather than adding a new pipeline stage. The diff extends `AdmonitionProcessor` only: the marker regex accepts `???`, collapsible blocks use `<details>` / `<summary class="admonition-title">`, and sibling continuation treats `details` like `div`. The architecture document appears to have helped here by reinforcing the extension-only pattern (block processor on `md.blockprocessors`, no core edits). All four hidden acceptance tests passed with zero regressions on the baseline suite.

## Weak run: `T3-A-1` (Complete, 4/4 acceptance, design_fit 1)

Without `ARCHITECTURE.md`, the agent still found `tasklist.py`, `makeExtension`, and the `pyproject.toml` entry point, but when `extensions=['tasklist']` failed before reinstall it patched `markdown/core.py` with a built-in short-name fallback. That made the hidden tests pass after editable install, yet it violates the design-fit rule that built-ins register through entry points and `makeExtension`, not a special case in core. The log shows the pivot explicitly: after `python -c "… extensions=['tasklist']"` failed, the next edit is a `StrReplace` on `build_extension` in `core.py`. Functionally the run is **Complete** on acceptance, but architecturally it is the weakest T3 run (design_fit 1/3). Contrast with condition B runs on T3, which also scored 1/3 on design fit in this batch—suggesting the cross-component task pushed agents toward core shortcuts even when they read the architecture doc.
