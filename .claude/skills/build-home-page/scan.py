#!/usr/bin/env python3
"""Scan the sibling microprediction package repos for paper drafts and arXiv links.

These repos publish the subdomains schur / humpday / precise / mechanics /
skaters .microprediction.org and hold the *latest* drafts (in their papers/ and
docs/ folders), which usually move faster than the arXiv/published copies linked
from home.microprediction.org.

This script does NOT edit anything. It prints a report (and writes scan_report.json
next to itself) so that papers.json can be reconciled by hand, then built with
build.py.

Run:  python3 scan.py
"""
from __future__ import annotations
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# Subdomains to scan. Add to this list as new package sites appear.
TARGETS = ["schur", "humpday", "precise", "mechanics", "skaters", "conformalprediction"]

# Folders within each repo worth scanning for drafts.
DRAFT_DIRS = ["papers", "docs", "academic", "paper"]
DRAFT_EXTS = {".pdf", ".tex"}
# Skip auto-generated / figure clutter.
SKIP_PARTS = {"figures", "fig", "assets", "build", "_minted", "node_modules"}

ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", re.I)
ARXIV_ID_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})", re.I)
TITLE_RE = re.compile(r"\\title\{(.*?)\}", re.S)


def find_repo_root(start: Path) -> Path:
    """Ascend until we find papers.json (the home repo root)."""
    for d in [start, *start.parents]:
        if (d / "papers.json").exists():
            return d
    return start


def mtime(p: Path) -> str:
    ts = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    return ts.strftime("%Y-%m-%d")


def clean_title(tex: str) -> str:
    t = TITLE_RE.search(tex)
    if not t:
        return ""
    s = t.group(1)
    s = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", s)  # \pkg{x} -> x
    s = re.sub(r"\\[a-zA-Z]+\b", "", s)               # \vspace etc
    s = s.replace("\\\\", " ").replace("---", "—").replace("--", "–")
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def scan_repo(repo: Path) -> dict:
    info: dict = {"name": repo.name, "site": None, "drafts": [], "arxiv": []}

    cname = repo / "docs" / "CNAME"
    if cname.exists():
        info["site"] = "https://" + cname.read_text().strip()

    arxiv_hits: dict[str, set[str]] = {}
    for sub in DRAFT_DIRS:
        base = repo / sub
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            if SKIP_PARTS & set(part.lower() for part in p.parts):
                continue
            rel = p.relative_to(repo).as_posix()
            if p.suffix.lower() in DRAFT_EXTS:
                entry = {
                    "path": rel,
                    "modified": mtime(p),
                    "blob": f"https://github.com/microprediction/{repo.name}/blob/main/{rel}",
                }
                if p.suffix.lower() == ".tex":
                    try:
                        entry["title"] = clean_title(p.read_text(errors="ignore"))
                    except Exception:
                        pass
                info["drafts"].append(entry)
            # harvest arxiv ids from text-ish files
            if p.suffix.lower() in {".tex", ".bib", ".md", ".html", ".txt"}:
                try:
                    txt = p.read_text(errors="ignore")
                except Exception:
                    continue
                for m in list(ARXIV_RE.finditer(txt)) + list(ARXIV_ID_RE.finditer(txt)):
                    arxiv_hits.setdefault(m.group(1), set()).add(rel)

    info["drafts"].sort(key=lambda d: d["modified"], reverse=True)
    info["arxiv"] = [
        {"id": k, "in": sorted(v)} for k, v in sorted(arxiv_hits.items())
    ]
    return info


def main() -> None:
    here = Path(__file__).resolve().parent
    repo_root = find_repo_root(here)
    parent = repo_root.parent  # the github/ folder holding the sibling repos

    report = {"scanned_from": str(parent), "repos": []}
    for name in TARGETS:
        repo = parent / name
        if not repo.is_dir():
            report["repos"].append({"name": name, "missing": True})
            continue
        report["repos"].append(scan_repo(repo))

    out = here / "scan_report.json"
    out.write_text(json.dumps(report, indent=2))

    # Human-readable summary
    print(f"Scanned sibling repos under {parent}\n")
    for r in report["repos"]:
        if r.get("missing"):
            print(f"  {r['name']:<10} (not cloned locally — skipped)")
            continue
        print(f"  {r['name']:<10} {r.get('site') or ''}")
        for d in r["drafts"][:8]:
            title = f"  «{d['title']}»" if d.get("title") else ""
            print(f"      {d['modified']}  {d['path']}{title}")
        if r["arxiv"]:
            ids = ", ".join(a["id"] for a in r["arxiv"][:12])
            print(f"      arXiv ids referenced: {ids}")
        print()
    print(f"Full report → {out}")
    print("Next: reconcile newer drafts / arXiv links into papers.json, then run build.py")


if __name__ == "__main__":
    main()
