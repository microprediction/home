---
name: build-home-page
description: Rebuild the home.microprediction.org GitHub Pages site (Peter Cotton's papers index) from papers.json. Use when asked to update the home page / papers list, add or refresh a working paper, pull in newer drafts or arXiv links from the package repos (schur / humpday / precise / mechanics / skaters .microprediction.org), or regenerate docs/index.html. Run from the microprediction/home repo.
---

# Build home.microprediction.org

A small data-driven static-site generator for Peter Cotton's papers page.
`papers.json` (repo root) is the single source of truth; `scan.py` discovers
what's new in the sibling package repos; `build.py` renders the site into
`docs/`. The site distinguishes the **canonical** version of each paper (arXiv /
journal) from the **latest draft**, which usually lives in a package repo and
moves faster.

## Files

| File | Role |
|------|------|
| `../../../papers.json` (repo root) | Source of truth: site meta, sections, one entry per paper. **Edit this.** |
| `scan.py` | Read-only. Scans `../{schur,humpday,precise,mechanics,skaters}` for draft PDFs/TeX (with mod dates) and arXiv ids. Writes `scan_report.json`. |
| `build.py` | Renders `papers.json` → `docs/index.html`, `docs/academic.css`, `docs/CNAME`. |
| `academic_base.css` | Shared base stylesheet (kept in sync with the package sites); `build.py` prepends it. |

## Procedure

1. **Scan for what's new** — `python3 scan.py`. Read the summary (and
   `scan_report.json`). Look for: draft files with a newer `modified` date than
   what `papers.json` links, new draft titles, and arXiv ids that belong to
   Peter's own papers (most ids in `.bib` files are *references* — don't add
   those).

2. **Reconcile into `papers.json`.** For each paper entry:
   - `draft` = URL of the most recent draft. When it lives in a package repo,
     use the GitHub blob URL the scan prints (`.../blob/main/papers/X.pdf`).
   - Set `"draft_new": true` when that draft is newer than the arXiv/journal
     version — it renders as a highlighted **latest draft** badge.
   - Keep `arxiv` (bare id, e.g. `2411.05807`) and `journal` (full URL) on the
     canonical version.
   - Optional fields: `blog`, `talk`, `site`, `package`, `abstract`, `year`,
     `tags`. Omit anything that doesn't apply.
   - `section` must be one of the ids in the `sections` array
     (`working` / `papers` / `book` / `preworking`). Add a section there first
     if you need a new one.
   - Don't invent arXiv↔draft pairings you're unsure of — leave a paper with just
     a `draft` link rather than guess.

3. **Build** — `python3 build.py`. It overwrites `docs/index.html`,
   `docs/academic.css`, `docs/CNAME` (= `home.microprediction.org`).

4. **Show the result** and let Peter review. The DNS for
   `home.microprediction.org` already points at `microprediction.github.io`;
   GitHub Pages must be set to serve from the `docs/` folder on `main`.
   **Do not commit or push unless asked** — Peter handles publishing.

## Adding a new package subdomain

Add its name to `TARGETS` in `scan.py`. The scan reads each repo's
`docs/CNAME` for the live URL automatically.

## Notes

- Pure standard-library Python 3; no dependencies.
- PDFs at the repo root (`workingpapers/`, `papers/`) are **not** served by
  Pages (which only serves `docs/`), so link them via `github.com/.../blob/...`
  URLs, as the seed entries do.
- To restyle, edit `EXTRA_CSS` in `build.py` (page-specific) or
  `academic_base.css` (shared look with the package sites).
