# Lids Reads

Book reviews by Lindsey, published with GitHub Pages at **https://itslids.github.io/lids-reads/**.

## Adding a review

1. Copy `templates/review-template.md` into `_reviews/` and name it after the book, e.g. `_reviews/bleak-house.md`. The file name becomes the page address: `/reviews/bleak-house/`.
2. Fill in the details at the top (title, author, date finished, rating, and optionally an ISBN for the cover) and write the review below them.
3. Commit and push. The site rebuilds itself within a minute or two.

## Settings

- `_config.yml`: site title, tagline, and `substack_url`. Fill that in once the newsletter exists to add a "Newsletter" link.
- `about.md`: the About page.
- `assets/style.css`: colors and fonts.

New reviews also appear in the RSS feed at `/feed/reviews.xml`.

## Currently reading

The "Currently reading" shelf and the yearly goal on the home page come from `_data/reading.json`. A GitHub Action (`.github/workflows/currently-reading.yml`) refreshes that file every morning from Lindsey's public Goodreads shelves, using `scripts/update_reading.py`. To refresh it on demand, open **Actions → Update currently reading → Run workflow**.
