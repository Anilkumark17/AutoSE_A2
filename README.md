# AutoSE Assignment 2

Does an architecture document change how a coding agent carries out a bug fix, a local feature, and a cross-component change?

- **Repository:** https://github.com/Python-Markdown/markdown.git
- **Commit:** `b41e0aaf1181f1a8cb200cf5a815aad7c0020d23` (tag `3.11.2`, package 3.11.2)
- **Agent / model:** Cursor subagent (`generalPurpose`), Grok 4.7 per run — see [`experiment/config.md`](experiment/config.md)

## Layout

```text
README.md                 this file
report.pdf                full study report (Part 5)
ARCHITECTURE.md           given only to condition B sandboxes
experiment/
  config.md               agent, model, prompt, run record
  removed_files.txt       paths deleted from upstream
  tasks/T1.md T2.md T3.md spec + design-fit checks (not sent verbatim to agent)
  acceptance_tests/       hidden tests (never copied into a sandbox)
  cond-A/ cond-B/         prepared trees (local replay; not required in submission zip)
  score_runs.py           Part 4 scorer
results/
  results.csv             twelve scored runs
  baseline_tests.txt      verbose baseline before T1 bug injection
  qualitative_notes.md    two runs for the report narrative
  runs/<run_id>/          log.txt, diff.patch, test_output.txt
```

## Baseline

Prepared tree before the T1 bug: **1077 passed, 0 failed, 52 skipped** (1129 tests). After injection the shipped unittest suite still passes; the bug is only caught by `acceptance_tests/test_T1.py`.

## How to rerun one task

Example: T2, condition B.

1. Copy `experiment/cond-B` to an empty sandbox outside this folder. Do not copy `acceptance_tests/` or `tasks/`.
2. `python -m venv .venv` and `.venv\Scripts\python -m pip install -e ".[testing]"` inside the sandbox.
3. New Cursor agent (Grok 4.7): paste the fenced spec from `experiment/tasks/T2.md`, then the closing line from `experiment/config.md`, and for B add “Read ARCHITECTURE.md before you start.”
4. Save transcript as `results/runs/<run_id>/log.txt` and staged diff as `diff.patch`.

## How to rescore runs

From this directory:

```powershell
python -m venv .venv_eval
.venv_eval\Scripts\python -m pip install -e ".[testing]" fpdf2
.venv_eval\Scripts\python experiment/score_runs.py
.venv_eval\Scripts\python experiment/write_report_part5.py
```
