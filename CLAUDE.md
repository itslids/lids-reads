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
| `.github/workflows/currently-reading.yml` | Runs that script twice a day, at about 7:17 AM and 6:17 PM Mountain, and commits any change |
| `_layouts/`, `_includes/`, `assets/style.css` | Site design |
| `stats.html` | The Stats page: charts and numbers computed in the browser from `_data/read.json` (books, pages, pace, ratings, authors) |
| `about.md` | The About page. Lindsey approved this wording line by line (2026-10-07); don't reword it without her |

## Where reviews come from

As of 2026-10-26 this repo is the gold copy of Lindsey's reviews. She no longer keeps them in Obsidian (the old vault file, `~/Desktop/MyWorld/AI-GEN/reading-reviews-2026.md`, is retired).

The workflow:
1. She finishes a book and marks it read on Goodreads. The Action (twice a day) adds it to `_data/read.json`, and the home page shows a "Review to come" card.
2. A Claude scheduled task checks twice a day (about 7:36 AM and 6:36 PM Mountain) for books in `read.json` with no review, and reminds her in her Lids Reads Claude project.
3. She writes the review there: rating, format, review, favorite quote(s), who she'd recommend it to, and optionally why she picked it up. Rough notes are fine.
4. Claude turns it into `_reviews/<slug>.md` using the rules below, shows her the draft, and commits and pushes only after her explicit OK.

When turning her review into `_reviews/<slug>.md`:
- **Keep Lindsey's wording exactly.** Don't rewrite, polish or summarize her review, quotes or recommendations.
- `verdict` is the short teaser line on the card: a sentence, or a trimmed piece of one, lifted word for word from her review. Cut it down to the sharpest part, but never add or change words.
- `rating` comes from the number of ★. `date` is the Finished date (YYYY-MM-DD). Use the cover URL from `_data/read.json` in `cover`.
- Don't publish the **Reading Playlist**; Lindsey had playlists removed from the site (2026-10-06).
- `goodreads_id` is the book's id from `_data/read.json` (the number in its Goodreads URL), quoted as a string. It is what swaps a book's placeholder card for the real review card, so always set it.
- `genre` and `series` are optional, factual labels.
- `format` is how she read it, one of `audio`, `ebook`, `physical`, or two joined with ` + ` (audio first). Don't add "(library)": everything she reads comes from the library (print copies or the library app), so it isn't tracked per book. Goodreads doesn't record this, so ask her for it if she leaves it out. The Stats page charts it.
- `vibes` are short tags (shown as chips, searchable on the home page). Build them from phrases in her review and recommendation, not new descriptions.
- `why` ("Why I picked it up") is only filled in when she states the reason herself: a "why I picked it up" line in what she sends, or a sentence in the review that says it. Otherwise leave it out.
- `part_of` groups reviews into a reading project; reviews sharing a label link to each other. Current labels: "Tracking the International Booker Prize", "The Abhorsen series", "My Mona Awad micro-obsession", "My Claire Keegan obsession", "The Maze Runner series", "Obsession stories". Reuse the exact label text.

## Conventions

- Lindsey works in Mountain Time.
- Never put her children's names on the site (her instruction, 2026-10-08). Write "my kid", not "my daughter" or "my son" (her instruction, 2026-10-08).
- After changes: commit with a clear message and push to `main`. Pages redeploys in a minute or two.
