# Experiment configuration

Every run uses the settings below, unchanged. Phase 1 prepared the repository.
Part 3 executes the twelve runs.

## Repository

- Python-Markdown, https://github.com/Python-Markdown/markdown.git
- Tag `3.11.2`, commit `b41e0aaf1181f1a8cb200cf5a815aad7c0020d23` (2026-10, "Bump version to 3.11.2"). Package version 3.11.2.
- Prepared as described in `removed_files.txt` (design docs removed, README reduced to usage). The T1 bug is then injected into both copies.
- `experiment/cond-A/` is the prepared code. `experiment/cond-B/` is the same tree plus `ARCHITECTURE.md`. Nothing else differs.

## Agent

| Setting | Value |
|---|---|
| Agent | Cursor subagent, type `generalPurpose`, one fresh agent per run |
| Model | Grok 4.7 (parent session model, `inherit`; Cursor does not expose a separate temperature or effort control) |
| Sampling | Provider default. The same for every run. |
| Machine | Windows 11 Home 10.0.26200, Python 3.12.10, Git 2.50.1 at `C:\Program Files\Git\cmd\git.exe` |
| Tools | Read, search, edit, and shell inside the sandbox. No web. |
| Sandbox root | `C:\Users\anilk\autose_sandboxes\<run_id>` which is outside `RollNo_AutoSE_A2`, so the agent cannot open `tasks/` or `acceptance_tests/`. |
| Isolation | Copy of `cond-A` or `cond-B`, then `git init` and one commit. The subagent tool has no working-directory parameter, so the prompt starts with one harness line naming that sandbox and forbidding any other path. The task text after that line is identical across runs of the same task. |
| Time limit | 30 minutes |

## Prompt template

Every prompt starts with the same harness line, with only the run directory filled in:

```text
Work only in C:\Users\anilk\autose_sandboxes\<run_id>. Do not read or write any other path.
```

Then the fenced spec in `experiment/tasks/Tn.md`, copied verbatim, then this line:

```text
When you are done, make sure the existing tests still pass.
```

Condition B adds one more line at the end:

```text
Read ARCHITECTURE.md before you start.
```

The "Injected bug" and "Design-fit" sections are never sent. No hints and no corrections. If the agent asks a question, the only reply is "Use your best judgement."

## Run record

Twelve runs were saved, in order: `T1-A-1`, `T1-B-1`, `T1-A-2`, `T1-B-2`, `T2-A-1`, `T2-B-1`, `T2-A-2`, `T2-B-2`, `T3-A-1`, `T3-B-1`, `T3-A-2`, `T3-B-2`. Each sandbox was deleted after `log.txt` and `diff.patch` were written. The agent's edits were not committed and were not corrected. `results.csv` was not filled in.

`T1-A-1` was repeated. The first attempt, started at 14:05, opened `experiment/tasks/T1.md` and `experiment/acceptance_tests/test_T1.py` outside its sandbox. That attempt was discarded and is not the saved run. The saved `T1-A-1` is the repeat, started at 14:11. For that repeat and every later run, `experiment/`, `ARCHITECTURE.md`, `README.md`, `report.pdf`, and `system-architecture.html` were moved out of the workspace to `C:\Users\anilk\autose_hold` and restored only after `T3-B-2` was saved, so a run could not open the task notes or the hidden tests. No later run read those files. No run was repeated for an API or network failure.

## How a run is scored

Part 4 replays each saved `diff.patch` on a fresh copy of `cond-A` or `cond-B`, then installs and tests. The driver is [`experiment/score_runs.py`](score_runs.py):

```text
python experiment/score_runs.py
```

For each run it writes `results/runs/<run_id>/test_output.txt`, one row in `results/results.csv`, and `results/qualitative_notes.md`. Install that run's tree (`pip install -e ".[testing]"` from `.venv_eval`), run `python -m unittest discover tests`, and run the hidden file `experiment/acceptance_tests/test_Tn.py` against that install. Regressions are baseline tests that passed in `results/baseline_tests.txt` and no longer pass. Design fit is the three checks in the task file, scored from the diff.
