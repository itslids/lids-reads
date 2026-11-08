#!/usr/bin/env python3
"""
update_reading.py: refreshes the "Currently reading" shelf and the books-read list of Lids Reads.

Reads Lindsey's Hardcover shelves through the Hardcover API (Goodreads turned off its
RSS feeds in October 2026) and writes _data/reading.json and _data/read.json.
Also reads her "Little Lids: <kid>" Hardcover lists (one per kid, books they finished, added
to the list but not marked Read, so they stay out of her own count) into _data/little_read.json.
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
LITTLE_OUT = os.path.join(os.path.dirname(__file__), "..", "_data", "little_read.json")
LITTLE_LIST = "Little Lids"   # each kid's list is "Little Lids: <nickname>" (any capitalization)

CURRENTLY_READING, READ = 2, 3   # Hardcover status ids

BOOK_FIELDS = "id title slug pages release_year rating cached_contributors image { url }"
QUERY = """
query($since: date!) {
  me {
    current: user_books(where: {status_id: {_eq: %d}}, order_by: {updated_at: desc}) {
      edition { image { url } }
      book { %s }
    }
    finished: user_books(where: {status_id: {_eq: %d}, last_read_date: {_gte: $since}},
                         order_by: {last_read_date: desc}) {
      rating last_read_date
      edition { image { url } }
      book { %s }
    }
  }
}
""" % (CURRENTLY_READING, BOOK_FIELDS, READ, BOOK_FIELDS)

# Hardcover doesn't allow name searches (ilike), so this takes all her lists and the
# script keeps the "Little Lids: ..." ones. Tags she puts on a book come back as taggings.
LITTLE_QUERY = """
{
  me {
    lists(order_by: {name: asc}) {
      name
      list_books(order_by: {date_added: desc}) {
        date_added reason
        edition { image { url } }
        book { %s }
      }
    }
    taggings(where: {taggable_type: {_eq: "Book"}}, order_by: {created_at: asc}) {
      taggable_id created_at tag { tag }
    }
  }
}
""" % BOOK_FIELDS


def fetch(query=QUERY, variables=None):
    token = os.environ.get("HARDCOVER_TOKEN", "").strip()
    if not token:
        sys.exit("HARDCOVER_TOKEN is not set")
    if not token.lower().startswith("bearer "):
        token = "Bearer " + token
    if variables is None:
        variables = {"since": f"{YEAR}-01-01"}
    body = json.dumps({"query": query, "variables": variables}).encode()
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


def cover(ub):
    # the edition she shelved on Hardcover, falling back to the book's default cover
    for src in (ub.get("edition"), ub["book"]):
        url = ((src or {}).get("image") or {}).get("url")
        if url:
            return url
    return ""


def year(y):
    """A plausible publication year, or 0."""
    return y if isinstance(y, int) and 1000 <= y <= YEAR + 1 else 0


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
            "cover": prev.get("cover") or cover(ub),
            "rating": ub["rating"] or 0, "date": ub["last_read_date"],
            "pages": bk.get("pages") or prev.get("pages") or 0,
            # Hardcover's release_year is often an edition's year (or junk like 4), so a year
            # already in read.json wins; fix a wrong year by editing read.json and it sticks
            "published": prev.get("published") or year(bk.get("release_year")),
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
            {"title": clean_title(ub["book"]["title"]), "author": author(ub["book"]), "cover": cover(ub),
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
    try:   # the kids' page is extra; never let it break Lindsey's own shelves
        write_little(fetch(LITTLE_QUERY, {}))
    except (Exception, SystemExit) as e:
        print(f"Skipped Little Lids: {e}")


def tag_key(t):
    return re.sub(r"[^a-z]", "", t.lower())


def is_reading_now(tag):
    # "Reading Now", "reading now", even the "Readig Now" typo
    k = tag_key(tag)
    return k.endswith("now") and k.startswith("read")


def local_day(ts):
    """A Hardcover timestamp (UTC) as Lindsey's calendar day."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Denver")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return (ts or "")[:10]


def write_little(me):
    """One section per "Little Lids: <nickname>" list. A book tagged "Reading Now" in Hardcover goes on
    that kid's Reading now shelf; everything else counts as finished, dated by its "Finished" tag
    (or, without one, by when it was added to the list)."""
    prefix = tag_key(LITTLE_LIST)
    lists = [l for l in me.get("lists") or [] if tag_key(l["name"]).startswith(prefix)]
    if not lists:
        print(f'No Hardcover list named "{LITTLE_LIST}: ..." yet; leaving {os.path.basename(LITTLE_OUT)} alone')
        return
    tags = {}   # book id -> {tag key: (tag, day tagged)}, latest tagging wins
    for t in me.get("taggings") or []:
        tags.setdefault(t["taggable_id"], {})[tag_key(t["tag"]["tag"])] = (t["tag"]["tag"], local_day(t.get("created_at")))
    kids = []
    for lst in lists:
        label = lst["name"][len(LITTLE_LIST):].strip(" :-\u2013\u2014") or LITTLE_LIST
        reading, finished = [], []
        for lb in lst["list_books"]:
            bk = lb["book"]
            btags = tags.get(bk["id"], {})
            book = {
                # keep subtitles: kids' series books are often only told apart by them ("Dog Man: Fetch-22")
                "id": f"hc-{bk['id']}", "title": re.sub(r"\s*\([^)]*#\d+[^)]*\)\s*$", "", bk["title"]).strip(),
                "author": author(bk), "cover": cover(lb), "pages": bk.get("pages") or 0,
                "note": (lb.get("reason") or "").strip(),   # the note on the list entry, shown on the card
            }
            if any(is_reading_now(t) for t, _ in btags.values()):
                reading.append(book)
            else:
                book["date"] = (btags.get("finished") or (None, ""))[1] or local_day(lb.get("date_added"))
                finished.append(book)
        finished.sort(key=lambda b: b["date"], reverse=True)
        kids.append({"name": label, "slug": re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-"),
                     "reading": reading, "books": finished})
    with open(LITTLE_OUT, "w") as f:
        json.dump({"kids": kids}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("Little Lids: " + ", ".join(f"{k['name']} {len(k['reading'])} reading, {len(k['books'])} finished" for k in kids))

if __name__ == "__main__":
    main()
