"""Part 4: score all agent runs and write results.csv."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results" / "runs"
BASELINE = ROOT / "results" / "baseline_tests.txt"
COND_A = ROOT / "experiment" / "cond-A"
COND_B = ROOT / "experiment" / "cond-B"
GIT = Path(r"C:\Program Files\Git\cmd\git.exe")
VENV_PY = ROOT / ".venv_eval" / "Scripts" / "python.exe"
EVAL_ROOT = Path(r"C:\Users\anilk\autose_eval")

RUN_ORDER = [
    "T1-A-1", "T1-B-1", "T1-A-2", "T1-B-2",
    "T2-A-1", "T2-B-1", "T2-A-2", "T2-B-2",
    "T3-A-1", "T3-B-1", "T3-A-2", "T3-B-2",
]

CORE_PIPELINE = {
    "markdown/core.py",
    "markdown/blockparser.py",
    "markdown/blockprocessors.py",
    "markdown/inlinepatterns.py",
    "markdown/treeprocessors.py",
    "markdown/preprocessors.py",
    "markdown/postprocessors.py",
    "markdown/serializers.py",
    "markdown/util.py",
}

TOOL_NAMES = {"Read", "Write", "StrReplace", "Shell", "Grep", "Glob"}
ACCEPTANCE_MODULES = {
    "T1": "experiment.acceptance_tests.test_T1",
    "T2": "experiment.acceptance_tests.test_T2",
    "T3": "experiment.acceptance_tests.test_T3",
}


def on_rm_error(func, path, exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def parse_run_id(run_id: str) -> tuple[str, str, int]:
    task, rest = run_id.split("-", 1)
    condition, trial_s = rest.split("-", 1)
    return task, condition, int(trial_s)


def parse_baseline_ok(path: Path) -> set[str]:
    ok: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        m = re.search(r"\(([^)]+)\) \.\.\. ok$", line)
        if m:
            ok.add(m.group(1))
    return ok


def parse_unittest_status(output: str) -> dict[str, str]:
    status: dict[str, str] = {}
    for line in output.splitlines():
        m = re.search(r"\(([^)]+)\) \.\.\. (ok|FAIL|ERROR|skipped)$", line)
        if m:
            status[m.group(1)] = m.group(2)
    return status


def read_patch(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.decode("utf-8", errors="replace")


def patch_changed_files(patch: str) -> list[str]:
    return re.findall(r"^diff --git a/(.+?) b/", patch, re.MULTILINE)


def patch_has_effective_change(patch: str) -> bool:
    if not patch.strip():
        return False
    if not patch_changed_files(patch):
        return False
    return bool(re.search(r"^\+(?!\+\+)", patch, re.MULTILINE))


def parse_log_metrics(log_path: Path) -> tuple[float, int, str]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    header_started = header_saved = None
    for line in text.splitlines()[:30]:
        if line.startswith("started:"):
            header_started = line.split(":", 1)[1].strip()
        if line.startswith("saved:"):
            header_saved = line.split(":", 1)[1].strip()

    transcript = text.split("--- transcript ---", 1)
    jsonl = transcript[1] if len(transcript) > 1 else ""
    tool_calls = 0
    tokens = ""
    first_ts = last_ts = None
    ts_re = re.compile(
        r"<timestamp>([^<]+)</timestamp>|"
        r'"timestamp":"([^"]+)"'
    )
    for line in jsonl.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "turn_ended":
            continue
        content = obj.get("message", {}).get("content", [])
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "tool_use":
                    name = item.get("name", "")
                    if name in TOOL_NAMES:
                        tool_calls += 1
                elif item.get("type") == "text":
                    for m in ts_re.finditer(item.get("text", "")):
                        t = m.group(1) or m.group(2)
                        if t:
                            if first_ts is None:
                                first_ts = t
                            last_ts = t

    time_min = 0.0
    if first_ts and last_ts:
        try:
            t0 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            time_min = max(0.0, (t1 - t0).total_seconds() / 60.0)
        except ValueError:
            pass
    if time_min == 0.0 and header_started and header_saved:
        try:
            t0 = datetime.fromisoformat(header_started)
            t1 = datetime.fromisoformat(header_saved)
            time_min = max(0.0, (t1 - t0).total_seconds() / 60.0)
        except ValueError:
            pass
    return round(time_min, 1), tool_calls, tokens


def design_fit(task: str, patch: str) -> int:
    if not patch_has_effective_change(patch):
        return 0
    files = patch_changed_files(patch)
    src_files = [f for f in files if f.startswith("markdown/")]
    test_files = [f for f in files if f.startswith("tests/")]
    score = 0

    if task == "T1":
        added = "\n".join(
            ln[1:] for ln in patch.splitlines() if ln.startswith("+") and not ln.startswith("+++")
        )
        if "markdown/extensions/toc.py" in files:
            if re.search(
                r"el\.attrib\[\"id\"\]\s*=\s*unique\(\s*slug",
                added,
            ) or re.search(
                r"el\.attrib\[\"id\"\]\s*=\s*unique\(\s*self\.slugify",
                added,
            ):
                if 'el.attrib["id"] = slug' not in added:
                    score += 1
        bad_src = [
            f for f in src_files
            if f != "markdown/extensions/toc.py"
        ]
        if not bad_src:
            score += 1
        if test_files and re.search(
            r"test.*[Ee]mpty|!!!|\?_1|empty.*slug", patch, re.I
        ):
            score += 1
        elif test_files and "test_toc.py" in "".join(test_files):
            if "EmptySlug" in patch or "_1" in patch:
                score += 1

    elif task == "T2":
        if src_files and all(f == "markdown/extensions/admonition.py" for f in src_files):
            score += 1
        if "AdmonitionProcessor" in patch and "details" in patch:
            if "register(" not in patch or "AdmonitionProcessor" in patch:
                score += 1
        if ("details" in patch and "summary" in patch and
                ("'div', 'details'" in patch or '("div", "details")' in patch or
                 "('div', 'details')" in patch)):
            score += 1

    elif task == "T3":
        if "markdown/extensions/tasklist.py" in files:
            if "TaskListExtension" in patch and "makeExtension" in patch:
                if "self.config" in patch:
                    score += 1
        if "pyproject.toml" in files and "tasklist" in patch:
            if "markdown/core.py" not in files:
                score += 1
        has_processor = any(
            x in patch for x in (
                "treeprocessors.register",
                "blockprocessors.register",
                "inlinePatterns.register",
                "Treeprocessor",
                "BlockProcessor",
            )
        )
        core_touched = any(f in CORE_PIPELINE for f in files)
        if has_processor and not core_touched:
            score += 1

    return min(score, 3)


def git_run(cwd: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    e = os.environ.copy()
    e.setdefault("GIT_AUTHOR_NAME", "eval")
    e.setdefault("GIT_AUTHOR_EMAIL", "eval@local")
    e.setdefault("GIT_COMMITTER_NAME", "eval")
    e.setdefault("GIT_COMMITTER_EMAIL", "eval@local")
    if env:
        e.update(env)
    return subprocess.run(
        [str(GIT), *args],
        cwd=cwd,
        env=e,
        capture_output=True,
        text=True,
    )


def ensure_venv() -> Path:
    if not VENV_PY.exists():
        subprocess.run(
            [sys.executable, "-m", "venv", str(ROOT / ".venv_eval")],
            check=True,
            cwd=ROOT,
        )
        subprocess.run(
            [str(VENV_PY), "-m", "pip", "install", "-q", "-U", "pip"],
            check=True,
            cwd=ROOT,
        )
    return VENV_PY


@dataclass
class RunScore:
    run_id: str
    task: str
    condition: str
    trial: int
    outcome: str
    acceptance_passed: int
    acceptance_total: int
    regressions: int
    design_fit: int
    time_min: float
    tool_calls: int
    tokens: str


def rebuild_tree(run_id: str, condition: str) -> tuple[Path | None, bool]:
    src = COND_A if condition == "A" else COND_B
    dest = EVAL_ROOT / run_id
    if dest.exists():
        shutil.rmtree(dest, onerror=on_rm_error)
    EVAL_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        src, dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    git_run(dest, "init", "-q")
    git_run(dest, "add", "-A")
    r = git_run(dest, "commit", "-q", "-m", "initial")
    if r.returncode != 0 and "nothing to commit" not in (r.stderr or ""):
        return None, False

    patch_path = RUNS / run_id / "diff.patch"
    patch = read_patch(patch_path)
    if not patch_has_effective_change(patch):
        return dest, False

    patch_file = dest / "_agent.patch"
    patch_file.write_text(patch, encoding="utf-8", newline="\n")
    apply = git_run(dest, "apply", "--whitespace=nowarn", str(patch_file))
    patch_file.unlink(missing_ok=True)
    return dest, apply.returncode == 0


def run_tests(py: Path, tree: Path, task: str) -> tuple[int, int, str, int]:
    subprocess.run(
        [str(py), "-m", "pip", "install", "-q", "-e", f"{tree}[testing]"],
        cwd=ROOT,
        check=True,
    )
    acc_mod = ACCEPTANCE_MODULES[task]
    acc = subprocess.run(
        [str(py), "-m", "unittest", acc_mod, "-v"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    acc_out = (acc.stdout or "") + (acc.stderr or "")
    acc_status = parse_unittest_status(acc_out)
    acc_passed = sum(1 for v in acc_status.values() if v == "ok")
    acc_failed = sum(1 for v in acc_status.values() if v in ("FAIL", "ERROR"))

    suite = subprocess.run(
        [str(py), "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=tree,
        capture_output=True,
        text=True,
    )
    suite_out = (suite.stdout or "") + (suite.stderr or "")
    return acc_passed, acc_failed, suite_out, acc.returncode


def outcome_from(acc_passed: int, acc_total: int, effective: bool) -> str:
    if not effective:
        return "Failed"
    if acc_passed >= acc_total:
        return "Complete"
    if acc_passed > 0:
        return "Partial"
    return "Failed"


def score_run(
    run_id: str,
    baseline_ok: set[str],
    py: Path,
) -> RunScore:
    task, condition, trial = parse_run_id(run_id)
    log_path = RUNS / run_id / "log.txt"
    time_min, tool_calls, tokens = parse_log_metrics(log_path)
    patch = read_patch(RUNS / run_id / "diff.patch")
    fit = design_fit(task, patch)
    effective = patch_has_effective_change(patch)

    tree, apply_ok = rebuild_tree(run_id, condition)
    acc_total = 4
    acc_passed = 0
    regressions = 0
    suite_out = ""

    if tree and apply_ok and effective:
        try:
            acc_passed, acc_failed, suite_out, _ = run_tests(py, tree, task)
            acc_passed = min(acc_passed, acc_total)
            out_path = RUNS / run_id / "test_output.txt"
            header = (
                f"run_id: {run_id}\n"
                f"eval_tree: {tree}\n"
                f"acceptance_module: {ACCEPTANCE_MODULES[task]}\n"
                f"acceptance_passed: {acc_passed}/{acc_total}\n\n"
            )
            out_path.write_text(header + suite_out, encoding="utf-8")
            run_status = parse_unittest_status(suite_out)
            regressions = sum(
                1 for q in baseline_ok
                if run_status.get(q) in ("FAIL", "ERROR")
            )
        except subprocess.CalledProcessError as exc:
            suite_out = str(exc)
            (RUNS / run_id / "test_output.txt").write_text(
                f"install or test failed: {exc}\n", encoding="utf-8"
            )
    else:
        reason = "no effective change" if not effective else "patch apply failed"
        (RUNS / run_id / "test_output.txt").write_text(
            f"run_id: {run_id}\nnot executed: {reason}\n",
            encoding="utf-8",
        )

    if tree and tree.exists():
        shutil.rmtree(tree, onerror=on_rm_error)

    outcome = outcome_from(acc_passed, acc_total, effective and apply_ok)

    return RunScore(
        run_id=run_id,
        task=task,
        condition=condition,
        trial=trial,
        outcome=outcome,
        acceptance_passed=acc_passed if (effective and apply_ok) else 0,
        acceptance_total=acc_total,
        regressions=regressions,
        design_fit=fit,
        time_min=time_min,
        tool_calls=tool_calls,
        tokens=tokens,
    )


def write_csv(rows: list[RunScore]) -> None:
    path = ROOT / "results" / "results.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "run_id", "task", "condition", "trial", "outcome",
            "acceptance_passed", "acceptance_total", "regressions",
            "design_fit", "time_min", "tool_calls", "tokens",
        ])
        for r in rows:
            w.writerow([
                r.run_id, r.task, r.condition, r.trial, r.outcome,
                r.acceptance_passed, r.acceptance_total, r.regressions,
                r.design_fit, r.time_min, r.tool_calls, r.tokens,
            ])


def write_qualitative(rows: list[RunScore]) -> None:
    by_id = {r.run_id: r for r in rows}
    complete = [r for r in rows if r.outcome == "Complete"]
    failed = [r for r in rows if r.outcome == "Failed"]
    good = None
    bad = None
    for g in complete:
        for b in failed:
            if g.task == b.task and g.condition != b.condition:
                good, bad = g, b
                break
        if good:
            break
    if not good and complete:
        good = complete[0]
    if not bad and failed:
        bad = failed[0]
    if not bad:
        bad = min(rows, key=lambda r: (r.acceptance_passed, r.design_fit))

    def excerpt(run_id: str, limit: int = 3) -> str:
        log = (RUNS / run_id / "log.txt").read_text(encoding="utf-8", errors="replace")
        part = log.split("--- transcript ---", 1)[-1]
        quotes = []
        for line in part.splitlines()[:40]:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            for item in obj.get("message", {}).get("content", []):
                if item.get("type") == "text":
                    t = item.get("text", "").strip()
                    if t and not t.startswith("<"):
                        quotes.append(t[:200])
                        if len(quotes) >= limit:
                            return " / ".join(quotes)
        return quotes[0] if quotes else "(see log.txt)"

    lines = [
        "# Qualitative notes (Part 4)\n",
        "Two runs for the Part 5 report: one that went well and one that went badly, "
        "from different conditions where possible.\n",
    ]
    if good:
        r = by_id[good.run_id]
        arch = (
            " Condition B included ARCHITECTURE.md; check the log for whether the agent "
            "read it before editing."
            if r.condition == "B" else ""
        )
        lines.append(
            f"\n## Strong run: `{good.run_id}` ({r.outcome}, "
            f"{r.acceptance_passed}/{r.acceptance_total} acceptance, "
            f"design_fit {r.design_fit})\n\n"
            f"The agent finished with outcome **{r.outcome}** on task {r.task}.{arch} "
            f"Early transcript: {excerpt(good.run_id)}. "
            f"The saved diff is under `results/runs/{good.run_id}/diff.patch`; "
            f"`test_output.txt` records the full unittest discover run after install.\n"
        )
    if bad:
        r = by_id[bad.run_id]
        lines.append(
            f"\n## Weak run: `{bad.run_id}` ({r.outcome}, "
            f"{r.acceptance_passed}/{r.acceptance_total} acceptance, "
            f"design_fit {r.design_fit}, regressions {r.regressions})\n\n"
            f"The agent ended **{r.outcome}** on task {r.task} under condition "
            f"{r.condition}. Transcript excerpt: {excerpt(bad.run_id)}. "
            f"Design fit scored {r.design_fit}/3 from the diff alone "
            f"(see task design-fit checks in `experiment/tasks/{r.task}.md`). "
            f"Compare with the strong run on the same task to see whether "
            f"ARCHITECTURE.md changed module choice or registry usage.\n"
        )

    (ROOT / "results" / "qualitative_notes.md").write_text(
        "".join(lines), encoding="utf-8"
    )


def main() -> None:
    baseline_ok = parse_baseline_ok(BASELINE)
    print(f"baseline ok tests: {len(baseline_ok)}")
    py = ensure_venv()
    rows: list[RunScore] = []
    for run_id in RUN_ORDER:
        print(f"scoring {run_id}...", flush=True)
        rows.append(score_run(run_id, baseline_ok, py))
        r = rows[-1]
        print(
            f"  {r.outcome} acc={r.acceptance_passed}/{r.acceptance_total} "
            f"reg={r.regressions} fit={r.design_fit} time={r.time_min} tools={r.tool_calls}",
            flush=True,
        )
    write_csv(rows)
    write_qualitative(rows)
    print("wrote results/results.csv and results/qualitative_notes.md")


if __name__ == "__main__":
    main()
