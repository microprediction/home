#!/usr/bin/env python3
"""Generate home.microprediction.org from papers.json + abstracts.json.

Writes docs/index.html, docs/academic.css, docs/CNAME. Pure stdlib so it runs in
CI (which only has the home repo, no pdftotext) — abstracts come from the
committed abstracts.json, produced locally by extract_abstracts.py.
"""
from __future__ import annotations
import html
import json
from pathlib import Path

CNAME = "home.microprediction.org"

CSS = """
:root{
  --ink:#1b1b1b; --muted:#666; --rule:#e3e1da; --link:#33527a; --link-h:#1d3358;
  --new:#6b4e16; --bg:#fcfcfa;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
  font-family:Charter,Georgia,Cambria,"Times New Roman",serif;
  font-size:18px;line-height:1.55;-webkit-font-smoothing:antialiased}
main{max-width:760px;margin:0 auto;padding:56px 24px 96px}
a{color:var(--link);text-decoration:none}
a:hover{color:var(--link-h);text-decoration:underline}
header.top{display:flex;gap:26px;align-items:flex-start;margin-bottom:8px}
header.top .ht{flex:1}
header.top img{width:132px;border-radius:4px;filter:grayscale(15%)}
h1{font-size:1.95rem;font-weight:600;margin:0 0 6px;letter-spacing:-.01em}
.tagline{color:var(--muted);font-style:italic;margin:0 0 10px}
.toplinks{font-size:.92rem;color:var(--muted)}
.toplinks a{margin-right:2px}
.toplinks .sep{color:var(--rule);margin:0 7px}
nav.contents{font-size:.86rem;color:var(--muted);margin:22px 0 8px;line-height:1.9}
nav.contents a{color:var(--muted)}
nav.contents a:hover{color:var(--link)}
nav.contents .sep{color:var(--rule);margin:0 6px}
h2{font-size:1.12rem;font-weight:600;margin:2.4em 0 .2em;padding-bottom:5px;
  border-bottom:1px solid var(--rule)}
h2 .pkg{font-weight:400;font-size:.8rem;color:var(--muted)}
ul.pubs{list-style:none;margin:0;padding:0}
ul.pubs>li{padding:13px 0;border-bottom:1px solid #efede6}
ul.pubs>li:last-child{border-bottom:none}
.t{font-size:1rem}
.venue{font-style:italic;color:var(--muted)}
.ln{font-size:.85rem;margin-top:3px;color:var(--muted)}
.ln a{margin:0}
.ln .sep{color:var(--rule);margin:0 6px}
.ln a.new{color:var(--new)}
.ln .wip{font-style:italic;color:var(--muted)}
details{margin-top:5px}
details summary{font-size:.82rem;color:var(--muted);cursor:pointer;list-style:none;
  display:inline-block}
details summary::-webkit-details-marker{display:none}
details summary::before{content:"▸ ";color:var(--rule)}
details[open] summary::before{content:"▾ "}
details p{font-size:.92rem;color:#3a3a3a;margin:.5em 0 .2em;
  padding-left:14px;border-left:2px solid var(--rule)}
.soft{font-size:.95rem}
.soft .nm{color:var(--ink)}
footer{max-width:760px;margin:0 auto;padding:18px 24px 40px;font-size:.82rem;
  color:var(--muted)}
footer a{color:var(--muted)}
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


def links_row(p: dict) -> str:
    parts = []
    for ln in p.get("links", []):
        cls = ' class="new"' if ln["label"] == "latest draft" else ""
        parts.append(f'<a{cls} href="{esc(ln["url"])}">{esc(ln["label"])}</a>')
    if p.get("draft_in_progress"):
        parts.append('<span class="wip">draft in progress</span>')
    return '<span class="sep">·</span>'.join(parts)


def pub_li(p: dict, abstracts: dict) -> str:
    venue = f'<span class="venue"> — {esc(p["venue"])}.</span>' if p.get("venue") else ""
    ab = abstracts.get(p["title"])
    det = (f'\n      <details><summary>abstract</summary><p>{esc(ab)}</p></details>'
           if ab else "")
    return (
        '    <li>\n'
        f'      <div class="t">{esc(p["title"])}{venue}</div>\n'
        f'      <div class="ln">{links_row(p)}</div>{det}\n'
        '    </li>'
    )


def pub_list(papers: list, abstracts: dict) -> str:
    return ('  <ul class="pubs">\n'
            + "\n".join(pub_li(p, abstracts) for p in papers)
            + "\n  </ul>")


def build(root: Path) -> None:
    data = json.loads((root / "papers.json").read_text())
    ab_path = root / "abstracts.json"
    abstracts = json.loads(ab_path.read_text()) if ab_path.exists() else {}
    site = data["site"]
    docs = root / "docs"
    docs.mkdir(exist_ok=True)

    blocks = []          # (anchor, heading_html, body_html)

    if data.get("book_length"):
        blocks.append(("book-length", "Book Length", pub_list(data["book_length"], abstracts)))

    for th in data.get("themes", []):
        pkg = (f' <span class="pkg">· '
               f'<a href="https://github.com/microprediction/{esc(th["package"])}">'
               f'{esc(th["package"])}</a></span>') if th.get("package") else ""
        blocks.append((slug(th["title"]), esc(th["title"]) + pkg,
                       pub_list(th["papers"], abstracts)))

    if data.get("software"):
        rows = "\n".join(
            f'    <li class="soft"><a class="nm" href="{esc(s["url"])}">{esc(s["name"])}</a> '
            f'— {esc(s["desc"])}</li>' for s in data["software"])
        blocks.append(("software", "Software", f'  <ul class="pubs">\n{rows}\n  </ul>'))

    if data.get("talks"):
        blocks.append(("talks", "Talks", pub_list(data["talks"], abstracts)))

    if data.get("patents"):
        blocks.append(("patents", "Patents", pub_list(data["patents"], abstracts)))

    # header
    photo = (f'<img src="{esc(site["photo"])}" alt="">'
             if site.get("photo") else "")
    toplinks = '<span class="sep">·</span>'.join(
        f'<a href="{esc(l["url"])}">{esc(l["label"])}</a>' for l in site.get("links", []))
    tagline = f'<p class="tagline">{esc(site["tagline"])}</p>' if site.get("tagline") else ""
    nav = '<span class="sep">·</span>'.join(
        f'<a href="#{a}">{h.split("<")[0].strip()}</a>' for a, h, _ in blocks)

    body = "\n".join(
        f'  <h2 id="{a}">{h}</h2>\n{b}' for a, h, b in blocks)

    more = ""
    if data.get("more"):
        ml = " · ".join(f'<a href="{esc(m["url"])}">{esc(m["label"])}</a>'
                        for m in data["more"])
        more = f"\n  <footer>{ml}</footer>"

    pagetitle = esc(site.get("name", "Home"))
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{pagetitle}</title>
  <link rel="stylesheet" href="./academic.css" />
</head>
<body>
  <main>
    <header class="top">
      <div class="ht">
        <h1>{pagetitle}</h1>
        {tagline}
        <div class="toplinks">{toplinks}</div>
      </div>
      {photo}
    </header>
    <nav class="contents">{nav}</nav>

{body}
  </main>{more}
</body>
</html>
"""
    (docs / "academic.css").write_text(CSS.lstrip())
    (docs / "index.html").write_text(page)
    (docs / "CNAME").write_text(CNAME + "\n")
    n = sum(len(b.get("papers", b.get("book_length", []))) for b in [])  # noqa
    print(f"Wrote {docs/'index.html'} — {len(blocks)} sections, {len(abstracts)} abstracts")


def find_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "papers.json").exists():
            return d
    raise SystemExit("papers.json not found")


if __name__ == "__main__":
    build(find_root(Path(__file__).resolve().parent))
