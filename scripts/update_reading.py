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

GOODREADS_USER_ID = "6818060"
GOAL = 100
YEAR = datetime.now(timezone.utc).year
OUT = os.path.join(os.path.dirname(__file__), "..", "_data", "reading.json")


def fetch(shelf, page=1):
    url = (f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}"
           f"?shelf={shelf}&per_page=200&page={page}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    items = []
    for it in root.find("channel").findall("item"):
        g = lambda t: ((it.find(t).text or "").strip() if it.find(t) is not None else "")
        items.append({k: g(k) for k in ("title", "author_name", "book_large_image_url",
                                        "book_image_url", "book_id", "user_read_at", "user_date_added")})
    return items


def parse_date(s):
    try:
        return datetime.strptime(s, "%a, %d %b %Y %H:%M:%S %z")
    except (ValueError, TypeError):
        return None


def clean_title(t):
    t = re.sub(r"\s*\([^)]*#\d+[^)]*\)\s*$", "", t)   # drop "(Series, #1)"
    return t.split(":")[0].strip()                    # drop subtitles


def cover(item):
    url = item["book_large_image_url"] or item["book_image_url"]
    return "" if (not url or "nophoto" in url) else url


def main():
    current = fetch("currently-reading")
    current.sort(key=lambda b: parse_date(b["user_date_added"]) or datetime.min.replace(tzinfo=timezone.utc),
                 reverse=True)

    read_count, page = 0, 1
    while True:
        books = fetch("read", page)
        dates = [parse_date(b["user_read_at"]) for b in books]
        read_count += sum(1 for d in dates if d and d.year == YEAR)
        known = [d for d in dates if d]
        if len(books) < 200 or (known and min(known).year < YEAR):
            break
        page += 1

    data = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
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
    print(f"{len(data['currently_reading'])} currently reading, {read_count} read in {YEAR}")


if __name__ == "__main__":
    main()
