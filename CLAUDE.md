# Lids Reads — project notes for Claude

Lindsey's ("Lids") public book review site, built with Jekyll and published by GitHub Pages.

- Repo: `itslids/lids-reads` (public)
- Live site: https://itslids.github.io/lids-reads/ (`baseurl: /lids-reads`)
- Pages source: branch `main`, folder `/ (root)`. GitHub builds the site; there's no local build step and no Gemfile.

## Layout

| Path | What it is |
|---|---|
| `_reviews/*.md` | One file per review; the file name becomes the URL (`/reviews/<name>/`) |
| `templates/review-template.md` | The front matter fields a review can use |
| `_data/reading.json` | Currently-reading shelf + yearly goal, rendered on the home page |
| `scripts/update_reading.py` | Refreshes `_data/reading.json` from Lindsey's public Goodreads RSS shelves (user 6818060) |
| `.github/workflows/currently-reading.yml` | Runs that script daily at about 7:17 AM Mountain and commits any change |
| `_layouts/`, `_includes/`, `assets/style.css` | Site design |
| `about.md` | The About page (a starting draft that Lindsey may edit) |

## Where reviews come from

Lindsey writes her reviews in her Obsidian vault at `~/Desktop/MyWorld/AI-GEN/reading-reviews-2026.md`. Each book is a `## *Title* — Author` section with **Finished**, **Rating** (★), cover image, **My Review**, **Favorite quote(s)**, **Would recommend to**, and an optional **Reading Playlist**. Sections still containing `_Add your review here_` are unwritten stubs. Skip those.

When converting a vault review into `_reviews/<slug>.md`:
- **Keep Lindsey's wording exactly.** Don't rewrite, polish or summarize her review, quotes or recommendations.
- `verdict` is a single sentence copied word for word from her review, never a paraphrase.
- `rating` comes from the number of ★. `date` is the Finished date (YYYY-MM-DD). Use the cover URL from the vault in `cover`.
- Drop `utm_*` and other tracking parameters from Spotify links.
- `genre` and `series` are optional, factual labels.
- Published so far: Normal People, American Fantasy, Among the Thugs, 13 Ways of Looking at a Fat Girl, Lirael.

## Conventions

- Lindsey works in Mountain Time.
- The vault has its own CLAUDE.md; follow it when working inside the vault. This repo should only ever read from the vault, never write to it.
- After changes: commit with a clear message and push to `main`. Pages redeploys in a minute or two.
