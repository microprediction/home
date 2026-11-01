#!/usr/bin/env python3
"""Generate home.microprediction.org from papers.json + abstracts.json.

Writes docs/index.html, docs/academic.css, docs/CNAME. Pure stdlib so it runs in
CI (which only has the home repo, no pdftotext) — abstracts come from the
committed abstracts.json, produced locally by extract_abstracts.py.
"""
from __future__ import annotations
import html
import hashlib
import json
from datetime import date
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
header.top{margin-bottom:8px}
header.top::after{content:"";display:table;clear:both}
header.top img{float:right;width:340px;margin:2px 0 14px 34px;border-radius:6px;filter:grayscale(12%)}
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
.ln .date{color:var(--muted);font-variant-numeric:tabular-nums}
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
li.technote{display:none}
body.show-notes li.technote{display:list-item}
.tag{display:inline-block;font-size:.7rem;font-weight:400;color:var(--muted);
  border:1px solid var(--rule);border-radius:3px;padding:0 5px;margin-left:8px;vertical-align:middle;
  letter-spacing:.02em}
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
details.ultra{border-color:var(--rule);background:transparent}
details.ultra>summary{color:var(--link)}
.ultra .ultra-meta{font-size:.78rem;color:var(--muted)}
.ultra h4{font-size:.8rem;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:1.4em 0 .3em}
.ultra h5{font-size:.95rem;font-weight:600;color:var(--ink);margin:1em 0 .3em}
.ultra ol,.ultra ul.also{list-style:none;margin:.6em 0 .3em;padding:0}
.ultra li{padding:1px 0 1px 12px;margin:0 0 8px;border-left:3px solid var(--new)}
.ultra ul.also li{border-left-color:var(--rule)}
.ultra li:last-child{margin-bottom:0}
.ultra .rk{display:inline-block;min-width:1.6em;color:var(--muted);font-variant-numeric:tabular-nums}
.ultra .ttl{font-weight:600}
.ultra .ttl a{color:var(--ink)}
.ultra .th{color:var(--muted);font-size:.85rem;margin-left:6px}
.ultra .verdict{display:block;font-size:.88rem;color:#3a3a3a;margin:2px 0 0}
.ultra p{padding-left:0;border-left:0}
.ultra details.more{margin:2px 0 0;font-size:.85rem}
.ultra details.more>summary{color:var(--muted);cursor:pointer;list-style:none;font-size:.8rem}
.ultra details.more>summary::-webkit-details-marker{display:none}
.ultra details.more>summary::before{content:"▸ ";color:var(--rule)}
.ultra details.more[open]>summary::before{content:"▾ "}
.ultra .ultra-caveat{font-size:.85rem;color:var(--muted)}
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_date(d: str) -> str:
    """'2026-09' -> 'Sep 2026'; '2022' -> '2022'."""
    d = str(d)
    if len(d) >= 7 and d[4] == "-":
        try:
            return f"{MONTHS[int(d[5:7]) - 1]} {d[:4]}"
        except (ValueError, IndexError):
            return d[:4]
    return d[:4]


def links_row(p: dict) -> str:
    parts = []
    if p.get("date") and not p.get("venue"):
        parts.append(f'<span class="date">{esc(fmt_date(p["date"]))}</span>')
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
    classes = []
    if classify and is_working(p):
        classes.append("working")
    if p.get("note"):
        classes.append("technote")
    cls = f' class="{" ".join(classes)}"' if classes else ""
    tag = ' <span class="tag">technical note</span>' if p.get("note") else ""
    return (
        f'    <li{cls}>\n'
        f'      <div class="t">{esc(p["title"])}{venue}{tag}</div>\n'
        f'      <div class="ln">{links_row(p)}</div>{det}\n'
        '    </li>'
    )


def soft_li(s: dict) -> str:
    home = s.get("docs") or s.get("code")
    name = f'<a class="nm" href="{esc(home)}">{esc(s["name"])}</a>'
    code = (f' <span class="sep">·</span> <a href="{esc(s["code"])}">{esc(s.get("code_label", "code"))}</a>'
            if s.get("docs") and s.get("code") else "")
    return f'    <li class="soft">{name} — {esc(s["desc"])}{code}</li>'


def visible(papers: list) -> list:
    """Drop entries marked ``"hidden": true`` (kept in papers.json, not rendered)."""
    return [p for p in papers if not p.get("hidden")]


def pub_list(papers: list, abstracts: dict, classify: bool = False) -> str:
    return ('  <ul class="pubs">\n'
            + "\n".join(pub_li(p, abstracts, classify) for p in visible(papers))
            + "\n  </ul>")


def ultra_foldout(data: dict) -> str:
    """Render an editorial reading list, resolving each paper against the catalogue.

    Each entry is one line: rank, linked title, theme, and a one-sentence
    ``verdict``. The longer ``why`` / ``caveat`` / ``heritage`` text, when
    present, folds under a "more" toggle. An optional ``also`` block lists
    further papers with a one-line note each and names who wrote the notes.
    """
    ultra = data.get("ultra")
    if ultra is None:
        return ""
    reviewed = date.fromisoformat(ultra["reviewed"])
    entries = ultra["entries"]
    if not entries:
        raise ValueError("ultra.entries must contain at least one paper")
    catalogue = {}
    for theme in data.get("themes", []):
        for paper in theme["papers"]:
            catalogue.setdefault(paper["title"], []).append((theme["title"], paper))
    for book in data.get("book_length", []):
        catalogue.setdefault(book["title"], []).append(("Book", book))

    link_order = ("journal", "arXiv", "SSRN", "DOI", "MIT Press", "latest draft", "pdf")
    selected = set()

    def resolve(title: str, where: str):
        if title in selected:
            raise ValueError(f"Duplicate {where} selection: {title}")
        selected.add(title)
        matches = catalogue.get(title, [])
        if len(matches) != 1:
            raise ValueError(f"{where} selection must match one catalogue paper: {title}")
        theme_title, paper = matches[0]
        if paper.get("hidden"):
            raise ValueError(f"{where} selection is hidden in the catalogue: {title}")
        links = paper.get("links", [])
        link = next((ln for label in link_order for ln in links
                     if ln.get("label") == label), None)
        if not link or not link["url"].startswith(("https://", "http://")):
            raise ValueError(f"{where} selection needs a public paper link: {title}")
        return theme_title, link["url"]

    def line(entry: dict, where: str, rank: int | None) -> str:
        title = entry["title"]
        theme_title, url = resolve(title, where)
        verdict = entry.get("verdict")
        if not isinstance(verdict, str) or not verdict.strip():
            raise ValueError(f"{where} entry needs a one-line verdict: {title}")
        rk = f'<span class="rk">{rank}</span>' if rank is not None else ""
        more = []
        if entry.get("why"):
            more.append(f'          <p>{esc(entry["why"])}</p>\n')
        if entry.get("caveat"):
            more.append(f'          <p class="ultra-caveat">Scope: {esc(entry["caveat"])}</p>\n')
        heritage = entry.get("heritage")
        if "heritage" in entry and (not isinstance(heritage, str) or not heritage.strip()):
            raise ValueError(f"{where} heritage must be nonempty plain text: {title}")
        if heritage:
            more.append(f'          <p class="ultra-caveat">Heritage: {esc(heritage)}</p>\n')
        more_html = (
            '        <details class="more"><summary>more</summary>\n'
            + "".join(more) + '        </details>\n'
        ) if more else ""
        return (
            '      <li>\n'
            f'        {rk}<span class="ttl"><a href="{esc(url)}">{esc(title)}</a></span> '
            f'<span class="th">{esc(theme_title)}</span>\n'
            f'        <span class="verdict">{esc(verdict)}</span>\n'
            + more_html
            + '      </li>'
        )

    rows = [line(e, "ULTRA", i) for i, e in enumerate(entries, 1)]
    also_html = ""
    also = ultra.get("also")
    if also:
        groups = also.get("groups")
        if not groups:
            raise ValueError("ultra.also.groups must contain at least one group")
        by = also.get("by")
        if not isinstance(by, str) or not by.strip():
            raise ValueError("ultra.also needs a 'by' attribution")
        note = also.get("note", "")
        parts = [f'      <h4>Also worth a look · notes by {esc(by)}</h4>\n']
        if note:
            parts.append(f'      <p class="ultra-meta">{esc(note)}</p>\n')
        for group in groups:
            heading = group.get("heading")
            if not isinstance(heading, str) or not heading.strip() or not group.get("entries"):
                raise ValueError("each ultra.also group needs a heading and entries")
            parts.append(f'      <h5>{esc(heading)}</h5>\n')
            parts.append('      <ul class="also">\n'
                         + "\n".join(line(e, "ULTRA also", None) for e in group["entries"])
                         + '\n      </ul>\n')
        also_html = "".join(parts)
    return (
        f'    <details class="best ultra" id="ultra"><summary>{esc(ultra["summary"])}</summary>\n'
        f'      <p class="ultra-meta">A selection of {len(entries)} papers · '
        f'reviewed <time datetime="{reviewed.isoformat()}">{reviewed.strftime("%d %b %Y")}</time></p>\n'
        f'      <p>{esc(ultra["description"])}</p>\n'
        '      <ol>\n' + "\n".join(rows) + '\n      </ol>\n'
        + also_html
        + '    </details>\n'
    )


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

    hidden_n = 0
    for th in data.get("themes", []):
        hidden_n += len(th["papers"]) - len(visible(th["papers"]))
        if not visible(th["papers"]):
            continue
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
        de = ' data-essays="1"' if "essay" in a else ''
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
        '  var cn=document.getElementById("shownotes");\n'
        '  if(!cw&&!ce&&!cn) return;\n'
        '  function apply(){\n'
        '    document.body.classList.toggle("show-working", cw&&cw.checked);\n'
        '    document.body.classList.toggle("show-notes", cn&&cn.checked);\n'
        '    document.querySelectorAll(".theme").forEach(function(s){\n'
        '      if(s.getAttribute("data-essays")==="1"){\n'
        '        s.style.display=(ce&&ce.checked)?"block":"none"; return;}\n'
        '      var vis=[].some.call(s.querySelectorAll("li"),function(li){\n'
        '        return (!li.classList.contains("working")||(cw&&cw.checked))\n'
        '            &&(!li.classList.contains("technote")||(cn&&cn.checked));});\n'
        '      s.style.display=vis?"":"none";\n'
        '    });\n'
        '  }\n'
        '  if(cw) cw.addEventListener("change",apply);\n'
        '  if(ce) ce.addEventListener("change",apply);\n'
        '  if(cn) cn.addEventListener("change",apply);\n'
        '  apply();\n'
        '})();\n'
        '  </script>'
    )
    hl = data.get("highlight")
    highlight_html = (f'    <details class="best"><summary>{esc(hl["summary"])}</summary>'
                      f'<p>{hl["body"]}</p></details>\n') if hl else ""
    ultra_html = ultra_foldout(data)
    css_hash = hashlib.sha1(CSS.lstrip().encode()).hexdigest()[:8]
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{pagetitle}</title>{og}
  <link rel="icon" href="./assets/favicon.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="./academic.css?v={css_hash}" />
</head>
<body>
  <main>
    <header class="top">
      {photo}
      <div class="ht">
        <h1>{pagetitle}</h1>
        {tagline}
        <div class="toplinks">{toplinks}</div>
        <nav class="contents">{nav}</nav>
      </div>
    </header>
    <label class="toggle"><input type="checkbox" id="showwork" checked> show working papers</label>
    <label class="toggle"><input type="checkbox" id="showessays" checked> include essays</label>
    <label class="toggle"><input type="checkbox" id="shownotes" checked> include technical notes</label>
{highlight_html}
{ultra_html}
{body}
  </main>{more}
{toggle_js}
</body>
</html>
"""
    (docs / "academic.css").write_text(CSS.lstrip())
    (docs / "index.html").write_text(page)
    (docs / "CNAME").write_text(CNAME + "\n")
    print(f"Wrote {docs/'index.html'} — {len(blocks)} sections, {len(abstracts)} abstracts, "
          f"{hidden_n} hidden papers")


def find_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "papers.json").exists():
            return d
    raise SystemExit("papers.json not found")


if __name__ == "__main__":
    build(find_root(Path(__file__).resolve().parent))
