#!/usr/bin/env python3
"""Posting status of every paper in papers.json: what is on SSRN and arXiv, and
whether the local draft has moved on since it was posted.

For each paper the script
  * reads SSRN and arXiv ids off the entry's links (an explicit "ssrn" or
    "arxiv" field on the entry overrides);
  * asks the arXiv API for the latest version and its date (cached in
    arxiv_cache.json beside this script, refreshed when older than a day);
  * takes SSRN posting dates from posted.json at the repo root, because SSRN
    sits behind Cloudflare and cannot be scraped; record the date there when
    you upload or revise;
  * resolves the "latest draft" / "pdf" link to a file in a sibling repo under
    ../ (github.com and raw.githubusercontent.com URLs directly, package sites
    through their CNAME files) and takes the last commit date of that file and
    of any .md/.tex source with the same stem, plus an uncommitted-changes
    flag;
  * reports one of: published, in sync, local newer (N days), not posted,
    unknown SSRN date, unresolved local.

Writes STATUS.md and status.json at the repo root and prints a summary.
Read-only otherwise.

Run:  python3 status.py            # from anywhere
      python3 status.py --offline  # skip the arXiv API, use the cache
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = next(d for d in [HERE, *HERE.parents] if (d / "papers.json").exists())
GITHUB = ROOT.parent
CACHE = HERE / "arxiv_cache.json"
POSTED = ROOT / "posted.json"

SSRN_RE = re.compile(r"ssrn\.com/(?:sol3/papers\.cfm\?abstract_id=|abstract=)(\d+)", re.I)
ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
GH_RE = re.compile(r"https?://github\.com/microprediction/([^/]+)/blob/[^/]+/(.+)")
RAW_RE = re.compile(r"https?://raw\.githubusercontent\.com/microprediction/([^/]+)/[^/]+/(.+)")
SITE_RE = re.compile(r"https?://([^/]+)/(.*)")


# ---------------------------------------------------------------- sites -> repos
def host_map() -> dict[str, tuple[Path, str]]:
    """host -> (repo dir, served subdir). Prefers the repo named after the host's first label."""
    found: dict[str, list[tuple[Path, str]]] = {}
    for repo in GITHUB.iterdir():
        if not repo.is_dir():
            continue
        for sub in ("docs", ""):
            cname = repo / sub / "CNAME" if sub else repo / "CNAME"
            if cname.exists():
                host = cname.read_text().strip()
                if host:
                    found.setdefault(host, []).append((repo, sub))
    out = {}
    for host, cands in found.items():
        label = host.split(".")[0]
        exact = [c for c in cands if c[0].name == label]
        out[host] = (exact or sorted(cands, key=lambda c: len(c[0].name)))[0]
    return out


HOSTS = host_map()


def resolve_local(url: str):
    """Return (repo_dir, relative path) for a draft URL, or None."""
    m = GH_RE.match(url) or RAW_RE.match(url)
    if m:
        return GITHUB / m.group(1), m.group(2)
    m = SITE_RE.match(url)
    if m and m.group(1) in HOSTS:
        repo, sub = HOSTS[m.group(1)]
        rel = m.group(2).split("#")[0].split("?")[0]
        return repo, (f"{sub}/{rel}" if sub else rel)
    return None


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


def local_state(repo: Path, rel: str):
    """Last commit date over the file and same-stem .md/.tex sources; dirty flag; paths used."""
    if not repo.is_dir():
        return None
    stem = Path(rel).stem
    tracked = git(repo, "ls-files").splitlines()
    cands = [rel] if rel in tracked else []
    cands += [t for t in tracked if Path(t).stem == stem and Path(t).suffix in (".md", ".tex") and t != rel]
    if not cands:
        return {"paths": [rel], "date": None, "dirty": False, "missing": True}
    dates = [git(repo, "log", "-1", "--format=%cs", "--", c) for c in cands]
    dates = [d for d in dates if d]
    dirty = any(git(repo, "status", "--porcelain", "--", c) for c in cands)
    return {"paths": cands, "date": max(dates) if dates else None, "dirty": dirty, "missing": False}


# ---------------------------------------------------------------- arXiv
def load_cache() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def arxiv_info(aid: str, cache: dict, offline: bool):
    hit = cache.get(aid)
    if hit and (offline or datetime.fromisoformat(hit["fetched"]) > datetime.now(timezone.utc) - timedelta(days=1)):
        return hit
    if offline:
        return None
    try:
        with urllib.request.urlopen(f"https://export.arxiv.org/api/query?id_list={aid}", timeout=20) as r:
            xml = r.read()
    except Exception as e:  # network down: keep the stale cache if any
        return hit
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entry = ET.fromstring(xml).find("a:entry", ns)
    if entry is None or entry.find("a:id", ns) is None:
        return hit
    eid = entry.find("a:id", ns).text or ""
    vm = re.search(r"v(\d+)$", eid)
    info = {
        "id": aid,
        "version": int(vm.group(1)) if vm else None,
        "published": (entry.find("a:published", ns).text or "")[:10],
        "updated": (entry.find("a:updated", ns).text or "")[:10],
        "title": re.sub(r"\s+", " ", entry.find("a:title", ns).text or "").strip(),
        "fetched": datetime.now(timezone.utc).isoformat(),
    }
    cache[aid] = info
    return info


