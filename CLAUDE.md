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
| `_data/read.json` | Every book finished this year with its Goodreads star rating, written by the same script. The home page shows a "Review to come" placeholder card for each one that has no review |
| `_data/read_manual.json` | Hand-kept list of books finished this year that aren't on Goodreads (title, author, date, rating, cover). The script merges them into `read.json` and the goal count, and skips one once Goodreads lists the same title |
| `_data/reading.json` | Currently-reading shelf + yearly goal, rendered on the home page |
| `scripts/update_reading.py` | Refreshes `_data/reading.json` from Lindsey's public Goodreads RSS shelves (user 6818060) |
| `.github/workflows/currently-reading.yml` | Runs that script daily at about 7:17 AM Mountain and commits any change |
| `_layouts/`, `_includes/`, `assets/style.css` | Site design |
| `about.md` | The About page (a starting draft that Lindsey may edit) |

## Where reviews come from

Lindsey writes her reviews in her Obsidian vault at `~/Desktop/MyWorld/AI-GEN/reading-reviews-2026.md`. Each book is a `## *Title* — Author` section with **Finished**, **Rating** (★), cover image, **My Review**, **Favorite quote(s)**, **Would recommend to**, and an optional **Reading Playlist**. Sections still containing `_Add your review here_` are unwritten stubs. Skip those.

When converting a vault review into `_reviews/<slug>.md`:
- **Keep Lindsey's wording exactly.** Don't rewrite, polish or summarize her review, quotes or recommendations.
- `verdict` is the short teaser line on the card: a sentence, or a trimmed piece of one, lifted word for word from her review. Cut it down to the sharpest part, but never add or change words.
- `rating` comes from the number of ★. `date` is the Finished date (YYYY-MM-DD). Use the cover URL from the vault in `cover`.
- Don't publish the **Reading Playlist**; Lindsey had playlists removed from the site (2026-10-06).
- `goodreads_id` is the book's id from `_data/read.json` (the number in its Goodreads URL), quoted as a string. It is what swaps a book's placeholder card for the real review card, so always set it.
- `genre` and `series` are optional, factual labels.
- `vibes` are short tags (shown as chips, searchable on the home page). Build them from phrases in her review and recommendation, not new descriptions.
- `why` ("Why I picked it up") is only filled in when she states the reason herself: a **Why I picked it up** line in the vault, or a sentence in the review that says it. Otherwise leave it out.
- `part_of` groups reviews into a reading project; reviews sharing a label link to each other. Current labels: "Tracking the International Booker Prize", "The Abhorsen series", "My Mona Awad micro-obsession", "Obsession stories". Reuse the exact label text.
- Published so far: every written review in the vault as of 2026-10-06 (18). Check `_reviews/` against the vault for new ones.

## Conventions

- Lindsey works in Mountain Time.
- The vault has its own CLAUDE.md; follow it when working inside the vault. This repo should only ever read from the vault, never write to it.
- After changes: commit with a clear message and push to `main`. Pages redeploys in a minute or two.
