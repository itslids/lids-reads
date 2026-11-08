#!/usr/bin/env python3
"""
update_reading.py: refreshes the "Currently reading" shelf and the books-read list of Lids Reads.

Reads Lindsey's Hardcover shelves through the Hardcover API (Goodreads turned off its
RSS feeds in October 2026) and writes _data/reading.json and _data/read.json.
Also reads her "Little Lids: <kid> Reading Now" and "Little Lids: <kid> Finished" Hardcover lists
(two per kid; books on them are not marked Read, so they stay out of her own count) into
_data/little_read.json, and her husband's "Lids Better Half: Reading Now", "... Next On Deck" and
"... Finished" lists (mostly audiobooks) into _data/better_half.json.
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
LITTLE_LIST = "Little Lids"   # lists are "Little Lids: <nickname> Reading Now" / "... Finished"
HALF_OUT = os.path.join(os.path.dirname(__file__), "..", "_data", "better_half.json")
HALF_AUDIO = os.path.join(os.path.dirname(__file__), "..", "_data", "better_half_audio.json")
HALF_LIST = "Lids Better Half"   # lists are "Lids Better Half: Reading Now" / "... Next On Deck" / "... Finished"

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
# script keeps the "Little Lids: ..." ones.
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
  }
}
""" % BOOK_FIELDS

# Her husband's lists. The edition she put on the list says whether it's the audiobook,
# and gives its narrator and length.
HALF_QUERY = """
{
  me {
    lists(order_by: {name: asc}) {
      name
      list_books(order_by: {date_added: desc}) {
        date_added reason
        edition { audio_seconds cached_contributors image { url } }
        book { %s audio_seconds }
      }
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
    try:   # same for her husband's page
        write_better_half(fetch(HALF_QUERY, {}))
    except (Exception, SystemExit) as e:
        print(f"Skipped Lids Better Half: {e}")


def name_key(t):
    return re.sub(r"[^a-z]", "", t.lower())


def local_day(ts):
    """A Hardcover timestamp (UTC) as Lindsey's calendar day."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Denver")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return (ts or "")[:10]