# ---------------------------------------------------------------- main
def main() -> int:
    offline = "--offline" in sys.argv
    papers = json.loads((ROOT / "papers.json").read_text())
    posted = json.loads(POSTED.read_text()) if POSTED.exists() else {}
    cache = load_cache()
    rows = []
    for theme in papers.get("themes", []):
        for p in theme.get("papers", []):
            links = p.get("links", [])
            urls = " ".join(l["url"] for l in links)
            ssrn_ids = [str(p["ssrn"])] if p.get("ssrn") else sorted(set(SSRN_RE.findall(urls)))
            arxiv_ids = [str(p["arxiv"])] if p.get("arxiv") else sorted(set(ARXIV_RE.findall(urls)))
            draft = next((l["url"] for l in links if l["label"] in ("latest draft", "pdf")), None)
            loc = resolve_local(draft) if draft else None
            # PDFs archived in this repo (papers/, workingpapers/) are copies, not sources:
            # their commit date says when they were filed here, so no drift is computed.
            local = local_state(*loc) if loc and loc[0] != ROOT else None
            if loc and loc[0] == ROOT:
                local = {"paths": [loc[1]], "date": None, "dirty": False, "missing": False, "archived": True}

            ssrn = [{"id": i, **posted.get("ssrn", {}).get(i, {})} for i in ssrn_ids]
            arx = [arxiv_info(i, cache, offline) or {"id": i} for i in arxiv_ids]
            posted_dates = [s.get("revised") or s.get("posted") for s in ssrn] + [a.get("updated") for a in arx]
            posted_dates = [d for d in posted_dates if d]
            latest_posted = max(posted_dates) if posted_dates else None

            if p.get("venue"):
                status = "published"
                if latest_posted and local and local.get("date") and local["date"] > latest_posted:
                    days = (date.fromisoformat(local["date"]) - date.fromisoformat(latest_posted)).days
                    status += f", local newer ({days}d)"
            elif not ssrn_ids and not arxiv_ids:
                status = "not posted"
            elif any(not (s.get("posted") or s.get("revised")) for s in ssrn) and not latest_posted:
                status = "unknown SSRN date"
            elif local is not None and local.get("archived"):
                status = "posted; draft archived here"
            elif local is None or local.get("missing") or not local.get("date"):
                status = "unresolved local"
            elif local["date"] > latest_posted:
                days = (date.fromisoformat(local["date"]) - date.fromisoformat(latest_posted)).days
                status = f"local newer ({days}d)"
            else:
                status = "in sync"
            if any(not (s.get("posted") or s.get("revised")) for s in ssrn) and status not in ("published", "unknown SSRN date"):
                status += ", SSRN date unknown"
            if local and local.get("dirty"):
                status += ", uncommitted"
            rows.append({
                "theme": theme.get("title"), "title": p["title"], "hidden": bool(p.get("hidden")),
                "venue": p.get("venue"), "date": p.get("date"),
                "ssrn": ssrn, "arxiv": arx, "local": local, "draft": draft, "status": status,
            })
    if not offline:
        CACHE.write_text(json.dumps(cache, indent=1))

    (ROOT / "status.json").write_text(json.dumps(rows, indent=1))

    def cell(x):
        return str(x).replace("|", "/")
    lines = ["# Posting status", "",
             f"Generated {date.today().isoformat()} by `.claude/skills/build-home-page/status.py`. "
             "SSRN dates come from `posted.json` (SSRN cannot be scraped); arXiv dates from the arXiv API; "
             "local dates are the last commit touching the draft or its .md/.tex source in the sibling repo.", "",
             "| theme | paper | local | SSRN | arXiv | status |", "|---|---|---|---|---|---|"]
    for r in rows:
        if r["hidden"]:
            continue
        ssrn = "; ".join(f"[{s['id']}](https://papers.ssrn.com/abstract={s['id']}) {s.get('revised') or s.get('posted') or '?'}" for s in r["ssrn"]) or "-"
        arx = "; ".join(f"[{a['id']}](https://arxiv.org/abs/{a['id']})" + (f" v{a['version']} {a['updated']}" if a.get("updated") else "") for a in r["arxiv"]) or "-"
        loc = (r["local"] or {}).get("date") or ("archived here" if (r["local"] or {}).get("archived") else "missing" if r["local"] else "-")
        lines.append(f"| {cell(r['theme'])} | {cell(r['title'])} | {loc} | {ssrn} | {arx} | {r['status']} |")
    counts = {}
    for r in rows:
        key = r["status"].split(" (")[0].split(",")[0]
        counts[key] = counts.get(key, 0) + 1
    lines += ["", "## Counts", ""] + [f"- {k}: {v}" for k, v in sorted(counts.items())]
    (ROOT / "STATUS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-len(counts) - 2:]))
    print(f"\nWrote {ROOT / 'STATUS.md'} and status.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
