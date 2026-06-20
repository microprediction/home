#!/usr/bin/env python3
"""Extract the REAL abstract of each paper from its source (never fabricate one).

Sources, in preference order: a TeX abstract (\\begin{abstract} or jss \\Abstract{}),
else pdftotext on the first page (text between "Abstract" and "Introduction").
Writes abstracts.json keyed by paper title. build.py reads that committed cache,
so CI never needs pdftotext or the sibling repos.

Run locally after adding/updating papers:  python3 extract_abstracts.py
"""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def repo_root() -> Path:
    for d in [HERE, *HERE.parents]:
        if (d / "papers.json").exists():
            return d
    raise SystemExit("papers.json not found")


ROOT = repo_root()
GH = ROOT.parent  # folder holding the sibling repos


def local_path(url: str) -> Path | None:
    m = re.match(r"https://github\.com/microprediction/([^/]+)/blob/main/(.+)$", url)
    if not m:
        return None
    repo, rel = m.groups()
    base = ROOT if repo == "home" else GH / repo
    p = base / rel
    return p if p.exists() else None


def clean_tex(s: str) -> str:
    s = re.sub(r"(?<!\\)%.*", "", s)                      # strip comments
    for cmd in ("emph", "textit", "textbf", "pkg", "proglang", "code",
                "texttt", "textsc", "mbox"):
        s = re.sub(r"\\%s\{([^{}]*)\}" % cmd, r"\1", s)
    s = re.sub(r"\\(noindent|vspace\{[^}]*\}|smallskip|medskip|bigskip)", " ", s)
    s = s.replace("\\\\", " ").replace("~", " ")
    s = re.sub(r"\\[a-zA-Z]+\b", "", s)                   # drop remaining commands
    s = s.replace("---", "—").replace("--", "–")
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def balanced(s: str, start: int) -> str | None:
    """Return contents of a {...} group whose '{' is at index `start`."""
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1:i]
    return None


def from_tex(p: Path) -> str | None:
    t = p.read_text(errors="ignore")
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, re.S)
    body = m.group(1) if m else None
    if body is None:
        m = re.search(r"\\Abstract\s*\{", t)
        if m:
            body = balanced(t, m.end() - 1)
    if body is None:
        return None
    out = clean_tex(body)
    # Reject when the "abstract" was just a macro reference like \skatersabstract.
    return out if len(out) > 60 else None


def _tidy(body: str) -> str:
    body = re.sub(r"-\n", "", body)        # de-hyphenate line breaks
    return re.sub(r"\s+", " ", body).strip()


def from_pdf(p: Path) -> str | None:
    try:
        txt = subprocess.run(["pdftotext", "-f", "1", "-l", "2", str(p), "-"],
                             capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    intro = r"(?:\n\s*(?:1\.?\s+)?Introduction\b|\nKeywords\b|\nJEL\b)"
    # Case 1: an explicit "Abstract" heading.
    m = re.search(r"\bAbstract\b[.:]?\s*(.+?)" + intro, txt, re.S)
    # Case 2: no heading — the abstract is the block just before "Introduction",
    # after the all-caps title/author lines (common in SIAM-style papers).
    if not m:
        head = re.search(intro, txt)
        if head:
            before = txt[:head.start()]
            # drop leading TITLE / AUTHOR lines (uppercase or very short).
            lines = before.splitlines()
            while lines and (lines[0].isupper() or len(lines[0].strip()) < 4
                             or lines[0].strip().istitle() and len(lines[0]) < 40):
                lines.pop(0)
            body = _tidy("\n".join(lines))
            return body if 120 < len(body) < 2500 else None
        return None
    body = _tidy(m.group(1))
    return body if len(body) > 80 else None


def source_for(p: dict) -> Path | None:
    tex, pdf = None, None
    for ln in p.get("links", []):
        loc = local_path(ln["url"])
        if not loc:
            continue
        if loc.suffix == ".tex" and tex is None:
            tex = loc
        elif loc.suffix == ".pdf" and pdf is None:
            pdf = loc
    return tex or pdf  # prefer tex, but also use a tex sibling of a pdf below


def extract(p: dict) -> str | None:
    src = source_for(p)
    if src is None:
        return None
    if src.suffix == ".tex":
        return from_tex(src)
    # pdf: prefer a sibling .tex if present (cleaner), else pdftotext
    sib = src.with_suffix(".tex")
    if sib.exists():
        a = from_tex(sib)
        if a:
            return a
    return from_pdf(src)


def main() -> None:
    data = json.loads((ROOT / "papers.json").read_text())
    papers = [p for th in data.get("themes", []) for p in th["papers"]]
    if data.get("book"):
        papers.append(data["book"])

    out: dict[str, str] = {}
    missing = []
    for p in papers:
        a = extract(p)
        if a:
            out[p["title"]] = a
        else:
            missing.append(p["title"])

    (ROOT / "abstracts.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"Extracted {len(out)} abstracts -> {ROOT/'abstracts.json'}")
    for t in missing:
        print(f"  (no source / abstract)  {t[:70]}")


if __name__ == "__main__":
    main()
