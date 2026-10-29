#!/usr/bin/env python3
"""
update_reading.py: refreshes the "Currently reading" shelf and the books-read list of Lids Reads.

Reads Lindsey's Hardcover shelves through the Hardcover API (Goodreads turned off its
RSS feeds in October 2026) and writes _data/reading.json and _data/read.json.
Needs her Hardcover API key in the HARDCOVER_TOKEN environment variable (a repository
secret on GitHub). Runs twice a day via .github/workflows/currently-reading.yml, or by hand:
    HARDCOVER_TOKEN=... python scripts/update_reading.py
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API = "https://api.hardcover.app/v1/graphql"
GOAL = 100
YEAR = datetime.now(timezone.utc).year
OUT = os.path.join(os.path.dirname(__file__), "..", "_data", "reading.json")
READ_OUT = os.path.join(os.path.dirname(__file__), "..", "_data", "read.json")
MANUAL = os.path.join(os.path.dirname(__file__), "..", "_data", "read_manual.json")

CURRENTLY_READING, READ = 2, 3   # Hardcover status ids

BOOK_FIELDS = "id title slug pages release_year rating cached_contributors image { url }"
QUERY = """
query($since: date!) {
  me {
    current: user_books(where: {status_id: {_eq: %d}}, order_by: {updated_at: desc}) {
      book { %s }
    }
    finished: user_books(where: {status_id: {_eq: %d}, last_read_date: {_gte: $since}},
                         order_by: {last_read_date: desc}) {
      rating last_read_date
      book { %s }
    }
  }
}
""" % (CURRENTLY_READING, BOOK_FIELDS, READ, BOOK_FIELDS)


def fetch():
    token = os.environ.get("HARDCOVER_TOKEN", "").strip()
    if not token:
        sys.exit("HARDCOVER_TOKEN is not set")
    if not token.lower().startswith("bearer "):
        token = "Bearer " + token
    body = json.dumps({"query": QUERY, "variables": {"since": f"{YEAR}-01-01"}}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "content-type": "application/json", "authorization": token, "user-agent": "lids-reads"})
    for attempt in range(3):   # ride out a brief Hardcover hiccup
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.load(r)
            break
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                raise
            print(f"Hardcover request failed ({e}), retrying")
            time.sleep(20)
    if res.get("errors"):
        sys.exit(f"Hardcover API error: {res['errors']}")
    me = res["data"]["me"]
    return me[0] if isinstance(me, list) else me


def clean_title(t):
    t = re.sub(r"\s*\([^)]*#\d+[^)]*\)\s*$", "", t)   # drop "(Series, #1)"
    return t.split(":")[0].strip()                    # drop subtitles


def key(title):
    return title.lower().replace("\u2019", "'")   # curly and straight apostrophes match


def author(book):
    for c in book.get("cached_contributors") or []:
        name = (c.get("author") or {}).get("name")
        if name:
            return " ".join(name.split())
    return ""


def cover(book):
    return (book.get("image") or {}).get("url") or ""


def main():
    me = fetch()

    # Reviews link to books by the id in read.json. Books that were already listed keep
    # their old (Goodreads) id so existing reviews stay matched; new ones get "hc-<id>".
    old = {}
    if os.path.exists(READ_OUT):
        for b in json.load(open(READ_OUT)).get("books", []):
            old[key(b["title"])] = b

    books = []
    for ub in me["finished"]:
        bk = ub["book"]
        title = clean_title(bk["title"])
        prev = old.get(key(title), {})
        books.append({
            "id": prev.get("id") or f"hc-{bk['id']}",
            "title": title, "author": author(bk),
            "cover": prev.get("cover") or cover(bk),
            "rating": ub["rating"] or 0, "date": ub["last_read_date"],
            "pages": bk.get("pages") or prev.get("pages") or 0,
            "published": bk.get("release_year") or prev.get("published") or 0,
            "avg_rating": round(bk.get("rating") or 0, 2),
        })

    # books finished this year that Hardcover doesn't have; dropped once Hardcover lists them
    if os.path.exists(MANUAL):
        seen = {key(b["title"]) for b in books}
        for m in json.load(open(MANUAL)):
            if m["date"].startswith(str(YEAR)) and key(m["title"]) not in seen:
                books.append({"id": "manual-" + re.sub(r"[^a-z0-9]+", "-", m["title"].lower()).strip("-"),
                              "title": m["title"], "author": m["author"], "cover": m.get("cover", ""),
                              "rating": m.get("rating", 0), "date": m["date"],
                              "pages": m.get("pages", 0), "published": m.get("published", 0),
                              "avg_rating": 0})
    books.sort(key=lambda b: b["date"], reverse=True)

    data = {
        "updated": datetime.now(ZoneInfo("America/Denver")).strftime("%Y-%m-%d"),  # Lindsey's day, not UTC
        "year": YEAR,
        "goal": GOAL,
        "read_this_year": len(books),
        "currently_reading": [
            {"title": clean_title(ub["book"]["title"]), "author": author(ub["book"]), "cover": cover(ub["book"]),
             "link": f"https://hardcover.app/books/{ub['book']['slug']}" if ub["book"].get("slug") else ""}
            for ub in me["current"]
        ],
    }
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    # every book finished this year, newest first; the home page shows a placeholder card
    # for any that has no review yet (matched to reviews by goodreads_id)
    with open(READ_OUT, "w") as f:
        json.dump({"year": YEAR, "books": books}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"{len(data['currently_reading'])} currently reading, {len(books)} read in {YEAR}")


if __name__ == "__main__":
    main()
