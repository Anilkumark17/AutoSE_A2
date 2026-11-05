"""Generate the Part 5 report.pdf (up to eight pages)."""

from __future__ import annotations

import csv
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "results" / "results.csv"
OUT = ROOT / "report.pdf"


def load_rows() -> list[dict[str, str]]:
    with CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize(rows: list[dict[str, str]], condition: str) -> dict[str, float]:
    sub = [r for r in rows if r["condition"] == condition]
    n = len(sub)
    complete = sum(1 for r in sub if r["outcome"] == "Complete")
    return {
        "runs": n,
        "complete_rate": 100.0 * complete / n if n else 0.0,
        "regressions": sum(float(r["regressions"]) for r in sub) / n if n else 0.0,
        "design_fit": sum(float(r["design_fit"]) for r in sub) / n if n else 0.0,
        "time_min": sum(float(r["time_min"]) for r in sub) / n if n else 0.0,
        "tool_calls": sum(float(r["tool_calls"]) for r in sub) / n if n else 0.0,
    }


class Report(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 8, f"AutoSE Assignment 2 | Python-Markdown 3.11.2 | Page {self.page_no()}", align="C")


def ascii_safe(text: str) -> str:
    return (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2026", "...")
    )


def body_text(pdf: FPDF, text: str, size: int = 10) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.multi_cell(0, 4.5, ascii_safe(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def heading(pdf: FPDF, title: str, level: int = 1) -> None:
    pdf.ln(2 if level == 1 else 1)
    pdf.set_font("Helvetica", "B", 14 if level == 1 else 12)
    pdf.multi_cell(0, 6, ascii_safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def main() -> None:
    rows = load_rows()
    sum_a = summarize(rows, "A")
    sum_b = summarize(rows, "B")

    pdf = Report()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    heading(pdf, "Does ARCHITECTURE.md Change How a Coding Agent Works?", 1)
    body_text(
        pdf,
        "This report compares two conditions on Python-Markdown 3.11.2: code only (A) "
        "versus the same code plus a two-page architecture document (B). Three tasks "
        "and two trials each yield twelve agent runs scored on acceptance tests, "
        "regressions, design fit, time, and tool use.",
        10,
    )

    heading(pdf, "1. Hypotheses", 2)
    body_text(
        pdf,
        "RQ1 (outcome). I expected condition B to show a higher complete rate on the "
        "cross-component task (T3), because the document names the Extension contract, "
        "entry points in pyproject.toml, and the rule that core must not import "
        "extensions. For T1 and T2 I expected both conditions to succeed often, since "
        "the bugs and features are local to one extension file.",
    )
    body_text(
        pdf,
        "RQ2 (quality). I expected B to produce fewer regressions and higher design-fit "
        "scores, especially on T3, where violating C2 or C3 is easy if the agent "
        "patches core.py instead of adding tasklist.py plus an entry point.",
    )
    body_text(
        pdf,
        "RQ3 (efficiency). I expected B to need fewer tool calls and less time on T2 "
        "and T3 because the overview diagram and ADR-2 shorten the search for where "
        "to register processors. I did not expect a large effect on T1 once the agent "
        "opens toc.py.",
    )

    heading(pdf, "2. Setup", 2)
    body_text(
        pdf,
        "Repository. Python-Markdown, https://github.com/Python-Markdown/markdown.git, "
        "tag 3.11.2, commit b41e0aaf1181f1a8cb200cf5a815aad7c0020d23. Ninety-one "
        "documentation paths were removed (experiment/removed_files.txt); the upstream "
        "README was replaced by a short install-and-test note. Baseline before the "
        "injected T1 bug: 1077 passed, 0 failed, 52 skipped (1129 tests run). "
        "experiment/cond-A is the prepared tree with the bug; cond-B adds ARCHITECTURE.md only.",
    )
    body_text(
        pdf,
        "Tasks. T1 (bug): empty heading ids in the toc extension must use the existing "
        "_1, _2 numbering. T2 (local feature): ??? admonitions as collapsible "
        "<details> blocks in admonition.py. T3 (cross-component): new built-in tasklist "
        "extension loadable as tasklist or markdown.extensions.tasklist. Each task has "
        "a 5–10 line spec sent to the agent, four hidden acceptance tests, and three "
        "design-fit checks (see experiment/tasks/Tn.md).",
    )
    body_text(
        pdf,
        "Agent and settings. Each run used a fresh Cursor generalPurpose subagent with "
        "model Grok 4.7 (inherit), provider-default sampling, 30-minute limit, and "
        "sandbox C:\\Users\\anilk\\autose_sandboxes\\<run_id> copied from cond-A or "
        "cond-B. The prompt is the fenced spec plus “When you are done, make sure the "
        "existing tests still pass.” Condition B adds “Read ARCHITECTURE.md before you "
        "start.” No hints. Part 4 replayed each diff.patch with pip install -e \".[testing]\".",
    )

    pdf.add_page()
    heading(pdf, "3. Architecture document", 2)
    body_text(
        pdf,
        "Production. The first draft was written in Cursor with Grok 4.7 while preparing "
        "the repository: an eight-row component table, mermaid pipeline diagram, three "
        "ADRs, and five constraints with file citations. There was no separate prompt "
        "file. A second pass on 5 November 2026 checked ten factual claims against "
        "experiment/cond-A; two were corrected (Extension import also in __init__.py; "
        "serializers.py does not import util.py). ADR-1 and ADR-2 are Verified from "
        "commits 6ee07d2 and cd73243; ADR-3 mechanism is Verified from HtmlStash "
        "docstring with Inferred alternatives. Total authoring time was roughly three "
        "hours including the claim check. Only cond-B receives the file.",
    )

    pdf.set_font("Helvetica", "B", 9)
    pdf.multi_cell(0, 4, "Ten claims checked against the code", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    claim_rows = [
        ["1", "Default output format is xhtml", "core.py:130", "Yes"],
        ["2", "Tree processors inline 20, prettify 10, unescape 0", "treeprocessors.py:42-44", "Yes"],
        ["3", "Block processor priorities 100 down to 10", "blockprocessors.py:45-55", "Yes"],
        ["4", "Higher Registry priority runs first", "util.py:377-379", "Yes"],
        ["5", "Extension load: entry point, module:Class, makeExtension", "core.py:208-214", "Yes"],
        ["6", "toc tree processor priority 5", "extensions/toc.py:492", "Yes"],
        ["7", "attr_list priority 8 before toc", "extensions/attr_list.py:215", "Yes"],
        ["8", "NormalizeWhitespace strips STX/ETX", "preprocessors.py:71", "Yes"],
        ["9", "Only core imports Extension", "__init__.py:46 too", "Fixed in C3"],
        ["10", "util imported everywhere", "serializers.py: no util", "Fixed in overview"],
    ]
    headings_style = FontFace(emphasis="BOLD", fill_color=(230, 236, 242))
    with pdf.table(
        headings_style=headings_style,
        col_widths=(8, 52, 38, 18),
        line_height=4.2,
        text_align=("CENTER", "LEFT", "LEFT", "CENTER"),
    ) as table:
        row = table.row()
        for h in ["#", "Claim", "File:line", "OK?"]:
            row.cell(h)
        for r in claim_rows:
            row = table.row()
            for c in r:
                row.cell(ascii_safe(c))

    pdf.add_page()
    heading(pdf, "4. Results", 2)
    body_text(
        pdf,
        "Table 1 lists all twelve runs. Every run reached Complete on the four hidden "
        "acceptance tests for its task, with zero regressions on the baseline unittest "
        "set (975 named tests matched from baseline_tests.txt). Design fit varied by "
        "task, not by condition.",
    )

    pdf.set_font("Helvetica", "B", 9)
    pdf.multi_cell(0, 4, "Table 1. Per-run scores", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    with pdf.table(
        headings_style=headings_style,
        col_widths=(24, 8, 8, 6, 16, 10, 8, 8, 10, 10, 10),
        line_height=4.0,
        text_align="CENTER",
    ) as table:
        hdr = table.row()
        for h in [
            "run_id", "task", "cond", "trial", "outcome", "acc", "reg",
            "fit", "time", "tools", "tok",
        ]:
            hdr.cell(h)
        for r in rows:
            row = table.row()
            row.cell(r["run_id"])
            row.cell(r["task"])
            row.cell(r["condition"])
            row.cell(r["trial"])
            row.cell(r["outcome"][:8])
            row.cell(f"{r['acceptance_passed']}/{r['acceptance_total']}")
            row.cell(r["regressions"])
            row.cell(r["design_fit"])
            row.cell(r["time_min"])
            row.cell(r["tool_calls"])
            row.cell(r["tokens"] or "-")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.multi_cell(0, 4, "Table 2. Summary by condition (mean over six runs)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    with pdf.table(
        headings_style=headings_style,
        col_widths=(18, 22, 22, 22, 22, 22),
        line_height=4.5,
        text_align="CENTER",
    ) as table:
        row = table.row()
        for h in ["Condition", "Complete rate", "Mean regressions", "Mean design fit", "Mean time (min)", "Mean tool calls"]:
            row.cell(h)
        for label, s in [("A (no doc)", sum_a), ("B (+ ARCHITECTURE.md)", sum_b)]:
            row = table.row()
            row.cell(label)
            row.cell(f"{s['complete_rate']:.0f}%")
            row.cell(f"{s['regressions']:.1f}")
            row.cell(f"{s['design_fit']:.2f}")
            row.cell(f"{s['time_min']:.1f}")
            row.cell(f"{s['tool_calls']:.0f}")

    body_text(
        pdf,
        "By task, mean design fit was 2.0 on T1 (missing regression test in most diffs), "
        "3.0 on T2, and 1.0 on T3 in both conditions. Mean time on T3 was about 16 min "
        "without the document and 15 min with it—within run-to-run noise.",
    )

    pdf.add_page()
    heading(pdf, "5. Analysis", 2)
    body_text(
        pdf,
        "RQ1. All twelve runs Complete on acceptance tests. The architecture document "
        "did not change the binary outcome in this sample: agents fixed T1, shipped T2, "
        "and passed T3 functionally in every trial. That does not mean the tasks were "
        "too easy overall—T3 still required a new module—but it does mean RQ1 cannot "
        "separate A from B on success rate here.",
    )
    body_text(
        pdf,
        "RQ2. Regressions were zero everywhere. Design fit differed by task: T2 runs "
        "scored 3/3 in both conditions; T1 scored 2/3 because agents fixed toc.py but "
        "usually omitted a dedicated regression test; T3 scored 1/3 in both conditions "
        "because every agent edited markdown/core.py to load the short name tasklist "
        "instead of relying on the pyproject.toml entry point alone—contrary to ADR-2 "
        "and constraint C3 even when B read ARCHITECTURE.md. The document did not "
        "prevent that shortcut.",
    )
    body_text(
        pdf,
        "RQ3. Mean tool calls were 53 (A) versus 52 (B); mean time 9.4 min versus 9.0 min. "
        "B was slightly faster on T1 and T3 trials but slower on T2-B-2 (62 tools, 9.0 min). "
        "With only two trials per cell, those differences are descriptive, not evidence "
        "that the document saves time.",
    )

    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 5, "Qualitative runs", new_x="LMARGIN", new_y="NEXT")
    body_text(
        pdf,
        "Strong run T2-B-2 (condition B). The agent stated it would read the architecture "
        "notes first, opened ARCHITECTURE.md, then edited only admonition.py—extending "
        "AdmonitionProcessor for ??? markers and treating <details> like <div> for "
        "indented continuations. The document aligned with the intended module boundary.",
    )
    body_text(
        pdf,
        "Weak run T3-A-1 (condition A). The agent created tasklist.py and the entry point, "
        "but when extensions=['tasklist'] failed before reinstall it patched build_extension "
        "in core.py. Acceptance tests passed after install; design fit was 1/3. The log "
        "shows the failure probe immediately followed by a core.py StrReplace. Condition B "
        "runs on T3 behaved the same on design fit, so reading ADRs did not stop the core "
        "shortcut in this study.",
    )

    heading(pdf, "6. Limitations", 2)
    body_text(
        pdf,
        "Only two trials per task and condition; all outcomes were Complete, so there is "
        "no variance to compare on RQ1. I authored the tasks, the hidden tests, and the "
        "architecture document, which may match Grok’s training priors. The agent is "
        "non-deterministic: T2-B-2 used 62 tool calls while T2-A-1 used 36 despite the "
        "same spec. Scoring used replayed diffs on Windows with one Python version. "
        "Condition C (overview-only ARCHITECTURE.md for T3) was not run. Token/cost "
        "columns are empty because subagent logs did not report usage.",
    )

    heading(pdf, "7. Conclusion", 2)
    body_text(
        pdf,
        "In these twelve runs, ARCHITECTURE.md did not measurably improve acceptance "
        "outcomes or design fit on the hardest task. It may have helped agents choose "
        "the right extension file on T2 when they actually read it, but it did not stop "
        "core.py edits on T3. Correct behaviour and architecturally correct change "
        "decouple when the agent can patch the loader. Fair comparison and scored diffs "
        "made that visible; the evidence supports “little difference on outcomes, limited "
        "effect on structure,” not “documentation always helps.”",
    )

    pdf.output(OUT)
    print(f"wrote {OUT} ({pdf.page_no()} pages)")


if __name__ == "__main__":
    main()
