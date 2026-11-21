#!/usr/bin/env python3
"""Mechanical checks on a building-backend-services document set.

Usage:
  python3 check_docs.py [docs-dir]          the self-check (default docs-dir: docs/backend-design)
  python3 check_docs.py --gate [docs-dir]   before presenting a gate or a stop: adds the git checks,
                                            then names the shape to present in

Prints one line per finding (path:line: message) and exits 1 when there is any.
With --gate and no finding, prints the shape of the message this gate presents.
Standard library only; the git checks run when docs-dir is inside a git repository.
What it cannot judge (whether a change needs approval, whether a decision is
sound) stays with the author and the agent review.
"""
import re
import subprocess
import sys
from pathlib import Path

STEP_DOCS = {"requirements.md", "data-design.md", "architecture-design.md", "stack-selection.md"}
STATUS_RE = re.compile(
    r"^Status: (?:(?:DRAFT|REVIEWED) · \d{4}-\d{2}-\d{2}"
    r"|APPROVED · \d{4}-\d{2}-\d{2} · approved by [^·]+)$"
)
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
STATUS_WORD_RE = re.compile(r"\b(?:APPROVED|REVIEWED|DRAFT)\b")
OI_RE = re.compile(r"\bOI-\d+\b")
OI_COLUMNS = ["Id", "Question", "Raised in", "Blocks", "Decide by", "Owner",
              "Recommendation", "Assumption in force"]
MODES = {"gated", "auto until design done", "auto until feature done", "auto until done"}
STATE_RE = re.compile(
    r"^(?:later|to do|in design|awaiting approval|design approved|building|built|parked \(OI-\d+\))$"
)

findings = []


def report(path, line, message):
    findings.append(f"{path}:{line}: {message}")


def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def check_header(path):
    lines = path.read_text().splitlines()
    head = {}
    for n, line in enumerate(lines[:8], 1):
        for key in ("Status:", "Form:", "Builds on:"):
            if line.startswith(key):
                head[key] = (n, line)
    for key in ("Status:", "Form:", "Builds on:"):
        if key not in head:
            report(path, 1, f"header has no '{key}' line (documents.md, Header)")
    if "Status:" in head:
        n, line = head["Status:"]
        if not STATUS_RE.match(line):
            report(path, n, "Status line holds one value and its stamp, nothing else: "
                            "'Status: DRAFT|REVIEWED · <date>' or 'Status: APPROVED · <date> · approved by <name>'")
    if "Form:" in head:
        n, line = head["Form:"]
        if line.strip() not in ("Form: design", "Form: built"):
            report(path, n, "Form is 'design' or 'built'")
    if "Builds on:" in head:
        n, line = head["Builds on:"]
        if DATE_RE.search(line) or STATUS_WORD_RE.search(line) or OI_RE.search(line):
            report(path, n, "Builds on names documents and ids only — no status, date or open-item id")


def check_open_items(path):
    """Returns the ids of the open items."""
    ids, header_seen, blocking_done = set(), False, False
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.startswith("|"):
            continue
        row = cells(line)
        if not header_seen:
            header_seen = True
            if row != OI_COLUMNS:
                report(path, n, "columns are exactly: " + " | ".join(OI_COLUMNS))
            continue
        if set("".join(row)) <= set("-: "):
            continue
        if len(row) != len(OI_COLUMNS):
            report(path, n, f"row has {len(row)} cells, not {len(OI_COLUMNS)}")
            continue
        if not OI_RE.fullmatch(row[0]):
            report(path, n, f"id '{row[0]}' is not OI-<n>")
        ids.add(row[0])
        if any("<br" in c for c in row) or re.search(r"\bUpdated?\b", line):
            report(path, n, "each cell is one line, with no dated updates (documents.md, open-items.md)")
        blocking = row[3].lower() != "no"
        read_plan = "read plan" in row[1].lower()
        if blocking and blocking_done and not read_plan:
            report(path, n, "rows are sorted by Blocks: blocking rows come before 'no'")
        if not blocking:
            blocking_done = True
    return ids


def check_plan(path):
    text = path.read_text()
    for key in ("Size:", "Run mode:", "Reviewer:"):
        if not re.search(rf"^{key} \S", text, re.M):
            report(path, 1, f"plan.md has no '{key}' line (documents.md, plan.md)")
    m = re.search(r"^Run mode: (.+)$", text, re.M)
    if m and m.group(1).strip() not in MODES:
        report(path, 1, "Run mode is one of: " + ", ".join(sorted(MODES)))
    header_seen = False
    for n, line in enumerate(text.splitlines(), 1):
        if not line.startswith("|"):
            continue
        row = cells(line)
        if not header_seen:
            header_seen = True
            if row[:1] != ["Chunk"] or row[-1:] != ["State"]:
                report(path, n, "chunk table columns: Chunk | Code | Covers | Depends on | State")
            continue
        if set("".join(row)) <= set("-: "):
            continue
        if not STATE_RE.match(row[-1]):
            report(path, n, f"state '{row[-1]}' is not one of the plan.md states")


