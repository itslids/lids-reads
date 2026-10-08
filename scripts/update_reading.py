#!/usr/bin/env python3
"""
update_reading.py: refreshes the "Currently reading" section of Lids Reads.

Pulls Lindsey's public Goodreads shelves via RSS (the same feeds her Obsidian
update_reading.py uses) and writes _data/reading.json, which the home page renders.
Runs daily via .github/workflows/currently-reading.yml, or by hand:
    python scripts/update_reading.py
"""
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

GOODREADS_USER_ID = "6818060"
GOAL = 100
YEAR = datetime.now(timezone.utc).year
OUT = os.path.join(os.path.dirname(__file__), "..", "_data", "reading.json")
READ_OUT = os.path.join(os.path.dirname(__file__), "..", "_data", "read.json")
MANUAL = os.path.join(os.path.dirname(__file__), "..", "_data", "read_manual.json")


def fetch(shelf, page=1):
    url = (f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}"
           f"?shelf={shelf}&per_page=200&page={page}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    items = []
    for it in root.find("channel").findall("item"):
        g = lambda t: ((it.find(t).text or "").strip() if it.find(t) is not None else "")
        item = {k: g(k) for k in ("title", "author_name", "book_large_image_url",
                                  "book_image_url", "book_id", "user_read_at", "user_date_added",
                                  "user_rating", "average_rating", "book_published")}
        pages = it.find("book/num_pages")
        item["num_pages"] = (pages.text or "").strip() if pages is not None else ""
        items.append(item)
    return items


def parse_date(s):
    try:
        return datetime.strptime(s, "%a, %d %b %Y %H:%M:%S %z")
    except (ValueError, TypeError):
        return None


def clean_title(t):
    t = re.sub(r"\s*\([^)]*#\d+[^)]*\)\s*$", "", t)   # drop "(Series, #1)"
    return t.split(":")[0].strip()                    # drop subtitles


def num(s):
    m = re.search(r"\d+", s or "")
    return int(m.group()) if m else 0


def cover(item):
    url = item["book_large_image_url"] or item["book_image_url"]
    return "" if (not url or "nophoto" in url) else url


def main():
    current = fetch("currently-reading")
    current.sort(key=lambda b: parse_date(b["user_date_added"]) or datetime.min.replace(tzinfo=timezone.utc),
                 reverse=True)

    read_count, page, finished = 0, 1, []
    while True:
        books = fetch("read", page)
        dates = [parse_date(b["user_read_at"]) for b in books]
        read_count += sum(1 for d in dates if d and d.year == YEAR)
        finished += [(d, b) for d, b in zip(dates, books) if d and d.year == YEAR]
        known = [d for d in dates if d]
        if len(books) < 200 or (known and min(known).year < YEAR):
            break
        page += 1

    # books finished this year that Goodreads doesn't have; dropped once the feed lists them
    books = [
        {"id": b["book_id"], "title": clean_title(b["title"]), "author": " ".join(b["author_name"].split()),
         "cover": cover(b), "rating": int(b["user_rating"] or 0), "date": d.strftime("%Y-%m-%d"),
         "pages": num(b["num_pages"]), "published": num(b["book_published"]),
         "avg_rating": float(b["average_rating"] or 0)}
        for d, b in finished
    ]
    if os.path.exists(MANUAL):
        seen = {b["title"].lower() for b in books}
        for m in json.load(open(MANUAL)):
            if m["date"].startswith(str(YEAR)) and m["title"].lower() not in seen:
                books.append({"id": "manual-" + re.sub(r"[^a-z0-9]+", "-", m["title"].lower()).strip("-"),
                              "title": m["title"], "author": m["author"], "cover": m.get("cover", ""),
                              "rating": m.get("rating", 0), "date": m["date"],
                              "pages": m.get("pages", 0), "published": m.get("published", 0),
                              "avg_rating": 0})
    books.sort(key=lambda b: b["date"], reverse=True)
    read_count = len(books)

    data = {
        "updated": datetime.now(ZoneInfo("America/Denver")).strftime("%Y-%m-%d"),  # Lindsey's day, not UTC
        "year": YEAR,
        "goal": GOAL,
        "read_this_year": read_count,
        "currently_reading": [
            {"title": clean_title(b["title"]), "author": b["author_name"], "cover": cover(b),
             "link": f"https://www.goodreads.com/book/show/{b['book_id']}" if b["book_id"] else ""}
            for b in current
        ],
    }
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    # every book finished this year, newest first; the home page shows a placeholder card
    # for any that has no review yet (matched to reviews by goodreads_id)
    read = {"year": YEAR, "books": books}
    with open(READ_OUT, "w") as f:
        json.dump(read, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"{len(data['currently_reading'])} currently reading, {read_count} read in {YEAR}")


if __name__ == "__main__":
    main()
