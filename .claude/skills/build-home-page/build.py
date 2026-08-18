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
main{max-width:1060px;margin:0 auto;padding:56px 24px 96px}
.cols{column-count:2;column-gap:48px}
.cols .theme{break-inside:avoid;-webkit-column-break-inside:avoid;page-break-inside:avoid;margin-bottom:1.4em}
@media(max-width:820px){main{max-width:760px}.cols{column-count:1}}
a{color:var(--link);text-decoration:none}
a:hover{color:var(--link-h);text-decoration:underline}
header.top{display:flex;gap:30px;align-items:flex-start;margin-bottom:8px}
header.top .ht{flex:1;min-width:0}
header.top img{width:172px;border-radius:5px;filter:grayscale(12%)}
h1{font-size:1.95rem;font-weight:600;margin:0 0 6px;letter-spacing:-.01em}
.tagline{color:var(--muted);font-style:italic;margin:0 0 10px}
.toplinks{font-size:.92rem;color:var(--muted)}
.toplinks a{margin-right:2px}
.toplinks .sep{color:var(--rule);margin:0 7px}
nav.contents{font-size:.86rem;color:var(--muted);margin:22px 0 8px;line-height:1.9}
.cols{margin-top:44px}
nav.contents a{color:var(--muted)}
nav.contents a:hover{color:var(--link)}
nav.contents .sep{color:var(--rule);margin:0 6px}
h2{font-size:1.12rem;font-weight:600;margin:.2em 0 .2em;padding-bottom:5px;
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
.toggle{display:inline-block;font-size:.82rem;color:var(--muted);cursor:pointer;margin:2px 0 4px}
.toggle input{margin-right:6px;vertical-align:middle}
li.working{display:none}
body.show-working li.working{display:list-item}
.theme[data-essays="1"]{display:none}
details.best{margin:10px 0 4px;font-size:.92rem;border:1px solid var(--new);border-radius:6px;
  padding:7px 14px;background:#fbf7ef}
details.best>summary{font-weight:600;color:var(--new);cursor:pointer;list-style:none}
details.best>summary::-webkit-details-marker{display:none}
details.best>summary::before{content:"\\25B8  "}
details.best[open]>summary::before{content:"\\25BE  "}
details.best>summary::after{content:"  (click to expand)";font-weight:400;font-size:.8rem;color:var(--muted)}
details.best[open]>summary::after{content:""}
details.best p{margin:.5em 0 .1em;color:#3a3a3a}
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


POSTED = {"arXiv", "SSRN", "journal", "chapter", "publisher", "MIT Press", "DOI"}


def is_working(p: dict) -> bool:
    """Working paper = draft only: no venue and no arXiv/SSRN/journal-style link."""
    if p.get("venue"):
        return False
    return not any(ln.get("label") in POSTED for ln in p.get("links", []))


def pub_li(p: dict, abstracts: dict, classify: bool = False) -> str:
    venue = f'<span class="venue"> — {esc(p["venue"])}.</span>' if p.get("venue") else ""
    ab = abstracts.get(p["title"])
    det = (f'\n      <details><summary>abstract</summary><p>{esc(ab)}</p></details>'
           if ab else "")
    cls = ' class="working"' if (classify and is_working(p)) else ""
    return (
        f'    <li{cls}>\n'
        f'      <div class="t">{esc(p["title"])}{venue}</div>\n'
        f'      <div class="ln">{links_row(p)}</div>{det}\n'
        '    </li>'
    )


def soft_li(s: dict) -> str:
    home = s.get("docs") or s.get("code")
    name = f'<a class="nm" href="{esc(home)}">{esc(s["name"])}</a>'
    code = (f' <span class="sep">·</span> <a href="{esc(s["code"])}">{esc(s.get("code_label", "code"))}</a>'
            if s.get("docs") and s.get("code") else "")
    return f'    <li class="soft">{name} — {esc(s["desc"])}{code}</li>'


def pub_list(papers: list, abstracts: dict, classify: bool = False) -> str:
    return ('  <ul class="pubs">\n'
            + "\n".join(pub_li(p, abstracts, classify) for p in papers)
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
        bits = []
        if th.get("package"):
            bits.append(f'<a href="https://github.com/microprediction/{esc(th["package"])}">'
                        f'{esc(th["package"])}</a>')
        for s in th.get("sites", []):
            bits.append(f'<a href="{esc(s["url"])}">{esc(s["label"])}</a>')
        pkg = (' <span class="pkg">· ' + ' · '.join(bits) + '</span>') if bits else ""
        blocks.append((slug(th["title"]), esc(th["title"]) + pkg,
                       pub_list(th["papers"], abstracts, classify=True)))

    if data.get("software"):
        rows = "\n".join(soft_li(s) for s in data["software"])
        ss = data.get("software_site")
        head = "Software" + (f' <span class="pkg">· <a href="{esc(ss["url"])}">'
                             f'{esc(ss["label"])}</a></span>' if ss else "")
        blocks.append(("software", head, f'  <ul class="pubs">\n{rows}\n  </ul>'))

    if data.get("talks"):
        blocks.append(("talks", "Selected Talks", pub_list(data["talks"], abstracts)))

    if data.get("videos"):
        blocks.append(("videos", "Videos", pub_list(data["videos"], abstracts)))

    if data.get("interviews"):
        blocks.append(("interviews", "Interviews", pub_list(data["interviews"], abstracts)))

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

    def sec(a, h, b):
        de = ' data-essays="1"' if a == "essays" else ''
        return f'    <section class="theme"{de}><h2 id="{a}">{h}</h2>\n{b}\n    </section>'
    body = ('  <div class="cols">\n'
            + "\n".join(sec(a, h, b) for a, h, b in blocks)
            + '\n  </div>')

    more = ""
    if data.get("more"):
        ml = " · ".join(f'<a href="{esc(m["url"])}">{esc(m["label"])}</a>'
                        for m in data["more"])
        more = f"\n  <footer>{ml}</footer>"

    pagetitle = esc(site.get("name", "Home"))
    desc = esc(site.get("description", ""))
    url = site.get("url", "")
    img = f'{url.rstrip("/")}/{site["photo"]}' if url and site.get("photo") else ""
    og = ""
    if desc or img:
        og = f"""
  <meta name="description" content="{desc}" />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{pagetitle}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:url" content="{esc(url)}" />
  <meta property="og:image" content="{esc(img)}" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{pagetitle}" />
  <meta name="twitter:description" content="{desc}" />
  <meta name="twitter:image" content="{esc(img)}" />"""
    toggle_js = (
        '  <script>\n'
        '(function(){\n'
        '  var cw=document.getElementById("showwork");\n'
        '  var ce=document.getElementById("showessays");\n'
        '  if(!cw&&!ce) return;\n'
        '  function apply(){\n'
        '    document.body.classList.toggle("show-working", cw&&cw.checked);\n'
        '    document.querySelectorAll(".theme").forEach(function(s){\n'
        '      if(s.getAttribute("data-essays")==="1"){\n'
        '        s.style.display=(ce&&ce.checked)?"block":"none"; return;}\n'
        '      var vis=[].some.call(s.querySelectorAll("li"),function(li){\n'
        '        return !li.classList.contains("working")||(cw&&cw.checked);});\n'
        '      s.style.display=vis?"":"none";\n'
        '    });\n'
        '  }\n'
        '  if(cw) cw.addEventListener("change",apply);\n'
        '  if(ce) ce.addEventListener("change",apply);\n'
        '  apply();\n'
        '})();\n'
        '  </script>'
    )
    hl = data.get("highlight")
    highlight_html = (f'    <details class="best"><summary>{esc(hl["summary"])}</summary>'
                      f'<p>{hl["body"]}</p></details>\n') if hl else ""
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{pagetitle}</title>{og}
  <link rel="icon" href="./assets/favicon.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="./academic.css" />
</head>
<body>
  <main>
    <header class="top">
      <div class="ht">
        <h1>{pagetitle}</h1>
        {tagline}
        <div class="toplinks">{toplinks}</div>
        <nav class="contents">{nav}</nav>
      </div>
      {photo}
    </header>
    <label class="toggle"><input type="checkbox" id="showwork"> show working papers</label>
    <label class="toggle"><input type="checkbox" id="showessays"> include essays</label>
{highlight_html}
{body}
  </main>{more}
{toggle_js}
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