def git(root, *args):
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return r.stdout if r.returncode == 0 else None


def head_line(path, key):
    return next((l for l in path.read_text().splitlines()[:8] if l.startswith(key)), "")


def check_git(docs, step_docs, gate):
    """Returns the step documents that are, or once were, APPROVED."""
    approved = {p for p in step_docs if head_line(p, "Status:").startswith("Status: APPROVED")}
    if git(docs, "rev-parse", "HEAD") is None:
        if gate:
            report(docs, 0, "not in a git repository with a commit: commit the work on a local branch")
        return approved
    for path in step_docs:
        ever = git(docs, "log", "--format=%h", "-G", "^Status: APPROVED", "--", str(path.resolve()))
        if ever and ever.strip() and path not in approved:
            report(path, 1, "this document was APPROVED: an edit keeps its Status line "
                            "(documents.md, Changes since an approval)")
            approved.add(path)
    if not gate:
        return approved
    for path in step_docs:
        if head_line(path, "Status:").startswith("Status: DRAFT"):
            report(path, 1, "a gate presents reviewed documents: Status reads REVIEWED once the "
                            "review's fixes are re-verified (SKILL.md, cycle step 3)")
    branch = (git(docs, "branch", "--show-current") or "").strip()
    if branch in ("main", "master", ""):
        report(docs, 0, f"on '{branch or 'a detached HEAD'}': every run — recording a ruling included — "
                        "commits on a local branch (backend/<service> or backend/<change-slug>)")
    dirty = git(docs, "status", "--porcelain", "--", str(docs.resolve()))
    if dirty and dirty.strip():
        report(docs, 0, "uncommitted changes: commit the phase's work, the review's result in the message")
    return approved


def template(heading):
    text = (Path(__file__).resolve().parent / "run-modes.md").read_text()
    section = text.split(heading, 1)[1]
    return re.search(r"```markdown\n(.*?)```", section, re.S).group(1).rstrip()


def print_shape(docs, step_docs, approved):
    """Names the shape of the message this gate presents."""
    plan = docs / "plan.md"
    m = re.search(r"^Run mode: (.+)$", plan.read_text(), re.M) if plan.exists() else None
    mode = m.group(1).strip() if m else "gated"
    if mode.startswith("auto"):
        print(f"Run mode: {mode}. A gate before this mode's stop passes on its own: present nothing "
              "and go on to the next phase. At the stop, set each stopped chunk's plan.md state to "
              "'awaiting approval' (or 'parked (OI-n)'), commit, then present the stop's sitting "
              "(run-modes.md) in this shape:")
        print(template("## The stop's sitting"))
    elif not approved and not any(head_line(p, "Form:").strip() == "Form: built" for p in step_docs):
        print("No document is approved yet: this gate is the start sitting (run-modes.md). "
              "Present it in this shape, every part included:")
        print(template("## The start sitting"))
    else:
        print("Present the gate as SKILL.md's 'Gate presentation is glanceable' says: the review "
              "findings with dispositions, the changes since each approval in two groups, the open "
              "items (blocking first), the next-step line, then the render question, last.")


def main(argv):
    gate = "--gate" in argv
    args = [a for a in argv if a != "--gate"]
    docs = Path(args[0] if args else "docs/backend-design")
    if not docs.is_dir():
        print(f"{docs}: no such directory")
        return 2
    md = [p for p in sorted(docs.rglob("*.md")) if "changes" not in p.relative_to(docs).parts]
    step_docs = [p for p in md if p.name in STEP_DOCS]
    open_items = docs / "open-items.md"
    open_ids = check_open_items(open_items) if open_items.exists() else set()
    if not open_items.exists():
        report(open_items, 0, "missing (documents.md, open-items.md)")
    for path in step_docs:
        check_header(path)
    for path in md:
        if path == open_items:
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            for oi in sorted(set(OI_RE.findall(line)) - open_ids):
                report(path, n, f"cites {oi}, which is not an open item: cite the decision that settled it")
    plan = docs / "plan.md"
    if plan.exists():
        check_plan(plan)
    else:
        report(plan, 0, "missing (documents.md, plan.md)")
    approved = check_git(docs, step_docs, gate)
    for line in findings:
        print(line)
    if gate and not findings:
        print_shape(docs, step_docs, approved)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
