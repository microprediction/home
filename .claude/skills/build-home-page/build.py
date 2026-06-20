#!/usr/bin/env python3
"""Generate home.microprediction.org from papers.json.

Writes docs/index.html, docs/academic.css and docs/CNAME. GitHub Pages serves
the docs/ folder, so PDFs that live at the repo root (workingpapers/, papers/)
are linked via github.com blob URLs rather than relative paths.

Run:  python3 build.py
"""
from __future__ import annotations
import html
import json
from datetime import date
from pathlib import Path

CNAME = "home.microprediction.org"

# Link kinds rendered for each paper, in order. label -> css modifier.
LINK_KINDS = [
    ("arxiv", "arXiv", "arxiv"),
    ("draft", "draft", "draft"),       # may be re-labelled "latest draft" if draft_new
    ("journal", "journal", "journal"),
    ("blog", "blog", "blog"),
    ("talk", "talk", "talk"),
    ("site", "site", "site"),
]

EXTRA_CSS = """
/* --- paper list (home page) --- */
.section-blurb { color: var(--muted); margin: 0 0 14px; font-size: 0.96rem; }
ul.papers { list-style: none; padding: 0; margin: 0; }
ul.papers > li { padding: 14px 0; border-bottom: 1px solid var(--border); }
ul.papers > li:last-child { border-bottom: none; }
.ptitle { font-weight: 600; }
.pmeta { color: var(--muted); font-size: 0.85rem; margin-left: 8px; }
.abstract { color: var(--muted); font-size: 0.95rem; margin: 4px 0 8px; }
.links { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.lnk { font-size: 0.82rem; padding: 2px 9px; border-radius: 4px; border: 1px solid var(--border); background: #fff; }
.lnk:hover { text-decoration: none; border-color: var(--accent); }
.lnk.draft { border-color: #d9d4ff; }
.lnk.draft.latest { background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600; }
.lnk.arxiv { background: #fbf0ea; border-color: #f0d9c8; color: var(--warn); }
.pkg { font-size: 0.82rem; color: var(--muted); margin-left: 4px; }
.hero { display: flex; gap: 28px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 8px; }
.hero img { width: 360px; max-width: 100%; border-radius: 8px; }
.hero .blurb { flex: 1; min-width: 280px; }
.toplinks { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0 4px; }
"""


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def render_links(p: dict) -> str:
    out = []
    for key, label, mod in LINK_KINDS:
        url = p.get("arxiv") and key == "arxiv" and f"https://arxiv.org/abs/{p['arxiv']}" or p.get(key)
        if not url:
            continue
        cls = f"lnk {mod}"
        text = label
        if key == "draft" and p.get("draft_new"):
            cls += " latest"
            text = "latest draft"
        out.append(f'<a class="{cls}" href="{esc(url)}">{esc(text)}</a>')
    return "".join(out)


def render_paper(p: dict) -> str:
    meta = []
    if p.get("authors"):
        meta.append(esc(p["authors"]))
    if p.get("year"):
        meta.append(esc(p["year"]))
    meta_html = f'<span class="pmeta">{" · ".join(meta)}</span>' if meta else ""
    pkg = ""
    if p.get("package"):
        pkg = (f' <span class="pkg">· '
               f'<a href="https://github.com/microprediction/{esc(p["package"])}">'
               f'{esc(p["package"])}</a></span>')
    abstract = f'<p class="abstract">{esc(p["abstract"])}</p>' if p.get("abstract") else ""
    return (
        '    <li>\n'
        f'      <span class="ptitle">{esc(p["title"])}</span>{meta_html}{pkg}\n'
        f'      {abstract}\n'
        f'      <div class="links">{render_links(p)}</div>\n'
        '    </li>'
    )


def render_section(sec: dict, papers: list[dict]) -> str:
    items = [p for p in papers if p.get("section") == sec["id"]]
    if not items:
        return ""
    items.sort(key=lambda p: p.get("year", 0), reverse=True)
    blurb = f'<p class="section-blurb">{esc(sec["blurb"])}</p>' if sec.get("blurb") else ""
    body = "\n".join(render_paper(p) for p in items)
    return (
        f'  <h2 id="{esc(sec["id"])}">{esc(sec["title"])}</h2>\n'
        f'  {blurb}\n'
        f'  <ul class="papers">\n{body}\n  </ul>'
    )


def build(repo_root: Path) -> None:
    data = json.loads((repo_root / "papers.json").read_text())
    site = data["site"]
    papers = data["papers"]
    docs = repo_root / "docs"
    docs.mkdir(exist_ok=True)

    nav = "".join(
        f'<a href="#{esc(s["id"])}">{esc(s["title"])}</a>'
        for s in data["sections"] if any(p.get("section") == s["id"] for p in papers)
    )
    toplinks = "".join(
        f'<a class="btn secondary" href="{esc(l["url"])}">{esc(l["label"])}</a>'
        for l in site.get("links", [])
    )
    photo = (f'<img src="{esc(site["photo"])}" alt="Peter Cotton" />'
             if site.get("photo") else "")
    sections_html = "\n".join(
        s for s in (render_section(sec, papers) for sec in data["sections"]) if s
    )
    built = date.today().isoformat()

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{esc(site["title"])} — papers</title>
  <meta name="description" content="{esc(site["tagline"])}" />
  <link rel="stylesheet" href="./academic.css" />
</head>
<body>
  <header class="site-header">
    <div class="nav-inner">
      <a class="brand" href="/">{esc(site["title"])}</a>
      <nav>{nav}<a href="https://github.com/microprediction">GitHub</a></nav>
    </div>
  </header>

  <main>
    <h1>{esc(site["title"])}</h1>
    <p class="subtitle">{esc(site["tagline"])}</p>
    <div class="hero">
      {photo}
      <div class="blurb">
        <p class="lead">{esc(site["intro"])}</p>
        <div class="toplinks">{toplinks}</div>
      </div>
    </div>

{sections_html}
  </main>

  <footer>
    Generated from <code>papers.json</code> on {built} ·
    <a href="https://github.com/microprediction/home">source</a>
  </footer>
</body>
</html>
"""

    # academic.css = shared base + page-specific extras.
    base_css = (repo_root / ".claude" / "skills" / "build-home-page" / "academic_base.css")
    css = base_css.read_text() if base_css.exists() else ""
    (docs / "academic.css").write_text(css + EXTRA_CSS)
    (docs / "index.html").write_text(page)
    (docs / "CNAME").write_text(CNAME + "\n")

    print(f"Wrote {docs/'index.html'} ({len(papers)} papers, {sections_html.count('<h2')} sections)")
    print(f"Wrote {docs/'academic.css'}")
    print(f"Wrote {docs/'CNAME'} -> {CNAME}")


def find_repo_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "papers.json").exists():
            return d
    raise SystemExit("Could not locate papers.json above " + str(start))


if __name__ == "__main__":
    build(find_repo_root(Path(__file__).resolve().parent))
