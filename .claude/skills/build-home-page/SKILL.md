---
name: build-home-page
description: Rebuild the home.microprediction.org GitHub Pages site (Peter Cotton's publications page) from papers.json. Use when asked to update the home page / publications list, add or refresh a paper, pull in newer drafts or arXiv links from the package repos (schur / humpday / precise / mechanics / skaters .microprediction.org), or regenerate docs/index.html. Run from the microprediction/home repo.
---

# Build home.microprediction.org

An academic publications page generated from data. Organized by **research theme**
(related work sits together); within each theme, published work / preprints come
first, then the most recent working drafts. Restrained academic styling — serif,
low bold, abstracts in collapsed `<details>`.

## Files

| File | Role |
|------|------|
| `papers.json` (repo root) | **Source of truth.** `site`, `book_length[]`, `themes[]` (each with `papers[]`), `software[]`, `talks[]`, `patents[]`, `more[]`. **Edit this.** |
| `abstracts.json` (repo root) | Generated cache of **real** abstracts keyed by title. Committed so CI needn't extract. |
| `scan.py` | Read-only. Scans `../{schur,humpday,precise,mechanics,skaters}` for draft PDFs/TeX + arXiv ids. |
| `extract_abstracts.py` | Local only (needs pdftotext + sibling repos). Pulls real abstracts → `abstracts.json`. |
| `build.py` | Renders `papers.json` + `abstracts.json` → `docs/index.html`, `docs/academic.css`, `docs/CNAME`. Pure stdlib; runs in CI. |

## Paper entry

```json
{ "title": "...", "venue": "SIAM J. Financial Math., 2021",
  "draft_new": true, "abstract_source": "https://github.com/.../x.tex",
  "links": [ {"label":"arXiv","url":"..."}, {"label":"latest draft","url":"..."} ] }
```
- `venue` present ⇒ published (rendered italic). List the canonical link (`arXiv`/`journal`) **first**.
- `latest draft` label is highlighted; use a **PDF** url, never a raw `.tex`.
- `draft_in_progress: true` shows a muted "draft in progress" note (no link).
- `abstract_source` = a local file to extract the abstract from when it isn't one of the entry's links (e.g. a TeX with no public PDF).

## Procedure

1. **Find what's new / verify arXiv ids** — `python3 scan.py`. To confirm an
   arXiv id belongs to Peter (vs. someone citing him), check the author:
   `curl -s "https://export.arxiv.org/api/query?search_query=au:%22Peter+Cotton%22&max_results=40"`.
2. **Edit `papers.json`** — add/move papers into the right theme, published-first;
   add arXiv/journal/draft links. Don't invent abstracts or arXiv pairings.
3. **Abstracts** — `python3 extract_abstracts.py` (local). It writes only abstracts
   it can extract verbatim; papers without a clean source get none (that's fine —
   never fabricate). To add a missing one, paste the real text into `abstracts.json`.
4. **Build** — `python3 build.py`. Then `open docs/index.html` to review.
5. **Publish** — commit `papers.json`, `abstracts.json` and the skill. The Pages
   workflow runs `build.py` and deploys `docs/`. DNS already points
   `home.microprediction.org` → `microprediction.github.io`.

## Notes

- `docs/index.html`, `docs/academic.css`, `docs/CNAME` are generated and gitignored.
- Restyle: edit `CSS` in `build.py`.