def write_little(me):
    """One section per kid, from her "Little Lids: <nickname> Reading Now" and "Little Lids: <nickname> Finished"
    lists. A finished book is dated by when it was added to the Finished list. A book on both lists counts
    as finished."""
    prefix = name_key(LITTLE_LIST)
    kids = {}   # nickname -> {"reading": [...], "books": [...]}, in list-name order
    for lst in me.get("lists") or []:
        if not name_key(lst["name"]).startswith(prefix):
            continue
        rest = lst["name"].strip()[len(LITTLE_LIST):].strip(" :-\u2013\u2014")
        m = re.match(r"(.*?)[\s:\-\u2013\u2014(]*(reading\s*now|finished)\)?$", rest, re.I)
        if not m or not m.group(1).strip():
            print(f'Skipping list "{lst["name"]}": expected "{LITTLE_LIST}: <name> Reading Now" or "... Finished"')
            continue
        label, shelf = m.group(1).strip(), ("books" if m.group(2).lower() == "finished" else "reading")
        kid = kids.setdefault(label, {"reading": [], "books": []})
        for lb in lst["list_books"]:
            bk = lb["book"]
            book = {
                # keep subtitles: kids' series books are often only told apart by them ("Dog Man: Fetch-22")
                "id": f"hc-{bk['id']}", "title": re.sub(r"\s*\([^)]*#\d+[^)]*\)\s*$", "", bk["title"]).strip(),
                "author": author(bk), "cover": cover(lb), "pages": bk.get("pages") or 0,
                "note": (lb.get("reason") or "").strip(),   # the note on the list entry, shown on the card
            }
            if shelf == "books":
                book["date"] = local_day(lb.get("date_added"))
            kid[shelf].append(book)
    if not kids:
        print(f'No "{LITTLE_LIST}: ..." lists on Hardcover yet; leaving {os.path.basename(LITTLE_OUT)} alone')
        return
    out = []
    for label, kid in kids.items():
        done = {b["id"] for b in kid["books"]}
        kid["reading"] = [b for b in kid["reading"] if b["id"] not in done]
        kid["books"].sort(key=lambda b: b["date"], reverse=True)
        out.append({"name": label, "slug": re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-"),
                    "reading": kid["reading"], "books": kid["books"]})
    with open(LITTLE_OUT, "w") as f:
        json.dump({"kids": out}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("Little Lids: " + ", ".join(f"{k['name']} {len(k['reading'])} reading, {len(k['books'])} finished" for k in out))


def narrator(edition):
    names = [" ".join(((c.get("author") or {}).get("name") or "").split())
             for c in (edition or {}).get("cached_contributors") or []
             if "narrat" in (c.get("contribution") or "").lower()]
    return ", ".join(n for n in names if n)


def write_better_half(me):
    """Her husband's page, from her "Lids Better Half: Reading Now", "... Next On Deck" and "... Finished"
    lists. A finished book is dated by when it went on the Finished list; a finished book drops off the
    other two lists on the site."""
    prefix = name_key(HALF_LIST)
    shelves = {"reading": [], "next": [], "books": []}
    # hand-kept audiobook narrators and lengths (looked up on the web), by book id, for when
    # the list entry isn't Hardcover's audiobook edition
    extra = json.load(open(HALF_AUDIO)) if os.path.exists(HALF_AUDIO) else {}
    found = False
    for lst in me.get("lists") or []:
        if not name_key(lst["name"]).startswith(prefix):
            continue
        rest = name_key(lst["name"])[len(prefix):]
        shelf = ("books" if rest.startswith("finished") else "reading" if rest.startswith("readingnow")
                 else "next" if rest.startswith("next") else None)
        if not shelf:
            print(f'Skipping list "{lst["name"]}": expected "{HALF_LIST}: Reading Now", "... Next On Deck" or "... Finished"')
            continue
        found = True
        for lb in lst["list_books"]:
            bk, ed = lb["book"], lb.get("edition") or {}
            hid, add = f"hc-{bk['id']}", extra.get(f"hc-{bk['id']}", {})
            # Hardcover's audiobook edition wins, then the hand-kept file, then the book's usual audiobook length
            secs = ed.get("audio_seconds") or 0
            minutes = round(secs / 60) or add.get("minutes") or round((bk.get("audio_seconds") or 0) / 60)
            book = {"id": hid, "title": clean_title(bk["title"]), "author": author(bk),
                    "cover": cover(lb), "narrator": (narrator(ed) if secs else "") or add.get("narrator", ""),
                    "minutes": minutes, "pages": bk.get("pages") or 0,
                    "note": (lb.get("reason") or "").strip()}
            if shelf == "books":
                book["date"] = local_day(lb.get("date_added"))
            shelves[shelf].append(book)
    if not found:
        print(f'No "{HALF_LIST}: ..." lists on Hardcover yet; leaving {os.path.basename(HALF_OUT)} alone')
        return
    done = {b["id"] for b in shelves["books"]}
    for s in ("reading", "next"):
        shelves[s] = [b for b in shelves[s] if b["id"] not in done]
    shelves["next"] = [b for b in shelves["next"] if b["id"] not in {x["id"] for x in shelves["reading"]}]
    shelves["books"].sort(key=lambda b: b["date"], reverse=True)
    this_year = [b for b in shelves["books"] if b["date"].startswith(str(YEAR))]
    out = {"year": YEAR, "finished_this_year": len(this_year),
           "hours_this_year": round(sum(b["minutes"] for b in this_year) / 60), **shelves}
    with open(HALF_OUT, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Lids Better Half: {len(shelves['reading'])} reading, {len(shelves['next'])} next, "
          f"{len(shelves['books'])} finished ({out['hours_this_year']} hours this year)")


if __name__ == "__main__":
    main()
